# OpenRU-X6 GPU Simulation Lab

OpenRU-X6 is a reproducible, GPU-accelerated digital-twin laboratory for the proposed
OpenRU-X6 64T64R hybrid massive-MIMO research radio: 64 RF chains, 256 antenna
feed ports and 16 RF tiles. It is a system-level behavioural simulator for
architecture trade-offs, control-plane safety and experiment reproducibility.

It is **not** a PCB, EM, circuit or thermal sign-off tool. It does not establish
physical RF performance, O-RAN Open Fronthaul interoperability or hardware
readiness. Every result carries an explicit evidence class.

## Research scope

The lab supports:

- 8/16/32/64-chain and 16-256/500-UE comparisons with matched seeds.
- 3GPP-inspired NR-grid link adaptation, per-user scheduling, CSI aging,
  mobility, blockage and dual-polarized feed abstractions.
- 100 MHz channel modelling, analog beamforming, MF/ZF/RZF precoding and
  per-chain power limits.
- Energy-state, wake-up, thermal and sleep-policy experiments.
- Fault injection, telemetry diagnosis, authorized recovery, safety vetoes and
  command audit trails.
- ISAC, RIS, fronthaul and GPU-scaling experiments.
- Real OCUDU DU/PHY test-mode scheduling evidence via `ru_dummy`; Open Fronthaul
  remains `NOT_TESTED`.

## Repository layout

```text
.
├── compose.yaml                 # pinned GPU/Docker runtime
├── Dockerfile                   # simulation image
├── configs/                     # radio, energy, security and suite definitions
│   └── scenarios/               # per-experiment parameters
├── openru_x6/                   # simulator package
│   ├── experiments/             # E00-E10 and INTEGRATION drivers
│   └── ocudu/                   # OCUDU helper package
├── tests/                       # unit, property, integration and scenario tests
├── scripts/                     # GPU verification and full local validation
├── docs/                        # models, assumptions, validation and limitations
├── reports/                     # report templates
├── REV10_VERIFICATION.md        # latest independent-audit response
└── results/                     # generated locally; not committed
```

## H100 environment

The verified reference environment is:

- NVIDIA H100 NVL, 95 GB, driver `580.126.09`, CUDA driver API `13.0`.
- PyTorch `2.9.1+cu128`, Sionna `2.2.0`.
- Python `3.12`, Ubuntu-based `sionna:2.2.0` base image.
- Physical GPU 1 is pinned by default through Compose. Inside the container the
  selected device is exposed as `cuda:0`.

Override the device when needed:

```bash
OPENRU_GPU_DEVICE_ID=0 docker compose run --rm sim python -m openru_x6.cli --help
```

The Compose file does not preempt other workloads. It mounts the host Docker
socket so E10 can launch the pinned OCUDU nightly image; that socket provides
powerful host-level Docker access and should only be used in a trusted lab
environment.

## Quick start

Build and run the tests:

```bash
docker compose build
docker compose run --rm sim python -m pytest -q
```

Run a suite:

```bash
docker compose run --rm sim python -m openru_x6.cli run-suite \
  --suite smoke --out results/smoke

docker compose run --rm sim python -m openru_x6.cli run-suite \
  --suite full --out results/full

docker compose run --rm sim python -m openru_x6.cli run-suite \
  --suite long_horizon --out results/long_horizon
```

Run the complete local pipeline (build, GPU check, tests, coverage, smoke and
full suites; nonzero exit on mandatory failure):

```bash
bash scripts/run_all.sh
```

Useful Make targets:

```bash
make build
make test
make smoke
make full
make all
```

## Experiment map

| ID | Purpose |
|---|---|
| E00 | GPU, array geometry, path loss, Sionna PHY/RT and engine sanity |
| E01 | 8/16/32/64-chain, UE-count, precoder and scheduler comparisons |
| E02 | Energy-state policy under load, including sleep/wake and QoS costs |
| E03 | Mobility, blockage, CSI delay, phase error and quantisation |
| E04 | Fault injection, telemetry diagnosis and authorized recovery |
| E05 | Role-policy command validation and independent safety path |
| E06 | ISAC communication/sensing trade-off |
| E07 | RIS practical/oracle comparison |
| E08 | Fronthaul loss, jitter, compression and sync loss |
| E09 | GPU sensitivity and abstract bandwidth scaling |
| E10 | OCUDU DU/PHY `ru_dummy` test-mode evidence |
| INTEGRATION | Fault, command, safety, energy and service-recovery lifecycle |

## Evidence classes

Every metric is labelled:

| Class | Meaning |
|---|---|
| `SIMULATED` | Abstract model output from this repository |
| `PHY_VALIDATED` | Selected Sionna PHY/RT corroboration |
| `OCUDU_TESTED` | Real OCUDU process reached gNB start and test-mode scheduling |
| `HARDWARE_MEASURED` | Never asserted by this repository |

`summary.json` is authoritative for PASS/FAIL/BLOCKED/NOT_RUN status.

## Latest verified results

Published Rev10 baseline (pre-P1), local H100 run, 2026-11-11:

| Item | Result |
|---|---|
| Tests | **40 passed**, **54%** coverage |
| Smoke suite | 12/12 PASS, 4,372 metric rows, 40.6 s |
| Full suite | 12/12 PASS, 99,041 metric rows, 590.6 s |
| Full config digest | `1d89961ada5a68e3` |
| Smoke config digest | `e00ba9df0f1b575a` |
| Image | `sha256:927fd2d6cc07b27cce32c6e435db285c8f57eeb6675c5a584c275900afb5a4dd` |

P1 branch regression, fresh container run, 2026-11-11:

| Item | Result |
|---|---|
| Tests | **47 passed** in the pinned container; 46 non-property tests passed locally |
| Smoke suite | 6/6 PASS, 2,681 metric rows, 34.2 s, digest `cf44501c4f9daa81` |
| Full suite | 12/12 PASS, 99,041 metric rows, 592.5 s, digest `2200ad495a88f95c` |
| P1 reduced suite | 5/5 PASS, 9,454 metric rows, 1,221.8 s, digest `d432664706af1f75` |
| Image | unchanged `sha256:927fd2d6cc07b27cce32c6e435db285c8f57eeb6675c5a584c275900afb5a4dd` |
| E04 full | PASS; 1,024 actions attempted and verified, 0 rolled back/failed/unrouted |
| INTEGRATION full | PASS; 20/20 seeds detected and isolated; audit valid |

All deterministic smoke/full metrics are unchanged from the Rev10 baseline. Only
GPU timing, stochastic Sionna BLER and the OCUDU test-mode PDSCH count vary
between runs. The config digest changed because the new default
`simple` polarization configuration is now part of the serialized radio config.

Important scientific result: the low-load predictive energy policy saved
**17.43%** energy, but reduced goodput by **1.37 Mbps**, increased the
deadline-expired fraction by **0.0253**, and produced **P99 completed latency of
105 slots**. It is **not QoS-neutral** and is not presented as a QoS-safe default.

At 128 UEs the modeled 64-chain mode delivered 1,154.98 Mbps at 455.90 W versus
872.71 Mbps at 344.30 W for 32 chains, with 15.7 mean useful layers in both
cases. Goodput and modeled power rose by approximately the same proportion; this
is **not** an energy-efficiency or hardware-cost justification for 64 chains.

P1 results are deliberately mixed: paired 500-slot runs show 64 chains raising
mean goodput from 444.57 to 473.78 Mbps but also raising energy per bit from
804.7 to 980.1 nJ/bit. All 48 constrained P1-D runs remained infeasible under
the tested QoS thresholds, and P1-E's healthy sensor-fault cases produced a
high false-alarm rate. These are reported as negative findings, not smoothed
away. See `docs/P1_VALIDATION.md` for details. P1 is a separate, reduced local
suite; it does not replace the published Rev10 full-suite baseline.

## Reproducibility

- Suite seeds, UE counts, fault lists and horizons live in `configs/suites.yaml`.
- Per-experiment parameters live in `configs/scenarios/`.
- Calibration and evaluation telemetry seeds are separated.
- Generated outputs include `environment.json`, `metrics.csv`, `metrics.parquet`,
  per-experiment JSON, `summary.json`, `report.md`, `report.html`,
  `assumptions.yaml`, `manifest.json` and PNG/SVG figures.
- Generated results are intentionally excluded from Git. They can be reproduced
  locally with the commands above.

## Known limitations and open issues

- **E01 horizon:** the published full suite still runs only 3 slots (1.5 ms).
  P1 adds a disclosed reduced long-horizon investigation, but does not establish
  deployment-scale long-horizon scheduling, fairness or mobility claims.
- **32T32R vs 64T64R:** no decisive energy-efficiency advantage has been shown.
- **E02/P1-D QoS:** P1 adds a closed-loop constraint sweep, but the published
  predictive policy is not QoS-neutral. Deployment Pareto claims still require
  broader traffic traces and scheduler-fairness validation.
- **INTEGRATION:** it exercises a scripted energy transition plus a fault, not a
  fully coupled adaptive energy + fault + wake + traffic control loop.
- **Diagnostics:** P1 adds held-out unknown-fault and missing/biased/frozen/
  stale/quantized/inconsistent sensor cases. These are simulation-only; recall
  and false-alarm figures are not physical diagnostic accuracy.
- **Dual polarization:** P1 adds a configurable 2x2 Jones/XPD/XPR model, but it is
  not calibrated to an antenna chamber, PCB or measured cross-polar pattern.
- **NR resource semantics:** P1 audits the 273-PRB/98.28-MHz grid and the
  separate 0.88 coded-link factor. The audit is not a 3GPP conformance test.
- **Security:** E05 is role-policy simulation. There is no mTLS credential proof,
  persistent anti-replay store, secure element or board-level command attestation.
- **OCUDU/OFH:** E10 is DU/PHY `ru_dummy` + `test_mode` only. `ru_emu` and O-RAN
  Open Fronthaul interoperability are `BLOCKED`/`NOT_TESTED`.
- **Hardware:** no PCB EM/SI/PI/thermal sign-off, 8.4 GHz front-end measurement or
  calibrated real dual-polarized array exists. PCB fabrication is **NO-GO**.

## Testing policy

All testing is local on the H100 server. This repository intentionally contains
no GitHub Actions, CI/CD workflows or cloud test configuration.

## License

Apache-2.0. See `LICENSE`.
