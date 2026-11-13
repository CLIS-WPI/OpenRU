"""Hardware-impairment and measurement-uncertainty validation.

The model in this module is still synthetic.  It adds first-order hardware
error mechanisms on top of the observable chain/feed calibration so the report
can distinguish an algorithmic floor from a hardware-limited result:

* reference-path drift, independent per chain and common across chains;
* switch leakage between feeds that share a switched calibration bus;
* independent and common phase noise;
* uncalibrated mutual coupling between feeds;
* correlated per-chain calibration errors.

The reported values are not measurements.  The module is deliberately
independent of register writes, RFIC control, and transmit enable.
"""

from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .calibration import CalibrationConfig
from .hierarchical import (
    HierarchicalCalibrationResult,
    HierarchicalMeasurementConfig,
    calibrate_hierarchical,
    simulate_hierarchical_measurements,
)
from .measurement import MismatchConfig
from .metrics import beam_metrics_polarized
from .observability import get_architecture
from .polarization import (
    linear_jones,
    matched_receiver_jones,
    orthogonal_jones,
    polarized_steering_weights,
)
from .topology import Topology

_DEFAULT_ANGLE = ((0.37, 0.23), (12.63, -7.41), (-30.37, 10.23))
_DEFAULT_RESOLUTION_ANGLES = ((0.37, 0.23), (12.63, -7.41))
_NEGLIGIBLE_DB = -300.0


@dataclass(frozen=True)
class ImpairmentConfig:
    """First-order hardware impairments applied to a synthetic calibration.

    ``reference_drift_*`` is a residual error after the reference path was
    characterized.  The independent term varies per chain; the common term is
    shared by every chain.  ``correlated_*`` is a per-chain measurement error
    shared by the four feeds on that chain.  ``phase_noise_deg_rms`` is an
    independent per-feed residual after capture averaging.  ``switch_leakage``
    only applies when multiple feeds on the same switch are active at once.
    """

    reference_drift_phase_std_deg: float = 0.0
    reference_drift_gain_std_db: float = 0.0
    reference_drift_common_phase_std_deg: float = 0.0
    reference_drift_common_gain_std_db: float = 0.0
    switch_leakage_db: float = _NEGLIGIBLE_DB
    switch_leakage_phase_deg: float = 90.0
    switch_leakage_simultaneous: bool = False
    phase_noise_deg_rms: float = 0.0
    common_phase_noise_deg_rms: float = 0.0
    mutual_coupling_db: float = _NEGLIGIBLE_DB
    mutual_coupling_phase_deg: float = 0.0
    correlated_phase_std_deg: float = 0.0
    correlated_gain_std_db: float = 0.0

    def validate(self) -> None:
        for name in (
            "reference_drift_phase_std_deg",
            "reference_drift_gain_std_db",
            "reference_drift_common_phase_std_deg",
            "reference_drift_common_gain_std_db",
            "phase_noise_deg_rms",
            "common_phase_noise_deg_rms",
            "correlated_phase_std_deg",
            "correlated_gain_std_db",
        ):
            if getattr(self, name) < 0.0:
                raise ValueError(f"{name} must be non-negative")
        if self.switch_leakage_db > 0.0:
            raise ValueError("switch_leakage_db must be non-positive")
        if self.mutual_coupling_db > 0.0:
            raise ValueError("mutual_coupling_db must be non-positive")

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference_drift_phase_std_deg": self.reference_drift_phase_std_deg,
            "reference_drift_gain_std_db": self.reference_drift_gain_std_db,
            "reference_drift_common_phase_std_deg": self.reference_drift_common_phase_std_deg,
            "reference_drift_common_gain_std_db": self.reference_drift_common_gain_std_db,
            "switch_leakage_db": self.switch_leakage_db,
            "switch_leakage_phase_deg": self.switch_leakage_phase_deg,
            "switch_leakage_simultaneous": self.switch_leakage_simultaneous,
            "phase_noise_deg_rms": self.phase_noise_deg_rms,
            "common_phase_noise_deg_rms": self.common_phase_noise_deg_rms,
            "mutual_coupling_db": self.mutual_coupling_db,
            "mutual_coupling_phase_deg": self.mutual_coupling_phase_deg,
            "correlated_phase_std_deg": self.correlated_phase_std_deg,
            "correlated_gain_std_db": self.correlated_gain_std_db,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ImpairmentConfig":
        data = data or {}
        config = cls(
            reference_drift_phase_std_deg=float(
                data.get("reference_drift_phase_std_deg", 0.0)
            ),
            reference_drift_gain_std_db=float(
                data.get("reference_drift_gain_std_db", 0.0)
            ),
            reference_drift_common_phase_std_deg=float(
                data.get("reference_drift_common_phase_std_deg", 0.0)
            ),
            reference_drift_common_gain_std_db=float(
                data.get("reference_drift_common_gain_std_db", 0.0)
            ),
            switch_leakage_db=float(data.get("switch_leakage_db", _NEGLIGIBLE_DB)),
            switch_leakage_phase_deg=float(
                data.get("switch_leakage_phase_deg", 90.0)
            ),
            switch_leakage_simultaneous=bool(
                data.get("switch_leakage_simultaneous", False)
            ),
            phase_noise_deg_rms=float(data.get("phase_noise_deg_rms", 0.0)),
            common_phase_noise_deg_rms=float(
                data.get("common_phase_noise_deg_rms", 0.0)
            ),
            mutual_coupling_db=float(data.get("mutual_coupling_db", _NEGLIGIBLE_DB)),
            mutual_coupling_phase_deg=float(
                data.get("mutual_coupling_phase_deg", 0.0)
            ),
            correlated_phase_std_deg=float(
                data.get("correlated_phase_std_deg", 0.0)
            ),
            correlated_gain_std_db=float(data.get("correlated_gain_std_db", 0.0)),
        )
        config.validate()
        return config

    @property
    def is_ideal(self) -> bool:
        return self == ImpairmentConfig()


@dataclass(frozen=True)
class ImpairmentCase:
    name: str
    architecture: str
    impairments: ImpairmentConfig = field(default_factory=ImpairmentConfig)
    description: str = ""

    def validate(self) -> None:
        if not self.name:
            raise ValueError("impairment case name must not be empty")
        get_architecture(self.architecture)
        self.impairments.validate()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "architecture": self.architecture,
            "description": self.description,
            "impairments": self.impairments.to_dict(),
        }


DEFAULT_IMPAIRMENT_CASES: tuple[ImpairmentCase, ...] = (
    ImpairmentCase(
        name="h3_no_impairment",
        architecture="proposed_switched_feed_loopback",
        impairments=ImpairmentConfig(),
        description="Per-feed switched-loopback model floor.",
    ),
    ImpairmentCase(
        name="h2_no_impairment",
        architecture="h2_available",
        impairments=ImpairmentConfig(),
        description="Current-H2 chain loopback and feed-power model floor.",
    ),
    ImpairmentCase(
        name="reference_drift_0p5deg",
        architecture="proposed_switched_feed_loopback",
        impairments=ImpairmentConfig(
            reference_drift_phase_std_deg=0.5,
            reference_drift_gain_std_db=0.05,
        ),
        description="Independent per-chain reference drift.",
    ),
    ImpairmentCase(
        name="reference_drift_common_0p5deg",
        architecture="proposed_switched_feed_loopback",
        impairments=ImpairmentConfig(
            reference_drift_common_phase_std_deg=0.5,
            reference_drift_common_gain_std_db=0.05,
        ),
        description="Common-mode reference drift across all chains.",
    ),
    ImpairmentCase(
        name="switch_leakage_20db_simultaneous",
        architecture="proposed_switched_feed_loopback",
        impairments=ImpairmentConfig(
            switch_leakage_db=-20.0,
            switch_leakage_simultaneous=True,
        ),
        description="Worst-case leakage with all four feeds active.",
    ),
    ImpairmentCase(
        name="switch_leakage_20db_one_at_a_time",
        architecture="proposed_switched_feed_loopback",
        impairments=ImpairmentConfig(
            switch_leakage_db=-20.0,
            switch_leakage_simultaneous=False,
        ),
        description="One-feed-at-a-time switched calibration.",
    ),
    ImpairmentCase(
        name="phase_noise_2deg",
        architecture="proposed_switched_feed_loopback",
        impairments=ImpairmentConfig(phase_noise_deg_rms=2.0),
        description="Independent per-feed residual phase noise.",
    ),
    ImpairmentCase(
        name="phase_noise_common_2deg",
        architecture="proposed_switched_feed_loopback",
        impairments=ImpairmentConfig(common_phase_noise_deg_rms=2.0),
        description="Common-mode residual phase noise.",
    ),
    ImpairmentCase(
        name="mutual_coupling_20db",
        architecture="proposed_switched_feed_loopback",
        impairments=ImpairmentConfig(mutual_coupling_db=-20.0),
        description="Uncalibrated nearest-neighbour mutual coupling.",
    ),
    ImpairmentCase(
        name="mutual_coupling_30db",
        architecture="proposed_switched_feed_loopback",
        impairments=ImpairmentConfig(mutual_coupling_db=-30.0),
        description="Weak uncalibrated nearest-neighbour mutual coupling.",
    ),
    ImpairmentCase(
        name="correlated_chain_0p5deg",
        architecture="proposed_switched_feed_loopback",
        impairments=ImpairmentConfig(correlated_phase_std_deg=0.5),
        description="Per-chain correlated measurement error.",
    ),
    ImpairmentCase(
        name="combined_moderate",
        architecture="proposed_switched_feed_loopback",
        impairments=ImpairmentConfig(
            reference_drift_phase_std_deg=0.3,
            reference_drift_gain_std_db=0.03,
            switch_leakage_db=-25.0,
            switch_leakage_simultaneous=True,
            phase_noise_deg_rms=1.0,
            mutual_coupling_db=-25.0,
            correlated_phase_std_deg=0.2,
        ),
        description="Moderate combined hardware errors.",
    ),
)


@dataclass(frozen=True)
class ImpairmentValidationConfig:
    seeds: tuple[int, ...] = tuple(range(5))
    n_captures: int = 4
    n_samples: int = 64
    base_snr_db: float = 30.0
    base_mismatch: MismatchConfig = field(default_factory=MismatchConfig)
    calibration: CalibrationConfig = field(default_factory=CalibrationConfig)
    angles: tuple[tuple[float, float], ...] = _DEFAULT_ANGLE
    search_step_deg: float = 0.01
    search_span_deg: float = 3.0
    resolution_search_steps: tuple[float, ...] = (0.5, 0.25, 0.1, 0.05, 0.01)
    resolution_search_span_deg: float = 2.0
    resolution_offset_fraction_az: float = 0.37
    resolution_offset_fraction_el: float = 0.23
    resolution_angles: tuple[tuple[float, float], ...] = _DEFAULT_RESOLUTION_ANGLES
    cases: tuple[ImpairmentCase, ...] = DEFAULT_IMPAIRMENT_CASES

    def validate(self) -> None:
        if not self.seeds:
            raise ValueError("at least one seed is required")
        if not self.angles:
            raise ValueError("at least one steering angle is required")
        if self.n_captures < 1 or self.n_samples < 2:
            raise ValueError("invalid capture or sample count")
        if self.search_step_deg <= 0.0:
            raise ValueError("search_step_deg must be positive")
        if self.search_span_deg <= 0.0:
            raise ValueError("search_span_deg must be positive")
        if self.resolution_search_span_deg <= 0.0:
            raise ValueError("resolution_search_span_deg must be positive")
        for name in (
            "resolution_offset_fraction_az",
            "resolution_offset_fraction_el",
        ):
            if not 0.0 <= getattr(self, name) < 1.0:
                raise ValueError(f"{name} must be in [0, 1)")
        if not self.cases:
            raise ValueError("at least one impairment case is required")
        if len({case.name for case in self.cases}) != len(self.cases):
            raise ValueError("impairment case names must be unique")
        self.calibration.validate()
        for case in self.cases:
            case.validate()
        for step in self.resolution_search_steps:
            if step <= 0.0:
                raise ValueError("resolution search steps must be positive")
        if not self.resolution_angles:
            raise ValueError("at least one resolution angle is required")

    @classmethod
    def quick(cls) -> "ImpairmentValidationConfig":
        names = {
            "h3_no_impairment",
            "h2_no_impairment",
            "reference_drift_0p5deg",
            "reference_drift_common_0p5deg",
            "switch_leakage_20db_simultaneous",
            "switch_leakage_20db_one_at_a_time",
            "phase_noise_2deg",
            "phase_noise_common_2deg",
            "mutual_coupling_20db",
            "correlated_chain_0p5deg",
        }
        return cls(
            seeds=(0,),
            angles=((0.37, 0.23),),
            cases=tuple(case for case in DEFAULT_IMPAIRMENT_CASES if case.name in names),
            resolution_search_steps=(0.25, 0.1, 0.05),
        )


@dataclass
class ImpairmentValidationReport:
    topology_name: str
    carrier_freq_hz: float
    config: ImpairmentValidationConfig
    records: list[dict[str, Any]]
    summary: list[dict[str, Any]]
    resolution_records: list[dict[str, Any]]
    resolution_summary: list[dict[str, Any]]
    runtime_s: float
    simulated: bool = True

    def to_dict(self, *, include_records: bool = True) -> dict[str, Any]:
        payload = {
            "schema_version": "1.0",
            "simulated": True,
            "evidence_label": "SIMULATED",
            "hardware_measured": False,
            "topology_name": self.topology_name,
            "carrier_freq_hz": self.carrier_freq_hz,
            "runtime_s": self.runtime_s,
            "config": {
                "seeds": list(self.config.seeds),
                "n_captures": self.config.n_captures,
                "n_samples": self.config.n_samples,
                "base_snr_db": self.config.base_snr_db,
                "base_mismatch": self.config.base_mismatch.to_dict(),
                "angles": [[az, el] for az, el in self.config.angles],
                "search_step_deg": self.config.search_step_deg,
                "search_span_deg": self.config.search_span_deg,
                "cases": [case.to_dict() for case in self.config.cases],
                "resolution_search_steps": list(self.config.resolution_search_steps),
                "resolution_search_span_deg": self.config.resolution_search_span_deg,
                "resolution_offset_fraction_az": (
                    self.config.resolution_offset_fraction_az
                ),
                "resolution_offset_fraction_el": (
                    self.config.resolution_offset_fraction_el
                ),
                "resolution_angles": [
                    [az, el] for az, el in self.config.resolution_angles
                ],
            },
            "summary": self.summary,
            "resolution_summary": self.resolution_summary,
        }
        if include_records:
            payload["records"] = self.records
            payload["resolution_records"] = self.resolution_records
        return payload

    def to_json(self, path: str | Path, *, include_records: bool = True) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(
                self.to_dict(include_records=include_records),
                handle,
                indent=2,
                sort_keys=True,
            )
            handle.write("\n")

    def to_csv(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not self.records:
            raise ValueError("no impairment records to write")
        fieldnames = list(self.records[0].keys())
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.records)

    def to_markdown(self) -> str:
        lines = [
            "# Hardware Impairment and Uncertainty Validation",
            "",
            "**Evidence label: SIMULATED.** No hardware measurements are present.",
            "",
            "This report adds first-order reference drift, switch leakage, phase noise,",
            "mutual coupling, and correlated calibration errors to the observable",
            "chain/feed model. It reports dispersion across seeds, not only a mean.",
            "",
            f"- Topology: `{self.topology_name}`",
            f"- Carrier: `{self.carrier_freq_hz / 1e9:.3f} GHz`",
            f"- Seeds: `{len(self.config.seeds)}`; beam angles: `{len(self.config.angles)}`",
            f"- Fine-search step: `{self.config.search_step_deg:.3f} deg`; "
            f"span: `{self.config.search_span_deg:.3f} deg`",
            f"- Cases: `{len(self.config.cases)}`",
            f"- Runtime: `{self.runtime_s:.3f} s`",
            "",
            "## Uncertainty by case",
            "",
            "Every row is the spread over seeds and steering angles. `p95` is the",
            "95th percentile; `max` is the worst case in this synthetic ensemble.",
            "",
            "| case | architecture | n | pointing mean (deg) | pointing std (deg) | "
            "pointing p95 (deg) | pointing max (deg) | cal phase mean (deg) | "
            "cal phase std (deg) | cal gain mean (dB) |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for row in self.summary:
            lines.append(
                "| {case} | {architecture} | {count} | "
                "{pointing_error_deg_mean:.4f} | {pointing_error_deg_std:.4f} | "
                "{pointing_error_deg_p95:.4f} | {pointing_error_deg_max:.4f} | "
                "{calibration_phase_error_deg_mean:.4f} | "
                "{calibration_phase_error_deg_std:.4f} | "
                "{calibration_gain_error_db_mean:.4f} |".format(**row)
            )
        lines.extend(
            [
                "",
                "## Angular-search resolution",
                "",
                "The ideal calibrated beam is evaluated on intentional off-grid search",
                "windows offset by fixed fractions of each step. The grid bound is",
                "`step * sqrt(2) / 2` in two dimensions. Values scale with the search",
                "step and are not a statement of physical accuracy.",
                "",
                "| search step (deg) | grid bound (deg) | n | "
                "pointing mean (deg) | pointing max (deg) |",
                "|---:|---:|---:|---:|---:|",
            ]
        )
        for row in self.resolution_summary:
            lines.append(
                "| {search_step_deg:.4f} | {grid_quantization_bound_deg:.4f} | "
                "{count} | {pointing_error_deg_mean:.4f} | "
                "{pointing_error_deg_max:.4f} |".format(**row)
            )
        lines.extend(
            [
                "",
                "## Findings",
                "",
                "1. The previously reported `0.01 deg` switched-loopback result is at or",
                "   below the configured `0.25 deg` search step. It is a grid/model floor,",
                "   not a measured or guaranteed physical pointing accuracy.",
                "2. Common-mode reference drift and common-mode phase noise do not change",
                "   relative pointing or relative calibration accuracy. They are a global",
                "   phase/gain offset that is normalized out here. Independent and per-chain",
                "   terms are the pointing-relevant errors.",
                "3. Switch leakage is only first order when multiple feeds on one switch are",
                "   active. A one-feed-at-a-time sequence suppresses that term; finite",
                "   isolation and settling must still be measured on hardware.",
                "4. Mutual coupling is not observed by an ADTR1107 `CPLR_OUT` tap. It must be",
                "   characterized separately or included in a near-field/OTA calibration.",
                "5. Every value here is synthetic. Use the same distributions only as a",
                "   test harness; replace the parameters with measured distributions.",
                "",
                "All IQ, path responses, coupling values, and calibration tables are synthetic.",
                "The ADAR1000 is not qualified at 8.4 GHz by this result.",
                "",
            ]
        )
        return "\n".join(lines)

    def to_markdown_file(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_markdown(), encoding="utf-8")


def run_impairment_validation(
    topology: Topology,
    config: ImpairmentValidationConfig | None = None,
) -> ImpairmentValidationReport:
    """Run the impairment ensemble and an angular-resolution study."""

    config = config or ImpairmentValidationConfig()
    config.validate()
    start = time.perf_counter()
    incident = linear_jones(0.0)
    receiver = matched_receiver_jones(incident)
    cross_incident = orthogonal_jones(incident)
    records: list[dict[str, Any]] = []

    for case_index, case in enumerate(config.cases):
        for seed in config.seeds:
            measurement = simulate_hierarchical_measurements(
                topology,
                HierarchicalMeasurementConfig(
                    seed=seed,
                    snr_db=config.base_snr_db,
                    n_captures=config.n_captures,
                    n_samples=config.n_samples,
                    mismatch=config.base_mismatch,
                    architecture=case.architecture,
                ),
            )
            calibration = calibrate_hierarchical(
                topology, measurement, config.calibration
            )
            rng = np.random.default_rng(seed + 1009 * case_index)
            truth = _coupled_truth(
                topology, measurement.truth_response, case.impairments, rng
            )
            corrections = _impaired_corrections(
                topology, calibration, case.impairments, rng
            )
            accuracy = _calibration_accuracy(
                truth, corrections, calibration.healthy_mask
            )
            phase_only = np.zeros_like(corrections)
            healthy = calibration.healthy_mask
            phase_only[healthy] = np.exp(1j * np.angle(corrections[healthy]))
            for target_az, target_el in config.angles:
                base_weights = polarized_steering_weights(
                    topology, target_az, target_el, receiver
                )
                beam = beam_metrics_polarized(
                    topology,
                    base_weights * phase_only,
                    target_az,
                    target_el,
                    incident,
                    path_response=truth,
                    cross_incident_jones=cross_incident,
                    search_span_az_deg=config.search_span_deg,
                    search_span_el_deg=config.search_span_deg,
                    search_step_deg=config.search_step_deg,
                )
                records.append(
                    {
                        "seed": seed,
                        "case": case.name,
                        "architecture": case.architecture,
                        "target_az_deg": float(target_az),
                        "target_el_deg": float(target_el),
                        "search_step_deg": config.search_step_deg,
                        "pointing_error_deg": beam.pointing_error_deg,
                        "co_pol_gain_db": beam.co_pol_gain_db,
                        "cross_pol_gain_db": beam.cross_pol_gain_db,
                        "xpd_db": beam.cross_pol_discrimination_db,
                        "calibration_phase_error_deg": accuracy["phase_error_deg"],
                        "calibration_gain_error_db": accuracy["gain_error_db"],
                        "healthy_paths": int(np.sum(healthy)),
                        "mutual_coupling_db": case.impairments.mutual_coupling_db,
                        "switch_leakage_db": case.impairments.switch_leakage_db,
                    }
                )

    resolution_records, resolution_summary = _resolution_study(topology, config)
    summary = _summarize_impairments(records)
    runtime_s = time.perf_counter() - start
    return ImpairmentValidationReport(
        topology_name=topology.name,
        carrier_freq_hz=topology.carrier_freq_hz,
        config=config,
        records=records,
        summary=summary,
        resolution_records=resolution_records,
        resolution_summary=resolution_summary,
        runtime_s=runtime_s,
        simulated=True,
    )


def _coupled_truth(
    topology: Topology,
    truth_response: np.ndarray,
    config: ImpairmentConfig,
    rng: np.random.Generator,
) -> np.ndarray:
    truth = np.asarray(truth_response, dtype=np.complex128).copy()
    if config.mutual_coupling_db <= _NEGLIGIBLE_DB + 1.0:
        return truth
    coupling = _mutual_coupling_matrix(topology, config)
    return truth + coupling @ truth


def _mutual_coupling_matrix(
    topology: Topology, config: ImpairmentConfig
) -> np.ndarray:
    positions = topology.positions_m()
    n_feeds = topology.n_feeds
    matrix = np.zeros((n_feeds, n_feeds), dtype=np.complex128)
    coupling = 10.0 ** (config.mutual_coupling_db / 20.0)
    phase = np.deg2rad(config.mutual_coupling_phase_deg)
    threshold = 0.55 * topology.wavelength_m
    for source in range(n_feeds):
        for victim in range(n_feeds):
            if source == victim:
                continue
            delta = positions[source] - positions[victim]
            distance = float(np.linalg.norm(delta))
            if 0.0 < distance <= threshold:
                matrix[victim, source] = coupling * np.exp(
                    1j * (phase + 2.0 * np.pi * distance / topology.wavelength_m)
                )
    return matrix


def _impaired_corrections(
    topology: Topology,
    calibration: HierarchicalCalibrationResult,
    config: ImpairmentConfig,
    rng: np.random.Generator,
) -> np.ndarray:
    corrections = np.asarray(calibration.corrections, dtype=np.complex128).copy()
    chain_ids = topology.chain_ids
    common_reference = _complex_error(
        rng,
        config.reference_drift_common_phase_std_deg,
        config.reference_drift_common_gain_std_db,
    )
    for chain in chain_ids:
        indices = topology.chain_indices(chain)
        independent = _complex_error(
            rng,
            config.reference_drift_phase_std_deg,
            config.reference_drift_gain_std_db,
        )
        correlated = _complex_error(
            rng,
            config.correlated_phase_std_deg,
            config.correlated_gain_std_db,
        )
        corrections[indices] *= common_reference * independent * correlated
    if config.phase_noise_deg_rms > 0.0:
        for feed in topology.feeds:
            corrections[feed.index] *= np.exp(
                1j * np.deg2rad(rng.normal(0.0, config.phase_noise_deg_rms))
            )
    if config.common_phase_noise_deg_rms > 0.0:
        corrections *= np.exp(
            1j * np.deg2rad(rng.normal(0.0, config.common_phase_noise_deg_rms))
        )
    if (
        config.switch_leakage_simultaneous
        and config.switch_leakage_db > _NEGLIGIBLE_DB + 1.0
    ):
        leakage = 10.0 ** (config.switch_leakage_db / 20.0)
        for chain in chain_ids:
            indices = topology.chain_indices(chain)
            for position, index in enumerate(indices):
                source = indices[(position + 1) % len(indices)]
                corrections[index] += (
                    leakage
                    * np.exp(
                        1j
                        * np.deg2rad(
                            config.switch_leakage_phase_deg + 90.0 * position
                        )
                    )
                    * corrections[source]
                )
    return corrections


def _complex_error(
    rng: np.random.Generator, phase_std_deg: float, gain_std_db: float
) -> complex:
    phase = 0.0 if phase_std_deg == 0.0 else rng.normal(0.0, phase_std_deg)
    gain = 0.0 if gain_std_db == 0.0 else rng.normal(0.0, gain_std_db)
    return 10.0 ** (gain / 20.0) * np.exp(1j * np.deg2rad(phase))


def _calibration_accuracy(
    truth: np.ndarray,
    corrections: np.ndarray,
    healthy: np.ndarray,
) -> dict[str, float]:
    values = np.asarray(truth, dtype=np.complex128)[healthy] * np.asarray(
        corrections, dtype=np.complex128
    )[healthy]
    if values.size == 0:
        return {"phase_error_deg": float("nan"), "gain_error_db": float("nan")}
    reference_phase = float(np.angle(np.mean(np.exp(1j * np.angle(values)))))
    reference_gain_db = float(
        np.mean(20.0 * np.log10(np.maximum(np.abs(values), 1e-300)))
    )
    phase_error = np.rad2deg(
        np.angle(np.exp(1j * (np.angle(values) - reference_phase)))
    )
    gain_error = (
        20.0 * np.log10(np.maximum(np.abs(values), 1e-300)) - reference_gain_db
    )
    return {
        "phase_error_deg": float(np.sqrt(np.mean(phase_error**2))),
        "gain_error_db": float(np.sqrt(np.mean(gain_error**2))),
    }


def _summarize_impairments(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    records = list(records)
    if not records:
        return []
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for record in records:
        key = (str(record["case"]), str(record["architecture"]))
        groups.setdefault(key, []).append(record)
    summary: list[dict[str, Any]] = []
    metric_keys = (
        "pointing_error_deg",
        "co_pol_gain_db",
        "calibration_phase_error_deg",
        "calibration_gain_error_db",
    )
    for (case, architecture), group in sorted(groups.items()):
        row: dict[str, Any] = {
            "case": case,
            "architecture": architecture,
            "count": len(group),
        }
        for metric in metric_keys:
            values = np.asarray(
                [record[metric] for record in group if record.get(metric) is not None],
                dtype=float,
            )
            values = values[np.isfinite(values)]
            if values.size == 0:
                row[f"{metric}_mean"] = float("nan")
                row[f"{metric}_std"] = float("nan")
                row[f"{metric}_p95"] = float("nan")
                row[f"{metric}_max"] = float("nan")
                continue
            row[f"{metric}_mean"] = float(np.mean(values))
            row[f"{metric}_std"] = float(np.std(values, ddof=0))
            row[f"{metric}_p95"] = float(np.percentile(values, 95))
            row[f"{metric}_max"] = float(np.max(values))
        summary.append(row)
    return summary


def _resolution_study(
    topology: Topology, config: ImpairmentValidationConfig
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    incident = linear_jones(0.0)
    receiver = matched_receiver_jones(incident)
    cross_incident = orthogonal_jones(incident)
    measurement = simulate_hierarchical_measurements(
        topology,
        HierarchicalMeasurementConfig(
            seed=0,
            snr_db=120.0,
            n_captures=1,
            n_samples=32,
            mismatch=MismatchConfig(
                chain_phase_std_deg=0.0,
                chain_gain_std_db=0.0,
                feed_phase_std_deg=0.0,
                feed_gain_std_db=0.0,
            ),
            architecture="ideal_16iq_nonrealizable",
        ),
    )
    calibration = calibrate_hierarchical(topology, measurement, config.calibration)
    corrections = calibration.phase_only_corrections
    records: list[dict[str, Any]] = []
    for step in config.resolution_search_steps:
        for target_az, target_el in config.resolution_angles:
            base_weights = polarized_steering_weights(
                topology, target_az, target_el, receiver
            )
            beam = beam_metrics_polarized(
                topology,
                base_weights * corrections,
                target_az,
                target_el,
                incident,
                path_response=measurement.truth_response,
                cross_incident_jones=cross_incident,
                search_span_az_deg=(
                    config.resolution_search_span_deg
                    + config.resolution_offset_fraction_az * step
                ),
                search_span_el_deg=(
                    config.resolution_search_span_deg
                    + config.resolution_offset_fraction_el * step
                ),
                search_step_deg=step,
            )
            records.append(
                {
                    "search_step_deg": float(step),
                    "grid_quantization_bound_deg": float(step * np.sqrt(2.0) / 2.0),
                    "target_az_deg": float(target_az),
                    "target_el_deg": float(target_el),
                    "pointing_error_deg": beam.pointing_error_deg,
                }
            )
    groups: dict[float, list[dict[str, Any]]] = {}
    for record in records:
        groups.setdefault(float(record["search_step_deg"]), []).append(record)
    summary: list[dict[str, Any]] = []
    for step, group in sorted(groups.items()):
        values = np.asarray(
            [record["pointing_error_deg"] for record in group], dtype=float
        )
        summary.append(
            {
                "search_step_deg": step,
                "grid_quantization_bound_deg": float(step * np.sqrt(2.0) / 2.0),
                "count": len(group),
                "pointing_error_deg_mean": float(np.mean(values)),
                "pointing_error_deg_max": float(np.max(values)),
            }
        )
    return records, summary
