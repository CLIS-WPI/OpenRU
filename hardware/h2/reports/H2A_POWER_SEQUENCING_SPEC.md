# H2-A Power-rail and sequencing specification (prototype tile)

Status: **preliminary**. The regulators are `TBD_*` placeholder blocks (U601–U608), not designed circuits. Everything
else on this page is drawn in the schematic (`power.kicad_sch`, `mcu.kicad_sch`). It was checked in the exported
netlist by `tools/verify_netlist.py` (checks `safety`, `safety-default` and `rail`).

## Rails

| Net | Loads | Source (placeholder) | Enable | Basis |
|---|---|---|---|---|
| `+1V8_DIG` | MCU, 74LVC gates, TPS3430, TMP117, ADAR1000 ADDR straps, CS pull-ups | U603, always on | — | ADAR1000 digital I/O is 1.8 V CMOS, abs max 2.0 V (Rev B p11, p13) |
| `+3V3_AUX` | INA226 ×5 VS, I²C 3.3 V side | U606, always on | — | telemetry must work before the RF rails are on |
| `+3V3_RF_SRC` → 10 mΩ → `+3V3_RF` | ADAR1000 AVDD3 ×4, ADTR1107 VDD_SW + VDD_LNA ×16, LTC5553 VCC ×4 | U601 (≥4 A; ADI suggests LT8609S for 4 devices) | `PWR_EN_3V3` | ADAR1000 Rev B Table 1 & Table 26 |
| `-5V_BF` | ADAR1000 AVDD1 ×4 (−4 mA reset, −50 mA with PA bias fully loaded) | U607 (LT1931/LT3462 class per ADI) | `PWR_EN_NEG` | ADAR1000 Rev B Table 1, p45 |
| `-3V3_SW` | ADTR1107 VSS_SW ×16 (120 µA each) | U608, negative LDO from −5 V | `PWR_EN_NEG` | ADTR1107 Rev C Table 5 |
| `+5V_PA` → 10 mΩ → TPS22810 → `+5V_PA_C1..4` | ADTR1107 VDD_PA, 4 per chain (220 mA quiescent each) | U602 (≥5 A) + U621–U624 | `PWR_EN_5VPA` + hardware `PA_DRAIN_EN` | ADTR1107 Rev C Table 1 |
| `+3V3_LO` | ADF4371 AVDD group (14 pins) | U604, low noise (ADM7150/LT3045 per DS) | `PWR_EN_LO` | ADF4371 Rev 0 p24 |
| `+5V_LO` | ADF4371 VCC_VCO + VCC_LDO; AVA-183A+ (bias network UNRESOLVED) | U605, low noise | `PWR_EN_LO` | ADF4371 Rev 0 p9, p24 |

Quiescent tile power (prototype, from H1.1): TX 27.4 W, RX 12.8 W, TDD average 23.8 W, plus the LO chain:
- ADF4371 ≈ 0.9–1.3 W;
- AVA-183A+ ≈ 0.65–0.83 W.

Conversion losses are not included.

## Power-up order (enforced by firmware; the PA drain is also blocked in hardware)

1. `+1V8_DIG`, `+3V3_AUX` come up and the MCU boots.
   - Every enable, load and TDD net has a 100 k pull-down (R710–R721), so nothing is enabled while the MCU is in reset.
   - The CS lines are pulled high (R730–R734).
2. `PWR_EN_3V3` brings up `+3V3_RF`, powering:
   - ADTR1107 VDD_SW and VDD_LNA;
   - ADAR1000 AVDD3;
   - the mixers, which remain disabled.
   Before this step the ADAR1000 needs AVDD3 before or together with AVDD1 (Rev B p13), and the ADTR1107 needs VDD_SW
   before VSS_SW (Rev C p24).
3. `PWR_EN_NEG` brings up `-5V_BF` and `-3V3_SW`. `U609` asserts `NEG_OK` once both are in window (part UNRESOLVED).
4. Firmware programs each ADAR1000:
   - BIAS_CTRL = 1;
   - EXT_PA_BIAS_OFF ≈ **−1.75 V** on all four PA_BIAS outputs;
   - LNA bias;
   - TR_SOURCE = pin.
   CTRL_SW is already at RX: it is pulled up by R120/R220/R320/R420 while TR_SW_POS floats (ADAR1000 p41).
5. `PWR_EN_5VPA` brings up the `+5V_PA` bus (before the per-chain switches).
6. Firmware sets `MCU_PA_EN`. The hardware AND `PA_DRAIN_EN = MCU_PA_EN · WDT_OK · NEG_OK` (U705) turns on TPS22810
   U621–U624.
7. Firmware raises VGG_PA (EXT_PA_BIAS_ON) until each ADTR1107 draws IDQ = 220 mA. The current is read on the INA226
   per chain; the datasheet typical gate voltage is −1.1 V.
8. The LO comes up: `PWR_EN_LO`, `PLL_CE`, program ADF4371 (set LEV_SEL = 1.8 V before any MUXOUT readback), lock,
   then `MIX_EN`.
9. Firmware sets `MCU_TX_EN`, and an external `TX_PERMIT_IN` is supplied. TX now follows `TDD_TR_IN`.

**PA_BIAS OFF-value conflict (to resolve with ADI):**
- ADAR1000 Rev B p45 recommends EXT_PAx_BIAS_OFF = 0x85 ≈ **−2.5 V** for the ADTR1107.
- ADTR1107 Rev C Table 6 gives the VGG_PA abs max as **−2 V to 0 V**, and its own sequence uses −1.75 V.

H2-A uses −1.75 V (a firmware setting) and lists this as review item R2.

## Power-down order

1. `MCU_TX_EN` low, so `TX_ALLOW` and `BF_TR` go low:
   - ADAR1000 PA_ON low forces the PA_BIAS OFF values;
   - the RF chain goes to RX.
2. PA_BIAS goes to −1.75 V (if not already there).
3. `MCU_PA_EN` low, so the drains switch off.
4. `PWR_EN_5VPA` low.
5. `PWR_EN_NEG` low (ADTR1107 Rev C p24: VDD_PA, then VSS_SW, then VDD_SW).
6. `PWR_EN_3V3` low.

## Hardware interlocks (independent of firmware)

| Signal | Logic (as drawn) | Effect when false |
|---|---|---|
| `WDT_OK` | TPS3430 ~WDO, open-drain, 10 k pull-up | TX_ALLOW and PA_DRAIN_EN both drop |
| `NEG_OK` | U609 (UNRESOLVED part) | PA drain cannot be enabled without −5 V / −3.3 V |
| `TX_ALLOW` | U703 = MCU_TX_EN · WDT_OK · TX_PERMIT_IN | ADAR1000 PA_ON low (bias OFF); BF_TR forced low |
| `BF_TR` | U704 = TDD_TR_IN · TX_ALLOW, to all 4 ADAR1000 TR | RX mode on all chips at the same moment |
| `PA_DRAIN_EN` | U705 = MCU_PA_EN · WDT_OK · NEG_OK | TPS22810 ×4 off |

Truth-table property, checked against the netlist: TX RF can be present only when MCU_TX_EN, WDT_OK, TX_PERMIT_IN,
TDD_TR_IN, MCU_PA_EN and NEG_OK are all high. Each is pulled to its safe state at reset, except WDT_OK. WDT_OK is
pulled up; its start-up state depends on the TPS3430 SET/CRST configuration, which is UNRESOLVED (U25). Because
MCU_TX_EN and MCU_PA_EN are pulled low, the radio stays muted whatever WDT_OK does. `TX_PERMIT_IN` is an external interlock and
inhibits TX when open.

## TDD timing (datasheet values)

| Step | Time | Source |
|---|---|---|
| ADAR1000 TR edge → RF (TR switching) | 180 ns | ADAR1000 Rev B p7 |
| ADAR1000 TX_LOAD/RX_LOAD → new phase/gain | 20 ns | Rev B p7 |
| ADAR1000 PA_BIAS off↔on | 60 ns **into 1 nF** | Rev B p7 |
| ADTR1107 CTRL_SW → RF | 10 ns | Rev C Table 1 |
| LTC5553 EN on / off | 0.2 / 0.1 µs | 5553f |

**Review item R3:**
- ADTR1107 Fig 89 puts **10 nF** on VGG_PA, but ADAR1000 specifies PA_BIAS switching at 1 nF with ±10 mA drive.
- At 10 nF, a 0.65 V step (−1.75 → −1.1 V) takes about 0.65 µs at 10 mA. Larger OFF swings take longer.
- This sets the minimum TX/RX guard time if PA bias is toggled every TDD transition.
- Options: choose the value from the ADAR1000-EVALZ / Stingray design, or keep the bias ON for a whole TX burst.

ADAR1000 TX/RX delay registers 0x4B/0x4C must not both be non-zero, because of an erratum (Rev B p43).

## Beam-update synchronisation

- `BF_TX_LOAD` and `BF_RX_LOAD` are shared nets to all four ADAR1000 (latch on the rising edge, 20 ns), driven by MCU
  timer outputs PA8/PA9.
- The two must never be pulsed within 8 SCLK of each other (Rev B p33–34).
- A RAM beam fetch needs ≥6 extra SCLK cycles before the load pulse (p32).

## Telemetry

- **Current and voltage:** INA226 U610 on `+3V3_RF`, and U611–U614 on each chain's PA drain, read over a
  PCA9306-translated I²C bus.
- **Temperature:**
  - TMP117 U706/U707 on the 1.8 V I²C bus;
  - ADAR1000 on-die temperature sensor (8-bit ADC, Rev B p32);
  - per-element TX power from ADTR1107 CPLR_OUT into ADAR1000 DET1–4.
- **Alerts:** `INA_ALERT_N` is a wired-OR of all INA226 and TMP117 alert outputs into MCU PA2.
