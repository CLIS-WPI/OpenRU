from __future__ import annotations

import numpy as np
import pytest

from openru_x6.rfcal.beamforming import steering_weights
from openru_x6.rfcal.metrics import (
    array_gain_db,
    beam_metrics,
    beam_metrics_polarized,
)
from openru_x6.rfcal.polarization import (
    PolarizationConfig,
    circular_jones,
    feed_jones,
    feed_polarization_gain,
    linear_jones,
    matched_receiver_jones,
    orthogonal_jones,
    polarized_steering_weights,
    site_jones,
)
from openru_x6.rfcal.topology import load_topology


def test_jones_vectors_are_unit_and_orthogonal() -> None:
    v = linear_jones(0.0)
    h = linear_jones(90.0)
    diagonal = linear_jones(45.0)
    rhcp = circular_jones("rhcp")
    lhcp = circular_jones("lhcp")
    np.testing.assert_allclose(v, [1.0, 0.0])
    np.testing.assert_allclose(h, [0.0, 1.0], atol=1e-12)
    np.testing.assert_allclose(np.abs(diagonal), [np.sqrt(0.5), np.sqrt(0.5)])
    np.testing.assert_allclose(np.linalg.norm(rhcp), 1.0)
    np.testing.assert_allclose(rhcp, np.conj(lhcp))
    for vector in (v, h, diagonal, rhcp, lhcp):
        np.testing.assert_allclose(
            np.vdot(vector, orthogonal_jones(vector)), 0.0, atol=1e-12
        )
    np.testing.assert_allclose(matched_receiver_jones(diagonal), np.conj(diagonal))


def test_feed_jones_contains_cross_pol_leakage_per_site() -> None:
    topology = load_topology()
    config = PolarizationConfig(cross_pol_db=20.0, cross_pol_phase_deg=30.0)
    matrices = site_jones(topology, config)
    rows = feed_jones(topology, config)
    assert matrices.shape == (8, 2, 2)
    assert rows.shape == (16, 2)
    leakage = 10.0 ** (-20.0 / 20.0) * np.exp(1j * np.deg2rad(30.0))
    np.testing.assert_allclose(matrices[0, 0, 1], leakage)
    np.testing.assert_allclose(matrices[0, 1, 0], leakage)
    for feed in topology.feeds:
        expected_row = 0 if feed.polarization == "V" else 1
        np.testing.assert_allclose(rows[feed.index], matrices[feed.site, expected_row])


def test_v_receiver_co_pol_gain_and_cross_pol_discrimination() -> None:
    topology = load_topology()
    incident = linear_jones(0.0)
    receiver = matched_receiver_jones(incident)
    weights = polarized_steering_weights(topology, 0.0, 0.0, receiver)
    metrics = beam_metrics_polarized(topology, weights, 0.0, 0.0, incident)
    assert metrics.co_pol_gain_db == pytest.approx(10.0 * np.log10(8.0), abs=1e-9)
    assert metrics.cross_pol_gain_db == pytest.approx(
        10.0 * np.log10(8.0) - 25.0, abs=1e-9
    )
    assert metrics.cross_pol_discrimination_db == pytest.approx(25.0, abs=1e-9)
    assert metrics.pointing_error_deg < 1e-9
    assert metrics.peak_sidelobe_db < -10.0


def test_cross_pol_leakage_sets_xpd() -> None:
    topology = load_topology()
    incident = linear_jones(0.0)
    receiver = matched_receiver_jones(incident)
    weights = polarized_steering_weights(topology, 0.0, 0.0, receiver)
    for leakage_db in (15.0, 25.0, 35.0):
        metrics = beam_metrics_polarized(
            topology,
            weights,
            0.0,
            0.0,
            incident,
            polarization=PolarizationConfig(cross_pol_db=leakage_db),
        )
        assert metrics.cross_pol_discrimination_db == pytest.approx(
            leakage_db, abs=1e-9
        )


def test_circular_receiver_uses_both_polarization_ports() -> None:
    topology = load_topology()
    incident = circular_jones("rhcp")
    receiver = matched_receiver_jones(incident)
    weights = polarized_steering_weights(topology, 0.0, 0.0, receiver)
    assert np.count_nonzero(np.abs(weights) > 0.0) == 16
    metrics = beam_metrics_polarized(topology, weights, 0.0, 0.0, incident)
    # The coherent ceiling is the number of dual-polarized sites, not the number
    # of ports: each port receives one orthogonal field component.
    assert metrics.co_pol_gain_db == pytest.approx(10.0 * np.log10(8.0), abs=1e-9)


def test_scalar_baseline_is_unchanged_and_distinctly_labeled() -> None:
    topology = load_topology()
    scalar_weights = steering_weights(topology, 0.0, 0.0)
    scalar = beam_metrics(topology, scalar_weights, 0.0, 0.0)
    assert scalar.array_gain_db == pytest.approx(10.0 * np.log10(16.0), abs=1e-12)
    assert array_gain_db(
        topology, scalar_weights, 0.0, 0.0
    ) == pytest.approx(10.0 * np.log10(16.0), abs=1e-12)

    polarized = polarized_steering_weights(
        topology, 0.0, 0.0, matched_receiver_jones(linear_jones(0.0))
    )
    vector = beam_metrics_polarized(
        topology, polarized, 0.0, 0.0, linear_jones(0.0)
    )
    assert vector.co_pol_gain_db < scalar.array_gain_db
    assert not np.allclose(scalar_weights, polarized)


def test_polarization_gain_matches_jones_matrix_product() -> None:
    topology = load_topology()
    config = PolarizationConfig(cross_pol_db=22.0, cross_pol_phase_deg=-40.0)
    incident = linear_jones(33.0, phase_deg=15.0)
    gain = feed_polarization_gain(topology, incident, config)
    assert gain.shape == (16,)
    rows = feed_jones(topology, config)
    np.testing.assert_allclose(gain, rows @ incident)
