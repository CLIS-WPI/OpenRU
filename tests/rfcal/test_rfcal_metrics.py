from __future__ import annotations

import numpy as np
import pytest

from openru_x6.rfcal.beamforming import steering_weights
from openru_x6.rfcal.calibration import apply_calibration, calibrate
from openru_x6.rfcal.measurement import MeasurementConfig, MismatchConfig, simulate_measurements
from openru_x6.rfcal.metrics import (
    array_gain_db,
    beam_metrics,
    pointing_error_deg,
    quantization_loss_db,
    truth_calibration_accuracy,
)
from openru_x6.rfcal.quantization import quantize_weights
from openru_x6.rfcal.topology import load_topology


def test_ideal_broadside_metrics_are_consistent() -> None:
    topology = load_topology()
    weights = steering_weights(topology, 0.0, 0.0)
    metrics = beam_metrics(topology, weights, 0.0, 0.0)
    assert metrics.array_gain_db == pytest.approx(10.0 * np.log10(16.0), abs=1e-12)
    assert metrics.pointing_error_deg < 1e-9
    assert metrics.peak_sidelobe_db == pytest.approx(-11.303475521585804, abs=1e-6)


def test_path_response_changes_gain_and_pointing() -> None:
    topology = load_topology()
    weights = steering_weights(topology, 0.0, 0.0)
    ideal_gain = array_gain_db(topology, weights, 0.0, 0.0)
    path_response = np.exp(1j * np.linspace(0.0, 1.5, topology.n_feeds))
    degraded_gain = array_gain_db(
        topology, weights, 0.0, 0.0, path_response=path_response
    )
    assert degraded_gain < ideal_gain
    error, _, _ = pointing_error_deg(
        topology, weights, 0.0, 0.0, path_response=path_response
    )
    assert error > 0.0


def test_phase_only_calibration_improves_gain_for_seeded_mismatch() -> None:
    topology = load_topology()
    measurement = simulate_measurements(
        topology,
        MeasurementConfig(
            seed=0,
            snr_db=30.0,
            n_captures=4,
            n_samples=64,
            mismatch=MismatchConfig().scaled(2.0),
        ),
    )
    calibration = calibrate(topology, measurement)
    uncalibrated = steering_weights(topology, 0.0, 0.0)
    phase_only = apply_calibration(uncalibrated, calibration, mode="phase_only")
    uncalibrated_metrics = beam_metrics(
        topology, uncalibrated, 0.0, 0.0, path_response=measurement.truth_response
    )
    calibrated_metrics = beam_metrics(
        topology, phase_only, 0.0, 0.0, path_response=measurement.truth_response
    )
    assert calibrated_metrics.array_gain_db > uncalibrated_metrics.array_gain_db
    assert calibrated_metrics.pointing_error_deg < uncalibrated_metrics.pointing_error_deg
    assert calibrated_metrics.pointing_error_deg < 0.3


def test_quantization_loss_is_small_for_default_quantizer() -> None:
    topology = load_topology()
    weights = steering_weights(topology, -20.0, 5.0)
    quantized = quantize_weights(weights)
    loss = quantization_loss_db(
        topology, weights, quantized.weights, -20.0, 5.0
    )
    assert 0.0 <= loss < 0.1


def test_truth_calibration_accuracy_detects_residual_error() -> None:
    truth = np.ones(8, dtype=np.complex128)
    corrections = np.exp(1j * np.deg2rad(np.linspace(0.0, 20.0, 8)))
    accuracy = truth_calibration_accuracy(
        truth, corrections, target_response=1.0 + 0.0j
    )
    assert accuracy["phase_error_deg"] > 0.0
    assert accuracy["gain_error_db"] == pytest.approx(0.0, abs=1e-12)
