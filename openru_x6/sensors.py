"""Sensor-failure transforms for held-out diagnostic challenges.

These transforms deliberately corrupt only the telemetry dictionary; physical
fault labels and future channel state remain hidden from the detector.  They are
simulation instruments for P1-E, not a model of a particular board sensor bus.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

import numpy as np


SENSOR_FAULT_TYPES = [
    "missing", "stuck_at", "frozen", "biased", "drifting", "quantized",
    "stale", "inconsistent",
]
_FEATURES = ["gain_db_mean", "gain_db_std", "phase_error_deg_rms", "vswr_max",
             "temp_c", "supply_v", "ptp_offset_ns", "noise_fig_db_max", "fan_fail"]


@dataclass
class SensorFaultSpec:
    kind: str
    onset_slot: int = 0
    duration_slots: int = 10_000
    tile: int = 3
    feature: str = "gain_db_mean"
    magnitude: float = 5.0
    quantum: float = 0.5


@dataclass
class SensorFaultInjector:
    specs: list[SensorFaultSpec] = field(default_factory=list)
    _last: dict[str, Any] | None = None
    _last_tile: dict[int, dict[str, Any]] = field(default_factory=dict)

    def active(self, slot: int) -> list[SensorFaultSpec]:
        return [s for s in self.specs if s.onset_slot <= slot < s.onset_slot + s.duration_slots]

    def step(self, telemetry: dict[str, Any], slot: int, rng: np.random.Generator | None = None) -> dict[str, Any]:
        rng = rng or np.random.default_rng(0)
        tel = deepcopy(telemetry)
        active = self.active(slot)
        if not active:
            self._last = deepcopy(tel)
            self._last_tile = {int(t["tile"]): deepcopy(t) for t in tel["per_tile"]}
            return tel
        # A stale bus freezes the whole snapshot for the duration.
        if any(s.kind == "stale" for s in active) and self._last is not None:
            return deepcopy(self._last)
        for s in active:
            for t in tel["per_tile"]:
                if int(t["tile"]) != int(s.tile):
                    continue
                if s.kind == "missing":
                    t[s.feature] = float("nan")
                elif s.kind == "stuck_at":
                    t[s.feature] = 0.0
                elif s.kind == "frozen" and s.tile in self._last_tile:
                    t[s.feature] = self._last_tile[s.tile].get(s.feature, t[s.feature])
                elif s.kind == "biased":
                    t[s.feature] = float(t[s.feature]) + s.magnitude
                elif s.kind == "drifting":
                    elapsed = max(0, slot - s.onset_slot)
                    t[s.feature] = float(t[s.feature]) + s.magnitude * elapsed / 100.0
                elif s.kind == "quantized":
                    q = max(float(s.quantum), 1e-12)
                    t[s.feature] = round(float(t[s.feature]) / q) * q
                elif s.kind == "inconsistent":
                    # A calibration-like inconsistency: high mean gain with an
                    # implausibly low tile-to-tile spread.
                    t["gain_db_mean"] = float(t["gain_db_mean"]) + s.magnitude
                    t["gain_db_std"] = 0.0
                break
        self._last = deepcopy(tel)
        self._last_tile = {int(t["tile"]): deepcopy(t) for t in tel["per_tile"]}
        return tel
