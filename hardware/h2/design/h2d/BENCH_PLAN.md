# H2-D: low-risk bench validation plan (PA safety path)

- **Date:** 2026-11-12.
- **Purpose:** produce the measurements that datasheets do not guarantee, for:
  - candidate A (ARCH_COMPARE §3.8, §7);
  - the as-built H2-C baseline (B-TOFF, B-TD, B-M5, DU1, B-ADAR);
  - candidate B's tOFF, only if B is pursued.
- **Bench results are characterisation, not guarantees.** Each result is accepted only with the guardband stated in its test. Where a datasheet limit exists, it remains the design value.

## 0. Safety rules (apply to every test)

1. **No ADTR1107 is fitted or energised in any test.**
   - PA footprints stay unpopulated. Every PA is replaced by a dummy load (§1.2).
   - The ADAR1000 is used only on its own evaluation board with no PA connected (T9).
2. **Supplies.**
   - Every external supply is current-limited: ≤ 3 A on +5V_PA per chain and ≤ 0.5 A on the logic rails.
   - The +5V_PA source gets a 5 A fast fuse.
   - The 12 V over-voltage injection (T12) uses a dedicated current-limited supply behind a series resistor.
3. **Pulse tests** (T6, T12) are run with the board in an enclosure, with safety glasses. The pulse rate is ≤ 1 per minute unless the test is explicitly a repetition test.
4. **Thermal chamber:** −40 °C, +25 °C and +85 °C soak, each ≥ 20 min after the board thermocouple reading is stable. Record the board temperature at the DUT, not the chamber air.
5. **ESD control** for every DUT.
6. **Sample size:** ≥ 3 units of each DUT part, from 2 date codes where possible. Record lot codes.

## 1. Equipment and fixtures

### 1.1 Instruments

| Item | Minimum spec |
|---|---|
| Oscilloscope | ≥ 4 channels (8 preferred), ≥ 200 MHz, ≥ 12-bit vertical (or HiRes mode), ≥ 10 Mpts, segmented memory |
| Current probes | 2 × clamp-on, DC–≥ 50 MHz, ≥ 30 A peak (e.g. 30 A/120 MHz class) |
| Shunts | 10 mΩ coaxial shunt for the crowbar loop, as a cross-check |
| Voltage probes | ≥ 2 × differential (≥ 100 MHz) for floating nodes; passive 10× probes with spring ground tips |
| Supplies | Programmable supplies with external-trigger list mode (for ramps). One fast-slew supply or power op-amp able to make 0.01–50 V/µs edges on a 5 V/3 A rail (for rail-collapse emulation) |
| Pulse source | Function/pulse generator, 2 channels, ns edges |
| Static characterisation | SMU (or precision supply plus DMM) for VGS(th), VOL and RDS(on) |
| Environment | Thermal chamber −40…+85 °C; thermocouple logger |
| Electronic load | 4-channel, CC mode, ≥ 1 A per channel, ≥ 10 kHz transient bandwidth |

### 1.2 Dummy PA load ("PA emulator"), one per ADTR1107 position

| Element | Value | Purpose |
|---|---|---|
| Decoupling | Same MPNs and layout as the PA position: 4.7 µF X5R (GRM035R60J475ME15D or the H2 part), 10 nF, 100 pF on VDD_PA; per chain 4 × 4.7 µF + 1 µF + 10 nF + 100 pF | Real stored energy, including DC-bias derating |
| Quiescent emulation | 22.6 Ω 1 % 1 W (5 V / 0.221 A) | IDQ 220 mA |
| Fault emulation | 8.2 Ω 1 % in series with a logic-level MOSFET, switched by the pulse generator | 0.6 A (gate-lost at 0 V) |
| "Pinched" condition | Both loads disconnected | Worst case for discharge (no PA current) |
| Electronic load (alternative) | 0.22 / 0.6 A steps | Load-current dependence of tOFF |
| Gate emulator | 10 nF + 49.9 kΩ to a bench supply set to −1.1 / −1.75 / 0 V | Exercises the gate-lost and pinch comparators without a PA |

### 1.3 Standard test points

| Group | Nodes |
|---|---|
| Permit / interlock | P, SHDN_c, UVLO_c, CD out, CA out, C_t, CB out, crowbar gate |
| Power | VOUT_c (drain), +5V_PA_IN_c |
| Currents | eFuse input current (current probe on the IN lead), crowbar current (probe on the R_CB return) |

For the H2-C baseline, the equivalent nodes are PA_DRAIN_EN, PWR_CB_Dc, PWR_CB_Gc and PG_3V3RF.

**Overlap metric (both architectures):** the time during which eFuse/switch input current > 0.5 A **and** crowbar current > 0.5 A simultaneously. Both probes are deskewed to < 2 ns.

## 2. Tests

Pass/fail limits refer to the design values in ARCH_COMPARE. "GB" means guardband.

### T1a: TPS16630 SHDN → FET-off time (A). Mandatory

- **Why:** tSD(dly) is 0.8–1.5 µs (SLVSET9G p10), but "FET OFF" is not defined and was characterised only at C(OUT) = 1 µF.
- **Setup:**
  - TPS16630 eval or H2-D prototype; VIN 4.5 / 5.0 / 5.5 V; ILIM 9.09 kΩ.
  - Load: PA emulator on a chain at 0.88 A, 2.0 A (electronic load) and pinched.
  - SHDN is driven by the pulse generator (fall time < 10 ns) through the actual 47 k / 47 k / 1 nF network, and also directly.
- **Measure:** delay from SHDN = 0.8 V to:
  - (i) input current < 1 % of the load current;
  - (ii) VOUT starting to fall with dV/dt set by C_drain only.
- **Conditions:** −40 / 25 / 85 °C; 50 events per condition.
- **Pass:** max delay ≤ 1.5 µs at every condition, **and** max ≤ 0.75 × the crowbar delay minimum (2.78 µs), so ≤ 2.08 µs with GB.
- **Fail:** any delay > 1.5 µs. That reopens R3 for A.

### T1b: TPS16630 below its ROC (A). Mandatory

- **Setup:** SHDN held low (0 V), and separately SHDN high. VIN swept 5.0 → 0 V at 0.01, 0.1, 1 and 10 V/µs, and held statically at 4.4, 4.2, 4.0, 3.5, 3.0, 2.0 V. The output has the 23.8 µF + pinched dummy, with the crowbar connected and forced ON (worst case).
- **Measure:**
  - eFuse input current (overlap);
  - FET leakage with SHDN low;
  - with SHDN high: does the FET turn on, at what VIN, and is current limiting still active?
- **Pass:** with SHDN low, input current ≤ 10 mA at every VIN in 0–4.5 V and every temperature.
- **Record:** the internal POR thresholds (min and max seen).

### T2: TPS22810 tOFF, tD and EN deglitch (H2-C baseline; B uses the same method for the TPS22918)

- **Setup:** as T1a, with the as-built EN network (10 k / 1 nF Q2 RC included).
- **Measure:**
  - EN = VENF crossing → input current < 1 %;
  - EN rising → first input current > 10 mA (tD);
  - repeat with VIN = 5.0 V and VIN collapsing.
- **Conditions:** −40 / 25 / 85 °C.
- **Pass (H2-C):** tOFF_max + 2.5 µs (deglitch) < Q2 release time measured in T5. **Overlap (metric §1.3) = 0** in 500 cycles per temperature.
- **For the TPS22918 (B):** tOFF_max ≤ 5 µs over temperature, otherwise B fails R4.

### T3: Supervisor detection delay vs overdrive and ramp rate. Mandatory for both

- **DUTs:** TPS3703 (A) and TPS386000 (H2-C, B-TD).
- **Setup:** SENSE is driven by the fast-slew supply.
  - Steps of 2 %, 5 %, 10 % and 20 % overdrive.
  - Ramps of 0.01, 0.1, 1 and 10 V/ms through the threshold.
  - Pull-up as designed: 2.2 kΩ to 5 V for A; the as-built network for H2-C.
- **Measure:** threshold crossing → output ≤ 0.8 V.
- **Conditions:** −40 / 25 / 85 °C.
- **Pass:**

  | DUT | Overdrive | Limit |
  |---|---|---|
  | TPS3703 | 5 % | ≤ 30 µs (DS) |
  | TPS3703 | 2 % and slow ramps | ≤ 30 µs, otherwise the A budget must use the measured value + 50 % |
  | TPS386000 | — | ≤ 0.1 µs is needed for the as-built design to pass its own sim. **Expect FAIL;** record the value |

### T4: VOL at the real sink current vs temperature. Mandatory

| DUT | Test current | Limit |
|---|---|---|
| TPS3703 RESET | 2.5 mA (A: 2.2 kΩ to 5.08 V), VDD 4.9 V | ≤ 0.25 V |
| TPS3430 WDO | 2.5 mA, VDD 4.9 V | ≤ 0.4 V |
| TPS16630 FLT | 2.5 mA | ≤ 0.33 V (130 Ω) |
| TLV3202 output | 1 mA into the NMOS gate network | — |
| Baseline TPS386000 RESETn | 2.4 / 2.9 / 4.4 mA at VDD 1.3, 1.8, 3.3, 5 V, **during VDD ramp-down** | ≤ 0.3 V, otherwise B-M5a stands |

- **Method:** SMU on the output, DUT VDD from a precision supply, at −40 / 25 / 85 °C.
- **Pass for A:** VOL ≤ 0.35 V, so that P ≤ 0.35 V and SHDN_c ≤ 0.6 V without Q_sd, which is below V(SHUTF) min 0.8 V.

### T5: MOSFET VGS(th) and RDS(on) at −40 / +85 °C. Mandatory

- **DUTs:**
  - A: the crowbar FET (CSD16301Q2 or replacement), Q_sd, Q_t, and the ARM and gate-lost NMOS;
  - H2-C: DMG1012T Q2 / Q3 / Q966.
- **Measure:**
  - VGS(th) at 250 µA, and VGS at ID = 1.1 mA (H2-C Q2 hold current);
  - RDS(on) at VGS = 4.5 V and 3.0 V at 5 A (crowbar) or 10 mA (small FETs);
  - IDSS at VGS = 0 and 0.1 V, VDS = 5.5 V.
- **Pass for A:**
  - crowbar RDS(on) at +85 °C ≤ 58 mΩ (the PLACEHOLDER used in the 12.9 µs discharge term);
  - IDSS at VGS = 0.1 V, +85 °C ≤ 1 mA;
  - small-FET RDS(on) ≤ 10 Ω at VGS 4.5 V.
- **For H2-C:** feed the measured Q2 range into the as-built sim (replacing the 25 °C-only corners).

### T6: Crowbar pulse and overlap (energy test). Mandatory

- **Setup:** a full chain with the PA emulator (decoupling only, pinched) charged to 5.5 V by the eFuse. Fault injected by pulling P low through an OD (A), or PA_DRAIN_EN low (H2-C).
- **Measure:**
  - crowbar peak current and VOUT(t);
  - drain < 0.5 V time;
  - overlap metric;
  - R_CB resistance before and after.
- **Sequences:**
  1. 10 single events at 1 per minute.
  2. 100 events at 1 per minute. Check R_CB drift ≤ 1 %.
  3. **Rate test** at 1 per second for 60 events, to establish the arming-rate limit. Stop if ΔR > 1 % or R_CB > 120 °C (IR camera).
- **Pass for A:**
  - peak ≤ 27 A;
  - drain < 0.5 V ≤ 16.5 µs after P low;
  - overlap = 0 (resolution 10 ns);
  - ΔR_CB ≤ 1 % after sequence 2.

### T7: Crowbar timer delay and BBM margin at temperature (A). Mandatory

- **Measure:**
  - SHDN_c < 0.515 V → crowbar gate > 0.3 V (falling edge);
  - SHDN_c > 0.515 V → gate < 0.3 V (rising edge);
  - SHDN_c 0.515 → 0.8 V rise time.
- **Conditions:** −40 / 25 / 85 °C; VCB 4.77 and 5.08 V.
- **Pass:**
  - delay within 2.78–3.22 µs (DS-derived) ± 5 % measurement;
  - rising-edge margin ≥ 2.0 µs.
  - Combined with T1a: **delay_min − tSD_measured_max ≥ 1.0 µs**.

### T8: Rail-collapse and ordering matrix with dummy loads. Mandatory

- **Setup:** full interlock board, PA emulators on all 4 chains (two in quiescent load, two pinched). Each rail is supplied externally and can be collapsed or ramped independently:
  - +5V_IL;
  - VIN_12V;
  - +5V_PA;
  - +3V3_RF;
  - +3V3_AUX;
  - +1V8_DIG;
  - −5V_BF;
  - −3V3_SW.
- **Collapse runs:** each rail collapses at 0.01, 0.1, 1, 10 and 50 V/µs, and by a hard short (via a MOSFET to GND through 0.1 Ω).
- **Ordering runs:** 50 randomised power-up / power-down orders, reusing the sim seed list.
- **Measure:** P, SHDN_c ×4, gate ×4, VOUT ×4 (rotate channels), and the overlap metric.
- **Pass:**
  - drain < 0.5 V within **50 µs** of the rail crossing its monitor threshold by 5 %;
  - overlap = 0;
  - no eFuse turn-on at any time while any rail is outside its window. Trigger on SHDN_c > 0.8 V or input current > 10 mA.
- **Baseline:** run the same matrix on the H2-C prototype if one is built. The expected failures are those in the sim's pessimistic list.

### T9: ADAR1000 PA_BIAS with AVDD3 lost (B-ADAR / Ua13). Mandatory before any PA is fitted

- **Setup:** ADAR1000 evaluation board only, **no ADTR1107**. Each PA_BIAS output is loaded with 10 nF and, separately, with 49.9 kΩ to GND (the H2 Rg).
- **Supplies:**
  - AVDD3 (3.3 V) and AVDD1 (−5 V) from independent bench supplies;
  - AVDD1 adjustable −4.75…−5.25 V, plus an abs-max stress at −5.5 V for 1 s;
  - AVDD1 −6.7 V **not** applied.
- **Steps:**
  1. Program codes 0x00, 0x5D, 0x85 and 0xFF.
  2. Remove AVDD3 abruptly (switch) while AVDD1 stays up.
  3. Ramp AVDD3 down at 1 V/ms and 1 V/µs.
  4. Remove AVDD1 first.
  5. Power up in reversed order.
- **Conditions:** 25 °C, then −40 / +85 °C on the eval board.
- **Measure:** PA_BIAS1–4 vs time (4 channels); DAC full scale at 0xFF vs AVDD1 (headroom, for GATE_BIAS_ANALYSIS §3.4).
- **Pass (needed for TE2 closure):** PA_BIAS ≥ −2.0 V in every sequence at codes ≤ 0x5D, and PA_BIAS ≥ AVDD1 at all times.
- **Report:** the most negative value seen at any code, and whether the output follows AVDD1 when AVDD3 is absent.

### T10: TPS3430 WDO during VDD ramps, and WDI→WDO delay (DU1)

- **Setup:** VDD ramps 0 → 5 V and 5 → 0 V at 0.1 V/ms and 10 V/ms; WDI held static; WDO pulled up to the same VDD through 2.2 kΩ.
- **Measure:**
  - WDO vs VDD (confirms DU1: high for 0.8 < VDD < 1.6 V);
  - tRST;
  - WDI-stop → WDO low delay distribution.
- **Pass for A:** the guard (T11) makes DU1 irrelevant. Record values only.
- **Pass for H2-C:** none. DU1 is datasheet-defined.

### T11: Rail-guard and "undefined output never enables" (A)

- **Setup:** +5V_IL swept 0 → 5.1 V and back, at 0.01 V/ms and 10 V/µs.
  - Every monitor output is forced to its *released* state by disconnecting it (worst case).
  - Repeat with the monitors connected.
- **Measure:** UVLO_c; eFuse input current; SHDN_c.
- **Pass:**
  - eFuse never conducts (> 10 mA) for +5V_IL < 4.38 V;
  - FLT/UVLO trip at 3.89–4.0 V falling (computed from the measured k and V(UVLOF));
  - with the monitors connected, P stays low until all rails are valid plus tD.

### T12: +5V_PA over-voltage injection (F-5V)

- **Setup:**
  - No PA; chains loaded with the PA emulators.
  - Emulate the FB-open failure by driving +5V_PA from a current-limited source: 12 V through a 2.2 µH inductor and series switch, limited to 12 A peak, into the 235 µF bulk.
  - Also apply a slow 5.0 → 6.0 V ramp at 1 V/ms.
- **Measure:** VOUT_c peak; time above 5.5 V; TLV3202 fast-OV trip time; TPS16630 OVP; crowbar action.
- **Pass:**
  - VOUT_c ≤ 5.5 V at all times, or above 5.5 V for ≤ 2 µs, with the peak value reported to ADI (M6);
  - the eFuse latches off;
  - P stays low.

### T13: Drain decoupling and timing parasitics (supporting measurements)

| Item | Method | Pass |
|---|---|---|
| Effective chain capacitance | Capacitance at 5 V DC bias, LCR with bias, at 25 °C and −40 °C (the upper bound matters for discharge) | ≤ 23.8 µF |
| Crowbar loop inductance | From the di/dt at turn-on | ≤ 20 nH |
| SHDN pin capacitance and V(SHUTR) − V(SHUTF) hysteresis | TPS16630, slow triangle on SHDN | Hysteresis ≥ 0 (assumption in the rising-edge BBM proof) |

## 3. Exit criteria

1. T1a, T1b, T3, T4, T5, T6, T7, T8, T9 and T11 all pass.
2. Each measured value is ≤ 0.5 × the margin it consumes in `sim/budget.py`; otherwise the budget is re-run with the measured value + 50 %.
3. The manufacturer answers M1, M2 and M4–M7 (ARCH_COMPARE §7.1) are received. If an answer contradicts a bench value, the answer wins.
4. TE2 (gate bias) is resolved separately (R6) using T9 and ADI's answers.
