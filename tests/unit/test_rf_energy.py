import numpy as np

from openru_x6.energy import (EnergyManager, ThermalModel, power_breakdown,
                              state_chains)
from openru_x6.engine import mask_for_chains
from openru_x6.rf import build_feed_map


def test_feed_map_is_complete(radio, feed_map):
    assert feed_map.n_feeds == 256
    assert feed_map.n_chains == 64
    assert feed_map.validate() == []
    assert set(feed_map.feed_tile.tolist()) == set(range(16))
    assert np.all(np.bincount(feed_map.feed_chain) == 4)


def test_chain_masks_have_expected_spread(radio, feed_map):
    for chains in (8, 16, 32, 64):
        mask = mask_for_chains(chains)
        assert int(mask.sum()) == chains
        per_tile = [int(np.sum(mask[feed_map.chain_tile == t])) for t in range(16)]
        assert sum(per_tile) == chains
        assert max(per_tile) - min(per_tile) <= 64 // 16
        total = sum(per_tile)
        assert min(per_tile) == total // 16
        assert max(per_tile) == (total + 15) // 16


def test_power_breakdown_and_zero_tx(radio, energy):
    full = power_breakdown(energy, "FULL_64", 0.0)
    eco = power_breakdown(energy, "ECO_16", 0.0)
    assert full["pa_dc"] == 0.0
    assert full["total_w"] > eco["total_w"]
    assert power_breakdown(energy, "SLEEP_0", 0.0)["rf_chains"] == 0.0


def test_sleep_is_illegal_for_sole_coverage(energy):
    mgr = EnergyManager(energy, sole_coverage_cell=True)
    assert mgr.request("SLEEP_0", now_s=1.0, load_fraction=0.0) is False
    assert mgr.illegal_sleep_attempts == 1


def test_thermal_model_heats_and_trips(energy):
    model = ThermalModel(energy)
    start = float(model.temp_c.mean())
    for _ in range(100):
        model.update(400.0, 1e-3)
    assert float(model.temp_c.mean()) > start
    model.fan_failure()
    assert model.fan_ok is False
    assert np.all(np.isfinite(model.temp_c))


def test_state_chains_match_config(energy):
    assert state_chains(energy, "FULL_64") == 64
    assert state_chains(energy, "SLEEP_0") == 0
