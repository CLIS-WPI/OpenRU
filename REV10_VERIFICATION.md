# OpenRU-X6 Rev10 Verification

Date: 2026-11-11  
Scope: immediate R10-P0 fixes A/B/C from the Rev10 independent audit, plus a clean H100 smoke/full rerun.

## Fix inventory

| Audit item | Change | Evidence |
|---|---|---|
| R10-P0-1 power command ineffective | `ControlPlane._actuate()` now writes `RFHardware.tx_power_limit_dbm`; rollback snapshot/restore includes the cap; readback reports the effective limit. | `tests/unit/test_rev10_fixes.py::test_tx_power_command_changes_effective_phy_cap`, `::test_rejected_power_command_does_not_raise_cap` |
| R10-P0-2 rollback counted as applied | Added `CommandRecord.committed` (true only for `VERIFIED`). Engine, INTEGRATION and recovery callers use `committed`, not `executed`. Attempted/verified/rolled-back/failed counters are reported separately. | `test_rollback_is_not_reported_as_committed`, `test_failed_actuation_is_not_committed`, `test_duplicate_verified_command_is_idempotent`, `test_vetoed_recovery_is_retried_until_verified` |
| R10-P1-3 optimistic latency | Completion samples now include late service once; expiry is no longer a completion sample. Added `latency_p*_completed_slots`, `deadline_miss_fraction`, `completed_service_fraction`, `remaining_queued_fraction`. | `test_late_service_latency_is_completion_delay_not_expiry_delay`, `test_completion_samples_are_weighted_and_not_double_counted`, `test_empty_queue_latency_is_nan_and_fractions_zero` |

Primary files: `openru_x6/control.py`, `openru_x6/engine.py`, `openru_x6/diagnostics.py`, `openru_x6/traffic.py`, `openru_x6/experiments/e02.py`, `openru_x6/experiments/e04.py`, `openru_x6/experiments/integration.py`, `openru_x6/reporting.py`.

## Verification run

Command: `bash scripts/run_all.sh`  
Result: exit 0, smoke and full both PASS.

- Tests: **40 passed**, coverage **54%**.
- Image: `sha256:927fd2d6cc07b27cce32c6e435db285c8f57eeb6675c5a584c275900afb5a4dd`.
- Smoke digest `e00ba9df0f1b575a`: 12/12 PASS, 4,372 rows, 40.6 s.
- Full digest `1d89961ada5a68e3`: 12/12 PASS, 99,041 rows, 590.6 s.
- E04 full: recall 1.00, localization 1.00, false-alarm rate 0.00; 1,024 attempted actions, 1,024 verified, 0 rolled back, 0 failed, 0 unrouted.
- INTEGRATION full: 20/20 seeds detected/isolated, zero unauthorized commands, zero unsafe sleep commands, audit valid, energy command verified, service recovered.
- E02 full: 17.43% mean low-load energy saving, goodput delta -1.37 Mbps, deadline-expired delta +0.0253, P99 completed latency 105 slots. The energy policy is explicitly **not QoS-neutral**.

Artifacts: `results/pytest.log`, `results/tests.xml`, `results/coverage.xml`, `results/smoke/`, `results/full/`, `results/full/report.md`, `results/full/summary.json`, `results/image_id.txt`.

## Remaining limitations

- E04 still evaluates conspicuous, injected simulation faults, not unknown physical fault mechanisms; recall 1.00 is not physical diagnostic accuracy.
- Missing/biased/frozen sensors, sensor outages and domain shift remain untested.
- E01 still uses a 3-slot (1.5 ms) horizon; long-horizon scheduling, fairness and latency claims are not established.
- E02 is not a QoS-constrained Pareto sweep. Its P99 completed latency exceeds the 40-slot deadline under the tested low-load policy.
- INTEGRATION exercises one scripted energy transition plus a fault; a fully coupled adaptive-energy/fault/wake/traffic loop remains P1 work.
- Dual polarization, NR resource-factor semantics, OCUDU/OFH interoperability and all RF hardware claims remain unverified.
- E05 remains role-policy simulation, not cryptographic identity or board-level attestation.

## Decision

**Software immediate-fix gate: PASS.** R10-P0-1, R10-P0-2 and R10-P1-3 are implemented and covered by regression tests; the clean full suite passes.

**Scientific validation gate: NOT MET.** Extended E01/E02/E04 and combined adaptive INTEGRATION work remains.

**PCB / hardware release: NO-GO.** No OFH interoperability, RF measurement, EM/thermal signoff or calibrated dual-polarized array validation exists in this repository.


## P1 follow-on (separate reduced suite)

P1 is implemented on branch `p1-scientific-validation` as the separate
`long_horizon` suite; `smoke` and `full` membership is unchanged. Latest local
P1 run: **5/5 PASS**, 9,454 rows, 1,221.8 s, digest `d432664706af1f75`.

Fresh container regression after the P1 changes: smoke 6/6 PASS (2,681 rows,
34.2 s, digest `cf44501c4f9daa81`), full 12/12 PASS (99,041 rows, 592.5 s,
digest `2200ad495a88f95c`). Deterministic metrics match the Rev10 baseline; only
GPU timing, stochastic Sionna BLER and the OCUDU test-mode PDSCH count vary.
The config digest changed because the new default simple-polarization
configuration is now part of the serialized radio config.

- P1-A: 64 vs 32 chains, 20 paired seeds at 500 slots: +0.276 dB mean goodput,
  energy per bit +186.9 nJ/bit (804.7 to 980.1). The 20,000-slot profile is one
  run and is not extrapolated.
- P1-B: NR grid and zero-resource boundaries audited; Sionna coded-link
  cross-check executed (`PHY_VALIDATED` for that check only).
- P1-C: optional Jones/XPD sweep; scalar channel remains default. No calibrated
  antenna/polarization claim.
- P1-D: all 48 constrained runs infeasible under tested QoS thresholds.
- P1-E: sensor-degraded recall 0.744; 28/48 healthy sensor-fault cases false
  alarmed (105,000/hour in-harness). These are negative reliability findings.

P1 does not change the Rev10 decision: **PCB / hardware release remains NO-GO.**
