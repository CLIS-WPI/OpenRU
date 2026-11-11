"""E04: fault injection, diagnosis, isolation and recovery."""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from ..config import config_digest
from ..diagnostics import StatisticalDetector, ThresholdDetector
from ..faults import FaultSpec
from .common import (make_context, make_result, params_for, record, run_engine,
                     seeds_for)


MAGNITUDES = {
    "pa_gain_loss": 8.0, "pa_saturation": 8.0, "antenna_vswr": 8.0,
    "phase_drift": 8.0, "tile_dead": 0.0, "noisy_receiver": 6.0,
    "ptp_loss": 3.0, "fan_failure": 0.0, "overtemperature": 5.0,
    "supply_droop": 8.0, "fronthaul_degraded": 0.0,
}


def _specs(kind: str, onset: int, duration: int, tile: int) -> list[FaultSpec]:
    if kind == "combo_pa_tile":
        return [FaultSpec("pa_gain_loss", onset, duration, tile, 8.0),
                FaultSpec("tile_dead", onset, duration, (tile + 1) % 16, 0.0)]
    return [FaultSpec(kind, onset, duration, tile, MAGNITUDES.get(kind, 6.0))]


def run(radio, energy, security, suite, out_dir: Path, store) -> object:
    t0 = time.time()
    p = params_for("E04", suite)
    seeds = seeds_for(suite, "E04")
    cal_seeds = [int(x) for x in p.get("seeds_cal", [900, 901])]
    faults = list(p.get("faults", ["pa_gain_loss", "tile_dead", "phase_drift"]))
    policies = list(p.get("policies", ["none", "threshold", "proposed"]))
    n_slots = int(p.get("slots", 40))
    n_users = int(p.get("users", 24))
    onset = int(p.get("onset", 12))
    duration = int(p.get("duration", 20))
    tile = int(p.get("tile", 3))
    digest = config_digest(radio, energy, security, suite)
    checks: dict[str, bool] = {}
    metrics: dict[str, object] = {}
    all_finite = True

    cal_samples: list[dict] = []
    for cseed in cal_seeds:
        ctx = make_context(radio, seed=cseed, n_users=n_users, n_slots=30,
                           channel_update_slots=15, saturate=True)
        r = run_engine(radio, energy, security, ctx, scheduler_policy="pf",
                       energy_kind="static", collect_telemetry=True)
        cal_samples.extend(r.telemetry)
    detector = StatisticalDetector(z_threshold=6.0)
    detector.fit(cal_samples, cal_seeds[0])
    detector.calibration_seeds = list(cal_seeds)
    metrics["calibration_samples"] = detector.calibration_samples
    checks["detector_calibrated"] = bool(detector.calibrated and detector.calibration_samples > 0)

    detections: list[int] = []
    localizations: list[int] = []
    latencies: list[float] = []
    recoveries: list[float] = []
    false_alarm_runs = 0
    healthy_runs = 0
    recovery_attempted = 0
    recovery_authorized = 0
    recovery_vetoed = 0
    recovery_unrouted = 0
    recovery_rolled_back = 0
    recovery_failed = 0
    by_fault: dict[str, dict[str, list[float]]] = {}

    for seed in seeds:
        ctx = make_context(radio, seed=seed, n_users=n_users, n_slots=n_slots,
                           channel_update_slots=max(10, n_slots // 3), saturate=True)
        for kind in faults:
            specs = _specs(kind, onset, duration, tile)
            for pol in policies:
                kwargs = dict(scheduler_policy="pf", energy_kind="static", faults=specs)
                if pol == "none":
                    kwargs.update(healing=False)
                elif pol == "threshold":
                    kwargs.update(healing=True, threshold_detector=ThresholdDetector())
                else:
                    kwargs.update(healing=True, healing_detector=detector)
                r = run_engine(radio, energy, security, ctx, **kwargs)
                if pol in ("threshold", "proposed") and r.healing:
                    n_att = int(r.healing.get("actions_attempted", 0))
                    n_auth = int(r.healing.get("actions_authorized", 0))
                    n_veto = int(r.healing.get("actions_vetoed", 0))
                    n_unr = int(r.healing.get("unrouted_actions", 0))
                    by_state = r.healing.get("control_by_state", {})
                    recovery_attempted += n_att
                    recovery_authorized += n_auth
                    recovery_vetoed += n_veto
                    recovery_unrouted += n_unr
                    recovery_rolled_back += int(by_state.get("ROLLED_BACK", 0))
                    recovery_failed += int(by_state.get("FAILED", 0))
                    store.add("E04", f"fault_{kind}", seed, pol,
                              "recovery_actions_authorized", float(n_auth), "", "SIMULATED", digest)
                    store.add("E04", f"fault_{kind}", seed, pol,
                              "recovery_actions_unrouted", float(n_unr), "", "SIMULATED", digest)
                    store.add("E04", f"fault_{kind}", seed, pol,
                              "recovery_actions_attempted", float(n_att), "", "SIMULATED", digest)
                record(r, "E04", f"fault_{kind}", seed, pol, store, digest)
                vals = [r.summary["sum_goodput_mbps"], r.summary["mean_sinr_db"],
                        r.summary["energy_j"]]
                all_finite &= all(np.isfinite(v) for v in vals)
                if pol == "proposed":
                    det = bool(r.healing.get("detected"))
                    detections.append(int(det))
                    store.add("E04", f"fault_{kind}", seed, pol, "detected", float(det),
                              "", "SIMULATED", digest)
                    stats = by_fault.setdefault(kind, {"detected": [], "localized": []})
                    stats["detected"].append(float(det))
                    if det:
                        lat = r.healing.get("detection_latency_slots")
                        if lat is not None:
                            latencies.append(float(lat))
                            store.add("E04", f"fault_{kind}", seed, pol, "detection_latency_slots",
                                      float(lat), "slots", "SIMULATED", digest)
                        loc = int(r.healing.get("localized_tile", -1))
                        if kind.startswith("combo"):
                            good = loc in (tile, (tile + 1) % 16)
                        elif kind == "fan_failure":
                            good = loc >= 0
                        else:
                            good = loc == tile
                        localizations.append(int(good))
                        by_fault[kind]["localized"].append(float(good))
                        store.add("E04", f"fault_{kind}", seed, pol, "localized_correctly",
                                  float(good), "", "SIMULATED", digest)
                        rec_lat = r.healing.get("recovery_latency_slots")
                        if r.healing.get("isolation_slot") is not None:
                            store.add("E04", f"fault_{kind}", seed, pol, "isolation_latency_slots",
                                      float(rec_lat if rec_lat is not None else 0), "slots",
                                      "SIMULATED", digest)
                            recoveries.append(float(rec_lat if rec_lat is not None else 0))
        # healthy run with proposed detector for false alarms
        if "proposed" in policies:
            hr = run_engine(radio, energy, security, ctx, scheduler_policy="pf",
                            energy_kind="static", healing=True, healing_detector=detector)
            healthy_runs += 1
            fa = int(bool(hr.healing.get("detected")))
            false_alarm_runs += fa
            store.add("E04", "healthy_false_alarm", seed, "proposed", "false_alarm", float(fa),
                      "", "SIMULATED", digest)

    checks["all_metrics_finite"] = bool(all_finite)
    checks["faults_injected"] = len(detections) > 0
    if detections:
        recall = float(np.mean(detections))
        checks["fault_recall_ge_80pct"] = recall >= 0.8
        metrics["fault_recall"] = recall
    if localizations:
        checks["localization_ge_70pct"] = float(np.mean(localizations)) >= 0.7
        metrics["localization_accuracy"] = float(np.mean(localizations))
    if latencies:
        checks["mean_detection_latency_le_10_slots"] = float(np.mean(latencies)) <= 10
        metrics["mean_detection_latency_slots"] = float(np.mean(latencies))
    if recoveries:
        metrics["mean_isolation_latency_slots"] = float(np.mean(recoveries))
    metrics["recall_by_fault"] = {
        k: float(np.mean(v["detected"])) for k, v in by_fault.items() if v["detected"]}
    metrics["localization_by_fault"] = {
        k: float(np.mean(v["localized"])) for k, v in by_fault.items() if v["localized"]}
    checks["false_alarm_rate_low"] = (false_alarm_runs / max(healthy_runs, 1)) <= 0.2
    metrics["false_alarm_rate_per_run"] = false_alarm_runs / max(healthy_runs, 1)
    metrics["healthy_runs"] = healthy_runs
    metrics["recovery_actions_attempted"] = recovery_attempted
    metrics["recovery_actions_verified"] = recovery_authorized
    metrics["recovery_actions_authorized"] = recovery_authorized
    metrics["recovery_actions_vetoed"] = recovery_vetoed
    metrics["recovery_actions_unrouted"] = recovery_unrouted
    metrics["recovery_actions_rolled_back"] = recovery_rolled_back
    metrics["recovery_actions_failed"] = recovery_failed
    checks["recovery_actions_use_control_plane"] = recovery_unrouted == 0
    checks["recovery_actions_authorized"] = recovery_authorized > 0

    return make_result("E04", "Hardware faults, diagnosis and recovery", t0, checks, metrics)
