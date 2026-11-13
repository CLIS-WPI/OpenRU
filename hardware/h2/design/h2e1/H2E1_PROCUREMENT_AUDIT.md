# H2-E.1 Final bench procurement and fixture audit (working paper)

- **Date:** 2026-11-12.
- **Baseline:** `203c69f` (H2-E). **Branch:** `hardware/h2e1-procurement-audit`.
- **Scope:** fixture project `fixture_h2e/` and the H2-E bench documents only.
- **Not done:** the main OpenRU tile schematic is unchanged. Nothing purchased, fabricated or energised. No vendor
  contacted.
- **Evidence classes:**
  - **DS:** datasheet / user guide;
  - **WEB:** vendor page snapshot, 2026-11-12;
  - **DERIVED:** `h2e1_checks.py`, which imports the H2-D `budget.py` unchanged;
  - **UNVERIFIED.**
- **Datasheets used:**
  - TPS3703 SBVS249B;
  - TPS3703-Q1 SBVS344D;
  - TPS1663x SLVSET9G;
  - SNVU635 (TPS3703Q1-A4120EVM);
  - TLV3201/02 SBOS561C;
  - KOA RN73R, Vishay TNPW e3, Stackpole RNCF, Yageo RT, Susumu RG, Bourns CRT.

## 1. A-SENSE: TPS3703 SENSE over-voltage with +5V_PA at 12 V (FB-open regulator fault)

### 1.1 The exposure (as drawn in H2-E)

- U4 is a TPS3703A7330 (3.30 V nominal) behind a 5.49 k / 10.7 k divider, so k = 0.661.
- At +5V_PA = 12 V, SENSE = 7.93 V. The limits are 6 V abs max and 5.5 V ROC (SBVS249B §7.1, §7.3). The ROC holds
  only up to +5V_PA = 8.3 V.
- The H2-E fix, a BAS116 clamp to +5V_IL, limited SENSE to about 5.9 V. That is still above the ROC.
- The clamp also creates a back-power path: about 0.56 mA flows into +5V_IL, which the TPS7A25 cannot sink.

### 1.2 Options evaluated (DERIVED, `h2e1_checks.py`; worst case = VIT accuracy + 2 × 0.1 % ratio + 2 × 25 ppm/K over 65 K + ISENSE 1.5 µA)

| | H2-E (A7330, clamp) | Option 1: TPS3703B6050 (0.5 V, ±6 %) 18.0 k/2.00 k | **Option 2: TPS3703A7120-Q1 (1.2 V, ±7 %) 3.16 k/1.00 k — selected** |
|---|---|---|---|
| SENSE at +5V_PA 12 / 13.2 V | 7.93 / 8.72 V (clamped ≈ 5.9 V) | 1.20 / 1.32 V | **2.88 / 3.17 V** |
| SENSE ≤ 5.5 V ROC up to +5V_PA | 8.3 V | 55 V | **22.9 V** |
| Clamp / back-power path | yes / yes (+5V_IL) | none | **none** |
| UV trip min / max | 4.603 / 4.693 V | 4.631 / 4.796 V | **4.592 / 4.698 V** |
| OV trip min / max | 5.296 / 5.399 V | 5.222 / 5.408 V | **5.283 / 5.406 V** |
| Margin to tile rail 4.85–5.18 V (UV / OV) | +157 / +116 mV | +54 / +42 mV (nuisance-trip risk) | **+152 / +103 mV** |
| OV max to ADTR1107 5.5 V abs max | +101 mV | +92 mV | **+94 mV** |
| UV min to eFuse VIN ROC 4.5 V | +103 mV | +131 mV | **+92 mV** |
| Accuracy / tPD / timing option | ±0.7 % / 30 µs / A | ±1 % (VIT < 0.8 V) / 30 µs / B (1 / 20 ms) | **±0.7 % / 30 µs max (SBVS344D §7.6) / A (10 / 200 ms), same as U3** |
| Stock (WEB) | ti.com OOS; LCSC 37 | ti.com in stock; LCSC 0 | **ti.com in stock, $1.151** |

**Rejected options:**
- **Series resistor plus a clamp to +5V_IL** (as drawn): violates the ROC and back-powers +5V_IL.
- **Precision shunt clamp to GND (TLV431-class) on the A7330 divider:** it would work, but it adds an active part
  whose open-circuit failure is latent.

**Option 2 notes:**
- **Why selected:** it removes the exposure with no added part: it is a divider change on the same DSE footprint and
  pinout.
- **Divider current:** the 3.16 k / 1.00 k divider draws 1.2 mA at 5 V. R10 dissipates 32 mW at 13.2 V (0.1 W
  rating).

**Not datasheet-bounded:**
- ISENSE is specified only at VSENSE = 5 V (≤ 1.5 µA), and the same value is assumed at 1.2 V. The SENSE Thevenin
  resistance is 760 Ω, so 1.5 µA shifts the trip points by 0.1 %, and that shift is included in the table.
- The -Q1 part is automotive-qualified. Its electrical tables (abs max, ROC, accuracy, tPD, VOL) match the
  commercial datasheet line for line. The match was checked for the rows used here.

### 1.3 Applied to the fixture (schematic change)

- U4 changes to **TPS3703A7120DSERQ1**. The symbol is pin-identical; lib_id is unchanged and the Value and MPN fields
  are updated.
- The divider changes to R10 **3.16 k** (ERA-3AEB3161V) and R11 **1.00 k** (ERA-3AEB102V).
- **D1 BAS116 is removed** together with its two stubs and labels. The SENSE node now has no path to +5V_IL.
- U3 (the +5V_IL monitor) stays TPS3703A7330.

**Other pins on +5V_PA at 13.2 V (DERIVED):**

| Pin | Voltage at 13.2 V | Limit / note |
|---|---|---|
| TLV3201 fast-OV input (k = 0.339) | 4.48 V | ≤ VCC + 0.2 V; holds up to 15.2 V |
| eFuse OVP pin (k = 0.224) | 2.96 V | 5.5 V abs max |
| U10 IN / P_IN | — | rated to 60 V |

**Tile (not changed):** the same substitution is recommended for the tile's +5V_PA monitor (open item A-SENSE becomes
"resolved in fixture, pending tile implementation").

**New related item A-IL12 (not addressed by this fix):**
- A TPS7A25 pass-element short puts VIN (12 V) on +5V_IL. That rail supplies every permit-logic part (TPS3703 VDD abs
  max 6 V, TLV320x, TPS3430).
- A SENSE clamp cannot protect against this. Rail-level OV protection for +5V_IL is needed on the tile.
- It applies to the fixture as well, where VIN is a bench supply that can be current-limited.

## 2. MPN synchronisation (fixture schematic ↔ `FIXTURE_BOM.csv`)

- **The 7 CHANGED lines (10 references) are now written into the schematic MPN fields:**

| References | New MPN |
|---|---|
| C1 | CL10B105KA8NNNC |
| C2–C4 | CL10A475KP8NNNC |
| C5 | CL31B106KPHNNNE |
| C10 | CL10B104KB8NNNC |
| C33 | GRM155Z71A105KE01D |
| J2 | 1711725 |
| R55, R56 | ERA-3AEB103V |

- **Other edits:**
  - TP10–TP24 MPN fields are normalised to `5000` / `5001` (they read "Keystone 5000").
  - `FIXTURE_PARTS.csv` is regenerated from the BOM, so both lists agree.
- **New check, `tools/check_bom_sync.py`:** it compares every schematic MPN field with the BOM.
  Result: **0 mismatches**, and 0 schematic parts missing from the BOM (bare-pad TPs are excluded by design).
- **Fixed defect:** the committed H2-E netlist `out/candA_fixture.xml` was not valid XML, because path sanitising had
  inserted `<repo>`. The path is now sanitised to a relative `<source>` and the file parses.

## 3. Unavailable parts

### 3.1 U10 TPS16630RGER (VQFN-24): out of stock (ti.com, LCSC; RGERG4/RGET also OOS)

| Alternative | Status (WEB) | Electrical equivalence (DS, SLVSET9G) | Action |
|---|---|---|---|
| **TPS16630PWPT** (HTSSOP-20, PWP0020T) | **ti.com InStock**, $2.428 (qty break UNVERIFIED) | §6.5 Electrical Characteristics and §6.6 Timing have **no package column**. ILIM, RON, OVP, SHDN→FET-off 0.8–1.5 µs and MODE are identical. Only thermal differs: RθJA 32.2 vs 31.4 °C/W. Typical curves are "taken on VQFN" | **Recommended**, not drawn. It needs a new symbol (every pin number differs: IN 1–3, P_IN 6, UVLO 7, OVP 8, GND 9, dVdT 10, ILIM 11, MODE 12, SHDN 13, IMON 14, FLT 15, PGOOD 16, OUT 18–20, NC 4/5/17, PowerPAD 21) and footprint `Package_SO:HTSSOP-20-1EP_4.4x6.5mm_P0.65mm_EP3.4x6.5mm_Mask2.96x2.96mm`. The KiCad land matches TI's PWP0020T copper and mask; signal pad length is 1.575 vs 1.5 mm. Do it together with the fixture layout approval. After the swap: rerun ERC/netlist and `expected_fixture.json`, and check that the PowerPAD is not the only GND |
| TPS16630PWPR | OOS | as above | — |
| TPS16632 / TPS16637 | TPS16637PWPR in stock | **Not equivalent:** fixed 39 V clamp or no OVP; TPS16637 has PLIM on pin 8 | Rejected (OVP is a safety function) |
| "TPS1663A/B" | do not exist (404; not in SLVSET9G) | — | — |

E1 uses the TPS16630-32EVM, so U10 stock does **not** block E1–E4.

### 3.2 R58 1.01 kΩ 0.1 % 25 ppm (E192): no stocked source at any maker

**Same-spec parts:** none showed stock at any reachable source.

| Maker | MPN | E192 status |
|---|---|---|
| KOA | RN73R1JTTD1011B25 | standard E192 |
| Vishay | TNPW06031K01BEEA | standard E192 |
| Stackpole | RNCF0603BTE1K01 | E192, "higher MOQ" |
| Yageo | RT0603BRD071K01L | "on request" |
| Susumu RG, Bourns CRT | — | E24/E96 only |

Note: Yageo RT…**BRE**… is 50 ppm and is rejected.

**Applied:** R57/R58 changes from 9.09 k / 1.01 k to **18.0 k / 2.00 k** (ERA-3AEB183V / ERA-3AEB202V). These are E24
values in the same catalog, at the same 0.1 % and 25 ppm.

**Revalidation (DERIVED):**
- **Divider ratio:** k = 0.10000 exactly in both cases. The H2-D budget (`vref_max = 0.1·VCB·1.001 + VIO`) and the
  `arch_a_sim.py` model use only k, so the BBM bounds (1.278 / 2.713 µs) are unchanged.
- **Comparator source impedance:** 1.8 kΩ × IIB 5 nA max (−40…125 °C, SBOS561C) gives 9 µV, against the 6 mV VIO
  already in the budget.
- **Load:** VCB load falls from 0.47 to 0.24 mA. VCB_MIN in the budget already assumes the higher load.
- **Not re-run:** the behavioural sim, because it has no R57/R58 values to change.

## 4. E1–E5 gate and timing-budget audit

**Budget recomputed from `budget.py` (DERIVED):**

| Quantity | Value |
|---|---|
| Rail row | 46.50 µs |
| Chain after P↓ | 16.499 µs |
| d_min | 2.778 µs |
| BBM falling / rising | ≥ 1.278 / 2.713 µs |
| E2 discharge allowance | 16.40 µs |

**Checked and consistent:**
- the 46.5 / 16.5 µs split;
- the E4 bound P < 1.13 V: 2 × (0.8 − 0.235) V;
- the E5 BBM GO limits (1.0 / 2.0 µs) sit inside the budget (1.278 / 2.713 µs);
- the overlap threshold: 50 mA = 2.5 × the 20 mA noise floor.

**Corrections applied to `design/h2e/BENCH_PROCEDURES.md`:**

| # | Finding | Correction |
|---|---|---|
| G1 | The decision tree's "GO/HOLD → continue" could be read as passing | Explicit rule: **HOLD is never a PASS**. It is reported as "HOLD — not passed", does not satisfy its T-test or "A is viable", and becomes GO only through a written budget re-run (plus a vendor answer where stated) |
| G2 | The E1a HOLD band reached 2.08 µs (0.75 × d_min). That leaves BBM_fall = 0.69 µs, below BENCH_PLAN T7's 1.0 µs, and T1a's pass limit is 1.5 µs. The band relaxed a BENCH_PLAN limit | HOLD 1.50–**1.778 µs** (d_min − 1.0 µs); NO-GO > 1.778 µs. T1a is reported FAILED in the HOLD band until TI answers Q1 |
| G3 | The E2 RDS(on) kill bound was rounded **up** (exact value 119.4 mΩ, stated as 120 mΩ) | NO-GO > **119 mΩ** |
| G4 | E3 had no gate for slow UV ramps. The 5 %-overdrive point below UV(min) is 4.36 V, under the eFuse 4.5 V VIN ROC, and tPD does not bound low overdrive | New **E3c**: RESET ≤ 0.8 V before +5V_PA < 4.50 V + U_V, else NO-GO (unless E1b is GO at that VIN) |
| G5 | The E3 HOLD band depends on E5, which runs later; the E3 device was not the H2 part | E3 HOLD is provisional (33.5 µs ceiling) until E5. E3 runs on **both** exact MPNs (A7120-Q1 on +5V_PA, A7330 on +5V_IL) |
| G6 | E5 t_chain on the fixture includes RS3 (10 mΩ): the placeholder budget alone gives 17.07 µs, a false HOLD. Subtracting a calculated term would favour the design | Measure t_chain with the RS3 force pads shorted; no subtraction. The NO-GO edge is written as 50 − max(30 µs, E3 X_g + U_t) |

**Unchanged and noted:**
- The E5 crowbar peak current (27/33 A) is a model-consistency check, not a safety bound. Per the H2-E correction, the
  peak is not guaranteed.
- BENCH_PROCEDURES uses 22.6 Ω / 0.88 A; the fixture fits 22.1 Ω (0.905 A). The fixture value is the worst case for
  load current, so this is acceptable.

## 5. Can the TPS3703 EVM characterise the exact device?

**No, not as shipped** (SNVU635, DS):
- U1 is **TPS3703A4120DSERQ1** (1.2 V, **±4 %**), soldered, on the DSE0006A land. It has no SENSE divider: SENSE is
  fed at J2-1, with a 10 nF filter (C2). RESET pull-up and CT parts are 10 k.

**What it does provide:** the DSE land and the circuit topology. Same family (-Q1) and same 1.2 V threshold as the
selected U4.

**Required adaptation (no adapter board needed):**
1. **Rework U1** to TPS3703A7120DSERQ1 on each E3/E4 EVM, and to TPS3703A7330DSER for the U3 runs. The land pattern
   is identical: SBVS249B / SBVS344D package outline.
2. Replace R1 (RESET pull-up) with **2.2 kΩ to 5.08 V**, as in E3/E4.
3. **Remove C2**, or record it: 10 nF on SENSE changes the ramp and step response.
4. Drive SENSE through the real divider: 3.16 k / 1.00 k (0.1 %) from the fast-slew source. This also exercises the
   divider's 760 Ω source impedance.
5. Decode CT before use. The user guide contradicts itself: C3 is labelled "100 ms" vs 10 ms in §3.4, and the latch
   jumper is J3 1-2 vs J4 1-2. **Check both on the board** before any latch-mode run.

**Bare-part alternative:**
- IPC0056 (DFN-6 1.6 × 1.6 mm, 0.5 mm, no EP) DIP adapter: LCSC $4.86, 0 stock. Its fit to DSE is UNVERIFIED, so it
  is not preferred.
- **Do not count EVM-device (A4120) data as H2 evidence:** it is family data only.

## 6. E1–E4 minimal purchase shortlist (nothing ordered)

Prices are WEB 2026-11-12 and indicative. EVM stock is UNVERIFIED because ti.com renders it client-side.

**Stage 1 (kill-first, one unit of each)** answers whether any NO-GO exists. **Stage 2** adds units to meet the §2.5
statistics (≥ 3 units per DUT, ≥ 5 for MOSFETs), and is bought only if Stage 1 has no NO-GO.

| # | Item | Use | Stage 1 qty | Stage 2 add | Unit (USD) | Availability | Stage 1 cost |
|---|---|---|---|---|---|---|---|
| 1 | TPS16630-32EVM | E1, E4 (FLT) | 1 | +2 | 108.90 | listed; stock UNVERIFIED | 108.90 |
| 2 | TPS3703Q1-A4120EVM | E3, E4 (rework U1) | 1 | +2 | 27.50 | listed; stock UNVERIFIED | 27.50 |
| 3 | TPS3430EVM | E4 (WDO) | 1 | +0 (rework TPS3430 onto the board) | 31.90 | listed; stock UNVERIFIED | 31.90 |
| 4 | TPS3703A7120DSERQ1 | E3/E4 DUT (U4) | 4 | +4 | 1.151 | ti.com InStock | 4.60 |
| 5 | TPS3703A7330DSER | E3/E4 DUT (U3) | 4 | +4 | 2.65 @10 (LCSC) | ti.com OOS; LCSC 37 | 10.60 |
| 6 | CSD16301Q2 | E2 crowbar FET | 10 (two sources = two lots) | — | 0.307 (ti.com) / 0.332 (LCSC) | ti.com 24,241; LCSC 3,235 | 3.20 |
| 7 | 2N7002LT1G | E2/E4 small NMOS | 20 | — | 0.0309 @20 (LCSC) | LCSC 319,180 | 0.62 |
| 8 | TPS3430WDRCR | E4 spare DUTs | 3 | +2 | 2.186 | ti.com 43,359 | 6.56 |
| 9 | TLV3202AIDGKR | E4 (NMOS gate drive at real VOH) | 3 | — | 2.12 | ti.com **230** | 6.36 |
| 10 | SN74LVC1G17DBVR | E2 (measure VOH at 32 mA for the RDS(on) point) | 5 | — | 0.142 | ti.com 558,061 | 0.71 |
| 11 | Kelvin shunt 20–50 mΩ 4-terminal (e.g. WSK2512R0250FEA) | E1 eFuse output current | 2 | — | UNVERIFIED | UNVERIFIED | — |
| 12 | PA-emulator parts for E1 (4 × 4.7 µF 10 V, 1 µF, 10 nF, 100 pF; 22.1 Ω 1 W ×4 or 2 × 44.2 Ω; 8.2 Ω 5 W + logic NMOS) | E1 load corners | 1 set | — | ≈ 5 (EST) | catalog parts | ≈ 5 |
| 13 | SON-6 2 × 2 mm adapter IPC0165, or a custom 4-wire Kelvin coupon | E2 | 5 | — | UNVERIFIED | Proto-Advantage refused; **no stock Kelvin socket found** | — |

**Totals:**
- **Stage 1:** about **$206** plus the UNVERIFIED items 11 and 13.
- **Stage 2:** adds about **$292**:
  - 2 × TPS16630-32EVM = $217.80;
  - 2 × TPS3703 EVM = $55.00;
  - spare DUTs about $20.
- **Overall:** about $498 for full statistics.
- **Not included:** shipping and tax.

**Laboratory instruments** (from BENCH_PROCEDURES §2.1, limited to E1–E4). Lab inventory was not checked, and none
are priced.

| Instrument | Needed for | Minimum |
|---|---|---|
| Oscilloscope | E1, E3 | ≥ 4 ch (8 ch only for E5), ≥ 350 MHz, ≥ 2.5 GS/s, ≥ 12-bit/HiRes, segmented memory, in calibration |
| Passive probes with spring tips; differential probe | E1 (high-side shunt) | ≥ 100 MHz, ±10 V, CMRR ≥ 80 dB DC–1 MHz |
| DC current probe | E1 alternative to the shunt | 3σ ≤ 20 mA at 20 MHz BW |
| Pulse / function generator | E1 SHDN, E3 steps | 2 ch, ≤ 10 ns edges, burst/trigger |
| Fast-slew source | E3 1–10 V/µs ramps and steps | power op-amp or MOSFET switch |
| Programmable supplies | E1, E3 | 0–6 V ≤ 0.5 A ×2 with ramp/list mode; 0–6 V ≥ 3 A for eFuse VIN (current-limited) |
| SMU, 4-wire | E2, E4 | ±10 V, ±1 A DC, ≥ 10 A pulsed (≥ 24 A optional for the single-pulse point) |
| DMMs, 6½-digit | E3 static thresholds, shunt calibration | ×2 |
| Thermal chamber or forcing system | E1–E4 | −45…+90 °C, dry-N₂ purge; type-T thermocouples ±1 °C bonded to the DUT; ice-point check |
| Electronic load | E1 | optional; resistor loads are the reference |

**E1–E4 procurement readiness:** the shortlist is complete except items 11 and 13, which have no reachable price or
stock. Stage 1 can be ordered once purchase approval is given and EVM stock is confirmed in a browser.
