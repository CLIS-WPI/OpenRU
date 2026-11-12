from pathlib import Path

import numpy as np

from openru_x6.config import CONFIG_DIR, load_radio, load_scenario
from openru_x6.experiments import REQUIRED_LONG_HORIZON, SUITE_REQUIRED
from openru_x6.experiments.common import load_suite
from openru_x6.experiments.p1d import _constraint_pass
from openru_x6.experiments.p1e import _first_detection
from openru_x6.phy import _sionna_uses_torch, nr_grid_audit, resource_multiplier
from openru_x6.polarization import jones_matrices
from openru_x6.rf import array_response, array_response_geometry, build_feed_map, direction_from_angles
from openru_x6.sensors import SensorFaultInjector, SensorFaultSpec
from openru_x6.traffic import generate_trace


def test_long_horizon_registry_and_scenarios_are_separate():
    suite = load_suite("long_horizon")
    assert SUITE_REQUIRED["long_horizon"] == REQUIRED_LONG_HORIZON
    for eid in REQUIRED_LONG_HORIZON:
        assert eid.lower() in suite
        path = Path(CONFIG_DIR) / "scenarios" / f"{eid}.yaml"
        assert load_scenario(path).id == eid
    # The published full/smoke membership must not silently grow P1 experiments.
    assert "P1A" not in SUITE_REQUIRED["full"]
    assert "P1A" not in SUITE_REQUIRED["smoke"]


def test_default_polarization_is_backward_compatible():
    radio = load_radio()
    assert radio.polarization.model == "simple"
    fm = build_feed_map(radio.array, radio.cell.carrier_freq_hz)
    u = direction_from_angles(np.array([10.0, -5.0]), np.array([0.0, 3.0])).reshape(-1, 3)
    geom = array_response_geometry(fm, u)
    legacy = array_response(fm, u)
    pol = np.where(fm.feed_pol == 0, 1.0 + 0j, 1j)
    assert np.allclose(legacy, geom * pol)


def test_jones_matrices_are_power_normalized_and_shape_safe():
    radio = load_radio()
    cfg = radio.polarization.model_copy(update={
        "model": "jones", "xpd_db": 10.0, "xpr_db": 20.0,
        "orientation_std_deg": 0.0, "calibration_amplitude_error_db": 0.0,
        "calibration_phase_error_deg": 0.0,
    })
    J = jones_matrices(cfg, 3, 2, 2, np.random.default_rng(7))
    assert J.shape == (3, 2, 2, 2)
    power = np.abs(J) ** 2
    assert np.allclose(power.sum(axis=(2, 3)), 2.0, atol=1e-12)
    # Lower XPD must create more cross-polar leakage than higher XPD.
    leak10 = np.mean(np.abs(J[..., 0, 1]) ** 2)
    cfg20 = cfg.model_copy(update={"xpd_db": 30.0})
    J20 = jones_matrices(cfg20, 3, 2, 2, np.random.default_rng(7))
    leak30 = np.mean(np.abs(J20[..., 0, 1]) ** 2)
    assert leak10 >= leak30


def test_sionna_api_detection_prefers_concrete_torch_classes():
    class TorchFec:
        LDPC5GEncoder = object
        ldpc = object

    class TfFec:
        ldpc = None  # type: ignore[assignment]

    class Namespace:
        fec: object

    torch_ns, tf_ns = Namespace(), Namespace()
    torch_ns.fec, tf_ns.fec = TorchFec(), TfFec()
    assert _sionna_uses_torch(torch_ns)
    assert not _sionna_uses_torch(tf_ns)


def test_nr_resource_audit_is_explicit_and_zero_safe():
    radio = load_radio()
    audit = nr_grid_audit(radio.cell)
    assert abs(audit["occupied_bandwidth_mhz"] - 98.28) < 1e-9
    assert audit["grid_utilization"] < 1.0
    assert 0.0 < audit["resource_multiplier"] <= 1.0
    resource = {"mode": "nr_grid", "n_prb": 273, "n_rb_total": 273,
                "symbols_per_slot": 14, "dl_symbols_per_slot": 11,
                "tdd_dl_fraction": 0.75, "control_overhead_fraction": 0.08,
                "dmrs_overhead_fraction": 0.083, "ssb_overhead_fraction": 0.01}
    assert resource_multiplier(dict(resource, n_prb=0)) == 0.0
    assert resource_multiplier(dict(resource, tdd_dl_fraction=0.0)) == 0.0
    assert resource_multiplier(dict(resource, dl_symbols_per_slot=0)) == 0.0
    assert resource_multiplier(dict(resource, mode="capacity_bound")) == 1.0


def test_sensor_injector_does_not_mutate_caller_data():
    rng = np.random.default_rng(1)
    tel = {"active_chains": 64, "state": "FULL_64", "per_tile": [
        {"tile": i, "gain_db_mean": 0.0, "gain_db_std": 0.1,
         "phase_error_deg_rms": 0.2, "vswr_max": 1.2, "temp_c": 30.0,
         "supply_v": 48.0, "ptp_offset_ns": 0.0, "noise_fig_db_max": 0.0,
         "fan_fail": 0} for i in range(16)]}
    before = tel["per_tile"][3]["gain_db_mean"]
    inj = SensorFaultInjector([SensorFaultSpec("biased", onset_slot=0, duration_slots=10,
                                               tile=3, feature="gain_db_mean", magnitude=5.0)])
    out = inj.step(tel, 0, rng)
    assert tel["per_tile"][3]["gain_db_mean"] == before
    assert out["per_tile"][3]["gain_db_mean"] == before + 5.0

    stale = SensorFaultInjector([SensorFaultSpec("stale", onset_slot=0, duration_slots=10,
                                                 tile=3)])
    first = stale.step(tel, 0, rng)
    second = stale.step(first, 1, rng)
    assert second == first

    missing = SensorFaultInjector([SensorFaultSpec("missing", onset_slot=0, duration_slots=2,
                                                   tile=4, feature="temp_c")])
    assert np.isnan(missing.step(tel, 0, rng)["per_tile"][4]["temp_c"])


def test_detection_and_constraint_helpers_are_explicit():
    trace = [{"slot": 1, "detected": False}, {"slot": 3, "detected": True,
                                             "suspected_fault": "pa_gain_loss", "tile": 2}]
    assert _first_detection(trace, 2, 3)["tile"] == 2
    assert _first_detection(trace, 5, 3) is None
    summary = {"deadline_miss_fraction": 0.01, "latency_p99_completed_slots": 20.0,
               "p5_user_goodput_mbps": 0.2, "energy_j": 100.0}
    assert _constraint_pass(summary, {"max_deadline_miss": 0.02,
                                      "max_p99_completed_slots": 30.0,
                                      "min_p5_goodput_mbps": 0.1,
                                      "max_energy_j": 200.0})
    assert not _constraint_pass(summary, {"max_deadline_miss": 0.001})
