# H2-A Unresolved schematic issues

Generated from `H2A_BUILD_LOG.json`. Every item here is left **unconnected** in the schematic or is an explicit `TBD_*` placeholder block (not a part), so KiCad ERC reports it instead of hiding it. Grouped across the four identical chains.

| # | Item | Why unresolved / what closes it | Blocks | Where |
|---|---|---|---|---|
| U1 | footprint | SMA connector type/footprint not selected | layout | J101 (chain1.kicad_sch), J201 (chain2.kicad_sch), J301 (chain3.kicad_sch), J401 (chain4.kicad_sch) |
| U2 | AVDD1/AVDD3 decoupling | values not in ADAR1000 Rev B; need ADAR1000-EVALZ schematic | schematic | UBF1 (bf1.kicad_sch), UBF2 (bf2.kicad_sch), UBF3 (bf3.kicad_sch), UBF4 (bf4.kicad_sch) |
| U3 | footprint | 88-terminal LGA CC-88-1 land pattern only as image in DS; use ADI footprint | layout | UBF1 (bf1.kicad_sch), UBF2 (bf2.kicad_sch), UBF3 (bf3.kicad_sch), UBF4 (bf4.kicad_sch) |
| U4 | antenna interface | feed connector/antenna EM design not done (H1 M6) | EM | JF1 (fe1.kicad_sch), JF2 (fe1.kicad_sch), JF3 (fe1.kicad_sch) ... (+13) |
| U5 | VDD_PA/VDD_LNA/VDD_SW/VSS_SW decoupling | values not in ADTR1107 Rev C; need ADTR1107-EVAL schematic | schematic | UFE1-UFE4 (fe1.kicad_sch), UFE5-UFE8 (fe2.kicad_sch), UFE9-UFE12 (fe3.kicad_sch), UFE13-UFE16 (fe4.kicad_sch) |
| U6 | LNA supply in TX | ADTR1107 TX power-up sequence sets VDD_LNA = 0 V; design keeps 3.3 V and pinches gate via LNA_BIAS (ADAR1000 p45). Needs ADI confirmation | vendor | UFE1-UFE4 (fe1.kicad_sch), UFE5-UFE8 (fe2.kicad_sch), UFE9-UFE12 (fe3.kicad_sch), UFE13-UFE16 (fe4.kicad_sch) |
| U7 | footprint | UDB 12-lead 3x2 QFN; use ADI land pattern | layout | UMX1 (conv1.kicad_sch), UMX2 (conv2.kicad_sch), UMX3 (conv3.kicad_sch), UMX4 (conv4.kicad_sch) |
| U8 | loop filter CPOUT->VTUNE, RS_SW | no reference loop filter in ADF4371 Rev 0; design with ADIsimPLL for 10 MHz PFD / 6.6 GHz | schematic | U501 (lo.kicad_sch) |
| U9 | VD1/VD2 bias network (L1 3.3 nH, C1-C4, ML1-ML7) | AVA-183A+ Fig 2 values known but node-by-node wiring not verified; pins left open. Gain/P1dB not specified 5-8 GHz | schematic | U502 (lo.kicad_sch) |
| U10 | footprints | LGA-48 CC-48-4 (EP size ambiguous in DS), DQ849, DG1677-2: use vendor land patterns | layout | U501/U502/U503 (lo.kicad_sch) |
| U11 | regulator for +3V3_RF_SRC | +3.3 V RF, >= 4 A (4x ADAR1000 350 mA TX + 16x ADTR1107 LNA 80 mA + 4x LTC5553 150 mA). ADI suggests LT8609S (ADAR1000 DS Table 26, 4 devices) | schematic | U601 (power.kicad_sch) |
| U12 | regulator for +5V_PA | +5 V PA drain, >= 5 A (16x 220 mA quiescent + RF drive) | schematic | U602 (power.kicad_sch) |
| U13 | regulator for +1V8_DIG | +1.8 V always-on logic/MCU (ADAR1000 SPI is 1.8 V CMOS, abs max 2.0 V) | schematic | U603 (power.kicad_sch) |
| U14 | regulator for +3V3_LO | +3.3 V ADF4371 AVDD, low noise (DS recommends ADM7150 / LT3045) | schematic | U604 (power.kicad_sch) |
| U15 | regulator for +5V_LO | +5 V ADF4371 VCC_VCO/VCC_LDO + AVA-183A+, low noise (ADM7150 / LT3045 per DS) | schematic | U605 (power.kicad_sch) |
| U16 | regulator for +3V3_AUX | +3.3 V always-on telemetry (INA226 VS) | schematic | U606 (power.kicad_sch) |
| U17 | regulator for -5V_BF | -5 V ADAR1000 AVDD1 (-50 mA max per chip, PA bias fully loaded) -> ~-0.2 A; ADI suggests LT1931/LT3462 (DS p45, Table 26) | schematic | U607 (power.kicad_sch) |
| U18 | regulator for -3V3_SW | -3.3 V ADTR1107 VSS_SW (16x 120 uA); negative LDO from -5 V (e.g. LT3094 class) | schematic | U608 (power.kicad_sch) |
| U19 | negative-rail window monitor | hardware NEG_OK so PA drain cannot be on with -5 V/-3.3 V absent; comparator/supervisor not yet selected | schematic | U609 (power.kicad_sch) |
| U20 | CT (slew) capacitor and QOD resistor | values need TI TPS22810 DS; pins left open | schematic | U621 (power.kicad_sch), U622 (power.kicad_sch), U623 (power.kicad_sch), U624 (power.kicad_sch) |
| U21 | INA226 address straps / shunt values | A1:A0 = GND/VS combinations from memory of TI address table - verify in TI INA226 DS; 10 mOhm shunt is a design choice | datasheet check | U610-U614 (power.kicad_sch) |
| U22 | PCA9306 VREF2/EN 200k bias and pull-ups | standard TI application from memory - verify in TI PCA9306 DS | datasheet check | U615 (power.kicad_sch) |
| U23 | MCU pin / alternate-function map | SPI1 PA5/6/7, I2C1 PA15/PB7, TIM capture on PB3 etc. are provisional - verify with STM32CubeMX / ST DS before sign-off | schematic | U701 (mcu.kicad_sch) |
| U24 | MCU decoupling | VDD/VDDA/VREF+ bypass per ST STM32G431 DS not yet placed | schematic | U701 (mcu.kicad_sch) |
| U25 | TPS3430 CWD/CRST/SET0/SET1 timing | window timing selection needs TI TPS3430 DS; pins left open. VDD range vs 1.8 V to verify | schematic | U702 (mcu.kicad_sch) |
| U26 | TMP117 placement | must sit on the FE heat spreader; one per tile half. Thermal design open (H1 M5) | thermal | U706/U707 (mcu.kicad_sch) |

**schematic** = close before schematic sign-off / layout preparation; **layout** = vendor land pattern needed before placement; **datasheet check** = KiCad-library part whose application values came from memory, check against the TI datasheet; **vendor** = ADI answer needed; **EM** / **thermal** = separate H2 work packages.
