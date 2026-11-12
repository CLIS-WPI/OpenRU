#!/usr/bin/env python3
"""Run the reproducible simulated RF calibration validation sweep."""

from __future__ import annotations

import sys

from openru_x6.rfcal.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["validate", *sys.argv[1:]]))
