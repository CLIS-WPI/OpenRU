import numpy as np

from openru_x6.beamforming import evaluate_mimo
from openru_x6.control import RESOURCE_SCOPE, ControlPlane, RFCommand
from openru_x6.energy import EnergyManager
from openru_x6.experiments.common import make_context
from openru_x6.rf import RFHardware
from openru_x6.safety import SafetySupervisor
from openru_x6.traffic import TrafficTrace


def _cmd(role, resource, action, params, now, offset=4000):
    return RFCommand(role=role, scope=RESOURCE_SCOPE[resource], resource=resource,
                     action=action, params=params, issue_time_ns=now,
                     expiry_time_ns=now + 50_000_000,
                     effective_time_ns=now + offset)


def _ctrl(radio, energy, security):
    from openru_x6.rf import build_feed_map
    hw = RFHardware(radio.array, build_feed_map(radio.array, radio.cell.carrier_freq_hz),
                    telemetry_seed=7)
    emgr = EnergyManager(energy, sole_coverage_cell=True)
    ctrl = ControlPlane(security, energy, hw, SafetySupervisor(security, energy), emgr,
                        start_ns=1_000_000)
    return hw, emgr, ctrl


def test_tx_power_command_changes_effective_phy_cap(radio, energy, security):
    hw, _emgr, ctrl = _ctrl(radio, energy, security)
    ctx = make_context(radio, seed=9, n_users=8, n_slots=1,
                       channel_update_slots=1, saturate=True)
    snap = ctx.snapshot(0)
    users = np.arange(8)
    before = evaluate_mimo(snap.H, hw, users, snap.directions_az_el[users], radio.mimo,
                           np.random.default_rng(11), snap.noise_power_w,
                           radio.cell.bandwidth_hz)
    rec = ctrl.submit(_cmd("rf_operator", "tx_power", "set_tx_power",
                           {"power_dbm": 40.0}, ctrl.now_ns()))
    ctrl.tick(ctrl.now_ns() + 4000)
    assert rec.state == "VERIFIED" and rec.committed
    assert hw.tx_power_limit_dbm == 40.0
    assert abs(rec.readback["tx_power_limit_dbm"] - 40.0) < 1e-9
    after = evaluate_mimo(snap.H, hw, users, snap.directions_az_el[users], radio.mimo,
                          np.random.default_rng(11), snap.noise_power_w,
                          radio.cell.bandwidth_hz)
    assert after.tx_power_w < before.tx_power_w
    assert abs(after.tx_power_w / before.tx_power_w - 10 ** (-3.0 / 10.0)) < 0.03


def test_rejected_power_command_does_not_raise_cap(radio, energy, security):
    hw, _emgr, ctrl = _ctrl(radio, energy, security)
    ok = ctrl.submit(_cmd("rf_operator", "tx_power", "set_tx_power",
                          {"power_dbm": 40.0}, ctrl.now_ns()))
    ctrl.tick(ctrl.now_ns() + 4000)
    assert ok.committed and hw.tx_power_limit_dbm == 40.0
    bad = ctrl.submit(_cmd("xapp", "tx_power", "set_tx_power",
                           {"power_dbm": 46.0}, ctrl.now_ns()))
    ctrl.tick(ctrl.now_ns() + 4000)
    assert bad.state == "REJECTED" and not bad.executed and not bad.committed
    assert hw.tx_power_limit_dbm == 40.0


def test_rollback_is_not_reported_as_committed(radio, energy, security, monkeypatch):
    hw, _emgr, ctrl = _ctrl(radio, energy, security)
    mask = np.zeros(hw.fm.n_chains, dtype=bool)
    mask[:16] = True
    monkeypatch.setattr(ctrl, "_readback_matches", lambda cmd, rb: False)
    rec = ctrl.submit(_cmd("rf_operator", "rf_chain_mask", "set_rf_chain_mask",
                           {"chain_mask": mask.tolist()}, ctrl.now_ns()))
    ctrl.tick(ctrl.now_ns() + 4000)
    assert rec.state == "ROLLED_BACK"
    assert rec.executed and not rec.committed
    assert not rec.as_dict()["committed"]
    assert hw.active_chains() == 64


def test_failed_actuation_is_not_committed(radio, energy, security, monkeypatch):
    _hw, _emgr, ctrl = _ctrl(radio, energy, security)
    monkeypatch.setattr(ctrl, "_actuate", lambda cmd, ctx: (_ for _ in ()).throw(RuntimeError("boom")))
    rec = ctrl.submit(_cmd("rf_operator", "tx_power", "set_tx_power",
                           {"power_dbm": 40.0}, ctrl.now_ns()))
    ctrl.tick(ctrl.now_ns() + 4000)
    assert rec.state == "FAILED" and not rec.committed


def test_duplicate_verified_command_is_idempotent(radio, energy, security):
    _hw, _emgr, ctrl = _ctrl(radio, energy, security)
    cmd = _cmd("rf_operator", "tx_power", "set_tx_power", {"power_dbm": 40.0}, ctrl.now_ns())
    first = ctrl.submit(cmd)
    ctrl.tick(ctrl.now_ns() + 4000)
    second = ctrl.submit(cmd)
    assert first.committed and second.idempotent and second.committed
    assert len(ctrl.records) == 1


def test_late_service_latency_is_completion_delay_not_expiry_delay():
    trace = TrafficTrace(np.array([[100.0], [0.0], [0.0], [0.0], [0.0]]),
                         np.array([1]), 1.0, 1.0, 5e-4)
    q = trace.replay()
    for slot in range(5):
        q.step_arrivals()
        q.serve(np.array([100.0] if slot == 4 else [0.0]))
    assert q.expired_bits == 100.0
    assert q.late_served_bits == 100.0
    assert q.latency_percentile(0.99) == 4.0
    assert q.deadline_miss_fraction() == 1.0
    assert q.conservation_error() == 0.0


def test_empty_queue_latency_is_nan_and_fractions_zero():
    trace = TrafficTrace(np.zeros((3, 2)), np.array([2, 2]), 1.0, 1.0, 5e-4)
    q = trace.replay()
    for _ in range(3):
        q.step_arrivals()
        q.serve(np.zeros(2))
    assert np.isnan(q.latency_percentile(0.99))
    assert q.deadline_miss_fraction() == 0.0
    assert q.queued_fraction() == 0.0
    assert q.completed_fraction() == 0.0


def test_completion_samples_are_weighted_and_not_double_counted():
    trace = TrafficTrace(np.array([[300.0], [0.0], [0.0], [0.0]]),
                         np.array([10]), 1.0, 1.0, 5e-4)
    q = trace.replay()
    q.step_arrivals()
    q.serve(np.array([100.0]))
    q.step_arrivals()
    q.serve(np.array([0.0]))
    q.step_arrivals()
    q.serve(np.array([200.0]))
    assert q.served_bits.sum() == 300.0
    assert q.latency_percentile(0.50) == 2.0
    assert q.latency_percentile(0.99) == 2.0
    assert q.conservation_error() == 0.0


class _AlwaysFault:
    calibrated = True

    def detect(self, telemetry):
        from openru_x6.diagnostics import Diagnosis
        return Diagnosis(True, 3, "pa_gain_loss", 1.0, [], 100.0)


def test_vetoed_recovery_is_retried_until_verified(hardware):
    from openru_x6.diagnostics import SelfHealingController
    ctrl = SelfHealingController(hardware, _AlwaysFault())
    answers = iter([False, True])

    def executor(action, slot):
        if action.action == "isolate_tile":
            return next(answers, True)
        return True

    ctrl.step(4, hardware.telemetry(), {}, executor=executor)
    assert ctrl.actions_vetoed == 1
    assert 3 not in ctrl.isolated
    ctrl.step(5, hardware.telemetry(), {}, executor=executor)
    assert ctrl.actions_authorized >= 1 and 3 in ctrl.isolated
    assert ctrl.actions_attempted >= 2
