from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from openru_x6.rfcal.hierarchical import (
    HierarchicalCalibrationResult,
    HierarchicalMeasurementConfig,
    apply_hierarchical_calibration,
    calibrate_hierarchical,
    hierarchical_calibration_accuracy,
    simulate_hierarchical_measurements,
)
from openru_x6.rfcal.measurement import FaultSpec, MismatchConfig
from openru_x6.rfcal.topology import load_topology


def _measurement(
    architecture: str,
    *,
    seed: int = 0,
    faults: FaultSpec | None = None,
    snr_db: float = 30.0,
):
    topology = load_topology()
    return topology, simulate_hierarchical_measurements(
        topology,
        HierarchicalMeasurementConfig(
            seed=seed,
            snr_db=snr_db,
            n_captures=4,
            n_samples=64,
            mismatch=MismatchConfig(),
            faults=faults or FaultSpec(),
            architecture=architecture,
        ),
    )


def test_h2_available_does_not_invent_feed_phase_corrections() -> None:
    topology, measurement = _measurement("h2_available")
    calibration = calibrate_hierarchical(topology, measurement)
    assert calibration.feed_phase_observable is False
    assert all(not path.phase_observable for path in calibration.paths)
    np.testing.assert_allclose(np.angle(calibration.feed_corrections), 0.0, atol=1e-12)
    assert np.any(np.abs(np.angle(calibration.chain_corrections)) > 1e-6)
    accuracy = hierarchical_calibration_accuracy(
        measurement.truth_response, calibration
    )
    assert accuracy["phase_error_deg"] > 1.0


def test_switched_feed_loopback_recovers_feed_phase() -> None:
    topology, measurement = _measurement("proposed_switched_feed_loopback")
    calibration = calibrate_hierarchical(topology, measurement)
    assert calibration.feed_phase_observable is True
    assert all(path.phase_observable for path in calibration.paths)
    accuracy = hierarchical_calibration_accuracy(
        measurement.truth_response, calibration
    )
    assert accuracy["phase_error_deg"] < 1.0
    assert accuracy["gain_error_db"] < 0.2


def test_switched_calibration_beats_h2_available_on_residual_phase() -> None:
    topology = load_topology()
    available = simulate_hierarchical_measurements(
        topology,
        HierarchicalMeasurementConfig(seed=3, architecture="h2_available"),
    )
    switched = simulate_hierarchical_measurements(
        topology,
        HierarchicalMeasurementConfig(
            seed=3, architecture="proposed_switched_feed_loopback"
        ),
    )
    available_accuracy = hierarchical_calibration_accuracy(
        available.truth_response, calibrate_hierarchical(topology, available)
    )
    switched_accuracy = hierarchical_calibration_accuracy(
        switched.truth_response, calibrate_hierarchical(topology, switched)
    )
    assert (
        switched_accuracy["phase_error_deg"]
        < available_accuracy["phase_error_deg"]
    )


def test_chain_fault_is_detected_without_per_feed_complex_data() -> None:
    topology, measurement = _measurement(
        "h2_available", faults=FaultSpec(chain_faults={0: "missing"})
    )
    calibration = calibrate_hierarchical(topology, measurement)
    chain = [item for item in calibration.chains if item.chain == 0][0]
    assert chain.status == "missing"
    assert np.sum(calibration.chain_healthy_mask) == 12
    assert np.sum(calibration.healthy_mask) == 12
    for feed in topology.feeds_for_chain(0):
        assert calibration.corrections[feed.index] == 0.0


def test_feed_power_faults_are_detected_on_h2_available() -> None:
    topology, measurement = _measurement(
        "h2_available", faults=FaultSpec(path_faults={5: "missing"})
    )
    calibration = calibrate_hierarchical(topology, measurement)
    assert calibration.chain_status_counts["ok"] == 4
    assert calibration.paths[5].status == "missing"
    assert np.sum(calibration.healthy_mask) == 15

    topology, measurement = _measurement(
        "h2_available", faults=FaultSpec(path_faults={6: "faulty"})
    )
    calibration = calibrate_hierarchical(topology, measurement)
    assert calibration.paths[6].status == "faulty"
    assert np.sum(calibration.healthy_mask) == 15


def test_feed_phase_fault_is_invisible_to_power_but_visible_to_switched() -> None:
    phase_only_fault = FaultSpec(
        path_faults={5: "faulty"},
        faulty_gain_db=0.0,
        faulty_phase_deg=120.0,
    )
    topology, available_measurement = _measurement(
        "h2_available", faults=phase_only_fault
    )
    available = calibrate_hierarchical(topology, available_measurement)
    assert available.paths[5].status == "ok"

    topology, switched_measurement = _measurement(
        "proposed_switched_feed_loopback", faults=phase_only_fault
    )
    switched = calibrate_hierarchical(topology, switched_measurement)
    assert switched.paths[5].status == "faulty"


def test_hierarchical_modes_and_json_csv_round_trip(tmp_path: Path) -> None:
    topology, measurement = _measurement("h2_available")
    calibration = calibrate_hierarchical(topology, measurement)
    weights = np.ones(topology.n_feeds, dtype=np.complex128)
    assert apply_hierarchical_calibration(weights, calibration, mode="none").shape == (
        16,
    )
    assert apply_hierarchical_calibration(
        weights, calibration, mode="chain_only"
    ).shape == (16,)
    assert apply_hierarchical_calibration(
        weights, calibration, mode="phase_only"
    ).shape == (16,)
    with pytest.raises(ValueError):
        apply_hierarchical_calibration(weights, calibration, mode="unknown")

    json_path = tmp_path / "hierarchical.json"
    csv_path = tmp_path / "hierarchical.csv"
    calibration.to_json(json_path)
    calibration.to_csv(csv_path)
    loaded = HierarchicalCalibrationResult.from_json(json_path)
    assert loaded.feed_phase_observable == calibration.feed_phase_observable
    assert loaded.status_counts == calibration.status_counts
    np.testing.assert_allclose(
        loaded.corrections, calibration.corrections, atol=1e-12
    )
    assert csv_path.stat().st_size > 0
