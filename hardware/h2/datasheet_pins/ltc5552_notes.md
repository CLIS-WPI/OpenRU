# LTC5552 datasheet facts (source: m_ltc5552.txt / m_ltc5552.pdf, doc "5552f")

All quotes are from the local datasheet text. Page = printed page number (matches PDF page index, 18 pages).

## Revision / identity
- Title: "LTC5552 3GHz to 20GHz Microwave Mixer with Wideband DC to 6GHz IF" (p1).
- Document code: "5552f" (footer, every page). Footer p18: "LT 0717 • PRINTED IN USA", "LINEAR TECHNOLOGY CORPORATION 2017". PDF metadata CreationDate Jul 13 2017.
- No revision-history table and no revision letter present in the text. Revision letter: UNRESOLVED (document appears to be the original 0717 release).

## Package (p2, p17)
- "UDB PACKAGE 12-LEAD (3mm × 2mm) PLASTIC QFN", "TJMAX = 150°C, θJC = 25°C/W", "EXPOSED PAD (PIN 13) IS GND, MUST BE SOLDERED TO PCB" (p2).
- Order part: "LTC5552IUDB#TRMPBF" / "LTC5552IUDB#TRPBF", marking "LHCK", "–40°C to 105°C" case temp (p2).
- Drawing: "LTC DWG # 05-08-1985 Rev Ø", "(UDB12) DFN 0814 REV 0" (p17).
- Pinout (p2 TOP VIEW): 1 GND, 2 IF+, 3 IF–, 4 GND, 5 RF, 6 GND, 7 EN, 8 GND, 9 VCC, 10 GND, 11 LO, 12 GND, 13 exposed pad GND.
- INCONSISTENCY (p9): Pin Functions says "GND (Pins 1, 3, 4, 6, 8, 10, 12, Exposed Pad Pin 13)" but also "IF+, IF– (Pins 2, 3)". Pin config (p2), test circuit Fig. 1 (p11), block diagram (p10) and Fig. 7 (p14) all show pin 3 = IF–. Treated pin 3 as IF– (the "3" in the GND list looks like a typo).

## Absolute maximum ratings (p2)
- "Supply Voltage (VCC)....4V"
- "Enable Input Voltage (EN)....–0.3V to VCC + 0.3V"
- "LO Input Power (1GHz to 20GHz)....+10dBm"
- "RF Power (3GHz to 20GHz)....+20dBm"
- "RF DC Voltage .... ±0.1V"
- "IF+/IF – Power (LF to 6GHz)....+20dBm"
- "IF+/IF – DC Voltage....±0.3V"
- "Operating Temperature Range (TC)....–40°C to 105°C"; "Storage Temperature Range....–65°C to 150°C"; "Junction Temperature (TJ)....150°C"
- ESD (p1): "HBM = Class 0 on Pin 11", "Class 1C All Other Pins", "CDM = 500V All Pins".

## Supply / current (p2 DC Electrical Characteristics, VCC = 3.3V, EN = High)
- Supply Voltage: min 3.0, typ 3.3, max 3.6 V (full temp).
- Supply Current, EN = High: typ 132, max 150 mA. Feature: "3.3V/132mA Supply" (p1).
- Shutdown Current, EN = Low: max 100 μA.
- p15: "A supply voltage ramp time of greater than 1ms is recommended."

## EN logic and TDD timing (p2, p9, p14)
- Input High Voltage (On): min 1.2 V (full temp). Input Low Voltage (Off): max 0.3 V (full temp).
- Input Current (–0.3V to VCC + 0.3V): min –30, max 100 μA.
- "Chip Turn-On Time" typ 0.2 μs; "Chip Turn-Off Time" typ 0.1 μs. Feature: "Fast Turn ON/OFF for TDD Operation" (p1).
- p9: "Typical input current is less than 30μA. This pin has an internal 376kΩ pull-down resistor."
- p14: "The voltage at the EN pin should never exceed VCC by more than 0.3V." "If the EN pin is left floating, its voltage will be pulled low by the internal pull-down resistor and the chip will be disabled."

## AC electrical characteristics (p3)
Conditions: "VCC = 3.3V, EN = High, PLO = 0dBm, PRF = –6dBm (–6dBm/tone for two-tone IIP3 tests)", test circuit Fig. 1 (T1 = TC1-1-13M+ standard eval config).
- LO Frequency Range 1 to 20 GHz; RF Frequency Range 3 to 20 GHz; IF Frequency Range DC to 6000 MHz.
- RF Return Loss (3–17GHz) >9 dB; LO Input Return Loss (1–20GHz) >10 dB.
- **LO Input Power (LO drive range): min –6, typ 0, max 6 dBm.**

Target RF 8.4 GHz / LO 6.6 GHz / IF 1.8 GHz: the table's spec points are RF 4/10/14/17 GHz, all at **IF = 240MHz, Low Side LO**. Nearest = RF 10 GHz. There are NO tabulated values at IF = 1.8 GHz. Curves G12/G13 (p6) and G28/G29 (p8) show CL/IIP3 vs IF at RF = 10GHz, but values cannot be read from text: UNRESOLVED (must read plots from PDF).

### Downmixer, IF = 240MHz, Low Side LO
| Parameter | Nearest point | Value |
|---|---|---|
| Conversion Loss | RF Input = 10GHz | 8.0 dB (4GHz: 6.9 dB) |
| IIP3 (ΔfRF = 2MHz) | RF Input = 10GHz | 22.5 dBm (4GHz: 23.8 dBm) |
| Input 1dB Compression | RF Input = 10GHz | 14.6 dBm |
| SSB Noise Figure | RF Input = 10GHz | 9.8 dB (15.7GHz: 11.7 dB) |
| LO to RF Input Leakage | fLO = 1–20GHz | <–24 dBm |
| LO to IF Leakage | fLO = 1–20GHz | <–19 dBm |
| RF to LO Isolation | fRF = 3–20GHz | >53 dB |
| RF Input to IF Output Isolation | fRF = 3–20GHz | >34 dB |
| CL vs Temperature | RF 10GHz | 0.007 dB/°C |

### Upmixer, IF = 240MHz, Low Side LO
| Parameter | Nearest point | Value |
|---|---|---|
| Conversion Loss | RF Output = 10GHz | 8.6 dB (4GHz: 7.0 dB) |
| IIP3 (ΔfIF = 2MHz) | RF Output = 10GHz | 21.1 dBm (4GHz: 24.6 dBm) |
| Input 1dB Compression | RF Output = 10GHz | 14.5 dBm |
| SSB Noise Figure | RF Output = 10GHz | 9.9 dB (15.7GHz: 11.5 dB) |
| LO to RF Output Leakage | fLO = 1–20GHz | <–24 dBm |
| LO to IF Input Leakage | fLO = 1–20GHz | <–19 dBm |
| IF to LO Isolation | fIF = 500MHz to 9GHz | >60 dB |
| IF Input to RF Output Isolation | fIF = 500MHz to 9GHz | >33 dB |
| CL vs Temperature | RF Output = 5.8GHz | 0.007 dB/°C |

Note 3 (p3): "SSB noise figure measurements performed with a small-signal noise source, bandpass filter and 2dB matching pad on input, with bandpass filters on LO, and output."
p16: datasheet performance includes eval-board trace/SMA insertion loss, "not de-embedded" (Fig. 10/11).

## IF port: differential, balun, matching
- p9: "IF+, IF– (Pins 2, 3): Differential Terminals for the IF. These pins may be used for a differential IF or connected to an external balun if a single-ended IF port is needed. The IF port can be used from DC up to 6GHz depending on the external balun bandwidth. DC voltages at IF+ and IF– are 0V."
- p12: "The RF and LO are single-ended 50Ω ports. The IF is differential. An external balun is needed if a single-ended IF signal is desired."
- p14: "ESD protection diodes are connected to both of these ports. The single-ended impedance of each of the IF+ and IF– terminals is approximately 25Ω in parallel with 0.25pF. An external 1:1 balun is required for a 50Ω single-ended IF. Using a TC1-1-13M+ balun, for example, the IF port is broadband matched from 4.5MHz to 3GHz, when the LO is applied. For higher frequency IF operation, up to 6GHz, the TCM1-83X+ balun is recommended."
- Fig. 1 test circuit BOM (p11): "T1  TC1-1-13M+*  Mini Circuits  IF = 4.5MHz to 3GHz"; "TCM1-83X+  Mini Circuits  IF = 10MHz to 6GHz"; "* Standard Evaluation Board Configuration". No other IF matching components shown (balun directly on pins 2/3; IF 50Ω).
- Eval board DC-number (DCxxxx): NOT present in the datasheet text. UNRESOLVED. (Fig. 2 "Evaluation Board Layout" is an image only.)
- For IF = 1.8 GHz both baluns are in-band per the stated ranges.

## DC blocking / DC conditions
- RF (p9): "internally connected to the primary side of the RF transformer, which has low DC resistance to ground. A series DC blocking capacitor must be used to avoid damage to the integrated transformer if DC voltage is present."
- RF (p12): "The primary side of the RF transformer is DC–grounded internally and the DC resistance of the primary side is approximately 2.5Ω. A DC blocking capacitor is needed if the RF source has DC voltage present." Abs max RF DC ±0.1V. Fig. 1 shows NO RF DC-block cap (RF 50Ω direct to pin 5).
- LO (p9): "A series DC blocking capacitor must be used. Typical DC voltage at this pin is 1.6V." (p13): "A DC blocking capacitor (C1) is required." C1 = 18pF.
- IF: "DC voltages at IF+ and IF– are 0V" (p9); abs max IF DC ±0.3V. The datasheet does not state whether IF pins are internally DC-blocked, nor require a DC-ground/bias; no IF DC-block capacitors appear in Fig. 1 (TC1-1-13M+ / TCM1-83X+ connected directly). Whether a DC path through the balun is required: UNRESOLVED (not stated). Inference only (not a datasheet statement): external DC on IF must be kept within ±0.3V.
- RF port matching option (p12): "A 0.15pF shunt capacitor located 1.4mm away from the RF pin can be used to improve the RF port matching between 13GHz to 15GHz." "LO power between –6dBm and 6dBm is required for good RF impedance matching."
- LO (p13): "The LO is 50Ω matched from 1GHz to 20GHz." "no ESD protection devices are used at the LO input. As a result, the LO is the most sensitive pin to ESD stress for the mixer."

## Typical application / test circuit components (p11 Fig. 1)
| Ref | Value | Size | Vendor | P/N / comment |
|---|---|---|---|---|
| C1 (LO DC block) | 18pF | 0402 | AVX | 0402ZK180GBS |
| C2 (VCC bypass) | 18pF | 0402 | Murata | GJM1555C1H180FB01 |
| C3 (VCC bypass) | 1µF | 0603 | Murata | GRM188R71A105KA61 |
| T1 (IF balun) | TC1-1-13M+* | – | Mini Circuits | IF = 4.5MHz to 3GHz |
| T1 alt | TCM1-83X+ | – | Mini Circuits | IF = 10MHz to 6GHz |
VCC "(3.0V TO 3.6V)". C2/C3 role as VCC bypass inferred from schematic placement next to VCC (pin 9).
p18 Typical Application "Wideband Upconversion to 7.5GHz": TCM1-83X+ balun on IF (10MHz TO 6GHz), LO "7.51GHz to 13.5GHz" through 18pF, RF 7.5GHz.
p1 Typical Application: TX/RX block diagram (LNA, PA, duplexer), no component values.

## LTC5552 vs LTC5553 — verbatim sentences
- p1: "The device is similar to the LTC5553, but with a broadband, differential DC to 6GHz IF port. The LTC5552 is recommended for applications where the IF frequency range extends below 500MHz. For applications where the IF frequency is always above 500MHz, the LTC5553 is recommended, since it includes an integrated IF balun."
- (Plot label "5553 G02" on p4 is a figure ID artifact, not a comparison.)

## Related parts entry for LTC5553 (p18, verbatim)
"LTC5553        3GHz to 20GHz Microwave Mixer                         9dB Conversion Loss, 24dBm IIP3, 500MHz to 9GHz Single-Ended IF with Integrated Balun"
