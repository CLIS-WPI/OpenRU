"""E08: abstract fronthaul impairment observability."""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from ..config import config_digest
from ..fronthaul import FronthaulConfig, FronthaulLink
from .common import (make_context, make_result, params_for, run_engine, seeds_for)


CONDITIONS = {
    "baseline": dict(loss_prob=0.0, jitter_us=5.0, compression_bits=9, sync_lost=False),
    "loss_1pct": dict(loss_prob=0.01, jitter_us=5.0, compression_bits=9, sync_lost=False),
    "loss_5pct": dict(loss_prob=0.05, jitter_us=5.0, compression_bits=9, sync_lost=False),
    "jitter": dict(loss_prob=0.0, jitter_us=80.0, compression_bits=9, sync_lost=False),
    "compression_8bit": dict(loss_prob=0.0, jitter_us=5.0, compression_bits=8, sync_lost=False),
    "sync_loss": dict(loss_prob=0.0, jitter_us=5.0, compression_bits=9, sync_lost=True),
    "combined": dict(loss_prob=0.01, jitter_us=60.0, compression_bits=8, sync_lost=False),
}


def run(radio, energy, security, suite, out_dir: Path, store) -> object:
    t0 = time.time()
    p = params_for("E08", suite)
    seeds = seeds_for(suite, "E08")
    conditions = list(p.get("conditions", ["baseline", "loss_5pct", "sync_loss", "combined"]))
    n_slots = int(p.get("slots", 30))
    digest = config_digest(radio, energy, security, suite)
    dt = radio.cell.slot_duration_s
    checks: dict[str, bool] = {}
    metrics: dict[str, object] = {}
    all_finite = True
    ratios: dict[str, list[float]] = {}

    for seed in seeds:
        ctx = make_context(radio, seed=seed, n_users=24, n_slots=3,
                           channel_update_slots=2, saturate=True)
        base = run_engine(radio, energy, security, ctx, scheduler_policy="pf",
                          energy_kind="static", forced_chains=64)
        base_bps = max(base.summary["sum_goodput_mbps"] * 1e6, 1.0)
        base_sinr = float(base.summary["mean_sinr_db"])
        base_bits = base_bps * n_slots * dt
        for cond in conditions:
            c = CONDITIONS[cond]
            link = FronthaulLink(FronthaulConfig(loss_prob=c["loss_prob"],
                                                 jitter_us=c["jitter_us"],
                                                 compression_bits=c["compression_bits"],
                                                 sync_lost=c["sync_lost"]),
                                 np.random.default_rng(seed + 8000), seed)
            good = 0.0
            for _ in range(n_slots):
                out = link.transmit_slot(base_bps * dt)
                good += out["goodput_bits"]
            s = link.summary()
            ratio = good / max(base_bits, 1.0)
            impaired = link.impair_sinr_db(base_sinr)
            ratios.setdefault(cond, []).append(ratio)
            store.add("E08", cond, seed, "fronthaul", "goodput_ratio", ratio, "",
                      "SIMULATED", digest)
            store.add("E08", cond, seed, "fronthaul", "loss_rate", s["loss_rate"], "",
                      "SIMULATED", digest)
            store.add("E08", cond, seed, "fronthaul", "late_rate", s["late_rate"], "",
                      "SIMULATED", digest)
            store.add("E08", cond, seed, "fronthaul", "sequence_error_rate",
                      s["sequence_error_rate"], "", "SIMULATED", digest)
            store.add("E08", cond, seed, "fronthaul", "compression_evm", s["compression_evm"],
                      "", "SIMULATED", digest)
            store.add("E08", cond, seed, "fronthaul", "sync_loss_fraction",
                      s["sync_loss_fraction"], "", "SIMULATED", digest)
            store.add("E08", cond, seed, "fronthaul", "impaired_sinr_db", impaired, "dB",
                      "SIMULATED", digest)
            all_finite &= np.isfinite(ratio) and np.isfinite(impaired)

    checks["metrics_finite"] = bool(all_finite)
    if "baseline" in ratios:
        checks["baseline_has_no_loss"] = float(np.max(ratios["baseline"])) > 0.999
        metrics["baseline_goodput_ratio"] = float(np.mean(ratios["baseline"]))
    if "loss_5pct" in ratios:
        checks["loss_reduces_goodput"] = float(np.mean(ratios["loss_5pct"])) < 0.99
    if "jitter" in ratios:
        checks["jitter_creates_late_packets"] = any(
            r["value"] > 0 for r in store.rows if r["experiment"] == "E08"
            and r["scenario"] == "jitter" and r["metric"] == "late_rate")
    if "sync_loss" in ratios:
        checks["sync_loss_is_observable"] = any(
            r["value"] > 0 for r in store.rows if r["experiment"] == "E08"
            and r["scenario"] == "sync_loss" and r["metric"] == "sync_loss_fraction")
    if "combined" in ratios and "baseline" in ratios:
        checks["combined_worse_than_baseline"] = float(np.mean(ratios["combined"])) < \
            float(np.mean(ratios["baseline"]))
    checks["data_collected"] = bool(ratios)

    return make_result("E08", "Fronthaul impairment observability", t0, checks, metrics)
