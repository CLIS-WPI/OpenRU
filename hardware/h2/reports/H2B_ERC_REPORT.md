# H2-B ERC report

- **Tool:** KiCad 9.0.9 (host install, PPA `kicad-9.0-releases`), run through the MCP tool `run_erc`.
- **Raw report:** `openru_x6_tile-erc.json` (current). The H2-A baseline stays in `H2A_ERC.json`.
- **Hierarchy validation:** `validate_hierarchy` → ok, 0 issues.
- **Severity settings:** unchanged. No ERC severity was changed.
- **No-connect flags:** none added in H2-B.

## Result: **5 errors** (H2-A: 22)

| # | ERC item | Status | Why it remains |
|---|---|---|---|
| 1 | U501 pin 3 RS_SW — pin not connected | **UNRESOLVED** | ADF4371 Rev 0 only says "Used for switching loop filter resistors in fastlock applications." Whether it may be left open when fastlock is unused is not stated. Needs ADI / eval-board schematic (inquiry 7) |
| 2–5 | U621–U624 QOD (open collector) ↔ VOUT (power output) — pin_to_pin | **REVIEWED, datasheet-sanctioned** | TI TPS22810 pin table: QOD may be enabled by "Tying QOD directly to VOUT and using the internal resistor value (RPD)". KiCad flags it only because the library types QOD as open-collector and VOUT as power-output. Kept visible, not waived in KiCad |

## The 22 H2-A errors, one by one

| H2-A error | Disposition in H2-B | Source |
|---|---|---|
| U501 CPOUT — not connected | **Fixed:** CPOUT → C509 ∥ (R507 + C510) → R508 | loop filter DERIVED (`tools/loop_filter.py`); topology per ADF4371 pin table ("output of the loop filter is connected to VTUNE") |
| U501 VTUNE — not connected | **Fixed:** VTUNE = R508 / C511 node | same |
| U501 VTUNE — not driven | **Fixed** (driven through the loop filter) | same |
| U501 RS_SW — not connected | **Open** (#1 above) | — |
| U502 VD1 — not connected | **Fixed:** VD1 – C512 0.1 µF – L505 3.3 nH | AVA-183A+ Fig 2 |
| U502 VD1 — power pin not driven | **Fixed:** PWR_FLAG #FLG501 on the VD1 node, which is powered from +5V_LO through L505 (ERC cannot follow an inductor) | AVA-183A+ Fig 2 |
| U502 VD2 — not connected | **Fixed:** VD2 = +5V_LO with C513 1 nF, C514 18 pF, C515 5.6 pF | AVA-183A+ Fig 2 |
| U502 VD2 — power pin not driven | **Fixed** (+5V_LO is driven by U605) | — |
| U621–U624 QOD — not connected (×4) | **Fixed:** QOD tied to VOUT. This creates the 4 pin-type findings #2–5 | TPS22810 pin table |
| U621–U624 CT — not connected (×4) | **Fixed:** 2200 pF to GND | TPS22810 §7 test condition (CT = 2200 pF) |
| U702 CWD — not connected | **Fixed:** 10 kΩ to VDD | TPS3430 Table 6.6 |
| U702 CRST — not connected | **Fixed:** 10 kΩ to VDD (tRST 10 ms) | TPS3430 Table 6.6 |
| U702 SET0 — not connected / not driven | **Fixed:** GND | TPS3430 Table 6.6 |
| U702 SET1 — not connected / not driven | **Fixed:** GND | TPS3430 Table 6.6 |

**Count:** 22 H2-A errors. 21 are closed by connections taken from datasheets (the loop-filter values are derived).
1 is still open (RS_SW). 4 new pin-type findings were introduced by a datasheet-sanctioned connection.

## Not visible to ERC

- **Placeholder regulators** (U601–U608, U609) still make every rail look driven.
- **Missing bypass networks:** ADAR1000, ADTR1107 and STM32.
- **Footprints:** custom parts have none.

These are listed in `H2B_UNRESOLVED_ISSUES.md`.

## Netlist verification

`tools/verify_netlist.py` against the MCP-exported netlist (`openru_x6_tile.xml`) gives **0 failures**:
- all H2-A checks: 1088 symbol pins, feed map, interfaces, rails, safety chain;
- 20 new H2-B checks: loop filter topology, AVA-183A+ bias per Fig 2, watchdog straps, QOD/CT/CIN on all four PA switches;
- all 26 remaining unconnected pins are declared.

Results are in `H2B_PIN_INTERFACE_VERIFICATION.csv`.
