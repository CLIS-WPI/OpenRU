# Candidate A BBM / discharge check -- BEHAVIOURAL / PRELIMINARY

Times from the instant the OD fault source asserts (S1, S2), the +5V_IL ramp starts (S3) or the glitch ends (S4).
Detection delay of the source (e.g. TPS3703 tPD <= 30 us) is NOT included; add it from the budget table.

| Scenario | corners | max overlap (us) | worst drain<0.5 V (us) | min BBM margin (us) |
|---|---|---|---|---|
| S1_odfault | 16 | 0.000 | 16.30 | 1.29 |
| S2_arm_edge | 16 | 0.000 | 13.07 | 1.29 |
| S3_il_collapse_0.01Vus | 16 | 0.000 | 128.76 | 1.29 |
| S3_il_collapse_0.05Vus | 16 | 0.000 | 38.11 | 1.29 |
| S3_il_collapse_0.1Vus | 16 | 0.000 | 27.26 | 1.29 |
| S3_il_collapse_0.3Vus | 16 | 0.000 | 20.08 | 1.29 |
| S3_il_collapse_1.0Vus | 16 | 0.000 | 17.57 | 1.29 |
| S3_il_collapse_5.0Vus | 16 | 0.000 | 16.68 | 1.28 |
| S3_il_collapse_50.0Vus | 16 | 0.000 | 16.40 | 1.29 |
| S4_glitch_0.2us | 16 | 0.000 | 0.00 | n/a |
| S4_glitch_0.5us | 16 | 0.000 | 0.00 | n/a |
| S4_glitch_1us | 16 | 0.000 | 0.00 | n/a |
| S4_glitch_2us | 16 | 0.000 | 0.00 | n/a |
| S4_glitch_5us | 16 | 0.000 | 0.00 | n/a |
| S4_glitch_20us | 16 | 0.000 | 8.09 | 1.29 |
