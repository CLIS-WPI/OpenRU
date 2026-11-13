# H2-E: bench-validation procedures for Candidate A (PA-safety architecture)

- **Date:** 2026-11-12. **Document only:** no KiCad file opened or edited, nothing committed, nothing purchased.
- **Inputs:** `h2d/ARCH_COMPARE.md` (A: §2–§3, §7), `h2d/BENCH_PLAN.md` (T1–T13, H2-E corrected),
  `h2d/CHARACTERISTICS.md`, `h2d/AUDIT_FMEA.md`, `h2d/sim/budget.txt`, `reports/H2D_SAFETY_ARCHITECTURE_REVIEW.md`.
- **Relation to BENCH_PLAN.md:** BENCH_PLAN lists *what* must be measured (T-numbers). This file gives the
  executable procedures, the order, the kill criteria and the uncertainty handling. Where a T-number exists it is
  cited; nothing here relaxes a BENCH_PLAN limit.
- **Hardware assumed:** (a) manufacturer EVMs for phase 1; (b) the one-chain Candidate-A test fixture being designed
  separately (dummy PA loads, gate-emulation input VGG_EMU, fault-injection jumpers, probe points, Kelvin shunts in the
  crowbar and eFuse-output paths). §2.6 lists the fixture features these procedures rely on.
- **Evidence status of every result here:** bench characterisation (`HARDWARE_MEASURED` on a sample), never a
  guarantee. A datasheet limit, where one exists, stays the design value. A manufacturer written answer that
  contradicts a bench value wins.

Requirements referenced (ARCH_COMPARE §5):

| ID | Requirement |
|---|---|
| R1 | Default TX inhibit: undefined monitor outputs, floating inputs or MCU faults never enable the PA drain |
| R2 | No diode-clamped logic nodes; every open-drain sink operates at a specified VOL point |
| R3 | Crowbar/eFuse break-before-make (BBM) proven from bounded parameters, falling and rising edge |
| R4 | PA drain < 0.5 V within 50 µs of any listed fault, worst case |

Budget numbers used for thresholds (DERIVED, `h2d/sim/budget.txt`): TPS3703 detection ≤ 30 µs; P fall ≤ 0.1 µs;
CD + Q_sd ≤ 0.075 µs; crowbar delay 2.778–3.218 µs; CA + CB + LVC ≤ 0.117 µs; gate charge ≤ 0.088 µs;
discharge 5.5 → 0.5 V ≤ 12.90 µs (τ = 0.2263 Ω × 23.77 µF, crowbar RDS(on) PLACEHOLDER 58 mΩ); chain after P↓ ≤ 16.5 µs;
rail-fault total 46.5 µs (margin 3.5 µs); BBM falling ≥ 1.278 µs (2.778 − 1.5), rising ≥ 2.713 µs.

---

## 1. Minimum experiment set (run first; decides whether A is viable)

Five experiments. They attack the five assumptions on which A's R3/R4 argument rests and that no datasheet bounds
(ARCH_COMPARE §3.8 items 1, 2, 5, 7 and the R2 sink points). E1–E4 need no fixture (EVMs, loose parts, SMU), so a
kill is found before the fixture is built out. E5 needs the fixture and is run only if E1–E4 are not NO-GO.

### 1.1 Decision tree

```
E1  eFuse SHDN→FET-off (+ SHDN-low leakage below 4.5 V)   [TPS16630-32EVM, chamber]
 ├─ NO-GO → STOP: A's R3 falling-edge proof is void. Escalate TI Q1–Q3. Do not build fixtures.
 └─ GO/HOLD
E2  crowbar MOSFET VGS(th), RDS(on), IDSS at −40/+25/+85 °C   [SMU + Kelvin socket]
 ├─ NO-GO → STOP for this MPN: select another FET (MOSFET Q1), repeat E2. A itself is not killed.
 └─ GO/HOLD
E3  TPS3703 detection delay vs real overdrive and ramp        [TPS3703Q1-A4120EVM or bare part]
 ├─ NO-GO → STOP: the rail-fault R4 row cannot close. Escalate TI Q6.
 └─ GO/HOLD
E4  VOL of every open-drain sinker at the real sink current   [EVMs + SMU, chamber]
 ├─ NO-GO → redesign pull-up / sinker (R2), repeat E4. A is not killed.
 └─ GO/HOLD
E5  BBM margin + P↓→drain<0.5 V on the one-chain fixture      [fixture, chamber]
 ├─ NO-GO → STOP: A fails R3 or R4 in hardware.
 └─ GO → A is viable: run §3 fault-injection set.  Any HOLD anywhere → re-run sim/budget.py with
         measured value + uncertainty before §3; A proceeds only if the re-run budget closes.
```

Outcome definitions (apply to every gate below):

- **GO:** the gated statistic plus uncertainty is inside the DERIVED design value (the budget is unchanged).
- **HOLD:** inside the hard requirement but outside the design value. A continues only after `sim/budget.py` is
  re-run with (measured gated statistic + U) and still closes R3/R4, and the deviation is reported to the vendor.
- **NO-GO:** the hard requirement (50 µs, BBM > 0, abs max) is violated, or the budget cannot close.

**H2-E.1 rule — HOLD is never a PASS.** A HOLD result is reported as "HOLD — not passed" in every table, summary
and CSV. It does not satisfy the matching BENCH_PLAN T-test, does not count toward "A is viable", and is not
described as safety evidence. A HOLD becomes GO only through the written budget re-run (and, where the gate says so,
a written vendor answer). If neither exists, it stays HOLD and A stays unproven.

"Gated statistic" X_g is defined in §2.5 (worst observed, or tolerance bound, whichever is worse), and U is the
expanded uncertainty of §2.4. Uncertainty is always applied **against** the design.

### 1.2 E1: TPS16630 SHDN → FET-off time and SHDN-low leakage below ROC (BENCH_PLAN T1a, T1b subset)

- **Hardware:** TPS16630-32EVM (TI; user guide SLVUBI9A). Reconfigure before use (verify against SLVUBI9A, the
  defaults were not read): R_ILIM = 9.09 kΩ, MODE open (latch), OVP divider to 5.35 V or OVP disabled, output loaded
  with the PA emulator (4 × 4.7 µF + 1 µF + 10 nF + 100 pF; plus 22.6 Ω ×4 equivalent or electronic load).
  Insert a 20–50 mΩ Kelvin shunt (or the DC current probe) in the eFuse **output** lead. The crowbar is not present
  in E1.
- **Drive:** SHDN from a pulse generator, fall time < 10 ns, high level 2.5 V (≤ 5 V SHDN ROC), (i) directly,
  (ii) through the design network 47 k / 47 k / 1 nF from a 5.08 V-referenced P emulation.
- **Corners:** VIN 4.5 / 5.0 / 5.5 V × load {pinched (caps only), 0.88 A, 1.49 A (0.88 A + 8.2 Ω), 2.0 A} ×
  T {−40, +25, +85 °C}; ≥ 50 events per corner, ≥ 3 units (2 date codes if obtainable).
- **Measure:** t_off = SHDN crossing 0.8 V falling → eFuse output current < 50 mA (I_off threshold, same as the
  overlap threshold in §3). Also record the crossing at 10 % of I_load and the instant dVOUT/dt changes to the
  C_drain-only slope, so the result can be mapped to TI's definition of "FET OFF" once received.
- **Part b (T1b subset, static):** SHDN held at 0 V; VIN held at 4.4, 4.2, 4.0, 3.5, 3.0, 2.0, 1.0 V; output
  shorted to GND through the Kelvin shunt (worst case: crowbar on). Measure output current with a DMM (≥ 10 s per
  point) at −40 / +85 °C.

| Gate | GO | HOLD | NO-GO |
|---|---|---|---|
| E1a t_off: X_g + U_t | ≤ 1.50 µs (DS max holds under H2 conditions) | 1.50–1.778 µs (H2-E.1: ceiling = d_min 2.778 − 1.0 µs, so BENCH_PLAN T7 "delay_min − tSD ≥ 1.0 µs" can still pass; T1a itself is FAILED in this band until TI answers Q1) | > 1.778 µs, or any single event ≥ 2.778 µs − U_t (BBM falling margin ≤ 0 by datasheet d_min) |
| E1b leakage, SHDN low, VIN 0–4.5 V | ≤ 10 mA at every point | — | > 10 mA at any point (the FET conducts below ROC with SHDN low: R1/R3 hole at brown-out) |

### 1.3 E2: crowbar MOSFET VGS(th), RDS(on), IDSS over temperature (BENCH_PLAN T5)

- **Hardware:** no EVM exists for CSD16301Q2 (none found on ti.com). Use an SMU (or pulsed curve tracer) with a
  4-wire Kelvin socket/adapter in the chamber. ≥ 5 units from ≥ 2 date codes. Repeat for Q_sd, Q_t, the ARM NMOS and
  the gate-lost NMOS with the "small FET" limits.
- **Measure, at −40 / +25 / +85 °C (DUT temperature, §2.3):**
  - VGS(th) at ID = 250 µA, VDS = VGS;
  - RDS(on) at VGS = 3.8 V (LVC1G17 VOH floor used here as worst case; replace with the measured VOH at 32 mA) and 4.5 V,
    ID = 5 A pulsed (≤ 300 µs, ≤ 1 % duty, so TJ ≈ TA) — and at 24 A single pulse if the SMU allows;
  - IDSS at VGS = 0 and 0.1 V, VDS = 5.5 V.
- **Derived kill bound for RDS(on):** R4 rail row leaves 50 − 30 − 3.598 = 16.40 µs for the discharge, so
  τ ≤ 6.84 µs and R_loop ≤ 0.2878 Ω, i.e. **RDS(on) ≤ 0.120 Ω including any fixture shunt and wiring in the loop**
  (R_CB max 0.168 Ω).

| Gate | GO | HOLD | NO-GO |
|---|---|---|---|
| RDS(on) max at +85 °C, VGS 3.8 V: X_g + U | ≤ 58 mΩ (PLACEHOLDER holds) | 58–119 mΩ (budget re-run; margin consumed) | > 119 mΩ (H2-E.1: exact bound 119.4 mΩ, rounded down) |
| VGS(th) min at +85 °C: X_g − U (lower tolerance bound) | ≥ 0.50 V (≥ 0.4 V above the ≤ 0.1 V gate-off level) | 0.30–0.50 V | < 0.30 V |
| VGS(th) max at −40 °C: X_g + U | ≤ 2.0 V (≥ 1.8 V overdrive at VOH 3.8 V) | 2.0–2.5 V | > 2.5 V |
| IDSS at VGS 0.1 V, VDS 5.5 V, +85 °C | ≤ 1 mA | — | > 1 mA |
| Small FETs: RDS(on) at VGS 4.4 V, +85 °C | ≤ 10 Ω (PLACEHOLDER) | 10–50 Ω (re-run budget) | > 50 Ω |

V_th,lim (used by the overlap gate in E5 and §3) = min VGS(th) measured at +85 °C over all units − 3·s − U_V,
but not above the GO floor 0.50 V.

### 1.4 E3: TPS3703 detection delay at the real overdrive and ramp (BENCH_PLAN T3)

- **Hardware:** TPS3703Q1-A4120EVM (TI; user guide SNVU635). Caution: this is the automotive -Q1 variant with a
  specific threshold/delay option; decode the option from SNVU635 before use. If it is not the adjustable/window
  variant intended for H2, E3 on the EVM is family characterisation only and **must be repeated on the H2 part**
  (bare part on an adapter or on the fixture). Replace the RESET pull-up with 2.2 kΩ to 5.08 V. VDD = 5.0 V and 3.9 V
  (guard edge).
- **Static first:** measure each unit's actual UV and OV threshold with a slow DC sweep (≤ 1 mV/s, DMM ±0.5 mV),
  rising and falling. All dynamic onsets are referenced to these measured values.
- **Dynamic:** SENSE driven by the fast-slew source. Steps from 2 % inside to 2 / 5 / 10 / 20 % overdrive; ramps
  through threshold at 0.01, 0.1, 1, 10 V/ms and 1, 10 V/µs (rail collapse). 25 / −40 / +85 °C. ≥ 30 events per
  corner, ≥ 3 units.
- **Measure:** t_det = onset → RESET ≤ 0.8 V, with onset = instant the input is 5 % beyond the measured threshold
  (budget definition). Also record threshold crossing → RESET ≤ 0.8 V (informational; needed for TI Q6).
- For ramps slower than 5 %/30 µs the 5 % point is reached after the output should have fallen; then t_det is
  negative or small and the gate is "RESET low no later than (5 % point + 30 µs − U_t)".

| Gate | GO | HOLD | NO-GO |
|---|---|---|---|
| X_g(t_det from 5 % point) + U_t, every overdrive ≥ 5 % and every ramp | ≤ 30 µs | 30 µs < X_g + U_t ≤ 50 µs − (E5 chain X_g + U_t) | > 50 µs − (E5 chain X_g + U_t), or > 33.5 µs if E5 not yet run (consumes the 3.5 µs margin) |
| 2 % step overdrive | record only; feeds TI Q6 and the onset definition | — | — |
| Missed detection (RESET never asserts within 10 ms at ≥ 5 % overdrive) | — | — | any occurrence |
| E3c (H2-E.1) slow +5V_PA collapse ≤ 1 V/ms, UV side, referred to +5V_PA through the divider: RESET ≤ 0.8 V before +5V_PA falls below 4.50 V + U_V (eFuse VIN ROC) | always | — | any event where RESET is still high at +5V_PA ≤ 4.50 V + U_V, unless E1b is GO at that VIN |

H2-E.1 notes on E3:
- **Device under test.** The +5V_PA monitor is now **TPS3703A7120DSERQ1** (1.2 V, ±7 %, 3.16 k / 1.00 k divider;
  A-SENSE fix, `design/h2e1/H2E1_PROCUREMENT_AUDIT.md` §1). The +5V_IL monitor stays TPS3703A7330DSER. E3 must be run on **both**
  exact MPNs. Results from the EVM device are family data only (§7).
- **Why E3c.** The 5 %-overdrive point below the A7120-Q1 UV minimum is 4.36 V, under the eFuse 4.5 V ROC. The
  datasheet tPD does not bound the slow-ramp case.
- **E3 HOLD is provisional.** The HOLD ceiling depends on the E5 chain result, so an E3 HOLD stays open until E5 is
  measured. Until then the 33.5 µs ceiling applies.

### 1.5 E4: VOL at the real sink current (BENCH_PLAN T4)

- **Sink current:** P pull-up 2.2 kΩ −1 % to 5.08 V gives 2.33 mA when one sinker holds P; the SHDN networks and
  47 kΩ readbacks add nothing when P is low. Test at **2.5 mA** (gate) and 5 mA (record).
- **DUTs and hardware:** TPS3703 RESET (TPS3703 EVM / bare part), TPS3430 WDO (TPS3430EVM), TPS16630 FLT
  (TPS16630-32EVM, FLT forced by UVLO pin pulled low), gate-lost / negative-rail / fast-OV NMOS with gate at TLV3202
  VOH (bare parts), ARM NMOS. SMU sinks the current into the output; DUT VDD from a precision supply at 3.9 V
  (guard edge) and 5.08 V; −40 / +25 / +85 °C; ≥ 3 units; 3 readings per point.
- **Derived bound:** without Q_sd, SHDN_c = P/2 + (≤ 10 µA × 23.5 kΩ) = P/2 + 0.235 V, which must stay < V(SHUTF)min
  0.8 V, so P < 1.13 V. With Q_sd the CA comparator also needs SHDN_c < 0.471 V (0.1·VCBmin − VIO), which Q_sd
  provides; E4 makes the eFuse path independent of Q_sd.

| Gate | GO | HOLD | NO-GO |
|---|---|---|---|
| VOL at 2.5 mA, every sinker, all T and VDD: X_g + U_V | ≤ 0.35 V | 0.35–1.0 V (eFuse shutdown then depends on Q_sd; R2 deviation documented) | > 1.0 V |
| TPS3703 RESET during VDD ramp-down 5 → 0 V at 0.1 V/ms (RESET held low for VPOR < VDD < UVLO) | ≤ 0.35 V while P pull-up rail ≥ 1 V | — | RESET releases (> 0.8 V) while VDD is between VPOR and UVLO |

### 1.6 E5: BBM margin and P↓ → drain < 0.5 V on the fixture (BENCH_PLAN T6, T7)

- **Hardware:** one-chain fixture, PA emulator pinched (caps only, worst-case discharge) and at 0.88 A; +5V_PA 5.5 V
  (max stored energy) and 4.77 / 5.08 V VCB; −40 / +25 / +85 °C.
- **Two modes:**
  - **E5a gate-only** (R_CB open jumper, crowbar FET drain disconnected): the timing chain runs without pulse
    current, so it can repeat fast. ≥ 500 cycles per temperature per unit, falling and rising edges.
  - **E5b full-energy** (R_CB fitted): ≥ 30 events per temperature at ≤ 1 event/min (RCS1206 rating, Vishay Q1).
    Compare E5a vs E5b gate timing; if they differ by more than U_t, E5a is not representative and only E5b counts.
- **Fault stimulus:** an open-drain on P (pulse generator driving an NMOS), fall < 20 ns; re-arm by release.
- **Measure, per event** (same acquisition, deskewed):
  - t_off: SHDN_c crossing 0.8 V → I_eFuse_out < 50 mA;
  - t_cb: SHDN_c crossing 0.8 V → crowbar VGS > V_th,lim (from E2);
  - BBM_fall = t_cb − t_off − U_t;
  - rising: t_cb_off = SHDN_c crossing 0.515 V rising → VGS < V_th,lim; t_on = SHDN_c → I_eFuse_out > 50 mA;
    BBM_rise = t_on − t_cb_off − U_t;
  - t_chain: P ≤ 0.8 V → VOUT_c < 0.5 V;
  - crowbar peak current, eFuse output current during the whole event (E5b).

| Gate | GO | HOLD | NO-GO |
|---|---|---|---|
| BBM_fall: lower tolerance bound of (t_cb − t_off) − U_t | ≥ 1.0 µs (BENCH_PLAN T7) | 0 < … < 1.0 µs | ≤ 0, or any single event with I_eFuse_out ≥ 50 mA while VGS ≥ V_th,lim |
| BBM_rise: lower tolerance bound − U_t | ≥ 2.0 µs | 0 < … < 2.0 µs | ≤ 0 |
| t_chain: X_g + U_t (H2-E.1: measured with the RS3 force pads shorted; with RS3 in the loop the placeholder budget alone gives 17.07 µs. Do not subtract a calculated shunt term) | ≤ 16.5 µs | 16.5–20.0 µs (fits only if E3 X_g + U_t ≤ 50 − t_chain) | > 50 − max(30 µs, E3 X_g + U_t), i.e. > 20.0 µs at the DS detection value |
| VOUT_c max (any time): X_g + U_V | ≤ 5.5 V | — | > 5.5 V (abs max, §4) |
| E5b crowbar peak: X_g | ≤ 27 A (BENCH_PLAN T6) | 27–33 A | > 33 A (≥ V/R_CB,min: the loop model is wrong) |

**A is viable** when E1–E5 are all GO, or HOLD with a closed budget re-run. Only then is §3 executed in full.

---

## 2. Measurement setup and instrumentation

### 2.1 Instruments (minimum)

| Item | Requirement | Why |
|---|---|---|
| Oscilloscope | ≥ 8 analogue channels (or two 4-ch scopes with shared trigger and timebase reference, deskewed as one); ≥ 350 MHz analogue BW (≥ 200 MHz acceptable if the uncertainty table is recomputed); ≥ 12-bit ADC or HiRes; ≥ 2.5 GS/s per channel; ≥ 50 Mpts per channel; segmented memory; DC accuracy ≤ ±1.5 % FS; calibrated within 12 months | 6 signals per event (P, SHDN_c, VGS_CB, VOUT_c, I_eFuse_out, I_CB) + trigger + one fault-specific signal; ns-level BBM edges inside a 100 µs window |
| Scope isolation | Mains-earthed scope; all fixture grounds bonded to the scope earth at one point; no floating of the scope. Floating quantities (high-side shunt) only via differential probes | operator safety, no ground loops in the 30 A loop |
| Passive voltage probes | 10×, ≥ 500 MHz, ≤ 10 pF; spring ground tips (≤ 5 mm) on every timing node; never the 15 cm ground lead | ground-lead inductance in a 30 A di/dt loop adds tens of mV and ns of ringing |
| Differential probe | ≥ 100 MHz, ±10 V differential, CMRR ≥ 80 dB DC–1 MHz and ≥ 60 dB at 10 MHz | eFuse high-side shunt at 5 V common mode |
| Current probes (option 1) | 2 × DC-coupled Hall/CT clamp, ≥ 30 A peak, ≥ 50 MHz (≥ 100 MHz preferred), noise floor such that 3σ ≤ 20 mA at 20 MHz BW limit; degauss before every run set | I_eFuse_out and I_CB |
| Kelvin shunts (option 2, preferred for the fixture) | Crowbar: 5–10 mΩ coaxial or 4-terminal low-inductance (≤ 1 nH) in the source-to-GND return, ground-referenced. eFuse output: 20–50 mΩ 4-terminal, read by the differential probe. TCR ≤ 50 ppm/K | the crowbar shunt adds to R_loop: include it in the E2 RDS(on) kill bound (≤ 0.120 Ω total) |
| Programmable supplies | +5V_PA: 0–12 V, ≥ 5 A, current limit settable to 3 A, list/ramp mode with external trigger, slew 0.01–10 V/ms. +5V_IL, VCB, logic: 0–6 V, ≤ 0.5 A limit, ramp mode. Negative-rail emulation: 0 to −6 V, ≤ 0.2 A limit | ramps, brown-out, ordering |
| Fast-slew source | Power op-amp or MOSFET-switched source able to make 1–50 V/µs edges on a 5 V/3 A rail, plus hard short through 0.1 Ω | rail-collapse cases |
| OV injection source | Dedicated supply 12 V, current limit ≤ 12 A peak via 2.2 µH + series MOSFET switch + fuse; never the +5V_PA supply in overvoltage | FB-open emulation (F9) |
| Function / pulse generator | 2 channels, ≤ 10 ns edges, burst and external-trigger modes, 0–5 V into high-Z; second unit for WDI | SHDN/P/gate stimulus, VGG_EMU steps, WDI |
| Electronic load | ≥ 1 channel, CC 0–3 A, ≥ 10 kHz transient BW (optional; resistor loads are the reference) | load-current dependence |
| Resistor loads | 22.6 Ω 1 % 1 W ×4 (IDQ), 8.2 Ω 1 % 5 W + logic-level MOSFET (gate-lost), 1.5 Ω 10 W and 1.0 Ω 10 W (overcurrent), 0.05 Ω hard short via MOSFET | fault loads |
| SMU | ±10 V, ±1 A DC, ≥ 10 A pulsed (or pulsed curve tracer to 30 A); 4-wire | E2, E4 |
| DMMs | 2 × 6½-digit, calibrated; 4-wire Ω | static thresholds, shunt calibration, scope correction |
| Thermal chamber (or thermal forcing system) | −45…+90 °C; DUT temperature measured by a calibrated type-T thermocouple bonded to the DUT case: accuracy ±1.0 °C, stability ±1 °C over 5 min; soak ≥ 20 min after the DUT reading is stable; DUT must reach ≤ −40 °C and ≥ +85 °C (−42…−40 and +85…+87 °C); dry-N₂ purge at cold | temperature corners; record DUT temperature, not air |
| IR camera | ±2 °C | R_CB temperature during repetition tests |

### 2.2 Calibration and deskew (daily, before any gated run)

1. Instruments in calibration (record due dates). Warm-up ≥ 30 min. Scope self-calibration after warm-up and after
   any lab temperature change ≥ 5 °C.
2. **Voltage channels at the decision levels.** Apply 0.500, 0.800, 5.500 V from a precision source (verified by
   DMM) through the actual probe to each channel at the vertical setting used in the test. Record the reading error
   → per-channel correction; residual after correction enters U_V. For VOUT_c use offset (≈ 5 V) and ≤ 50 mV/div
   so the 5.5 V gate is resolved to ≤ 10 mV.
3. **Current channels.** Degauss/zero probes. DC check at 0.05, 1, 3 A from the SMU (DMM reference); pulse check at
   ~20 A via the calibrated crowbar shunt. Shunts: 4-wire DC resistance with the DMM at 25 °C and at the chamber
   corners if the shunt is in the chamber.
4. **Common-mode zero run (eFuse high-side shunt).** Run the E5 discharge event with the eFuse disabled and its
   output physically disconnected from the shunt input side (zero true current). The residual reading is the
   CM-induced error; its peak (3σ over 30 runs) must be ≤ 20 mA, otherwise improve the probe/shunt before E5.
5. **Deskew.** Use a deskew fixture or a common fast edge: a ≤ 5 ns current step through a resistor seen
   simultaneously by every voltage probe, current probe and shunt channel. Adjust per-channel skew until edges
   coincide at 50 %. Residual skew ≤ 1 ns (record). Repeat at the end of the day; if drift > 1 ns, the day's
   timing data get the larger residual in U_t.
6. **Thermocouple** check at ice point (0 ± 0.5 °C) or against a reference probe.
7. **Timebase.** Use the instrument spec (typically ppm); negligible below 100 µs but recorded.

### 2.3 Thermal procedure

Soak each corner until the DUT thermocouple is stable within ±1 °C for 5 min, then ≥ 20 min more. Run cold before
hot. Remove power and wait for dew point margin (N₂ purge on) before opening the chamber at cold. Fixture boards
with the crowbar in the chamber: the shunt and R_CB TCR must be corrected from step 3.

### 2.4 Uncertainty budget and subtraction rule

Expanded uncertainty U is a **linear (worst-case) sum** of the components below (no RSS, for safety gates). It is
recomputed per test from that test's settings and recorded in the CSV (§5).

**Timing, for an interval between crossing A and crossing B in the same acquisition:**

| Component | Value (example at 2.5 GS/s, 350 MHz) |
|---|---|
| Sample interval (interpolated crossing, ±½ Δt per edge) | ±0.2 ns × 2 |
| Residual deskew between the two channels | ±1 ns |
| System rise-time bias (0.35 / BW_system, per edge, only if edge faster than the system) | ±1 ns × 2 |
| Threshold-voltage uncertainty converted to time: U_V / slope at the crossing, per edge | e.g. 10 mV / (50 mV/ns) = 0.2 ns on VGS; 20 mA / (10 mA/ns) = 2 ns on I_eFuse_out |
| Timebase | < 0.01 ns at 10 µs |
| **Example U_t (BBM interval)** | **≈ 6 ns** |

For slow edges the U_V/slope term dominates (e.g. a 0.1 V/ms ramp with 1 mV uncertainty gives 10 µs). For E3 ramps,
reduce it by referencing onsets to the per-unit DMM-measured threshold and a high-resolution, offset-corrected
channel; report U_t per ramp rate.

**Voltage:** U_V = corrected gain error + offset error + 3σ noise at the bandwidth used + probe attenuation error.
Static values (thresholds, VOL, VGS(th)) use the DMM/SMU spec instead.

**Subtraction rule (all gates):**

- Upper-limit quantity (time, VOL, VOUT, current): pass only if X_g + U ≤ limit. Margin = limit − X_g − U.
- Lower-limit quantity (BBM, VGS(th) min): pass only if X_g − U ≥ limit. Margin = X_g − U − limit.
- BBM margin must be **> 0 after U is subtracted**; a margin equal to U is a fail.

### 2.5 Statistics

- ≥ 3 units per DUT (≥ 5 for MOSFETs), 2 date codes where obtainable; record lot/date code.
- ≥ 30 repetitions per corner per unit (≥ 50 for E1, ≥ 500 for E5a). Report n, mean, s, min, max.
- **Gated statistic X_g** for an upper limit = max(observed maximum, mean + k·s); for a lower limit =
  min(observed minimum, mean − k·s); k = one-sided normal tolerance factor for 99 % coverage at 95 % confidence for
  the actual n (k ≈ 2.90 at n = 30, ≈ 2.74 at n = 50). Pool across units only after checking unit means do not
  differ by > U.
- Any single event that violates a hard (NO-GO) limit is a NO-GO regardless of statistics.
- Outliers are never removed; a suspected instrument artefact is re-run and both results are kept.

### 2.6 Fixture features assumed (to be confirmed against the fixture design)

| Feature | Used by |
|---|---|
| Probe points with spring-tip pads: P, SHDN_c, UVLO_c, CA out, C_t, CB out, crowbar gate (VGS at the FET pins), VOUT_c, +5V_PA_IN_c, VCB, FLT, WDO, every OD sinker output | all |
| Kelvin shunt in the crowbar source return (ground-referenced) and in the eFuse output path (high side) | E5, §3 |
| PA emulator: decoupling identical to a chain, 22.6 Ω × 4 switchable, 8.2 Ω + MOSFET, "pinched" (all loads off) | E5, §3 |
| Gate emulation: VGG_EMU node with 10 nF + 49.9 kΩ to a bench input, plus a direct low-impedance injection point | F3, F4 |
| Separate inputs: +5V_PA, +5V_IL (or VIN_12V → TPS7A25), VCB override, negative-rail emulation into the window comparators, "rail-OK" emulation inputs for rails not present, TPS3430 VDD jumper, WDI input | F1–F8 |
| Fault jumpers: C_t open, R_t short, SHDN_c override to a 2.5 V source, crowbar gate stuck high / stuck low, R_CB open, Q_sd open, monitor output disconnect (forces "released") | F7, E5a, F8 |
| No ADTR1107 and no ADAR1000 footprint populated on the fixture | §0 rule |

---

## 3. Fault-injection procedures (fixture; after §1 is GO/HOLD-closed)

### 3.0 Common to every procedure

**Preconditions (PC):**

- PC1: no ADTR1107 fitted or energised anywhere; no ADAR1000 on the fixture (ADAR1000 tests are BENCH_PLAN T9 on its
  own eval board only, inside recommended operating conditions).
- PC2: §2.2 calibration done today; deskew residual recorded.
- PC3: supply limits: +5V_PA ≤ 3 A per chain behind a 5 A fast fuse; logic rails ≤ 0.5 A; OV source per F9.
- PC4: crowbar full-energy events ≤ 1 per minute per R_CB set (unless the test is the repetition test and Vishay data
  allow more); R_CB 4-wire resistance recorded before and after each session (ΔR ≤ 1 %).
- PC5: power-up proof test passes: with ARM asserted (MCU not releasing), P reads low and VOUT_c < 0.1 V; releasing ARM
  with all rails valid gives P high and the eFuse on; asserting any one monitor input drops P.
- PC6: jumper configuration recorded in the CSV `config` column.

**Standard channels:** CH1 P, CH2 SHDN_c, CH3 crowbar VGS, CH4 VOUT_c, CH5 I_eFuse_out, CH6 I_CB, CH7 fault stimulus /
rail under test, CH8 fault-specific (FLT, WDO, VGG_EMU, VCB, UVLO_c).

**Common gates (CG), applied to every event unless the procedure says otherwise:**

| ID | Gate | Type |
|---|---|---|
| CG1 | VOUT_c max + U_V ≤ 5.5 V at every instant | abs max (§4), never relaxed |
| CG2 | Zero overlap: I_eFuse_out < 50 mA whenever crowbar VGS ≥ V_th,lim (E2); 50 mA is ≥ 2.5 × the demonstrated 3σ noise floor (≤ 20 mA). Report the overlap duration and peak if any | R3, never relaxed |
| CG3 | VOUT_c < 0.5 V no later than onset + 50 µs − U_t (onset per table below); design target in the right column | R4, never relaxed |
| CG4 | While the fault persists: no eFuse conduction (I_eFuse_out ≤ 10 mA averaged over 10 µs, VOUT_c ≤ 0.5 V); P stays low | R1 |
| CG5 | P < 0.8·VCB within 0.1 µs + U_t of the asserting OD output falling below 0.8 V (budget term); exceeding it is HOLD, re-run the budget | R4 budget |
| CG6 | After a latching fault (OC, TSD, OVP): no re-enable until the deliberate re-arm sequence | R1 |

**Fault onset definitions and R4 targets:**

| Fault class | Onset (t = 0) | DERIVED target (budget) | Hard gate |
|---|---|---|---|
| Rail UV/OV via TPS3703 | rail 5 % beyond the unit's measured threshold | ≤ 46.5 µs | ≤ 50 µs − U_t |
| Gate lost via TLV3202 | VGG_EMU 100 mV beyond the measured comparator threshold (TLV3202 tPD condition); also report from the threshold crossing | ≤ 16.6 µs | ≤ 50 µs − U_t |
| +5V_PA fast OV | +5V_PA crossing the measured fast-OV threshold (≈ 5.30 V) | ≤ 31.2 µs | ≤ 50 µs − U_t, and CG1 |
| Watchdog | WDO ≤ 0.8 V | ≤ 16.7 µs | ≤ 50 µs − U_t |
| eFuse fault | FLT ≤ 0.8 V | ≤ 16.7 µs | ≤ 50 µs − U_t |
| +5V_IL abrupt loss | +5V_IL 5 % beyond its monitor threshold | ≤ 16.9 µs | ≤ 50 µs − U_t |

**Operator safety (all procedures):** crowbar pulses reach 24–33 A with di/dt of A/ns; stored energy is small per
chain (≈ 0.36 mJ at 5.5 V on 23.8 µF) but the +5V_PA bulk (235 µF at 12 V ≈ 17 mJ) and supply energy behind it are
not. Run pulse tests in a closed enclosure with safety glasses; no hand contact with the R_CB/crowbar area while
armed; discharge and verify < 0.5 V with a DMM before touching; current-limited supplies only; the OV source has its
own fuse and an emergency-off within reach. Cold-chamber frost: never power a board with visible condensation.

### F1: Rail UV / OV (+5V_PA, +5V_IL, negative-rail emulation)

- **Preconditions:** PC1–PC6; chain armed (P high, eFuse on, VOUT_c ≈ +5V_PA); PA emulator at 0.88 A and pinched.
- **Steps:**
  1. Static thresholds: sweep each monitored input slowly (≤ 1 mV/s) to find UV/OV trip and release per unit
     (DMM); for the negative rails sweep the emulation input over 0 → −6.0 V (fixture has no ADAR1000, so this is a
     comparator input only).
  2. Dynamic, per rail: step to 2, 5, 10, 20 % beyond each threshold; ramps 0.01, 0.1, 1, 10 V/ms; collapse at 1,
     10, 50 V/µs; hard short via 0.1 Ω (+5V_IL only with VCB hold-up connected).
  3. Re-arm after each event (wait > tD max, release ARM) and confirm P high before the next.
- **Measure:** onset, OD output ↓, P ↓, SHDN_c, VGS_CB, VOUT_c, I_eFuse_out, I_CB.
- **N:** ≥ 30 per corner (rail × direction × shape × T {−40, 25, 85 °C}); full-energy events count against PC4.
- **Pass:** CG1–CG5. Negative rails additionally: over-magnitude trip |V_trip| + U_V < 5.5 V for −5V_BF (ADAR1000 AVDD1
  abs max −5.5 V) and below the ADTR1107 VSS_SW limit for −3V3_SW (take the value from ADTR1107 Table 6; not in the H2-D
  extracts); UV trip ≥ the designed −4.6 V / −3.0 V levels within the monitor tolerance.
- **Safety:** as §3.0; hard shorts only through the 0.1 Ω MOSFET path, never with a wire.

### F2: +5V_PA brown-out through 4.5 V and below (BENCH_PLAN T1b in-circuit)

- **Preconditions:** chain armed at +5V_PA = 5.0 V; crowbar connected; PA emulator pinched and at 0.88 A.
- **Steps:**
  1. Ramp +5V_PA 5.0 → 0 V at 0.01, 0.1, 1 V/ms and 1, 10 V/µs.
  2. Static holds at 4.6, 4.5, 4.4, 4.2, 4.0, 3.5, 3.0, 2.0, 1.0 V (≥ 10 s each), entered from 5.0 V.
  3. Repeat 1–2 with the SHDN_c override jumper holding SHDN_c at 2.5 V (eFuse commanded on; emulates a monitor
     failing to assert) — this measures the eFuse's own behaviour below ROC, not the design.
  4. Recovery: ramp back 0 → 5.0 V at the same rates; P must not re-assert before the TPS3703 tD.
- **Measure:** P, SHDN_c, I_eFuse_out, I_CB, VOUT_c, +5V_PA; static I_eFuse_out by DMM; FET state (VOUT vs VIN).
- **N:** ≥ 30 per ramp per T; statics 3 readings per point per T.
- **Pass:** CG1–CG4; onset = +5V_PA 5 % below the measured UV threshold (≈ 4.37 V at 4.6 V nominal); with SHDN low,
  I_eFuse_out ≤ 10 mA at every VIN 0–4.5 V (static) and CG2 holds dynamically. Step 3 result is record-only
  (TI Q3) but any conduction > 10 mA with SHDN low in step 1–2 is a FAIL.
- **Safety:** with the crowbar on and the eFuse possibly conducting below ROC, supply current is limited by the 3 A
  setting; watch R_CB temperature (IR) during static holds and abort above 100 °C.

### F3: Gate lost (VGG_EMU step to 0 V)

- **Preconditions:** chain armed; VGG_EMU at −1.1 V (operating) through 10 nF + 49.9 kΩ; 8.2 Ω load enabled
  synchronously with the step (emulates 0.6 A PA current at 0 V gate).
- **Steps:**
  1. Static: find the gate-lost comparator threshold per unit (slow sweep −1.1 → 0 V, DMM).
  2. Bench input stepped −1.1 → 0 V (node rises with τ ≈ 0.5 ms).
  3. Direct injection: low-impedance step on the gate node −1.1 → 0 V (< 1 µs).
  4. Slow drift: −1.1 → 0 V at 1 V/s.
  5. Repeat at VGG_EMU = −1.75 V start.
- **Measure:** VGG_EMU, comparator output, P, standard channels.
- **N:** ≥ 30 per shape per T.
- **Pass:** CG1–CG5 with the gate-lost onset definition. Also report onset-from-threshold-crossing; if that exceeds
  50 µs for step 2, record it as a design-review item (slow gate drift vs R4 definition), not as a pass.
- **Safety:** none beyond §3.0 (low energy).

### F4: Gate below −2 V (must be detected; no ADTR1107 present)

- **Preconditions:** chain armed; VGG_EMU at −1.1 V.
- **Steps:** step VGG_EMU to −1.90, −1.95, −2.00, −2.10 V and ramp −1.1 → −2.5 V at 1 V/ms and 1 V/s; direct-injection
  variant as F3.
- **Measure:** the over-negative detector output (whatever implements it), P, VGG_EMU at the detection instant.
- **N:** ≥ 30 per shape per T.
- **Pass:** detection (P low and MCU-readable flag) asserts at VGG_EMU ≥ −2.0 V + U_V (i.e. trip threshold − U_V
  above −2.0 V, so a real gate would be flagged before its abs max), every event, every T; P low within 50 µs − U_t of
  the threshold crossing.
- **Expected status:** Candidate A as documented in ARCH_COMPARE has gate-lost (too positive) comparators only; **no
  over-negative gate detector is described.** Unless the fixture implements one, F4 is recorded **FAIL — not
  implemented** and stays an open design item under R6/TE2. Detection does not protect a real PA (the gate would
  already be at its abs max); prevention depends on GATE_BIAS_ANALYSIS (divider) and ADI answers.
- **Safety:** none beyond §3.0.

### F5: Watchdog stop and brown-out (TPS3430)

- **Hardware:** fixture; WDI-timing parts may first be run on the TPS3430EVM.
- **Steps:**
  1. WDI running in-window (pulse generator at the mid-window period) → arm.
  2. Stop WDI (held high, held low) → expect WDO↓ within tWDU max (63.3 ms at CWD = NC, SET = 00; use the H2 setting).
  3. Early WDI (period < tWDL min) → expect WDO↓.
  4. Brown-out, realistic: +5V_IL (= TPS3430 VDD) ramped 5.0 → 0 → 5.0 V at 0.1 V/ms and 10 V/ms, dwelling 1 s at
     1.6, 1.2, 0.8 V. The guard must keep the eFuse off (CG4) throughout.
  5. Brown-out, single fault (TPS3430 VDD jumper on a separate supply, rest valid): VDD at 1.6, 1.2, 0.8 V.
- **Measure:** WDI, WDO, P, VOUT_c, I_eFuse_out; WDI-stop → WDO delay; WDO↓ → P↓ delay.
- **N:** ≥ 30 per step per T.
- **Pass:** step 2–3: WDO↓ within the datasheet window (+ U_t) and CG1–CG5 from WDO↓. Step 4: CG4 throughout
  (no conduction while +5V_IL < 4.38 V, eFuse off below 3.89 V as derived). Step 5: record only — WDO is
  datasheet-defined HIGH for 0.8 < VDD < 1.6 V (DU1); if P stays high, it is reported as the known DU1 residual, and
  the design must show the single fault is otherwise detected (open item).
- **Safety:** low energy.

### F6: eFuse overcurrent and thermal shutdown (dummy 8.2 Ω + extra load)

- **Preconditions:** chain armed at +5V_PA 5.0 V, 0.88 A + 8.2 Ω (≈ 1.49 A, below I(OL) 1.84 A); supply limit raised to
  5 A for this test only, 5 A fuse retained.
- **Steps:**
  1. Add 1.5 Ω (≈ 3.3 A, between I(OL) max 2.16 A and fast-trip 2 × I(OL)): expect current limit, then TSD and latch.
  2. Add 1.0 Ω (≈ 5 A, above 2 × I(OL) max 4.32 A): expect fast-trip in 2.2–4.5 µs and latch.
  3. Hard short via 0.05 Ω MOSFET.
  4. Check latch: hold the overload for 60 s after the trip; no restart.
- **Measure:** I_eFuse_out, VOUT_c, FLT, P, SHDN_c, crowbar, eFuse case temperature (thermocouple), time from load
  step to FLT↓ (record; not specified by TI).
- **N:** ≥ 30 per step at 25 °C; ≥ 10 per step at −40/+85 °C (TSD steps are slow; allow cool-down between events).
- **Pass:** CG1–CG6 with onset = FLT↓; current during limit within 1.84–2.16 A (+U); fast-trip time ≤ 4.5 µs + U_t;
  latched off (I_eFuse_out ≤ 10 mA) for the full 60 s.
- **Safety:** load resistors dissipate up to 25 W during the limit phase; mount on heatsinks, enclosure closed.

### F7: Single faults (fault-injection jumpers)

Each sub-test: fit the jumper with the chain disarmed, then arm and run the E5 stimulus (OD on P). Full-energy events
≤ 1/min. ≥ 30 events per sub-test at 25 °C, ≥ 10 at −40 and +85 °C.

| Sub | Jumper | Expected behaviour | Pass |
|---|---|---|---|
| F7a | C_t open | crowbar fires ≈ 0.2 µs after SHDN_c↓, before the eFuse is off: overlap expected | overlap duration (I_eFuse_out ≥ 50 mA while VGS ≥ V_th,lim) ≤ 1.5 µs + U_t from SHDN_c 0.8 V; eFuse then latched (CG6); CG1, CG3. **Peak and energy recorded; no peak limit is claimed** (TPS1663 ≈ 45 A short-circuit current is typical only). Peak > 33 A (Ohm's-law bound with intact R_CB) → FAIL, investigate. Crowbar-gate readback flags the fault at the next proof test |
| F7b | R_t short | as F7a | as F7a |
| F7c | SHDN_c override to 2.5 V (eFuse forced on) | P↓ fires the crowbar into an enabled eFuse: overlap until fast-trip/current limit latch | eFuse fast-trip ≤ 4.5 µs + U_t from crowbar conduction; latch; CG1; VOUT_c < 0.5 V within 50 µs − U_t; peak recorded (not guaranteed). Proof test must detect the override (P low but eFuse PGOOD/IMON high) |
| F7d | Crowbar gate stuck high | arming attempt into a permanently-on crowbar | at arm: eFuse fast-trip + latch, no repeated retries (count events in 60 s = 1); proof test flags gate readback high before arming |
| F7e | Crowbar gate stuck low (or R_CB open) | no crowbar discharge: drain decays only by load | **expected R4 FAIL** (pinched: decay by leakage only). Pass condition is detection: the power-up crowbar self-test flags it before any arm. Record decay time |
| F7f | Q_sd open | eFuse shut down only via P/2 + 0.235 V path | SHDN_c < 0.8 V − U_V (from E4 VOL); CG2, CG3 |

- **Safety:** F7a–F7d produce uncontrolled-peak overlap pulses; enclosure closed, one event per minute, check R_CB
  ΔR and the eFuse for damage (re-run E1 on that unit at 25 °C after the F7 series; any change > U_t retires the unit).

### F8: Arbitrary supply ordering (matrix)

- **Rails on the fixture:** +5V_IL (or VIN_12V via TPS7A25), VCB (normally from +5V_IL; separately only as a fault
  case), +5V_PA, negative-rail emulation, VGG_EMU, plus "rail-OK" emulation for rails not physically present
  (+3V3_RF, +3V3_AUX, +1V8_DIG, IL_REF).
- **Matrix:**
  1. Full permutation of the 4 physical rails {+5V_IL, +5V_PA, NEG_EMU, VGG_EMU}: 24 power-up × 24 power-down orders
     at 1 ms inter-rail delay, ARM released (MCU "wants" to arm throughout) — 576 sequences.
  2. 50 randomised sequences including rail-OK emulation inputs, delays drawn from {0, 10 µs, 1 ms, 100 ms}, ramp
     rates {0.1 V/ms, 10 V/ms}, reusing the sim seed list.
  3. Repeat 1 with the monitor outputs disconnected ("released", BENCH_PLAN T11 worst case).
  4. Run at 25 °C; repeat the 50 random sequences at −40 and +85 °C.
- **Measure:** all rails, P, SHDN_c, UVLO_c, I_eFuse_out, VOUT_c, crowbar VGS. Trigger on SHDN_c > 0.8 V or
  I_eFuse_out > 10 mA while any rail is outside its window (scope mask/limit test).
- **Pass:** zero eFuse conduction (> 10 mA) while any rail is outside its window or VGG_EMU is outside its ON range
  (CG4); with monitors released, no conduction while +5V_IL < 4.38 V; CG1, CG2 in every sequence; on power-down,
  CG3 from the first rail leaving its window by 5 %.
- **Safety:** low energy except crowbar events (rate-limited per PC4: insert ≥ 60 s idle after each sequence that
  fired the crowbar).

### F9: FB-open over-voltage emulation (current-limited source) (BENCH_PLAN T12)

- **Preconditions:** PC1–PC6; chain armed at 5.0 V; +5V_PA bulk 235 µF fitted. **Replace the PA emulator's 6.3 V
  capacitors with ≥ 16 V parts of the same effective capacitance at 5 V bias**, because a protection failure would
  put up to 12 V on them. OV source: 12 V supply → fuse → 2.2 µH → series MOSFET → +5V_PA node, current limit
  ≤ 12 A peak.
- **Steps:**
  1. Slow ramp +5V_PA 5.0 → 6.0 V at 1 V/ms (precision supply).
  2. Fast injection: close the series MOSFET for 50 µs, then 500 µs, then until the source current limit holds.
  3. Repeat with the TLV3202 fast-OV path disabled (jumper), so only TPS3703 OV and TPS16630 OVP act (layer test).
  4. Repeat with both disabled: only the eFuse OVP acts (OVP_toff 8.5–14 µs).
- **Measure:** +5V_PA, VOUT_c (offset-corrected, ≤ 10 mV resolution), time above 5.5 V, fast-OV output, P, FLT, eFuse
  latch state, crowbar.
- **N:** ≥ 30 per step at 25 °C; ≥ 10 at −40/+85 °C.
- **Pass:** **VOUT_c max + U_V ≤ 5.5 V in every event, every step** (no duration allowance; §4); eFuse latched; P low;
  CG3 from the fast-OV threshold crossing. Steps 3–4 test single layers: any VOUT_c > 5.5 V − U_V there is a FAIL of
  that layer and is reported (to ADI with the waveform, per ADI Q1).
- **Safety:** 12 V / 12 A source; fuse; enclosure closed; the 235 µF bulk at up to 12 V holds ≈ 17 mJ — discharge
  through a 10 Ω resistor before handling.

---

## 4. Gates that are never relaxed

1. **ADTR1107 VDD_PA (VOUT_c, the PA-drain node): ≤ 5.5 V at every instant** (ADTR1107 Table 6 abs max). Measured
   max + U_V ≤ 5.5 V. No duration or energy allowance.
2. **ADTR1107 VGG_PA: −2.0 V ≤ VGG ≤ 0 V** for any gate value the design would deliver to a PA (abs max). On the
   fixture VGG_EMU is driven beyond this deliberately (F4) only because no ADTR1107 is present.
3. **ADAR1000 AVDD1: never beyond −5.5 V (abs max); tests stay inside −4.75…−5.25 V (recommended).** AVDD3 ≤ 3.6 V
   (abs max). PA_BIAS outputs are only observed, never forced. No stress test is run on the ADAR1000 (BENCH_PLAN T9,
   H2-E correction).
4. **R4: VOUT_c < 0.5 V within 50 µs − U_t** of the defined onset, worst case.
5. **R3: BBM margin − U_t > 0** on both edges; zero overlap per CG2 in fault-free operation.
6. **R1: no eFuse conduction while any monitored condition is out of range** (CG4).
7. Every fixture part inside its own abs max (e.g. TPS16630 SHDN ≤ 5 V ROC; CSD16301Q2 VGS −8…+10 V; DMG1012T
   ±6 V); a test that would exceed one is redesigned, not run.

**Rule.** Any measured or extrapolated value beyond an ADTR1107 or ADAR1000 absolute maximum rating is a **FAIL**,
regardless of duration, statistics or engineering judgement, unless **written manufacturer evidence** covers that
exact condition. Written evidence means a datasheet/app-note revision or a written, attributable reply from the
manufacturer (support case number, author, date) filed in the project record; verbal statements, forum posts and
typical curves do not count. Uncertainty is added to the measured value before comparison, never subtracted. Gates
1–7 cannot be changed by a HOLD/budget re-run; only the GO design values in §1 can.

---

## 5. Data recording and traceability

### 5.1 CSV template (one row per measured quantity per event)

```
run_id,datetime_utc,operator,procedure_id,step,event_idx,fixture_sn,fixture_rev,board_or_evm,dut_ref,dut_mpn,dut_unit,lot_code,date_code,config_jumpers,temp_setpoint_C,temp_dut_C,v_5vpa_V,v_5vil_V,v_vcb_V,v_neg_V,vgg_emu_V,load_config,i_load_A,stimulus,slew_V_per_s,overdrive_pct,onset_def,quantity,value,unit,u_expanded,u_components,limit,limit_kind,gate_id,margin,verdict,n_in_corner,stat_mean,stat_s,stat_k,x_gated,scope_sn,scope_cal_due,probe_ids,shunt_ids,deskew_residual_ns,sample_rate_Sps,bw_limit_Hz,waveform_file,waveform_sha256,notes
```

- `limit_kind` ∈ {max, min}; `margin` = limit − value − U (max) or value − U − limit (min); `verdict` ∈
  {PASS, FAIL, GO, HOLD, NO-GO, RECORD}.
- `stat_*` and `x_gated` are filled on the corner summary row (`event_idx = SUMMARY`).
- Waveforms are kept raw (instrument format + CSV export) and hashed; no waveform is discarded.

### 5.2 Traceability

| Req | Claim in ARCH_COMPARE | Tests | Acceptance |
|---|---|---|---|
| R1 | Rail guard (eFuse off for +5V_IL < 3.89 V, on only ≥ 4.38 V); floating inputs disable; MCU cannot force P | E1b, E4 (TPS3703 ramp-down), F2, F5 step 4, F8 (incl. released monitors), PC5 proof test, F7c/F7d detection | CG4, CG6; I_eFuse_out ≤ 10 mA with any fault/out-of-window rail; SHDN-low leakage ≤ 10 mA at VIN 0–4.5 V |
| R2 | No diode clamps; OD sinkers at specified VOL | E4, F7f | VOL + U_V ≤ 0.35 V at 2.5 mA (GO), never > 1.0 V |
| R3 | BBM ≥ 1.278 µs falling, ≥ 2.713 µs rising, from DS limits; lost-BBM overlap duration ≤ 1.5 µs | E1a, E2 (V_th,lim), E5a/E5b, F1–F9 (CG2), F7a–F7c | BBM − U_t ≥ 1.0 / 2.0 µs (GO), > 0 (hard); overlap = 0 in fault-free runs; single-fault overlap ≤ 1.5 µs + U_t, then latch; peak recorded, not guaranteed |
| R4 | Worst case 46.5 µs (rail), 16.6 (gate), 31.2 (OV), 16.7 (WDO/FLT), 16.9 (+5V_IL) | E2 (discharge), E3 (detection), E5 (chain), F1, F2, F3, F5, F6, F9 | CG3: < 0.5 V by onset + 50 µs − U_t; GO if within the DERIVED row values; VOUT_c ≤ 5.5 V always (CG1) |
| abs max | ADTR1107 VDD_PA 5.5 V, VGG −2…0 V; ADAR1000 AVDD1 −5.5 V, AVDD3 3.6 V | F9, F1 (NEG), F4, all CG1 | §4 rule |

---

## 6. Manufacturer questions (one line each; ✱ = blocks a §1 kill decision)

**TI**

1. ✱ TPS1663/TPS16630 tSD(dly): what defines "FET OFF" (gate level or drain current), and is 1.5 µs max valid at 1–2.2 A and C(OUT) ≤ 25 µF? → R3 falling BBM, E1.
2. ✱ TPS1663: is V(SHUTR) ≥ V(SHUTF) guaranteed, and what is the SHDN pin capacitance max? → R3 rising BBM.
3. ✱ TPS1663: with SHDN low and VIN 0–4.5 V, can the FET conduct; what are the internal POR min/max? → R1/R3 at +5V_PA brown-out (E1b, F2).
4. TPS1663: FLT assertion delay after TSD/OC/UVLO events, and is the FET off when FLT↓? → R4 eFuse-fault row (F6).
5. TPS1663: is there a guaranteed maximum peak current before fast-trip (≈ 45 A is typical only)? → bounds single-fault overlap energy (F7).
6. ✱ TPS3703: tPD maximum for overdrive < 5 % and for ramps 0.01–10 V/ms? → R4 rail row, 3.5 µs margin (E3).
7. TPS3703: does an MR-initiated reset latch in CT = GND latch mode? → re-arm latch, removes a firmware dependency.
8. TPS3703: VOL max at 2.5 mA for VDD 3.9–5.1 V over −40…125 °C (between the 2 V and 5 V spec points)? → R2 (E4).
9. TPS3430: maximum WDI→WDO delay (tWD-del, typical 50 ns only)? → R4 watchdog row.
10. TLV3202: output state for VCC 0–2.7 V (can it drive high below its supply range)? → R1 below the guard.
11. TPS568230 (U651): OCL and peak inductor current with FB open? → +5V_PA OV slew, abs max gate (F9).

**ADI**

1. ✱ ADTR1107: written VDD_PA transient rating above 5.5 V (amplitude, duration), or confirmation that 5.5 V is absolute for any duration? → §4 gate 1, F9.
2. ADTR1107: VGG_PA abs max when VDD_PA = 0 V, and the VSS_SW abs max for the −3V3_SW window? → TE2, F1/F4 limits.
3. ADAR1000: PA_BIAS output with AVDD3 absent and AVDD1 present (Ua13)? → TE2, T9.
4. ADAR1000: PA_BIAS pin abs max and DAC full-scale min/max vs AVDD1? → gate-divider bound (R6).
5. ADAR1000: how is code 0x85 (−2.5 V, p45) reconciled with ADTR1107 VGG −2 V abs max? → firmware bias limit (TE2).

**MOSFET vendor (TI CSD or alternative)**

1. ✱ A crowbar NMOS (≥ 35 A pulse, 20 V) with VGS(th) min/max and RDS(on) max at −40 and +125 °C — CSD16301Q2 or replacement? → R4 discharge term, R3 off-state (E2).
2. Small-signal NMOS (Q_sd, Q_t, ARM, gate-lost) with VGS(th) min at +125 °C and RDS(on) max at VGS 4.4 V over temperature? → R1 off-state, P/SHDN timing.
3. Repetitive SOA: 35 A, 10 µs, at 1 Hz and 1/min, TJ ≤ 85 °C? → crowbar re-arm rate.

**Vishay**

1. ✱ RCS1206 1 Ω: repetitive pulse rating at 5.5 A peak, τ 5.4 µs exponential, at 1/s and 1/min, and lifetime ΔR? → crowbar repetition (PC4, E5b).
2. RCS1206: pulse rating derating at −40 °C and +85 °C ambient? → pulse tests at temperature.

---

## 7. EVM availability (checked on ti.com, 2026-11-12, plain curl)

| Need | EVM | Status |
|---|---|---|
| TPS1663 / TPS16630 | **TPS16630-32EVM** (user guide SLVUBI9A) | listed on the TPS1663 product page; "TPS16630EVM", "TPS1663EVM" return 404. TPS2663-166EVM also exists (different device family, not used) |
| TPS3703 | **TPS3703Q1-A4120EVM** (user guide SNVU635) | H2-E.1: U1 = TPS3703A4120DSERQ1 (1.2 V, ±4 %), soldered, DSE land, no SENSE divider. **Not the H2 device**: rework U1 to TPS3703A7120DSERQ1 / TPS3703A7330DSER, R1 → 2.2 kΩ, remove or record C2 10 nF; check the C3/latch-jumper contradictions in SNVU635 on the board (`h2e1/H2E1_PROCUREMENT_AUDIT.md` §5). No commercial-grade TPS3703 EVM exists |
| TPS3430 | **TPS3430EVM** | listed |
| TLV3202 | none | product page lists only reference designs; use a SOT/MSOP adapter or the fixture |
| CSD16301Q2 | none | Kelvin socket/adapter on SMU |
| TPS7A25 | TPS7A26EVM-021 listed (different device); not needed for §1 | — |
| ADAR1000 | ADI eval board (BENCH_PLAN T9) | not checked here (ADI site not queried) |

EVM user guides were not read; jumper defaults, R_ILIM and C_OUT must be checked against SLVUBI9A / SNVU635 before
reconfiguration.
