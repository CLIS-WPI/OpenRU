# H2-D — ADAR1000 PA_BIAS / LNA_BIAS vs ADTR1107 VGG abs max: passive-divider analysis

Date 2026-11-12. Research and analysis only: no KiCad edits, no commits.
The calculation script is `divider_calc.py`, next to this file (`python3 -I divider_calc.py`). It contains self-check asserts.
Rendered figure crops are in `img/`.

Evidence classes used below:
- **DS-TEXT**: datasheet text or table, quoted.
- **DS-FIG**: datasheet figure, read visually from a pdftoppm render.
- **ADI-REF**: ADI Stingray schematic 02_059522 Rev B.
- **H2-SPEC**: OpenRU's own design documents.
- **DERIVED**: calculated here.
- **UNVERIFIED**: not stated anywhere.

## 1. What ADI documents (Q1)

| # | Finding | Class / source |
|---|---|---|
| 1 | **Stingray, sheet 4 of 19:** ADAR1000 U1_x pin A10 `PA_BIAS1` connects through net `PA1_BIAS` **directly** to ADTR1107 U2_x pin 7 `VGG_PA`. PA2–PA4 are the same (U3–U5). There is **no resistor, no capacitor and no test point** on the net. `PAn_BIAS` appears exactly 16 times in the 19-sheet text: 8 sheet copies × (ADAR pin + VGG_PA pin). C5_1…C8_x (4.7 µF 0201) sit on `+5.0V`/VDD_PA (pin 8), not on VGG_PA. This was checked on the high-resolution render. | ADI-REF (`h2c/periph/stingray/hi-04.png`, `sch.txt`, BOM `059522b_bom.csv`) |
| 2 | **Stingray LNA_BIAS:** pin A11 connects directly to VGG_LAN (pin 23) of all four ADTR1107s. There is no component on the net. The 100 k parts R1_x/R2_x sit near TX_LOAD/RX_LOAD and are not on the bias nets. | ADI-REF |
| 3 | **ADAR1000 Fig 97:** PA_BIAS3 is wired straight to VGG_PA, and LNA_BIAS goes to VGG_LNA (marked optional). The datasheet says "glueless interfacing, requiring no components between the connected ports" (that sentence is about RF ports). | DS-FIG / DS-TEXT p44 |
| 4 | **ADTR1107 Fig 7 (VGG_PA interface):** the pin feeds a **series resistor of unstated value** into the PA FET gate. There is **no internal shunt to GND**. So the DC load is the gate current only. | DS-FIG p7 (`img/f7b-07.png`) |
| 5 | **ADTR1107 Fig 9 (VGG_LNA interface):** the pin node has an **internal shunt resistor to GND (value unstated)** and a shunt capacitor. It feeds the LNA gate, and an RF coupling capacitor also connects there. | DS-FIG p8 (`img/f9-08.png`) |
| 6 | **ADTR1107 Fig 50:** IGG_PA vs input power at IDQ 220 mA, VDD 5 V. It is ≈0 below −10 dBm and falls to **≈ −0.1…−0.3 mA** at +5…+10 dBm for 6–16 GHz. It reaches **−0.5 mA at 18 GHz, +5 dBm**. No static gate-leakage spec exists. | DS-FIG p15 |
| 7 | **ADTR1107 Fig 49:** IDQ_PA ≈ 10 mA at −1.75 V, ≈150 mA at −1.25 V, ≈400 mA at −0.75 V, ≈650 mA at −0.25 V. The slope is **≈500 mA/V** around the −1.1 V operating point. | DS-FIG p15 |
| 8 | **ADAR1000 Fig 86 (simplified bias DAC):** the output stage is a PNP to the **1.8 V LDO** and an NPN whose **emitter is at AVDD1**. One clamp diode runs from the output to GND (anode at the output). Another runs from AVDD1 to the output (anode at AVDD1). | DS-FIG p27 (`img/f86-27.png`) |
| 9 | **ADAR1000 PA_BIAS spec:** "Voltage Range −4.8 to 0 V" and "Source and Sink Current −10 to +10 mA". Both are **typ column only, no min/max**. Switching is 60 ns with a 1 nF load. The theory text says the output is "amplified and translated to a 0 V to −4.8 V range". There is **no absolute-maximum rating for the PA_BIAS/LNA_BIAS pins**, and **no statement relating the output to AVDD1** beyond Fig 86. | DS-TEXT p7, p10, p11, p31 |
| 10 | **No ADI document reconciles 0x85 (−2.5 V) with the −2 V VGG_PA abs max.** Neither datasheet has a transient or negative-gate allowance. ADAR1000 p45 calls −2.5 V "a safe voltage for the VGG_PA pins". | DS-TEXT |

**Answer to Q1:** ADI's own board drives VGG_PA from PA_BIASx with **nothing in between**: no series R, no shunt R, and not even the 10 nF of ADTR1107 Fig 89. No ADI material resolves the conflict.

## 2. Can the bound rely on physics? (Q2, premise)

- **Basis.** Fig 86 shows the only pull-down device, the NPN, with its emitter at AVDD1. With only passive loads to GND, the output cannot be driven below AVDD1 (plus Vce(sat)).
  - The AVDD1→output diode conducts only if something external pulls the pin *below* AVDD1. A divider to GND never does that.
  - So `V(PA_BIAS) ≥ AVDD1` is supported by **DS-FIG (a "simplified" schematic)** plus device physics.
  - It is **not** a datasheet guarantee (there is no pin abs max and no output-range min/max).
- **Upper side.** The PNP pull-up goes to +1.8 V LDO. The output-to-GND diode limits a positive excursion to about one diode drop (~+0.6…0.7 V, UNVERIFIED).
  - Code 0x00 is nominally 0 V, but the DAC offset is not specified.
  - VGG_PA abs max is "+0 V" and VGG_LNA is "+0.2 V", so a positive offset or glitch is an **unaddressed** risk in the direct ADI connection as well.
- **Full scale.** 0xFF = −4.8 V typ. The datasheet does not say whether this is set by an internal reference or is ratiometric to AVDD1. It also does not say whether −4.8 V is achievable when AVDD1 = −4.75 V (the supply minimum magnitude is *below* the 4.8 V full scale). UNVERIFIED.
- **Rails.**
  - ADAR1000 AVDD1 recommended range is −4.75…−5.25 V; abs max is −5.5 V.
  - The H2 −5V_BF (TPS7A3301 U658) worst case is −4.848…−5.150 V (H2-SPEC POWER_SPEC).
  - Its input PWR_VNEG is −6.005…−6.688 V. A shorted LDO pass element would put up to −6.69 V on AVDD1.
  - The H2 interlock (NEG_OK) detects only *under*-voltage. It does not detect over-voltage.

## 3. Divider design (Q2)

Topology: `PA_BIASx —R1— VGG_PA node —R2— GND`, with the 10 nF (ADTR1107 Fig 89) at the node. k = R2/(R1+R2).

### 3.1 The squeeze (DERIVED)

- **Bound:** k_max·|V_src,max| ≤ 2.0 V.
- **Reach:** k_min·|V_DAC,max usable| ≥ 1.75 V.
- **Combined:** both hold only if (2.0/1.75)·(|V_DAC,usable| / |V_src,max|) > 1. The excess over 1 is the total budget for resistor tolerance, DAC full-scale error, output headroom and abs-max margin:

| V_src,max | V_DAC,usable | Margin product | Total budget |
|---|---|---|---|
| 5.25 V (ADAR spec) | 4.8 V (typ) | 1.0449 | **4.5 %** |
| 5.150 V (H2 rail) | 4.8 V (typ) | 1.0652 | **6.5 %** |

The DAC full-scale accuracy and the output headroom are **not specified**, so this budget cannot be closed on paper.

### 3.2 Chosen values (E96, 0.1 %, 25 ppm/K, ΔT 65 K → ±0.26 % per resistor)

| Item | Value |
|---|---|
| R1 (DAC side) | **619 Ω** |
| R2 (to GND) | **365 Ω** |
| k | 0.37093 nominal (k_min 0.36971 / k_max 0.37216) |
| Thevenin resistance | **229.6 Ω** |
| R total | 984 Ω |

Alternatives with the same ratio: 634/374, 665/392, 649/383, 590/348.

### 3.3 Worst-case VGG_PA (most negative)

| Source condition | VGG_PA (k_max) | Margin to −2.0 V |
|---|---|---|
| DAC at 0xFF (−4.8 V typ; firmware error) | −1.786 V | +0.214 V |
| PA_BIAS at H2 rail worst case −5.150 V (physical bound, H2 rail) | **−1.917 V** | **+0.083 V** |
| PA_BIAS at ADAR spec AVDD1 −5.25 V (physical bound, any compliant rail) | **−1.954 V** | **+0.046 V** |
| AVDD1 at its abs max −5.5 V | −2.047 V | −0.047 V ✗ |
| LDO pass short, AVDD1 = PWR_VNEG −6.688 V | −2.489 V | −0.489 V ✗ (ADAR1000 is also beyond its own abs max) |

- **Loading error on the bound.** VGG_PA has no internal shunt (Fig 7), and any DAC output resistance (unspecified) adds to R1. Both effects can only *reduce* k, which is the safe direction.
- **Gate current at pinch-off** is not specified.
  - Fig 50 shows that under RF compression the current flows *out* of the gate (negative IGG). That moves VGG toward 0 V.
  - If the sign were opposite, 100 µA × 230 Ω = 23 mV would still leave −1.94 V at the H2 rail.
- **Least-negative side.** With the ADAR1000 unpowered, R2 holds VGG_PA at 0 V, which is inside the 0 V limit.
  - A +0.7 V excursion at the DAC pin gives **+0.26 V** at VGG_PA. That is still above the 0 V abs max, but it is 2.7× smaller than with a direct connection.

### 3.4 Function (reach, resolution, load)

| Target VGG_PA | DAC needed | Code | Status |
|---|---|---|---|
| −0.25 V | −0.674 V | ≈36 | fine |
| −1.10 V (typ ON) | −2.97 V | ≈158 | fine |
| −1.75 V (ADTR1107 pinch / sequence value) | −4.72…−4.73 V | **251–252 of 255** | marginal (below) |

**−1.75 V reach is marginal and UNVERIFIED:**
- At 0xFF the divider gives −1.775…−1.786 V, *if* the DAC reaches −4.8 V.
- If the output saturates h volts above an H2 rail at −4.848 V, the reach is:

| h | VGG_PA reach |
|---|---|
| 0.1 V | −1.755 V |
| 0.2 V | −1.718 V |
| 0.3 V | −1.681 V |

- At −1.70 V, Fig 49 gives IDQ of about 20 mA instead of about 10 mA. This is a **functional deviation, not a damage risk**.

**Other effects:**
- **Resolution:** the step at VGG is 18.82 mV × k = **6.98 mV/LSB**, versus 18.82 mV direct. That is ≈3.5 mA IDQ per LSB, which is better than direct.
- **DAC load:**

| Condition | DAC current |
|---|---|
| ON | 3.0 mA |
| OFF | 4.8 mA |
| Physical worst case | 5.3 mA |

  All are inside ±10 mA, and the load is continuous. For 16 PA channels in OFF, ≈77 mA is added to −5V_BF, which is inside the 0.25 A budget line in POWER_SPEC (budget not re-checked).
- **Bias stiffness (main functional cost).** ADI provides a ±10 mA push-pull output "for PAs that can draw significant gate current when pushed deep into compression" (p31). With 230 Ω of source resistance, the Fig 50 gate current shifts VGG toward 0 V:

| IGG | VGG shift | IDQ shift (Fig 49 slope) |
|---|---|---|
| 0.05 mA | +11 mV | ≈ +6 mA |
| 0.3 mA (6–16 GHz, compressed) | +69 mV | ≈ +34 mA |
| 0.5 mA (18 GHz) | +115 mV | ≈ +57 mA |

  This is positive feedback: more drive gives more gate current, which gives more IDQ. Thermal impact is not evaluated.
- **Timing with the 10 nF:**
  - τ = 230 Ω × 10 nF = **2.30 µs**. Settling takes 10.6 µs to 1 % and 15.8 µs to 0.1 %, per TR edge.
  - Direct drive (S6) is ≈0.65 µs, limited by the 10 mA slew into 10 nF.
  - With 1 nF (the ADAR1000 spec load; Stingray uses 0 nF), τ = 0.23 µs and 1 % settling takes 1.06 µs.
  - Compare the TR switch at 180 ns (ADAR1000) and 10 ns (ADTR1107). The PA gate becomes the dominant TDD guard-time term.
  - The RC response is first order and monotonic, so it adds no overshoot and it low-pass filters DAC glitches (scaled by k).
  - OpenRU's TDD guard-time requirement was not available to this analysis.

### 3.5 Supply events

| Event | Direct (as H2-B) | With divider |
|---|---|---|
| ADAR1000 unpowered | pin undriven; VGG floats or sits at the clamp diodes | VGG = 0 V via R2 (within abs max; full IDQ if the drain is on, same as DAC reset) |
| AVDD1 collapses | gate follows max(DAC, AVDD1) → 0 V | VGG = k·max(DAC, AVDD1). The ON DAC sits at −2.97 V, so the gate starts to move only once AVDD1 has risen past ≈−3.1 V (more lead time after the −4.6 V NEG_OK trip). OFF moves at once but stays ≥ −1.70 V near the trip |
| AVDD1 within −4.75…−5.25 V, any firmware or DAC fault | up to −4.8 V typ (or AVDD1) on VGG ✗ | **≤ −1.954 V ✓** |
| AVDD1 over-voltage (LDO short) | ✗ | ✗ (−2.49 V) |

### 3.6 LNA_BIAS → VGG_LNA (abs max −2 V…+0.2 V)

- The same R1/R2 ratio gives the same bound: **≤ −1.954 V**.
- **Loading.** Fig 9 shows an internal shunt resistor of unknown value per device, and LNA_BIAS drives 4 devices in parallel. The H2 schematic already has a 10 kΩ to GND on VGG_LNA.
  - Unknown shunts only **reduce** k, so the bound still holds. The reach, however, is **unknown**. If the 10 kΩ is reused as R2 with an R1 sized for k, the internal shunts (4 in parallel, unknown value) can shift k by an unquantifiable amount.
  - The design would have to be sized for k ≤ 0.372 with R2 equal to the parallel combination of R2, the 10 kΩ and R_int/4. Because R_int is unknown, the debias reach cannot be guaranteed.
- **Firmware-independent alternative with documented basis.**
  - Leave VGG_LNA on its 10 kΩ to GND and disable LNA_BIAS (not connected, or 0 Ω DNP). ADI: "Connecting the ADAR1000 LNA_BIAS pin to the ADTR1107 VGG_LNA is optional because the ADTR1107 LNA is self biased" (ADAR1000 p45). Self-bias with VGG_LNA at 0 V is in ADTR1107 p24.
  - This removes the VGG_LNA overvoltage path entirely.
  - The cost is that the LNA stays biased during TX (80 mA each). That is the combined mode ADI documents. Its TX-isolation residual is the same open item S3.

## 4. Remaining unverified items; what ADI must confirm (Q3)

1. Whether the PA_BIAS/LNA_BIAS output can ever go below AVDD1, or more negative than −4.8 V. This needs a pin abs max or output range relative to AVDD1, including fault and latch-up. Fig 86 is only "simplified".
2. The DAC full-scale min/max and the output saturation headroom to AVDD1 at −4.75…−5.25 V. These decide whether −1.75 V is reachable through k ≈ 0.37.
3. The DAC offset at code 0x00 (positive excursion vs the VGG_PA +0 V limit) and the DAC output resistance.
4. Whether the ADTR1107 VGG_PA −2 V abs max applies with VDD_PA = 0 V. ADAR1000 p45 implies −2.5 V is safe before +5 V is applied. This is the root conflict (inquiry 5a).
5. The ADTR1107 Fig 7 series-resistor and Fig 9 shunt-resistor values, and the gate leakage at pinch-off.
6. Whether a 230 Ω gate source impedance is acceptable for the ADTR1107 PA (bias walk and stability under compression).
7. ESD and transients: ADTR1107 is HBM Class 1B (±500 V) and ADAR1000 is HBM ±2500 V. The divider's effect on these is not quantifiable from the datasheets.
8. The TDD timing requirement against τ = 2.3 µs.

## 5. Other firmware-independent options (Q4)

- **AVDD1 set point.** Centring AVDD1 nearer −4.75 V does **not** help by itself. With a divider, the margin depends on the *spread* |AVDD1|min/|AVDD1|max and on the DAC headroom, not on the centre.
  - Tighter regulation would widen the budget. The TPS7A33 at ±2.5 % gives a ratio of 0.941. A ±1 % rail would give ≈0.98. This is DERIVED. It needs a precision reference/LDO choice, and the H2 rail as specified does not provide it.
  - Without a divider, the AVDD1 value is irrelevant to the −2 V limit: the DAC can put −4.8 V on the gate at any compliant AVDD1.
- **AVDD1 over-voltage detection** (PWR_VNEG → −6.69 V on an LDO short) is needed for *any* bound based on the rail. The current NEG_OK comparator detects only under-voltage. Adding an OV window is an H2 item. It is a comparator change like the existing IL_N5V divider, not a clamp.
- **Not proposed:** diode or zener clamps on VGG. Their leakage and soft-knee behaviour near −1.9 V at temperature would load the bias. This is unverified, as already decided in H2-B §1.
- **Not useful:** an offset divider to a negative rail. The span constraint stays the same (0.45·k ≤ 0.25), and it adds a rail dependency.

## 6. Recommendation

**Do not adopt the divider as the populated default in H2-D.** Instead, reserve footprints for it:
- R1 = 0 Ω fitted, in place of 619 Ω 0.1 %;
- R2 = 365 Ω 0.1 %, DNP;
- the 10 nF unchanged.

The decision on populating it should follow ADI's answers to §4 items 1, 2 and 4, plus a bench measurement of the PA_BIAS output at 0xFF on the actual −5V_BF rail.

| For adopting | Against adopting |
|---|---|
| The only firmware-independent bound found. VGG_PA ≥ −1.954 V for any compliant AVDD1 and any code or fault inside the ADAR1000, and −1.917 V on the H2 rail. | It rests on a "simplified" figure, not a spec. |
| 2.7× finer bias resolution. | Reaching −1.75 V OFF needs DAC code 251–252 of 255, with unspecified full-scale and headroom (no verified functional margin). |
| Defined 0 V when the ADAR1000 is unpowered. | It replaces ADI's stiff push-pull with 230 Ω, giving +34…+57 mA IDQ walk in compression. |
| | It slows gate settling to ≈10 µs with 10 nF. |
| | It deviates from ADI's own board (direct connection). |
| | It does not cover an AVDD1 over-voltage fault. |

The firmware limit ≤ 0x5D, readback and bench pre-check from H2-B §1 remain mandatory either way.

**For LNA_BIAS**, the cleaner firmware-independent option is self-bias:
- VGG_LNA stays on its existing 10 kΩ to GND;
- LNA_BIAS goes through a DNP 0 Ω;
- this is documented by ADI as optional, and the cost is no LNA debias in TX (S3 still applies).
