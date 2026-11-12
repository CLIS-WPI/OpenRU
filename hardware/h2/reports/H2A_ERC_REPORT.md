# H2-A Schematic ERC report

- **Tool:** KiCad 9.0.9 `kicad-cli sch erc`, run through the `run_erc` function of mcp-server-kicad 0.21.1, using the
  official `kicad/kicad:9.0` Docker image (KiCad is not installed on the host).
- **Raw output:** `H2A_ERC.json` and `openru_x6_tile-erc.json`.
- **Reproduce:** `tools/run_h2a_checks.sh`.

## Result: **ERC does NOT pass — 22 violations (all errors, 0 warnings)**

Hierarchy validation (`validate_hierarchy`): **ok, 0 issues** (21 sheets; no orphaned labels, no duplicate references).

Every violation is a pin that was **deliberately left unconnected** because its circuit could not be verified, and each
maps to an item in `H2A_UNRESOLVED_ISSUES.md`. No unexplained ERC violation remains.

| Violations | Pins | Unresolved item | What closes it |
|---|---|---|---|
| 4 | U501 CPOUT, VTUNE (×2: not connected + not driven), RS_SW | U8 loop filter | ADIsimPLL loop-filter design for 10 MHz PFD, 6.6 GHz |
| 4 | U502 VD1, VD2 (not connected + power not driven) | U9 AVA-183A+ bias network | wire AVA-183A+ Fig 2 / PL-328 bias tee (L1 3.3 nH, C1–C4) |
| 8 | U621–U624 QOD, CT | U20 TPS22810 slew/discharge | values from TI TPS22810 datasheet |
| 6 | U702 CWD, CRST, SET0, SET1 (SET0/SET1 also not driven) | U25 TPS3430 timing | window timing from TI TPS3430 datasheet |

## What ERC cannot see (not covered by this report)

- **Unconnected-by-design pins:** pins with an explicit no-connect flag, where the datasheet allows them to be left
  open or the part is a placeholder:
  - ADF4371 RF16P/N, RF32P/N, VCC_REG_OUT;
  - ADAR1000 TR_SW_NEG, TR_POL;
  - AVA-183A+ "NOT USED" pads;
  - placeholder PG outputs;
  - spare MCU GPIOs.
  `H2A_PIN_INTERFACE_VERIFICATION.csv` lists all 42 such pins (check `unconnected`).
- **Missing decoupling** (ADAR1000 AVDD1/AVDD3; ADTR1107 VDD_PA/VDD_LNA/VDD_SW/VSS_SW; STM32). The nets are
  electrically complete, so ERC raises nothing.
- **Placeholder regulators** (`TBD_REG_*`, `TBD_NEG_RAIL_MON`) satisfy the "power output" rule only because they are
  placeholders.
- **Footprints:** custom ICs, Mini-Circuits parts and SMA connectors have no footprint (U1, U3, U7, U10). ERC does not
  check footprints. DRC and layout are out of scope.

## Netlist verification (beyond ERC)

`tools/verify_netlist.py` compares the KiCad-exported netlist (`openru_x6_tile.xml`) against the datasheet pin tables,
the topology-A feed map and the intended interfaces. It reports **0 failures**:

| Check | Pass | Fail |
|---|---|---|
| symbol pin number ↔ datasheet name (10 custom parts, 44 instances) | 1088 | 0 |
| symbol pin count | 44 | 0 |
| ADAR1000 ↔ ADTR1107 (TX, RX, PA_BIAS→VGG_PA, DET←CPLR_OUT, TR_SW_POS→CTRL_SW, LNA_BIAS→VGG_LNA) | 96 | 0 |
| feed ownership vs `H1_FEED_POLARIZATION_MAP.csv` | 16 | 0 |
| front-end rails | 96 | 0 |
| RF / IF / LO / cal paths | 36 | 0 |
| ADAR1000 control + unique chip addresses | 48 | 0 |
| mixer supply / enable | 12 | 0 |
| safety interlocks + default pull-downs + per-chain drain gating | 21 | 0 |
| unconnected pins all declared | 42 | 0 |

**Limits of this check:**
- It proves the schematic matches the transcribed datasheet tables and the stated design intent.
- It does not prove the tables were transcribed correctly. Each table was extracted from the PDF text and grep
  self-checked; an independent second read (rendered pin figures + tables, built blind, then diffed) found **no mismatch** for ADAR1000 (88 + EP), ADF4371 (48 + EP), LTC5553 (12 + EP) or ADTR1107 (24 + EP). A human review is still recommended before sign-off.
- It does not prove the design intent is right; that is the purpose of the review report.
