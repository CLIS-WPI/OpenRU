import numpy as np

from openru_x6.diagnostics import Diagnosis, SelfHealingController
from openru_x6.faults import FaultSpec
from openru_x6.rf import RFHardware
from openru_x6.traffic import TrafficQueue, TrafficTrace
from openru_x6.experiments.common import make_context, run_engine


class _AlwaysFault:
    calibrated = True

    def detect(self, telemetry):
        return Diagnosis(True, 3, "pa_gain_loss", 1.0, [], 100.0)


def test_deadline_expiry_counts_unserved_queued_bits():
    trace = TrafficTrace(np.zeros((5, 1)), np.array([1]), 1.0, 1.0, 5e-4)
    trace.arrivals_bits[0, 0] = 1000.0
    q = trace.replay()
    for _ in range(5):
        q.step_arrivals()
        q.serve(np.zeros(1))
    assert q.expired_bits == 1000.0
    assert q.qos_violation_fraction() == 1.0
    assert abs(q.conservation_error()) < 1e-6
    assert q.conservation_error() == 0.0


def test_queue_conservation_includes_overflow_drops():
    trace = TrafficTrace(np.array([[1000.0], [1000.0], [0.0]]), np.array([10]), 1.0, 1.0, 5e-4)
    q = TrafficQueue(trace, max_bits_per_user=1500.0)
    for _ in range(3):
        q.step_arrivals()
        q.serve(np.array([200.0]))
    assert q.arrived_bits == 2000.0
    assert q.dropped_bits == 300.0
    assert abs(q.arrived_bits - q.served_bits.sum() - q.dropped_bits - q.backlog.sum()) < 1e-6


def test_telemetry_noise_is_seeded_per_hardware_instance(radio, feed_map):
    h1 = RFHardware(radio.array, feed_map, telemetry_seed=101)
    h2 = RFHardware(radio.array, feed_map, telemetry_seed=202)
    t1 = h1.telemetry()["per_tile"]
    t2 = h2.telemetry()["per_tile"]
    assert any(a["gain_db_mean"] != b["gain_db_mean"] for a, b in zip(t1, t2))


def test_normal_self_healing_never_mutates_without_authorized_executor(hardware):
    ctrl = SelfHealingController(hardware, _AlwaysFault())
    before = hardware.chain_enabled.copy()
    ctrl.step(4, hardware.telemetry(), {})
    assert np.array_equal(hardware.chain_enabled, before)
    assert not hardware.tile_isolated[3]
    assert ctrl.actions_authorized == 0
    assert ctrl.unrouted_actions > 0


def test_normal_self_healing_uses_executor_and_emergency_stays_local(hardware):
    ctrl = SelfHealingController(hardware, _AlwaysFault())
    seen = []

    def executor(action, slot):
        seen.append(action.action)
        return False

    ctrl.step(4, hardware.telemetry(), {}, executor=executor)
    assert seen and hardware.active_chains() == 64
    assert ctrl.actions_vetoed > 0
    assert not hardware.tile_isolated[3]
    assert not hardware.protection_latched


def test_engine_recovery_actions_are_routed_through_control(radio, energy, security):
    ctx = make_context(radio, seed=55, n_users=8, n_slots=5,
                       channel_update_slots=5, saturate=True)
    r = run_engine(radio, energy, security, ctx, scheduler_policy="pf", energy_kind="static",
                   faults=[FaultSpec("pa_gain_loss", onset_slot=0, duration_slots=5,
                                     tile=3, magnitude=8.0)],
                   healing=True, healing_detector=_AlwaysFault())
    assert r.healing["detected"]
    assert r.healing["actions_authorized"] > 0
    assert r.healing["unrouted_actions"] == 0
