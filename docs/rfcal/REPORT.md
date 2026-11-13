# OpenRU-X6 RF Calibration Validation Report

**Evidence label: SIMULATED.** This report contains synthetic IQ, path, and
polarization data. It is not a hardware measurement and does not qualify the
ADAR1000 at 8.4 GHz.

## Scope

The validation exercises the hardware-independent model for the documented H1
4T4R / 16-feed topology:

- 4 RF chains, 16 feeds, 8 dual-polarized sites in a 2x4 grid.
- 8.4 GHz carrier, 17.845 mm site pitch.
- Chain-level complex calibration and per-feed power/detector observability.
- Optional per-feed complex measurements for factory, near-field, and proposed
  switched architectures.
- Jones-vector polarization with assumed cross-polar leakage.
- Per-feed phase and gain quantization.
- Per-path/chain calibration, fault detection, and failed-chain scenarios.
- Beam pointing, co-pol and cross-pol gain, XPD, peak sidelobe, and
  quantization loss.
- First-order reference drift, switch leakage, phase noise, mutual coupling,
  correlated chain errors, and angular-search resolution in a separate
  impairment sweep.

The model does not write RFIC registers or control a transmitter. The main
sweep does not include measured element patterns, measured polarization
leakage, temperature drift, ADC effects, or RF compression. The impairment
sweep adds synthetic versions of several of these mechanisms; they are
engineering assumptions, not measurements.

## Run configuration

| Parameter | Value |
|---|---|
| Seeds | 10 |
| SNR levels | 10, 20, 30, 40 dB |
| Mismatch scales | 0, 0.5, 1, 2 |
| Steering angles | 5 azimuth/elevation targets |
| Captures per path | 4 |
| Samples per capture | 64 |
| Architectures | 5 observability architectures |
| Beam scenarios | 5 per calibration |
| Fault seeds | 3 |
| Fault types | missing and faulty, each chain and feed |
| Quantizer | 2.8125 deg phase, 0.5 dB gain, 31 dB range |
| Polarization | 25 dB assumed cross-pol, 90 deg leakage phase |
| Container | `openru-x6-sim:0.1.0` |
| GPU used | No |
| Scalar-baseline runtime | 17.907 s |
| Observability runtime | 88.116 s |

The observability run produced 20,000 vector beam records, 600 fault records,
and a separate 250-record scalar per-feed-IQ base-case baseline. All values are
deterministic for the configured seeds; only runtime varies.

The current H2 hardware cannot identify 16 independent feed complex responses.
It can identify a relative complex chain common-path response at the CAL
coupler and per-feed amplitude. Feed phase requires a factory/bench per-feed
table, a shielded near-field probe, or an H3 per-feed switch/combiner. See
`docs/rfcal/CALIBRATION_OBSERVABILITY.md` for the schematic audit, and
`docs/rfcal/RFC_HARDWARE_INTEGRATION.md` for the H2/H3 interface and staged
recommendation. The full generated observability tables are in
`docs/rfcal/OBSERVABILITY_REPORT.md`.

## Base-case vector results

Base case is 30 dB SNR and mismatch scale 1.0. The receiver is matched to the
incident V polarization. Co-pol and cross-pol gains are relative to one
unit-amplitude feed. XPD is the assumed polarization discrimination, not a
measured isolation.

| Architecture | Scenario | Pointing (deg) | Co-pol (dB) | Cross-pol (dB) | XPD (dB) | Sidelobe (dB) |
|---|---|---:|---:|---:|---:|---:|
| `h2_available` | uncalibrated | 2.2915 | 9.0117 | -15.9883 | 25.000 | -9.84 |
| `h2_available` | chain equalized | 1.3080 | 8.9408 | -16.0592 | 25.000 | -10.30 |
| `h2_available` | chain + feed amplitude (equalized) | 1.2530 | 8.9116 | -16.0884 | 25.000 | -10.34 |
| `h2_available` | chain phase only | 1.2735 | 9.0651 | -15.9349 | 25.000 | -10.27 |
| `h2_available` | chain phase only quantized | 1.2981 | 9.0644 | -15.9356 | 25.000 | -10.27 |
| `factory_vna_feed_table` | chain + feed phase-only | 0.0000 | 9.0905 | -15.9095 | 25.000 | -10.47 |
| `near_field_probe` | chain + feed phase-only | 0.2861 | 9.0870 | -15.9130 | 25.000 | -10.37 |
| `proposed_switched_feed_loopback` | chain + feed phase-only | 0.0100 | 9.0903 | -15.9097 | 25.000 | -10.46 |
| `proposed_switched_feed_loopback` | phase-only quantized | 0.1569 | 9.0894 | -15.9106 | 25.000 | -10.43 |
| `ideal_16iq_nonrealizable` | chain + feed phase-only | 0.0000 | 9.0905 | -15.9095 | 25.000 | -10.48 |

The current-H2 result is the key negative result: the best available
chain-plus-feed-amplitude equalized correction reduces pointing error from about
2.29 degrees to about 1.25 degrees, but cannot remove the unobserved feed-phase
error. The combined phase-only scenario applies only chain phase on
`h2_available`, because a feed phase correction does not exist; it lands near
1.27 degrees. All per-feed-complex architectures reach below 0.3 degrees in this
synthetic model. The proposed switched loopback and factory table are
effectively at the simulation floor; the near-field probe is limited by its
configured probe path and SNR.

The reported `0.0100 deg` switched result was obtained with a `0.25 deg` search
step. It is a grid/model floor, not a physical accuracy claim. The impairment
sweep below reports the resolution floor explicitly.

## Calibration accuracy by SNR

Accuracy is against synthetic truth on paths classified as healthy. Lower is
better. The uncalibrated phase RMSE is 7.396 degrees for every architecture
because the same mismatch realization is used.

| Architecture | 10 dB cal phase (deg) | 30 dB cal phase (deg) | 30 dB cal gain (dB) |
|---|---:|---:|---:|
| `h2_available` | 4.511 | 4.380 | 0.052 |
| `near_field_probe` | 1.964 | 1.851 | 0.196 |
| `factory_vna_feed_table` | 0.754 | 0.285 | 0.032 |
| `proposed_switched_feed_loopback` | 0.831 | 0.467 | 0.051 |
| `ideal_16iq_nonrealizable` | 0.719 | 0.072 | 0.010 |

The H2-available phase error does not fall with SNR because the missing feed
phase is a bias, not measurement noise. Per-feed-complex architectures improve
with SNR and converge toward the simulated floor. The full four-SNR tables are
in `docs/rfcal/OBSERVABILITY_REPORT.md`.

## Calibration accuracy by mismatch

| Architecture | Mismatch 0.0 phase (deg) | Mismatch 1.0 phase (deg) | Mismatch 2.0 phase (deg) |
|---|---:|---:|---:|
| `h2_available` | 0.474 | 4.914 | 9.776 |
| `proposed_switched_feed_loopback` | 0.564 | 0.568 | 0.571 |

This is the expected identifiability signature. With no feed mismatch, the H2
chain-only estimate is nearly correct. As feed phase mismatch grows, the H2
residual grows because feed phase is not observable. The switched architecture
stays flat because it measures each feed phase.

## Scalar per-feed-IQ baseline

This is the original model assumption: 16 independent complex feed observations.
It is retained as a clearly labeled baseline, not as an available H2 measurement
path.

| Scenario | Pointing (deg) | Array gain (dB) | Sidelobe (dB) |
|---|---:|---:|---:|
| Scalar uncalibrated | 2.3705 | 12.0005 | -9.91 |
| Scalar calibrated equalized | 0.0000 | 11.9356 | -10.56 |
| Scalar calibrated phase-only | 0.0000 | 12.0970 | -10.49 |
| Scalar calibrated phase-only quantized | 0.0991 | 12.0961 | -10.46 |
| Scalar ideal | 0.0000 | 12.0412 | -10.56 |

The scalar ideal gain of 12.0412 dB is the coherent sum of 16 unit-amplitude
feeds. The vector model gives about 9.03-9.09 dB for a matched single-polarized
receiver because the 16 ports form 8 dual-polarized sites and each port receives
one orthogonal field component. The two gains are not interchangeable. The
scalar baseline must not be presented as the current H2 vector capability.

## Impairment and uncertainty results

A separate sweep adds first-order synthetic hardware errors to the switched
model. It uses 5 seeds and 3 steering angles per case (`15` samples), a
`0.01 deg` fine-search step, and a `3.0 deg` search half-span.

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

The resolution study uses an ideal calibrated beam and intentional off-grid
search windows:

| Search step (deg) | Grid bound (deg) | Pointing mean (deg) | Pointing max (deg) |
|---:|---:|---:|---:|
| 0.010 | 0.0071 | 0.0043 | 0.0044 |
| 0.050 | 0.0354 | 0.0217 | 0.0218 |
| 0.100 | 0.0707 | 0.0434 | 0.0436 |
| 0.250 | 0.1768 | 0.1086 | 0.1089 |
| 0.500 | 0.3536 | 0.2172 | 0.2178 |

The `0.0043 deg` value at a `0.010 deg` step is a numerical floor, not a
hardware accuracy. The full generated report is
`docs/rfcal/IMPAIRMENT_REPORT.md`; the compact summary is
`docs/rfcal/impairment_reference_summary.json`.

## Polarization results

- Co-pol gain is about 9.03-9.09 dB for a V-matched receiver, versus 12.0412 dB
  in the scalar 16-feed baseline.
- Cross-pol gain is about -15.91 to -16.06 dB at the base case.
- XPD is 25.000 dB because the model uses an assumed 25 dB cross-polar leakage.
  This is a parameter assumption, not a measured H1 isolation result.
- Quantization changes co-pol gain by at most about 0.001 dB. The
  per-feed-complex quantized cases have absolute pointing errors of about
  0.16-0.28 degrees; on `h2_available` quantization adds only about 0.025
  degrees because the unobserved feed-phase bias dominates.
- The vector model uses a Jones matrix per site and a receiver matched to the
  incident field. Cross-pol leakage and site-to-site leakage phase are
  configurable and labelled as assumptions.

## Fault scenarios

Each scenario removes or corrupts a chain or feed. Detection is the fraction of
runs where every affected path is classified as not healthy. False positives
count non-healthy classifications outside the affected target.

| Level | Fault | Detection rate | Mean gain loss (dB) | Mean false positives |
|---|---|---:|---:|---:|
| Chain | missing | 1.000 | 1.236-1.240 | 0.000 |
| Chain | faulty | 1.000 | 1.238-1.239 | 0.000 |
| Feed | missing | 1.000 | 0.286-0.289 | 0.000 |
| Feed | faulty | 1.000 | 0.289 | 0.000 |

These are gain-changing faults. A phase-only feed fault is invisible to the
current H2 power detectors and is not detected by `h2_available`; the
per-feed-complex and switched architectures can detect it. The unit tests cover
that distinction explicitly.

## Interpretation

1. The current H2 chain loopback plus feed detectors is insufficient for
   per-feed phase calibration. The best H2-available equalized correction,
   using chain phase/gain and feed amplitude, leaves a residual pointing error
   of about 1.25 degrees in this synthetic model.
2. A per-feed complex observation is required to remove feed phase. Factory
   VNA/reference tables, shielded near-field probes, and the proposed H3
   switched loopback all provide it; only the last is a board change.
3. The switched loopback is the strongest proposed autonomous path in the
   model because it measures one feed at a time through a shared complex
   receiver and de-embeds characterized switch/CAL paths.
4. The scalar 16-feed gain is not a valid current-H2 vector claim. Use the Jones
   model for polarization-aware gain, cross-pol, and XPD.
5. The assumed 25 dB XPD must be replaced by measured H1/H2 polarization data
   before any hardware isolation claim.
6. Fault detection/exclusion works for the tested gain-changing chain and feed
   faults. Thresholds must be re-derived from measured hardware and temperature
   data before operational use.

## Hardware integration requirements

1. **Adopt the observability boundary.** Current H2 applies relative chain
   corrections and per-feed amplitude corrections only. Do not report feed phase
   as calibrated on `h2_available`.
2. **Choose a feed-phase source.** Use a factory/bench VNA or reference receiver,
   a shielded near-field probe, or an H3 per-chain 4:1 switch/combiner from
   ADTR1107 `CPLR_OUT` to a shared complex CAL receiver.
3. **Characterize the CAL path.** Measure `K_c`, detector response, switch paths,
   couplers, and cable/LO/IF distribution versus frequency and temperature. The
   current model uses synthetic path values.
4. **Reference and LO distribution.** Repeat chain loopback after every N310
   init/retune because the N310 phase is random per start/retune.
5. **ADAR1000 qualification at 8.4 GHz.** Measure actual phase step, gain step,
   range, settling, temperature drift, and frequency dependence. Replace
   reported-constraint defaults with measured data. Do not implement register
   writes from this model without firmware validation.
6. **Fail-closed operation.** Integrate the classifier with the control plane so
   unhealthy paths are excluded or the beam is inhibited. Log path status,
   thresholds, calibration timestamp, temperature, frequency, and correction
   table with an explicit evidence label.
7. **Safety gating.** Calibration must be performed with transmit disabled or
   safely terminated, PA drain disabled where required, and any over-the-air
   radiation explicitly authorized. The model does not contain safety logic.
8. **Measured pattern validation.** Compare measured pointing, gain, sidelobe,
   polarization, and XPD against the model in a chamber or controlled range.
9. **Drift and re-calibration policy.** Define when calibration expires, how
   temperature and frequency changes trigger recalibration, and how stale or
   failed calibration data is handled.

## Reproduce

```bash
python -m openru_x6.rfcal validate --output /tmp/rfcal_validation
python -m openru_x6.rfcal audit --output /tmp/rfcal_validation/audit.json
python -m openru_x6.rfcal impairments --output /tmp/rfcal_impairments
```

Pinned container:

```bash
mkdir -p /tmp/rfcal_validation
docker run --rm -v "$PWD":/workspace -v /tmp/rfcal_validation:/out \
  -w /workspace openru-x6-sim:0.1.0 \
  python -m openru_x6.rfcal validate --output /out
```

The `validate` command writes the scalar-baseline files
(`validation.json`, `reference_summary.json`, `validation_runs.csv`,
`report.md`) and the observability files
(`observability_validation.json`, `observability_reference_summary.json`,
`observability_runs.csv`, `observability_report.md`,
`observability_audit.json`). The `impairments` command writes
`impairments.json`, `impairment_reference_summary.json`,
`impairment_runs.csv`, and `impairment_report.md`. The compact committed
summaries are `docs/rfcal/reference_summary.json`,
`docs/rfcal/observability_reference_summary.json`, and
`docs/rfcal/impairment_reference_summary.json`.

## Evidence boundary

This report supports software validation of the calibration, observability, and
polarization model only. It does not support a hardware performance, range,
regulatory, safety, polarization-isolation, or ADAR1000-at-8.4-GHz qualification
claim.
