# Validation

## Evidence classes

| Class | Meaning |
|---|---|
| `SIMULATED` | Abstract model output from this repository. |
| `PHY_VALIDATED` | Sionna PHY/RT corroboration of a modeled quantity. |
| `OCUDU_TESTED` | Real OCUDU process reached gNB start and test-mode scheduling. |
| `HARDWARE_MEASURED` | Never asserted by this lab. |

## Checks performed by E00

- CUDA availability, finite GPU matmul, device name and visible GPU index.
- Feed/chain/tile mapping: 256 feeds, 64 chains, 4 feeds/chain, 16 tiles.
- Chain masks have exact counts and correct tile spread.
- Zero TX power produces zero PA DC consumption.
- Friis path loss and thermal noise are physically plausible.
- Beam steering gives positive gain versus a random direction.
- Sionna PHY runs at high/low SNR and Sionna RT produces a plausible path loss in
  the `floor_wall` scene.
- Engine smoke run is finite and non-negative.

## Checks performed by E10

- Docker CLI and pinned OCUDU image are present.
- The real `gnb` binary starts with `ru_dummy` and `test_mode`.
- PDSCH scheduling for test UE `rnti=0x44` is observed at debug level.
- PUSCH is scheduled; `crc=KO` is expected with the dummy RU and is not claimed
  as a decoding success.
- `ru_emu` is reported `BLOCKED` because the pinned image does not contain it.
- Open Fronthaul interoperability is `NOT_TESTED`.

## Rev08 P0 remediation checks

- P0-1: `analog_weights` uses physical chain indices; E01 still shows a monotonic
  8/16/32/64-chain trend and reduced-mask directions are validated.
- P0-2: `resource_multiplier` and `capacity_bps` are reported separately from
  delivered goodput using the configured NR grid.
- P0-3: blockage is applied once in the channel model; a regression test checks
  no double counting.
- P0-4: wake state has no RF service and transition energy; energy-policy load
  uses backlog/peak airtime; predictive horizon is configured.
- P0-5: thermal trip forces zero TX and latches protection; the engine records
  trip slots and emergency/reduce-power behavior.
- P0-6: `INTEGRATION` issues a positive energy command through the control
  plane, uses actual served bits, and applies QoS-aware recovery checks across
  full-suite seeds.
- P0-7: E05 is labeled role-policy validation; no fixed repository secret or
  cryptographic identity claim is made.

## Rev09 P0 remediation checks

- P0-A: deadline cohorts count expired-but-unserved bits and overflow drops.
  `qos_violation_fraction()` is the union of expired and dropped bits, and the
  conservation identity is checked with `arrived = served + dropped + queued`.
  The audit counterexample yields one expired bit-cohort with zero conservation
  error. E02 records expired/dropped fractions, P50/P95/P99 completed-service
  latency, and the predictive-vs-static QoS delta.
- P0-B: telemetry RNGs are per hardware instance, seeded from the run seed,
  healing mode and fault signature; calibration and evaluation seeds differ.
  Telemetry adds slow correlated drift, quantization and sensor-resolution floors.
  E04 reports recall/localization by fault class and false alarms on independent
  healthy seeds.
- P0-C: `SelfHealingController` is proposal-only for normal recovery. The engine
  executes isolate, reduce-chains, recalibrate, PTP resync and reduce-power via
  `ControlPlane.submit()`, with a regression test asserting no direct mutation
  without an executor. Only emergency shutdown may bypass the normal path.
- Regression coverage: `tests/unit/test_rev09_p0_fixes.py` covers queue deadline
  union, overflow conservation, telemetry seed independence, no-mutation without
  authorization, executor vetoes, and control-routed engine recovery.

## Rev10 P0 fixes

- R10-P0-1: `set_tx_power` writes `RFHardware.tx_power_limit_dbm`; the PHY cap
  therefore changes, rollback restores the prior cap, and readback reports the
  effective limit. Tests compare modeled transmit power on a matched channel
  and seed and confirm a rejected command cannot raise the cap.
- R10-P0-2: recovery callers use `CommandRecord.committed` (`VERIFIED`) rather
  than `executed` (actuation attempted). Attempted, verified, rolled-back and
  failed command counts are reported separately. Tests cover rollback,
  failed actuation, duplicate commands and recovery retry.
- R10-P1-3: latency percentiles use weighted completion delays for every served
  bit, including late service; expiry is no longer inserted as a completion
  sample. Deadline-miss, remaining-queued and completed-service fractions are
  reported separately. The audit's late-service counterexample returns 4 slots.

## Reproducibility

Run `bash scripts/run_all.sh`. It writes `results/build.log`,
`results/gpu_verify.log`, `results/tests.xml`, `results/coverage.xml`,
`results/smoke/`, and `results/full/`. The full run is expected to take several
minutes on an H100; E02 is the dominant cost.


## P1 scientific validation

P1 is implemented by the separate `long_horizon` suite and documented in
`docs/P1_VALIDATION.md`. Its mandatory set is P1A-P1E; the published `smoke` and
`full` suites are unchanged. P1-A reports paired 20-seed 500-slot comparisons and
a separate 20,000-slot timing profile; it does not claim a 20-seed 20,000-slot
matrix. P1-B separates the NR resource audit from the Sionna coded-link check.
P1-C keeps the scalar channel default and adds an optional Jones/XPD sweep. P1-D
routes closed-loop energy/recovery actions through `ControlPlane`. P1-E uses
disjoint calibration/evaluation seeds and does not give labels to the detector.
No P1 output is `HARDWARE_MEASURED`. See `docs/P1_FINAL_DECISION.md` for the
bounded software, 4T4R architecture and PCB-fabrication decisions.
