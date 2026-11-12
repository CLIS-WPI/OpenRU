# Passives / LO buffer: datasheet facts (8.4 GHz RF / 1.8 GHz IF / 6.6 GHz LO)

How these were read: each PDF was fetched with WebFetch from minicircuits.com/pdfs/<PART>.pdf and its text pulled out locally with pdftotext.
Pin tables are quoted exactly as printed. Rev, ECO and date code come from the footer (YYMMDD).

## VERIFIED

### 1. BFCN-8350+ (LTCC bandpass, 8250-8450 MHz)
- URL: https://www.minicircuits.com/pdfs/BFCN-8350+.pdf. REV. D, M151107, footer date code 190725.
- CASE STYLE: FV1206-4 (3.20 x 1.60 mm). Demo board TB-518+, PCB layout PL-305.
- Pin Connections:
  RF IN    1
  RF OUT   3
  GROUND   2,4
- Passband 8250-8450 MHz, Fc 8350 MHz. IL 1.8 dB typ, 3.5 dB max over 8250-8450. VSWR 1.4 typ.
- Stop band, lower: DC-7300 MHz, 18 dB typ IL. Stop band, upper: 10300-15050 MHz, 18 dB typ.
- RF Power Input: 2 W max at 25 °C (passband rating), derated linearly to 0.5 W at 100 °C.
- Not a DC block (note 2): blocking caps are needed if DC is present.
- Typical data (MHz: IL dB / VSWR):
  100: 49.29 / 1737.18 | 800: 31.37 / 289.53 | 1500: 26.27 / 124.09 | 2200: 23.55 / 78.97
  3600: 21.00 / 52.65 | 4300: 20.28 / 42.38 | 6050: 20.00 / 40.41 | 6750: 23.97 / 37.77
  7200: 31.32 / 25.94 | 7400: 18.52 / 17.22 | 8250: 1.75 / 1.29 | 8450: 1.78 / 1.36
  9550: 19.49 / 13.92 | 11050: 19.69 / 7.66 | 15050: 23.94 / 8.23
- No rows at exactly 1800, 4800, 6600 or 8400 MHz. Nearest points: 1500/2200 (26.3/23.6 dB); 4300/6050 (20.3/20.0 dB);
  6050/6750 (20.0/24.0 dB). The guaranteed figure at the LO and image is only "DC-7300 = 18 dB typ" (no min given).
  The IL at 8350-8450 is not tabulated separately: 1.8 typ / 3.5 max over the band, 1.78 dB measured at 8450.

### 2. HFCN-7150+ (LTCC high-pass)
- URL: https://www.minicircuits.com/pdfs/HFCN-7150+.pdf. REV. J, ECO-023938, date code 250702.
- CASE STYLE: FV1206-1 (3.20 x 1.60 mm). Marking "ZR". Demo board TB-HFCN-7150+, PCB layout PL-158.
- PIN CONNECTIONS:
  RF IN    1
  RF OUT   3
  GROUND   2,4,5,6
- Passband 7900-11000 MHz: IL 2.0 dB max; 8500-10500 MHz: IL 1.5 dB max. Cutoff 7150 MHz (3.0 dB typ).
- Stopband rejection: 5100 MHz, 30 dB typ; 6150 MHz, 20 dB min.
- RF power: 6 W max at 25 °C, derated to 3 W at 100 °C.
- Typical data (MHz: IL dB): 50: 59.58 | 1000: 35.04 | 2800: 28.81 | 4540: 38.96 | 5100: 29.87 | 6150: 23.72
  | 6650: 18.85 | 7020: 4.74 | 7150: 2.97 | 7250: 2.31 | 7900: 1.46 | 8500: 1.24 | 10500: 0.92 | 11000: 0.82 | 12000: 1.37 | 15000: 3.95 | 18000: 5.64
- At the 6.6 GHz LO: about 18.85 dB (6650 MHz row). At 4.8 GHz: no exact row; the 4540 and 5100 MHz rows give 38.96 and 29.87 dB.

### 3. IF bandpass: BFCN-1840+ is the best match (1750-1930 MHz covers 1.75-1.85 GHz)
- URL: https://www.minicircuits.com/pdfs/BFCN-1840+.pdf. REV. E, M151107, date code 190725.
- CASE STYLE: FV1206. Demo board TB-270, PCB layout PL-137.
- Pin Connections:
  RF IN    1
  RF OUT   3
  GROUND   2,4
- Passband 1750-1930 MHz, Fc 1840 MHz. IL 3.0 dB max (2.0 dB typ per "Big Deal"). VSWR 2.5 max.
- Stop band: DC-1460 MHz, 20 dB typ; 3500-5700 MHz, 25 dB typ. RF power 1.5 W max at 25 °C (0.25 W at 100 °C).
- Typical data (MHz: IL dB): 100: 23.50 | 300: 30.09 | 1000: 35.23 | 1300: 45.92 | 1450: 24.19 | 1750: 2.09 | 1880: 1.73 |
  1950: 2.28 | 2850: 21.69 | 3400: 29.13 | 3800: 36.64 | 4100: 50.84 | 5100: 34.05 | 5700: 31.08
- 4.8 GHz: no exact row (4100 = 50.84 dB, 5100 = 34.05 dB). 6.6 GHz and 8.4 GHz: NOT TABULATED (the data stops at 5700 MHz).
- Part existence: BFCN-1800+ returned 404 (does not exist). BFCN-1840+, BFCN-1855+ and BFCN-1860+ exist.
- Alternatives that were read:
  - BFCN-1855+: 1790-1920 MHz, so it does NOT cover 1750. FV1206, pins RF IN 1 / RF OUT 3 / GROUND 2,4. REV. D. 4800 MHz IL is 39.10 dB.
    https://www.minicircuits.com/pdfs/BFCN-1855+.pdf
  - BFCN-1860+: 1580-2200 MHz, wider. CASE FV1206-4, pins RF IN 1 / RF OUT 3 / GROUND 2,4. REV. D, ECO-031453, 261006.
    IL 2.0 typ / 3.5 max; at 1750-1850 MHz it measures 1.56-1.53 dB. 4800 MHz: 30.01 dB. Upper stop band 2600-4800 MHz, 20 dB typ. 2.5 W.
    https://www.minicircuits.com/pdfs/BFCN-1860+.pdf

### 4. 4-way 0° splitter: EP4RKU+ (DC-18 GHz) covers BOTH the 6.6 GHz LO and the 8.35-8.45 GHz cal network
- URL: https://www.minicircuits.com/pdfs/EP4RKU+.pdf. REV. C, ECO-028633, date code 260302.
- CASE STYLE: DG1677-2, a 5x5 mm plastic QFN-style package with exposed paddle. PCB layout PL-649. Eval boards TB-EP4RKU+ and TB-EP4RKUC+.
- PAD CONNECTIONS:
  SUM PORT   21
  PORT 1     14
  PORT 2     10
  PORT 3     31
  PORT 4     27
  GROUND     9,11,13,15,20,22,26,28,30,32 and Paddle
  NOT USED, GROUND EXTERNALLY   1-8, 12, 16-19, 23-25, 29
- Specs for the 4-18 GHz band, which holds both 6.6 and 8.4 GHz:
  - IL above 6.0 dB: 3.4 typ / 4.9 max (so about 9.4 dB total typ)
  - Isolation: 11 min / 18.8 typ
  - Phase unbalance: 1.9° typ / 19° max
  - Amplitude unbalance: 0.2 typ / 1.2 max dB
  - VSWR: S 1.4, ports 1.5
- Power: 3.1 W max as a splitter; 1.5 W per port as a combiner.
- Caveat: the datasheet's "Product Overview" paragraph says "10.7 to 31 GHz", which contradicts the title and spec table (DC-18 GHz).
  It looks like a copy-paste error; the spec table is authoritative.
- Searched for a narrowband, lower-loss 4-way SMT part covering 6.6 or 8.4 GHz from Mini-Circuits and found none
  (SCA-4-10+ is 5-1000 MHz; EP4KA+ is 10.7-31 GHz per search snippet, not read).

### 5. Directional coupler: EDC21-24+ (MMIC, 21 dB, 4-20 GHz)
- URL: https://www.minicircuits.com/pdfs/EDC21-24+.pdf. REV. A, ECO-012570, date code 250904.
- CASE STYLE: DG1847, MCLP 4x4 mm, 24 leads, exposed paddle. PCB layout PL-532, eval board TB-978+.
- PAD CONNECTIONS:
  INPUT     3
  COUPLED   7
  OUTPUT    16
  GROUND    1,2,4-6,8-15, 17-24 & paddle
- 8000-10000 MHz band:
  - Coupling: 17.8 min / 21 typ / 24.6 max dB
  - Directivity: 12.5 min / 19 typ dB
  - Mainline loss: 0.7 typ / 1.4 max dB
  - Return loss (in / out / coupled): 16 / 16 / 16 dB typ
- Coupling flatness is ±2.0 dB from 4 to 20 GHz. The coupler has an internal termination (no external load needed).
- Input power: +29.5 dBm continuous. Internal termination: +12 dBm continuous.
- The coupled port is in quadrature with the through port.

### 6. LO buffer: AVA-183A+ (5-18 GHz, single +5 V)
- URL: https://www.minicircuits.com/pdfs/AVA-183A+.pdf. REV. D, ECO-024424, date code 250205.
- CASE STYLE: DQ849, 3x3 mm MCLP with exposed paddle. PCB layout PL-328, test board TB-547-2+.
- Pad table:
  RF-IN      2
  RF-OUT     5
  DC         8(VD1), 7(VD2)
  GND        Paddle in Center of Bottom
  NOT USED   1,3,4,6   (No internal connection; recommended use: per PCB Layout PL-328)
- Supply: +5.0 V on VD1 and VD2. Current 131 mA typ (104 min / 166 max). Abs max: 5.5 V on pads 7 and 8; +20 dBm input (CW).
- At 5.0 GHz: gain 12.9 dB, P1dB +17.6 dBm.
- At 8.0 GHz: gain 14.7 typ (12.0 min), P1dB +18.0 dBm typ.
- 6-7 GHz itself is NOT tabulated; it lies between the 5 and 8 GHz points.
- P1dB minimum: +16.0 dBm is given only at 10 GHz. No minimum is given at 5 or 8 GHz.
- OIP3 is +32.2 dBm at 5 GHz and +29.0 dBm at 8 GHz. Additive phase noise is -151 dBc/Hz at 10 kHz (5 GHz).
- The part has integrated DC blocks, bias-tee and bypass capacitor, so the RF ports need no external DC blocks.
- Fig. 2 "Recommended Application Circuit" (the same values as the Fig. 1 test circuit):
  - C1 = 5.6 pF 0402 NPO
  - C2 = 18 pF 0402 NPO
  - C3 = 0.001 µF 0402 NPO
  - C4 = 0.1 µF 0402 X7R
  - L1 = 3.3 nH 0805 wire-wound
  - ML1-ML7 are short microstrip lines (refer to 98-PL-328)
- The figure shows L1, C2 and C1 on the +VS feed line, and C4 near pad 8 and C3 near pad 7. The exact node-by-node topology
  could not be read reliably from the extracted text. Copy it from the Fig. 2 drawing / PL-328, do not take it from this note.

## UNRESOLVED / NOT TABULATED
- BFCN-8350+: no rejection value at exactly 1.8, 4.8 or 6.6 GHz, and no IL at exactly 8350 or 8400 MHz (only the nearest rows above).
- HFCN-7150+: no row at exactly 4.8 GHz.
- BFCN-1840+: no values at 4.8 GHz (exact), 6.6 GHz or 8.4 GHz.
- AVA-183A+: no gain or P1dB at 6-7 GHz; the exact bias-network topology is to be copied from the Fig. 2 drawing.
- No narrowband 4-way splitter with lower loss than EP4RKU+ was identified.
