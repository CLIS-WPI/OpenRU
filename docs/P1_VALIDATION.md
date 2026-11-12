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

Run: `python -m openru_x6.cli run-suite --suite long_horizon --out results/long_horizon`

Status: **5/5 PASS**; 9,455 metric rows; 906.0 s; config digest
`d432664706af1f75`. Evidence summary: 9,454 `SIMULATED`, 1 `PHY_VALIDATED`,
0 `OCUDU_TESTED`, 0 `HARDWARE_MEASURED`.

| Workstream | Main finding |
|---|---|
| P1-A | Corrected paired result: 32-chain mean 503.54 Mbps; 64-chain 525.67 Mbps; +0.187 dB. Energy per bit rose from 700.6 to 875.1 nJ/bit. Paired goodput CIs were positive in both pivotal conditions. |
| P1-B | 98.28 MHz, 273-PRB grid audited; 0.492 resource factor; delivered/capacity 0.374. Sionna BLER was 1.0 at 0-4 dB, 0.5625 at 6 dB and 0.0 at 8 dB; the same-SE abstraction gave 0.592 at 6 dB and 0.077 at 8 dB, so it is conservative at high SNR in this small batch. |
| P1-C | Corrected Jones mean 590.29 Mbps versus 675.66 Mbps simple reference; XPD 10/20/30 dB changed goodput only slightly across three seeds. This is a sensitivity result, not calibrated polarization evidence. |
| P1-D | 48 total runs, of which **24 were QoS-constrained**; **0/24 were feasible**. Mean constrained deadline-miss fraction 0.311 (range 0.114-0.463), mean P99 173 slots (range 89-264), mean service interruption 18 slots, mean energy 41.18 J. All 48 injected faults were detected and recovered through authorized commands. |
| P1-E | Physical-fault recall 1.0 and localization 1.0 on 56 injected cases; sensor-degraded recall 0.744 on 336 cases. Healthy cases with sensor faults produced **28/48 false alarms (58.3%)**. The 105,000/hour value is an arithmetic extrapolation from short simulated cases, not a measured operational rate. |

The P1-D feasibility failure and P1-E false-alarm rate are negative findings.
They mean the current scheduler/policy and detector are not ready for a
deployment claim. The 20,000-slot profile is one run, not a seed ensemble. See
`docs/P1_FINAL_DECISION.md` for the resulting software, architecture and PCB
readiness decisions.


## Container and regression checks

- Fresh `docker compose` smoke: 6/6 PASS, 2,681 rows, 33.1 s.
- Fresh `docker compose` full: 12/12 PASS, 99,041 rows, 596.6 s. Deterministic
  metrics match the Rev10 baseline; only timing/stochastic rows and the config
  digest changed.
- All fresh P1 results came from the pinned Sionna 2.2.0/Torch container on GPU 1.
  P1-B used `sionna.phy(torch)` and passed.
- Regression suite: **52 passed** in the pinned container; 51 non-property tests
  pass locally. The property test module requires `hypothesis`, which is not
  installed in the local environment.
