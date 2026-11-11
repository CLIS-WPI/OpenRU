"""Reconfigurable Intelligent Surface double-hop model.

Geometry-consistent path loss, quantized phases, finite control delay and
imperfect CSI.  The 'oracle' mode is an explicitly unavailable upper bound.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .config import RadioConfig
from .phy import link_adaptation
from .rf import C_LIGHT


@dataclass
class RISResult:
    mode: str
    sinr_db: float
    rate_bps: float
    direct_power_db: float
    ris_power_db: float
    blocked: bool
    phase_error_deg: float
    control_delay_slots: int
    ris_power_w: float
    evidence_class: str = "SIMULATED"


class RISController:
    def __init__(self, cfg: RadioConfig, n_elements: int = 256, phase_bits: int = 2,
                 efficiency: float = 0.7, ris_pos: tuple[float, float, float] = (55.0, 10.0, 12.0),
                 control_delay_slots: int = 2, ris_power_w: float = 4.0,
                 csi_phase_error_deg: float = 8.0) -> None:
        self.cfg = cfg
        self.n = n_elements
        self.bits = phase_bits
        self.eta = efficiency
        self.pos = np.asarray(ris_pos, dtype=float)
        self.delay = control_delay_slots
        self.power_w = ris_power_w
        self.csi_err = csi_phase_error_deg
        self.lam = C_LIGHT / cfg.cell.carrier_freq_hz
        side = int(round(np.sqrt(n_elements)))
        self.rows, self.cols = side, side
        self.n = side * side
        self._phase_history: list[np.ndarray] = []
        self._last_phases = np.zeros(self.n)

    def _elem_positions(self) -> np.ndarray:
        d = self.lam / 2
        ys = (np.arange(self.cols) - (self.cols - 1) / 2) * d
        zs = (np.arange(self.rows) - (self.rows - 1) / 2) * d
        yy, zz = np.meshgrid(ys, zs)
        return np.stack([np.full(yy.size, self.pos[0]), self.pos[1] + yy.ravel(),
                         self.pos[2] + zz.ravel()], axis=1)

    def _geo_phases(self, ue_pos: np.ndarray) -> tuple[np.ndarray, float, float]:
        elems = self._elem_positions()
        bs = np.array([0.0, 0.0, self.cfg.channel.bs_height_m])
        d1 = np.linalg.norm(elems - bs, axis=1)
        d2 = np.linalg.norm(elems - ue_pos, axis=1)
        k = 2 * np.pi / self.lam
        theta = k * (d1 + d2)
        return theta, float(np.linalg.norm(self.pos - bs)), float(np.linalg.norm(self.pos - ue_pos))

    def _phase_profile(self, theta: np.ndarray, mode: str, rng: np.random.Generator,
                       slot: int) -> tuple[np.ndarray, float]:
        if mode == "off":
            return np.zeros_like(theta), 0.0
        if mode == "random":
            return rng.uniform(0, 2 * np.pi, theta.size), 0.0
        if mode == "oracle":
            return -theta, 0.0
        # practical: stale CSI + imperfect estimate + quantization
        if len(self._phase_history) >= self.delay:
            stale = self._phase_history[-self.delay]
        else:
            stale = self._last_phases
        est = stale + rng.normal(0.0, np.deg2rad(self.csi_err), theta.size)
        phi = -est
        step = 2 * np.pi / (2 ** self.bits)
        phi_q = np.round(phi / step) * step
        err = float(np.rad2deg(np.sqrt(np.mean((phi_q - (-theta)) ** 2))))
        self._phase_history.append(theta.copy())
        self._last_phases = theta.copy()
        return phi_q, err

    def evaluate(self, ue_pos: np.ndarray, mode: str, rng: np.random.Generator,
                 slot: int = 0, direct_blocked: bool = True) -> RISResult:
        theta, d1, d2 = self._geo_phases(ue_pos)
        phi, phase_err = self._phase_profile(theta, mode, rng, slot)
        # direct link (voltage for 1 W isotropic; single-feed reference, no BS array gain)
        d_direct = float(np.linalg.norm(ue_pos - np.array([0.0, 0.0, self.cfg.channel.bs_height_m])))
        h_direct = self.lam / (4 * np.pi * max(d_direct, 1.0))
        if direct_blocked:
            h_direct *= 10 ** (-self.cfg.channel.blockage_attenuation_db / 20.0)
        # double hop: N coherent elements
        h_elem = (self.lam / (4 * np.pi)) ** 2 * np.sqrt(self.eta) / (d1 * d2)
        h_ris = h_elem * np.sum(np.exp(1j * (theta + phi)))
        h_total = h_direct + h_ris
        p_tx = 10 ** (self.cfg.mimo.total_tx_power_dbm / 10.0) / 1000.0
        noise = 1.380649e-23 * self.cfg.cell.temperature_k * self.cfg.cell.bandwidth_hz * \
            10 ** ((self.cfg.cell.noise_figure_db + self.cfg.cell.implementation_margin_db) / 10.0)
        # modest BS array gain for a fair SISO comparison
        array_gain = 64.0
        sinr = p_tx * array_gain * abs(h_total) ** 2 / noise
        sinr_db = 10 * np.log10(max(sinr, 1e-30))
        la = link_adaptation(np.array([sinr_db]), self.cfg.cell.bandwidth_hz, self.cfg.mimo)
        direct_db = 20 * np.log10(max(abs(h_direct), 1e-30))
        ris_db = 20 * np.log10(max(abs(h_ris), 1e-30))
        return RISResult(mode, float(sinr_db), float(la["rate_bps"][0]), float(direct_db),
                         float(ris_db), direct_blocked, phase_err,
                         self.delay if mode == "practical" else 0, self.power_w)
