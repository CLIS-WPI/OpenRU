# H1/H2 Calibration Observability Audit

**Evidence label: SCHEMATIC_AUDIT.** This document records what the documented
H1/H2 hardware can and cannot measure. It is not a hardware measurement or an
RFIC qualification. The model and validation results derived from it are
`SIMULATED`.

## Result in one paragraph

The current H2 tile provides a complex calibration loopback per RF chain and a
power detector per feed. It does **not** provide 16 independent complex feed
observations. Therefore the current H2 can identify a relative complex response
for each of the four chains at the CAL coupler and an amplitude for each of the
16 feeds, but it cannot identify the phase of each feed. Feed phase requires a
factory/bench per-feed table, a shielded near-field probe, or an H3 per-feed
switch/combiner.
The software model must not silently assume the unavailable per-feed IQ path.

## Schematic evidence

| Evidence | Observation | Consequence |
|---|---|---|
| `hardware/H1_CLOCK_CALIBRATION.md` | L1 feed-to-feed calibration requires a cabled VNA or a reference receiver per feed. L3 states the N310 relative phase is random per start/retune. Detectors are amplitude-only. | Feed phase is not observable from the normal H2 detector path. Chain loopback must be repeated after every N310 init/retune. |
| `hardware/h2/schematics/cal.kicad_sch` | J801 is labelled `SMA CAL (inject / sample)`. U801 EP4RKU+ is a 4-way splitter/combiner with `SUM` and `P1`-`P4`. DC801-DC804 are EDC21-24+ couplers. Nets include `CAL_SUM`, `CAL_INJ1`-`CAL_INJ4`, `C1_RFIO_MIX`, and `C1_RFIO_BF`. | The CAL network can inject/sample one complex loopback per chain. It does not route four independent feed responses to four complex receivers. |
| `hardware/h2/schematics/cal.kicad_sch` note | N310 phase is random per start/retune; run CAL loopback after every init/retune. | Absolute phase is not retained across N310 restarts. A relative chain correction is observable only after a fresh loopback. |
| `hardware/h2/schematics/cal.kicad_sch` note | ADTR1107 `CPLR_OUT` to ADAR1000 `DETx` is power-only; element phase calibration needs a near-field/OTA probe. | The per-feed detectors cannot replace complex per-feed IQ. |
| `hardware/h2/schematics/chain1.kicad_sch` | Chain path: N310 IF <-> LTC5553 <-> 8.4 GHz <-> CAL coupler <-> ADAR1000 <-> four ADTR1107 <-> four feeds. | The chain common path is shared by four feeds. A single chain loopback cannot separate the four feed phases. |
| `hardware/h2/schematics/fe1.kicad_sch` | ADTR1107 `CPLR_OUT` pin 12 drives `C1_DET1`-`C1_DET4`. | Each feed has a coupled power observation. |
| `hardware/h2/schematics/bf1.kicad_sch` | `C1_DET1`-`C1_DET4` drive ADAR1000 `DET1`-`DET4`. | The detector interface is a power measurement, not a complex receiver. |

## Observability model

For chain `c` and feed `f(c,s)` on that chain, write the true responses as

```text
chain response:  H_c
feed response:   F_{c,s}
CAL path:        K_c
```

The current H2 observations are modelled as

```text
chain loopback:  y_c = H_c K_c + noise                  (complex, c = 1..4)
feed detector:   p_{c,s} = |H_c F_{c,s}|^2 + noise       (real, f = 1..16)
```

The chain equations contain four unknown complex `H_c` values and four
unknown `K_c` values. Only their product is observable unless `K_c` is
characterized separately. The feed equations contain the magnitude of
`H_c F_{c,s}`, so they constrain feed amplitude but not feed phase. There are
four complex chain observations and sixteen real power observations available
for sixteen complex feed responses; the feed phase subproblem is
underdetermined.

The practical consequences are:

- **Observable now:** relative complex chain common-path response at the CAL
  coupler, per-feed received power,
  per-feed amplitude after detector calibration, chain and feed health for
  gain-changing faults.
- **Not observable now:** per-feed phase, per-feed complex response, a
  phase-only feed fault that does not change feed power, and an absolute phase
  reference across N310 restarts.
- **Still required:** a characterized CAL path `K_c`, detector calibration
  versus frequency/temperature, and a defined phase reference.

## Architecture options

| Architecture | Chain complex | Feed power | Feed complex | Feed phase | Current H2 | Fixture / change |
|---|---|---|---|---|---|---|
| `h2_available` | Yes | Yes | No | No | Yes | None |
| `factory_vna_feed_table` | Yes | Yes | Yes | Yes | Yes, with fixture | VNA or reference RX per feed |
| `near_field_probe` | Yes | Yes | Yes | Yes | Yes, with fixture | Shielded near-field/OTA probe, one feed at a time |
| `proposed_switched_feed_loopback` | Yes | Yes | Yes | Yes | No | H3 hardware change: per-chain 4:1 switch/combiner to a shared complex CAL receiver |
| `ideal_16iq_nonrealizable` | Yes | Yes | Yes | Yes | No | Comparison only; not an available H2 path |

`factory_vna_feed_table` and `near_field_probe` are realizable with the current
board only when an external fixture is used. They do not make the H2 board
self-calibrating in the field. `proposed_switched_feed_loopback` is the option
that could provide autonomous per-feed complex measurements, but it is a
hardware change and has not been implemented or qualified.

## Proposed switched-feed procedure

This is an engineering proposal, not a schematic change in this repository.

1. Add a per-chain 4:1 switch/combiner from the four ADTR1107 `CPLR_OUT` paths
   to one shared complex calibration receiver. The switch and combiner must
   preserve a known, stable path for each selected feed.
2. Characterize the switch/combiner and CAL path versus frequency and
   temperature with a VNA or a traceable reference receiver. Store the
   characterized complex path for each selected feed.
3. For each chain, enable exactly one feed path, terminate or disable the other
   three, and measure the selected feed through the shared complex receiver.
4. Measure the chain common path with the existing CAL loopback. De-embed the
   known CAL path and the selected switch path to obtain `H_c F_{c,s}`.
5. Estimate and store chain corrections and feed corrections separately. Do not
   collapse a feed-phase estimate into a chain correction.
6. Re-measure after calibration and reject the table if residual phase, gain,
   coherence, or fault status fails the configured policy.

## Recommended staged use

1. **Current H2 only:** apply relative chain phase/gain and per-feed amplitude
   corrections. Report feed phase as uncalibrated. Do not claim the scalar
   16-IQ result as an available H2 capability.
2. **Factory/bench table:** populate per-feed complex corrections with a VNA or
   reference receiver. Treat the table as a characterized external fixture, not
   as an H2 self-calibration result.
3. **Near-field revalidation:** use a shielded probe to check drift and to
   refresh feed phase when a full factory fixture is unavailable.
4. **H3 switched loopback:** only after hardware review, EMC/safety review, and
   measured characterization of the switch/combiner paths.

## Safety and evidence boundary

Any calibration procedure must keep transmit disabled or safely terminated,
disable PA drain where required, use shielded/conducted paths, and obtain
explicit authorization before any over-the-air radiation. This repository does
not contain safety logic, firmware register writes, or a qualified H2/H3
calibration procedure.

The synthetic model confirms the architectural conclusion but cannot replace
measured CAL-path, detector, switch, coupler, antenna, or RFIC data. Feed phase
results for `factory_vna_feed_table`, `near_field_probe`, and
`proposed_switched_feed_loopback` are model predictions, not measured hardware
performance. See `docs/rfcal/RFC_HARDWARE_INTEGRATION.md` for the H2/H3
interface control record, the `CPLR_OUT` tap analysis, and the staged
recommendation.
