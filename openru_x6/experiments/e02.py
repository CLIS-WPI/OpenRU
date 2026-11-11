"""E02: energy-state optimisation under identical traffic and channel traces."""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from ..config import config_digest
from ..traffic import generate_trace
from .common import (make_context, make_result, params_for, record, run_engine,
                     seeds_for)


def run(radio, energy, security, suite, out_dir: Path, store) -> object:
    t0 = time.time()
    p = params_for("E02", suite)
    seeds = seeds_for(suite, "E02")
    loads = [float(x) for x in p.get("loads", [0.0, 0.25, 1.0])]
    policies = list(p.get("policies", ["static", "threshold", "predictive"]))
    n_slots = int(p.get("slots", 120))
    n_users = int(p.get("users", 48))
    mean_mbps = float(p.get("mean_arrival_mbps", 120.0))
    digest = config_digest(radio, energy, security, suite)
    checks: dict[str, bool] = {}
    metrics: dict[str, object] = {}
    all_finite = True
    illegal_sole = 0
    sleep_sole = 0
    deep_sleep_ok = False
    deep_energy_saved = False
    saving_low_load: list[float] = []
    qos_conservation_ok = True
    qos_tradeoff_values: list[float] = []
    completed_latency_reported = True

    traffic_cfg = radio.traffic.model_copy(update={"mean_arrival_mbps": mean_mbps})
    radio_t = radio.model_copy(update={"traffic": traffic_cfg})

    for load in loads:
        for seed in seeds:
            trace = generate_trace(n_users, n_slots, radio.cell.slot_duration_s,
                                   mean_mbps, load, radio.traffic.burstiness,
                                   radio.traffic.qos_deadline_slots,
                                   np.random.default_rng(seed + 3000))
            ctx = make_context(radio_t, seed=seed, n_users=n_users, n_slots=n_slots,
                               channel_update_slots=max(10, n_slots // 4), trace=trace)
            runs = {}
            for pol in policies:
                r = run_engine(radio_t, energy, security, ctx, energy_kind=pol,
                               scheduler_policy="pf", sole_coverage=True)
                runs[pol] = r
                sc = f"load{load:.2f}"
                record(r, "E02", sc, seed, pol, store, digest,
                       extra={"load_fraction": load, "offered_mbps": mean_mbps * n_users * load})
                vals = [r.summary["energy_j"], r.summary["sum_goodput_mbps"],
                        r.summary["mean_power_w"]]
                all_finite &= all(np.isfinite(v) for v in vals)
                illegal_sole += int(r.summary["illegal_sleep_attempts"])
                sleep_sole += int(r.energy.get("state_counts", {}).get("SLEEP_0", 0))
            if "predictive" in runs and "static" in runs:
                st, pr = runs["static"], runs["predictive"]
                save_pct = 100.0 * (st.summary["energy_j"] - pr.summary["energy_j"]) / \
                    max(st.summary["energy_j"], 1e-12)
                gd = pr.summary["sum_goodput_mbps"] - st.summary["sum_goodput_mbps"]
                store.add("E02", f"load{load:.2f}", seed, "predictive",
                          "energy_saving_pct_vs_static", save_pct, "%", "SIMULATED", digest)
                store.add("E02", f"load{load:.2f}", seed, "predictive",
                          "goodput_delta_mbps_vs_static", gd, "Mbps", "SIMULATED", digest)
                if 0.0 < load <= 0.11:
                    saving_low_load.append(save_pct)
                qos_conservation_ok &= all(np.isfinite(
                    [st.summary["qos_expired_fraction"], pr.summary["qos_expired_fraction"],
                     st.summary["deadline_miss_fraction"], pr.summary["deadline_miss_fraction"]]))
                qos_conservation_ok &= all(
                    abs(x.summary["queue_conservation_error"]) < 1e-3 for x in (st, pr))
                if load > 0:
                    completed_latency_reported &= bool(np.isfinite(
                        pr.summary["latency_p99_completed_slots"]))
                qos_delta = (pr.summary["qos_expired_fraction"] -
                             st.summary["qos_expired_fraction"])
                qos_tradeoff_values.append(float(qos_delta))
                store.add("E02", f"load{load:.2f}", seed, "predictive",
                          "qos_expired_delta_vs_static", qos_delta,
                          "fraction", "SIMULATED", digest)
                store.add("E02", f"load{load:.2f}", seed, "predictive",
                          "latency_p99_slots", pr.summary["latency_p99_slots"],
                          "slots", "SIMULATED", digest)
            if abs(load) < 1e-12:
                ctx_deep = make_context(radio_t, seed=seed, n_users=n_users, n_slots=n_slots,
                                        channel_update_slots=max(10, n_slots // 4), trace=trace)
                d = run_engine(radio_t, energy, security, ctx_deep, energy_kind="predictive",
                               scheduler_policy="pf", sole_coverage=False)
                record(d, "E02", "deep_sleep_non_sole", seed, "predictive", store, digest)
                if d.energy.get("state_counts", {}).get("SLEEP_0", 0) > 0:
                    deep_sleep_ok = True
                    if d.summary["energy_j"] < runs["static"].summary["energy_j"]:
                        deep_energy_saved = True

    checks["metrics_finite"] = bool(all_finite)
    checks["sole_coverage_never_slept"] = sleep_sole == 0 and illegal_sole == 0
    checks["zero_prohibited_sleep_transitions"] = illegal_sole == 0
    checks["non_sole_load0_can_sleep"] = deep_sleep_ok
    checks["deep_sleep_saves_energy"] = deep_energy_saved
    if saving_low_load:
        checks["predictive_saves_energy_at_low_load"] = bool(np.mean(saving_low_load) > 1.0)
        metrics["mean_energy_saving_low_load_pct"] = float(np.mean(saving_low_load))
    checks["qos_accounting_conserved"] = bool(qos_conservation_ok)
    checks["qos_tradeoff_quantified"] = bool(qos_tradeoff_values and
                                             all(np.isfinite(qos_tradeoff_values)))
    checks["completed_latency_reported"] = bool(completed_latency_reported)
    checks["data_collected"] = len(store.rows) > 0

    return make_result("E02", "Energy optimization under traffic load", t0, checks, metrics)
