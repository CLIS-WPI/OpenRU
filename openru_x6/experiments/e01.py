"""E01: massive-MIMO scaling with paired channel realisations."""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from ..config import config_digest
from .common import (make_context, make_result, params_for, record, run_engine,
                     seeds_for)


def run(radio, energy, security, suite, out_dir: Path, store) -> object:
    t0 = time.time()
    p = params_for("E01", suite)
    seeds = seeds_for(suite, "E01")
    chains_list = [int(x) for x in p.get("chain_modes", [8, 64])]
    ue_list = [int(x) for x in p.get("ue_counts", [16, 128])]
    n_slots = int(p.get("slots", 3))
    precoders = list(p.get("precoders", ["mf", "zf", "rzf"]))
    digest = config_digest(radio, energy, security, suite)
    checks: dict[str, bool] = {}
    metrics: dict[str, object] = {}
    all_finite = True
    all_nonneg = True

    for U in ue_list:
        for seed in seeds:
            ctx = make_context(radio, seed=seed, n_users=U, n_slots=n_slots,
                               channel_update_slots=n_slots, saturate=True)
            for chains in chains_list:
                r = run_engine(radio, energy, security, ctx, forced_chains=chains,
                               scheduler_policy="pf", energy_kind="static")
                sc = f"chains{chains}_ue{U}"
                record(r, "E01", sc, seed, "pf", store, digest)
                vals = [r.summary["sum_goodput_mbps"], r.summary["mean_sinr_db"],
                        r.summary["energy_per_bit_nj"], r.summary["mean_useful_layers"]]
                all_finite &= all(np.isfinite(v) for v in vals)
                all_nonneg &= r.summary["sum_goodput_mbps"] >= 0 and r.summary["energy_j"] > 0
            if chains_list == [8, 64] or 64 in chains_list:
                for prec in precoders:
                    m = radio.mimo.model_copy(update={"precoder": prec})
                    rp = radio.model_copy(update={"mimo": m})
                    r = run_engine(rp, energy, security, ctx, forced_chains=64,
                                   scheduler_policy="pf", energy_kind="static")
                    sc = f"precoder_{prec}_ue{U}"
                    record(r, "E01", sc, seed, prec, store, digest)
            if U in (64, 128):
                for sched in ("pf", "rr", "mt"):
                    r = run_engine(radio, energy, security, ctx, forced_chains=64,
                                   scheduler_policy=sched, energy_kind="static")
                    sc = f"sched_{sched}_ue{U}"
                    record(r, "E01", sc, seed, sched, store, digest)

    checks["all_metrics_finite"] = bool(all_finite)
    checks["no_negative_service"] = bool(all_nonneg)
    base = [r["value"] for r in store.rows if r["experiment"] == "E01"
            and r["metric"] == "sum_goodput_mbps" and r["scenario"] == "chains8_ue64"]
    high = [r["value"] for r in store.rows if r["experiment"] == "E01"
            and r["metric"] == "sum_goodput_mbps" and r["scenario"] == "chains64_ue64"]
    if base and high:
        checks["64_chains_beats_8_at_64_ues"] = bool(np.mean(high) > np.mean(base))
        metrics["gain_64_vs_8_db"] = float(10 * np.log10(np.mean(high) / max(np.mean(base), 1e-9)))
    checks["data_collected"] = len(store.rows) > 0

    return make_result("E01", "Massive MIMO scaling", t0, checks, metrics)
