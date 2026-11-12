"""Synthetic complex-IQ measurement emulator.

Every measurement produced here is simulated.  The emulator is intentionally
separate from any transmit, RFIC register, or hardware-control code path.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from .topology import Topology

FAULT_MODES = ("ok", "missing", "faulty", "inconsistent")


@dataclass(frozen=True)
class MismatchConfig:
    """Random path mismatch used by the synthetic emulator."""

    chain_phase_std_deg: float = 8.0
    chain_gain_std_db: float = 1.0
    feed_phase_std_deg: float = 5.0
    feed_gain_std_db: float = 0.5

    def scaled(self, scale: float) -> "MismatchConfig":
        if not np.isfinite(scale) or scale < 0:
            raise ValueError("mismatch scale must be finite and non-negative")
        return MismatchConfig(
            chain_phase_std_deg=self.chain_phase_std_deg * scale,
            chain_gain_std_db=self.chain_gain_std_db * scale,
            feed_phase_std_deg=self.feed_phase_std_deg * scale,
            feed_gain_std_db=self.feed_gain_std_db * scale,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain_phase_std_deg": self.chain_phase_std_deg,
            "chain_gain_std_db": self.chain_gain_std_db,
            "feed_phase_std_deg": self.feed_phase_std_deg,
            "feed_gain_std_db": self.feed_gain_std_db,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MismatchConfig":
        return cls(
            chain_phase_std_deg=float(data.get("chain_phase_std_deg", 8.0)),
            chain_gain_std_db=float(data.get("chain_gain_std_db", 1.0)),
            feed_phase_std_deg=float(data.get("feed_phase_std_deg", 5.0)),
            feed_gain_std_db=float(data.get("feed_gain_std_db", 0.5)),
        )


@dataclass(frozen=True)
class FaultSpec:
    """Deterministic path or chain faults for the emulator."""

    path_faults: Mapping[int, str] = field(default_factory=dict)
    chain_faults: Mapping[int, str] = field(default_factory=dict)
    faulty_gain_db: float = -15.0
    faulty_phase_deg: float = 120.0
    inconsistent_phase_std_deg: float = 45.0
    inconsistent_gain_std_db: float = 2.0

    def validate(self) -> None:
        for mode in list(self.path_faults.values()) + list(self.chain_faults.values()):
            if mode not in FAULT_MODES:
                raise ValueError(f"unsupported fault mode: {mode}")

    def mode_for_path(self, path_index: int, chain: int) -> str:
        if path_index in self.path_faults:
            return self.path_faults[path_index]
        return self.chain_faults.get(chain, "ok")

    def to_dict(self) -> dict[str, Any]:
        return {
            "path_faults": {str(key): value for key, value in self.path_faults.items()},
            "chain_faults": {str(key): value for key, value in self.chain_faults.items()},
            "faulty_gain_db": self.faulty_gain_db,
            "faulty_phase_deg": self.faulty_phase_deg,
            "inconsistent_phase_std_deg": self.inconsistent_phase_std_deg,
            "inconsistent_gain_std_db": self.inconsistent_gain_std_db,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "FaultSpec":
        data = data or {}
        spec = cls(
            path_faults={
                int(key): str(value) for key, value in data.get("path_faults", {}).items()
            },
            chain_faults={
                int(key): str(value) for key, value in data.get("chain_faults", {}).items()
            },
            faulty_gain_db=float(data.get("faulty_gain_db", -15.0)),
            faulty_phase_deg=float(data.get("faulty_phase_deg", 120.0)),
            inconsistent_phase_std_deg=float(
                data.get("inconsistent_phase_std_deg", 45.0)
            ),
            inconsistent_gain_std_db=float(data.get("inconsistent_gain_std_db", 2.0)),
        )
        spec.validate()
        return spec


@dataclass(frozen=True)
class MeasurementConfig:
    seed: int = 0
    snr_db: float = 30.0
    n_captures: int = 4
    n_samples: int = 64
    pilot_amplitude: float = 1.0
    mismatch: MismatchConfig = field(default_factory=MismatchConfig)
    faults: FaultSpec = field(default_factory=FaultSpec)

    def validate(self) -> None:
        if self.n_captures < 1:
            raise ValueError("n_captures must be at least one")
        if self.n_samples < 2:
            raise ValueError("n_samples must be at least two")
        if self.pilot_amplitude <= 0:
            raise ValueError("pilot_amplitude must be positive")
        self.faults.validate()

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "snr_db": self.snr_db,
            "n_captures": self.n_captures,
            "n_samples": self.n_samples,
            "pilot_amplitude": self.pilot_amplitude,
            "mismatch": self.mismatch.to_dict(),
            "faults": self.faults.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MeasurementConfig":
        config = cls(
            seed=int(data.get("seed", 0)),
            snr_db=float(data.get("snr_db", 30.0)),
            n_captures=int(data.get("n_captures", 4)),
            n_samples=int(data.get("n_samples", 64)),
            pilot_amplitude=float(data.get("pilot_amplitude", 1.0)),
            mismatch=MismatchConfig.from_dict(data.get("mismatch", {})),
            faults=FaultSpec.from_dict(data.get("faults", {})),
        )
        config.validate()
        return config


@dataclass
class MeasurementSet:
    topology_name: str
    config: MeasurementConfig
    pilot: np.ndarray
    iq: np.ndarray
    capture_response: np.ndarray
    truth_response: np.ndarray
    fault_labels: tuple[str, ...]
    simulated: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def n_feeds(self) -> int:
        return int(self.iq.shape[0])

    @property
    def n_captures(self) -> int:
        return int(self.iq.shape[1])

    @property
    def n_samples(self) -> int:
        return int(self.iq.shape[2])

    def validate(self) -> None:
        if not self.simulated:
            raise ValueError("this package only generates simulated measurements")
        if self.iq.ndim != 3:
            raise ValueError("iq must have shape (n_feeds, n_captures, n_samples)")
        n_feeds, n_captures, n_samples = self.iq.shape
        if self.pilot.shape != (n_samples,):
            raise ValueError("pilot shape does not match iq")
        if self.capture_response.shape != (n_feeds, n_captures):
            raise ValueError("capture_response shape does not match iq")
        if self.truth_response.shape != (n_feeds,):
            raise ValueError("truth_response shape does not match iq")
        if len(self.fault_labels) != n_feeds:
            raise ValueError("fault_labels must have one entry per feed")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "simulated": True,
            "topology_name": self.topology_name,
            "config": self.config.to_dict(),
            "pilot_real": np.real(self.pilot).astype(float).tolist(),
            "pilot_imag": np.imag(self.pilot).astype(float).tolist(),
            "iq_real": np.real(self.iq).astype(float).tolist(),
            "iq_imag": np.imag(self.iq).astype(float).tolist(),
            "capture_response_real": np.real(self.capture_response).astype(float).tolist(),
            "capture_response_imag": np.imag(self.capture_response).astype(float).tolist(),
            "truth_response_real": np.real(self.truth_response).astype(float).tolist(),
            "truth_response_imag": np.imag(self.truth_response).astype(float).tolist(),
            "fault_labels": list(self.fault_labels),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MeasurementSet":
        pilot = np.asarray(data["pilot_real"], dtype=float) + 1j * np.asarray(
            data["pilot_imag"], dtype=float
        )
        iq = np.asarray(data["iq_real"], dtype=float) + 1j * np.asarray(
            data["iq_imag"], dtype=float
        )
        capture_response = np.asarray(
            data["capture_response_real"], dtype=float
        ) + 1j * np.asarray(data["capture_response_imag"], dtype=float)
        truth_response = np.asarray(
            data["truth_response_real"], dtype=float
        ) + 1j * np.asarray(data["truth_response_imag"], dtype=float)
        measurement = cls(
            topology_name=str(data["topology_name"]),
            config=MeasurementConfig.from_dict(data["config"]),
            pilot=pilot,
            iq=iq,
            capture_response=capture_response,
            truth_response=truth_response,
            fault_labels=tuple(str(item) for item in data["fault_labels"]),
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
    def from_json(cls, path: str | Path) -> "MeasurementSet":
        with Path(path).open("r", encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))


def simulate_measurements(
    topology: Topology,
    config: MeasurementConfig | None = None,
) -> MeasurementSet:
    """Generate deterministic synthetic pilot measurements."""

    config = config or MeasurementConfig()
    config.validate()
    seed_sequence = np.random.SeedSequence(config.seed)
    truth_rng, noise_rng, fault_rng = (
        np.random.default_rng(child) for child in seed_sequence.spawn(3)
    )

    mismatch = config.mismatch
    chain_ids = topology.chain_ids
    chain_index = {chain: index for index, chain in enumerate(chain_ids)}
    chain_phase = np.deg2rad(
        truth_rng.normal(0.0, mismatch.chain_phase_std_deg, size=len(chain_ids))
    )
    chain_gain_db = truth_rng.normal(
        0.0, mismatch.chain_gain_std_db, size=len(chain_ids)
    )
    feed_phase = np.deg2rad(
        truth_rng.normal(0.0, mismatch.feed_phase_std_deg, size=topology.n_feeds)
    )
    feed_gain_db = truth_rng.normal(
        0.0, mismatch.feed_gain_std_db, size=topology.n_feeds
    )

    base_response = np.empty(topology.n_feeds, dtype=np.complex128)
    for feed in topology.feeds:
        chain_position = chain_index[feed.chain]
        gain_db = chain_gain_db[chain_position] + feed_gain_db[feed.index]
        phase = chain_phase[chain_position] + feed_phase[feed.index]
        base_response[feed.index] = 10.0 ** (gain_db / 20.0) * np.exp(1j * phase)

    fault_modes = np.asarray(
        [config.faults.mode_for_path(feed.index, feed.chain) for feed in topology.feeds],
        dtype=object,
    )
    truth_response = base_response.copy()
    capture_response = np.repeat(base_response[:, None], config.n_captures, axis=1)

    for feed in topology.feeds:
        mode = str(fault_modes[feed.index])
        if mode == "missing":
            truth_response[feed.index] = 0.0
            capture_response[feed.index, :] = 0.0
        elif mode == "faulty":
            offset = 10.0 ** (config.faults.faulty_gain_db / 20.0) * np.exp(
                1j * np.deg2rad(config.faults.faulty_phase_deg)
            )
            truth_response[feed.index] *= offset
            capture_response[feed.index, :] *= offset
        elif mode == "inconsistent":
            for capture in range(config.n_captures):
                phase_jitter = np.deg2rad(
                    fault_rng.normal(0.0, config.faults.inconsistent_phase_std_deg)
                )
                gain_jitter_db = fault_rng.normal(
                    0.0, config.faults.inconsistent_gain_std_db
                )
                capture_response[feed.index, capture] *= 10.0 ** (
                    gain_jitter_db / 20.0
                ) * np.exp(1j * phase_jitter)

    pilot = config.pilot_amplitude * np.exp(
        2j * np.pi * 0.125 * np.arange(config.n_samples, dtype=float)
    )
    pilot_power = float(np.mean(np.abs(pilot) ** 2))
    iq = np.zeros(
        (topology.n_feeds, config.n_captures, config.n_samples), dtype=np.complex128
    )
    for feed_index in range(topology.n_feeds):
        for capture in range(config.n_captures):
            response = capture_response[feed_index, capture]
            if response == 0:
                continue
            signal_power = abs(response) ** 2 * pilot_power
            noise_power = signal_power / (10.0 ** (config.snr_db / 10.0))
            noise = np.sqrt(noise_power / 2.0) * (
                noise_rng.normal(size=config.n_samples)
                + 1j * noise_rng.normal(size=config.n_samples)
            )
            iq[feed_index, capture, :] = response * pilot + noise

    measurement = MeasurementSet(
        topology_name=topology.name,
        config=config,
        pilot=pilot,
        iq=iq,
        capture_response=capture_response,
        truth_response=truth_response,
        fault_labels=tuple(str(mode) for mode in fault_modes),
        simulated=True,
        metadata={
            "generator": "openru_x6.rfcal.measurement",
            "evidence_label": "SIMULATED",
            "hardware_measured": False,
        },
    )
    measurement.validate()
    return measurement
