#!/usr/bin/env bash
# A-IL12 study: reproduce every output in out/ inside the pinned image (no GPU needed).
# Usage (from the repository root):  bash hardware/h2/design/ail12/run_all.sh [--quick]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
IMG="${OPENRU_IMAGE_REF:-openru-x6-sim:0.1.0}"
D=hardware/h2/design/ail12
run() { docker run --rm --name "ail12-$$-$RANDOM" -u "$(id -u):$(id -g)" -e MPLCONFIGDIR=/tmp -e PYTHONDONTWRITEBYTECODE=1 \
        -v "$ROOT":/workspace -w /workspace "$IMG" "$@" </dev/null; }
run python -I "$D/calc.py" > /dev/null
run python -I "$D/run_sim.py" "$@"
run python -I -m pytest -q -p no:cacheprovider "$D/test_ail12.py"
