"""Reproducible synthetic calibration sweeps and report generation."""

from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .beamforming import steering_weights
from .calibration import (
    CalibrationConfig,
    CalibrationResult,
    apply_calibration,
    calibrate,
)
from .measurement import FaultSpec, MeasurementConfig, MeasurementSet, MismatchConfig
from .metrics import (
    beam_metrics,
    quantization_loss_db,
    truth_calibration_accuracy,
)
from .quantization import QuantizerConfig, quantize_weights
from .topology import Topology

DEFAULT_ANGLES = ((-30.0, 0.0), (0.0, 0.0), (30.0, 0.0), (-20.0, 10.0), (20.0, -10.0))


@dataclass(frozen=True)
class ValidationConfig:
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
    fault_seeds: tuple[int, ...] = (0, 1, 2)

    def validate(self) -> None:
        if not self.seeds:
            raise ValueError("at least one seed is required")
        if not self.snr_db_levels:
            raise ValueError("at least one SNR level is required")
        if not self.mismatch_scales:
            raise ValueError("at least one mismatch scale is required")
        if not self.angles:
            raise ValueError("at least one steering angle is required")
        if not self.fault_seeds:
            raise ValueError("at least one fault seed is required")
        if self.n_captures < 1 or self.n_samples < 2:
            raise ValueError("invalid capture or sample count")
        self.calibration.validate()
        self.quantizer.validate()

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
            "fault_seeds": list(self.fault_seeds),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ValidationConfig":
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
            fault_seeds=tuple(int(value) for value in data.get("fault_seeds", (0, 1, 2))),
        )
        config.validate()
        return config

    @classmethod
    def quick(cls) -> "ValidationConfig":
        return cls(
            seeds=(0, 1, 2),
            snr_db_levels=(20.0, 30.0),
            mismatch_scales=(0.0, 1.0),
            angles=((0.0, 0.0), (30.0, 0.0)),
            fault_seeds=(0,),
        )


@dataclass
class ValidationReport:
    topology_name: str
    carrier_freq_hz: float
    config: ValidationConfig
    records: list[dict[str, Any]]
    aggregate: list[dict[str, Any]]
    by_snr: list[dict[str, Any]]
    by_mismatch: list[dict[str, Any]]
    accuracy_by_snr: list[dict[str, Any]]
    accuracy_by_mismatch: list[dict[str, Any]]
    fault_records: list[dict[str, Any]]
    fault_summary: list[dict[str, Any]]
    calibration_example: CalibrationResult | None
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
            "aggregate": self.aggregate,
            "by_snr": self.by_snr,
            "by_mismatch": self.by_mismatch,
            "accuracy_by_snr": self.accuracy_by_snr,
            "accuracy_by_mismatch": self.accuracy_by_mismatch,
            "fault_summary": self.fault_summary,
            "fault_records": self.fault_records,
            "calibration_example": (
                self.calibration_example.to_dict()
                if self.calibration_example is not None
                else None
            ),
        }
        if include_records:
            payload["records"] = self.records
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
            raise ValueError("no validation records to write")
        fieldnames = list(self.records[0].keys())
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.records)

    def to_markdown(self) -> str:
        lines = [
            "# Scalar RF Calibration Validation Baseline",
            "",
            "**Evidence label: SIMULATED.** No hardware measurements are present.",
            "",
            "This baseline assumes 16 independent complex feed observations. The",
            "current H2 does not provide that measurement; see",
            "`docs/rfcal/OBSERVABILITY_REPORT.md` for the observable architecture",
            "results.",
            "",
            f"- Topology: `{self.topology_name}`",
            f"- Carrier: `{self.carrier_freq_hz / 1e9:.3f} GHz`",
            f"- Seeds: `{len(self.config.seeds)}`, SNR levels: `{len(self.config.snr_db_levels)}`, "
            f"mismatch scales: `{len(self.config.mismatch_scales)}`",
            f"- Beam angles: `{len(self.config.angles)}`",
            f"- Measured software runtime: `{self.runtime_s:.3f} s`",
            "",
            "## Beam metrics by scenario",
            "",
            "| scenario | n | pointing err (deg) | array gain (dB) | peak sidelobe (dB) |",
            "|---|---:|---:|---:|---:|",
        ]
        for row in self.aggregate:
            lines.append(
                "| {scenario} | {count} | {pointing_error_deg_mean:.4f} | "
                "{array_gain_db_mean:.4f} | {peak_sidelobe_db_mean:.2f} |".format(**row)
            )
        lines.extend(
            [
                "",
                "## Calibrated vs uncalibrated by mismatch scale",
                "",
                "| mismatch | scenario | n | pointing err (deg) | "
                "array gain (dB) | peak sidelobe (dB) |",
                "|---:|---|---:|---:|---:|---:|",
            ]
        )
        for row in self.by_mismatch:
            if row["scenario"] in {
                "uncalibrated",
                "calibrated_equalized",
                "calibrated_phase_only",
            }:
                lines.append(
                    "| {mismatch_scale:.1f} | {scenario} | {count} | "
                    "{pointing_error_deg_mean:.4f} | {array_gain_db_mean:.4f} | "
                    "{peak_sidelobe_db_mean:.2f} |".format(**row)
                )
        lines.extend(
            [
                "",
                "## Calibration accuracy against simulated truth",
                "",
                "| SNR (dB) | phase RMSE (deg) | gain RMSE (dB) |",
                "|---:|---:|---:|",
            ]
        )
        for row in self.accuracy_by_snr:
            lines.append(
                "| {snr_db:.1f} | {calibration_phase_error_deg_mean:.4f} | "
                "{calibration_gain_error_db_mean:.4f} |".format(**row)
            )
        lines.extend(
            [
                "",
                "## Failed RF-chain scenarios",
                "",
                "| chain | fault | detection rate | mean gain loss (dB) | false positives |",
                "|---:|---|---:|---:|---:|",
            ]
        )
        for row in self.fault_summary:
            lines.append(
                "| {chain} | {fault_type} | {detected_mean:.3f} | "
                "{gain_loss_db_mean:.3f} | {false_positives_mean:.3f} |".format(**row)
            )
        lines.extend(
            [
                "",
                "All IQ, path responses, and calibration tables are synthetic. "
                "The ADAR1000 is not qualified at 8.4 GHz by this result.",
                "",
            ]
        )
        return "\n".join(lines)

    def to_markdown_file(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_markdown(), encoding="utf-8")


def run_validation(
    topology: Topology,
    config: ValidationConfig | None = None,
) -> ValidationReport:
    """Run deterministic calibration/beamforming sweeps and fault scenarios."""

    config = config or ValidationConfig()
    config.validate()
    start = time.perf_counter()
    records: list[dict[str, Any]] = []
    accuracy_records: list[dict[str, Any]] = []
    calibration_example: CalibrationResult | None = None
    first_calibration: CalibrationResult | None = None

    for seed in config.seeds:
        for snr_db in config.snr_db_levels:
            for mismatch_scale in config.mismatch_scales:
                measurement = simulate_measurements(
                    topology,
                    MeasurementConfig(
                        seed=seed,
                        snr_db=snr_db,
                        n_captures=config.n_captures,
                        n_samples=config.n_samples,
                        mismatch=config.base_mismatch.scaled(mismatch_scale),
                    ),
                )
                calibration = calibrate(topology, measurement, config.calibration)
                if first_calibration is None:
                    first_calibration = calibration
                accuracy = truth_calibration_accuracy(
                    measurement.truth_response,
                    calibration.corrections,
                    healthy_mask=calibration.healthy_mask,
                    target_response=calibration.target_response,
                )
                uncalibrated_accuracy = truth_calibration_accuracy(
                    measurement.truth_response,
                    np.ones(topology.n_feeds, dtype=np.complex128),
                    healthy_mask=calibration.healthy_mask,
                    target_response=calibration.target_response,
                )
                accuracy_records.append(
                    {
                        "seed": seed,
                        "snr_db": float(snr_db),
                        "mismatch_scale": float(mismatch_scale),
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
                if (
                    calibration_example is None
                    and seed == config.seeds[0]
                    and float(mismatch_scale) == 1.0
                    and float(snr_db) == config.base_snr_db
                ):
                    calibration_example = calibration

                for target_az, target_el in config.angles:
                    base_weights = steering_weights(topology, target_az, target_el)
                    equalized_weights = apply_calibration(
                        base_weights, calibration, mode="equalize"
                    )
                    phase_only_weights = apply_calibration(
                        base_weights, calibration, mode="phase_only"
                    )
                    quantized = quantize_weights(
                        phase_only_weights, config.quantizer
                    )
                    scenarios = {
                        "ideal": (base_weights, None),
                        "uncalibrated": (base_weights, measurement.truth_response),
                        "calibrated_equalized": (
                            equalized_weights,
                            measurement.truth_response,
                        ),
                        "calibrated_phase_only": (
                            phase_only_weights,
                            measurement.truth_response,
                        ),
                        "calibrated_phase_only_quantized": (
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
                        status_counts = calibration.status_counts
                        records.append(
                            {
                                "seed": seed,
                                "snr_db": float(snr_db),
                                "mismatch_scale": float(mismatch_scale),
                                "scenario": scenario,
                                "target_az_deg": float(target_az),
                                "target_el_deg": float(target_el),
                                "pointing_error_deg": beam.pointing_error_deg,
                                "array_gain_db": beam.array_gain_db,
                                "peak_sidelobe_db": beam.peak_sidelobe_db,
                                "phase_quantization_loss_db": (
                                    quant_loss
                                    if scenario == "calibrated_phase_only_quantized"
                                    else None
                                ),
                                "calibration_phase_error_deg": accuracy[
                                    "phase_error_deg"
                                ],
                                "calibration_gain_error_db": accuracy["gain_error_db"],
                                "healthy_paths": int(np.sum(calibration.healthy_mask)),
                                "missing_paths": status_counts["missing"],
                                "faulty_paths": status_counts["faulty"],
                                "inconsistent_paths": status_counts["inconsistent"],
                            }
                        )

    if calibration_example is None:
        calibration_example = first_calibration
    fault_records = _run_fault_scenarios(topology, config)
    aggregate = _summarize(records, ("scenario",))
    by_snr = _summarize(records, ("snr_db", "scenario"))
    by_mismatch = _summarize(records, ("mismatch_scale", "scenario"))
    accuracy_by_snr = _summarize(
        accuracy_records,
        ("snr_db",),
        metric_keys=(
            "calibration_phase_error_deg",
            "calibration_gain_error_db",
            "uncalibrated_phase_error_deg",
            "uncalibrated_gain_error_db",
        ),
    )
    accuracy_by_mismatch = _summarize(
        accuracy_records,
        ("mismatch_scale",),
        metric_keys=(
            "calibration_phase_error_deg",
            "calibration_gain_error_db",
            "uncalibrated_phase_error_deg",
            "uncalibrated_gain_error_db",
        ),
    )
    fault_summary = _summarize(
        fault_records,
        ("chain", "fault_type"),
        metric_keys=("detected", "false_positives", "gain_loss_db"),
    )
    runtime_s = time.perf_counter() - start
    return ValidationReport(
        topology_name=topology.name,
        carrier_freq_hz=topology.carrier_freq_hz,
        config=config,
        records=records,
        aggregate=aggregate,
        by_snr=by_snr,
        by_mismatch=by_mismatch,
        accuracy_by_snr=accuracy_by_snr,
        accuracy_by_mismatch=accuracy_by_mismatch,
        fault_records=fault_records,
        fault_summary=fault_summary,
        calibration_example=calibration_example,
        runtime_s=runtime_s,
        simulated=True,
    )


def simulate_measurements(topology: Topology, config: MeasurementConfig) -> MeasurementSet:
    from .measurement import simulate_measurements as _simulate

    return _simulate(topology, config)


def _run_fault_scenarios(
    topology: Topology, config: ValidationConfig
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    angle_az, angle_el = 0.0, 0.0
    for seed in config.fault_seeds:
        healthy_measurement = simulate_measurements(
            topology,
            MeasurementConfig(
                seed=seed,
                snr_db=config.base_snr_db,
                n_captures=config.n_captures,
                n_samples=config.n_samples,
                mismatch=config.base_mismatch,
            ),
        )
        healthy_calibration = calibrate(topology, healthy_measurement, config.calibration)
        healthy_weights = apply_calibration(
            steering_weights(topology, angle_az, angle_el), healthy_calibration
        )
        healthy_beam = beam_metrics(
            topology,
            healthy_weights,
            angle_az,
            angle_el,
            path_response=healthy_measurement.truth_response,
        )
        for fault_type in ("missing", "faulty"):
            for chain in topology.chain_ids:
                fault_measurement = simulate_measurements(
                    topology,
                    MeasurementConfig(
                        seed=seed,
                        snr_db=config.base_snr_db,
                        n_captures=config.n_captures,
                        n_samples=config.n_samples,
                        mismatch=config.base_mismatch,
                        faults=FaultSpec(chain_faults={chain: fault_type}),
                    ),
                )
                calibration = calibrate(
                    topology, fault_measurement, config.calibration
                )
                weights = apply_calibration(
                    steering_weights(topology, angle_az, angle_el), calibration
                )
                beam = beam_metrics(
                    topology,
                    weights,
                    angle_az,
                    angle_el,
                    path_response=fault_measurement.truth_response,
                )
                chain_paths = [
                    path for path in calibration.paths if path.chain == chain
                ]
                detected = all(path.status != "ok" for path in chain_paths)
                false_positives = sum(
                    path.status != "ok"
                    for path in calibration.paths
                    if path.chain != chain
                )
                records.append(
                    {
                        "seed": seed,
                        "chain": chain,
                        "fault_type": fault_type,
                        "detected": 1.0 if detected else 0.0,
                        "false_positives": float(false_positives),
                        "gain_db": beam.array_gain_db,
                        "healthy_gain_db": healthy_beam.array_gain_db,
                        "gain_loss_db": healthy_beam.array_gain_db
                        - beam.array_gain_db,
                        "healthy_paths": int(np.sum(calibration.healthy_mask)),
                        "missing_paths": calibration.status_counts["missing"],
                        "faulty_paths": calibration.status_counts["faulty"],
                        "inconsistent_paths": calibration.status_counts["inconsistent"],
                    }
                )
    return records


def _summarize(
    records: Iterable[dict[str, Any]],
    group_keys: tuple[str, ...],
    *,
    metric_keys: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    records = list(records)
    if not records:
        return []
    if metric_keys is None:
        metric_keys = (
            "pointing_error_deg",
            "array_gain_db",
            "peak_sidelobe_db",
            "phase_quantization_loss_db",
            "calibration_phase_error_deg",
            "calibration_gain_error_db",
        )
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for record in records:
        key = tuple(record[key] for key in group_keys)
        groups.setdefault(key, []).append(record)
    summary: list[dict[str, Any]] = []
    for key, group in sorted(groups.items(), key=lambda item: item[0]):
        row: dict[str, Any] = {name: value for name, value in zip(group_keys, key)}
        row["count"] = len(group)
        for metric in metric_keys:
            values = np.asarray(
                [record[metric] for record in group if record.get(metric) is not None],
                dtype=float,
            )
            values = values[np.isfinite(values)]
            row[f"{metric}_mean"] = float(np.mean(values)) if values.size else float("nan")
            row[f"{metric}_std"] = (
                float(np.std(values, ddof=0)) if values.size else float("nan")
            )
        summary.append(row)
    return summary
