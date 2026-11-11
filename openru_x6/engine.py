"""Closed-loop simulation engine shared by the experiments."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np
import torch

from .beamforming import evaluate_mimo
from .channel import ChannelModel, ChannelRealization
from .config import EnergyConfig, RadioConfig, SecurityConfig
from .control import RESOURCE_SCOPE, ControlPlane, RFCommand
from .diagnostics import SelfHealingController, StatisticalDetector
from .energy import EnergyPolicy, ThermalModel, power_breakdown, state_chains
from .faults import FaultInjector, FaultSpec
from .metrics import jain_fairness, percentile
from .phy import resource_multiplier
from .rf import RFHardware, build_feed_map
from .safety import SafetySupervisor
from .scheduler import Scheduler, channel_quality
from .traffic import TrafficQueue, TrafficTrace


def mask_for_chains(n: int, n_tiles: int = 16, chains_per_tile: int = 4) -> np.ndarray:
    """Select ``n`` chains spread over the aperture, preserving all tiles when possible."""
    mask = np.zeros(n_tiles * chains_per_tile, dtype=bool)
    if n <= 0:
        return mask
    n = min(n, n_tiles * chains_per_tile)
    if n >= n_tiles:
        per_tile = n // n_tiles
        extra = n - per_tile * n_tiles
        for t in range(n_tiles):
            k = per_tile + (1 if t < extra else 0)
            mask[t * chains_per_tile:t * chains_per_tile + k] = True
    else:
        tiles = np.linspace(0, n_tiles - 1, n).round().astype(int)
        for t in tiles:
            mask[t * chains_per_tile] = True
    return mask


@dataclass
class SimContext:
    radio: RadioConfig
    seed: int
    n_users: int
    n_slots: int
    speed_kmh: float
    channel_update_slots: int
    trace: TrafficTrace | None
    blocked_schedule: Callable[[int], np.ndarray] | None = None
    snapshots: list[ChannelRealization] = field(default_factory=list)
    positions: np.ndarray | None = None
    velocities: np.ndarray | None = None
    channel: ChannelModel | None = None
    device: str = "cpu"
    saturate: bool = False

    @classmethod
    def build(cls, radio: RadioConfig, seed: int, n_users: int, n_slots: int,
              speed_kmh: float = 3.0, channel_update_slots: int = 20,
              trace: TrafficTrace | None = None, device: torch.device | None = None,
              blocked_schedule: Callable[[int], np.ndarray] | None = None,
              saturate: bool = False) -> "SimContext":
        device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        fm = build_feed_map(radio.array, radio.cell.carrier_freq_hz)
        ch = ChannelModel(radio, fm, device, seed)
        pos = ch.sample_positions(n_users)
        vel = ch.random_velocities(n_users, speed_kmh)
        ctx = cls(radio=radio, seed=seed, n_users=n_users, n_slots=n_slots,
                  speed_kmh=speed_kmh, channel_update_slots=channel_update_slots,
                  trace=trace, blocked_schedule=blocked_schedule,
                  positions=pos, velocities=vel, channel=ch, device=str(device),
                  saturate=saturate)
        ch.prepare(n_users, speed_kmh)
        cur = pos.copy()
        last: ChannelRealization | None = None
        for slot in range(n_slots):
            if slot % channel_update_slots == 0:
                blocked = blocked_schedule(slot) if blocked_schedule else None
                last = ch.realize(cur, slot * radio.cell.slot_duration_s, blocked=blocked,
                                  speed_kmh=speed_kmh)
            assert last is not None
            ctx.snapshots.append(last)
            cur = ch.move(cur, vel, radio.cell.slot_duration_s)
        return ctx

    def snapshot(self, slot: int) -> ChannelRealization:
        return self.snapshots[min(slot, len(self.snapshots) - 1)]


@dataclass
class RunResult:
    summary: dict[str, Any]
    slots: list[dict[str, Any]]
    per_user_bits: np.ndarray
    telemetry: list[dict[str, Any]] = field(default_factory=list)
    fault_events: list[dict[str, Any]] = field(default_factory=list)
    healing: dict[str, Any] = field(default_factory=dict)
    energy: dict[str, Any] = field(default_factory=dict)

    def as_metrics(self, experiment: str, scenario: str, seed: int, policy: str,
                   store: Any, config_digest: str = "") -> None:
        for k, v in self.summary.items():
            if isinstance(v, (int, float, bool, np.floating, np.integer)):
                store.add(experiment, scenario, seed, policy, k, float(v), "", "SIMULATED", config_digest)


class SimulationEngine:
    def __init__(self, radio: RadioConfig, energy_cfg: EnergyConfig,
                 security_cfg: SecurityConfig, ctx: SimContext) -> None:
        self.radio = radio
        self.energy_cfg = energy_cfg
        self.security_cfg = security_cfg
        self.ctx = ctx
        self.fm = build_feed_map(radio.array, radio.cell.carrier_freq_hz)
        self.device = torch.device(ctx.device)

    def run(self, scheduler_policy: str = "pf", energy_kind: str = "static",
            sole_coverage: bool = True, forced_chains: int | None = None,
            faults: list[FaultSpec] | None = None, healing: bool = False,
            healing_detector: StatisticalDetector | None = None,
            threshold_detector: Any | None = None,
            collect_telemetry: bool = True) -> RunResult:
        radio, e_cfg, ctx = self.radio, self.energy_cfg, self.ctx
        fault_sig = sum(sum(ord(ch) for ch in spec.kind) + spec.onset_slot + spec.tile
                        for spec in (faults or []))
        telemetry_seed = ((int(ctx.seed) * 1_000_003) ^ 0x5EEDBEEF ^
                          (0xA5A5 if healing else 0x1234) ^ fault_sig)
        hw = RFHardware(radio.array, self.fm, telemetry_seed=telemetry_seed)
        thermal = ThermalModel(e_cfg)
        policy = EnergyPolicy(energy_kind, e_cfg, sole_coverage)
        policy.mgr.state = "FULL_64" if forced_chains is None else _state_for_count(forced_chains)
        policy.mgr.target_state = policy.mgr.state
        safety = SafetySupervisor(self.security_cfg, e_cfg)
        ctrl = ControlPlane(self.security_cfg, e_cfg, hw, safety, policy.mgr, start_ns=0)
        slot_ns = int(round(radio.cell.slot_duration_s * 1e9))
        resource = {
            "mode": radio.cell.resource_mode,
            "n_prb": radio.cell.n_prb,
            "n_rb_total": radio.cell.n_prb,
            "symbols_per_slot": radio.cell.symbols_per_slot,
            "dl_symbols_per_slot": radio.cell.dl_symbols_per_slot,
            "tdd_dl_fraction": radio.cell.tdd_dl_fraction,
            "control_overhead_fraction": radio.cell.control_overhead_fraction,
            "dmrs_overhead_fraction": radio.cell.dmrs_overhead_fraction,
            "ssb_overhead_fraction": radio.cell.ssb_overhead_fraction,
        }
        res_factor = resource_multiplier(resource)

        def submit_cmd(resource: str, action: str, params: dict[str, Any], slot: int,
                       load_obs: float, role: str = "rf_operator",
                       extra_ctx: dict[str, Any] | None = None) -> Any:
            now = slot * slot_ns
            ctrl.advance_to(now)
            cmd = RFCommand(role=role, scope=RESOURCE_SCOPE[resource],
                            resource=resource, action=action, params=params,
                            issue_time_ns=now, expiry_time_ns=now + 50_000_000,
                            effective_time_ns=now)
            ctx_cmd = {"sole_coverage": sole_coverage and forced_chains is None,
                       "load_fraction": load_obs,
                       "max_temp_c": float(np.max(hw.tile_temp_c))}
            if extra_ctx:
                ctx_cmd.update(extra_ctx)
            rec = ctrl.submit(cmd, ctx_cmd)
            if rec.state == "SCHEDULED":
                ctrl.tick(now)
            return rec

        def apply_mask(desired: np.ndarray, slot: int, load_obs: float,
                       fail_safe: bool = False) -> bool:
            if np.array_equal(np.asarray(desired, dtype=bool), hw.chain_enabled):
                return True
            if fail_safe:
                # Independent protection path: allowed to bypass the normal
                # command/safety-veto path and mute the hardware immediately.
                hw.set_chain_mask(np.asarray(desired, dtype=bool))
                hw.tile_enabled[:] = False
                hw.protection_latched = True
                return True
            rec = submit_cmd("rf_chain_mask", "set_rf_chain_mask",
                             {"chain_mask": np.asarray(desired, dtype=bool).tolist()},
                             slot, load_obs)
            return bool(rec.committed)

        rng = np.random.default_rng(ctx.seed + 991)
        injector = FaultInjector(hw, thermal, np.random.default_rng(ctx.seed + 71))
        for spec in faults or []:
            injector.inject(spec)
        healer = None
        if healing:
            Det = healing_detector or StatisticalDetector()
            if not Det.calibrated and threshold_detector is not None:
                Det = threshold_detector
            healer = SelfHealingController(hw, Det)

        def execute_recovery(act: Any, slot: int) -> bool:
            """Execute a non-emergency recovery action through ControlPlane."""
            if act.action == "isolate_tile" and act.tile >= 0:
                chains = int(np.sum(hw.fm.chain_tile == act.tile))
                rec = submit_cmd("tile_isolation", "isolate_tile", {"tile": int(act.tile)},
                                 slot, load_obs,
                                 extra_ctx={"active_chains_after": hw.active_chains() - chains,
                                            "isolated_tiles_after": int(hw.tile_isolated.sum()) + 1})
                return bool(rec.committed)
            if act.action == "reduce_chains":
                state = str(act.params.get("state", "BALANCED_32"))
                n = int(state.split("_")[-1])
                desired = mask_for_chains(n)
                desired &= ~hw.tile_isolated[hw.fm.chain_tile]
                rec = submit_cmd("rf_chain_mask", "set_rf_chain_mask",
                                 {"chain_mask": desired.tolist()}, slot, load_obs)
                return bool(rec.committed)
            if act.action == "recalibrate":
                rec = submit_cmd("calibration", "start_calibration",
                                 {"seed": int(ctx.seed * 1_000_003 + slot),
                                  "residual_deg": float(act.params.get("residual_deg", 2.0))},
                                 slot, load_obs)
                return bool(rec.committed)
            if act.action == "resync_ptp":
                rec = submit_cmd("calibration", "start_calibration",
                                 {"reset_ptp": True, "tile": int(act.tile)}, slot, load_obs)
                return bool(rec.committed)
            if act.action == "reduce_power":
                rec = submit_cmd("tx_power", "set_tx_power",
                                 {"power_dbm": float(act.params.get("power_dbm", 40.0))},
                                 slot, load_obs)
                return bool(rec.committed)
            return False

        queue = ctx.trace.replay() if ctx.trace is not None else None
        if queue is None:
            backlog = np.full(ctx.n_users, 1e9)
        else:
            backlog = queue.backlog
        scheduler = Scheduler(scheduler_policy, max_users=min(radio.mimo.max_layers, 64))
        avg_rate = np.zeros(ctx.n_users)
        per_user_bits = np.zeros(ctx.n_users)
        served_total = 0.0
        slots: list[dict[str, Any]] = []
        telem_hist: list[dict[str, Any]] = []
        sinr_hist: list[float] = []
        bler_hist: list[float] = []
        layer_hist: list[float] = []
        power_hist: list[float] = []
        temp_hist: list[float] = []
        qos_hist: list[float] = []
        interruption_slots = 0
        prev_state = policy.mgr.state
        dt = radio.cell.slot_duration_s
        bw = radio.cell.bandwidth_hz
        energy_j = 0.0
        peak_power = 0.0
        capacity_bits = 0.0
        thermal_trip_slots = 0
        wake_blocked_slots = 0
        use_csi_delay = radio.mimo.csi_delay_slots

        for slot in range(ctx.n_slots):
            snap = ctx.snapshot(slot)
            # --- traffic -------------------------------------------------
            if queue is not None:
                queue.step_arrivals()
                backlog = queue.backlog
            active_backlog = np.flatnonzero(backlog > 0)
            if ctx.saturate:
                load_obs = 1.0
            elif queue is not None:
                # Utilisation is backlog / peak schedulable airtime, not the
                # fraction of UEs that happen to have a non-empty queue.
                peak = (min(radio.mimo.max_layers, 64) * 7.4 * 0.88 *
                        bw * res_factor * dt)
                load_obs = float(np.clip(backlog.sum() / max(peak, 1.0), 0.0, 1.0))
            else:
                load_obs = float(active_backlog.size) / max(ctx.n_users, 1)
            # --- faults (physics) ----------------------------------------
            injector.step(slot, dt)
            # --- energy decision -----------------------------------------
            if forced_chains is None:
                policy.update(load_obs, load_obs, slot * dt, thermal.throttled, dt_s=dt)
            else:
                policy.mgr.state = _state_for_count(forced_chains)
                policy.mgr.target_state = policy.mgr.state
            n_eff = policy.mgr.effective_chains()
            mask = mask_for_chains(n_eff)
            iso = hw.tile_isolated[self.fm.chain_tile]
            mask = mask & ~iso
            fail_safe = bool(thermal.tripped or hw.protection_latched)
            if fail_safe:
                # Independent hard protection: zero RF output, not just an alarm.
                mask[:] = False
                hw.protection_latched = True
                thermal_trip_slots += 1
            if not policy.mgr.service_ready():
                wake_blocked_slots += 1
            apply_mask(mask, slot, load_obs, fail_safe=fail_safe)
            if policy.mgr.pending_wake and load_obs > 0.2:
                interruption_slots += 1
            # --- scheduler -----------------------------------------------
            Q = channel_quality(snap.H)
            scheduler.max_users = max(1, min(radio.mimo.max_layers, hw.active_chains()))
            users = scheduler.select(backlog, Q, queue.age if queue is not None else None)
            # --- CSI delay / error ---------------------------------------
            delayed = ctx.snapshot(max(0, slot - use_csi_delay))
            est_dir = delayed.directions_az_el[users] if users.size else np.zeros((0, 2))
            if users.size and radio.mimo.csi_phase_error_deg > 0:
                est_dir = est_dir + rng.normal(0.0, radio.mimo.csi_phase_error_deg, est_dir.shape)
            # --- MIMO ------------------------------------------------------
            noise = snap.noise_power_w * 10 ** (float(np.max(hw.chain_noise_fig_db[hw.chain_enabled])) / 10.0) \
                if np.any(hw.chain_enabled) else snap.noise_power_w
            res = evaluate_mimo(snap.H, hw, users, est_dir, radio.mimo, rng,
                                noise_power_w=noise, bandwidth_hz=bw,
                                H_est=delayed.H if use_csi_delay > 0 else None,
                                resource=resource)
            if users.size:
                capacity_bits += float(res.capacity_bps.sum()) * dt
            # --- service ---------------------------------------------------
            bits = res.rate_bps * dt if users.size else np.zeros(0)
            if queue is not None:
                full = np.zeros(ctx.n_users)
                if users.size:
                    full[users] = bits
                served = queue.serve(full)
                per_user_bits += served
                served_total += float(served.sum())
            elif users.size:
                per_user_bits[users] += bits
                served_total += float(bits.sum())
            if users.size:
                avg_rate[users] = 0.98 * avg_rate[users] + 0.02 * res.rate_bps
                sinr_hist.extend(res.sinr_db.tolist())
                bler_hist.extend(res.bler.tolist())
                layer_hist.append(float(res.useful_layers))
            # --- power / thermal ------------------------------------------
            tx_w = res.tx_power_w
            pb = policy.step(dt, tx_w, load_obs, thermal.fan_ok,
                             active_chains=hw.active_chains(),
                             active_tiles=int(np.sum(hw.tile_enabled)))
            energy_j += pb["total_w"] * dt
            peak_power = max(peak_power, pb["total_w"])
            temp = thermal.update(pb["dissipation_w"], dt, hot_tile=None)
            hw.tile_temp_c[:] = temp
            hw.fan_ok = bool(thermal.fan_ok)
            power_hist.append(pb["total_w"])
            temp_hist.append(float(temp.max()))
            # --- telemetry / diagnostics ---------------------------------
            tel = hw.telemetry() if collect_telemetry else {}
            if collect_telemetry:
                telem_hist.append({"slot": slot, **{k: v for k, v in tel.items()
                                                    if k in ("active_chains", "state")},
                                   "per_tile": tel["per_tile"]})
            if healer is not None and collect_telemetry:
                healer.step(slot, tel, {"load_fraction": load_obs},
                            executor=execute_recovery)
            qos = queue.qos_violation_fraction() if queue is not None else 0.0
            qos_hist.append(qos)
            slots.append({
                "slot": slot, "users": int(users.size), "active_chains": hw.active_chains(),
                "energy_state": policy.mgr.state, "sum_rate_bps": float(res.rate_bps.sum()),
                "mean_sinr_db": float(np.mean(res.sinr_db)) if res.sinr_db.size else float("nan"),
                "bler": float(np.mean(res.bler)) if res.bler.size else float("nan"),
                "useful_layers": int(res.useful_layers), "tx_power_w": tx_w,
                "total_power_w": pb["total_w"], "temp_c": float(temp.max()),
                "qos_violation": qos, "load": load_obs,
                "faults_active": sum(1 for s in injector.states if s.active),
            })
            prev_state = policy.mgr.state
        duration = ctx.n_slots * dt
        goodput_total = served_total / duration
        per_user_goodput = per_user_bits / duration
        negative = [k for k, v in {
            "sum_rate": goodput_total, "energy": energy_j,
        }.items() if v < 0]
        summary = {
            "sum_goodput_mbps": goodput_total / 1e6,
            "mean_user_goodput_mbps": float(np.mean(per_user_goodput) / 1e6),
            "p5_user_goodput_mbps": percentile(per_user_goodput / 1e6, 5),
            "p50_user_goodput_mbps": percentile(per_user_goodput / 1e6, 50),
            "jain_fairness": jain_fairness(per_user_goodput),
            "mean_sinr_db": float(np.mean(sinr_hist)) if sinr_hist else float("nan"),
            "p5_sinr_db": percentile(sinr_hist, 5) if sinr_hist else float("nan"),
            "mean_bler": float(np.mean(bler_hist)) if bler_hist else float("nan"),
            "outage_fraction": float(np.mean(np.asarray(sinr_hist) < -3.0)) if sinr_hist else float("nan"),
            "mean_useful_layers": float(np.mean(layer_hist)) if layer_hist else 0.0,
            "mean_active_chains": float(np.mean([s["active_chains"] for s in slots])),
            "energy_j": energy_j,
            "mean_power_w": float(np.mean(power_hist)) if power_hist else 0.0,
            "peak_power_w": peak_power,
            "energy_per_bit_nj": (energy_j / served_total * 1e9) if served_total > 0 else float("nan"),
            "spectral_efficiency_bps_hz": goodput_total / bw,
            "capacity_bound_mbps": capacity_bits / duration / 1e6,
            "resource_multiplier": float(res_factor),
            "thermal_trip_slots": thermal_trip_slots,
            "wake_blocked_slots": wake_blocked_slots,
            "protection_latched": bool(hw.protection_latched),
            "qos_violation_fraction": (queue.qos_violation_fraction() if queue is not None
                                       else (float(np.mean(qos_hist)) if qos_hist else 0.0)),
            "qos_expired_fraction": queue.expired_fraction() if queue is not None else 0.0,
            "qos_dropped_fraction": queue.dropped_fraction() if queue is not None else 0.0,
            "queue_conservation_error": queue.conservation_error() if queue is not None else 0.0,
            "mean_hol_delay_slots": queue.mean_delay_slots() if queue is not None else 0.0,
            "latency_p50_slots": queue.latency_percentile(0.50) if queue is not None else float("nan"),
            "latency_p95_slots": queue.latency_percentile(0.95) if queue is not None else float("nan"),
            "latency_p99_slots": queue.latency_percentile(0.99) if queue is not None else float("nan"),
            "latency_p50_completed_slots": queue.latency_percentile(0.50) if queue is not None else float("nan"),
            "latency_p95_completed_slots": queue.latency_percentile(0.95) if queue is not None else float("nan"),
            "latency_p99_completed_slots": queue.latency_percentile(0.99) if queue is not None else float("nan"),
            "deadline_miss_fraction": queue.deadline_miss_fraction() if queue is not None else 0.0,
            "remaining_queued_fraction": queue.queued_fraction() if queue is not None else 0.0,
            "completed_service_fraction": queue.completed_fraction() if queue is not None else 0.0,
            "service_interruption_slots": interruption_slots,
            "transitions": policy.mgr.transitions,
            "oscillations": policy.mgr.oscillations,
            "illegal_sleep_attempts": policy.mgr.illegal_sleep_attempts,
            "max_temp_c": float(max(temp_hist)) if temp_hist else 0.0,
            "negative_metric_violation": bool(negative),
            "n_users": ctx.n_users,
            "n_slots": ctx.n_slots,
        }
        healing_summary = {}
        if healer is not None:
            healing_summary = {
                "detected": healer.detection_slot is not None,
                "detection_slot": healer.detection_slot,
                "isolation_slot": healer.isolation_slot,
                "localized_tile": healer.localized_tile,
                "diagnosis": healer.diagnosis.as_dict() if healer.diagnosis else None,
                "isolated_tiles": sorted(healer.isolated),
                "detection_latency_slots": max(0, healer.detection_slot - min(
                    (s.spec.onset_slot for s in injector.states), default=0))
                if healer.detection_slot is not None else None,
                "recovery_latency_slots": (healer.isolation_slot - healer.detection_slot)
                if healer.isolation_slot is not None and healer.detection_slot is not None else None,
                "actions_attempted": healer.actions_attempted,
                "actions_authorized": healer.actions_authorized,
                "actions_vetoed": healer.actions_vetoed,
                "unrouted_actions": healer.unrouted_actions,
                "control_commands": ctrl.summary()["commands"],
                "control_by_state": ctrl.summary()["by_state"],
                "control_executed": ctrl.summary()["executed"],
                "control_bypass_attempts": ctrl.summary()["bypass_attempts"],
            }
        energy_summary = {
            "transitions": policy.mgr.transitions,
            "state_counts": policy.mgr.state_counts,
            "illegal_sleep_attempts": policy.mgr.illegal_sleep_attempts,
            "oscillations": policy.mgr.oscillations,
        }
        fault_events = [{"kind": s.spec.kind, "tile": s.spec.tile, "onset": s.spec.onset_slot,
                         "active_slots": int(s.applied_slots)} for s in injector.states]
        return RunResult(summary=summary, slots=slots, per_user_bits=per_user_bits,
                         telemetry=telem_hist, fault_events=fault_events,
                         healing=healing_summary, energy=energy_summary)


def _state_for_count(n: int) -> str:
    for name, chains in (("FULL_64", 64), ("BALANCED_32", 32), ("ECO_16", 16), ("COVERAGE_8", 8)):
        if n >= chains:
            return name
    return "COVERAGE_8"
