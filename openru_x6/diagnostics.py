"""Telemetry-based fault diagnosis and safe self-healing planning."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .rf import RFHardware


FEATURES = ["gain_db_mean", "gain_db_std", "phase_error_deg_rms", "vswr_max",
            "temp_c", "supply_v", "ptp_offset_ns", "noise_fig_db_max", "fan_fail"]


def feature_matrix(telemetry: dict[str, Any]) -> tuple[np.ndarray, list[int]]:
    tiles = [t["tile"] for t in telemetry["per_tile"]]
    x = np.array([[t[f] for f in FEATURES] for t in telemetry["per_tile"]], dtype=float)
    return x, tiles


@dataclass
class Alarm:
    tile: int
    feature: str
    value: float
    score: float
    method: str
    suspected_fault: str


@dataclass
class Diagnosis:
    detected: bool
    tile: int
    suspected_fault: str
    confidence: float
    alarms: list[Alarm] = field(default_factory=list)
    score: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {"detected": self.detected, "tile": self.tile, "suspected_fault": self.suspected_fault,
                "confidence": self.confidence, "score": self.score,
                "alarms": [a.__dict__ for a in self.alarms]}


class ThresholdDetector:
    """Rule baseline with fixed engineering thresholds."""
    thresholds = {
        "gain_db_mean": ("lt", -2.0, "pa_gain_loss"),
        "gain_db_std": ("gt", 2.0, "calibration_fault"),
        "phase_error_deg_rms": ("gt", 10.0, "phase_drift"),
        "vswr_max": ("gt", 2.0, "antenna_vswr"),
        "temp_c": ("gt", 80.0, "overtemperature"),
        "supply_v": ("lt", 45.0, "supply_droop"),
        "ptp_offset_ns": ("gt", 100.0, "ptp_loss"),
        "noise_fig_db_max": ("gt", 3.0, "noisy_receiver"),
        "fan_fail": ("gt", 0.5, "fan_failure"),
    }

    def detect(self, telemetry: dict[str, Any]) -> Diagnosis:
        x, tiles = feature_matrix(telemetry)
        alarms: list[Alarm] = []
        for i, tile in enumerate(tiles):
            for j, f in enumerate(FEATURES):
                op, thr, fault = self.thresholds[f]
                v = x[i, j]
                if (op == "gt" and v > thr) or (op == "lt" and v < thr):
                    score = abs(v - thr) / max(abs(thr), 1e-6)
                    alarms.append(Alarm(tile, f, float(v), float(score), "threshold", fault))
        best_tile = max(set(a.tile for a in alarms),
                        key=lambda t: sum(a.score for a in alarms if a.tile == t), default=-1)
        if not alarms:
            return Diagnosis(False, -1, "healthy", 0.0, [], 0.0)
        fault = max((a for a in alarms if a.tile == best_tile), key=lambda a: a.score).suspected_fault
        return Diagnosis(True, best_tile, fault, min(1.0, sum(a.score for a in alarms) / 5.0),
                         alarms, max(a.score for a in alarms))


class StatisticalDetector:
    """Mahalanobis / z-score detector calibrated on independent healthy seeds.

    The calibration traces are never used for evaluation.  If calibration data
    is unavailable this detector is reported as uncalibrated rather than
    silently falling back to the threshold rules.
    """

    def __init__(self, z_threshold: float = 4.0) -> None:
        self.z_threshold = z_threshold
        self.mu: np.ndarray | None = None
        self.sigma: np.ndarray | None = None
        self.calibration_seeds: list[int] = []
        self.calibration_samples = 0
        self.calibrated = False

    def fit(self, telemetry_samples: list[dict[str, Any]], seed: int) -> None:
        xs = [feature_matrix(t)[0] for t in telemetry_samples]
        if not xs:
            raise ValueError("no calibration telemetry")
        stacked = np.concatenate(xs, axis=0)
        self.mu = stacked.mean(axis=0)
        # Sensor resolution/quantisation floors prevent a near-zero sample
        # variance from turning benign LSB changes into enormous z-scores.
        floors = np.array([0.05, 0.03, 0.12, 0.005, 0.05, 0.01, 0.2, 0.05, 1e-6])
        self.sigma = np.maximum(stacked.std(axis=0), floors)
        self.calibration_samples = int(stacked.shape[0])
        self.calibration_seeds.append(seed)
        self.calibrated = True

    def detect(self, telemetry: dict[str, Any]) -> Diagnosis:
        if not self.calibrated:
            raise RuntimeError("statistical detector not calibrated")
        x, tiles = feature_matrix(telemetry)
        z = np.abs((x - self.mu) / self.sigma)
        alarms: list[Alarm] = []
        for i, tile in enumerate(tiles):
            for j, f in enumerate(FEATURES):
                if z[i, j] > self.z_threshold:
                    # interpret the direction of the anomaly for recovery planning
                    direction = "high" if x[i, j] > self.mu[j] else "low"
                    fault = {
                        "gain_db_mean": "pa_gain_loss" if direction == "low" else "calibration_fault",
                        "gain_db_std": "calibration_fault",
                        "phase_error_deg_rms": "phase_drift",
                        "vswr_max": "antenna_vswr",
                        "temp_c": "overtemperature",
                        "supply_v": "supply_droop",
                        "ptp_offset_ns": "ptp_loss",
                        "noise_fig_db_max": "noisy_receiver",
                        "fan_fail": "fan_failure",
                    }[f]
                    alarms.append(Alarm(tile, f, float(x[i, j]), float(z[i, j]), "zscore", fault))
        if not alarms:
            return Diagnosis(False, -1, "healthy", 0.0, [], 0.0)
        best_tile = max(set(a.tile for a in alarms),
                        key=lambda t: sum(a.score for a in alarms if a.tile == t))
        fault = max((a for a in alarms if a.tile == best_tile), key=lambda a: a.score).suspected_fault
        score = max(a.score for a in alarms)
        return Diagnosis(True, best_tile, fault, min(1.0, score / (self.z_threshold * 2)), alarms, score)


@dataclass
class RecoveryAction:
    action: str
    tile: int = -1
    params: dict[str, Any] = field(default_factory=dict)
    safety_critical: bool = False


class RecoveryPlanner:
    def plan(self, diag: Diagnosis, telemetry: dict[str, Any], ctx: dict[str, Any]) -> list[RecoveryAction]:
        if not diag.detected:
            return []
        tile = diag.tile
        fault = diag.suspected_fault
        max_temp = max(t["temp_c"] for t in telemetry["per_tile"])
        actions: list[RecoveryAction] = []
        if max_temp >= 90:
            actions.append(RecoveryAction("emergency_shutdown", safety_critical=True))
            return actions
        if max_temp >= 80:
            actions.append(RecoveryAction("reduce_chains", params={"state": "COVERAGE_8"}))
        if fault in ("pa_gain_loss", "antenna_vswr", "tile_dead", "supply_droop"):
            actions.append(RecoveryAction("isolate_tile", tile=tile))
            actions.append(RecoveryAction("reduce_chains", params={"state": "BALANCED_32"}))
        elif fault in ("phase_drift", "calibration_fault"):
            actions.append(RecoveryAction("recalibrate", tile=tile, params={"residual_deg": 2.0}))
        elif fault == "ptp_loss":
            actions.append(RecoveryAction("resync_ptp", tile=tile))
            actions.append(RecoveryAction("recalibrate", tile=tile, params={"residual_deg": 3.0}))
        elif fault == "noisy_receiver":
            actions.append(RecoveryAction("isolate_tile", tile=tile))
        elif fault == "overtemperature":
            actions.append(RecoveryAction("reduce_power", params={"power_dbm": 40.0}))
        elif fault == "fan_failure":
            actions.append(RecoveryAction("reduce_chains", params={"state": "COVERAGE_8"}))
        return actions


class SelfHealingController:
    def __init__(self, hw: RFHardware, detector: Any, planner: RecoveryPlanner | None = None,
                 isolated_limit: int = 4) -> None:
        self.hw = hw
        self.detector = detector
        self.planner = planner or RecoveryPlanner()
        self.detection_slot: int | None = None
        self.isolation_slot: int | None = None
        self.recovery_slot: int | None = None
        self.localized_tile: int = -1
        self.diagnosis: Diagnosis | None = None
        self.actions: list[RecoveryAction] = []
        self.isolated: set[int] = set()
        self.isolated_limit = isolated_limit
        self.false_alarms = 0
        self.safe_blocked = 0
        self.hardware_shutdown = False
        self.power_limit_dbm: float | None = None
        self.actions_attempted = 0
        self.actions_authorized = 0
        self.actions_vetoed = 0
        self.unrouted_actions = 0
        self._executed_actions: set[tuple[Any, ...]] = set()

    def step(self, slot: int, telemetry: dict[str, Any], ctx: dict[str, Any] | None = None,
             executor: Any | None = None) -> Diagnosis:
        """Diagnose and propose recovery.

        Normal recovery is executed only through ``executor`` (the authorized
        control path).  Only the independent emergency mute is allowed to touch
        hardware directly here.
        """
        ctx = ctx or {}
        diag = self.detector.detect(telemetry)
        self.diagnosis = diag
        if diag.detected:
            if self.detection_slot is None:
                self.detection_slot = slot
                self.localized_tile = diag.tile
            plan = self.planner.plan(diag, telemetry, ctx)
            self.actions = plan
            for act in plan:
                if act.action == "emergency_shutdown":
                    # Hard protection must mute hardware itself, not merely
                    # increment a counter and stop planning.
                    self.hw.set_chain_mask(np.zeros(self.hw.fm.n_chains, dtype=bool))
                    self.hw.tile_enabled[:] = False
                    self.hw.protection_latched = True
                    self.hardware_shutdown = True
                    self.safe_blocked += 1
                    break
                if act.action == "isolate_tile" and act.tile >= 0:
                    if act.tile in self.isolated:
                        continue
                    if executor is None:
                        self.unrouted_actions += 1
                        continue
                    self.actions_attempted += 1
                    if bool(executor(act, slot)):
                        self.actions_authorized += 1
                        self.isolated.add(act.tile)
                        if self.isolation_slot is None:
                            self.isolation_slot = slot
                    else:
                        self.actions_vetoed += 1
                    continue
                key = (act.action, act.tile, tuple(sorted(act.params.items())))
                if key in self._executed_actions:
                    continue
                if executor is None:
                    self.unrouted_actions += 1
                    continue
                self.actions_attempted += 1
                if bool(executor(act, slot)):
                    self.actions_authorized += 1
                    self._executed_actions.add(key)
                    if act.action == "reduce_power":
                        target_dbm = float(act.params.get("power_dbm", 40.0))
                        self.power_limit_dbm = target_dbm
                else:
                    self.actions_vetoed += 1
            if self.isolation_slot is not None and self.recovery_slot is None:
                self.recovery_slot = slot
        else:
            if self.detection_slot is None and slot > 5:
                pass
        return diag
