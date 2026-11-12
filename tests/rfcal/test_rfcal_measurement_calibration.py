from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from openru_x6.rfcal.calibration import (
    CalibrationConfig,
    CalibrationResult,
    apply_calibration,
    calibrate,
    corrections_for_mode,
)
from openru_x6.rfcal.measurement import (
    FaultSpec,
    MeasurementConfig,
    MeasurementSet,
    MismatchConfig,
    simulate_measurements,
)
from openru_x6.rfcal.metrics import truth_calibration_accuracy
from openru_x6.rfcal.topology import load_topology


def test_synthetic_measurement_is_deterministic_and_labelled_simulated() -> None:
    topology = load_topology()
    config = MeasurementConfig(seed=17, snr_db=25.0, n_captures=3, n_samples=32)
    first = simulate_measurements(topology, config)
    second = simulate_measurements(topology, config)
    assert first.simulated
    assert first.metadata["evidence_label"] == "SIMULATED"
    assert not first.metadata["hardware_measured"]
    assert first.iq.shape == (16, 3, 32)
    assert first.pilot.shape == (32,)
    assert first.truth_response.shape == (16,)
    np.testing.assert_allclose(first.iq, second.iq)
    different = simulate_measurements(
        topology, MeasurementConfig(seed=18, snr_db=25.0, n_captures=3, n_samples=32)
    )
    assert not np.allclose(first.iq, different.iq)


def test_zero_mismatch_calibration_recovers_unity_paths() -> None:
    topology = load_topology()
    measurement = simulate_measurements(
        topology,
        MeasurementConfig(
            seed=0,
            snr_db=100.0,
            n_captures=2,
            n_samples=64,
            mismatch=MismatchConfig(
                chain_phase_std_deg=0.0,
                chain_gain_std_db=0.0,
                feed_phase_std_deg=0.0,
                feed_gain_std_db=0.0,
            ),
        ),
    )
    calibration = calibrate(topology, measurement)
    assert np.all(calibration.healthy_mask)
    assert calibration.status_counts["ok"] == 16
    np.testing.assert_allclose(calibration.corrections, 1.0, atol=1e-4)
    accuracy = truth_calibration_accuracy(
        measurement.truth_response,
        calibration.corrections,
        healthy_mask=calibration.healthy_mask,
        target_response=calibration.target_response,
    )
    assert accuracy["phase_error_deg"] < 0.001
    assert accuracy["gain_error_db"] < 0.001


def test_noisy_mismatch_calibration_improves_phase_accuracy() -> None:
    topology = load_topology()
    measurement = simulate_measurements(
        topology,
        MeasurementConfig(
            seed=1,
            snr_db=30.0,
            n_captures=8,
            n_samples=128,
            mismatch=MismatchConfig().scaled(2.0),
        ),
    )
    calibration = calibrate(topology, measurement)
    assert calibration.status_counts["ok"] == 16
    calibrated = truth_calibration_accuracy(
        measurement.truth_response,
        calibration.corrections,
        healthy_mask=calibration.healthy_mask,
        target_response=calibration.target_response,
    )
    uncalibrated = truth_calibration_accuracy(
        measurement.truth_response,
        np.ones(16, dtype=np.complex128),
        healthy_mask=calibration.healthy_mask,
        target_response=calibration.target_response,
    )
    assert calibrated["phase_error_deg"] < 1.0
    assert calibrated["phase_error_deg"] < uncalibrated["phase_error_deg"]
    assert calibrated["gain_error_db"] < 0.1


@pytest.mark.parametrize(
    ("fault", "path_index", "expected_status"),
    [
        (FaultSpec(path_faults={5: "missing"}), 5, "missing"),
        (FaultSpec(path_faults={6: "faulty"}), 6, "faulty"),
        (FaultSpec(path_faults={7: "inconsistent"}), 7, "inconsistent"),
    ],
)
def test_single_path_fault_detection(
    fault: FaultSpec, path_index: int, expected_status: str
) -> None:
    topology = load_topology()
    measurement = simulate_measurements(
        topology,
        MeasurementConfig(
            seed=5,
            snr_db=30.0,
            n_captures=8,
            n_samples=128,
            faults=fault,
        ),
    )
    calibration = calibrate(topology, measurement)
    assert calibration.paths[path_index].status == expected_status
    assert calibration.status_counts[expected_status] == 1
    assert calibration.corrections[path_index] == 0.0


def test_missing_chain_is_detected_and_excluded_from_beam() -> None:
    topology = load_topology()
    measurement = simulate_measurements(
        topology,
        MeasurementConfig(
            seed=8,
            snr_db=30.0,
            n_captures=4,
            n_samples=64,
            faults=FaultSpec(chain_faults={0: "missing"}),
        ),
    )
    calibration = calibrate(topology, measurement)
    for feed in topology.feeds_for_chain(0):
        assert calibration.paths[feed.index].status == "missing"
        assert calibration.corrections[feed.index] == 0.0
    weights = apply_calibration(np.ones(16, dtype=np.complex128), calibration)
    np.testing.assert_allclose(weights[:4], 0.0)
    assert corrections_for_mode(calibration, "none").shape == (16,)
    assert corrections_for_mode(calibration, "phase_only").shape == (16,)
    with pytest.raises(ValueError):
        corrections_for_mode(calibration, "unknown")


def test_calibration_json_and_csv_round_trip(tmp_path: Path) -> None:
    topology = load_topology()
    measurement = simulate_measurements(
        topology,
        MeasurementConfig(seed=3, snr_db=30.0, n_captures=4, n_samples=64),
    )
    calibration = calibrate(topology, measurement)
    json_path = tmp_path / "calibration.json"
    csv_path = tmp_path / "calibration.csv"
    calibration.to_json(json_path)
    calibration.to_csv(csv_path)
    loaded_json = CalibrationResult.from_json(json_path)
    loaded_csv = CalibrationResult.from_csv(
        csv_path, topology_name=topology.name, config=calibration.config
    )
    assert loaded_json.to_dict()["paths"] == calibration.to_dict()["paths"]
    assert loaded_csv.n_feeds == 16
    assert loaded_csv.status_counts == calibration.status_counts
    np.testing.assert_allclose(
        loaded_json.corrections, calibration.corrections, atol=1e-12
    )
    np.testing.assert_allclose(
        loaded_csv.corrections, calibration.corrections, atol=1e-9
    )


def test_measurement_json_round_trip(tmp_path: Path) -> None:
    topology = load_topology()
    measurement = simulate_measurements(
        topology,
        MeasurementConfig(seed=4, snr_db=20.0, n_captures=2, n_samples=16),
    )
    path = tmp_path / "measurements.json"
    measurement.to_json(path)
    loaded = MeasurementSet.from_json(path)
    np.testing.assert_allclose(loaded.pilot, measurement.pilot)
    np.testing.assert_allclose(loaded.iq, measurement.iq)
    np.testing.assert_allclose(loaded.truth_response, measurement.truth_response)
    assert loaded.fault_labels == measurement.fault_labels


def test_topology_mismatch_is_rejected() -> None:
    topology = load_topology()
    measurement = simulate_measurements(
        topology,
        MeasurementConfig(seed=0, snr_db=30.0, n_captures=2, n_samples=16),
    )
    measurement.topology_name = "other"
    with pytest.raises(ValueError):
        calibrate(topology, measurement, CalibrationConfig())
