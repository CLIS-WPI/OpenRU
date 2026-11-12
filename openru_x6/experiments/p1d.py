"""P1-D: QoS-constrained closed-loop energy and fault recovery."""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from ..config import config_digest
from ..diagnostics import StatisticalDetector
from ..faults import FaultSpec
from ..metrics import write_json
from ..sensors import SensorFaultInjector, SensorFaultSpec
from ..traffic import TrafficTrace
from .common import make_context, make_result, params_for, record, run_engine
from .p1_common import write_csv


def _burst_trace(radio, users: int, slots: int, seed: int) -> TrafficTrace:
    rng = np.random.default_rng(seed + 40_003)
    dt = radio.cell.slot_duration_s
    mean_bits = radio.traffic.mean_arrival_mbps * 1e6 * dt
    arr = np.zeros((slots, users), dtype=float)
    arr[90:150] = rng.poisson(mean_bits * 0.30, size=(60, users)).astype(float)
    deadline = np.full(users, radio.traffic.qos_deadline_slots, dtype=int)
    return TrafficTrace(arrivals_bits=arr, deadline_slots=deadline,
                        mean_mbps=radio.traffic.mean_arrival_mbps,
                        load_fraction=1.0, slot_duration_s=dt)


def _calibrate(radio, energy, security, suite, p: dict) -> tuple[StatisticalDetector, dict]:
    slots = int(p.get("slots", 400))
    users = int(p.get("users", 48))
    cal_seeds = [int(x) for x in suite.get("p1e", {}).get("cal_seeds", [9001, 9002])]
    samples: list[dict] = []
    for seed in cal_seeds:
        ctx = make_context(radio, seed=seed, n_users=users, n_slots=min(30, slots),
                           channel_update_slots=10, saturate=True)
        r = run_engine(radio, energy, security, ctx, forced_chains=64,
                       scheduler_policy="pf", energy_kind="static",
                       sole_coverage=True, collect_telemetry=True)
        samples.extend(r.telemetry)
    detector = StatisticalDetector()
    detector.fit(samples, cal_seeds[0])
    return detector, {"calibration_seeds": cal_seeds, "samples": len(samples)}


def _constraint_pass(summary: dict, c: dict) -> bool:
    return bool(
        summary["deadline_miss_fraction"] <= float(c.get("max_deadline_miss", 1.0)) and
        summary["latency_p99_completed_slots"] <= float(c.get("max_p99_completed_slots", 1e9)) and
        summary["p5_user_goodput_mbps"] >= float(c.get("min_p5_goodput_mbps", 0.0)) and
        summary["energy_j"] <= float(c.get("max_energy_j", 1e18))
    )


def run(radio, energy, security, suite, out_dir: Path, store) -> object:
    t0 = time.time()
    p = params_for("P1D", suite)
    digest = config_digest(radio, energy, security, suite)
    checks: dict[str, bool] = {}
    metrics: dict[str, object] = {}
    detector, cal = _calibrate(radio, energy, security, suite, p)
    slots = int(p.get("slots", 400))
    users = int(p.get("users", 48))
    seeds = [int(x) for x in p.get("seeds", suite.get("p1d", {}).get("seeds", [7201]))]
    policies = [str(x) for x in p.get("policies", ["static", "threshold", "predictive", "constrained"])]
    constraints = list(p.get("constraints", [{}]))
    rows: list[dict] = []
    command_counts = 0
    detected = 0

    for seed in seeds:
        trace = _burst_trace(radio, users, slots, seed)
        ctx = make_context(radio, seed=seed, n_users=users, n_slots=slots,
                           channel_update_slots=max(10, slots // 20), trace=trace)
        for policy_kind in policies:
            variants = constraints if policy_kind == "constrained" else [{"id": "none"}]
            for c in variants:
                cid = str(c.get("id", "none"))
                injector = SensorFaultInjector([
                    SensorFaultSpec("stale", onset_slot=74, duration_slots=8, tile=5),
                    SensorFaultSpec("biased", onset_slot=84, duration_slots=4, tile=2,
                                    feature="temp_c", magnitude=3.0),
                ])
                rng = np.random.default_rng(seed + 41_000)
                r = run_engine(radio, energy, security, ctx,
                               scheduler_policy="pf", energy_kind=policy_kind,
                               sole_coverage=False, forced_chains=None,
                               faults=[FaultSpec(kind="pa_gain_loss", onset_slot=70,
                                                 duration_slots=50, tile=5, magnitude=10.0)],
                               healing=True, healing_detector=detector,
                               collect_telemetry=True,
                               telemetry_transform=lambda tel, slot: injector.step(tel, slot, rng),
                               energy_constraints=c if policy_kind == "constrained" else None)
                sc = f"seed{seed}_{policy_kind}_{cid}"
                record(r, "P1D", sc, seed, policy_kind, store, digest,
                       extra={"slots": slots})
                cmd = int(r.healing.get("control_commands", 0))
                command_counts += cmd
                det = bool(r.healing.get("detected", False))
                detected += int(det)
                feasible = _constraint_pass(r.summary, c) if policy_kind == "constrained" else None
                rows.append({
                    "seed": seed, "policy": policy_kind, "constraint_id": cid,
                    "slots": slots, "energy_j": r.summary["energy_j"],
                    "mean_power_w": r.summary["mean_power_w"],
                    "sum_goodput_mbps": r.summary["sum_goodput_mbps"],
                    "p5_user_goodput_mbps": r.summary["p5_user_goodput_mbps"],
                    "deadline_miss_fraction": r.summary["deadline_miss_fraction"],
                    "latency_p99_completed_slots": r.summary["latency_p99_completed_slots"],
                    "qos_expired_fraction": r.summary["qos_expired_fraction"],
                    "queue_conservation_error": r.summary["queue_conservation_error"],
                    "service_interruption_slots": r.summary["service_interruption_slots"],
                    "transitions": r.summary["transitions"],
                    "oscillations": r.summary["oscillations"],
                    "fault_detected": det,
                    "detection_slot": r.healing.get("detection_slot"),
                    "isolation_slot": r.healing.get("isolation_slot"),
                    "actions_attempted": r.healing.get("actions_attempted", 0),
                    "actions_authorized": r.healing.get("actions_authorized", 0),
                    "actions_vetoed": r.healing.get("actions_vetoed", 0),
                    "control_commands": cmd,
                    "constraint_pass": feasible,
                    "constraint_max_deadline_miss": c.get("max_deadline_miss"),
                    "constraint_max_p99_slots": c.get("max_p99_completed_slots"),
                    "constraint_min_p5_mbps": c.get("min_p5_goodput_mbps"),
                })
                # Store the constraint pass as an explicit boolean metric.
                store.add("P1D", sc, seed, policy_kind, "constraint_pass",
                          1.0 if feasible else 0.0, "", "SIMULATED", digest)
                store.add("P1D", sc, seed, policy_kind, "fault_detected",
                          1.0 if det else 0.0, "", "SIMULATED", digest)

    write_csv(out_dir / "p1d_policy_results.csv", rows)
    write_json(out_dir / "p1d_manifest.json", {
        "calibration": cal, "detector": "StatisticalDetector(z_threshold=4.0)",
        "fault": {"kind": "pa_gain_loss", "tile": 5, "onset": 70, "duration": 50},
        "sensor_faults": ["stale@74-82", "biased temp@84-88"],
        "traffic": "zero offered 0-89, burst 90-149, zero offered 150+",
        "constraint_note": "constraint_pass is evaluated from the run, not asserted by the controller.",
    })
    constrained = [r for r in rows if r["policy"] == "constrained"]
    checks["all_policies_executed"] = bool(len(rows) >= len(seeds) * (len(policies) - 1 + len(constraints)))
    checks["fault_injected_and_scored"] = bool(detected > 0)
    checks["control_commands_observed"] = bool(command_counts > 0)
    checks["qos_conserved"] = bool(all(abs(r["queue_conservation_error"]) < 1e-3 for r in rows))
    checks["constrained_feasibility_reported"] = bool(constrained and all(
        r["constraint_pass"] is not None for r in constrained))
    checks["data_collected"] = len(store.rows) > 0
    expected_total = len(seeds) * ((len(policies) - 1) + len(constraints))
    expected_constrained = len(seeds) * len(constraints)
    checks["run_counts_match_config"] = bool(
        len(rows) == expected_total and len(constrained) == expected_constrained)
    metrics["runs"] = len(rows)
    metrics["total_runs"] = len(rows)
    metrics["expected_total_runs"] = expected_total
    metrics["constrained_runs"] = len(constrained)
    metrics["expected_constrained_runs"] = expected_constrained
    metrics["constrained_feasible_runs"] = int(sum(
        1 for r in constrained if r["constraint_pass"]))
    metrics["fault_detections"] = int(detected)
    metrics["control_commands"] = int(command_counts)
    metrics["runs_with_authorized_recovery"] = int(sum(
        1 for r in rows if r["fault_detected"] and r["actions_authorized"] > 0))
    if constrained:
        metrics["constrained_feasible_rate"] = float(np.mean(
            [1.0 if r["constraint_pass"] else 0.0 for r in constrained]))
        metrics["constrained_mean_energy_j"] = float(np.mean([r["energy_j"] for r in constrained]))
        metrics["constrained_mean_deadline_miss_fraction"] = float(np.mean(
            [r["deadline_miss_fraction"] for r in constrained]))
        metrics["constrained_min_deadline_miss_fraction"] = float(np.min(
            [r["deadline_miss_fraction"] for r in constrained]))
        metrics["constrained_max_deadline_miss_fraction"] = float(np.max(
            [r["deadline_miss_fraction"] for r in constrained]))
        metrics["constrained_mean_p99_completed_slots"] = float(np.mean(
            [r["latency_p99_completed_slots"] for r in constrained]))
        metrics["constrained_min_p99_completed_slots"] = float(np.min(
            [r["latency_p99_completed_slots"] for r in constrained]))
        metrics["constrained_max_p99_completed_slots"] = float(np.max(
            [r["latency_p99_completed_slots"] for r in constrained]))
        metrics["constrained_mean_service_interruption_slots"] = float(np.mean(
            [r["service_interruption_slots"] for r in constrained]))
    return make_result("P1D", "QoS-constrained closed-loop energy and fault recovery",
                       t0, checks, metrics,
                       reason="Closed-loop runs include injected RF fault, stale/biased telemetry and constraint accounting.")
