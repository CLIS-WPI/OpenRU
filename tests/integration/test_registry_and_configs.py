from openru_x6.config import config_digest, load_energy, load_radio, load_scenario, load_security
from openru_x6.experiments import EXPERIMENTS, REQUIRED_FULL, REQUIRED_SMOKE
from openru_x6.experiments.common import load_suite


def test_registry_has_all_required_experiments():
    ids = [eid for eid, _ in EXPERIMENTS]
    for required in REQUIRED_FULL:
        assert required in ids
    for required in REQUIRED_SMOKE:
        assert required in ids


def test_all_scenarios_load():
    for eid in ["E00", "E01", "E02", "E03", "E04", "E05", "E06", "E07",
                "E08", "E09", "E10", "INTEGRATION"]:
        assert load_scenario_path(eid)


def load_scenario_path(eid):
    from pathlib import Path
    from openru_x6.config import CONFIG_DIR
    return load_scenario(Path(CONFIG_DIR) / "scenarios" / f"{eid}.yaml")


def test_suites_and_digest_are_stable():
    for name in ("smoke", "full"):
        suite = load_suite(name)
        assert suite["seeds"] >= 1
    d1 = config_digest(load_radio(), load_energy(), load_security())
    d2 = config_digest(load_radio(), load_energy(), load_security())
    assert d1 == d2 and len(d1) == 16
