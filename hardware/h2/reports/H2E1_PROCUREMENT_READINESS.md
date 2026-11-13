# H2-E.1 Bench procurement and fixture audit: readiness report

- **Date:** 2026-11-12. **Branch:** `hardware/h2e1-procurement-audit` (from H2-E `203c69f`).
- **Main OpenRU tile schematic: unchanged.**
- **Not done:** nothing purchased, fabricated or energised; no vendor contacted.
- **Working paper:** `design/h2e1/H2E1_PROCUREMENT_AUDIT.md`.
- **Checks:** `design/h2e1/h2e1_checks.py`, output in `h2e1_checks.txt`. The H2-D budget is imported unchanged.

## 1. Results

| # | Task | Result |
|---|---|---|
| 1 | TPS3703 SENSE overvoltage (+5V_PA → 12 V on an FB-open fault) | **Resolved in the fixture.** U4 is now TPS3703A7120DSERQ1 (1.2 V, ±7 %) behind 3.16 k / 1.00 k. SENSE stays ≤ 5.5 V ROC up to +5V_PA = 22.9 V (3.17 V at 13.2 V) with **no clamp and no back-power path**. The BAS116 clamp to +5V_IL is removed: it held SENSE only to about 5.9 V and fed +5V_IL. Worst-case trips: UV 4.592–4.698 V, OV 5.283–5.406 V, i.e. ≥ 103 mV from the tile rail spec and 94 mV below the 5.5 V abs max. Same tPD (30 µs max), accuracy and A timing as before. **Tile: change recommended, not applied** |
| 2 | Sync of the 7 outdated MPN fields | **Done:** 10 references plus TP10–TP24 normalised. New `tools/check_bom_sync.py` reports **0 mismatches** |
| 3a | TPS16630RGER out of stock | **TPS16630PWPT (HTSSOP-20) is in stock** at ti.com. SLVSET9G specifies the electrical and timing limits identically for both packages; only the thermal figures differ. **Not substituted:** it needs a new symbol and footprint (every pin number changes), to be done together with layout approval. TPS16632/37 are rejected because their OVP differs. U10 does not block E1–E4 |
| 3b | R58 1.01 kΩ made to order | No stocked same-spec source at any maker. **Applied:** R57/R58 are now 18.0 k / 2.00 k (E24, same 0.1 % / 25 ppm). k = 0.1000 exactly, which is the only quantity the budget and sim use. Comparator bias error is 9 µV against the 6 mV already budgeted |
| 4 | E1–E5 gate and budget audit | The budget re-derives exactly (46.5 / 16.5 µs; BBM 1.278 / 2.713 µs). **Six corrections:** (G1) HOLD is never a PASS; (G2) E1 HOLD ceiling 2.08 → 1.778 µs, because the old band relaxed T1a/T7; (G3) E2 kill bound 120 → 119 mΩ (rounded the safe way); (G4) new E3c slow-ramp gate against the eFuse 4.5 V ROC; (G5) E3 HOLD is provisional until E5, and E3 runs on both exact MPNs; (G6) E5 t_chain is measured with RS3 shorted (RS3 alone would cause a false HOLD), with no subtraction |
| 5 | Can the TPS3703 EVM test the exact device? | **No, not as shipped:** it fits TPS3703A4120-Q1 (±4 %). **Required:** rework U1 to A7120-Q1 or A7330 (same DSE land), set R1 to 2.2 k, remove or record C2 (10 nF on SENSE), and drive SENSE through the real divider. The user guide contradicts itself on the CT capacitor and the latch jumper, so verify both on the board. No adapter board is needed. EVM-device data counts as family data only |
| 6 | E1–E4 purchase shortlist | Stage 1 (one of each, kill-first) **≈ $206**; Stage 2 (statistics) **≈ $292**. Quantities, prices, stock and the instrument list are in the working paper §6 |
| 7 | ERC / netlist after the fixture changes | **ERC 0** (no severity changes), `validate_hierarchy` 0 issues, netlist **725/725** against `expected_fixture.json` (728 − D1's 3 checks), MPN sync 0 mismatches. The H2-E netlist file was not valid XML, because path sanitising had inserted `<repo>`; it is now fixed |

## 2. Procurement readiness

| Item | Status |
|---|---|
| E1–E4 Stage 1 | **Ready to order on approval.** Remaining before ordering: confirm EVM stock in a browser (ti.com renders it client-side); price a 20–50 mΩ Kelvin shunt and the E2 SON-2×2 fixture (no stock Kelvin socket exists, so an adapter or custom coupon is needed) |
| E5 fixture | **Not build-ready.** Blockers: U10 (drawn as the OOS RGE; PWPT requires a redraw); fixture PCB layout not started (needs approval); about 25 lines with stock UNVERIFIED (Panasonic ERA, Yageo 2512, Vishay RCS/WSK, Würth); unpriced lines; U1/U2 TPS7A25 OOS at ti.com; U3 A7330 LCSC-only (37 pcs) |
| Candidate A on the tile | Not started. Gated by E1–E5, the ✱ manufacturer questions, A-SENSE (tile change) and the new A-IL12 |
| OpenRU tile PCB layout | **NO-GO** |

## 3. Remaining blockers and new items

- **A-IL12 (new):** a TPS7A25 pass-element short puts VIN (12 V) on +5V_IL. That rail supplies every permit-logic VDD,
  rated 6 V abs max. A SENSE fix cannot cover it; it needs rail-level OV protection (tile; fixture via a current-limited
  VIN).
- **A-SENSE (tile):** implement the A7120-Q1 + 3.16 k / 1.00 k change in the tile schematic when the PA safety subsystem
  is redrawn.
- **Unchanged from H2-E:**
  - gate-bias S1 (firmware-only);
  - TPS1663 "FET OFF" definition and behaviour below 4.5 V;
  - TPS3703 delay at low overdrive, now also gated by E3c;
  - crowbar MOSFET temperature parameters;
  - RCS1206 pulse rating;
  - ADI PA_BIAS with AVDD3 lost.
- **New manufacturer questions:**
  - **TI:** TPS3703-Q1 ISENSE at VSENSE ≈ 1.2 V (only 5 V is specified);
  - **TI:** TPS16630PWPT lead time;
  - **KOA/Vishay/Stackpole:** quotes for 1.01 k, only if the original R57/R58 values are ever wanted back.
