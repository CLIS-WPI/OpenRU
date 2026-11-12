# ADAR1000 datasheet notes (verified from local text only)

Source: m_adar1000.pdf (79 pages). Page numbers = PDF page = printed "N of 79".

## Revision
- "Rev. B" (p1 footer, every page). Revision history: "7/2022—Rev. A to Rev. B" (p2).
- Title: "8 GHz to 16 GHz, 4-Channel, X Band and Ku Band Beamformer" (p1).

## Package
- "88-terminal, 7 mm × 7 mm, LGA package and is specified from −40°C to +85°C" (p1).
- Outline: "Figure 107. 88-Terminal Land Grid Array [LGA] (CC-88-1)" (p79). Ordering: ADAR1000ACCZN / ADAR1000ACCZN-R7 (reel 500), "88-Lead LGA (7mm x 7mm)", CC-88-1 (p79).
- Ball grid: rows A,B,M,N fully populated (13 each), rows C–L (no I) only columns 1,2,12,13 → 88 terminals + exposed pad "EPAD" (p12–14). Detailed dimensions are in the Fig. 107 drawing (image; not in text) → UNRESOLVED (pitch/land size not extractable from text).
- Thermal (Table 4, p11): CC-88-1 θJA 18.7, θJC-TOP 9.72, θJC-BOTTOM 10.1 °C/W.

## Absolute maximum ratings (Table 3, p11)
- AVDD1 to GND: −5.5 V
- AVDD3 to GND: 3.6 V
- Digital Input/Output Voltage to GND: 2.0 V
- Maximum RF Input Power: 20 dBm ("Applicable to any receive or transmit input")
- Operating temp −40°C to +85°C; storage −65°C to +150°C; reflow peak 260°C; TJ 135°C
- ESD: CDM ±500 V, HBM ±2500 V

## Recommended supplies (Table 1, p8)
| Rail | Min | Typ | Max |
|---|---|---|---|
| AVDD1 | −5.25 V | −5 V | −4.75 V |
| AVDD3 | 3.1 V | 3.3 V | 3.5 V |

- IAVDD1: "Quiescent (reset state)" −4 mA; "PA bias outputs fully loaded" −50 mA.
- IAVDD3: Reset Mode (Standby) 23 mA; Transmit, four channels, nominal bias 350 mA / low bias 240 mA; Receive, four channels, nominal bias 260 mA / low bias 160 mA.
- Power (derived, not stated in DS): TX nominal ≈ 3.3 V × 350 mA ≈ 1.16 W on AVDD3 — computed, not quoted.
- Nominal bias regs: 0x034=0x08, 0x035=0x55, 0x036=0x2D, 0x037=0x06; low-power: 0x034=0x05, 0x035=0x1A, 0x036=0x2A, 0x037=0x03 (p5).
- AVDD1 may be grounded "If the PA_BIASx and LNA_BIAS pins are not used ... to use a single voltage supply" (p13).
- Suggested regulators: LT8609S (+3.3 V) and LT3462 (−5 V) from a single 5.5 V (p45); multi-chip options Table 26 (p46): 4 devices LT8609S/LT1931; 16 LT8642S/LT3580; 32 LTC7151S/LT3957A; 64 LTM4636/LT3757.

## Power-up / power-down sequencing
- AVDD1 pin (p13): "It is recommended to power up the AVDD3 pins (3.3 V) before or at the same time as the AVDD1 pin (−5 V)." Same on AVDD3 (p14).
- With ADTR1107 (p44): "The ADTR1107 PA gate bias depends on the ADAR1000 −5 V supply powering up first before the PA VDD is powered on." Sequence: 1) 3.3 V to ADTR1107 VDD_SW, VDD_LNA and ADAR1000; 2) −3.3 V to ADTR1107 VSS_SW; 3) set TR_SW_POS to drive CTRL_SW; 4) −5 V to ADAR1000; 5) set PA_BIASx to −2.5 V to drive VGG_PA; 6) 5 V to ADTR1107 VDD_PA.
- p45: "For safe power up of the ADTR1107 PA, the PA_BIASx bias pins must be set to −2.5 V before the +5 V supply is powered up." Recipe (TR control): BIAS_CTRL=1 (0x30 b6); BIAS_RAM_BYPASS=1 (0x38 b5); EXT_PAx_BIAS_ON (0x29–0x2C)=0x39 (≈−1.1 V); EXT_PAx_BIAS_OFF (0x46–0x49)=0x85 (≈−2.5 V); TR low → ≈−2.5 V; after +5 V up, TR high → ≈−1.1 V, "sets the ADTR1107 PA bias current to 220 mA".
- Power-down sequence: not stated in the ADAR1000 DS → UNRESOLVED.
- RAM: "on a power cycle, the data in the RAM is undefined. The user must rewrite to the RAM after each power cycle"; soft reset does not affect RAM (p32).

## Decoupling / required external components
- CREG1 (M8, 1.8 V LDO reference), CREG2 (M9, 2.8 V LDO output), CREG3 (N10, 2.8 V LDO reference), CREG4 (N9, 1.8 V LDO output): each "Connect a 1 µF capacitor through a low impedance path from this pin to a ground plane" (p14).
- AVDD1/AVDD3 bulk/bypass capacitor values: not stated in text → UNRESOLVED.
- TX_LOAD / RX_LOAD: "no internal pull-down resistor on this pin; pull down to ground if not using pin" (p14).
- DETx unused: "leave the detector disabled and either provide a 50 Ω termination or ground the input" (p12–14); p31 adds "but they can also be left floating".
- SDO: "recommended to install a 50 Ω series current limiting resistor between the SDO pin and the MISO bus line" (p49, Fig. 106).
- RF ports to ADTR1107: "glueless interfacing, requiring no components between the connected ports" (p44).
- All GND + EPAD to low-impedance ground plane (p12, p14).
- Optional LDO trim in SPI example: 0x401=0x02 "Allow LDO adjustments from user settings", 0x400=0x55 "Adjust LDO regulators" (p50).

## SPI interface
- "4-wire SPI interface" (p1). 3-wire when SDO ACTIVE bit = 0, 4-wire when = 1 (SDIO pin, p13). SDOACTIVE reset = 0x0 (Reg 0x000, p57) → 3-wire at reset (inference from reset value).
- Logic: all SPI/control pins "1.8 V CMOS Logic" (p13–14). VIH min 1.0 V, VIL max 0.4 V, IIN ±1 µA, CIN 1 pF, 100 mV hysteresis; VOH 1.4 V min @ −10 mA, VOL 0.4 V max @ 10 mA (p8). Abs max digital I/O 2.0 V (p11).
- Timing (Table 2, p9): max clock 25 MHz; min period 40 ns; tPWH/tPWL 10 ns; tDS 5 ns; tDH 5 ns; tDV 5 ns; tDCS 10 ns; tR/tF 4 ns (80 pF).
- Clock edges: "In write mode, data is sampled on the rising edge of SCLK. During a read cycle, output data changes at the falling edge of SCLK." (p13). CSB active low. Explicit "SPI mode 0/CPOL/CPHA" wording: not in DS → UNRESOLVED (edge behaviour above is consistent with mode 0 but that's inference).
- Frame: 24-bit standard, MSB first default; address header bit 15 R/W, bits[14:13] chip ID (= ADDR1, ADDR0), bit 12 = RAM space; broadcast write all with bits[14:11]=0001 (registers only, not RAM) (p9–10, p32).
- ADDR0 (N4) = header bit 13, ADDR1 (N5) = bit 14; up to 4 chips per bus (p14, p32).
- Silicon errata: SDO of non-addressed chips not tristated → readback contention; procedures Table 28/29 (p47–48). Soft reset to Chip 0 resets all chips on bus (p47).

## TR / TX_LOAD / RX_LOAD and beam update
- TR (N6): "TR = Low is receive mode and TR = High is transmit mode" (p14). Active only when TR_SOURCE (0x031 b2)=1; else TR_SPI bit (p30). Reset of 0x031 = 0x00 → SPI control, receive (p69–70).
- TR switching time: 180 ns (TR edge 50% to RF 90%) (p7).
- TX_LOAD/RX_LOAD: "A rising edge causes contents in the transmit[receive] channel holding registers to transfer to the working registers"; OR'ed with LDTX_OVERRIDE/LDRX_OVERRIDE (0x28) (p14, p35). Phase/gain switching time 20 ns from load rising edge 50% to RF 90% (p7). Gain/phase registers are "dual-rank" (p35).
- RAM: 121 beam positions (0–120) + 7 bias settings each for TX and RX (p32). BEAM_RAM_BYPASS (0x038 b6): 0 = from memory, 1 = from registers. RX beams start 0x1000, TX 0x1800; RX bias 0x1790, TX bias 0x1F90 (p32).
- Fetch: set BEAM_RAM_BYPASS low; write 7-bit index to 0x039 (RX)/0x03A (TX) with bit 7 fetch (or per-channel 0x3D–0x44); "Provide at least six additional clock cycles on SCLK to load the new data from the RAM" (SCLK independent of CSB); then pulse TX_LOAD/RX_LOAD (p32–33).
- "loading problems can occur when the TX_LOAD and RX_LOAD pins are pulsed high together"; separate by "at least eight SCLK cycles"; "cannot be tied together" (p33–34).
- Sequencer: start/stop indices 0x04D/0x04E (TX), 0x04F/0x050 (RX); TX_BEAM_STEP_EN / RX_BEAM_STEP_EN in 0x038; wraps after stop (p33).
- Min TX_LOAD/RX_LOAD pulse width: not specified → UNRESOLVED.
- TX↔RX delays (0x4B/0x4C): with 20 MHz SCLK, max 750 ns, 50 ns/step; only active in TR pin control with SCLK running (p43). ERRATUM: "A silicon error exists that prevents all four of the PA bias pins from changing state ... when delay values in Register 0x4B and Register 0x4C are all nonzero" (p43).

## PA_ON / PA_BIAS / LNA_BIAS / switch outputs
- NOTE: There is no "LNA_ON" pin on ADAR1000 (string absent from datasheet). PA_ON (B3) is an INPUT, not an output.
- PA_ON: used only in TR-pin control with BIAS_CTRL=1, TR_SOURCE=1; low forces all PA_BIASx to OFF values; "internally pulled up to the 1.8 V ... (LDO) regulator bias voltage with a 100 kΩ resistor" (p13).
- PA_BIAS1–4 (A10, A9, A5, A4): 8-bit DAC, "−4.8 to 0" V, source/sink "−10 to +10" mA, off↔on 60 ns (1 nF load) (p7). 0x00 = 0 V, 0xFF = −4.8 V (p31). Push-pull for GaAs/GaN gates (p31).
- LNA_BIAS (A11): same range, 8 bits (p7–8); high-impedance when LNA_BIAS_OUT_EN (0x030 b4)=0 (p31, Table 18 p40). One pin shared across up to 4 LNAs (p31, p44).
- Control truth tables: Table 16 (PA, p39), Table 18 (LNA, p40), Table 23 (SPI mode, p42). BIAS_CTRL=0 → DACs always use ON values (p39, p69).
- **Reset/power-up state (critical):** "The PA_BIASx pins assume the EXT_PAx_BIAS_ON values upon power-up. That is, all PA_BIASx pins are driven to 0 V." (p41). Reg 0x029–0x02C and 0x046–0x049 reset = 0x00 (p66–67, p75); 0x030 reset 0x00 (BIAS_CTRL=0). → PA bias is NOT in a pinched-off state at reset: 0 V gate. Safe only if the PA drain supply is off until PA_BIASx is programmed to a pinch-off value (DS recipe: −2.5 V via 0x85 before +5 V VDD_PA, p45). Also note AVDD1 must be up for negative outputs (p44).
- "The LNA_BIAS pin is floating upon power-up." "TR_SW_POS and TR_SW_NEG are floating upon power-up." (p41). TR_POL power-up state: not stated → UNRESOLVED.
- TR_SW_NEG / TR_POL: 0 V to AVDD1, ±1 mA push-pull; TR_SW_POS: 0 V to AVDD3 (table says "0 to 3.2" V) (p8, p31). Switching 15 ns (p8). Only one of TR_SW_POS/TR_SW_NEG active (SW_DRV_TR_MODE_SEL, 0x030 b7) (p38, p42).
- ADTR1107 hookup (p44, Fig. 97): PA_BIASx → VGG_PA (one per device), LNA_BIAS → VGG_LNA (optional, ADTR1107 LNA self-biased, p45), TR_SW_POS → CTRL_SW; LNA bias example ON 0x00 (0 V), OFF 0x68 (≈−2 V) (p45).
- Table 16 ambiguity (p39): TR-pin rows list TX_EN=0 yet PA uses ON with TR=1, PA_ON=1 — likely TX_EN is don't-care in TR mode; reproduced as printed.

## Temperature sensor / ADC
- 8-bit ADC muxes temp sensor + 4 detectors; Reg 0x032 control, result in 0x033 (p32). MUX_SEL 0b000 = temp sensor, 0b001–0b100 = Det 1–4 (Table 7, p32).
- Conversion: 16 ADC clocks, "minimum conversion time of 8 µs (2 MHz clock)"; clock 2 MHz or 250 kHz (ADC_CLKFREQ_SEL) (p32).
- Temp sensor: range −40 to +85 °C, slope 0.8 LSB/°C, nominal output 145 decimal at 25 °C in POR mode, 8 bits (p7).
- Detector: −20 to +10 dBm at 11.5 GHz, input RL −10 dB, code 60 at 0 dBm (p7); "matched on chip to 50 Ω" (p31).

## RF performance at lowest tabulated frequency (9.5 GHz, Table 1, p5–7; max gain, 25 °C)
- TX single-channel gain: 21 dB.
- TX OP1dB: 10 dBm (nominal bias), 6 dBm (low bias).
- TX PSAT: 14 dBm (nominal), 14 dBm (low).
- TX OIP3: 20 dBm nominal / 15 dBm low (p6). TX noise figure 22 dB (p5).
- RX single-channel gain: 10 dB; electronic gain 16 dB; coherent gain 22 dB (nominal bias, p6).
- RX NF: 8 dB nominal / 9 dB low bias (p7). RX IP1dB −16 dBm nominal / −13 dBm low; IIP3 −7 dBm (p6).
- Gain flatness ±1.0 dB 9–14 GHz, ±1.7 dB 8–15 GHz (p5, p6).

## RF port impedance
- TX/RX ports via balun "match the input and outputs to 50 Ω over the operating bandwidth"; RF_IO "single-ended, matched to 50 Ω ... connected to dc ground through a shunt matching inductor" (p28). TX output RL −10 dB, RF_IO RL −12 dB (p6); RX input RL −10 dB (p7).
- DC: RF_IO "dc bias is 0 V due to the on-chip shunt inductor" (p13); TX/RX ac-coupled (p13).

## Frequency range / below 9.5 GHz
- "RF Range 8 [min] ... 16 [max] GHz" (Table 1, p5); feature "8 GHz to 16 GHz frequency range" (p1).
- Numeric specs tabulated only at 9.5, 11.5, 14 GHz; the only sub-9.5 GHz numbers are gain flatness "From 8 GHz to 15 GHz ±1.7 dB" (p5, p6). No explicit statement restricting/derating operation below 9.5 GHz found in text. Typical-performance plots (p15–27) are images; their low-frequency values were not extracted → UNRESOLVED.
