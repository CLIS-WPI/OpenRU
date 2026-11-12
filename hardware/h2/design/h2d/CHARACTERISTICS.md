# OpenRU H2-D — PA safety parts: guaranteed-characteristics database

Research only. Sources are manufacturer datasheets only (TI symlink PDFs, the latest revision checked on 2026-11-12; Diodes Inc.). The PDFs are in `scratchpad/h2c/...`, `scratchpad/ds2/` and `scratchpad/h2d/chars/ds/`, and the text extracts with page markers are in `scratchpad/h2d/chars/txt/*.pg`.

How to read the tables:
- **min/max** is a datasheet limit, over the temperature range the table states.
- **TYP ONLY** means the datasheet gives only a typical (or NOM) value. Do not use it as a bound.
- **NOT SPECIFIED** means the datasheet does not give the parameter.
- **25 °C ONLY** means the limit is guaranteed at TA = 25 °C only.
- "p.N" is the PDF page number, which is the same as the printed page number in TI datasheets.

---

## 1. TPS22810 load switch — SLVSDH0C (Jan 2018, latest)
EC: TA = –40…+105 °C. Switching table: **TA = 25 °C, typical only**.

| Parameter | min | typ | max | Conditions | Source |
|---|---|---|---|---|---|
| tON | TYP ONLY | 520 / 380 / 185 µs | — | VIN = 18 / 12 / 3.3 V, RL = 10 Ω, CL = 0.1 µF, CT = 2.2 nF, 25 °C | p.7 §7.6 |
| tOFF | TYP ONLY | 3.3 µs | — | same | p.7 |
| tD (ON delay) | TYP ONLY | 180 / 150 / 130 µs | — | same | p.7 |
| tR | TYP ONLY | 700 / 460 / 120 µs | — | same | p.7 |
| tF | TYP ONLY | 2 µs | — | same | p.7 |
| EN/UVLO falling deglitch | TYP ONLY | 2.5 µs | — | text only | p.15 §9.3.3 |
| VENR (EN rising) | 1.13 V | 1.23 | 1.30 V | –40…105 °C | p.5 |
| VENF (EN falling) | 1.08 V | 1.13 | 1.18 V | –40…105 °C | p.5 |
| VSHUTF (low-IQ shutdown) | 0.5 V | 0.75 | 0.9 V | –40…105 °C | p.5 |
| IEN/UVLO leakage | — | — | 0.1 µA | VIN = 18 V | p.5 |
| VUVR (VIN UVLO rising) | 2.0 V | 2.54 | 2.62 V | –40…105 °C | p.5 |
| VIN UVLO hysteresis | TYP ONLY | 5 % (125 mV) | — | | p.5, p.15 |
| RPD (QOD internal) | NOT SPECIFIED | 290 | **350 Ω** | VIN = VOUT = 18 V, VEN = 0 V | p.6 |
| RPD | NOT SPECIFIED | 265 | **350 Ω** | 12 V, VEN = 0 V | p.6 |
| RPD | NOT SPECIFIED | 250 | **400 Ω** | 5 V, VEN = 0 V | p.6 |
| RPD at VIN < 5 V | NOT SPECIFIED | | | | — |
| QOD fall-time table | TYP ONLY | e.g. 500 µs at CL = 1 µF, 5 V | — | "TYPICAL VALUES" | p.14 Table 1 |
| Max CL with internal RPD only | — | — | 200 µF | otherwise add REXT (TJ limit) | p.14 §9.3.2.2 |
| TSD | TYP ONLY | 160 °C, hysteresis 30 °C | — | | p.6 |

When QOD is active and when it is not (datasheet statements):
- **Active:** when the switch is disabled by EN/UVLO < VENF. The limit is characterised with VEN = 0 V, which is also below VSHUTF, so the discharge is guaranteed in low-IQ shutdown (p.6). The QOD pin must be tied to VOUT; if QOD floats there is no discharge (p.13–14).
- **Inactive in thermal shutdown:** "during thermal shutdown, the QOD functionality is not available. The device does not discharge the load as RPD does not become engaged" (p.14).
- **Inactive below UVLO:** "Past the set UVLO level, the pull-down resistance RPD becomes disabled and the output no longer becomes discharged" (p.14 §9.3.2.1). So with VIN < VUVF (about 2.4 V typ) the output floats.
- The function table lists only EN L = Disabled and EN H = Enabled (p.17).

## 2. TPS22917 load switch — SLVSDW8B (Dec 2021, latest)
EC: TJ –40…125 °C (RPD and QOD only –40…105 °C). Switching table: 25 °C, **typical only**.

| Parameter | min | typ | max | Conditions | Source |
|---|---|---|---|---|---|
| VIH (ON) | 1.0 V | | 5.5 V | ROC, VIN 1–5.5 V | p.5 §7.3 |
| VIL (ON) | 0 | | 0.35 V | ROC | p.5 |
| ION leakage | –10 nA | | 10 nA | enabled, –40…125 °C | p.6 |
| Smart ON pulldown RPD | TYP ONLY | 750 kΩ | — | VON ≤ VIL; disconnected once ON ≥ VIH | p.6, p.15 |
| tON | TYP ONLY | 100 µs at 5 V … 400 µs at 1 V (CT open) | — | CL = 1 µF, RL = 10 Ω | p.7 |
| tOFF | TYP ONLY | 10 µs | — | | p.7 |
| tFALL | TYP ONLY | 22 µs (1 µF, QOD shorted) | — | | p.7 |
| QOD resistance | TYP ONLY | 150 Ω | — | disabled, –40…105 °C (feature list says "≥ 150 Ω") | p.6, p.1 |
| QOD at low VIN | NOT SPECIFIED | "Past a certain VIN level, the strength of the RPD is reduced" | | | p.16 §9.3.3.1 |
| Thermal shutdown | none in device | | | | — |
| RCB activation time | TYP ONLY | 10 µs | | | p.6 |

## 3. TPS386000 quad supervisor — SBVS105F (Oct 2018, latest)
EC: TJ –40…125 °C, 1.8 V < VDD < 6.5 V.

| Parameter | min | typ | max | Conditions | Source |
|---|---|---|---|---|---|
| VDD operating | 1.8 V | | 6.5 V | | p.7 |
| Power-up reset voltage (minimum VDD for a valid RESET low) | — | — | **0.9 V** | VOL ≤ 0.2 V, IRESET = 15 µA, VDD rise ≥ 15 µs/V | p.7 note 2,3 |
| VOL RESETn | — | — | 0.3 V | 1.3 V < VDD < 1.8 V, IOL = 0.4 mA | p.7 |
| VOL RESETn / WDO | — | — | 0.4 V | IOL = 1 mA (**the only IOL specified; nothing at ≥ 3 mA**) | p.7 |
| VITN (SENSE1–3, 4L) | 396 mV | 400 | 404 mV | | p.7 |
| VITP (SENSE4H) | 396 mV | 400 | 404 mV | | p.7 |
| Hysteresis VHYSN / VHYSP | NOT SPECIFIED (no min) | 3.5 mV | 10 mV | | p.7 |
| ISENSE | –25 nA | | +25 nA | | p.7 |
| Output leakage (RESETn, WDO) | –300 nA | | 300 nA | 6.5 V, output high | p.7 |
| tW (input pulse width to SENSE) | TYP ONLY | 4 µs | — | 1.05 → 0.95 VIT | p.8 §6.6 |
| **Detection / propagation delay SENSE → RESET asserted** | NOT SPECIFIED | "almost immediately with minimal propagation delay" (text only) | NOT SPECIFIED | | p.23 |
| tD (release delay) | 14 ms | 20 | 24 ms | CTn open | p.8 |
| tD | 225 ms | 300 | 375 ms | CTn = VDD | p.8 |
| tWDT | 450 ms | 600 | 750 ms | | p.8 |
| VTH(CTn) / ICT | 1.18 / 235 nA | 1.238 / 300 | 1.299 V / 365 nA | | p.7 |

## 4. LM339B quad comparator — SLCS006Z (May 2025, latest)
EC rows without a temperature are 25 °C only; some rows add TA = –40…85 °C.

| Parameter | min | typ | max | Conditions | Source |
|---|---|---|---|---|---|
| Supply VS | 2 V | | 36 V | ROC | p.6 §6.4 |
| Input voltage range VIVR | (V–) – 0.1 V | | (V+) – 2.0 V | ROC | p.6 |
| VCM range | V– | | (V+) – 1.5 V (25 °C); (V+) – 2.0 V (–40…85) | VS = 3–36 V | p.7 |
| VIO | –3.5 mV (25 °C); –5.5 mV (–40…85) | ±0.37 | 3.5 mV; 5.5 mV | VS = 5–36 V | p.7 |
| VOL | — | 110 mV | **400 mV (25 °C)** | ISINK ≤ 4 mA, VID = –1 V | p.7 |
| VOL | — | — | **550 mV (–40…85 °C)** | ISINK ≤ 4 mA | p.7 |
| IOL | 6 mA (25 °C only) | 21 | — | VOL = 1.5 V, VS = 5 V | p.7 |
| IOH leakage | — | 0.1 | 50 nA (5 V); 100 nA (36 V) | | p.7 |
| **Response time, 5 mV overdrive** | TYP ONLY | 1000 ns | — | 100 mV step, RL = 5.1 k, CL = 15 pF, 25 °C | p.8 §6.13 |
| Response time, TTL input | TYP ONLY | 300 ns | — | | p.8 |
| Output state for VS < 2 V | NOT SPECIFIED | | | | — |

## 5. SN74LVC1G08 / 1G11 / 1G17 / 1G74
Revisions (all latest): 1G08 SCES217AA (Aug 2026), 1G11 SCES487I (Nov 2024), 1G17 SCES351Y (Oct 2025), 1G74 SCES794G (Sep 2021).

Values common to all four (ROC: 1G08 p.5, 1G11 p.4, 1G17 p.5, 1G74 p.6; EC: 1G08 p.6, 1G11 p.5, 1G17 p.6, 1G74 p.7):

| Parameter | min | max | Conditions |
|---|---|---|---|
| VCC operating | **1.65 V** | 5.5 V | ROC |
| VCC "data retention only" | 1.5 V | | ROC. No output, VIH/VIL or tpd specification applies here. |
| VIH | 0.65·VCC / 1.7 V / 2.0 V / 0.7·VCC | | VCC 1.65–1.95 / 2.3–2.7 / 3–3.6 / 4.5–5.5 V (not 1G17) |
| VIL | | 0.35·VCC / 0.7 / 0.8 / 0.3·VCC | same bands (not 1G17) |
| VOL | | 0.45 V at 4 mA (1.65 V); 0.3 V at 8 mA (2.3 V); 0.4 V at 16 mA and 0.55 V at 24 mA (3 V); 0.55 V at 32 mA (4.5 V); 0.1 V at 100 µA | over the recommended TA |
| Ioff | | ±10 µA | VCC = 0, VI or VO = 5.5 V |
| II | | ±5 µA | |
| TA | –40 °C | 125 °C (1G11 BGA, 1G74 RSE/DQE: 85 °C) | |

SN74LVC1G17 Schmitt thresholds (–40…125 °C, p.6):

| VCC | VT+ min/max | VT– min/max | ΔVT min/max |
|---|---|---|---|
| 1.65 V | 0.76 / 1.13 | 0.35 / 0.59 | 0.36 / 0.64 |
| 2.3 V | 1.08 / 1.56 | 0.56 / 0.88 | 0.45 / 0.78 |
| 3 V | 1.48 / 1.92 | 0.89 / 1.20 | 0.51 / 0.83 |
| 4.5 V | 2.19 / 2.74 | 1.51 / 1.97 | 0.58 / 0.93 |
| 5.5 V | 2.65 / 3.33 | 1.88 / 2.40 | 0.69 / 1.04 |

tpd max in ns (CL = 30/50 pF unless noted). The min is about 1 ns at 3.3–5 V.

| Part | 1.8 V ±0.15 | 2.5 V ±0.2 | 3.3 V ±0.3 | 5 V ±0.5 | Range / source |
|---|---|---|---|---|---|
| 1G08 | 8 (85 °C) / 10 (125 °C) | 5.5 / 7 | 4.5 / 6 | 4 / 5 | p.6–7 |
| 1G11 | 17.2 / 20 | 6.2 / 7.8 | 4.9 / 6.2 | 3.5 / 4.6 | p.6 |
| 1G17 | 11 / 13 | 6.5 / 8 | 5.5 / 6.5 | 5 / 6 | p.7 |
| 1G74 CLK→Q | 13.4 (85 °C only) | 7.1 (85 °C only) | 5.9 / 7.9 | 4.1 / 6.1 | p.7 |
| 1G74 PRE/CLR→Q | 12.9 (85 °C only) | 7.0 (85 °C only) | 5.9 / 7.9 | 4.1 / 6.1 | p.7 |
| 1G74 tw PRE/CLR low (min) | 6.2 | 2.7 | 2.7 | 2.0 | p.7 Timing |

- Behaviour **below 1.65 V VCC: NOT SPECIFIED**. Only "data retention ≥ 1.5 V" is given. Ioff is specified only at VCC = 0 V; the output disable is described for "supply pin held at 0 V" (1G08 p.10 §7.3.2).
- **1G74 power-up state: NOT SPECIFIED.** The datasheet says only that PRE = CLR = L is a non-stable state (p.10).

## 6. CSD16301Q2 N-FET — SLPS235E (Nov 2024, latest). All EC values are 25 °C ONLY (p.3).

| Parameter | min | typ | max | Conditions | Source |
|---|---|---|---|---|---|
| VGS(th) | 0.9 V | 1.1 | 1.55 V | VDS = VGS, 250 µA, **25 °C** | p.3 |
| VGS(th) over temperature | NOT SPECIFIED. Only typical curve Fig 4-6. | | | | p.6 |
| RDS(on) | — | 27 | 34 mΩ | VGS = 3 V, 4 A, 25 °C | p.3 |
| RDS(on) | — | 23 | 29 mΩ | VGS = 4.5 V | p.3 |
| RDS(on) | — | 19 | 24 mΩ | VGS = 8 V | p.3 |
| RDS(on) over temperature | Typical normalised curve only (Fig 4-8) | | | | p.6 |
| Ciss | — | 260 | 340 pF | VDS = 12.5 V, 1 MHz | p.3 |
| Coss / Crss | — | 165 / 13 | 215 / 17 pF | | p.3 |
| Qg (4.5 V) | — | 2.0 | 2.8 nC | VDS = 10 V, 4 A | p.3 |
| Rg | — | 1.3 | 2.6 Ω | | p.3 |
| td(on) / tr / td(off) / tf | TYP ONLY | 2.7 / 4.4 / 4.1 / 1.7 ns | | | p.3 |
| IDSS / IGSS | — | — | 1 µA / 100 nA | VDS = 20 V / VGS = +10/–8 V | p.3 |
| VGS abs max | –8 V | | +10 V | | p.1 |
| IDM | | | 85 A | ≤ 100 µs, ≤ 1 % duty, RθJC max 8.4 °C/W | p.1 |
| EAS | | | 10 mJ | 14 A, 0.1 mH | p.1 |
| SOA | Figure only (single pulse, TC = 25 °C, max RθJC). Curves for 10 µs–100 ms. | | | | p.6 Fig 4-10 |

## 7. DMG1012T N-FET (Diodes, DS31783 Rev. 8-2, Feb 2022). All EC values are 25 °C ONLY (p.2).

| Parameter | min | typ | max | Conditions |
|---|---|---|---|---|
| VGS(th) | 0.5 V | — | 1.0 V | VDS = VGS, 250 µA, 25 °C (over temperature: NOT SPECIFIED) |
| RDS(on) | — | 0.3 | **0.4 Ω** | VGS = 4.5 V, 600 mA |
| RDS(on) | — | 0.4 | **0.5 Ω** | VGS = 2.5 V, 500 mA |
| RDS(on) | — | 0.5 | **0.7 Ω** | VGS = 1.8 V, 350 mA |
| Ciss / Coss / Crss | TYP ONLY | 60.67 / 9.68 / 5.37 pF | — | VDS = 16 V |
| Qg | TYP ONLY | 736.6 pC | — | 4.5 V |
| td(off) / tf | TYP ONLY | 26.7 / 12.3 ns | — | |
| IGSS | — | — | ±1 µA | ±4.5 V |
| VGSS abs | | | ±6 V | |
| SOA | Figure only (Fig. 11) | | | p.6 |

## 8. BAT54C Schottky (Diodes "BAT54/A/C/S", DS11005 Rev. 35), p.2. Values are 25 °C ONLY.

| Parameter | max | Conditions |
|---|---|---|
| VF | 240 mV | IF = 0.1 mA |
| VF | 320 mV | 1 mA |
| VF | 400 mV | 10 mA |
| VF | 500 mV | 30 mA |
| VF | 800 mV | 100 mA |
| IR | 2 µA | VR = 25 V |
| CT | 10 pF | VR = 1 V |
| VF over temperature | NOT SPECIFIED (typical curves only) | |

(onsemi BAT54LT1 in h2c is the single-diode part, not BAT54C. The Nexperia PDF was blocked by the site.)

## 9. TLV755P LDO — SBVS320D (Sep 2024, latest). EC TJ –40…125 °C.

| Parameter | min | typ | max | Conditions | Source |
|---|---|---|---|---|---|
| VHI (EN high) | 1.0 V | | | | p.6 |
| VLO (EN low) | | | 0.3 V | | p.6 |
| IEN | TYP ONLY | 10 nA | | EN = 5.5 V | p.6 |
| VUVLO rising | 1.21 V | 1.3 | 1.44 V | | p.6 |
| UVLO hysteresis | TYP ONLY | 40 mV | | | p.6 |
| tSTR | TYP ONLY | 550 µs | | | p.6 |
| RPULLDOWN (active discharge) | TYP ONLY | 120 Ω | | VIN = 5.5 V | p.6 |
| ISHDN | — | 0.1 | 1 µA | VEN ≤ 0.4 V | p.5 |
| TSD | TYP ONLY | 165 / 155 °C | | | p.6 |

- Pulldown is connected when EN is low and when VIN < VUVLO (p.12 §6.3.1–6.3.2).
- Thermal shutdown sets the device to "disabled" (p.14 Table 6-1), but the datasheet does not say explicitly that the pulldown is engaged in TSD.
- No resistance is specified at low VIN.

## 10. TPS568230 buck — SLVSEY5C (Aug 2019, latest). EC TJ –40…125 °C, VIN = 12 V.

| Parameter | min | typ | max | Conditions | Source |
|---|---|---|---|---|---|
| PGOOD VOL | — | — | **0.4 V** | IOL = 4 mA | p.5 |
| PGOOD leakage | — | — | 1 µA | 5.5 V | p.5 |
| PG thresholds | TYP ONLY | 85/90 % (UV), 110/115 % (OV) | | | p.5 |
| PG start-up delay | TYP ONLY | 1 ms | | | p.5 |
| RDIS (output discharge) | TYP ONLY | 420 Ω | | **TJ = 25 °C**, VEN = 0 | p.5 |
| VENH / VENL | 1.21 / 0.95 V | 1.31 / 1.11 | 1.40 / 1.19 V | | p.6 |
| VIN UVLO | wake 4.2 typ, 4.4 max; shutdown 3.6 min, 3.8 typ | | | | p.6 |
| OTP | TYP ONLY, "not production tested" | 150 °C, hysteresis 20 | | | p.6 |
| OVP / UVP deglitch | TYP ONLY | 20 µs / 256 µs | | | p.6 |

Behaviour:
- PGOOD is low on UV/OV, TSD, EN shutdown and during soft-start (pin table p.3; §7.3.4 p.14–15).
- The output is discharged on EN low, on UVLO ("shut off and output is discharged", p.15 §7.3.7) and in OTP (p.15 §7.3.9).
- **PGOOD state when VIN is below the internal-logic level or 0 V: NOT SPECIFIED.** It is an open drain, so assume it floats high via the pull-up.

## 11. TPS65131 boost/inverter — SLVS493E (Apr 2022, latest)

| Parameter | min | typ | max | Conditions | Source |
|---|---|---|---|---|---|
| VIH ENP/ENN | 1.4 V | | | –40…125 °C | p.5 |
| VIL | | | 0.4 V | | p.5 |
| VUVLO | 2.1 V | 2.35 | 2.7 V | | p.5 |
| TSD | TYP ONLY | 150 °C, hysteresis 5 | | | p.6 |
| RBSW | TYP ONLY | 27 kΩ | | | p.5 |
| **Output discharge (VPOS, VNEG)** | NOT SPECIFIED. The device has no discharge function. | | | | — |

Behaviour:
- When disabled, the inverter's PMOS is turned off, so VNEG decays only through the load and the feedback divider.
- The boost output keeps a DC path through the inductor and diode, so VPOS ≈ VIN − VF unless an external PMOS driven by BSW is fitted (p.9 §7.3.4).
- UVLO and TSD shut both converters down. "Parts of the control circuits remain active" in UVLO (p.9–10).

## 12. TPS7A3301 negative LDO — SBVS169D (Apr 2015, latest)

| Parameter | min | typ | max | Conditions | Source |
|---|---|---|---|---|---|
| VEN(+HI) | 2 V | | 10 V | | p.6 |
| VEN(+LO) | 0 | | 0.4 V | | p.6 |
| VEN(–HI) | VIN | | –2 V | | p.6 |
| VEN(–LO) | –0.4 V | | 0 | | p.6 |
| VUVLO | TYP ONLY | –2 V | | | p.6 |
| Tsd | TYP ONLY | 170 / 150 °C | | | p.6 |
| **Active output discharge** | NOT SPECIFIED. The device has none. | | | | — |

Disabled when |VEN| < V(HI) or in TSD (p.14). The output state when disabled is not given.

## 13. TPS3430 window watchdog — SBVS366A (Oct 2021, latest). EC 1.6 V ≤ VDD ≤ 6.5 V, –40…125 °C.

| Parameter | min | typ | max | Conditions | Source |
|---|---|---|---|---|---|
| VDD | 1.6 V | | 6.5 V | must be ≥ 1.6 V for ≥ 300 µs at power-on | p.5 |
| VPOR | — | — | 0.8 V | VOL ≤ 0.25 V | p.5 |
| WDO VOL | — | — | **0.4 V** | VDD = 5 V, ISINK = 3 mA (only point) | p.5 |
| WDO leakage | — | — | 1 µA | VDD = 1.6 V, 6.5 V | p.5 |
| tRST | 170 ms | 200 | 230 ms | CRST = NC | p.6 |
| tRST | 8.5 ms | 10 | 11.5 ms | CRST = 10 kΩ to VDD | p.6 |
| tWDL / tWDU (CWD = NC, SET = 00) | 19.1 / 46.8 ms | 22.5 / 55 | 25.9 / 63.3 ms | other settings: p.6 table | p.6 |
| tWD-del (WDI → WDO) | TYP ONLY | 50 ns | | | p.6 |
| Startup delay | TYP ONLY | 300 µs | | | p.6 |

Power-up state (p.15 Table 7-1 and §7.4):
- VDD < VPOR: WDO undefined.
- **VPOR < VDD < 1.6 V: WDO is HIGH (not asserted).**
- During tRST after power-up the watchdog is disabled.

So WDO is **not fail-safe low** during power-up or brown-out.

---

# Candidate alternative parts

## (i) Load switches / eFuses — is tOFF max given? Is the discharge resistance max given?

| Part (rev) | tOFF / turn-off max | Discharge R max | Discharge active when | Notes / source |
|---|---|---|---|---|
| **TPS22918** (SLVSD76C) | TYP ONLY (2–3 µs, 25 °C) p.6 | **30 Ω at 5 V, 35 Ω at 3.3 V, 60 Ω at 1.8 V**, –40…105 °C (typ 24/25/45) p.5 | Switch disabled (VON = 0). "Past a certain VIN level, the strength of RPD will be reduced" p.14. | VIN 1–5.5 V. VIH 1 V / VIL 0.5 V (ROC p.4). **No thermal shutdown**, so TSD cannot disable QOD. Best guaranteed RPD found. |
| **TPS22992** (SLVSFT0A) | TYP ONLY (~15 µs) p.8–9 | **100 Ω**, –40…125 °C (typ 25 Ω) at VBIAS = 5/3.3/1.5 V, p.6–8 | ON < VIL, with VBIAS 1.5–5.5 V present. Mode table: TSD → VOUT Hi-Z (p.16). | Needs VBIAS ≥ VIN. VIH 0.8 V. TSD 170 °C typ. |
| TPS22975 (SLVSDD0B) | TYP ONLY (2–3 µs) p.7 | 300 Ω (VBIAS 5 V), 330 Ω (VBIAS 2.5 V), –40…105 °C p.5–6 | Switch disabled. "Disable before VBIAS falls below min" p.15. | TSD 160 °C typ. |
| TPS22965 (SLVSBJ0F) | TYP ONLY (9–100 µs) p.8 | 300 Ω (5 V), 325 Ω (2.5 V), –40…105 °C p.6–7 | Switch disabled | |
| TPS22810 | TYP ONLY | 350–400 Ω (VIN ≥ 5 V only) | **Not in TSD, not below UVLO** | see §1 |
| TPS2595x5 eFuse (SLVSE57C) | tD,OFF TYP ONLY 11.3 µs p.8 | RQOD TYP ONLY 19 Ω p.8 | QOD pin variant only | UVLO thresholds 1.13/1.27 V rise, 1.03/1.17 V fall (guaranteed) p.8 |
| TPS25947 eFuse (SLVSFC9C) | tD,OFF TYP ONLY 25 µs p.12. tFT/tSC TYP ONLY 500 ns p.11. | NOT SPECIFIED (no output discharge) | — | EN/UVLO 1.183/1.223 V rise, 1.076/1.116 V fall (guaranteed) p.9 |
| **TPS1663** eFuse (SLVSET9G, 60 V) | **tSD(dly) SHDN↓ → FET OFF: 0.8 / 1 / 1.5 µs (min/typ/max)**. **UVLO_toff: 9 / 11 / 16 µs** (UVLO↓ → FLT↓). OVP_toff 8.5–14 µs. –40…125 °C. p.9–10 | NOT SPECIFIED (no output discharge) | — | Only candidate with a **guaranteed max turn-off time**. UVLO 1.176/1.224 V rise, 1.09/1.15 V fall. SHDN falling threshold 0.8 V min. tFASTTRIP soft-short 2.2–4.5 µs. |

**Conclusion (i):** no candidate guarantees both tOFF max and a discharge-R max.
- TPS1663 guarantees FET-off time but has no discharge.
- TPS22918 and TPS22992 guarantee discharge-R max but give tOFF as typical only.
- A guaranteed architecture would combine the two: an eFuse or switch with guaranteed off time, plus a separately guaranteed discharge path, for example a discrete FET plus resistor whose gate is driven from a guaranteed-VOL supervisor.

## (ii) Supervisors / window comparators

| Part (rev) | Propagation delay max | VOL at IOL | VPOR (minimum VDD for a controlled output) | VDD | Source |
|---|---|---|---|---|---|
| **TPS3703** (SBVS249B) | **tPD 15 typ / 30 µs max** (5 % overdrive, to VOL), –40…125 °C | **≤ 250 mV at 3 mA** (VDD = 2 V) | ≤ 1.0 V (VOL ≤ 0.25 V, 15 µA) | 1.7–5.5 V | p.6–7. Thresholds ±0.7 %, hysteresis 0.3–0.8 %. ILKG ≤ 300 nA. tD variants guaranteed (e.g. 7–13 ms). |
| **TPS3762** (SNVSCM8A) | **tCTS 85 typ / 100 µs max** (20 % overdrive, CTS open). Release tCTR 350/600 µs max. | ≤ 350 mV at **2.7 mA** (not ≥ 3 mA) | ≤ 1.4 V | 2.7–65 V | p.6, p.8. VITP/VITN ±0.9 %. BIST built in. |
| TPS3700 (SBVS187G) | TYP ONLY (18 / 29 µs) p.7 | ≤ 250 mV at 3 mA (1.8 V), at 5 mA (5 V), at 0.4 mA (1.3 V) | ≤ 0.8 V | 1.8–18 V | p.6 |
| TLV6700 (SNVSAV2B) | TYP ONLY (18 / 29 µs) p.6 | ≤ 250 mV at 3 mA (1.8 V) | ≤ 0.8 V | 1.8–18 V | p.5. VIT+ 396–404 mV. |
| TPS3702 (SBVS251A) | TYP ONLY (19 / 35 µs) p.6 | ≤ 250 mV at 3 mA (2 V) | ≤ 0.8 V | 2–18 V | p.5 |
| TPS3808 (SBVS050N) | TYP ONLY (20 µs) p.7 | ≤ 0.4 V at 1 mA only | ≤ 0.8 V | 1.7–6.5 V | p.6 |
| TPS3890 (SLVSD65A) | TYP ONLY (tPD(f) 8 µs) p.5 | ≤ 0.25 V at 2 mA (VDD ≥ 2.7 V) | ≤ 0.8 V | 1.5–5.5 V | p.5 |

Below VPOR, every one of these parts has an **undefined** output.

## (iii) Break-before-make

| Part | tBBM min | Conditions | Source |
|---|---|---|---|
| TS5A3159 (SCDS174D) SPDT | **1 ns** (typ 12–21 ns). tON max 40 ns, tOFF max 35 ns at 5 V. | –40…85 °C, V+ 4.5–5.5 V and 3–3.6 V, RL 50 Ω, CL 35 pF | p.5–6 |
| TMUX1219 (SCDS409A) SPDT | **1 ns**. tTRAN max 18 ns (5 V), 20 ns (3.3 V), 44 ns (1.8 V), 190 ns (1.2 V). | –40…125 °C, VDD 1.08–5.5 V | p.6, 8, 10, 12 |

- Both guarantee only a 1 ns gap, so any meaningful dead time must come from an external RC.
- No gate driver with a guaranteed dead-time min/max was retrieved in this pass. **Not researched further.**

## (iv) Low-voltage logic

| Part (rev) | Minimum VCC (ROC) | Ioff | Specified at minimum VCC | tpd max first given at |
|---|---|---|---|---|
| SN74AUP1G08 (SCES502Q) | **0.8 V** | **≤ 0.2 µA (25 °C), ≤ 0.6 µA (–40…85 °C)**, VCC = 0, VI/VO 0–3.6 V | At 0.8 V: VIH = VCC, VIL = 0, IOL/IOH = 20 µA, VOL ≤ 0.1 V at 20 µA. **tpd 18 ns TYP ONLY.** | 1.2 V ±0.1: 15.6 ns (CL 5 pF, –40…85 °C). p.5–8 |
| SN74AUP1G74 (SCES644D) | 0.8 V | ≤ 0.6 µA (–40…85 °C) | Same 0.8 V restrictions; tpd TYP ONLY at 0.8 V | ≥ 1.2 V. p.4–8 |
| SN74AUC1G08 (SCES374P) | 0.8 V (max 2.7 V) | ±10 µA (VI/VO = 2.7 V) | VOL ≤ 0.25 V at 0.7 mA (0.8 V). **tpd 4.7 ns TYP ONLY.** | 1.2 V: 0.9–3.3 ns. –40…85 °C. p.4–5 |
| SN74LVC1G (any) | 1.65 V (data retention 1.5 V) | ±10 µA | — | 1.8 V |
| SN74LV1T08 (SCLS739F) | 1.6 V | — | — | — |
| SN74AXP1G | ti.com symlink returned HTML. **Not retrieved.** | | | |

- AUP and AUC parts are rated to TA –40…85 °C only.
- None of these parts gives a tpd max at 0.8 V. Below 0.8 V nothing is specified.

---

# Parameters the safety argument needs but no datasheet guarantees

1. **TPS22810 turn-off timing:** tOFF, tF and tD are 25 °C typical only, with no min/max over temperature. The EN falling deglitch (2.5 µs) is also typical only.
2. **TPS22810 QOD below UVLO and in TSD:** the datasheet says RPD is **disabled** in both cases. There is no discharge guarantee when VIN collapses (VIN < about 2.4 V) or when the die overheats. RPD max is given only for VIN ≥ 5 V, and RPD has no minimum, which matters for the TJ and the 200 µF limit.
3. **TPS22917:** QOD (150 Ω) and tOFF are typical only. QOD weakens at low VIN (no value given). There is no TSD.
4. **TPS386000 SENSE → RESET assertion delay:** not specified at all; only "minimal" in text, and tW = 4 µs is typical only. VOL is specified only at 1 mA, nothing at ≥ 3 mA. Hysteresis has no minimum.
5. **LM339B:** response time is typical only (1 µs at 5 mV overdrive). VOL is guaranteed only at ≤ 4 mA (0.55 V over temperature). There is no output-state guarantee below VS = 2 V.
6. **SN74LVC1G family:** no behaviour is specified for 0 < VCC < 1.65 V; Ioff applies only at VCC = 0. The 1G74 has **no defined power-up state**.
7. **MOSFETs (CSD16301Q2, DMG1012T):** VGS(th) and RDS(on) limits are at 25 °C only, with typical curves over temperature. DMG1012T Ciss and Qg are typical only. SOA is a typical figure only.
8. **BAT54C:** VF max is at 25 °C only.
9. **TLV755P:** active discharge 120 Ω and tSTR are typical only. The pulldown in TSD is implied, not stated.
10. **TPS568230:** discharge RDIS is typical at 25 °C only. OTP is "not production tested". The PGOOD state when VIN is below the internal-logic level is not specified.
11. **TPS65131 and TPS7A3301:** no output discharge exists. The output state when disabled is not specified. The TPS65131 boost output stays at ≈ VIN − VF unless an external BSW PMOS is used.
12. **TPS3430:** WDO is **high (unasserted)** for VPOR < VDD < 1.6 V and undefined below 0.8 V. tWD-del is typical only.
13. **Every supervisor's output below VPOR (0.8–1.4 V):** undefined. A fail-safe pull-down needs an independent passive path.
14. **No single load switch or eFuse guarantees both a max turn-off time and a max discharge resistance.** TPS1663 has the time (0.8–1.5 µs SHDN → FET off) but no discharge. TPS22918 and TPS22992 have the resistance (≤ 30–60 Ω, ≤ 100 Ω) but typical-only timing.
15. **Fall time of any rail:** only bounded by τ = Rmax·C, using RPD max where it exists. Every tabulated fall time is typical.
