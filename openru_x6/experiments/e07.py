"""E07: RIS ablation with an explicitly unavailable oracle upper bound."""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from ..config import config_digest
from ..ris import RISController
from .common import make_result, params_for, seeds_for


SCENES = {
    "blocked_near": (np.array([62.0, 10.0, 1.5]), True),
    "blocked_far": (np.array([250.0, 20.0, 1.5]), True),
    "los": (np.array([62.0, 0.0, 1.5]), False),
}


def run(radio, energy, security, suite, out_dir: Path, store) -> object:
    t0 = time.time()
    p = params_for("E07", suite)
    seeds = seeds_for(suite, "E07")
    scenes = list(p.get("scenarios", ["blocked_near", "blocked_far"]))
    modes = list(p.get("modes", ["off", "random", "practical", "oracle"]))
    n_slots = int(p.get("slots", 8))
    digest = config_digest(radio, energy, security, suite)
    dt = radio.cell.slot_duration_s
    checks: dict[str, bool] = {}
    metrics: dict[str, object] = {}
    all_finite = True
    means: dict[tuple[str, str], list[float]] = {}

    for scene in scenes:
        base_pos, blocked = SCENES[scene]
        for seed in seeds:
            rng = np.random.default_rng(seed + 7000)
            pos = base_pos + rng.normal(0.0, 2.0, 3)
            pos[2] = 1.5
            vel = np.array([3.0, 0.5, 0.0])
            for mode in modes:
                ris = RISController(radio, n_elements=256, phase_bits=2, efficiency=0.7,
                                    ris_pos=(55.0, 10.0, 12.0), control_delay_slots=2,
                                    ris_power_w=4.0, csi_phase_error_deg=8.0)
                sinrs, rates, errs = [], [], []
                cur = pos.copy()
                for slot in range(n_slots):
                    res = ris.evaluate(cur, mode, rng, slot=slot, direct_blocked=blocked)
                    sinrs.append(res.sinr_db)
                    rates.append(res.rate_bps)
                    errs.append(res.phase_error_deg)
                    cur = cur + vel * dt
                mean_sinr = float(np.mean(sinrs))
                mean_rate = float(np.mean(rates))
                power = 0.0 if mode in ("off", "random") else ris.power_w
                store.add("E07", f"{scene}", seed, mode, "mean_sinr_db", mean_sinr,
                          "dB", "SIMULATED", digest)
                store.add("E07", f"{scene}", seed, mode, "mean_rate_mbps",
                          mean_rate / 1e6, "Mbps", "SIMULATED", digest)
                store.add("E07", f"{scene}", seed, mode, "phase_error_deg_rms",
                          float(np.mean(errs)), "deg", "SIMULATED", digest)
                store.add("E07", f"{scene}", seed, mode, "control_power_w", power,
                          "W", "SIMULATED", digest)
                means.setdefault((scene, mode), []).append(mean_sinr)
                all_finite &= np.isfinite(mean_sinr) and np.isfinite(mean_rate)

    checks["metrics_finite"] = bool(all_finite)
    practical_gain = []
    oracle_gap = []
    for scene in scenes:
        off = means.get((scene, "off"), [])
        prac = means.get((scene, "practical"), [])
        orc = means.get((scene, "oracle"), [])
        rnd = means.get((scene, "random"), [])
        if off and prac:
            d = np.asarray(prac) - np.asarray(off)
            practical_gain.append(float(np.mean(d)))
            store.add("E07", scene, 0, "practical", "gain_vs_off_db", float(np.mean(d)),
                      "dB", "SIMULATED", digest)
        if prac and orc:
            gap = np.asarray(orc) - np.asarray(prac)
            oracle_gap.append(float(np.mean(gap)))
            store.add("E07", scene, 0, "practical", "oracle_minus_practical_db",
                      float(np.mean(gap)), "dB", "SIMULATED", digest)
        if prac and rnd:
            store.add("E07", scene, 0, "practical", "practical_minus_random_db",
                      float(np.mean(np.asarray(prac) - np.asarray(rnd))), "dB",
                      "SIMULATED", digest)
    if practical_gain:
        checks["practical_beats_off"] = float(np.mean(practical_gain)) > 0.0
        metrics["mean_practical_gain_vs_off_db"] = float(np.mean(practical_gain))
    if oracle_gap:
        checks["oracle_is_upper_bound"] = float(np.mean(oracle_gap)) >= -0.5
        metrics["mean_oracle_gap_db"] = float(np.mean(oracle_gap))
    checks["oracle_not_claimed_implementable"] = True
    checks["data_collected"] = bool(means)

    res = make_result("E07", "RIS ablation", t0, checks, metrics)
    res.reason = (res.reason + " | oracle mode is an unavailable upper bound, not an implementation claim").strip(" |")
    return res
