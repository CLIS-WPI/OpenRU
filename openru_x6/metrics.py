"""Statistical summaries, paired confidence intervals and metric persistence."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


def bootstrap_ci(values: Iterable[float], n_boot: int = 5000, level: float = 0.95,
                 rng: np.random.Generator | None = None) -> tuple[float, float, float]:
    x = np.asarray(list(values), dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return float("nan"), float("nan"), float("nan")
    rng = rng or np.random.default_rng(0)
    if x.size == 1:
        return float(x[0]), float(x[0]), float(x[0])
    idx = rng.integers(0, x.size, size=(n_boot, x.size))
    means = x[idx].mean(axis=1)
    lo = float(np.quantile(means, (1 - level) / 2))
    hi = float(np.quantile(means, 1 - (1 - level) / 2))
    return float(x.mean()), lo, hi


def paired_delta_ci(a: Iterable[float], b: Iterable[float], n_boot: int = 5000) -> dict[str, float]:
    """Bootstrap CI of mean(a-b) over paired seeds. Positive means a>b."""
    a = np.asarray(list(a), dtype=float)
    b = np.asarray(list(b), dtype=float)
    n = min(a.size, b.size)
    d = a[:n] - b[:n]
    d = d[np.isfinite(d)]
    if d.size == 0:
        return {"mean_delta": float("nan"), "ci_low": float("nan"), "ci_high": float("nan"), "n": 0}
    mean, lo, hi = bootstrap_ci(d, n_boot=n_boot)
    return {"mean_delta": mean, "ci_low": lo, "ci_high": hi, "n": int(d.size)}


def jain_fairness(rates: Iterable[float]) -> float:
    x = np.asarray(list(rates), dtype=float)
    x = x[x >= 0]
    if x.size == 0 or np.sum(x) == 0:
        return 0.0
    return float(np.sum(x) ** 2 / (x.size * np.sum(x ** 2)))


def percentile(values: Iterable[float], q: float) -> float:
    x = np.asarray(list(values), dtype=float)
    return float(np.percentile(x, q)) if x.size else float("nan")


@dataclass
class MetricRow:
    experiment: str
    scenario: str
    seed: int
    policy: str
    metric: str
    value: float
    unit: str = ""
    evidence_class: str = "SIMULATED"
    config_digest: str = ""


class MetricsStore:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def add(self, experiment: str, scenario: str, seed: int, policy: str, metric: str,
            value: float, unit: str = "", evidence_class: str = "SIMULATED",
            config_digest: str = "") -> None:
        try:
            v = float(value)
        except (TypeError, ValueError):
            return
        self.rows.append({
            "experiment": experiment, "scenario": scenario, "seed": int(seed),
            "policy": policy, "metric": metric, "value": v, "unit": unit,
            "evidence_class": evidence_class, "config_digest": config_digest,
        })

    def extend(self, rows: list[dict[str, Any]]) -> None:
        self.rows.extend(rows)

    def dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows)

    def save(self, out_dir: Path) -> tuple[Path, Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        df = self.dataframe()
        csv = out_dir / "metrics.csv"
        pq = out_dir / "metrics.parquet"
        df.to_csv(csv, index=False)
        try:
            df.to_parquet(pq, index=False)
        except Exception as exc:  # pragma: no cover - depends on pyarrow
            (out_dir / "metrics_parquet_error.txt").write_text(str(exc), encoding="utf-8")
        return csv, pq


@dataclass
class ExperimentResult:
    id: str
    title: str
    status: str = "NOT_RUN"
    reason: str = ""
    checks: dict[str, bool] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    runtime_s: float = 0.0
    evidence_class: str = "SIMULATED"
    artifacts: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "title": self.title, "status": self.status, "reason": self.reason,
            "checks": self.checks, "metrics": self.metrics, "runtime_s": self.runtime_s,
            "evidence_class": self.evidence_class, "artifacts": self.artifacts,
        }


def aggregate(df: pd.DataFrame, experiment: str, metric: str, by: list[str] | None = None) -> dict[str, Any]:
    sub = df[(df.experiment == experiment) & (df.metric == metric)]
    out: dict[str, Any] = {}
    if sub.empty:
        return out
    by = by or ["policy"]
    for key, g in sub.groupby(by):
        mean, lo, hi = bootstrap_ci(g.value)
        k = "|".join(str(x) for x in (key if isinstance(key, tuple) else (key,)))
        out[k] = {"mean": mean, "ci_low": lo, "ci_high": hi, "n": int(len(g))}
    return out


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")
