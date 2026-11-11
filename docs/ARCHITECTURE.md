# Architecture

OpenRU-X6 is a behavioral digital twin of a proposed 64T64R hybrid massive-MIMO
radio with 256 feed ports and 16 RF tiles. The implementation is a Python package
driven by YAML configuration; the public entry point is `openru_x6.cli`.

## Data path

1. `channel.py` generates geometry-consistent user channels from path loss,
   shadowing, blockage, mobility and small-scale fading.
2. `beamforming.py` selects analog beams per RF chain and computes MF, ZF or RZF
   digital precoding with per-chain power limits.
3. `phy.py` maps effective SINR to MCS/BLER and goodput; Sionna PHY/RT checks are
   run separately in E00 as `PHY_VALIDATED` corroboration.
4. `scheduler.py` provides PF, RR and max-throughput scheduling.
5. `traffic.py` supplies backlog/arrival traces with deadline-cohort QoS
   accounting; `engine.py` advances slots, accounts energy, applies faults and
   records metrics.
6. `energy.py` implements FULL_64, BALANCED_32, ECO_16, COVERAGE_8 and SLEEP_0
   states with dwell, hysteresis and wake-up delays.
7. `diagnostics.py` calibrates a statistical telemetry detector and proposes
   recovery actions; normal recovery executes through `control.py`. `faults.py`
   injects PA, VSWR, phase, tile, fan, thermal, PTP, supply and receiver faults.
8. `safety.py` independently vetoes unsafe commands and owns the emergency path;
   `control.py` validates, schedules, applies and verifies commands with an
   HMAC-chained audit log.
9. `isac.py`, `ris.py` and `fronthaul.py` model sensing, RIS and transport
   degradation. These are model outputs, not hardware measurements.
10. `metrics.py` and `reporting.py` persist per-seed rows and generate the
    Markdown/HTML report and figures.

## Execution

`openru_x6.cli run-suite --suite smoke|full --out DIR` runs experiments in order,
writes per-experiment JSON, `metrics.csv`, `metrics.parquet`, `summary.json`,
`environment.json`, and reports. `scripts/run_all.sh` builds the image, verifies
the GPU, runs tests, then executes both suites and returns nonzero on any
mandatory failure.

## Isolation and safety boundaries

- The simulation container is non-root (`ubuntu`, UID/GID 1000).
- GPU 1 is pinned through Compose; the container sees it as `cuda:0`.
- The Docker socket is mounted only so E10 can launch the pinned OCUDU image.
  That socket is powerful; do not expose this container to untrusted users.
- E10 uses `ru_dummy` + `test_mode`. It does **not** test Open Fronthaul
  interoperability or RF hardware.
