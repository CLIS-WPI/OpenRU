# H2-B Unresolved-issues register

Supersedes `H2A_UNRESOLVED_ISSUES.md` (kept for history).

**Status values:**
- **OPEN** — not done;
- **PARTIAL** — circuit drawn, but values derived or unconfirmed;
- **CLOSED** — drawn and checked against a datasheet.

## Safety (from `H2B_ELECTRICAL_SAFETY_REVIEW.md`)

| ID | Item | Status | Closes with |
|---|---|---|---|
| S1 | ADAR1000 PA/LNA OFF bias (−2.5 V / −1.96 V) vs ADTR1107 VGG abs max −2 V. **Contained** by firmware limit ≤ 0x5D plus a bench pre-check with the drains off | OPEN (contained) | ADI answer (inquiry 5a); firmware limit implemented and reviewed; bench DAC measurement |
| S2 | Negative-rail monitor U609 is a placeholder; the PA drain is not protected against −5 V collapsing first | OPEN | select a supervisor or window comparator and design the decay order |
| S3 | LNA debias at −1.75 V and TX isolation with the LNA powered | OPEN | bench (current with TR high vs low; leakage) |
| S4 | No hardware ordering of the +3.3 V / −3.3 V / −5 V rails | OPEN | regulator design with PG chaining |
| S5 | TPS3430 WDO during the VDD ramp | OPEN (low) | bench |
| S6 | 10 nF on VGG_PA slows PA_BIAS switching (≈0.65 µs or more per edge) | OPEN | ADI (inquiry 5c) or eval-board value |

## Electrical

| H2-A ID | Item | H2-B status | Note |
|---|---|---|---|
| U8 | ADF4371 loop filter | **PARTIAL** | Drawn with DERIVED values (98 kHz BW, 46° PM). Confirm in ADIsimPLL. **RS_SW still open** (ERC #1) |
| U9 | AVA-183A+ bias network | **CLOSED** (schematic) | Fig 2 values. Microstrips ML1–ML7 and pads 1, 6, 3, 4 per PL-328 are a layout item. Gain/P1dB between 5 and 8 GHz still unspecified (bench C4) |
| U20 | TPS22810 CT / QOD | **CLOSED** | TI datasheet values. Adds 1 µF CIN |
| U25 | TPS3430 timing | **CLOSED** | TI Table 6.6 |
| U11–U18 | Regulators (+3V3_RF, +5V_PA, +1V8, +3V3_LO, +5V_LO, +3V3_AUX, −5V, −3.3V) | OPEN | placeholders. ADI suggests LT8609S + LT1931 for 4 ADAR1000; ADM7150/LT3045 for the ADF4371 |
| U19 | NEG_OK monitor | OPEN | = S2 |
| U2 | ADAR1000 AVDD1/AVDD3 bypass | OPEN | not in the datasheet; needs the ADAR1000-EVALZ schematic |
| U5 | ADTR1107 VDD_PA/VDD_LNA/VDD_SW/VSS_SW bypass | OPEN | not in the datasheet; needs the ADTR1107-EVAL schematic |
| U6 | LNA supply in TX | **CLOSED as a design question** | ADI-documented combined mode (ADAR1000 Rev B p44–45); residual risk is S3 |
| U21 | INA226 address straps / shunts | OPEN (datasheet check) | TI INA226 datasheet now available locally; not yet cross-checked |
| U22 | PCA9306 VREF2/EN bias | OPEN (datasheet check) | TI PCA9306 datasheet now available locally; not yet cross-checked |
| U23 | MCU pin / alternate-function map | OPEN | STM32CubeMX |
| U24 | MCU decoupling | OPEN | ST datasheet |
| U26 | TMP117 placement | OPEN | thermal |
| U1, U3, U7, U10 | Footprints (SMA, ADAR1000, LTC5553, ADF4371, AVA-183A+, EP4RKU+; plus EDC21-24+, Mini-Circuits filters) | OPEN | vendor land patterns. Symbol pin `EP` must match the footprint pad numbering |
| U4 | Antenna / feed interface | OPEN | EM work package |
| new | ADF4371 RS_SW | OPEN | ERC #1 |
| new | U621–U624 QOD↔VOUT pin-type ERC findings | ACCEPTED (TI-sanctioned) | ERC #2–5 |
