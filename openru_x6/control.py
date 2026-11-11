"""Role-policy and time-scheduled hardware-control emulation.

This is a policy simulator, not a cryptographic hardware authorization system.
The caller supplies a role string; no mTLS/credential proof, anti-replay store,
permission lease or board-side secure element is modelled.  E05 evidence is
therefore policy behaviour, not a product security claim.

Commands transition through REQUESTED -> VALIDATED -> SCHEDULED -> APPLIED ->
VERIFIED, or REJECTED / FAILED / ROLLED_BACK.  FPGA timestamps are modelled at
4 ns tick resolution, but actuation completion additionally includes the RF
settling time.  Nanosecond timestamp resolution is therefore never presented as
nanosecond RF switching.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from .config import EnergyConfig, SecurityConfig
from .rf import RFHardware
from .safety import SafetySupervisor


class RFCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    command_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: str
    scope: str
    resource: str
    action: str
    params: dict[str, Any] = Field(default_factory=dict)
    issue_time_ns: int
    expiry_time_ns: int
    effective_time_ns: int
    deadline_ns: int | None = None

    def payload(self) -> dict[str, Any]:
        return self.model_dump()


RESOURCE_SCOPE = {
    "rf_chain_mask": "rf_chain_mask",
    "tile_isolation": "tile_isolation",
    "energy_state": "energy_state",
    "beam_profile": "beam_profile",
    "tx_power": "tx_power",
    "calibration": "calibration",
    "diagnostics": "diagnostics",
    "ris_profile": "ris_profile",
    "health": "query",
    "emergency": "emergency_shutdown",
}
ALLOWED_ACTIONS = {
    "rf_chain_mask": {"set_rf_chain_mask"},
    "tile_isolation": {"isolate_tile"},
    "energy_state": {"set_energy_state"},
    "beam_profile": {"set_beam_profile"},
    "tx_power": {"set_tx_power"},
    "calibration": {"start_calibration"},
    "diagnostics": {"run_diagnostics"},
    "ris_profile": {"set_ris_profile"},
    "health": {"query_health"},
    "emergency": {"emergency_shutdown"},
}


@dataclass
class CommandRecord:
    command: RFCommand
    state: str = "REQUESTED"
    reason: str = ""
    created_ns: int = 0
    applied_at_ns: int | None = None
    completion_ns: int | None = None
    timing_violation: bool = False
    readback: Any = None
    idempotent: bool = False
    executed: bool = False
    history: list[tuple[str, int]] = field(default_factory=list)

    def set_state(self, state: str, now_ns: int, reason: str = "") -> None:
        self.state = state
        self.reason = reason or self.reason
        self.history.append((state, now_ns))

    @property
    def committed(self) -> bool:
        """True only after readback verification, not after actuation alone."""
        return self.state == "VERIFIED"

    def as_dict(self) -> dict[str, Any]:
        return {
            "command_id": self.command.command_id,
            "correlation_id": self.command.correlation_id,
            "role": self.command.role,
            "resource": self.command.resource,
            "action": self.command.action,
            "state": self.state,
            "reason": self.reason,
            "created_ns": self.created_ns,
            "effective_time_ns": self.command.effective_time_ns,
            "applied_at_ns": self.applied_at_ns,
            "completion_ns": self.completion_ns,
            "timing_violation": self.timing_violation,
            "executed": self.executed,
            "committed": self.committed,
            "idempotent": self.idempotent,
            "readback": self.readback,
            "history": self.history,
        }


class ControlPlane:
    def __init__(self, cfg: SecurityConfig, energy_cfg: EnergyConfig, hw: RFHardware,
                 safety: SafetySupervisor, energy_mgr: Any,
                 diagnostics: Callable[[], dict[str, Any]] | None = None,
                 ris: Any | None = None, secret: str | None = None,
                 start_ns: int = 0) -> None:
        self.cfg = cfg
        self.energy_cfg = energy_cfg
        self.hw = hw
        self.safety = safety
        self.energy_mgr = energy_mgr
        self.diagnostics = diagnostics
        self.ris = ris
        self._now_ns = int(start_ns)
        # No fixed repository secret.  The audit HMAC key is supplied by the
        # environment or generated per process; real deployment still needs
        # managed keys, authenticated issuers and board-MCU protection.
        self._secret = (secret or os.environ.get("OPENRU_AUDIT_SECRET")
                        or secrets.token_hex(32)).encode()
        self.records: dict[str, CommandRecord] = {}
        self.pending: list[str] = []
        self.audit: list[dict[str, Any]] = []
        self._prev_mac = "0" * 64
        self.degraded = False
        self.crashes = 0
        self.beam_profile: dict[str, Any] = {}
        self.tx_power_dbm = (hw.tx_power_limit_dbm
                             if hw.tx_power_limit_dbm is not None else float("nan"))
        self.tick_ns = int(cfg.clock.get("fpga_tick_ns", 4.0))
        self.settling_ns = int(float(cfg.commands.get("settling_time_us", 12.0)) * 1000)
        self.max_future_ns = int(float(cfg.commands.get("max_future_s", 0.02)) * 1e9)
        self.default_ttl_ns = int(float(cfg.commands.get("default_ttl_s", 0.05)) * 1e9)
        self.duplicate_window_ns = int(float(cfg.commands.get("duplicate_window_s", 2.0)) * 1e9)

    # ---------------------------------------------------------------- clock
    def now_ns(self) -> int:
        return self._now_ns

    def advance_to(self, ns: int) -> None:
        self._now_ns = max(self._now_ns, int(ns))

    # ---------------------------------------------------------------- audit
    def _audit(self, kind: str, payload: dict[str, Any]) -> None:
        body = {"seq": len(self.audit), "kind": kind, "utc_ns": self._now_ns,
                "payload": payload, "prev": self._prev_mac}
        blob = json.dumps(body, sort_keys=True, default=str).encode()
        mac = hmac.new(self._secret, blob, hashlib.sha256).hexdigest()
        body["mac"] = mac
        self._prev_mac = mac
        self.audit.append(body)

    def verify_audit(self) -> bool:
        prev = "0" * 64
        for e in self.audit:
            mac = e.pop("mac")
            body = {k: v for k, v in e.items()}
            body["prev"] = prev
            blob = json.dumps(body, sort_keys=True, default=str).encode()
            if hmac.new(self._secret, blob, hashlib.sha256).hexdigest() != mac:
                e["mac"] = mac
                return False
            e["mac"] = mac
            prev = mac
        return True

    # ------------------------------------------------------------- lifecycle
    def _auth(self, cmd: RFCommand) -> tuple[bool, str]:
        role = self.cfg.roles.get(cmd.role)
        if role is None:
            return False, "unknown_role"
        scope = RESOURCE_SCOPE.get(cmd.resource)
        if scope is None:
            return False, "unknown_resource"
        if scope not in role.scopes:
            return False, "role_scope_denied"
        if cmd.scope != scope:
            return False, "scope_resource_mismatch"
        if cmd.action not in ALLOWED_ACTIONS[cmd.resource]:
            return False, "action_not_allowed"
        return True, ""

    def submit(self, cmd: RFCommand, ctx: dict[str, Any] | None = None) -> CommandRecord:
        ctx = ctx or {}
        now = self._now_ns
        self._audit("submit", {"command": cmd.payload(), "ctx": ctx})
        # Idempotency / replay
        if cmd.command_id in self.records:
            prior = self.records[cmd.command_id]
            if prior.command.payload() == cmd.payload():
                prior.idempotent = True
                self._audit("idempotent_replay", {"command_id": cmd.command_id})
                return prior
            rec = CommandRecord(cmd, created_ns=now)
            rec.set_state("REJECTED", now, "command_id_reuse_with_different_payload")
            self.records[cmd.command_id] = rec
            self._audit("reject", {"command_id": cmd.command_id, "reason": rec.reason})
            return rec
        rec = CommandRecord(cmd, created_ns=now)
        self.records[cmd.command_id] = rec

        # Emergency fast path: independent of normal lockout and degraded control.
        if cmd.resource == "emergency":
            ok, why = self._auth(cmd)
            if not ok:
                rec.set_state("REJECTED", now, why)
                self._audit("reject", {"command_id": cmd.command_id, "reason": why})
                return rec
            rec.set_state("VALIDATED", now)
            rec.set_state("SCHEDULED", now)
            self._apply(rec, now, {"emergency": True})
            self._audit("emergency", {"command_id": cmd.command_id, "result": rec.readback})
            return rec

        if self.degraded:
            rec.set_state("REJECTED", now, "control_degraded")
            self._audit("reject", {"command_id": cmd.command_id, "reason": rec.reason})
            return rec
        ok, why = self._auth(cmd)
        if not ok:
            rec.set_state("REJECTED", now, why)
            self._audit("reject", {"command_id": cmd.command_id, "reason": why})
            return rec
        # Clock sanity and expiry
        if cmd.effective_time_ns % self.tick_ns != 0:
            rec.set_state("REJECTED", now, "effective_time_not_on_4ns_tick")
            self._audit("reject", {"command_id": cmd.command_id, "reason": rec.reason})
            return rec
        if cmd.issue_time_ns > now + self.max_future_ns or now - cmd.issue_time_ns > self.duplicate_window_ns:
            rec.set_state("REJECTED", now, "stale_or_future_clock")
            self._audit("reject", {"command_id": cmd.command_id, "reason": rec.reason})
            return rec
        if now >= cmd.expiry_time_ns:
            rec.set_state("REJECTED", now, "expired")
            self._audit("reject", {"command_id": cmd.command_id, "reason": rec.reason})
            return rec
        if cmd.effective_time_ns < now:
            rec.set_state("REJECTED", now, "effective_time_in_past")
            self._audit("reject", {"command_id": cmd.command_id, "reason": rec.reason})
            return rec
        if cmd.effective_time_ns > now + self.max_future_ns:
            rec.set_state("REJECTED", now, "effective_time_too_far_future")
            self._audit("reject", {"command_id": cmd.command_id, "reason": rec.reason})
            return rec
        rec.set_state("VALIDATED", now)
        allowed, reason = self.safety.veto(cmd.resource, cmd.action, cmd.params, ctx)
        if not allowed:
            rec.set_state("REJECTED", now, f"safety_veto:{reason}")
            self._audit("reject", {"command_id": cmd.command_id, "reason": rec.reason})
            return rec
        # Conflict: another pending command on the same resource
        for pid in self.pending:
            other = self.records.get(pid)
            if other and other.command.resource == cmd.resource and other.state == "SCHEDULED":
                rec.set_state("REJECTED", now, "conflicting_pending_command")
                self._audit("reject", {"command_id": cmd.command_id, "reason": rec.reason})
                return rec
        rec.set_state("SCHEDULED", now)
        rec._ctx = ctx  # type: ignore[attr-defined]
        self.pending.append(cmd.command_id)
        self._audit("scheduled", {"command_id": cmd.command_id, "apply_at_ns": cmd.effective_time_ns})
        return rec

    def tick(self, now_ns: int | None = None) -> list[CommandRecord]:
        if now_ns is not None:
            self.advance_to(now_ns)
        applied: list[CommandRecord] = []
        for cid in list(self.pending):
            rec = self.records[cid]
            if rec.command.effective_time_ns > self._now_ns:
                continue
            self._apply(rec, self._now_ns, getattr(rec, "_ctx", {}))
            self.pending.remove(cid)
            applied.append(rec)
        return applied

    def _snapshot(self) -> dict[str, Any]:
        return {
            "chain_mask": self.hw.chain_enabled.copy(),
            "tile_mask": self.hw.tile_enabled.copy(),
            "tile_isolated": self.hw.tile_isolated.copy(),
            "gains": self.hw.chain_gain_db.copy(),
            "phases": self.hw.chain_phase_deg.copy(),
            "tx_power_limit_dbm": self.hw.tx_power_limit_dbm,
            "tx_power_dbm": self.tx_power_dbm,
            "energy_state": self.energy_mgr.state,
        }

    def _restore(self, snap: dict[str, Any]) -> None:
        self.hw.chain_enabled = snap["chain_mask"].copy()
        self.hw.tile_enabled = snap["tile_mask"].copy()
        self.hw.tile_isolated = snap["tile_isolated"].copy()
        self.hw.chain_gain_db = snap["gains"].copy()
        self.hw.chain_phase_deg = snap["phases"].copy()
        self.hw.tx_power_limit_dbm = snap["tx_power_limit_dbm"]
        self.tx_power_dbm = snap["tx_power_dbm"]
        self.energy_mgr.state = snap["energy_state"]

    def _apply(self, rec: CommandRecord, now: int, ctx: dict[str, Any]) -> None:
        cmd = rec.command
        if self._now_ns < cmd.effective_time_ns:
            self._now_ns = cmd.effective_time_ns
        apply_ns = max(now, cmd.effective_time_ns)
        rec.applied_at_ns = apply_ns
        rec.completion_ns = apply_ns + self.settling_ns
        if cmd.deadline_ns is not None and rec.completion_ns > cmd.deadline_ns:
            rec.timing_violation = True
            self._audit("timing_violation", {"command_id": cmd.command_id,
                                             "completion_ns": rec.completion_ns,
                                             "deadline_ns": cmd.deadline_ns})
        snap = self._snapshot()
        try:
            rb = self._actuate(cmd, ctx)
            rec.readback = rb
            rec.executed = True
            rec.set_state("APPLIED", apply_ns)
            if self._readback_matches(cmd, rb):
                rec.set_state("VERIFIED", rec.completion_ns)
            else:
                if self.cfg.rollback_on_readback_mismatch:
                    self._restore(snap)
                    rec.set_state("ROLLED_BACK", rec.completion_ns, "readback_mismatch")
                else:
                    rec.set_state("FAILED", rec.completion_ns, "readback_mismatch")
        except Exception as exc:  # noqa: BLE001
            self._restore(snap)
            rec.set_state("FAILED", apply_ns, f"{type(exc).__name__}:{exc}")
        self._audit("result", {"command_id": cmd.command_id, "state": rec.state,
                               "reason": rec.reason, "readback": rec.readback})

    def _actuate(self, cmd: RFCommand, ctx: dict[str, Any]) -> Any:
        p = cmd.params
        if cmd.resource == "rf_chain_mask":
            mask = np.asarray(p["chain_mask"], dtype=bool)
            if mask.size != self.hw.fm.n_chains:
                raise ValueError("bad chain mask length")
            self.hw.set_chain_mask(mask)
            return {"chain_mask": self.hw.chain_enabled.tolist()}
        if cmd.resource == "tile_isolation":
            tile = int(p["tile"])
            if tile < 0 or tile >= self.hw.cfg.n_tiles:
                raise ValueError("bad tile index")
            self.hw.isolate_tile(tile)
            return {"tile": tile, "tile_isolated": bool(self.hw.tile_isolated[tile]),
                    "chain_mask": self.hw.chain_enabled.tolist()}
        if cmd.resource == "energy_state":
            state = str(p["state"])
            ok = self.energy_mgr.request(state, self._now_ns / 1e9, float(ctx.get("load_fraction", 0.0)))
            if not ok:
                raise RuntimeError("energy_transition_refused_dwell_or_rule")
            return {"state": self.energy_mgr.state}
        if cmd.resource == "beam_profile":
            self.beam_profile = dict(p)
            return {"beam_profile": self.beam_profile}
        if cmd.resource == "tx_power":
            # The command must change the cap consumed by the PHY model, not
            # only a bookkeeping field.  Readback reports the effective cap.
            self.tx_power_dbm = float(p["power_dbm"])
            self.hw.tx_power_limit_dbm = self.tx_power_dbm
            return {"tx_power_dbm": self.tx_power_dbm,
                    "tx_power_limit_dbm": self.hw.tx_power_limit_dbm}
        if cmd.resource == "calibration":
            if p.get("reset_ptp"):
                self.hw.resync_ptp(int(p.get("tile", 0)))
                return {"ptp_reset": True, "tile": int(p.get("tile", 0))}
            self.hw.recalibrate(np.random.default_rng(int(p.get("seed", 0))), float(p.get("residual_deg", 2.0)))
            return {"calibration_epoch": self.hw.calibration_epoch}
        if cmd.resource == "diagnostics":
            result = self.diagnostics() if self.diagnostics else {"status": "unavailable"}
            return result
        if cmd.resource == "ris_profile":
            if self.ris is not None:
                self.ris.set_profile(p)
            return {"ris_profile": p}
        if cmd.resource == "health":
            return self.hw.telemetry()
        if cmd.resource == "emergency":
            return self.safety.emergency_shutdown(self.hw)
        raise ValueError("unhandled resource")

    def _readback_matches(self, cmd: RFCommand, rb: Any) -> bool:
        if cmd.resource == "rf_chain_mask":
            req = np.asarray(cmd.params["chain_mask"], dtype=bool)
            return np.array_equal(np.asarray(rb["chain_mask"], dtype=bool), req)
        if cmd.resource == "tile_isolation":
            return bool(rb.get("tile_isolated"))
        if cmd.resource == "energy_state":
            return rb.get("state") == cmd.params["state"] or self.energy_mgr.state == cmd.params["state"]
        if cmd.resource == "tx_power":
            return (abs(rb["tx_power_dbm"] - float(cmd.params["power_dbm"])) < 1e-9 and
                    abs(float(rb["tx_power_limit_dbm"]) -
                        float(cmd.params["power_dbm"])) < 1e-9)
        if cmd.resource == "calibration":
            if cmd.params.get("reset_ptp"):
                return bool(rb.get("ptp_reset"))
            return rb.get("calibration_epoch", 0) >= 1
        return True

    # ------------------------------------------------------------- failures
    def crash(self) -> None:
        self.crashes += 1
        self.degraded = True
        for cid in list(self.pending):
            rec = self.records[cid]
            rec.set_state("FAILED", self._now_ns, "control_service_crash")
        self.pending.clear()
        self._audit("crash", {"crashes": self.crashes})

    def recover(self) -> None:
        self.degraded = False
        self._audit("recover", {"crashes": self.crashes})

    def summary(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for r in self.records.values():
            counts[r.state] = counts.get(r.state, 0) + 1
        return {
            "commands": len(self.records),
            "by_state": counts,
            "executed": sum(1 for r in self.records.values() if r.executed),
            "committed": sum(1 for r in self.records.values() if r.committed),
            "rolled_back": counts.get("ROLLED_BACK", 0),
            "failed": counts.get("FAILED", 0),
            "timing_violations": sum(1 for r in self.records.values() if r.timing_violation),
            "audit_valid": self.verify_audit(),
            "emergency_latched": self.safety.emergency_latched,
            "bypass_attempts": self.safety.bypass_attempts,
        }
