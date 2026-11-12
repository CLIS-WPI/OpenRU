"""P1-B: explicit NR resource accounting and PHY link-boundary audit."""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from ..config import config_digest
from ..metrics import write_json
from ..phy import link_adaptation, nr_grid_audit, resource_multiplier, sionna_phy_validation
from ..traffic import generate_trace
from .common import make_context, make_result, params_for, record, run_engine
from .p1_common import grid_audit, resource_dict


def run(radio, energy, security, suite, out_dir: Path, store) -> object:
    t0 = time.time()
    p = params_for("P1B", suite)
    digest = config_digest(radio, energy, security, suite)
    checks: dict[str, bool] = {}
    metrics: dict[str, object] = {}
    resource = resource_dict(radio)
    audit = grid_audit(radio)
    write_json(out_dir / "nr_grid_audit.json", audit)

    expected_factor = (
        float(audit["tdd_dl_fraction"]) *
        (float(audit["dl_symbols_per_slot"]) / max(float(audit["symbols_per_slot"]), 1.0)) *
        (float(audit["n_prb"]) / max(float(audit["n_rb_total"]), 1.0)) *
        (1.0 - float(audit["control_overhead_fraction"])) *
        (1.0 - float(audit["dmrs_overhead_fraction"])) *
        (1.0 - float(audit["ssb_overhead_fraction"]))
    )
    checks["bandwidth_98_28_mhz"] = abs(float(audit["occupied_bandwidth_mhz"]) - 98.28) < 0.02
    checks["grid_utilization_below_envelope"] = 0.0 < float(audit["grid_utilization"]) <= 1.0
    checks["resource_factor_computed_once"] = abs(float(audit["resource_multiplier"]) -
                                                   expected_factor) < 1e-12
    zero = dict(resource, n_prb=0)
    checks["zero_prb_forces_zero"] = resource_multiplier(zero) == 0.0
    zero_tdd = dict(resource, tdd_dl_fraction=0.0)
    checks["zero_tdd_forces_zero"] = resource_multiplier(zero_tdd) == 0.0
    full = resource_multiplier(dict(resource, mode="capacity_bound"))
    checks["capacity_bound_factor_is_one"] = full == 1.0

    # Link-boundary sweep: abstraction is evaluated at the same SINR and the
    # delivered rate must remain bounded by capacity x resource factor.
    snrs = [float(x) for x in p.get("snr_db", [0.0, 2.0, 4.0, 6.0, 8.0])]
    la = link_adaptation(np.asarray(snrs), radio.cell.bandwidth_hz, radio.mimo, resource=resource)
    boundary = [{"snr_db": float(s), "mcs": int(m), "bler": float(b),
                 "se_bps_hz": float(e), "capacity_mbps": float(c) / 1e6,
                 "delivered_mbps": float(r) / 1e6}
                for s, m, b, e, c, r in zip(snrs, la["mcs"], la["bler"], la["se"],
                                             la["capacity_bps"], la["rate_bps"])]
    write_json(out_dir / "link_boundary.json", boundary)
    checks["link_boundary_rate_bounded"] = bool(all(
        x["delivered_mbps"] <= x["capacity_mbps"] * float(audit["resource_multiplier"]) + 1e-9
        for x in boundary))
    checks["link_boundary_finite"] = bool(all(
        np.isfinite(v) for x in boundary for v in
        (x["bler"], x["se_bps_hz"], x["capacity_mbps"], x["delivered_mbps"])))

    # End-to-end delivered vs capacity bound using a short trace.
    slots = int(p.get("slots", 80))
    users = int(p.get("users", 128))
    seed = int(p.get("seeds", [7001])[0])
    trace = generate_trace(users, slots, radio.cell.slot_duration_s,
                           radio.traffic.mean_arrival_mbps, 1.0,
                           radio.traffic.burstiness, radio.traffic.qos_deadline_slots,
                           np.random.default_rng(seed + 20_001))
    ctx = make_context(radio, seed=seed, n_users=users, n_slots=slots,
                       channel_update_slots=max(10, slots // 4), trace=trace)
    r = run_engine(radio, energy, security, ctx, forced_chains=64,
                   scheduler_policy="pf", energy_kind="static", sole_coverage=True)
    record(r, "P1B", "nr_grid_end_to_end", seed, "static", store, digest)
    cap = float(r.summary["capacity_bound_mbps"])
    got = float(r.summary["sum_goodput_mbps"])
    checks["delivered_below_capacity_bound"] = got <= cap * float(audit["resource_multiplier"]) + 1e-6
    checks["delivered_positive"] = got > 0.0
    metrics.update({
        "occupied_bandwidth_mhz": audit["occupied_bandwidth_mhz"],
        "grid_utilization": audit["grid_utilization"],
        "resource_multiplier": audit["resource_multiplier"],
        "capacity_bound_mbps": cap,
        "delivered_goodput_mbps": got,
        "delivered_over_capacity": got / max(cap * float(audit["resource_multiplier"]), 1e-12),
    })

    # Optional real PHY cross-check.  If Sionna is unavailable, report BLOCKED
    # rather than silently substituting simulated numbers.
    try:
        phy = sionna_phy_validation([float(x) for x in snrs],
                                    batch=int(p.get("sionna_batch", 32)),
                                    seed=int(seed))
        write_json(out_dir / "sionna_crosscheck.json", phy)
        checks["sionna_crosscheck_executed"] = bool(phy.get("rows"))
        high = max(phy["rows"], key=lambda x: x["snr_db"])
        low = min(phy["rows"], key=lambda x: x["snr_db"])
        checks["sionna_bler_decreases_with_snr"] = bool(high["bler"] <= low["bler"])
        metrics["sionna_high_snr_bler"] = high["bler"]
        metrics["sionna_low_snr_bler"] = low["bler"]
        store.add("P1B", "sionna_crosscheck", seed, "awgn", "sionna_high_snr_bler",
                  high["bler"], "", "PHY_VALIDATED", digest)
    except Exception as exc:  # pragma: no cover - depends on optional package
        checks["sionna_crosscheck_executed"] = False
        write_json(out_dir / "sionna_crosscheck_error.json", {"error": repr(exc)})
        metrics["sionna_error"] = repr(exc)

    checks["nr_grid_audit_written"] = (out_dir / "nr_grid_audit.json").exists()
    checks["data_collected"] = len(store.rows) > 0
    result = make_result("P1B", "NR grid and link-boundary audit", t0, checks, metrics,
                         reason="NR accounting audited; coded-link evidence is separate from RF/hardware.")
    if not checks.get("sionna_crosscheck_executed", False):
        result.status = "BLOCKED"
    return result
