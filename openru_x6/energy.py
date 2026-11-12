"""RF power states, energy accounting and QoS-aware energy policies.

Thermal behaviour is a lumped RC abstraction, not CFD.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .config import EnergyConfig

STATE_BY_CHAINS = {64: "FULL_64", 32: "BALANCED_32", 16: "ECO_16", 8: "COVERAGE_8", 0: "SLEEP_0"}
ORDER = ["SLEEP_0", "COVERAGE_8", "ECO_16", "BALANCED_32", "FULL_64"]


def state_chains(cfg: EnergyConfig, state: str) -> int:
    return int(cfg.states[state])


def power_breakdown(cfg: EnergyConfig, state: str, tx_power_w: float = 0.0,
                    fan_ok: bool = True, active_chains: int | None = None,
                    active_tiles: int | None = None,
                    transition: str | None = None) -> dict[str, float]:
    """Per-domain power for the currently enabled hardware.

    ``active_chains``/``active_tiles`` let the caller account for fault isolation
    and pending wake instead of charging power for abstract state names.
    ``transition="WAKE"`` models clock/bias/calibration power with zero PA and no
    service output until the wake sequence completes.
    """
    n = state_chains(cfg, state)
    n_elec = n if active_chains is None else max(0, min(n, int(active_chains)))
    n_tiles = (int(active_tiles) if active_tiles is not None
               else (cfg.states.get("FULL_64", 64) // 4 if n_elec else 0))
    out: dict[str, float] = {}
    if n == 0:
        out["always_on"] = cfg.always_on_w * 0.35
        out["dsp_fpga"] = 0.0
        out["rf_chains"] = 0.0
        out["feed_branches"] = 0.0
        out["pa_dc"] = 0.0
        out["standby"] = cfg.sleep_standby_w
        out["tile_control"] = 0.0
        dissip = sum(out.values())
        out["cooling"] = 0.0
        out["total_w"] = dissip
        out["dissipation_w"] = dissip
        return out
    dsp_scale = 0.55 + 0.45 * n_elec / 64.0
    out["always_on"] = cfg.always_on_w
    out["dsp_fpga"] = cfg.dsp_fpga_w * dsp_scale
    out["rf_chains"] = n_elec * cfg.per_chain_electronics_w
    out["feed_branches"] = n_elec * 4 * cfg.per_feed_branch_w
    out["tile_control"] = (cfg.per_tile_control_w * n_tiles) if cfg.per_tile_control_w else 0.0
    out["pa_dc"] = (tx_power_w / cfg.pa_efficiency) if cfg.tx_power_included_in_pa else 0.0
    if transition == "WAKE":
        # Clock/PLL/bias/calibration are powered, but the PA is muted and no
        # user-plane service is emitted before READY.
        out["rf_chains"] *= 0.25
        out["feed_branches"] = 0.0
        out["pa_dc"] = 0.0
        out["standby"] = cfg.sleep_standby_w
    dissip = (out["always_on"] + out["dsp_fpga"] + out["rf_chains"] + out["feed_branches"] +
              out["tile_control"] + out.get("standby", 0.0) + out["pa_dc"])
    out["cooling"] = cfg.cooling_fraction_of_dissipation * dissip * (1.0 if fan_ok else 1.4)
    out["total_w"] = dissip + out["cooling"]
    out["dissipation_w"] = dissip
    return out


class ThermalModel:
    def __init__(self, cfg: EnergyConfig) -> None:
        self.cfg = cfg
        self.temp_c = np.full(16, cfg.thermal.ambient_c + 3.0)
        self.fan_ok = True
        self.throttled = False
        self.tripped = False

    def update(self, total_power_w: float, dt_s: float, hot_tile: int | None = None) -> np.ndarray:
        t = self.cfg.thermal
        r = t.thermal_resistance_k_per_w * (1.0 if self.fan_ok else t.fan_failure_multiplier)
        heat = total_power_w / 16.0
        dT = (heat - (self.temp_c - t.ambient_c) / r) / (t.thermal_capacity_j_per_k / 16.0)
        self.temp_c = self.temp_c + dT * dt_s
        self.temp_c = np.clip(self.temp_c, t.ambient_c - 5, 150.0)
        if hot_tile is not None:
            self.temp_c[hot_tile] += t.hot_spot_delta_c * dt_s
        self.throttled = bool(self.temp_c.max() >= t.throttle_c)
        self.tripped = bool(self.temp_c.max() >= t.trip_c)
        return self.temp_c

    def fan_failure(self) -> None:
        self.fan_ok = False

    def reset_fan(self) -> None:
        self.fan_ok = True


@dataclass
class EnergyOutcome:
    energy_j: float
    mean_power_w: float
    peak_power_w: float
    state_counts: dict[str, int]
    transitions: int
    waking_slots: int
    service_interruption_slots: int
    qos_violation_fraction: float
    oscillation_count: int
    sleep_forbidden: bool
    illegal_sleep_attempts: int

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


class EnergyManager:
    """State machine enforcing dwell, hysteresis, wake-up and coverage rules."""

    def __init__(self, cfg: EnergyConfig, sole_coverage_cell: bool = True) -> None:
        self.cfg = cfg
        self.sole_coverage = sole_coverage_cell
        self.state = "FULL_64"
        self.target_state = "FULL_64"
        self.time_in_state = 0.0
        self.wake_remaining = 0.0
        self.pending_wake = False
        self.shutdown_remaining = 0.0
        self.hw_phase = "READY"
        self.transition_energy_j = 0.0
        self.transitions = 0
        self.waking_slots = 0
        self.illegal_sleep_attempts = 0
        self.energy_j = 0.0
        self.peak_power = 0.0
        self.state_counts: dict[str, int] = {}
        self.last_switch_time = -1e9
        self.switch_times: list[float] = []
        self.oscillations = 0
        self._last_dir = 0

    def _legal(self, state: str, load_fraction: float) -> bool:
        if state == "SLEEP_0":
            if self.sole_coverage or not self.cfg.allow_sleep_only_cell:
                self.illegal_sleep_attempts += 1
                return False
            if load_fraction > 0.01:
                self.illegal_sleep_attempts += 1
                return False
        return True

    def request(self, target: str, now_s: float, load_fraction: float) -> bool:
        if not self._legal(target, load_fraction):
            return False
        if target == self.state:
            self.target_state = target
            return True
        if self.cfg.max_switches_per_second > 0:
            recent = [t for t in self.switch_times if now_s - t < 1.0]
            if len(recent) >= self.cfg.max_switches_per_second:
                return False
        down = state_chains(self.cfg, target) < state_chains(self.cfg, self.state)
        dwell = self.cfg.min_on_dwell_s if down else self.cfg.min_off_dwell_s
        if self.time_in_state < dwell:
            return False
        self.target_state = target
        if down and state_chains(self.cfg, target) < state_chains(self.cfg, self.state):
            if self._last_dir == -1:
                self.oscillations += 1
            self._last_dir = -1
        elif not down:
            if self._last_dir == 1:
                self.oscillations += 1
            self._last_dir = 1
        prev_chains = state_chains(self.cfg, self.state)
        self.state = target
        self.time_in_state = 0.0
        self.transitions += 1
        self.last_switch_time = now_s
        self.switch_times.append(now_s)
        if target != "SLEEP_0" and down is False:
            self.wake_remaining = self.cfg.wakeup_delay_s
            self.pending_wake = True
            self.hw_phase = "CLOCK_LOCKING"
            self._wake_from_chains = prev_chains
        elif target == "SLEEP_0" and down:
            self.shutdown_remaining = self.cfg.shutdown_delay_s
            self.hw_phase = "SHUTTING_DOWN"
        else:
            self.shutdown_remaining = 0.0
            self.hw_phase = "READY"
        return True

    def effective_chains(self) -> int:
        # No RF service is emitted until CLOCK_LOCKING -> BIAS/PLL -> READY
        # completes.  Returning 8 chains during wake was a safety/validity bug.
        if self.pending_wake and self.wake_remaining > 0:
            return 0
        if self.shutdown_remaining > 0:
            return 0
        return state_chains(self.cfg, self.state)

    def service_ready(self) -> bool:
        return not self.pending_wake and self.shutdown_remaining <= 0

    def step(self, dt_s: float, tx_power_w: float, load_fraction: float,
             fan_ok: bool = True, active_chains: int | None = None,
             active_tiles: int | None = None) -> dict[str, float]:
        self.time_in_state += dt_s
        transition_energy = 0.0
        if self.pending_wake:
            self.wake_remaining -= dt_s
            self.waking_slots += 1
            transition_energy = (self.cfg.wakeup_energy_j *
                                 min(dt_s, max(self.wake_remaining + dt_s, 0.0)) /
                                 max(self.cfg.wakeup_delay_s, dt_s))
            self.hw_phase = "BIAS_PLL" if self.wake_remaining < self.cfg.wakeup_delay_s * 0.5 else "CLOCK_LOCKING"
            if self.wake_remaining <= 0:
                self.pending_wake = False
                self.wake_remaining = 0.0
                self.hw_phase = "READY"
        if self.shutdown_remaining > 0:
            self.shutdown_remaining = max(0.0, self.shutdown_remaining - dt_s)
            transition_energy += self.cfg.sleep_standby_w * dt_s
            if self.shutdown_remaining <= 0:
                self.hw_phase = "READY" if self.state != "SLEEP_0" else "OFF"
        pb = power_breakdown(self.cfg, self.state, tx_power_w, fan_ok,
                             active_chains=active_chains,
                             active_tiles=active_tiles,
                             transition="WAKE" if self.pending_wake else None)
        self.transition_energy_j += transition_energy
        self.energy_j += pb["total_w"] * dt_s + transition_energy
        pb["transition_energy_j"] = transition_energy
        pb["hw_phase"] = 0.0 if self.hw_phase == "READY" else 1.0
        self.peak_power = max(self.peak_power, pb["total_w"])
        self.state_counts[self.state] = self.state_counts.get(self.state, 0) + 1
        return pb


def required_state_for_load(load_fraction: float, min_chains: int = 8,
                            max_chains: int = 64) -> str:
    need = max(min_chains, int(np.ceil(load_fraction * max_chains)))
    for name in ORDER:
        if state_chains_from_name(name) >= need:
            return name
    return "FULL_64"


def state_chains_from_name(name: str) -> int:
    return int(name.split("_")[-1])


class EnergyPolicy:
    def __init__(self, kind: str, cfg: EnergyConfig, sole_coverage: bool = True) -> None:
        self.kind = kind
        self.cfg = cfg
        self.mgr = EnergyManager(cfg, sole_coverage)
        self.load_ewma = 0.0
        self.forecast = 0.0
        self.history: list[float] = []

    def observe(self, load_fraction: float, queue_fraction: float) -> None:
        """Update causal load/queue observations and forecast; never sees future."""
        self.load_ewma = (1 - self.cfg.predictive_ewma_alpha) * self.load_ewma + \
            self.cfg.predictive_ewma_alpha * load_fraction
        self.history.append(float(load_fraction))
        keep = max(self.cfg.predictive_horizon_slots * 4, 8)
        self.history = self.history[-keep:]
        slope = 0.0
        if len(self.history) >= 3:
            x = np.arange(len(self.history), dtype=float)
            slope = float(np.polyfit(x, np.asarray(self.history), 1)[0])
        self.forecast = float(np.clip(self.load_ewma + self.cfg.predictive_horizon_slots * slope,
                                      0.0, 1.0))

    def target_for(self, load_fraction: float, queue_fraction: float,
                   thermal_throttle: bool = False,
                   constraints: dict[str, Any] | None = None) -> str:
        """Return the policy target without mutating the energy manager.

        ``constraints`` is used by the P1 closed-loop controller to sweep
        minimum-chain/QoS floors.  A target is not a claim that the resulting
        service meets the constraint; that is evaluated from the run metrics.
        """
        constraints = constraints or {}
        min_chains = int(constraints.get("coverage_requires_min_chains",
                                         self.cfg.coverage_requires_min_chains))
        if self.kind == "static":
            target = "FULL_64"
        elif (not self.mgr.sole_coverage and self.cfg.allow_sleep_only_cell
              and load_fraction < 0.01 and queue_fraction < 0.01):
            target = "SLEEP_0"
        elif self.kind in ("predictive", "constrained"):
            # Look-ahead uses only past queue observations and the configured
            # horizon; it is not an oracle and never sees future arrivals.
            pred = max(load_fraction, self.load_ewma, self.forecast)
            pred = max(pred, float(constraints.get("min_load_for_full", 0.0)))
            target = required_state_for_load(pred, max(8, min_chains))
        else:  # threshold with hysteresis
            current = self.mgr.state
            cur_ch = state_chains_from_name(current)
            need = load_fraction * 64
            h = self.cfg.hysteresis_fraction
            if need > cur_ch * (1 + h / 2):
                target = required_state_for_load(load_fraction, max(8, min_chains))
            elif need < cur_ch * (1 - h / 2):
                target = required_state_for_load(max(load_fraction, 0.0), max(8, min_chains))
            else:
                target = current
        if thermal_throttle:
            target = "COVERAGE_8" if target != "SLEEP_0" else target
        return target

    def update(self, load_fraction: float, queue_fraction: float, now_s: float,
               thermal_throttle: bool = False, dt_s: float = 5e-4,
               constraints: dict[str, Any] | None = None) -> None:
        self.observe(load_fraction, queue_fraction)
        target = self.target_for(load_fraction, queue_fraction, thermal_throttle, constraints)
        self.mgr.request(target, now_s, load_fraction)

    def step(self, dt_s: float, tx_power_w: float, load_fraction: float,
             fan_ok: bool = True, active_chains: int | None = None,
             active_tiles: int | None = None):
        return self.mgr.step(dt_s, tx_power_w, load_fraction, fan_ok,
                             active_chains=active_chains, active_tiles=active_tiles)
