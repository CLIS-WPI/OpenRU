"""Command line entry point for the OpenRU-X6 simulation lab."""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
import traceback
from pathlib import Path

from .config import config_digest, load_energy, load_radio, load_security
from .experiments import EXPERIMENTS, REQUIRED_FULL, REQUIRED_SMOKE
from .experiments.common import load_suite
from .gpu import environment_report
from .metrics import ExperimentResult, MetricsStore, write_json


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def cmd_run_suite(args: argparse.Namespace) -> int:
    suite_name = args.suite
    suite = load_suite(suite_name)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    radio = load_radio()
    energy = load_energy()
    security = load_security()
    store = MetricsStore()
    digest = config_digest(radio, energy, security, suite)
    t_start = time.time()

    env = environment_report(Path.cwd())
    env["suite"] = suite_name
    env["config_digest"] = digest
    env["started_utc"] = _now()
    write_json(out / "environment.json", env)

    selected = [x.strip() for x in (args.only or "").split(",") if x.strip()]
    results: list[ExperimentResult] = []
    print(f"[openru] suite={suite_name} out={out} config={digest} python={platform.python_version()}")
    for exp_id, module in EXPERIMENTS:
        if selected and exp_id not in selected:
            continue
        print(f"[openru] running {exp_id} ...", flush=True)
        t0 = time.time()
        try:
            res = module.run(radio, energy, security, suite, out, store)
            if res is None:  # pragma: no cover
                res = ExperimentResult(id=exp_id, title=exp_id, status="ERROR",
                                       reason="experiment returned no result")
        except Exception as exc:  # noqa: BLE001
            tb = traceback.format_exc()
            (out / f"{exp_id.lower()}_error.txt").write_text(tb, encoding="utf-8")
            res = ExperimentResult(id=exp_id, title=exp_id, status="ERROR",
                                   reason=f"{type(exc).__name__}: {exc}",
                                   runtime_s=time.time() - t0)
            print(tb, file=sys.stderr)
        results.append(res)
        write_json(out / f"{exp_id.lower()}_result.json", res.as_dict())
        print(f"[openru] {exp_id}: {res.status} ({res.runtime_s:.1f}s)"
              f"{' - ' + res.reason if res.reason else ''}", flush=True)

    csv, _pq = store.save(out)
    required = REQUIRED_FULL if suite_name == "full" else REQUIRED_SMOKE
    by_id = {r.id: r for r in results}
    mandatory = {k: (by_id.get(k).status if by_id.get(k) else "NOT_RUN") for k in required}
    failed_required = [k for k, v in mandatory.items() if v != "PASS"]
    summary = {
        "suite": suite_name,
        "started_utc": env["started_utc"],
        "finished_utc": _now(),
        "runtime_s": time.time() - t_start,
        "config_digest": digest,
        "metrics_csv": str(csv),
        "n_metric_rows": len(store.rows),
        "experiments": [r.as_dict() for r in results],
        "mandatory": mandatory,
        "failed_required": failed_required,
        "overall": "PASS" if not failed_required else "FAIL",
        "evidence_summary": {
            "SIMULATED": sum(1 for r in store.rows if r["evidence_class"] == "SIMULATED"),
            "PHY_VALIDATED": sum(1 for r in store.rows if r["evidence_class"] == "PHY_VALIDATED"),
            "OCUDU_TESTED": sum(1 for r in store.rows if r["evidence_class"] == "OCUDU_TESTED"),
            "HARDWARE_MEASURED": 0,
        },
        "notes": [
            "No HARDWARE_MEASURED evidence is produced by this lab.",
            "OCUDU test-mode/DU evidence is not Open Fronthaul interoperability.",
            "Timestamps at 4 ns resolution are not physical RF switching times.",
        ],
    }
    write_json(out / "summary.json", summary)

    try:
        from .reporting import write_reports
        write_reports(out, summary, store)
    except Exception as exc:  # noqa: BLE001
        (out / "reporting_error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        print(f"[openru] reporting failed: {type(exc).__name__}: {exc}", file=sys.stderr)

    print(f"[openru] {summary['overall']}: {len(results)} experiments, "
          f"{len(store.rows)} metric rows, {summary['runtime_s']:.1f}s")
    if failed_required:
        print(f"[openru] required not passing: {', '.join(failed_required)}", file=sys.stderr)
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="openru_x6", description="OpenRU-X6 simulation lab")
    sub = p.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run-suite", help="run an experiment suite")
    r.add_argument("--suite", choices=["smoke", "full"], required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--only", default="", help="comma-separated experiment ids")
    r.set_defaults(func=cmd_run_suite)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
