"""Geometry-based steering, codebooks, and complex array responses."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from .quantization import QuantizedWeights, QuantizerConfig, quantize_weights
from .topology import Topology


def direction_vector(az_deg: float | np.ndarray, el_deg: float | np.ndarray) -> np.ndarray:
    """Return unit vectors for azimuth/elevation angles in degrees.

    Azimuth is measured in the array plane from broadside and elevation is the
    out-of-plane angle.  The resulting vector is ``(x, y, z)`` with broadside
    along ``+x``.
    """

    az_rad = np.deg2rad(np.asarray(az_deg, dtype=float))
    el_rad = np.deg2rad(np.asarray(el_deg, dtype=float))
    cos_el = np.cos(el_rad)
    return np.stack(
        (cos_el * np.cos(az_rad), cos_el * np.sin(az_rad), np.sin(el_rad)),
        axis=-1,
    )


def array_response(
    topology: Topology,
    az_deg: float | np.ndarray,
    el_deg: float | np.ndarray,
) -> np.ndarray:
    """Return the per-feed phase response for one or more directions."""

    directions = direction_vector(az_deg, el_deg)
    output_shape = directions.shape[:-1]
    flat_directions = directions.reshape(-1, 3)
    positions = topology.positions_m()
    projection = positions @ flat_directions.T
    response = np.exp(1j * topology.wavenumber_rad_m * projection)
    return response.T.reshape(output_shape + (topology.n_feeds,))


def array_factor(
    topology: Topology,
    weights: np.ndarray,
    az_deg: float | np.ndarray,
    el_deg: float | np.ndarray,
    *,
    path_response: np.ndarray | None = None,
) -> np.ndarray:
    """Return the complex array factor for a set of directions."""

    weights = np.asarray(weights, dtype=np.complex128)
    if weights.shape != (topology.n_feeds,):
        raise ValueError(
            f"weights must have shape ({topology.n_feeds},), got {weights.shape}"
        )
    response = array_response(topology, az_deg, el_deg)
    if path_response is not None:
        path_response = np.asarray(path_response, dtype=np.complex128)
        if path_response.shape != (topology.n_feeds,):
            raise ValueError(
                f"path_response must have shape ({topology.n_feeds},), "
                f"got {path_response.shape}"
            )
        response = response * path_response
    return np.sum(weights * response, axis=-1)


def steering_weights(
    topology: Topology,
    az_deg: float,
    el_deg: float,
    *,
    amplitude: np.ndarray | Sequence[float] | None = None,
    polarization_weights: Mapping[str, complex] | None = None,
) -> np.ndarray:
    """Return conjugate steering weights normalized to unit peak amplitude."""

    response = array_response(topology, az_deg, el_deg)
    if response.ndim != 1:
        raise ValueError("steering_weights requires scalar angles")
    weights = np.conj(response)
    if polarization_weights:
        for feed in topology.feeds:
            weights[feed.index] *= complex(polarization_weights.get(feed.polarization, 1.0))
    if amplitude is not None:
        amplitude_array = np.asarray(amplitude, dtype=float)
        if amplitude_array.shape != (topology.n_feeds,):
            raise ValueError(
                f"amplitude must have shape ({topology.n_feeds},), "
                f"got {amplitude_array.shape}"
            )
        if np.any(amplitude_array < 0):
            raise ValueError("amplitude values must be non-negative")
        weights = weights * amplitude_array
    peak = float(np.max(np.abs(weights)))
    if peak > 0:
        weights = weights / peak
    return weights.astype(np.complex128)


@dataclass(frozen=True)
class CodebookConfig:
    az_min_deg: float = -60.0
    az_max_deg: float = 60.0
    az_step_deg: float = 5.0
    el_min_deg: float = -20.0
    el_max_deg: float = 20.0
    el_step_deg: float = 5.0
    quantizer: QuantizerConfig = field(default_factory=QuantizerConfig)

    def validate(self) -> None:
        if self.az_step_deg <= 0 or self.el_step_deg <= 0:
            raise ValueError("codebook steps must be positive")
        if self.az_min_deg > self.az_max_deg:
            raise ValueError("az_min_deg must not exceed az_max_deg")
        if self.el_min_deg > self.el_max_deg:
            raise ValueError("el_min_deg must not exceed el_max_deg")
        self.quantizer.validate()

    def angles(self) -> list[tuple[float, float]]:
        self.validate()
        az_values = _inclusive_axis(self.az_min_deg, self.az_max_deg, self.az_step_deg)
        el_values = _inclusive_axis(self.el_min_deg, self.el_max_deg, self.el_step_deg)
        return [(float(az), float(el)) for az in az_values for el in el_values]

    def to_dict(self) -> dict[str, Any]:
        return {
            "az_min_deg": self.az_min_deg,
            "az_max_deg": self.az_max_deg,
            "az_step_deg": self.az_step_deg,
            "el_min_deg": self.el_min_deg,
            "el_max_deg": self.el_max_deg,
            "el_step_deg": self.el_step_deg,
            "quantizer": self.quantizer.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CodebookConfig":
        config = cls(
            az_min_deg=float(data.get("az_min_deg", -60.0)),
            az_max_deg=float(data.get("az_max_deg", 60.0)),
            az_step_deg=float(data.get("az_step_deg", 5.0)),
            el_min_deg=float(data.get("el_min_deg", -20.0)),
            el_max_deg=float(data.get("el_max_deg", 20.0)),
            el_step_deg=float(data.get("el_step_deg", 5.0)),
            quantizer=QuantizerConfig.from_dict(data.get("quantizer", {})),
        )
        config.validate()
        return config


@dataclass
class CodebookEntry:
    beam_id: int
    target_az_deg: float
    target_el_deg: float
    weights: np.ndarray
    quantized: QuantizedWeights

    def to_dict(self) -> dict[str, Any]:
        return {
            "beam_id": self.beam_id,
            "target_az_deg": self.target_az_deg,
            "target_el_deg": self.target_el_deg,
            "weights_real": np.real(self.weights).astype(float).tolist(),
            "weights_imag": np.imag(self.weights).astype(float).tolist(),
            "attenuation_db": self.quantized.attenuation_db.astype(float).tolist(),
            "phase_deg": self.quantized.phase_deg.astype(float).tolist(),
            "phase_error_deg": self.quantized.phase_error_deg.astype(float).tolist(),
            "amplitude_error_db": self.quantized.amplitude_error_db.astype(float).tolist(),
            "clipped": self.quantized.clipped.astype(bool).tolist(),
        }


@dataclass
class Codebook:
    topology_name: str
    config: CodebookConfig
    entries: list[CodebookEntry]
    simulated: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "simulated": self.simulated,
            "topology_name": self.topology_name,
            "config": self.config.to_dict(),
            "entries": [entry.to_dict() for entry in self.entries],
        }

    def to_json(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2, sort_keys=True)
            handle.write("\n")

    def to_csv(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "beam_id",
                    "target_az_deg",
                    "target_el_deg",
                    "feed_index",
                    "weight_real",
                    "weight_imag",
                    "attenuation_db",
                    "phase_deg",
                    "phase_error_deg",
                    "amplitude_error_db",
                    "clipped",
                ]
            )
            for entry in self.entries:
                for feed_index in range(len(entry.weights)):
                    writer.writerow(
                        [
                            entry.beam_id,
                            entry.target_az_deg,
                            entry.target_el_deg,
                            feed_index,
                            float(np.real(entry.weights[feed_index])),
                            float(np.imag(entry.weights[feed_index])),
                            float(entry.quantized.attenuation_db[feed_index]),
                            float(entry.quantized.phase_deg[feed_index]),
                            float(entry.quantized.phase_error_deg[feed_index]),
                            float(entry.quantized.amplitude_error_db[feed_index]),
                            bool(entry.quantized.clipped[feed_index]),
                        ]
                    )


def generate_codebook(
    topology: Topology,
    config: CodebookConfig | None = None,
    *,
    calibration_corrections: np.ndarray | None = None,
) -> Codebook:
    """Generate a steering codebook on a rectangular azimuth/elevation grid."""

    config = config or CodebookConfig()
    config.validate()
    if calibration_corrections is not None:
        corrections = np.asarray(calibration_corrections, dtype=np.complex128)
        if corrections.shape != (topology.n_feeds,):
            raise ValueError(
                f"calibration_corrections must have shape ({topology.n_feeds},), "
                f"got {corrections.shape}"
            )
    else:
        corrections = np.ones(topology.n_feeds, dtype=np.complex128)

    entries: list[CodebookEntry] = []
    for beam_id, (az_deg, el_deg) in enumerate(config.angles()):
        weights = steering_weights(topology, az_deg, el_deg) * corrections
        quantized = quantize_weights(weights, config.quantizer)
        entries.append(
            CodebookEntry(
                beam_id=beam_id,
                target_az_deg=az_deg,
                target_el_deg=el_deg,
                weights=weights,
                quantized=quantized,
            )
        )
    return Codebook(
        topology_name=topology.name,
        config=config,
        entries=entries,
        simulated=True,
    )


def _inclusive_axis(start: float, stop: float, step: float) -> np.ndarray:
    count = int(round((stop - start) / step)) + 1
    values = start + step * np.arange(max(count, 0), dtype=float)
    return values[values <= stop + 1e-9]
