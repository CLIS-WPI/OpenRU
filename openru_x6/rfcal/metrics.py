"""Beam and calibration metrics for simulated array evaluations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .beamforming import array_factor, direction_vector
from .topology import Topology

_FLOOR_DB = -300.0


@dataclass(frozen=True)
class BeamMetrics:
    target_az_deg: float
    target_el_deg: float
    peak_az_deg: float
    peak_el_deg: float
    pointing_error_deg: float
    array_gain_db: float
    peak_sidelobe_db: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_az_deg": self.target_az_deg,
            "target_el_deg": self.target_el_deg,
            "peak_az_deg": self.peak_az_deg,
            "peak_el_deg": self.peak_el_deg,
            "pointing_error_deg": self.pointing_error_deg,
            "array_gain_db": self.array_gain_db,
            "peak_sidelobe_db": self.peak_sidelobe_db,
        }


def array_gain_db(
    topology: Topology,
    weights: np.ndarray,
    az_deg: float,
    el_deg: float,
    *,
    path_response: np.ndarray | None = None,
) -> float:
    """Return coherent array gain relative to one unit-amplitude feed."""

    weights = np.asarray(weights, dtype=np.complex128)
    weight_power = float(np.sum(np.abs(weights) ** 2))
    if weight_power <= 0:
        return _FLOOR_DB
    factor = array_factor(
        topology, weights, az_deg, el_deg, path_response=path_response
    )
    gain = float(abs(factor) ** 2 / weight_power)
    if gain <= 0:
        return _FLOOR_DB
    return float(10.0 * np.log10(gain))


def pointing_error_deg(
    topology: Topology,
    weights: np.ndarray,
    target_az_deg: float,
    target_el_deg: float,
    *,
    path_response: np.ndarray | None = None,
    search_span_az_deg: float = 10.0,
    search_span_el_deg: float = 10.0,
    search_step_deg: float = 0.25,
) -> tuple[float, float, float]:
    """Find the beam peak near the target and report angular error."""

    if search_step_deg <= 0:
        raise ValueError("search_step_deg must be positive")
    az_axis = np.arange(
        target_az_deg - search_span_az_deg,
        target_az_deg + search_span_az_deg + search_step_deg * 0.5,
        search_step_deg,
    )
    el_axis = np.arange(
        target_el_deg - search_span_el_deg,
        target_el_deg + search_span_el_deg + search_step_deg * 0.5,
        search_step_deg,
    )
    az_grid, el_grid = np.meshgrid(az_axis, el_axis, indexing="xy")
    pattern = np.abs(
        array_factor(
            topology,
            weights,
            az_grid,
            el_grid,
            path_response=path_response,
        )
    )
    peak_index = np.unravel_index(int(np.argmax(pattern)), pattern.shape)
    peak_az = float(az_grid[peak_index])
    peak_el = float(el_grid[peak_index])
    target_vector = direction_vector(target_az_deg, target_el_deg)
    peak_vector = direction_vector(peak_az, peak_el)
    cosine = float(np.clip(np.dot(target_vector, peak_vector), -1.0, 1.0))
    return float(np.rad2deg(np.arccos(cosine))), peak_az, peak_el


def peak_sidelobe_db(
    topology: Topology,
    weights: np.ndarray,
    target_az_deg: float,
    target_el_deg: float,
    *,
    path_response: np.ndarray | None = None,
    az_min_deg: float = -90.0,
    az_max_deg: float = 90.0,
    step_deg: float = 0.25,
    exclusion_deg: float | None = None,
) -> float:
    """Return the highest sidelobe in an azimuth cut relative to the peak."""

    if step_deg <= 0:
        raise ValueError("step_deg must be positive")
    if exclusion_deg is None:
        exclusion_deg = _broadside_first_null_deg(topology)
    az_axis = np.arange(az_min_deg, az_max_deg + step_deg * 0.5, step_deg)
    pattern = np.abs(
        array_factor(
            topology,
            weights,
            az_axis,
            np.full_like(az_axis, target_el_deg),
            path_response=path_response,
        )
    )
    peak = float(np.max(pattern))
    if peak <= 0:
        return _FLOOR_DB
    outside_main = np.abs(az_axis - target_az_deg) > exclusion_deg
    if not np.any(outside_main):
        return _FLOOR_DB
    sidelobe = float(np.max(pattern[outside_main]))
    if sidelobe <= 0:
        return _FLOOR_DB
    return float(20.0 * np.log10(sidelobe / peak))


def quantization_loss_db(
    topology: Topology,
    ideal_weights: np.ndarray,
    quantized_weights: np.ndarray,
    az_deg: float,
    el_deg: float,
    *,
    path_response: np.ndarray | None = None,
) -> float:
    """Return the target-direction gain loss caused by quantization."""

    ideal_gain = array_gain_db(
        topology, ideal_weights, az_deg, el_deg, path_response=path_response
    )
    quantized_gain = array_gain_db(
        topology, quantized_weights, az_deg, el_deg, path_response=path_response
    )
    if ideal_gain <= _FLOOR_DB or quantized_gain <= _FLOOR_DB:
        return float("inf")
    return float(ideal_gain - quantized_gain)


def beam_metrics(
    topology: Topology,
    weights: np.ndarray,
    target_az_deg: float,
    target_el_deg: float,
    *,
    path_response: np.ndarray | None = None,
    search_span_az_deg: float = 10.0,
    search_span_el_deg: float = 10.0,
    search_step_deg: float = 0.25,
    sidelobe_exclusion_deg: float | None = None,
) -> BeamMetrics:
    """Compute pointing, gain, and sidelobe metrics for one beam."""

    error_deg, peak_az, peak_el = pointing_error_deg(
        topology,
        weights,
        target_az_deg,
        target_el_deg,
        path_response=path_response,
        search_span_az_deg=search_span_az_deg,
        search_span_el_deg=search_span_el_deg,
        search_step_deg=search_step_deg,
    )
    gain_db = array_gain_db(
        topology,
        weights,
        target_az_deg,
        target_el_deg,
        path_response=path_response,
    )
    sidelobe_db = peak_sidelobe_db(
        topology,
        weights,
        target_az_deg,
        target_el_deg,
        path_response=path_response,
        step_deg=search_step_deg,
        exclusion_deg=sidelobe_exclusion_deg,
    )
    return BeamMetrics(
        target_az_deg=float(target_az_deg),
        target_el_deg=float(target_el_deg),
        peak_az_deg=peak_az,
        peak_el_deg=peak_el,
        pointing_error_deg=error_deg,
        array_gain_db=gain_db,
        peak_sidelobe_db=sidelobe_db,
    )


def _broadside_first_null_deg(topology: Topology) -> float:
    positions = topology.positions_m()
    unique_y = np.unique(np.round(positions[:, 1], 12))
    if unique_y.size < 2:
        return 90.0
    pitch = float(np.min(np.diff(unique_y)))
    ratio = topology.wavelength_m / (unique_y.size * pitch)
    if ratio >= 1.0:
        return 90.0
    return float(np.rad2deg(np.arcsin(ratio)))


def truth_calibration_accuracy(
    truth_response: np.ndarray,
    calibration_corrections: np.ndarray,
    *,
    healthy_mask: np.ndarray | None = None,
    target_response: complex | None = None,
) -> dict[str, float]:
    """Measure calibration error against simulated truth on healthy paths."""

    truth = np.asarray(truth_response, dtype=np.complex128)
    corrections = np.asarray(calibration_corrections, dtype=np.complex128)
    if truth.shape != corrections.shape:
        raise ValueError("truth_response and calibration_corrections must match")
    if healthy_mask is None:
        healthy_mask = np.ones(truth.shape, dtype=bool)
    else:
        healthy_mask = np.asarray(healthy_mask, dtype=bool)
        if healthy_mask.shape != truth.shape:
            raise ValueError("healthy_mask must match truth_response")
    values = truth[healthy_mask] * corrections[healthy_mask]
    if values.size == 0:
        return {
            "phase_error_deg": float("nan"),
            "gain_error_db": float("nan"),
        }
    if target_response is None or target_response == 0:
        reference_phase = float(np.angle(np.mean(np.exp(1j * np.angle(values)))))
        reference_gain_db = float(np.mean(20.0 * np.log10(np.maximum(np.abs(values), 1e-300))))
    else:
        reference_phase = float(np.angle(target_response))
        reference_gain_db = float(
            20.0 * np.log10(max(abs(target_response), 1e-300))
        )
    phases = np.angle(values)
    phase_error = np.rad2deg(
        np.angle(np.exp(1j * (phases - reference_phase)))
    )
    amplitudes_db = 20.0 * np.log10(np.maximum(np.abs(values), 1e-300))
    gain_error = amplitudes_db - reference_gain_db
    return {
        "phase_error_deg": float(np.sqrt(np.mean(phase_error**2))),
        "gain_error_db": float(np.sqrt(np.mean(gain_error**2))),
    }
