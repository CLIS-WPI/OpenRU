"""E06: ISAC sensing versus communication under a matched airtime budget."""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from ..config import config_digest
from ..isac import ISACController, Target
from .common import (make_context, make_result, params_for, record, run_engine,
                     seeds_for)


def run(radio, energy, security, suite, out_dir: Path, store) -> object:
    t0 = time.time()
    p = params_for("E06", suite)
    seeds = seeds_for(suite, "E06")
    budgets = [float(x) for x in p.get("budgets", [0.01, 0.05])]
    policies = list(p.get("policies", ["comm_only", "periodic", "adaptive"]))
    n_slots = int(p.get("slots", 240))
    digest = config_digest(radio, energy, security, suite)
    dt = radio.cell.slot_duration_s
    targets = [Target(range_m=80.0, velocity_mps=1.2, rcs_m2=1.0, present_slots=(10, n_slots - 10)),
               Target(range_m=150.0, velocity_mps=-0.8, rcs_m2=1.0, present_slots=(10, n_slots - 10))]
    checks: dict[str, bool] = {}
    metrics: dict[str, object] = {}
    all_finite = True

    for seed in seeds:
        ctx = make_context(radio, seed=seed, n_users=32, n_slots=4,
                           channel_update_slots=2, saturate=True)
        base_run = run_engine(radio, energy, security, ctx, scheduler_policy="pf",
                              energy_kind="static", forced_chains=64)
        base_bps = max(base_run.summary["sum_goodput_mbps"] * 1e6, 1.0)
        store.add("E06", "base_capacity", seed, "none", "comm_capacity_mbps",
                  base_bps / 1e6, "Mbps", "SIMULATED", digest)
        for pol in policies:
            budget_list = [0.0] if pol == "comm_only" else budgets
            for budget in budget_list:
                ctrl = ISACController(radio, budget, "off" if pol == "comm_only" else pol,
                                      np.random.default_rng(seed + 6000 + int(budget * 1e6)),
                                      clutter_cnr_db=10.0, pfa_target=1e-8)
                rate_sum = 0.0
                for slot in range(n_slots):
                    out = ctrl.step(slot, targets, radio.cell.n_rb_sim * 14, base_bps, dt)
                    rate_sum += out["comm_rate_bps"] * dt
                s = ctrl.summary(targets, n_slots)
                integrated = rate_sum / (n_slots * dt)
                overhead = 100.0 * (1.0 - integrated / base_bps)
                sc = f"budget{budget:.3f}"
                store.add("E06", sc, seed, pol, "pd", float(s["pd"]), "", "SIMULATED", digest)
                store.add("E06", sc, seed, pol, "pd_per_look",
                          float(s["pd_per_look"]), "", "SIMULATED", digest)
                store.add("E06", sc, seed, pol, "pfa_per_minute",
                          float(s["pfa_per_minute"]), "1/min", "SIMULATED", digest)
                store.add("E06", sc, seed, pol, "pfa_per_sensing_look",
                          float(s["pfa_per_sensing_look"]), "", "SIMULATED", digest)
                store.add("E06", sc, seed, pol, "comm_overhead_pct", float(overhead), "%",
                          "SIMULATED", digest)
                store.add("E06", sc, seed, pol, "realized_sensing_fraction",
                          float(s["realized_sensing_fraction"]), "", "SIMULATED", digest)
                if s["mean_abs_range_error_m"] is not None:
                    store.add("E06", sc, seed, pol, "mean_abs_range_error_m",
                              float(s["mean_abs_range_error_m"]), "m", "SIMULATED", digest)
                if s["mean_detection_latency_slots"] is not None:
                    store.add("E06", sc, seed, pol, "mean_detection_latency_slots",
                              float(s["mean_detection_latency_slots"]), "slots",
                              "SIMULATED", digest)
                all_finite &= all(np.isfinite(v) for v in (overhead, s["pd"], s["pfa_per_minute"]))
                if pol == "comm_only":
                    checks["comm_only_has_zero_overhead"] = abs(overhead) < 1e-6

    checks["metrics_finite"] = bool(all_finite)
    pa = [r["value"] for r in store.rows if r["experiment"] == "E06"
          and r["policy"] == "adaptive" and r["metric"] == "pd"]
    pp = [r["value"] for r in store.rows if r["experiment"] == "E06"
          and r["policy"] == "periodic" and r["metric"] == "pd"]
    if pa:
        checks["adaptive_detects_targets"] = float(np.mean(pa)) >= 0.5
        metrics["adaptive_mean_pd"] = float(np.mean(pa))
    if pa and pp:
        checks["adaptive_beats_periodic_pd"] = float(np.mean(pa)) >= float(np.mean(pp))
        metrics["periodic_mean_pd"] = float(np.mean(pp))
    ov = [r["value"] for r in store.rows if r["experiment"] == "E06"
          and r["metric"] == "comm_overhead_pct" and r["policy"] != "comm_only"]
    if ov:
        checks["sensing_overhead_bounded"] = float(np.max(ov)) <= 8.0
        metrics["max_comm_overhead_pct"] = float(np.max(ov))
    pf = [r["value"] for r in store.rows if r["experiment"] == "E06"
          and r["metric"] == "pfa_per_minute" and r["policy"] != "comm_only"]
    if pf:
        checks["false_alarms_bounded"] = float(np.max(pf)) <= 20.0
        metrics["max_false_alarms_per_min"] = float(np.max(pf))
    checks["data_collected"] = bool(pa)

    return make_result("E06", "ISAC sensing versus communication", t0, checks, metrics)
