# OpenRU H2-C — RF tile power tree (POWER_SPEC)

Research and design only. Nothing in the KiCad project was changed. All values come from the TI datasheets listed in (a). "p" means the printed page number of that datasheet. Values that the datasheet procedure does not fix are marked **UNRESOLVED** and are collected in (d).
Datasheet text and renders used: `hardware/h2/design/h2c/ (scratch) power/*.txt|*.pdf`

```
VIN_12V (11–13 V) ─┬─ U650 TPS568230  (EN=PWR_EN_3V3,  PG→PG_3V3RF) ─────────── +3V3_RF_SRC  3.3 V / 4 A
                   ├─ U651 TPS568230  (EN=PWR_EN_5VPA) ──────────────────────── +5V_PA       5.0 V / 5 A
                   ├─ U652 TPS62933   (EN = UVLO divider, start at 8 V) ──────── +3V3_AUX     3.3 V / ≤1 A (always on)
                   │      ├─ U653 TLV75518P (EN=IN) ──────────────────────────── +1V8_DIG     1.8 V / ≤150 mA
                   │      └─ U657 TPS65131 inverter (ENN=PWR_EN_NEG, ENP=GND) ─ PWR_VNEG ≈ −6.34 V
                   │             ├─ U658 TPS7A3301 (EN tied to IN) ───────────── -5V_BF      −5.0 V / 0.25 A
                   │             └─ U659 TPS7A3301 (EN tied to IN) ───────────── -3V3_SW     −3.3 V / 5 mA
                   └─ U654 TPS62933   (EN=PWR_EN_LO) ── PWR_6V2_LO ≈ 6.25 V
                          ├─ U655 TPS7A4701 ANY-OUT 5.0 V (EN tied to IN) ────── +5V_LO      5.0 V / 0.4 A
                          └─ U656 TPS7A4701 ANY-OUT 3.3 V (EN tied to IN) ────── +3V3_LO     3.3 V / 0.35 A
```

## (a) Summary

| Rail | Reg. | Part | Topology / setting | Nominal Vout | Worst-case Vout (ref tolerance + 1 % resistors) | Datasheet (revision, URL) |
|---|---|---|---|---|---|---|
| +3V3_RF_SRC | U650 | TPS568230RJE | D-CAP3 buck, FCCM, 600 kHz | 3.327 V | 3.229 … 3.444 V | SLVSEY5C (Aug 2019), https://www.ti.com/lit/ds/symlink/tps568230.pdf |
| +5V_PA | U651 | TPS568230RJE | D-CAP3 buck, FCCM, 600 kHz | 5.000 V | 4.847 … **5.182 V (≤5.5 V)** | same |
| +3V3_AUX | U652 | TPS62933DRL | Peak-current-mode buck, 500 kHz | 3.328 V | 3.212 … 3.447 V | SLUSEA4D (Aug 2022), https://www.ti.com/lit/ds/symlink/tps62933.pdf |
| +1V8_DIG | U653 | TLV75518PDBV | LDO, fixed | 1.8 V | ±1 % (−40…85 °C) | SBVS320D (Sep 2024), https://www.ti.com/lit/ds/symlink/tlv755p.pdf |
| PWR_6V2_LO | U654 | TPS62933DRL | buck, 500 kHz (LDO pre-regulator) | 6.248 V | 6.017 … 6.486 V | SLUSEA4D |
| +5V_LO | U655 | TPS7A4701RGW | ANY-OUT (3P2V+0P4V to GND) | 5.0 V | ±2.5 % → 4.875 … 5.125 V | SBVS204G (May 2026), https://www.ti.com/lit/ds/symlink/tps7a47.pdf |
| +3V3_LO | U656 | TPS7A4701RGW | ANY-OUT (1P6V+0P2V+0P1V to GND) | 3.3 V | ±2.5 % → 3.218 … 3.383 V | SBVS204G |
| PWR_VNEG | U657 | TPS65131RGE | inverting buck-boost, 1.38 MHz; boost stage disabled | −6.344 V | −6.005 … −6.688 V | SLVS493E (Apr 2022), https://www.ti.com/lit/ds/symlink/tps65131.pdf |
| -5V_BF | U658 | TPS7A3301RGW | adjustable negative LDO | −4.999 V | −4.848 … −5.150 V (ADAR1000 spec −4.75…−5.25 ✓) | SBVS169D (Apr 2015), https://www.ti.com/lit/ds/symlink/tps7a33.pdf |
| -3V3_SW | U659 | TPS7A3301RGW | adjustable negative LDO | −3.311 V | −3.219 … −3.403 V (abs max −3.6 V ✓) | SBVS169D |

Why these parts:
- TPS568230 is rated 8 A (DS §6.3 p4). The same part, with the same layout, covers both the 4 A and the 5 A rails. The other TI parts in the KiCad library are too small (TPS56339 and LMR33630 are 3 A) or need an external diode and compensation (TPS54560B).
- TPS62933 covers both the 3.3 V AUX rail and the LO pre-regulator. Its datasheet names a real inductor and real capacitors (DS §10.2.2.7 p31, §10.2.2.8 p32, §10.2.2.9 p32).
- LM27762 was rejected for the negative rails. It is a charge pump limited to a 5.5 V input, so from +3V3_AUX it cannot reach −5 V. TPS65131 + TPS7A33 is kept as suggested.
- Estimated VIN_12V load at full load is about 50 W, or about 4.2 A at 12 V. The bench supply must be set to at least 5 A.

## (b) Placement tables

Symbol notes (all checked with `get_symbol_info` against the datasheet pinout; **no pin-number mismatches found**):
- `Regulator_Switching:TPS568230` is **derived**: it `extends "TPS51396A"`. Place **`Regulator_Switching:TPS51396A`** and set Value = TPS568230. The base symbol's pins match the TPS568230 DS pin table (p3): BST 1, VIN 2–5, SW 6/19/20, GND 7/8/18 + pad (symbol pin 21), PGOOD 9, NC 10/16, SS 11, EN 12, AGND 13, FB 14, MODE 15, VCC 17.
- `Regulator_Switching:TPS65131RGE` `extends "TPS65130RGE"`. Place **`Regulator_Switching:TPS65130RGE`** and set Value = TPS65131. The pins match DS Table 5-1 (p3). The exposed pad is symbol pin 25.
- `Regulator_Linear:TLV75518PDBV` `extends "TLV70012_SOT23-5"`. Place **`Regulator_Linear:TLV70012_SOT23-5`** and set Value = TLV75518PDBV. The pins match TLV755P DBV (DS Table 4-1 p3): IN 1, GND 2, EN 3, NC 4, OUT 5.
- `Regulator_Switching:TPS62933` (not derived) matches DS Table 7-1 (p3–4): RT 1, EN 2, VIN 3, GND 4, SW 5, BST 6, SS 7, FB 8.
- `Regulator_Linear:TPS7A4701xRGW` (not derived) matches DS Table 4-1 (p3). Symbol names "0.1V…6.4V" correspond to DS "0P1V…6P4V2". DS NC pins 2 and 17–19 are not drawn. The exposed pad is pin 21.
- `Regulator_Linear:TPS7A3301RGW` (not derived) matches DS pin table (p4): OUT 1/20, FB 3, GND 7, EN 13, NR/SS 14, IN 15/16. The exposed pad is pin 21. The NC pins are not drawn.
- Passives use `Device:C`, `Device:R`, `Device:L` (pin 1/2) and `Device:D_Schottky` (pin 1 = K, pin 2 = A).
- Every footprint below was confirmed with `ls /usr/share/kicad/footprints/<lib>.pretty`.

### U650 — +3V3_RF_SRC (TPS568230, FCCM 600 kHz)
| ref | lib_id | value | footprint | MPN | connections |
|---|---|---|---|---|---|
| U650 | Regulator_Switching:TPS51396A | TPS568230 | Package_DFN_QFN:Texas_RJE0020A_VQFN-20-1EP_3x3mm_P0.45mm_EP0.675x0.76mm | TPS568230RJER | 2,3,4,5 VIN→VIN_12V; 12 EN→PWR_EN_3V3; 9 PGOOD→PG_3V3RF; 15 MODE→PWR_MODE_3V3RF; 17 VCC→PWR_VCC_3V3RF; 11 SS→PWR_SS_3V3RF; 14 FB→PWR_FB_3V3RF; 1 BST→PWR_BST_3V3RF; 6,19,20 SW→PWR_SW_3V3RF; 7,8,18,21 GND→GND; 13 AGND→GND; 10,16 NC→GND (DS p3 allows GND for thermal) |
| C650–C653 | Device:C | 10µF 50V X7R | Capacitor_SMD:C_1206_3216Metric | CGA5L1X7R1H106K160AC | 1→VIN_12V, 2→GND |
| C654 | Device:C | 100nF 50V X7R | Capacitor_SMD:C_0402_1005Metric | TBD | 1→VIN_12V, 2→GND |
| C655 | Device:C | 100nF 25V X7R | Capacitor_SMD:C_0402_1005Metric | TBD | 1→PWR_BST_3V3RF, 2→PWR_SW_3V3RF |
| C656 | Device:C | 1µF 16V X7R | Capacitor_SMD:C_0603_1608Metric | TBD | 1→PWR_VCC_3V3RF, 2→GND |
| C657 | Device:C | 22nF 16V X7R | Capacitor_SMD:C_0402_1005Metric | TBD | 1→PWR_SS_3V3RF, 2→GND |
| C658 | Device:C | 100pF 50V C0G (CFF) | Capacitor_SMD:C_0402_1005Metric | TBD | 1→+3V3_RF_SRC, 2→PWR_FB_3V3RF |
| C659–C662 | Device:C | 47µF 10V X7R | Capacitor_SMD:C_1210_3225Metric | TBD | 1→+3V3_RF_SRC, 2→GND |
| L650 | Device:L | 1.5µH, Isat ≥ 14.7 A (≥ 5.4 A minimum) | UNRESOLVED (choose with MPN) | UNRESOLVED | 1→PWR_SW_3V3RF, 2→+3V3_RF_SRC |
| R650 | Device:R | 90.9k 1% (RUPPER) | Resistor_SMD:R_0402_1005Metric | TBD | 1→+3V3_RF_SRC, 2→PWR_FB_3V3RF |
| R651 | Device:R | 20.0k 1% (RLOWER) | Resistor_SMD:R_0402_1005Metric | TBD | 1→PWR_FB_3V3RF, 2→GND |
| R652 | Device:R | 110k 1% (RM_H) | Resistor_SMD:R_0402_1005Metric | TBD | 1→PWR_VCC_3V3RF, 2→PWR_MODE_3V3RF |
| R653 | Device:R | 51k 1% (RM_L) | Resistor_SMD:R_0402_1005Metric | TBD | 1→PWR_MODE_3V3RF, 2→GND |
| R654 | Device:R | 100k 1% (PG pull-up) | Resistor_SMD:R_0402_1005Metric | TBD | 1→+1V8_DIG, 2→PG_3V3RF |

### U651 — +5V_PA (TPS568230, FCCM 600 kHz)
| ref | lib_id | value | footprint | MPN | connections |
|---|---|---|---|---|---|
| U651 | Regulator_Switching:TPS51396A | TPS568230 | Package_DFN_QFN:Texas_RJE0020A_VQFN-20-1EP_3x3mm_P0.45mm_EP0.675x0.76mm | TPS568230RJER | 2,3,4,5 VIN→VIN_12V; 12 EN→PWR_EN_5VPA; 9 PGOOD→no-connect (not required; can be routed to a spare MCU input with 100k to +1V8_DIG); 15 MODE→PWR_MODE_5VPA; 17 VCC→PWR_VCC_5VPA; 11 SS→PWR_SS_5VPA; 14 FB→PWR_FB_5VPA; 1 BST→PWR_BST_5VPA; 6,19,20 SW→PWR_SW_5VPA; 7,8,18,21 GND→GND; 13 AGND→GND; 10,16 NC→GND |
| C663–C666 | Device:C | 10µF 50V X7R | Capacitor_SMD:C_1206_3216Metric | CGA5L1X7R1H106K160AC | 1→VIN_12V, 2→GND |
| C667 | Device:C | 100nF 50V X7R | Capacitor_SMD:C_0402_1005Metric | TBD | 1→VIN_12V, 2→GND |
| C668 | Device:C | 100nF 25V X7R | Capacitor_SMD:C_0402_1005Metric | TBD | 1→PWR_BST_5VPA, 2→PWR_SW_5VPA |
| C669 | Device:C | 1µF 16V X7R | Capacitor_SMD:C_0603_1608Metric | TBD | 1→PWR_VCC_5VPA, 2→GND |
| C670 | Device:C | 22nF 16V X7R | Capacitor_SMD:C_0402_1005Metric | TBD | 1→PWR_SS_5VPA, 2→GND |
| C671 | Device:C | 100pF 50V C0G (CFF) | Capacitor_SMD:C_0402_1005Metric | TBD | 1→+5V_PA, 2→PWR_FB_5VPA |
| C672–C676 | Device:C | 47µF 16V X5R/X7R | Capacitor_SMD:C_1210_3225Metric | TBD | 1→+5V_PA, 2→GND |
| L651 | Device:L | 2.2µH, Isat ≥ 14.4 A (≥ 6.2 A minimum) | UNRESOLVED (choose with MPN) | UNRESOLVED | 1→PWR_SW_5VPA, 2→+5V_PA |
| R655 | Device:R | 220k 1% (RUPPER) | Resistor_SMD:R_0402_1005Metric | TBD | 1→+5V_PA, 2→PWR_FB_5VPA |
| R656 | Device:R | 30.0k 1% (RLOWER) | Resistor_SMD:R_0402_1005Metric | TBD | 1→PWR_FB_5VPA, 2→GND |
| R657 | Device:R | 110k 1% (RM_H) | Resistor_SMD:R_0402_1005Metric | TBD | 1→PWR_VCC_5VPA, 2→PWR_MODE_5VPA |
| R658 | Device:R | 51k 1% (RM_L) | Resistor_SMD:R_0402_1005Metric | TBD | 1→PWR_MODE_5VPA, 2→GND |

### U652 — +3V3_AUX (TPS62933, 500 kHz, always on)
| ref | lib_id | value | footprint | MPN | connections |
|---|---|---|---|---|---|
| U652 | Regulator_Switching:TPS62933 | TPS62933 | Package_TO_SOT_SMD:SOT-583-8 | TPS62933DRLR | 3 VIN→VIN_12V; 2 EN→PWR_EN_AUX; 1 RT→no-connect (floating = 500 kHz); 7 SS→PWR_SS_AUX; 8 FB→PWR_FB_AUX; 6 BST→PWR_BST_AUX; 5 SW→PWR_SW_AUX; 4 GND→GND |
| C677, C678 | Device:C | 10µF 50V X7R | Capacitor_SMD:C_1206_3216Metric | CGA5L1X7R1H106K160AC | 1→VIN_12V, 2→GND |
| C679 | Device:C | 100nF 50V X7R | Capacitor_SMD:C_0402_1005Metric | TBD | 1→VIN_12V, 2→GND |
| C680 | Device:C | 100nF 25V X7R | Capacitor_SMD:C_0402_1005Metric | TBD | 1→PWR_BST_AUX, 2→PWR_SW_AUX |
| C681 | Device:C | 33nF 16V X7R | Capacitor_SMD:C_0402_1005Metric | TBD | 1→PWR_SS_AUX, 2→GND |
| C682–C684 | Device:C | 22µF 35V X5R | Capacitor_SMD:C_1206_3216Metric | C3216X5R1V226M160AC | 1→+3V3_AUX, 2→GND |
| C685 | Device:C | 10pF C0G (CFF, **DNP**) | Capacitor_SMD:C_0402_1005Metric | TBD | 1→+3V3_AUX, 2→PWR_FB_AUX |
| L652 | Device:L | 6.8µH, Isat 10 A | Inductor_SMD:L_Wuerth_XHMI-6060 (verify) | Würth 74439346068 | 1→PWR_SW_AUX, 2→+3V3_AUX |
| R659 | Device:R | 31.6k 1% (RFBT) | Resistor_SMD:R_0402_1005Metric | TBD | 1→+3V3_AUX, 2→PWR_FB_AUX |
| R660 | Device:R | 10.0k 1% (RFBB) | Resistor_SMD:R_0402_1005Metric | TBD | 1→PWR_FB_AUX, 2→GND |
| R661 | Device:R | 511k 1% (UVLO R1) | Resistor_SMD:R_0402_1005Metric | TBD | 1→VIN_12V, 2→PWR_EN_AUX |
| R662 | Device:R | 88.7k 1% (UVLO R2) | Resistor_SMD:R_0402_1005Metric | TBD | 1→PWR_EN_AUX, 2→GND |

### U653 — +1V8_DIG (TLV75518P)
| ref | lib_id | value | footprint | MPN | connections |
|---|---|---|---|---|---|
| U653 | Regulator_Linear:TLV70012_SOT23-5 | TLV75518PDBV | Package_TO_SOT_SMD:SOT-23-5 | TLV75518PDBVR | 1 IN→+3V3_AUX; 3 EN→+3V3_AUX; 2 GND→GND; 5 OUT→+1V8_DIG; 4 NC→no-connect |
| C686 | Device:C | 1µF 10V X7R | Capacitor_SMD:C_0603_1608Metric | TBD | 1→+3V3_AUX, 2→GND |
| C687 | Device:C | 1µF 10V X7R | Capacitor_SMD:C_0603_1608Metric | TBD | 1→+1V8_DIG, 2→GND |

### U654 — PWR_6V2_LO pre-regulator (TPS62933, 500 kHz)
| ref | lib_id | value | footprint | MPN | connections |
|---|---|---|---|---|---|
| U654 | Regulator_Switching:TPS62933 | TPS62933 | Package_TO_SOT_SMD:SOT-583-8 | TPS62933DRLR | 3 VIN→VIN_12V; 2 EN→PWR_EN_LO; 1 RT→no-connect; 7 SS→PWR_SS_LOPRE; 8 FB→PWR_FB_LOPRE; 6 BST→PWR_BST_LOPRE; 5 SW→PWR_SW_LOPRE; 4 GND→GND |
| C688, C689 | Device:C | 10µF 50V X7R | Capacitor_SMD:C_1206_3216Metric | CGA5L1X7R1H106K160AC | 1→VIN_12V, 2→GND |
| C690 | Device:C | 100nF 50V X7R | Capacitor_SMD:C_0402_1005Metric | TBD | 1→VIN_12V, 2→GND |
| C691 | Device:C | 100nF 25V X7R | Capacitor_SMD:C_0402_1005Metric | TBD | 1→PWR_BST_LOPRE, 2→PWR_SW_LOPRE |
| C692 | Device:C | 33nF 16V X7R | Capacitor_SMD:C_0402_1005Metric | TBD | 1→PWR_SS_LOPRE, 2→GND |
| C693, C694 | Device:C | 22µF 35V X5R | Capacitor_SMD:C_1206_3216Metric | C3216X5R1V226M160AC | 1→PWR_6V2_LO, 2→GND |
| C695 | Device:C | 10pF C0G (CFF, **DNP**) | Capacitor_SMD:C_0402_1005Metric | TBD | 1→PWR_6V2_LO, 2→PWR_FB_LOPRE |
| L653 | Device:L | 6.8µH, Isat 10 A | Inductor_SMD:L_Wuerth_XHMI-6060 (verify) | Würth 74439346068 | 1→PWR_SW_LOPRE, 2→PWR_6V2_LO |
| R663 | Device:R | 68.1k 1% (RFBT) | Resistor_SMD:R_0402_1005Metric | TBD | 1→PWR_6V2_LO, 2→PWR_FB_LOPRE |
| R664 | Device:R | 10.0k 1% (RFBB) | Resistor_SMD:R_0402_1005Metric | TBD | 1→PWR_FB_LOPRE, 2→GND |
| R665 | Device:R | 100k (EN pull-down) | Resistor_SMD:R_0402_1005Metric | TBD | 1→PWR_EN_LO, 2→GND |

### U655 / U656 — +5V_LO / +3V3_LO (TPS7A4701, ANY-OUT)
| ref | lib_id | value | footprint | MPN | connections |
|---|---|---|---|---|---|
| U655 | Regulator_Linear:TPS7A4701xRGW | TPS7A4701 (5.0 V) | Package_DFN_QFN:Texas_RGW0020A_VQFN-20-1EP_5x5mm_P0.65mm_EP3.15x3.15mm_ThermalVias | TPS7A4701RGWR | 15,16 IN→PWR_6V2_LO; 13 EN→PWR_6V2_LO; 1,20 OUT→+5V_LO; 3 SENSE/FB→+5V_LO (at load); 14 NR→PWR_NR_5VLO; 6 (3.2V)→GND; 10 (0.4V)→GND; 4,5,8,9,11,12→no-connect (open); 7 GND→GND; 21 EP→GND |
| C696 | Device:C | 10µF 16V X7R | Capacitor_SMD:C_1206_3216Metric | TBD | 1→PWR_6V2_LO, 2→GND |
| C697 | Device:C | 47µF 10V X7R | Capacitor_SMD:C_1210_3225Metric | TBD | 1→+5V_LO, 2→GND |
| C698 | Device:C | 1µF 16V X7R | Capacitor_SMD:C_0603_1608Metric | TBD | 1→PWR_NR_5VLO, 2→GND |
| U656 | Regulator_Linear:TPS7A4701xRGW | TPS7A4701 (3.3 V) | Package_DFN_QFN:Texas_RGW0020A_VQFN-20-1EP_5x5mm_P0.65mm_EP3.15x3.15mm_ThermalVias | TPS7A4701RGWR | 15,16 IN→PWR_6V2_LO; 13 EN→PWR_6V2_LO; 1,20 OUT→+3V3_LO; 3 SENSE/FB→+3V3_LO (at load); 14 NR→PWR_NR_3V3LO; 8 (1.6V)→GND; 11 (0.2V)→GND; 12 (0.1V)→GND; 4,5,6,9,10→no-connect (open); 7 GND→GND; 21 EP→GND |
| C699 | Device:C | 10µF 16V X7R | Capacitor_SMD:C_1206_3216Metric | TBD | 1→PWR_6V2_LO, 2→GND |
| C700 | Device:C | 47µF 10V X7R | Capacitor_SMD:C_1210_3225Metric | TBD | 1→+3V3_LO, 2→GND |
| C701 | Device:C | 1µF 16V X7R | Capacitor_SMD:C_0603_1608Metric | TBD | 1→PWR_NR_3V3LO, 2→GND |

### U657 — PWR_VNEG (TPS65131 inverting stage; boost stage disabled)
| ref | lib_id | value | footprint | MPN | connections |
|---|---|---|---|---|---|
| U657 | Regulator_Switching:TPS65130RGE | TPS65131 | Package_DFN_QFN:VQFN-24-1EP_4x4mm_P0.5mm_EP2.45x2.45mm_ThermalVias | TPS65131RGER | 4 VIN→PWR_VIN_NEGCONV; 5,6 INN→+3V3_AUX; 1,24 INP→PWR_INP_NEG; 23 VPOS→PWR_VPOS_NEG; 22 FBP→PWR_FBP_NEG; 21 CP→PWR_CP_NEG; 8 ENP→GND; 9 PSP→GND; 10 ENN→PWR_EN_NEG; 11 PSN→GND (forced PWM); 7 BSW→no-connect (DS §8.2.2.5); 17 VREF→PWR_VREF_NEG; 16 FBN→PWR_FBN_NEG; 15 VNEG→PWR_VNEG; 13,14 OUTN→PWR_OUTN_NEG; 18 CN→PWR_CN_NEG; 19 AGND→GND; 2,3 PGND→GND; 25 EP→GND; 12,20 NC→no-connect |
| R666 | Device:R | 100Ω (VIN RC filter) | Resistor_SMD:R_0402_1005Metric | TBD | 1→+3V3_AUX, 2→PWR_VIN_NEGCONV |
| C704 | Device:C | 100nF 10V X5R | Capacitor_SMD:C_0402_1005Metric | TBD | 1→PWR_VIN_NEGCONV, 2→GND |
| C703 | Device:C | 4.7µF 10V X5R (INN input) | Capacitor_SMD:C_0805_2012Metric | TBD | 1→+3V3_AUX, 2→GND |
| C702 | Device:C | 4.7µF 10V X5R (INP input) | Capacitor_SMD:C_0805_2012Metric | TBD | 1→+3V3_AUX, 2→GND |
| L654 | Device:L | 4.7µH (boost L1, idle) | Inductor_SMD:L_6.3x6.3_H3 (verify) | EPCOS/TDK B82462G4472M000 | 1→+3V3_AUX, 2→PWR_INP_NEG |
| D650 | Device:D_Schottky | MBRM120 (boost D1, idle) | Diode_SMD:D_Powermite_KA (verify pad map) | MBRM120 (onsemi) | K→PWR_VPOS_NEG, A→PWR_INP_NEG |
| C705 | Device:C | 4.7µF 25V X7R (VPOS) | Capacitor_SMD:C_0805_2012Metric | TBD | 1→PWR_VPOS_NEG, 2→GND |
| R667 | Device:R | 1M 1% (R1) | Resistor_SMD:R_0402_1005Metric | TBD | 1→PWR_VPOS_NEG, 2→PWR_FBP_NEG |
| R668 | Device:R | 130k 1% (R2) | Resistor_SMD:R_0402_1005Metric | TBD | 1→PWR_FBP_NEG, 2→GND |
| C706 | Device:C | 10nF 16V X7R (CP) | Capacitor_SMD:C_0402_1005Metric | TBD | 1→PWR_CP_NEG, 2→GND |
| C707 | Device:C | 220nF 6.3V+ X5R (VREF) | Capacitor_SMD:C_0402_1005Metric | TBD | 1→PWR_VREF_NEG, 2→GND |
| R669 | Device:R | 523k 1% (R3) | Resistor_SMD:R_0402_1005Metric | TBD | 1→PWR_VNEG, 2→PWR_FBN_NEG |
| R670 | Device:R | 100k 1% (R4) | Resistor_SMD:R_0402_1005Metric | TBD | 1→PWR_FBN_NEG, 2→PWR_VREF_NEG |
| C708 | Device:C | 15pF C0G (C10, FF) | Capacitor_SMD:C_0402_1005Metric | TBD | 1→PWR_VNEG, 2→PWR_FBN_NEG |
| C709 | Device:C | 4.7nF 50V C0G (CN) | Capacitor_SMD:C_0402_1005Metric | TBD | 1→PWR_CN_NEG, 2→GND |
| L655 | Device:L | 4.7µH (inverter L2) | Inductor_SMD:L_6.3x6.3_H3 (verify) | EPCOS/TDK B82462G4472M000 | 1→PWR_OUTN_NEG, 2→GND |
| D651 | Device:D_Schottky | MBRM120 (inverter D2) | Diode_SMD:D_Powermite_KA (verify pad map) | MBRM120 (onsemi) | K→PWR_OUTN_NEG, A→PWR_VNEG |
| C710–C713 | Device:C | 4.7µF 25V X7R | Capacitor_SMD:C_0805_2012Metric | TBD | 1→GND, 2→PWR_VNEG |
| R671 | Device:R | 100k (ENN pull-down) | Resistor_SMD:R_0402_1005Metric | TBD | 1→PWR_EN_NEG, 2→GND |

### U658 / U659 — -5V_BF / -3V3_SW (TPS7A3301)
| ref | lib_id | value | footprint | MPN | connections |
|---|---|---|---|---|---|
| U658 | Regulator_Linear:TPS7A3301RGW | TPS7A3301 (−5.0 V) | Package_DFN_QFN:Texas_RGW0020A_VQFN-20-1EP_5x5mm_P0.65mm_EP3.15x3.15mm_ThermalVias | TPS7A3301RGWR | 15,16 IN→PWR_VNEG; 13 EN→PWR_VNEG; 1,20 OUT→-5V_BF; 3 FB→PWR_FB_5VBF; 14 NR/SS→PWR_NR_5VBF; 7 GND→GND; 21 EP→GND |
| C714 | Device:C | 10µF 16V X7R | Capacitor_SMD:C_1206_3216Metric | TBD | 1→GND, 2→PWR_VNEG |
| C715 | Device:C | 47µF 10V X7R | Capacitor_SMD:C_1210_3225Metric | TBD | 1→GND, 2→-5V_BF |
| C716 | Device:C | 100nF 16V X7R | Capacitor_SMD:C_0402_1005Metric | TBD | 1→GND, 2→PWR_NR_5VBF |
| C717 | Device:C | 10nF 16V X7R (CFF) | Capacitor_SMD:C_0402_1005Metric | TBD | 1→PWR_FB_5VBF, 2→-5V_BF |
| R672 | Device:R | 332k 1% (R1) | Resistor_SMD:R_0402_1005Metric | TBD | 1→-5V_BF, 2→PWR_FB_5VBF |
| R673 | Device:R | 102k 1% (R2) | Resistor_SMD:R_0402_1005Metric | TBD | 1→PWR_FB_5VBF, 2→GND |
| U659 | Regulator_Linear:TPS7A3301RGW | TPS7A3301 (−3.3 V) | Package_DFN_QFN:Texas_RGW0020A_VQFN-20-1EP_5x5mm_P0.65mm_EP3.15x3.15mm_ThermalVias | TPS7A3301RGWR | 15,16 IN→PWR_VNEG; 13 EN→PWR_VNEG; 1,20 OUT→-3V3_SW; 3 FB→PWR_FB_3V3SW; 14 NR/SS→PWR_NR_3V3SW; 7 GND→GND; 21 EP→GND |
| C718 | Device:C | 10µF 16V X7R | Capacitor_SMD:C_1206_3216Metric | TBD | 1→GND, 2→PWR_VNEG |
| C719 | Device:C | 47µF 10V X7R | Capacitor_SMD:C_1210_3225Metric | TBD | 1→GND, 2→-3V3_SW |
| C720 | Device:C | 100nF 16V X7R | Capacitor_SMD:C_0402_1005Metric | TBD | 1→GND, 2→PWR_NR_3V3SW |
| C721 | Device:C | 10nF 16V X7R (CFF) | Capacitor_SMD:C_0402_1005Metric | TBD | 1→PWR_FB_3V3SW, 2→-3V3_SW |
| R674 | Device:R | 200k 1% (R1) | Resistor_SMD:R_0402_1005Metric | TBD | 1→-3V3_SW, 2→PWR_FB_3V3SW |
| R675 | Device:R | 110k 1% (R2) | Resistor_SMD:R_0402_1005Metric | TBD | 1→PWR_FB_3V3SW, 2→GND |

Refs used: U650–U659, C650–C721, R650–R675, L650–L655, D650–D651.

## (c) Calculations and datasheet references

### U650 / U651 TPS568230 (SLVSEY5C)
- **Input range and enable.** VIN 4.5–18 V (§6.3 p4). The EN pin's recommended maximum is 3.6 V and its absolute maximum is 4 V (§6.1, §6.3 p4). VENH is 1.21 V min / 1.31 V typ / 1.4 V max, and VENL is 0.95 V min (§6.5 p6). A 1.8 V logic high is ≥ 1.4 V, so it works, with 0.4 V margin. The pin has an internal 2 µA pull-down, so a floating EN is off (§7.4.6 p17). Drive EN directly from PWR_EN_3V3 / PWR_EN_5VPA.
- **Feedback.** VOUT = 0.6·(1+RUPPER/RLOWER) (Eq 4, §8.2.2.1.1 p19). VFB is 594/600/606 mV at 25 °C and 592/600/611 mV over −40…125 °C (§6.5 p5).
  - 3.3 V: Table 3 (p20) gives 20 k / 90 k. Using 20.0 k / 90.9 k gives 3.327 V nominal.
    - Max = 0.611·(1+90.9·1.01/(20·0.99)) = **3.444 V**.
    - Min = 0.592·(1+90.9·0.99/(20·1.01)) = **3.229 V**.
  - 5.0 V: Table 3 gives 30 k / 220 k, so the nominal is exactly 5.000 V.
    - Max = 0.611·(1+220·1.01/(30·0.99)) = 0.611·8.4815 = **5.182 V**.
    - Min = 0.592·(1+220·0.99/(30·1.01)) = **4.847 V**.
    - **5.182 V is below the 5.5 V ADTR1107 absolute maximum**, leaving 318 mV for ripple plus load-release overshoot. The DS example (1 V out) shows ±40 mV for a 0–8 A step and 18 mV p-p ripple (Table 2 p18). The 5 V overshoot is not specified, see (d).
    - The TPS568230 OVP trips at 125 % = 6.25 V (§6.5 p6, §7.3.6 p15), so **OVP does not protect the PA**.
- **CFF.** Table 3 gives 47–330 pF for 3.3 V and 5 V. 100 pF is chosen inside that range; tune it from the load-step measurement.
- **Frequency and mode.** Table 1 (p17): RM_H = 110 k and RM_L = 51 k from VCC give FCCM at 600 kHz. FCCM is chosen for a fixed switching frequency near RF circuits.
- **Inductor.** Table 3 gives 1.5 µH for 3.3 V and 2.2 µH for 5 V at 600 kHz. Ripple is from Eq 5/6 (p19) at VIN(max) = 13 V:
  - 3.3 V: ΔI = 3.3·(13−3.3)/(13·1.5 µ·600 k) = 2.74 A. Peak at 4 A = 5.37 A.
  - 5 V: ΔI = 5·(13−5)/(13·2.2 µ·600 k) = 2.33 A. Peak at 5 A = 6.17 A.
  - The DS (p19) says to choose Isat above the peak current under current limit. Valley OCL is 12 A max (§6.5 p5), so the target is Isat ≥ 12 + ΔI ≈ 14.7 A (3.3 V) / 14.4 A (5 V).
  - The DS names no inductor part number → MPN UNRESOLVED.
- **COUT.** 66–500 µF (Table 3). Use 4×47 µF (3.3 V) and 5×47 µF (5 V). The effective value after DC bias must stay ≥ 66 µF (UNRESOLVED: vendor DC-bias curve).
- **CIN.** "40 µF X5R/X7R recommended" (§8.2.2.1.4 p20) → 4×10 µF 50 V plus 100 nF. Eq 8: ICIN(rms) at 5 V / 5 A / 11 V = 5·√(0.4545·0.5455) = 2.49 A, shared across 4 capacitors.
- **VCC and BST.** VCC needs 1 µF (p20, pin table p3). BST needs 0.1 µF (pin table p3).
- **Soft-start.** Tss = Css·VREF/Iss = 22 nF·0.6 V/5 µA = **2.64 ms** (Eq 2 §7.3.2 p14; the internal minimum is 1.3 ms). The ramp starts about 0.6 ms after EN because of the MODE read (Fig 29 p17). PGOOD then rises 1 ms after VFB passes 90 % (§6.5 p5, §7.3.4 p14).
- **PGOOD.** Open drain, 6 V absolute maximum, VOL ≤ 0.4 V at 4 mA (§6.1 p4, §6.5 p5). The DS recommends 100 k to VCC (§7.3.4 p14). Here it is pulled up with 100 k to +1V8_DIG instead, because the MCU input is 1.8 V; that is 18 µA when low. PGOOD is low during soft-start, below 85 % or above 115 %, on UVP/OVP/OTP, and when EN is low.
- **Discharge.** An internal discharge of about 420 Ω on SW is active when EN = 0 (RDIS §6.5 p5, §7.3.8 p15), and the output is also discharged on UVLO and OTP (§7.3.7, §7.3.9 p15). The DS says this discharge is slow.
- **Efficiency and dissipation.** From Fig 15 (FCCM 600 kHz, VIN = 12 V, p9):
  - 3.3 V at 4 A: about 92 %, so Pin ≈ 14.3 W and the loss is ≈ 1.15 W.
  - 5 V at 5 A: about 93 %, so Pin ≈ 26.9 W and the loss is ≈ 1.9 W.
  - These losses include the inductor. RθJA is 44.9 °C/W on a JEDEC board (§6.4 p5). The real board needs the thermal vias of the _ThermalVias footprint variant if it is used.

### U652 / U654 TPS62933 (SLUSEA4D)
- **Input range and reference.** VIN 3.8–30 V. VFB is 784/800/816 mV over −40…150 °C (§8.5 p6), which is ±2 % (§9.3.3 p19).
- **Feedback.** RFBT = (VOUT−VREF)/VREF·RFBB (Eq 1 p19 / Eq 14 p29), with RFBB = 10 k recommended.
  - AUX: RFBT = 31.6 k gives 3.328 V nominal (Table 10-2 p32 gives 31.3 k).
    - Max = 0.816·(1+31.6·1.01/9.9) = **3.447 V**.
    - Min = 0.784·(1+31.6·0.99/10.1) = **3.212 V**.
  - LO pre-regulator: RFBT = 68.1 k gives 6.248 V nominal.
    - Max = 0.816·(1+68.1·1.01/9.9) = **6.486 V**.
    - Min = 0.784·(1+68.1·0.99/10.1) = **6.017 V**.
- **Frequency.** RT floating = 500 kHz (Table 9-1 p20).
- **Inductor.** Eq 16 (p30) with K = 0.4, IOUT_MAX = 3 A, VIN = 13 V gives L ≥ 4.1 µH (3.3 V) and ≥ 5.4 µH (6.25 V). The DS-named 6.8 µH Würth 74439346068 is used for both: Isat 10 A ≥ IHS_LIMIT max 5.8 A (§10.2.2.7 p31, §8.5 p6). Ripple from Eq 15 at 13 V:
  - AUX: 0.72 A.
  - LO pre-regulator: 0.95 A.
  - Both are ≥ 10 % of 3 A, the rule-of-thumb minimum (p31).
- **COUT.** Table 10-2 (p32):
  - 3.3 V needs 40 µF effective typical, 15 µF minimum → 3×22 µF C3216X5R1V226M160AC (the part named on p32).
  - 5 V needs 20 µF typical, 10 µF minimum. The 6.25 V rail uses 2×22 µF, matching the DS example (p32).
- **CIN.** 2× CGA5L1X7R1H106K160AC plus 100 nF (§10.2.2.9 p32).
- **BST.** 0.1 µF, ≥ 16 V, X5R or better (§10.2.2.5 p29). The optional series resistor R4 (< 10 Ω, shown as 0 Ω in Fig 10-1 p28) is omitted.
- **CFF.** 10 pF, optional (§10.2.2.10 p33), so it is placed as DNP.
- **Soft-start.** tSS = CSS·0.8/5.5 µA (Eq 6 p22). 33 nF gives **4.8 ms**, as in the DS example (§10.2.2.4 p29). The minimum is 6.8 nF, and the SS pin must not float.
- **AUX enable.** EN must stay ≤ 5.5 V (§8.3 p5), so EN cannot be tied straight to 12 V. The documented UVLO divider is used (§9.3.6 p20–21, Eq 3/4/5; DS example §10.2.2.6 p30): R1 = 511 k, R2 = 88.7 k gives VSTART = 8 V and VSTOP = 7 V.
  - Recalculated with Ip = 0.7 µA, Ih = 1.4 µA, VEN_FALL = 1.17 V, VEN_RISE = 1.21 V: R1 = 517 k and R2 = 86.6 k, which agrees with the example values.
  - VEN at 13 V = 88.7/599.7·13 + 511k·88.7k·2.1µA/599.7k = 1.92 + 0.16 = **2.08 V < 5.5 V** ✓.
  - Note: the DS text says "R2 = 80.7 kΩ" but the Fig 10-1 schematic shows 88.7 k. The 88.7 k value matches the formula.
- **LO pre-regulator enable.** EN has an internal pull-up (0.7 µA), so a floating EN means on (pin table p3, §9.3.6 p20). R665 = 100 k to GND is therefore required: it gives 70 mV, which is off. A 1.8 V GPIO high exceeds VEN_RISE max 1.28 V (§8.5 p6) ✓. The DS explicitly allows GPIO drive (§9.3.6 p20).
- **Variant note.** The plain TPS62933 runs PFM at light load and has ±6 % spread spectrum (§9.3.10 p23).
- **Discharge.** None stated in the DS; shutdown is described only as "stops switching" (§9.4.8 p27).
- **Efficiency.**
  - AUX: Fig 8-19 (3.3 V, 12 V in, 1.2 MHz; p12) shows ≈ 90 % at 1 A. 500 kHz is expected to be at least that good. Loss ≈ 0.37 W.
  - LO pre-regulator: Fig 8-22 (5 V, 500 kHz, 6.8 µH, 12 V in; p12) shows ≈ 95 % at 0.8 A. Out ≈ 6.25 V·0.76 A = 4.75 W, so in ≈ 5.0 W.

### U653 TLV75518P (SBVS320D)
- **Ratings.** VIN 1.45–5.5 V and IOUT ≤ 500 mA (§5.3 p4). CIN and COUT must be ≥ 1 µF, with ≥ 0.47 µF effective (§5.3 p4, pin table note p3).
- **Dropout.** For 1.8 V out, VDO ≤ 400 mV at 500 mA (§5.5 p6). The minimum AUX of 3.212 V leaves plenty of headroom.
- **Enable.** EN is tied to IN, as the DS allows (§6.3.2 p12); VHI is 1 V (p6).
- **Accuracy and start-up.** Accuracy is ±1 % (−40…85 °C). tSTR is 550 µs typ (p6).
- **Discharge.** An active 120 Ω pull-down is applied when disabled or in UVLO (RPULLDOWN p6, §6.3.1 p12).
- **Dissipation.** (3.3−1.8)·0.15 = 0.225 W. That is +23 °C at RθJA 100.8 °C/W (EVM board) or +52 °C at 231 °C/W (JEDEC) (§5.4 p5).

### U655 / U656 TPS7A4701 (SBVS204G)
- **ANY-OUT.** VOUT = 1.4 V + Σ(grounded pins) (Eq 2 §6.5.1 p12, Table 6-2 p13).
  - 5.0 V = 0P4V + 3P2V to GND.
  - 3.3 V = 0P1V + 0P2V + 1P6V to GND.
  - Unused program pins are left open. SENSE/FB goes to OUT (pin table p3–4).
- **Accuracy.** ±1 % at 25 °C, and ±2.5 % overall for VI ≥ VO+1.0 V, IO 0–1 A (§5.5 p6). The minimum pre-regulator output of 6.017 V is ≥ 5.0 + 1.0 V, so the overall-accuracy condition holds for the 5 V LDO.
- **Dropout.** VDO is 307 mV typ / 450 mV max at 1 A (p6) and scales with current (§7.2.2.2 p16): ≤ 180 mV at 0.4 A. The minimum headroom of 1.02 V is enough ✓.
- **Enable.** VEN(HI) is **2.0 V min** (p6), so **1.8 V logic cannot drive EN**. EN is tied to IN instead (pin table p3, §6.3.2 p11), and PWR_EN_LO gates the U654 pre-regulator.
- **Capacitors.** CIN 10 µF; COUT 47 µF ceramic, with ≥ 10 µF required (pin table p3–4, §7.2.2.1.1 p16); CNR 1 µF (pin table p3). Apply 50 % derating (§7.2.2.1 p15).
- **Start-up.** tSS = 100000·CNR·ln((VR+5)/5) (Eq 5 §7.2.2.4 p16; the operator was checked on the rendered page).
  - 5 V: 100 k·1 µF·ln 2 = **69 ms**.
  - 3.3 V: ln 1.66 → **51 ms**.
  - Each LDO starts once its input exceeds the UVLO of 2.67 V (p6).
- **Disable.** OUT is high-Z when disabled, with no discharge (§6.4 p12).
- **Dissipation.**
  - +5V_LO: nominal (6.25−5)·0.4 = 0.50 W; worst (6.49−5)·0.4 = 0.60 W.
  - +3V3_LO: nominal (6.25−3.3)·0.35 = 1.03 W; worst 1.12 W, which is +36 °C at RθJA 32.5 °C/W (§5.4 p5).
- **Noise.** 4.67 µVrms for 6 V → 5 V with CNR 1 µF and COUT 50 µF (p6).

### U657 TPS65131 (SLVS493E)
- **Supply, enable and mode pins.**
  - Supplied from +3V3_AUX (2.7–5.5 V, §6.3 p4).
  - ENN has VIH 1.4 V min and VIL 0.4 V max (§6.5 p5), so 1.8 V logic is OK. Its absolute maximum is VIN+0.3 V (§6.1 p4).
  - ENP = GND disables the boost. The DS says "both converters can be enabled or disabled individually" (§7.3.3 p9).
  - PSN = PSP = GND gives forced PWM (§7.4.1 p10).
  - R671 (100 k) holds ENN low while PWR_EN_NEG floats.
- **VNEG.** VNEG = −VREF·R3/R4 with R4 < 200 k (Eq 2 §8.2.2.1.2 p13). R3 = 523 k and R4 = 100 k give −1.213·5.23 = **−6.344 V**.
  - Worst case, with VNEG = VFBN − (VREF−VFBN)·R3/R4, VREF 1.200–1.225 V and VFBN ±24 mV (§6.5 p5):
    - Least negative: 0.024 − 1.176·5.1265 = **−6.005 V**.
    - Most negative: −0.024 − 1.249·5.3357 = **−6.688 V**.
  - The divider current is 12 µA, above the ≥ 5 µA the DS asks for (p13).
- **Feed-forward.** C10 = 7.5/R3 (Eq 12 p15). The DS example gives 7.5 pF for 1 MΩ, so for 523 k: 14.3 pF → **15 pF**.
- **Compensation.** CN 4.7 nF and CP 10 nF (§8.2.2.6.2 p15). VREF bypass is 220 nF (pin table p3).
- **VIN filter.** RC filter of 100 Ω + 100 nF between INN and VIN (§8.2.3.1 p16).
- **Inductor.** 4.7 µH recommended; 3.3–6.8 µH allowed (p14). EPCOS B82462-G4472 is named in Table 8-2 (p12).
  - Peak current from Eq 4 (p13): IL_N = (VI+|VNEG|)/(VI·0.64)·INEG = (3.212+6.688)/(3.212·0.64)·0.255 = **1.23 A** worst case.
  - That is below the minimum 1.8 A switch limit (§6.5 p5). The Isat of the named part is not given in the DS → UNRESOLVED (should be ≥ 2.2 A, the maximum ILIMN).
- **Diode.** MBRM120 (1 A, 20 V) named in Table 8-2 (p12). Reverse voltage is about 3.45 + 6.69 = 10.1 V < 20 V ✓.
- **Output capacitance.** 4×4.7 µF 25 V X7R (Table 8-2 p12). Eq 8 (p14) with ΔV = 10 mV: C5min = 0.255·6.69/(1.25 MHz·0.01·(6.69+3.21)) = **13.8 µF**, against 18.8 µF nominal.
- **Input capacitance.** ≥ 4.7 µF each on INP and INN (§8.2.2.3.1 p14).
- **Capability.** Fig 6-4 (p7), VIN 3.3 V: about 600 mA at −4 V and 300 mA at −10 V, so roughly 450 mA at −6.3 V by interpolation. 255 mA is needed ✓.
- **Soft-start.** The switch-current limit ramps over about 1 ms (§7.3.5 p9); there is no external soft-start pin.
- **Protection and power-down.**
  - OVP shuts the converter down at about +5 % on the feedback (§7.3.6 p9).
  - When disabled, the inverter's internal PMOS disconnects the load from the input (§7.3.4 p9).
  - No active output discharge is stated.
- **Efficiency.** Fig 8-9/8-11 (p18), VIN 3 V, about 250 mA: roughly 75–80 %. Pout = 6.34·0.255 = 1.62 W, so Pin ≈ 2.1 W at 77 %. That is **≈ 0.64 A from +3V3_AUX**.
- **Boost stage, disabled.** Parts L654, D650, C705, R667/R668 (DS 10.5 V example values) and C706 follow Fig 8-1/Table 8-2 so that the DS topology stays complete. C705 is reduced to a single capacitor. With ENP = GND, VPOS sits at about VIN − Vf. Whether these parts may be omitted is UNRESOLVED.

### U658 / U659 TPS7A3301 (SBVS169D)
- **Feedback.** R1 = R2·(|VOUT|/|VREF| − 1), with VREF −1.175 V typ (−1.192…−1.157 V at 25 °C) (Eq 2 p15, §6.5 p6). R2 must be ≤ 240 k (§6.3 p5) and |VREF|/R2 > 5 µA (p15).
  - −5 V: Table 2 (p15) gives 332 k / 102 k → −4.999 V; divider current 11.5 µA.
    - Worst with 1 % resistors: 1.157·(1+332·0.99/(102·1.01)) = **4.848 V** and 1.192·(1+332·1.01/(102·0.99)) = **5.150 V**.
    - Overall accuracy is ±2.5 % (p6). The ADAR1000 AVDD1 window of −4.75…−5.25 V holds ✓.
  - −3.3 V: Table 2 gives 200 k / 110 k → −3.311 V; worst −3.219 … **−3.403 V**, inside the −3.6 V absolute maximum ✓.
- **Enable.** EN is dual-polarity: enabled at |VEN| ≥ 2 V and disabled for −0.4…+0.4 V (§6.5 p6, §7.3.2 p13). **1.8 V logic is below the 2 V threshold.** EN is tied to IN (pin table p4: "EN can be connected to IN"), and PWR_EN_NEG gates the TPS65131.
- **Input headroom.** The overall-accuracy condition is |VIN| ≥ |VOUT|+1 V (p6). For the −5 V LDO the minimum |PWR_VNEG| of 6.005 V meets it ✓. Dropout is 325 mV typ / 800 mV max at 1 A (p6), scaled to ≤ 200 mV at 0.25 A.
- **Capacitors.** CIN and COUT are 10 µF minimum, 47 µF recommended (§6.3 p5, §8.1.3 p16). Here CIN = 10 µF (as in the DS example §8.2.2 p18) and COUT = 47 µF. CFF = 10 nF and CNR = 1 µF are recommended (§8.1.4 p16).
- **Soft-start.** tSS(ms) = 1.2·CNR(nF) (Eq 1 §7.3.3 p13). The recommended 1 µF would give **1.2 s**. 100 nF is used instead, as in the DS example (§8.2.2 p18), giving **120 ms**. Noise is somewhat higher than with 1 µF.
- **Discharge.** None stated.
- **Dissipation.**
  - −5 V: nominal (6.344−5)·0.25 = 0.34 W; worst (6.688−5)·0.25 = 0.42 W, which is +14 °C at RθJA 33.7 °C/W (§6.4 p5).
  - −3.3 V: about 15 mW.

### Start-up ramp summary (0→100 %)
| Rail | Ramp | Source |
|---|---|---|
| +3V3_AUX | 4.8 ms, starting once VIN_12V > 8 V | TPS62933 Eq 6, UVLO divider |
| +1V8_DIG | ~0.55 ms after +3V3_AUX | TLV755P tSTR |
| +3V3_RF_SRC / +5V_PA | ~0.6 ms delay + 2.64 ms ramp after EN; PG_3V3RF +1 ms | TPS568230 Eq 2, Fig 29 |
| PWR_6V2_LO | 4.8 ms after PWR_EN_LO | TPS62933 Eq 6 |
| +5V_LO / +3V3_LO | 69 ms / 51 ms (CNR-limited; the pre-regulator is already up) | TPS7A47 Eq 5 |
| PWR_VNEG | ~1 ms | TPS65131 §7.3.5 |
| -5V_BF / -3V3_SW | ~120 ms each | TPS7A33 Eq 1 |

### +3V3_AUX budget
| Load | Current |
|---|---|
| TPS65131 | ≈ 0.64 A |
| +1V8_DIG | ≤ 0.15 A |
| Telemetry / comparators | ≈ 0.2 A |
| **Total** | **≈ 1.0 A** |

This is at the stated ~1 A budget. The TPS62933 can supply 3 A, so the regulator is not the limit.

### VIN_12V total
14.3 W + 26.9 W + 3.7 W + 5.0 W ≈ **50 W, which is ≈ 4.2 A at 12 V**.

## (d) UNRESOLVED / to verify
1. **L650 / L651 MPN and footprint.** The TPS568230 DS names no inductor. Requirements:
   - L650: 1.5 µH, Isat ≥ 14.7 A.
   - L651: 2.2 µH, Isat ≥ 14.4 A.
   - At the absolute minimum, Isat must exceed the full-load peak (5.4 A / 6.2 A).
   - Pick from a vendor catalogue and set the footprint to match.
2. **TPS568230 COUT.** Confirm with the vendor DC-bias curves that 4×47 µF / 10 V (3.3 V) and 5×47 µF / 16 V (5 V) give ≥ 66 µF effective. Choose MPNs.
3. **CFF of 100 pF on U650 / U651.** This is inside the DS range of 47–330 pF; final value to be set by load-step and Bode measurement.
4. **+5V_PA overshoot.** The worst-case DC level is 5.182 V. Load-release overshoot at 5 V / 5 A is not specified in the DS, and TPS568230 OVP (6.25 V) does not protect the 5.5 V ADTR1107. Measure at bring-up, or add a clamp or crowbar (not designed here).
5. **AUX COUT DC bias.** The effective capacitance of 3× C3216X5R1V226M160AC at 3.3 V must be ≥ 15 µF minimum (40 µF typical); check the TDK DC-bias data.
6. **Würth 74439346068 footprint.** Mapping it to `Inductor_SMD:L_Wuerth_XHMI-6060` needs to be checked against the Würth drawing.
7. **EPCOS B82462G4472.** Its Isat is not given in the TPS65131 DS; it should be ≥ 2.2 A (maximum ILIMN), and the worst-case peak is 1.23 A. The `L_6.3x6.3_H3` footprint fit needs to be checked.
8. **MBRM120 pad numbering.** Check the cathode/anode pad assignment against `Diode_SMD:D_Powermite_KA` and the `Device:D_Schottky` pin numbering (pin 1 = K) before layout.
9. **TPS65131 boost stage depopulation.** The DS does not say whether INP/VPOS/FBP and the boost passives may be left unpopulated when ENP = GND. They are kept here: L654, D650, C705, R667, R668, C706.
10. **TPS7A33 soft-start choice.** CNR = 100 nF gives 120 ms; the DS-recommended 1 µF gives 1.2 s. Confirm against the ADAR1000 / ADTR1107 power sequencing (not checked here).
11. **Sequencing between rails** (for example, VSS_SW must be negative before VDD_PA is applied) is not analysed. PWR_EN_* ordering is left to firmware.
12. **TPS62933 variant for the LO pre-regulator.** The plain TPS62933 has PFM and ±6 % spread spectrum. TPS62933F has FCCM and no spread spectrum (§9.3.10 p23). The `TPS62933F` KiCad symbol was not checked.
13. **Bulk electrolytic on VIN_12V.** The TPS568230 DS says bulk capacitance is needed "depending on the application" (p20); it depends on the bench lead length and is not sized.
14. **Pull-down duplication.** R665 (PWR_EN_LO) and R671 (PWR_EN_NEG) are added because those EN inputs would otherwise float, and on the TPS62933 a floating EN means on. Omit them if the MCU sheet already has pull-downs on these nets. PWR_EN_5VPA relies on the TPS568230 internal 2 µA pull-down.
15. **KiCad default footprint for TPS568230.** `Texas_RJE0020A_..._EP0.675x0.76mm` was not compared against the DS land pattern (DS §12, not reviewed).
