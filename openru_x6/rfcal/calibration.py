"""Per-path calibration and fault detection from synthetic pilot IQ."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from .measurement import MeasurementSet
from .topology import Topology

STATUSES = ("ok", "missing", "faulty", "inconsistent")
_FLOOR_DB = -300.0


@dataclass(frozen=True)
class CalibrationConfig:
    """Thresholds for robust per-path estimation and fault classification."""

    missing_relative_db: float = 30.0
    faulty_gain_deviation_db: float = 6.0
    faulty_phase_deviation_deg: float = 40.0
    inconsistent_phase_std_deg: float = 15.0
    inconsistent_gain_std_db: float = 2.0
    min_coherence: float = 0.5

    def validate(self) -> None:
        if self.missing_relative_db <= 0:
            raise ValueError("missing_relative_db must be positive")
        if self.faulty_gain_deviation_db <= 0:
            raise ValueError("faulty_gain_deviation_db must be positive")
        if self.faulty_phase_deviation_deg <= 0:
            raise ValueError("faulty_phase_deviation_deg must be positive")
        if self.inconsistent_phase_std_deg <= 0:
            raise ValueError("inconsistent_phase_std_deg must be positive")
        if self.inconsistent_gain_std_db <= 0:
            raise ValueError("inconsistent_gain_std_db must be positive")
        if not (0.0 < self.min_coherence <= 1.0):
            raise ValueError("min_coherence must be in (0, 1]")

    def to_dict(self) -> dict[str, Any]:
        return {
            "missing_relative_db": self.missing_relative_db,
            "faulty_gain_deviation_db": self.faulty_gain_deviation_db,
            "faulty_phase_deviation_deg": self.faulty_phase_deviation_deg,
            "inconsistent_phase_std_deg": self.inconsistent_phase_std_deg,
            "inconsistent_gain_std_db": self.inconsistent_gain_std_db,
            "min_coherence": self.min_coherence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "CalibrationConfig":
        data = data or {}
        config = cls(
            missing_relative_db=float(data.get("missing_relative_db", 30.0)),
            faulty_gain_deviation_db=float(data.get("faulty_gain_deviation_db", 6.0)),
            faulty_phase_deviation_deg=float(
                data.get("faulty_phase_deviation_deg", 40.0)
            ),
            inconsistent_phase_std_deg=float(
                data.get("inconsistent_phase_std_deg", 15.0)
            ),
            inconsistent_gain_std_db=float(
                data.get("inconsistent_gain_std_db", 2.0)
            ),
            min_coherence=float(data.get("min_coherence", 0.5)),
        )
        config.validate()
        return config


@dataclass
class PathCalibration:
    path_index: int
    chain: int
    polarization: str
    measured_amplitude_db: float
    measured_phase_deg: float
    coherence: float
    estimated_snr_db: float
    capture_phase_std_deg: float
    capture_gain_std_db: float
    status: str
    reason: str
    correction: complex

    @property
    def correction_amplitude(self) -> float:
        return float(abs(self.correction))

    @property
    def correction_phase_deg(self) -> float:
        return float(np.rad2deg(np.angle(self.correction)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "path_index": self.path_index,
            "chain": self.chain,
            "polarization": self.polarization,
            "measured_amplitude_db": self.measured_amplitude_db,
            "measured_phase_deg": self.measured_phase_deg,
            "coherence": self.coherence,
            "estimated_snr_db": self.estimated_snr_db,
            "capture_phase_std_deg": self.capture_phase_std_deg,
            "capture_gain_std_db": self.capture_gain_std_db,
            "status": self.status,
            "reason": self.reason,
            "correction_real": float(np.real(self.correction)),
            "correction_imag": float(np.imag(self.correction)),
            "correction_amplitude": self.correction_amplitude,
            "correction_phase_deg": self.correction_phase_deg,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PathCalibration":
        correction = float(data.get("correction_real", 0.0)) + 1j * float(
            data.get("correction_imag", 0.0)
        )
        path = cls(
            path_index=int(data["path_index"]),
            chain=int(data["chain"]),
            polarization=str(data["polarization"]),
            measured_amplitude_db=float(data.get("measured_amplitude_db", _FLOOR_DB)),
            measured_phase_deg=float(data.get("measured_phase_deg", 0.0)),
            coherence=float(data.get("coherence", 0.0)),
            estimated_snr_db=float(data.get("estimated_snr_db", _FLOOR_DB)),
            capture_phase_std_deg=float(data.get("capture_phase_std_deg", 0.0)),
            capture_gain_std_db=float(data.get("capture_gain_std_db", 0.0)),
            status=str(data.get("status", "faulty")),
            reason=str(data.get("reason", "unknown")),
            correction=correction,
        )
        if path.status not in STATUSES:
            raise ValueError(f"unsupported calibration status: {path.status}")
        return path


@dataclass
class CalibrationResult:
    topology_name: str
    config: CalibrationConfig
    paths: list[PathCalibration]
    target_response: complex
    seed: int | None = None
    simulated: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def n_feeds(self) -> int:
        return len(self.paths)

    @property
    def corrections(self) -> np.ndarray:
        return np.asarray([path.correction for path in self.paths], dtype=np.complex128)

    @property
    def phase_only_corrections(self) -> np.ndarray:
        """Unit-magnitude corrections that align phases without attenuation."""

        corrections = np.zeros(self.n_feeds, dtype=np.complex128)
        target_phase = float(np.angle(self.target_response))
        for path in self.paths:
            if path.status == "ok":
                corrections[path.path_index] = np.exp(
                    1j * (target_phase - np.deg2rad(path.measured_phase_deg))
                )
        return corrections

    @property
    def healthy_mask(self) -> np.ndarray:
        return np.asarray([path.status == "ok" for path in self.paths], dtype=bool)

    @property
    def status_counts(self) -> dict[str, int]:
        return {
            status: sum(path.status == status for path in self.paths)
            for status in STATUSES
        }

    @property
    def pre_calibration_phase_spread_deg(self) -> float:
        healthy = [path for path in self.paths if path.status == "ok"]
        if not healthy:
            return float("nan")
        angles = np.deg2rad([path.measured_phase_deg for path in healthy])
        return _circular_std_deg(angles)

    @property
    def pre_calibration_gain_spread_db(self) -> float:
        healthy = [path for path in self.paths if path.status == "ok"]
        if not healthy:
            return float("nan")
        amplitudes = np.asarray([path.measured_amplitude_db for path in healthy])
        return float(np.std(amplitudes, ddof=0))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "simulated": True,
            "topology_name": self.topology_name,
            "seed": self.seed,
            "config": self.config.to_dict(),
            "target_response_real": float(np.real(self.target_response)),
            "target_response_imag": float(np.imag(self.target_response)),
            "target_amplitude_db": float(
                20.0 * np.log10(max(abs(self.target_response), 1e-300))
            ),
            "target_phase_deg": float(np.rad2deg(np.angle(self.target_response))),
            "status_counts": self.status_counts,
            "pre_calibration_phase_spread_deg": self.pre_calibration_phase_spread_deg,
            "pre_calibration_gain_spread_db": self.pre_calibration_gain_spread_db,
            "paths": [path.to_dict() for path in self.paths],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CalibrationResult":
        target = float(data.get("target_response_real", 1.0)) + 1j * float(
            data.get("target_response_imag", 0.0)
        )
        result = cls(
            topology_name=str(data["topology_name"]),
            config=CalibrationConfig.from_dict(data.get("config", {})),
            paths=sorted(
                (PathCalibration.from_dict(item) for item in data["paths"]),
                key=lambda path: path.path_index,
            ),
            target_response=target,
            seed=None if data.get("seed") is None else int(data["seed"]),
            simulated=bool(data.get("simulated", True)),
            metadata=dict(data.get("metadata", {})),
        )
        _validate_result(result)
        return result

    def to_json(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2, sort_keys=True)
            handle.write("\n")

    @classmethod
    def from_json(cls, path: str | Path) -> "CalibrationResult":
        with Path(path).open("r", encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))

    def to_csv(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "path_index",
            "chain",
            "polarization",
            "measured_amplitude_db",
            "measured_phase_deg",
            "coherence",
            "estimated_snr_db",
            "capture_phase_std_deg",
            "capture_gain_std_db",
            "status",
            "reason",
            "correction_real",
            "correction_imag",
            "correction_amplitude",
            "correction_phase_deg",
        ]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for path_calibration in self.paths:
                row = path_calibration.to_dict()
                writer.writerow({key: row[key] for key in fieldnames})

    @classmethod
    def from_csv(
        cls,
        path: str | Path,
        *,
        topology_name: str = "from-csv",
        config: CalibrationConfig | None = None,
    ) -> "CalibrationResult":
        with Path(path).open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if not rows:
            raise ValueError(f"calibration CSV {path} is empty")
        paths = sorted(
            (PathCalibration.from_dict(row) for row in rows),
            key=lambda path: path.path_index,
        )
        healthy = [path for path in paths if path.status == "ok"]
        if not healthy:
            raise ValueError("calibration CSV has no healthy paths")
        corrected = []
        for path in healthy:
            measured = 10.0 ** (path.measured_amplitude_db / 20.0) * np.exp(
                1j * np.deg2rad(path.measured_phase_deg)
            )
            corrected.append(measured * path.correction)
        target = complex(np.mean(corrected))
        result = cls(
            topology_name=topology_name,
            config=config or CalibrationConfig(),
            paths=paths,
            target_response=target,
            seed=None,
            simulated=True,
            metadata={"source": str(path), "target_note": "mean correction"},
        )
        _validate_result(result)
        return result


def calibrate(
    topology: Topology,
    measurement: MeasurementSet,
    config: CalibrationConfig | None = None,
) -> CalibrationResult:
    """Estimate per-path responses, classify faults, and form corrections."""

    config = config or CalibrationConfig()
    config.validate()
    measurement.validate()
    if measurement.topology_name != topology.name:
        raise ValueError(
            f"measurement topology {measurement.topology_name!r} does not match "
            f"{topology.name!r}"
        )
    if measurement.n_feeds != topology.n_feeds:
        raise ValueError("measurement feed count does not match topology")

    estimates = [
        _estimate_path(measurement.pilot, measurement.iq[feed.index])
        for feed in topology.feeds
    ]
    amplitudes_db = np.asarray([item["amplitude_db"] for item in estimates])
    phases_deg = np.asarray([item["phase_deg"] for item in estimates])
    coherences = np.asarray([item["coherence"] for item in estimates])
    phase_stds = np.asarray([item["capture_phase_std_deg"] for item in estimates])
    gain_stds = np.asarray([item["capture_gain_std_db"] for item in estimates])

    finite_amplitudes = amplitudes_db[amplitudes_db > _FLOOR_DB]
    median_amplitude_db = (
        float(np.median(finite_amplitudes)) if finite_amplitudes.size else _FLOOR_DB
    )
    initial_missing = amplitudes_db <= max(
        median_amplitude_db - config.missing_relative_db, _FLOOR_DB + 1.0
    )
    initial_inconsistent = coherences < config.min_coherence

    candidate_mask = ~initial_missing
    if np.any(candidate_mask):
        candidate_phases = np.deg2rad(phases_deg[candidate_mask])
        reference_phase_deg = float(
            np.rad2deg(np.angle(np.mean(np.exp(1j * candidate_phases))))
        )
        reference_amplitude_db = float(np.median(amplitudes_db[candidate_mask]))
    else:
        reference_phase_deg = 0.0
        reference_amplitude_db = _FLOOR_DB

    path_results: list[PathCalibration] = []
    for feed, estimate in zip(topology.feeds, estimates, strict=True):
        phase_error_deg = abs(_wrap_deg(estimate["phase_deg"] - reference_phase_deg))
        gain_error_db = abs(estimate["amplitude_db"] - reference_amplitude_db)
        if initial_missing[feed.index]:
            status = "missing"
            reason = "amplitude below the healthy-path median by the missing threshold"
        elif initial_inconsistent[feed.index]:
            status = "inconsistent"
            reason = "pilot coherence below threshold"
        elif phase_stds[feed.index] > config.inconsistent_phase_std_deg:
            status = "inconsistent"
            reason = "capture-to-capture phase variation above threshold"
        elif gain_stds[feed.index] > config.inconsistent_gain_std_db:
            status = "inconsistent"
            reason = "capture-to-capture gain variation above threshold"
        elif (
            gain_error_db > config.faulty_gain_deviation_db
            or phase_error_deg > config.faulty_phase_deviation_deg
        ):
            status = "faulty"
            reason = "amplitude or phase outlier relative to healthy-path median"
        else:
            status = "ok"
            reason = "within calibration thresholds"

        path_results.append(
            PathCalibration(
                path_index=feed.index,
                chain=feed.chain,
                polarization=feed.polarization,
                measured_amplitude_db=float(estimate["amplitude_db"]),
                measured_phase_deg=float(estimate["phase_deg"]),
                coherence=float(estimate["coherence"]),
                estimated_snr_db=float(estimate["snr_db"]),
                capture_phase_std_deg=float(estimate["capture_phase_std_deg"]),
                capture_gain_std_db=float(estimate["capture_gain_std_db"]),
                status=status,
                reason=reason,
                correction=0.0 + 0.0j,
            )
        )

    healthy = [path for path in path_results if path.status == "ok"]
    if not healthy:
        raise ValueError("calibration failed: no healthy RF paths")

    target_amplitude = float(
        10.0 ** (np.mean([path.measured_amplitude_db for path in healthy]) / 20.0)
    )
    target_phase_rad = float(
        np.angle(
            np.mean(
                np.exp(
                    1j * np.deg2rad([path.measured_phase_deg for path in healthy])
                )
            )
        )
    )
    target_response = target_amplitude * np.exp(1j * target_phase_rad)
    for path in path_results:
        if path.status == "ok":
            measured = 10.0 ** (path.measured_amplitude_db / 20.0) * np.exp(
                1j * np.deg2rad(path.measured_phase_deg)
            )
            path.correction = target_response / measured

    result = CalibrationResult(
        topology_name=topology.name,
        config=config,
        paths=path_results,
        target_response=target_response,
        seed=measurement.config.seed,
        simulated=True,
        metadata={
            "generator": "openru_x6.rfcal.calibration",
            "evidence_label": "SIMULATED",
            "hardware_measured": False,
            "measurement_snr_db": measurement.config.snr_db,
            "measurement_captures": measurement.config.n_captures,
            "measurement_samples": measurement.config.n_samples,
        },
    )
    _validate_result(result)
    return result


def corrections_for_mode(
    calibration: CalibrationResult, mode: str = "equalize"
) -> np.ndarray:
    """Return calibration corrections for a supported application mode."""

    if mode == "equalize":
        return calibration.corrections
    if mode == "phase_only":
        return calibration.phase_only_corrections
    if mode == "none":
        return np.ones(calibration.n_feeds, dtype=np.complex128)
    raise ValueError(f"unsupported calibration mode: {mode}")


def apply_calibration(
    weights: np.ndarray,
    calibration: CalibrationResult,
    *,
    mode: str = "equalize",
) -> np.ndarray:
    """Apply calibration corrections to complex beam weights."""

    weights = np.asarray(weights, dtype=np.complex128)
    if weights.shape != (calibration.n_feeds,):
        raise ValueError(
            f"weights must have shape ({calibration.n_feeds},), got {weights.shape}"
        )
    return weights * corrections_for_mode(calibration, mode)


def _estimate_path(pilot: np.ndarray, iq: np.ndarray) -> dict[str, float]:
    pilot = np.asarray(pilot, dtype=np.complex128)
    iq = np.asarray(iq, dtype=np.complex128)
    pilot_energy = float(np.sum(np.abs(pilot) ** 2))
    captures = iq.shape[0]
    capture_responses = np.zeros(captures, dtype=np.complex128)
    residual_power = 0.0
    signal_power = 0.0
    for capture in range(captures):
        samples = iq[capture]
        response = np.sum(np.conj(pilot) * samples) / pilot_energy
        capture_responses[capture] = response
        residual = samples - response * pilot
        residual_power += float(np.mean(np.abs(residual) ** 2))
        signal_power += float(abs(response) ** 2 * np.mean(np.abs(pilot) ** 2))
    response = np.mean(capture_responses)
    amplitude = float(abs(response))
    amplitude_db = 20.0 * np.log10(amplitude) if amplitude > 0 else _FLOOR_DB
    phase_deg = float(np.rad2deg(np.angle(response))) if amplitude > 0 else 0.0

    signal_energy = float(np.sum(np.abs(iq) ** 2))
    coherent = np.sum(np.conj(pilot)[None, :] * iq)
    denominator = np.sqrt(pilot_energy * signal_energy) if signal_energy > 0 else 0.0
    coherence = float(abs(coherent) / denominator) if denominator > 0 else 0.0
    coherence = float(np.clip(coherence, 0.0, 1.0))

    noise_power = residual_power / captures
    signal_power = signal_power / captures
    if noise_power > 0 and signal_power > 0:
        snr_db = float(10.0 * np.log10(signal_power / noise_power))
    elif signal_power > 0:
        snr_db = 300.0
    else:
        snr_db = _FLOOR_DB

    capture_phases = np.angle(capture_responses[capture_responses != 0])
    capture_phase_std_deg = (
        _circular_std_deg(capture_phases) if capture_phases.size > 1 else 0.0
    )
    nonzero_amplitudes = np.abs(capture_responses[capture_responses != 0])
    capture_gain_std_db = (
        float(np.std(20.0 * np.log10(nonzero_amplitudes), ddof=0))
        if nonzero_amplitudes.size > 1
        else 0.0
    )

    return {
        "amplitude_db": float(amplitude_db),
        "phase_deg": float(phase_deg),
        "coherence": coherence,
        "snr_db": snr_db,
        "capture_phase_std_deg": float(capture_phase_std_deg),
        "capture_gain_std_db": float(capture_gain_std_db),
    }


def _validate_result(result: CalibrationResult) -> None:
    if sorted(path.path_index for path in result.paths) != list(range(len(result.paths))):
        raise ValueError("calibration path indices must be contiguous from zero")
    for path in result.paths:
        if path.status not in STATUSES:
            raise ValueError(f"unsupported calibration status: {path.status}")
    if not np.isfinite(result.target_response):
        raise ValueError("target_response must be finite")


def _wrap_deg(value: float) -> float:
    return (value + 180.0) % 360.0 - 180.0


def _circular_std_deg(angles_rad: np.ndarray) -> float:
    if angles_rad.size == 0:
        return 0.0
    resultant = abs(np.mean(np.exp(1j * angles_rad)))
    resultant = float(np.clip(resultant, np.finfo(float).tiny, 1.0))
    return float(np.rad2deg(np.sqrt(-2.0 * np.log(resultant))))
