#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p results
status=0

echo "== build =="
docker compose build 2>&1 | tee results/build.log
build_rc=${PIPESTATUS[0]}
if [[ $build_rc -ne 0 ]]; then status=1; fi

docker image inspect openru-x6-sim:0.1.0 --format '{{.Id}}' > results/image_id.txt 2>/dev/null || true

echo "== GPU verification =="
bash scripts/verify_gpu.sh || status=1

echo "== unit/property/integration tests =="
docker compose run --rm --no-deps sim python -m pytest \
  --junitxml=results/tests.xml \
  --cov=openru_x6 --cov-report=term-missing \
  --cov-report=xml:results/coverage.xml 2>&1 | tee results/pytest.log
test_rc=${PIPESTATUS[0]}
if [[ $test_rc -ne 0 ]]; then status=1; fi

echo "== smoke suite =="
docker compose run --rm --no-deps sim python -m openru_x6.cli run-suite \
  --suite smoke --out results/smoke 2>&1 | tee results/smoke.log
smoke_rc=${PIPESTATUS[0]}
if [[ $smoke_rc -ne 0 ]]; then status=1; fi

echo "== full suite =="
docker compose run --rm --no-deps sim python -m openru_x6.cli run-suite \
  --suite full --out results/full 2>&1 | tee results/full.log
full_rc=${PIPESTATUS[0]}
if [[ $full_rc -ne 0 ]]; then status=1; fi

echo "== summary =="
python3 - <<'PY' || true
import json
from pathlib import Path
for name in ("smoke", "full"):
    p = Path("results") / name / "summary.json"
    if p.exists():
        d = json.loads(p.read_text())
        print(name, d["overall"], d.get("failed_required"), len(d.get("experiments", [])))
PY
exit $status
