# H2-C amendments: these override POWER_SPEC.md, INTERLOCK_SPEC.md and PERIPH_SPEC.md where they conflict

## A1. Gate dividers must not inject positive voltage into an unpowered PA gate (interlock open risk #1)

- **Gate-monitor reference:** the top leg of every gate divider (the 17.4 k leg, ×16) and the two gate-threshold
  reference dividers (−0.15 V "lost" and −1.5 V "pinched") connect to a new net **`IL_REF`**, not to `+1V8_DIG`.
- **IL_REF supply:** IL_REF = `+1V8_DIG` through a load switch, TI **TPS22917DBV** (KiCad
  `Power_Management:TPS22917DBV`). Download https://www.ti.com/lit/ds/symlink/tps22917.pdf and verify the pinout, the
  EN thresholds at VIN = 1.8 V, quick output discharge (QOD/CT if present) and Ron. Its EN = **`NEG_RAILS_OK`**.
- **Rail monitors stay on +1V8_DIG:** the comparators for −5V_BF, −3V3_SW and +3V3_AUX keep their dividers and
  thresholds on `+1V8_DIG`. Their open-collector outputs go onto **`NEG_RAILS_OK`**, using the fail-safe 10 k from
  `+3V3_AUX` / 10 k to GND scheme.
- **Gate outputs:** the 16 gate-"lost" comparator outputs go onto **`GATES_OK`** (same fail-safe scheme).
  `GATES_PINCHED` is unchanged, but its dividers are now IL_REF-based.
- **Combining:** **`NEG_OK` = NEG_RAILS_OK · GATES_OK** through a new 74LVC1G08 (`74xGxx:74LVC1G08`, VCC = +1V8_DIG,
  SOT-23-5), ref **U912**. The output is NEG_OK.
- **Effect:**
  - While the negative rails are not OK, IL_REF is off, so no positive bias reaches any gate.
  - The gate comparator inputs go negative, current-limited by the 49.9 k (check the LM339B input-current abs max and
    state it). GATES_OK reads low, so NEG_OK is low (fail-safe).
  - Once both negative rails are good, the ADAR1000 is powered (AVDD3 first, then AVDD1, by A2 below) and drives
    PA_BIAS at 0 V or lower, low-impedance.
- Keep the ratiometric analysis valid: every gate-related divider uses IL_REF.

## A2. Hardware rail ordering

- TPS65131 **ENN** = PWR_EN_NEG · PG_3V3RF, through a new 74LVC1G08 (ref **U913**, VCC = +1V8_DIG). The negative
  rails therefore cannot start before +3V3_RF is in regulation. This follows ADAR1000 p13 (AVDD3 before or with AVDD1)
  and ADTR1107 p24 (VDD_SW before VSS_SW).
- PG_3V3RF needs its 100 k pull-up to +1V8_DIG from POWER_SPEC.

## A3. Existing pull-downs

- PWR_EN_LO and PWR_EN_NEG already have 100 k pull-downs on the MCU sheet (R717 and R715 region). **Do not add**
  R665/R671.
- PA_DRAIN_EN has no pull-down, so **add R965** (100 k to GND) as INTERLOCK_SPEC says.

## A4. Peripheral fixes (PERIPH_SPEC)

- **INA226 duplicate address:**
  - U610 A0 is currently GND, giving the same address as U611. Change **U610 A0 → net I2C3_SDA** (address 0x42).
  - Remove U610's existing A0 label and connect the new one through MCP (`remove_label` at the pin, then
    `wire_pins_to_net`).
- **PCA9306:** add **100 pF** C on PCA_VREF2 to GND (TI SCPS113O Fig 9-1).
- **MCU decoupling (ST DS12589 Fig 16):**
  - VDD (pins 23, 35, 48): 3 × 100 nF + 1 × 4.7 µF.
  - VDDA: 10 nF + 1 µF.
  - VREF+: 100 nF + 1 µF.
  - VBAT: no value documented, so add none and keep it listed UNRESOLVED.
  - All of these pins are on +1V8_DIG (refs C703+).
- **MCU sheet text:** replace the TPS3430 note's "SLVSxxx" with "SBVS366A" (`remove_text` + `add_text`).

## A5. ADAR1000 / ADTR1107 decoupling (Stingray 02_059522 Rev B sheet 4 / BOM 05-059522-01-b, one tile = 1 ADAR1000 + 4 ADTR1107)

- **On each `bf{c}` sheet (per ADAR1000):**
  - +3V3_RF: 1 µF X7R 0402 + 10 nF X7R + 100 pF C0G.
  - −5V_BF: 10 nF + 100 pF.
- **On each `fe{c}` sheet (per tile):**
  - −3V3_SW: 10 nF + 100 pF.
  - +5V_PA_C{c}: 1 µF + 10 nF + 100 pF.
  - **Per ADTR1107 VDD_PA:** 4.7 µF X5R (GRM035R60J475ME15D on Stingray). Use a **≥10 V** rated equivalent in 0402
    (our judgement: 6.3 V rating on a 5 V rail with 5.18 V worst case is too tight) and record it as a deviation.
- Keep the existing CREG 1 µF and VGG_PA 10 nF.
- Refs:
  - bf: C{100c+5}…C{100c+9}.
  - fe: C{100c+40}…C{100c+48}, plus VDD_PA 4.7 µF ×4 as C{100c+50}…C{100c+53}.
- Footprints: 0402 (`Capacitor_SMD:C_0402_1005Metric`); 0201 only if a KiCad footprint exists.
- **Values from Stingray are per-rail sets, not per-pin.** Note on the sheet: "decoupling per ADI Stingray 02_059522
  Rev B (per-tile set); per-pin values not documented".

## A6. Placeholders

- Remove placeholder regulators U601–U608 and the NEG monitor U609 from `power.kicad_sch`, using `remove_component`.
  Their labels go too: remove the orphan labels at their pins, via `list_schematic_global_labels` /
  `list_schematic_labels` near their pin positions.
- New circuits go on new sub-sheets of the root: `pwr_main.kicad_sch`, `pwr_lo.kicad_sch`, `pwr_neg.kicad_sch`,
  `interlock.kicad_sch`.
- The existing rail names are unchanged: +3V3_RF_SRC, +5V_PA, +3V3_AUX, +1V8_DIG, +3V3_LO, +5V_LO, -5V_BF, -3V3_SW,
  VIN_12V, GND, PWR_EN_*, PG_3V3RF, NEG_OK.
- **U705 pin 1 → PA_ARMED**, replacing MCU_PA_EN on U705.
