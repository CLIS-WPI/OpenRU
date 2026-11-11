"""Shared helpers for the experiment drivers."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
import yaml

from ..config import (CONFIG_DIR, RadioConfig, ScenarioConfig, config_digest,
                      load_scenario)
from ..engine import RunResult, SimContext, SimulationEngine
from ..metrics import ExperimentResult, MetricsStore


def load_suite(name: str) -> dict[str, Any]:
    data = yaml.safe_load((CONFIG_DIR / "suites.yaml").read_text(encoding="utf-8"))
    if name not in data:
        raise KeyError(f"suite {name!r} not found in suites.yaml")
    return data[name]


def seeds_for(suite: dict[str, Any], exp: str | None = None) -> list[int]:
    base = int(suite.get("seed_base", 100))
    n = int(suite.get("seeds", 2))
    if exp is not None:
        cfg = suite.get(exp.lower(), {}) or {}
        n = int(cfg.get("seeds", n))
    return [base + i for i in range(n)]


def scenario(exp_id: str) -> ScenarioConfig:
    return load_scenario(CONFIG_DIR / "scenarios" / f"{exp_id}.yaml")


def params_for(exp_id: str, suite: dict[str, Any]) -> dict[str, Any]:
    sc = scenario(exp_id)
    out = dict(sc.params)
    out.update((suite.get(exp_id.lower(), {}) or {}))
    return out


def make_context(radio: RadioConfig, seed: int, n_users: int, n_slots: int,
                 speed_kmh: float = 3.0, channel_update_slots: int = 20,
                 trace=None, blocked_schedule=None, saturate: bool = False) -> SimContext:
    return SimContext.build(radio, seed, n_users, n_slots, speed_kmh=speed_kmh,
                            channel_update_slots=channel_update_slots, trace=trace,
                            blocked_schedule=blocked_schedule, saturate=saturate)


def run_engine(radio: RadioConfig, energy, security, ctx: SimContext, **kwargs: Any) -> RunResult:
    return SimulationEngine(radio, energy, security, ctx).run(**kwargs)


def record(result: RunResult, exp: str, scenario_name: str, seed: int, policy: str,
           store: MetricsStore, digest: str, extra: dict[str, float] | None = None) -> None:
    result.as_metrics(exp, scenario_name, seed, policy, store, digest)
    for k, v in (extra or {}).items():
        store.add(exp, scenario_name, seed, policy, k, float(v), "", "SIMULATED", digest)


def make_result(exp_id: str, title: str, t0: float, checks: dict[str, bool],
                metrics: dict[str, Any] | None = None, reason: str = "",
                evidence_class: str = "SIMULATED") -> ExperimentResult:
    checks = {k: bool(v) for k, v in checks.items()}
    failed = [k for k, v in checks.items() if not v]
    status = "PASS" if not failed else "FAIL"
    if reason and status == "PASS":
        status = "PASS"
    return ExperimentResult(id=exp_id, title=title, status=status,
                            reason=reason or ("" if not failed else "failed checks: " + ", ".join(failed)),
                            checks=checks, metrics=metrics or {}, runtime_s=time.time() - t0,
                            evidence_class=evidence_class)


def digest(*objects: Any) -> str:
    return config_digest(*objects)


def device_name() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


def metric_values(store: MetricsStore, exp: str, metric: str, **filters: Any) -> np.ndarray:
    vals = [r["value"] for r in store.rows
            if r["experiment"] == exp and r["metric"] == metric
            and all(r.get(k) == v for k, v in filters.items())]
    return np.asarray(vals, dtype=float)
