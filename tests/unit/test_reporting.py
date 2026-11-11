import json
from pathlib import Path

import pandas as pd

from openru_x6.metrics import MetricsStore, ExperimentResult
from openru_x6.reporting import write_reports


def test_reporting_writes_standalone_markdown_html_and_figures(tmp_path):
    store = MetricsStore()
    for seed in (100, 101):
        for chains in (8, 64):
            store.add("E01", f"chains{chains}_ue128", seed, "pf",
                      "sum_goodput_mbps", 1000.0 * chains / 8, "Mbps")
            store.add("E01", f"chains{chains}_ue128", seed, "pf",
                      "jain_fairness", 0.5, "", "SIMULATED")
        store.add("E02", "load0.05", seed, "predictive",
                  "mean_power_w", 300.0, "W")
        store.add("E02", "load0.05", seed, "predictive",
                  "energy_saving_pct_vs_static", 12.0, "%")
    store.save(tmp_path)
    summary = {
        "suite": "smoke", "overall": "PASS", "config_digest": "test",
        "runtime_s": 1.0, "n_metric_rows": len(store.rows),
        "started_utc": "2026-01-01T00:00:00Z", "finished_utc": "2026-01-01T00:00:01Z",
        "experiments": [ExperimentResult("E01", "MIMO", "PASS").as_dict(),
                        ExperimentResult("E02", "Energy", "PASS").as_dict()],
        "mandatory": {}, "failed_required": [],
    }
    (tmp_path / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (tmp_path / "environment.json").write_text(json.dumps({"gpu_selected": {"name": "test"}}),
                                               encoding="utf-8")
    write_reports(tmp_path, summary, store)
    assert (tmp_path / "report.md").exists()
    assert (tmp_path / "report.html").exists()
    assert (tmp_path / "assumptions.yaml").exists()
    assert (tmp_path / "manifest.json").exists()
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert "data:image/png;base64," in html
    assert "HARDWARE_MEASURED" in html or "hardware" in html.lower()
    assert any(p.suffix == ".png" for p in tmp_path.iterdir())
