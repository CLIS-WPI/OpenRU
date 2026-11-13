# RFC: RF Calibration Hardware Integration for OpenRU-X6 H2/H3

- **Status:** Proposed for review. No schematic, layout, firmware, or hardware
  change is implemented by this document.
- **Branch:** `feature/rf-calibration-core`.
- **Evidence labels:** `SCHEMATIC_AUDIT` for the interface statements;
  `SIMULATED` for every numerical result. No hardware measurement is present.
- **Decision requested:** approve the H2 measurement boundary for v0.1, and
  authorize a one-chain H3 switched-loopback prototype before any full-board
  H3 change.

## 1. Summary and recommendation

The current H2 tile has a complex calibration loopback per RF chain and a
power detector per feed. It does not provide 16 independent complex feed
observations. The missing feed phase is not a software-estimation problem; it
is absent from the available measurement equations.

The recommended staged decision is:

1. **v0.1 uses H2 as it exists.** Apply relative chain phase/gain and per-feed
   amplitude corrections. Obtain per-feed phase from a factory/bench VNA table
   or a shielded near-field probe. Report feed phase as externally calibrated,
   not as an H2 self-calibration result.
2. **Do not add H3 to v0.1.** The H2-A schematic is preliminary and is a
   layout NO-GO. The later H2-E bench-readiness package does not change the tile
   schematic or clear that gate. The ADAR1000 is not qualified at 8.4 GHz, the
   antenna/feed interface is unresolved, and the `CPLR_OUT` coupler has not been
   measured at the operating point.
3. **Fund an H3 one-chain prototype as a v0.2 investigation.** Put a per-chain
   4:1 switch/combiner on the four `CPLR_OUT` taps, keep the detector path
   observable, and measure one selected feed at a time with a shared complex
   calibration receiver.
4. **Treat H3 as an electronics-loopback calibration, not full antenna
   self-calibration.** `CPLR_OUT` observes the ADTR1107 output at its internal
   coupler. It does not observe the passive feed/antenna path beyond that
   coupler, the receive path, antenna impedance, or mutual coupling. Those
   require a characterized passive table or a near-field/OTA fixture.

The H3 concept is the strongest autonomous option in the synthetic model, but
it is not a complete 16-feed self-calibration solution until the passive and
receive paths are addressed.

## 2. Scope and evidence boundary

In scope:

- exact H2 feed, CAL, detector, reference, and test interfaces that a fixture
  or an H3 change must connect to;
- a reference H3 per-chain switched-loopback architecture;
- measurement equations and de-embedding requirements;
- comparison of H2, factory VNA, near-field probe, and H3;
- synthetic impairment, uncertainty, and angular-search resolution evidence.

Out of scope:

- KiCad schematic edits, PCB layout, switch part selection, or firmware;
- register writes, PA enable logic, or transmit control;
- a released test procedure or an authorization to radiate;
- measured coupler, switch, detector, cable, antenna, or RFIC data;
- a claim that ADAR1000 meets its reported specifications at 8.4 GHz.

The H2-A review states that the design is preliminary, has 22 deliberate ERC
opens, a placeholder power tree, missing bypass values, unresolved footprints,
and no antenna/feed EM design. The H2-A gate is **NO-GO for layout**. This RFC
does not change that gate.

H2-A remains the historical baseline for the RF/cal interface statements in
this RFC. The subsequent H2-E and H2-E.1 work is a separate bench-readiness
package, not a revised RF interface:

- H2-E (`hardware/h2e-bench-prep`, `203c69f`) leaves the main OpenRU tile
  schematic unchanged and adds a one-chain Candidate-A safety fixture schematic
  only. It has no fixture PCB layout, nothing was purchased, fabricated, or
  energised, and no ADTR1107 is on a test article. Its tile-layout status is
  still **NO-GO**.
- H2-E.1 (`hardware/h2e1-procurement-audit`, `3062b65`) resolves the fixture
  A-SENSE and R57/R58 procurement items. The corresponding A-SENSE tile change
  is recommended, not applied, and the tile PCB layout is not started. The
  fixture is not build-ready: it still has no PCB layout, and nothing was
  purchased, fabricated, or energised. The main tile schematic is unchanged and
  the tile layout remains **NO-GO**.

H2-E therefore does not qualify the ADAR1000 at 8.4 GHz, release the antenna or
feed reference plane, validate the `CPLR_OUT` coupler, or provide any measured
calibration evidence. It prepares a safer bench article and must not be cited as
an RF calibration capability.

## 3. H2 interfaces

### 3.1 Feed interface

The H2-A schematic contains 16 coaxial feed symbols, `JF1` through `JF16`, in
`fe1.kicad_sch` through `fe4.kicad_sch`. Each symbol value carries the
simulation feed index, site, and polarization, for example
`FEED sim0 site0 V`.

| Item | Current H2 evidence | Integration consequence |
|---|---|---|
| Feed connector | `JF1`-`JF16`, `Conn_Coaxial` symbols | A VNA/near-field fixture must mate with the final connector and launch. |
| Feed ownership | Chain `c` drives `UFE{4(c-1)+k}` and `JF{4(c-1)+k}` for `k=1..4` | A per-chain 4:1 switch can select the four feeds of that chain. |
| Footprint | Not assigned for the SMA/feed interface | The mechanical reference plane and fixture cannot be frozen yet. |
| Antenna/feed EM | Unresolved (H2-A U4, R13, R14) | No exact antenna-port reference plane exists yet. |
| Polarization map | `hardware/H1_FEED_POLARIZATION_MAP.csv` | Use the feed map, not symbol order, for V/H and site assignment. |

The exact VNA reference plane is therefore defined functionally as **the final
feed launch at `JF1`-`JF16`**, but not yet mechanically released. A fixture
design must wait for the connector/footprint and antenna-interface decisions.

### 3.2 CAL interface

The H2 CAL sheet provides:

| Element | Connection | Role |
|---|---|---|
| `J801` | SMA labelled `SMA CAL (inject / sample)` | External CAL port. |
| `U801` | EP4RKU+ 4-way splitter/combiner, `SUM` and `P1`-`P4` | Combines/splits the four chain CAL paths. |
| `DC801`-`DC804` | EDC21-24+ couplers between `C*_RFIO_MIX` and `C*_RFIO_BF` | Couples the CAL signal into/out of each chain. |
| `CAL_SUM`, `CAL_INJ1`-`CAL_INJ4` | Nets from `U801` to the chain couplers | One complex loopback path per chain. |

This network measures a chain common-path loopback at the CAL coupler. It does
not route four independent feed responses to four complex receivers.

Two documented uncertainties directly affect any calibration table:

- the EP4RKU+ phase unbalance is up to 19 degrees;
- the EDC21-24+ coupler directivity is 19 dB typical.

Both must be characterized over frequency and temperature. The `J801` label
says `inject / sample`; the exact forward/reverse coupling direction and the
reference plane at the coupler must be confirmed on a bench before a table is
trusted.

### 3.3 Per-feed detector path

Each ADTR1107 `CPLR_OUT` pin 12 drives an ADAR1000 `DET1`-`DET4` input. The
ADTR1107 coupling is documented as 28 dB at the low end of 6-18 GHz and 18 dB at
the high end. The ADAR1000 detector range is documented as -20 to +10 dBm at
11.5 GHz. Neither value is an 8.4 GHz qualification.

The detector path is power-only. It can support per-feed amplitude and
gain-changing fault detection. It cannot support per-feed phase, a phase-only
feed fault, or a complex feed table.

### 3.4 Reference and LO

The N310 relative phase is random per start/retune. The CAL loopback must be
repeated after every N310 initialization or retune. A stored correction table
without a fresh reference measurement is not an absolute phase reference.

Any H3 receiver must either share the N310 reference/LO distribution or have a
characterized reference channel. A separate receiver with only a 10 MHz
reference still has an unknown startup phase until its own reference path is
measured.

## 4. Observable quantities

For chain `c` and feed `s`:

```text
H_c          chain common complex response
F_{c,s}      feed complex response
K_c          CAL-path complex response
A_c          ADAR1000 complex gain at the selected state
P_{c,s}      ADTR1107 complex gain at the selected state
C_{c,s}      CPLR_OUT coupling complex response
X_{c,s}      switch/combiner complex path
```

### 4.1 Current H2

```text
chain loopback:  y_c = H_c K_c + noise                  (complex, c = 1..4)
feed detector:   p_{c,s} = |H_c F_{c,s}|^2 + noise       (real, f = 1..16)
```

There are four complex observations and sixteen real observations for sixteen
complex feed responses. The feed phase subproblem is underdetermined. The
current H2 can identify relative chain amplitude/phase at the CAL coupler and
per-feed amplitude, but not per-feed phase.

### 4.2 H3 electronics loopback

A selected feed is observed through `CPLR_OUT`:

```text
z_{c,s} = H_c A_c P_{c,s} C_{c,s} X_{c,s} + leakage + noise
```

The passive path after the ADTR1107 output, `F_{c,s}`, is **not** in this
equation. If `F_{c,s}` is required, it must come from a factory/bench table or
a near-field measurement. The H3 loopback calibrates the electronics to the
ADTR output coupler, not the radiated element.

The chain loopback is still needed:

```text
y_c = H_c K_c
```

De-embed the characterized `K_c`, `C_{c,s}`, and `X_{c,s}`:

```text
z_{c,s} / y_c = A_c P_{c,s} C_{c,s} X_{c,s} / K_c
```

The result can support relative per-feed electronics phase/gain corrections
after `A_c`, `P_{c,s}`, and the switch path are characterized. It does not
separate the passive antenna/feed phase or the receive path.

## 5. H3 reference architecture

This is a reference architecture for review, not a schematic change.

```text
ADTR1107 CPLR_OUT (4 per chain)
        |
        +--> power detector (ADAR1000 DETx), always connected where possible
        |
        +--> per-chain 4:1 switch
                 |
                 +--> 4:1 combiner (or two-stage 16:1 mux)
                          |
                          +--> shared complex CAL receiver
                                   ^
                                   |
                          chain CAL loopback / reference switch
```

### 5.1 Tap and detector budget

The preferred tap keeps the detector connected through a two-way splitter so
power monitoring is not lost during calibration. The splitter adds about 3.5
dB to the detector path. At 10 dBm per feed and 18-28 dB `CPLR_OUT` coupling,
the coupled power is approximately -18 to -8 dBm before the splitter. The
splitter therefore places the detector near or below the low end of the
documented -20 dBm range, before accounting for frequency, temperature, and
coupler directivity.

Consequences:

- do not commit to a splitter until the 8.4 GHz detector response and the
  `CPLR_OUT` coupling are measured at the expected power levels;
- if detector headroom is insufficient, use a fail-safe SPDT that defaults to
  the detector, but log that monitoring is unavailable during calibration;
- re-derive the detector thresholds after the tap change; do not reuse the
  current thresholds;
- add a calibrated attenuator or buffer only after its own drift and
  compression are characterized.

The switch and combiner should be selected for isolation and repeatability,
not only insertion loss. A 20 dB switch-isolation assumption is not a hardware
specification; the model shows that simultaneous feed leakage at -20 dB raises
the synthetic pointing error from 0.077 to 0.846 degrees.

### 5.2 Measurement sequence

1. Initialize the N310 and LO; wait for lock and temperature stabilization.
2. Disable or safely terminate transmit; set PA drain to the approved state.
3. Measure the chain CAL loopback through `J801` for every chain.
4. Select one feed per chain; disable or terminate the other three.
5. Measure the selected `CPLR_OUT` path through the switch/combiner and shared
   receiver.
6. Repeat for all four feeds and all four chains.
7. Repeat the chain CAL loopback after the feed sweep to detect drift.
8. Reject the table if residual phase, gain, coherence, isolation, or settling
   exceeds the configured policy.

The exact switch truth table, settling delay, blanking, and PA-disable policy
must be defined with the hardware owner and firmware owner before any test.

### 5.3 What H3 does not observe

- passive feed/antenna phase after the ADTR1107 output;
- antenna impedance, mutual coupling, or radiated pattern;
- receive-path phase/gain;
- a phase-only fault in the passive feed path;
- absolute phase across independent N310 restarts.

A complete self-calibration claim requires additional observation points. If
receive calibration is required, add a characterized receive coupler/switch
path; do not assume TX/RX reciprocity without measurement. If antenna/feed
phase is required, add a factory table or a near-field fixture.

## 6. Interface control

### 6.1 H2 factory VNA table

This is the v0.1 external-calibration interface.

| Item | Requirement |
|---|---|
| Reference planes | Final `J801` CAL launch and final `JF1`-`JF16` feed launches. |
| Fixture | Phase-stable cables, calibrated SOLT/TRL at both planes, documented cable flex. |
| States | Define TX and RX separately; record PA/LNA/switch/attenuator states. |
| Drive | Low-level, compression-free, safely terminated; no unauthorized OTA. |
| Data | Complex S21 versus frequency at 8.4 GHz and the operating band; S11/S22 where relevant. |
| Per feed | Feed index, chain, site, polarization, timestamp, temperature, firmware state. |
| Reference | Repeat the chain loopback in the same session; store the N310 state. |
| Uncertainty | Include connector repeatability, cable drift, coupler directivity, and reference-plane uncertainty. |

The table is only valid for the state in which it was measured. It must not be
silently reused after an N310 retune, switch change, cable change, or
temperature excursion outside the characterized range.

### 6.2 Near-field probe

A shielded near-field probe can observe the radiated complex field one feed at
a time. It requires a mechanical positioner, absorber, probe characterization,
and a defined aperture reference. It is slower than a conducted VNA table and
is not a field self-calibration method. It is the fallback when the passive
feed/antenna path cannot be measured conductively.

The exact probe plane cannot be frozen until the antenna/feed EM design and
the `JF` launch are released.

### 6.3 H3 control and data

At minimum, the H3 interface needs:

- per-chain selected-feed control with a safe default;
- detector-path state reporting;
- switch settling and blanking requirements;
- shared-receiver reference state;
- per-measurement metadata: chain, feed, switch path, attenuator, PA state,
  temperature, LO state, timestamp;
- raw complex results and a characterized switch/combiner/CAL table;
- an explicit validity flag when detector monitoring is disconnected.

No H3 control line or register write is defined by this RFC.

## 7. Comparison

| Option | Feed complex | Feed phase | Passive antenna/feed | RX path | Field self-cal | Change |
|---|---|---|---|---|---|---|
| Current H2 | No | No | No | No per-feed complex | No | None |
| Factory VNA table | Yes, at reference planes | Yes | Yes if fixture includes it | Yes if measured | No | Fixture |
| Near-field probe | Yes, radiated | Yes | Yes | No | Fixture-dependent | Positioner/probe |
| H3 switched `CPLR_OUT` | Yes to ADTR coupler | Yes for electronics | No | No | Yes for electronics | Board/prototype |
| H3 plus passive table | Yes | Yes | Yes | No | Partly | Board + fixture |
| Ideal 16-IQ | Yes | Yes | Yes | Yes | Not realizable | Comparison only |

The synthetic model ranks H3 above current H2 because it removes feed-phase
ambiguity. That ranking is conditional on switch isolation, path stability,
coupler characterization, and a valid detector tap. It does not establish that
H3 alone can calibrate the radiated element or the receive path.

## 8. Validation evidence

The impairment model adds first-order synthetic reference drift, switch
leakage, phase noise, mutual coupling, and correlated chain errors. The full
run uses 5 seeds and 3 steering angles per case, for 15 samples per row. Values
are means over that ensemble; `p95` is the 95th percentile.

| Case | Pointing mean (deg) | Pointing std (deg) | Pointing p95 (deg) | Cal phase mean (deg) |
|---|---:|---:|---:|---:|
| H3 no impairment | 0.0771 | 0.0300 | 0.1334 | 0.4987 |
| H2 no impairment | 1.4296 | 0.5534 | 2.0310 | 4.9716 |
| Independent reference drift, 0.5 deg | 0.2387 | 0.2009 | 0.6123 | 0.6871 |
| Common reference drift, 0.5 deg | 0.0771 | 0.0300 | 0.1334 | 0.4987 |
| Switch leakage, -20 dB, simultaneous | 0.8463 | 0.1351 | 1.0582 | 4.0681 |
| Switch leakage, -20 dB, one at a time | 0.0771 | 0.0300 | 0.1334 | 0.4987 |
| Independent phase noise, 2 deg | 0.6335 | 0.3442 | 1.1309 | 2.1244 |
| Common phase noise, 2 deg | 0.0771 | 0.0300 | 0.1334 | 0.4987 |
| Mutual coupling, -20 dB | 0.7689 | 0.4935 | 1.6930 | 9.0357 |
| Mutual coupling, -30 dB | 0.1736 | 0.0558 | 0.2807 | 1.5682 |
| Combined moderate | 0.5619 | 0.2215 | 0.9319 | 4.2570 |

Angular-search resolution is evaluated with an ideal calibrated beam and
intentional off-grid windows:

| Search step (deg) | Grid bound (deg) | Pointing mean (deg) | Pointing max (deg) |
|---:|---:|---:|---:|
| 0.010 | 0.0071 | 0.0043 | 0.0044 |
| 0.050 | 0.0354 | 0.0217 | 0.0218 |
| 0.100 | 0.0707 | 0.0434 | 0.0436 |
| 0.250 | 0.1768 | 0.1086 | 0.1089 |
| 0.500 | 0.3536 | 0.2172 | 0.2178 |

The previously reported `0.01 deg` switched-loopback result was at the
configured `0.25 deg` search step. It is a grid/model floor, not a physical
accuracy claim. The fine-search `0.0043 deg` result at a `0.010 deg` step is
also a numerical floor. Neither number is a hardware guarantee.

The impairment parameters are engineering assumptions. The model does not
include measured coupler directivity, switch isolation, detector nonlinearity,
compression, temperature dependence, or measured antenna patterns.

See `docs/rfcal/IMPAIRMENT_REPORT.md` for the generated report and
`docs/rfcal/impairment_reference_summary.json` for the compact summary.

## 9. Risks and open questions

| ID | Risk/question | Why it matters | Closure |
|---|---|---|---|
| H3-1 | `CPLR_OUT` coupling/directivity at 8.4 GHz | Sets sampled power and feed-to-feed isolation | Bench measurement with selected switch path |
| H3-2 | Detector headroom after splitter | May lose low-power monitoring | Measure DET response at 8.4 GHz; choose splitter or fail-safe SPDT |
| H3-3 | Switch isolation and settling | Leakage and stale samples corrupt phase | Specify isolation/settling; measure with one feed active |
| H3-4 | Switch/combiner phase stability | Drift becomes calibration error | Characterize over temperature, frequency, and power |
| H3-5 | Passive feed/antenna phase | H3 cannot observe it | Factory table or near-field fixture |
| H3-6 | Receive path | `CPLR_OUT` is not an RX observation | Add RX coupler or measure RX separately |
| H3-7 | N310 reference phase | Random per start/retune | Fresh chain loopback and reference channel |
| H3-8 | H2-A layout NO-GO | H3 cannot be laid out on an unfrozen H2 | Close power, ERC, footprints, antenna EM; H2-E fixture readiness does not unblock the tile layout |
| H3-9 | ADAR1000 8.4 GHz qualification | Reported specifications are not guaranteed | Bench characterization at the operating point |
| H3-10 | Safety/control | Switch/PA state can create unintended radiation | Hardware/firmware interlock review; no register writes here |

## 10. Staged plan and acceptance criteria

### v0.1: H2 plus external feed table

Acceptance:

- chain loopback repeated after every N310 init/retune;
- per-feed amplitude from the detector path after re-characterization;
- per-feed phase from a documented factory/near-field table;
- the report labels feed phase as externally calibrated;
- no claim that H2 alone self-calibrates 16 feeds.

### v0.2: one-chain H3 prototype

Build a bench prototype, not a board change:

- four `CPLR_OUT` taps from one chain;
- per-chain 4:1 switch and characterized combiner;
- detector tap with measured headroom;
- shared complex receiver with a reference channel;
- one-feed-at-a-time sequencing.

Acceptance:

- measured switch isolation and settling;
- measured path stability over the operating temperature range;
- measured detector response at 8.4 GHz before and after the tap;
- recovered electronics phase within a pre-agreed bound of a VNA reference;
- documented residual after de-embedding;
- no regression in detector-based power monitoring.

### v1.0: full H3 decision

Only after the one-chain prototype and a passive feed/antenna characterization.
Do not approve a full 16-feed H3 layout on the basis of the synthetic model.

## 11. Reproduce

```bash
python -m openru_x6.rfcal impairments --output results/rfcal_impairments
python -m pytest tests/rfcal/test_rfcal_impairments.py -q
```

The `impairments` command writes:

- `impairments.json`: all beam records and resolution records;
- `impairment_reference_summary.json`: compact summary without records;
- `impairment_runs.csv`: flat beam-record table;
- `impairment_report.md`: generated uncertainty and resolution tables.

The full report in this repository was generated with the default 5 seeds,
3 angles, 12 cases, and 0.01 degree fine search.

## 12. References

- `hardware/h2/reports/H2A_SCHEMATIC_REVIEW.md`
- `hardware/h2/reports/H2A_UNRESOLVED_ISSUES.md`
- `hardware/h2/reports/H2E_BENCH_READINESS.md` (branch `hardware/h2e-bench-prep`, `203c69f`)
- `hardware/h2/reports/H2E1_PROCUREMENT_READINESS.md` (branch `hardware/h2e1-procurement-audit`, `3062b65`)
- `hardware/h2/schematics/cal.kicad_sch`
- `hardware/h2/schematics/fe1.kicad_sch` through `fe4.kicad_sch`
- `hardware/h2/schematics/bf1.kicad_sch` through `bf4.kicad_sch`
- `hardware/H1_CLOCK_CALIBRATION.md`
- `hardware/H1_FEED_POLARIZATION_MAP.csv`
- `docs/rfcal/CALIBRATION_OBSERVABILITY.md`
- `docs/rfcal/IMPAIRMENT_REPORT.md`
- `docs/rfcal/REPORT.md`
