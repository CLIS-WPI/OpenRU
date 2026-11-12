# ADF4371 datasheet facts (local source only: ds/m_adf4371.txt / m_adf4371.pdf)

## Revision / package
- "Rev. 0" — Revision history: "1/2019—Revision 0: Initial Version" (p2). Doc code "D16982-0-1/19(0)" (p48).
- Package: "7mm × 7mm, 48-terminal LGA package" (p1). Ordering: ADF4371BCCZ / ADF4371BCCZ-RL7, "48-Terminal Land Grid Array Package [LGA] CC-48-4", −40°C to +105°C (p48).
- Outline (Fig 45, p48): 7.00 body (6.90–7.10), pitch "0.50 BSC", exposed pad "5.50 REF SQ" (also "5.00 BSC SQ" listed — UNRESOLVED which is pad vs. pin-span; use ADI land pattern).
- EP: "must be soldered to a metal plate on the PCB for mechanical reasons and to GND" (p9/p10).
- Thermal (Table 4, p8): θJA 25 °C/W, θJC 14.4 °C/W.
- 48 pins + EP. CSV has 48 numbered rows + EP = 49 rows.

## Absolute maximum (Table 3, p8)
- AVDD rails to GND: −0.3 V to +3.6 V; AVDD rails to each other: ±0.3 V
- VCC_VCO to GND: −0.3 V to +5.5 V; VCC_VCO to AVDD: −0.3 V to AVDD + 2.8 V
- CPOUT, VTUNE, digital I/O, analog I/O, REFP/REFN to GND: −0.3 V to AVDD + 0.3 V
- REFP to REFN: ±2.1 V
- Operating −40°C to +105°C; storage −65°C to +125°C; Tj max 125 °C; reflow peak 260°C, 30 s
- ESD: CDM 1.0 kV, HBM 4.0 kV

## Supply rails (Table 1, p3–4; pin table p9–10)
- AVDD group (all same voltage): "VCC_CAL, VCC_X4, VDD_X4, VCC_X1, VDD_X1, VCC_X2, VCC_MUX, VCC_3V, VDD_NDIV, VDD_LS, VCC_LDO_3V, VCC_REF, VDD_PFD, VDD_VP" — 3.15 V min, 3.45 V max (3.3 V ± 5%).
- AIDD: 190 typ / 260 max mA "All outputs are disabled". Output dividers: ÷2 14/20 mA ("Each divide by 2 will consume additional typical 7 mA"), ÷64 50/65 mA.
- VCC_VCO: 3.3 V condition 3.15/3.3/3.45 V, IVCO 80 typ/120 max mA; 5 V condition 4.75/5/5.25 V, IVCO 135/180 mA.
  - Mode must match register: REG002F bit7 SWITCH_LDO_3P3V_5V, default 1 = "5 V VCO operation" (p41).
- RF8x supply current (extra, drawn in VCC_X1): 25 / 39 / 52 / 65 mA at −4 / −1 / 2 / 5 dBm setting.
- RFAUX8x: 42 / 56 / 70 / 84 mA at −4 / −1 / 2 / 5 dBm setting.
- RF16x: 90 typ / 120 max mA. RF32x: 160 typ / 210 max mA.
- Sleep: HW power-down 5.1/6.2 mA (3.3 V VCO), 8/9.5 mA (5 V VCO); SW power-down 21.5/25 mA (3.3 V VCO), 23.7/28 mA (5 V VCO).
- Power-supply recommendations (p24): "it is recommended to connect a low noise regulator, such as the ADM7150 or LT3045 to the VCC_VCO pin. Connect the same regulator to the VCC_VCO and VCC_LDO pins. 1 μF decoupling capacitors connected to the 5 V VCO supply are recommended." "For all other the 3.3 V supply pins, use one ADM7150 or one LT3045 regulator. 1 μF is also recommended for the VDD_VP pin. Additional decoupling to other supply pins is not required."
- Internal VCO LDO option: VCC_REG_OUT "must be decoupled to GND with a 10 μF capacitor and shorted to the VCC_VCO pin. Leave this pin open if an external LDO regulator is connected to VCC_VCO." VCC_LDO: "If the external regulator is used, short this pin to VCC_VCO." (p9). REG0027 bit2 VCOLDO_PD default 1 = "VCO LDO disabled"; "For optimal spurious and phase noise performance, disable VCO LDO."
- VDD_VP: "A 1 μF decoupling capacitor to GND must be included to minimize spurious signals." (p10)

## Required external components
- NO typical application circuit / reference schematic is in this datasheet. Loop filter topology and values: UNRESOLVED (datasheet only says "external loop filter", CPOUT → filter → VTUNE; refers to ADIsimPLL). Charge pump current 0.35–5.6 mA (REG001E, default 0x4 = 1.75 mA).
- Optional series resistor CPOUT→loop filter in fractional mode: "In most cases, 91 Ω gives the best results. This resistor is not required in integer mode" (p17).
- No RSET / VBIAS / bias-resistor pins exist on this part (grep finds none).
- RS_SW: loop-filter resistor switch for fastlock (p9); usage details UNRESOLVED (no circuit given).
- TEST (pin 40): connect to ground. CE (pin 39): "Connect to 3.3 V or AVDD."
- Decoupling summary: 1 μF on 5 V VCO supply, 1 μF on VDD_VP, 10 μF on VCC_REG_OUT only if internal LDO used.

## Reference input (Table 1 p3; p10; p19)
- Frequency: single-ended 10–500 MHz, differential 10–600 MHz (doubler disabled); 10–125 MHz with doubler enabled.
- Sensitivity: SE 0.4 V p-p to AVDD ("REFP biased at AVDD/2, ac coupling ensures AVDD/2 bias"); diff 0.4–1.8 V p-p, "LVDS and LVPECL compatible, REFP and REFN biased at 2.1 V".
- Input capacitance SE 6.9 pF, diff 1.4 pF; input current ±150 µA (SE) / 300 µA (diff).
- "In differential configuration, the differential impedance is 100 Ω." (p10). Fig 35 shows 2.5 kΩ / 2.5 kΩ and 85 kΩ internal bias network.
- Coupling: "If driven single-ended, the reference signal must be connected to REFP, and the REFN must be ac-coupled to GND." Differential: "REFP and REFN must be ac-coupled".
- "use the single-ended setting for all references up to 500 MHz (even if using a differential signal)" (p19). Mode bit: REG0022 bit6 REFIN_MODE, default 0 = single-ended.
- Slew: functional at 0.4 V p-p / 21 V/µs; optimum with up to 1000 V/µs; square wave recommended (p16).
- PFD max: 160 MHz fractional, 250 MHz integer. R counter "Division ratios from 1 to 1023" (p20; text also says "5-bit R counter" — internal inconsistency).

## RF outputs (Table 1 p4–5; p21–24)
- VCO fundamental 4000–8000 MHz.
- RF8P/RF8N: 62.5–8000 MHz. RFAUX8P/N: 62.5–8000 MHz. RF16P/N: 8000–16000 MHz (2× VCO). RF32P/N: 16000–32000 MHz (4× VCO).
- Output power, max setting (footnote 3: EV board, differential outputs combined with Marki BAL-0036 balun, board/cable de-embedded):
  - RF8P = 4 GHz: 7 dBm typ (3 dBm min) "7.5 nH inductor to VCC_X1"; RF8P = 8 GHz: 5 dBm typ.
  - RF16x = 8 GHz: 0 dBm; RF16x = 16 GHz: 4 dBm. RF32x = 16 GHz: −1 dBm; RF32x = 32 GHz: −7 dBm.
  - Variation over frequency: RF8x and RFAUX8x 4–8 GHz ±2 dB; RF16x ±2.5 dB; RF32x ±5 dB.
- **RF8x near 6.6 GHz: NO table value. Only Figure 13 (p12)** "RF8P and RF8N Output Power, De-Embedded Board and Cable Measurement, Combined Using Balun (7.4 nH Inductors, 10 pF AC Coupling Capacitors Limit Power at Low Frequencies)". My visual read of the rendered plot at ~6.6 GHz: de-embedded ≈ +6 to +7 dBm, raw ≈ +2 dBm. These are plot readings (approx ±1 dB), balun-combined differential, max power setting — not per single-ended pin; single-ended per-pin power is UNRESOLVED (not stated for RF8x).
- Programmable RF8 levels (REG0025 [1:0] RF_OUT_POWER, default 0x3): "approximate output power levels of −4 dBm, −1 dBm, 2 dBm, and 5 dBm" (p21).
- RFAUX8 power (REG0072 [5:4] POUT_AUX, default 0x3): −4.5 dBm SE / −1.5 dBm diff; 1 / 4; 4 / 7; 6 dBm SE / 9 dBm diff. AUX_FREQ_SEL bit6: 0 = divided output, 1 = VCO output.
- Off-isolation (output disabled): RF8 −50 dBm @1 GHz, −44 dBm @8 GHz; RF16 −75/−55 dBm; RF32 −85/−70 dBm.

## Output termination (p9, p21, p24)
- RF8P/N: open-collector NPN pair with "internal 50 Ω resistors connected to the VCC_X1 pin". "Levels of −4 dBm, −1 dBm, and 2 dBm can be achieved by ac coupling into a 50 Ω load. A 5 dBm level requires an external shunt inductor to VCC_X1." "Terminate the unused complementary output with a circuit similar to the used output."
- Fig 44 "Optimum Output Stage": 7.5 nH pull-up, 10 pF AC coupling, 50 Ω load (figure labels the pull-up rail VDD_X1 while text/Table 1 say VCC_X1 — ambiguity; text/table say VCC_X1, which is the "Power Supply for the Main RF Output").
- "For lower frequencies less than 1 GHz, it is recommended to use a 100 nH inductor on the RF8P and RF8N pins."
- RFAUX8P/N: "effectively the same as RF8P and RF8N and must be treated in the manner as outlined for RF8P and RF8N." Pin table: "AC couple".
- RF16P/N and RF32P/N: "can be directly connected to the next circuit stage. These pins are internally matched to 50 Ω and do not require additional decoupling." Pin table: "AC or dc couple ... If unused, this pin can be left open."
- PCB: avoid FR4; "Rogers 4350, Rogers 4003, or Rogers 3003" suitable (p24). Thermal vias 1.2 mm pitch, 0.3–0.33 mm dia.

## MUXOUT / lock detect (p10, p20, REG0020/0028/007C)
- MUXOUT selects digital lock detect, analog lock detect, R/N divider outputs, etc.; also readback output in 4-wire SPI.
- REG0020: MUXOUT[7:4] default 0x1 = "digital lock detect"; MUXOUT_EN default 0 ("data pin used for readback"); LEV_SEL default 1 = 3.3 V logic. Interaction of MUXOUT_EN=0 with MUXOUT driving lock detect at default is UNRESOLVED (description: MUXOUT field used "when MUXOUT_EN = 1").
- Logic out: VOH AVDD−0.4 V (3.3 V mode) or 1.5–1.875 V (1.8 V mode); VOL 0.4 V @ 500 µA; IOH 500 µA.
- LD_COUNT default 1 (2048 PFD cycles); LOL_EN default 1 (recommended). Lock detect also readable at REG007C (LOCK_DETECT_READBACK).

## SPI (Table 1 p3, Table 2 p7, p22–23, REG0000)
- "3-wire or 4-wire SPI port": SCLK, SDIO, CS, MUXOUT (MUXOUT "not used in 3-wire SPI").
- Frame: R/W bit + 15 address bits + 8 data bits, MSB first default; streaming supported.
- REG0000 bit3 SDO_ACTIVE default 1 = "4-pin. Enables SDIO pin and the SDIO pin becomes an input only." (0 = 3-pin). Table 8 setup writes 0x18 to 0x00 ("4-wire SPI").
- fSCLK max 50 MHz (tSCLK 20 ns, tHIGH/tLOW 10 ns, tDS/tDH 2 ns, tACCESS 10 ns).
- Input levels: VINH 1.17 V min, VINL 0.63 V max, ±1 µA, 3.0 pF. Table 1 heads this "CS, SDIO, SCLK, and CE is 3 V logic"; p22: "input logic level for the write cycle is compatible with 1.8 V logic level". Readback output on SDIO/MUXOUT "configurable for 1.8 V (default) or 3.3 V" by LEV_SEL — but REG0020 LEV_SEL default is 1 = 3.3 V. Contradiction: UNRESOLVED.
- Pin desc: "Data is clocked into the 24-bit shift register on the clock rising (or falling) edge" — exact edge UNRESOLVED beyond timing diagrams.

## Power-up defaults (register defaults, Table 9 p25–26; no explicit power-up narrative in datasheet)
- REG0025 default 0x07: MUTE_LD = 0 (mute-to-lock-detect disabled), RF_EN = 1 ("RFOUT enabled"), RF_OUT_POWER = 3 (5 dBm), X2_EN = 0, X4_EN = 0.
- REG0072 default 0x32: PDB_AUX = 0 ("auxiliary RF off"), POUT_AUX = 3.
- So by register defaults RF8x is enabled and NOT muted at power-up; RF16/RF32/RFAUX8 off. Whether the output actually toggles before programming (VCO uncalibrated) is not stated: UNRESOLVED.
- Mute feature: "the supply current to the RF8P and RF8N output stage can shut down until the ADF4371 achieves lock as measured by the digital lock detect circuitry" via MUTE_LD (p22).
- CE behavior beyond "Connect to 3.3 V or AVDD" not described; "Hardware power-down" current is listed but the pin that triggers it is not stated (presumably CE): UNRESOLVED.

## Phase resync / multi-chip sync
- REG0023 [5:4] CLK_DIV_MODE: "Set to 10 to enable phase resynchronization. When not using phase resynchronization, set to 00." No procedure/timing given (CLK1_DIV/CLK2_DIVIDER registers marked "Reserved").
- REG002A bit3 LE_SEL: "CSB from Pin, Synchronized with REFN" (1 = enabled).
- Phase adjust: REG001A bit6 PHASE_ADJ + 24-bit PHASE_WORD; "Phase step = Phase Word ÷ 16,777,216 × 360°".
- Deterministic multi-chip sync procedure: UNRESOLVED (not described).

## Datasheet inconsistencies noted
- RF32N described as "Quadrupler Output" and RF32P as "Complementary" (reverse of RF8/RF16 convention) (p9).
- Output-stage text references "Figure 13" for the schematic; actual schematic is Figure 41.
- Fig 13 caption 7.4 nH vs Table 1/Fig 44 7.5 nH.
- Fig 44 pull-up rail labeled VDD_X1 vs text VCC_X1.
- Block diagram labels RF8/RFAUX8 "6.25MHz TO 8000MHz" vs spec table 62.5 MHz min.
- R counter "5-bit" vs "1 to 1023".
