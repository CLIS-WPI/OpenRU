# H2-C ERC report

- **Tool:** KiCad 9.0.9 `run_erc` (MCP), run on the root with the project hierarchy.
- **Raw report:** `openru_x6_tile-erc.json`.
- **Hierarchy:** `validate_hierarchy` → ok, 0 issues (25 schematic files).
- **Severity settings:** unchanged.

## Result: 5 errors, classified

| # | Finding | Class | Basis |
|---|---|---|---|
| 1 | U501 (ADF4371) pin 3 RS_SW — pin not connected | **GENUINELY UNRESOLVED** | ADF4371 Rev 0 only says "Used for switching loop filter resistors in fastlock applications"; no statement that it may be left open. Needs ADI (inquiry 7) |
| 2–5 | U621–U624 (TPS22810) QOD (open collector) ↔ VOUT (power output) — pin_to_pin | **DATASHEET-APPROVED CONNECTION** | TI SLVSDH0C pin table: QOD may be enabled by "Tying QOD directly to VOUT and using the internal resistor value (RPD)". KiCad flags it only because of the library pin types. Kept visible, not waived |

**No ERC error was suppressed.**

### No-connect flags added in H2-C

Each one is backed by datasheet text, listed in `H2C_OPEN_PIN_DECLARATIONS.json`:
- TPS62933 RT (float = 500 kHz);
- TPS7A47 unused ANY-OUT pins ("If not used, leave this pin floating");
- TPS65131 BSW;
- TPS22917 CT;
- TPS386000 CT3/CT4/VREF;
- 74LVC1G74 ~Q.

The TPS22917 QOD uses a 100 Ω resistor to VOUT (also a TI option) rather than a direct tie, so it adds no ERC finding.

### Not visible to ERC

These are listed in `H2C_HARDWARE_SAFETY_REVIEW.md` §5 and `H2C_UNRESOLVED_ISSUES.md`:
- the gate-bias firmware limit;
- clamp sink-current margins;
- supervisor timing;
- inductor selection;
- footprints for custom parts.

## Netlist verification (as built, `openru_x6_tile.xml`)

- **`tools/verify_netlist.py`:** all H2-A/H2-B checks pass on the as-built netlist:
  - 1088 symbol pins; feed map; interfaces; rails;
  - safety chain, updated for the H2-C interlock (PA_ARMED, NEG_OK, PA_DRAIN_EN via R735/R965);
  - loop filter, LO-amp bias, watchdog, PA switches;
  - 44 declared open pins.

  Results: `H2C_PIN_INTERFACE_VERIFICATION.csv`.
- **`tools/verify_expected.py`** against `design/h2c/expected_asbuilt.json`, generated from the specs *before* placement
  by each implementation pass, with later passes overriding pins they intentionally changed: **1300 checks, 4
  differences**, all intentional or cosmetic:
  - R970 and R971 value strings carry an extra "25ppm";
  - U912 pin 1 and U914 pin 3 moved from NEG_RAILS_OK to IL_EN. This is the H2-C simulation-driven fix (U915), made
    after the interlock expectation was written. It is reported as one split plus one merge.
