# P1 final readiness decision

Date: 2026-11-11 (local), from the corrected `long_horizon` run
Scope: bounded P1 software validation and the next hardware step for OpenRU-X6.

This decision is based on `results/long_horizon` with config digest
`d432664706af1f75`, 5/5 PASS, and the corrected pinned-container regression
(52 tests, smoke 6/6, full 12/12). Every P1 output is simulation evidence. No P1
result is `HARDWARE_MEASURED`.

## Decisions

| Decision | Status | Meaning |
|---|---|---|
| `SOFTWARE_VALIDATION` | **PASS, bounded** | The corrected P1 suite is internally consistent and reproducible for the reduced design. This is not a deployment or product-validation pass. |
| `HARDWARE_ARCHITECTURE_READINESS` | **CONDITIONAL GO** | Proceed to **4T4R/16-feed RF architecture and component selection**. Do not commit to the full 64T64R/256-feed build. |
| `PCB_FABRICATION_READINESS` | **NO-GO** | No PCB fabrication release. RF/EM/SI/PI/thermal, RFIC, stackup, calibration and OFH prerequisites remain unmet. |

## Corrected P1 evidence

| Item | Result |
|---|---|
| P1-A 32 vs 64 chains | 503.54 vs 525.67 Mbps mean goodput; **+0.187 dB** |
| P1-A energy per bit | 700.6 vs 875.1 nJ/bit; 64 chains costs about **+24.9%** |
| P1-A paired evidence | 20 paired seeds, 500-slot pivots, both goodput CIs above zero; one separate 20,000-slot profile, not a seed matrix |
| P1-B NR grid | 98.28 MHz occupied, 273 PRBs, 0.492 resource factor, delivered/capacity 0.374 |
| P1-B Sionna cross-check | Small AWGN coded-link check only; abstraction is conservative at high SNR (6 dB: 0.592 vs 0.5625; 8 dB: 0.077 vs 0.0) |
| P1-C polarization | Jones mean 590.29 Mbps vs 675.66 Mbps simple reference; XPD/XPR are simulated, not chamber data |
| P1-D constrained QoS | **24 constrained runs out of 48 total; 0/24 feasible** |
| P1-D constrained metrics | Mean deadline miss 0.311 (0.114-0.463); mean P99 173 slots (89-264); mean service interruption 18 slots; mean energy 41.18 J |
| P1-D recovery | 48/48 faults detected and recovered through authorized commands |
| P1-E detection | Physical-fault recall 1.0 and localization 1.0 on 56 injected cases |
| P1-E sensor degradation | Recall 0.744 on 336 cases |
| P1-E false alarms | **28/48 healthy sensor-fault cases (58.3%)**; 105,000/hour is a short-run extrapolation, not a measured rate |

## Answers to the hardware questions

1. **Is a full 64T64R/256-feed commitment justified now?** No. The simulated
   goodput gain is only +0.187 dB while energy per bit rises about 24.9%, and the
   model has no BOM, RF loss, thermal-margin or reliability evidence.
2. **What should be built or specified next?** A **4T4R/16-feed tile** with
   modular tile power gating, per-tile telemetry, readback, calibration and a
   safe fallback path. This is the correct first physical and component-level
   step, not a 256-feed board.
3. **Can PCB fabrication start?** No. Fabrication remains `NO-GO`.
4. **Is O-RAN Open Fronthaul or RU interoperability proven?** No. It remains
   `NOT_TESTED`/`BLOCKED`; OCUDU `ru_dummy` and test-mode scheduling are not OFH
   evidence.
5. **Are the scheduler and fault detector deployment-ready?** No. P1-D has zero
   feasible constrained runs and P1-E has a 58.3% healthy-case false-alarm rate.

## Known hardware risks

- No physical PA, VSWR, antenna, filter, clock, supply or thermal measurement.
- No calibrated dual-polarized array or antenna-chamber pattern.
- No controlled-impedance stackup, RF EM, SI/PI, DFM or fabricator review.
- No RFIC/component derating, BOM cost, yield or supply-chain analysis.
- No OFH transport, synchronization, C/U/S/M-plane or multi-vendor integration.
- P1's scheduler is infeasible under the tested QoS constraints, so it cannot
  justify a hardware capacity commitment.

## Transition decision

**Yes: transition to 4T4R RF Hardware Architecture and Component Selection.**
The transition is limited to architecture definition, RFIC/front-end component
selection, measurement planning and a 4T4R/16-feed tile concept. It does **not**
authorize the full 64T64R array, PCB fabrication, or a deployment claim.

Exit criteria for that next phase:

- Freeze 4T4R/16-feed requirements and interface boundaries.
- Select RFIC, PA, LNA, switch, filter, clock and power components with derating.
- Produce a controlled-impedance stackup and SI/PI/EM/thermal analysis plan.
- Define calibration, telemetry, readback, fault-injection and safety tests.
- Obtain measured bench evidence before any PCB fabrication gate is reconsidered.
