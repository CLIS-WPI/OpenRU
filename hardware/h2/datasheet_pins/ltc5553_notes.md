# LTC5553 datasheet notes (source: ds/m_ltc5553.txt / m_ltc5553.pdf, 16 pages)

Page numbers are the printed datasheet page numbers, which match the PDF page numbers.

## Identity
- Title: "LTC5553 3GHz to 20GHz Microwave Mixer" (p1)
- Revision/footer code: "5553f" on every page. Back page: "LT 0417 • PRINTED IN USA", "LINEAR TECHNOLOGY CORPORATION 2017" (p16). The PDF is from a mirror stamped "Downloaded from Arrow.com."
- Package: "3mm × 2mm, 12-Lead QFN Package" (p1); "UDB PACKAGE 12-LEAD (3mm × 2mm) PLASTIC QFN", "TJMAX = 150°C, θJC = 25°C/W", "EXPOSED PAD (PIN 13) IS GND, MUST BE SOLDERED TO PCB" (p2). Drawing: "LTC DWG # 05-08-1985 Rev Ø", "(UDB12) DFN 0814 REV 0" (p15)
- Order: LTC5553IUDB#TRMPBF / LTC5553IUDB#TRPBF, marking "LGZX", –40°C to 105°C case (p2)
- ESD: "HBM = Class 0 on Pin 11", "Class 1C All Other Pins", "CDM = 500V All Pins" (p1). Pin 11 is LO, and Class 0 is the most sensitive HBM class.
- Description (p1): "integrated LO amplifier optimized for the 1GHz to 20GHz frequency range, requiring only 0dBm drive. The integrated IF balun is optimized to cover a very wide, 500MHz to 9GHz, frequency range while providing a single-ended 50Ω interface."

## Pin map (p2 pin configuration, p8 Pin Functions)
1 GND, 2 IF, 3 GND, 4 GND, 5 RF, 6 GND, 7 EN, 8 GND, 9 VCC, 10 GND, 11 LO, 12 GND, 13 = exposed pad, GND

## Absolute Maximum Ratings (p2)
- "Supply Voltage (VCC)...4V"
- "Enable Input Voltage (EN)...–0.3V to VCC + 0.3V"
- "LO Input Power (1GHz to 20GHz)...+10dBm"
- "LO Input DC Voltage...±0.1V"
- "RF Power (3GHz to 20GHz)...+20dBm"
- "RF DC Voltage...±0.1V"
- "IF Power (500MHz to 9GHz)...+20dBm"
- "IF DC Voltage...±0.1V"
- Operating TC –40°C to 105°C; storage –65°C to 150°C; TJ 150°C
- Note: the LO pin sits at about 1.6V DC internally (p8, p11), but the LO abs-max DC is ±0.1V. This is consistent only if the ±0.1V limit applies to the external source side of the required DC block. The datasheet does not say so explicitly; this is my interpretation.

## DC Electrical Characteristics (p2; VCC = 3.3V, EN = High, TC = 25°C)
- Supply Voltage: 3.0 min / 3.3 typ / 3.6 max V
- Supply Current, EN = High: 132 typ / 150 max mA
- Shutdown Current, EN = Low: 100 μA max (no typical value given)
- EN Input High Voltage (On): 1.2 V min. EN Input Low Voltage (Off): 0.3 V max
- EN Input Current (–0.3V to VCC + 0.3V): –30 min / 100 max μA. Pin Functions says "Typical input current is less than 30μA." (p8)
- Chip Turn-On Time 0.2 μs typ; Chip Turn-Off Time 0.1 μs typ
- EN pull-down: "This pin has an internal 376kΩ pull-down resistor." (p8). "If the EN pin is left floating, its voltage will be pulled low by the internal pull-down resistor and the chip will be disabled." (p13)
- Supply ramp: "A supply voltage ramp time of greater than 1ms is recommended." (p13)

## AC Electrical Characteristics (p3)
Conditions: VCC = 3.3V, EN = High, PLO = 0dBm, PRF = –6dBm (–6dBm/tone for two-tone tests), TC = 25°C, Figure 1 circuit.
- LO Frequency Range: 1 to 20 GHz. RF Frequency Range: 3 to 20 GHz. IF Frequency Range: 500 to 9000 MHz
- RF Return Loss (ZO = 50Ω, 3GHz to 17GHz): >9 dB
- LO Input Return Loss (ZO = 50Ω, 1GHz to 20GHz): >10 dB
- LO Input Power: –6 min / 0 typ / 6 max dBm
- **Only one IF frequency is tabulated: IF = 1890MHz, Low Side LO.** The table has no high-side-LO rows and no other IF frequencies.

### Downmixer Application, IF = 1890MHz, Low Side LO (all typical)
| Parameter | Condition | Value |
|---|---|---|
| Conversion Loss | RF = 4GHz | 8.2 dB |
| | RF = 10GHz | 9.0 dB |
| | RF = 14GHz | 11.3 dB |
| | RF = 17GHz | 11.6 dB |
| CL vs Temperature | TC = –40 to 105°C, RF = 9.8GHz | 0.006 dB/°C |
| 2-Tone IIP3 (ΔfRF = 2MHz) | RF = 4GHz | 27.6 dBm |
| | RF = 10GHz | 24.3 dBm |
| | RF = 14GHz | 23.9 dBm |
| | RF = 17GHz | 21.5 dBm |
| SSB NF | RF = 10GHz | 10.9 dB |
| | RF = 15.7GHz | 12.8 dB |
| LO to RF Leakage | fLO = 1–20GHz | <–23 dBm |
| LO to IF Leakage | fLO = 1–20GHz | <–13 dBm |
| RF to LO Isolation | fRF = 3–20GHz | >40 dB |
| RF Input to IF Output Isolation | fRF = 3–20GHz | >32 dB |
| Input 1dB Compression | RF = 10GHz | 16 dBm |

### Upmixer Application, IF = 1890MHz, Low Side LO (all typical)
| Parameter | Condition | Value |
|---|---|---|
| Conversion Loss | RF Out = 4GHz | 8.3 dB |
| | RF Out = 10GHz | 9.3 dB |
| | RF Out = 14GHz | 11.9 dB |
| | RF Out = 17GHz | 11.5 dB |
| CL vs Temperature | TC = –40 to 105°C, RF Out = 5.8GHz | 0.006 dB/°C |
| 2-Tone IIP3 (ΔfIF = 2MHz) | RF Out = 4GHz | 27.2 dBm |
| | RF Out = 10GHz | 25.6 dBm |
| | RF Out = 14GHz | 21.2 dBm |
| | RF Out = 17GHz | 17.3 dBm |
| SSB NF | RF Out = 10GHz | 10.1 dB |
| | RF Out = 15.7GHz | 12.1 dB |
| LO to RF Output Leakage | fLO = 1–20GHz | <–25 dBm |
| LO to IF Input Leakage | fLO = 1–20GHz | <–26 dBm |
| IF to LO Isolation | fIF = 500MHz–9GHz | >50 dB |
| IF to RF Isolation | fIF = 500MHz–9GHz | >40 dB |
| Input 1dB Compression | RF Out = 10GHz | 14.8 dBm |

- Note 3 (p3): "SSB noise figure measurements performed with a small-signal noise source, bandpass filter and 2dB matching pad on input, with bandpass filters on LO, and output."
- Feature list (p1) says "Low LO-RF Leakage: <–25dBm". This matches the upmixer row. The downmixer row is <–23dBm.
- The datasheet performance includes eval-board and SMA losses, which are not de-embedded: "The insertion loss of the board traces and SMA connectors are not de-embedded" (p14, Fig 10/11).

## Port details
### IF (pin 2)
- "Single-Ended Terminal for the IF Port. This pin is internally connected to the primary side of the IF transformer, which has low DC resistance to ground. A series DC blocking capacitor should be used to avoid damage to the integrated transformer if DC voltage is present. The IF port is impedance matched from 500MHz to 9GHz, as long as the LO is driven with a 0 ±6dBm source between 1GHz and 20GHz." (p8)
- "The primary side of the IF transformer is DC-grounded internally and the DC resistance is approximately 6.2Ω. A DC blocking capacitor is needed if the IF source has DC voltage present." (p12)
- DC level: DC-grounded through about 6.2Ω, so roughly 0V. No DC blocking is internal; the blocking cap is external and needed only if DC is present. Figure 1 has **no** IF DC block.
- Table 3 (p12, at Pin 2, no external matching): 1.5GHz 66.5 – j6.3 (|S11| 0.15); 2.0GHz 45.5 – j16.8 (|S11| 0.18, angle printed as "95.0", which looks like a sign/typo anomaly — UNRESOLVED); 1.0GHz 58.3 + j36.2 (0.33); 0.5GHz 16.0 + j30.4 (0.63).
- IF return loss: shown in Figure 8 (p12). I did not read values from it.

### RF (pin 5)
- "A series DC blocking capacitor must be used to avoid damage to the integrated transformer if DC voltage is present. The RF port is impedance matched from 3GHz to 20GHz as long as the LO is driven with a 0 ±6dBm source between 1GHz and 20GHz." (p8)
- "The primary side of the RF transformer is DC–grounded internally and the DC resistance of the primary side is approximately 2.5Ω. A DC blocking capacitor is needed if the RF source has DC voltage present." (p10)
- "A 0.15pF shunt capacitor located 1.4mm away from the RF pin can be used to improve the RF port matching between the 13GHz to 15GHz frequency range." (p10)
- Table 1 (p11, Pin 5, LO driven at 12GHz): 8GHz 54.1 – j1.7 (|S11| 0.04); 9GHz 52.7 – j7.3 (0.08)
- Figure 1 has **no** RF DC block. The datasheet wording is inconsistent here: "must be used ... if DC voltage is present" on p8 versus "needed if" on p10.

### LO (pin 11)
- "Input for the Local Oscillator (LO). A series DC blocking capacitor must be used. Typical DC voltage at this pin is 1.6V." (p8)
- "The DC voltage at the LO input is about 1.6V. A DC blocking capacitor (C1) is required." (p11)
- "The LO is 50Ω matched from 1GHz to 20GHz. External matching components may be needed for extended LO operating frequency range." "The nominal LO input level is 0dBm, although the limiting amplifiers will deliver excellent performance over a ±6dBm input power range." (p11)
- Table 2 (p12, with C1 = 18pF): 6GHz 46.7 – j9.5 (0.10); 7GHz 44.4 – j13.3 (0.15)

### VCC (pin 9)
- "must be externally connected to a regulated 3.3V supply, with a bypass capacitor located close to the pin. Typical current consumption is 132mA when the part is enabled." (p8)

## Test circuit, Figure 1 "Standard Test Circuit Schematic" (p9)
- RF (pin 5) goes directly to a 50Ω connector, and IF (pin 2) goes directly to a 50Ω connector; neither has a capacitor.
- LO (pin 11) goes through C1 to the LO 50Ω input.
- C2 and C3 shunt VCC (pin 9) to GND. The supply is labelled "VCC (3.0V TO 3.6V)". EN (pin 7) is a direct wire. Pins 1, 3, 4, 6, 8, 10, 12 and 13 are GND.
- BOM:
  - C1 18pF 0402 AVX "0402ZK180GBS"
  - C2 18pF 0402 Murata "GJM1555C1H180FB01"
  - C3 1µF 0603 Murata "GRM188R71A105KA61"
- Footnote "* Standard Evaluation Board Configuration": no table row carries an asterisk in the render.
- Eval board: there is only "Figure 2. Evaluation Board Layout" (p10). **No DC-number (demo board number) is printed anywhere.** UNRESOLVED.
- Typical application (p16) "Wideband Downconversion to 6GHz": 7GHz to 16GHz RF in, ZO = 50Ω / L = 1.4mm line with shunt C (OPEN or 0.15pF); 18pF LO cap; "1GHz to 10GHz" LO; 6GHz IF.

## LTC5552 comparison
- The text contains **no sentence mentioning LTC5552**; grep for "5552" returns nothing. The related-parts list (p16) contains LTC5548, LTC5549, LTC5544, LTC5576, LTC5551, LTC5567, LTC5577, LTC5510, LTC5586, LTC5588-1 and others, but not LTC5552.

## Spurs (p13)
- Table 4a (downconversion: RF 5250MHz, LO 4900MHz) and Table 4b (upconversion: RF 5835MHz, IF 1890MHz, LS LO): see p13. These are not at our frequencies.

## Plot reads relevant to RF 8.4 GHz / IF 1.8 GHz / LO 6.6 GHz (low side)
All values below are [plot read, approximate]. They were read from 400-dpi renders, and the accuracy is about ±0.3–0.5 dB.
- G09 "Conversion Loss and IIP3 vs IF Frequency (Low Side LO)", downmixer, p6. Curve RF = 9.8GHz LS LO, at IF ≈ 1.8GHz: CL ≈ 8.7 dB, IIP3 ≈ 24.1 dBm. CL rises sharply below about 1GHz IF (≈ 11.5 dB at 0.5GHz) and stays at about 8.6–9.3 dB from 1.3 to 3.5GHz IF. No curve is given at RF 8.4GHz.
- G03 downmix CL/IIP3 vs RF (LS LO, IF 1890MHz), p5. At RF ≈ 8.4GHz, 25°C: CL ≈ 8.0 dB, IIP3 ≈ 23.5 dBm. IIP3 has a local dip of about 23.4 dBm near 8.5–9GHz.
- G10 downmix Input P1dB vs RF, p6. At 8.4GHz LS LO: ≈ 16.2 dBm.
- G11 LO Leakage vs LO frequency, p6. At LO ≈ 6.6GHz: LO–RF ≈ –25 dBm (the curve has a local peak there, on a steep slope), LO–IF ≈ –32 dBm. Confidence is low because the slope is steep.
- G12 RF Isolation vs RF, p6. At 8.4GHz: RF–LO ≈ 59 dB, RF–IF (LS LO) ≈ 54 dB (near the peak).
- G21 upmixer "Conversion Loss and IIP3 vs IF Frequency (Low Side LO)", p7. RF = 9.8GHz LS at IF 1.8GHz: CL ≈ 10.0 dB, IIP3 ≈ 25 dBm. The y-axis tick labels were cropped, so the scale was inferred from the p7 text (8 to 30 in 2 dB steps).
- G22 upmixer "Input P1dB vs IF Frequency", p7. At IF 1.8GHz: LS LO ≈ 14.8 dBm.
- G23 upmixer "IF Isolation", p7. At IF 1.8GHz: IF–LO ≈ 67 dB, IF–RF ≈ 41 dB.
- RF port return-loss plots, Fig 4 (p10), exist for IF = 900MHz, 2GHz and 4GHz. I did not read values from them.

## UNRESOLVED
- Eval board DC-number: not in the datasheet.
- LTC5552 comparison: not in the datasheet.
- Table 3 at 2.0GHz: the S11 angle "95.0" is inconsistent with the impedance 45.5 – j16.8, which implies a negative angle. Probably a typo.
- RF DC block: the p8 wording is "must be used ... if DC voltage is present", but Figure 1 omits it. Treat it as conditional on the source having DC.
