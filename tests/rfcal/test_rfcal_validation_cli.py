from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from openru_x6.rfcal.cli import main
from openru_x6.rfcal.topology import load_topology
from openru_x6.rfcal.validation import ValidationConfig, run_validation


def test_quick_validation_structure_and_determinism() -> None:
    topology = load_topology()
    config = ValidationConfig.quick()
    first = run_validation(topology, config)
    second = run_validation(topology, config)
    expected_records = (
        len(config.seeds)
        * len(config.snr_db_levels)
        * len(config.mismatch_scales)
        * len(config.angles)
        * 5
    )
    assert len(first.records) == expected_records
    assert len(first.fault_records) == len(config.fault_seeds) * 2 * topology.n_chains
    assert first.runtime_s > 0.0
    assert first.calibration_example is not None
    assert first.records == second.records
    assert json.dumps(first.aggregate, sort_keys=True) == json.dumps(
        second.aggregate, sort_keys=True
    )
    scenarios = {row["scenario"] for row in first.aggregate}
    assert scenarios == {
        "ideal",
        "uncalibrated",
        "calibrated_equalized",
        "calibrated_phase_only",
        "calibrated_phase_only_quantized",
    }
    assert all(row["detected_mean"] == 1.0 for row in first.fault_summary)


def test_validation_outputs_json_csv_and_markdown(tmp_path: Path) -> None:
    output = tmp_path / "validation"
    assert (
        main(
            [
                "validate",
                "--quick",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    for name in (
        "validation.json",
        "reference_summary.json",
        "validation_runs.csv",
        "report.md",
        "calibration_example.json",
        "calibration_example.csv",
        "observability_validation.json",
        "observability_reference_summary.json",
        "observability_runs.csv",
        "observability_report.md",
        "observability_audit.json",
    ):
        assert (output / name).stat().st_size > 0
    payload = json.loads((output / "reference_summary.json").read_text(encoding="utf-8"))
    assert payload["simulated"]
    assert payload["evidence_label"] == "SIMULATED"
    assert payload["hardware_measured"] is False
    assert "records" not in payload
    assert "RF Calibration Validation" in (output / "report.md").read_text(
        encoding="utf-8"
    )
    observability_payload = json.loads(
        (output / "observability_reference_summary.json").read_text(encoding="utf-8")
    )
    assert observability_payload["evidence_label"] == "SIMULATED"
    assert observability_payload["hardware_measured"] is False
    assert observability_payload["audit"]["identifiability"]["feed_phase"] is False
    assert "records" not in observability_payload
    observability_markdown = (output / "observability_report.md").read_text(
        encoding="utf-8"
    )
    assert "Observability-Aware RF Calibration Validation" in observability_markdown
    assert "Scalar per-feed-IQ baseline" in observability_markdown


def test_cli_topology_simulate_calibrate_and_codebook(tmp_path: Path) -> None:
    topology_path = tmp_path / "topology.json"
    measurements_path = tmp_path / "measurements.json"
    calibration_dir = tmp_path / "calibration"
    codebook_path = tmp_path / "codebook.csv"
    assert main(["topology", "--output", str(topology_path)]) == 0
    assert main(
        [
            "simulate",
            "--seed",
            "7",
            "--captures",
            "2",
            "--samples",
            "16",
            "--output",
            str(measurements_path),
        ]
    ) == 0
    assert main(
        [
            "calibrate",
            "--topology",
            str(topology_path),
            "--measurements",
            str(measurements_path),
            "--output",
            str(calibration_dir),
        ]
    ) == 0
    assert main(
        [
            "codebook",
            "--topology",
            str(topology_path),
            "--az-min",
            "-5",
            "--az-max",
            "5",
            "--az-step",
            "5",
            "--el-min",
            "0",
            "--el-max",
            "0",
            "--el-step",
            "5",
            "--output",
            str(codebook_path),
        ]
    ) == 0
    assert (calibration_dir / "calibration.json").stat().st_size > 0
    assert (calibration_dir / "calibration.csv").stat().st_size > 0
    assert (calibration_dir / "calibration_summary.md").stat().st_size > 0
    assert codebook_path.stat().st_size > 0
    calibration = json.loads(
        (calibration_dir / "calibration.json").read_text(encoding="utf-8")
    )
    assert calibration["simulated"]
    assert len(calibration["paths"]) == 16
    assert np.isfinite(calibration["target_response_real"])


def test_cli_audit_writes_observability_evidence(tmp_path: Path) -> None:
    output = tmp_path / "audit.json"
    assert main(["audit", "--output", str(output)]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["evidence_label"] == "SCHEMATIC_AUDIT"
    assert payload["identifiability"]["feed_phase"] is False
    assert payload["findings"]


def test_cli_rejects_unknown_output_format(tmp_path: Path) -> None:
    try:
        main(["topology", "--output", str(tmp_path / "topology.txt")])
    except SystemExit as error:
        assert error.code == 2
    else:
        raise AssertionError("expected argparse error")
