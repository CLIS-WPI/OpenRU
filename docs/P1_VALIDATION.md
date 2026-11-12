# P1 scientific validation (local, reduced)

P1 is a separate suite (`long_horizon`) layered on the published Rev10 baseline.
It is not part of `smoke` or `full`, and it does not change the historical full
suite membership.

## What P1 exercises

- **P1-A:** paired 32-vs-64-chain comparisons over 20 seeds, with a separately
  timed 20,000-slot mechanism profile and bootstrap confidence intervals.
- **P1-B:** explicit 273-PRB NR grid accounting, zero-resource boundary tests,
  a coded-link boundary sweep and an optional real Sionna PHY cross-check.
- **P1-C:** optional 2x2 Jones polarimetric sweep over XPD/XPR; the legacy
  scalar path remains the default and is regression-tested.
- **P1-D:** quiet-to-burst closed-loop energy/fault run with injected PA gain loss,
  stale/biased telemetry, control-plane recovery and constraint accounting.
- **P1-E:** held-out fault families and sensor degradation cases
  (`missing`, `frozen`, `biased`, `stale`, `quantized`, `inconsistent`) with a
  calibration/validation/evaluation seed split.

## Reduced-design disclosure

The local P1 configuration is intentionally affordable rather than a
publication-scale matrix:

- P1-A screening uses 250 slots; pivotal comparisons use 500 slots and 20 paired
  seeds; the 20,000-slot profile is one 64-chain, 16-UE timing/mechanism run.
- P1-A therefore reports **paired 20-seed evidence at 500 slots**, not a
  20-seed × 20,000-slot matrix. The 20,000-slot result is not extrapolated to
  all seeds.
- P1-B uses a small Sionna coded-link batch. `PHY_VALIDATED` applies to the
  coded-link cross-check only, not RF or NR conformance.
- P1-C XPD/XPR values are configuration sweeps, not antenna-chamber data.
- P1-D/P1-E use short runs and behavioural telemetry; they are harness and
  sensitivity evidence, not field reliability.

## Evidence boundaries

No P1 result is `HARDWARE_MEASURED`. P1 does not establish Open Fronthaul
interoperability, PCB/RF/EM/thermal qualification, or a product reliability
figure. Ground-truth fault labels are used only for scoring and are never passed
to the detector.

## Reproduce locally

```bash
python -m pytest -q --ignore=tests/property   # property test needs hypothesis
python -m openru_x6.cli run-suite --suite long_horizon --out results/long_horizon
```

Inspect `summary.json`, `p1a_result.json` ... `p1e_result.json`,
`paired_comparisons.csv`, `nr_grid_audit.json`, `polarization_sensitivity.csv`,
`p1d_policy_results.csv`, `p1e_confusion.csv` and `hardware_choice_memo.md`.


## Latest local result

Run: `python -m openru_x6.cli run-suite --suite long_horizon --out results/p1_long`  
Status: **5/5 PASS**; 9,454 metric rows; 1,221.8 s; config digest
`d432664706af1f75`. Evidence summary: 9,453 `SIMULATED`, 1 `PHY_VALIDATED`,
0 `OCUDU_TESTED`, 0 `HARDWARE_MEASURED`.

| Workstream | Main finding |
|---|---|
| P1-A | 32-chain mean 444.57 Mbps; 64-chain 473.78 Mbps; +0.276 dB. Energy per bit rose from 804.7 to 980.1 nJ/bit. Paired goodput CIs were positive in both pivotal conditions. |
| P1-B | 98.28 MHz, 273-PRB grid audited; 0.492 resource factor; delivered/capacity 0.491. Sionna BLER was 1.0 at low SNR and 0.0 at high SNR in the modelled batch. |
| P1-C | Jones mean 479.49 Mbps versus 550.08 Mbps simple reference; XPD 10/20/30 dB changed goodput only slightly across three seeds. This is a sensitivity result, not calibrated polarization evidence. |
| P1-D | 48 runs, 48 detections, 678 control commands; constrained feasible rate **0.0**. Mean constrained deadline-miss fraction 0.315-0.382 and P99 191-227 slots under the tested thresholds. |
| P1-E | Physical-fault recall 1.0 and localization 1.0 on injected cases; sensor-degraded recall 0.744. Healthy cases with sensor faults produced 28/48 false alarms, or 105,000/hour in this harness. |

The P1-D feasibility failure and P1-E false-alarm rate are negative findings.
They mean the current scheduler/policy and detector are not ready for a
deployment claim. The 20,000-slot profile is one run, not a seed ensemble.


## Container and regression checks

- Fresh `docker compose` smoke: 6/6 PASS, 2,681 rows, 34.2 s.
- Fresh `docker compose` full: 12/12 PASS, 99,041 rows, 592.5 s. Deterministic
  metrics match the Rev10 baseline; only timing/stochastic rows and the config
  digest changed.
- E00 and P1-B were rerun in the pinned Sionna 2.2/Torch container. P1-B used
  `sionna.phy(torch)` and passed. The local P1-A/P1-C/P1-D/P1-E results used the
  local TensorFlow-backed Sionna 1.2.1 environment where relevant.
- Regression suite: **47 passed** in the pinned container; 46 non-property tests
  pass locally. The property test module requires `hypothesis`.
