"""P1-C: 2x2 polarimetric sensitivity (simulation only)."""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from ..config import config_digest
from ..metrics import write_json
from ..traffic import generate_trace
from .common import make_context, make_result, params_for, record, run_engine
from .p1_common import write_csv


def run(radio, energy, security, suite, out_dir: Path, store) -> object:
    t0 = time.time()
    p = params_for("P1C", suite)
    digest = config_digest(radio, energy, security, suite)
    checks: dict[str, bool] = {}
    metrics: dict[str, object] = {}
    rows: list[dict] = []
    slots = int(p.get("slots", 160))
    users = int(p.get("users", 128))
    seeds = [int(x) for x in p.get("seeds", suite.get("p1c", {}).get("seeds", [7101]))]
    chains = [int(x) for x in p.get("chain_modes", [32, 64])]
    xpds = [float(x) for x in p.get("xpd_db", [10.0, 20.0, 30.0])]
    xpr = p.get("xpr_db", 20.0)
    xpr = float(xpr[0] if isinstance(xpr, (list, tuple)) else xpr)

    for seed in seeds:
        for xpd in xpds:
            cfg = radio.model_copy(deep=True)
            cfg = cfg.model_copy(update={"polarization": cfg.polarization.model_copy(update={
                "model": "jones", "xpd_db": xpd, "xpr_db": xpr,
                "orientation_std_deg": float(p.get("orientation_std_deg", 0.0)),
                "calibration_amplitude_error_db": float(
                    p.get("calibration_amplitude_error_db", 0.0)),
                "calibration_phase_error_deg": float(
                    p.get("calibration_phase_error_deg", 0.0)),
            })})
            trace = generate_trace(users, slots, cfg.cell.slot_duration_s,
                                   cfg.traffic.mean_arrival_mbps, 1.0,
                                   cfg.traffic.burstiness, cfg.traffic.qos_deadline_slots,
                                   np.random.default_rng(seed + 30_001))
            ctx = make_context(cfg, seed=seed, n_users=users, n_slots=slots,
                               channel_update_slots=max(10, slots // 8), trace=trace,
                               saturate=True)
            for n in chains:
                r = run_engine(cfg, energy, security, ctx, forced_chains=n,
                               scheduler_policy="pf", energy_kind="static", sole_coverage=True)
                sc = f"jones_xpd{xpd:g}_chains{n}"
                record(r, "P1C", sc, seed, "jones", store, digest,
                       extra={"xpd_db": xpd, "xpr_db": xpr, "chains": n})
                rows.append({"seed": seed, "model": "jones", "xpd_db": xpd,
                             "xpr_db": xpr, "chains": n,
                             "sum_goodput_mbps": r.summary["sum_goodput_mbps"],
                             "p5_user_goodput_mbps": r.summary["p5_user_goodput_mbps"],
                             "mean_sinr_db": r.summary["mean_sinr_db"],
                             "energy_per_bit_nj": r.summary["energy_per_bit_nj"],
                             "mean_useful_layers": r.summary["mean_useful_layers"]})

    # Explicit scalar reference: changing structure must not alter the legacy path.
    trace = generate_trace(users, slots, radio.cell.slot_duration_s,
                           radio.traffic.mean_arrival_mbps, 1.0,
                           radio.traffic.burstiness, radio.traffic.qos_deadline_slots,
                           np.random.default_rng(seeds[0] + 30_001))
    ctx = make_context(radio, seed=seeds[0], n_users=users, n_slots=slots,
                       channel_update_slots=max(10, slots // 8), trace=trace,
                       saturate=True)
    simple = run_engine(radio, energy, security, ctx, forced_chains=64,
                        scheduler_policy="pf", energy_kind="static", sole_coverage=True)
    record(simple, "P1C", "simple_reference_chains64", seeds[0], "simple", store, digest)
    write_csv(out_dir / "polarization_sensitivity.csv", rows)
    write_json(out_dir / "polarization_manifest.json", {
        "model": "2x2 dual-polarized Jones matrix; simulation only",
        "xpd_db": xpds, "xpr_db": xpr,
        "orientation_std_deg": float(p.get("orientation_std_deg", 0.0)),
        "calibration_amplitude_error_db": float(
            p.get("calibration_amplitude_error_db", 0.0)),
        "calibration_phase_error_deg": float(
            p.get("calibration_phase_error_deg", 0.0)),
        "note": "XPD/XPR are configuration sweeps, not antenna-chamber measurements.",
        "seeds": seeds, "chains": chains,
    })
    checks["jones_grid_completed"] = bool(len(rows) == len(seeds) * len(xpds) * len(chains))
    checks["jones_metrics_finite"] = bool(all(
        np.isfinite(v) for r in rows for v in (r["sum_goodput_mbps"], r["mean_sinr_db"])))
    checks["simple_reference_preserved"] = bool(
        np.isfinite(simple.summary["sum_goodput_mbps"]) and
        simple.summary["sum_goodput_mbps"] > 0)
    checks["polarization_artifact_written"] = (out_dir / "polarization_sensitivity.csv").exists()
    checks["data_collected"] = len(store.rows) > 0
    metrics["jones_mean_goodput_mbps"] = float(np.mean([r["sum_goodput_mbps"] for r in rows]))
    metrics["simple_reference_goodput_mbps"] = simple.summary["sum_goodput_mbps"]
    metrics["xpd_levels"] = len(xpds)
    return make_result("P1C", "2x2 polarimetric sensitivity", t0, checks, metrics,
                       reason="Optional polarimetric sweep complete; XPD/XPR are simulated.")
