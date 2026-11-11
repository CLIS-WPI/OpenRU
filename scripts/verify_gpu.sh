#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p results
docker compose run --rm --no-deps sim python - <<'PY' | tee results/gpu_verify.log
import json
import torch
from openru_x6.config import load_radio
from openru_x6.gpu import environment_report
rep = environment_report(__import__("pathlib").Path.cwd())
print(json.dumps({"torch": torch.__version__, "cuda_available": torch.cuda.is_available(),
                  "device_count": torch.cuda.device_count(),
                  "selected": rep.get("torch", {}).get("selected"),
                  "gpu_selected": rep.get("gpu_selected")}, indent=2))
assert torch.cuda.is_available(), "CUDA is not available inside the container"
assert torch.cuda.device_count() >= 1, "no visible CUDA device"
radio = load_radio()
assert radio.array.n_chains == 64 and radio.array.n_feeds == 256
PY
