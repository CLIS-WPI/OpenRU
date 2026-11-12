# ADTR1107 — verified datasheet facts

Source: local file m_adtr1107.txt/.pdf (ADI ADTR1107 data sheet). Page numbers are the datasheet's own "Rev. C | N of 27" numbers.
Figure 89 and Figure 91 contain no extractable text. They were read by rendering PDF pages 25 and 26 (pdftoppm) and are marked [figure, visual read].

## Revision
- "Rev. C" (p.1). Revision history: "6/2023—Rev. B to Rev. C  Changes to Theory of Operation Section" (p.2). Outline "Updated: May 26, 2023" (p.27).

## Package
- "5 mm × 5 mm, 24-terminal, land grid array (LGA) package" (p.1).
- Ordering guide: "ADTR1107ACCZ … 24-Lead LGA (5mm x 5mm x 1.13mm w/ EP) … CC-24-8"; also ADTR1107ACCZ-R7 (p.27). Figure 92: "24-Terminal Land Grid Array [LGA] (CC-24-8)".
- 24 numbered pins plus EPAD: "Exposed Pad. Must be connected to RF/dc ground." (p.7). Figure 89 labels the pad "PAD".
- Frequency: "6 GHz to 18 GHz" (p.1). I/Os "internally matched to 50 Ω" (p.1).
- MSL: "Moisture Sensitivity Level 3, MSL3", peak reflow "260°C" (p.6).

## Absolute maximum ratings (Table 6, p.6)
Transmit State (PA On), Receive State Off:
- VDD_PA: "5.5 V"
- VGG_PA: "−2 V to +0 V"
- "Continuous Wave (CW) RF Input Power (RFIN) at TX_IN": "20 dBm"
- PDISS: "(TA = 85°C, Derate 18.98 mW/°C Above 85°C)": "1.71 W"

Receive State (LNA On), Transmit State Off:
- VDD_LNA: "4V"
- VGG_LNA: "−2 V to +0.2 V"
- "CW RFIN at ANT": "20 dBm"
- PDISS: "(TA = 85°C, Derate 5.04 mW/°C Above 85°C)": "0.453 W"

Transmit and Receive States:
- "Output Load Voltage Standing Wave Ratio (VSWR)": "7:1"
- "VDD_SW Range": "−0.3 V to +3.6 V"
- "VSS_SW Range": "−3.6 V to +0.3 V"
- "VDD_CTRL Range": "−0.3 V to VDD + 0.3 V". UNRESOLVED: no pin is named VDD_CTRL. It almost certainly means CTRL_SW, but the datasheet does not say so.
- "Channel Temperature": "175°C"
- Storage: "−40°C to +125°C"; Operating: "−40°C to +85°C"
- ESD: "Class 1B (Passed ±500 V)" (HBM)

## Recommended operating conditions
There is no separate ROC table. Supply min/typ/max values from the spec tables:
- VDD_PA: min "3.3", typ "5.0", max "5.5" V (Table 1 p.3, Table 2 p.4)
- IDQ_PA: "220" mA, "Adjust VGG_PA voltage between −1.75 V and −0.25 V to achieve the desired IDQ_PA" (p.3)
- VDD_LNA: min "2.0", typ "3.3", max "3.6" V. IDQ_LNA: "80" mA "Self biased" (Table 3 p.4, Table 4 p.5)
- Switch bias: "VDD_SW = 3.3 V, VSS_SW = −3.3 V". IDD_SW "14" µA, ISS_SW "120" µA (Table 5 p.5)
- CTRL_SW: Low "0" to "0.8" V; High "1.2" to "3.3" V; current "<1" µA (Table 5 p.5)
- Operating temperature: "−40°C to +85°C" (p.6)

## TX performance at 8.4 GHz: Table 1, "Frequency Range 6 … 14 GHz" (p.3)
Conditions: "VDD_PA = 5 V, IDQ_PA = 220 mA, VDD_SW = 3.3 V, VSS_SW = −3.3 V, CTRL_SW = 0 V, receive state off (VDD_LNA = 0 V, VGG_LNA = 0 V), TA = 25°C"
- Small Signal Gain: min "19.5", typ "21.5" dB (TX_IN to ANT)
- Gain Flatness: "±0.8" dB
- Input RL "13" dB; Output RL "15" dB
- OP1dB: min "21", typ "23" dBm
- PSAT: "25" dBm
- OIP3: "31" dBm (POUT per tone = 8 dBm). IIP3: NOT IN DATASHEET.
- Noise Figure (TX path): "9" dB
- Coupling Factor: "23.5" dB, "Coupling factor = ANT POUT − CPLR_OUT POUT"
- Isolation TX_IN to RX_OUT "40" dB; ANT to RX_OUT "64" dB (receive state off)
- RF settling: 0.1 dB "17" ns, 0.05 dB "22" ns; tRISE/tFALL "2" ns; tON/tOFF "10" ns ("50% CTRL_SW to 90% of RF output")
- The values at exactly 8.4 GHz exist only on the plots (Figs 12–50), which have no extractable data: UNRESOLVED.

## RX performance at 8.4 GHz: Table 3, "Frequency Range 6 … 14 GHz" (p.4)
Conditions: "self biased, VDD_LNA = 3.3 V, VGG_LNA = 0 V, VDD_SW = 3.3 V, VSS_SW = −3.3 V, CTRL_SW = 3.3 V, transmit state off (VDD_PA = 0 V, VGG_PA = −1.75 V), TA = 25°C"
- Small Signal Gain: min "15.5", typ "17.5" dB (ANT to RX_OUT)
- Gain Flatness "±0.6" dB; Input RL "13" dB; Output RL "14" dB
- OP1dB: min "12", typ "14" dBm
- PSAT: "16" dBm
- OIP3: "26" dBm (POUT per tone = 0 dBm). IIP3: NOT IN DATASHEET.
- Noise Figure: "2.5" dB
- Isolation ANT to TX_IN "32" dB; RX_OUT to TX_IN "48" dB (transmit state off)
- Switching values are the same as for TX: 17/22 ns settling, 2 ns rise/fall, 10 ns on/off.

## Coupler and detector
- The ADTR1107 has a coupler only, with NO on-chip detector. "The device has a directional coupler for power detection." (p.1). CPLR_OUT: "used in connection with a detector to monitor transmitted power." (p.7)
- "The coupling factor of the ADTR1107 directional coupler ranges from 28 dB at 6 GHz to 18 dB at 18 GHz." (p.26)
- Table 1 typ coupling factor (6–14 GHz) is "23.5" dB; Table 2 (14–18 GHz) is "18" dB.
- Calibration use (p.26): "The ADTR1107 CPLR_OUT coupler output can be tied back to one of the four ADAR1000 RF detector inputs (DET1 to DET4). These diode based RF detectors have an input range of −20 dBm to +10 dBm. … At 12 GHz, with a coupling factor of 22 dB and a maximum power amplifier output of 26 dBm, the coupled output power is a maximum of 4 dBm. If the coupler output is connected directly to the detector input, this connection provides a detection range of 24 dB. Figure 90 shows the relationship between the ADTR1107 output power and the ADC code of the ADAR1000 detector at 12 GHz."
- Figure 91 [figure, visual read]: CPLR_OUT connects to ADAR1000 DET3 (one channel shown).

## TX/RX switch control (p.6, p.23, p.24)
- Table 8 (p.6): "Transmit | CTRL_SW Low | TX_IN to ANT"; "Receive | CTRL_SW High | ANT to RX_OUT".
- "The high logic state is set at 3.3 V, and the low logic state is set at 0 V." (p.24)
- Thresholds: low "0 … 0.8" V, high "1.2 … 3.3" V (p.5).
- "integrated driver … (CMOS)/low voltage transistor to transistor logic (LVTTL)-compatible control interface … single digital control input pin, CTRL_SW." (p.23)
- Switching time: tON/tOFF "10" ns; tRISE/tFALL "2" ns; 0.1 dB settling "17" ns (pp.3–5).
- ADAR1000 link (p.26): "Asserting the ADAR1000 TR pin switches the polarity of the ADAR1000 TR_SW_NEG pin and TR_SW_POS pin. The TR_SW_POS pin can drive the gates of up to four switches and can be used to control the ADTR1107 SPDT switch."

## Gate bias (VGG_PA / VGG_LNA)
- VGG_PA (p.24): "The power amplifier on the transmit path is biased with +5 V on the VDD_PA pin and a voltage from −1.75 V to −0.25 V is applied to the VGG_PA pin to achieve 220 mA quiescent current."
- Typical value (p.26): "The typical gate voltage required to bias the ADTR1107 power amplifier is −1.1 V (see Figure 49)."
- VGG_LNA (p.24): "For self biased mode, apply 3.3 V to the VDD_LNA pin and leave the VGG_LNA pin supplied with 0 V or connected to ground. For external biased mode, apply +3.3 V to the VDD_LNA pin and adjust the VGG_LNA pin with a voltage range of −1.5 V to 0 V to achieve the desired IDQ_PA." (The datasheet says "IDQ_PA" here even though the paragraph is about the LNA; this is quoted as printed.)
- ADAR1000 connection: YES. The datasheet shows it (p.26 and Fig 91):
  - "The gate voltage for the ADTR1107 power amplifier (VGG_PA) is provided by the ADAR1000 PA_BIAS3 pin. … Each voltage is set by an 8-bit digital-to-analog converter (DAC) with an output voltage range of 0 V to −4.8 V." "This voltage can be asserted by the ADAR1000 TR input pin (rising edge enables the power amplifier) or by a serial peripheral interface (SPI) write."
  - "While the ADTR1107 LNA gate voltage is self biased (the VGG_LNA pin is connected to 0 V or grounded), the voltage can also be controlled from the ADAR1000. In this case, there is a single LNA_BIAS voltage (0 V to −4.8 V) controlled by an 8‑bit DAC that can be used to bias four ADTR1107 devices connected to each ADAR1000."
  - Fig 91 footnote [visual read]: "LNA_BIAS IS A SINGLE PIN THAT CAN DRIVE UP TO FOUR GATES AND IS AN OPTIONAL CONNECTION THAT CAN BE USED TO VARY THE BIAS CURRENT OF THE ADTR1107."
  - Fig 91 [visual read]: ADAR1000 TX3 to TX_IN, RX3 to RX_OUT, PA_BIAS3 to VGG_PA, LNA_BIAS to VGG_LNA (dashed, optional), TR_SW_POS (dashed) toward CTRL_SW. Supplies are shown as VDD_PA +5V, VDD_LNA +3.3V, VSS_SW −3.3V, VDD_SW +3.3V.

## Power-up / power-down sequencing (verbatim, p.24)
Transmit state power-up:
"1. Connect all GND pins to ground. 2. Set the VDD_SW pin to 3.3 V. 3. Set the VSS_SW pin to −3.3 V. 4. Set the CTRL_SW pin to 0 V. 5. Set the VGG_LNA pin to 0 V. 6. Set the VDD_LNA pin to 0 V. 7. Set the VGG_PA pin to −1.75 V. 8. Set the VDD_PA pin to 5 V. 9. Increase the VGG_PA voltage to achieve the desired IDQ_PA. 10. Apply the RF signal to the TX_IN pin."

Transmit state power-down:
"1. Turn off the RF signal. 2. Decrease the VGG_PA voltage to −1.75 V. 3. Set the VDD_PA pin to 0 V. 4. Set the VSS_SW pin to 0 V. 5. Set the VDD_SW pin to 0 V."

Receive state power-up:
"1. Connect all GND pins to ground. 2. Set the VDD_SW pin to 3.3 V. 3. Set the VSS_SW pin to −3.3 V. 4. Set the CTRL_SW pin to 3.3 V. 5. Set the VGG_PA pin to −1.75 V. 6. Set the VDD_PA pin to 0 V. 7. Set the VGG_LNA pin to 0 V. 8. Set the VDD_LNA pin to 3.3 V. 9. Apply the RF signal to the ANT pin."

Receive state power-down:
"1. Turn off the RF signal. 2. Set the VDD_LNA pin to 0 V. 3. Set the CTRL_SW pin to 0 V. 4. Set the VSS_SW pin to 0 V. 5. Set the VDD_SW pin to 0 V."

Also on p.24: "To obtain optimal performance while not damaging the device, follow the recommended biasing sequences described in this section and adhere to the values shown in the Absolute Maximum Ratings section."
Summary of the order: switch supplies VDD_SW then VSS_SW come first; the PA gate is pinched off at −1.75 V before VDD_PA is applied; the gate is returned to −1.75 V before VDD_PA is removed.

## Application circuit / decoupling (Figure 89, p.25 [figure, visual read])
- The ONLY component shown is "10nF" from VGG_PA (pin 7) to GND. VGG_PA is fed from "−1.75V TO −0.25V".
- VDD_PA (pin 8) goes to "+5V" with no capacitor drawn.
- Top rail [visual read]: pin 19 VDD_SW "+3.3V"; pin 20 CTRL_SW "0V/+3.3V"; pin 21 VSS_SW "−3.3V"; pin 23 VGG_LNA "0V"; pin 24 VDD_LNA "+3.3V". Pin 22 and PAD go to GND.
- NIC pins 9 and 10 are tied to the GND bus, as are all GND pins.
- RX_OUT goes to "RECEIVE PATH OUTPUT", TX_IN to "TRANSMIT PATH INPUT", ANT to the antenna, and CPLR_OUT (pin 12) to "COUPLED OUTPUT". No DC blocks are drawn.
- DC blocks (p.23): ANT "no dc block is required … when the RF line potential is equal to 0 V". RX_OUT is "dc-coupled to ground through an 8 kΩ resistor"; TX_IN is "dc‑coupled to ground through a 2.5 kΩ resistor". In each case "No dc block is required … when the RF line potential is equal to 0 V".
- Bulk/HF decoupling on VDD_PA, VDD_LNA, VDD_SW and VSS_SW: NOT IN DATASHEET (none drawn). The evaluation board ADTR1107-EVAL is only referenced (p.27).

## Thermal resistance (Table 7, p.6)
- CC-24-8: θJC Transmit State "52.7" °C/W; θJC Receive State "198.4" °C/W. Footnote: "simulated values are based on a JEDEC 2S2P thermal test board with 36 thermal vias."
- θJA: NOT IN DATASHEET.

## Pin typing notes for the CSV
- NIC (pins 9, 10) is typed `passive`, not `no_connect`. The datasheet says "Solder these pins to a low impedance ground plane" and Fig 89 ties them to GND. A no_connect type would raise a KiCad ERC error when wired to GND.
- EPAD is listed as pin "EP" (the table prints no number) and typed power_in (ground).
