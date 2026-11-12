# H2-D independent safety audit: PA-drain interlock, crowbar, supervisors, PA supply path

- Date 2026-11-12. Reviewer: independent (H2-D). **Read-only**: no KiCad file was opened or edited, nothing committed, the 20-min sim suite was not re-run.
- Netlist evidence: `hardware/h2/reports/openru_x6_tile.xml` (as-built), parsed with Python (`h2d/tools/nl.py`, `q.py`, `c.py`; dump in `h2d/nl.json`). Every connection quoted below was read from that netlist, not from the design notes.
- Datasheet evidence: the TI / Diodes / ST texts already downloaded under `scratchpad/h2c/{power,interlock/ds,rec/ds,periph}` and `scratchpad/ds2`. Quotes are verbatim from the pdftotext output.
- Classification used for every undefined state:
  - **(a) PHYSICALLY REACHABLE**: a real supply/ramp/fault puts the part in a region where its datasheet gives no (or an unsafe) guarantee, and nothing else in the circuit bounds it.
  - **(b) PESSIMISTIC BOUND ONLY**: the datasheet gives no guarantee, but physics or another circuit element bounds the state, so "worst case" is a modelling bound rather than an expected behaviour.
  - **DS-DEFINED-UNSAFE**: the datasheet *defines* the state, and the defined state is the unsafe one.

---

## 0. As-built topology (from the netlist)

```
PA_DRAIN_EN  = U705(74LVC1G11, VCC +1V8_DIG): A=PA_ARMED, B=WDT_OK, C=NEG_OK → Y=IL_PA_DRAIN_EN_Y →R735 1k→ PA_DRAIN_EN
               PA_DRAIN_EN loads: R965 100k→GND; D961.1 (BAT54C anode, cathode=PG_3V3RF); R996..R999 10k → PWR_CB_Dc (C931..934 1nF) → Q971..974 gate;
               U621..U624 TPS22810 EN/UVLO. (No MCU readback of PA_DRAIN_EN, PA_ARMED, VOUT.)
NEG_OK       = U912(LVC1G08): A=IL_EN, B=GATES_OK. No pull-down. Also on STM32 PA0 (bidirectional, no series R).
IL_EN        = U915(LVC1G08): A=NEG_RAILS_OK, B=PG_3V3RF; R973 100k→GND. Also → R974 10k → IL_ON (TPS22917 U914 ON; Q965 "Q3" drain).
NEG_RAILS_OK = U908 OC ch A(−5V_BF), B(−3V3_SW), C(+3V3_AUX 2.97 V), D(+3V3_RF 3.10 V); R960 10k→+3V3_AUX, R961 10k→GND.
GATES_OK     = 16 × LM339B "lost" OC (U900–U907 ch A/C); R968 10k→+3V3_AUX, R969 10k→GND.
GATES_PINCHED= 16 × LM339B "pinch" OC (ch B/D); R962/R963; → U909 D only.
PA_ARMED     = U909 (LVC1G74) Q; CLK = IL_CLK (U910 Schmitt of MCU_PA_EN→R964 10k/C912 1nF); ~CLR = IL_CLR_N; ~PRE = +1V8_DIG.
IL_CLR_N     = U911(LVC1G11): MCU_PA_EN·WDT_OK·NEG_OK → R975 1k → IL_CLR_N; D961.2 (BAT54C anode → PG_3V3RF).
WDT_OK       = U702 TPS3430 ~WDO (OD) + R702 10k→+1V8_DIG + STM32 PA3 (bidirectional, no series R). Also feeds U703 (TX_ALLOW = ADAR PA_ON).
PG_3V3RF     = U650 PGOOD (OD) ∧ U920 TPS386000 RESET1/RESET2 (OD) ∧ D961 cathode; R654 100k→+1V8_DIG; STM32 PA1 (no series R);
               loads: U921 TLV75518P EN, U913/U915 inputs, Q966 gate.
U920 VDD     = IL_SUP_VDD = D960 BAT54C OR(+3V3_RF, +5V_PA); SENSE1 = +1V8_DIG (R977 32.4k/R978 10.2k, 1.671 V), SENSE2 = +3V3_AUX (R979/R1000, 2.968 V); CT1/CT2 2.2 nF.
IL_Q3G       = R976 100k from IL_SUP_VDD; Q966 drain (gate = PG_3V3RF). Q965 (Q3) gate = IL_Q3G, drain = IL_ON.
IL_REF       = U914 TPS22917 VOUT (VIN = IL_REF_SRC = U921 TLV75518P OUT, IN = +3V3_RF, EN = PG_3V3RF); QOD via R972 100 Ω; C915 10 nF.
               IL_REF feeds the 16 gate-divider top legs (R901…R946) and the LOST/PINCH reference dividers (R952/R953, R954/R955). Nothing monitors IL_REF.
Per chain c  : +5V_PA →R61c 10 mΩ→ +5V_PA_IN_Cc → U62c TPS22810 VIN; VOUT=QOD (pins 1,2 shorted) = +5V_PA_Cc (4×ADTR1107 VDD_PA, 4×4.7 µF+1 µF…);
               crowbar Q96c CSD16301Q2 drain → PWR_CB_Rc → 3×1 Ω RCS1206 → +5V_PA_Cc; gate PWR_CB_Gc ← R99x 4.7k from +5V_PA_IN_Cc; Q97c (Q2) pulls it to GND.
Rails        : U652 TPS62933 → +3V3_AUX (always on from VIN); U653 TLV75518P → +1V8_DIG (EN = IN = +3V3_AUX); U650 TPS568230 → +3V3_RF (EN = PWR_EN_3V3 = STM32 PB4, R714 100k↓);
               U651 TPS568230 → +5V_PA (EN = PWR_EN_5VPA = PB6, R716 100k↓; FB R655 220k/R656 30k; PGOOD → PG_5VPA → STM32 PC4 only);
               U657 TPS65131 (INN = +3V3_AUX, VIN via R666 from +3V3_AUX; ENN = PWR_ENN_NEG = U913 Y, **no pull-down**) → U658/U659 TPS7A3301 (EN tied to IN) → −5V_BF / −3V3_SW.
PA gate      : C{c}_PABIAS{k} = ADAR1000 PA_BIASx ∧ ADTR1107 VGG_PA ∧ Rg 49.9k (R900+3n) into IL_G node.
```

The as-built netlist agrees with H2C_HARDWARE_SAFETY_REVIEW §2 and IMPL_REC. One structural fact the documents do not spell out: **every protection path (gate-lost, rail monitors, watchdog, latch) converges on a single gate U705 and a single net PA_DRAIN_EN shared by all four TPS22810s and all four crowbar drivers.** The only path that bypasses U705 is the supervisor clamp D961 (BAT54C into PG_3V3RF), and that path only acts on +1V8_DIG / +3V3_AUX / U650-PGOOD faults, not on gate or negative-rail faults.

---

## 1. Datasheet statements used (verbatim)

| ID | Part / doc | Statement | Used for |
|---|---|---|---|
| D1 | TPS22810 SLVSDH0C §9.3.2 | "Note that during thermal shutdown, the QOD functionality is not available. The device does not discharge the load as RPD does not become engaged." | QOD in TSD |
| D2 | TPS22810 §9.3.2.1 | "When the power is removed, the input capacitor, CIN, discharges at VIN. Past the set UVLO level, the pull-down resistance RPD becomes disabled and the output no longer becomes discharged." | QOD below UVLO |
| D3 | TPS22810 §9.3.5 | "The switch disables when the junction temperature (TJ) rises above the thermal shutdown threshold, TSD. The switch re-enables once the temperature drops below the TSD – TSD,HYS value." (TS 160 °C typ, hyst 30 °C typ, both only "Threshold, VIN = 18 V") | TSD auto-restart |
| D4 | TPS22810 §7.5 | VUVR 2.0 / 2.54 / 2.62 V; hysteresis 5 %; VENR 1.13–1.3 V; VENF 1.08–1.18 V; VSHUTF 0.5–0.9 V; IEN ≤ 0.1 µA; RPD 250 typ / 400 max Ω at "VIN = VOUT = 5 V, VEN/UVLO = 0 V" | EN levels, RPD conditions |
| D5 | TPS22810 §7.6 | tOFF **3.3 µs typ only** (no min/max), tD 130–180 µs typ only; "only valid for the power-up sequence where VIN is already in steady state condition before the EN/UVLO pin is asserted high." | B-TOFF |
| D6 | TPS22810 §9.3.3 | "The internal de-glitch delay on EN/UVLO falling edge is intentionally kept low (2.5 μs typical)"; "EN/UVLO terminal must not be left floating." | timing, R965 |
| D7 | TPS22810 §9.3.2.2 | "the total capacitive load must not exceed 200 uF … the remaining charge from CL needs to decay naturally through the internal QOD resistance and must not be driven." | QOD stress |
| D8 | TPS22810 §7.1 | VOUT abs max "min(VIN + 0.3, 20)" V; no current limit anywhere in the document (only "thermal protection") | body-diode / shoot-through |
| D9 | SN74LVC1G11 / 1G74 ROC | VCC "Operating 1.65 … 5.5", "Data retention only 1.5" V; "The Ioff circuitry disables the outputs, preventing damaging current backflow through the device when it is powered down." Ioff is tested at VCC = 0 only. | LVC below 1.65 V |
| D10 | LM339B SLCS006Z §6.4 / §6.7 | ROC VS 2–36 V; VIVR (V−)−0.1 … (V+)−2.0 V; **VIO ±5.5 mV specified only for "VS = 5 to 36V"**; VCM only for "VS = 3 to 36V"; note 1: "When the voltage at either input goes negative by more than 0.3V, the output can be incorrect … only one input needs to be in the valid common mode range" | comparator undefined states |
| D11 | TPS3430 SBVS366A §7.4.2 | "When VDD is above VPOR and below VDD (min), **the watchdog is disabled, WDO is logic high** and WDI is ignored." VDD min 1.6 V; VPOR 0.8 V max; "(2) When VDD falls below VPOR, WDO is undefined."; "During power up, the watchdog is disabled until tRST expires." | WDT_OK in brown-out |
| D12 | TPS386000 SBVS105F §8.3.4 / §6.5 | "The RESETn … outputs are defined for VDD voltage higher than 0.9 V"; "the transitions from released-state to asserted-state are performed almost immediately with minimal propagation delay" (no max); VOL ≤ 0.4 V at **IOL = 1 mA** only; low-VDD VOL rows: "(2) … only define RESETn … output performance during **VDD ramp up**", "(3) … tRISE(VDD) ≥ 15 μs/V"; "The pullup resistor should be no smaller than 10 kΩ" | B-TD, M5 |
| D13 | TLV755P SBVS320D §6.5/§6.3 | VHI ≥ 1 V, **VLO ≤ 0.3 V**; VUVLO 1.21–1.44 V; "When VIN is less than VUVLO, the output is connected to ground with a 120Ω pulldown resistor." | IL_REF_SRC |
| D14 | TPS22917 SLVSDW8B | ON VIH 1.0 V, VIL 0.35 V; "Past a certain VIN level, the strength of the RPD is reduced." | IL_REF |
| D15 | TPS568230 SLVSEY5C pin table/§7.3.4/§7.3.6 | PGOOD "asserted low if output voltage is out of PGOOD threshold, over voltage or if the device is under thermal shutdown, EN shutdown or during soft start"; VOL 0.4 V @ 4 mA; OVP 125 % (FB-based), UVP 60 % after 256 µs; VENH 1.21–1.4 V, VENL 0.95–1.19 V | +3V3_RF / +5V_PA |
| D16 | TPS65131 SLVS493E | ENN "0 V: disabled, VIN: enabled"; VIH 1.4 V, VIL 0.4 V, IIN ≤ 0.1 µA (no internal pull-down stated); UVLO 2.1–2.7 V | PWR_ENN_NEG |
| D17 | DMG1012T DS31783 | "Electrical Characteristics (@ TA = +25°C …)": VGS(TH) 0.5–1.0 V at 250 µA. No min/max over temperature (Fig 7 typical only). | Q2/Q3/Q966 |
| D18 | CSD16301Q2 SLPS235E | "TA = 25°C": VGS(th) 0.9 / 1.1 / 1.55 V | crowbar |
| D19 | BAT54C DS11005 | "Electrical Characteristics (@TA = +25°C …)": VF ≤ 240 mV@0.1 mA, 320 mV@1 mA, 400 mV@10 mA; IR ≤ 2 µA@25 V | clamp level |
| D20 | STM32G431 DS12589 | "After reset, these pins are configured as JTAG/SW debug alternate functions, and the internal pull-up on PA15, PA13, **PB4** … activated"; RPU 25–55 kΩ; VBOR0 falling 1.60–1.69 V; "When RESET is released functionality is guaranteed down to VBOR0 Min." | PWR_EN_3V3, MCU state |
| D21 | ADAR1000 Rev B (adar1000_notes) | PA_BIAS "−4.8 to 0" V, 0xFF = −4.8 V; "all PA_BIASx pins are driven to 0 V" at power-up (p41); power-down sequence and output behaviour with AVDD3 absent: **not stated** | TE2 |
| D22 | ADTR1107 Table 6 | VGG_PA "−2 V to +0 V"; VDD_PA 5.5 V abs max | TE1/TE2 |

---

## 2. Task 1: signal-state audit

### 2.1 Conditions

| Code | Condition | Physical coupling the auditor found in the netlist |
|---|---|---|
| P | all rails in regulation | — |
| VIN0 | VIN_12V lost | +3V3_AUX/+1V8_DIG/+3V3_RF collapse in ms; **+5V_PA bulk (235 µF) stays ≈ 5 V for ~100 ms** (sim note), so TPS22810 VIN, crowbar gate supply and U920 VDD stay alive longest |
| AUX0 | +3V3_AUX absent | **cannot be "individual"**: U653 (+1V8_DIG) EN = IN = +3V3_AUX and TPS65131 INN/VIN come from +3V3_AUX, so +1V8_DIG and both negative rails go with it |
| AUXb | +3V3_AUX ramp/brown-out 1.9–2.97 V (+1V8_DIG still in regulation) | LM339B VS in or near the bottom of ROC |
| V18-0 | +1V8_DIG absent, AUX up (U653 failure/TSD/output short) | MCU in reset → all MCU outputs high-Z + 100 k pull-downs |
| V18b | +1V8_DIG 0.8–1.65 V (ramp, brown-out, decay) | LVC below "Operating 1.65 V"; TPS3430 below 1.6 V; MCU reset below VBOR0 1.60–1.69 V |
| RF0 / RFb | +3V3_RF absent / 2.8–3.10 V | ADAR1000 AVDD3, TLV755 IL_REF_SRC input, U920 VDD (one OR leg) |
| 5P0 | +5V_PA absent | TPS22810 VIN < UVLO; crowbar gate supply absent; U920 VDD (other leg) |
| N50 / N30 | −5V_BF absent or > −4.6 V / −3V3_SW absent or > −3.0 V | ADAR1000 AVDD1 / ADTR1107 VSS_SW |
| HZ | the net's own driver unpowered/high-Z/open | — |
| TSD | thermal shutdown / UVLO of the device on that net | see §2.4 |

Legend: **L** defined low (safe), **H** defined high, **fw** set by firmware, **Z** floating (no driver, no bias), **L\*** low via pull resistor only, **Ua#** undefined, physically reachable, **Ub#** undefined, pessimistic bound only, **DU#** datasheet-defined unsafe. "masked" = the state exists but a downstream element that is itself defined holds the drain off.

### 2.2 State matrix

| Net | Driver(s) / pulls | P | VIN0 | AUX0 | AUXb | V18-0 | V18b | RF0/RFb | 5P0 | N50/N30 | HZ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| MCU_PA_EN | STM32 PB15 push-pull; R711 100k↓ | fw | L\* | L\* | fw | L\* (MCU off) | L\* below VBOR0 (D20), fw above | fw | fw | fw | L\* |
| WDT_OK | TPS3430 ~WDO (OD) + R702 10k↑+1V8_DIG + **STM32 PA3** | H (serviced) | **DU1** H while +1V8 0.8–1.6 V, then ≤0.8 V | ≤ V18 | H | ≈0 (pull-up dead; WDO undefined <0.8 V, D11) | **DU1** H (D11 §7.4.2) | H | H | H | H\* (R702) — latent watchdog loss; PA3 as output = **fw override** |
| NEG_RAILS_OK | U908 4×OC; R960 10k↑AUX, R961 10k↓ | H | L (ch C trips 2.97 V, later R961) | L\* | **Ua2** for AUX ≈1.9–2.5 V; L for 2.5–2.97 V | **Ua7** (rail-divider nodes ≈ −1.0 V < −0.3 V, refs = 0; D10 note 1), masked (U915 unpowered) | H with thresholds scaled by V18 (−5V_BF trip −3.07 V at 1.2 V) | L (ch D, 3.10 V) | H | L | **H** if U908 V+/GND pin open (outputs off, pull-up wins) — latent |
| PG_3V3RF | U650 PGOOD (OD) ∧ U920 RESET1/2 (OD) ∧ D961 cathode; R654 100k↑+1V8_DIG; **STM32 PA1** | H | L (U920 on +5V_PA bulk sees V18/AUX UV; detection delay **Ua3**) | L | L (U920 SENSE2) | L (no pull-up) | L, but level 0.07–0.66 V under clamp current (**Ua4**, VOL only at 1 mA, D12) | L (RF0: PGOOD "EN shutdown"); **H for RF 2.83–3.10 V falling** (PGOOD fault at 85 %), masked by U908 ch D | H | H | U920 VDD < 0.9 V → RESET undefined (D12), relies on U650 PGOOD; PA1 as output = **fw override** |
| IL_EN | U915 (LVC) ; R973 100k↓ | H | L, then L\* | L\* | L (PG) / Ua2 | L\* (Ioff) | **Ua5** (LVC < 1.65 V, D9) | L | H | L | L\* |
| IL_Q3G (Q3 gate) | R976 100k↑IL_SUP_VDD; Q966 drain (gate PG_3V3RF) | L (Q966 on) | H (Q3 clamps ON) | H | H | H | **Ua6**: PG at 0.5–0.66 V ≥ Q966 VGS(th) min 0.5 V (25 °C only, D17) → Q966 partly on → IL_Q3G can fall below Q3 VGS(th) → Q3 clamp released | H (if 5VPA up) / L (both OR legs down: masked, TLV755 IN < UVLO) | H via RF | H | L if U920 VDD rail absent (masked) |
| IL_ON (TPS22917 ON) | R974 10k from IL_EN; Q965 drain; internal 750 k "smart pull-down" only when VON ≤ VIL | H | L | L | L | L | **Ua5/Ua6** (0.35–1.0 V band, D14) | L | H | L | — |
| IL_REF_SRC | U921 TLV755 OUT (IN +3V3_RF, EN PG_3V3RF) | 1.8 V | → 0 | 0 (EN low) | 0 | 0 | **Ua4** EN between VLO 0.3 V and VHI 1.0 V (D13) → may stay on | 0 (UVLO pull-down, D13) | 1.8 V | 1.8 V | — |
| IL_REF | U914 VOUT; QOD→R972 100 Ω; C915 10 nF; ≈1 kΩ divider bleed | 1.8 V | 0 | 0 | 0 | 0 | **Ua** only if both Ua4 and Ua5/6 occur (sim: REF failures only with U920 delay ≥ 50 µs) | 0 | 1.8 V | 0 | **0 V if U914/U921 dead/open or C915 short → see FMEA F-REF (unsafe: comparators read "OK/pinched")** |
| NEG_OK | U912 push-pull; **no pull-down**; **STM32 PA0** | H | L | L | L/Ua2 | **Z** (Ioff), masked (U705/U911 unpowered) | **Ua5** | L | H | L | Z; PA0 as output = **fw override/contention** |
| GATES_OK | 16 OC; R968 10k↑AUX, R969 10k↓ | H (all gates < −0.15 V) | L\* | L\* | Ua2 | L/H: gate nodes ≈ 0.2·Vg (IL_REF off) | H/L (scaled) | **Ua7** when IL_REF off with gates ≤ −1.5 V (node < −0.3 V, D10 note 1); masked by IL_EN = L | — | **Ua7**, masked | H if any package V+/GND open (that package's 4 checks lost) |
| GATES_PINCHED | 16 OC; R962/R963 | = gate state | L\* | L\* | Ua2 | Ua7 | scaled | Ua7 masked (D only sampled on IL_CLK edge, CLR held) | — | Ua7 masked | as GATES_OK |
| IL_CLR_N | U911 Y →R975 1k; D961 to PG; **no pull-down** | = MCU_PA_EN·WDT_OK·NEG_OK | L | Z (masked) | L | **Z** (masked, flop unpowered) | **Ua5** + clamp level 0.5–0.93 V (**Ua4**; sim M5c +345 mV above VIL) | L | fw | L | Z |
| IL_CLK | U910 Schmitt of R964/C912 | delayed MCU_PA_EN | L | Z | fw | Z | Ua5 | fw | fw | fw | — |
| PA_ARMED | U909 Q; **no pull-down** | latched | L (CLR) | Z masked | L | **Z**, masked (U705 unpowered) | 1.5–1.65 V: **retains** last state (D9 "Data retention only"), CLR not guaranteed → **Ua8**; power-up from 0 V: random → **Ua8** | L | fw | L | Z |
| PA_DRAIN_EN | U705 →R735 1k; R965 100k↓; D961 clamp; 4×(10k+1nF) | fw-armed | L (clamp/supervisor on +5V_PA bulk) | L | L | **L\*** (U705 Ioff, R965; plus clamp if U920 powered) | **Ua9**: U705 output undefined up to VCC; for VCC 1.08–1.65 V it can exceed VENF min 1.08 V (D4) until U920 asserts (delay **unspecified**); then clamp 0.5–0.97 V (pess.) — switch off but Q2 possibly still on | L | logic unaffected (switch has no VIN) | L | L\* (R965) / clamp |
| PWR_CB_Dc (Q2 gate) | RC 10k/1nF from PA_DRAIN_EN | follows, τ = 10 µs | | | | | Ua9 | | | | open R99x → **Z** (latent) |
| PWR_CB_Gc (crowbar gate) | R99x 4.7k↑+5V_PA_IN_Cc; Q2 drain | L when armed; ≈ VIN when disarmed | ≈ +5V_PA bulk → crowbar fires | ≈ VIN (fires) | ≈ VIN | ≈ VIN (fires; switch off → no current) | **Ua10**: Q2 VGS in 0.5–1.1 V band → partial; crowbar linear | ≈ VIN | **0 → crowbar unavailable** | ≈ VIN | — |
| +5V_PA_IN_Cc (TPS22810 VIN) | +5V_PA via 10 mΩ | 4.85–5.18 V | holds ~100 ms | 5 V if U651 still enabled (MCU dead → R716 → U651 off → decays) | 5 V | decays (MCU reset → PWR_EN_5VPA L\*) | 5 V | 5 V | 0 | 5 V | **no hardware OV limit** (see F-5V) |
| TPS22810 VOUT +5V_PA_Cc | switch / QOD / crowbar / PA load | 5 V armed | follows EN; QOD lost below VIN UVLO (D2) | 0 | 0 | 0 | Ua9 | 0 | ≈ 0 (body diode to VIN, D8 inference) | 0 | — |
| TPS22810 QOD | tied to VOUT | off while EN high | active while VIN ≥ UVLO | | | | | | **inactive** (D2) | | **inactive in TSD** (D1) |
| PWR_ENN_NEG (TPS65131 ENN) | U913 Y; **no pull-down** | PWR_EN_NEG·PG | L then Z | — (no VIN) | L | **Z → Ua12** (U913 Ioff; ENN IIN ≤ 0.1 µA, D16) — negative rails may start before +3V3_RF | Ua (sim INFO line) | L | | | Z |
| PWR_EN_5VPA (+5V_PA enable) | PB6; R716 100k↓; U651 EN 2 µA internal ↓ | fw | L\* | L\* | fw | L\* | L\* below VBOR0 | fw | fw | fw | L\* |
| PWR_EN_3V3 (U650 EN) | PB4; R714 100k↓ | fw | L\* | L\* | fw | L\* | **Ua11**: in reset/before firmware config PB4 = NJTRST with 25–55 kΩ pull-up (D20) → 1.8 V × 100/(100+25…55) = **1.16–1.44 V**, straddling VENL 0.95–1.19 / VENH 1.21–1.4 V (D15) | fw | fw | fw | — |
| U650 PGOOD | TPS568230 OD | H | needs VIN (internal) | H | H | — (pull-up gone) | — | L (D15) | — | — | — |
| U651 PGOOD = PG_5VPA | OD; R676 100k↑+1V8_DIG; STM32 PC4 only | H | | | | | | | L | | **not in the hardware chain** |
| TLV755 EN (U921) | PG_3V3RF | H | | | | | Ua4 | | | | |
| TPS22917 ON | IL_ON | see IL_ON | | | | | | | | | |
| C{c}_PABIAS{k} (VGG_PA) | ADAR1000 PA_BIASx (0…−4.8 V, ±10 mA) + 10 nF + Rg 49.9k | fw (0 V at reset, D21) | AVDD3/AVDD1 collapse order uncontrolled → **Ua13** | 0 (both down) | fw | ADAR keeps last value (its own LDOs from AVDD3) | fw | **Ua13**: AVDD3 absent with AVDD1 still present → output not specified (D21); sim assumes high-Z | fw | AVDD1 absent → clipped to 0 V (sim ASSUMPTION, "AVDD1 must be up for negative outputs") | PA_BIAS trace open → gate pulled to +1.30 V/62.5 kΩ when IL_REF on → GaAs gate diode ≈ +0.6 V (**TE2**) |

### 2.3 Undefined states: classification with justification

| # | State | Class | Justification |
|---|---|---|---|
| DU1 | WDT_OK = H while +1V8_DIG 0.8–1.6 V, and for tRST + tWDU (8.5–11.5 ms + 92.7–125.4 ms) after every power-up regardless of MCU | **DS-DEFINED-UNSAFE** | D11 §7.4.2 states WDO "is logic high" in VPOR < VDD < VDD(min); "During power up, the watchdog is disabled until tRST expires." The sim (`h2c_plant.inc` line 95: `wdt_ok = V(v18) > 1.65 && fw_wdt ? V(v18) : 0`) models the **opposite**. So the nominal-logic "0/920" ordering result assumes a watchdog input that the real TPS3430 does not provide in exactly the brown-out band where every other LVC input is also unspecified. |
| Ua2 | Comparator outputs (all three wired-OR nets) for +3V3_AUX ≈ 1.9–2.5 V | (a) | LM339B is in ROC (VS ≥ 2 V) but VCM is only specified for VS ≥ 3 V (D10). The rail-monitor references (0.53–0.84 V) and IL_REF_LOST (1.0 V) exceed (V+)−2 V. The pull-up level AUX/2 = 0.95–1.25 V sits in or just above the LVC undefined band (VIL 0.63 V … VIH 1.17 V at VCC 1.8 V). +1V8_DIG is in regulation during this ramp (TLV755 needs only ~1.9 V in). Masked when U920 is powered (SENSE2 holds PG low); **not masked at first power-up** if +3V3_RF/+5V_PA are off (U920 unpowered, D12) — then only U650 PGOOD ("EN shutdown", D15) holds PG low, which needs VIN present. |
| Ua3 | U920 assert delay | (a) | D12: "almost immediately with minimal propagation delay", no maximum; tW 4 µs typ is a pulse-width spec, overdrive dependent. The sim shows ≥ 20 µs causes EN/T50/CB failures. |
| Ua4 | PG_3V3RF low level under clamp current (0.5–0.66 V pessimistic; IL_CLR_N 0.5–0.93 V; PA_DRAIN_EN 0.8–0.97 V) | (a) for the level; (b) for the 1.1–1.5 mA source current | The sink current is real whenever U705/U911 still drive high while U920 asserts. VOL is specified only at 1 mA (D12) and BAT54C VF only at 25 °C (D19, VF rises at −40 °C, raising every clamp level). The 1.1–1.5 mA per LVC output assumed by the sim is a pessimistic bound: an LVC output at VCC 1.1–1.6 V physically has weak drive (b). TLV755 EN band 0.3–1.0 V (D13) is reached in the pessimistic case only. |
| Ua5 | U705/U911/U912/U913/U915 outputs at VCC 0.8–1.65 V | (a) for VCC 1.08–1.65 V; (b) below 1.08 V | D9: no spec below 1.65 V (combinational gates have no retention rating). Physically CMOS still switches at 1.2–1.6 V, so the output *follows its inputs*; the danger is that its inputs (PA_ARMED retained H, WDT_OK = H by DU1) are themselves unsafe. Below 1.08 V the output cannot exceed VENF min (an LVC output cannot go above its VCC), so the TPS22810 is off: bounded (b). |
| Ua6 | Q3 clamp released while PG is "asserted" at 0.5–0.66 V | (a) at hot / pessimistic clamp | DMG1012T VGS(th) 0.5 V min is a 25 °C value (D17); MOSFET thresholds fall with temperature. With 100 kΩ pull-up, Q966 needs only ≈ 30–40 µA to pull IL_Q3G below Q3's VGS(th). Not covered by the sim (Q966 swept 0.5–1.0 V at 25 °C only). |
| Ua7 | LM339B gate/rail channels with inputs < −0.3 V | (a) | Occurs every time IL_REF is off while the DAC holds −1.5…−4.8 V (node ≈ 0.2·Vg = −0.35…−1.0 V) and on V18-0 (rail nodes ≈ −1.0 V). D10 note 1: "the output can be incorrect". Masked by design (IL_EN low ⇒ NEG_OK low), **unmasked if IL_REF is lost by a component failure** (FMEA F-REF). |
| Ua8 | U909 state at VCC 1.5–1.65 V (retains Q = 1) and at power-up | (a) retention; (b) random power-up state | D9 "Data retention only 1.5 V": a flop armed in TX keeps Q = 1 through a +1V8 sag to 1.5 V while ~CLR is not guaranteed. Power-up random state: MCU_PA_EN is a hard 0 V into U911 (physically pulls ~CLR low once VCC ≳ 1 V), so this is a bound (b), but it is not specified. |
| Ua9 | PA_DRAIN_EN at 1.08–1.65 V during +1V8_DIG brown-out with switch still ON | (a) | Combination of DU1 + Ua5 + Ua8 + Ua3. The only defence is U920 (SENSE1 trips at 1.654–1.687 V) with unspecified delay, then the clamp (Ua4). U920 is a **single, latent-failable channel** here (e.g. R978 open ⇒ SENSE1 = V18 ⇒ never trips). |
| Ua10 | Crowbar in linear mode when PA_DRAIN_EN parks in 0.5–1.1 V | (a) | Clamp level (Ua4) overlaps Q2 VGS(th) (0.5–1.0 V at 25 °C, D17). Q2 must sink ≈ (5 − 0.9)/4.7 k = 0.87 mA to hold the crowbar below its 0.9 V threshold (D18): at VGS ≈ Vth it sinks only 250 µA. Result is either "crowbar held off" (sim T50, ≤ 50.3 µs) or a partially conducting crowbar. Shoot-through additionally requires EN > VENF, which at 25 °C needs Vth(Q2) > 1.08 V (impossible at 25 °C); **at −40 °C both Q2 Vth and BAT54C VF rise and no datasheet bounds them** → classify (a) at cold, bounded at 25 °C. |
| Ua11 | PWR_EN_3V3 at 1.16–1.44 V during MCU reset/boot | (a) | D20 pull-up is active "after reset"; R714 100 k is too weak. +3V3_RF may start uncommanded. Not a drain hazard (IL_EN still needs both negative rails, which need PWR_EN_NEG), but it removes the firmware's control of the first rail and sets PG_3V3RF high early. |
| Ua12 | TPS65131 ENN floating when +1V8_DIG absent and +3V3_AUX up | (a) | U913 output is Ioff/high-Z (D9) and the net has no pull-down; ENN is a ≤ 0.1 µA CMOS input (D16). Negative rails can start with +3V3_RF absent → violates ADAR1000 p13 / ADTR1107 p24 ordering → Ua13. The sim's "residual (ordering)" note covers only the pessimistic HIGH, not the floating input. |
| Ua13 | PA_BIAS with AVDD3 absent, AVDD1 present | (a) | Reachable on +3V3_RF loss while −5V_BF still decays (the TPS7A3301 outputs and caps hold it), and via Ua12. ADAR1000 does not state the output behaviour (D21). If the DAC output stage follows AVDD1 the gate sees up to −5 V (> −2 V abs max). |

**Which "pessimistic logic" failures of the review are real?** M5a/M5b/M5c rest on (i) LVC outputs driving 1.1–1.5 mA at VCC < 1.65 V — a bound (b); and (ii) U920 VOL at > 1 mA and BAT54C VF over temperature — genuinely unspecified (a). B-TD (U920 delay) is (a). In addition the auditor finds **DU1 (TPS3430 WDO high in brown-out) is not pessimism but datasheet fact**, and Ua6, Ua12, Ua11 are (a) states that the sim does not model at all.

### 2.4 Thermal shutdown / UVLO of each part

| Part | TSD / UVLO behaviour (DS) | Effect on PA |
|---|---|---|
| U652 TPS62933 (+3V3_AUX) | TSD/UVLO → output off | AUX0 cascade: 1V8 off, negative rails off (TPS65131 VIN), comparators unpowered → NEG_OK L via pull-downs; PA_DRAIN_EN L (R965). Gate: AVDD1 collapses → PA_BIAS → 0 V (assumed) while drain off. Safe, provided U920 (on +5V_PA/+3V3_RF) asserts quickly enough (Ua3). |
| U653 TLV755 (+1V8_DIG) | TSD 165 °C; output off | V18-0: MCU reset, PA_DRAIN_EN L\*, **ENN floats (Ua12)** |
| U650 TPS568230 (+3V3_RF) | TSD/UVLO: "device is shut off and the output will be discharged"; PGOOD L (D15) | PG L ⇒ IL_EN L, TLV755 off, ENN off; drain off. ADAR AVDD3 collapse with AVDD1 decaying ⇒ Ua13 |
| U651 TPS568230 (+5V_PA) | same; PGOOD → PG_5VPA → MCU only | drain supply disappears (benign). OVP (125 %) is FB-based and below-threshold for 5.5–6.25 V; see F-5V |
| U657 TPS65131 | UVLO 2.1–2.7 V on VIN (=AUX) | −5V_BF/−3V3_SW decay → U908 ch A/B ⇒ latched off |
| U658/U659 TPS7A3301 | TSD → output off | as above. **Over-voltage (more negative) failure not monitored** (one-sided window) |
| U921 TLV755 (IL_REF_SRC) | TSD, UVLO (D13) | IL_REF → 0 **while IL_EN may be H** ⇒ F-REF (unsafe: all comparators read "OK"/"pinched") |
| U914 TPS22917 | (load switch; no TSD discussed here) | as U921 |
| U62c TPS22810 | **TSD: switch off, QOD not available (D1), re-enables automatically when cooled (D3)**; UVLO: switch off, QOD disabled below UVLO (D2) | In TSD with EN still high, the crowbar is also held off (Q2 on) ⇒ VOUT decays only through the PAs. Repeated TSD cycling in a shoot-through or PA-short case (no current limit, D8). |
| U920 TPS386000 | VDD < 0.9 V undefined; low-VDD VOL rows defined only on ramp-up (D12) | VIN0 with +5V_PA bulk also gone: PG relies on U650 PGOOD; masked because then nothing powers the drain |
| U702 TPS3430 | VDD 0.8–1.6 V ⇒ WDO **high** (D11) | DU1 |

---

## 3. Task 4: when is the TPS22810 QOD unavailable?

The QOD (RPD 250 typ / 400 max Ω, specified only at "VIN = VOUT = 5 V, VEN/UVLO = 0 V") is **not available**:

1. **Thermal shutdown.** "Note that during thermal shutdown, the QOD functionality is not available. The device does not discharge the load as RPD does not become engaged." (§9.3.2). TSD is not latched: "The switch re-enables once the temperature drops below the TSD – TSD,HYS value." (§9.3.5). TS and its hysteresis are typical-only and characterised at VIN = 18 V.
2. **VIN below UVLO.** "When the power is removed, the input capacitor, CIN, discharges at VIN. Past the set UVLO level, the pull-down resistance RPD becomes disabled and the output no longer becomes discharged." (§9.3.2.1). VUVR 2.0–2.62 V rising, 5 % hysteresis ⇒ disabled below ≈ 1.9–2.5 V VIN. In this design the crowbar gate is also pulled up from the same VIN (R99x 4.7 k from +5V_PA_IN_Cc), so **QOD and crowbar disappear together** when +5V_PA collapses. VOUT is then bounded only by the switch body diode (VOUT abs max "min(VIN + 0.3, 20)") and the PA load.
3. **While EN/UVLO is high.** RPD engages "after the switch becomes disabled" (§9.3.2); with PA_DRAIN_EN stuck or parked above VENF (U705 stuck-high, Ua9, EN back-driven) there is no discharge at all.
4. **During the EN de-glitch and tOFF.** "de-glitch delay on EN/UVLO falling edge … (2.5 μs typical)" plus tOFF 3.3 µs typ, no maximum (§7.6). Before the switch is disabled RPD is not engaged.
5. **Load / back-drive limits.** "When using only the internal RPD … the total capacitive load must not exceed 200 uF … the remaining charge from CL … must not be driven." Per chain the VOUT capacitance is ≈ 20 µF (OK), but any case where VOUT is driven (e.g. switch fails short) is outside the QOD rating.
6. **Not specified at all for VIN ≠ 5/12/18 V or VIN ≠ VOUT** (e.g. during the VIN collapse in VIN0 or 5P0).

Consequences for this design: (i) TSD with EN high (overcurrent, shoot-through, PA short) leaves VOUT discharged only by the PAs; (ii) in a +5V_PA collapse the crowbar cannot help either; (iii) the 50 µs criterion is therefore met only by the crowbar, which itself depends on VIN ≥ ≈ 1.5–2 V (crowbar VGS(th) 0.9–1.55 V at 25 °C, RDS(on) specified only at 4.5 V).

---

## 4. Task 2: FMEA

Severity: **S5** destructive/fire (PCB, R_CB, regulator) or PA destroyed with energy; **S4** PA abs-max exceeded with drain energised, or loss of the 50 µs criterion in a real fault; **S3** abs-max stress at negligible energy, or latent loss of one protection layer; **S2** availability/nuisance; **S1** negligible. "Latent" = no hardware or firmware indication during normal operation.

### 4.1 Interlock logic and comparators

| ID | Component / function | Failure mode | Local effect | System effect (PA gate / drain) | Detection | Sev | Existing mitigation | Residual risk |
|---|---|---|---|---|---|---|---|---|
| F1 | U705 (final AND) | output stuck H / latch-up | PA_DRAIN_EN H | all 4 drains on irrespective of gates, rails, watchdog, latch; no crowbar | **none** (PA_DRAIN_EN, VOUT not observable; INA226 sees current only if gates biased) | S5 | supervisor clamp only for V18/AUX/RF faults | **single point, latent**. Add MCU readback of PA_DRAIN_EN/VOUT and a second, diverse EN path (e.g. PA_DRAIN_EN gated again by NEG_RAILS_OK in an OD stage) |
| F2 | U705 | stuck L / open | drain never enabled | none (safe) | arming fails | S2 | — | — |
| F3 | PA_DRAIN_EN net | PCB short to +1V8_DIG/+3V3 net | EN H | as F1 | none | S5 | — | layout keep-out; readback |
| F4 | U62c TPS22810 | EN pin ↔ VIN internal short (damaged part) | PA_DRAIN_EN pulled to ≈5 V (only R735 1 k from U705) | **all four chains** enabled (shared EN net), crowbars held off | none | S5 | U705 sinking through 1 k cannot win | common-cause across chains; per-chain EN buffering/series R would contain it |
| F5 | U62c TPS22810 | pass FET short | VOUT = VIN always | drain energised at every +5V_PA enable, incl. ADAR1000 reset (gates 0 V, D21) ⇒ 0.6 A/PA; on disarm the crowbar fires into a live +5V_PA (8–12 A U651 OCL; R_CB 0.333 Ω ⇒ 21–48 W in three 1206 parts; UVP at 60 % may not trip at the 12 A end) | INA226 current (fw) | S5 | none in HW | **TE1 and TE3**; no current limit anywhere in the PA path |
| F6 | U62c | tOFF slow (unspecified max) | switch opens late | T50 fails; crowbar/switch overlap (TE3) | none | S4 | crowbar (but overlap risk) | B-TOFF; bench |
| F7 | U62c | TSD (overcurrent/PA short) | switch off, **QOD off**, auto re-enable | repeated pulses into the fault; crowbar not fired (EN high) | INA226 (fw) | S4 | TPS22810 self-protection | hiccup into a shorted PA/crowbar; fw must drop MCU_PA_EN |
| F8 | U62c | QOD/RPD open | slower discharge | T50 only via crowbar; 7 ms if crowbar also fails | none | S3 latent | crowbar | — |
| F9 | U912 (NEG_OK AND) | stuck H | NEG_OK H | gate-lost (16) and all rail monitors and PG removed from U705/U911 | **fw proof test possible** (PA0 reads NEG_OK; write one gate to 0 V while disarmed) | S4 | supervisor clamp (V18/AUX only) | latent until proof-tested; no proof test is specified |
| F10 | U915 (IL_EN AND) | stuck H | IL_EN H | rail monitors and PG bypassed for NEG_OK and for TPS22917 ON (Q3 still clamps on PG low) | fw proof test (pull PWR_EN_NEG low, read NEG_OK) | S4 | Q3 clamp; U921 EN | latent |
| F11 | U909 flop | Q stuck H | PA_ARMED H | no pinch check, no fault latch, **MCU_PA_EN can no longer disarm**; drain = WDT_OK·NEG_OK | none (PA_ARMED not routed to MCU) | S4 | gate-lost, rails, WDT still act | latent; route PA_ARMED to MCU |
| F12 | U911 (CLR AND) | stuck H | CLR never asserted | faults not latched; drain re-enables after a transient without pinch (spec F4 regression) | none | S3 latent | U705 still drops during fault | — |
| F13 | U910 / C912 / R964 | stuck / open | no clock | cannot arm | arming fails | S2 | — | — |
| F14 | R955 open or R954 short (PINCH ref) | IL_REF_PINCH → IL_REF (1.8 V) | all 16 pinch channels read "pinched" | arming possible with gates at ON bias or 0 V | none | S4 | gate-lost still trips at −0.15 V | **single resistor defeats the pinch check for all gates, latent** |
| F15 | R953 open or R952 short (LOST ref) | IL_REF_LOST → 1.8 V (> VCC−2, but node input in range ⇒ valid "OK") | all 16 gate-lost channels read "OK" | gate rising to 0 V not detected (0.6 A/PA) | fw proof test via NEG_OK | S4 | — | single resistor, latent |
| F-REF | U921 TLV755 / U914 TPS22917 dead, C915 short, R972/QOD stuck on | IL_REF = 0 V (or low) while IL_EN = H | both refs = 0; gate nodes = 0.2·Vg ⇒ any gate ≤ 0 reads "OK" and "pinched"; at gate 0 V both inputs are equal (VIO decides). Partial IL_REF droop scales both trip points toward 0 V (ratiometric) | **gate-lost and pinch checks silently disabled**; nothing monitors IL_REF | none (fw proof test at gate = 0 V is ambiguous) | S4 | none | **design gap: the reference that defines "fault" can disappear without causing a fault.** Monitor IL_REF with a U908-type channel on NEG_RAILS_OK, or reference the LOST comparator so that loss of IL_REF trips |
| F16 | Gate divider Rt (R901+3n) open | node = 0.2·Vg only | that gate always "OK" and "pinched"; LM339 input < −0.3 V | per-gate loss of both checks | none | S4 (per PA) | — | latent per gate |
| F17 | Gate divider Rg (R900+3n) short | node = gate voltage | as F16, plus DAC drives the 17.4 k/45.3 k legs (≤ 0.2 mA) | per-gate loss | none | S4 | — | latent |
| F18 | Rg open / Rn open | node rises | gate-lost trips / cannot arm | safe | nuisance trip | S2 | — | — |
| F19 | LM339B output open (any channel) | wired-OR misses that channel | per-gate loss of lost or pinch check | none (lost: fw proof test) | S3 latent | — | — |
| F20 | LM339B package V+ or GND pin open | 4 outputs off ⇒ pull-up wins ⇒ "OK" | U908: **all four rail monitors lost**; U90x: 2 gates × 2 checks lost | none | S4 (U908) | — | latent; R961/R969/R963 make AUX loss safe but not a single-package power-pin open |
| F21 | LM339B output stuck low | nuisance trip | safe | — | S2 | — | — |
| F22 | R960/R968/R962 shorted to +3V3_AUX (PCB) | wired-OR cannot be pulled low (25 mA abs max into 0 Ω) | that net stuck H | as F9/F14 | none | S4 | — | layout |
| F23 | R965 open | PA_DRAIN_EN floats when U705 unpowered | TPS22810 EN "must not be left floating" (D6) | covered only if U920 powered and asserted (BAT54C then clamps any EN > 0.24 V) | none | S3 latent | D961 clamp | depends on U920 |
| F24 | R735 short | clamp current = LVC IOH (several mA) | U920 sink > 1 mA, possibly > 5 mA abs max | clamp level higher (M5 worse) | none | S3 | — | — |
| F25 | MCU PA3 configured as output-high (fw fault, crashed MCU) | WDT_OK forced H against TPS3430 OD (VOL spec 0.4 V @ 3 mA) | **watchdog defeated** for U705, U911 and U703 (PA_ON) | MCU hang with ON-bias and armed ⇒ drain stays on indefinitely | none | S4 | — | no series R / no input-only enforcement in HW. Add 1–10 k series R on PA0/PA1/PA3 or use buffers |
| F26 | MCU PA0 output-high (fw) | contention with U912 | NEG_OK level undefined/H | gate-lost and rail paths defeated | none | S4 | — | as F25 |
| F27 | MCU PA1 output-high (fw) | contention with U650 PGOOD / U920 (≤ 5 mA abs max) | PG_3V3RF H, U920 overstressed | supervisor, TLV755 EN, Q3 clamp, ENN gate all defeated | none | S4 | — | as F25 |
| F28 | U702 TPS3430 WDO pin open / part dead | WDT_OK H via R702 | watchdog lost | latent | none | S3 | — | fw can test by withholding WDI (needs ≤ 125 ms) |
| F29 | TPS3430 brown-out behaviour (by design, D11) | WDO H for 0.8 < VDD < 1.6 V and ~100–137 ms after power-up | WDT_OK gives no protection in exactly the V18b band | see Ua9 | — | S3 | U920 SENSE1 | DU1; sim models the opposite |

### 4.2 Supervisor, clamp and IL_REF supply

| ID | Component / function | Failure mode | Local effect | System effect | Detection | Sev | Existing mitigation | Residual risk |
|---|---|---|---|---|---|---|---|---|
| F30 | U920 TPS386000 | RESET1/2 open / part dead | PG = U650 PGOOD only | no +1V8_DIG/+3V3_AUX supervision; no clamp | none (PG still toggles via U650) | S4 latent | U908 ch C (AUX 2.97 V) partly overlaps | single channel for the V18b band |
| F31 | R978 open (SENSE1 bottom) / R1000 open | SENSE = rail ⇒ never trips | +1V8 (or AUX) UV never detected | as F30 for that rail | none | S4 latent | — | — |
| F32 | R977 open / R979 open | SENSE = 0 ⇒ always asserted | PG L | cannot arm | obvious | S2 | — | — |
| F33 | D960 both diodes open | U920 VDD ≈ 0 | outputs undefined (D12) | as F30 | none | S4 latent | — | — |
| F34 | U920 assert delay long (unspecified) | late PG L | clamp/IL_EN late | B-TD: EN on with invalid supply, 1.5–4.0 µs crowbar overlap in sim | none | S4 | — | bench or part with specified tPD |
| F35 | U920 VOL at 2.4–4.4 mA (unspecified) | PG 0.5–0.66 V (pess.) | TLV755 EN not guaranteed off; Q966 partly on (Ua6); clamp levels 0.8–0.97 V hold Q2 on | T50 up to 50.3 µs; IL_REF possibly on | none | S4 | — | M5a/b/c + Ua6; also violates "pullup resistor should be no smaller than 10 kΩ" (effective 1 kΩ) |
| F36 | D961 BAT54C open | no clamp | V18b band unprotected except via U915 | none | S4 latent | IL_EN path | — |
| F37 | D961 short (anode–cathode) | PA_DRAIN_EN/IL_CLR_N tied to PG_3V3RF | PG high (1.8 V via 100 k) ⇒ PA_DRAIN_EN pulled toward 1.8 V through 100 k when U705 drives low through 1 k ⇒ ≈ 0.02 V (OK); but **when U705 is unpowered PA_DRAIN_EN = PG** | if +1V8_DIG present and U705 high-Z (U705 fault): PG high ⇒ switch on | none | S3 | — | double fault needed |
| F38 | Q966 (inverter) open / gate open | IL_Q3G always H | Q3 always on ⇒ IL_REF never on | cannot arm (gates read lost) | obvious | S2 | — | — |
| F39 | Q966 D–S short / Q965 open | Q3 never clamps | TPS22917 ON = IL_EN only | Q3 layer lost | none | S3 latent | U921 EN, U915 | — |
| F40 | R976 open | IL_Q3G = 0 | same as F39 | | none | S3 latent | | |
| F41 | U921 TLV755 pass short | IL_REF_SRC = +3V3_RF (3.3 V) | IL_REF 3.3 V when on: nodes leave VCM (> 1.3 V), trips scale ×1.83 (pinch −2.75 V ⇒ cannot arm normally; lost −0.27 V ⇒ nuisance); **positive injection Thevenin ≈ +2.4 V/62.5 kΩ** if PA_BIAS high-Z | TE2 risk | arming failure (indirect) | S3 | TPS22917 | — |
| F42 | TPS22917 pass short | IL_REF = IL_REF_SRC | one of two series layers lost | latent | none | S3 | U921 EN = PG | — |
| F43 | PG pull-up R654 shorted to +1V8_DIG | PG cannot be pulled low (U920 5 mA abs max into 0 Ω) | supervisor + U650 PGOOD defeated | as F30 + loses A2 ordering | none | S4 | — | layout |

### 4.3 Crowbar and its driver

| ID | Component / function | Failure mode | Local effect | System effect | Detection | Sev | Existing mitigation | Residual risk |
|---|---|---|---|---|---|---|---|---|
| F44 | Q97c (Q2) | drain–source open / gate open | crowbar gate = VIN always | **crowbar permanently on**; at arm, TPS22810 drives into 0.36 Ω ⇒ ≈ 13 A until TPS22810 TSD, then auto-restart cycles (D3) | INA226 (fw) | S5 | none (no current limit, D8) | **TE3, single point, latent until arm** |
| F45 | R99x 10 k (R996..R999) open | Q2 gate floating on C93x | undefined Q2 | either crowbar never fires (TE4) or fires during armed TX (TE3) | none | S5 | — | latent |
| F46 | C93x short | Q2 gate = 0 | crowbar always on | as F44 | INA226 | S5 | — | — |
| F47 | Q2 G–D short (typical ESD failure) | PWR_CB_Gc ↔ PWR_CB_Dc | PA_DRAIN_EN pulled to 5 V × 100 k/114.7 k ≈ 4.4 V **when U705 is unpowered**; ≈ 0.3 V when U705 drives low | +1V8_DIG absent ⇒ all switches on, crowbars off | none | S4 | BAT54C clamp if U920 powered & asserted (sinks ≈ 0.3 mA) | depends on U920 |
| F48 | Q2 stuck on (D–S short) | crowbar never fires | T50 relies on QOD: 7.2 ms gates-pinched case, 73–111 µs others (R2 data) | none | S4 latent | QOD | proof test needs VOUT monitor |
| F49 | Q96c crowbar D–S short / G–D short | VOUT shorted through 0.333 Ω | TE3 whenever armed (as F44) | INA226 | S5 | — | — |
| F50 | Q96c open / R_CB (all three) open | no crowbar | T50 lost (QOD only) | none | S4 latent | QOD | — |
| F51 | R_CB one of three open | 0.5 Ω, ≥ 1.5× energy share in the other two | slower T50, more stress | none | S3 | — | — |
| F52 | R99x 4.7 k (R992..R995) open | crowbar gate floats | crowbar may not fire (TE4) or may float on (TE3) | none | S4 | — | — |
| F53 | R_CB pulse rating exceeded | RCS1206 curve is for pulses at ≥ 1-min intervals | drift/open after rapid arm/disarm cycling | as F50 | none | S3 | fw arm-rate limit (not specified) | firmware-dependent |
| F54 | Q2 Vth at temperature (unspecified, D17) | release earlier/later | cold: Q2 releases at higher EN ⇒ overlap with tOFF; hot: clamp level holds Q2 on longer | TE3/TE4 | none | S4 | sim corners 0.5/1.0 V at 25 °C | bench at −40/+85 °C |

### 4.4 Regulators feeding the PA and the ADAR1000 bias path

| ID | Component / function | Failure mode | Local effect | System effect | Detection | Sev | Existing mitigation | Residual risk |
|---|---|---|---|---|---|---|---|---|
| F-5V | U651 TPS568230 (+5V_PA) | **FB top R655 open or R656 short** (FB ≈ 0 ⇒ max duty), or high-side FET short | +5V_PA → ≈ VIN 12 V; OVP is FB-based (D15) so it **does not trip** on FB-open | **12 V on all 16 VDD_PA through the TPS22810** (abs max 5.5 V, D22); U920 VDD 12 V via D960 (abs max 7 V) ⇒ supervisor destroyed, outputs unknown; crowbar firing into 12 V ⇒ 33 A | PG_5VPA L (FB < 85 %), **routed to MCU only** | S5 | none in HW | **single resistor ⇒ destruction of every PA**. Route PG_5VPA into the PG_3V3RF wired-AND (both are OD) and add an independent +5V_PA OV comparator (U908-style) on NEG_RAILS_OK |
| F55 | U651 | output 5.5–6.25 V (load-step overshoot, drift) | below its 125 % OVP | PA abs max exceeded, nothing reacts | INA226 Vbus (fw) | S4 | — | B-INDUCT |
| F56 | U650 TPS568230 (+3V3_RF) | FB open / HS short | +3V3_RF → 12 V | ADAR1000 AVDD3 (abs max 3.6 V) destroyed ⇒ PA_BIAS undefined ⇒ TE2; ADTR1107 VDD_SW | PGOOD L ⇒ PG L ⇒ drain off (good) | S5 (parts) | PG in chain | gates unprotected after ADAR damage; drain off |
| F57 | U650 | output OV 3.6–4.16 V (< OVP 125 %) | AVDD3 abs max exceeded | ADAR stress | none (U908 ch D is UV only) | S4 | — | one-sided monitor |
| F58 | U658 TPS7A3301 (−5V_BF) | pass short ⇒ −6.3 V (PWR_VNEG) | AVDD1 abs max −5.5 V exceeded | ADAR damage ⇒ PA_BIAS undefined (TE2) | **none** (U908 ch A only checks > −4.6 V) | S4 | — | one-sided window; add an over-magnitude channel |
| F59 | U659 (−3V3_SW) | pass short ⇒ −6.3 V | ADTR1107 VSS_SW over-range | switch damage | none | S4 | — | as F58 |
| F60 | U657 TPS65131 ENN | floats when +1V8_DIG absent (Ua12) | negative rails start with +3V3_RF off | ADAR AVDD1 before AVDD3 ⇒ Ua13 ⇒ possible VGG < −2 V; drain off | none | S4 | — | add 100 k pull-down on PWR_ENN_NEG (A3 did this for the MCU-driven enables but not for U913's output) |
| F61 | U653 TLV755 (+1V8_DIG) brown-out 1.08–1.65 V | V18b band | Ua9 | U920 only | — | S4 | U920 + clamp | B-TD, M5 |
| F62 | PWR_EN_3V3 at MCU reset | Ua11 | +3V3_RF may start uncommanded | ordering only | — | S2 | — | 10 k pull-down or move off PB4 |
| F63 | ADAR1000 | firmware writes PA bias code > 0x6A (< −2.0 V), incl. ADI's own 0x85 recipe | VGG < −2 V | TE2 | none | S4 | fw limit 0x5D | **firmware-only (S1/B-S1)** |
| F64 | ADAR1000 | SPI corruption / SDO-contention erratum / soft reset during TX | arbitrary or 0 V bias | gate-lost catches 0 V; codes in (−1.5, −0.15) V or < −2 V not caught | none | S4 | gate-lost | — |
| F65 | ADAR1000 AVDD3 lost, AVDD1 present | Ua13 | PA_BIAS unspecified | TE2 possible | — | S4 | +3V3_RF UV channel removes drain/IL_REF; gate unprotected | B-ADAR |
| F66 | PA_BIAS trace/solder open between ADAR and the Rg tap | gate on divider only | gate → +1.30 V/62.5 kΩ, clamped by gate diode ≈ +0.6 V (≈ 11 µA) when IL_REF on | gate-lost trips (drain off) but **VGG > 0 V abs max** (TE2) for as long as IL_REF is on | NEG_OK L (fw sees) | S3 | R5 layout makes the open detectable | low energy, but abs max exceeded by design choice |
| F67 | Armed, firmware leaves ON bias outside TX (or TR stuck high, PA_ON ineffective because BIAS_CTRL = 0) | drain on, gate −1.1 V | 220 mA/PA quiescent outside TX | none (hardware cannot distinguish TX from armed-idle) | S2–S3 | WDT (125 ms) on hang | firmware-only by architecture |
| F68 | Gate drifts into (−1.5, −0.15) V after arming (DAC error, fw code 0x08–0x4F) | Idq above nominal (up to ≈0.6 A at 0 V) | not detected (no window between −0.15 and −1.5 V after arming) | INA226 (fw) | S3 | — | no hardware overcurrent trip on +5V_PA_Cc |

---

## 5. Task 3: fault trees

Notation: `OR{…}`, `AND{…}`. Basic-event tags: **[FW]** firmware-dependent; **[U:x]** relies on an unspecified datasheet parameter x; **[B]** bounded by datasheet or physics; **[HW]** random hardware failure; **[L]** latent (not indicated in normal operation).

### TE1: PA drain energised while any gate is above −1.5 V outside armed TX

```
TE1 = OR{
  G1  switch conducts without a valid arm:
      OR{ F5 TPS22810 pass short [HW][L],
          F4 any TPS22810 EN–VIN short (all 4 chains) [HW],
          F1 U705 stuck H [HW][L],  F3 PA_DRAIN_EN bridged high [HW],
          F47 Q2 G–D short AND +1V8_DIG absent AND U920 not clamping [HW][U:U920 VOL/delay],
          G1a false arm: AND{ MCU_PA_EN rising edge [FW],
                               OR{ F14 R955 open / R954 short [HW][L], F-REF IL_REF lost [HW][L],
                                   F16/F17 per-gate Rt open / Rg short [HW][L], F19 pinch channel open [HW][L],
                                   F20 package power pin open [HW][L], F22 pull-up bridged [HW] } },
          G1b power-state: AND{ +1V8_DIG in 1.08–1.65 V [reachable],
                                PA_ARMED retained/random H [U:LVC <1.65 V (Ua8)],
                                WDT_OK H [B: DS-defined H, D11 — i.e. TRUE],
                                NEG_OK/U705 output H [U:LVC <1.65 V (Ua5)],
                                OR{ U920 delay [U:tdet], U920 VOL/clamp too high [U:VOL>1 mA, BAT54C VF(T)], F30/F31/F33/F36 [HW][L] } },
          F11 flop Q stuck H AND gates > −1.5 V [HW][L] },
  G2  armed, gate moved above −1.5 V outside TX:
      OR{ F67 ON bias left / TR stuck / PA_ON ineffective [FW], F68 code in (−1.5,−0.15) V [FW], F64 SPI corruption [FW/HW] },
  G3  gate above −0.15 V and interlock does not drop:
      AND{ gate lost (ADAR reset, PA_BIAS open, AVDD3 loss) ,
           OR{ F9 U912 stuck H [HW][L], F15 R953 open/R952 short [HW][L], F-REF [HW][L],
               F16/F17 [HW][L], F19/F20 [HW][L], F26 PA0 driving NEG_OK [FW], F1/F3/F4/F5 } },
  G4  MCU hang while armed with ON bias, watchdog defeated:
      AND{ MCU hang [FW], OR{ F25 PA3 output-high [FW], F28 WDO open [HW][L] } } }
```

Minimal cut sets (order 1 unless stated):
- {F5}, {F4}, {F1}, {F3} — hardware singles, F5/F1 latent and **unobservable** (no PA_DRAIN_EN/VOUT readback).
- {F67}, {F68}, {F64} — firmware singles (by architecture; hardware cannot know "outside TX").
- Order 2: {FW arm edge, F14}, {FW arm edge, F-REF}, {FW arm edge, F16/F17/F19 on that gate}, {gate lost, F9}, {gate lost, F15}, {gate lost, F-REF}, {gate lost, F26 [FW]}, {MCU hang, F25 [FW]}, {MCU hang, F28}, {F11, ON bias}.
- Order 3–4 (supply-state): {V18 brown-out 1.08–1.65 V, Ua8, Ua5, U920 delay [U]} — DU1 contributes a TRUE input, so it does not appear as an event; {F47, V18-0, U920 not clamping [U]}.

### TE2: VGG_PA outside −2.0 … 0 V

```
TE2 = OR{
  F63 firmware writes code > 0x6A (incl. ADI recipe 0x85) [FW]            (single)
  F64 SPI/register corruption to a code > 0x6A [FW/HW]                       (single)
  Ua13 AND{ AVDD3 absent, AVDD1 present [reachable: +3V3_RF loss with −5V_BF decaying; or F60/Ua12 ENN float],
            PA_BIAS follows AVDD1 [U:ADAR1000 power-down behaviour not stated] }
  F58 −5V_BF over-magnitude ⇒ ADAR damaged [HW] (single, undetected)
  F56 +3V3_RF OV ⇒ ADAR damaged [HW] (single; drain off, gate undefined)
  positive injection: AND{ PA_BIAS not driving [U:ADAR high-Z threshold, assumed 2.8 V],
                           IL_REF on: OR{ AND{TLV755 EN in 0.3–1.0 V [U:U920 VOL>1 mA, Ua4],
                                              TPS22917 ON high: OR{U915 out H at VCC<1.65 [U:Ua5], Q3 clamp released [U:Q966 Vth(T), Ua6], F39/F40 [HW][L]}},
                                          F41/F42 [HW][L] } }
  F66 PA_BIAS open between ADAR and Rg tap [HW] (single; +0.6 V at ≈ 11 µA, drain off) }
```

Minimal cut sets: {F63}, {F64}, {F58}, {F56}, {F66} (order 1); {AVDD3 loss with AVDD1 up, ADAR output follows AVDD1 [U]}; {1V8-only failure ⇒ ENN floats, ADAR output follows AVDD1 [U]}; {PA_BIAS high-Z [U], TLV755 EN not off [U], U915/ON undefined [U]} (order 3, sim says pass at U920 delay 0.1 µs, REF fails at ≥ 50 µs).

### TE3: crowbar conducts while the PA supply switch is on

```
TE3 = OR{
  F44 Q2 open [HW][L],  F45 R99x open [HW][L],  F46 C93x short [HW],  F49 crowbar short [HW],  F52 R_CBPU open (floating on) [HW]    (single; detected only by fw via INA226 after the event)
  F5  switch short, then any disarm/fault [HW][L] (single: crowbar fires into live +5V_PA, 8–12 A sustained by U651)
  AND{ fault turn-off edge, tOFF + de-glitch > Q2 release time [U:TPS22810 tOFF max; U:Q2 Vth over temperature] }
  AND{ arm edge, tD < Q2 turn-on (~8 µs) [U:TPS22810 tD min] }
  AND{ PA_DRAIN_EN parked between Q2 release level and VENF [reachable via clamp, Ua4/Ua10], Vth(Q2) ≥ VENF [B at 25 °C: 1.0 < 1.08 V; U at −40 °C] }
  AND{ +1V8_DIG abrupt loss, U920 delay ≥ 20 µs [U:tdet] }            (sim: 1.5–4.0 µs overlap, 2–6 runs)
  F47 Q2 G–D short with U705 unpowered [HW] (switch on via 4.4 V, crowbar off: not TE3, but TE1) }
```

Minimal cut sets: {F44}, {F45}, {F46}, {F49}, {F52}, {F5 + any disarm} (hardware, order 1–2, no hardware current limit downstream of U651 except TPS22810 TSD); {tOFF long [U], cold Q2 [U]}; {tD short [U]}; {U920 delay [U], V18 abrupt loss}. None of the order-1 hardware cut sets is detected before the event.

### TE4: drain not below 0.5 V within 50 µs after a fault

```
TE4 = OR{
  switch does not open: OR{ F1, F3, F4, F5, F9 (gate/rail faults), F25/F26/F27 [FW], G1b supply band [U] }
  switch opens late: OR{ tOFF [U:no max], LM339B response [U:1 µs typ only, VS = 5 V test], U920 delay for V18/AUX faults [U] }
  crowbar does not fire / fires late:
     OR{ Q2 held on by clamp level 0.8–0.97 V [U:U920 VOL>1 mA, BAT54C VF(T), Q2 Vth(T)] (sim worst 50.3 µs),
         F48 Q2 stuck on [HW][L], F50 crowbar/R_CB open [HW][L], F52 [HW], F45 [HW][L],
         crowbar gate supply gone: +5V_PA_IN collapsing (VIN0/5P0) [B: then VIN also gone, VOUT ≤ VIN + diode],
         TPS22810 TSD with EN high (QOD off, crowbar off) [HW] }
  and QOD cannot rescue it: OR{ TSD (D1), VIN < UVLO (D2), EN high } }
```

Minimal cut sets: {F1}, {F3}, {F4}, {F5}, {F48}, {F50}, {F45}, {F52} (order 1, all latent); {gate fault, F9}; {fault, F25/F26/F27 [FW]}; {clamp-level fault (V18 band), U920 VOL [U], cold BAT54C/warm Q2 [U]} (the sim's T50/A failure family); {tOFF > ≈ 20 µs [U]}; {U920 delay ≥ 20 µs [U], V18 abrupt loss}.

### Summary of basic-event dependencies

| Dependency | Basic events |
|---|---|
| **Firmware** | F63 code > 0x6A; F64 SPI corruption; F67/F68 bias outside TX; arm edge with unpinched gates (G1a); F25/F26/F27 MCU pins driven as outputs on WDT_OK/NEG_OK/PG_3V3RF; F53 arm-rate; proof tests (none specified) |
| **Unspecified DS parameter** | TPS22810 tOFF max / tD min; TPS386000 assert delay; TPS386000 VOL above 1 mA and on VDD ramp-down; BAT54C VF and DMG1012T/CSD16301 VGS(th) away from 25 °C; LM339B VIO/response at VS = 3.3 V; LVC function at VCC < 1.65 V; ADAR1000 PA_BIAS with AVDD3 absent; TPS22810 QOD below VIN UVLO |
| **Bounded** | LVC output ≤ VCC (⇒ TPS22810 off for V18 < 1.08 V); Vth(Q2) max 1.0 V < VENF min 1.08 V *at 25 °C*; PG/WDT pull-ups dead when +1V8_DIG absent; LM339 input current < 0.1 mA when IL_REF off; positive gate injection ≤ ≈ 11 µA |
| **Datasheet-defined, unsafe** | TPS3430 WDO high for 0.8 < VDD < 1.6 V and during power-up (DU1); TPS22810 QOD off in TSD and below UVLO; TPS22810 TSD auto-restart; TPS22810 has no current limit |

---

## 6. Top findings (ranked)

1. **F-5V (S5, single point, not in the review).** An open R655 (or short R656) in the +5V_PA feedback drives +5V_PA toward 12 V. The TPS568230 OVP is FB-based, so it does not trip. The TPS22810 passes it to all 16 VDD_PA (abs max 5.5 V), and D960 puts 12 V on the TPS386000 (abs max 7 V). The only indicator, PG_5VPA, goes to the MCU only. Fix: put U651 PGOOD into the PG_3V3RF wired-AND (both OD) and add a +5V_PA over-voltage channel to NEG_RAILS_OK.
2. **F-REF (S4, latent, not in the review).** Nothing monitors IL_REF. If U921 or U914 fails, or C915 shorts, while IL_EN is high, both thresholds collapse to 0 V. Every gate then reads "OK" and "pinched", so the gate-lost and pinch checks are silently gone. A single open R953/R955 (F14/F15) has the same effect for one check across all 16 gates.
3. **No current limit in the PA path, plus single-component shoot-through (F44/F45/F46/F49/F5; S5).** The TPS22810 has only thermal shutdown, and it re-enables by itself (D3). One open Q2, open R996–R999, shorted C931–C934 or shorted crowbar leaves the crowbar permanently on. The next arm then puts about 13 A through 0.333 Ω with TSD cycling. A shorted switch makes every disarm fire the crowbar into U651, which supplies 8–12 A. None of these faults is visible before it happens.
4. **DU1: the TPS3430 WDO is defined HIGH for +1V8_DIG between 0.8 and 1.6 V, and for about 100–137 ms after power-up (§7.4.2).** The sim models WDT_OK = 0 below 1.65 V. In the brown-out band, WDT_OK therefore protects nothing, and the review's nominal "0/920" result rests on a watchdog behaviour that the real part does not have.
5. **Single-channel convergence on U705 / PA_DRAIN_EN, with no readback (F1/F3/F4/F11).** Gate, rail, watchdog and latch faults all reach the drain through one LVC1G11 and one net shared by all four chains. One damaged TPS22810 (EN–VIN short) enables all four chains. PA_DRAIN_EN, PA_ARMED and VOUT are not routed to the MCU, so the faults are latent and proof tests are impossible.
6. **MCU GPIOs sit directly on safety nets (F25/F26/F27, firmware-dependent).** PA3 is on WDT_OK, PA0 on NEG_OK and PA1 on PG_3V3RF, with no series resistors. If a crashed or misconfigured MCU drives any of them high, it overrides the watchdog, the interlock or the supervisor. Pin PA1 driving high can also exceed the TPS386000 5 mA abs max.
7. **B-TD / M5, confirmed as genuinely unspecified (Ua3/Ua4/Ua9).** In the 1.08–1.65 V +1V8_DIG band, the only defence is U920 plus the BAT54C clamp. The relevant behaviour depends on the unspecified assert delay, VOL above 1 mA (and VOL on VDD ramp-down), and BAT54C VF and DMG1012T VGS(th) away from 25 °C (all specified at 25 °C only). U920 is also latent-failable (R978/R1000 open, D960 open).
8. **Temperature is not covered for any threshold device in the clamp/crowbar timing (F54/Ua6/Ua10).** VGS(th) of Q2, Q966 and the crowbar, and VF of the BAT54C, are 25 °C numbers only. At cold, the Q2 release level rises toward VENF min (1.08 V), so the shoot-through margin (2.5 µs at the sim's worst corner) shrinks. At hot, Q966 can partly conduct at the clamp-raised PG level and release the Q3 clamp. The sim varies these only at 25 °C corners.
9. **Ua12 / F60: PWR_ENN_NEG has no pull-down.** With +1V8_DIG absent and +3V3_AUX up, U913 goes high-Z and ENN floats (IIN ≤ 0.1 µA). The negative rails can then start before +3V3_RF, which defeats A2. This leads to Ua13: the ADAR1000 PA_BIAS behaviour with AVDD1 up and AVDD3 down is unspecified, a possible TE2 path. A3 added pull-downs to the MCU enables but missed this LVC-driven one. Related one-sided gaps: rail monitors have no over-magnitude check (F58/F59), and the +3V3_RF monitor has no OV check (F57).
10. **TE2 stays firmware-only and partly design-inherent (F63/F64/F66), and the TPS22810 QOD is lost exactly when it is needed.** VGG below −2 V has no hardware clamp. A PA_BIAS open puts about +0.6 V on the gate by design (R5 layout). QOD is unavailable in TSD and below VIN UVLO, and the crowbar shares the same VIN, so on a +5V_PA collapse both discharge paths go away together.

Lower-ranked but real: Ua11 (STM32 PB4 NJTRST pull-up enables U650 at reset); LM339B VIO and response times are specified only at VS ≥ 5 V while the design runs at 3.3 V; per-gate latent faults (Rt open, Rg short, open comparator outputs); and a single open supply pin on U908 loses all four rail monitors (F20).

## 7. Notes on the existing review / sim (for the record)

- The review's netlist claims check out: U915/R973, U914/U921, D961, R735/R975, U920 wiring, crowbar per chain, U908 ch D on IL_RFMON.
- The sim's **nominal** mode is optimistic in two places the datasheets contradict: WDT_OK (DU1), and "MCU GPIO low below 1.65 V". The second holds only below VBOR0 (1.60–1.69 V, D20). Its **pessimistic** mode is pessimistic in the LVC drive strength (b), but it does not cover DU1-specific logic, temperature, Ua6, Ua11 or Ua12.
- The pessimistic failures M5a/M5b/M5c and B-TD should stay as blockers. The auditor would add F-5V, F-REF, F44 to F46, DU1, F60/Ua12 and F25 to F27 to the exit criteria before layout.
