# Observability-Aware RF Calibration Validation

**Evidence label: SIMULATED.** No hardware measurements are present.

- Topology: `openru-x6-h1-4t4r`
- Carrier: `8.400 GHz`
- Seeds: `10`, SNR levels: `4`, mismatch scales: `4`
- Beam angles: `5`
- Architectures: `h2_available, factory_vna_feed_table, near_field_probe, proposed_switched_feed_loopback, ideal_16iq_nonrealizable`
- Measured software runtime: `88.116 s`

## Hardware observability

The current H2 hardware cannot identify 16 independent feed complex responses. It can identify a relative complex chain common-path response at the CAL coupler and per-feed amplitude. Feed phase requires a factory/bench per-feed table, a shielded near-field probe, or an H3 per-feed switch/combiner.

| architecture | feed phase | realizable on H2 | needs hardware change | needs fixture |
|---|---|---|---|---|
| `h2_available` | False | True | False | False |
| `factory_vna_feed_table` | True | True | False | True |
| `near_field_probe` | True | True | False | True |
| `proposed_switched_feed_loopback` | True | False | True | False |
| `ideal_16iq_nonrealizable` | True | False | True | True |

## Base-case vector results

Base case is the configured base SNR and mismatch scale 1.0. The receiver is matched to the incident linear polarization; cross-pol is the orthogonal incident field with the same weights.

| architecture | scenario | pointing err (deg) | co-pol gain (dB) | cross-pol gain (dB) | XPD (dB) | peak sidelobe (dB) |
|---|---|---:|---:|---:|---:|---:|
| factory_vna_feed_table | chain_feed_equalized | 0.0000 | 8.9394 | -16.0606 | 25.000 | -10.54 |
| factory_vna_feed_table | chain_feed_phase_only | 0.0000 | 9.0905 | -15.9095 | 25.000 | -10.47 |
| factory_vna_feed_table | chain_feed_phase_only_quantized | 0.1818 | 9.0896 | -15.9104 | 25.000 | -10.44 |
| factory_vna_feed_table | chain_only | 1.3080 | 8.9408 | -16.0592 | 25.000 | -10.30 |
| factory_vna_feed_table | uncalibrated | 2.2915 | 9.0117 | -15.9883 | 25.000 | -9.84 |
| h2_available | chain_feed_equalized | 1.2530 | 8.9116 | -16.0884 | 25.000 | -10.34 |
| h2_available | chain_feed_phase_only | 1.2735 | 9.0651 | -15.9349 | 25.000 | -10.27 |
| h2_available | chain_feed_phase_only_quantized | 1.2981 | 9.0644 | -15.9356 | 25.000 | -10.27 |
| h2_available | chain_only | 1.3080 | 8.9408 | -16.0592 | 25.000 | -10.30 |
| h2_available | uncalibrated | 2.2915 | 9.0117 | -15.9883 | 25.000 | -9.84 |
| ideal_16iq_nonrealizable | chain_feed_equalized | 0.0000 | 8.9392 | -16.0608 | 25.000 | -10.56 |
| ideal_16iq_nonrealizable | chain_feed_phase_only | 0.0000 | 9.0905 | -15.9095 | 25.000 | -10.48 |
| ideal_16iq_nonrealizable | chain_feed_phase_only_quantized | 0.1771 | 9.0897 | -15.9103 | 25.000 | -10.43 |
| ideal_16iq_nonrealizable | chain_only | 1.2933 | 8.9433 | -16.0567 | 25.000 | -10.29 |
| ideal_16iq_nonrealizable | uncalibrated | 2.2915 | 9.0117 | -15.9883 | 25.000 | -9.84 |
| near_field_probe | chain_feed_equalized | 0.2961 | 8.9362 | -16.0638 | 25.000 | -10.45 |
| near_field_probe | chain_feed_phase_only | 0.2861 | 9.0870 | -15.9130 | 25.000 | -10.37 |
| near_field_probe | chain_feed_phase_only_quantized | 0.2766 | 9.0860 | -15.9140 | 25.000 | -10.37 |
| near_field_probe | chain_only | 1.3080 | 8.9408 | -16.0592 | 25.000 | -10.30 |
| near_field_probe | uncalibrated | 2.2915 | 9.0117 | -15.9883 | 25.000 | -9.84 |
| proposed_switched_feed_loopback | chain_feed_equalized | 0.0100 | 8.9395 | -16.0605 | 25.000 | -10.53 |
| proposed_switched_feed_loopback | chain_feed_phase_only | 0.0100 | 9.0903 | -15.9097 | 25.000 | -10.46 |
| proposed_switched_feed_loopback | chain_feed_phase_only_quantized | 0.1569 | 9.0894 | -15.9106 | 25.000 | -10.43 |
| proposed_switched_feed_loopback | chain_only | 1.3080 | 8.9408 | -16.0592 | 25.000 | -10.30 |
| proposed_switched_feed_loopback | uncalibrated | 2.2915 | 9.0117 | -15.9883 | 25.000 | -9.84 |

On `h2_available`, `chain_feed_phase_only` applies chain phase only
because a feed phase correction does not exist. The
`chain_feed_equalized` row includes per-feed amplitude correction.

## Calibration accuracy by SNR

| architecture | SNR (dB) | calibrated phase RMSE (deg) | calibrated gain RMSE (dB) | uncalibrated phase RMSE (deg) |
|---|---:|---:|---:|---:|
| factory_vna_feed_table | 10.0 | 0.7535 | 0.1073 | 7.3955 |
| factory_vna_feed_table | 20.0 | 0.3506 | 0.0447 | 7.3955 |
| factory_vna_feed_table | 30.0 | 0.2849 | 0.0316 | 7.3955 |
| factory_vna_feed_table | 40.0 | 0.2780 | 0.0297 | 7.3955 |
| h2_available | 10.0 | 4.5109 | 0.0522 | 7.3955 |
| h2_available | 20.0 | 4.3997 | 0.0522 | 7.3955 |
| h2_available | 30.0 | 4.3799 | 0.0522 | 7.3955 |
| h2_available | 40.0 | 4.3756 | 0.0522 | 7.3955 |
| ideal_16iq_nonrealizable | 10.0 | 0.7192 | 0.1010 | 7.3955 |
| ideal_16iq_nonrealizable | 20.0 | 0.2271 | 0.0319 | 7.3955 |
| ideal_16iq_nonrealizable | 30.0 | 0.0718 | 0.0101 | 7.3955 |
| ideal_16iq_nonrealizable | 40.0 | 0.0227 | 0.0032 | 7.3955 |
| near_field_probe | 10.0 | 1.9641 | 0.2253 | 7.3955 |
| near_field_probe | 20.0 | 1.8593 | 0.1999 | 7.3955 |
| near_field_probe | 30.0 | 1.8506 | 0.1962 | 7.3955 |
| near_field_probe | 40.0 | 1.8504 | 0.1955 | 7.3955 |
| proposed_switched_feed_loopback | 10.0 | 0.8309 | 0.1153 | 7.3955 |
| proposed_switched_feed_loopback | 20.0 | 0.5084 | 0.0600 | 7.3955 |
| proposed_switched_feed_loopback | 30.0 | 0.4665 | 0.0505 | 7.3955 |
| proposed_switched_feed_loopback | 40.0 | 0.4628 | 0.0491 | 7.3955 |

## Scalar per-feed-IQ baseline

This is the original model assumption: 16 independent complex feed observations. It is retained as a clearly labeled baseline, not as an available H2 measurement path.

| scenario | pointing err (deg) | array gain (dB) | peak sidelobe (dB) |
|---|---:|---:|---:|
| scalar_calibrated_equalized | 0.0000 | 11.9356 | -10.56 |
| scalar_calibrated_phase_only | 0.0000 | 12.0970 | -10.49 |
| scalar_calibrated_phase_only_quantized | 0.0991 | 12.0961 | -10.46 |
| scalar_ideal | 0.0000 | 12.0412 | -10.56 |
| scalar_uncalibrated | 2.3705 | 12.0005 | -9.91 |

## Fault scenarios

| architecture | level | fault | detection rate | mean gain loss (dB) | mean false positives |
|---|---|---|---:|---:|---:|
| factory_vna_feed_table | chain | faulty | 1.000 | 1.239 | 0.000 |
| factory_vna_feed_table | chain | missing | 1.000 | 1.240 | 0.000 |
| factory_vna_feed_table | feed | faulty | 1.000 | 0.289 | 0.000 |
| factory_vna_feed_table | feed | missing | 1.000 | 0.289 | 0.000 |
| h2_available | chain | faulty | 1.000 | 1.238 | 0.000 |
| h2_available | chain | missing | 1.000 | 1.236 | 0.000 |
| h2_available | feed | faulty | 1.000 | 0.289 | 0.000 |
| h2_available | feed | missing | 1.000 | 0.286 | 0.000 |
| ideal_16iq_nonrealizable | chain | faulty | 1.000 | 1.239 | 0.000 |
| ideal_16iq_nonrealizable | chain | missing | 1.000 | 1.240 | 0.000 |
| ideal_16iq_nonrealizable | feed | faulty | 1.000 | 0.289 | 0.000 |
| ideal_16iq_nonrealizable | feed | missing | 1.000 | 0.289 | 0.000 |
| near_field_probe | chain | faulty | 1.000 | 1.239 | 0.000 |
| near_field_probe | chain | missing | 1.000 | 1.240 | 0.000 |
| near_field_probe | feed | faulty | 1.000 | 0.289 | 0.000 |
| near_field_probe | feed | missing | 1.000 | 0.289 | 0.000 |
| proposed_switched_feed_loopback | chain | faulty | 1.000 | 1.239 | 0.000 |
| proposed_switched_feed_loopback | chain | missing | 1.000 | 1.240 | 0.000 |
| proposed_switched_feed_loopback | feed | faulty | 1.000 | 0.289 | 0.000 |
| proposed_switched_feed_loopback | feed | missing | 1.000 | 0.289 | 0.000 |

All IQ, path responses, polarization leakage, and calibration tables are synthetic. The ADAR1000 is not qualified at 8.4 GHz by this result.
