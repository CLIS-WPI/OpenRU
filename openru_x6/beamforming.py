"""Hybrid analog beam selection and digital precoding."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch

from .config import MimoConfig
from .rf import FeedMap, RFHardware


@dataclass
class BeamChoice:
    F_RF: torch.Tensor            # [F,C] complex64
    chain_user: np.ndarray        # [C] assigned scheduled-user index (-1 if inactive)
    directions_deg: np.ndarray    # [C,2] az/el used per chain
    active_chains: int


def select_analog_beams(hw: RFHardware, fm: FeedMap, n_sched: int,
                        est_dir_deg: np.ndarray, rng: np.random.Generator,
                        cfg: MimoConfig) -> BeamChoice:
    """Assign every active chain to one scheduled user's estimated direction.

    Chains are distributed as evenly as possible, with extra chains given to the
    users with the weakest estimated large-scale channel (path loss).  The
    analog beam is quantized and impaired by the hardware model, so quantisation
    and calibration errors propagate into the effective channel.
    """
    active = np.flatnonzero(hw.chain_enabled)
    C = fm.n_chains
    chain_user = np.full(C, -1, dtype=int)
    dirs = np.zeros((C, 2))
    if active.size == 0 or n_sched == 0:
        return BeamChoice(F_RF=torch.zeros((fm.n_feeds, C), dtype=torch.complex64, device="cpu"),
                          chain_user=chain_user, directions_deg=dirs, active_chains=0)
    # weighted round-robin: user order is fixed, extra chains repeat strongest demand
    order = np.arange(active.size) % n_sched
    chain_user[active] = order
    dirs[active] = est_dir_deg[np.asarray(chain_user[active])]
    # unique user directions tensor indexed by chain
    chain_dirs = np.zeros((C, 3))
    for c in active:
        u = int(chain_user[c])
        az, el = np.deg2rad(dirs[c, 0]), np.deg2rad(dirs[c, 1])
        chain_dirs[c] = [np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)]
    F = hw.analog_weights(chain_dirs, np.maximum(chain_user, 0), rng,
                          cfg.analog_amplitude_error_db, cfg.analog_phase_error_deg,
                          cfg.calibration_phase_error_deg, cfg.phase_shifter_bits)
    for c in range(C):
        if not hw.chain_enabled[c]:
            F[:, c] = 0
    return BeamChoice(F_RF=torch.as_tensor(F, dtype=torch.complex64), chain_user=chain_user,
                      directions_deg=dirs, active_chains=int(active.size))


@dataclass
class MimoResult:
    users: np.ndarray
    sinr_db: np.ndarray            # [K] effective over RBs
    sinr_db_per_rb: np.ndarray     # [K,R]
    rate_bps: np.ndarray           # [K] delivered goodput after resource accounting
    capacity_bps: np.ndarray       # [K] spectral-efficiency bound before TDD/overhead
    se_bits_s_hz: np.ndarray       # [K]
    bler: np.ndarray               # [K]
    mcs_index: np.ndarray          # [K]
    useful_layers: int
    condition_number: float
    tx_power_w: float
    per_chain_power_w: np.ndarray
    power_limited: bool
    rank_singular_values: np.ndarray
    F_RF: torch.Tensor
    F_BB: torch.Tensor


def _rx_combine(H_eff: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """MRC receive vector per user from [K,Rx,C,R] effective channel."""
    U, Rx, C, R = H_eff.shape
    cov = torch.einsum("urcb,uscb->urs", H_eff, H_eff.conj())  # [U,Rx,Rx]
    # principal eigenvector of 2x2 Hermitian matrix (analytical for Rx<=2)
    if Rx == 1:
        v = torch.ones((U, 1, 1), dtype=H_eff.dtype, device=H_eff.device)
    else:
        a = cov[:, 0, 0].real
        d = cov[:, 1, 1].real
        b = cov[:, 0, 1]
        # eigenvector for largest eigenvalue
        lam = 0.5 * (a + d) + torch.sqrt(0.25 * (a - d) ** 2 + torch.abs(b) ** 2)
        v1 = torch.stack([b, lam - a], dim=1)
        v2 = torch.stack([lam - d, b.conj()], dim=1)
        n1 = torch.linalg.norm(v1, dim=1, keepdim=True)
        n2 = torch.linalg.norm(v2, dim=1, keepdim=True)
        v1 = v1 / torch.clamp(n1, min=1e-12)
        v2 = v2 / torch.clamp(n2, min=1e-12)
        v = torch.where(n1 >= n2, v1, v2).unsqueeze(-1)
    G = torch.einsum("ur,urcb->ucb", v[:, :, 0].conj(), H_eff)  # [U,C,RB]
    return v[:, :, 0], G


def _digital_precoder(G: torch.Tensor, cfg: MimoConfig) -> torch.Tensor:
    """G [K,C] -> W [C,K] with unit-norm columns."""
    K, C = G.shape
    if cfg.precoder == "mf":
        W = G.conj().T
    else:
        GGram = G @ G.conj().T
        alpha = cfg.rzf_alpha if cfg.precoder == "rzf" else 0.0
        reg = alpha * torch.eye(K, dtype=G.dtype, device=G.device) * torch.clamp(
            torch.diagonal(GGram).real.mean(), min=1e-12)
        try:
            inv = torch.linalg.inv(GGram + reg)
        except Exception:
            inv = torch.linalg.pinv(GGram)
        W = G.conj().T @ inv
    W = W / torch.clamp(torch.linalg.norm(W, dim=0, keepdim=True), min=1e-12)
    return W


def evaluate_mimo(H: torch.Tensor, hw: RFHardware, users: np.ndarray,
                  est_dir_deg: np.ndarray, cfg: MimoConfig, rng: np.random.Generator,
                  noise_power_w: float, bandwidth_hz: float, phy: object | None = None,
                  return_internals: bool = False, H_est: torch.Tensor | None = None,
                  resource: dict[str, object] | None = None) -> MimoResult:
    """Compute MU-MIMO SINR/throughput for selected users.

    ``H`` is the *true* channel.  ``est_dir_deg`` are the angles available to the
    beamformer (imperfect CSI is injected by the caller).
    """
    from .phy import link_adaptation

    K = len(users)
    if K == 0:
        z = np.zeros(0)
        return MimoResult(users=users, sinr_db=z, sinr_db_per_rb=np.zeros((0, H.shape[-1])),
                          rate_bps=z, capacity_bps=z, se_bits_s_hz=z, bler=z,
                          mcs_index=np.zeros(0, dtype=int),
                          useful_layers=0, condition_number=float("inf"), tx_power_w=0.0,
                          per_chain_power_w=np.zeros(hw.fm.n_chains), power_limited=False,
                          rank_singular_values=np.zeros(0),
                          F_RF=torch.zeros((hw.fm.n_feeds, hw.fm.n_chains)),
                          F_BB=torch.zeros((hw.fm.n_chains, 0)))
    device = H.device
    H_sel = H[users]  # [K,Rx,F,R]
    beam = select_analog_beams(hw, hw.fm, K, est_dir_deg, rng, cfg)
    F_RF = beam.F_RF.to(device)
    # effective channel [K,Rx,C,R]
    H_eff = torch.einsum("krfb,fc->krcb", H_sel.to(torch.complex64), F_RF)
    _, G_rb = _rx_combine(H_eff)                 # [K,C,RB]
    G_avg = G_rb.mean(dim=-1)                     # [K,C]
    if H_est is not None:
        H_est_sel = H_est[users].to(torch.complex64)
        H_eff_est = torch.einsum("krfb,fc->krcb", H_est_sel, F_RF)
        _, G_est_rb = _rx_combine(H_eff_est)
        G_pre = G_est_rb.mean(dim=-1)
    else:
        G_pre = G_avg
    # imperfect CSI at the precoder (not at the true SINR evaluation)
    if cfg.csi_phase_error_deg > 0 or cfg.csi_amplitude_error_db > 0:
        pe = torch.as_tensor(np.deg2rad(rng.normal(0.0, cfg.csi_phase_error_deg, G_pre.shape[1])),
                             dtype=torch.float32, device=device)
        ae = torch.as_tensor(10 ** (rng.normal(0.0, cfg.csi_amplitude_error_db, G_pre.shape[1]) / 20.0),
                             dtype=torch.float32, device=device)
        G_est = G_pre * torch.exp(1j * pe)[None, :] * ae[None, :]
    else:
        G_est = G_pre
    W = _digital_precoder(G_est, cfg)             # [C,K]
    tx_dbm = cfg.total_tx_power_dbm
    if hw.tx_power_limit_dbm is not None:
        tx_dbm = min(tx_dbm, hw.tx_power_limit_dbm)
    P_total = 10 ** (tx_dbm / 10.0) / 1000.0
    scale = np.sqrt(P_total / K)
    W_scaled = W * scale
    # per-chain power (F_RF columns orthonormal)
    chain_p = (torch.abs(W_scaled) ** 2).sum(dim=1).detach().cpu().numpy()
    cap = 10 ** (cfg.per_chain_power_cap_dbm / 10.0) / 1000.0
    power_limited = bool(chain_p.max() > cap)
    if power_limited:
        s = np.sqrt(cap / chain_p.max())
        W_scaled = W_scaled * s
        scale *= s
        chain_p = chain_p * s ** 2
    # SINR per RB (true channel)
    sig = torch.einsum("kcb,ck->kb", G_rb, W_scaled)
    all_rx = torch.einsum("kcb,cm->kbm", G_rb, W_scaled)
    p_sig = torch.abs(sig) ** 2
    p_int = (torch.abs(all_rx) ** 2).sum(dim=-1) - p_sig
    noise = torch.tensor(noise_power_w, dtype=torch.float32, device=device)
    sinr = p_sig / torch.clamp(p_int + noise, min=1e-30)
    sinr_db_rb = 10 * torch.log10(torch.clamp(sinr, min=1e-12))
    sinr_eff = sinr.mean(dim=-1)  # wideband linear average (documented abstraction)
    sinr_db = (10 * torch.log10(torch.clamp(sinr_eff, min=1e-12))).cpu().numpy()
    # rank / useful layers
    G_rank = G_avg / torch.clamp(torch.linalg.norm(G_avg, dim=1, keepdim=True), min=1e-30)
    try:
        sv = torch.linalg.svdvals(G_rank.to(torch.complex64)).cpu().numpy()
    except Exception:
        sv = np.linalg.svd(G_rank.to(torch.complex64).cpu().numpy(), compute_uv=False)
    useful = int(np.sum(sv > cfg.rank_threshold * max(sv[0] if sv.size else 0.0, 1e-12)))
    useful = min(useful, K, hw.active_chains())
    cond = float(sv[0] / max(sv[-1], 1e-12)) if sv.size else float("inf")
    la = link_adaptation(sinr_db, bandwidth_hz, cfg, phy=phy, resource=resource)
    return MimoResult(
        users=users, sinr_db=sinr_db, sinr_db_per_rb=sinr_db_rb.cpu().numpy(),
        rate_bps=la["rate_bps"], capacity_bps=la["capacity_bps"],
        se_bits_s_hz=la["se"], bler=la["bler"],
        mcs_index=la["mcs"], useful_layers=useful, condition_number=cond,
        tx_power_w=float((chain_p.sum())), per_chain_power_w=chain_p,
        power_limited=power_limited, rank_singular_values=sv,
        F_RF=F_RF.detach().cpu(), F_BB=W_scaled.detach().cpu(),
    )
