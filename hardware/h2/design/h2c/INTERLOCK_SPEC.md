# H2-C PA-drain safety interlock — specification

- Date: 2026-11-12. Status: **design only**. No KiCad file has been edited, and nothing is committed.
- Inputs used: ADAR1000 / ADTR1107 notes and the H2B_ELECTRICAL_SAFETY_REVIEW (local), plus these TI datasheets, downloaded from ti.com to `interlock/ds/`:

| Part | Doc | Used for |
|---|---|---|
| LM339B | SLCS006Z (May 2025) | pins p4, abs max p5, ROC p6, LM339B EC p7, LMx39 EC p10, switching p12 |
| SN74LVC1G74 | SCES794G (Sep 2021) | pins p4, abs max and ROC p6, timing p7, §9.1 |
| SN74LVC1G17 | SCES351Y (Oct 2025) | pins p3, VT± p6, tpd p7 |
| SN74LVC1G11 | SCES487I (Nov 2024) | pins p3, tpd p6 |
| TPS22810 | SLVSDH0C (Jan 2018) | EN thresholds and leakage p5, RPD p6, tOFF/tD p7 |

## 1. Summary of the design

```
C{c}_PABIAS{k} ──49.9k──┬──17.4k── +1V8_DIG        (×16, node IL_G{c}{k})
                        └──45.3k── GND
IL_G.. → LM339B(−) vs IL_REF_LOST (+)  → open collector → NEG_OK        (gate > −0.15 V ⇒ low)
IL_G.. → LM339B(−) vs IL_REF_PINCH(+)  → open collector → GATES_PINCHED (gate > −1.5 V  ⇒ low)
-5V_BF  ──49.9k── IL_N5V  ──12.4k── +1V8_DIG ; LM339B(−)=IL_N5V,  (+)=IL_REF_N5V  → NEG_OK
-3V3_SW ──49.9k── IL_N3V3 ──12.4k── +1V8_DIG ; LM339B(−)=IL_N3V3, (+)=IL_REF_N3V3 → NEG_OK
NEG_OK, GATES_PINCHED pull-up: 10k from +3V3_AUX, 10k to GND  (Thevenin 1.65 V / 5 k)

U911 (LVC1G11): IL_CLR_N = MCU_PA_EN · WDT_OK · NEG_OK
MCU_PA_EN ─R964 10k─ IL_CLK_RC ─C912 1nF─GND ; U910 (LVC1G17 Schmitt) → IL_CLK
U909 (LVC1G74): D=GATES_PINCHED, CLK=IL_CLK, ~CLR=IL_CLR_N, ~PRE=+1V8_DIG, Q=PA_ARMED
U705 (LVC1G11, existing): PA_DRAIN_EN = PA_ARMED · WDT_OK · NEG_OK ; R965 100k PA_DRAIN_EN→GND
```

Parts: 34 comparator channels (16 gate-lost, 16 gate-pinched, 2 rails), so 9 × LM339B (U900–U908, with 2 spare channels). Also 1 × LVC1G74, 1 × LVC1G17, 1 × LVC1G11, 66 resistors and 13 capacitors.

### Deviations from the brief, and why

1. **The NEG_OK and GATES_PINCHED pull-ups go to +3V3_AUX (10 k), with 10 k to GND. They do not go to +1V8_DIG.**
   - When +3V3_AUX is absent, the LM339 is unpowered and its open-collector outputs cannot sink. A pull-up to +1V8_DIG would then read NEG_OK = 1 and enable the drain. That fails unsafe.
   - With the Thevenin pull-up, a missing +3V3_AUX gives 0 V on the node, so the interlock fails safe.
   - The high level is 3.3 × ½ = 1.57–1.73 V for +3V3_AUX ±5 %. That is above the LVC VIH of 0.65 × VCC (1.27 V max at VCC = 1.95 V, SCES794G p6) and below the 2.0 V ADAR1000 digital abs max, in case the MCU or anything else reads NEG_OK.
   - LVC inputs accept 5.5 V even when unpowered (abs max p6; Ioff).
2. **The gate dividers use three resistors (gate, +1V8_DIG and GND), not two.**
   - A two-resistor divider cannot keep the node ≥ 0 V at gate = −4.8 V and also hold the trip-point node ≤ VCC − 2 V. With VCC = +3V3_AUX − 5 %, that limit is 1.135 V (LM339B VCM, full temperature, p7).
   - With two resistors, the ratio α has to satisfy both α ≥ 0.737 and α ≤ 0.613, which is impossible. See §3.1.
3. **The flop's ~CLR is driven by `IL_CLR_N` = MCU_PA_EN · WDT_OK · NEG_OK (new U911), not by MCU_PA_EN alone.**
   - Without this, a transient fault would turn the drain off. When the fault clears, NEG_OK returns high and the drain would come back on with the gate at its ON bias. That re-enables the drain **without** the pinch check.
   - With U911, any fault is latched until the MCU toggles MCU_PA_EN with the gates pinched.
4. **The clock is delayed (RC + Schmitt buffer U910), so there is no CLR-release/CLK race.** See §4.
5. **LM339B, not plain LM339.**
   - Same die family and pinout, and the same KiCad symbol (`Comparator:LM339`).
   - LM339B: VIO ±5.5 mV and IB 50 nA over −40…85 °C (p7), rated for TA −40…85 °C (p6).
   - Plain LM339: VIO 9 mV and IB 400 nA, and it is rated for 0…70 °C only (p10, p6).
   - With the plain part, the bias-current error alone would be 2 × 400 nA × 10 k = 8 mV at the node, which is 40 mV at the gate.
6. **No 74LVC1G74 symbol exists in the KiCad 9 `74xGxx` library.** Use `74xGxx:74AUC1G74` with Value = SN74LVC1G74. Its pins are identical to TI's DCU pinout: 1 CLK (named `C` in the symbol), 2 D, 3 ~Q, 4 GND, 5 Q, 6 ~CLR, 7 ~PRE, 8 VCC (SCES794G p4).

## 2. Assumptions to confirm

- **Rail tolerances.** +1V8_DIG is assumed ±3 % and +3V3_AUX ±5 %. Both regulators (U603, U606) are still placeholders.
  - All trip points scale with +1V8_DIG (ratiometric), so its tolerance appears directly in the trip points. The 1V8 sensitivity at each trip is listed in §3.4.
- **Gate drive.** The PA_BIAS DACs drive 0 … −4.8 V and cannot go below AVDD1 (= −5V_BF, worst case −5.25 V).
- **Negative rails.** The negative rails are taken over the range 0 … −6 V.

## 3. Analogue calculations

### 3.1 Why two-resistor gate dividers fail

A two-resistor divider gives V_node = α·V18 + (1−α)·Vg. It must meet two limits:

- **Node ≥ 0 V** at Vg = −4.8 V and V18 = 1.71 V. This is the low end of VICR, "0 to VCC−2" (LMx39 p10; LM339B p7, (V−)). It requires α ≥ 4.8/6.51 = **0.737**.
- **Node ≤ 1.135 V at the −0.15 V trip.** At that point both comparator inputs sit at the node voltage, so both must be inside VICR. VICR is V+ − 2.0 V over full temperature, with V+ = 3.135 V (LM339B p7). With V18 = 1.854 V this requires α ≤ 1.25/2.004 = **0.613**.

The two limits contradict each other. Adding a third resistor to GND lowers the +1V8 weight `a` without raising the gate weight `b`, which removes the conflict.

### 3.2 Gate divider (×16)

The divider is Rg = 49.9 k (gate→node), Rt = 17.4 k (+1V8→node) and Rn = 45.3 k (node→GND), all 0.1 %.

- Node voltage: V_node = a·V18 + b·Vg, with **a = 0.57710** and **b = 0.20123**.
- Node source resistance: Rth = 10.04 k.

| Check | Value | Limit |
|---|---|---|
| node at Vg = −4.8 V, V18 = 1.746 V (−3 %) | +0.042 V | ≥ 0 V (VICR min) |
| node at Vg = −4.8 V, V18 = 1.71 V (−5 %) | +0.021 V | ≥ 0 V |
| node at Vg = −5.25 V (DAC at the AVDD1 limit), V18 −5 % | −0.070 V | > −0.3 V (abs max; output stays correct, p7 note 1) |
| node at Vg = 0 V (DAC reset), V18 +3 % | 1.070 V | ≤ 1.135 V. Not required, because only one input must be in range (p7 note 1), but it is met |
| DAC load (Thevenin seen by PA_BIAS: 1.30 V behind 62.5 k) | 38 µA @ −1.1 V; 49 µA @ −1.75 V; 98 µA @ −4.8 V | PA_BIAS ±10 mA (ADAR1000 p7) |
| bias-current error at the node | 2 inputs × 50 nA × 10.04 k = 1.0 mV, i.e. 5 mV at the gate | LM339B IB max 50 nA (p7) |

### 3.3 Rail dividers (−5V_BF, −3V3_SW)

The divider is Rr = 49.9 k (rail→node) and Rt = 12.4 k (+1V8→node), 0.1 %. This gives **a = 0.80096**, **b = 0.19904** and Rth = 9.93 k.

- Node at a −6 V rail: +0.204 V with V18 −3 %, and +0.175 V with V18 −5 %. Both are ≥ 0 ✓.
- Node at a 0 V rail is 1.44 V, above VICR. That is allowed, because the reference input stays in range and the comparator still gives a valid output (p7 note 1; p10 note 3).

### 3.4 Thresholds (reference dividers, 0.1 %, from +1V8_DIG to GND)

| Net | Rtop / Rbot | V at 1.80 V | Trip (nominal) | Worst case* | +1V8 ±3 % share |
|---|---|---|---|---|---|
| IL_REF_LOST | R952 2.15 k / R953 2.74 k | 1.0086 V | gate −0.150 V | **−0.191 … −0.110 V** | ±4.5 mV |
| IL_REF_PINCH | R954 1.47 k / R955 1.02 k | 0.7373 V | gate −1.498 V | **−1.584 … −1.416 V** | ±45 mV |
| IL_REF_N5V | R956 3.92 k / R957 1.62 k | 0.5264 V | −5V_BF −4.599 V | **−4.781 … −4.420 V** | ±138 mV |
| IL_REF_N3V3 | R958 1.21 k / R959 1.07 k | 0.8447 V | −3V3_SW −2.999 V | **−3.132 … −2.870 V** | ±90 mV |
| IL_V33MON (on +3V3_AUX) | R966 46.4 k / R967 10.0 k, compared with IL_REF_N5V | — | +3V3_AUX 2.97 V | ≈ 2.85 … 3.09 V | — |

\* The worst case is an exhaustive corner search over:
- each resistor ±0.1 %;
- +1V8_DIG ±3 %;
- LM339B VIO ±5.5 mV (−40…85 °C, p7);
- IB 0 … 50 nA out of every input on the node and on the reference. A reference node carries up to 18 inputs.

The script is `interlock/calc/calc.py`. Resistor tempco (25 ppm/K) is not included. All parts are the same type, so ratio drift is small, but this is unverified.

Margins:
- **Gate-lost.** The highest gate setting that ADTR1107 still allows for 220 mA is −0.25 V (p3). The trip window ends at −0.191 V, giving ≥ 59 mV margin, so there are no nuisance trips. A reset gate at 0 V (ADAR1000 p41) is always caught.
- **Pinch.** The OFF value is −1.75 V (0x5D firmware limit). The worst trip is −1.584 V, giving 166 mV margin. Not counted here: DAC error, which the datasheet does not give and the bench pre-check measures.
- **−5V_BF.** ⚠ The worst-case trip of −4.78 V lies **inside** the ADAR1000 AVDD1 range of −4.75 … −5.25 V. That can only cause nuisance trips when the rail is at its low edge; it never trips late. To tighten it, use a ±1 % +1V8_DIG regulator, which gives −4.70 … −4.50 V.
- **References.** All four reference nodes stay ≤ 1.039 V (V18 +3 %), inside VICR at V+ ≥ 3.04 V.

No hysteresis is added, deliberately:
- Chatter on NEG_OK clears the latch through U911 on its first low pulse, and the latch then stays off. Chatter there is therefore fail-safe.
- GATES_PINCHED is sampled once, with the gates settled ≥ 166 mV from the threshold.

### 3.5 Pull-ups and loads

- **NEG_OK / GATES_PINCHED.**
  - High level: 1.57–1.73 V (+3V3_AUX ±5 %) behind 5 k, so the sink current is 0.33 mA. VOL at 4 mA is ≤ 400 mV (p7), well below VIL = 0.35 × 1.65 = 0.58 V (SCES794G p6).
  - Leakage: 19 open collectors × 100 nA max (p7) × 5 k gives < 10 mV.
  - Rise time: about 5 k × 100 pF ≈ 0.5 µs. Only the enabling edge is this slow.
- **+1V8_DIG load:** about 3.4 mA. That is 16 × ~60 µA for the gate dividers, 2.2 mA for the reference dividers and 0.3 mA for the rail dividers.
- **+3V3_AUX load:** ≤ 9 × 1.2 mA (LM339B IQ, p7) + 0.7 mA, i.e. ≤ 12 mA.

## 4. Enable latch: flop analysis

- **~CLR polarity.** ~CLR is active-low ("Pull low to set Q output low", SCES794G p4). Driving it from MCU_PA_EN, low = clear, is the correct sense.
- **The race.** If CLK and ~CLR were both MCU_PA_EN, the CLR release would have to come ≥ **tsu(PRE or CLR inactive) = 1.9 ns** before CLK↑ at 1.8 V (p7).
  - With the same edge, that margin is 0 ns.
  - With U911 in the ~CLR path (tpd 2.6–15.2 ns, SCES487I p6), CLR is released **after** the clock edge.
  - TI does not specify what the flop does when this setup time is violated, so capture is **undefined**. It might fail to arm or go metastable. That is not acceptable.
- **The fix.** CLK = MCU_PA_EN → R964 10 k / C912 1 nF (τ = 10 µs) → U910 SN74LVC1G17 Schmitt buffer.
  - U910's VT+ is 0.76–1.13 V at VCC 1.65 V (SCES351Y p6).
  - Delay t = τ·ln(V_H/(V_H − VT+)) = **5.5–9.9 µs** for V_H = 1.8 V, and ≤ 10.8 µs for V_H = 1.71 V. U910 adds tpd ≤ 9.9 ns (p7).
  - The required lead is 15.2 + 1.9 = 17.1 ns, so the margin is more than 300×.
  - The Schmitt buffer is mandatory: the LVC1G74 needs input edges of Δt/Δv ≤ 20 ns/V at 1.8 V (p6), and a raw RC edge is about 5 µs/V.
- **D = GATES_PINCHED.** tsu(data) = 2.9 ns and th = 0 (p7). GATES_PINCHED must be static for ≥ 2 µs before the delayed edge, which covers LM339 response plus pull-up rise.
  - **Firmware rule:** with MCU_PA_EN low:
    1. Write every EXT_PAx_BIAS_OFF ≤ 0x5D.
    2. Select OFF (TR low or PA_ON low).
    3. Wait ≥ 50 µs, which covers the 10 nF gate settle.
    4. Raise MCU_PA_EN.
    5. After ≥ 20 µs, check that VOUT or PA_ARMED is up. PA_ARMED is optionally routed to an MCU GPIO.
- **Falling MCU_PA_EN or any fault.** IL_CLR_N falls within 15.2 ns, and Q is low after CLR→Q tpd ≤ 14.4 ns (p7). The CLK fall about 5–10 µs later is ignored, because the flop triggers on the rising edge only. A glitch on MCU_PA_EN shorter than about 5 µs never clocks, so it never arms.
- **Power-up.** The MCU_PA_EN 100 k pull-down holds ~CLR low, so Q = 0 whatever the flop's initial state. ~PRE is tied to +1V8_DIG and ~Q is not connected.

## 5. U705 after the change

Remove U609 (the NEG_OK placeholder). NEG_OK is now driven only by the open collectors of U900–U908 plus R960/R961.

| U705 pin (74LVC1G11, KiCad pins) | Net |
|---|---|
| 1 (A) | **PA_ARMED**. This replaces MCU_PA_EN. If MCU_PA_EN is on a different input today, swap that input instead. |
| 3 (B) | WDT_OK (unchanged) |
| 6 (C) | NEG_OK (unchanged net name; the driver changes) |
| 4 (Y) | PA_DRAIN_EN |
| 5 (VCC) | +1V8_DIG |
| 2 (GND) | GND |

- MCU_PA_EN keeps its 100 k pull-down and now drives U911 pin 1 and R964.
- Add R965 100 k from PA_DRAIN_EN to GND unless a pull-down already exists. With +1V8_DIG absent, the LVC outputs are disabled by Ioff (SCES487I), and TPS22810 EN has no internal pull-down, only 0.1 µA leakage (SLVSDH0C p5).

## 6. Response times (typical; TI gives no maximum for these parameters)

| Event | Chain | Time to VOUT starting to fall (EN 50 % → VOUT 90 %) |
|---|---|---|
| Gate crosses −0.15 V | LM339B ≈ 1.0 µs (LM339B, p12) / 1.3 µs (LMx39, p12) + pull-down of NEG_OK below 0.58 V (≈ 0.1 µs) + U705 ≤ 15.2 ns + TPS22810 tOFF 3.3 µs (p7) | **≈ 4.7 µs typ**. Budget 8 µs, allowing 2× on the comparator. |
| −5V_BF rises past −4.6 V | same chain | ≈ 4.7 µs after the crossing |
| WDT_OK falls | U705 ≤ 15.2 ns + tOFF 3.3 µs | ≈ 3.3 µs. TPS3430 internal delay not included. |
| Parallel latch path | U911 15.2 ns + CLR→Q 14.4 ns, then U705 | about 30 ns slower than the direct path. This path is redundant. |

Notes on these times:
- The LM339 test conditions are VS = 5 V and 5.1 k to 5 V with 5 mV overdrive (p12).
- A gate stepping from −1.1 V to 0 V gives 30 mV of node overdrive at the trip point, so the 5 mV-overdrive figure is conservative.
- After tOFF, VOUT decays through QOD at RPD = 250–400 Ω (p6) into the +5V_PA_C{c} bulk capacitance, while the PA draws its own current. With 10 µF of bulk and no PA current, the QOD time constant is 2.5–4 ms. The "S2" gap is closed only if the gate stays valid for that long.
- The −5V_BF trip at −4.6 V gives early warning: the DAC can still hold −1.1 V until AVDD1 nears the gate value. ADAR1000 does not state the DAC's headroom, so the lead time is **unverified**.

## 7. Supply-loss behaviour (fail-safe matrix)

| Condition | What happens | Drain |
|---|---|---|
| +3V3_AUX absent | The LM339s are unpowered and their outputs float. R961/R963 pull NEG_OK and GATES_PINCHED to 0 V, which drives IL_CLR_N low, clears PA_ARMED and holds U705 low. Comparator inputs up to 1.8 V with V+ = 0 are within the 38 V input abs max (p5). | **off** |
| +3V3_AUX at 2.34–2.97 V (brown-out or ramp) | The NEG_OK high level V33/2 is below VIH 1.17 V when V33 < 2.34 V. Above that, the spare channel (IL_V33MON < IL_REF_N5V) pulls NEG_OK low up to about 2.97 V. Without that channel, IL_REF_LOST (1.0 V) would leave VICR once V+ < 3.04 V. | **off** |
| +1V8_DIG absent | U705, U909 and U911 are unpowered. R965 holds PA_DRAIN_EN at about 10 mV, far below VENF 1.08 V. | **off** |
| +1V8_DIG brown-out, 1.2–1.65 V | Trips scale with V18: at 1.2 V, gate-lost is −0.10 V and −5V_BF trips at −3.07 V. LVC operation is unspecified below 1.65 V. The TPS22810 turns off when EN < 1.08–1.18 V, which happens once V18 falls below about 1.2 V. | partly protected. This is residual risk R3 below. |
| −5V_BF or −3V3_SW absent/collapsing | Rail comparators trip at the §3.4 thresholds | **off, latched** |
| ADAR1000 reset (PA_BIAS = 0 V) | gate-lost trips | **off, latched** |
| Watchdog | WDT_OK feeds both U705 and IL_CLR_N | **off, latched** |

## 8. Flaws and residual risks found

1. **F1 (fixed): pull-up to +1V8_DIG fails unsafe when +3V3_AUX is absent.**
   - The unpowered LM339 cannot pull NEG_OK low, so it would read high.
   - Fixed by the Thevenin pull-up from +3V3_AUX (§1, deviation 1).
2. **F2 (fixed): the two-resistor divider cannot meet the LM339 input range.**
   - Fixed by the 3-resistor gate divider (§3.1).
3. **F3 (fixed): CLK and CLR released by the same edge is undefined.**
   - It violates tsu(CLR inactive) = 1.9 ns.
   - Fixed by RC + LVC1G17 delay (§4).
4. **F4 (fixed): the drain could re-enable after a transient fault without the pinch check.**
   - Fixed by IL_CLR_N = MCU_PA_EN · WDT_OK · NEG_OK, which latches the fault.
5. **F5 (fixed): no pull-down on PA_DRAIN_EN.**
   - The EN pin has no internal pull-down, and LVC outputs are high-Z under Ioff. R965 fixes this.
6. **F6 (fixed): comparator accuracy is lost below +3V3_AUX ≈ 3.04 V.**
   - Fixed with a spare channel used as a +3V3_AUX UV monitor.
7. **F7 (fixed): plain LM339 is not accurate enough.**
   - It is rated 0–70 °C and its IB is 400 nA. LM339B is specified instead.
8. **R1 (open): positive voltage injected onto VGG_PA when the DAC is not driving.**
   - Every gate divider has an open-circuit Thevenin of **+1.30 V behind 62.5 kΩ**. If the ADAR1000 is unpowered while +1V8_DIG is up, PA_BIAS is not driven. The gate is then pulled positive and clamped by the GaAs gate diode at ≤ ≈ 11 µA.
   - That breaks the ADTR1107 VGG_PA abs max of "−2 V to +0 V" (Table 6, p6). The drain is off at the time.
   - Options:
     - (a) A Schottky clamp from gate to GND per PA, e.g. BAT54. It limits the gate to about +0.2 V, and its leakage at −1.75 V is µA-level.
     - (b) Power +1V8_DIG's divider leg only when the ADAR1000 AVDD3 is up. This costs ratiometric accuracy.
     - (c) Add this to ADI inquiry 5a.
   - Recommendation: (a), if the bench confirms that its leakage does not shift bias.
9. **R2 (open): LM339 inputs below −0.3 V when +1V8_DIG is absent but the negative rails are up.**
   - The nodes reach about −0.2·|V|, i.e. down to −1.0 V. Current is limited to < 50 µA by the 10 k Rth, against an input-current abs max of 50 mA (p5).
   - The voltage still exceeds the VI abs max. The drain is held off by R965, so this is a stress item, not a safety one.
   - Optional fix: a BAT54S on each node.
10. **R3 (open): +1V8_DIG brown-out between 1.2 and 1.65 V.**
    - In this window the LVC gates are outside their specified range and the thresholds have shifted.
    - Recommendation: give U603 a voltage supervisor. Its RESET should be wired into IL_CLR_N, e.g. replacing WDT_OK if the TPS3430 has no UV function. Not checked.
11. **R4 (open): gate over-range below −2 V (S1) is still firmware-only.**
    - The same divider can detect it: add a third reference at −1.9 V, i.e. 16 more channels, which is 4 more LM339B.
    - Not added, because it is outside this brief.
12. **R5 (layout): place each Rg at the ADTR1107 VGG_PA pin, not at the ADAR1000.**
    - Then an open trace pulls the gate node positive and trips the gate-lost comparator.
13. **R6: LM339 response time and TPS22810 tOFF have typical values only.**
    - Measure both on the bench.
14. **R7 (MPNs): MPNs follow the vendor naming patterns but were not checked against distributor stock.**
    - The patterns are Panasonic ERA-2AEB 0402 0.1 % 25 ppm, ERJ-2RKF 1 %, and Murata GRM155.

## 9. Placement table

KiCad pin numbers come from `get_symbol_info`. The comparator pin pairs are (2 | 4−, 5+), (1 | 6−, 7+), (14 | 8−, 9+) and (13 | 10−, 11+), which matches the TI D-package pinout (p4, with TI's channel-1/2 naming note). Use `SOIC-14_3.9x8.7mm_P1.27mm` for the LM339B D package. For the LVC1G74, the DCU footprint is `VSSOP-8_2.3x2mm_P0.5mm` (JEDEC MO-187). For the LVC1G17 and LVC1G11 DCK footprints, use `Texas_R-PDSO-G5_DCK-5` and `SOT-363_SC-70-6`. All footprints exist under /usr/share/kicad/footprints.

Comparator gate assignment:
- U900: C1_PABIAS1, C1_PABIAS2
- U901: C1_PABIAS3, C1_PABIAS4
- U902: C2_PABIAS1, C2_PABIAS2
- U903: C2_PABIAS3, C2_PABIAS4
- U904: C3_PABIAS1, C3_PABIAS2
- U905: C3_PABIAS3, C3_PABIAS4
- U906: C4_PABIAS1, C4_PABIAS2
- U907: C4_PABIAS3, C4_PABIAS4

Gate-divider resistors: for gate n (0 = C1_PABIAS1 … 15 = C4_PABIAS4), Rg = R(900+3n), Rt = R(901+3n) and Rn = R(902+3n).

| ref | lib_id | value | footprint | MPN | pin→net |
|---|---|---|---|---|---|
| R900 | Device:R | 49.9k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4992X | 1→C1_PABIAS1, 2→IL_G11 |
| R901 | Device:R | 17.4k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB1742X | 1→+1V8_DIG, 2→IL_G11 |
| R902 | Device:R | 45.3k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4532X | 1→IL_G11, 2→GND |
| R903 | Device:R | 49.9k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4992X | 1→C1_PABIAS2, 2→IL_G12 |
| R904 | Device:R | 17.4k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB1742X | 1→+1V8_DIG, 2→IL_G12 |
| R905 | Device:R | 45.3k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4532X | 1→IL_G12, 2→GND |
| R906 | Device:R | 49.9k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4992X | 1→C1_PABIAS3, 2→IL_G13 |
| R907 | Device:R | 17.4k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB1742X | 1→+1V8_DIG, 2→IL_G13 |
| R908 | Device:R | 45.3k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4532X | 1→IL_G13, 2→GND |
| R909 | Device:R | 49.9k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4992X | 1→C1_PABIAS4, 2→IL_G14 |
| R910 | Device:R | 17.4k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB1742X | 1→+1V8_DIG, 2→IL_G14 |
| R911 | Device:R | 45.3k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4532X | 1→IL_G14, 2→GND |
| R912 | Device:R | 49.9k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4992X | 1→C2_PABIAS1, 2→IL_G21 |
| R913 | Device:R | 17.4k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB1742X | 1→+1V8_DIG, 2→IL_G21 |
| R914 | Device:R | 45.3k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4532X | 1→IL_G21, 2→GND |
| R915 | Device:R | 49.9k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4992X | 1→C2_PABIAS2, 2→IL_G22 |
| R916 | Device:R | 17.4k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB1742X | 1→+1V8_DIG, 2→IL_G22 |
| R917 | Device:R | 45.3k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4532X | 1→IL_G22, 2→GND |
| R918 | Device:R | 49.9k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4992X | 1→C2_PABIAS3, 2→IL_G23 |
| R919 | Device:R | 17.4k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB1742X | 1→+1V8_DIG, 2→IL_G23 |
| R920 | Device:R | 45.3k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4532X | 1→IL_G23, 2→GND |
| R921 | Device:R | 49.9k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4992X | 1→C2_PABIAS4, 2→IL_G24 |
| R922 | Device:R | 17.4k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB1742X | 1→+1V8_DIG, 2→IL_G24 |
| R923 | Device:R | 45.3k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4532X | 1→IL_G24, 2→GND |
| R924 | Device:R | 49.9k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4992X | 1→C3_PABIAS1, 2→IL_G31 |
| R925 | Device:R | 17.4k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB1742X | 1→+1V8_DIG, 2→IL_G31 |
| R926 | Device:R | 45.3k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4532X | 1→IL_G31, 2→GND |
| R927 | Device:R | 49.9k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4992X | 1→C3_PABIAS2, 2→IL_G32 |
| R928 | Device:R | 17.4k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB1742X | 1→+1V8_DIG, 2→IL_G32 |
| R929 | Device:R | 45.3k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4532X | 1→IL_G32, 2→GND |
| R930 | Device:R | 49.9k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4992X | 1→C3_PABIAS3, 2→IL_G33 |
| R931 | Device:R | 17.4k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB1742X | 1→+1V8_DIG, 2→IL_G33 |
| R932 | Device:R | 45.3k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4532X | 1→IL_G33, 2→GND |
| R933 | Device:R | 49.9k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4992X | 1→C3_PABIAS4, 2→IL_G34 |
| R934 | Device:R | 17.4k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB1742X | 1→+1V8_DIG, 2→IL_G34 |
| R935 | Device:R | 45.3k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4532X | 1→IL_G34, 2→GND |
| R936 | Device:R | 49.9k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4992X | 1→C4_PABIAS1, 2→IL_G41 |
| R937 | Device:R | 17.4k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB1742X | 1→+1V8_DIG, 2→IL_G41 |
| R938 | Device:R | 45.3k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4532X | 1→IL_G41, 2→GND |
| R939 | Device:R | 49.9k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4992X | 1→C4_PABIAS2, 2→IL_G42 |
| R940 | Device:R | 17.4k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB1742X | 1→+1V8_DIG, 2→IL_G42 |
| R941 | Device:R | 45.3k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4532X | 1→IL_G42, 2→GND |
| R942 | Device:R | 49.9k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4992X | 1→C4_PABIAS3, 2→IL_G43 |
| R943 | Device:R | 17.4k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB1742X | 1→+1V8_DIG, 2→IL_G43 |
| R944 | Device:R | 45.3k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4532X | 1→IL_G43, 2→GND |
| R945 | Device:R | 49.9k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4992X | 1→C4_PABIAS4, 2→IL_G44 |
| R946 | Device:R | 17.4k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB1742X | 1→+1V8_DIG, 2→IL_G44 |
| R947 | Device:R | 45.3k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4532X | 1→IL_G44, 2→GND |
| R948 | Device:R | 12.4k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB1242X | 1→+1V8_DIG, 2→IL_N5V |
| R949 | Device:R | 49.9k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4992X | 1→-5V_BF, 2→IL_N5V |
| R950 | Device:R | 12.4k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB1242X | 1→+1V8_DIG, 2→IL_N3V3 |
| R951 | Device:R | 49.9k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4992X | 1→-3V3_SW, 2→IL_N3V3 |
| R952 | Device:R | 2.15k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB2151X | 1→+1V8_DIG, 2→IL_REF_LOST |
| R953 | Device:R | 2.74k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB2741X | 1→IL_REF_LOST, 2→GND |
| R954 | Device:R | 1.47k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB1471X | 1→+1V8_DIG, 2→IL_REF_PINCH |
| R955 | Device:R | 1.02k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB1021X | 1→IL_REF_PINCH, 2→GND |
| R956 | Device:R | 3.92k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB3921X | 1→+1V8_DIG, 2→IL_REF_N5V |
| R957 | Device:R | 1.62k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB1621X | 1→IL_REF_N5V, 2→GND |
| R958 | Device:R | 1.21k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB1211X | 1→+1V8_DIG, 2→IL_REF_N3V3 |
| R959 | Device:R | 1.07k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB1071X | 1→IL_REF_N3V3, 2→GND |
| R966 | Device:R | 46.4k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB4642X | 1→+3V3_AUX, 2→IL_V33MON |
| R967 | Device:R | 10.0k 0.1% 25ppm | Resistor_SMD:R_0402_1005Metric | Panasonic ERA-2AEB1002X | 1→IL_V33MON, 2→GND |
| R960 | Device:R | 10k 1% | Resistor_SMD:R_0402_1005Metric | Panasonic ERJ-2RKF1002X | 1→+3V3_AUX, 2→NEG_OK |
| R961 | Device:R | 10k 1% | Resistor_SMD:R_0402_1005Metric | Panasonic ERJ-2RKF1002X | 1→NEG_OK, 2→GND |
| R962 | Device:R | 10k 1% | Resistor_SMD:R_0402_1005Metric | Panasonic ERJ-2RKF1002X | 1→+3V3_AUX, 2→GATES_PINCHED |
| R963 | Device:R | 10k 1% | Resistor_SMD:R_0402_1005Metric | Panasonic ERJ-2RKF1002X | 1→GATES_PINCHED, 2→GND |
| R964 | Device:R | 10k 1% | Resistor_SMD:R_0402_1005Metric | Panasonic ERJ-2RKF1002X | 1→MCU_PA_EN, 2→IL_CLK_RC |
| R965 | Device:R | 100k 1% | Resistor_SMD:R_0402_1005Metric | Panasonic ERJ-2RKF1003X | 1→PA_DRAIN_EN, 2→GND |
| U900 | Comparator:LM339 | LM339B | Package_SO:SOIC-14_3.9x8.7mm_P1.27mm | TI LM339BIDR | 3→+3V3_AUX, 12→GND; 4(−)→IL_G11, 5(+)→IL_REF_LOST, 2→NEG_OK; 6(−)→IL_G11, 7(+)→IL_REF_PINCH, 1→GATES_PINCHED; 8(−)→IL_G12, 9(+)→IL_REF_LOST, 14→NEG_OK; 10(−)→IL_G12, 11(+)→IL_REF_PINCH, 13→GATES_PINCHED |
| U901 | Comparator:LM339 | LM339B | Package_SO:SOIC-14_3.9x8.7mm_P1.27mm | TI LM339BIDR | 3→+3V3_AUX, 12→GND; 4(−)→IL_G13, 5(+)→IL_REF_LOST, 2→NEG_OK; 6(−)→IL_G13, 7(+)→IL_REF_PINCH, 1→GATES_PINCHED; 8(−)→IL_G14, 9(+)→IL_REF_LOST, 14→NEG_OK; 10(−)→IL_G14, 11(+)→IL_REF_PINCH, 13→GATES_PINCHED |
| U902 | Comparator:LM339 | LM339B | Package_SO:SOIC-14_3.9x8.7mm_P1.27mm | TI LM339BIDR | 3→+3V3_AUX, 12→GND; 4(−)→IL_G21, 5(+)→IL_REF_LOST, 2→NEG_OK; 6(−)→IL_G21, 7(+)→IL_REF_PINCH, 1→GATES_PINCHED; 8(−)→IL_G22, 9(+)→IL_REF_LOST, 14→NEG_OK; 10(−)→IL_G22, 11(+)→IL_REF_PINCH, 13→GATES_PINCHED |
| U903 | Comparator:LM339 | LM339B | Package_SO:SOIC-14_3.9x8.7mm_P1.27mm | TI LM339BIDR | 3→+3V3_AUX, 12→GND; 4(−)→IL_G23, 5(+)→IL_REF_LOST, 2→NEG_OK; 6(−)→IL_G23, 7(+)→IL_REF_PINCH, 1→GATES_PINCHED; 8(−)→IL_G24, 9(+)→IL_REF_LOST, 14→NEG_OK; 10(−)→IL_G24, 11(+)→IL_REF_PINCH, 13→GATES_PINCHED |
| U904 | Comparator:LM339 | LM339B | Package_SO:SOIC-14_3.9x8.7mm_P1.27mm | TI LM339BIDR | 3→+3V3_AUX, 12→GND; 4(−)→IL_G31, 5(+)→IL_REF_LOST, 2→NEG_OK; 6(−)→IL_G31, 7(+)→IL_REF_PINCH, 1→GATES_PINCHED; 8(−)→IL_G32, 9(+)→IL_REF_LOST, 14→NEG_OK; 10(−)→IL_G32, 11(+)→IL_REF_PINCH, 13→GATES_PINCHED |
| U905 | Comparator:LM339 | LM339B | Package_SO:SOIC-14_3.9x8.7mm_P1.27mm | TI LM339BIDR | 3→+3V3_AUX, 12→GND; 4(−)→IL_G33, 5(+)→IL_REF_LOST, 2→NEG_OK; 6(−)→IL_G33, 7(+)→IL_REF_PINCH, 1→GATES_PINCHED; 8(−)→IL_G34, 9(+)→IL_REF_LOST, 14→NEG_OK; 10(−)→IL_G34, 11(+)→IL_REF_PINCH, 13→GATES_PINCHED |
| U906 | Comparator:LM339 | LM339B | Package_SO:SOIC-14_3.9x8.7mm_P1.27mm | TI LM339BIDR | 3→+3V3_AUX, 12→GND; 4(−)→IL_G41, 5(+)→IL_REF_LOST, 2→NEG_OK; 6(−)→IL_G41, 7(+)→IL_REF_PINCH, 1→GATES_PINCHED; 8(−)→IL_G42, 9(+)→IL_REF_LOST, 14→NEG_OK; 10(−)→IL_G42, 11(+)→IL_REF_PINCH, 13→GATES_PINCHED |
| U907 | Comparator:LM339 | LM339B | Package_SO:SOIC-14_3.9x8.7mm_P1.27mm | TI LM339BIDR | 3→+3V3_AUX, 12→GND; 4(−)→IL_G43, 5(+)→IL_REF_LOST, 2→NEG_OK; 6(−)→IL_G43, 7(+)→IL_REF_PINCH, 1→GATES_PINCHED; 8(−)→IL_G44, 9(+)→IL_REF_LOST, 14→NEG_OK; 10(−)→IL_G44, 11(+)→IL_REF_PINCH, 13→GATES_PINCHED |
| U908 | Comparator:LM339 | LM339B | Package_SO:SOIC-14_3.9x8.7mm_P1.27mm | TI LM339BIDR | 3→+3V3_AUX, 12→GND; 4(−)→IL_N5V, 5(+)→IL_REF_N5V, 2→NEG_OK; 6(−)→IL_N3V3, 7(+)→IL_REF_N3V3, 1→NEG_OK; 8(−)→IL_REF_N5V, 9(+)→IL_V33MON, 14→NEG_OK (+3V3_AUX UV); 10(−)→IL_REF_PINCH, 11(+)→GND, 13→NC (spare) |
| U909 | 74xGxx:74AUC1G74 (no 74LVC1G74 in KiCad 9 lib; pin-identical) | SN74LVC1G74 | Package_SO:VSSOP-8_2.3x2mm_P0.5mm | TI SN74LVC1G74DCUR | 1 C(CLK)→IL_CLK, 2 D→GATES_PINCHED, 3 ~Q→NC, 4 GND→GND, 5 Q→PA_ARMED, 6 ~CLR→IL_CLR_N, 7 ~PRE→+1V8_DIG, 8 VCC→+1V8_DIG |
| U910 | 74xGxx:74LVC1G17 | SN74LVC1G17 | Package_TO_SOT_SMD:Texas_R-PDSO-G5_DCK-5 | TI SN74LVC1G17DCKR | 1 NC→NC, 2 A→IL_CLK_RC, 3 GND→GND, 4 Y→IL_CLK, 5 VCC→+1V8_DIG |
| U911 | 74xGxx:74LVC1G11 | SN74LVC1G11 | Package_TO_SOT_SMD:SOT-363_SC-70-6 | TI SN74LVC1G11DCKR | 1 A→MCU_PA_EN, 3 B→WDT_OK, 6 C→NEG_OK, 4 Y→IL_CLR_N, 5 VCC→+1V8_DIG, 2 GND→GND |
| C900 | Device:C | 100nF 16V X7R | Capacitor_SMD:C_0402_1005Metric | Murata GRM155R71C104KA88D | 1→+3V3_AUX, 2→GND (U900 pin 3) |
| C901 | Device:C | 100nF 16V X7R | Capacitor_SMD:C_0402_1005Metric | Murata GRM155R71C104KA88D | 1→+3V3_AUX, 2→GND (U901 pin 3) |
| C902 | Device:C | 100nF 16V X7R | Capacitor_SMD:C_0402_1005Metric | Murata GRM155R71C104KA88D | 1→+3V3_AUX, 2→GND (U902 pin 3) |
| C903 | Device:C | 100nF 16V X7R | Capacitor_SMD:C_0402_1005Metric | Murata GRM155R71C104KA88D | 1→+3V3_AUX, 2→GND (U903 pin 3) |
| C904 | Device:C | 100nF 16V X7R | Capacitor_SMD:C_0402_1005Metric | Murata GRM155R71C104KA88D | 1→+3V3_AUX, 2→GND (U904 pin 3) |
| C905 | Device:C | 100nF 16V X7R | Capacitor_SMD:C_0402_1005Metric | Murata GRM155R71C104KA88D | 1→+3V3_AUX, 2→GND (U905 pin 3) |
| C906 | Device:C | 100nF 16V X7R | Capacitor_SMD:C_0402_1005Metric | Murata GRM155R71C104KA88D | 1→+3V3_AUX, 2→GND (U906 pin 3) |
| C907 | Device:C | 100nF 16V X7R | Capacitor_SMD:C_0402_1005Metric | Murata GRM155R71C104KA88D | 1→+3V3_AUX, 2→GND (U907 pin 3) |
| C908 | Device:C | 100nF 16V X7R | Capacitor_SMD:C_0402_1005Metric | Murata GRM155R71C104KA88D | 1→+3V3_AUX, 2→GND (U908 pin 3) |
| C909 | Device:C | 100nF 16V X7R | Capacitor_SMD:C_0402_1005Metric | Murata GRM155R71C104KA88D | 1→+1V8_DIG, 2→GND (U909 VCC) |
| C910 | Device:C | 100nF 16V X7R | Capacitor_SMD:C_0402_1005Metric | Murata GRM155R71C104KA88D | 1→+1V8_DIG, 2→GND (U910 VCC) |
| C911 | Device:C | 100nF 16V X7R | Capacitor_SMD:C_0402_1005Metric | Murata GRM155R71C104KA88D | 1→+1V8_DIG, 2→GND (U911 VCC) |
| C912 | Device:C | 1nF 50V C0G | Capacitor_SMD:C_0402_1005Metric | Murata GRM1555C1H102JA01D | 1→IL_CLK_RC, 2→GND |

**Local nets** (IL_ prefix):
- IL_G11 … IL_G44: gate divider nodes
- IL_N5V, IL_N3V3: rail divider nodes
- IL_REF_LOST, IL_REF_PINCH, IL_REF_N5V, IL_REF_N3V3: reference dividers
- IL_V33MON: +3V3_AUX monitor
- IL_CLR_N, IL_CLK_RC, IL_CLK: latch control

## 10. Behavioural ngspice netlist

**BEHAVIOURAL ONLY. No vendor models are used.**

- File: `interlock/interlock_behav.cir`.
- Comparators are ideal B-sources with a 1.3 µs ideal delay line driving open-collector switches. The flop is XSPICE `d_dff`. The TPS22810 is modelled as a 3.3 µs tOFF delay, a 150 µs on-delay (the tR ramp is not modelled) and a 0.9 µs discharge time constant.
- Two of the 16 gates are modelled: gate1 has the fault injected, and gate2 stands for the other 15.
- **The netlist has not been run.** ngspice is not installed on this host, so syntax and results are unverified.

| t | Stimulus | Expected |
|---|---|---|
| 0–0.3 ms | +1V8/+3V3 ramp, −3V3_SW and −5V_BF up, gates at 0 V (DAC reset) | NEG_OK low, PA_ARMED 0, VOUT 0 |
| 0.4 ms | gates OFF at −1.75 V | NEG_OK and GATES_PINCHED high |
| 0.6 ms | MCU_PA_EN ↑ | PA_ARMED ↑ about 7.5 µs later; VOUT up after about 150 µs |
| 0.8 ms | gates ON at −1.1 V | GATES_PINCHED low, PA_ARMED stays 1 |
| 1.0 ms | gate1 steps −1.1 → 0 V (gate lost) | NEG_OK ↓ at +1.3 µs, PA_ARMED ↓, VOUT < 4.5 V at about +4.7 µs |
| 1.2 ms | gate1 back to −1.1 V | **VOUT stays 0** (latched): `vout_1p25m` ≈ 0 |
| 1.3 / 1.4 ms | gates OFF, MCU_PA_EN low, then high | re-armed |
| 1.7–1.9 ms | WDT_OK low pulse | VOUT off about 3.3 µs after; stays off (`vout_1p95m` ≈ 0) |
| 2.0 / 2.1 ms | gates OFF, MCU_PA_EN toggled | re-armed |
| 2.5–2.7 ms | −5V_BF collapses linearly to 0 V; gates follow max(DAC, AVDD1) | trips at −4.6 V (2.516 ms); VOUT falls about 4.7 µs later, before the gates move (they reach −1.1 V at 2.656 ms) |

The run prints d_gate, d_wdt and d_n5v (the response times) and writes `interlock_behav.csv`.
