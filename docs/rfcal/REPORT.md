# OpenRU-X6 RF Calibration Validation Report

**Evidence label: SIMULATED.** This report contains synthetic IQ and path data.
It is not a hardware measurement and does not qualify the ADAR1000 at 8.4 GHz.

## Scope

The validation exercises the hardware-independent model for the documented H1
4T4R / 16-feed topology:

- 4 RF chains, 16 feeds, 8 dual-polarized sites in a 2x4 grid.
- 8.4 GHz carrier, 17.845 mm site pitch.
- Per-feed phase and gain quantization.
- Synthetic pilot IQ with chain and feed mismatch.
- Per-path calibration, fault detection, and failed-chain scenarios.
- Beam pointing, coherent array gain, peak sidelobe, and quantization loss.

The model does not write RFIC registers, control a transmitter, or include mutual
coupling, element patterns, polarization leakage, phase noise, ADC effects, or RF
compression.

## Run configuration

| Parameter | Value |
|---|---|
| Seeds | 10 |
| SNR levels | 10, 20, 30, 40 dB |
| Mismatch scales | 0, 0.5, 1, 2 |
| Steering angles | 5 azimuth/elevation targets |
| Captures per path | 4 |
| Samples per capture | 64 |
| Beam scenarios | 5 per calibration |
| Fault seeds | 3 |
| Fault types | missing and faulty, each of 4 chains |
| Quantizer | 2.8125 deg phase, 0.5 dB gain, 31 dB range |
| Container | `openru-x6-sim:0.1.0` |
| GPU used | No |
| Measured software runtime | 17.988 s |

The run produced 4000 beam records and 24 failed-chain records. All aggregate
values are deterministic for the configured seeds; only the measured runtime
varies between executions.

## Beam results

| Scenario | n | Pointing error (deg) | Array gain (dB) | Peak sidelobe (dB) |
|---|---:|---:|---:|---:|
| Ideal geometry | 800 | 0.0000 | 12.0412 | -10.56 |
| Uncalibrated | 800 | 2.0797 | 11.9872 | -9.93 |
| Calibrated, equalized | 800 | 0.0247 | 11.8688 | -10.54 |
| Calibrated, phase-only | 800 | 0.0241 | 12.0825 | -10.45 |
| Calibrated, phase-only, quantized | 800 | 0.0843 | 12.0819 | -10.41 |

The mean phase-quantization loss for the calibrated phase-only beam is
**0.0007 dB**. The quantization model therefore has negligible beam impact
under its reported ADAR1000-style constraints.

The phase-only calibrated gain exceeds the ideal-geometry value because the
simulated path responses include amplitude mismatch and the gain metric is
normalized by applied weight power. The equalized mode intentionally reduces or
increases path amplitudes to a common target, so its normalized gain is lower.
Both modes correct phase; phase-only is the better default when coherent gain
under a total-power normalization is the objective.

## Calibration accuracy by SNR

Accuracy is measured against synthetic truth on paths classified as healthy.
Lower is better.

| SNR (dB) | Calibrated phase RMSE (deg) | Uncalibrated phase RMSE (deg) | Calibrated gain RMSE (dB) | Uncalibrated gain RMSE (dB) |
|---:|---:|---:|---:|---:|
| 10 | 0.6911 | 7.0271 | 0.1170 | 0.8216 |
| 20 | 0.2187 | 7.0083 | 0.0370 | 0.8169 |
| 30 | 0.0692 | 7.0026 | 0.0117 | 0.8155 |
| 40 | 0.0219 | 7.0008 | 0.0037 | 0.8151 |

At 30 dB per-path pilot SNR, calibration reduces phase RMSE from about 7.0
degrees to 0.069 degrees and gain RMSE from 0.82 dB to 0.012 dB.

## Calibration accuracy by mismatch scale

| Mismatch scale | Calibrated phase (deg) | Uncalibrated phase (deg) | Calibrated gain (dB) | Uncalibrated gain (dB) |
|---:|---:|---:|---:|---:|
| 0.0 | 0.2513 | 0.0378 | 0.0421 | 0.0090 |
| 0.5 | 0.2501 | 4.2265 | 0.0423 | 0.4632 |
| 1.0 | 0.2492 | 8.4521 | 0.0424 | 0.9259 |
| 2.0 | 0.2502 | 15.3224 | 0.0426 | 1.8710 |

The calibration estimate itself is noise-limited at about 0.25 degrees and
0.042 dB in this run. At zero mismatch, doing nothing is slightly better because
calibration adds estimation noise. From mismatch scale 0.5 upward, calibration
removes most of the phase and gain error.

## Failed RF-chain results

Each scenario removes or corrupts all four paths of one RF chain. Detection is
the fraction of runs where every path in the affected chain is classified as not
healthy. False positives count non-healthy classifications outside the affected
chain.

| Chain | Fault | Detection rate | Mean gain loss (dB) | Mean false positives |
|---:|---|---:|---:|---:|
| 0 | missing | 1.000 | 1.039 | 0.000 |
| 0 | faulty | 1.000 | 1.039 | 0.000 |
| 1 | missing | 1.000 | 1.224 | 0.000 |
| 1 | faulty | 1.000 | 1.224 | 0.000 |
| 2 | missing | 1.000 | 1.300 | 0.000 |
| 2 | faulty | 1.000 | 1.300 | 0.000 |
| 3 | missing | 1.000 | 1.401 | 0.000 |
| 3 | faulty | 1.000 | 1.401 | 0.000 |

The gain loss is consistent with losing roughly one quarter of the feeds. The
important result is that failed chains were detected and excluded without
flagging healthy paths in these scenarios. This is a software result, not a
hardware fault-detection guarantee.

## Interpretation

1. Phase calibration removes the dominant pointing error in the synthetic model:
   mean error falls from 2.08 degrees to about 0.024 degrees.
2. Phase-only calibration improves coherent gain and sidelobe level relative to
   uncalibrated steering in the presence of mismatch.
3. Full equalization is useful for amplitude normalization but can reduce
   normalized coherent gain; the application should choose the correction mode
   explicitly.
4. Reported ADAR1000-style quantization adds negligible gain loss and a small
   pointing quantization error.
5. Fault detection and exclusion work for the tested missing/faulty path and
   chain scenarios. Thresholds must be re-derived from measured hardware and
   temperature data before operational use.

## Hardware integration requirements

The following work is required before this model can support a hardware claim.

1. **Per-path observation path.** Add or identify per-feed couplers, a coherent
   calibration receiver, and known pilot capture. The current model assumes
   complex IQ for every feed with a shared timing reference.
2. **Reference and LO distribution.** Characterize chain-to-chain phase and gain
   from LO, IF, mixer, cable, and distribution differences. Calibration at the
   feed is not sufficient if the reference path drifts independently.
3. **ADAR1000 qualification at 8.4 GHz.** Measure the actual phase step, gain
   step, gain range, readback, settling, temperature drift, and frequency
   dependence. Replace the reported-constraint defaults with measured data. Do
   not implement register writes from this model without firmware validation.
4. **Fail-closed operation.** Integrate the classifier with the control plane so
   unhealthy paths are excluded or the beam is inhibited. Log path status,
   thresholds, calibration timestamp, temperature, frequency, and correction
   table with an explicit evidence label.
5. **Safety gating.** Calibration must be performed with transmit disabled or
   safely terminated, PA drain disabled where required, and any over-the-air
   radiation explicitly authorized. The model does not contain safety logic.
6. **Measured pattern validation.** Compare measured pointing, gain, sidelobe,
   and polarization behavior against the simulated model in a chamber or
   controlled range. Update the geometry, element pattern, mutual coupling, and
   mismatch model from those measurements.
7. **Drift and re-calibration policy.** Define when calibration expires, how
   temperature and frequency changes trigger recalibration, and how failed or
   stale calibration data is handled.

## Reproduce

From the repository root:

```bash
python -m openru_x6.rfcal validate --output results/rfcal_validation
```

Pinned container:

```bash
docker run --rm -v "$PWD":/workspace -w /workspace openru-x6-sim:0.1.0 \
  python -m openru_x6.rfcal validate --output /tmp/rfcal_validation
```

The compact generated summary is stored at
`docs/rfcal/reference_summary.json`. The full record table and calibration
example are generated by the command above and are not needed for review.

## Evidence boundary

This report supports software validation of the calibration and beamforming
model only. It does not support a hardware performance, range, regulatory,
safety, or ADAR1000-at-8.4-GHz qualification claim.
