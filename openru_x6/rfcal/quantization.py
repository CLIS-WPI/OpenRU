"""Configurable phase and gain quantization for the beamformer model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class QuantizerConfig:
    """Quantization constraints.

    The defaults reflect reported ADAR1000 capabilities: a roughly 2.8 degree
    phase step, 0.5 dB gain steps, and at least 31 dB of gain range.  They are
    software constraints only and are not a qualification of the device at
    8.4 GHz.
    """

    phase_step_deg: float = 360.0 / 128.0
    gain_step_db: float = 0.5
    gain_range_db: float = 31.0
    name: str = "adar1000-reported"
    source: str = "H1.1 reported 2.8 deg phase step, 0.5 dB gain step, >=31 dB range"

    def validate(self) -> None:
        if not np.isfinite(self.phase_step_deg) or self.phase_step_deg <= 0:
            raise ValueError("phase_step_deg must be finite and positive")
        if not np.isfinite(self.gain_step_db) or self.gain_step_db <= 0:
            raise ValueError("gain_step_db must be finite and positive")
        if not np.isfinite(self.gain_range_db) or self.gain_range_db < 0:
            raise ValueError("gain_range_db must be finite and non-negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "phase_step_deg": self.phase_step_deg,
            "gain_step_db": self.gain_step_db,
            "gain_range_db": self.gain_range_db,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QuantizerConfig":
        config = cls(
            phase_step_deg=float(data.get("phase_step_deg", 360.0 / 128.0)),
            gain_step_db=float(data.get("gain_step_db", 0.5)),
            gain_range_db=float(data.get("gain_range_db", 31.0)),
            name=str(data.get("name", "custom")),
            source=str(data.get("source", "custom quantizer")),
        )
        config.validate()
        return config


@dataclass
class QuantizedWeights:
    """Complex weights after phase and attenuation quantization."""

    weights: np.ndarray
    attenuation_db: np.ndarray
    phase_deg: np.ndarray
    phase_error_deg: np.ndarray
    amplitude_error_db: np.ndarray
    clipped: np.ndarray
    peak_scale: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "weights_real": np.real(self.weights).astype(float).tolist(),
            "weights_imag": np.imag(self.weights).astype(float).tolist(),
            "attenuation_db": self.attenuation_db.astype(float).tolist(),
            "phase_deg": self.phase_deg.astype(float).tolist(),
            "phase_error_deg": self.phase_error_deg.astype(float).tolist(),
            "amplitude_error_db": self.amplitude_error_db.astype(float).tolist(),
            "clipped": self.clipped.astype(bool).tolist(),
            "peak_scale": float(self.peak_scale),
        }


def quantize_weights(
    weights: np.ndarray,
    config: QuantizerConfig | None = None,
    *,
    normalize_peak: bool = True,
) -> QuantizedWeights:
    """Quantize complex weights to the configured phase and gain grid.

    Attenuation is represented relative to the largest requested feed
    amplitude.  A common RF-chain gain can therefore be applied outside this
    model without changing the relative array excitation.
    """

    config = config or QuantizerConfig()
    config.validate()
    weights = np.asarray(weights, dtype=np.complex128)
    if weights.ndim != 1:
        raise ValueError("weights must be a one-dimensional complex array")
    if not np.all(np.isfinite(weights)):
        raise ValueError("weights must be finite")

    amplitudes = np.abs(weights)
    peak = float(np.max(amplitudes)) if amplitudes.size else 0.0
    scale = peak if normalize_peak and peak > 0 else 1.0
    normalized = weights / scale

    normalized_amplitudes = np.abs(normalized)
    with np.errstate(divide="ignore", invalid="ignore"):
        requested_attenuation_db = np.where(
            normalized_amplitudes > 0,
            -20.0 * np.log10(np.maximum(normalized_amplitudes, np.finfo(float).tiny)),
            config.gain_range_db,
        )
    clipped = (requested_attenuation_db > config.gain_range_db) | (
        requested_attenuation_db < 0.0
    )
    bounded_attenuation_db = np.minimum(requested_attenuation_db, config.gain_range_db)
    quantized_attenuation_db = (
        np.round(bounded_attenuation_db / config.gain_step_db) * config.gain_step_db
    )
    quantized_attenuation_db = np.clip(
        quantized_attenuation_db, 0.0, config.gain_range_db
    )

    phase_rad = np.angle(normalized)
    phase_step_rad = np.deg2rad(config.phase_step_deg)
    quantized_phase_rad = np.round(phase_rad / phase_step_rad) * phase_step_rad
    phase_error_rad = _wrap_angle(quantized_phase_rad - phase_rad)

    quantized_amplitudes = 10.0 ** (-quantized_attenuation_db / 20.0)
    quantized_weights = quantized_amplitudes * np.exp(1j * quantized_phase_rad)
    quantized_weights = np.where(normalized_amplitudes > 0, quantized_weights, 0.0)

    with np.errstate(divide="ignore", invalid="ignore"):
        amplitude_error_db = np.where(
            normalized_amplitudes > 0,
            20.0
            * np.log10(
                np.maximum(quantized_amplitudes, np.finfo(float).tiny)
                / np.maximum(normalized_amplitudes, np.finfo(float).tiny)
            ),
            0.0,
        )

    return QuantizedWeights(
        weights=quantized_weights.astype(np.complex128),
        attenuation_db=quantized_attenuation_db.astype(float),
        phase_deg=np.rad2deg(_wrap_angle(quantized_phase_rad)).astype(float),
        phase_error_deg=np.rad2deg(phase_error_rad).astype(float),
        amplitude_error_db=amplitude_error_db.astype(float),
        clipped=clipped.astype(bool),
        peak_scale=float(scale),
    )


def _wrap_angle(angle_rad: np.ndarray) -> np.ndarray:
    return (angle_rad + np.pi) % (2.0 * np.pi) - np.pi
