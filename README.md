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

Rev10 local H100 run, 2026-11-11:

| Item | Result |
|---|---|
| Tests | **40 passed**, **54%** coverage |
| Smoke suite | 12/12 PASS, 4,372 metric rows, 40.6 s |
| Full suite | 12/12 PASS, 99,041 metric rows, 590.6 s |
| Full config digest | `1d89961ada5a68e3` |
| Smoke config digest | `e00ba9df0f1b575a` |
| Image | `sha256:927fd2d6cc07b27cce32c6e435db285c8f57eeb6675c5a584c275900afb5a4dd` |
| E04 full | 1,024 recovery actions attempted and verified; 0 rolled back, failed or unrouted |
| INTEGRATION full | 20/20 seeds detected and isolated; zero unauthorized/unsafe commands; audit valid |

Important scientific result: the low-load predictive energy policy saved
**17.43%** energy, but reduced goodput by **1.37 Mbps**, increased the
deadline-expired fraction by **0.0253**, and produced **P99 completed latency of
105 slots**. It is **not QoS-neutral** and is not presented as a QoS-safe default.

At 128 UEs the modeled 64-chain mode delivered 1,154.98 Mbps at 455.90 W versus
872.71 Mbps at 344.30 W for 32 chains, with 15.7 mean useful layers in both
cases. Goodput and modeled power rose by approximately the same proportion; this
is **not** an energy-efficiency or hardware-cost justification for 64 chains.

See `REV10_VERIFICATION.md` and `docs/VALIDATION.md` for the validation summary.

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

- **E01 horizon:** the full suite still runs only 3 slots (1.5 ms). Long-horizon
  scheduling, fairness, queueing and mobility claims are not established.
- **32T32R vs 64T64R:** no decisive energy-efficiency advantage has been shown.
- **E02 QoS:** the predictive energy policy is not QoS-constrained. A proper
  Pareto sweep over permitted deadline-miss/latency loss is still required.
- **INTEGRATION:** it exercises a scripted energy transition plus a fault, not a
  fully coupled adaptive energy + fault + wake + traffic control loop.
- **Diagnostics:** conspicuous injected faults are detected reliably, but
  unknown fault mechanisms, missing/biased/frozen sensors, sensor outages and
  domain shift remain untested. Recall 1.00 is not physical diagnostic accuracy.
- **Dual polarization:** the model does not yet implement calibrated XPD/XPR,
  polarization-dependent path responses or cross-polar scattering.
- **NR resource semantics:** TDD/symbol overhead factors and the separate 0.88
  efficiency factor still need auditing against a known physical-layer reference.
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
