# H2-E Candidate-A safety-test fixture (one chain) — `candA_fixture`

- **Date:** 2026-11-12. **Status:** schematic + part list only. No PCB layout.
- **H2-E.1 changes:** A-SENSE fix (U4, R10, R11, D1 removed), R57/R58 re-valued, MPN fields synced to `FIXTURE_BOM.csv`. See
  `../design/h2e1/H2E1_PROCUREMENT_AUDIT.md`.
- **Scope:** one Candidate-A chain (permit P, monitors, TPS16630 eFuse, SHDN-timed crowbar) on a separate KiCad 9 project.
  The OpenRU tile project (`hardware/h2/schematics/`) was not opened or changed.
- **No ADTR1107 / ADAR1000 on the board.** The PA is replaced by dummy loads plus the tile's drain decoupling; gate and
  negative-rail signals come from bench supplies through the tile's divider networks.
- **Sources:** `design/h2d/ARCH_COMPARE.md` §2–§3 (incl. H2-E correction: overlap peak current is NOT guaranteed),
  `design/h2d/sim/arch_a_sim.py` (as-simulated values: 2.2 k pull-up, 47 k / 47 k / 1 nF, R_t 4.32 k, C_t 1 nF, 6 × 1 Ω),
  `design/h2c/INTERLOCK_SPEC.md` §3 (tile gate / rail divider values), `design/h2d/BENCH_PLAN.md` (T1a…T13).
- **Files:** `candA_fixture.kicad_pro/.kicad_sch`, project library `candA_fixture.kicad_sym` + `sym-lib-table`,
  `expected_fixture.json`, `FIXTURE_PARTS.csv`, `out/candA_fixture-erc.json`, `out/candA_fixture.xml`, `out/candA_fixture.pdf`.
- **Sheet:** one A2 sheet. All nets are local labels prefixed `IL_` (interlock/logic) or `PWR_` (power), so
  `tools/verify_expected.py out/candA_fixture.xml expected_fixture.json` can check them: **728 checks, 0 failures**.

## 1. Circuit description

### 1.1 Supplies and ground

| Item | Implementation | Notes |
|---|---|---|
| VIN_12V (`PWR_VIN`) | J1 Phoenix MKDS 1,5/2 terminal → U1 TPS7A2550DRVR (5.0 V fixed, ±1 %, SBVS372C p6) → `IL_5V` (= +5V_IL) | C1 1 µF/25 V in, C2 4.7 µF out. EN tied to IN. PG open (see §4) |
| IL_REF (1.8 V) | U2 TPS7A2518DRVR from `IL_5V` | Replaces the tile's +1V8_DIG/IL_REF for the gate and negative-rail dividers. ±1 % instead of the tile's assumed ±3 % |
| VCB (`IL_VCB`) | R1 100 Ω + C5 10 µF from `IL_5V` | Crowbar-timing domain, as ARCH §3.2 / sim |
| +5V_PA (`PWR_5V_PA`) | J2 Phoenix MKDS 3/2 terminal from an **external lab supply** (ramp / brown-out / OV injection) | C6–C9 4 × 47 µF footprints, **DNP** (fit to emulate the tile bulk, 188 µF) |
| eFuse input | RS1 10 mΩ Kelvin shunt (A's "+5V_PA ─10 mΩ─ IN") → `PWR_EFIN`; C10 100 nF/50 V | Sense on J9 |
| GND (`PWR_GND`) | Single net; star point is a layout item. TP23/TP24 black loops = GND sense points | Every probe pad TP1–TP9 has its own GND pad for the probe spring |

### 1.2 Permit node P (`IL_P`) and monitors

P is pulled up by R2 **2.2 kΩ** to +5V_IL with C11 100 pF (as simulated). Open-drain sinks on P:

| Source | Part / function | Values and thresholds | Source of values |
|---|---|---|---|
| +5V_IL UV/OV | U3 TPS3703A7330DSER, SENSE via R7 5.49 k / R8 10.7 k (0.1 %) | k = 0.6609 → UV 4.64 V, OV 5.34 V (VIT ±7 %, accuracy ±0.7 %). CT = 10 k to VDD → tD 140–260 ms (SBVS249B p7) | A §2.3/§2.4 (A variant, CT 10 k) |
| +5V_PA UV/OV | U4 **TPS3703A7120DSERQ1** (1.2 V, ±7 %), SENSE via R10 3.16 k / R11 1.00 k (0.1 %) from `PWR_5V_PA` (H2-E.1) | k = 0.2404 → UV 4.643 V, OV 5.341 V nominal (worst 4.592–4.698 / 5.283–5.406 V). SENSE ≤ 5.5 V ROC up to +5V_PA = 22.9 V. CT open = 7–13 ms, R12 10 k DNP for 200 ms | A §2.5 F-5V; SBVS344D |
| SENSE clamp | **Removed in H2-E.1** (D1 BAS116 to +5V_IL clamped only to ≈ 5.9 V, above the 5.5 V ROC, and back-powered +5V_IL). Not needed with the 1.2 V device | §5 F2 |
| Gate lost ×4 | U6, U7 TLV3202AIDGKR on +5V_IL; per gate: `IL_VGGk` (J4) → C 10 nF → Rg 49.9 k → node `IL_Gk`; Rt 17.4 k to IL_REF; Rn 45.3 k to GND; compared with IL_REF_LOST (R31 2.15 k / R32 2.74 k) | Trip at gate −0.150 V nominal (node = 0.577·V_REF + 0.201·V_gate). Comparator high → Q4–Q7 2N7002 pull P low. A floating gate input reads 0 V = "lost" (fail-safe) | Tile divider, INTERLOCK_SPEC §3.2/§3.4; A §2.2 (TLV3202 instead of LM339B) |
| Negative rail window | U8 TLV3202; `IL_VNEG` (J4 pin 9) → R33 49.9 k → `IL_N5V`, R34 12.4 k to IL_REF | UV (less negative than −4.60 V; ref R35 3.92 k / R36 1.62 k) and OV (more negative than −5.40 V; ref R37 10.7 k / R38 2.74 k). Outputs → Q8, Q9. Floating input = fault | UV: tile IL_REF_N5V. OV level −5.40 V is a **fixture choice** (A asks for a two-sided window but gives no OV value) |
| Fast +5V_PA OV | U9 TLV3201AIDBVR on +5V_IL; R39 10.7 k / R40 5.49 k vs IL_REF | Trip 5.31 V nominal (A: 5.30 V) → Q10 | A §2.5 |
| Watchdog | U5 TPS3430WDRCR, VDD = `IL_WDVDD` (R13 0 Ω from +5V_IL), WDO → R14 0 Ω → P | SET0 pulled **up** (R16 100 k) → watchdog disabled by default; jumper J3-9 to J3-10 (GND) enables it (SET0 = SET1 = 0: window 19.1–22.5 / 46.8–55 ms). CWD, CRST open (factory presets, datasheet allows NC). WDI from J3-7 (100 k pull-down) | A §2.3 |
| eFuse FLT | U10 FLT → R49 0 Ω → P | Remove R49 to observe FLT on its own (TP9) | A §2.2 |
| ARM / MCU_PA_EN | J3-1 → Q1 (100 k pull-down) → `IL_ARMG` (10 k pull-up) → Q2 on P | MCU/bench must **drive** MCU_PA_EN high to release P; open/low input = P held low | A §2.1 rule 3/4 |
| FAULT_INJ | J6 SMA → Q3 gate (100 k pull-down, 49.9 Ω termination R6 DNP) | Pulse generator pulls P low through an OD | BENCH_PLAN T6 |

Readbacks (each through 47 kΩ, A §2.4) to J5: P (R71), FLT (R72), crowbar gate (R73), PGOOD (R74, 10 k pull-up R48),
IMON (R75; IMON load R47 20 k → 0.558 V/A with 27.9 µA/A, SLVSET9G p9).

### 1.3 eFuse U10 TPS16630RGER (VQFN-24 RGE0024H)

| Pin | Connection | Value / result | Source |
|---|---|---|---|
| IN, P_IN | `PWR_EFIN` | "Always connect P_IN to IN directly" (SLVSET9G p5) | DS |
| UVLO | R41 27.4 k / R42 10.7 k (0.1 %) from +5V_IL | k = 0.2808: FET can be on only above 3.88 V; guaranteed enable at 4.36 V | A §2.4 (k ≈ 0.28) |
| OVP | R43 47.5 k / R44 13.7 k (0.1 %) from `PWR_EFIN` | k = 0.2239 → trip 5.25–5.47 V (5.36 V nominal); at 12 V OVP pin = 2.7 V < 5.5 V abs max | A §3.1 (5.35 V) |
| ILIM | R45 9.09 k 1 % | I(OL) ≈ 1.84–2.16 A (spec point 9 kΩ, SLVSET9G p8) | A §2.3 |
| dVdT | C23 22 nF | ≈ 2.3 V/ms, ≈ 54 mA inrush into 23.8 µF; turn-on ≈ 1.8 ms | Fixture choice (A gives no value) |
| MODE | open = **latch**; R46 0 Ω DNP to GND = auto-retry option | SLVSET9G p9 | A §2.3 |
| SHDN | `IL_SHDN` (SHDN_c) | — | — |
| OUT | → RS2 10 mΩ Kelvin shunt → `PWR_VOUT` (drain) | J10 sense | Fixture addition |
| N.C. 3, 4, 15, 19–24 | not connected (symbol pin type "unconnected"; datasheet "No connect") | — | SLVSET9G p6 |

### 1.4 SHDN-timed crowbar (A §3.1–§3.2, values as simulated)

- SHDN_c: R52 47 k from P, R53 47 k to GND, C25 1 nF C0G; Q11 (Q_sd) pulls SHDN_c low when CD fires.
- CD: U11 TLV3201 on VCB, P vs 0.8·VCB (R50 2.55 k / R51 10.2 k, 0.1 %).
- CA: U12A TLV3202 on VCB, SHDN_c vs 0.1·VCB (R57 18.0 k / R58 2.00 k, H2-E.1; was 9.09 k / 1.01 k, E192 not stocked; same k) → Q12 (Q_t) resets C_t.
- Timer: R59 **4.32 k 1 %** from VCB → `IL_CT` → R61 0 Ω → C27 **1 nF C0G 5 %**.
- CB: U12B, V(C_t) vs 0.5·VCB (R55/R56 10.0 k) → U13 SN74LVC1G17 (VCC = VCB) → R62 0 Ω → `IL_CB_G` (R64 100 k pull-down).
- Crowbar: Q13 CSD16301Q2; drain ← 6 × RCS1206 1 Ω (R65–R70, 0.167 Ω) ← `PWR_VOUT`; source → RS3 10 mΩ Kelvin shunt → GND (J11).

### 1.5 PA dummy-load bank (on `PWR_VOUT`)

- Decoupling exactly as the tile chain (IMPL_PERIPH A5): C29–C32 4 × 4.7 µF 10 V X5R, C33 1 µF 10 V X7R, C34 10 nF, C35 100 pF (0402).
- Four "biased PA" loads: each 2 × 44.2 Ω 1 W 2512 in parallel (22.1 Ω → 0.226 A at 5 V, 0.57 W per resistor at 5 V,
  0.68 W at 5.5 V) switched by CSD16301Q2 Q14–Q17; gates PWR_LEN1…4 from J3-3…6 (100 k pull-downs).
- "Gate lost" branch: 6 × 49.9 Ω 1 W 2512 in parallel (8.32 Ω → 0.60 A at 5 V, 3.0 W total, 6 W rating) switched by Q18;
  gate `PWR_GLEN` from SMA J8 (pulse generator) with 100 k pull-down.
- All loads on at 5.5 V: 1.66 A < I(OL) min 1.84 A, so the full bank does not trip the current limit.

### 1.6 Measurement access

| Node | Access |
|---|---|
| VIN, +5V_PA, eFuse OUT, drain (VOUT), P, SHDN_c, crowbar gate, C_t node, FLT | TP1–TP9: signal pad + GND pad, 5.08 mm, for a probe ground spring |
| +5V_IL, VCB, IL_REF, UVLO, OVP, CD out, CA out, CB out, SENSE1/2, MR1/2, WD VDD | TP10–TP22 Keystone 5000 loops |
| Currents | RS1 (eFuse input, for the T1/T6 overlap metric), RS2 (eFuse output), RS3 (crowbar); 10 mΩ WSK2512 Kelvin, sense on J9/J10/J11 |
| Temperature | TP25 (place at Q13 crowbar FET), TP26 (place at U10) — 3 × 3 mm copper pads on GND for a thermocouple |
| GND | TP23/TP24 black loops at the star point |

## 2. Fault-injection and test options

| Ref | Default | Option | Purpose |
|---|---|---|---|
| R61 | 0 Ω fitted | remove → **C_t open** | BBM-loss single fault (A §3.4) |
| R60 | DNP | fit 0 Ω → **R_t short** | BBM-loss single fault |
| R54 + J7 | DNP | fit 0 Ω → **SHDN override** from SMA J7 (pulse generator drives SHDN_c directly; T1a "directly" case) | T1a, T13 |
| R63 | DNP | fit 0 Ω (after removing R62) → **crowbar gate stuck on** (gate = VCB) | TE3 cut set, gate-readback check |
| R62 | 0 Ω fitted | remove → isolate LVC output from gate | with R63 |
| R46 | DNP | fit → MODE auto-retry | compare latch vs retry |
| R49 | 0 Ω fitted | remove → FLT isolated from P | FLT timing (M1) |
| R14 / R15 | 0 Ω / DNP | remove R14, fit R15 2.2 k → WDO isolated with its own pull-up (T10 setup) | T10 |
| R13 + TP22 | 0 Ω fitted | remove → drive TPS3430 VDD from a bench supply at TP22 | T10 brown-out ramps |
| R7/R10 + TP18/TP19 | fitted | lift R7/R10 → drive SENSE from the fast-slew supply | T3 |
| R9 / R12 | fitted / DNP | CT preset selection 200 ms / 10 ms | T3, T11 |
| R6 | DNP | 49.9 Ω termination on FAULT_INJ | 50 Ω pulse source |
| C6–C9 | DNP | tile-like +5V_PA bulk (188 µF) | T12 |
| J4 pins 1/3/5/7, 9 | — | gate emulation VGG_EMU1…4, negative-rail emulation | T8, gate-lost proof test |
| J3 pins 3–6, J8 | — | PA_LOAD_EN1…4, gate-lost 0.6 A step | T1a load cases, T6 |

## 3. Bench test → fixture feature map

| Test | Uses |
|---|---|
| T1a SHDN→FET off | J6 FAULT_INJ (through 47 k/47 k/1 nF) or J7 + R54 (direct); RS1 current (J9); TP6 SHDN_c; loads via J3/J8; VIN 4.5/5.0/5.5 V on J2 |
| T1b eFuse below ROC | J2 ramps 5→0 V; SHDN low via FAULT_INJ or high via J7/R54; crowbar forced on with R63 (+R62 removed); RS1 current |
| T3 supervisor delay | U3/U4 SENSE via TP18/TP19 with R7/R10 lifted; RESET on TP5 (P) with 2.2 k pull-up as designed |
| T4 VOL at real sink current | P pull-up 2.2 k to +5V_IL; R14/R49 remove to isolate WDO/FLT; TP5 |
| T5 MOSFET VGS(th)/RDS(on) | Q13 (crowbar), Q11/Q12, Q1–Q10 in circuit with TP25 thermocouple; SMU on the pads |
| T6 crowbar pulse / overlap | FAULT_INJ; RS1 (eFuse in) + RS3 (crowbar) Kelvin currents; TP4 VOUT; TP25 thermocouple; loads off (pinched) |
| T7 timer / BBM at temperature | TP6 SHDN_c, TP8 C_t, TP17 CB out, TP7 gate; VCB adjustable by changing +5V_IL load or via TP11 |
| T8 rail-collapse matrix (one chain) | J1 (VIN), J2 (+5V_PA), TP10 +5V_IL injection, J4 VGG/VNEG; P, SHDN_c, gate, VOUT probe pads |
| T10 TPS3430 brown-out | R13 removed, TP22 driven; R14 removed, R15 fitted; WDI on J3-7; SET0 jumper |
| T11 rail guard | +5V_IL swept (U1 bypassed by driving TP10 with VIN off), TP13 UVLO, RS1 current; monitors disconnected by lifting R14/R49 and the OD FETs' drains (manual) |
| T12 +5V_PA OV | J2 from the current-limited 12 V source, C6–C9 fitted; U4 SENSE stays ≤ 3.2 V at 13.2 V (H2-E.1); TP2/TP4, TP14 OVP; P must stay low |
| T13 parasitics | C_t, SHDN pin hysteresis via J7/R54 slow triangle; crowbar loop di/dt via RS3 |

## 4. ERC result

Final: **0 violations** (`out/candA_fixture-erc.json`), `validate_hierarchy`: 0 issues. No ERC severities were changed.

The first run had 3 errors, all fixed in the design rather than suppressed:

| # | Finding | Cause | Fix |
|---|---|---|---|
| 1, 2 | "Open collector and Power output connected" — U1 PG / U2 PG vs PWR_FLAG on GND | TPS7A25 PG was tied to GND (datasheet's thermal suggestion) and GND carries the PWR_FLAG | PG left open with a no-connect flag. Datasheet: "If not used this pin can be floated" (SBVS372C Table 5-1). Thermal effect is irrelevant at < 20 mA |
| 3 | "Power output and Power output connected" — U10 pins 17/18 | Two power-output pins of the same OUT net in the project symbol | New symbol `TPS16630_RGE` with pin 18 power_out and pin 17 passive (same net inside the IC); U10 re-placed at the same position. The first symbol `TPS16630RGER` is left unused in the library |

No-connect flags (all datasheet-permitted): U5 pin 2 CWD and pin 4 CRST ("leaving unconnected (NC)… selection of the preset",
SBVS366A p3 Table 5-1), U5 pin 9 ("This pin is no-connect and must be left floating"), U1/U2 pin 3 PG (quote above).
U13 pin 1 (SN74LVC1G17 "NC – Not connected") and U10 N.C. pins are "unconnected"-type symbol pins. H2-E.1 re-run: ERC 0,
`validate_hierarchy` 0 issues, netlist 725/725 (`tools/verify_expected.py`), MPN sync 0 mismatches (`tools/check_bom_sync.py`).

## 5. Findings and limitations

1. **F1 – Candidate-A H2-E correction kept:** the fixture measures, but does not bound, the overlap peak current (C_t open / R_t short
   / gate stuck-on). Use the 1-per-minute pulse rule (BENCH_PLAN §0) for these options.
2. **F2 – TPS3703 SENSE over-voltage — resolved in the fixture (H2-E.1):** U4 is a 1.2 V ±7 % TPS3703A7120-Q1 behind
   3.16 k / 1.00 k, so SENSE ≤ 5.5 V ROC for +5V_PA up to 22.9 V without a clamp; D1 removed. The tile still needs the same change (A-SENSE).
   Related, not resolved: a TPS7A25 pass-element short puts VIN on +5V_IL and every permit-logic VDD (A-IL12).
3. **F3 – Shunts in the discharge path:** RS3 (10 mΩ) adds ≈ 4 % to the crowbar τ (≈ 12.9 → 13.5 µs worst case) and lifts the
   FET source by ≈ 0.24 V at 24 A; RS2 is upstream of the crowbar node and does not affect discharge. Bypass by shorting the
   force pads if the exact tile τ is needed.
4. **F4 – IL_REF is not monitored on the fixture** (the tile's F-REF TPS3703 window is not reproduced); IL_REF is a dedicated
   TPS7A2518 and TP12 lets the bench check it. Gate-lost and negative-rail thresholds scale with it.
5. **F5 – Negative-rail OV threshold (−5.40 V) and dVdT (22 nF) are fixture choices**, not values from ARCH_COMPARE.
6. **F6 – TPS3703 window:** ±7 % is needed (commercial A7330 for +5V_IL; -Q1 A7120 for +5V_PA since H2-E.1); UV/OV land at
   ≈ 4.64 / 5.34 V instead of 4.60 / 5.35 V. +5V_PA UV assertion at 5 % overdrive is ≈ 4.36 V (worst), still below the eFuse
   4.5 V ROC (A §3.8 item 1) — covered by the new bench gate E3c.
7. **F7 – Load resistor thermal:** 2512 1 W thick film is ≈ 0.82 W at 85 °C (linear derating 70→155 °C); worst use is 0.68 W (22 Ω
   loads at 5.5 V) — acceptable but hot in the +85 °C chamber; the gate-lost bank is intended for pulsed use.
8. **F8 – DNP marking:** the MCP tool sets a `DNP` property field and the Value text carries "DNP"; KiCad's own DNP attribute is
   not set (no tool for it). Set it in KiCad before BOM export.

## 6. Parts not fully verified

All IC footprints exist in `/usr/share/kicad/footprints` and match the orderable package (pad maps checked with
`get_footprint_info`: RGE0024H 25 pads, DRC0010J 11 pads, DRV WSON-6 + EP 7, DSE WSON-6 no EP, DQK 8 pads, WSK2512 4 pads).
Project symbols were drawn from the datasheet pin tables and checked with `get_symbol_info`:

| Symbol | Datasheet page |
|---|---|
| TPS16630_RGE | SLVSET9G p5–6, Table 5-1 (RGE column) |
| TPS3703A7330DSER (also used for U4 TPS3703A7120DSERQ1: identical DSE pinout, SBVS344D Pin Functions) | SBVS249B p4, Pin Functions |
| TLV3202AIDGKR / TLV3201AIDBVR | SBOS561C p3, Pin Functions / Figure 5-1, 5-2 |
| TPS7A25xxDRV_fixed | SBVS372C p3–4, Figure 5-2, Table 5-1 (fixed column) |

Orderability was verified from the manufacturer's datasheet ordering tables for: TPS16630RGER, TPS3703A7330DSER,
TPS3430WDRCR, TLV3202AIDGKR, TLV3201AIDBVR, TPS7A2550DRVR, TPS7A2518DRVR, SN74LVC1G17DBVR, CSD16301Q2, 2N7002LT1G,
WSK2512R0100FEA; H2-E.1: TPS3703A7120DSERQ1 (SBVS344D addendum) (part-number scheme, value range, 1.19 mm thickness for 0.005–0.2 Ω).

**Not verified against a datasheet or distributor in this session** (MPNs follow the vendor part-numbering scheme; confirm
stock before ordering): Murata GRM… capacitors (in particular **GRM155R61A475MEAAD**, 4.7 µF 10 V X5R 0402 — the tile has no MPN
for this position either), Samsung CL05B105KP5NNNC, Yageo RC0603…/RC2512FK…, Panasonic ERA-3AEB… (incl. the E192 value
**ERA-3AEB1011V**, removed in H2-E.1), Vishay RCS12061R00FKEA (vishay.com not reachable from here, as in H2-D), Würth 613xxx11121 headers,
Phoenix 1715721 / 1714971, Keystone 5000/5001, Amphenol RF 132134. TP1–TP9 and TP25/TP26 are bare PCB pads (no MPN).

Element not realisable with verified parts: a crowbar MOSFET with VGS(th)/RDS(on) specified over temperature (ARCH §3.8 item 5,
M4) — CSD16301Q2 is used as in Candidate A; its 25 °C-only limits remain a T5 measurement item.
