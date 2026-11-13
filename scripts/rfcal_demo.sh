#!/usr/bin/env bash
set -euo pipefail

PYTHON="${PYTHON:-python3}"
OUT="${1:-results/rfcal_demo}"

"${PYTHON}" -m openru_x6.rfcal topology --output "${OUT}/topology.json"
"${PYTHON}" -m openru_x6.rfcal simulate --seed 0 --captures 4 --samples 64 \
  --output "${OUT}/measurements.json"
"${PYTHON}" -m openru_x6.rfcal calibrate --measurements "${OUT}/measurements.json" \
  --output "${OUT}/calibration"
"${PYTHON}" -m openru_x6.rfcal codebook --output "${OUT}/codebook.json"
"${PYTHON}" -m openru_x6.rfcal audit --output "${OUT}/observability_audit.json"
"${PYTHON}" -m openru_x6.rfcal validate --quick --output "${OUT}/validation"

printf 'RF calibration demo outputs: %s\n' "${OUT}"
