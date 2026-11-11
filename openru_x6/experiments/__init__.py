"""Experiment registry."""
from __future__ import annotations

from . import (e00, e01, e02, e03, e04, e05, e06, e07, e08, e09, e10,
               integration)

EXPERIMENTS = [
    ("E00", e00), ("E01", e01), ("E02", e02), ("E03", e03), ("E04", e04),
    ("E05", e05), ("E06", e06), ("E07", e07), ("E08", e08), ("E09", e09),
    ("E10", e10), ("INTEGRATION", integration),
]

REQUIRED_FULL = [k for k, _ in EXPERIMENTS]
REQUIRED_SMOKE = ["E00", "E01", "E02", "E05", "E10", "INTEGRATION"]
