"""Hierarchical chain/feed calibration for the observable H2 architecture.

The H2 tile can measure a complex response per RF chain and a power response per
ADTR1107.  Those observations are not equivalent to one complex IQ stream per
feed.  This module keeps the chain-level and feed-level calibration layers
separate, and only uses per-feed complex data when the selected architecture
actually provides it.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from .calibration import CalibrationConfig, _estimate_path
from .measurement import FaultSpec, MismatchConfig
from .observability import (
    MeasurementArchitecture,
    get_architecture,
)
from .topology import Topology

STATUSES = ("ok", "missing", "faulty", "inconsistent")
_FLOOR_DB = -300.0


@dataclass(frozen=True)
class HierarchicalMeasurementConfig:
    seed: int = 0
    snr_db: float = 30.0
    n_captures: int = 4
    n_samples: int = 64
    pilot_amplitude: float = 1.0
    mismatch: MismatchConfig = field(default_factory=MismatchConfig)
    faults: FaultSpec = field(default_factory=FaultSpec)
    architecture: str = "h2_available"

    def validate(self) -> None:
        if self.n_captures < 1:
            raise ValueError("n_captures must be at least one")
        if self.n_samples < 2:
            raise ValueError("n_samples must be at least two")
        if self.pilot_amplitude <= 0.0:
            raise ValueError("pilot_amplitude must be positive")
        self.faults.validate()
        get_architecture(self.architecture)

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "snr_db": self.snr_db,
            "n_captures": self.n_captures,
            "n_samples": self.n_samples,
            "pilot_amplitude": self.pilot_amplitude,
            "mismatch": self.mismatch.to_dict(),
            "faults": self.faults.to_dict(),
            "architecture": self.architecture,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HierarchicalMeasurementConfig":
        config = cls(
            seed=int(data.get("seed", 0)),
            snr_db=float(data.get("snr_db", 30.0)),
            n_captures=int(data.get("n_captures", 4)),
            n_samples=int(data.get("n_samples", 64)),
            pilot_amplitude=float(data.get("pilot_amplitude", 1.0)),
            mismatch=MismatchConfig.from_dict(data.get("mismatch", {})),
            faults=FaultSpec.from_dict(data.get("faults", {})),
            architecture=str(data.get("architecture", "h2_available")),
        )
        config.validate()
        return config


@dataclass
class HierarchicalMeasurementSet:
    topology_name: str
    config: HierarchicalMeasurementConfig
    architecture: MeasurementArchitecture
    pilot: np.ndarray
    chain_iq: np.ndarray
    feed_power: np.ndarray
    feed_iq: np.ndarray | None
    truth_chain_response: np.ndarray
    truth_feed_response: np.ndarray
    truth_response: np.ndarray
    chain_fault_labels: tuple[str, ...]
    feed_fault_labels: tuple[str, ...]
    chain_cal_path_true: np.ndarray
    chain_cal_path_known: np.ndarray
    feed_cal_path_true: np.ndarray
    feed_cal_path_known: np.ndarray
    simulated: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.simulated:
            raise ValueError("this package only generates simulated measurements")
        n_chains = len(self.truth_chain_response)
        n_feeds = len(self.truth_feed_response)
        if self.chain_iq.ndim != 3 or self.chain_iq.shape[0] != n_chains:
            raise ValueError("chain_iq must have shape (n_chains, captures, samples)")
        if self.feed_power.shape != (n_feeds, self.config.n_captures):
            raise ValueError("feed_power shape does not match feeds/captures")
        if self.feed_iq is not None:
            if self.feed_iq.ndim != 3 or self.feed_iq.shape[0] != n_feeds:
                raise ValueError("feed_iq must have shape (n_feeds, captures, samples)")
            if self.feed_iq.shape[1:] != self.chain_iq.shape[1:]:
                raise ValueError("feed_iq and chain_iq capture/sample shapes differ")
        if self.truth_response.shape != (n_feeds,):
            raise ValueError("truth_response shape does not match feeds")
        if len(self.chain_fault_labels) != n_chains:
            raise ValueError("chain_fault_labels must match chains")
        if len(self.feed_fault_labels) != n_feeds:
            raise ValueError("feed_fault_labels must match feeds")
        if self.chain_cal_path_true.shape != (n_chains,):
            raise ValueError("chain_cal_path_true shape does not match chains")
        if self.chain_cal_path_known.shape != (n_chains,):
            raise ValueError("chain_cal_path_known shape does not match chains")
        if self.feed_cal_path_true.shape != (n_feeds,):
            raise ValueError("feed_cal_path_true shape does not match feeds")
        if self.feed_cal_path_known.shape != (n_feeds,):
            raise ValueError("feed_cal_path_known shape does not match feeds")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "simulated": True,
            "topology_name": self.topology_name,
            "config": self.config.to_dict(),
            "architecture": self.architecture.to_dict(),
            "pilot_real": np.real(self.pilot).tolist(),
            "pilot_imag": np.imag(self.pilot).tolist(),
            "chain_iq_real": np.real(self.chain_iq).tolist(),
            "chain_iq_imag": np.imag(self.chain_iq).tolist(),
            "feed_power": self.feed_power.tolist(),
            "feed_iq_real": (
                None if self.feed_iq is None else np.real(self.feed_iq).tolist()
            ),
            "feed_iq_imag": (
                None if self.feed_iq is None else np.imag(self.feed_iq).tolist()
            ),
            "truth_chain_response_real": np.real(self.truth_chain_response).tolist(),
            "truth_chain_response_imag": np.imag(self.truth_chain_response).tolist(),
            "truth_feed_response_real": np.real(self.truth_feed_response).tolist(),
            "truth_feed_response_imag": np.imag(self.truth_feed_response).tolist(),
            "truth_response_real": np.real(self.truth_response).tolist(),
            "truth_response_imag": np.imag(self.truth_response).tolist(),
            "chain_fault_labels": list(self.chain_fault_labels),
            "feed_fault_labels": list(self.feed_fault_labels),
            "chain_cal_path_true_real": np.real(self.chain_cal_path_true).tolist(),
            "chain_cal_path_true_imag": np.imag(self.chain_cal_path_true).tolist(),
            "chain_cal_path_known_real": np.real(self.chain_cal_path_known).tolist(),
            "chain_cal_path_known_imag": np.imag(self.chain_cal_path_known).tolist(),
            "feed_cal_path_true_real": np.real(self.feed_cal_path_true).tolist(),
            "feed_cal_path_true_imag": np.imag(self.feed_cal_path_true).tolist(),
            "feed_cal_path_known_real": np.real(self.feed_cal_path_known).tolist(),
            "feed_cal_path_known_imag": np.imag(self.feed_cal_path_known).tolist(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HierarchicalMeasurementSet":
        architecture = get_architecture(str(data["architecture"]["name"]))
        pilot = np.asarray(data["pilot_real"], dtype=float) + 1j * np.asarray(
            data["pilot_imag"], dtype=float
        )
        chain_iq = np.asarray(data["chain_iq_real"], dtype=float) + 1j * np.asarray(
            data["chain_iq_imag"], dtype=float
        )
        feed_iq = None
        if data.get("feed_iq_real") is not None:
            feed_iq = np.asarray(
                data["feed_iq_real"], dtype=float
            ) + 1j * np.asarray(data["feed_iq_imag"], dtype=float)
        measurement = cls(
            topology_name=str(data["topology_name"]),
            config=HierarchicalMeasurementConfig.from_dict(data["config"]),
            architecture=architecture,
            pilot=pilot,
            chain_iq=chain_iq,
            feed_power=np.asarray(data["feed_power"], dtype=float),
            feed_iq=feed_iq,
            truth_chain_response=_complex_array(
                data["truth_chain_response_real"], data["truth_chain_response_imag"]
            ),
            truth_feed_response=_complex_array(
                data["truth_feed_response_real"], data["truth_feed_response_imag"]
            ),
            truth_response=_complex_array(
                data["truth_response_real"], data["truth_response_imag"]
            ),
            chain_fault_labels=tuple(str(item) for item in data["chain_fault_labels"]),
            feed_fault_labels=tuple(str(item) for item in data["feed_fault_labels"]),
            chain_cal_path_true=_complex_array(
                data["chain_cal_path_true_real"], data["chain_cal_path_true_imag"]
            ),
            chain_cal_path_known=_complex_array(
                data["chain_cal_path_known_real"], data["chain_cal_path_known_imag"]
            ),
            feed_cal_path_true=_complex_array(
                data["feed_cal_path_true_real"], data["feed_cal_path_true_imag"]
            ),
            feed_cal_path_known=_complex_array(
                data["feed_cal_path_known_real"], data["feed_cal_path_known_imag"]
            ),
            simulated=bool(data.get("simulated", True)),
            metadata=dict(data.get("metadata", {})),
        )
        measurement.validate()
        return measurement

    def to_json(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2, sort_keys=True)
            handle.write("\n")

    @classmethod
    def from_json(cls, path: str | Path) -> "HierarchicalMeasurementSet":
        with Path(path).open("r", encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))


@dataclass
class ChainPathCalibration:
    chain: int
    measured_amplitude_db: float
    measured_phase_deg: float
    coherence: float
    estimated_snr_db: float
    capture_phase_std_deg: float
    capture_gain_std_db: float
    status: str
    reason: str
    correction: complex

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain": self.chain,
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
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChainPathCalibration":
        return cls(
            chain=int(data["chain"]),
            measured_amplitude_db=float(data.get("measured_amplitude_db", _FLOOR_DB)),
            measured_phase_deg=float(data.get("measured_phase_deg", 0.0)),
            coherence=float(data.get("coherence", 0.0)),
            estimated_snr_db=float(data.get("estimated_snr_db", _FLOOR_DB)),
            capture_phase_std_deg=float(data.get("capture_phase_std_deg", 0.0)),
            capture_gain_std_db=float(data.get("capture_gain_std_db", 0.0)),
            status=str(data.get("status", "faulty")),
            reason=str(data.get("reason", "unknown")),
            correction=float(data.get("correction_real", 0.0))
            + 1j * float(data.get("correction_imag", 0.0)),
        )


@dataclass
class FeedPathCalibration:
    path_index: int
    chain: int
    polarization: str
    measured_amplitude_db: float
    measured_phase_deg: float
    coherence: float
    estimated_snr_db: float
    capture_phase_std_deg: float
    capture_gain_std_db: float
    phase_observable: bool
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
            "phase_observable": self.phase_observable,
            "status": self.status,
            "reason": self.reason,
            "correction_real": float(np.real(self.correction)),
            "correction_imag": float(np.imag(self.correction)),
            "correction_amplitude": self.correction_amplitude,
            "correction_phase_deg": self.correction_phase_deg,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FeedPathCalibration":
        return cls(
            path_index=int(data["path_index"]),
            chain=int(data["chain"]),
            polarization=str(data["polarization"]),
            measured_amplitude_db=float(data.get("measured_amplitude_db", _FLOOR_DB)),
            measured_phase_deg=float(data.get("measured_phase_deg", 0.0)),
            coherence=float(data.get("coherence", 0.0)),
            estimated_snr_db=float(data.get("estimated_snr_db", _FLOOR_DB)),
            capture_phase_std_deg=float(data.get("capture_phase_std_deg", 0.0)),
            capture_gain_std_db=float(data.get("capture_gain_std_db", 0.0)),
            phase_observable=bool(data.get("phase_observable", False)),
            status=str(data.get("status", "faulty")),
            reason=str(data.get("reason", "unknown")),
            correction=float(data.get("correction_real", 0.0))
            + 1j * float(data.get("correction_imag", 0.0)),
        )


@dataclass
class HierarchicalCalibrationResult:
    topology_name: str
    architecture: MeasurementArchitecture
    config: CalibrationConfig
    chains: list[ChainPathCalibration]
    paths: list[FeedPathCalibration]
    chain_target_response: complex
    feed_target_response: complex
    seed: int | None = None
    simulated: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def n_feeds(self) -> int:
        return len(self.paths)

    @property
    def n_chains(self) -> int:
        return len(self.chains)

    @property
    def feed_phase_observable(self) -> bool:
        return self.architecture.feed_phase_observable

    @property
    def chain_corrections(self) -> np.ndarray:
        by_chain = {item.chain: item.correction for item in self.chains}
        return np.asarray([by_chain[path.chain] for path in self.paths], dtype=np.complex128)

    @property
    def feed_corrections(self) -> np.ndarray:
        return np.asarray([path.correction for path in self.paths], dtype=np.complex128)

    @property
    def corrections(self) -> np.ndarray:
        return self.chain_corrections * self.feed_corrections

    @property
    def phase_only_corrections(self) -> np.ndarray:
        corrections = np.zeros(self.n_feeds, dtype=np.complex128)
        combined = self.corrections
        healthy = self.healthy_mask
        corrections[healthy] = np.exp(1j * np.angle(combined[healthy]))
        return corrections

    @property
    def chain_healthy_mask(self) -> np.ndarray:
        by_chain = {item.chain: item.status == "ok" for item in self.chains}
        return np.asarray([by_chain[path.chain] for path in self.paths], dtype=bool)

    @property
    def healthy_mask(self) -> np.ndarray:
        feed_healthy = np.asarray([path.status == "ok" for path in self.paths], dtype=bool)
        return feed_healthy & self.chain_healthy_mask

    @property
    def status_counts(self) -> dict[str, int]:
        return {
            status: sum(path.status == status for path in self.paths)
            for status in STATUSES
        }

    @property
    def chain_status_counts(self) -> dict[str, int]:
        return {
            status: sum(chain.status == status for chain in self.chains)
            for status in STATUSES
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "simulated": True,
            "topology_name": self.topology_name,
            "architecture": self.architecture.to_dict(),
            "seed": self.seed,
            "config": self.config.to_dict(),
            "feed_phase_observable": self.feed_phase_observable,
            "chain_target_response_real": float(np.real(self.chain_target_response)),
            "chain_target_response_imag": float(np.imag(self.chain_target_response)),
            "feed_target_response_real": float(np.real(self.feed_target_response)),
            "feed_target_response_imag": float(np.imag(self.feed_target_response)),
            "chain_status_counts": self.chain_status_counts,
            "status_counts": self.status_counts,
            "chains": [item.to_dict() for item in self.chains],
            "paths": [item.to_dict() for item in self.paths],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HierarchicalCalibrationResult":
        result = cls(
            topology_name=str(data["topology_name"]),
            architecture=get_architecture(str(data["architecture"]["name"])),
            config=CalibrationConfig.from_dict(data.get("config", {})),
            chains=sorted(
                (ChainPathCalibration.from_dict(item) for item in data["chains"]),
                key=lambda item: item.chain,
            ),
            paths=sorted(
                (FeedPathCalibration.from_dict(item) for item in data["paths"]),
                key=lambda item: item.path_index,
            ),
            chain_target_response=float(data.get("chain_target_response_real", 1.0))
            + 1j * float(data.get("chain_target_response_imag", 0.0)),
            feed_target_response=float(data.get("feed_target_response_real", 1.0))
            + 1j * float(data.get("feed_target_response_imag", 0.0)),
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
    def from_json(cls, path: str | Path) -> "HierarchicalCalibrationResult":
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
            "phase_observable",
            "status",
            "reason",
            "correction_real",
            "correction_imag",
        ]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for path_calibration in self.paths:
                row = path_calibration.to_dict()
                writer.writerow({key: row[key] for key in fieldnames})


def simulate_hierarchical_measurements(
    topology: Topology,
    config: HierarchicalMeasurementConfig | None = None,
) -> HierarchicalMeasurementSet:
    """Generate chain-loopback, feed-power, and optional per-feed complex data."""

    config = config or HierarchicalMeasurementConfig()
    config.validate()
    architecture = get_architecture(config.architecture)
    (
        truth_rng,
        chain_cal_rng,
        feed_cal_rng,
        chain_noise_rng,
        feed_noise_rng,
        power_rng,
        fault_rng,
    ) = (np.random.default_rng(child) for child in np.random.SeedSequence(config.seed).spawn(7))

    mismatch = config.mismatch
    chain_ids = topology.chain_ids
    chain_index = {chain: index for index, chain in enumerate(chain_ids)}
    chain_phase = np.deg2rad(
        truth_rng.normal(0.0, mismatch.chain_phase_std_deg, size=topology.n_chains)
    )
    chain_gain_db = truth_rng.normal(
        0.0, mismatch.chain_gain_std_db, size=topology.n_chains
    )
    feed_phase = np.deg2rad(
        truth_rng.normal(0.0, mismatch.feed_phase_std_deg, size=topology.n_feeds)
    )
    feed_gain_db = truth_rng.normal(
        0.0, mismatch.feed_gain_std_db, size=topology.n_feeds
    )

    base_chain = 10.0 ** (chain_gain_db / 20.0) * np.exp(1j * chain_phase)
    base_feed = 10.0 ** (feed_gain_db / 20.0) * np.exp(1j * feed_phase)
    chain_capture = np.repeat(base_chain[:, None], config.n_captures, axis=1)
    feed_capture = np.repeat(base_feed[:, None], config.n_captures, axis=1)

    chain_fault_modes = np.asarray(
        [config.faults.chain_faults.get(chain, "ok") for chain in chain_ids], dtype=object
    )
    feed_fault_modes = np.asarray(
        [
            config.faults.path_faults.get(feed.index, "ok")
            for feed in topology.feeds
        ],
        dtype=object,
    )
    for position, chain in enumerate(chain_ids):
        _apply_fault(
            chain_capture[position],
            chain_fault_modes[position],
            config.faults,
            fault_rng,
        )
    for position, feed in enumerate(topology.feeds):
        _apply_fault(
            feed_capture[position],
            feed_fault_modes[position],
            config.faults,
            fault_rng,
        )

    truth_chain_response = np.mean(chain_capture, axis=1)
    truth_feed_response = np.mean(feed_capture, axis=1)
    truth_response = np.zeros(topology.n_feeds, dtype=np.complex128)
    for feed in topology.feeds:
        truth_response[feed.index] = (
            truth_chain_response[chain_index[feed.chain]]
            * truth_feed_response[feed.index]
        )

    chain_cal_true = 10.0 ** (
        chain_cal_rng.normal(0.0, 0.2, size=topology.n_chains) / 20.0
    ) * np.exp(1j * np.deg2rad(chain_cal_rng.normal(0.0, 5.0, size=topology.n_chains)))
    chain_cal_known = chain_cal_true * _measurement_error(
        chain_cal_rng,
        architecture.chain_cal_phase_error_std_deg,
        architecture.chain_cal_gain_error_std_db,
        topology.n_chains,
    )
    feed_cal_true = 10.0 ** (
        feed_cal_rng.normal(0.0, 0.2, size=topology.n_feeds) / 20.0
    ) * np.exp(1j * np.deg2rad(feed_cal_rng.normal(0.0, 5.0, size=topology.n_feeds)))
    feed_cal_known = feed_cal_true * _measurement_error(
        feed_cal_rng,
        architecture.per_feed_complex_phase_error_std_deg,
        architecture.per_feed_complex_gain_error_std_db,
        topology.n_feeds,
    )

    pilot = config.pilot_amplitude * np.exp(
        2j * np.pi * 0.125 * np.arange(config.n_samples, dtype=float)
    )
    pilot_power = float(np.mean(np.abs(pilot) ** 2))
    chain_iq = np.zeros(
        (topology.n_chains, config.n_captures, config.n_samples),
        dtype=np.complex128,
    )
    for position, chain in enumerate(chain_ids):
        for capture in range(config.n_captures):
            response = chain_capture[position, capture] * chain_cal_true[position]
            chain_iq[position, capture, :] = _pilot_iq(
                response,
                pilot,
                config.snr_db,
                chain_noise_rng,
            )

    feed_power = np.zeros((topology.n_feeds, config.n_captures), dtype=float)
    for feed in topology.feeds:
        position = chain_index[feed.chain]
        for capture in range(config.n_captures):
            response = (
                chain_capture[position, capture]
                * feed_capture[feed.index, capture]
            )
            power = float(abs(response) ** 2 * pilot_power)
            if power > 0.0:
                power *= 10.0 ** (
                    power_rng.normal(0.0, architecture.power_noise_std_db) / 10.0
                )
            feed_power[feed.index, capture] = power

    feed_iq = None
    if architecture.per_feed_complex:
        feed_iq = np.zeros(
            (topology.n_feeds, config.n_captures, config.n_samples),
            dtype=np.complex128,
        )
        for feed in topology.feeds:
            position = chain_index[feed.chain]
            for capture in range(config.n_captures):
                response = (
                    chain_capture[position, capture]
                    * feed_capture[feed.index, capture]
                    * feed_cal_true[feed.index]
                )
                feed_iq[feed.index, capture, :] = _pilot_iq(
                    response,
                    pilot,
                    config.snr_db,
                    feed_noise_rng,
                )

    measurement = HierarchicalMeasurementSet(
        topology_name=topology.name,
        config=config,
        architecture=architecture,
        pilot=pilot,
        chain_iq=chain_iq,
        feed_power=feed_power,
        feed_iq=feed_iq,
        truth_chain_response=truth_chain_response,
        truth_feed_response=truth_feed_response,
        truth_response=truth_response,
        chain_fault_labels=tuple(str(mode) for mode in chain_fault_modes),
        feed_fault_labels=tuple(str(mode) for mode in feed_fault_modes),
        chain_cal_path_true=chain_cal_true,
        chain_cal_path_known=chain_cal_known,
        feed_cal_path_true=feed_cal_true,
        feed_cal_path_known=feed_cal_known,
        simulated=True,
        metadata={
            "generator": "openru_x6.rfcal.hierarchical",
            "evidence_label": "SIMULATED",
            "hardware_measured": False,
            "architecture": architecture.name,
            "architecture_notes": architecture.notes,
        },
    )
    measurement.validate()
    return measurement


def calibrate_hierarchical(
    topology: Topology,
    measurement: HierarchicalMeasurementSet,
    config: CalibrationConfig | None = None,
) -> HierarchicalCalibrationResult:
    """Estimate chain and feed responses without inventing unobservable phase."""

    config = config or CalibrationConfig()
    config.validate()
    measurement.validate()
    if measurement.topology_name != topology.name:
        raise ValueError(
            f"measurement topology {measurement.topology_name!r} does not match "
            f"{topology.name!r}"
        )
    if len(measurement.truth_feed_response) != topology.n_feeds:
        raise ValueError("measurement feed count does not match topology")

    chain_ids = topology.chain_ids
    chain_index = {chain: index for index, chain in enumerate(chain_ids)}
    chain_estimates: list[dict[str, float]] = []
    chain_complex: list[complex] = []
    for position, _chain in enumerate(chain_ids):
        estimate = _estimate_path(measurement.pilot, measurement.chain_iq[position])
        deembedded = _complex_from_estimate(estimate) / _safe_complex(
            measurement.chain_cal_path_known[position]
        )
        estimate = dict(estimate)
        estimate["amplitude_db"] = _amplitude_db(deembedded)
        estimate["phase_deg"] = _phase_deg(deembedded)
        chain_estimates.append(estimate)
        chain_complex.append(deembedded)
    chain_statuses, chain_reasons = _classify_estimates(
        chain_estimates, config, phase_observable=True
    )

    feed_estimates: list[dict[str, float]] = []
    feed_complex: list[complex] = []
    for feed in topology.feeds:
        position = chain_index[feed.chain]
        chain_response = chain_complex[position]
        if measurement.architecture.per_feed_complex and measurement.feed_iq is not None:
            estimate = _estimate_path(measurement.pilot, measurement.feed_iq[feed.index])
            divisor = chain_response * measurement.feed_cal_path_known[feed.index]
            deembedded = _complex_from_estimate(estimate) / _safe_complex(divisor)
            estimate = dict(estimate)
            estimate["amplitude_db"] = _amplitude_db(deembedded)
            estimate["phase_deg"] = _phase_deg(deembedded)
        else:
            mean_power = float(np.mean(measurement.feed_power[feed.index]))
            pilot_rms = float(np.sqrt(np.mean(np.abs(measurement.pilot) ** 2)))
            denominator = abs(chain_response) * pilot_rms
            amplitude = float(np.sqrt(max(mean_power, 0.0)) / denominator) if denominator > 0 else 0.0
            powers_db = 10.0 * np.log10(
                np.maximum(measurement.feed_power[feed.index], 1e-300)
            )
            estimate = {
                "amplitude_db": _amplitude_db(amplitude),
                "phase_deg": 0.0,
                "coherence": 1.0,
                "snr_db": 0.0,
                "capture_phase_std_deg": 0.0,
                "capture_gain_std_db": (
                    float(np.std(powers_db, ddof=0)) if powers_db.size > 1 else 0.0
                ),
            }
            deembedded = _polar(amplitude, 0.0)
        feed_estimates.append(estimate)
        feed_complex.append(deembedded)

    feed_statuses, feed_reasons = _classify_estimates(
        feed_estimates,
        config,
        phase_observable=measurement.architecture.feed_phase_observable,
    )
    for feed in topology.feeds:
        chain_position = chain_index[feed.chain]
        if chain_statuses[chain_position] != "ok":
            feed_statuses[feed.index] = chain_statuses[chain_position]
            feed_reasons[feed.index] = "chain-level calibration failed"

    chain_target = _robust_target(
        [estimate for estimate, status in zip(chain_estimates, chain_statuses, strict=True) if status == "ok"]
    )
    chain_target = chain_target if chain_target != 0.0 else 1.0 + 0.0j
    feed_healthy = [
        estimate
        for estimate, status in zip(feed_estimates, feed_statuses, strict=True)
        if status == "ok"
    ]
    if not feed_healthy:
        raise ValueError("hierarchical calibration failed: no healthy feed paths")
    if measurement.architecture.feed_phase_observable:
        feed_target = _robust_target(feed_healthy)
    else:
        feed_target = complex(
            float(np.mean([10.0 ** (item["amplitude_db"] / 20.0) for item in feed_healthy])),
            0.0,
        )
    if feed_target == 0.0:
        feed_target = 1.0 + 0.0j

    chain_corrections: dict[int, complex] = {}
    for position, chain in enumerate(chain_ids):
        if chain_statuses[position] == "ok" and chain_complex[position] != 0.0:
            chain_corrections[chain] = chain_target / chain_complex[position]
        else:
            chain_corrections[chain] = 0.0 + 0.0j

    path_results: list[FeedPathCalibration] = []
    for feed, estimate, status, reason, measured in zip(
        topology.feeds,
        feed_estimates,
        feed_statuses,
        feed_reasons,
        feed_complex,
        strict=True,
    ):
        chain_ok = chain_statuses[chain_index[feed.chain]] == "ok"
        correction = 0.0 + 0.0j
        if status == "ok" and chain_ok and measured != 0.0:
            if measurement.architecture.feed_phase_observable:
                correction = feed_target / measured
            else:
                target_amplitude = abs(feed_target)
                correction = target_amplitude / abs(measured) + 0.0j
        path_results.append(
            FeedPathCalibration(
                path_index=feed.index,
                chain=feed.chain,
                polarization=feed.polarization,
                measured_amplitude_db=float(estimate["amplitude_db"]),
                measured_phase_deg=float(estimate["phase_deg"]),
                coherence=float(estimate["coherence"]),
                estimated_snr_db=float(estimate["snr_db"]),
                capture_phase_std_deg=float(estimate["capture_phase_std_deg"]),
                capture_gain_std_db=float(estimate["capture_gain_std_db"]),
                phase_observable=measurement.architecture.feed_phase_observable,
                status=status,
                reason=reason,
                correction=correction,
            )
        )

    chain_results = [
        ChainPathCalibration(
            chain=chain,
            measured_amplitude_db=float(estimate["amplitude_db"]),
            measured_phase_deg=float(estimate["phase_deg"]),
            coherence=float(estimate["coherence"]),
            estimated_snr_db=float(estimate["snr_db"]),
            capture_phase_std_deg=float(estimate["capture_phase_std_deg"]),
            capture_gain_std_db=float(estimate["capture_gain_std_db"]),
            status=status,
            reason=reason,
            correction=chain_corrections[chain],
        )
        for chain, estimate, status, reason in zip(
            chain_ids, chain_estimates, chain_statuses, chain_reasons, strict=True
        )
    ]

    result = HierarchicalCalibrationResult(
        topology_name=topology.name,
        architecture=measurement.architecture,
        config=config,
        chains=chain_results,
        paths=path_results,
        chain_target_response=chain_target,
        feed_target_response=feed_target,
        seed=measurement.config.seed,
        simulated=True,
        metadata={
            "generator": "openru_x6.rfcal.hierarchical",
            "evidence_label": "SIMULATED",
            "hardware_measured": False,
            "architecture": measurement.architecture.name,
            "architecture_notes": measurement.architecture.notes,
        },
    )
    _validate_result(result)
    return result


def apply_hierarchical_calibration(
    weights: np.ndarray,
    calibration: HierarchicalCalibrationResult,
    *,
    mode: str = "equalize",
) -> np.ndarray:
    """Apply chain-only or combined chain/feed corrections to beam weights."""

    weights = np.asarray(weights, dtype=np.complex128)
    if weights.shape != (calibration.n_feeds,):
        raise ValueError(
            f"weights must have shape ({calibration.n_feeds},), got {weights.shape}"
        )
    if mode == "none":
        corrections = np.ones(calibration.n_feeds, dtype=np.complex128)
    elif mode == "chain_only":
        corrections = calibration.chain_corrections
    elif mode == "equalize":
        corrections = calibration.corrections
    elif mode == "phase_only":
        corrections = calibration.phase_only_corrections
    else:
        raise ValueError(f"unsupported hierarchical calibration mode: {mode}")
    return weights * corrections


def hierarchical_calibration_accuracy(
    truth_response: np.ndarray,
    calibration: HierarchicalCalibrationResult,
) -> dict[str, float]:
    """Measure residual error after the observable correction is applied."""

    truth = np.asarray(truth_response, dtype=np.complex128)
    corrected = truth * calibration.corrections
    healthy = calibration.healthy_mask
    values = corrected[healthy]
    if values.size == 0:
        return {"phase_error_deg": float("nan"), "gain_error_db": float("nan")}
    reference_phase = float(np.angle(np.mean(np.exp(1j * np.angle(values)))))
    reference_gain_db = float(
        np.mean(20.0 * np.log10(np.maximum(np.abs(values), 1e-300)))
    )
    phase_error = np.rad2deg(np.angle(np.exp(1j * (np.angle(values) - reference_phase))))
    gain_error = 20.0 * np.log10(np.maximum(np.abs(values), 1e-300)) - reference_gain_db
    return {
        "phase_error_deg": float(np.sqrt(np.mean(phase_error**2))),
        "gain_error_db": float(np.sqrt(np.mean(gain_error**2))),
    }


def _apply_fault(
    capture_response: np.ndarray,
    mode: str,
    faults: FaultSpec,
    rng: np.random.Generator,
) -> None:
    if mode == "missing":
        capture_response[:] = 0.0
    elif mode == "faulty":
        capture_response[:] *= 10.0 ** (faults.faulty_gain_db / 20.0) * np.exp(
            1j * np.deg2rad(faults.faulty_phase_deg)
        )
    elif mode == "inconsistent":
        for capture in range(capture_response.size):
            capture_response[capture] *= 10.0 ** (
                rng.normal(0.0, faults.inconsistent_gain_std_db) / 20.0
            ) * np.exp(1j * np.deg2rad(rng.normal(0.0, faults.inconsistent_phase_std_deg)))
    elif mode != "ok":
        raise ValueError(f"unsupported fault mode: {mode}")


def _pilot_iq(
    response: complex,
    pilot: np.ndarray,
    snr_db: float,
    rng: np.random.Generator,
) -> np.ndarray:
    if response == 0.0:
        return np.zeros_like(pilot, dtype=np.complex128)
    signal_power = abs(response) ** 2 * float(np.mean(np.abs(pilot) ** 2))
    noise_power = signal_power / (10.0 ** (snr_db / 10.0))
    noise = np.sqrt(noise_power / 2.0) * (
        rng.normal(size=pilot.size) + 1j * rng.normal(size=pilot.size)
    )
    return response * pilot + noise


def _measurement_error(
    rng: np.random.Generator,
    phase_std_deg: float,
    gain_std_db: float,
    size: int,
) -> np.ndarray:
    if phase_std_deg == 0.0 and gain_std_db == 0.0:
        return np.ones(size, dtype=np.complex128)
    return 10.0 ** (rng.normal(0.0, gain_std_db, size=size) / 20.0) * np.exp(
        1j * np.deg2rad(rng.normal(0.0, phase_std_deg, size=size))
    )


def _classify_estimates(
    estimates: list[dict[str, float]],
    config: CalibrationConfig,
    *,
    phase_observable: bool,
) -> tuple[list[str], list[str]]:
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

    statuses: list[str] = []
    reasons: list[str] = []
    for index, _estimate in enumerate(estimates):
        phase_error_deg = abs(_wrap_deg(phases_deg[index] - reference_phase_deg))
        gain_error_db = abs(amplitudes_db[index] - reference_amplitude_db)
        if initial_missing[index]:
            status, reason = (
                "missing",
                "amplitude below the healthy-path median by the missing threshold",
            )
        elif initial_inconsistent[index]:
            status, reason = "inconsistent", "pilot coherence below threshold"
        elif phase_stds[index] > config.inconsistent_phase_std_deg:
            status, reason = "inconsistent", "capture-to-capture phase variation above threshold"
        elif gain_stds[index] > config.inconsistent_gain_std_db:
            status, reason = "inconsistent", "capture-to-capture gain variation above threshold"
        elif gain_error_db > config.faulty_gain_deviation_db or (
            phase_observable and phase_error_deg > config.faulty_phase_deviation_deg
        ):
            status, reason = "faulty", "amplitude or phase outlier relative to healthy-path median"
        else:
            status, reason = "ok", "within calibration thresholds"
        statuses.append(status)
        reasons.append(reason)
    return statuses, reasons


def _robust_target(estimates: list[dict[str, float]]) -> complex:
    if not estimates:
        return 0.0 + 0.0j
    amplitudes_db = np.asarray([item["amplitude_db"] for item in estimates])
    phases_deg = np.asarray([item["phase_deg"] for item in estimates])
    amplitude = float(10.0 ** (np.mean(amplitudes_db) / 20.0))
    phase = float(np.angle(np.mean(np.exp(1j * np.deg2rad(phases_deg)))))
    return _polar(amplitude, phase)


def _complex_from_estimate(estimate: dict[str, float]) -> complex:
    return _polar(
        10.0 ** (estimate["amplitude_db"] / 20.0),
        np.deg2rad(estimate["phase_deg"]),
    )


def _polar(amplitude: float, phase_rad: float) -> complex:
    if amplitude <= 0.0:
        return 0.0 + 0.0j
    return complex(amplitude * np.exp(1j * phase_rad))


def _amplitude_db(value: complex) -> float:
    amplitude = abs(value)
    return 20.0 * np.log10(amplitude) if amplitude > 0.0 else _FLOOR_DB


def _phase_deg(value: complex) -> float:
    return float(np.rad2deg(np.angle(value))) if abs(value) > 0.0 else 0.0


def _safe_complex(value: complex) -> complex:
    return value if value != 0.0 else 1.0 + 0.0j


def _complex_array(real: Any, imag: Any) -> np.ndarray:
    return np.asarray(real, dtype=float) + 1j * np.asarray(imag, dtype=float)


def _validate_result(result: HierarchicalCalibrationResult) -> None:
    if sorted(path.path_index for path in result.paths) != list(range(len(result.paths))):
        raise ValueError("calibration path indices must be contiguous from zero")
    if sorted(item.chain for item in result.chains) != sorted(
        {path.chain for path in result.paths}
    ):
        raise ValueError("chain calibration entries do not match feed chains")
    for path in result.paths:
        if path.status not in STATUSES:
            raise ValueError(f"unsupported calibration status: {path.status}")
    for chain in result.chains:
        if chain.status not in STATUSES:
            raise ValueError(f"unsupported chain status: {chain.status}")


def _wrap_deg(value: float) -> float:
    return (value + 180.0) % 360.0 - 180.0
