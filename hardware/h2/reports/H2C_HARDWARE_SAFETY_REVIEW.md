# H2-C Hardware power-safety review

- **Date:** 2026-11-12.
- **Branch:** `hardware/h2c-power-safety` (from H2-B `622ef3c`).
- **Scope:** schematic plus behavioural simulation. No PCB layout, no hardware, no measurement.
- **Evidence classes:**
  - **DS:** manufacturer datasheet.
  - **DERIVED:** calculation from DS values.
  - **SIM-BEHAV:** ngspice behavioural model using datasheet timing. **Preliminary, not hardware-validated.**

All KiCad edits went through the KiCad MCP tools (plugin 0.21.1, KiCad 9.0.9).

## 1. What changed in H2-C

| Block | Implementation | Evidence |
|---|---|---|
| Regulators (placeholders U601–U609 removed) | **TI parts.** analog.com is unreachable, so ADI datasheets could not be verified. The parts:<ul><li>TPS568230 → +3V3_RF_SRC (3.327 V) and +5V_PA (5.000 V; worst case 4.85–5.18 V, under the ADTR1107 5.5 V abs max)</li><li>TPS62933 → +3V3_AUX (always on, UVLO start 8 V)</li><li>TLV75518P → +1V8_DIG</li><li>TPS62933 6.25 V pre-regulator plus 2× TPS7A4701 → +5V_LO / +3V3_LO</li><li>TPS65131 inverter → −6.3 V, plus 2× TPS7A3301 → −5V_BF / −3V3_SW</li></ul> | DS design procedures; `design/h2c/POWER_SPEC.md` |
| Rail ordering in hardware | TPS65131 ENN = PWR_EN_NEG · PG_3V3RF (U913), so the negative rails cannot start before +3V3_RF regulates | ADAR1000 p13; ADTR1107 p24 |
| Independent PA-drain interlock | See §2 | `design/h2c/INTERLOCK_SPEC.md`, `AMENDMENTS.md`, `REC_PARTS.md`, `IMPL_*.md` |
| Decoupling | ADAR1000/ADTR1107 per ADI Stingray schematic 02_059522 Rev B (per-tile sets; per-pin values not documented); +5 V parts rated 10 V; STM32 per ST DS12589 Fig 16 | `design/h2c/PERIPH_SPEC.md` |
| Peripheral checks | <ul><li>STM32 pin/AF map verified against DS12589; PC4 now takes PG_5VPA</li><li>INA226 duplicate address fixed (U610 → 0x42)</li><li>PCA9306 100 pF on VREF2 added</li><li>TPS568230 PGOOD (U651) routed (PG_5VPA)</li></ul> | DS |
| Loop filter | ADIsimPLL is **not available** here (Windows tool; analog.com unreachable). The H2-B derived filter was cross-checked with an ngspice AC analysis: 98.9 kHz crossover, 46.2° PM, −81.3 dB at fPFD. It is still DERIVED (`sim/lf.cir`) | DERIVED |

## 2. Independent PA-drain interlock (as built)

Per chain the drain is switched by a TPS22810, plus an active crowbar: a CSD16301Q2 through 3 × 1 Ω RCS1206 to GND, with
break-before-make drive by DMG1012T Q2 and an RC.

```
PA_DRAIN_EN = PA_ARMED · WDT_OK · NEG_OK                            (U705; R735 1 kΩ; R965 pull-down)
NEG_OK      = IL_EN · GATES_OK                                      (U912)
IL_EN       = NEG_RAILS_OK · PG_3V3RF                               (U915; R973 pull-down)
NEG_RAILS_OK: LM339B window monitors on −5V_BF (< −4.6 V), −3V3_SW (< −3.0 V), +3V3_AUX (> 2.97 V), +3V3_RF (> 3.10 V)
GATES_OK:     16× LM339B "gate lost" (PA_BIAS > −0.15 V → fault)
PA_ARMED:     74LVC1G74 latch; D = GATES_PINCHED (all 16 gates ≤ −1.5 V), CLK = delayed MCU_PA_EN,
              CLR = MCU_PA_EN · WDT_OK · NEG_OK (faults stay latched; re-arm only with pinched gates)
IL_REF (gate-divider reference) = TLV75518P from +3V3_RF (EN = PG_3V3RF) → TPS22917 (ON = IL_EN, clamped by Q3)
PG_3V3RF = U650 PGOOD wired-AND TPS386000 supervisor (+1V8_DIG 1.671 V, +3V3_AUX 2.968 V, 9.6 ms release)
```

- **IL_REF supply:** IL_REF physically cannot exist unless +3V3_RF (ADAR1000 AVDD3) is regulated, both negative rails
  are good, and the supervisor sees +1V8_DIG and +3V3_AUX valid.
- **Why it changed:** this is the result of two simulation-driven corrections, both found by the behavioural sim.
  1. In the first version the gate-divider pull-up put about +0.63 V on an unpowered PA gate.
  2. Undefined comparator/LVC states during the supply ramps could turn the reference on.

## 3. ADAR1000 / ADTR1107 gate-bias conflict (S1)

- **Status:** unchanged from H2-B. The ADAR1000 Rev B p45 OFF value (0x85 ≈ −2.5 V) exceeds the ADTR1107 VGG_PA abs max
  (−2 V).
- **Firmware:** the firmware limit (codes ≤ 0x5D ≈ −1.75 V) is kept as **defence in depth**.
- **No hardware clamp:** none was added. No ADI-verified clamp exists, and inventing one was explicitly ruled out.
- **What the hardware now guarantees independently of firmware:**
  - the drain cannot be armed unless all gates are ≤ −1.5 V;
  - the drain is removed if any gate rises above −0.15 V or any negative rail fails.
- **What it cannot do:** prevent a firmware write below −2 V. That remains firmware-only, so **S1 stays open** until
  ADI answers (draft inquiry 5a, not sent).
- **SIM-BEHAV:** in every simulated run VGG_PA stayed within **+2 mV … −1.750 V**. The +2 mV is PA_BIAS at 0 V through
  the assumed 100 Ω DAC output. That includes ADAR1000-unpowered states and 920 arbitrary-order runs per configuration.
  The minimum is −1.75 V only because the model firmware never writes lower.

## 4. Sequencing / fault evidence (SIM-BEHAV, preliminary)

Source: `sim/H2C_SEQUENCING_SIM.md` (Revision 3, as built), `sim/h2c_results.md`, 50 plots `sim/h2c_*.png`.
Re-run: `env -u LD_LIBRARY_PATH python3 hardware/h2/sim/run_h2c_sim.py` (about 20 min; exits 1 on any failure).

| Fault (as built) | Switch open | Drain < 0.5 V (criterion ≤ 50 µs) | Residual PA energy | Peak crowbar current |
|---|---|---|---|---|
| Gate lost during TX | 4.5 µs | **26.3 µs** | 0.086 mJ | 8.5 A |
| −5V_BF collapse (ENN / LDO) | 6.3 / 7.6 µs | **29.1 / 30.3 µs** | 0.063 mJ | 9.0 A |
| Watchdog in TX / idle | 3.8 µs | **26.8 / 30.3 µs** | 0.064 / 0.001 mJ | 9.0 / 10.4 A |
| VIN loss | 4.8 µs | **27.2 µs** | 0.062 mJ | 9.1 A |
| +3V3_RF lost (EN / silent) | 3.8 / 0.0 µs | **25.9 / 14.4 µs** | 0.060 / 0.029 mJ | 9.1 / 9.0 A |

The H2-B design (no crowbar) took 73–111 µs, and 7.2 ms with the gates pinched. **The 50 µs criterion was not relaxed;**
the active crowbar was added to meet it.

**Ordering test:** 920 runs per configuration (all 720 start-order permutations of the major rails, each with a
shuffled shut-down order and random gaps, plus 200 fully random runs).

| As-built configuration | Failing runs | Worst drain < 0.5 V | Crowbar/switch overlap |
|---|---|---|---|
| Nominal logic | **0 / 920** | 34.1 µs | 0 |
| Pessimistic logic (undefined comparator/LVC outputs and enable inputs treated as ON) | **635 / 920 FAIL** | 50.3 µs | 0 |
| Supervisor detection delay ≥ 20 µs (unspecified in DS) | additional failures | up to 104 µs | up to 4.0 µs shoot-through |

## 5. Destructive or safety-relevant failure modes still open (blockers)

| ID | Failure mode | Status |
|---|---|---|
| **B-S1** | Firmware writes PA/LNA bias beyond −2 V (ADAR1000 p45 values) | firmware limit only; ADI answer pending |
| **B-M5a** | Worst-case logic: BAT54C clamp current lifts PG_3V3RF to 0.66 V, above the TLV755P EN guaranteed-off level (0.3 V). The IL_REF LDO is not *guaranteed* off while +1V8_DIG is between 1.08 and 1.65 V. TPS386000 VOL is specified only at 1 mA | open: needs a clamp redesign (stiffer dedicated clamp transistor, re-simulated) or bench data |
| **B-M5b** | Same clamp holds PA_DRAIN_EN at 0.8–0.97 V, keeping Q2 on and delaying the crowbar (worst 50.3 µs) | open (same fix) |
| **B-TD** | TPS386000 detection delay unspecified ("almost immediately"). At ≥ 20 µs: drain switch on while a supply is invalid; switch opening takes up to 50 µs; up to 4 µs crowbar/switch overlap | needs bench measurement or a supervisor with a specified delay |
| **B-TOFF** | TPS22810 tOFF max and turn-on delay min unspecified; crowbar break-before-make margin is 2.5 µs at the worst corner | bench |
| B-PA0 | PA drain current at 0 V gate (0.6 A/PA) is an ASSUMPTION; ADTR1107 transient SOA not given | ADI / bench |
| B-ADAR | PA_BIAS behaviour while AVDD3 collapses (model assumes high-Z below 2.8 V; no DS basis) | ADI |
| B-INDUCT | Big-buck inductors L650/L651 (≥14.5 A sat) have no MPN/footprint; +5V_PA load-step overshoot not specified (PA abs max 5.5 V) | design + bench |

A candidate fix for B-M5a/b was simulated: dedicated DMG1012T clamps instead of the BAT54C. It removed M5a but
introduced 76 other pessimistic failures because of a slow 100 kΩ/100 pF node. It is **not built**, and it would need
a stiffer drive and a re-run.

## 6. Decision

**PCB layout preparation: NO-GO.**

- The independent interlock passes every nominal-logic simulation, including all 920 arbitrary-ordering runs.
- It does **not** pass the worst-case (pessimistic-logic) bound: B-M5a/b and B-TD remain open.
- The gate-bias conflict (B-S1) is still firmware-protected only.
- All evidence is behavioural simulation; nothing is hardware-validated.

Exit criteria for layout preparation:
1. Close B-M5a/b with a clamp design that passes the pessimistic ordering test.
2. Close B-TD with a supervisor that has a specified maximum detection delay, or with bench data.
3. Bench-characterise TPS22810 tOFF and the crowbar margin on an eval setup.
4. Get ADI's answer on S1 and on PA_BIAS behaviour during AVDD3 collapse.
5. Select MPNs and footprints for L650/L651.
6. Confirm ERC (§ H2C_ERC_REPORT) has no new unresolved findings.

> **H2-D erratum (2026-11-12):** the independent audit (`design/h2d/AUDIT_FMEA.md` finding DU1) shows that the TPS3430
> WDO is *high* (not asserted) for VDD between VPOR and 1.6 V and during power-up (TPS3430 §7.4.2). The H2-C behavioural
> model assumed WDT_OK = 0 below 1.65 V, so the "0/920 nominal-logic" ordering result above is **not valid evidence**.
> See `H2D_SAFETY_ARCHITECTURE_REVIEW.md`.
