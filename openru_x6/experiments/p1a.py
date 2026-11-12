"""P1-A: long-horizon, paired massive-MIMO scaling and hardware selection."""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from ..config import config_digest
from ..metrics import paired_delta_ci
from ..traffic import generate_trace
from .common import (make_context, make_result, params_for, record, run_engine,
                     seeds_for)
from .p1_common import pct, write_csv
from ..metrics import write_json


def _conditions(p: dict) -> list[str]:
    return [str(x) for x in p.get("conditions", ["baseline"])]


def _radio_for(radio, spread: float, condition: str):
    cfg = radio.model_copy(deep=True)
    cfg = cfg.model_copy(update={
        "channel": cfg.channel.model_copy(update={"angular_spread_deg": float(spread)})})
    if condition == "stale_csi":
        cfg = cfg.model_copy(update={
            "mimo": cfg.mimo.model_copy(update={
                "csi_delay_slots": max(4, cfg.mimo.csi_delay_slots)})})
    return cfg


def _run_case(radio, energy, security, suite, seed: int, chains: int, users: int,
              load: float, spread: float, condition: str, slots: int, store, digest: str,
              tag: str):
    speed = 30.0 if condition == "mobility" else 3.0
    trace = generate_trace(users, slots, radio.cell.slot_duration_s,
                           radio.traffic.mean_arrival_mbps, load,
                           radio.traffic.burstiness, radio.traffic.qos_deadline_slots,
                           np.random.default_rng(seed + 10_007))
    rcfg = _radio_for(radio, spread, condition)
    ctx = make_context(rcfg, seed=seed, n_users=users, n_slots=slots,
                       speed_kmh=speed,
                       channel_update_slots=max(10, slots // 10), trace=trace)
    r = run_engine(rcfg, energy, security, ctx, forced_chains=chains,
                   scheduler_policy="pf", energy_kind="static",
                   sole_coverage=True, collect_telemetry=False)
    sc = f"chains{chains}_ue{users}_load{load:.2f}_spread{spread:g}_{condition}"
    record(r, "P1A", sc, seed, tag, store, digest,
           extra={"chains": chains, "users": users, "offered_load": load,
                  "angular_spread_deg": spread, "slots": slots})
    return {
        "seed": seed, "chains": chains, "users": users, "load": load,
        "spread": spread, "condition": condition, "slots": slots, "tag": tag,
        "scenario": sc,
        **{k: r.summary[k] for k in (
            "sum_goodput_mbps", "p5_user_goodput_mbps", "mean_user_goodput_mbps",
            "mean_sinr_db", "p5_sinr_db", "energy_j", "energy_per_bit_nj",
            "mean_power_w", "mean_active_chains", "capacity_bound_mbps",
            "latency_p95_completed_slots", "latency_p99_completed_slots",
            "deadline_miss_fraction", "qos_expired_fraction",
            "queue_conservation_error", "service_interruption_slots")},
    }


def run(radio, energy, security, suite, out_dir: Path, store) -> object:
    t0 = time.time()
    p = params_for("P1A", suite)
    base = int(suite.get("seed_base", 2000))
    digest = config_digest(radio, energy, security, suite)
    checks: dict[str, bool] = {}
    metrics: dict[str, object] = {}
    rows: list[dict] = []

    screen_slots = int(p.get("screening_slots", 2000))
    screen_seeds = int(p.get("screening_seeds", 2))
    chain_modes = [int(x) for x in p.get("chain_modes", [16, 32, 64])]
    ue_counts = [int(x) for x in p.get("ue_counts", [64, 128])]
    loads = [float(x) for x in p.get("loads", [0.25, 1.0])]
    spreads = [float(x) for x in p.get("spatial_spreads_deg", [2.0, 20.0])]
    conditions = _conditions(p)

    screening_runs = 0
    for si in range(screen_seeds):
        seed = base + 500 + si
        for U in ue_counts:
            for chains in chain_modes:
                for load in loads:
                    for spread in spreads:
                        for cond in conditions:
                            rows.append(_run_case(radio, energy, security, suite, seed,
                                                  chains, U, load, spread, cond,
                                                  screen_slots, store, digest, "screening"))
                            screening_runs += 1

    # Pivotal paired contrast at the configured short horizon and 20 seeds.  The
    # 20,000-slot stage is timed/measured separately rather than pretending every
    # seed ran much longer than the recorded runtime supports.
    pivotal_seeds = int(p.get("pivotal_seeds", 20))
    pivot_slots = int(p.get("pivotal_slots_short", 1000))
    long_slots = int(p.get("long_horizon_slots", 20000))
    pivot_chains = [int(x) for x in p.get("pivotal_chain_modes", [32, 64])]
    pivot_ue = [int(x) for x in p.get("pivotal_ue_counts", [128])]
    pivot_loads = [float(x) for x in p.get("pivotal_loads", [1.0])]
    pivot_spreads = [float(x) for x in p.get("pivotal_spreads_deg", [2.0, 20.0])]
    pivot_conditions = [str(x) for x in p.get("pivotal_conditions", ["baseline"])]
    pivotal_rows: list[dict] = []
    for pi in range(pivotal_seeds):
        seed = base + 2000 + pi
        for U in pivot_ue:
            for load in pivot_loads:
                for spread in pivot_spreads:
                    for cond in pivot_conditions:
                        for chains in pivot_chains:
                            rr = _run_case(radio, energy, security, suite, seed,
                                           chains, U, load, spread, cond,
                                           pivot_slots, store, digest, "pivotal")
                            rows.append(rr)
                            pivotal_rows.append(rr)

    # Runtime/mechanism check at the requested long horizon.  This is a
    # measured profile, not a claim that the 20-seed pivotal matrix used 20k.
    profile_seeds = int(p.get("pivotal_profile_seeds", 2))
    profile_chains = [int(x) for x in p.get("long_horizon_profile_chains", pivot_chains)]
    profile_users = int(p.get("long_horizon_profile_users", 16))
    profile_load = float(p.get("long_horizon_profile_load", 1.0))
    profile_spread = float(p.get("long_horizon_profile_spread_deg", 20.0))
    long_rows: list[dict] = []
    for pi in range(profile_seeds):
        seed = base + 4000 + pi
        for chains in profile_chains:
            long_rows.append(_run_case(radio, energy, security, suite, seed, chains,
                                       profile_users, profile_load, profile_spread,
                                       "baseline", long_slots, store, digest,
                                       "long_horizon_profile"))

    # Paired comparisons across chains for each matched cell.
    by_key: dict[tuple, dict[int, list[dict]]] = {}
    for rr in rows:
        key = (rr["tag"], rr["users"], rr["load"], rr["spread"], rr["condition"])
        by_key.setdefault(key, {}).setdefault(rr["chains"], []).append(rr)
    paired: list[dict] = []
    for key, groups in sorted(by_key.items(), key=lambda kv: str(kv[0])):
        tag, U, load, spread, cond = key
        for lo, hi in ((16, 32), (16, 64), (32, 64)):
            if lo not in groups or hi not in groups:
                continue
            a = {r["seed"]: r for r in groups[hi]}
            b = {r["seed"]: r for r in groups[lo]}
            common = sorted(set(a) & set(b))
            if not common:
                continue
            for metric_name in ("sum_goodput_mbps", "p5_user_goodput_mbps",
                                "energy_per_bit_nj", "latency_p99_completed_slots",
                                "deadline_miss_fraction"):
                aa = [a[s][metric_name] for s in common]
                bb = [b[s][metric_name] for s in common]
                ci = paired_delta_ci(aa, bb, n_boot=int(p.get("n_boot", 1000)))
                paired.append({
                    "stage": tag, "users": U, "load": load, "spread_deg": spread,
                    "condition": cond, "contrast": f"{hi}_minus_{lo}",
                    "metric": metric_name, "n_pairs": ci["n"],
                    "mean_delta": ci["mean_delta"], "ci_low": ci["ci_low"],
                    "ci_high": ci["ci_high"],
                })
                store.add("P1A", f"paired_{tag}_ue{U}_load{load:.2f}_spread{spread:g}_{cond}",
                          -1, f"{hi}_minus_{lo}", f"paired_{metric_name}_mean_delta",
                          ci["mean_delta"], "", "SIMULATED", digest)

    write_json(out_dir / "p1a_progress.json", {
        "stage": "paired-complete", "screening_runs": len(rows) - len(pivotal_rows),
        "pivotal_runs": len(pivotal_rows), "long_profile_runs": len(long_rows),
        "paired_rows": len(paired),
    })
    write_csv(out_dir / "paired_comparisons.csv", paired)
    write_csv(out_dir / "p1a_runs.csv", rows)
    write_json(out_dir / "seed_manifest.json", {
        "seed_base": base,
        "screening_seeds": [base + 500 + i for i in range(screen_seeds)],
        "pivotal_seeds": [base + 2000 + i for i in range(pivotal_seeds)],
        "long_horizon_profile_seeds": [base + 4000 + i for i in range(profile_seeds)],
        "screening_slots": screen_slots,
        "pivotal_slots": pivot_slots,
        "long_horizon_slots": long_slots,
        "reduced_long_horizon": True,
        "reason": (f"20,000-slot profile is measured separately; {pivotal_seeds} pivots use "
                   f"{pivot_slots} slots to keep the local suite affordable. This is "
                   "disclosed, not extrapolated as 20k-seed evidence."),
    })

    p32 = [r for r in pivotal_rows if r["chains"] == 32]
    p64 = [r for r in pivotal_rows if r["chains"] == 64]
    if p32 and p64:
        g32 = float(np.mean([r["sum_goodput_mbps"] for r in p32]))
        g64 = float(np.mean([r["sum_goodput_mbps"] for r in p64]))
        epb32 = float(np.nanmean([r["energy_per_bit_nj"] for r in p32]))
        epb64 = float(np.nanmean([r["energy_per_bit_nj"] for r in p64]))
        metrics.update({"pivotal_32_mean_goodput_mbps": g32,
                        "pivotal_64_mean_goodput_mbps": g64,
                        "pivotal_64_vs_32_gain_db": float(10 * np.log10(g64 / max(g32, 1e-12))),
                        "pivotal_32_energy_per_bit_nj": epb32,
                        "pivotal_64_energy_per_bit_nj": epb64,
                        "pivotal_64_count": len(p64), "pivotal_32_count": len(p32)})
    metrics["screening_runs"] = screening_runs
    metrics["screening_slots"] = screen_slots
    metrics["pivotal_slots"] = pivot_slots
    metrics["long_horizon_profile_slots"] = long_slots
    metrics["long_horizon_profile_runs"] = len(long_rows)
    metrics["paired_comparisons"] = len(paired)
    metrics["reduced_long_horizon"] = True

    finite = all(np.isfinite(r["sum_goodput_mbps"]) and np.isfinite(r["energy_j"])
                 for r in rows)
    checks["metrics_finite"] = bool(finite)
    checks["paired_20_seed_pivots_completed"] = bool(
        pivotal_seeds >= 20 and len({r["seed"] for r in pivotal_rows}) >= 20)
    checks["long_horizon_20k_profile_completed"] = bool(long_rows and all(
        r["slots"] >= 20000 for r in long_rows))
    checks["paired_comparisons_written"] = (out_dir / "paired_comparisons.csv").exists()
    checks["queue_conservation"] = bool(all(abs(r["queue_conservation_error"]) < 1e-3
                                            for r in rows))
    checks["data_collected"] = bool(rows and paired)

    # Honest hardware memo: state the conditional decision rule, not a winner
    # chosen after looking only at the mean.
    sel = [x for x in paired if x["metric"] == "sum_goodput_mbps" and
           x["contrast"] == "64_minus_32" and x["stage"] == "pivotal"]
    if sel:
        pos = sum(1 for x in sel if x["ci_low"] > 0)
        neg = sum(1 for x in sel if x["ci_high"] < 0)
        metrics["pivotal_goodput_contrasts"] = len(sel)
        metrics["pivotal_goodput_positive_ci"] = pos
        metrics["pivotal_goodput_negative_ci"] = neg
    lines = [
        "# Hardware-selection memo (P1-A, simulated)",
        "",
        "Status: conditional simulation evidence, not a hardware purchase recommendation.",
        "",
        f"- Pivotal seeds: {pivotal_seeds}; pivot length: {pivot_slots} slots per run; U={pivot_ue}.",
        f"- Pivotal 32-chain mean goodput: {metrics.get('pivotal_32_mean_goodput_mbps', float('nan')):.3f} Mbps",
        f"- Pivotal 64-chain mean goodput: {metrics.get('pivotal_64_mean_goodput_mbps', float('nan')):.3f} Mbps",
        f"- 64-vs-32 mean gain: {metrics.get('pivotal_64_vs_32_gain_db', float('nan')):.3f} dB",
        f"- 32-chain energy/bit: {metrics.get('pivotal_32_energy_per_bit_nj', float('nan')):.3f} nJ/bit",
        f"- 64-chain energy/bit: {metrics.get('pivotal_64_energy_per_bit_nj', float('nan')):.3f} nJ/bit",
        "",
        "Decision rule: choose 64 chains only where the paired 64-minus-32 goodput CI is",
        "above zero and the energy/QoS constraints are also met. Choose 32 where the CI",
        "straddles zero or the extra energy is not justified. This memo does not model",
        "BOM cost, PCB loss/reliability, thermal design margin, or regulatory limits.",
        "",
        f"Paired goodput contrasts: {metrics.get('pivotal_goodput_contrasts', 0)}; "
        f"CI>0: {metrics.get('pivotal_goodput_positive_ci', 0)}; "
        f"CI<0: {metrics.get('pivotal_goodput_negative_ci', 0)}.",
        "",
        f"A {long_slots:,}-slot timing/mechanism profile (U={profile_users}) was run separately; it is not a",
        f"20-seed {long_slots:,}-slot matrix. See `p1a_runs.csv` and `seed_manifest.json`.",
    ]
    (out_dir / "hardware_choice_memo.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return make_result("P1A", "Long-horizon paired massive-MIMO scaling", t0, checks, metrics,
                       reason="P1-A completed with disclosed reduced long-horizon design.")
