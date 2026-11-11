"""Integrated Sensing and Communication (ISAC) abstraction.

Radar equation + square-law detection with clutter.  The online scheduling
controller only sees past detections/estimates; future target truth is never
provided to it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy.stats import ncx2

from .config import RadioConfig

K_BOLTZMANN = 1.380649e-23


@dataclass
class Target:
    range_m: float
    velocity_mps: float
    rcs_m2: float = 1.0
    azimuth_deg: float = 0.0
    present_slots: tuple[int, int] = (10, 60)


@dataclass
class SensingTrack:
    last_detect_slot: int | None = None
    detections: int = 0
    misses: int = 0
    range_est_m: float | None = None
    velocity_est_mps: float | None = None


class ISACController:
    def __init__(self, cfg: RadioConfig, budget_fraction: float, policy: str,
                 rng: np.random.Generator, clutter_cnr_db: float = 10.0,
                 pfa_target: float = 1e-6, n_range_cells: int = 128,
                 n_doppler_cells: int = 64) -> None:
        self.cfg = cfg
        self.budget = budget_fraction
        self.policy = policy
        self.rng = rng
        self.clutter_cnr_db = clutter_cnr_db
        self.pfa_target = pfa_target
        self.n_cells = n_range_cells * n_doppler_cells
        self.tracks: dict[int, SensingTrack] = {}
        self.sense_slots = 0
        self.total_slots = 0
        self.detections = 0
        self.misses = 0
        self.false_alarms = 0
        self.looks = 0
        self.hits = 0
        self.sensing_energy_j = 0.0
        self.detection_slots: dict[int, int] = {}
        self._last_sense_slot = -10_000
        self._tokens = 0.0

    def _snr_linear(self, target: Target, n_symbols: int) -> float:
        cell = self.cfg.cell
        lam = 299_792_458.0 / cell.carrier_freq_hz
        p_tx = 10 ** (self.cfg.mimo.total_tx_power_dbm / 10.0) / 1000.0
        g = 256.0  # coherent array gain assumption (documented)
        ktb = K_BOLTZMANN * cell.temperature_k * cell.bandwidth_hz
        nf = 10 ** ((cell.noise_figure_db + cell.implementation_margin_db) / 10.0)
        loss = 10 ** (3.0 / 10.0)
        snr = (p_tx * g * g * lam ** 2 * target.rcs_m2) / (
            (4 * np.pi) ** 3 * max(target.range_m, 1.0) ** 4 * ktb * nf * loss)
        snr_int = snr * n_symbols
        cnr = 10 ** (self.clutter_cnr_db / 10.0)
        return float(snr_int / (1.0 + cnr))

    def _detect(self, snr: float) -> tuple[bool, bool]:
        eta = -np.log(self.pfa_target)
        pd = float(ncx2.sf(2 * eta, 2, 2 * snr))
        detected = self.rng.random() < pd
        pfa_cell = self.pfa_target
        false_alarm = self.rng.random() < min(1.0, pfa_cell * self.n_cells)
        return detected, false_alarm

    def decide(self, slot: int) -> bool:
        if self.policy == "off" or self.budget <= 0:
            return False
        if self.policy == "periodic":
            period = max(1, int(round(1.0 / self.budget)))
            return slot % period == 0
        # Adaptive token bucket: average sensing cost never exceeds the budget.
        # Dense sampling is triggered only by stale *past* tracks, never future truth.
        self._tokens = min(2.0, self._tokens + self.budget)
        if self._tokens < 1.0:
            return False
        stale = any((slot - (t.last_detect_slot if t.last_detect_slot is not None else -10_000)) > 8
                    for t in self.tracks.values())
        if len(self.tracks) == 0 or stale:
            self._tokens -= 1.0
            return True
        # otherwise sample with probability proportional to remaining budget
        if self.rng.random() < self.budget:
            self._tokens -= 1.0
            return True
        return False

    def step(self, slot: int, targets: list[Target], n_symbols_per_slot: int,
             comm_rate_bps: float, slot_duration_s: float) -> dict[str, Any]:
        self.total_slots += 1
        sensing = self.decide(slot)
        actual_fraction = 0.0
        n_symbols = 0
        det_events = []
        fa_events = 0
        if sensing:
            self.sense_slots += 1
            self._last_sense_slot = slot
            # a sensing slot consumes the full slot airtime; the budget is enforced
            # by the duty cycle / token bucket above, so all policies are cost-matched.
            n_symbols = n_symbols_per_slot
            actual_fraction = 1.0
            self.sensing_energy_j += (10 ** (self.cfg.mimo.total_tx_power_dbm / 10.0) / 1000.0) * \
                slot_duration_s * actual_fraction
            fa_once = self.rng.random() < min(1.0, self.pfa_target * self.n_cells)
            if fa_once:
                fa_events += 1
                self.false_alarms += 1
            for ti, t in enumerate(targets):
                if not (t.present_slots[0] <= slot < t.present_slots[1]):
                    continue
                tr = self.tracks.setdefault(ti, SensingTrack())
                snr = self._snr_linear(t, n_symbols)
                det, _fa = self._detect(snr)
                self.looks += 1
                self.hits += int(det)
                if det:
                    if ti not in self.detection_slots:
                        self.detection_slots[ti] = slot
                    tr.last_detect_slot = slot
                    tr.detections += 1
                    self.detections += 1
                    sigma_r = 299_792_458.0 / (2 * self.cfg.cell.bandwidth_hz * np.sqrt(2 * max(snr, 1e-12)))
                    sigma_v = (299_792_458.0 / self.cfg.cell.carrier_freq_hz) / (
                        2 * slot_duration_s * n_symbols * np.sqrt(2 * max(snr, 1e-12)))
                    tr.range_est_m = t.range_m + self.rng.normal(0, sigma_r / 2)
                    tr.velocity_est_mps = t.velocity_mps + self.rng.normal(0, sigma_v / 2)
                    det_events.append({"target": ti, "snr_db": 10 * np.log10(max(snr, 1e-12)),
                                       "range_est_m": tr.range_est_m,
                                       "range_error_m": abs(tr.range_est_m - t.range_m)})
                else:
                    tr.misses += 1
                    self.misses += 1
        comm_rate = comm_rate_bps * (1.0 - actual_fraction)
        return {
            "slot": slot, "sensing": bool(sensing), "actual_fraction": actual_fraction,
            "comm_rate_bps": comm_rate, "detections": det_events, "false_alarms": fa_events,
            "n_tracks": len(self.tracks),
        }

    def _mean_range_error(self, targets: list[Target]) -> float | None:
        errs = []
        for ti, t in enumerate(targets):
            tr = self.tracks.get(ti)
            if tr is not None and tr.range_est_m is not None:
                errs.append(abs(tr.range_est_m - t.range_m))
        return float(np.mean(errs)) if errs else None

    def summary(self, targets: list[Target], eval_slots: int) -> dict[str, Any]:
        detected_targets = sum(1 for ti, t in enumerate(targets) if ti in self.detection_slots)
        latencies = []
        for ti, t in enumerate(targets):
            if ti in self.detection_slots:
                latencies.append(max(0, self.detection_slots[ti] - t.present_slots[0]))
        mins = eval_slots * self.cfg.cell.slot_duration_s / 60.0
        return {
            "budget_fraction": self.budget,
            "policy": self.policy,
            "realized_sensing_fraction": self.sense_slots / max(self.total_slots, 1),
            "pd": detected_targets / max(len(targets), 1),
            "pd_per_look": self.hits / max(self.looks, 1),
            "pfa_per_minute": self.false_alarms / max(mins, 1e-9),
            "pfa_per_sensing_look": self.false_alarms / max(self.sense_slots, 1),
            "sensing_looks": self.looks,
            "mean_detection_latency_slots": float(np.mean(latencies)) if latencies else None,
            "sensing_energy_j": self.sensing_energy_j,
            "sensing_overhead_fraction": self.sense_slots / max(self.total_slots, 1),
            "mean_abs_range_error_m": self._mean_range_error(targets),
        }
