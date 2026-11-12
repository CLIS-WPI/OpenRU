"""Experiment registry and suite membership.

``full`` and ``smoke`` remain the published Rev10 baseline.  P1 experiments
are only run by the separate ``long_horizon`` suite so the historical full
suite is not silently redefined.
"""
from __future__ import annotations

from . import (e00, e01, e02, e03, e04, e05, e06, e07, e08, e09, e10,
               integration, p1a, p1b, p1c, p1d, p1e)

EXPERIMENTS = [
    ("E00", e00), ("E01", e01), ("E02", e02), ("E03", e03), ("E04", e04),
    ("E05", e05), ("E06", e06), ("E07", e07), ("E08", e08), ("E09", e09),
    ("E10", e10), ("INTEGRATION", integration),
    ("P1A", p1a), ("P1B", p1b), ("P1C", p1c), ("P1D", p1d), ("P1E", p1e),
]

_BASELINE = ["E00", "E01", "E02", "E03", "E04", "E05", "E06", "E07",
             "E08", "E09", "E10", "INTEGRATION"]
REQUIRED_FULL = list(_BASELINE)
REQUIRED_SMOKE = ["E00", "E01", "E02", "E05", "E10", "INTEGRATION"]
REQUIRED_LONG_HORIZON = ["P1A", "P1B", "P1C", "P1D", "P1E"]

SUITE_EXPERIMENTS = {
    "smoke": REQUIRED_SMOKE,
    "full": REQUIRED_FULL,
    "long_horizon": REQUIRED_LONG_HORIZON,
}
SUITE_REQUIRED = {
    "smoke": REQUIRED_SMOKE,
    "full": REQUIRED_FULL,
    "long_horizon": REQUIRED_LONG_HORIZON,
}


def experiments_for_suite(name: str):
    ids = SUITE_EXPERIMENTS.get(name, REQUIRED_FULL)
    by_id = dict(EXPERIMENTS)
    return [(eid, by_id[eid]) for eid in ids if eid in by_id]
