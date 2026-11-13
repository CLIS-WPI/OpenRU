"""Reproducible observability-aware validation for the H2 calibration model.

This report deliberately separates three cases:

* the scalar per-feed-IQ baseline used by the first model package;
* the actual H2 observations (chain complex loopback + per-feed power);
* per-feed complex architectures (factory table, near-field probe, proposed
  switched loopback, and an ideal non-realizable comparison).
"""

from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .beamforming import steering_weights
from .calibration import CalibrationConfig, apply_calibration, calibrate
from .hierarchical import (
    HierarchicalMeasurementConfig,
    HierarchicalMeasurementSet,
    apply_hierarchical_calibration,
    calibrate_hierarchical,
    hierarchical_calibration_accuracy,
    simulate_hierarchical_measurements,
)
from .measurement import FaultSpec, MeasurementConfig, MismatchConfig, simulate_measurements
from .metrics import (
    beam_metrics,
    beam_metrics_polarized,
    quantization_loss_db,
    quantization_loss_polarized_db,
    truth_calibration_accuracy,
)
from .observability import (
    DEFAULT_ARCHITECTURES,
    MeasurementArchitecture,
    audit_h2_observability,
    get_architecture,
)
from .polarization import (
    PolarizationConfig,
    linear_jones,
    matched_receiver_jones,
    orthogonal_jones,
    polarized_steering_weights,
)
from .quantization import QuantizerConfig, quantize_weights
from .topology import Topology
from .validation import DEFAULT_ANGLES, _summarize

DEFAULT_FAULT_ARCHITECTURES = (
    "h2_available",
    "factory_vna_feed_table",
    "near_field_probe",
    "proposed_switched_feed_loopback",
    "ideal_16iq_nonrealizable",
)


@dataclass(frozen=True)
class ObservabilityValidationConfig:
    seeds: tuple[int, ...] = tuple(range(10))
    snr_db_levels: tuple[float, ...] = (10.0, 20.0, 30.0, 40.0)
    mismatch_scales: tuple[float, ...] = (0.0, 0.5, 1.0, 2.0)
    angles: tuple[tuple[float, float], ...] = DEFAULT_ANGLES
    n_captures: int = 4
    n_samples: int = 64
    base_snr_db: float = 30.0
    base_mismatch: MismatchConfig = field(default_factory=MismatchConfig)
    calibration: CalibrationConfig = field(default_factory=CalibrationConfig)
    quantizer: QuantizerConfig = field(default_factory=QuantizerConfig)
    polarization: PolarizationConfig = field(default_factory=PolarizationConfig)
    incident_polarization_deg: float = 0.0
    architectures: tuple[str, ...] = DEFAULT_ARCHITECTURES
    include_scalar_baseline: bool = True
    fault_seeds: tuple[int, ...] = (0, 1, 2)
    fault_architectures: tuple[str, ...] = DEFAULT_FAULT_ARCHITECTURES

    def validate(self) -> None:
        if not self.seeds:
            raise ValueError("at least one seed is required")
        if not self.snr_db_levels:
            raise ValueError("at least one SNR level is required")
        if not self.mismatch_scales:
            raise ValueError("at least one mismatch scale is required")
        if not self.angles:
            raise ValueError("at least one steering angle is required")
        if not self.architectures:
            raise ValueError("at least one architecture is required")
        if self.n_captures < 1 or self.n_samples < 2:
            raise ValueError("invalid capture or sample count")
        self.calibration.validate()
        self.quantizer.validate()
        self.polarization.validate()
        for name in self.architectures + self.fault_architectures:
            get_architecture(name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "seeds": list(self.seeds),
            "snr_db_levels": list(self.snr_db_levels),
            "mismatch_scales": list(self.mismatch_scales),
            "angles": [[az, el] for az, el in self.angles],
            "n_captures": self.n_captures,
            "n_samples": self.n_samples,
            "base_snr_db": self.base_snr_db,
            "base_mismatch": self.base_mismatch.to_dict(),
            "calibration": self.calibration.to_dict(),
            "quantizer": self.quantizer.to_dict(),
            "polarization": self.polarization.to_dict(),
            "incident_polarization_deg": self.incident_polarization_deg,
            "architectures": list(self.architectures),
            "include_scalar_baseline": self.include_scalar_baseline,
            "fault_seeds": list(self.fault_seeds),
            "fault_architectures": list(self.fault_architectures),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ObservabilityValidationConfig":
        config = cls(
            seeds=tuple(int(value) for value in data.get("seeds", range(10))),
            snr_db_levels=tuple(
                float(value) for value in data.get("snr_db_levels", (10, 20, 30, 40))
            ),
            mismatch_scales=tuple(
                float(value) for value in data.get("mismatch_scales", (0, 0.5, 1, 2))
            ),
            angles=tuple(
                (float(item[0]), float(item[1]))
                for item in data.get("angles", DEFAULT_ANGLES)
            ),
            n_captures=int(data.get("n_captures", 4)),
            n_samples=int(data.get("n_samples", 64)),
            base_snr_db=float(data.get("base_snr_db", 30.0)),
            base_mismatch=MismatchConfig.from_dict(data.get("base_mismatch", {})),
            calibration=CalibrationConfig.from_dict(data.get("calibration", {})),
            quantizer=QuantizerConfig.from_dict(data.get("quantizer", {})),
            polarization=PolarizationConfig.from_dict(data.get("polarization", {})),
            incident_polarization_deg=float(
                data.get("incident_polarization_deg", 0.0)
            ),
            architectures=tuple(
                str(value) for value in data.get("architectures", DEFAULT_ARCHITECTURES)
            ),
            include_scalar_baseline=bool(data.get("include_scalar_baseline", True)),
            fault_seeds=tuple(int(value) for value in data.get("fault_seeds", (0, 1, 2))),
            fault_architectures=tuple(
                str(value)
                for value in data.get(
                    "fault_architectures", DEFAULT_FAULT_ARCHITECTURES
                )
            ),
        )
        config.validate()
        return config

    @classmethod
    def quick(cls) -> "ObservabilityValidationConfig":
        return cls(
            seeds=(0, 1, 2),
            snr_db_levels=(20.0, 30.0),
            mismatch_scales=(0.0, 1.0),
            angles=((0.0, 0.0), (30.0, 0.0)),
            fault_seeds=(0,),
            architectures=(
                "h2_available",
                "near_field_probe",
                "proposed_switched_feed_loopback",
                "ideal_16iq_nonrealizable",
            ),
            fault_architectures=(
                "h2_available",
                "proposed_switched_feed_loopback",
                "ideal_16iq_nonrealizable",
            ),
        )


@dataclass
class ObservabilityValidationReport:
    topology_name: str
    carrier_freq_hz: float
    config: ObservabilityValidationConfig
    audit: dict[str, Any]
    records: list[dict[str, Any]]
    scalar_baseline_records: list[dict[str, Any]]
    accuracy_records: list[dict[str, Any]]
    aggregate: list[dict[str, Any]]
    base_case: list[dict[str, Any]]
    accuracy_by_snr: list[dict[str, Any]]
    accuracy_by_mismatch: list[dict[str, Any]]
    scalar_baseline_summary: list[dict[str, Any]]
    fault_records: list[dict[str, Any]]
    fault_summary: list[dict[str, Any]]
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
            "config": self.config.to_dict(),
            "audit": self.audit,
            "aggregate": self.aggregate,
            "base_case": self.base_case,
            "accuracy_by_snr": self.accuracy_by_snr,
            "accuracy_by_mismatch": self.accuracy_by_mismatch,
            "scalar_baseline_summary": self.scalar_baseline_summary,
            "fault_summary": self.fault_summary,
        }
        if include_records:
            payload["records"] = self.records
            payload["scalar_baseline_records"] = self.scalar_baseline_records
            payload["accuracy_records"] = self.accuracy_records
            payload["fault_records"] = self.fault_records
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
            raise ValueError("no observability validation records to write")
        fieldnames = list(self.records[0].keys())
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.records)

    def to_markdown(self) -> str:
        lines = [
            "# Observability-Aware RF Calibration Validation",
            "",
            "**Evidence label: SIMULATED.** No hardware measurements are present.",
            "",
            f"- Topology: `{self.topology_name}`",
            f"- Carrier: `{self.carrier_freq_hz / 1e9:.3f} GHz`",
            f"- Seeds: `{len(self.config.seeds)}`, SNR levels: `{len(self.config.snr_db_levels)}`, "
            f"mismatch scales: `{len(self.config.mismatch_scales)}`",
            f"- Beam angles: `{len(self.config.angles)}`",
            f"- Architectures: `{', '.join(self.config.architectures)}`",
            f"- Measured software runtime: `{self.runtime_s:.3f} s`",
            "",
            "## Hardware observability",
            "",
            self.audit["conclusion"],
            "",
            "| architecture | feed phase | realizable on H2 | needs hardware change | needs fixture |",
            "|---|---|---|---|---|",
        ]
        for name in self.config.architectures:
            architecture = get_architecture(name)
            lines.append(
                f"| `{name}` | {architecture.feed_phase_observable} | "
                f"{architecture.realizable_on_current_h2} | "
                f"{architecture.requires_hardware_change} | "
                f"{architecture.requires_external_fixture} |"
            )
        lines.extend(
            [
                "",
                "## Base-case vector results",
                "",
                "Base case is the configured base SNR and mismatch scale 1.0. "
                "The receiver is matched to the incident linear polarization; "
                "cross-pol is the orthogonal incident field with the same weights.",
                "",
                "| architecture | scenario | pointing err (deg) | co-pol gain (dB) | "
                "cross-pol gain (dB) | XPD (dB) | peak sidelobe (dB) |",
                "|---|---|---:|---:|---:|---:|---:|",
            ]
        )
        for row in self.base_case:
            lines.append(
                "| {architecture} | {scenario} | {pointing_error_deg_mean:.4f} | "
                "{co_pol_gain_db_mean:.4f} | {cross_pol_gain_db_mean:.4f} | "
                "{cross_pol_discrimination_db_mean:.3f} | "
                "{peak_sidelobe_db_mean:.2f} |".format(**row)
            )
        lines.extend(
            [
                "",
                "On `h2_available`, `chain_feed_phase_only` applies chain phase only",
                "because a feed phase correction does not exist. The",
                "`chain_feed_equalized` row includes per-feed amplitude correction.",
                "",
                "## Calibration accuracy by SNR",
                "",
                "| architecture | SNR (dB) | calibrated phase RMSE (deg) | "
                "calibrated gain RMSE (dB) | uncalibrated phase RMSE (deg) |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for row in self.accuracy_by_snr:
            lines.append(
                "| {architecture} | {snr_db:.1f} | "
                "{calibration_phase_error_deg_mean:.4f} | "
                "{calibration_gain_error_db_mean:.4f} | "
                "{uncalibrated_phase_error_deg_mean:.4f} |".format(**row)
            )
        lines.extend(
            [
                "",
                "## Scalar per-feed-IQ baseline",
                "",
                "This is the original model assumption: 16 independent complex feed "
                "observations. It is retained as a clearly labeled baseline, not as "
                "an available H2 measurement path.",
                "",
                "| scenario | pointing err (deg) | array gain (dB) | peak sidelobe (dB) |",
                "|---|---:|---:|---:|",
            ]
        )
        for row in self.scalar_baseline_summary:
            lines.append(
                "| {scenario} | {pointing_error_deg_mean:.4f} | "
                "{array_gain_db_mean:.4f} | {peak_sidelobe_db_mean:.2f} |".format(**row)
            )
        lines.extend(
            [
                "",
                "## Fault scenarios",
                "",
                "| architecture | level | fault | detection rate | "
                "mean gain loss (dB) | mean false positives |",
                "|---|---|---|---:|---:|---:|",
            ]
        )
        for row in self.fault_summary:
            lines.append(
                "| {architecture} | {level} | {fault_type} | {detected_mean:.3f} | "
                "{gain_loss_db_mean:.3f} | {false_positives_mean:.3f} |".format(**row)
            )
        lines.extend(
            [
                "",
                "All IQ, path responses, polarization leakage, and calibration tables "
                "are synthetic. The ADAR1000 is not qualified at 8.4 GHz by this result.",
                "",
            ]
        )
        return "\n".join(lines)

    def to_markdown_file(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_markdown(), encoding="utf-8")


def run_observability_validation(
    topology: Topology,
    config: ObservabilityValidationConfig | None = None,
) -> ObservabilityValidationReport:
    """Run the chain/feed observability sweeps with Jones polarization metrics."""

    config = config or ObservabilityValidationConfig()
    config.validate()
    start = time.perf_counter()
    audit = audit_h2_observability(topology)
    incident = linear_jones(config.incident_polarization_deg)
    receiver = matched_receiver_jones(incident)
    cross_incident = orthogonal_jones(incident)

    records: list[dict[str, Any]] = []
    scalar_records: list[dict[str, Any]] = []
    accuracy_records: list[dict[str, Any]] = []
    for seed in config.seeds:
        for snr_db in config.snr_db_levels:
            for mismatch_scale in config.mismatch_scales:
                for architecture_name in config.architectures:
                    architecture = get_architecture(architecture_name)
                    measurement = simulate_hierarchical_measurements(
                        topology,
                        HierarchicalMeasurementConfig(
                            seed=seed,
                            snr_db=float(snr_db),
                            n_captures=config.n_captures,
                            n_samples=config.n_samples,
                            mismatch=config.base_mismatch.scaled(mismatch_scale),
                            architecture=architecture.name,
                        ),
                    )
                    calibration = calibrate_hierarchical(
                        topology, measurement, config.calibration
                    )
                    accuracy = hierarchical_calibration_accuracy(
                        measurement.truth_response, calibration
                    )
                    uncalibrated_accuracy = _accuracy_without_calibration(
                        measurement.truth_response, calibration.healthy_mask
                    )
                    accuracy_records.append(
                        {
                            "seed": seed,
                            "snr_db": float(snr_db),
                            "mismatch_scale": float(mismatch_scale),
                            "architecture": architecture.name,
                            "feed_phase_observable": architecture.feed_phase_observable,
                            "calibration_phase_error_deg": accuracy["phase_error_deg"],
                            "calibration_gain_error_db": accuracy["gain_error_db"],
                            "uncalibrated_phase_error_deg": uncalibrated_accuracy[
                                "phase_error_deg"
                            ],
                            "uncalibrated_gain_error_db": uncalibrated_accuracy[
                                "gain_error_db"
                            ],
                            "healthy_paths": int(np.sum(calibration.healthy_mask)),
                        }
                    )
                    for target_az, target_el in config.angles:
                        base_weights = polarized_steering_weights(
                            topology, target_az, target_el, receiver
                        )
                        phase_only_weights = apply_hierarchical_calibration(
                            base_weights, calibration, mode="phase_only"
                        )
                        quantized = quantize_weights(
                            phase_only_weights, config.quantizer
                        )
                        scenarios = {
                            "uncalibrated": base_weights,
                            "chain_only": apply_hierarchical_calibration(
                                base_weights, calibration, mode="chain_only"
                            ),
                            "chain_feed_phase_only": phase_only_weights,
                            "chain_feed_phase_only_quantized": quantized.weights,
                            "chain_feed_equalized": apply_hierarchical_calibration(
                                base_weights, calibration, mode="equalize"
                            ),
                        }
                        quantization_loss = quantization_loss_polarized_db(
                            topology,
                            phase_only_weights,
                            quantized.weights,
                            target_az,
                            target_el,
                            incident,
                            polarization=config.polarization,
                            path_response=measurement.truth_response,
                        )
                        for scenario, weights in scenarios.items():
                            beam = beam_metrics_polarized(
                                topology,
                                weights,
                                target_az,
                                target_el,
                                incident,
                                polarization=config.polarization,
                                path_response=measurement.truth_response,
                                cross_incident_jones=cross_incident,
                            )
                            records.append(
                                {
                                    "seed": seed,
                                    "snr_db": float(snr_db),
                                    "mismatch_scale": float(mismatch_scale),
                                    "architecture": architecture.name,
                                    "scenario": scenario,
                                    "target_az_deg": float(target_az),
                                    "target_el_deg": float(target_el),
                                    "pointing_error_deg": beam.pointing_error_deg,
                                    "co_pol_gain_db": beam.co_pol_gain_db,
                                    "cross_pol_gain_db": beam.cross_pol_gain_db,
                                    "cross_pol_discrimination_db": (
                                        beam.cross_pol_discrimination_db
                                    ),
                                    "peak_sidelobe_db": beam.peak_sidelobe_db,
                                    "phase_quantization_loss_db": (
                                        quantization_loss
                                        if scenario
                                        == "chain_feed_phase_only_quantized"
                                        else None
                                    ),
                                    "calibration_phase_error_deg": accuracy[
                                        "phase_error_deg"
                                    ],
                                    "calibration_gain_error_db": accuracy[
                                        "gain_error_db"
                                    ],
                                    "healthy_paths": int(
                                        np.sum(calibration.healthy_mask)
                                    ),
                                    "feed_phase_observable": (
                                        architecture.feed_phase_observable
                                    ),
                                    "realizable_on_current_h2": (
                                        architecture.realizable_on_current_h2
                                    ),
                                    "requires_hardware_change": (
                                        architecture.requires_hardware_change
                                    ),
                                }
                            )

                if (
                    config.include_scalar_baseline
                    and float(snr_db) == config.base_snr_db
                    and float(mismatch_scale) == 1.0
                ):
                    scalar_records.extend(
                        _run_scalar_baseline(
                            topology,
                            seed=seed,
                            snr_db=float(snr_db),
                            mismatch=config.base_mismatch,
                            n_captures=config.n_captures,
                            n_samples=config.n_samples,
                            angles=config.angles,
                            calibration_config=config.calibration,
                            quantizer=config.quantizer,
                        )
                    )

    fault_records = _run_fault_scenarios(topology, config, incident, cross_incident)
    aggregate = _summarize(
        records,
        ("architecture", "scenario"),
        metric_keys=(
            "pointing_error_deg",
            "co_pol_gain_db",
            "cross_pol_gain_db",
            "cross_pol_discrimination_db",
            "peak_sidelobe_db",
            "phase_quantization_loss_db",
            "calibration_phase_error_deg",
            "calibration_gain_error_db",
        ),
    )
    base_records = [
        record
        for record in records
        if float(record["snr_db"]) == config.base_snr_db
        and float(record["mismatch_scale"]) == 1.0
    ]
    base_case = _summarize(
        base_records,
        ("architecture", "scenario"),
        metric_keys=(
            "pointing_error_deg",
            "co_pol_gain_db",
            "cross_pol_gain_db",
            "cross_pol_discrimination_db",
            "peak_sidelobe_db",
            "phase_quantization_loss_db",
        ),
    )
    accuracy_by_snr = _summarize(
        accuracy_records,
        ("architecture", "snr_db"),
        metric_keys=(
            "calibration_phase_error_deg",
            "calibration_gain_error_db",
            "uncalibrated_phase_error_deg",
            "uncalibrated_gain_error_db",
        ),
    )
    accuracy_by_mismatch = _summarize(
        accuracy_records,
        ("architecture", "mismatch_scale"),
        metric_keys=(
            "calibration_phase_error_deg",
            "calibration_gain_error_db",
            "uncalibrated_phase_error_deg",
            "uncalibrated_gain_error_db",
        ),
    )
    scalar_baseline_summary = _summarize(
        scalar_records,
        ("scenario",),
        metric_keys=(
            "pointing_error_deg",
            "array_gain_db",
            "peak_sidelobe_db",
            "phase_quantization_loss_db",
        ),
    )
    fault_summary = _summarize(
        fault_records,
        ("architecture", "level", "fault_type"),
        metric_keys=("detected", "false_positives", "gain_loss_db"),
    )
    runtime_s = time.perf_counter() - start
    return ObservabilityValidationReport(
        topology_name=topology.name,
        carrier_freq_hz=topology.carrier_freq_hz,
        config=config,
        audit=audit,
        records=records,
        scalar_baseline_records=scalar_records,
        accuracy_records=accuracy_records,
        aggregate=aggregate,
        base_case=base_case,
        accuracy_by_snr=accuracy_by_snr,
        accuracy_by_mismatch=accuracy_by_mismatch,
        scalar_baseline_summary=scalar_baseline_summary,
        fault_records=fault_records,
        fault_summary=fault_summary,
        runtime_s=runtime_s,
        simulated=True,
    )


def _run_scalar_baseline(
    topology: Topology,
    *,
    seed: int,
    snr_db: float,
    mismatch: MismatchConfig,
    n_captures: int,
    n_samples: int,
    angles: tuple[tuple[float, float], ...],
    calibration_config: CalibrationConfig,
    quantizer: QuantizerConfig,
) -> list[dict[str, Any]]:
    measurement = simulate_measurements(
        topology,
        MeasurementConfig(
            seed=seed,
            snr_db=snr_db,
            n_captures=n_captures,
            n_samples=n_samples,
            mismatch=mismatch,
        ),
    )
    calibration = calibrate(topology, measurement, calibration_config)
    records: list[dict[str, Any]] = []
    for target_az, target_el in angles:
        base_weights = steering_weights(topology, target_az, target_el)
        phase_only_weights = apply_calibration(
            base_weights, calibration, mode="phase_only"
        )
        quantized = quantize_weights(phase_only_weights, quantizer)
        scenarios = {
            "scalar_ideal": (base_weights, None),
            "scalar_uncalibrated": (base_weights, measurement.truth_response),
            "scalar_calibrated_equalized": (
                apply_calibration(base_weights, calibration, mode="equalize"),
                measurement.truth_response,
            ),
            "scalar_calibrated_phase_only": (
                phase_only_weights,
                measurement.truth_response,
            ),
            "scalar_calibrated_phase_only_quantized": (
                quantized.weights,
                measurement.truth_response,
            ),
        }
        quant_loss = quantization_loss_db(
            topology,
            phase_only_weights,
            quantized.weights,
            target_az,
            target_el,
            path_response=measurement.truth_response,
        )
        for scenario, (weights, path_response) in scenarios.items():
            beam = beam_metrics(
                topology,
                weights,
                target_az,
                target_el,
                path_response=path_response,
            )
            records.append(
                {
                    "seed": seed,
                    "snr_db": snr_db,
                    "mismatch_scale": 1.0,
                    "model": "scalar_per_feed_iq_baseline",
                    "architecture": "ideal_16iq_nonrealizable",
                    "scenario": scenario,
                    "target_az_deg": float(target_az),
                    "target_el_deg": float(target_el),
                    "pointing_error_deg": beam.pointing_error_deg,
                    "array_gain_db": beam.array_gain_db,
                    "peak_sidelobe_db": beam.peak_sidelobe_db,
                    "phase_quantization_loss_db": (
                        quant_loss
                        if scenario == "scalar_calibrated_phase_only_quantized"
                        else None
                    ),
                }
            )
    return records


def _run_fault_scenarios(
    topology: Topology,
    config: ObservabilityValidationConfig,
    incident: np.ndarray,
    cross_incident: np.ndarray,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    angle_az, angle_el = 0.0, 0.0
    receiver = matched_receiver_jones(incident)
    for seed in config.fault_seeds:
        for architecture_name in config.fault_architectures:
            architecture = get_architecture(architecture_name)
            healthy_measurement = simulate_hierarchical_measurements(
                topology,
                HierarchicalMeasurementConfig(
                    seed=seed,
                    snr_db=config.base_snr_db,
                    n_captures=config.n_captures,
                    n_samples=config.n_samples,
                    mismatch=config.base_mismatch,
                    architecture=architecture.name,
                ),
            )
            healthy_calibration = calibrate_hierarchical(
                topology, healthy_measurement, config.calibration
            )
            healthy_weights = apply_hierarchical_calibration(
                polarized_steering_weights(topology, angle_az, angle_el, receiver),
                healthy_calibration,
            )
            healthy_beam = beam_metrics_polarized(
                topology,
                healthy_weights,
                angle_az,
                angle_el,
                incident,
                polarization=config.polarization,
                path_response=healthy_measurement.truth_response,
                cross_incident_jones=cross_incident,
            )
            for fault_type in ("missing", "faulty"):
                for chain in topology.chain_ids:
                    fault_measurement = simulate_hierarchical_measurements(
                        topology,
                        HierarchicalMeasurementConfig(
                            seed=seed,
                            snr_db=config.base_snr_db,
                            n_captures=config.n_captures,
                            n_samples=config.n_samples,
                            mismatch=config.base_mismatch,
                            faults=FaultSpec(chain_faults={chain: fault_type}),
                            architecture=architecture.name,
                        ),
                    )
                    calibration = calibrate_hierarchical(
                        topology, fault_measurement, config.calibration
                    )
                    weights = apply_hierarchical_calibration(
                        polarized_steering_weights(
                            topology, angle_az, angle_el, receiver
                        ),
                        calibration,
                    )
                    beam = beam_metrics_polarized(
                        topology,
                        weights,
                        angle_az,
                        angle_el,
                        incident,
                        polarization=config.polarization,
                        path_response=fault_measurement.truth_response,
                        cross_incident_jones=cross_incident,
                    )
                    detected = all(
                        item.status != "ok"
                        for item in calibration.chains
                        if item.chain == chain
                    )
                    false_positives = sum(
                        item.status != "ok"
                        for item in calibration.chains
                        if item.chain != chain
                    )
                    records.append(
                        {
                            "seed": seed,
                            "architecture": architecture.name,
                            "level": "chain",
                            "index": chain,
                            "fault_type": fault_type,
                            "detected": 1.0 if detected else 0.0,
                            "false_positives": float(false_positives),
                            "gain_db": beam.co_pol_gain_db,
                            "healthy_gain_db": healthy_beam.co_pol_gain_db,
                            "gain_loss_db": (
                                healthy_beam.co_pol_gain_db - beam.co_pol_gain_db
                            ),
                            "healthy_paths": int(
                                np.sum(calibration.healthy_mask)
                            ),
                        }
                    )
                for feed in topology.feeds:
                    fault_measurement = simulate_hierarchical_measurements(
                        topology,
                        HierarchicalMeasurementConfig(
                            seed=seed,
                            snr_db=config.base_snr_db,
                            n_captures=config.n_captures,
                            n_samples=config.n_samples,
                            mismatch=config.base_mismatch,
                            faults=FaultSpec(path_faults={feed.index: fault_type}),
                            architecture=architecture.name,
                        ),
                    )
                    calibration = calibrate_hierarchical(
                        topology, fault_measurement, config.calibration
                    )
                    weights = apply_hierarchical_calibration(
                        polarized_steering_weights(
                            topology, angle_az, angle_el, receiver
                        ),
                        calibration,
                    )
                    beam = beam_metrics_polarized(
                        topology,
                        weights,
                        angle_az,
                        angle_el,
                        incident,
                        polarization=config.polarization,
                        path_response=fault_measurement.truth_response,
                        cross_incident_jones=cross_incident,
                    )
                    detected = calibration.paths[feed.index].status != "ok"
                    false_positives = sum(
                        path.status != "ok"
                        for path in calibration.paths
                        if path.path_index != feed.index
                    )
                    records.append(
                        {
                            "seed": seed,
                            "architecture": architecture.name,
                            "level": "feed",
                            "index": feed.index,
                            "fault_type": fault_type,
                            "detected": 1.0 if detected else 0.0,
                            "false_positives": float(false_positives),
                            "gain_db": beam.co_pol_gain_db,
                            "healthy_gain_db": healthy_beam.co_pol_gain_db,
                            "gain_loss_db": (
                                healthy_beam.co_pol_gain_db - beam.co_pol_gain_db
                            ),
                            "healthy_paths": int(
                                np.sum(calibration.healthy_mask)
                            ),
                        }
                    )
    return records


def _accuracy_without_calibration(
    truth_response: np.ndarray, healthy_mask: np.ndarray
) -> dict[str, float]:
    return truth_calibration_accuracy(
        truth_response,
        np.ones_like(truth_response, dtype=np.complex128),
        healthy_mask=healthy_mask,
        target_response=None,
    )
