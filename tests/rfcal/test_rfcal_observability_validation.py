from __future__ import annotations

import json
from pathlib import Path

from openru_x6.rfcal.observability_validation import (
    ObservabilityValidationConfig,
    run_observability_validation,
)
from openru_x6.rfcal.topology import load_topology


def _small_config() -> ObservabilityValidationConfig:
    return ObservabilityValidationConfig(
        seeds=(0,),
        snr_db_levels=(30.0,),
        mismatch_scales=(1.0,),
        angles=((0.0, 0.0),),
        n_captures=2,
        n_samples=16,
        fault_seeds=(0,),
        architectures=(
            "h2_available",
            "proposed_switched_feed_loopback",
            "ideal_16iq_nonrealizable",
        ),
        fault_architectures=("h2_available",),
    )


def test_observability_validation_separates_available_and_per_feed_phase() -> None:
    topology = load_topology()
    report = run_observability_validation(topology, _small_config())
    assert report.simulated
    assert report.audit["identifiability"]["feed_phase"] is False
    architectures = {row["architecture"] for row in report.base_case}
    assert architectures == {
        "h2_available",
        "proposed_switched_feed_loopback",
        "ideal_16iq_nonrealizable",
    }
    available = next(
        row
        for row in report.accuracy_by_snr
        if row["architecture"] == "h2_available"
    )
    switched = next(
        row
        for row in report.accuracy_by_snr
        if row["architecture"] == "proposed_switched_feed_loopback"
    )
    assert switched["calibration_phase_error_deg_mean"] < available[
        "calibration_phase_error_deg_mean"
    ]
    assert report.scalar_baseline_summary
    assert report.scalar_baseline_records
    assert all(
        row["detected_mean"] == 1.0 for row in report.fault_summary
    )


def test_observability_validation_json_without_records_and_markdown(
    tmp_path: Path,
) -> None:
    topology = load_topology()
    report = run_observability_validation(topology, _small_config())
    json_path = tmp_path / "observability.json"
    summary_path = tmp_path / "summary.json"
    markdown_path = tmp_path / "report.md"
    report.to_json(json_path, include_records=True)
    report.to_json(summary_path, include_records=False)
    report.to_markdown_file(markdown_path)

    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["simulated"]
    assert payload["evidence_label"] == "SIMULATED"
    assert payload["hardware_measured"] is False
    assert "records" not in payload
    assert payload["audit"]["conclusion"]
    assert json_path.stat().st_size > summary_path.stat().st_size
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "Observability-Aware RF Calibration Validation" in markdown
    assert "Scalar per-feed-IQ baseline" in markdown
    assert "not as an available H2 measurement path" in markdown
