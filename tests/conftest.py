import numpy as np
import pytest

from openru_x6.config import load_energy, load_radio, load_security
from openru_x6.rf import RFHardware, build_feed_map


@pytest.fixture(scope="session")
def radio():
    return load_radio()


@pytest.fixture(scope="session")
def energy():
    return load_energy()


@pytest.fixture(scope="session")
def security():
    return load_security()


@pytest.fixture(scope="session")
def feed_map(radio):
    return build_feed_map(radio.array, radio.cell.carrier_freq_hz)


@pytest.fixture()
def hardware(radio, feed_map):
    return RFHardware(radio.array, feed_map)


@pytest.fixture()
def rng():
    return np.random.default_rng(7)
