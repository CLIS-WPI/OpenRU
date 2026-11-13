"""Command-line interface for the simulated RF calibration model."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Sequence

from .beamforming import CodebookConfig, generate_codebook
from .calibration import CalibrationConfig, calibrate
from .measurement import (
    FaultSpec,
    MeasurementConfig,
    MeasurementSet,
    MismatchConfig,
    simulate_measurements,
)
from .observability import audit_h2_observability
from .observability_validation import (
    ObservabilityValidationConfig,
    run_observability_validation,
)
from .polarization import PolarizationConfig
from .quantization import QuantizerConfig
from .topology import Topology, load_topology
from .validation import ValidationConfig, run_validation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m openru_x6.rfcal",
        description=(
            "Simulated beamforming and calibration model for the OpenRU-X6 "
            "4T4R prototype. No hardware control or register writes are performed."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    topology_parser = subparsers.add_parser(
        "topology", help="write the default or supplied topology as JSON or CSV"
    )
    _add_topology_argument(topology_parser)
    topology_parser.add_argument("--output", type=Path, required=True)
    topology_parser.set_defaults(handler=_cmd_topology)

    codebook_parser = subparsers.add_parser(
        "codebook", help="generate a quantized steering codebook"
    )
    _add_topology_argument(codebook_parser)
    codebook_parser.add_argument("--output", type=Path, required=True)
    codebook_parser.add_argument("--az-min", type=float, default=-60.0)
    codebook_parser.add_argument("--az-max", type=float, default=60.0)
    codebook_parser.add_argument("--az-step", type=float, default=5.0)
    codebook_parser.add_argument("--el-min", type=float, default=-20.0)
    codebook_parser.add_argument("--el-max", type=float, default=20.0)
    codebook_parser.add_argument("--el-step", type=float, default=5.0)
    _add_quantizer_arguments(codebook_parser)
    codebook_parser.set_defaults(handler=_cmd_codebook)

    simulate_parser = subparsers.add_parser(
        "simulate", help="write a synthetic pilot measurement set"
    )
    _add_topology_argument(simulate_parser)
    simulate_parser.add_argument("--output", type=Path, required=True)
    _add_measurement_arguments(simulate_parser)
    simulate_parser.add_argument(
        "--faults-json",
        type=Path,
        help="JSON object with FaultSpec fields for synthetic fault injection",
    )
    simulate_parser.set_defaults(handler=_cmd_simulate)

    calibrate_parser = subparsers.add_parser(
        "calibrate", help="calibrate a measurement set and write JSON/CSV tables"
    )
    _add_topology_argument(calibrate_parser)
    calibrate_parser.add_argument("--output", type=Path, required=True)
    calibrate_parser.add_argument(
        "--measurements",
        type=Path,
        help="measurements JSON produced by the simulate command",
    )
    calibrate_parser.add_argument("--seed", type=int, default=0)
    calibrate_parser.add_argument("--snr-db", type=float, default=30.0)
    calibrate_parser.add_argument("--captures", type=int, default=4)
    calibrate_parser.add_argument("--samples", type=int, default=64)
    calibrate_parser.add_argument("--mismatch-scale", type=float, default=1.0)
    calibrate_parser.add_argument("--faults-json", type=Path)
    calibrate_parser.set_defaults(handler=_cmd_calibrate)

    audit_parser = subparsers.add_parser(
        "audit",
        help="write the H1/H2 calibration-observability audit as JSON",
    )
    _add_topology_argument(audit_parser)
    audit_parser.add_argument("--output", type=Path, required=True)
    audit_parser.set_defaults(handler=_cmd_audit)

    validate_parser = subparsers.add_parser(
        "validate", help="run the reproducible synthetic calibration sweep"
    )
    _add_topology_argument(validate_parser)
    validate_parser.add_argument("--output", type=Path, required=True)
    validate_parser.add_argument(
        "--quick", action="store_true", help="small deterministic sweep for smoke tests"
    )
    validate_parser.add_argument("--seeds", type=int, default=10)
    validate_parser.add_argument("--fault-seeds", type=int, default=3)
    validate_parser.add_argument("--snr-levels", default="10,20,30,40")
    validate_parser.add_argument("--mismatch-scales", default="0,0.5,1,2")
    validate_parser.add_argument(
        "--angles",
        default="-30,0;0,0;30,0;-20,10;20,-10",
        help="semicolon-separated az,el pairs in degrees",
    )
    validate_parser.add_argument("--captures", type=int, default=4)
    validate_parser.add_argument("--samples", type=int, default=64)
    validate_parser.add_argument(
        "--architectures",
        default=",".join(ObservabilityValidationConfig().architectures),
        help="comma-separated calibration architectures for the observability sweep",
    )
    validate_parser.add_argument("--incident-pol-deg", type=float, default=0.0)
    validate_parser.add_argument("--cross-pol-db", type=float, default=25.0)
    validate_parser.add_argument("--cross-pol-phase-deg", type=float, default=90.0)
    validate_parser.set_defaults(handler=_cmd_validate)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (ValueError, KeyError, OSError) as error:
        parser.error(str(error))
        return 2


def _cmd_topology(args: argparse.Namespace) -> int:
    topology = load_topology(args.topology)
    if args.output.suffix.lower() == ".csv":
        topology.to_csv(args.output)
    elif args.output.suffix.lower() == ".json" or not args.output.suffix:
        topology.to_json(args.output)
    else:
        raise ValueError("topology output must end in .json or .csv")
    print(f"wrote topology to {args.output}")
    print(
        f"{topology.n_chains} chains, {topology.n_feeds} feeds, "
        f"{topology.n_sites} dual-polarized sites, "
        f"{topology.carrier_freq_hz / 1e9:.3f} GHz"
    )
    return 0


def _cmd_codebook(args: argparse.Namespace) -> int:
    topology = load_topology(args.topology)
    config = CodebookConfig(
        az_min_deg=args.az_min,
        az_max_deg=args.az_max,
        az_step_deg=args.az_step,
        el_min_deg=args.el_min,
        el_max_deg=args.el_max,
        el_step_deg=args.el_step,
        quantizer=_quantizer_from_args(args),
    )
    codebook = generate_codebook(topology, config)
    if args.output.suffix.lower() == ".csv":
        codebook.to_csv(args.output)
    elif args.output.suffix.lower() == ".json" or not args.output.suffix:
        codebook.to_json(args.output)
    else:
        raise ValueError("codebook output must end in .json or .csv")
    print(f"wrote {len(codebook.entries)} beams to {args.output}")
    return 0


def _cmd_simulate(args: argparse.Namespace) -> int:
    topology = load_topology(args.topology)
    faults = _load_faults(args.faults_json)
    measurement = simulate_measurements(
        topology, _measurement_config_from_args(args, faults=faults)
    )
    measurement.to_json(args.output)
    print(
        f"wrote simulated measurements to {args.output}: "
        f"{measurement.n_feeds} feeds x {measurement.n_captures} captures x "
        f"{measurement.n_samples} samples"
    )
    return 0


def _cmd_calibrate(args: argparse.Namespace) -> int:
    topology = load_topology(args.topology)
    if args.measurements is not None:
        measurement = MeasurementSet.from_json(args.measurements)
    else:
        faults = _load_faults(args.faults_json)
        measurement = simulate_measurements(
            topology,
            MeasurementConfig(
                seed=args.seed,
                snr_db=args.snr_db,
                n_captures=args.captures,
                n_samples=args.samples,
                mismatch=MismatchConfig().scaled(args.mismatch_scale),
                faults=faults,
            ),
        )
    calibration = calibrate(topology, measurement, CalibrationConfig())
    output_dir = _ensure_dir(args.output)
    calibration.to_json(output_dir / "calibration.json")
    calibration.to_csv(output_dir / "calibration.csv")
    (output_dir / "calibration_summary.md").write_text(
        _calibration_markdown(calibration),
        encoding="utf-8",
    )
    print(
        f"wrote calibration to {output_dir} "
        f"(healthy={int(calibration.healthy_mask.sum())}/{calibration.n_feeds}, "
        f"statuses={calibration.status_counts})"
    )
    return 0


def _cmd_audit(args: argparse.Namespace) -> int:
    topology = load_topology(args.topology)
    audit = audit_h2_observability(topology)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote observability audit to {path}")
    print(audit["conclusion"])
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    topology = load_topology(args.topology)
    if args.quick:
        config = ValidationConfig.quick()
        observability_config = ObservabilityValidationConfig.quick()
    else:
        angles = tuple(_parse_angles(args.angles))
        snr_levels = tuple(_parse_floats(args.snr_levels))
        mismatch_scales = tuple(_parse_floats(args.mismatch_scales))
        config = ValidationConfig(
            seeds=tuple(range(args.seeds)),
            fault_seeds=tuple(range(args.fault_seeds)),
            snr_db_levels=snr_levels,
            mismatch_scales=mismatch_scales,
            angles=angles,
            n_captures=args.captures,
            n_samples=args.samples,
        )
        observability_config = ObservabilityValidationConfig(
            seeds=tuple(range(args.seeds)),
            fault_seeds=tuple(range(args.fault_seeds)),
            snr_db_levels=snr_levels,
            mismatch_scales=mismatch_scales,
            angles=angles,
            n_captures=args.captures,
            n_samples=args.samples,
            architectures=tuple(
                item.strip()
                for item in args.architectures.split(",")
                if item.strip()
            ),
            polarization=PolarizationConfig(
                cross_pol_db=args.cross_pol_db,
                cross_pol_phase_deg=args.cross_pol_phase_deg,
            ),
            incident_polarization_deg=args.incident_pol_deg,
        )
    report = run_validation(topology, config)
    observability_report = run_observability_validation(topology, observability_config)
    output_dir = _ensure_dir(args.output)
    report.to_json(output_dir / "validation.json", include_records=True)
    report.to_json(output_dir / "reference_summary.json", include_records=False)
    report.to_csv(output_dir / "validation_runs.csv")
    report.to_markdown_file(output_dir / "report.md")
    if report.calibration_example is not None:
        report.calibration_example.to_json(output_dir / "calibration_example.json")
        report.calibration_example.to_csv(output_dir / "calibration_example.csv")
    observability_report.to_json(
        output_dir / "observability_validation.json", include_records=True
    )
    observability_report.to_json(
        output_dir / "observability_reference_summary.json", include_records=False
    )
    observability_report.to_csv(output_dir / "observability_runs.csv")
    observability_report.to_markdown_file(output_dir / "observability_report.md")
    (output_dir / "observability_audit.json").write_text(
        json.dumps(observability_report.audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"wrote scalar-baseline validation to {output_dir} in {report.runtime_s:.3f} s "
        f"({len(report.records)} beam records, "
        f"{len(report.fault_records)} fault records)"
    )
    print(
        f"wrote observability validation in {observability_report.runtime_s:.3f} s "
        f"({len(observability_report.records)} beam records, "
        f"{len(observability_report.fault_records)} fault records)"
    )
    return 0


def _add_topology_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--topology",
        type=Path,
        help="topology JSON or H1 feed-map CSV; omit for the embedded 4T4R topology",
    )


def _add_quantizer_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--phase-step-deg", type=float, default=360.0 / 128.0)
    parser.add_argument("--gain-step-db", type=float, default=0.5)
    parser.add_argument("--gain-range-db", type=float, default=31.0)


def _add_measurement_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--snr-db", type=float, default=30.0)
    parser.add_argument("--captures", type=int, default=4)
    parser.add_argument("--samples", type=int, default=64)
    parser.add_argument("--mismatch-scale", type=float, default=1.0)


def _quantizer_from_args(args: argparse.Namespace) -> QuantizerConfig:
    return QuantizerConfig(
        phase_step_deg=args.phase_step_deg,
        gain_step_db=args.gain_step_db,
        gain_range_db=args.gain_range_db,
        name="cli-custom",
        source="CLI-supplied quantizer",
    )


def _measurement_config_from_args(
    args: argparse.Namespace, *, faults: FaultSpec
) -> MeasurementConfig:
    return MeasurementConfig(
        seed=args.seed,
        snr_db=args.snr_db,
        n_captures=args.captures,
        n_samples=args.samples,
        mismatch=MismatchConfig().scaled(args.mismatch_scale),
        faults=faults,
    )


def _load_faults(path: Path | None) -> FaultSpec:
    if path is None:
        return FaultSpec()
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return FaultSpec.from_dict(data)


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _parse_floats(text: str) -> list[float]:
    values = [item.strip() for item in text.split(",") if item.strip()]
    if not values:
        raise ValueError("expected at least one numeric value")
    return [float(item) for item in values]


def _parse_angles(text: str) -> list[tuple[float, float]]:
    angles: list[tuple[float, float]] = []
    for item in text.split(";"):
        item = item.strip()
        if not item:
            continue
        parts = [part.strip() for part in item.split(",")]
        if len(parts) != 2:
            raise ValueError(f"invalid angle pair: {item!r}")
        angles.append((float(parts[0]), float(parts[1])))
    if not angles:
        raise ValueError("expected at least one angle pair")
    return angles


def _calibration_markdown(calibration) -> str:
    target_amplitude_db = 20.0 * math.log10(abs(calibration.target_response))
    target_phase_deg = math.degrees(
        math.atan2(
            calibration.target_response.imag,
            calibration.target_response.real,
        )
    )
    lines = [
        "# Simulated RF Calibration Summary",
        "",
        "**Evidence label: SIMULATED.** No hardware measurements are present.",
        "",
        f"- Topology: `{calibration.topology_name}`",
        f"- Seed: `{calibration.seed}`",
        f"- Target amplitude: `{target_amplitude_db:.3f} dB`",
        f"- Target phase: `{target_phase_deg:.3f} deg`",
        f"- Healthy paths: `{int(calibration.healthy_mask.sum())}/{calibration.n_feeds}`",
        f"- Status counts: `{calibration.status_counts}`",
        "",
        "| path | chain | pol | measured (dB) | measured phase (deg) | status | correction |",
        "|---:|---:|---|---:|---:|---|---:|",
    ]
    for path in calibration.paths:
        lines.append(
            f"| {path.path_index} | {path.chain} | {path.polarization} | "
            f"{path.measured_amplitude_db:.3f} | {path.measured_phase_deg:.3f} | "
            f"{path.status} | {path.correction_amplitude:.4f} |"
        )
    lines.append("")
    return "\n".join(lines)

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
