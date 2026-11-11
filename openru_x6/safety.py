"""Independent safety supervisor.

This module has no dependency on the xApp/controller decision path.  It can veto
any command and can always execute an emergency shutdown, even while the control
service is degraded.  It is intentionally small and auditable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .config import EnergyConfig, SecurityConfig
from .rf import RFHardware


@dataclass
class SafetyLimits:
    max_tx_power_dbm: float = 46.0
    min_active_chains: int = 8
    max_isolated_tiles: int = 4
    max_tile_isolation_if_critical: int = 2
    max_temp_c: float = 90.0


class SafetySupervisor:
    def __init__(self, cfg: SecurityConfig, energy: EnergyConfig,
                 limits: SafetyLimits | None = None) -> None:
        self.cfg = cfg
        self.energy = energy
        self.limits = limits or SafetyLimits()
        self.emergency_latched = False
        self.veto_log: list[dict[str, Any]] = []
        self.emergency_actions = 0
        self.bypass_attempts = 0

    def veto(self, resource: str, action: str, params: dict[str, Any],
             ctx: dict[str, Any]) -> tuple[bool, str]:
        """Return (allowed, reason)."""
        reason = ""
        allowed = True
        sole = bool(ctx.get("sole_coverage", True))
        load = float(ctx.get("load_fraction", 0.0))
        temp = float(ctx.get("max_temp_c", 25.0))
        if self.emergency_latched and action != "emergency_shutdown":
            allowed, reason = False, "emergency_latched"
            self.bypass_attempts += 1
        elif resource == "energy_state":
            target = params.get("state", "")
            if target == "SLEEP_0" and (sole or not self.energy.allow_sleep_only_cell):
                allowed, reason = False, "sleep_forbidden_sole_coverage"
            elif target not in self.energy.states:
                allowed, reason = False, "unknown_energy_state"
            elif load > 0.01 and target == "SLEEP_0":
                allowed, reason = False, "sleep_with_traffic"
        elif resource == "rf_chain_mask":
            mask = params.get("chain_mask")
            if mask is not None:
                n = int(np.sum(np.asarray(mask, dtype=bool)))
                if n < self.limits.min_active_chains and sole:
                    allowed, reason = False, "coverage_requires_min_chains"
                if self.energy.allow_sleep_only_cell is False and n == 0:
                    allowed, reason = False, "zero_chains_forbidden"
        elif resource == "tile_isolation":
            if sole and int(ctx.get("active_chains_after", 999)) < self.limits.min_active_chains:
                allowed, reason = False, "coverage_requires_min_chains"
            if int(ctx.get("isolated_tiles_after", 0)) > self.limits.max_isolated_tiles:
                allowed, reason = False, "too_many_isolated_tiles"
        elif resource == "tx_power":
            p = float(params.get("power_dbm", 0.0))
            if p > self.limits.max_tx_power_dbm:
                allowed, reason = False, "tx_power_above_safety_limit"
            if p < -20:
                allowed, reason = False, "tx_power_out_of_range"
        elif resource == "emergency":
            allowed, reason = True, ""
        if temp >= self.limits.max_temp_c and resource in ("tx_power", "energy_state"):
            if resource == "tx_power":
                allowed, reason = False, "overtemperature_power_increase"
        if not allowed:
            self.veto_log.append({"resource": resource, "action": action, "reason": reason})
        return allowed, reason

    def emergency_shutdown(self, hw: RFHardware) -> dict[str, Any]:
        """Independent hard shutdown path: zero every chain immediately."""
        hw.set_chain_mask(np.zeros(hw.fm.n_chains, dtype=bool))
        hw.tile_enabled[:] = False
        self.emergency_latched = True
        self.emergency_actions += 1
        rb = hw.telemetry()
        return {"emergency": True, "active_chains": rb["active_chains"], "latched": True,
                "readback_state": rb["state"]}

    def clear_emergency(self) -> None:
        self.emergency_latched = False

    def check_temperature(self, temp_c: float) -> dict[str, Any]:
        if temp_c >= self.limits.max_temp_c:
            return {"action": "throttle", "reason": "overtemperature", "temp_c": temp_c}
        return {"action": "none", "temp_c": temp_c}
