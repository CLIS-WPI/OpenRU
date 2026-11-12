from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from openru_x6.rfcal.topology import (
    DEFAULT_CARRIER_HZ,
    SPEED_OF_LIGHT_MPS,
    Topology,
    chain_groups,
    feed_indices_by_polarization,
    load_topology,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_default_topology_matches_h1_4t4r_shape() -> None:
    topology = load_topology()
    assert topology.is_4t4r()
    assert topology.n_chains == 4
    assert topology.n_feeds == 16
    assert topology.n_sites == 8
    assert topology.chain_ids == (0, 1, 2, 3)
    assert topology.polarization_names == ("H", "V")
    assert topology.carrier_freq_hz == DEFAULT_CARRIER_HZ
    assert topology.wavelength_m == pytest.approx(SPEED_OF_LIGHT_MPS / 8.4e9)


def test_default_topology_chain_ownership_and_geometry() -> None:
    topology = load_topology()
    groups = chain_groups(topology)
    assert {chain: len(feeds) for chain, feeds in groups.items()} == {
        0: 4,
        1: 4,
        2: 4,
        3: 4,
    }
    assert {feed.site for feed in groups[0]} == {0, 1}
    assert {feed.site for feed in groups[1]} == {2, 3}
    assert {feed.site for feed in groups[2]} == {4, 5}
    assert {feed.site for feed in groups[3]} == {6, 7}
    positions = topology.positions_m()
    assert positions.shape == (16, 3)
    np.testing.assert_allclose(positions[:, 0], 0.0)
    assert np.unique(np.round(positions[:, 1], 9)).size == 4
    assert np.unique(np.round(positions[:, 2], 9)).size == 2
    assert np.min(np.diff(np.unique(np.round(positions[:, 1], 9)))) == pytest.approx(
        topology.wavelength_m / 2.0
    )


def test_feed_map_csv_matches_default_topology() -> None:
    default = load_topology()
    from_csv = Topology.from_feed_map_csv(
        REPO_ROOT / "hardware" / "H1_FEED_POLARIZATION_MAP.csv"
    )
    assert from_csv.n_feeds == default.n_feeds
    assert from_csv.n_chains == default.n_chains
    assert from_csv.n_sites == default.n_sites
    for expected, actual in zip(default.feeds, from_csv.feeds, strict=True):
        assert actual.chain == expected.chain
        assert actual.site == expected.site
        assert actual.polarization == expected.polarization
        assert actual.y_m == pytest.approx(expected.y_m, abs=1e-6)
        assert actual.z_m == pytest.approx(expected.z_m, abs=1e-6)


def test_topology_json_and_csv_round_trip(tmp_path: Path) -> None:
    topology = load_topology()
    json_path = tmp_path / "topology.json"
    csv_path = tmp_path / "topology.csv"
    topology.to_json(json_path)
    topology.to_csv(csv_path)
    loaded_json = Topology.from_json(json_path)
    loaded_csv = Topology.from_feed_map_csv(csv_path)
    assert loaded_json.to_dict() == topology.to_dict()
    assert loaded_csv.n_feeds == topology.n_feeds
    assert [feed.chain for feed in loaded_csv.feeds] == [
        feed.chain for feed in topology.feeds
    ]


def test_polarization_indices_and_validation() -> None:
    topology = load_topology()
    indices = feed_indices_by_polarization(topology)
    assert set(indices) == {"H", "V"}
    assert len(indices["V"]) == 8
    assert len(indices["H"]) == 8
    topology.validate()
    with pytest.raises(ValueError):
        Topology(
            name="bad",
            carrier_freq_hz=0.0,
            sites=topology.sites,
            feeds=topology.feeds,
        ).validate()
    payload = topology.to_dict()
    duplicate = [dict(feed) for feed in payload["feeds"]]
    duplicate[1]["index"] = duplicate[0]["index"]
    with pytest.raises(ValueError):
        Topology.from_dict({**payload, "feeds": duplicate})
