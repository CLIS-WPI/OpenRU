"""E05: role-policy command validation and fail-safe behaviour.

This is not a cryptographic hardware-security test.  The caller supplies a role
string; mTLS/credential-bound identity and a board-side secure element are out of
scope and must not be inferred from zero policy violations.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import config_digest
from ..control import RESOURCE_SCOPE, ControlPlane, RFCommand
from ..energy import EnergyManager
from ..rf import RFHardware, build_feed_map
from ..safety import SafetySupervisor
from .common import make_result, params_for


def _cmd(role: str, resource: str, action: str, params: dict, now: int,
         eff_offset: int = 4000, ttl: int = 50_000_000, issue_offset: int = 0,
         deadline_offset: int | None = None) -> RFCommand:
    eff = now + eff_offset
    return RFCommand(role=role, scope=RESOURCE_SCOPE[resource], resource=resource,
                     action=action, params=params, issue_time_ns=now + issue_offset,
                     expiry_time_ns=now + ttl, effective_time_ns=eff,
                     deadline_ns=(eff + deadline_offset) if deadline_offset is not None else None)


def run(radio, energy, security, suite, out_dir: Path, store) -> object:
    t0 = time.time()
    p = params_for("E05", suite)
    trials = int(p.get("command_trials", 10))
    digest = config_digest(radio, energy, security, suite)
    fm = build_feed_map(radio.array, radio.cell.carrier_freq_hz)
    rows = []
    agg = {"valid_executed": 0, "unauthorized_executed": 0, "unsafe_sleep_applied": 0,
           "conflict_rejected": 0, "idempotent_single": 0, "emergency_degraded": 0,
           "deadline_detected": 0, "audit_valid": 0, "no_normal_after_crash": 0}

    for trial in range(trials):
        hw = RFHardware(radio.array, fm, telemetry_seed=(trial * 1_000_003) ^ 0xE05)
        emgr = EnergyManager(energy, sole_coverage_cell=True)
        safety = SafetySupervisor(security, energy)
        ctrl = ControlPlane(security, energy, hw, safety, emgr, start_ns=1_000_000)
        now = ctrl.now_ns()

        mask8 = np.zeros(fm.n_chains, dtype=bool)
        mask8[:8] = True
        valid = _cmd("rf_operator", "rf_chain_mask", "set_rf_chain_mask",
                     {"chain_mask": mask8.tolist()}, now)
        rec = ctrl.submit(valid, {"sole_coverage": True, "load_fraction": 0.9})
        ctrl.tick(ctrl.now_ns() + 4000)
        ok_valid = rec.executed and rec.state == "VERIFIED"
        agg["valid_executed"] += int(ok_valid)

        n_before = len(ctrl.records)
        rec_idem = ctrl.submit(valid, {"sole_coverage": True, "load_fraction": 0.9})
        same = rec_idem.idempotent and len(ctrl.records) == n_before
        agg["idempotent_single"] += int(same)

        bad = _cmd("xapp", "rf_chain_mask", "set_rf_chain_mask",
                   {"chain_mask": mask8.tolist()}, ctrl.now_ns())
        rec_bad = ctrl.submit(bad, {"sole_coverage": True})
        agg["unauthorized_executed"] += int(rec_bad.executed)

        expired = _cmd("rf_operator", "tx_power", "set_tx_power", {"power_dbm": 40.0},
                       ctrl.now_ns(), ttl=1)
        rec_exp = ctrl.submit(expired, {"sole_coverage": True})
        agg["unauthorized_executed"] += int(rec_exp.executed)

        past = _cmd("rf_operator", "tx_power", "set_tx_power", {"power_dbm": 41.0},
                    ctrl.now_ns(), eff_offset=-4)
        rec_past = ctrl.submit(past, {"sole_coverage": True})
        agg["unauthorized_executed"] += int(rec_past.executed)

        offtick = _cmd("rf_operator", "tx_power", "set_tx_power", {"power_dbm": 42.0},
                       ctrl.now_ns(), eff_offset=2)
        rec_tick = ctrl.submit(offtick, {"sole_coverage": True})
        agg["unauthorized_executed"] += int(rec_tick.executed)

        stale = _cmd("rf_operator", "tx_power", "set_tx_power", {"power_dbm": 40.0},
                     ctrl.now_ns(), issue_offset=-3_000_000_000)
        rec_stale = ctrl.submit(stale, {"sole_coverage": True})
        agg["unauthorized_executed"] += int(rec_stale.executed)

        future = _cmd("rf_operator", "tx_power", "set_tx_power", {"power_dbm": 40.0},
                      ctrl.now_ns(), issue_offset=1_000_000_000)
        rec_future = ctrl.submit(future, {"sole_coverage": True})
        agg["unauthorized_executed"] += int(rec_future.executed)

        unsafe = _cmd("energy_manager", "energy_state", "set_energy_state",
                      {"state": "SLEEP_0"}, ctrl.now_ns(), eff_offset=4000)
        rec_unsafe = ctrl.submit(unsafe, {"sole_coverage": True, "load_fraction": 0.8})
        ctrl.tick(ctrl.now_ns() + 4000)
        unsafe_applied = int(emgr.state == "SLEEP_0")
        agg["unsafe_sleep_applied"] += unsafe_applied
        agg["unauthorized_executed"] += int(rec_unsafe.executed)

        c1 = _cmd("rf_operator", "rf_chain_mask", "set_rf_chain_mask",
                  {"chain_mask": mask8.tolist()}, ctrl.now_ns(), eff_offset=8000)
        c2 = _cmd("rf_operator", "rf_chain_mask", "set_rf_chain_mask",
                  {"chain_mask": mask8.tolist()}, ctrl.now_ns(), eff_offset=12000)
        r1 = ctrl.submit(c1, {"sole_coverage": True})
        r2 = ctrl.submit(c2, {"sole_coverage": True})
        conflict_ok = (r2.state == "REJECTED" and "conflict" in r2.reason)
        agg["conflict_rejected"] += int(conflict_ok)
        ctrl.tick(ctrl.now_ns() + 8000)

        dl = _cmd("rf_operator", "tx_power", "set_tx_power", {"power_dbm": 38.0},
                  ctrl.now_ns(), eff_offset=16000, deadline_offset=1)
        rec_dl = ctrl.submit(dl, {"sole_coverage": True})
        ctrl.tick(ctrl.now_ns() + 16000)
        agg["deadline_detected"] += int(rec_dl.timing_violation)

        crash_cmd = _cmd("rf_operator", "tx_power", "set_tx_power", {"power_dbm": 39.0},
                         ctrl.now_ns(), eff_offset=24000)
        rec_crash = ctrl.submit(crash_cmd, {"sole_coverage": True})
        ctrl.crash()
        crashed_failed = rec_crash.state == "FAILED"

        after = _cmd("rf_operator", "tx_power", "set_tx_power", {"power_dbm": 39.0},
                     ctrl.now_ns(), eff_offset=4)
        rec_after = ctrl.submit(after, {"sole_coverage": True})
        agg["no_normal_after_crash"] += int(not rec_after.executed)

        bad_emg = _cmd("xapp", "emergency", "emergency_shutdown", {}, ctrl.now_ns(), eff_offset=4)
        rec_bad_emg = ctrl.submit(bad_emg, {"sole_coverage": False})
        agg["unauthorized_executed"] += int(rec_bad_emg.executed)

        emg = _cmd("safety_officer", "emergency", "emergency_shutdown", {},
                   ctrl.now_ns(), eff_offset=4)
        rec_emg = ctrl.submit(emg, {"sole_coverage": False})
        emergency_ok = rec_emg.executed and safety.emergency_latched and crashed_failed
        agg["emergency_degraded"] += int(emergency_ok)

        audit_ok = ctrl.verify_audit()
        agg["audit_valid"] += int(audit_ok)
        s = ctrl.summary()
        for k, v in s["by_state"].items():
            rows.append({"trial": trial, "metric": f"state_{k}", "value": v})
        rows.append({"trial": trial, "metric": "audit_valid", "value": int(audit_ok)})
        store.add("E05", "command_suite", trial, "security", "valid_executed", float(ok_valid),
                  "", "SIMULATED", digest)
        store.add("E05", "command_suite", trial, "security", "unauthorized_executed",
                  float(int(rec_bad.executed)), "", "SIMULATED", digest)
        store.add("E05", "command_suite", trial, "security", "unsafe_sleep_applied",
                  float(unsafe_applied), "", "SIMULATED", digest)
        store.add("E05", "command_suite", trial, "security", "emergency_during_degraded",
                  float(emergency_ok), "", "SIMULATED", digest)
        store.add("E05", "command_suite", trial, "security", "audit_valid", float(audit_ok),
                  "", "SIMULATED", digest)

    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out_dir / "e05_commands.csv", index=False)
    n = max(trials, 1)
    checks = {
        "valid_command_executed": agg["valid_executed"] == trials,
        "zero_unauthorized_executions": agg["unauthorized_executed"] == 0,
        "zero_unsafe_sleep_applications": agg["unsafe_sleep_applied"] == 0,
        "conflicts_rejected": agg["conflict_rejected"] == trials,
        "idempotent_replay_single_effect": agg["idempotent_single"] == trials,
        "emergency_works_when_control_degraded": agg["emergency_degraded"] == trials,
        "deadline_violation_detected": agg["deadline_detected"] == trials,
        "normal_commands_blocked_after_crash": agg["no_normal_after_crash"] == trials,
        "audit_chain_valid": agg["audit_valid"] == trials,
    }
    return make_result("E05", "Role-policy command validation", t0, checks,
                       {k: v / n for k, v in agg.items()})
