"""E00: environment, mathematical and physical sanity checks."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import numpy as np
import torch

from ..beamforming import evaluate_mimo
from ..config import config_digest
from ..energy import power_breakdown, state_chains
from ..engine import SimContext, mask_for_chains
from ..metrics import write_json
from ..phy import sionna_phy_validation
from ..rf import RFHardware, array_response, build_feed_map, direction_from_angles
from .common import digest, make_context, make_result, params_for, run_engine


def _gpu_sanity() -> dict[str, object]:
    ok = torch.cuda.is_available()
    out: dict[str, object] = {"cuda_available": bool(ok)}
    if ok:
        dev = torch.device("cuda")
        a = torch.randn(1024, 1024, device=dev)
        b = torch.randn(1024, 1024, device=dev)
        c = a @ b
        torch.cuda.synchronize()
        out.update({"device_name": torch.cuda.get_device_name(0),
                    "matmul_finite": bool(torch.isfinite(c).all().item()),
                    "vram_allocated_mb": float(torch.cuda.memory_allocated() / 2**20),
                    "cuda_version": torch.version.cuda})
    return out


def _sionna_rt_check(freq_hz: float) -> dict[str, object]:
    import sionna.rt as rt
    import sionna.rt.scenes as scenes

    path = os.path.join(os.path.dirname(scenes.__file__), "floor_wall", "floor_wall.xml")
    scene = rt.load_scene(path)
    scene.frequency = freq_hz
    scene.tx_array = rt.PlanarArray(num_rows=1, num_cols=2, vertical_spacing=0.5,
                                    horizontal_spacing=0.5, pattern="iso", polarization="V")
    scene.rx_array = rt.PlanarArray(num_rows=1, num_cols=2, vertical_spacing=0.5,
                                    horizontal_spacing=0.5, pattern="iso", polarization="V")
    tx = rt.Transmitter(name="e00_tx", position=[-1.5, 0.0, 1.5], look_at=[1.5, 0.0, 1.0])
    rx = rt.Receiver(name="e00_rx", position=[1.5, 0.0, 1.0])
    scene.add(tx)
    scene.add(rx)
    paths = rt.PathSolver()(scene, max_depth=2, los=True, specular_reflection=True,
                            diffuse_reflection=False, refraction=False, seed=7)
    a, tau = paths.cir()
    coeff = np.asarray(a[0])
    power = float(np.sum(np.abs(coeff) ** 2))
    distance = float(np.linalg.norm(np.array([1.5, 0, 1.0]) - np.array([-1.5, 0, 1.5])))
    lam = 299_792_458.0 / freq_hz
    fspl = float(20 * np.log10(4 * np.pi * distance / lam))
    rt_pl = float(-10 * np.log10(max(power, 1e-30)))
    return {"scene": "floor_wall", "distance_m": distance, "rt_power_linear": power,
            "rt_pathloss_db": rt_pl, "free_space_pathloss_db": fspl,
            "difference_db": rt_pl - fspl,
            "nonzero_coefficients": int(np.sum(np.abs(coeff) > 0)),
            "num_paths": int(np.asarray(paths.valid).sum()),
            "evidence_class": "PHY_VALIDATED",
            "note": "Sionna RT path solve in a bundled simple scene; not a site-specific calibration."}


def run(radio, energy, security, suite, out_dir: Path, store) -> object:
    t0 = time.time()
    p = params_for("E00", suite)
    out_dir.mkdir(parents=True, exist_ok=True)
    dg = config_digest(radio, energy, security, suite)
    checks: dict[str, bool] = {}
    metrics: dict[str, object] = {}
    artifacts: list[str] = []

    gpu = _gpu_sanity()
    checks["cuda_available"] = bool(gpu.get("cuda_available"))
    checks["cuda_matmul_finite"] = bool(gpu.get("matmul_finite", False))
    metrics["gpu"] = gpu

    fm = build_feed_map(radio.array, radio.cell.carrier_freq_hz)
    checks["feed_map_valid"] = not fm.validate()
    mask_sums = {}
    for n in (8, 16, 32, 64):
        m = mask_for_chains(n)
        mask_sums[str(n)] = int(m.sum())
        if n != 64:
            n_expected = min(n, radio.array.n_tiles)
            checks[f"mask_{n}_tile_spread"] = bool(
                len(set(fm.chain_tile[m].tolist())) == n_expected)
    checks["mask_sums_exact"] = all(mask_sums[str(n)] == n for n in (8, 16, 32, 64))
    metrics["mask_sums"] = mask_sums

    pb0 = power_breakdown(energy, "SLEEP_0", tx_power_w=0.0, fan_ok=True)
    checks["zero_tx_has_zero_pa"] = pb0["pa_dc"] == 0.0 and pb0["rf_chains"] == 0.0
    metrics["sleep0_power_w"] = pb0["total_w"]
    checks["full_state_has_more_power_than_eco"] = (
        power_breakdown(energy, "FULL_64", 20.0)["total_w"]
        > power_breakdown(energy, "ECO_16", 20.0)["total_w"])

    lam = 299_792_458.0 / radio.cell.carrier_freq_hz
    fspl_100 = float(20 * np.log10(4 * np.pi * 100.0 / lam))
    noise = float(1.380649e-23 * radio.cell.temperature_k * radio.cell.bandwidth_hz *
                  10 ** ((radio.cell.noise_figure_db + radio.cell.implementation_margin_db) / 10))
    metrics.update({"fspl_100m_db": fspl_100, "noise_power_w": noise})
    checks["fspl_plausible"] = 85.0 <= fspl_100 <= 100.0
    checks["noise_plausible"] = 1e-14 <= noise <= 1e-11

    hw = RFHardware(radio.array, fm, telemetry_seed=0xE00)
    hw.set_chain_mask(np.zeros(fm.n_chains, dtype=bool))
    hw.chain_enabled[0] = True
    u = direction_from_angles(np.array([17.0]), np.array([-3.0]))
    a_feeds = array_response(fm, u).reshape(-1)[fm.feed_chain == 0]
    weights = hw.analog_weights(np.repeat(u.reshape(1, 3), fm.n_chains, axis=0),
                                np.zeros(fm.n_chains, dtype=int), np.random.default_rng(1),
                                0.0, 0.0, 0.0, phase_bits=8)[fm.feed_chain == 0, 0]
    matched = float(np.abs(np.vdot(a_feeds, weights)))
    random_ph = np.exp(1j * np.random.default_rng(2).uniform(0, 2 * np.pi, a_feeds.size))
    unmatched = float(np.abs(np.vdot(a_feeds, random_ph / np.sqrt(a_feeds.size))))
    metrics["beam_matched_gain"] = matched
    metrics["beam_random_gain"] = unmatched
    checks["beam_steering_has_gain"] = matched > 2.5 * max(unmatched, 1e-6)

    try:
        phy = sionna_phy_validation(p.get("snr_db"))
        write_json(out_dir / "e00_sionna_phy.json", phy)
        artifacts.append("e00_sionna_phy.json")
        rows = phy["rows"]
        hi = [r for r in rows if r["snr_db"] >= 6.0]
        lo = [r for r in rows if r["snr_db"] <= 2.0]
        checks["sionna_phy_runs"] = len(rows) == len(p.get("snr_db", rows))
        checks["sionna_bler_decreases"] = bool(np.mean([r["bler"] for r in hi]) <
                                               np.mean([r["bler"] for r in lo]))
        metrics["sionna_phy_high_snr_bler"] = float(np.mean([r["bler"] for r in hi]))
        metrics["sionna_phy_low_snr_bler"] = float(np.mean([r["bler"] for r in lo]))
    except Exception as exc:  # noqa: BLE001
        checks["sionna_phy_runs"] = False
        metrics["sionna_phy_error"] = f"{type(exc).__name__}: {exc}"
    if "sionna_phy_high_snr_bler" in metrics:
        store.add("E00", "sionna_phy", 7, "sionna", "high_snr_bler",
                  float(metrics["sionna_phy_high_snr_bler"]), "", "PHY_VALIDATED", dg)
        store.add("E00", "sionna_phy", 7, "sionna", "low_snr_bler",
                  float(metrics["sionna_phy_low_snr_bler"]), "", "PHY_VALIDATED", dg)

    try:
        rtres = _sionna_rt_check(radio.cell.carrier_freq_hz)
        write_json(out_dir / "e00_sionna_rt.json", rtres)
        artifacts.append("e00_sionna_rt.json")
        metrics["sionna_rt"] = rtres
        checks["sionna_rt_runs"] = rtres["nonzero_coefficients"] > 0
        checks["sionna_rt_pathloss_plausible"] = 40.0 <= rtres["rt_pathloss_db"] <= 130.0
        checks["sionna_rt_close_to_fspl"] = abs(rtres["difference_db"]) < 30.0
    except Exception as exc:  # noqa: BLE001
        checks["sionna_rt_runs"] = False
        metrics["sionna_rt_error"] = f"{type(exc).__name__}: {exc}"
    if isinstance(metrics.get("sionna_rt"), dict):
        store.add("E00", "sionna_rt", 7, "sionna", "rt_pathloss_db",
                  float(metrics["sionna_rt"]["rt_pathloss_db"]), "dB", "PHY_VALIDATED", dg)

    ctx = make_context(radio, seed=7, n_users=16, n_slots=2, channel_update_slots=2, saturate=True)
    r = run_engine(radio, energy, security, ctx, forced_chains=64, scheduler_policy="pf",
                   energy_kind="static")
    record_extra = {"mean_sinr_db": r.summary["mean_sinr_db"],
                    "spectral_efficiency_bps_hz": r.summary["spectral_efficiency_bps_hz"]}
    checks["engine_runs"] = bool(np.isfinite(r.summary["mean_sinr_db"]))
    checks["engine_nonnegative_rate"] = r.summary["sum_goodput_mbps"] >= 0
    checks["engine_no_negative_energy"] = r.summary["energy_j"] > 0
    metrics["engine_smoke"] = {k: r.summary[k] for k in
                               ("sum_goodput_mbps", "mean_sinr_db", "mean_power_w", "energy_j")}
    for k, v in record_extra.items():
        store.add("E00", "smoke", 7, "static", k, v, "", "SIMULATED", dg)

    res = make_result("E00", "Docker/GPU, mathematical and physical sanity", t0, checks, metrics)
    res.artifacts = artifacts
    return res


def record_extra(*args, **kwargs):  # pragma: no cover - compatibility
    return None
