"""Small shared helpers for the P1 workstreams."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from ..phy import nr_grid_audit


def write_csv(path: Path, rows: list[dict[str, Any]], fields: Iterable[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    names = list(fields or rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=names, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def resource_dict(radio: Any) -> dict[str, Any]:
    c = radio.cell
    return {
        "mode": c.resource_mode,
        "n_prb": c.n_prb,
        "n_rb_total": c.n_prb,
        "symbols_per_slot": c.symbols_per_slot,
        "dl_symbols_per_slot": c.dl_symbols_per_slot,
        "tdd_dl_fraction": c.tdd_dl_fraction,
        "control_overhead_fraction": c.control_overhead_fraction,
        "dmrs_overhead_fraction": c.dmrs_overhead_fraction,
        "ssb_overhead_fraction": c.ssb_overhead_fraction,
    }


def grid_audit(radio: Any) -> dict[str, Any]:
    return nr_grid_audit(radio.cell, resource_dict(radio))


def pct(values: Iterable[float], q: float) -> float:
    x = np.asarray(list(values), dtype=float)
    x = x[np.isfinite(x)]
    return float(np.percentile(x, q)) if x.size else float("nan")
