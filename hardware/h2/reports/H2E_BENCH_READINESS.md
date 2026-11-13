# H2-E Candidate-A bench-validation readiness package

- **Date:** 2026-11-12.
- **Branch:** `hardware/h2e-bench-prep` (from H2-D `671ee23`).
- **Main OpenRU tile schematic: unchanged.**
- **Not done:** nothing purchased, fabricated or energised; no ADTR1107 on any test article; no vendor contacted.

## 1. Corrections to the H2-D safety analysis

| Item | Correction | Files |
|---|---|---|
| Crowbar/eFuse overlap "≤ 25 A" | **Not a guarantee.** 5.5 V / 0.221 Ω ≈ 25 A is an estimate from maximum resistances, but lower resistance gives higher current and the crowbar-FET / eFuse RDS(on) minima are not specified. The TPS1663 short-circuit current (≈ 45 A) is **typical**. Only the duration (≤ 1.5 µs once SHDN is asserted) is datasheet-bounded | `design/h2d/ARCH_COMPARE.md`, `reports/H2D_SAFETY_ARCHITECTURE_REVIEW.md` |
| T12 acceptance "VOUT above 5.5 V for ≤ 2 µs" | Removed. VOUT ≤ 5.5 V at all times (ADTR1107 VDD_PA abs max); any excursion is a FAIL unless ADI provides a written transient rating | `design/h2d/BENCH_PLAN.md` |
| T9 "abs-max stress at −5.5 V for 1 s" on ADAR1000 AVDD1 | Removed. Only the recommended range (−4.75…−5.25 V) is applied | `design/h2d/BENCH_PLAN.md` |
| Sim criterion G "+10 mV above 0 V" | Removed (`VG_HI = 0.0`). The recorded H2-C/D worst case of +2 mV therefore **fails**. It is open until ADI states the PA_BIAS output impedance at code 0x00 | `sim/run_h2c_sim.py`, `sim/H2C_SEQUENCING_SIM.md` |

## 2. Independent test fixture: `fixture_h2e/` (separate KiCad project, schematic only, no layout)

One chain of Candidate A with dummy PA loads only:
- **Power:** TPS7A25 +5V_IL; +5V_PA from an external supply terminal.
- **Permit:** permit node P with 2× TPS3703 window monitors, 3× TLV3202 (gate-lost ×4, negative-rail window), TLV3201
  fast OV, TPS3430 watchdog, ARM stage, FAULT_INJ.
- **Switch and crowbar:** TPS16630 eFuse (latch, OVP 5.36 V, ILIM 1.84–2.16 A); SHDN-timed CSD16301Q2 crowbar with
  6 × 1 Ω RCS1206.
- **Dummy loads:** 4 × 22.1 Ω PA loads plus an 8.32 Ω "gate lost" bank, each switched. Tile-identical drain
  decoupling.
- **Measurement:** 3 × 10 mΩ Kelvin shunts (eFuse in/out, crowbar), probe pads with GND springs, thermocouple pads.
- **Fault-injection links:** C_t open, R_t short, SHDN override, crowbar stuck-on, MODE retry, FLT/watchdog isolation.

**Checks:** ERC **0 violations** (no severity changes); `validate_hierarchy` 0 issues; netlist vs
`expected_fixture.json` **728/728**, re-run independently. Details: `fixture_h2e/FIXTURE_DESIGN.md`, `out/` (ERC,
netlist, PDF).

**Finding that feeds back into Candidate A:** the TPS3703 SENSE pin on +5V_PA exceeds its 6 V abs max once +5V_PA
passes about 9.1 V. The FB-open fault drives +5V_PA toward 12 V. The fixture adds a BAS116 clamp to +5V_IL, which
still allows about 5.9 V, above the 5.5 V operating range. **Candidate A on the tile needs a protected SENSE input**:
open item A-SENSE.

## 3. BOM (`fixture_h2e/FIXTURE_BOM.csv`, `FIXTURE_BOM_NOTES.md`; indicative prices, 2026-11-12)

| | Value |
|---|---|
| Parts per board (fitted, priced lines) | **$54.18** |
| Parts for 3 boards incl. MOQ | **$172.17** |
| PCB fab / assembly | NOT QUOTED |
| Phase-1 EVMs (ti.com list) | TPS16630-32EVM $108.90; TPS3703Q1-A4120EVM $27.50; TPS3430EVM $31.90 (**$168.30**) |
| Lines | 73: 62 VERIFIED (MPN exists), 7 CHANGED (same value/rating/package), 4 UNVERIFIED |
| Un-priced lines | Würth headers, RCS1206 1 Ω, WSK2512 shunts. The true total is higher |

**Build blockers:**
- **U10 TPS16630RGER:** out of stock at ti.com and LCSC. The HTSSOP variant needs a different footprint.
- **R58 1.01 kΩ 0.1 %:** made to order only. Choose an alternative source or a standard value.

**Stock risks:** TPS7A2550/TPS7A2518 (out of stock at ti.com), TPS3703A7330 (37 at LCSC; 6 needed).

Digi-Key, Mouser, Octopart and Findchips refused automated access and were not bypassed; check them manually.

**Schematic MPN fields still carry the pre-correction MPNs for the 7 CHANGED lines.** The BOM CSV is authoritative and
the schematic must be synced before any order.

## 4. Minimum experiments (`design/h2e/BENCH_PROCEDURES.md` §1)

Each experiment is GO / HOLD / NO-GO. Uncertainty always counts against the design: the value used is the worst
observed result or mean ± 2.9 s (n = 30). E1–E4 need no fixture and run first.

| # | Experiment | GO | NO-GO |
|---|---|---|---|
| E1 | TPS16630-32EVM: SHDN → FET off (output current < 50 mA) at −40/25/85 °C, 0–2 A, ≥ 50 events; leakage with SHDN low at VIN 0–4.5 V | ≤ 1.5 µs; leakage ≤ 10 mA | > 2.08 µs, or any single event ≥ 2.778 µs − U, or leakage > 10 mA |
| E2 | Crowbar MOSFET (SMU, Kelvin socket), −40/+85 °C | RDS(on) ≤ 58 mΩ at +85 °C/3.8 V; VGS(th) ≥ 0.5 V hot, ≤ 2.0 V cold | RDS(on) > 120 mΩ, VGS(th) < 0.30 V or > 2.5 V (rejects that MPN, not Candidate A) |
| E3 | TPS3703 detection delay vs overdrive 2–20 % and ramp 0.01 V/ms–10 V/µs | ≤ 30 µs | > 50 µs − measured E5 chain (33.5 µs until E5 is done); any missed detection |
| E4 | Supervisor VOL at 2.5 mA, including during supply ramp-down | ≤ 0.35 V | > 1.0 V |
| E5 | Fixture: break-before-make and discharge, gate-only ≥ 500 cycles per temperature, full-energy ≥ 30 events at ≤ 1/min | BBM ≥ 1.0 µs (falling), ≥ 2.0 µs (rising); P↓ → drain < 0.5 V ≤ 16.5 µs; VOUT ≤ 5.5 V | BBM ≤ 0; > 20 µs |

**Gates that are never relaxed:**
- nothing above an ADTR1107 or ADAR1000 abs max without written manufacturer evidence;
- the 50 µs drain criterion;
- BBM > 0 after subtracting measurement uncertainty.

**Overlap criterion:** eFuse output current < 50 mA (≥ 2.5 × the shunt noise floor) whenever the crowbar VGS is at or
above its threshold limit.

## 5. Manufacturer questions (concise; ✱ = blocks a kill decision)

**TI**
1. ✱ TPS1663/TPS16630: definition of "FET OFF" in the 1.5 µs SHDN spec; does it hold at 1–2.2 A with ≤ 25 µF output?
2. ✱ TPS1663: is SHDN V(rising) guaranteed ≥ V(falling); what is the SHDN pin capacitance?
3. ✱ TPS1663: can the FET conduct with SHDN low at VIN 0–4.5 V; what are the internal POR min/max?
4. TPS1663: FLT assertion delay after TSD/OCP/UVLO, and is the FET off by then?
5. TPS1663: is there a guaranteed peak current before fast-trip (≈ 45 A is typical only)?
6. ✱ TPS3703: maximum detection delay for overdrive < 5 % and for slow ramps?
7. TPS3703: does a manual reset latch in latch mode (CT = GND)?
8. TPS3703: VOL max at 2.5 mA, VDD 3.9–5.1 V, over temperature? Is SENSE protected above 6 V?
9. TPS3430: maximum WDI → WDO delay?
10. TLV3202: output state for VCC 0–2.7 V?
11. TPS568230: current limit and inductor peak with FB open?
12. Stock / lead time for TPS16630RGER, TPS7A2550DRVR, TPS7A2518DRVR.

**ADI**
1. ✱ ADTR1107: written VDD_PA transient rating above 5.5 V, or confirmation that 5.5 V is absolute?
2. ADTR1107: VGG_PA abs max when VDD_PA = 0 V; VSS_SW abs max?
3. ADAR1000: PA_BIAS output with AVDD3 absent and AVDD1 present; output impedance at code 0x00?
4. ADAR1000: PA_BIAS pin abs max and DAC full-scale min/max?
5. ADAR1000/ADTR1107: how is 0x85 (≈ −2.5 V) reconciled with the −2 V VGG_PA abs max?

**MOSFET vendor**
1. ✱ A ≥ 35 A crowbar NMOS with VGS(th) and RDS(on) specified at −40 and +125 °C?
2. Small NMOS with VGS(th) min hot and RDS(on) max at 4.4 V over temperature?
3. Repetitive pulse rating at 35 A / 10 µs, at 1 Hz and at 1/min?

**Vishay**
1. ✱ RCS1206 1 Ω: repetitive pulse rating at 5.5 A, τ 5.4 µs (1/s and 1/min), and drift over life?
2. RCS1206: pulse derating at −40 and +85 °C?

**Panasonic**
1. Availability or lead time of ERA-3AEB1011V (1.01 kΩ, 0.1 %).

## 6. Readiness

| | Status |
|---|---|
| Phase-1 experiments E1–E4 on EVMs/loose parts | **Ready to start once approved**: procedures, gates and instrument list written. Needs purchase approval ($168.30 EVMs plus the MOSFET samples) |
| Fixture (E5 onward) | **Schematic ready, not build-ready.** Blockers: U10 stock, R58 value, schematic MPN sync, PCB layout of the fixture (not started; needs approval), and unpriced lines |
| Candidate A on the tile | Not started. Gated by E1–E5 and the ✱ questions. Open item A-SENSE added |
| OpenRU tile PCB layout | **NO-GO** |

> **H2-E.1 update (2026-11-12):** see `H2E1_PROCUREMENT_READINESS.md`.
> - **A-SENSE:** resolved in the fixture with TPS3703A7120-Q1 behind 3.16 k / 1.00 k; D1 removed.
> - **Schematic MPNs:** synced with the BOM.
> - **R58:** R57/R58 moved to 18.0 k / 2.00 k (same ratio).
> - **U10:** TPS16630PWPT identified as the in-stock alternative; not drawn.
> - **E1:** HOLD ceiling corrected to 1.778 µs.
> - **E2:** kill bound 119 mΩ.
> - **E3:** new E3c gate.
> - **E5:** t_chain measured with RS3 shorted.
> - **HOLD:** never a PASS.
> - **Totals in §3:** superseded ($52.16 per board).
