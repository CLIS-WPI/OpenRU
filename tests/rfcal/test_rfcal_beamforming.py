from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from openru_x6.rfcal.beamforming import (
    CodebookConfig,
    array_factor,
    array_response,
    direction_vector,
    generate_codebook,
    steering_weights,
)
from openru_x6.rfcal.metrics import (
    array_gain_db,
    beam_metrics,
    peak_sidelobe_db,
    pointing_error_deg,
    quantization_loss_db,
)
from openru_x6.rfcal.quantization import QuantizerConfig, quantize_weights
from openru_x6.rfcal.topology import load_topology


def test_direction_vector_and_array_response_shapes() -> None:
    topology = load_topology()
    direction = direction_vector(0.0, 0.0)
    np.testing.assert_allclose(direction, [1.0, 0.0, 0.0], atol=1e-12)
    grid_directions = direction_vector(
        np.asarray([0.0, 30.0]), np.asarray([0.0, 10.0])
    )
    assert grid_directions.shape == (2, 3)
    np.testing.assert_allclose(
        np.linalg.norm(grid_directions, axis=-1), np.ones(2), atol=1e-12
    )
    assert array_response(topology, 0.0, 0.0).shape == (16,)
    assert array_response(topology, [0.0, 30.0], [0.0, 10.0]).shape == (2, 16)
    assert array_factor(topology, steering_weights(topology, 0.0, 0.0), 0.0, 0.0).shape == ()


def test_ideal_steering_reaches_broadside_gain_and_pointing() -> None:
    topology = load_topology()
    weights = steering_weights(topology, 0.0, 0.0)
    assert np.isclose(np.max(np.abs(weights)), 1.0)
    assert array_gain_db(topology, weights, 0.0, 0.0) == pytest.approx(
        10.0 * np.log10(16.0), abs=1e-12
    )
    error, peak_az, peak_el = pointing_error_deg(topology, weights, 0.0, 0.0)
    assert error < 1e-9
    assert peak_az == pytest.approx(0.0)
    assert peak_el == pytest.approx(0.0)
    metrics = beam_metrics(topology, weights, 0.0, 0.0)
    assert metrics.array_gain_db == pytest.approx(10.0 * np.log10(16.0))
    assert metrics.pointing_error_deg < 1e-9
    assert metrics.peak_sidelobe_db < -10.0


def test_steering_tracks_off_broadside_angles() -> None:
    topology = load_topology()
    for az, el in ((-30.0, 0.0), (30.0, 0.0), (-20.0, 10.0), (20.0, -10.0)):
        weights = steering_weights(topology, az, el)
        error, peak_az, peak_el = pointing_error_deg(
            topology, weights, az, el, search_span_az_deg=5.0, search_span_el_deg=5.0
        )
        assert error <= 0.3
        assert peak_az == pytest.approx(az, abs=0.3)
        assert peak_el == pytest.approx(el, abs=0.3)


def test_phase_quantization_bounds_and_loss() -> None:
    topology = load_topology()
    config = QuantizerConfig()
    weights = steering_weights(topology, 12.0, -7.0)
    quantized = quantize_weights(weights, config)
    assert np.max(np.abs(quantized.phase_error_deg)) <= config.phase_step_deg / 2.0 + 1e-9
    assert np.all(quantized.attenuation_db >= 0.0)
    assert np.all(quantized.attenuation_db <= config.gain_range_db)
    loss = quantization_loss_db(topology, weights, quantized.weights, 12.0, -7.0)
    assert 0.0 <= loss < 0.1


def test_gain_quantization_clips_and_zero_weights() -> None:
    config = QuantizerConfig(phase_step_deg=45.0, gain_step_db=1.0, gain_range_db=3.0)
    weights = np.asarray([1.0, 0.01, 0.0], dtype=np.complex128)
    quantized = quantize_weights(weights, config)
    assert quantized.clipped[1]
    assert quantized.attenuation_db[1] == pytest.approx(3.0)
    assert quantized.weights[2] == 0.0
    assert np.allclose(quantized.phase_error_deg[2], 0.0)


def test_codebook_generation_and_round_trip(tmp_path: Path) -> None:
    topology = load_topology()
    config = CodebookConfig(
        az_min_deg=-10.0,
        az_max_deg=10.0,
        az_step_deg=10.0,
        el_min_deg=-5.0,
        el_max_deg=5.0,
        el_step_deg=5.0,
    )
    codebook = generate_codebook(topology, config)
    assert len(codebook.entries) == 9
    assert codebook.entries[0].beam_id == 0
    assert codebook.entries[0].target_az_deg == pytest.approx(-10.0)
    assert codebook.entries[0].weights.shape == (16,)
    assert codebook.entries[0].quantized.weights.shape == (16,)
    json_path = tmp_path / "codebook.json"
    csv_path = tmp_path / "codebook.csv"
    codebook.to_json(json_path)
    codebook.to_csv(csv_path)
    assert json_path.stat().st_size > 0
    assert csv_path.stat().st_size > 0
    assert csv_path.read_text(encoding="utf-8").count("\n") == 1 + 9 * 16


def test_calibrated_codebook_uses_corrections() -> None:
    topology = load_topology()
    corrections = np.exp(1j * np.linspace(0.0, 0.2, topology.n_feeds))
    single_config = CodebookConfig(
        az_min_deg=0,
        az_max_deg=0,
        az_step_deg=1,
        el_min_deg=0,
        el_max_deg=0,
        el_step_deg=1,
    )
    plain = generate_codebook(topology, single_config)
    corrected = generate_codebook(
        topology,
        single_config,
        calibration_corrections=corrections,
    )
    assert not np.allclose(
        plain.entries[0].weights, corrected.entries[0].weights
    )
