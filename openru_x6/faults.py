"""Physically motivated fault injection.

Fault labels are only used for ground truth/scoring.  Detectors see telemetry
values derived from the injected physics, never the label.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .energy import ThermalModel
from .rf import RFHardware


FAULT_TYPES = [
    "pa_gain_loss", "pa_saturation", "antenna_vswr", "phase_drift", "tile_dead",
    "noisy_receiver", "ptp_loss", "fronthaul_degraded", "fan_failure",
    "overtemperature", "supply_droop", "thermal_gradient", "supply_transient",
]


@dataclass
class FaultSpec:
    kind: str
    onset_slot: int = 20
    duration_slots: int = 40
    tile: int = 3
    magnitude: float = 8.0
    seed: int = 0


@dataclass
class FaultState:
    spec: FaultSpec
    active: bool = False
    applied_slots: int = 0
    ground_truth_tile: int = -1
    history: list[dict[str, Any]] = field(default_factory=list)


class FaultInjector:
    def __init__(self, hw: RFHardware, thermal: ThermalModel, rng: np.random.Generator) -> None:
        self.hw = hw
        self.thermal = thermal
        self.rng = rng
        self.states: list[FaultState] = []
        self._phase_accum = np.zeros(hw.fm.n_chains)

    def inject(self, spec: FaultSpec) -> FaultState:
        if spec.kind not in FAULT_TYPES:
            raise ValueError(f"unknown fault {spec.kind}")
        st = FaultState(spec=spec, ground_truth_tile=spec.tile)
        self.states.append(st)
        return st

    def seed_all(self, kinds: list[str], **kwargs: Any) -> list[FaultState]:
        return [self.inject(FaultSpec(kind=k, **kwargs)) for k in kinds]

    def step(self, slot: int, dt_s: float) -> None:
        for st in self.states:
            s = st.spec
            if slot < s.onset_slot or slot >= s.onset_slot + s.duration_slots:
                if st.active:
                    self._recover(st)
                continue
            if not st.active:
                self._onset(st)
            st.applied_slots += 1
            self._evolve(st, dt_s)
            st.history.append({"slot": slot, "kind": s.kind, "tile": s.tile})

    def _chains(self, tile: int) -> np.ndarray:
        return np.flatnonzero(self.hw.fm.chain_tile == tile)

    def _onset(self, st: FaultState) -> None:
        st.active = True
        s = st.spec
        ch = self._chains(s.tile)
        if s.kind == "pa_gain_loss":
            self.hw.chain_gain_db[ch] -= s.magnitude
        elif s.kind == "pa_saturation":
            # drive-dependent compression approximated as gain loss at high drive
            self.hw.chain_gain_db[ch] -= min(s.magnitude, 6.0)
        elif s.kind == "antenna_vswr":
            vswr = 2.0 + s.magnitude / 4.0
            self.hw.chain_vswr[ch] = vswr
            gamma = (vswr - 1) / (vswr + 1)
            self.hw.chain_gain_db[ch] -= 10 * np.log10(max(1 - gamma ** 2, 1e-3))
        elif s.kind == "phase_drift":
            self._phase_accum[ch] = 0.0
        elif s.kind == "tile_dead":
            self.hw.chain_gain_db[ch] = -40.0
            self.hw.tile_enabled[s.tile] = False
        elif s.kind == "noisy_receiver":
            self.hw.chain_noise_fig_db[ch] += s.magnitude
        elif s.kind == "ptp_loss":
            self.hw.tile_ptp_offset_ns[s.tile] = max(200.0, s.magnitude * 50.0)
            self.hw.chain_phase_deg[ch] += self.rng.uniform(-180, 180, ch.size)
        elif s.kind == "fan_failure":
            self.thermal.fan_failure()
        elif s.kind == "overtemperature":
            self.thermal.temp_c[s.tile] = max(self.thermal.temp_c[s.tile], 82.0 + s.magnitude)
        elif s.kind == "supply_droop":
            self.hw.tile_supply_v[s.tile] = 48.0 - s.magnitude
            self.hw.chain_gain_db[ch] -= 0.5 * s.magnitude
        elif s.kind == "thermal_gradient":
            self.thermal.temp_c[s.tile] = max(self.thermal.temp_c[s.tile], 35.0 + s.magnitude)
        elif s.kind == "supply_transient":
            self.hw.tile_supply_v[s.tile] = 48.0 - s.magnitude
            self.hw.chain_gain_db[ch] -= 0.2 * s.magnitude
        elif s.kind == "fronthaul_degraded":
            pass  # handled by the fronthaul link model

    def _evolve(self, st: FaultState, dt_s: float) -> None:
        s = st.spec
        ch = self._chains(s.tile)
        if s.kind == "phase_drift":
            self._phase_accum[ch] += self.rng.normal(0.0, s.magnitude, ch.size)
            self.hw.chain_phase_deg[ch] = self._phase_accum[ch]
        elif s.kind == "pa_saturation":
            self.hw.chain_gain_db[ch] -= 0.05 * dt_s * 1e3

    def _recover(self, st: FaultState) -> None:
        st.active = False
        s = st.spec
        ch = self._chains(s.tile)
        self.hw.chain_gain_db[ch] = 0.0
        self.hw.chain_phase_deg[ch] = 0.0
        self.hw.chain_vswr[ch] = 1.2
        self.hw.chain_noise_fig_db[ch] = 0.0
        self.hw.tile_ptp_offset_ns[s.tile] = 0.0
        self.hw.tile_supply_v[s.tile] = 48.0
        self.hw.tile_enabled[s.tile] = True
        self.thermal.reset_fan()
