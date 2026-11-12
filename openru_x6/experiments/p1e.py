"""P1-E: held-out fault and sensor-degradation diagnostic challenge."""
from __future__ import annotations

import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from ..config import config_digest
from ..diagnostics import StatisticalDetector
from ..faults import FaultSpec
from ..metrics import write_json
from ..sensors import SensorFaultInjector, SensorFaultSpec
from .common import make_context, make_result, params_for, run_engine
from .p1_common import write_csv


FAULT_TILES = {
    "pa_gain_loss": (3,), "phase_drift": (4,), "tile_dead": (6,),
    "noisy_receiver": (8,), "thermal_gradient": (9,), "supply_transient": (10,),
    "multi_tile": (3, 7),
}


def _specs(kind: str, onset: int, duration: int) -> list[FaultSpec]:
    tiles = FAULT_TILES.get(kind, (3,))
    if kind == "multi_tile":
        return [FaultSpec("pa_gain_loss", onset_slot=onset, duration_slots=duration,
                          tile=tiles[0], magnitude=10.0),
                FaultSpec("thermal_gradient", onset_slot=onset, duration_slots=duration,
                          tile=tiles[1], magnitude=12.0)]
    mag = {"pa_gain_loss": 10.0, "phase_drift": 18.0, "tile_dead": 8.0,
           "noisy_receiver": 6.0, "thermal_gradient": 12.0,
           "supply_transient": 4.0}.get(kind, 8.0)
    return [FaultSpec(kind, onset_slot=onset, duration_slots=duration,
                      tile=tiles[0], magnitude=mag)]


def _calibrate(radio, energy, security, p: dict, seeds: list[int]) -> tuple[StatisticalDetector, int]:
    samples: list[dict] = []
    users = int(p.get("users", 24))
    slots = int(p.get("slots", 40))
    for seed in seeds:
        ctx = make_context(radio, seed=seed, n_users=users, n_slots=min(30, slots),
                           channel_update_slots=10, saturate=True)
        r = run_engine(radio, energy, security, ctx, forced_chains=64,
                       scheduler_policy="pf", energy_kind="static", sole_coverage=True,
                       collect_telemetry=True)
        samples.extend(r.telemetry)
    det = StatisticalDetector()
    det.fit(samples, seeds[0])
    return det, len(samples)


def _run(radio, energy, security, p: dict, seed: int, kind: str | None,
         sensors: list[SensorFaultSpec], detector: StatisticalDetector, onset: int,
         duration: int):
    slots = int(p.get("slots", 40))
    users = int(p.get("users", 24))
    ctx = make_context(radio, seed=seed, n_users=users, n_slots=slots,
                       channel_update_slots=max(10, slots // 2), saturate=True)
    faults = _specs(kind, onset, duration) if kind else []
    injector = SensorFaultInjector(sensors)
    rng = np.random.default_rng(seed + 50_000)
    r = run_engine(radio, energy, security, ctx, forced_chains=64,
                   scheduler_policy="pf", energy_kind="static", sole_coverage=True,
                   faults=faults, healing=True, healing_detector=detector,
                   collect_telemetry=True,
                   telemetry_transform=(lambda tel, slot: injector.step(tel, slot, rng))
                   if sensors else None)
    return r


def _first_detection(trace: list[dict], onset: int, duration: int) -> dict | None:
    for t in trace:
        if onset <= t["slot"] < onset + duration and t["detected"]:
            return t
    return None


def run(radio, energy, security, suite, out_dir: Path, store) -> object:
    t0 = time.time()
    p = params_for("P1E", suite)
    digest = config_digest(radio, energy, security, suite)
    checks: dict[str, bool] = {}
    metrics: dict[str, object] = {}
    cal_seeds = [int(x) for x in p.get("cal_seeds", [9001, 9002])]
    val_seeds = [int(x) for x in p.get("validation_seeds", [9101])]
    eval_seeds = [int(x) for x in p.get("eval_seeds", [9201, 9202])]
    faults = [str(x) for x in p.get("faults", list(FAULT_TILES))]
    sensor_kinds = [str(x) for x in p.get("sensor_faults", ["missing", "frozen", "biased", "stale"])]
    onset, duration = 10, 14
    detector, n_cal = _calibrate(radio, energy, security, p, cal_seeds)
    write_json(out_dir / "p1e_calibration.json", {
        "calibration_seeds": cal_seeds, "validation_seeds": val_seeds,
        "eval_seeds": eval_seeds, "calibration_samples": n_cal,
        "validation_used_for_threshold_tuning": False,
        "note": "Calibration, validation and evaluation seed sets are disjoint. P1-E does not tune on evaluation seeds.",
    })

    rows: list[dict] = []
    baseline_pred: dict[str, Counter] = defaultdict(Counter)
    for seed in eval_seeds:
        for kind in faults:
            r = _run(radio, energy, security, p, seed, kind, [], detector, onset, duration)
            trace = r.healing_trace
            fd = _first_detection(trace, onset, duration)
            actual_tiles = FAULT_TILES.get(kind, (3,))
            pred = fd["suspected_fault"] if fd else "missed"
            tile = int(fd["tile"]) if fd else -1
            localized = bool(fd and tile in actual_tiles)
            baseline_pred[kind][pred] += 1
            rows.append({
                "case": "baseline", "seed": seed, "actual_fault": kind,
                "predicted_fault": pred, "detected": bool(fd),
                "detection_slot": int(fd["slot"]) if fd else None,
                "detection_delay_slots": (int(fd["slot"]) - onset) if fd else None,
                "predicted_tile": tile, "actual_tiles": "|".join(map(str, actual_tiles)),
                "localized": localized,
                "actions_attempted": r.healing.get("actions_attempted", 0),
                "actions_authorized": r.healing.get("actions_authorized", 0),
                "actions_vetoed": r.healing.get("actions_vetoed", 0),
                "service_interruption_slots": r.summary["service_interruption_slots"],
                "goodput_mbps": r.summary["sum_goodput_mbps"],
                "sensor_fault": "none",
                "false_alarm": False,
            })
            for sk in sensor_kinds:
                spec = SensorFaultSpec(sk, onset_slot=onset - 2, duration_slots=duration + 4,
                                       tile=actual_tiles[0], magnitude=6.0)
                rs = _run(radio, energy, security, p, seed, kind, [spec], detector, onset, duration)
                fds = _first_detection(rs.healing_trace, onset, duration)
                preds = fds["suspected_fault"] if fds else "missed"
                tiles = int(fds["tile"]) if fds else -1
                rows.append({
                    "case": "sensor_degradation", "seed": seed, "actual_fault": kind,
                    "predicted_fault": preds, "detected": bool(fds),
                    "detection_slot": int(fds["slot"]) if fds else None,
                    "detection_delay_slots": (int(fds["slot"]) - onset) if fds else None,
                    "predicted_tile": tiles, "actual_tiles": "|".join(map(str, actual_tiles)),
                    "localized": bool(fds and tiles in actual_tiles),
                    "actions_attempted": rs.healing.get("actions_attempted", 0),
                    "actions_authorized": rs.healing.get("actions_authorized", 0),
                    "actions_vetoed": rs.healing.get("actions_vetoed", 0),
                    "service_interruption_slots": rs.summary["service_interruption_slots"],
                    "goodput_mbps": rs.summary["sum_goodput_mbps"],
                    "sensor_fault": sk, "false_alarm": False,
                })
        # Healthy + sensor faults only: false-alarm accounting.
        for sk in sensor_kinds:
            spec = SensorFaultSpec(sk, onset_slot=8, duration_slots=10,
                                   tile=2, magnitude=5.0)
            rh = _run(radio, energy, security, p, seed, None, [spec], detector, onset, duration)
            any_det = any(t["detected"] for t in rh.healing_trace)
            rows.append({
                "case": "healthy_sensor", "seed": seed, "actual_fault": "healthy",
                "predicted_fault": ("false_alarm" if any_det else "healthy"),
                "detected": False, "detection_slot": None, "detection_delay_slots": None,
                "predicted_tile": -1, "actual_tiles": "", "localized": False,
                "actions_attempted": rh.healing.get("actions_attempted", 0),
                "actions_authorized": rh.healing.get("actions_authorized", 0),
                "actions_vetoed": rh.healing.get("actions_vetoed", 0),
                "service_interruption_slots": rh.summary["service_interruption_slots"],
                "goodput_mbps": rh.summary["sum_goodput_mbps"],
                "sensor_fault": sk, "false_alarm": bool(any_det),
            })

    write_csv(out_dir / "p1e_cases.csv", rows)
    confusion = []
    for actual, counter in sorted(baseline_pred.items()):
        for pred, n in sorted(counter.items()):
            confusion.append({"actual_fault": actual, "predicted_fault": pred, "count": n})
    write_csv(out_dir / "p1e_confusion.csv", confusion)

    phys = [r for r in rows if r["case"] == "baseline"]
    sens = [r for r in rows if r["case"] == "sensor_degradation"]
    healthy = [r for r in rows if r["case"] == "healthy_sensor"]
    recall = float(np.mean([1.0 if r["detected"] else 0.0 for r in phys])) if phys else float("nan")
    loc = float(np.mean([1.0 if r["localized"] else 0.0 for r in phys])) if phys else float("nan")
    false_alarm_slots = sum(1 for r in healthy if r["false_alarm"])
    hours = len(healthy) * float(p.get("slots", 40)) * radio.cell.slot_duration_s / 3600.0
    metrics.update({
        "physical_cases": len(phys), "sensor_cases": len(sens), "healthy_cases": len(healthy),
        "detection_recall": recall, "localization_accuracy": loc,
        "median_detection_delay_slots": float(np.median(
            [r["detection_delay_slots"] for r in phys if r["detection_delay_slots"] is not None]))
        if any(r["detection_delay_slots"] is not None for r in phys) else None,
        "false_alarm_cases": false_alarm_slots,
        "false_alarm_case_fraction": (false_alarm_slots / len(healthy)
                                      if healthy else float("nan")),
        "false_alarms_per_hour_extrapolated": false_alarm_slots / max(hours, 1e-9),
        "sensor_detection_recall": float(np.mean(
            [1.0 if r["detected"] else 0.0 for r in sens])) if sens else float("nan"),
    })
    write_json(out_dir / "p1e_metrics.json", {
        "metrics": metrics,
        "confusion_matrix": confusion,
        "note": ("Ground-truth labels are used only for scoring; the detector receives telemetry only. "
                 "The per-hour false-alarm value is an arithmetic extrapolation from short "
                 "simulated cases, not a measured operational false-alarm rate."),
    })

    seed_sets = [set(cal_seeds), set(val_seeds), set(eval_seeds)]
    checks["calibration_eval_disjoint"] = bool(
        all(not (seed_sets[i] & seed_sets[j])
            for i in range(len(seed_sets)) for j in range(i + 1, len(seed_sets))))
    checks["all_fault_families_exercised"] = bool(set(faults) <= set(baseline_pred))
    checks["sensor_faults_exercised"] = bool(len(sens) > 0)
    checks["healthy_false_alarm_cases_present"] = bool(len(healthy) > 0)
    checks["confusion_matrix_written"] = (out_dir / "p1e_confusion.csv").exists()
    expected_rows = len(eval_seeds) * (len(faults) * (1 + len(sensor_kinds)) +
                                       len(sensor_kinds))
    checks["harness_executed"] = bool(len(rows) == expected_rows and len(store.rows) > 0)
    # Store a few aggregate rows for the suite table.
    for k, v in metrics.items():
        if isinstance(v, (int, float)) and v is not None:
            store.add("P1E", "heldout", eval_seeds[0], "detector", k, float(v), "",
                      "SIMULATED", digest)
    return make_result("P1E", "Held-out fault and sensor-degradation challenge",
                       t0, checks, metrics,
                       reason="Held-out challenge completed; metrics are simulation-only and not a product reliability claim.")
