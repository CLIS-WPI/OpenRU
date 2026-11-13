# Hardware Impairment and Uncertainty Validation

**Evidence label: SIMULATED.** No hardware measurements are present.

This report adds first-order reference drift, switch leakage, phase noise,
mutual coupling, and correlated calibration errors to the observable
chain/feed model. It reports dispersion across seeds, not only a mean.

- Topology: `openru-x6-h1-4t4r`
- Carrier: `8.400 GHz`
- Seeds: `5`; beam angles: `3`
- Fine-search step: `0.010 deg`; span: `3.000 deg`
- Cases: `12`
- Runtime: `32.017 s`

## Uncertainty by case

Every row is the spread over seeds and steering angles. `p95` is the
95th percentile; `max` is the worst case in this synthetic ensemble.

| case | architecture | n | pointing mean (deg) | pointing std (deg) | pointing p95 (deg) | pointing max (deg) | cal phase mean (deg) | cal phase std (deg) | cal gain mean (dB) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| combined_moderate | proposed_switched_feed_loopback | 15 | 0.5619 | 0.2215 | 0.9319 | 0.9319 | 4.2570 | 0.9890 | 0.8118 |
| correlated_chain_0p5deg | proposed_switched_feed_loopback | 15 | 0.1030 | 0.0206 | 0.1393 | 0.1393 | 0.5879 | 0.0929 | 0.0540 |
| h2_no_impairment | h2_available | 15 | 1.4296 | 0.5534 | 2.0310 | 2.0402 | 4.9716 | 0.4996 | 0.0521 |
| h3_no_impairment | proposed_switched_feed_loopback | 15 | 0.0771 | 0.0300 | 0.1334 | 0.1334 | 0.4987 | 0.0742 | 0.0540 |
| mutual_coupling_20db | proposed_switched_feed_loopback | 15 | 0.7689 | 0.4935 | 1.6930 | 1.6943 | 9.0357 | 1.8373 | 1.8045 |
| mutual_coupling_30db | proposed_switched_feed_loopback | 15 | 0.1736 | 0.0558 | 0.2807 | 0.2807 | 1.5682 | 0.4096 | 0.3521 |
| phase_noise_2deg | proposed_switched_feed_loopback | 15 | 0.6335 | 0.3442 | 1.1309 | 1.1336 | 2.1244 | 0.2558 | 0.0540 |
| phase_noise_common_2deg | proposed_switched_feed_loopback | 15 | 0.0771 | 0.0300 | 0.1334 | 0.1334 | 0.4987 | 0.0742 | 0.0540 |
| reference_drift_0p5deg | proposed_switched_feed_loopback | 15 | 0.2387 | 0.2009 | 0.6123 | 0.6129 | 0.6871 | 0.2417 | 0.0721 |
| reference_drift_common_0p5deg | proposed_switched_feed_loopback | 15 | 0.0771 | 0.0300 | 0.1334 | 0.1334 | 0.4987 | 0.0742 | 0.0540 |
| switch_leakage_20db_one_at_a_time | proposed_switched_feed_loopback | 15 | 0.0771 | 0.0300 | 0.1334 | 0.1334 | 0.4987 | 0.0742 | 0.0540 |
| switch_leakage_20db_simultaneous | proposed_switched_feed_loopback | 15 | 0.8463 | 0.1351 | 1.0582 | 1.0645 | 4.0681 | 0.1456 | 0.6350 |

## Angular-search resolution

The ideal calibrated beam is evaluated on intentional off-grid search
windows offset by fixed fractions of each step. The grid bound is
`step * sqrt(2) / 2` in two dimensions. Values scale with the search
step and are not a statement of physical accuracy.

| search step (deg) | grid bound (deg) | n | pointing mean (deg) | pointing max (deg) |
|---:|---:|---:|---:|---:|
| 0.0100 | 0.0071 | 2 | 0.0043 | 0.0044 |
| 0.0500 | 0.0354 | 2 | 0.0217 | 0.0218 |
| 0.1000 | 0.0707 | 2 | 0.0434 | 0.0436 |
| 0.2500 | 0.1768 | 2 | 0.1086 | 0.1089 |
| 0.5000 | 0.3536 | 2 | 0.2172 | 0.2178 |

## Findings

1. The previously reported `0.01 deg` switched-loopback result is at or
   below the configured `0.25 deg` search step. It is a grid/model floor,
   not a measured or guaranteed physical pointing accuracy.
2. Common-mode reference drift and common-mode phase noise do not change
   relative pointing or relative calibration accuracy. They are a global
   phase/gain offset that is normalized out here. Independent and per-chain
   terms are the pointing-relevant errors.
3. Switch leakage is only first order when multiple feeds on one switch are
   active. A one-feed-at-a-time sequence suppresses that term; finite
   isolation and settling must still be measured on hardware.
4. Mutual coupling is not observed by an ADTR1107 `CPLR_OUT` tap. It must be
   characterized separately or included in a near-field/OTA calibration.
5. Every value here is synthetic. Use the same distributions only as a
   test harness; replace the parameters with measured distributions.

All IQ, path responses, coupling values, and calibration tables are synthetic.
The ADAR1000 is not qualified at 8.4 GHz by this result.
