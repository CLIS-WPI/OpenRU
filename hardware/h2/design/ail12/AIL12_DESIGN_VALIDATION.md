# A-IL12 design-validation study: decision report

- **Date:** 2026-11-13. **Branch:** `hardware/ail12-design-validation`, from H2-E.1 `3062b65`.
- **Evidence class:** analysis plus **BEHAVIOURAL / PRELIMINARY simulation. Nothing is hardware-validated.**
- **Unchanged:**
  - the tile and fixture KiCad schematics;
  - the PCB layouts;
  - the existing safety requirements and BOMs.
- **Nothing was purchased, fabricated, energised or sent to a vendor.**
- **Fault studied:** the TPS7A2550 (U1) pass element shorts, which connects +5V_IL (every permit-logic VDD; TPS3703 abs max 6.0 V, ROC 5.5 V) to VIN_12V (12 V nominal, 13.2 V assumed maximum).
- **Reproduce:** `bash hardware/h2/design/ail12/run_all.sh` from the repository root (pinned image `openru-x6-sim:0.1.0`; about 4 min on 16 cores). Inputs are in `params.py`. Outputs are in `out/`. Sources and tool versions are in `SOURCES.md`.

## 0. Decision

1. **The proposal as received is not acceptable.**
   - The BSS84 interface cannot pull P to ≤ 0.8 V.
   - "BZX84C1V5" is not a real BZX84 part.
   - The eFuse input slew rate exceeds its abs max for hard shorts.
   - C2 (10 V) is over-stressed.
   - EN connection and RILM needed correction.
2. **A corrected candidate** (`CANDIDATE_CIRCUIT.md`) removes all of these problems by derivation. In behavioural simulation with **datasheet-typical** eFuse delays, it holds +5V_IL ≤ 5.05 V for every short with an edge of ≤ 100 µs, across all source impedances, current-limited sources and capacitance corners run. A 10 ms creep reaches ≤ 5.20 V, because +5V_IL follows U1 OUT up to the OVLO trip (≤ 5.41 V). P reaches ≤ 0.8 V within 1.7–2.3 µs of a hard short, and the TPS16630 FET is off by 3.2–3.8 µs.
3. **A-IL12 is NOT closed.** Its protection depends on eFuse response times that have **no guaranteed maximum**:
   - tOVLO (1.2 µs typ);
   - fast-trip tSC/tFT (0.5 µs typ);
   - the AUXOFF de-assertion delay (no figure at all).

   The study derives the largest delay that would still be acceptable. Those values are requirements to put to TI or to measure on the bench (§4, gates G-T1…G-T5). They are not guarantees.
4. **No schematic change is recommended yet.** The candidate is preliminary until the gates in §6 are answered.

## 1. Corrections to the proposal

Details and evidence are in `CANDIDATE_CIRCUIT.md` §1 and `out/calc.txt`.

| # | Proposal | Correction |
|---|---|---|
| C1 | AUXOFF → BSS84 (source P, drain GND) | Two-stage 2N7002 inverter, driving P directly (Q22) and U3 MR (Q21) |
| C2 | "BZX84C1V5" OVLO clamp | Removed. No clamp; the OVLO pin stays below its 6.5 V abs max |
| C3 | eFuse IN on U1 OUT | R80 2.2 Ω + C40 1 µF added, to keep the IN slew-rate abs max |
| C4 | C2 4.7 µF 10 V | 25 V part, kept on U1 OUT |
| C5 | RILM 6.65 kΩ (ROC edge) | 6.49 kΩ 0.1 % |
| C6 | EN not specified | 100 k / 37.4 k UVLO divider from U1 OUT |
| C7 | 2.2 nF dVdt, unrated | 50 V C0G |
| C8 | 47 µF added | Kept as 16 V X5R 1210. +5V_IL C_eff 19.4 / 33.4 / 62.2 µF, using ASSUMED DC-bias derating |

## 2. Datasheet-guaranteed findings (DS)

| Finding | Source |
|---|---|
| TPS259470x OVLO thresholds: rising 1.183–1.223 V, falling 1.076–1.116 V over −40…125 °C | SLVSFC9C 6.5 |
| **OVLO is not latched**, in either the L or the A variant. The output restarts when OVLO < VOV(F), and the restart bypasses dVdt (current-limited). "L" latches only on over-temperature and ILM faults | SLVSFC9C 7.3.3, Table 7-2/7-3 |
| AUXOFF goes low on OVLO, UV/UVP and inrush. It stays high on overcurrent, short-circuit, reverse current and OT. **FLT stays high on OVLO**, so FLT cannot signal this fault | Tables 7-3, 7-4 |
| **No maximum** exists for tOVLO, tSC/tFT, tSWOV or tRCB, nor for the AUXOFF delay or AUXOFF VOL while powered. ISC gain and IFT are typical only | 6.5, 6.6 |
| Abs max: IN 28 V; IN slew 100 V/µs rising, 10 V/µs falling; EN, OVLO, AUXOFF, FLT 6.5 V. ROC: EN ≤ 5 V, OVLO 0.5–1.5 V, AUXOFF ≤ 5 V, RILM 549–6650 Ω, dVdt capacitor rated ≥ VIN + 5 V | 6.1, 6.3 |
| The forward off-state leakage (VIN > VOUT, OVLO) is **not specified**. The 443 µA maximum applies to VOUT > VIN | 6.5 |
| TPS3703: VDD/MR abs max 6 V; VMR_L ≤ 0.3 V; RMR 100 k **typ only**; tPD(MR) 500 ns **typ only**; tD 140–260 ms; VOL ≤ 0.25 V at 5 mA | SBVS249B |
| BSS84LT1G \|VGS(th)\| 0.9–2.0 V at 25 °C (no hot limit). 2N7002LT1G VGS(th) 1.0–2.5 V; rDS(on) ≤ 7.5 Ω (25 °C) / 13.5 Ω (125 °C) at VGS 5 V | onsemi |
| The BZX84 series starts at 2V4 (Diodes DS18001, onsemi). 2V4 leakage IR is ≤ 50 µA at 1 V | — |
| TPS7A25 COUT 1–100 µF, assuming 50 % derating | SBVS372C |

## 3. Derived calculations (DERIVED; `calc.py` → `out/calc.txt`)

| Quantity | Result |
|---|---|
| OVLO trip, 10.0 k / 2.94 k 0.1 % with TCR | Rising 5.179–5.412 V, falling 4.710–4.939 V. Margin to U1 OUT max (5.08 V): 99 mV |
| OVLO pin at 13.2 V | 3.02 V. **Above the 1.5 V ROC**, below the 6.5 V abs max. The ROC is kept only up to 6.57 V on U1 OUT |
| OVLO recovery | **Not determined.** U1 OUT in regulation (4.92–5.08 V) overlaps the falling trip (4.71–4.94 V). At most corners the eFuse stays off after the short clears (the hysteresis acts as a de-facto latch until VIN is cycled). At the corner VOV(F) max + k min + U1 OUT 4.92 V it restarts by itself |
| BSS84 proposal | P ≥ \|VGS(th)\| ≥ 0.9 V **by construction**. Level-1 estimates: 1.28–2.56 V. **P ≤ 0.8 V is impossible at 25 °C** |
| eFuse IN slew with R80/C40 | ≤ 14.1 V/µs rising and ≤ 8.6 V/µs falling, for **any** R_short. The proposal violates 100 V/µs for R_short < 57 mΩ |
| EN at 13.2 V | 3.61 V. UVLO on at 4.32–4.52 V, off at 3.93–4.12 V |
| ILIM with 6.49 k | 0.514 A typ. 0.437–0.591 A is scaled from the 6.65 k test row, not guaranteed |
| U1 total COUT, nominal | 68 µF ≤ 100 µF. C2 stays local |
| H2-D budget re-run with VCB_MIN 4.736 V (R80 + Ron drop) | Unchanged at 3 decimals: crowbar 2.778–3.218 µs, BBM 1.278 µs, worst R4 row 46.50 µs |
| U3-UV fallback if AUXOFF never acts | +5V_IL must decay to 4.37 V. That takes ≤ 11.5 ms (C ≤ 73 µF, load ≥ 4.5 mA ASSUMED); the sim gives 8.4–9.3 ms |
| Analytic maximum turn-off delay (fast-trip ignored, C_out min, U1 OUT stepped to its peak) | 2.3 µs (5.5 V) / 5.3 µs (6.0 V) at 13.2 V. 1.4 / 3.2 µs at the 18.2 V ringing peak. A conservative bound; the sim values in §4.4 lie above it, as expected |

## 4. Simulated behaviour (BEHAVIOURAL, `run_sim.py` → `out/`)

### Assumptions and limits

- Datasheet-typical eFuse delays: tOVLO = AUXOFF delay = 1.2 µs, tSC = 0.5 µs, de-glitch 30 µs, tSWOV 90 µs.
- TPS3703 tPD 30 µs (max) is applied at 5 % overdrive. tD uses its 140 ms minimum, the earliest re-enable.
- U10 off is SHDN_c < 0.8 V plus tSD 1.5 µs (max).
- Drain < 0.5 V is reported as **t_sink + 16.5 µs**, the H2-D bound. The crowbar was not re-simulated.
- Bench source: 13.2 V, 470 µF output capacitor, 20 mΩ / 0.5 µH cable, unless stated.
- The model is not a vendor model (§5). Times run from the onset of the short.

### 4.1 Normal operation

| Case | Result |
|---|---|
| Start-up 0 → 12 V in 1 ms (`TR_N1`) | +5V_IL 4.98 V. P held low; U10 enabled at **146.4 ms** (U3 tD). AUXOFF pin ≤ 4.53 V. No ROC violation |
| Shutdown 12 → 0 V (`TR_N2`) | U1 OUT decays slowly (the LDO cannot sink). U3 UV pulls P low at 6.37 ms after the ramp starts; U10 off 1.5 µs later. Reverse blocking keeps +5V_IL off U1 OUT |
| Brown-out to 3 V for 19 ms (`TR_N3`) | P low at 3.76 ms (U3 UV). Re-enable 160.8 ms, i.e. tD after VIN returns. Brown-out to 5.4 V (`N4`): no trip. 13.2 V high line (`N5`): no trip |

### 4.2 Regulator short, corrected candidate

- **Fault grid (`G2`):** 16 cases, R_short 10 mΩ–10 Ω × edge 10 ns–10 ms.
- **Current-limited sources (`G3`):** 12 cases, 0.1/0.5/2 A × CC loop 0/100 µs × 10/470 µF.
- **Corners (`G4`):** capacitance min/max, thresholds min/max, hot 2N7002, minimum load.

| Metric (all runs above) | Range | Limit |
|---|---|---|
| Peak +5V_IL, fast edges (≤ 100 µs) | 4.99–5.05 V | 5.5 ROC / 6.0 abs |
| Peak +5V_IL, 10 ms creep | 5.11–5.20 V. It follows U1 OUT up to the OVLO trip (≤ 5.41 V) | 5.5 / 6.0 |
| Peak U1 OUT / eFuse IN | 19.2 / 18.5 V (0.5 µH ringing); 13.3 / 13.2 V without L | C2 25 V; IN ROC 23 V |
| eFuse IN slew | ≤ 9.8 V/µs rise, ≤ 4.3 V/µs fall | 100 / 10 V/µs |
| EN pin | ≤ 5.22 V with cable ringing (5.23 V in the recovery corner); 3.61 V without | **5.0 ROC exceeded** / 6.5 abs |
| OVLO pin | ≤ 4.36 V | **1.5 ROC exceeded** / 6.5 abs |
| AUXOFF pin / MR pin | ≤ 4.73 / ≤ 5.20 V (MR = +5V_IL through RMR) | 5.0 / 5.5 ROC |
| Short onset → P ≤ 0.8 V (edges ≤ 100 µs) | 1.73–23.4 µs. The slow end is the time U1 OUT takes to reach the OVLO trip through 10 Ω | — |
| Short onset → SHDN_c ≤ 0.8 V / U10 FET off | 1.69–23.4 / 3.19–24.9 µs | — |
| Short onset → drain < 0.5 V (bound) | 18.1–39.8 µs | 50 µs R4 |
| eFuse FET off → P ≤ 0.8 V / U10 off (all runs) | 0.53–1.72 / 1.99–3.19 µs | — |
| Slow creep, 10 ms edge | P ≤ 0.8 V 2.2 µs after the OVLO trip. From the start of the ramp: 114 / 519 µs. That number is ramp time, not response time | — |
| eFuse peak current / energy | ≤ 3.66 A / ≤ 0.16 µJ | IMAX 5.5 A |
| R80 peak current / energy | ≤ 3.71 A / ≤ 101 µJ per event | Pulse rating **unverified** |
| Q22 (P sink) peak | ≤ 6.9 mA / ≤ 12 mW | — |
| Recovery-corner restart (`G7`) | eFuse ≤ 174 µJ, R80 ≤ 220 µJ (current-limited restart into C_out) | — |

### 4.3 P interface and re-enable

| Case | P ≤ 0.8 V | U10 off | Re-enable after the short clears |
|---|---|---|---|
| Corrected (`TR_G5_corrected`) | 2.28 µs | 3.75 µs | Nominal corner: never. The eFuse stays off on OVLO hysteresis (`G7_..._nominal`) |
| BSS84, \|Vth\| 2.0 / 0.9 V (`TR_G5_bss84_*`) | **Not by the BSS84.** P stays about 2.3 / 1.3 V; the sink stays engaged. P ≤ 0.8 V only after U3 UV at 1.98–2.09 ms | 2.77 µs, via CD (P < 0.8·VCB) | — |
| No AUXOFF path (`TR_G5_none_U3only`, C max, minimum load) | 9.26 ms (U3 UV) | 9.27 ms | — |
| Recovery corner, short cleared at 1 / 20 ms (`TR_G7_*_reccorner`) | 2.31 µs | 3.77 µs | The eFuse restarts about 17 ms after the 1 ms clear, because U1 OUT, with only the divider load, decays slowly to the OVLO falling trip. **U10 re-enables at 158.6 / 177.6 ms after the short onset, with no MCU action** while MCU_PA_EN stays high, held off only by U3 tD ≥ 140 ms. The same timing occurs with the BSS84, because +5V_IL had already reached U3 UV. That ordering depends on the assumed loads, whereas the corrected circuit's MR path does not |

### 4.4 Sensitivity to unspecified delays (HYPOTHETICAL values; `out/sweeps.csv`, `out/limits.csv`, `out/fig_sweep_tovlo.png`)

**Largest permissible eFuse turn-off delay** after the OVLO comparator trips, with fast-trip ignored (bisection):

| Case | +5V_IL ≤ 5.5 V (ROC) | ≤ 6.0 V (abs max) |
|---|---|---|
| Hard short, C min, Ron max, 0.5 µH | **3.42 µs** | **5.68 µs** |
| Hard short, C min, no cable L | **3.01 µs** | 6.03 µs |
| Hard short, nominal | 4.12 µs | 8.18 µs |
| R_short 1 Ω, 1 µs edge, C min | 5.75 µs | 10.1 µs |
| **Proposal as drawn** (no R80/C40), C min | **1.06 µs** (below the 1.2 µs typical) | 1.66 µs |

The candidate therefore needs **t_off ≤ 3.0 µs** (ROC) or **≤ 5.7 µs** (abs max) in the worst simulated case.

- **Fast-trip as the only fast path** (OVLO response set to 50 µs): peak +5V_IL is 5.04 / 5.30 / 5.99 / 7.98 V for tSC = 0.5 / 2 / 5 / 20 µs (C min).
- **AUXOFF delay** (`aux` rows): drain < 0.5 V = t_AUX + 17.5 µs. Holding the R4 50 µs limit measured from the short itself needs **t_AUX ≤ 32.5 µs**. If AUXOFF never acts, P waits for U3 UV (8.4 ms).
- **Forward off-state leakage** (`H_leak*`, minimum load): 0 / 1 / 5 mA keep +5V_IL decaying. **10 mA drives +5V_IL to 7.60 V**, above the 6.0 V abs max. The tolerable leakage is set by the minimum +5V_IL load with P low, about 6.6–7 mA (ASSUMED).
- **AUXOFF low at 0.7 V with a hot 2N7002 (VGS(th) 1.0 V):** still works in the model (P ≤ 0.8 V at 1.68 µs), because Q20 turns off. This is not guaranteed: VOL is unspecified.

### 4.5 Proposal as drawn (`TR_G8`, `G8_*`)

| Case | Result |
|---|---|
| FT typical | Peak +5V_IL 5.19 V. IN slew **116 V/µs rising** and **16 V/µs falling** (abs max violations). U1 OUT/IN 21.2 V, **above the 10 V C2 rating**. EN 5.76 V and AUXOFF 5.19 V, both above their ROC. P **never reaches ≤ 0.8 V**: it ends at 2.25 V while CD holds SHDN_c |
| FT ignored, C min | +5V_IL **5.60 V (above ROC)** and IN 23.5 V (above the 23 V ROC) |

### 4.6 Back-power paths

| Path | Result |
|---|---|
| +5V_PA → U9 input ESD | ≤ 0.43 mA into a dead +5V_IL. The rail rises ≤ 1.6 V, which is below the TPS3703 1.7 V UVLO and the U10 3.88 V UVLO |
| J4 emulation inputs | ≤ 0.1 mA each |
| AUXOFF pull-up | ≤ 51 µA |
| eFuse reverse | No DC reverse current |
| eFuse forward leakage | **Not specified** (G-T4) |
| U4 SENSE with VDD = 0 | Not specified |

## 5. Model limitations

- **Not a vendor model.**
  - The TI TPS25947 transient model (SLVMDJ6) was obtained, but it is Cadence-encrypted for PSpice. It was **not executed** (`SOURCES.md`).
  - Comparators are ideal and all delays are parameters.
  - The FET is a resistor with ideal reverse blocking.
  - The active current limit is instantaneous: the 400 µs typical tLIM settling is ignored.
  - The turn-on delay after UV clears is a fixed 0.5 ms (ASSUMED; tD,ON is 1.32 ms typ at 1.8 nF, 12 V). It affects only start-up timing.
  - Thermal effects and OT are not modelled.
- **Discrete parts:** MOSFETs are level-1 fits to 25 °C maxima. The TPS3703 RESET is a 50 Ω sink.
- **U1:** a gm source with dropout and current limit. A short is a conductance ramp.
- **Loads:**
  - +5V_IL load is lumped (3/6/15 mA, ASSUMED).
  - Capacitor DC-bias retention is ASSUMED (no manufacturer curve was read).
  - The bench source is ideal → current limit → C → R–L.
- **Crowbar and drain:** not simulated. The H2-D bound (16.5 µs from P sink) is reused.
- **Not executed:**
  - vendor-model transients in PSpice for TI (OVLO/FT/AUXOFF timing, OVLO recovery);
  - TPS3703 MR timing;
  - any temperature simulation.

## 6. Unbounded parameters and open gates (A-IL12 remains OPEN)

| Gate | Parameter | Needed value (from §4.4) | How to close |
|---|---|---|---|
| **G-T1** | tOVLO maximum (VOVLO > VOV(R) → VOUT falling), over temperature, with VOVLO up to ~4.4 V | ≤ 3.0 µs (ROC) / ≤ 5.7 µs (abs) | TI statement, or E-bench measurement on ≥ 3 devices at −40/25/85 °C. **A typical value cannot close it** |
| **G-T2** | Fast-trip tSC/tFT maximum and ISC minimum | ≤ 2 µs keeps 5.3 V | TI statement or bench |
| **G-T3** | OVLO pin behaviour for 1.5 V < VOVLO ≤ 6.5 V (outside the ROC, 3.0–4.4 V here) | The trip must hold and must not latch up | TI statement. No clamp is proposed (none verified) |
| **G-T4** | Forward off-state leakage IN → OUT in OVLO at VIN − VOUT ≈ 8–13 V | < minimum +5V_IL load (≈ 6.6 mA ASSUMED); preferably ≤ 1 mA | TI statement plus a minimum-load bleeder decision |
| **G-T5** | AUXOFF de-assertion delay after the OVLO trip, and AUXOFF VOL at 46 µA | ≤ 32.5 µs if R4 is counted from the short; VOL < 1.0 V (Q20 VGS(th) min, 25 °C) | TI statement or bench |
| G-T6 | TPS3703 tPD(MR) maximum and RMR minimum | Not on the P timing path (Q22 is direct). Needed for the tD hold-off | TI |
| G-R1 | R4 onset definition for A-IL12: rail 5 % beyond threshold (existing; met, 46.5 µs) or the short itself | Decision for the safety owner. Not changed here | Requirement review |
| G-R2 | Re-enable without MCU action after the short clears (recovery corner): only U3 tD ≥ 140 ms; the eFuse OVLO is not a latch | Hardware latch, or explicit acceptance that MCU_PA_EN firmware gating is **not independent** | Design decision. A firmware-only hold-off must not be described as fail-safe |
| G-C1 | DC-bias curves: 47 µF 1210 16 V, C2 25 V, C40 1 µF at 13 V | C_out_eff ≥ 19.4 µF used for the t_off limits | Manufacturer data |
| G-C2 | R80 2.2 Ω pulse rating (≤ 3.7 A, ≤ 101 µJ per fault; 0.77 W for ≤ 0.72 ms at OVLO recovery) | — | Pick an MPN with a pulse curve |
| G-B1 | VIN lead ringing: EN 5.23 V > 5 V ROC with 0.5 µH | Measure. Add damping, or re-select the EN divider if confirmed | Bench (cabled, current-limited) |
| G-B2 | Latent interface faults (AUXOFF open, Q20 D–S short, R88 open) lose the AUXOFF path silently | Proof-test at start-up or by fixture test | Bench procedure addition |
| G-S1 | Vendor-model simulation in PSpice for TI | Compare with `out/sweeps.csv` | Needs a PSpice licence/tool |

**Draft questions for TI (NOT sent):** G-T1, G-T2, G-T3, G-T4, G-T5 and G-T6 above, each asked for TPS259470LRPW at VIN 5–13.2 V over −40…125 °C.

## 7. What this study does not claim

- No safety PASS. Typical datasheet values are never used as limits; each one is labelled TYP.
- Simulated numbers are behavioural and preliminary.
- A-IL12 stays **open** until G-T1, G-T4 and G-T5 have guaranteed or measured worst-case values inside the derived limits and G-R1/G-R2 are decided.
- The tile still needs the same protection: the tile +5V_IL is not studied separately here.
