"""End-to-end closed-loop integration experiment.

Signal -> geometry -> channel -> scheduler -> hybrid beamforming -> traffic ->
telemetry -> energy/fault decision -> validated command -> timed actuation ->
recomputed service, with independent safety vetoes.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd

from ..beamforming import evaluate_mimo
from ..config import config_digest
from ..control import RESOURCE_SCOPE, ControlPlane, RFCommand
from ..diagnostics import RecoveryPlanner, StatisticalDetector
from ..energy import EnergyManager, ThermalModel, power_breakdown, required_state_for_load
from ..engine import mask_for_chains
from ..faults import FaultInjector, FaultSpec
from ..rf import RFHardware, build_feed_map
from ..safety import SafetySupervisor
from ..scheduler import Scheduler, channel_quality
from ..traffic import generate_trace
from .common import make_context, make_result, params_for, seeds_for


def _cmd(role: str, resource: str, action: str, params: dict, now: int, eff: int,
         deadline: int | None = None) -> RFCommand:
    return RFCommand(role=role, scope=RESOURCE_SCOPE[resource], resource=resource,
                     action=action, params=params, issue_time_ns=now,
                     expiry_time_ns=now + 50_000_000, effective_time_ns=eff,
                     deadline_ns=deadline)


def run(radio, energy, security, suite, out_dir: Path, store) -> object:
    t0 = time.time()
    p = params_for("INTEGRATION", suite)
    seeds = seeds_for(suite, "INTEGRATION")
    n_slots = int(p.get("slots", 60))
    n_users = int(p.get("users", 16))
    digest = config_digest(radio, energy, security, suite)
    dt = radio.cell.slot_duration_s
    slot_ns = int(round(dt * 1e9))
    fm = build_feed_map(radio.array, radio.cell.carrier_freq_hz)
    checks: dict[str, bool] = {}
    metrics: dict[str, object] = {}
    trace_rows: list[dict] = []
    resource = {
        "mode": radio.cell.resource_mode, "n_prb": radio.cell.n_prb,
        "n_rb_total": radio.cell.n_prb,
        "symbols_per_slot": radio.cell.symbols_per_slot,
        "dl_symbols_per_slot": radio.cell.dl_symbols_per_slot,
        "tdd_dl_fraction": radio.cell.tdd_dl_fraction,
        "control_overhead_fraction": radio.cell.control_overhead_fraction,
        "dmrs_overhead_fraction": radio.cell.dmrs_overhead_fraction,
        "ssb_overhead_fraction": radio.cell.ssb_overhead_fraction,
    }

    detector = StatisticalDetector(z_threshold=4.0)
    cal = []
    for cseed in (9001, 9002):
        ctx = make_context(radio, seed=cseed, n_users=n_users, n_slots=30,
                           channel_update_slots=10, saturate=True)
        hw = RFHardware(radio.array, fm, telemetry_seed=(cseed * 1_000_003) ^ 0xCA11B8A7)
        thermal = ThermalModel(energy)
        hw.tile_temp_c[:] = thermal.temp_c
        for slot in range(30):
            snap = ctx.snapshot(slot)
            hw.set_chain_mask(mask_for_chains(64))
            tel = hw.telemetry()
            cal.append(tel)
            thermal.update(power_breakdown(energy, "FULL_64", 20.0)["dissipation_w"], dt)
            hw.tile_temp_c[:] = thermal.temp_c
    detector.fit(cal, 9001)
    checks["detector_calibrated"] = detector.calibrated

    for seed in seeds:
        trace = generate_trace(n_users, n_slots, dt, 120.0, 0.5, 2.0, 40,
                               np.random.default_rng(seed + 12000))
        ctx = make_context(radio, seed=seed, n_users=n_users, n_slots=n_slots,
                           channel_update_slots=4, trace=trace)
        hw = RFHardware(radio.array, fm, telemetry_seed=(seed * 1_000_003) ^ 0xE2E5EED)
        thermal = ThermalModel(energy)
        hw.tile_temp_c[:] = thermal.temp_c.copy()
        emgr = EnergyManager(energy, sole_coverage_cell=True)
        safety = SafetySupervisor(security, energy)
        ctrl = ControlPlane(security, energy, hw, safety, emgr, start_ns=0)
        injector = FaultInjector(hw, thermal, np.random.default_rng(seed + 77))
        injector.inject(FaultSpec("pa_gain_loss", onset_slot=12, duration_slots=18,
                                  tile=3, magnitude=8.0))
        planner = RecoveryPlanner()
        queue = trace.replay()
        sched = Scheduler("pf", max_users=min(radio.mimo.max_layers, 16))
        isolated: set[int] = set()
        detected_at = None
        isolated_at = None
        unauthorized_ok = 0
        unsafe_ok = 0
        emergency_ok = 0
        energy_cmd_ok = 0
        energy_cmd_states: list[str] = []
        pre_rates, fault_rates, post_rates = [], [], []
        pre_qos, post_qos = 0.0, 1.0
        delivered_bits = 0.0
        active_fault = 0

        def apply_mask(desired: np.ndarray, slot: int, load_obs: float,
                       fail_safe: bool = False) -> bool:
            desired = np.asarray(desired, dtype=bool)
            if np.array_equal(desired, hw.chain_enabled):
                return True
            if fail_safe:
                hw.set_chain_mask(desired)
                hw.tile_enabled[:] = False
                hw.protection_latched = True
                return True
            now = slot * slot_ns
            ctrl.advance_to(now)
            c = _cmd("rf_operator", "rf_chain_mask", "set_rf_chain_mask",
                     {"chain_mask": desired.tolist()}, now, now)
            rec = ctrl.submit(c, {"sole_coverage": True, "load_fraction": load_obs})
            if rec.state == "SCHEDULED":
                ctrl.tick(now)
            return bool(rec.committed)

        for slot in range(n_slots):
            ctrl.advance_to(slot * slot_ns)
            ctrl.tick()
            # physics
            injector.step(slot, dt)
            active_fault = int(sum(1 for s in injector.states if s.active))
            queue.step_arrivals()
            backlog = queue.backlog
            peak_bits = (min(radio.mimo.max_layers, 16) * 7.4 * 0.88 *
                         radio.cell.bandwidth_hz * 0.5 * dt)
            load_obs = float(np.clip(backlog.sum() / max(peak_bits, 1.0), 0.0, 1.0))
            # The integration test keeps FULL_64 so that isolating one faulty tile
            # still satisfies the safety minimum of 8 active chains. Energy-state
            # optimisation is validated independently in E02.
            # ensure mask reflects energy state and isolated tiles
            n_eff = emgr.effective_chains()
            desired = mask_for_chains(n_eff)
            for t in isolated:
                desired[fm.chain_tile == t] = False
            fail_safe = bool(safety.emergency_latched or thermal.tripped or hw.protection_latched)
            if fail_safe:
                desired[:] = False
                hw.protection_latched = True
            apply_mask(desired, slot, load_obs, fail_safe=fail_safe)
            # attacks / safety probes
            if slot == 5:
                c = _cmd("xapp", "rf_chain_mask", "set_rf_chain_mask",
                         {"chain_mask": np.zeros(fm.n_chains, dtype=bool).tolist()},
                         ctrl.now_ns(), ctrl.now_ns() + slot_ns)
                unauthorized_ok += int(ctrl.submit(c, {"sole_coverage": True}).executed)
            if slot == 6:
                c = _cmd("energy_manager", "energy_state", "set_energy_state",
                         {"state": "SLEEP_0"}, ctrl.now_ns(), ctrl.now_ns() + slot_ns)
                unsafe_ok += int(ctrl.submit(c, {"sole_coverage": True,
                                                "load_fraction": load_obs}).executed)
            if slot == 28:
                ctrl.crash()
            if slot == 32:
                ctrl.recover()
            if slot == 42:
                c = _cmd("energy_manager", "energy_state", "set_energy_state",
                         {"state": "BALANCED_32"}, ctrl.now_ns(), ctrl.now_ns())
                rec = ctrl.submit(c, {"sole_coverage": True, "load_fraction": load_obs})
                if rec.state == "SCHEDULED":
                    ctrl.tick(ctrl.now_ns())
                energy_cmd_ok += int(rec.committed)
                energy_cmd_states.append(emgr.state)
            if slot == 50:
                c = _cmd("safety_officer", "emergency", "emergency_shutdown", {},
                         ctrl.now_ns(), ctrl.now_ns() + 4)
                rec = ctrl.submit(c, {"sole_coverage": False})
                emergency_ok += int(rec.committed and safety.emergency_latched)
                break
            # service
            snap = ctx.snapshot(slot)
            Q = channel_quality(snap.H)
            sched.max_users = max(1, min(radio.mimo.max_layers, hw.active_chains()))
            users = sched.select(backlog, Q, queue.age)
            est_dir = snap.directions_az_el[users] if users.size else np.zeros((0, 2))
            noise = snap.noise_power_w * 10 ** (float(np.max(hw.chain_noise_fig_db[hw.chain_enabled])) / 10.0) \
                if np.any(hw.chain_enabled) else snap.noise_power_w
            res = evaluate_mimo(snap.H, hw, users, est_dir, radio.mimo,
                                np.random.default_rng(seed + slot), noise,
                                radio.cell.bandwidth_hz, resource=resource)
            bits = res.rate_bps * dt if users.size else np.zeros(0)
            full = np.zeros(n_users)
            if users.size:
                full[users] = bits
            served = queue.serve(full)
            delivered_bits += float(served.sum())
            tx_w = res.tx_power_w
            pb = emgr.step(dt, tx_w, load_obs, fan_ok=thermal.fan_ok,
                           active_chains=hw.active_chains(),
                           active_tiles=int(np.sum(hw.tile_enabled)))
            temp = thermal.update(pb["dissipation_w"], dt)
            hw.tile_temp_c[:] = temp
            # telemetry + diagnosis
            tel = hw.telemetry()
            diag = detector.detect(tel)
            if diag.detected and detected_at is None:
                detected_at = slot
            if diag.detected and diag.tile >= 0 and diag.tile not in isolated:
                plan = planner.plan(diag, tel, {"load_fraction": load_obs})
                for act in plan:
                    if act.action == "isolate_tile" and act.tile >= 0:
                        chains = int(np.sum(fm.chain_tile == act.tile))
                        c = _cmd("rf_operator", "tile_isolation", "isolate_tile",
                                 {"tile": int(act.tile)}, ctrl.now_ns(),
                                 ctrl.now_ns())
                        rec = ctrl.submit(c, {"sole_coverage": True,
                                              "active_chains_after": hw.active_chains() - chains,
                                              "isolated_tiles_after": int(hw.tile_isolated.sum()) + 1})
                        if rec.state == "SCHEDULED":
                            ctrl.tick(ctrl.now_ns())
                        if rec.committed:
                            isolated.add(act.tile)
                            if isolated_at is None:
                                isolated_at = slot
                        break
            goodput = float(served.sum()) / dt / 1e6
            if slot < 12:
                pre_rates.append(goodput)
            elif slot < 30:
                fault_rates.append(goodput)
            elif slot < 42:
                post_rates.append(goodput)
            if slot == 11:
                pre_qos = queue.qos_violation_fraction()
            if slot == 41:
                post_qos = queue.qos_violation_fraction() - pre_qos
            trace_rows.append({"seed": seed, "slot": slot, "load": load_obs,
                               "state": emgr.state, "active_chains": hw.active_chains(),
                               "users": int(users.size), "goodput_mbps": goodput,
                               "mean_sinr_db": float(np.mean(res.sinr_db)) if users.size else np.nan,
                               "fault_active": active_fault, "isolated_tiles": len(isolated),
                               "power_w": pb["total_w"], "detected": int(diag.detected),
                               "emergency": int(safety.emergency_latched)})

        audit_ok = ctrl.verify_audit()
        s = ctrl.summary()
        store.add("INTEGRATION", "closed_loop", seed, "system", "fault_detected",
                  float(detected_at is not None), "", "SIMULATED", digest)
        store.add("INTEGRATION", "closed_loop", seed, "system", "fault_isolated",
                  float(isolated_at is not None), "", "SIMULATED", digest)
        store.add("INTEGRATION", "closed_loop", seed, "system", "unauthorized_executed",
                  float(unauthorized_ok), "", "SIMULATED", digest)
        store.add("INTEGRATION", "closed_loop", seed, "system", "unsafe_sleep_executed",
                  float(unsafe_ok), "", "SIMULATED", digest)
        store.add("INTEGRATION", "closed_loop", seed, "system", "emergency_during_degraded",
                  float(emergency_ok), "", "SIMULATED", digest)
        store.add("INTEGRATION", "closed_loop", seed, "system", "audit_valid",
                  float(audit_ok), "", "SIMULATED", digest)
        store.add("INTEGRATION", "closed_loop", seed, "system", "energy_command_executed",
                  float(energy_cmd_ok), "", "SIMULATED", digest)
        store.add("INTEGRATION", "closed_loop", seed, "system", "delivered_goodput_mbps",
                  float(delivered_bits / (n_slots * dt) / 1e6), "Mbps", "SIMULATED", digest)
        store.add("INTEGRATION", "closed_loop", seed, "system", "pre_fault_goodput_mbps",
                  float(np.mean(pre_rates)) if pre_rates else float("nan"), "Mbps",
                  "SIMULATED", digest)
        store.add("INTEGRATION", "closed_loop", seed, "system", "fault_goodput_mbps",
                  float(np.mean(fault_rates)) if fault_rates else float("nan"), "Mbps",
                  "SIMULATED", digest)
        store.add("INTEGRATION", "closed_loop", seed, "system", "post_isolation_goodput_mbps",
                  float(np.mean(post_rates)) if post_rates else float("nan"), "Mbps",
                  "SIMULATED", digest)
        metrics.setdefault("seeds", {})[seed] = {
            "detected_at": detected_at, "isolated_at": isolated_at,
            "unauthorized_executed": unauthorized_ok, "unsafe_sleep_executed": unsafe_ok,
            "emergency_during_degraded": emergency_ok, "audit_valid": audit_ok,
            "energy_command_executed": energy_cmd_ok, "energy_command_states": energy_cmd_states,
            "commands": s["commands"], "by_state": s["by_state"],
        }
        checks[f"seed{seed}_detected"] = detected_at is not None
        checks[f"seed{seed}_isolated"] = isolated_at is not None
        checks[f"seed{seed}_no_unauthorized"] = unauthorized_ok == 0
        checks[f"seed{seed}_no_unsafe_sleep"] = unsafe_ok == 0
        checks[f"seed{seed}_emergency_degraded"] = emergency_ok == 1
        checks[f"seed{seed}_audit_valid"] = audit_ok
        checks[f"seed{seed}_energy_command_executed"] = energy_cmd_ok == 1
        if pre_rates and post_rates:
            checks[f"seed{seed}_service_recovers"] = (
                np.mean(post_rates) >= np.mean(pre_rates) * 0.5 and post_qos <= max(0.05, pre_qos))

    out_dir.mkdir(parents=True, exist_ok=True)
    if trace_rows:
        pd.DataFrame(trace_rows).to_csv(out_dir / "integration_trace.csv", index=False)
    res = make_result("INTEGRATION", "End-to-end closed loop", t0, checks, metrics)
    return res
