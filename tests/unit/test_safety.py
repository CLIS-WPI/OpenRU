import numpy as np

from openru_x6.energy import EnergyManager
from openru_x6.safety import SafetySupervisor


def test_safety_vetoes_unauthorized_full_mask_and_accepts_safe_mask(security, energy):
    sup = SafetySupervisor(security, energy)
    ok, reason = sup.veto("rf_chain_mask", "set_rf_chain_mask",
                          {"chain_mask": np.zeros(64, dtype=bool).tolist()},
                          {"sole_coverage": True})
    assert not ok and reason == "coverage_requires_min_chains"
    mask = np.zeros(64, dtype=bool)
    mask[:16] = True
    ok, _ = sup.veto("rf_chain_mask", "set_rf_chain_mask",
                     {"chain_mask": mask.tolist()}, {"sole_coverage": True})
    assert ok


def test_safety_rejects_sleep_and_overtemperature(security, energy):
    sup = SafetySupervisor(security, energy)
    ok, reason = sup.veto("energy_state", "set_energy_state",
                          {"state": "SLEEP_0"}, {"sole_coverage": True})
    assert not ok and reason == "sleep_forbidden_sole_coverage"
    ok, reason = sup.veto("tx_power", "set_tx_power",
                          {"power_dbm": 50.0}, {"max_temp_c": 95.0})
    assert not ok
    assert reason in ("tx_power_above_safety_limit", "overtemperature_power_increase")


def test_emergency_is_independent_and_latched(security, energy, hardware):
    sup = SafetySupervisor(security, energy)
    out = sup.emergency_shutdown(hardware)
    assert out["active_chains"] == 0
    assert sup.emergency_latched is True
    ok, reason = sup.veto("rf_chain_mask", "set_rf_chain_mask", {"chain_mask": [1] * 64},
                          {"sole_coverage": True})
    assert not ok and reason == "emergency_latched"
    sup.clear_emergency()
    assert sup.emergency_latched is False
