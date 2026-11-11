import numpy as np

from openru_x6.beamforming import evaluate_mimo
from openru_x6.channel import ChannelModel
from openru_x6.config import MimoConfig
from openru_x6.diagnostics import SelfHealingController, StatisticalDetector
from openru_x6.energy import EnergyManager
from openru_x6.engine import mask_for_chains
from openru_x6.phy import link_adaptation, resource_multiplier
from openru_x6.rf import RFHardware, array_response, build_feed_map, direction_from_angles


def _dirs(n):
    az = np.linspace(-55.0, 55.0, n)
    el = np.linspace(-8.0, 8.0, n)
    return direction_from_angles(az, el)


def test_every_active_chain_steers_to_its_own_direction(radio, feed_map):
    hw = RFHardware(radio.array, feed_map)
    dirs = _dirs(feed_map.n_chains)
    k = 2.0 * np.pi / feed_map.wavelength_m
    for chains in (8, 16, 32, 64):
        hw.set_chain_mask(mask_for_chains(chains))
        w = hw.analog_weights(dirs, np.zeros(feed_map.n_chains, dtype=int),
                              np.random.default_rng(4), 0.0, 0.0, 0.0, phase_bits=8)
        for c in np.flatnonzero(hw.chain_enabled):
            feeds = np.flatnonzero(feed_map.feed_chain == c)
            u = dirs[c]
            geom = k * (feed_map.feed_positions[feeds, 1] * u[1] +
                        feed_map.feed_positions[feeds, 2] * u[2])
            expected = np.exp(-1j * geom) / np.sqrt(feeds.size)
            coherent = abs(np.vdot(expected, w[feeds, c]))
            assert coherent > 0.999


def test_blockage_is_not_double_counted_in_path_loss(radio, feed_map):
    cfg = radio.model_copy(update={"channel": radio.channel.model_copy(
        update={"los_probability": 0.0, "indoor_fraction": 0.0, "shadowing_std_db": 0.0})})
    ch = ChannelModel(cfg, feed_map, "cpu", 11)
    pos = np.array([[120.0, 20.0, 1.5], [80.0, -40.0, 1.5]])
    los = np.zeros(2, dtype=bool)
    indoor = np.zeros(2, dtype=bool)
    clear = ch.pathloss_db(pos, np.zeros(2, dtype=bool), los, indoor)
    blocked = ch.pathloss_db(pos, np.ones(2, dtype=bool), los, indoor)
    assert np.allclose(clear, blocked)


def test_nr_resource_accounting_bounds_delivered_goodput(radio):
    cell = radio.cell
    resource = {
        "mode": "nr_grid", "n_prb": cell.n_prb, "n_rb_total": cell.n_prb,
        "symbols_per_slot": cell.symbols_per_slot,
        "dl_symbols_per_slot": cell.dl_symbols_per_slot,
        "tdd_dl_fraction": cell.tdd_dl_fraction,
        "control_overhead_fraction": cell.control_overhead_fraction,
        "dmrs_overhead_fraction": cell.dmrs_overhead_fraction,
        "ssb_overhead_fraction": cell.ssb_overhead_fraction,
    }
    factor = resource_multiplier(resource)
    assert 0.0 < factor < 1.0
    out = link_adaptation(np.array([20.0]), cell.bandwidth_hz, radio.mimo, resource=resource)
    assert out["capacity_bps"][0] > out["rate_bps"][0]
    assert abs(out["rate_bps"][0] / out["capacity_bps"][0] - factor * out["goodput_factor"][0]) < 1e-9


def test_no_rf_service_before_wake_ready(energy):
    mgr = EnergyManager(energy, sole_coverage_cell=False)
    mgr.state = "SLEEP_0"
    mgr.time_in_state = 1.0
    assert mgr.request("COVERAGE_8", now_s=2.0, load_fraction=0.0)
    assert mgr.effective_chains() == 0
    assert not mgr.service_ready()
    steps = int(np.ceil(energy.wakeup_delay_s / 5e-4)) + 1
    for _ in range(steps):
        mgr.step(5e-4, 0.0, 0.0, active_chains=0, active_tiles=0)
    assert mgr.effective_chains() == 8
    assert mgr.service_ready()
    assert mgr.transition_energy_j > 0.0


def test_thermal_emergency_mutes_hardware(hardware, radio, feed_map):
    det = StatisticalDetector()
    det.mu = np.zeros(9)
    det.sigma = np.ones(9)
    det.calibrated = True
    hw = hardware
    ctrl = SelfHealingController(hw, det)
    hw.tile_temp_c[:] = 96.0
    hw.telemetry()["per_tile"][0]["temp_c"] = 96.0
    ctrl.step(4, hw.telemetry(), {})
    assert hw.active_chains() == 0
    assert hw.protection_latched
    assert ctrl.hardware_shutdown or ctrl.safe_blocked >= 1


def test_detector_resolution_floors_suppress_quantisation_false_alarms(hardware):
    det = StatisticalDetector()
    base = hardware.telemetry()
    det.fit([base], seed=7)
    assert np.all(det.sigma > 0)
    perturbed = {**base, "per_tile": [dict(t) for t in base["per_tile"]]}
    perturbed["per_tile"][0]["noise_fig_db_max"] += 0.07
    assert not det.detect(perturbed).detected
