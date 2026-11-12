# H2-C REC safety hardware: implementation report (IMPL_REC)

Source: H2C_SEQUENCING_SIM.md revision 2, "Recommended hardware changes" items 1–9. Item 9, the +3V3_RF UV channel, was included because it is part of the simulated REC design. The part selection and the datasheet checks are in `REC_PARTS.md`.

All KiCad edits were made through the KiCad MCP tools. Nothing was committed, and no ERC severity was changed.

## Files
- `REC_PARTS.md`: part selection, datasheet parameters against the sim assumptions, and mismatches M1–M7.
- `rec/ds/`: the datasheets used (TI, Diodes, Vishay, KOA, onsemi PDFs + text).
- `expected_rec.json`: written before placement by `tools/gen_expected_rec.py`. Updated twice after placement: R1001 was added (ERC fix), and R735 pin 1/2 was recorded as built (a resistor, so symmetric).
- `tools/check_rec.py`: compares `net_rec/openru_x6_tile.xml` with the JSON. **Result: 0 mismatches.**
- Regression against `net_rec_before/`:
  - No ref removed; 51 parts added.
  - The only changed pins of existing parts are the 11 expected ones: U914.1, U914.3, C914.1, U911.4, U705.4, U908.10/11/13, R970.1, R971.1/2.
- `net_rec/`: netlist after the changes. `erc_rec/`: the ERC report.

## Where the parts went
- **Crowbars (items 1–4): power.kicad_sch (POWER_SEQUENCING), x ≈ 444–577, y 110–182.** This is to the right of U621–U624, where both the TPS22810 VIN-side net (+5V_PA_IN_Cc, local) and VOUT (+5V_PA_Cc, global) already exist.
- **Supervisor, Q3, inverter, BAT54Cs, IL_REF LDO, UV divider: interlock.kicad_sch,** in the new block at y 340–415, plus the re-wired U908/U914/U911/R970/R971/C914/C915.
- **R735: mcu.kicad_sch,** next to U705.

## Parts added (refs)

Per chain c = 1…4 (power sheet):

| Function | Ref | Part | Nets |
|---|---|---|---|
| Q_CB | Q961–Q964 | CSD16301Q2 (Texas_DQK) | G = PWR_CB_Gc; D (1, 2, 5, 6, 8) = PWR_CB_Rc; S (4, 7) = GND |
| R_CB | R980–R991 (3 per chain) | 1 Ω 1 % RCS12061R00FKEA, 1206 | +5V_PA_Cc ↔ PWR_CB_Rc |
| R_CBPU | R992–R995 | 4.7 k 0402 | +5V_PA_IN_Cc ↔ PWR_CB_Gc |
| Q2 | Q971–Q974 | DMG1012T-7 (SOT-523) | G = PWR_CB_Dc; D = PWR_CB_Gc; S = GND |
| R_CBD | R996–R999 | 10 k 0402 | PA_DRAIN_EN ↔ PWR_CB_Dc |
| C_CBD | C931–C934 | 1 nF 50 V C0G 0402 | PWR_CB_Dc ↔ GND |

Once (interlock sheet unless noted):

| Function | Ref | Part / value | Nets |
|---|---|---|---|
| Supervisor | U920 | TPS386000RGPR (new symbol openru_x6:TPS386000RGP) | 14 VDD, 1 MR = IL_SUP_VDD; 10 SENSE1 = IL_SNS1; 9 SENSE2 = IL_SNS2; 15/16 RESET1/2 = PG_3V3RF; 5 CT1 = IL_CT1; 4 CT2 = IL_CT2; 17/18/19 RESET3/RESET4/WDO = IL_SUP_OD; 6/7/8/11/12/20/21 = GND; 2, 3, 13 NC |
| VDD diode-OR | D960 | BAT54C-7-F | 1 = +3V3_RF, 2 = +5V_PA, 3 = IL_SUP_VDD |
| VDD bypass / PWR_FLAG | C935 100 nF, #FLG960 | – | IL_SUP_VDD |
| Delay caps | C936, C937 | 2.2 nF 50 V C0G | IL_CT1 / IL_CT2 → GND (tD 9.6 ms nominal) |
| SENSE1 divider | R977 32.4k / R978 10.2k, 0.1 % | – | +1V8_DIG → IL_SNS1 → GND (1.671 V) |
| SENSE2 divider | R979 64.2k / R1000 10.0k, 0.1 % | – | +3V3_AUX → IL_SNS2 → GND (2.968 V) |
| Unused open-drain outputs | R1001 | 1 MΩ | IL_SUP_VDD ↔ IL_SUP_OD |
| Inverter (2nd, active-high output) | Q966 | DMG1012T-7 | G = PG_3V3RF, D = IL_Q3G, S = GND |
| Inverter pull-up | R976 | 100 k | IL_SUP_VDD ↔ IL_Q3G |
| Q3 | Q965 | DMG1012T-7 | G = IL_Q3G, D = IL_ON, S = GND |
| ON series R | R974 | 10 k | IL_EN ↔ IL_ON |
| Clamp diodes | D961 | BAT54C-7-F | 1 = PA_DRAIN_EN, 2 = IL_CLR_N, 3 = PG_3V3RF |
| 1 k series (U911) | R975 | 1 k | IL_CLR_N_Y ↔ IL_CLR_N |
| 1 k series (U705, **mcu sheet**) | R735 | 1 k | PA_DRAIN_EN ↔ IL_PA_DRAIN_EN_Y |
| IL_REF LDO | U921 | TLV75518PDBVR (Regulator_Linear:TLV70012_SOT23-5, as U653) | 1 IN = +3V3_RF, 2 GND, 3 EN = PG_3V3RF, 4 NC (no_connect pin type), 5 OUT = IL_REF_SRC |
| LDO input cap | C938 | 1 µF 10 V X5R | +3V3_RF ↔ GND |

Existing parts changed:

| Part | Change |
|---|---|
| U914 TPS22917 | VIN (1): +1V8_DIG → **IL_REF_SRC**. ON (3): IL_EN → **IL_ON** (Q3 clamp; R974 10 k from IL_EN). |
| C914 1 µF | pin 1: +1V8_DIG → IL_REF_SRC. It is now the TLV755 COUT and the TPS22917 CIN. |
| C915 | 100 nF → **10 nF 50 V X7R** (MPN GRM155R71H103KA88D, not stock-checked). Item 8: IL_REF ≤ 10 nF. |
| U911 | Y (4): IL_CLR_N → IL_CLR_N_Y (via R975 1 k). |
| U705 (mcu) | Y (4): PA_DRAIN_EN → IL_PA_DRAIN_EN_Y (via R735 1 k). R965 stays on PA_DRAIN_EN. |
| U908 ch D | pin 10: IL_SPARE_N → IL_REF_N5V. Pin 11: IL_SPARE_P → IL_RFMON. Pin 13: NC flag removed → NEG_RAILS_OK. |
| R971 | 10k → **49.9k 0.1 % 25ppm**; pin 1 +3V3_AUX → +3V3_RF; pin 2 → IL_RFMON. The old MPN was cleared. |
| R970 | 10k → **10.2k 0.1 % 25ppm**; pin 1 → IL_RFMON (pin 2 stays GND). The old MPN was cleared. Trip point = 0.5264 V × 60.1/10.2 = 3.10 V. |

For every re-wired pin, the old label and its stub wire were removed first (remove_label + remove_wire). Every cross-sheet net ends in a passive global label: +3V3_RF, +5V_PA, +5V_PA_Cc, PA_DRAIN_EN, PG_3V3RF, +1V8_DIG, +3V3_AUX, GND. No sheet has a local and a global label of the same name; this was checked in the netlist (no `/<sheet>/GND`-style duplicates). Sheet notes were added on POWER_SEQUENCING, PA_INTERLOCK and MCU_SAFETY.

## Deviations from REC
1. **R_CB is 3 × 1 Ω in parallel (0.333 Ω), not one 0.33 Ω part.** No pulse-rated 1206 series with a reachable datasheet offers 0.33 Ω: Vishay RCS/CRCW-HP start at 1 Ω, WSL1206 stops at 0.2 Ω, and KOA SG73P starts at 1 Ω. RCS1206 1 Ω has a verified 10/700 µs pulse curve (≈ 10 V at 1 Ω). This adds 8 parts.
2. **Q_CB VGS(th) min is 0.9 V** (CSD16301Q2), against the requested 1–2 V. Ciss is 340 pF max (better than ≤ 1 nF) and RDS(on) 29 mΩ max. CSD17578Q3A was rejected because Ciss max is 1.59 nF and the part is not in the KiCad library. See REC_PARTS M1.
3. **Active-high supervisor output is built as an inverter (Q966 + R976)** driven from PG_3V3RF. The TPS386000 has only active-low outputs. Q3 therefore also clamps the ON pin whenever U650 PGOOD is low; that is consistent with IL_EN = NEG_RAILS_OK · PG_3V3RF. Rise time ≈ 10 µs through 100 k. Not re-simulated.
4. **Unused TPS386000 channels:**
   - SENSE3/SENSE4L/SENSE4H go to GND. The datasheet says "Connect to GND if not being used" for 4H; for SENSE3/4L it is within ROC 0…VDD.
   - RESET3/RESET4/WDO are joined on IL_SUP_OD with a 1 MΩ pull-up (R1001) to the supervisor VDD; ROC RPULL-UP is 6.5 k–10 MΩ. Tying them to GND produced 3 new ERC pin_to_pin errors (open collector against GND's PWR_FLAG power_out), so the pull-up was used instead. That costs ≈ 5 µA permanently, because RESET3/4 stay asserted.
   - NC flags on CT3/CT4 ("…or leaving it open, selects a fixed delay time", SBVS105F p4) and on VREF (IDD is specified with "VREF open", §6.5; "Do not connect only a capacitor", p4).
   - MR → VDD (no internal pull-up, §8.3.2). WDI → GND (EC test condition). NC pin 11 → GND (TI recommendation). PAD → GND.
5. **IL_REF_SRC output cap is the existing C914, moved** from +1V8_DIG, rather than a new 1 µF.
6. **Refs outside the suggested pools.**
   - R1000 and R1001: R980–R999 are used by the 20 crowbar resistors, and R974–R979 by the others.
   - R735 sits on the MCU sheet, next to U705.
   - C935–C938, D960/D961, U920/U921, Q961–Q966 and Q971–Q974 are inside the pools.
7. **Net names.**
   - Power-sheet locals: PWR_CB_Gc, PWR_CB_Rc, PWR_CB_Dc. REC calls them CB_G/CB_D; the PWR_ prefix was added.
   - Interlock locals: IL_SUP_VDD, IL_SUP_OD, IL_SNS1/2, IL_CT1/2, IL_Q3G, IL_ON, IL_REF_SRC, IL_RFMON, IL_CLR_N_Y.
   - MCU local: IL_PA_DRAIN_EN_Y.
8. **Supervisor footprint** `Texas_RGP0020D` (EP 2.7 mm) is UNVERIFIED. The TPS386000 datasheet copy carries only the generic RGP package view, not the exposed-pad dimension, and KiCad also has an RGP0020H (EP 2.4 mm). Check the TI land pattern before layout.
9. **Generic R/C MPNs left empty** (as in earlier passes). MPNs set: CSD16301Q2, DMG1012T-7, RCS12061R00FKEA, TPS386000RGPR, TLV75518PDBVR, BAT54C-7-F, GRM155R61A105KE15D (C938), GRM155R71H103KA88D (C915).

## Blockers / open items (nothing was left unimplemented)
1. **Supervisor sink current and the TLV755 EN low level (REC_PARTS M5): not guaranteed by the datasheets.**
   - While the BAT54C clamps act, the TPS386000 sinks ≈ 2.4–2.9 mA. VOL is specified only at 1 mA (≤ 0.4 V). The effective 1 kΩ pull-up is below the ROC 6.5 kΩ minimum (abs max 5 mA is respected).
   - TLV755P EN VLO is 0.3 V max, so the IL_REF LDO is guaranteed off only if PG_3V3RF ≤ 0.3 V under that current.
   - The PA_DRAIN_EN/IL_CLR_N clamp level ≈ VOL + 0.33 V (typ ≈ 0.5 V) is below VENF 1.08 V and the LVC VIL of 0.58 V, but only by typical values.
   - The same question applies to U650 (TPS568230) PGOOD.
   - Needs a bench check or a design change. Raising the series resistors is not an option: it breaks the TPS22810 EN fall, because the Q2 RC branches hold PA_DRAIN_EN at ≈ 1.44 V with 10 kΩ. A dedicated clamp FET driven from IL_Q3G would avoid the issue.
2. **Supervisor detection delay is unspecified** ("almost immediately … minimal propagation delay"; tW ≈ 4 µs typ). The sim modelled it as 0.
3. **Not re-simulated with the real parts:** CSD16301Q2 VGS(th) 0.9 V and Ciss 340 pF; 0.333 Ω; DMG1012T; the inverter delay. The sim results in H2C_SEQUENCING_SIM.md still refer to the idealised REC.
4. **TPS22810 tOFF max and tD min are still unspecified** (sim residual risk); measure them on the bench.
5. **RCS1206 pulse rating** is characterised for pulses at 1-min intervals. Rapid arm/disarm cycling in test is outside that curve.

## Checks
- **validate_hierarchy (root): ok, 0 issues.**
- **run_erc (root, `erc_rec/`): 5 violations, all pre-existing (the same set as IMPL_PERIPH):**
  - pin_not_connected: U501 pin 3 (RS_SW);
  - pin_to_pin: U621–U624 QOD (open collector) tied to VOUT (power output), ×4.
- No new ERC violations. There were 3 transient OC-to-GND errors; they were fixed by R1001 (deviation 4).
- **Netlist (`net_rec/`) against `expected_rec.json`: 0 mismatches** (values, footprints, every pin net). There are no unexpected changes on pre-existing parts.
