# H2-C power tree: implementation report (IMPL_POWER)

All edits were made through the KiCad MCP tools. Nothing was committed.

## What was done
- **Expected netlist.** `expected_power.json` was generated from POWER_SPEC + AMENDMENTS before anything was placed. It has 116 parts and was produced by `tools/gen_expected.py`. A pin value of "NC" means the pin is intentionally left unconnected.
- **A6.** U601–U609 were removed from `power.kicad_sch`, together with their 38 pin-stub labels, their 38 stub wires and 5 NC flags (on the PG pins of U602–U606). Nothing else on power.kicad_sch changed.
  - NEG_OK now survives only as the R601 global label, so it has no driver yet. This is expected.
- **New sheets.** Three sheets were added on the root at y = 199.39: PWR_MAIN (`pwr_main.kicad_sch`, A2), PWR_LO (`pwr_lo.kicad_sch`, A3) and PWR_NEG (`pwr_neg.kicad_sch`, A2). The sheets have no pins; nets cross sheets through global labels.
- **pwr_main:** U650, U651, U652, U653 + C650–C687, L650–L652, R650–R662, #FLG650–652.
- **pwr_lo:** U654, U655, U656 + C688–C700, C761, L653, R663, R664, #FLG653.
- **pwr_neg:** U657, U658, U659, U913 + C762–C782, L654, L655, D650, D651, R666–R670, R672–R675, #FLG654, #FLG655.
- **Global labels.** Every cross-sheet net is a passive global label at its stub end: VIN_12V, GND, all rails, PWR_EN_3V3/5VPA/LO/NEG, PG_3V3RF. No local label shares a name with a global one. All PWR_* internal nets are local.
- **Datasheet note.** Each new sheet has a text note citing the TI datasheets.

## Deviations from the spec
1. **C701–C722 renumbered to C761–C782** (+60). `mcu.kicad_sch` already holds C701 (100nF) and C702 (0.1uF), and AMENDMENTS A4 reserves C703+ for MCU decoupling. wire_pins_to_net refused with [dup_ref]. The mapping is C701→C761 (+3V3_LO NR) and C702..C721→C762..C781. The JSON reflects this remap.
2. **A2: U657 ENN (pin 10) goes to local net PWR_ENN_NEG**, driven by U913 pin 4 (Y). U913 inputs: pin 1 = PWR_EN_NEG, pin 2 = PG_3V3RF. Supply: pin 5 = +1V8_DIG, pin 3 = GND. Footprint SOT-23-5, MPN SN74LVC1G08DBVR. The MPN is my choice; the amendment names only the part.
3. **Added C782**, 100nF 0402, as the U913 VCC bypass (+1V8_DIG to GND). Neither the spec nor the amendment lists it; it is the standard logic-gate bypass. No 74LVC1G08 datasheet was downloaded to cite it.
4. **A3: R665 and R671 were not placed.**
5. **U651 PGOOD (pin 9) is left unconnected, with no NC flag.** The spec says "no-connect", but the TPS568230 datasheet (SLVSEY5C) never says PGOOD may be left open, so the no-flag rule applies. It gives one ERC pin_not_connected error. Options: NC flag it, tie it to GND, or route it to the MCU with a 100k pull-up to +1V8_DIG.
6. **Footprints and MPNs not set.**
   - L650 and L651 have no footprint or MPN; both are UNRESOLVED in the spec.
   - Passive MPNs marked "TBD" were left empty.
   - DNP parts C685 and C695 carry "DNP" only in their Value; the KiCad DNP attribute was not set.
7. **Two values differ from their spec text.**
   - C767 (spec C707) is "220nF 6.3V X5R"; the spec says "6.3V+".
   - C672–C676 are "47µF 16V X5R/X7R", as the spec gives.
8. **PWR_EN_AUX is a local net.** It is only the internal UVLO divider node of U652.

## NC flags added (each quoting the datasheet)
| Pins | Datasheet text |
|---|---|
| U652 pin 1 (RT), U654 pin 1 (RT) | TPS62933 SLUSEA4D Table 7-1: "Float for 500 kHz" |
| U655 pins 4, 5, 8, 9, 11, 12; U656 pins 4, 5, 6, 9, 10 (unused ANY-OUT pins) | TPS7A47 SBVS204G pin table: "If not used, leave this pin floating." |
| U657 pin 7 (BSW) | TPS65131 SLVS493E §8.2.2.5: "If there is no intention to use an external PMOS, leave the BSW pin floating." |

Pins left open with no flag, because their KiCad pin type is no_connect so ERC does not flag them:
- U653 pin 4 (TLV755P: "No internal connection")
- U657 pins 12 and 20 (TPS65131: "Not connected")

## PWR_FLAGs added
| Flag | Net | Why |
|---|---|---|
| #FLG650 | +3V3_RF_SRC | fed through L650 |
| #FLG651 | +5V_PA | fed through L651 |
| #FLG652 | +3V3_AUX | fed through L652 |
| #FLG653 | PWR_6V2_LO | fed through L653 |
| #FLG654 | PWR_VNEG | fed through D651 and L655 from OUTN |
| #FLG655 | PWR_VIN_NEGCONV | fed through R666 (RC filter) |

VIN_12V and GND already had flags on power.kicad_sch (#FLG601 and #FLG602).

## Checks
- **validate_hierarchy (root):** ok, 0 issues.
- **run_erc (root):** 6 violations. The report is in erc_power/.
  - Mine: pin_not_connected on U651 pin 9 (PGOOD). See deviation 5.
  - Not in my scope and not touched: pin_not_connected on U501 pin 3 (RS_SW).
  - Not in my scope and not touched: pin_to_pin on U621–U624, where pin 2 (QOD, open collector) is tied to pin 1 (VOUT, power output), on power.kicad_sch.
  - There are no power_pin_not_driven errors and no label errors.

## Open items for the caller
- **The A4 periph work must not use C703+ blindly.** C701 and C702 already exist on mcu.kicad_sch. My parts now occupy C761–C782.
- **The interlock block must drive NEG_OK.**
- **U651 PGOOD needs a decision** (deviation 5).
