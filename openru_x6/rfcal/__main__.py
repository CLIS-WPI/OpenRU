"""Module entry point for ``python -m openru_x6.rfcal``."""

from __future__ import annotations

import sys

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
