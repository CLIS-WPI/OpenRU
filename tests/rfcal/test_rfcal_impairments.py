from __future__ import annotations

import json
from pathlib import Path

import pytest

from openru_x6.rfcal.cli import main
from openru_x6.rfcal.impairments import (
    DEFAULT_IMPAIRMENT_CASES,
    ImpairmentConfig,
    ImpairmentValidationConfig,
    run_impairment_validation,
)
from openru_x6.rfcal.topology import load_topology


def _case(name: str):
    return next(case for case in DEFAULT_IMPAIRMENT_CASES if case.name == name)


def _small_config(
    names: tuple[str, ...],
    *,
    resolution_steps: tuple[float, ...] = (0.25,),
) -> ImpairmentValidationConfig:
    return ImpairmentValidationConfig(
        seeds=(0,),
        n_captures=2,
        n_samples=16,
        angles=((0.37, 0.23),),
        search_step_deg=0.05,
        search_span_deg=2.0,
        resolution_search_steps=resolution_steps,
        resolution_search_span_deg=2.0,
        resolution_angles=((0.37, 0.23),),
        cases=tuple(_case(name) for name in names),
    )


def test_impairment_cases_separate_common_and_independent_errors() -> None:
    names = (
        "h3_no_impairment",
        "h2_no_impairment",
        "reference_drift_0p5deg",
        "reference_drift_common_0p5deg",
        "switch_leakage_20db_simultaneous",
        "switch_leakage_20db_one_at_a_time",
        "phase_noise_2deg",
        "phase_noise_common_2deg",
        "mutual_coupling_20db",
        "mutual_coupling_30db",
    )
    report = run_impairment_validation(load_topology(), _small_config(names))
    rows = {row["case"]: row for row in report.summary}
    h3 = rows["h3_no_impairment"]["pointing_error_deg_mean"]
    h2 = rows["h2_no_impairment"]["pointing_error_deg_mean"]

    assert h3 < h2
    assert rows["reference_drift_common_0p5deg"]["pointing_error_deg_mean"] == pytest.approx(
        h3, abs=1e-9
    )
    assert rows["phase_noise_common_2deg"]["pointing_error_deg_mean"] == pytest.approx(
        h3, abs=1e-9
    )
    assert rows["reference_drift_0p5deg"]["pointing_error_deg_mean"] > h3
    assert rows["phase_noise_2deg"]["pointing_error_deg_mean"] > h3
    assert rows["switch_leakage_20db_one_at_a_time"][
        "pointing_error_deg_mean"
    ] == pytest.approx(h3, abs=1e-9)
    assert (
        rows["switch_leakage_20db_simultaneous"]["pointing_error_deg_mean"]
        > rows["switch_leakage_20db_one_at_a_time"]["pointing_error_deg_mean"]
    )
    assert (
        rows["mutual_coupling_20db"]["pointing_error_deg_mean"]
        > rows["mutual_coupling_30db"]["pointing_error_deg_mean"]
        > h3
    )
    assert all(row["count"] == 1 for row in report.summary)
    assert all(row["pointing_error_deg_std"] >= 0.0 for row in report.summary)


def test_impairment_resolution_study_and_serialization(tmp_path: Path) -> None:
    config = _small_config(
        ("h3_no_impairment", "h2_no_impairment"),
        resolution_steps=(0.25, 0.05),
    )
    report = run_impairment_validation(load_topology(), config)
    rows = {row["search_step_deg"]: row for row in report.resolution_summary}
    coarse = rows[0.25]
    fine = rows[0.05]
    assert coarse["pointing_error_deg_mean"] > fine["pointing_error_deg_mean"]
    assert fine["pointing_error_deg_mean"] <= fine["grid_quantization_bound_deg"]

    summary_payload = report.to_dict(include_records=False)
    assert summary_payload["evidence_label"] == "SIMULATED"
    assert summary_payload["hardware_measured"] is False
    assert "records" not in summary_payload
    assert summary_payload["config"]["search_span_deg"] == config.search_span_deg
    assert (
        summary_payload["config"]["resolution_search_span_deg"]
        == config.resolution_search_span_deg
    )

    json_path = tmp_path / "impairments.json"
    summary_path = tmp_path / "summary.json"
    csv_path = tmp_path / "runs.csv"
    markdown_path = tmp_path / "report.md"
    report.to_json(json_path, include_records=True)
    report.to_json(summary_path, include_records=False)
    report.to_csv(csv_path)
    report.to_markdown_file(markdown_path)
    assert json_path.stat().st_size > summary_path.stat().st_size
    assert csv_path.stat().st_size > 0
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "Hardware Impairment and Uncertainty Validation" in markdown
    assert "0.01 deg" in markdown
    assert "SIMULATED" in markdown


def test_impairment_config_round_trip_and_validation() -> None:
    config = ImpairmentConfig(
        reference_drift_phase_std_deg=0.5,
        switch_leakage_db=-20.0,
        switch_leakage_simultaneous=True,
        mutual_coupling_db=-25.0,
        correlated_phase_std_deg=0.2,
    )
    assert ImpairmentConfig.from_dict(config.to_dict()) == config
    assert not config.is_ideal
    assert ImpairmentConfig().is_ideal
    with pytest.raises(ValueError):
        ImpairmentConfig(reference_drift_phase_std_deg=-1.0).validate()
    with pytest.raises(ValueError):
        ImpairmentConfig(switch_leakage_db=3.0).validate()
    with pytest.raises(ValueError):
        ImpairmentConfig(mutual_coupling_db=3.0).validate()


def test_cli_impairments_writes_reports(tmp_path: Path) -> None:
    output = tmp_path / "impairments"
    assert main(["impairments", "--quick", "--output", str(output)]) == 0
    for name in (
        "impairments.json",
        "impairment_reference_summary.json",
        "impairment_runs.csv",
        "impairment_report.md",
    ):
        assert (output / name).stat().st_size > 0
    payload = json.loads(
        (output / "impairment_reference_summary.json").read_text(encoding="utf-8")
    )
    assert payload["evidence_label"] == "SIMULATED"
    assert payload["hardware_measured"] is False
    assert "records" not in payload
    assert payload["summary"]
