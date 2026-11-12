# H2-C PA-drain interlock: implementation report (IMPL_INTERLOCK)

Everything was done through the KiCad MCP tools. Nothing was committed.

## What was done
- **Expected netlist first.** `expected_interlock.json` (104 parts, U705 included) was generated from INTERLOCK_SPEC §9 + AMENDMENTS A1/A3/A6 by `tools/gen_expected_interlock.py` before any placement. "NC" means the pin is intentionally open.
- **New sheet.** `interlock.kicad_sch` (A1 841x594 mm), block "PA_INTERLOCK" on the root at (30.48, 259.08), with no sheet pins. Every cross-sheet net is a passive global label at its stub end.
- **Parts on interlock.kicad_sch:**
  - U900–U908 LM339B, U909 SN74LVC1G74, U910 SN74LVC1G17, U911 SN74LVC1G11.
  - U912 SN74LVC1G08 (A1). U914 TPS22917DBV (A1; U913 is already taken on pwr_neg).
  - R900–R972, C900–C915.
  - Every part has its Footprint and MPN set.
- **A1 (IL_REF).**
  - The 16 gate-divider top legs (R901, R904 … R946) and R952/R954 (the LOST and PINCH reference tops) go to IL_REF.
  - IL_REF = U914 VOUT. U914: VIN = +1V8_DIG, ON = NEG_RAILS_OK, QOD to VOUT through R972 100 Ω, CT open.
  - Rail monitors stay on +1V8_DIG: R948/R950/R956/R958, plus R966 on +3V3_AUX. Their outputs (U908 ch A/B/C) drive NEG_RAILS_OK, pulled by R960 (10k to +3V3_AUX) and R961 (10k to GND).
  - The 16 gate-lost outputs drive GATES_OK, pulled by R968/R969 (10k/10k, new).
  - GATES_PINCHED keeps R962/R963.
  - U912 makes NEG_OK = NEG_RAILS_OK · GATES_OK. C913 is its bypass.
- **A3.** R965 100k from PA_DRAIN_EN to GND is placed on the interlock sheet, through the global label.
- **A6 / U705 (mcu.kicad_sch).**
  - Removed: the MCU_PA_EN global label at (121.92, 69.85) and its stub wire.
  - U705 pin 1 is now wired to the PA_ARMED global label.
  - Other pins are unchanged: 3 WDT_OK, 6 NEG_OK, 4 PA_DRAIN_EN, 5 +1V8_DIG, 2 GND.
  - MCU_PA_EN keeps the MCU pin and its existing pull-down on mcu.kicad_sch, and now also feeds U911 pin 1 and R964 on the interlock sheet.
- **R601 (power.kicad_sch).** Removed with remove_component, together with its NEG_OK and +1V8_DIG global labels and their two stub wires.
- **Text notes.** Two notes on the interlock sheet cover the thresholds, the logic equations, the fail-safe behaviour and the datasheet IDs.

## Deviations (with reasons)
1. **LM339 symbol.** `place_component` places only unit A of the 5-unit `Comparator:LM339`, and no MCP tool can place units B–E.
   - I added a single-unit symbol, `openru_x6:LM339B_1U`, to the project library `openru_x6.kicad_sym` with add_symbol. This file was not on the list of files to touch.
   - Its pin numbers and types match `Comparator:LM339`: (5+, 4−, 2), (7+, 6−, 1), (9+, 8−, 14), (11+, 10−, 13), V+ = 3, GND = 12, and the outputs are open_collector.
2. **NEG_OK pull-ups moved.** The spec put R960/R961 on NEG_OK. Under A1, NEG_OK is push-pull (U912), so R960/R961 now sit on NEG_RAILS_OK, and R968/R969 were added for GATES_OK.
3. **Extra parts beyond the spec.** These follow A1 and the datasheets:
   - U912 + C913 (100 nF bypass).
   - U914, plus C914 1 µF on its VIN ("using an input capacitance (CIN) of 1 μF is sufficient", SLVSDW8B §11).
   - C915 100 nF on IL_REF. This is my choice; the datasheet characterises with CL = 1 µF.
   - R972 100 Ω between QOD and VOUT. This is a datasheet option ("Placing an external resistor between VOUT and QOD", Table 6-1).
     - I used it instead of a direct short because KiCad flags open_collector QOD → power_out VOUT as a pin_to_pin error (the same error U621–U624 already show).
     - The discharge then runs through 150 + 100 Ω; with 100 nF that gives tFALL ≈ 2.2 × 250 × 0.1 µF ≈ 55 µs.
4. **U908 spare channel D.** The spec had IN− = IL_REF_PINCH and IN+ = GND directly. TI SNOAA35F §9.1.1 says "inputs must not be connected directly to ground or any other low impedance node".
   - Now: IN− (pin 10) → IL_SPARE_N → R971 10k → +3V3_AUX, and IN+ (pin 11) → IL_SPARE_P → R970 10k → GND. This is TI's "Ok: VOL Full VID" connection (§9.1.2, Fig 9-1).
   - Output pin 13 is NC-flagged (§9.1.3: "TI recommends leaving the unused output pins floating").
5. **Net names.** NEG_RAILS_OK, GATES_OK and GATES_PINCHED are single-sheet (local) nets, but I kept the names the spec and amendment give rather than adding an IL_ prefix. All other local nets are IL_*. New local nets: IL_REF, IL_QOD, IL_SPARE_N, IL_SPARE_P.
6. **C914 MPN.** Murata GRM155R61A105KE15D (1 µF 10 V X5R 0402). X5R was chosen because I am not sure an X7R 1 µF/10 V 0402 GRM exists. MPNs were not checked against stock.
7. **Layout.** Decoupling caps sit in one row (y = 292) rather than next to their ICs. This is schematic placement only.

## NC flags and PWR_FLAGs
| Pin | Datasheet basis |
|---|---|
| U908 pin 13 (spare output) | SNOAA35F §9.1.3: "TI recommends leaving the unused output pins floating." |
| U909 pin 3 (~Q) | SCES794G §11.1: "It is acceptable to float outputs unless the part is a transceiver." |
| U914 pin 4 (CT) | SLVSDW8B Table 6-1: "Can be left floating for fastest timing." |

- U910 pin 1 is NC in the symbol (KiCad type no_connect), so it has no flag.
- No PWR_FLAGs were added. All supplies are driven on other sheets, and ERC reports no power_pin_not_driven.

## TPS22917 facts (SLVSDW8B, Dec 2021; downloaded to interlock/ds/tps22917.pdf)
- **Pinout (DBV, Fig 6-1).** 1 VIN, 2 GND, 3 ON, 4 CT, 5 QOD, 6 VOUT. This matches KiCad `Power_Management:TPS22917DBV` exactly. The KiCad types are VIN power_in, GND power_in, ON input, CT output, QOD open_collector, VOUT power_out.
- **ON thresholds (ROC §7.3, VIN 1–5.5 V).** VIH ≥ 1.0 V, VIL ≤ 0.35 V. ON leakage is ±10 nA. The smart pull-down (RPD 750 kΩ) is active only while VON ≤ VIL.
  - NEG_RAILS_OK high = 1.57–1.73 V, so ON has ≥ 0.57 V margin above VIH ✓.
- **Ron at VIN = 1.8 V, 200 mA.** 150 mΩ typ, 175 mΩ max (−40…85 °C).
  - The IL_REF load is about 2 mA, so the drop is < 0.4 mV.
  - It is common to the gate dividers and the LOST/PINCH references, so the thresholds stay ratiometric.
- **Timing at 1.8 V.** tON = 200 µs typ with CT open; tR = 100 µs; tOFF = 10 µs typ.
- **QOD.** Internal resistance 150 Ω. QOD floating gives no discharge ("output remains floating"), so it is connected to VOUT through R972 (see deviation 3).
- **CT.** Floating is allowed (fastest). VCT rating ≥ 7 V if a capacitor is ever fitted.

## LM339B facts (SLCS006Z §6.1, plus TI SNOAA35F)
- **Abs max (B version).** Input pins −0.3 V … 38 V. Current into input pins: −50 mA.
- **Current when IL_REF is off.** IL_REF is discharged to about 0 V and the gate DAC can be at −4.8 V (−5.25 V at the AVDD1 limit).
  - The open-circuit node is −5.25 × (17.4k‖45.3k) / (49.9k + 12.56k) ≈ −1.06 V. In practice the input diode clamps it at about −0.4…−0.6 V.
  - The current is ≤ (5.25 − 0.4) / 49.9k ≈ 0.1 mA. That is 500× under the −50 mA abs max and under TI's "1 mA or less" recommendation (SNOAA35 §6.9.3: 1 kΩ per volt of over-voltage; we have about 9.5 kΩ/V).
- **Result.** The current limit is met. The −0.3 V voltage abs max is exceeded, but only current-limited, and that is the case TI's §6.9.3 clamp-resistor guidance covers.
- **But the output is undefined then.** SNOAA35 §6.9.2: input < −0.3 V "can cause parasitic device conduction … that results in incorrect output behavior". SLCS006Z note 5: "can cause output to be incorrect".
  - So GATES_OK and GATES_PINCHED are undefined while IL_REF is off. AMENDMENTS A1 says "GATES_OK reads low"; that is not guaranteed.
  - Safety still holds, because NEG_OK = NEG_RAILS_OK · GATES_OK and NEG_RAILS_OK is low in exactly that state.
  - U908, the only rail-monitor package, never sees negative inputs.

## ERC (root, project_path set; report in erc_interlock/)
- **validate_hierarchy (root):** ok, 0 issues.
- **run_erc:** 6 violations. All 6 match the IMPL_POWER baseline; none come from the interlock work.
  - pin_not_connected U501 pin 3 (RS_SW). Pre-existing.
  - pin_to_pin U621–U624: QOD open-collector tied to VOUT power-out (4 errors). Pre-existing, power.kicad_sch.
  - pin_not_connected U651 pin 9 (PGOOD). Pre-existing, from IMPL_POWER deviation 5.
- **Cross-sheet check.**
  - C{c}_PABIAS{k} also exist as global labels on fe{c}.kicad_sch (checked on fe1).
  - PA_ARMED is on mcu + interlock.
  - NEG_OK is on mcu + interlock, and R601 is gone.

## Open items and risks
1. **TPS22917 ON low level is not datasheet-guaranteed.** The LM339B VOL is ≤ 400 mV (25 °C) and ≤ 550 mV (−40…85 °C) at ISINK ≤ 4 mA (SLCS006Z p7). TPS22917 VIL max is 0.35 V.
   - At the real 0.33 mA sink, VOL is far below the 110 mV typ figure (which is at 4 mA), so this should work, but no spec line guarantees it.
   - If ON sat in the 0.35–1.0 V band, IL_REF could stay on during a negative-rail fault. That loses only the A1 positive-bias protection.
   - NEG_OK is still forced low, because LVC VIL = 0.35 × VCC ≥ 0.58 V > 0.55 V.
   - Options: a bench check, or a lower-VOL driver for ON.
2. **IL_REF on while the ADAR1000 is unpowered.** If the negative rails are good but the ADAR1000 is still unpowered, IL_REF is on and the +1.3 V/62.5 k injection (R1) still applies. A1 relies on the A2 hardware ordering to rule this out; I did not verify that here.
3. **Resistor and capacitor MPNs** were not checked against distributor stock.
4. **The behavioural sim was not rerun** with the A1 topology.
