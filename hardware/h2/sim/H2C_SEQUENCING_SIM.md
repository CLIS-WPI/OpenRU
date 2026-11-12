# H2-C power sequencing and PA-drain interlock: behavioural simulation

**Classification: BEHAVIOURAL / PRELIMINARY, not hardware-validated.**

- Every IC is a datasheet-timing behavioural model (B-sources, switches, ramps, ideal delay lines, XSPICE flip-flop). No vendor SPICE model runs in ngspice.
- The results show whether the architecture and timing hold under the stated assumptions. They are not device-level verification.
- No KiCad file was touched and nothing is committed.

## Revision 3: as-built REC (current)

**BEHAVIOURAL / PRELIMINARY, not hardware-validated.** The model follows the schematic as drawn (`h2c/IMPL_REC.md`, `h2c/REC_PARTS.md`).

**Runner exit code: 1.** The as-built design fails under pessimistic logic (details below). Under nominal logic it passes everything. All results and plots were regenerated: `h2c_results.md`, `h2c_*.png` and `d_worst_*.cir` (design names ASB*, R2, FIX*).

### Model changes (`h2c_plant.inc`, `asb=1` and parameters)

| Part / net | As built → model |
|---|---|
| Crowbar Q961–Q964 CSD16301Q2 | VGS(th) 0.9 / 1.1 / 1.55 V (corners / nominal / corner). Ciss 340 pF max. Total on-resistance 0.362 Ω = 3 × 1 Ω RCS1206 in parallel + 29 mΩ RDS(on) max. Conductance rises linearly from VGS(th) to 4.5 V. |
| Q2 / Q3 / Q966 DMG1012T | VGS(th) 0.5–1.0 V, swept together; 0.7 Ω on. Q2 is fed by 10 k / 1 nF. The other three chains' Q2 RC branches now load PA_DRAIN_EN. |
| Q3 drive | No longer ideal. Q966 inverts PG_3V3RF onto IL_Q3G: R976 100 kΩ from the supervisor VDD, about 100 pF on the node (Q3 Ciss plus traces). Q3 clamps the TPS22917 ON pin when IL_Q3G > VGS(th). |
| PG_3V3RF | A real node: R654 100 k to +1V8_DIG, plus two sinks. **U650 PGOOD:** 100 Ω, i.e. VOL ≤ 0.4 V at 4 mA. **TPS386000 RESET_N, linearised pessimistically from §6.5:** 400 Ω (0.4 V at 1 mA) for VDD ≥ 1.8 V; 750 Ω for 1.3–1.8 V; 13.3 kΩ (0.2 V at 15 µA) for 0.9–1.3 V; no sink below 0.9 V. |
| BAT54C clamps | Real diodes fitted to the DS11005 VF maximums (0.24 V at 0.1 mA, 0.32 V at 1 mA, 0.40 V at 10 mA), from PA_DRAIN_EN and IL_CLR_N to PG_3V3RF. 1 kΩ series resistors R735 and R975. |
| TPS386000 | Thresholds 1.6706 V (+1V8_DIG) and 2.968 V (+3V3_AUX). Output valid from VDD 0.9 V; VDD = BAT54C OR of +3V3_RF and +5V_PA, minus 0.24 V. Release delay 9.6 ms. **Assert delay `sup_tdet` swept: 0.1, 20, 50, 100 µs.** |
| TPS22810 | tOFF 3.3 µs ± 50 % (1.65 / 4.95 µs); no maximum is specified. |
| New checks (M5) | **M5a:** PG_3V3RF ≤ 0.3 V whenever it is asserted, so the TLV755 EN is guaranteed off. **M5b:** clamped PA_DRAIN_EN < VENF min 1.08 V. **M5c:** clamped IL_CLR_N < LVC VIL (0.35·VCC). **M5d:** TPS386000 sink ≤ 5 mA (abs max). All are SAFETY checks and set the exit code. |

### Results: scenario suite (S1–S7)

- **ASB passes every scenario** in nominal and pessimistic logic, and at every corner: crowbar 0.9 / 1.55 V, DMG1012T 0.5 / 1.0 V, tOFF ± 50 %, supervisor delay 20 / 50 / 100 µs, and the combined slow and overlap corners.
- R2 (the schematic before REC) is shown for comparison.

| Fault | R2 nom: switch open / drain < 0.5 V / PA energy | ASB (nom = pess): switch open / drain < 0.5 V / PA energy / peak PA I | ASB crowbar peak / energy / starts after switch open |
|---|---|---|---|
| S3 gate lost | 4.5 µs / **73.5 µs** / 0.232 mJ | 4.5 µs / 26.3 µs / 0.086 mJ / 0.601 A | 8.5 A / 0.147 mJ / 9.0 µs |
| S4a −5V_BF via ENN | 6.3 µs / **106.0 µs** / 0.235 mJ | 6.3 µs / 29.1 µs / 0.063 mJ / 0.221 A | 9.0 A / 0.174 mJ / 8.7 µs |
| S4b −5V_BF via LDO | 7.1 µs / **106.8 µs** / 0.235 mJ | 7.6 µs / 30.3 µs / 0.063 mJ / 0.221 A | 9.0 A / 0.174 mJ / 8.7 µs |
| S5a watchdog, TX | 3.8 µs / **103.1 µs** / 0.235 mJ | 3.8 µs / 26.8 µs / 0.064 mJ / 0.221 A | 9.0 A / 0.173 mJ / 8.9 µs |
| S5b watchdog, pinched | 3.8 µs / **7.18 ms** / 0.114 mJ | 3.8 µs / 30.3 µs / 0.001 mJ / 0.002 A | 10.4 A / 0.247 mJ / 8.9 µs |
| S6 VIN loss | 4.8 µs / **104.4 µs** / 0.235 mJ | 4.8 µs / 27.2 µs / 0.062 mJ / 0.221 A | 9.1 A / 0.175 mJ / 8.5 µs |
| S7a +3V3_RF via EN | 3.8 µs / **96.0 µs** / 0.235 mJ | 3.8 µs / 25.9 µs / 0.060 mJ / 0.221 A | 9.1 A / 0.177 mJ / 8.0 µs |
| S7b +3V3_RF silent | 3.3 µs / **88.1 µs** / 0.235 mJ | 0.0 µs / 14.4 µs / 0.029 mJ / 0.224 A | 9.0 A / 0.172 mJ / 9.1 µs |

**Corners** (pessimistic logic, worst over the eight fault scenarios):

| Corner | Worst drain < 0.5 V | Worst switch open | Max PA energy | Max crowbar peak | Min crowbar start after switch open | Min crowbar-off before VOUT ramp | Overlap |
|---|---|---|---|---|---|---|---|
| nominal | 30.3 µs | 7.6 µs | 0.086 mJ | 10.4 A | 8.1 µs | 126.3 µs | 0 |
| crowbar VGS(th) 0.9 V | 30.3 µs | 7.6 µs | 0.086 mJ | 10.3 A | 8.0 µs | 126.3 µs | 0 |
| crowbar VGS(th) 1.55 V | 30.5 µs | 7.6 µs | 0.087 mJ | 10.5 A | 8.3 µs | 126.3 µs | 0 |
| DMG1012T 0.5 V | 35.8 µs | 7.6 µs | 0.112 mJ | 10.4 A | 13.5 µs | 129.4 µs | 0 |
| DMG1012T 1.0 V | 26.6 µs | 7.6 µs | 0.066 mJ | 10.4 A | 4.3 µs | 122.5 µs | 0 |
| tOFF −50 % | 30.3 µs | 5.9 µs | 0.094 mJ | 10.3 A | 9.7 µs | 124.7 µs | 0 |
| tOFF +50 % | 30.4 µs | 9.2 µs | 0.078 mJ | 10.3 A | 6.5 µs | 128.0 µs | 0 |
| supervisor 20 / 50 / 100 µs | 30.3 / 30.3 / 30.4 µs | 7.6 µs | 0.086 mJ | 10.4 A | 8.1 µs | 126.3 µs | 0 |
| slow (Q2 0.5 V, crowbar 1.55 V, supervisor 100 µs) | 36.0 µs | 7.6 µs | 0.113 mJ | 10.6 A | 13.7 µs | 129.4 µs | 0 |
| overlap (Q2 1.0 V, crowbar 0.9 V, tOFF +50 %) | 26.6 µs | 9.2 µs | 0.057 mJ | 10.3 A | **2.5 µs** | 124.1 µs | 0 |

**Pulses in the scenarios.**
- Peak PA current is ≤ 0.601 A (the gate-at-0 V assumption), reached only by the faulted PA in S3.
- The crowbar peak rose from 6–7.5 A (revision 2) to **8.5–10.6 A**, because the CSD16301Q2 Ciss of 340 pF makes the gate fast. That is within the CSD16301Q2 IDM of 85 A, and ≈ 3.5 A per RCS1206 resistor.
- Crowbar energy is ≤ 0.248 mJ per event.

**Switch timing.**
- The switch opens ≤ 9.2 µs after the fault in every corner. The 9.2 µs case is tOFF +50 %.
- S4b at nominal tOFF is 7.6 µs. That figure includes the comparator offset on a slow ramp.

### Results: ordering test (920 runs per design, seed 20261112)

| Design / logic | Failing runs | Failures by criterion | VGG max / min | Worst drain < 0.5 V | Worst switch open | Max overlap / min crowbar start |
|---|---|---|---|---|---|---|
| **ASB / nom** | **0** | – | +2 mV / −1.750 V | 34.1 µs | 4.6 µs | 0 / 7.9 µs |
| **ASB / pess** | **635** | M5a 635, T50 101, M5c 53, A 5 | +2 mV / −1.750 V | **50.3 µs** (P497) | 4.6 µs | 0 / 8.0 µs |
| ASB_td20 / pess | 635 | M5a 633, EN 238, (a) 128, T50 104, A 104, M5c 53, CB 2 | +2 mV / −1.750 V | 58.5 µs | 22.4 µs | **1.51 µs** / 8.0 µs |
| ASB_td50 / pess | 635 | M5a 632, EN 242, REF 178, (a) 126, T50 105, A 105, M5c 52, CB 5 | +2 mV / −1.750 V | 77.0 µs | 50.2 µs | **4.03 µs** / 7.4 µs |
| ASB_td100 / pess | 635 | M5a 468, EN 243, REF 178, (a) 124, T50 103, A 103, M5c 53, CB 5 | +2 mV / −1.750 V | 104.1 µs | 50.2 µs | **4.03 µs** / 7.7 µs |
| ASB_slow / pess | 635 | M5a 467, EN 243, REF 190, (a) 124, T50 104, A 104, M5c 59, CB 6 | +2 mV / −1.750 V | 120.8 µs | 50.2 µs | 0.96 µs / 13.7 µs |
| ASB_ovl / pess | 635 | M5a 635, M5c 53 | +2 mV / −1.750 V | 31.8 µs | 6.2 µs | 0 / 2.5 µs |
| R2 / nom (reference) | 666 | A 638, T50 661, REF 16, EN 9, G 6 | +128 mV / −1.750 V | 9.49 ms | 4.8 µs | – |
| FIX / nom (not built) | 0 | – | +2 mV / −1.750 V | 34.1 µs | 4.6 µs | 0 / 5.8 µs |
| FIX / pess (not built) | 76 | EN 47, M5b 33, CB 2 | +2 mV / −1.750 V | 34.1 µs | 4.6 µs | 1.00 µs / 4.7 µs |
| FIX_slow / pess | 243 | EN 243, (a) 124, A 103, T50 103, REF 178, CB 6 | +2 mV / −1.750 V | 114.0 µs | 50.2 µs | 0.96 µs / 8.7 µs |
| FIX_ovl / pess | 379 | M5b 379, EN 223 | +2 mV / −1.750 V | 29.6 µs | 6.2 µs | 0 / 0.2 µs |

### FAILs of the as-built design (all under pessimistic logic; nominal logic passes everything)

1. **M5a. PG_3V3RF is not held ≤ 0.3 V** (635 of 920 ordering runs, all corners).
   - Measured up to **0.661 V** while asserted. Scenario suite worst: 0.222 V, while U650 PGOOD (100 Ω) sinks the clamp current.
   - Cause: while +1V8_DIG is between 1.08 and 1.65 V, the pessimistic U705/U911 outputs drive about 1.1–1.5 mA each through R735/R975 and the BAT54C into PG_3V3RF. When only the TPS386000 sinks (400 Ω pessimistic linearisation), PG sits at about 0.5–0.66 V.
   - **Consequence:** the TLV755 EN is not guaranteed off (VLO is 0.3 V). Nominal logic stays ≤ 0.068 V.
2. **T50 / A. Crowbar inhibited by the clamp itself** (101 runs; worst 50.3 µs, P497: +1V8_DIG lost first during TX).
   - The clamp holds PA_DRAIN_EN at about 0.8–0.97 V. That is above the Q2 VGS(th) (0.75 V nominal), so Q2 stays on and the crowbar fires only once PA_DRAIN_EN has decayed. In P497 that is 38 µs after the switch opened.
   - Overruns are 0.1–0.3 µs at nominal supervisor delay (VOUT 0.52 V at 50 µs). The A failures (5) are the same runs.
   - The DMG1012T 1.0 V corner (ASB_ovl) does not show this.
3. **M5c. IL_CLR_N above LVC VIL by up to 345 mV** (53 runs). Same clamp-level cause. The flop CLR is then not guaranteed in that window. In this model it is pessimistically SET anyway while VCC is invalid.
4. **Supervisor assert delay ≥ 20 µs** (EN, (a), T50, A, REF, CB). Results in the ordering-test table above.
   - With +1V8_DIG falling abruptly (150 mA on 8.4 µF), the pessimistic LVC chain keeps PA_DRAIN_EN high until the TPS386000 asserts.
   - Switch open takes up to 22 µs (20 µs delay) or 50 µs (50 / 100 µs delay). Drain < 0.5 V takes up to 58 / 77 / 104 µs. REF fails from 50 µs.
   - **Crowbar/switch overlap of 1.5–4.0 µs** (shoot-through) occurs in 2–6 runs: Q2 releases on the slowly decaying, clamped PA_DRAIN_EN while the TPS22810 EN is still read as on.
   - The TPS386000 assert delay is "almost immediately" in the datasheet, with tW ≈ 4 µs typical. **0.1 µs is the only value that passes**, so a bench measurement is required.
5. **M5d (sink ≤ 5 mA) passes**, with a maximum of 4.44 mA. These are transient peaks: the 400 Ω pessimistic sink discharging the PG node, plus the clamp currents.
6. **All REF and G checks pass at supervisor delay 0.1 µs.** VGG stays within +2 mV / −1.750 V in every as-built run.

### Candidate fix FIX, evaluated but not built

- **Change:** replace the BAT54C clamps with two DMG1012T clamps on IL_Q3G, and feed R976 from a diode-OR of the supervisor VDD and +1V8_DIG.
- **What it fixes:** M5a (PG ≤ 0.007 V) and the T50 inhibition (worst 34.1 µs).
- **What it introduces:** new pessimistic failures (EN 47, M5b 33, CB 2). The 100 kΩ / 100 pF IL_Q3G node takes several µs to turn the clamp FETs on.
- **Verdict:** not recommended as is. It would need a stiffer IL_Q3G pull-up (≈ 10 kΩ) and re-simulation.

### Limitations specific to revision 3

- **Pessimistic logic is a bound, not a prediction.** Real LVC outputs at VCC 1.1–1.6 V have weak drive, so the real clamp currents are probably far below the pessimistic 1.1–1.5 mA. The M5 failures may then not occur, but the datasheets do not guarantee that.
- **The supervisor VOL is a linearisation** of single test points. A typical part (≈ 80 Ω at 1 mA from the typical curve) would keep PG ≈ 0.15 V.
- **Ordering tests use free-rail mode,** in which +1V8_DIG can collapse abruptly while all other rails stay up. That is the case that drives findings 2 and 4.

---

## Revision 2: idealised REC (superseded by revision 3)

> The tables in this section describe the idealised REC design and the revision 2 runner. The current runner simulates the as-built design (ASB*) and R2 only; `h2c_results.md` now holds the revision 3 results. The "REC" and "C0/C1/CAP/RECnoUV" numbers below are historical.

Revision 1 is kept below as history. Its plot file names no longer exist; the plots were regenerated under the names listed here.

### How to run

`env -u LD_LIBRARY_PATH python3 run_h2c_sim.py` takes about 12 minutes on this host with 48 worker processes; `--quick` runs 82 ordering runs instead of 920.

It writes:
- `h2c_results.md`: every table, event times, and per-check PASS/FAIL with details;
- `h2c_*.png` plots;
- `d_worst_*.cir` netlists for the worst ordering cases, which re-run on their own against `h2c_plant.inc`;
- `h2c_d_runs.json` with all ordering-run metrics.

**Exit code.** The runner exits 1 if any SAFETY check fails for a gating design.
- The gating designs are REC, plus its two Q2 threshold corners, in both nominal and pessimistic logic.
- The current schematic (R2) and the alternatives (C0, C1, CAP, RECnoUV) run through the same checks. Their failures are reported in full, but they do not set the exit code.
- Current result: **exit 0**. REC passes everything. R2 fails, as documented below.

### What changed in revision 2

| Area | Change |
|---|---|
| Schematic (coordinator) | U915 74LVC1G08: IL_EN = NEG_RAILS_OK · PG_3V3RF, with a 100 k pull-down. IL_EN drives the TPS22917 ON pin and U912 input A, so NEG_OK = IL_EN · GATES_OK. |
| PGOOD model | Per SLVSEY5C §7.3.4: low while EN is low, during soft-start, and outside 85–115 %. It is released 1 ms after FB has been inside 90–110 %, and it can sink only while VIN > 1.5 V (ASSUMPTION). |
| LVC supply model | Logic is valid only for +1V8_DIG ≥ 1.65 V (LVC VCC min). **Nominal mode:** below that, outputs are LOW (100 k pull-downs win). **Pessimistic mode:** the output equals VCC (HIGH) and the flop is SET. |
| Pessimistic logic (`pess=1`) | Inputs inside an undefined band read HIGH: LVC above VIL = 0.35·VCC, TPS22917 ON above 0.35 V, TPS22810 EN above VENF min 1.08 V, TLV755 EN above 0.3 V. LM339B outputs float when VS < 2 V, which reads HIGH through the pull-ups (in both modes). |
| Comparators | A 0.5 mV input offset in the late-trip direction (inside LM339B VIO 5.5 mV). It also prevents numerical chatter at equal inputs. Supply-validity windows use exactly the same ratiometric trip points. |
| ADAR1000 | PA_BIAS registers reset: they read 0 V unless AVDD3 has been continuously up since the last firmware write. This is used in the ordering runs. |
| Criteria | The 50 µs drain criterion (**T50**) is a **hard** criterion again. Added: (a) switch open ≤ 10 µs; (b) PA energy ≤ 0.25 mJ per chain and peak PA current ≤ 0.6 A; **G** VGG in −2.0…0 V (+10 mV tolerance) at all times; **EN** no drain switch on while a supply is invalid; **REF** no IL_REF while a supply is invalid; **CB** no crowbar/switch overlap. **A** (drain < 0.5 V when any gate > −1.5 V outside armed TX) is kept. |
| New scenarios | S7a: +3V3_RF lost through PWR_EN_3V3. S7b: +3V3_RF silent collapse with EN high. In both, −5V_BF and −3V3_SW stay up. Also D: arbitrary rail ordering. |
| Candidate hardware | Selected by `.param` in `h2c_plant.inc` and combined into the designs below. |

**Designs simulated**

| Design | Contents |
|---|---|
| **R2** | Current schematic (revision 2 above). |
| **REC** | Recommended. R2 plus: drain crowbar per chain; IL_REF from a TLV75518P on +3V3_RF with LDO EN = PG_3V3RF; dual supervisor (+1V8_DIG 1.67 V, +3V3_AUX 2.97 V) wired onto PG_3V3RF, plus Q3 clamping the TPS22917 ON pin; +3V3_RF UV channel (3.10 V) on NEG_RAILS_OK; IL_REF decoupling 10 nF. |
| **RECq05 / RECq10** | REC at the Q2 VGS(th) corners 0.5 V and 1.0 V. |
| **C0** | R2 plus only the lead's option C: IL_REF LDO on +3V3_RF, EN tied to IN. |
| **C1** | REC, but with the LDO EN tied to IN. |
| **RECnoUV** | REC without the +3V3_RF UV channel and with 100 nF on IL_REF. |
| **CAP** | R2 with drain capacitance cut to 8.8 µF per chain. |

### Results: scenario suite (S1–S7)

| Scenario | R2/nom | R2/pess | REC/nom | REC/pess | C0/pess | C1/pess | CAP/nom | RECq05/pess | RECq10/pess |
|---|---|---|---|---|---|---|---|---|---|
| S1 normal power-up | PASS | **FAIL** EN,G,REF | PASS | PASS | **FAIL** EN | PASS | – | – | – |
| S2 MCU_PA_EN with unprogrammed / unpinched gates | PASS | **FAIL** EN,G,REF | PASS | PASS | **FAIL** EN | PASS | – | – | – |
| S3 gate lost during TX | **FAIL** A,T50 | **FAIL** A,EN,G,REF,T50 | PASS | PASS | **FAIL** A,EN,T50 | PASS | PASS | PASS | PASS |
| S4a −5V_BF collapse via ENN | **FAIL** A,T50 | **FAIL** A,EN,G,REF,T50 | PASS | PASS | **FAIL** A,EN,T50 | PASS | – | PASS | PASS |
| S4b −5V_BF collapse via LDO disable | **FAIL** A,T50 | **FAIL** A,EN,G,REF,T50 | PASS | PASS | **FAIL** A,EN,T50 | PASS | – | PASS | PASS |
| S5a watchdog during TX + recovery | **FAIL** A,T50 | **FAIL** A,EN,G,REF,T50 | PASS | PASS | **FAIL** A,EN,T50 | PASS | PASS | PASS | PASS |
| S5b watchdog, armed, gates pinched | **FAIL** T50 | **FAIL** EN,G,REF,T50 | PASS | PASS | **FAIL** EN,T50 | PASS | **FAIL** T50 | PASS | PASS |
| S6 VIN_12V loss during TX | **FAIL** A,T50 | **FAIL** A,EN,G,PA_DRAIN_EN,REF,T50 | PASS | PASS | **FAIL** A,EN,PA_DRAIN_EN,REF,T50 | PASS | PASS | PASS | PASS |
| S7a +3V3_RF lost via EN (neg rails up) | **FAIL** A,T50 | **FAIL** A,EN,G,REF,T50 | PASS | PASS | **FAIL** A,EN,T50 | PASS | – | PASS | PASS |
| S7b +3V3_RF silent collapse (neg rails up) | **FAIL** A,T50 | **FAIL** A,EN,G,REF,T50 | PASS | PASS | **FAIL** A,EN,T50 | PASS | – | PASS | PASS |

### Fault response: R2 (nominal) against REC (pessimistic)

All times are measured from the moment the fault crosses its threshold.

| Fault | R2: switch open / drain < 0.5 V / PA energy | REC: switch open / drain < 0.5 V / PA energy | REC: crowbar peak current / energy | REC at Q2 VGS(th) = 0.5 V: drain < 0.5 V |
|---|---|---|---|---|
| S3 gate lost | 4.5 µs / **73.5 µs** / 0.232 mJ | 4.5 µs / 27.4 µs / 0.089 mJ | 6.0 A / 0.144 mJ | 31.4 µs |
| S4a −5V_BF via ENN | 6.3 µs / **106.0 µs** / 0.235 mJ | 6.4 µs / 30.4 µs / 0.065 mJ | 6.4 A / 0.171 mJ | 34.5 µs |
| S4b −5V_BF via LDO | 7.1 µs / **106.8 µs** / 0.235 mJ | 7.6 µs / 31.6 µs / 0.065 mJ | 6.4 A / 0.171 mJ | 35.8 µs |
| S5a watchdog, TX | 3.8 µs / **103.1 µs** / 0.235 mJ | 3.8 µs / 27.9 µs / 0.066 mJ | 6.4 A / 0.170 mJ | 32.1 µs |
| S5b watchdog, gates pinched | 3.8 µs / **7.18 ms** / 0.114 mJ | 3.8 µs / 31.9 µs / 0.001 mJ | 7.5 A / 0.246 mJ | 36.4 µs |
| S6 VIN loss | 4.9 µs / **104.4 µs** / 0.235 mJ | 5.0 µs / 29.2 µs / 0.067 mJ | 6.4 A / 0.170 mJ | 33.4 µs |
| S7a +3V3_RF via EN | 3.8 µs / **96.0 µs** / 0.235 mJ | 3.8 µs / 28.0 µs / 0.066 mJ | 6.4 A / 0.170 mJ | 32.1 µs |
| S7b +3V3_RF silent | 3.3 µs / **88.1 µs** / 0.235 mJ | 0.0 µs* / 15.6 µs / 0.031 mJ | 6.4 A / 0.169 mJ | 19.7 µs |

\* In S7b the 3.10 V +3V3_RF UV channel trips before the 85 % PGOOD threshold, which is the fault reference here.

- **Peak PA current** is ≤ 0.601 A in every case. That is the gate-at-0 V assumption, reached only by the faulted PA in S3; the others peak at 0.221–0.274 A.
- **Gate drift.** No gate reaches −0.15 V before the drain is below 0.5 V. The first gate reaches −0.15 V 1.22–1.82 ms after the fault, in S4, S6 and S7.

### Results: D, arbitrary rail ordering (free-rail mode)

**Method**
- The 6 major rails are independent ramps: +3V3_AUX, +1V8_DIG (always ≤ AUX − 0.15 V), +3V3_RF, +5V_PA, −5V_BF and −3V3_SW. Ramp times are random within 0.1–5 ms.
- **720 runs** cover every permutation of the start order. Each is paired with a shuffled permutation of the shutdown order, so every shutdown order also appears once.
  - Gaps between rails are random, and 15 % are zero, so rails also rise simultaneously.
  - Firmware does pinch → arm → TX, and shutdown begins during TX, so a rail fails mid-operation.
- **200 random runs** randomise everything:
  - per-rail on/off/re-on times;
  - VIN loss, which also takes +3V3_RF, +5V_PA and +3V3_AUX with it;
  - firmware writes (−1.75 / −1.1 / 0 V, including a single-gate 0 V write), MCU_PA_EN pulses at any time, and watchdog drops;
  - one proper arming sequence at a random, possibly too early, time.
- Seed 20261112. 920 runs per design and logic mode.

**Per-run criteria:** G, A, T50, (a), (b), EN, REF and CB, as defined above.

| Design / mode | Failing runs (of 920) | Failures by criterion | Worst VGG max | Worst VGG min | Worst drain < 0.5 V after fault | Worst switch-open | Crowbar overlap / min break-before-make |
|---|---|---|---|---|---|---|---|
| **REC / nom** | **0** | – | +2 mV | −1.750 V | 39.0 µs (R180) | 4.6 µs | 0.00 µs / 7.4 µs |
| **REC / pess** | **0** | – | +2 mV | −1.750 V | 39.0 µs (R180) | 4.6 µs | 0.00 µs / 7.6 µs |
| R2 / nom | 666 | A 638, EN 9, G 6, REF 16, T50 661 | **+128 mV** (R071) | −1.750 V | 9.49 ms (R069) | 4.8 µs | – |
| R2 / pess | 916 | (a) 190, (b) 1, A 753, EN 914, G 547, REF 915, T50 663 | **+566 mV** (P190) | −1.750 V | 9.49 ms | 46.9 µs | – |
| C1 / pess (LDO EN = IN) | 3 | REF 3 | +2 mV | −1.750 V | 39.0 µs | 4.6 µs | 0.00 µs / 7.6 µs |
| C0 / pess (option C alone) | 915 | (a) 190, A 753, EN 914, G 186, REF 783, T50 663 | **+628 mV** (P561) | −1.750 V | 9.49 ms | 46.9 µs | – |
| RECnoUV / pess | 4 | G 3, REF 4 | **+123 mV** (R192) | −1.750 V | 39.0 µs | 4.6 µs | 0.00 µs / 7.6 µs |

**Worst-case waveforms**

| Design / mode | Netlist | Plot | Cases |
|---|---|---|---|
| REC, nominal and pessimistic | `d_worst_REC_{nom,pess}_{gmax,gmin,t05}.cir` | `h2c_d_worst_REC_*.png` | – |
| R2 | `d_worst_R2_*.cir` | `h2c_d_worst_R2_*.png` | nominal R071: +128 mV; pessimistic P190: +566 mV |

- **VGG minimum.** −1.750 V in every run, because firmware never writes below −1.75 V. The −2.0 V abs-max limit is protected by firmware only (INTERLOCK_SPEC R4).
- **The REC worst T50 case (R180, 39.0 µs)** used the nominal Q2. At the Q2 = 0.5 V corner the scenario suite shows about +4.5 µs, so the expected worst case is ≈ 43.5 µs. That is below 50 µs with about 6 µs margin. The ordering runs were not repeated at the Q2 corners.

### A. The 73–111 µs discharge, and the crowbar

**Why R2 fails T50.**
- The interlock itself is fast. The TPS22810 is open 3.3–7.6 µs after the threshold crossing.
- Discharging the 19.81 µF per chain takes longer:
  - with the gates biased, the PAs draw 0.9–1.3 A, which takes 73–107 µs;
  - with the gates pinched, there is no PA current and the QOD alone (400 Ω) has τ = 7.9 ms, which takes 7.18 ms.
- Required discharge: 5 V → 0.5 V is 2.3 τ.
- With the budget of 50 µs − 1.3 µs (comparator) − 13 µs (break-before-make delay, worst corner) − 2 µs (crowbar gate rise) − 5 µs margin ≈ 29 µs:
  - τ ≤ 12.5 µs, i.e. **R_total ≤ 0.63 Ω** for 19.81 µF.
  - "≈ ≤ 1 Ω" holds only with no switch-to-crowbar delay.
- The simulated design uses **0.38 Ω** (0.33 Ω pulse resistor plus ≤ 50 mΩ Rds(on)).

**Crowbar topology (per chain).**
- N-MOSFET Q_CB from +5V_PA_C{c} (VOUT) through a 0.33 Ω resistor to GND.
- Its gate is pulled up by **4.7 kΩ from +5V_PA, the TPS22810 VIN side**.
- Q2, a small N-MOSFET, holds the gate low whenever PA_DRAIN_EN is high. Q2's gate is fed from PA_DRAIN_EN through **10 kΩ / 1 nF**.
- **Break-before-make on fault.**
  - PA_DRAIN_EN falls → the TPS22810 is off after 3.3 µs.
  - Q2's gate decays from 1.8 V to VGS(th) in 5.9–12.9 µs (τ = 10 µs).
  - Q_CB's gate then rises through 4.7 kΩ / 1 nF.
  - Simulated: **the crowbar conducts 7.3–7.9 µs after the switch is fully off** (nominal Q2), and **4.3–4.6 µs** at Q2 VGS(th) = 1.0 V. Overlap is 0.00 µs in all 920 × 7 runs and all scenarios.
- **Make-before-break on arm.**
  - PA_DRAIN_EN rises → Q2 on after ≤ 7.5 µs → the crowbar is off.
  - The TPS22810 output starts rising only after tD ≈ 130 µs, so the crowbar is off **128 µs before VOUT starts rising**.
- **Pulse.**
  - Simulated peak 5.5–7.5 A (the gate ramps while VOUT falls). The theoretical maximum is 13 A at 5.18 V / 0.38 Ω.
  - Crowbar energy is ≤ 0.248 mJ per event, i.e. ≤ ½·C·V² = 0.25 mJ.
  - Hold current while armed: 5 V / 4.7 kΩ = 1.1 mA per chain.
- **PA energy after the switch opens** falls from 0.232–0.235 mJ (R2) to **0.031–0.110 mJ** (REC).
- **Gate safety.** In every REC fault the drain is below 0.5 V (15.6–36.4 µs) long before any gate passes −0.15 V. Gates first reach −0.15 V at ≥ 1.25 ms in S4, S6 and S7; in S3 the gate itself is the fault.
- **Default ON with logic absent.**
  - If +1V8_DIG or +3V3_AUX is absent, R965 holds PA_DRAIN_EN at 0, Q2 is off, and the crowbar gate is at +5V_PA. The drain is clamped whenever +5V_PA exists.
  - There is no shoot-through, because the TPS22810 EN is the same PA_DRAIN_EN net, which is low.
  - A gate pull-up from VOUT itself was **rejected**: VGS would equal VOUT, so the crowbar turns itself off once VOUT drops to about Vth + 0.3 V and can never reach 0.5 V. It would also be unable to hold a node it has already discharged.
- **Residual risk.**
  - The TPS22810 tOFF has a typical value only (3.3 µs) and no maximum. Shoot-through would need tOFF > ~7.6 µs at the Q2 = 1.0 V corner.
  - The tD minimum is also unspecified; tD would have to fall below ~8 µs to cause overlap on arming.
  - Measure both on the bench, or raise the Q2 RC. Every +1 µs of delay costs about +1 µs on T50.

**Alternative: reduce the drain capacitance (CAP, 8.8 µF per chain, nominal logic).**

| Scenario | Drain < 0.5 V after fault |
|---|---|
| S3 | 35.2 µs |
| S5a | 48.0 µs |
| S6 | 49.1 µs (marginal) |
| S5b (gates pinched) | **3.19 ms** – FAIL |

- With pinched gates there is no PA current, so only an active discharge can meet 50 µs. Capacitance reduction alone cannot fix it.
- Going to 8.8 µF also means dropping ADI's Stingray **4.7 µF per ADTR1107 VDD_PA** (A5) to about 2 µF per PA. That is a deviation from the ADI-recommended decoupling, with unknown RF and stability impact.
- **Not recommended.** The 4 × 4.7 µF are kept in REC.

### B. Pessimistic logic

**R2 (current schematic) fails under pessimistic logic:**
- S1: VGG reaches +558 mV at 3.29 ms.
- D: 916 of 920 runs fail, with a worst VGG of +566 mV.
- Mechanism: while +1V8_DIG is between 0.8 and 1.65 V (ramp, brown-out or decay), U915, U912, U911 and U705 are undefined and taken as HIGH. So IL_EN turns the TPS22917 on (with VIN = +1V8_DIG) while the ADAR1000 is unpowered. PA_DRAIN_EN (≤ VCC, but above VENF 1.08 V) also enables the TPS22810, and the flop's undefined state is "armed".
- Under nominal logic R2 passes S1/S2 and the A1 injection (rev 1 finding 2) is fixed by U915 (+2 mV). In D, however, R2 nominal still reaches **+128 mV** (R071) when +3V3_RF collapses faster than IL_EN + TPS22917 tOFF can remove IL_REF.

**The minimal set that passes everywhere is REC.** Each element is needed:
- **Supervisor on the PG_3V3RF net.**
  - It senses +1V8_DIG and +3V3_AUX and is powered from +3V3_RF / +5V_PA, so it is alive whenever there is something to protect.
  - It replaces "logic decides" with an open-drain pull-down that is valid in the band where the LVC logic is not.
  - Through BAT54C diodes it clamps PA_DRAIN_EN and IL_CLR_N, and it disables the IL_REF LDO.
- **Q3 on the TPS22917 ON pin.** The LDO output cap (1 µF, 120 Ω pull-down) decays slowly (τ = 120 µs). Without Q3, a pessimistic IL_EN leaks up to 0.49 V of IL_REF while +1V8_DIG is invalid.
- **+3V3_RF UV channel at 3.10 V, plus IL_REF ≤ 10 nF.** Without them (RECnoUV) VGG reaches +123 mV in 3 random runs where +3V3_RF collapses abruptly (4 A on 188 µF, about 20 mV/µs). The ADAR1000 is assumed to go high-Z at 2.8 V before the 85 % PGOOD + TPS22917 tOFF chain has removed IL_REF.
- **Residual (ordering only, not a safety criterion).** U913 ENN is still LVC logic. Under pessimistic logic it pulses HIGH while +1V8_DIG < 1.65 V (S1/pess INFO line). The TPS65131 stays off in the simulated cases because +3V3_AUX < 2.35 V UVLO at that time. With a +1V8_DIG-only fault and AUX healthy, the negative rails could start before PG_3V3RF. If that matters, drive ENN from PG_3V3RF directly (open-drain AND) instead of U913.

### C. IL_REF from +3V3_RF through a TLV75518P

| Variant | Result | Reason |
|---|---|---|
| **C0**: R2 + LDO on +3V3_RF, EN tied to IN, under pessimistic logic | Fails broadly (+628 mV) | The LDO output exists for +3V3_RF ≳ 1.3 V, i.e. below the 2.8 V at which the ADAR1000 is assumed to drive PA_BIAS. The pessimistic IL_EN then puts that onto the gate dividers. |
| **C1**: all REC fixes, but EN = IN | 3 REF failures | IL_REF reaches 0.36–0.50 V for ~20–35 µs while a supply is already invalid. |
| **REC**: LDO EN = PG_3V3RF (the supervisor-qualified net) | 0 failures | IL_REF can exist only when +3V3_RF has been ≥ 90 % for ≥ 1 ms and +1V8_DIG and +3V3_AUX are good, regardless of the 1.8 V logic state. |

**Recommendation:** source IL_REF this way, but drive the LDO EN from PG_3V3RF, not from IN.

### D/E. Worst cases

| Quantity | REC (all 920 runs × 2 logic modes, all scenarios) | R2 nominal | R2 pessimistic |
|---|---|---|---|
| VGG max | **+2 mV** (PA_BIAS 0 V through 100 Ω with the divider injection) | +128 mV | +566 mV |
| VGG min | −1.750 V | −1.750 V | −1.750 V |
| Drain < 0.5 V after fault | 39.0 µs ordering runs; 36.4 µs scenarios at the Q2 0.5 V corner | 9.49 ms | 9.49 ms |
| Switch open after fault | 4.6 µs ordering runs; 7.6 µs scenarios (S4b) | 4.8 µs | 46.9 µs |

### Recommended hardware changes (for the schematic)

Per chain c = 1…4:
1. **Q_CB{c}, drain crowbar, N-MOSFET.**
   - Requirements: VDS ≥ 20 V; RDS(on) ≤ 50 mΩ at VGS = 4.5 V; VGS(th) 1–2 V; Ciss ≤ ~1 nF; pulsed ID ≥ 20 A for 10 µs; SON or SOT package.
   - Connections: drain → **R_CB{c} 0.33 Ω** (1206, pulse / anti-surge rated, 0.25 mJ per event, ≤ 13 A peak) → **+5V_PA_C{c}** (TPS22810 VOUT). Source → GND. Gate → net CB_G{c}.
   - Candidate to evaluate: a TI NexFET in the CSD17578Q3A class. Verify Ciss, VGS(th) and SOA.
2. **R_CBPU{c} 4.7 kΩ** from **+5V_PA** (TPS22810 VIN side) to CB_G{c}.
3. **Q2_{c}, small-signal N-MOSFET.**
   - Requirements: VDS ≥ 12 V; VGS(th) between 0.5 and 1.0 V (both corners simulated); must be fully on at VGS = 1.7 V.
   - Connections: drain → CB_G{c}; source → GND; gate → CB_D{c}.
4. **R_CBD{c} 10 kΩ** from PA_DRAIN_EN to CB_D{c}, and **C_CBD{c} 1 nF C0G** from CB_D{c} to GND.

Once:

5. **Dual voltage supervisor.**
   - **VDD:** diode-OR of +3V3_RF and +5V_PA through one BAT54C, plus 100 nF. The output must be valid down to VDD ≈ 0.9 V (model assumption; verify).
   - **SENSE1:** +1V8_DIG, threshold 1.67 V.
   - **SENSE2:** +3V3_AUX, threshold 2.97 V.
   - tRST ≈ 10 ms.
   - **Open-drain RESET_N → PG_3V3RF net**, as a wired-AND with U650 PGOOD. Keep the existing 100 kΩ pull-up to +1V8_DIG.
   - **Second output, active-high** (push-pull, or open-drain with 100 kΩ to the supervisor VDD) → gate of Q3.
   - Candidate families to evaluate: TI TPS3779/TPS3780 (dual) or TPS386000 (quad). Verify the output types, the low-VDD output validity and the threshold options.
6. **Q3, small N-MOSFET** (same type as Q2). Drain → TPS22917 ON pin; source → GND; gate → supervisor active-high output. Insert **10 kΩ** in series between U915 Y (IL_EN) and the TPS22917 ON pin. U912 A stays on IL_EN directly.
7. **BAT54C** (common cathode). Cathode → PG_3V3RF; anode 1 → PA_DRAIN_EN; anode 2 → IL_CLR_N.
   - Insert **1 kΩ** in series between U705 Y and PA_DRAIN_EN, and between U911 Y and IL_CLR_N. R965 stays on PA_DRAIN_EN.
   - With PGOOD sinking about 3.2 mA, the estimated clamp level is ≤ 0.5 V. That is below VENF min 1.08 V and below LVC VIL 0.58 V. Verify the PGOOD VOL at that current.
8. **IL_REF LDO: TLV75518PDBV** (same part as U653).
   - IN = +3V3_RF, with 1 µF. **EN = PG_3V3RF.** OUT → new net IL_REF_SRC, with 1 µF.
   - IL_REF_SRC feeds the TPS22917 VIN instead of +1V8_DIG.
   - IL_REF decoupling: **≤ 10 nF**.
9. **+3V3_RF UV channel on the spare LM339B channel of U908.**
   - Pin 10 (−) → IL_REF_N5V; pin 11 (+) → new net IL_RFMON; pin 13 → **NEG_RAILS_OK**. This replaces the spare-channel tie-offs of pins 10 and 11.
   - Divider: **49.9 kΩ 0.1 %** from +3V3_RF to IL_RFMON, and **10.2 kΩ 0.1 %** from IL_RFMON to GND.
   - Trip point: 3.10 V nominal, 3.07–3.13 V with +1V8_DIG ±1 %. That is above the assumed ADAR1000 PA_BIAS high-Z point (2.8 V) and below +3V3_RF min (3.229 V).

### Revision 1 findings: before and after

| Revision 1 finding | Revision 2 status |
|---|---|
| 1. 50 µs drain target missed (73–111 µs; QOD-only case 7.2 ms) | R2: still fails (hard criterion). **REC: 15.6–36.4 µs in all scenarios, 39.0 µs worst over 1840 ordering runs.** |
| 2. VGG +628 mV during AUX ramp (IL_REF glitch) | R2 nominal: fixed by U915 (+2 mV in S1). R2 pessimistic: +558 mV (S1), +566 mV (D). R2 nominal in D: +128 mV on abrupt +3V3_RF loss. **REC: +2 mV in every case.** |
| 3. S6 NEG_RAILS_OK / NEG_OK re-glitch after AUX collapse | R2: IL_EN/NEG_OK still return HIGH at 142.551 ms (INFO line), but IL_REF and the drain stay off (latch). **REC: PG_3V3RF is held low by the supervisor (AUX < 2.97 V), and Q3, the LDO EN and the BAT54C clamps make it irrelevant.** |
| 4. GATES_PINCHED / GATES_OK meaningless while IL_REF is off | Unchanged by design. In REC this state is always accompanied by PG_3V3RF low. |
| 5. +5V_PA bulk stays charged after VIN loss | Unchanged. The crowbar pull-up from +5V_PA uses this charge to keep the drain clamped. |
| +3V3_RF fails while −5V_BF/−3V3_SW are up (new) | R2: drain < 0.5 V at 88–96 µs (T50 FAIL), and the gates stay negative for 1.2 ms. **REC: 15.6–28.0 µs, VGG ≤ +2 mV.** |

### Additional assumptions and limitations of revision 2

- **ADAR1000 at AVDD3 collapse.** PA_BIAS is assumed high-Z below AVDD3 = 2.8 V, with no datasheet basis. The REC margin relies on the 3.10 V UV channel tripping first. If the real part goes high-Z above about 3.0 V, re-check.
- **Free-rail mode (D).** It bypasses the regulator models: rails are ideal sourcing ramps with real caps and loads but no discharge. The −5V_BF and −3V3_SW rails are allowed even without +3V3_AUX, which is a superset of physical behaviour. VIN loss in the random runs is an instant step.
- **Supervisor.** Modelled as ideal and instantaneous (no propagation delay) once VDD ≥ 0.9 V. A real supervisor adds tens of µs of detection delay on +1V8_DIG / +3V3_AUX faults. The drain path does not depend on it in the scenarios (the LM339 UV channels trip first), but the REF/G margins in ordering cases with an abrupt +1V8_DIG loss do.
- **Datasheet values not specified.** TPS22810 tOFF max and tD min; MOSFET VGS(th)/Ciss spread beyond the two simulated Q2 corners; MLCC DC-bias derating (nominal capacitance used, which is pessimistic for T50).
- **Comparator offset.** Fixed at 0.5 mV (real LM339B VIO is up to ±5.5 mV). On slow rail ramps this shifts the fault time, not the reaction time measured from the actual trip.
- **The 1.8 V "invalid" band** uses VCC < 1.65 V. Ideal behaviour is assumed below 0.8 V (an LVC output cannot exceed VCC, so the TPS22810 cannot be enabled below 1.08 V).

---

# Revision 1 (superseded; kept for traceability)

The plots referenced below were replaced by the revision 2 plots (`h2c_<scenario>_<design>_<mode>.png`). The netlists are unchanged except for added stimulus nodes.


**Evidence class: BEHAVIOURAL SIMULATION, using datasheet timing. This is not device-level verification.**

- No vendor SPICE model runs in ngspice. The TI models are PSpice/TINA-encrypted, and ADI ships none for ADAR1000/ADTR1107.
- Every IC is therefore modelled from its datasheet numbers as B-sources, switches, ramps, ideal delay lines or an XSPICE flip-flop.
- The results show whether the **architecture and timing** in POWER_SPEC / INTERLOCK_SPEC / AMENDMENTS behave as intended. They do not prove that the real parts do.
- No KiCad file was touched.

### Files

| File | What |
|---|---|
| `h2c_plant.inc` | shared behavioural model: power tree, amended interlock, chain 1 (1 ADAR1000 + 4 ADTR1107 + TPS22810) |
| `s1_powerup.cir` … `s6_vin_loss.cir` | one netlist per scenario. Stimulus only, each `.include`s the plant. 4 and 5 are split into a/b. |
| `run_h2c_sim.py` | re-runs every scenario through `ngrun.py` (libngspice), extracts event times, checks the criteria, writes `h2c_results.md` and `h2c_*.png`. It **exits 1 if any criterion fails** (it currently does). |
| `h2c_results.md` | generated tables: event times and PASS/FAIL per check |
| `h2c_<scenario>.png`, `h2c_<scenario>_zoom.png` | rails / interlock logic / gates / drain voltage and PA currents |

Run it with `env -u LD_LIBRARY_PATH python3 run_h2c_sim.py`. It takes about 40 s.

### What is modelled (amended design)

- **Power chain.**
  - VIN_12V feeds the TPS62933, which makes +3V3_AUX and +1V8_DIG (via the TLV75518P).
  - The MCU then drives PWR_EN_3V3 and PWR_EN_5VPA into the two TPS568230s (+3V3_RF_SRC and +5V_PA).
  - **ENN = PWR_EN_NEG · PG_3V3RF (U913, amendment A2)** enables the TPS65131. Its PWR_VNEG feeds two TPS7A3301s, giving −5V_BF and −3V3_SW.
- **Interlock (INTERLOCK_SPEC + A1).**
  - The rail comparators (−5V_BF, −3V3_SW and the +3V3_AUX UV channel) sit on +1V8_DIG and drive **NEG_RAILS_OK**.
  - NEG_RAILS_OK enables a TPS22917 that switches +1V8_DIG onto **IL_REF**.
  - The gate dividers and the LOST/PINCH references sit on IL_REF.
  - The gate-lost comparators drive **GATES_OK**. **NEG_OK = NEG_RAILS_OK · GATES_OK** (U912).
  - U911 forms IL_CLR_N. The RC/Schmitt stage delays the clock, and the LVC1G74 latch outputs PA_ARMED.
  - U705 forms PA_DRAIN_EN, with R965 as its pull-down. PA_DRAIN_EN drives the TPS22810, which drives the chain drain node (VOUT = VDD_PA).
- **Chain 1 in detail.** All 4 gates are modelled. The other 12 gates are identical and wired-OR, so they are not simulated. The other 3 chains appear only as a 3× mirror of chain 1's current on +5V_PA.

### Parameters and sources

| Block | Value used | Source |
|---|---|---|
| VIN_12V | 0→12 V in 1 ms; loss 12→0 V in 1 ms | brief / assumption (bench supply) |
| TPS62933 (+3V3_AUX) | start VIN > 8 V, stop < 7 V; tSS 4.8 ms; 3.328 V; COUT 3×22 µF; loads 0.2 A + 1V8 + TPS65131 input | POWER_SPEC (UVLO divider, Eq 6) |
| TLV75518P (+1V8_DIG) | UVLO 1.30 V rising / 1.26 V falling; tSTR 0.55 ms; 120 Ω pull-down when off; 8.4 µF; 150 mA | TLV755P p6, POWER_SPEC; caps from A4 MCU decoupling |
| MCU GPIO | valid only for +1V8 > 1.65 V, else low (100 k pull-downs) | ASSUMPTION (STM32 PDR) |
| TPS568230 ×2 | EN 1.31 V; UVLO 3.8 V; 0.6 ms MODE read + 2.64 ms SS; PG 1 ms after 90 %; 420 Ω discharge when off; 188 µF / 235 µF | POWER_SPEC, SLVSEY5C p5–p17 |
| +3V3_RF load | 4 A resistive (full budget, from the start) | POWER_SPEC (pessimistic for decay) |
| TPS65131 | ENN VIH 1.4 V; UVLO 2.35 V typ; ~1 ms start-up; −6.344 V; high-Z when off; η 77 %; 38.8 µF | SLVS493E p5/§7.3.5/§7.3.4, POWER_SPEC |
| TPS7A3301 ×2 | EN = IN (on at \|VIN\| ≥ 2 V); SS 1.2 ms/nF × 100 nF = 120 ms, linear; dropout 0.2 V; no discharge; 47 µF | SBVS169D Eq 1, p6, POWER_SPEC |
| −5V_BF load | 4 ADAR1000 × 50 mA, constant current (fades below 1 V) | brief (worst case) |
| −3V3_SW load | 5 mA | POWER_SPEC |
| Interlock resistors / thresholds | as INTERLOCK_SPEC §3 / §9 (R900…R967) | INTERLOCK_SPEC |
| LM339B | ideal, 1.3 µs delay, active only for +3V3_AUX > 2 V (VS min); outputs float below that | SLCS006Z p6/p12 |
| NEG_RAILS_OK / GATES_OK / GATES_PINCHED pull-up | 10 k from +3V3_AUX, 10 k to GND, 50 pF | INTERLOCK_SPEC deviation 1, A1 |
| TPS22917 (IL_REF) | EN threshold 0.675 V (midpoint of VIL 0.35 / VIH 1.0 V); tON 200 µs (≈100 µs delay + tR 100 µs) at VIN 1.8 V, CT open; tOFF 10 µs; QOD 150 Ω tied to VOUT; 100 nF on IL_REF | SLVSDW8B §7.3, §7.5, §7.6; QOD wiring and 100 nF are ASSUMPTIONS |
| LVC1G08/11/17/74 | ideal; input threshold VCC/2; unpowered below 1.5 V; CLK RC 10 k/1 nF, Schmitt 0.95 V; d_dff tpd 13–14 ns | INTERLOCK_SPEC §4 |
| TPS22810 | EN 1.18 V; tOFF 3.3 µs; at VIN 5 V tD ≈ 134 µs and tR ≈ 186 µs (interpolated between the 3.3 V and 12 V rows) → linear 5 V/232 µs; Ron 79 mΩ; QOD RPD **400 Ω** (worst of 250–400 Ω), active only for VIN > 2.7 V | SLVSDH0C p6–p7, CT = 2200 pF rows |
| Drain decoupling per chain | 4×4.7 µF + 1 µF + 10 nF + 100 pF = 19.81 µF (nominal, no DC-bias derating) | AMENDMENTS A5 |
| ADAR1000 PA_BIAS | output = clip(DAC, AVDD1, 0) behind 100 Ω; high-Z when +3V3_RF < 2.8 V; 0 V after power-up reset | brief ASSUMPTION; ADAR1000 p41 (reset 0 V); 100 Ω and 2.8 V are ASSUMPTIONS |
| ADTR1107 gate | 10 nF (VGG_PA cap) + gate diode clamp to GND (≈ +0.6 V) | A5; diode is an ASSUMPTION |
| ADTR1107 drain current | Id = Idss(Vg) · tanh(Vds / 0.5 V); Idss: 0 A at ≤ −1.75 V, 0.22 A at −1.1 V, **0.6 A at 0 V**, linear in between | ADTR1107/ADAR1000 p45 (220 mA at −1.1 V); 0.6 A and the 0.5 V knee are ASSUMPTIONS |
| Firmware timeline | MCU boots at 8 ms and asserts PWR_EN_3V3 / 5VPA / NEG together (NEG deliberately early). PA_BIAS −1.75 V at 140.0 ms. MCU_PA_EN at 140.2 ms. Gates −1.1 V (TX) at 141.0 ms. | brief; INTERLOCK_SPEC §4 firmware rule |

### Safety criterion and how it is checked

> PA drain voltage < 0.5 V whenever any gate is above −1.5 V (except during normal TX after arming) and within 50 µs of any interlock fault.

The checker implements it as two rules:

- **A.** VOUT > 0.5 V while max(gate) > −1.5 V is a violation, unless it falls inside an allowed window:
  - a firmware TX window, from the gate-raise event until the fault;
  - a 50 µs grace window after a fault.
- **B.** After each fault, VOUT must be < 0.5 V at t_fault + 50 µs and must stay below it until the next legitimate re-arm.

The fault time is the moment the monitored quantity crosses its interlock threshold:
- gate > −0.15 V;
- −5V_BF > −4.6 V;
- WDT_OK falling;
- for VIN loss, the first monitored threshold, which is +3V3_AUX < 2.97 V.

### Results (from `h2c_results.md`)

| Scenario | Interlock response (fault → PA_DRAIN_EN low) | VOUT < 0.5 V after fault | Result |
|---|---|---|---|
| S1 normal power-up | — | — | **FAIL** (only the positive-gate check; the sequencing checks pass) |
| S2 MCU_PA_EN with gates at 0 V, then with gates at −1.1 V | never arms | drain never rises | PASS |
| S3 gate lost (PA_BIAS1 −1.1 → 0 V, TX) | +1.2 µs; switch open at ≈ +4.5 µs | **+73.5 µs** (1.93 V at +50 µs) | **FAIL (B)** |
| S4a −5V_BF collapse via ENN | rail trip 381 µs after ENN↓; PA_DRAIN_EN low +7.9 µs* | **+111 µs** | **FAIL (B)** |
| S4b −5V_BF collapse via LDO disable | rail trip 93 µs after disable; +3.8 µs* | **+107 µs** | **FAIL (B)** |
| S5a watchdog during TX + recovery | +0.5 µs | **+103 µs** | **FAIL (B)**. Recovery behaves correctly. |
| S5b watchdog while armed but idle (gates −1.75 V) | +0.5 µs | **+7.18 ms** (QOD only) | **FAIL (B)** |
| S6 VIN_12V loss during TX | AUX UV trips 442 µs after VIN starts falling; +1.6 µs | **+104 µs** | **FAIL (B + fail-safe level)** |

\* The rail comparator is ratiometric to +1V8_DIG. In the model +1V8_DIG sits at 1.797 V, so the trip moves to about −4.58 V. The extra microseconds are this threshold offset on a slow ramp, not logic delay.

### What passes

- **Sequencing (S1).**
  - +3V3_RF (AVDD3 / VDD_SW) reaches 90 % at 11.0 ms. −3V3_SW reaches −10 % at 24.3 ms and −5V_BF at 24.3 ms, so AVDD3 → AVDD1 (ADAR1000 p13) and VDD_SW → VSS_SW (ADTR1107 p24) hold with a 13 ms margin.
  - ENN rises at 11.98 ms, exactly at PG_3V3RF, even though PWR_EN_NEG was asserted at 8 ms. U913 does its job.
  - −5V_BF passes −4.6 V at 122.8 ms. NEG_RAILS_OK and IL_REF are up at 122.8 ms.
  - Arming: all gates are below −1.5 V at 140.0025 ms. PA_ARMED and PA_DRAIN_EN rise at 140.2095 ms (9.5 µs clock delay). The drain passes 0.5 V at 140.368 ms and 4.5 V at 140.554 ms. The gates rise to −1.1 V only at 141.0 ms.
  - The drain never rises while a gate is above −1.5 V outside TX. TX current is 0.885 A per chain.
  - Info: −3V3_SW and −5V_BF come from the same TPS65131 with the same SS, so they ramp together. ADAR1000 p44 lists −3.3 V before −5 V; the simulated lead is only 89 µs.
- **Unprogrammed gates (S2).**
  - With the gates at reset 0 V, GATES_OK is low, so NEG_OK and IL_CLR_N are low. The latch is held clear.
  - With the gates programmed ON (−1.1 V) but not pinched, GATES_PINCHED is low, so the clock edge latches D = 0.
  - The drain stays at 0 V throughout.
- **Latching.**
  - S3: after PA_BIAS1 is restored, the drain stays off.
  - S5a: toggling MCU_PA_EN with the gates still ON does not re-arm. Re-arming happens only after the gates are pinched: PA_ARMED at 143.009 ms, VOUT > 4.5 V at 143.354 ms.
- **Gate-lost energy (S3).**
  - The faulted PA peaks at 0.601 A, with 1.265 A for the whole chain.
  - The faulted PA absorbs **0.127 mJ** from the step until VOUT < 0.5 V. That is roughly half of the 0.248 mJ stored in 19.81 µF at 5 V; the rest goes to the other PAs and QOD. +5V_PA cannot feed it, because the switch is open.
- **Collapse ordering (S4, S6).**
  - The −4.6 V rail comparator always trips first. The gates do not reach −0.15 V until:
    - 1.82 ms after the trip in S4a;
    - 1.29 ms after the trip in S4b;
    - 1.40 ms after the AUX-UV trip in S6.
  - So the drain is below 0.5 V **1.2–1.7 ms before** any gate reaches −0.15 V, and long before 0 V.
  - The gate-lost comparator is never needed in these cases. In S4 and S6 the gates drift only after AVDD1 has fallen below their bias, or after AVDD3 is lost and PA_BIAS goes high-Z.

### Findings (FAIL or marginal)

1. **The 50 µs "VOUT < 0.5 V" target is not met in any fault case (S3–S6).**
   - The interlock itself is fast: PA_DRAIN_EN falls 0.5–1.6 µs after the threshold crossing, and the TPS22810 opens 3.3 µs later.
   - The rest is the 19.81 µF drain capacitance draining into the PAs (0.9–1.3 A), which takes 73–111 µs.
   - With the gates pinched (S5b) there is no PA current, and only the 250–400 Ω QOD discharges the node: τ = 5–8 ms, so VOUT < 0.5 V takes **7.2 ms**. That case is benign, because no current flows with the gates at −1.75 V.
   - Meeting 50 µs from 5 V would need about τ ≤ 20 µs, i.e. ≲ 1 Ω of active crowbar on VOUT driven by the inverse of PA_DRAIN_EN, or less drain capacitance.
   - Alternatively, restate the criterion as "drain source disconnected within 50 µs" plus a bounded residual energy (≤ 0.25 mJ per chain). That version **passes**, but it is a criterion decision for the reviewer, not something this simulation can settle.
2. **The A1 positive-gate protection fails during the +3V3_AUX ramp (S1: +628 mV on VGG_PA at 3.57 ms; abs max 0 V).**
   - Mechanism:
     - While +3V3_AUX is below 2.0 V, the LM339B is below VS min, so its outputs are modelled as floating.
     - The fail-safe pull-up then sets NEG_RAILS_OK = AUX/2, which is 0.65–1.0 V.
     - That is in or above the TPS22917 undefined band (VIL 0.35 V, VIH 1.0 V). IL_REF turns on for about 0.8 ms (2.76 → 3.57 ms) while the ADAR1000 is unpowered.
     - Each gate then charges toward +1.30 V through 62.5 kΩ, clamped by the gate diode.
   - Sensitivity: with the TPS22917 EN threshold at 0.9 V the gate still reaches +255 mV. At its guaranteed VIH of 1.0 V it stays at 0 V.
   - Because AUX/2 reaches 1.0 V exactly when the LM339 wakes up, the margin is zero, and this result depends on two unspecified behaviours: the LM339 output below 2 V and the TPS22917 EN threshold.
   - NEG_OK also pulses high for 3.06–3.56 ms. This is harmless here, because the MCU is not running and MCU_PA_EN is low.
   - Mitigation options (not designed): a pull-up ratio whose mid-level stays < 0.35 V until AUX > 2 V; a pull-down on the TPS22917 EN until +3V3_RF is good; or the per-gate Schottky clamp of INTERLOCK_SPEC R1(a).
3. **Fail-safe level on +3V3_AUX loss is marginal (S6).**
   - After the trip, NEG_RAILS_OK returns to about 1.0 V (AUX/2) once AUX falls below 2.0 V at 142.55 ms. U912 (still powered at about 1.7 V) then drives NEG_OK high again at 142.552 ms. IL_REF re-glitches to about 0.67 V.
   - The drain stays off only because the latch is cleared and needs a new MCU_PA_EN edge, which never comes: PA_ARMED stays 0 and PA_DRAIN_EN stays at 0 V.
   - So the latch, not the pull-up, provides the safety here. In the real LVC parts the 1.0 V input sits between VIL and VIH, so the logic level is undefined.
   - The gates did not go positive in this run, because the ADAR1000 had lost AVDD3 and the divider pulls the gates toward 0 V.
4. **GATES_PINCHED and GATES_OK read "good" whenever IL_REF is off and the gates are negative (S4 plot).**
   - Both references collapse to 0 V, so any negative gate looks "pinched".
   - Safety then rests entirely on NEG_RAILS_OK, both in the U912 AND and in IL_CLR_N.
   - This is correct by construction. A firmware or bench test should not read these nets as meaningful while IL_REF is off.
5. **+5V_PA bulk (235 µF) stays charged for about 100 ms after VIN loss** (420 Ω UVLO discharge). The TPS22810 is off, so the drain is unaffected; this is noted for bench safety.

### Assumptions (all labelled in the netlists)

- **Gate and PA behaviour**
  - PA drain current: 0.6 A at Vg = 0 V and a 0.5 V knee (tanh) in Vds.
  - The gate diode clamps at about +0.6 V.
  - PA_BIAS output resistance is 100 Ω.
  - PA_BIAS is clipped to [AVDD1, 0] and goes high-Z when AVDD3 < 2.8 V.
- **Comparators and logic**
  - LM339B outputs float below VS = 2 V.
  - LVC thresholds are ideal at VCC/2.
  - The TPS22917 EN threshold is at the midpoint of its specification band (see finding 2 for sensitivity).
  - The TPS22917 QOD pin is tied to VOUT. IL_REF has 100 nF.
- **Timing**
  - TPS22810 tD and tR are interpolated to VIN = 5 V, and the ramp is linear.
  - TPS7A33 soft-start is linear over 120 ms.
  - The TPS65131 starts in about 1 ms with no explicit current limit.
  - No TPS3430 delay is included: WDT_OK is a direct stimulus.
- **Loads and capacitors**
  - Loads are constant current or resistive at their budget values. The other 3 chains are a mirror of chain 1.
  - Capacitors are nominal, with no DC-bias derating. Derated MLCCs would discharge faster, which helps finding 1 slightly.

### Limitations

- **Behavioural only.** There are no device models, no temperature or tolerance corners (the trip points are nominal), and no layout parasitics.
- **Typical datasheet timing.** LM339B response and TPS22810 tOFF are typical values with no specified maximum, so they must be measured on the bench (INTERLOCK_SPEC R6).
- **Behaviour outside specified operating ranges is not modelled.** This covers comparator input common-mode range and the LVC/LM339 parts below their minimum supply.
  - The LM339 and LVC rows in the Assumptions list are modelling choices, not datasheet facts.
  - Findings 2 and 3 depend on those choices and must be confirmed on the bench.
- **Only one chain has 4 explicit gates.** The 16-gate wired-OR is represented by 4 gates.
- **Rails not modelled.** RF drive, +5V_LO / +3V3_LO and LO rails are not modelled, because they are not in the interlock path.
- **Fixed firmware timing.** Firmware events are at fixed times, not reactive. The MCU is assumed to be running from 8 ms.
