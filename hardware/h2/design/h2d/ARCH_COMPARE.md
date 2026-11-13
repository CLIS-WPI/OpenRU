# H2-D: PA safety architecture comparison (as-built H2-C vs two alternatives)

- **Date:** 2026-11-12. **Analysis only:** no KiCad file was opened or edited, and nothing was committed.
- **Inputs:** `h2d/AUDIT_FMEA.md`, `h2d/CHARACTERISTICS.md`, `h2d/GATE_BIAS_ANALYSIS.md`, `design/h2c/*.md`, `reports/H2C_HARDWARE_SAFETY_REVIEW.md`, and `sim/H2C_SEQUENCING_SIM.md`.
- **New datasheets** are in `h2d/archds/` (text extracts in `h2d/archds/txt/`). They are TI TLV3201/3202, TLV3601, LMV7219, LMV7235/9, TLV7011/7031, TLV1805, TLV3501, TLV6713, TPS7A25, SN74LVC1G14/04, TPS3840 and TPS3762, plus onsemi NVMFS5C430N and 2N7002L and Diodes DMN3018SSS and DMT3009LDT.
  - nexperia.com returned "Access Denied" and vishay.com returned HTML. I did not try to get around either block.
- **Sim and calculation files** are in `h2d/sim/`:
  - `budget.py` with output `budget.txt`;
  - `arch_a_sim.py` with output `arch_a_results.md` and netlists `cases/*.cir`;
  - `rise_check.py` with output `rise_check.txt`.

Evidence classes:

| Class | Meaning |
|---|---|
| **DS** | Datasheet limit (min/max). The page is given. |
| **DS-TYP** | Typical value only, so not a bound. |
| **DERIVED** | Calculated from DS limits. |
| **PLACEHOLDER** | Engineering bound with no datasheet basis. Must be measured. |
| **SIM-BEHAV** | ngspice behavioural model. **BEHAVIOURAL / PRELIMINARY**, not hardware-validated. |

---

## 0. Verdict

| | As-built H2-C | **A: voltage-gated permit + eFuse + comparator-timed crowbar** | B: voltage-gated permit + eFuse + per-PA QOD switches, no crowbar |
|---|---|---|---|
| R4 50 µs bounded by DS maxima | **No.** Contributors with no max: TPS22810 tOFF, TPS386000 assert delay, LM339B response, LVC below 1.65 V | **Yes for every fault class with VIN ≥ 4.5 V.** Worst case 46.5 µs. PLACEHOLDER terms: crowbar RDS(on) over temperature (0.6 µs effect) and Q_sd/Q_t on-resistance (< 0.1 µs) | **No.** TPS22918 tOFF is typical only. Excluding it, the budget is 38.7 µs |
| R3 BBM from bounded parameters | **No.** Sim shows 1.5–4.0 µs overlap at supervisor delay ≥ 20 µs | **Yes:** falling edge ≥ 1.28 µs and rising edge ≥ 2.71 µs (DERIVED). 0 overlap in 272 SIM-BEHAV runs | No external crowbar. Internal QOD-vs-FET ordering is not specified (≤ 0.18 A) |
| Consequence if BBM is lost anyway | 8–13 A unbounded, TSD auto-restart | Duration bounded (≤ 1.5 µs if SHDN asserted); peak overlap current NOT guaranteed (TPS1663 short-circuit current ≈45 A is typical only; then current limit 2.16 A max and latch [H2-E correction] | n/a |
| Satisfies all of R1–R6 on verified characteristics | No | **No.** Residual items in §7 | No |

**Recommendation (R7):** carry **candidate A** into detailed design. Its evidence is stronger than H2-C's:

- every term of the R4 and R3 chain is a datasheet maximum or minimum over temperature, except the items listed in §7;
- the consequence of a lost BBM is bounded by a guaranteed current limit.

**R10:** no architecture, A included, meets every requirement with verified characteristics today. **PCB layout preparation stays NO-GO.** It can be reconsidered once:

- the missing manufacturer statements in §7.1 are obtained;
- the mandatory bench measurements in `BENCH_PLAN.md` pass;
- the gate-bias conflict (R6, TE2) is resolved separately. Neither alternative changes TE2.

---

## 1. Why the as-built H2-C cannot meet R3/R4/R5 on paper

Taken from AUDIT_FMEA and CHARACTERISTICS. All items are DS or SIM-BEHAV.

1. **Switch-off time.** The TPS22810 tOFF (3.3 µs), tD and the EN deglitch are **25 °C typical only** (SLVSDH0C p7, p15). The QOD is disabled in TSD and below VIN UVLO (p14).
   - The crowbar break-before-make therefore rests on a typical value. In the sim, the BBM margin at the worst corner is 2.5 µs.
2. **Supervisor assert delay.** For the TPS386000 this is "almost immediately", with **no maximum** (SBVS105F p23). Its VOL is specified only at 1 mA.
   - The BAT54C clamps make the supervisor sink 2.4–4.4 mA and park PA_DRAIN_EN at 0.8–0.97 V (B-M5a/b).
   - At an assert delay of 20–100 µs, the sim shows **1.5–4.0 µs of crowbar/switch overlap** and up to 104 µs to discharge the drain.
3. **Logic below its rated supply.** Everything converges on one LVC gate (U705), and the LVC parts are unspecified below 1.65 V.
   - The TPS3430 WDO is **defined HIGH** for 0.8 < VDD < 1.6 V (DU1).
   - The LM339B response time is typical only, and its VIO is specified only for VS ≥ 5 V while the design runs it at 3.3 V.
4. **Crowbar thresholds.** The crowbar timing depends on the VGS(th) of the DMG1012T and CSD16301Q2, both specified at **25 °C only**.
5. **No current limit.** One component fault (F44–F46, F49, F52) makes a permanent shoot-through of about 13 A with TSD auto-restart.
   - F-5V: one open resistor puts 12 V on 16 PAs.

---

## 2. Common building block (used by both A and B): the voltage-gated supervised permit (VGP)

### 2.1 Idea

The PA supply can be enabled only if four things hold:

1. **Gate on the interlock rail's own level.** The interlock rail must be high enough that *every* monitor is inside its specified operating range. This is enforced by the eFuse's own precision UVLO comparator, which gives:
   - a hardware POR with guaranteed thresholds;
   - no dependence on the output state of any monitor below its VDD min.
2. **Wired-AND permit.** Every monitor is an open-drain (or push-pull driving a dedicated NMOS) on one permit node P.
3. **MCU cannot force P high.** The MCU can only *release* its own pull-down, so it can never drive P high.
4. **Default off.** Every eFuse input is pulled to OFF by passive parts. A floating input disables.

### 2.2 Diagram (text)

```
VIN_12V ─ TPS7A25 (5.0 V fixed, ±1 %) ─ +5V_IL ──┬─ Rpu 2.2k ─ P (permit, ≈100 pF)
                                                 │      P is pulled LOW by any of (OD, all on +5V_IL):
                                                 │        TPS3703 windows: +5V_IL, VIN_12V, +5V_PA, +3V3_RF, +3V3_AUX, +1V8_DIG, REF (IL_REF)
                                                 │        TLV3202 gate-lost ×16 → NMOS   |  TLV3202 −5V_BF / −3V3_SW window → NMOS
                                                 │        TLV3202 fast +5V_PA OV (5.30 V vs monitored REF) → NMOS
                                                 │        TPS3430 WDO (VDD = +5V_IL)  |  ARM stage (NMOS on by default; MCU must actively release)
                                                 │        TPS1663 FLT ×4 (R_FLT ≤ 130 Ω)
                                                 ├─ R_g / R_h divider (0.1 %) → UVLO pin of every TPS1663 ("rail guard", k ≈ 0.28)
                                                 └─ 100 Ω ─ VCB (10 µF hold-up) → crowbar-timing domain (A) / CD comparator
P ──(47k)── SHDN_c (47k↓, 1 nF) of each TPS1663 c ;  Q_sd,c (NMOS) pulls SHDN_c low when CD: P < 0.8·VCB
P ──(47k)── MCU readback ;  each TPS1663 PGOOD / IMON / FLT ──(47k)── MCU ;  P → TX_ALLOW (ADAR1000 PA_ON) via divider
REF_EN (P without the gate checks) → TPS22917 ON for IL_REF (gate-divider reference)
```

### 2.3 Parts and the guaranteed parameters used

| Function | Part | Guaranteed parameter used | Source |
|---|---|---|---|
| Interlock rail | TPS7A25 fixed 5.0 V | VIN 2.4–18 V; VOUT ±1 %; line ±0.1 %; load ±0.5 %; TJ −40…125 °C | SBVS372C p1, p6 |
| Rail monitors | TPS3703 (adjustable window) | tPD ≤ **30 µs** (5 % overdrive, measured to VOL); thresholds ±0.7 % (±1 % below 0.8 V); VOL ≤ 0.25 V at 5 mA (VDD 5 V) and 3 mA (VDD 2 V); RESET held low for VPOR (≤ 1 V) < VDD < UVLO; tD 7–13 ms or 140–260 ms; latch mode with CT = GND | SBVS249B p6, p7, p17, p20 |
| Gate, negative-rail and fast-OV comparators | TLV3202 (dual, push-pull) | tPD ≤ **55 ns** (−40…125 °C, 100 mV overdrive, at both VCC 2.7 V and 5 V); VIO ≤ 6 mV (dual) over temperature; VCM (VEE − 0.2)…(VCC + 0.2) V; VOL ≤ 225 mV at 4 mA; supply 2.7–5.5 V; "off" below 2.7 V | SBOS561C p5, p6, p11 |
| Watchdog | TPS3430 on +5V_IL | VDD ≥ 1.6 V; WDO VOL ≤ 0.4 V at 3 mA; WDO is HIGH for VPOR < VDD < 1.6 V (DU1, **made irrelevant by the guard**) | SBVS366A p5, p15 |
| PA switch | **TPS16630** eFuse (one per chain, replaces TPS22810) | SHDN↓ → FET OFF **0.8–1.5 µs**; V(SHUTF) ≥ 0.8 V; V(SHUTR) ≤ 2 V; SHDN source ≤ 10 µA (open circuit 2.48–3.3 V); UVLO 1.176–1.224 V rising / 1.09–1.15 V falling; UVLO_toff 9–16 µs; OVP 1.176–1.224 V and OVP_toff 8.5–14 µs; I(OL) 1.84–2.16 A at 9 kΩ; fast-trip at 2 × I(OL) within 2.2–4.5 µs; RON ≤ 53 mΩ (−40…125 °C); R(FLT) and R(PGOOD) 36–130 Ω; VIN ROC 4.5–60 V; SHDN ROC ≤ 5 V; MODE open = latch | SLVSET9G p7–p10 |

### 2.4 Rail guard (proof of R1, DERIVED)

1. The UVLO pin divider has ratio k = 0.280 ± 0.1 %, fed from +5V_IL (0.1 % resistors).
2. The FET can be ON only if UVLO > V(UVLOF) ≥ 1.09 V, which needs +5V_IL > 1.09/k_max ≈ 3.89 V.
3. Turn-on is guaranteed once +5V_IL ≥ 1.224/k_min = 4.38 V. The +5V_IL minimum is 4.92 V, leaving 0.54 V of margin, so there are no nuisance lock-outs.
4. At +5V_IL ≥ 3.89 V every monitor is inside its specified range:

   | Monitor | VDD min |
   |---|---|
   | TPS3703 | 1.7 V |
   | TLV3202 | 2.7 V |
   | TPS3430 | 1.6 V |
   | SN74LVC1G17 | 1.65 V |

5. So while the FET can be ON, every monitor output is defined, and P is high only if all of them report valid.
6. Below the guard level, **monitor outputs may be anything; the FET is still OFF.** The FET is held off by the UVLO comparator, which runs on the TPS1663's own supply.
7. This holds while VIN is in the 4.5–60 V ROC. Below 4.5 V, see §7.

Further R1 points:

- **Floating inputs disable.**
  - SHDN_c has a 47 kΩ pull-down: the 10 µA × 47 kΩ = 0.47 V that results stays below 0.8 V.
  - UVLO has a resistor to GND and only ±150 nA leakage.
  - The ARM NMOS gate is pulled up, so a dead or reset MCU leaves P low.
  - TPS22917 ON for IL_REF is driven from REF_EN, which has the same guard.
- **The MCU cannot force the permit.**
  - The MCU's only path to P is releasing a pull-down.
  - Every readback (P, FLT, PGOOD, IMON, crowbar gate) goes through 47 kΩ to an MCU input. A GPIO misconfigured as an output can inject ≤ 0.1 mA, against a ≥ 2.7 mA net OD sink.
  - This closes F25–F27.
- **Watchdog.** The TPS3430 VDD is +5V_IL ≥ 3.89 V whenever the FET can be ON, so the DU1 band is unreachable.
  - The TPS3430 "disabled during tRST" window after power-up is covered: the +5V_IL TPS3703 release delay (A variant, CT = 10 kΩ, 140–260 ms) is longer than the TPS3430 tRST max of 230 ms.

### 2.5 VGP design rules that close audit findings

| Audit finding | Rule |
|---|---|
| F-REF | IL_REF gets its own TPS3703 window. If IL_REF is lost, P goes low. |
| F14 / F15 | Monitor dividers are oriented so that an open resistor reads "fault". Where that is impossible, it is listed as a residual (§4.6). |
| F-5V | Four independent layers: <ul><li>TPS3703 window on +5V_PA (OV 5.35 V, ≤ 30 µs);</li><li>TLV3202 fast OV (5.30 V ± 1 % against the monitored REF, 55 ns);</li><li>TPS16630 OVP per chain (≤ 14 µs);</li><li>U651 PGOOD as one more OD on P.</li></ul> |
| U920 abs max | U920 is removed, along with the D960 path that put +5V_PA onto a 7 V-abs-max part. |
| Ua12 | PWR_ENN_NEG gets a 100 kΩ pull-down. ENN IIN ≤ 0.1 µA gives ≤ 10 mV (SLVS493E p5). |
| Ua11 | PWR_EN_3V3 gets a 10 kΩ pull-down. Against PB4's 25–55 kΩ pull-up this gives ≤ 0.51 V, below VENL min 0.95 V (DS12589; SLVSEY5C p6). The alternative is to move it off PB4. |
| Single shared PA_DRAIN_EN | Each chain gets its own SHDN_c network (47 k / 47 k / 1 nF + Q_sd). One SHDN-to-IN short injects ≤ 5 V/47 kΩ ≈ 0.1 mA into P, which cannot defeat the other chains. P itself remains a shared node; see residuals. |

---

## 3. Candidate A: VGP + TPS16630 per chain + comparator-timed crowbar

### 3.1 Per-chain diagram (text)

```
+5V_PA ─10 mΩ─ IN ┌──────────┐ OUT ─────────────── +5V_PA_Cc (4×ADTR1107 VDD_PA, ≤ 23.8 µF)
                  │ TPS16630 │ ILIM 9.09k (1.84–2.16 A), MODE open (latch), OVP divider (5.35 V), dVdT
   UVLO ← guard   │          │ FLT → P ; PGOOD/IMON → MCU                          │
   SHDN_c ←───────┤          │                                                     ├─ 6 × 1 Ω RCS1206 ─ D
                  └──────────┘                                                     │        Q_CB CSD16301Q2
SHDN_c ──► CA (TLV3202a): SHDN_c > 0.1·VCB → Q_t ON (resets C_t)                   │        G ◄─ LVC1G17 (VCC = VCB) ◄─ CB
VCB ─ R_t 4.32k ─ C_t 1 nF C0G ─► CB (TLV3202b): V(C_t) > 0.5·VCB ──────────────────┘        S ─ GND
```

### 3.2 Crowbar timing parts (beyond §2.3)

| Item | Value | Guaranteed parameter used | Source |
|---|---|---|---|
| CA / CB | TLV3202 | tPD 0…55 ns; VIO ≤ 6 mV | SBOS561C p5–p6 |
| Thresholds | ratiometric to VCB: 0.1·VCB (CA) and 0.5·VCB (CB) | 0.1 % resistors, so no reference is needed and VCB variation cancels | DERIVED |
| R_t, C_t | 4.32 kΩ 1 % (≤ 100 ppm/K); 1 nF C0G 5 % (±30 ppm/K) | τ = 4.028…4.620 µs over −40…85 °C | DERIVED |
| Crowbar driver | SN74LVC1G17 on VCB (4.77–5.08 V) | tpd ≤ 6.5 ns; VOL ≤ 0.55 V at 32 mA; IOH 32 mA | SCES351Y p6, p7 |
| Crowbar FET | CSD16301Q2 | Qg ≤ 2.8 nC; RDS(on) ≤ 29 mΩ at VGS 4.5 V, **25 °C only**; IDM 85 A | SLPS235E p1, p3 |
| R_CB | 6 × Vishay RCS1206 1 Ω 1 % (0.168 Ω) | ≈ 10 V single pulse at 10 µs / 700 µs; **1-min pulse interval** | Vishay 20065 p4 (via REC_PARTS) |
| Hold-up | VCB = +5V_IL via 100 Ω, 10 µF | ≥ 4.77 V at a 1.5 mA domain load | DERIVED |

### 3.3 Worst-case R4 timing budget

DERIVED in `sim/budget.txt`. Every term is a maximum.

Common terms used in the per-fault rows:

| Term | Value | Basis |
|---|---|---|
| P fall | ≤ 0.1 µs | 100 pF; ≥ 2.7 mA net sink |
| CD + Q_sd | ≤ 0.075 µs | 55 ns + 10 Ω·1 nF (PLACEHOLDER R) |
| Crowbar delay | ≤ 3.218 µs | DERIVED |
| CA + CB + LVC | ≤ 0.117 µs | DS |
| Crowbar gate charge | ≤ 0.088 µs | 2.8 nC / 32 mA |
| Discharge 5.5 V → 0.5 V | ≤ **12.90 µs** | τ = (0.168 + 0.058 PLACEHOLDER) Ω × 23.8 µF = 5.38 µs; 24 A peak; 360 µJ per chain |
| eFuse FET off | ≤ 1.5 µs | **Runs in parallel with the crowbar delay**, so it does not add |

| Fault (R4 list) | Detection max | Rest of chain | **Total, worst case** | Margin to 50 µs |
|---|---|---|---|---|
| Supply UV/OV on +5V_PA, +3V3_RF, +3V3_AUX, +1V8_DIG, VIN_12V (VIN0), +5V_IL slow, IL_REF | TPS3703 30 µs | 16.5 µs | **46.5 µs** | 3.5 µs |
| Gate lost (> −0.15 V) | TLV3202 0.055 + NMOS 0.05 µs | 16.5 µs | **16.6 µs** | 33.4 µs |
| +5V_PA OV (F-5V) | TLV3202 fast OV 0.055 µs, or TPS16630 OVP 14 µs | 16.5 µs + discharge from 6.3 V (13.7 µs) | ≤ **31.2 µs** | 18.8 µs |
| Watchdog fault (from WDO↓) | WDO↓ to P ≈ 0.2 µs | 16.5 µs | **16.7 µs**, plus WDI→WDO delay (**DS-TYP 50 ns**) | 33.3 µs |
| TPS16630 TSD / overcurrent latch (from FLT↓) | FLT to P ≤ 0.1 µs | 16.5 µs | **16.7 µs**; FLT assertion vs the event is not specified | 33.3 µs |
| +5V_IL abrupt loss / short | P → dead rail (τ 0.22 µs) → CD | 16.5 µs | **16.9 µs** (SIM ≤ 16.7) | 33.1 µs |
| Arbitrary rail ordering | Guard holds the FET off until every monitor is valid. Outside that, the rows above apply | — | — | — |
| TPS22810-type "QOD lost in TSD / below UVLO" | Not applicable. The crowbar is independent of the eFuse and is powered by VCB, not by the PA rail | — | — | — |

*Fault onset* for TPS3703 channels is the instant the rail is 5 % beyond its threshold (the tPD condition). Slower overdrives are not specified (see §7.1).

### 3.4 Proof sketch of R3 (break-before-make from bounded parameters)

**Falling edge (fault → crowbar).**

1. Let t₀ be the instant SHDN_c falls below 0.1·VCB + VIO (≤ 0.515 V).
2. Because SHDN_c is falling, it crossed 0.8 V, and therefore the device's actual V(SHUTF) ≥ 0.8 V, no later than t₀.
3. So the FET is OFF by t₀ + 1.5 µs (tSD max).
4. Q_t holds C_t at about 0 V while SHDN_c > threshold, so every timing cycle starts from 0 regardless of history. That covers glitches.
5. The crowbar gate cannot start rising before t₀ + d_min, where d_min = τ_min · ln(1/(1 − k_max)) = 2.778 µs and comparator tPD min is taken as 0.
6. **Margin ≥ 1.278 µs.**
7. SIM-BEHAV: the minimum over 16 corners × 15 scenarios is 1.28 µs, with **0 overlap**.

**Rising edge (re-arm).**

1. The crowbar is commanded off as soon as SHDN_c > 0.515 V: CA → Q_t → CB → LVC → gate below threshold in ≤ 0.234 µs.
2. The FET cannot conduct before SHDN_c > 0.8 V. This assumes V(SHUTR) ≥ V(SHUTF); hysteresis ≥ 0 is not stated in the datasheet.
3. SHDN_c rises through R_s∥R_sd (23.25 kΩ min) × C_s (0.95 nF min) toward ≤ 2.79 V. The 0.515 → 0.8 V interval therefore takes ≥ 2.95 µs.
4. **Margin ≥ 2.71 µs.** SIM-BEHAV minimum: 3.21 µs over 32 runs (`rise_check.txt`).

**The proof requires VIN ≥ 4.5 V**, because the TPS16630 is characterised only inside its ROC.

**If BBM is lost anyway** (e.g. C_t open or R_t short, both single faults):

- the overlap lasts ≤ 1.5 µs (tSD max) once SHDN is asserted. **[H2-E correction]** Its peak current is NOT guaranteed: 5.5 V/(0.168 + 0.053) Ω ≈ 25 A is an estimate using maximum resistances, but lower resistance gives higher current and the crowbar-FET / eFuse RDS(on) minima are not specified; the TPS1663 short-circuit current (≈45 A) is a typical value, not a guaranteed maximum. The energy (≈0.2 mJ) is likewise an estimate;
- after that, the eFuse fast-trip (≤ 4.5 µs at > 2·I(OL)) and the 2.16 A current limit with latch bound any continued conduction.
- Compare H2-C, where TPS22810 has no current limit and auto-restarts.

### 3.5 Proof sketch of R1 and R4 for A

- **R1:** see §2.4. The crowbar is the only element that turns *on* by default, and it is on only when SHDN_c is low and the timer has elapsed.
- **R4:** every fault class in §3.3 is detected by a part with a guaranteed maximum delay.
  - The switch-off path (SHDN, 1.5 µs) and the crowbar path (≤ 3.42 µs to fully on) do not depend on the PA rail for their supply. VCB is +5V_IL plus hold-up.
  - The discharge is bounded by R_CB, C_max and V0.
  - TSD and UVLO of the eFuse do not disable the discharge (the TPS22810 problem, D1/D2).
  - The **+5V_PA collapse (5P0)** case is covered only while VIN ≥ 4.5 V (§7). Below that, VOUT ≤ VIN + body-diode drop (physics), and the crowbar stays on from VCB.

### 3.6 SIM-BEHAV results (A)

Source: `sim/arch_a_results.md`. **BEHAVIOURAL / PRELIMINARY.**

- **Corners** (16): timer τ min/max; SHDN RC fast/slow; comparator tPD 0 / 55 ns; VIO 0 / 6 mV in the unsafe direction.
- **Conservative FET model:** the eFuse FET turns on instantly at SHDN > 0.8 V and turns off 1.5 µs after SHDN < 0.8 V.
- **Pessimistic S3:** in the +5V_IL collapse runs, monitor outputs are treated as *released*.

| Scenario | Max overlap | Worst drain < 0.5 V (after OD assertion) | Min BBM margin |
|---|---|---|---|
| S1 OD fault (any monitor, FLT, WDO) | **0** | 16.3 µs (add the detection delay) | 1.29 µs |
| S2 re-arm, then fault | **0** | 13.1 µs | 1.29 µs fall / 3.21 µs rise |
| S3 +5V_IL collapse at 50 V/µs … 0.3 V/µs | **0** | 16.4 … 20.1 µs from ramp start | 1.28 µs |
| S3 +5V_IL collapse at 0.1 / 0.05 / 0.01 V/µs, monitors silent | **0** | 27 / 38 / 129 µs from ramp start | 1.29 µs |
| S4 permit glitches, 0.2–20 µs | **0** | ≤ 8.1 µs | 1.29 µs |

Notes on the table:

- **Slow S3 ramps.** Here the CD comparator (20 % droop) is the only active detector because the monitors are modelled as silent, which is beyond the guard's assumption. In the real circuit, the +5V_IL TPS3703 is powered and in its ROC at that point, so the 46.5 µs budget from the 5 % overdrive point applies.
- **What this sim does not show.** It does not model:
  - TPS16630 behaviour below 4.5 V;
  - parasitic inductance;
  - comparator behaviour outside 2.7–5.5 V.

### 3.7 Residual cut sets (A)

Order 1 unless stated.

| Top event | Cut set | Bounded? | Mitigation / detection |
|---|---|---|---|
| TE1 / TE4: drain energised or not discharged | P bridged to +5V_IL (PCB short) | No | Layout keep-out. P readback plus a power-up proof test (MCU disarm → P must read low) |
| | TPS16630 pass-FET short | Drain stays at +5V_PA; the crowbar then fires into U651 (OCL 8–12 A, about 29 W in R_CB) until U651 UVP (60 %, 256 µs **DS-TYP**) | Gate PWR_EN_5VPA with P in hardware (second, diverse disconnect); IMON/PGOOD readback; bench pulse test of R_CB |
| | All four comparator/NMOS gate-lost channels of one package dead *and* a gate lost (order 2) | | Power-up proof test: write one gate to 0 V with the drain disarmed and check that P stays low |
| TE3: crowbar vs enabled supply | C_t open, R_t short, Q_t open, CA/CB stuck, LVC stuck high, crowbar FET D–S or G–D short | **Yes.** ≤ 1.5 µs per event (peak current not guaranteed — see §3.4 correction); a permanent short is caught by fast-trip + latch at arm | Crowbar-gate readback while armed (must be low); proof test at power-up |
| | TPS16630 at VIN < 4.5 V (5P0 / brown-out) | **Not specified** | Bench item T1b |
| TE4 (late) | R_CB fully open, crowbar FET open, VCB hold-up open | No | Latent. Power-up crowbar self-test (arm into dummy-free chain, then disarm and time VOUT via MCU ADC) |
| TE2 (gate bias) | Unchanged from H2-C: F63, F64, F58, F66, Ua13 | No | R6, handled separately. A's IL_REF monitor removes the F-REF path |

### 3.8 What A still depends on that no datasheet bounds (must be measured or confirmed)

1. **TPS16630 below its ROC.** FET state and SHDN behaviour for VIN 0–4.5 V. The internal POR is 4.2/4.3 V **typ** (block diagram, p16).
   - A TPS3703 UV at 4.6 V on +5V_PA is guaranteed to assert only at a 5 % overdrive (≈ 4.37 V), which is below 4.5 V.
2. **TPS16630 "FET OFF".** The definition of FET OFF in tSD(dly) is not given (gate level? load current?).
   - Its dependence on load current (1–2 A) is not stated. Test conditions: C(OUT) = 1 µF.
3. **TPS16630 SHDN.** Rising threshold ≥ falling threshold (non-negative hysteresis) is not stated. The SHDN pin capacitance is not stated.
4. **TPS16630 FLT timing.** FLT assertion timing relative to TSD/overcurrent is not stated, and neither is whether UVLO_toff (defined to FLT↓) implies FET off by then. Neither is on the main path.
5. **Crowbar FET over temperature.** CSD16301Q2 RDS(on) and VGS(th) are 25 °C only (PLACEHOLDER × 2).
   - An off-state with VGS ≤ 0.1 V is bounded only by IDSS at VGS = 0 (physics bound (b)).
   - Automotive parts that specify VGS(th)/RDS(on) at −55/+175 °C (Nexperia) could not be retrieved, because the site blocked access.
6. **Q_sd and Q_t.** On-resistance over temperature is a PLACEHOLDER (10 Ω). Their gates are driven rail-to-rail (≥ 4.4 V / ≤ 0.23 V), so only RDS(on) at 4.5 V and VGS(th) min at hot matter.
7. **TPS3703 tPD for overdrive < 5 % and slow ramps** is not specified.
8. **TPS3430 WDI→WDO delay** is typical only (50 ns).
9. **RCS1206 repetitive pulses.** Behaviour at 5.5 A peak with τ = 5.4 µs at rates above 1 per minute is not covered.
10. **TPS3703 latch mode (§9.1.3)** for the re-arm-only-when-pinched fault latch. MR-initiated latching is not described.
    - Without a latch, the permit re-asserts after tD (7–13 ms) without a pinch check; this is a firmware dependency. It is not on the R4 path.
11. **+5V_PA OV slew.** The ≤ 5.46 V bound at the PA assumes a +5V_PA slew ≤ 64 mV/µs: U651 OCL 12 A into 188 µF.
    - The effective bulk C under DC bias is not specified. At 100 µF effective the PA sees ≈ 5.56 V for ≤ 1.7 µs.

### 3.9 Complexity (A vs H2-C)

| Change | Parts |
|---|---|
| Removed | U705, U909, U911, U912, U915 (LVC chain); U920 TPS386000; D960 and D961 BAT54C; Q965, Q966, Q971–Q974; 4× TPS22810 |
| Added, shared | <ul><li>TPS7A25</li><li>7× TPS3703</li><li>8× TLV3202 for gate-lost (16 ch), plus 1 for the negative rails and 1 for fast OV</li><li>1× TLV3201 (CD)</li><li>≈ 20 small NMOS</li><li>guard divider</li></ul> |
| Added, per chain | TPS16630 (VQFN-24) with ILIM/OVP/dVdT parts; TLV3202; R_t/C_t; LVC1G17; Q_t; Q_sd; 6× RCS1206 (was 3) |
| Total | **≈ +45 ICs/FETs and ≈ +80 passives net.** Pinch comparators (LM339B, not on the R4 path) can stay |
| Board cost | The TPS16630 is 4 × 4 mm. It takes more area than the TPS22810 and dissipates ≤ (2 A)² × 53 mΩ = 0.21 W per chain |

---

## 4. Candidate B: VGP + TPS16630 per chain + per-PA TPS22918 with guaranteed QOD (no crowbar)

### 4.1 Idea

Keep the PA bulk decoupling (4 × 4.7 µF) **upstream** of a per-PA load switch placed at the VDD_PA pin. Only a small local capacitance (0.1 µF + 10 nF + 100 pF) is left on the drain. That small capacitance is discharged by the switch's guaranteed QOD resistance.

The TPS22918 has **no thermal shutdown**, so its QOD cannot be lost to TSD. After the permit drops, its VIN (the chain bus) stays near 5 V, because the bus has no load and the TPS16630 is off. RPD is therefore in its specified 5 V condition.

```
+5V_PA ─ TPS16630 (ILIM/OVP/latch, SHDN = P) ─ chain bus (4×4.7 µF + 1 µF) ─┬─ TPS22918 ─ VDD_PA1 (0.1 µF+10 nF+100 pF)
                                                                           ├─ TPS22918 ─ VDD_PA2 …   (ON = P via 10k/100k)
```

### 4.2 Parts and guaranteed parameters

| Part | Guaranteed | Not guaranteed |
|---|---|---|
| TPS22918 (SLVSD76C) | RPD ≤ 30 Ω at VIN 5 V, ≤ 35 Ω at 3.3 V, ≤ 60 Ω at 1.8 V (−40…105 °C, p5); VIH 1 V / VIL 0.5 V (p4); no TSD | **tOFF typ only** (2–3 µs, p6); RPD "reduced past a certain VIN" (p14); internal ordering of QOD vs FET-off |
| TPS16630, TPS3703, TLV3202 | as §2.3 | as §3.8, items 1–4 |

### 4.3 R4 budget (B)

DERIVED. The QOD time is 30 Ω × 0.121 µF × ln(11) = **8.64 µs**.

| Fault | Total |
|---|---|
| Rail UV/OV | 30 + 0.1 + **tOFF(TPS22918, no max)** + 8.64 = **38.74 µs + tOFF** |
| Gate lost | 0.1 + **tOFF** + 8.64 = **8.84 µs + tOFF** |

At the *typical* tOFF (3 µs) the rail case is 41.7 µs. **R4 cannot be claimed under R5**, because one series term has no maximum.

### 4.4 R3 and R1 (B)

- **R3:** there is no external discharge device, so the external crowbar cut sets (F44–F52) disappear. The QOD sits inside the switch; whether it is enabled only after the FET is fully off is not stated.
  - The worst case of an internal overlap is 5.5 V/30 Ω = 0.18 A for ≤ tOFF. Formally this is still an unverified ordering.
- **R1:** same as A (VGP). Each TPS22918 ON pin also needs a pull-down. The ON-pin internal pull-down is not specified.

### 4.5 Residuals and dependencies (B)

- **ADI decoupling deviation.** VDD_PA decoupling would differ from ADI's Stingray reference (4.7 µF directly at VDD_PA). Unknowns:
  - PA stability and TDD transients through switch RON plus trace;
  - ADTR1107 performance.

  This needs RF validation and an ADI statement.
- **Part count and readback.** 16 extra switches and 16 more enable nets. The per-PA drain is not read back unless 16 ADC channels are added.
- **Low VIN.** QOD at VIN < 1.8 V is not specified. This matters in a +5V_PA collapse.
- **Pass-short cut set.** TPS22918 pass short is an order-1 cut set for that PA's drain. The TPS16630 upstream still disconnects, but the 18.8 µF chain bus then discharges into the PA.

### 4.6 Complexity (B)

The permit is the same as A. Per chain, B adds a TPS16630 and 4 TPS22918 (SOT-23-6) instead of a crowbar. There are no high-current pulses. The total is ≈ +55 ICs.

---

## 5. Decision table

| Criterion | H2-C as built | A | B |
|---|---|---|---|
| R1: default TX inhibit; undefined outputs never enable | Partly. DU1, Ua5/Ua8/Ua9 (LVC < 1.65 V), Ua12 (ENN float), Ua11 (PB4) | **Yes.** UVLO rail guard (DS thresholds) and passive defaults | Yes (same VGP) |
| R2: no diode-clamped logic nodes with uncertain sink | No (BAT54C clamps, B-M5a/b) | **Yes.** No diode clamps; OD sink currents within specified VOL points | Yes |
| R3: BBM from bounded parameters | No (typical tOFF, unspecified delay; overlap seen in sim) | **Yes** inside VIN 4.5–60 V: ≥ 1.28 µs fall / ≥ 2.71 µs rise | No crowbar; internal QOD ordering unspecified (low energy) |
| R4: < 0.5 V within 50 µs, worst case | Not provable (sim 34 / 50.3 / 104 µs) | **≤ 46.5 µs** (1 PLACEHOLDER term: RDS(on) temperature) | Not provable (tOFF typical only); 38.7 µs + tOFF |
| R4 in TSD / UVLO of the switch | QOD lost (D1/D2) | Crowbar independent of the eFuse | QOD independent of TSD (none in TPS22918) |
| R5: maxima and temperature | No | Yes, except §3.8 items | No (tOFF) |
| Current limit | None | 1.84–2.16 A per chain, fast-trip, latch | Same (TPS16630) |
| F-5V (12 V on drains) | S5 single point | Four layers; transient ≤ 5.46 V if slew ≤ 64 mV/µs | Same as A |
| IL_REF unmonitored (F-REF) | Yes | TPS3703 window on REF | Same |
| Shared PA_DRAIN_EN, no readback | Yes | Per-chain SHDN networks; P, FLT, PGOOD, IMON and crowbar-gate readback (P is still one shared node) | Per-PA ON nets; same readback |
| MCU GPIOs on safety nets | PA0, PA1, PA3 direct | 47 kΩ readback only; ARM can only release | Same |
| TPS3430 high in brown-out (DU1) | Unsafe | Unreachable (guard ≥ 3.89 V) | Same |
| ENN floating / PB4 pull-up | Open | 100 kΩ / 10 kΩ pull-downs (also applicable to H2-C) | Same |
| Shoot-through single-component cut sets | F44–F46, F49, F52: about 13 A, unbounded, TSD cycling | Still order 1, but **duration-bounded** (≤ 1.5 µs, then latch; peak current not guaranteed) and **detectable** (gate readback) | Eliminated (no crowbar) |
| Peak discharge current / energy per chain | 8.5–10.6 A / ≤ 0.25 mJ | 24 A / 0.36 mJ (R_CB 0.168 Ω) | 0.18 A per PA / ≈ 1.8 µJ |
| ADI reference compliance on VDD_PA | Yes | Yes | **No** (decoupling moved) |
| Parts added | — | ≈ +45 ICs/FETs | ≈ +55 ICs |
| Gate-bias TE2 (R6) | Firmware only | Unchanged (firmware only) | Unchanged |

---

## 6. Recommendation

**Adopt A as the H2-D architecture for detailed design.** It is the only option whose R3 and R4 arguments close on datasheet maxima and minima over temperature.

The remaining gaps are few, explicit and bench-measurable. They sit at the edges, not in the core chain:

- the eFuse below 4.5 V;
- crowbar FET temperature;
- the eFuse "FET OFF" definition.

A also turns the as-built unbounded shoot-through cut sets into bounded, detectable ones.

B is attractive for removing high-current pulses, but its R4 claim rests on a typical-only tOFF and it departs from ADI's decoupling. Do not choose B unless:

- TI provides a TPS22918 tOFF maximum, **and**
- ADI confirms that ≤ 0.1 µF at VDD_PA with upstream bulk is acceptable.

**Not a GO for layout.** R10 applies; see §7.

---

## 7. R10: missing evidence (no architecture is fully verified today)

### 7.1 Manufacturer statements required

| # | Part / maker | Question |
|---|---|---|
| M1 | TPS1663 (TI) | Definition of "FET OFF" in tSD(dly) (p10) and its validity at 1–2.2 A load. Behaviour of SHDN and of the FET for VIN between 0 and 4.5 V, plus the internal POR thresholds (min/max). Is V(SHUTR) ≥ V(SHUTF) guaranteed? Is the FET off by the time UVLO_toff FLT↓ asserts? What is the FLT assertion timing in TSD/OC? |
| M2 | TPS3703 (TI) | tPD bound for overdrive < 5 % and for slow ramps. Whether an MR-initiated reset latches in CT = GND latch mode. |
| M3 | TPS22918 (TI), only if B is pursued | tOFF maximum over −40…85 °C. QOD-vs-FET ordering. RPD at VIN < 1.8 V. |
| M4 | MOSFET vendor | A crowbar/Q_sd/Q_t part with VGS(th) and RDS(on) **min/max over −40…+125 °C**. Nexperia automotive datasheets normally state these; nexperia.com was blocked here. |
| M5 | Vishay RCS1206 | Repetitive pulse rating at 5.5 V / τ 5.4 µs, more often than 1 per minute. |
| M6 | ADI | PA_BIAS output with AVDD3 absent and AVDD1 present (B-ADAR/Ua13). VGG_PA abs max with VDD_PA = 0 (S1). ADTR1107 VDD_PA transient rating (for the ≤ 5.46 V OV bound). For B only: the decoupling deviation. |
| M7 | TI TPS568230 (U651) | OCL range and peak inductor current under FB-open, for the OV slew bound. |

### 7.2 Mandatory bench evidence

See `BENCH_PLAN.md` T1–T12. Each bench result is used as characterisation with a ≥ 2× guardband, not as a guarantee. The R3/R4 chain additionally requires:

- T1a/T1b: TPS16630 SHDN→off and low VIN;
- T5: MOSFETs at −40/+85 °C;
- T6: crowbar pulse and measured overlap;
- T7: timer at temperature;
- T8: rail-collapse matrix.

---

## 8. Audit top findings vs A

| # | Finding | A |
|---|---|---|
| 1 | F-5V | Closed by four layers, subject to residual M7/M6 |
| 2 | F-REF / F14 / F15 | REF monitored; divider orientation rule; residual for one-sided dividers |
| 3 | No current limit, shoot-through single points | Current limit + latch; shoot-through bounded and readable |
| 4 | DU1 | Unreachable through the guard |
| 5 | U705 convergence, no readback | U705 removed. P is still shared (readback + proof test) |
| 6 | MCU pins on safety nets | 47 kΩ readback; release-only ARM |
| 7 | B-TD / M5 | U920 and BAT54C removed; TPS3703 tPD ≤ 30 µs |
| 8 | Temperature of thresholds | Thresholds are comparators/supervisors with temperature-specified limits. The FETs are switched rail-to-rail; remaining FET items are M4 and T5 |
| 9 | ENN, ordering | 100 kΩ pull-down. Ordering is enforced by the VGP; −5V_BF/−3V3_SW windows are two-sided |
| 10 | TE2 / QOD loss | QOD loss is irrelevant (crowbar). TE2 is unchanged (R6) |
