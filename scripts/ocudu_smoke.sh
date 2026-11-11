#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p results/ocudu
docker compose run --rm --no-deps sim \
  python -m openru_x6.cli run-suite --suite smoke --out results/ocudu --only E10
