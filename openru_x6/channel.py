"""Geometric multi-user MIMO channel with mobility, blockage and imperfect CSI.

The channel is a ray-based abstraction: ``H[u, rx, feed, rb]`` in voltage units.
It is not a 3GPP-conformant channel and is not claimed to be.  Sionna RT is used
separately for selected physical-propagation sanity checks.

Temporal consistency: ray directions, random phases and path powers are drawn
once per user set; subsequently only geometry, path loss, blockage and Doppler
phase evolve.  This keeps paired comparisons and CSI-delay experiments valid.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import torch

from .config import RadioConfig
from .polarization import jones_matrices
from .rf import FeedMap, array_response, array_response_geometry, direction_from_angles

K_BOLTZMANN = 1.380649e-23


@dataclass
class ChannelRealization:
    H: torch.Tensor                 # [U, Rx, F, R] complex64
    positions: np.ndarray           # [U,3]
    directions_az_el: np.ndarray    # [U,2] LOS departure angles (deg)
    pathloss_db: np.ndarray         # [U]
    blocked: np.ndarray             # [U] bool
    indoor: np.ndarray              # [U] bool
    los: np.ndarray                 # [U] bool
    delays_s: np.ndarray            # [U,L]
    doppler_hz: np.ndarray          # [U,L]
    noise_power_w: float
    timestamp_s: float = 0.0


class ChannelModel:
    def __init__(self, cfg: RadioConfig, fm: FeedMap, device: torch.device, seed: int) -> None:
        self.cfg = cfg
        self.fm = fm
        self.device = device
        self.rng = np.random.default_rng(seed)
        self.feed_pos_t = torch.as_tensor(fm.feed_positions, dtype=torch.float64, device=device)
        self.n_rb = cfg.cell.n_rb_sim
        self.scs = cfg.cell.subcarrier_spacing_hz
        # Frequency samples must span the configured channel bandwidth, not one
        # subcarrier.  Using SCS here made the "100 MHz" grid only ~480 kHz wide.
        self.subband_spacing_hz = cfg.cell.bandwidth_hz / max(self.n_rb, 1)
        self.n_rx = cfg.cell.n_rx_antennas
        self.noise_w = self.compute_noise_power()
        self._cache: dict[str, Any] | None = None

    # ------------------------------------------------------------------ noise
    def compute_noise_power(self) -> float:
        cell = self.cfg.cell
        ktb = K_BOLTZMANN * cell.temperature_k * cell.bandwidth_hz
        return float(ktb * 10 ** ((cell.noise_figure_db + cell.implementation_margin_db) / 10.0))

    # -------------------------------------------------------------- geometry
    def sample_positions(self, n_users: int, rng: np.random.Generator | None = None) -> np.ndarray:
        rng = rng or self.rng
        ch = self.cfg.channel
        r = rng.uniform(ch.min_distance_m, ch.max_distance_m, n_users)
        az = rng.uniform(-np.pi, np.pi, n_users)
        return np.stack([r * np.cos(az), r * np.sin(az), np.full(n_users, ch.ue_height_m)], axis=1)

    def random_velocities(self, n_users: int, speed_kmh: float = 3.0,
                          rng: np.random.Generator | None = None) -> np.ndarray:
        rng = rng or self.rng
        speed = speed_kmh / 3.6
        ang = rng.uniform(0, 2 * np.pi, n_users)
        return np.stack([speed * np.cos(ang), speed * np.sin(ang), np.zeros(n_users)], axis=1)

    def prepare(self, n_users: int, speed_kmh: float = 3.0,
                rng: np.random.Generator | None = None) -> None:
        """Draw persistent ray parameters for a user set."""
        rng = rng or self.rng
        ch = self.cfg.channel
        U, L = n_users, ch.n_paths
        los = rng.random(U) < ch.los_probability
        indoor = rng.random(U) < ch.indoor_fraction
        az_off = rng.normal(0.0, ch.angular_spread_deg, (U, L))
        el_off = rng.normal(0.0, ch.angular_spread_deg * 0.5, (U, L))
        az_off[:, 0] = 0.0
        el_off[:, 0] = 0.0
        tau = np.sort(rng.exponential(ch.delay_spread_ns * 1e-9, (U, L)), axis=1)
        tau[:, 0] = 0.0
        p = np.exp(-tau / (ch.delay_spread_ns * 1e-9))
        p[los] *= np.array([3.0] + [1.0] * (L - 1))
        p /= p.sum(axis=1, keepdims=True)
        rx_phase = rng.uniform(0, 2 * np.pi, (U, L, self.n_rx))
        speed = max(speed_kmh, 0.1) / 3.6
        self._cache = {
            "n_users": U, "los": los, "indoor": indoor, "az_off": az_off, "el_off": el_off,
            "tau": tau, "power": p, "rx_phase": rx_phase, "speed": speed,
        }

    def _ensure_cache(self, positions: np.ndarray, speed_kmh: float,
                      rng: np.random.Generator | None = None) -> None:
        if self._cache is None or self._cache["n_users"] != positions.shape[0]:
            self.prepare(positions.shape[0], speed_kmh, rng)
        elif abs(self._cache["speed"] - max(speed_kmh, 0.1) / 3.6) > 1e-9:
            self._cache["speed"] = max(speed_kmh, 0.1) / 3.6

    def _los_angles(self, positions: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        ch = self.cfg.channel
        bs = np.array([0.0, 0.0, ch.bs_height_m])
        vec = positions - bs
        dist = np.linalg.norm(vec, axis=1)
        az = np.degrees(np.arctan2(vec[:, 1], vec[:, 0]))
        el = np.degrees(np.arctan2(vec[:, 2], np.hypot(vec[:, 0], vec[:, 1])))
        return az, el, dist, vec

    def pathloss_db(self, positions: np.ndarray, blocked: np.ndarray,
                    los: np.ndarray, indoor: np.ndarray) -> np.ndarray:
        ch = self.cfg.channel
        _, _, dist, _ = self._los_angles(positions)
        shadow = self.rng.normal(0.0, ch.shadowing_std_db, positions.shape[0])
        n = np.where(los & ~blocked, ch.pathloss_exponent_los, ch.pathloss_exponent_nlos)
        fs = 20 * np.log10(4 * np.pi * np.maximum(dist, 1.0) / self.fm.wavelength_m)
        pl = fs + 10 * (n - 2.0) * np.log10(np.maximum(dist, 1.0)) + shadow
        pl = pl + indoor * ch.indoor_penetration_db
        pl = pl + (~los) * ch.nlos_extra_loss_db
        # Blockage is applied exactly once, to the LOS ray amplitude in
        # ``realize``.  Adding it again to the path loss double-counted it and
        # could suppress a blocked LOS ray by 2x blockage_attenuation_db.
        return pl

    # ------------------------------------------------------------- realisation
    def realize(self, positions: np.ndarray, timestamp_s: float = 0.0,
                blocked: np.ndarray | None = None, rng: np.random.Generator | None = None,
                speed_kmh: float = 3.0) -> ChannelRealization:
        rng = rng or self.rng
        self._ensure_cache(positions, speed_kmh, rng)
        c = self._cache
        assert c is not None
        U, L = c["power"].shape
        if blocked is None:
            blocked = rng.random(U) < self.cfg.channel.blockage_probability
        blocked = np.asarray(blocked, dtype=bool)
        az, el, dist, _ = self._los_angles(positions)
        az_l = az[:, None] + c["az_off"]
        el_l = el[:, None] + c["el_off"]
        pl = self.pathloss_db(positions, blocked, c["los"], c["indoor"])
        F, R = self.fm.n_feeds, self.n_rb
        dev = self.device
        # Doppler: radial velocity component along the LOS direction
        v = c["speed"]
        f_d = (v / self.fm.wavelength_m) * np.cos(np.deg2rad(c["az_off"]))
        doppler_phase = np.exp(1j * 2 * np.pi * f_d * timestamp_s)
        # voltage gain relative to 1 W isotropic: sqrt(10^(-PL/10)); path split by power
        amp = np.sqrt(10 ** (-pl[:, None] / 10.0) * c["power"]) * doppler_phase
        # Blockage attenuates the LOS ray exactly once.  Non-LOS rays already use
        # the NLoS path-loss branch and are not attenuated again here.
        amp = amp.copy()
        amp[:, 0] *= np.where(blocked & c["los"], 10 ** (-self.cfg.channel.blockage_attenuation_db / 20.0), 1.0)
        u = direction_from_angles(az_l, el_l).reshape(-1, 3)
        geom = array_response_geometry(self.fm, u).reshape(U, L, F)
        g_t = (torch.as_tensor(amp, dtype=torch.complex64, device=dev).unsqueeze(-1) *
               torch.as_tensor(np.exp(1j * c["rx_phase"]), dtype=torch.complex64, device=dev))
        rb = torch.arange(R, device=dev, dtype=torch.float32)
        tau = torch.as_tensor(c["tau"], dtype=torch.float32, device=dev)
        d = torch.exp(-2j * np.pi * rb[None, None, :] *
                      (self.subband_spacing_hz * tau[..., None]))  # [U,L,R]
        if self.cfg.polarization.model == "jones":
            J = jones_matrices(self.cfg.polarization, U, L, self.n_rx, rng)
            J = J[..., self.fm.feed_pol]  # [U,L,Rx,F]
            h_coeff = torch.as_tensor(geom, dtype=torch.complex64, device=dev)[..., None, :] * \
                torch.as_tensor(J, dtype=torch.complex64, device=dev)
            H = torch.einsum("ulrf,ulr,ulb->urfb", h_coeff, g_t, d)
        else:
            a = (geom * np.where(self.fm.feed_pol == 0, 1.0 + 0j, 1j)).astype(np.complex128)
            a_t = torch.as_tensor(a, dtype=torch.complex64, device=dev)
            H = torch.einsum("ulr,ulf,ulb->urfb", g_t, a_t, d)
        return ChannelRealization(
            H=H, positions=positions.copy(),
            directions_az_el=np.stack([az, el], axis=1),
            pathloss_db=pl, blocked=blocked, indoor=c["indoor"].copy(), los=c["los"].copy(),
            delays_s=c["tau"], doppler_hz=f_d, noise_power_w=self.noise_w,
            timestamp_s=timestamp_s,
        )

    def move(self, positions: np.ndarray, velocities: np.ndarray, dt: float) -> np.ndarray:
        new = positions + velocities * dt
        r = np.linalg.norm(new[:, :2], axis=1)
        far = r > self.cfg.channel.max_distance_m
        new[far, :2] *= (self.cfg.channel.max_distance_m * 0.95) / r[far, None]
        return new
