"""E03: beamforming robustness to mobility, blockage, CSI delay and errors."""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from ..config import config_digest
from .common import (make_context, make_result, params_for, record, run_engine,
                     seeds_for)


SCENARIOS = {
    "baseline": dict(speed=3.0, update=4, delay=0, phase=3.0, quant=5, blockage=False),
    "mobility": dict(speed=5.0, update=2, delay=0, phase=3.0, quant=5, blockage=False),
    "vehicular": dict(speed=30.0, update=1, delay=0, phase=3.0, quant=5, blockage=False),
    "blockage": dict(speed=5.0, update=2, delay=0, phase=3.0, quant=5, blockage=True),
    "csi_delay": dict(speed=10.0, update=1, delay=4, phase=5.0, quant=5, blockage=False),
    "phase_error": dict(speed=5.0, update=2, delay=0, phase=20.0, quant=5, blockage=False),
    "quant3": dict(speed=5.0, update=2, delay=0, phase=5.0, quant=3, blockage=False),
}


def run(radio, energy, security, suite, out_dir: Path, store) -> object:
    t0 = time.time()
    p = params_for("E03", suite)
    seeds = seeds_for(suite, "E03")
    scenarios = list(p.get("scenarios", ["baseline", "mobility", "csi_delay", "phase_error"]))
    n_slots = int(p.get("slots", 10))
    n_users = int(p.get("users", 24))
    digest = config_digest(radio, energy, security, suite)
    checks: dict[str, bool] = {}
    metrics: dict[str, object] = {}
    all_finite = True

    means: dict[str, float] = {}
    for name in scenarios:
        cfg = SCENARIOS[name]
        mimo = radio.mimo.model_copy(update={
            "csi_delay_slots": int(cfg["delay"]),
            "csi_phase_error_deg": float(cfg["phase"]) if name != "phase_error" else 22.0,
            "analog_phase_error_deg": 10.0 if name == "phase_error" else radio.mimo.analog_phase_error_deg,
            "phase_shifter_bits": int(cfg["quant"]),
        })
        rad = radio.model_copy(update={"mimo": mimo})
        for seed in seeds:
            blocked_schedule = None
            if cfg["blockage"]:
                def blocked_schedule(slot, U=n_users):
                    phase = (slot // 5) % 2
                    return (np.arange(U) % 3 == 0) if phase == 0 else (np.arange(U) % 3 == 1)
            ctx = make_context(rad, seed=seed, n_users=n_users, n_slots=n_slots,
                               speed_kmh=float(cfg["speed"]),
                               channel_update_slots=int(cfg["update"]),
                               blocked_schedule=blocked_schedule, saturate=True)
            r = run_engine(rad, energy, security, ctx, scheduler_policy="pf",
                           energy_kind="static")
            record(r, "E03", name, seed, "pf", store, digest,
                   extra={"speed_kmh": float(cfg["speed"]), "csi_delay_slots": float(cfg["delay"])})
            vals = [r.summary["sum_goodput_mbps"], r.summary["mean_sinr_db"],
                    r.summary["mean_bler"], r.summary["outage_fraction"]]
            all_finite &= all(np.isfinite(v) for v in vals)

    checks["metrics_finite"] = bool(all_finite)
    for name in scenarios:
        vals = [row["value"] for row in store.rows if row["experiment"] == "E03"
                and row["scenario"] == name and row["metric"] == "sum_goodput_mbps"]
        if vals:
            means[name] = float(np.mean(vals))
    checks["data_collected"] = bool(means)
    if "baseline" in means:
        checks["impairment_observable"] = any(
            means.get(k, means["baseline"]) < means["baseline"] * 0.999
            for k in ("csi_delay", "phase_error", "vehicular") if k in means)
        metrics["baseline_goodput_mbps"] = means["baseline"]
    checks["no_negative_service"] = all(v >= 0 for v in means.values())

    return make_result("E03", "Beamforming robustness", t0, checks, metrics)
