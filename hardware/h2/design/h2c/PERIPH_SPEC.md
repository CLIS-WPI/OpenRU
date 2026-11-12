# OpenRU H2-C: peripheral and decoupling verification (PERIPH_SPEC)

Date: 2026-11-12. This is a research note only. No KiCad files were changed and nothing was committed.
Status words: **VERIFIED** = matches the manufacturer document. **WRONG** = conflicts with it (the fix is given). **UNRESOLVED** = the document is unavailable or does not give the value. **NOTE** = engineering comment, not a datasheet value.

## Sources

| ID | Document | Revision / date | URL / location |
|---|---|---|---|
| S1 | ADI ADAR1000EVAL1Z "Stingray" schematic, drawing 02_059522 | Rev B, sheet 4 of 19 ("Customer Evaluation Z", Products ADAR1000/ADTR1107). PDF created 2021-06-07. The wiki labels it the "Rev. B/C schematic". | https://wiki.analog.com/_media/resources/eval/user-guides/stingray/02_059522b_top.pdf (linked from https://wiki.analog.com/resources/eval/user-guides/stingray/userguide) |
| S2 | ADI Stingray BOM, 05-059522-01-b.csv | Rev b, dated 09/28/2020 | https://wiki.analog.com/_media/resources/eval/user-guides/stingray/059522b_bom.zip |
| S3 | ST DS12589 STM32G431x6/x8/xB datasheet | **Rev 2** (Oct 2019, 200 pp). ST's own server timed out, so this is an LCSC mirror of the ST PDF. Newer revisions exist (Rev 6 seen in search results). | https://datasheet.lcsc.com/datasheet/pdf/3f23d741047d660d2a0e8aabbc953854.pdf (via https://www.lcsc.com/datasheet/lcsc_datasheet_2304140030_STMicroelectronics-STM32G431CBU6_C529356.pdf) |
| S4 | ST STM32_open_pin_data (ST-authored CubeMX pin database): `mcu/STM32G431C(6-8-B)Ux.xml`, `mcu/IP/GPIO-STM32G43x_gpio_v1_0_Modes.xml` | master at commit 7d1f151 (2026-06-29) | https://github.com/STMicroelectronics/STM32_open_pin_data |
| S5 | TI INA226 datasheet | SBOS547C, revised Aug 2026 | local: scratchpad/ds2/ina226.pdf |
| S6 | TI PCA9306 datasheet | SCPS113O, revised Sep 2023 | local: scratchpad/ds2/pca9306.pdf |
| S7 | TI TMP117 datasheet | SNOSD82D, revised Sep 2022 | https://www.ti.com/lit/ds/symlink/tmp117.pdf |
| S8 | ADI ADTR1107 data sheet Rev C, ADAR1000 data sheet Rev B (summarized in local notes) | as noted | openru-x6-sim/hardware/h2/datasheet_pins/{adtr1107,adar1000}_notes.md |

**Not obtained (UNRESOLVED):** the ADAR1000-EVALZ user guide (UG-1283), its schematic (Rev C/D/E), and the ADTR1107-EVALZ user guide (UG-1684).
- analog.com timed out, as expected. The manualmachine, manuals.online and manualzz mirrors returned HTTP 403.
- ADI's cldnet CDN host was not tried because a permission rule blocked it as a bypass of analog.com.
- Search snippets mention an ez.analog.com forum reply that recommends "4.7 µF per ADTR1107" on +5 V. That is an informal forum answer and was not read, so it is not used below.

---

## A. Decoupling for ADAR1000 and ADTR1107 (from the Stingray tile, S1 sheet 4 + S2 BOM)

S1 sheet 4 is one "tile": U1_x ADAR1000 + U2_x..U5_x ADTR1107 (preliminary part `ADTR1107OPT2`). The board has 8 copies of this tile (suffix _1.._8).
- The tile has a block labeled **"DECOUPLING"** (sheet 4, zones D-C/7-6) that holds per-rail capacitors for the tile. These are not tied to one pin.
- Separately, there is a 1 µF capacitor on each CREG pin and a 4.7 µF capacitor at each ADTR1107's VDD_PA.
- Net mapping on the sheet: ADAR1000 AVDD3 (M10, M11, N11) = `+3.3V`, AVDD1 (B11) = `-5.0V`. ADTR1107 VDD_SW = `+3.3V`, VDD_LNA = `+3.3V`, VSS_SW = `-3.3V`, VDD_PA = `+5.0V`, VGG_PA = `PAx_BIAS` (from ADAR1000), VGG_LNA = `LNA_BIAS`, CTRL_SW = `TR_SW_POS`.

| Device pin / rail (Stingray net) | Ref (tile _1) | Value | Dielectric / rating / pkg (BOM S2) | MPN (S2) | Status |
|---|---|---|---|---|---|
| ADAR1000 AVDD3 M10/M11/N11 (+3.3V) and ADTR1107 VDD_SW / VDD_LNA (+3.3V) | C12_1, C13_1, C14_1 (shared tile block) | 1 µF + 0.01 µF + 100 pF | 1 µF: X7R 6.3 V 10 % 0402. 0.01 µF: X7R 10 V 10 % 0201. 100 pF: C0G 50 V 5 % 0201 | GRM155R70J105KA12D / GRM033R71A103KA01D / GRM0335C1H101JA01D | VERIFIED (S1 sh.4; S2 items 7/4/6) |
| ADAR1000 AVDD1 B11 (−5.0V) | C17_1, C18_1 (shared tile block) | 0.01 µF + 100 pF | 0.01 µF: X7R 10 V 0201. 100 pF: C0G 50 V 0201 | GRM033R71A103KA01D / GRM0335C1H101JA01D | VERIFIED. No bulk capacitor at the tile. |
| ADTR1107 VSS_SW (−3.3V) | C15_1, C16_1 (shared tile block) | 0.01 µF + 100 pF | 0.01 µF: X7R 10 V 0201. 100 pF: C0G 50 V 0201 | as above | VERIFIED |
| +5.0V rail (ADTR1107 VDD_PA), tile level | C9_1, C10_1, C11_1 (shared tile block) | 1 µF + 0.01 µF + 100 pF | 1 µF: **X7R 6.3 V** 0402. 0.01 µF: X7R 10 V 0201. 100 pF: C0G 50 V 0201 | GRM155R70J105KA12D / GRM033R71A103KA01D / GRM0335C1H101JA01D | VERIFIED |
| ADTR1107 VDD_PA, one per device | C5_1 (U2_1), C6_1 (U3_1), C7_1 (U4_1), C8_1 (U5_1) | 4.7 µF | **X5R 6.3 V** 20 % 0201 (JEDEC C0201H22) | GRM035R60J475ME15D | VERIFIED. A 300 dpi zoom shows C5_1 on the +5.0V/VDD_PA trace, not on PA1_BIAS. |
| ADAR1000 CREG1 M8, CREG2 M9, CREG3 N10, CREG4 N9 | C1_1..C4_1 | 1 µF each | X5R 10 V 20 % 0201 | Samsung CL03A105MP3NSNC | VERIFIED. Matches the ADAR1000 datasheet's 1 µF (S8). |
| ADTR1107 VGG_PA (PAx_BIAS) | none on Stingray sheet 4 | — | — | — | The Stingray board drives VGG_PA straight from ADAR1000 PA_BIASx with no capacitor. The ADTR1107 datasheet (Rev C, Fig. 89, p.25) shows 10 nF. ADAR1000 PA_BIAS is specified for a 1 nF load (60 ns, ADAR1000 p.7). Keep the 10 nF from the datasheet. |
| ADTR1107 VGG_LNA (LNA_BIAS) | none | — | — | — | Stingray has no capacitor here. The datasheet lists none (UNRESOLVED / not required by either source). |
| ADTR1107 CTRL_SW | none | — | — | — | No capacitor. |

Coverage and caveats:
- **Per-pin values for AVDD3 and AVDD1 are UNRESOLVED.** Neither the ADAR1000 datasheet nor Stingray assigns a capacitor to a specific pin. Stingray places one tile-level set per rail (shown above) for 1 ADAR1000 + 4 ADTR1107. The sheet does not show placement distance; layout files were not retrieved.
- ADAR1000-EVALZ (UG-1283) and ADTR1107-EVALZ (UG-1684) values: **UNRESOLVED** (documents not reachable, see Sources).
- NOTE: Stingray uses 6.3 V parts on the +5.0 V rail: 1 µF X7R 0402 and 4.7 µF X5R 0201. Under DC bias their effective capacitance falls a lot. If H2-C copies the values, choose ≥10 V-rated parts of the same nominal value (this is a design judgment, not an ADI statement).
- NOTE: The board-level power tree regulators (LT8652S, LT8642S, LT3093, LT3094, LT8606, ADP150-1.8, ADP5074, per the wiki user guide) carry their own bulk capacitors. Those are on other sheets and were not extracted.

---

## B. STM32G431CBU6 (UFQFPN48) — S3 (DS12589 Rev 2) + S4

Pin numbers come from DS12589 Fig. 7 (p.45) and Table 12 (pp.51-60, UFQFPN48 column), and agree with S4. AF numbers come from DS12589 Table 13 (pp.61-62) and S4.

| Function | Pin (UFQFPN48 #) | Finding | Status |
|---|---|---|---|
| SPI1_SCK | PA5 (13) | AF5 | VERIFIED |
| SPI1_MISO | PA6 (14) | AF5 | VERIFIED |
| SPI1_MOSI | PA7 (15) | AF5. The bidirectional 1-line mode, where the master uses MOSI as the data line, is described in RM0440, which was not retrieved. | Pin VERIFIED. The half-duplex behavior is UNRESOLVED (RM0440 needed). |
| I2C1_SCL | PA15 (38) | AF4. PA15 is FT_f. | VERIFIED |
| I2C1_SDA | PB7 (45) | AF4. FT_f. | VERIFIED |
| Timer out PA8 | PA8 (30) | TIM1_CH1 (AF6). This is the only timer channel on PA8; it also carries TIM4_ETR, an input. | VERIFIED |
| Timer out PA9 | PA9 (31) | TIM1_CH2 (AF6) **or TIM2_CH3 (AF10)** | VERIFIED. See the NOTE below. |
| PPS input capture | PB3 (41) | TIM2_CH2 (AF1). Also TIM8_CH1N (output only), TIM3_ETR, TIM4_ETR. | VERIFIED (TIM2_CH2, 32-bit TIM2) |
| BOOT0 | PB8-BOOT0 (46) | Pin name "PB8-BOOT0". Footnote 5: set PB8 to a mode other than analog after startup if it is left unconnected. | VERIFIED |
| NRST | PG10-NRST (7) | | VERIFIED |
| SWDIO / SWCLK | PA13 (36) / PA14 (37) | AF0 SYS_JTMS-SWDIO / SYS_JTCK-SWCLK | VERIFIED |
| Plain GPIO: PB0(17) PB1(18) PB2(19) PB10(22) PB11(24) PB12(25) PB13(26) PB14(27) PB15(28) PB4(42) PB5(43) PB6(44) PC13(2) PC14(3) PA0(8) PA1(9) PA2(10) PA3(11) PA4(12) PA10(32) | all present as I/O on UFQFPN48 | | VERIFIED (see restrictions below) |

NOTE on one-shot pulses. PA8 and PA9 are both on TIM1 (CH1/CH2). One-pulse mode in STM32 timers is a property of the whole counter (TIMx_CR1.OPM, RM0440 not retrieved). So two channels on TIM1 cannot fire fully independent one-shots. **Recommendation:** PA8 = TIM1_CH1 (AF6), PA9 = TIM2_CH3 (AF10). That gives two separate timers.
- Caution: TIM2 is then also used for PB3 PPS capture (TIM2_CH2). If the PPS capture needs TIM2 free-running while a TIM2 one-shot runs, move the PPS to a different timer, or move the second pulse to another pin with TIM15/16/17/TIM3/TIM8.
- Pins without a timer channel: PA10 is TIM1_CH3 / TIM2_CH4. PB6 is TIM4_CH1 / TIM8_CH1. PB4 is TIM3_CH1 / TIM16_CH1.

Restrictions (DS12589 Table 12 footnotes, p.60):
- **PC13 / PC14 / PC15:** VERIFIED as restricted. Footnote 2: "supplied through the power switch. Since the switch only sinks a limited amount of current (3 mA), the use of GPIOs PC13 to PC15 in output mode is limited: speed should not exceed 2 MHz with a maximum load of 30 pF; must not be used as current sources (e.g. to drive an LED)."
  - Footnote 3: after a Backup-domain power-up they work as GPIOs, but their function depends on RTC registers that a system reset does not clear (RM0440).
  - PC14 is also OSC32_IN, so do not enable the LSE.
  - These pins are fine for slow inputs or low-current sinking outputs.
- **PA13, PA14, PA15, PB3, PB4:** footnote 4: "After reset, these pins are configured as JTAG/SW debug alternate functions, and the internal pull-up on PA15, PA13, PB4 pins and the internal pull-down on PA14 pin are activated."
  - So PA15 (JTDI), PB4 (NJTRST) and PB3 (JTDO/SWO) are **not** I2C, GPIO or timer pins until firmware reprograms GPIOx_MODER/AFR. Once reprogrammed they are usable (AF numbers per S4).
  - Until init, PA15 and PB4 have their internal pull-ups on. PA15 as I2C1_SCL sits high, which is harmless. Footnote 4 lists no pull for PB3. If SWO trace is enabled, the debugger owns PB3, so do not use SWO while PB3 carries the PPS signal.
  - Status: VERIFIED usable after firmware reconfiguration.
- **PB4 / PB6 are FT_c (UCPD CC pins). PA9 / PA10 are "_d" (UCPD1_DBCC1/2, dead-battery).**
  - FT_c pins have VIN max 5 V (Table 17), not 5.5 V.
  - DS12589 Rev 2 does not describe what the dead-battery logic does to PB4/PB6 at reset: **UNRESOLVED**. Check RM0440 (PWR_CR3.UCPD_DBDIS) and disable dead-battery in early firmware before using PB4/PB6 as GPIO.

Decoupling (DS12589 Fig. 16 "Power supply scheme", p.68):

| Supply pin (UFQFPN48) | ST figure | Count for this package |
|---|---|---|
| VDD pins 23, 35, 48 | "n x 100 nF + 1 x 4.7 µF" | 3 × 100 nF (one per VDD pin) + 1 × 4.7 µF |
| VDDA pin 21 | "10 nF + 1 µF" | 1 × 10 nF + 1 × 1 µF |
| VREF+ pin 20 | "100 nF + 1 µF" | 1 × 100 nF + 1 × 1 µF |
| VBAT pin 1 | No capacitor is drawn; it is shown with a 1.55–3.6 V source | UNRESOLVED (ST gives no value). NOTE: the common ST practice of 100 nF when VBAT is tied to VDD comes from other-family app notes, not DS12589. |
| VSS / VSSA | "VSS pads are connected to the exposed pad" (Fig. 7 note 2, p.45). UFQFPN48 has no VSS or VSSA pin, and the 48-pin list in S4 has none. | EP must go to GND |

Caution (p.68): "Each power supply pair … must be decoupled with filtering ceramic capacitors as shown above … placed as close as possible to, or below, the appropriate pins". The dielectric and package are not specified.

Operation at VDD = 1.8 V (DS12589):
- VDD range 1.71–3.6 V (Table 17, p.71; §3.11.1 p.21). fHCLK up to 170 MHz has no VDD condition in Table 17. 170 MHz needs Range 1 boost (§3.11 p.22). **VERIFIED: runs at 1.8 V at 170 MHz.**
- SPI (Table 85, p.156): master fSCK max 50 MHz at 1.71–3.6 V (75 MHz only at 2.7–3.6 V). OK.
- I2C: Table 8 (p.38) and Table 84 set no VDD minimum beyond the general range. The I/Os are not true open-drain because the PMOS stays present. If a pin is pulled above Min(VDD, VDDA)+0.3 V, the internal pull-ups must be disabled (Table 17 note 3).
- ADC (Table 62): VDDA ≥ 1.62 V. fADC max is 42 MHz with all ADCs single-ended at VDDA ≥ 1.62 V (52 MHz needs ≥ 2.7 V). **When VDDA < 2 V, VREF+ must equal VDDA** (§3.11.1). Tie VREF+ to VDDA.
- VREFBUF needs VDDA ≥ 2.4 V and OPAMP needs ≥ 2.0 V (Table 17), so neither works at 1.8 V. The DAC is OK from 1.71 V. The analog-switch booster must be enabled when VDDA < 2.4 V (Table 62 note 2, SYSCFG_CFGR1.BOOSTEN).
- Flash (Table 48, p.111): no VDD condition is listed for programming or erase. VERIFIED (no restriction stated).
- BOR lowest level is 1.71 V at power-on (§3.11.2). A 1.8 V rail has only ~90 mV margin above BOR0, so rail tolerance must stay above 1.71 V. **NOTE:** a 1.8 V ±5 % rail (1.71 V min) is exactly at the limit.

---

## C. INA226 (S5, SBOS547C)

Address table (Table 6-2, p.18), 7-bit:

| A1 \ A0 | GND | VS | SDA | SCL |
|---|---|---|---|---|
| GND | 0x40 | 0x41 | 0x42 | 0x43 |
| VS | 0x44 | 0x45 | 0x46 | 0x47 |
| SDA | **0x48** | **0x49** | 0x4A | 0x4B |
| SCL | 0x4C | 0x4D | 0x4E | 0x4F |

TMP117 (S7, Table 7-2, p.21): ADD0 = GND gives 0x48, V+ gives 0x49, SDA gives 0x4A, SCL gives 0x4B.

- Planned straps use A1 ∈ {GND, VS}, A0 ∈ {GND, VS}, plus one with A0 = SDA. These give 0x40 / 0x41 / 0x44 / 0x45 and 0x42 (A1 = GND) or 0x46 (A1 = VS).
- **No conflict** with TMP117 0x48/0x49, because the PCA9306 joins both segments into one address space. VERIFIED.
- Conflict appears only if any INA226 has **A1 = SDA** (0x48–0x4B).
- Check the netlist: "U610 GND/GND and U611 GND/GND" as written in the brief are both **0x40, a duplicate**. If that is literal, it is **WRONG**. Give each INA226 a unique combination.
- The datasheet says the pins are sampled on every bus transaction (p.18), so a strap to SDA/SCL must be a direct connection.

Other INA226 items:
- VS decoupling: "A typical value for this supply bypass capacitor is 0.1 µF" (§8.3, p.31). Fig. 6-3 (p.14) also shows 0.1 µF. VERIFIED: 0.1 µF at VS.
- VS range: 2.7–5.5 V (p.1 features, §6.3). Absolute max 6 V (p.4). VSCL abs max is VVS + 0.3 V (p.4), so the 3.3 V-side placement is correct.
- Bus / common-mode voltage: 0–36 V operating ("Do not apply more than 36 V", p.5 note 1, p.11). Abs max 40 V (p.4). IN+/IN– must stay within −0.3 V to 40 V, so the INA226 **cannot sense the −5 V / −3.3 V rails**. It is fine on +5 V and +3.3 V.
- Input filter (§6.3.x, p.14, Fig. 6-3): needed only for transients at harmonics of the 500 kHz sampling rate. Use "≤ 10 Ω" series resistors and a differential capacitor of "0.1 µF to 1 µF". 10 Ω series resistors also protect against dV/dt during short-circuit events (p.14).
- Shunt scaling: full-scale ±81.92 mV, LSB 2.5 µV (p.5, p.24). CAL = 0.00512 / (Current_LSB × R_SHUNT) (Eq. 1, p.15).
  - With 10 mΩ: I_max = 81.92 mV / 10 mΩ = **8.19 A**, resolution 2.5 µV / 10 mΩ = 0.25 mA.
  - 1.2 A per PA chain: 12 mV, 14.6 % of full scale, 14.4 mW in the shunt. OK. NOTE: resolution is still 0.25 mA. If finer IDQ trims are wanted, 20–50 mΩ would make better use of the range (50 mΩ gives 1.64 A full scale).
  - ~4 A on +3V3_RF: 40 mV, 49 % of full scale, 0.16 W. That is a 1.2 % drop on 3.3 V, so use a ≥0.5 W, 1206-or-larger Kelvin shunt.
  - Verdict: **10 mΩ is appropriate for both** (NOTE: engineering judgment).

---

## D. PCA9306 (S6, SCPS113O)

| Item | Datasheet | Planned | Status |
|---|---|---|---|
| VREF1 = low side | Fig. 9-1 (p.17): "VREF1 = 1.8 V", pin 2 | +1V8_DIG | VERIFIED |
| VREF2 tied to EN, 200 kΩ to VDPU | Fig. 9-1: EN (8) tied to VREF2 (7), 200 kΩ to "VDPU = 3.3 V". §9.2.2.1 (p.18): "EN input must be connected to VREF2 and both pins pulled to high-side VDPU through a pullup resistor (typically 200 kΩ)" | VREF2 = EN, 200 k to +3V3_AUX | VERIFIED |
| VREF2 filter capacitor | §9.2.2.1: "A 100-pF filter capacitor connected to VREF2 is recommended." | not listed in plan | **MISSING. Add 100 pF from VREF2/EN to GND.** |
| Voltage constraint | ROC note 1 (p.5): "VREF1 supports 1.2 V to VREF2 − 0.6 V. VREF2 must be between VREF1 + 0.6 V to 5.5 V". Design requirements table (p.18): VREF2/EN min = VREF1 + 0.6 V. EN must be ≥ 0.6 V above SCL/SDA to conduct (§8.4). | 1.8 V / 3.3 V | VERIFIED. The constraint is **−0.6 V, not −1 V**. In the 200 k configuration VREF2 self-biases to VREF1 + Vth ≈ 2.4 V (Eq. 1, p.15). |
| Pull-ups | Pull-ups are needed on both sides: SCL1/SDA1 to VREF1, SCL2/SDA2 to VDPU (§8.3.2, §9.1.1). Values come from SLVA689 / Fig. 9-3 and 9-4 (p.20). Rp(min) at VDPU ≤ 2 V: VOL = 0.2·VDPU at IOL = 2 mA, which is ≈ 720 Ω at 1.8 V. At > 2 V: VOL 0.4 V at 3 mA, which is ≈ 967 Ω at 3.3 V. | 4.7 k on 3.3 V, 2.2 k on 1.8 V | VERIFIED as within limits. When the low side pulls down, the sink current is 3.3/4.7k + 1.8/2.2k ≈ 1.52 mA. That is below 2 mA (1.8 V device IOL) and the 6 mA pass-current design value (p.18). Rp(max) depends on bus capacitance (Fig. 9-3); check it once Cb is known. |
| VREF1 LDO bias current | §8.1.7 (p.14-15): Ibias = (VCC2 − Ven)/200 k with Ven = VREF1 + 0.6 V, so (3.3 − 2.4)/200 k ≈ 4.5 µA flows into VREF1. If the LDO cannot sink it, add Rpulldown = 0.75 × VOUT/Ibias ≈ 300 kΩ. | +1V8_DIG also feeds the MCU and TMP117 | OK. The rail's own load sinks 4.5 µA, so no pull-down is needed unless +1V8_DIG can be unloaded while +3V3_AUX is up. |

Overall: the planned PCA9306 circuit **matches Fig. 9-1 except that the recommended 100 pF on VREF2 is missing**.

---

## Summary of action items
1. Add 10 nF on each ADTR1107 VGG_PA. The datasheet requires it; Stingray omits it.
2. Use the Stingray tile-level decoupling sets as the baseline (table A). Use ≥10 V-rated parts on +5 V.
3. Move the PA9 one-shot to TIM2_CH3 (AF10), or another timer, so the two pulses are on independent timers. Resolve the TIM2 sharing with PPS capture on PB3.
4. Firmware must reconfigure PA15/PB3/PB4 away from JTAG after reset, and disable UCPD dead-battery before using PB4/PB6 (check RM0440).
5. Tie VREF+ to VDDA. Do not use VREFBUF or OPAMP at 1.8 V. Keep the 1.8 V rail above 1.71 V (BOR0).
6. Make the INA226 straps unique. Never use A1 = SDA (it collides with TMP117 0x48/0x49).
7. Add 100 pF on PCA9306 VREF2/EN.
