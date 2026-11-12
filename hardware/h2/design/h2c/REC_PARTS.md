# REC part selection (H2C_SEQUENCING_SIM.md revision 2, "Recommended hardware changes" items 1–9)

All datasheets are in `h2c/rec/ds/` (PDF + pdftotext). The page numbers are the datasheet's own page numbers.

## Summary

| REC item | Part (MPN) | KiCad symbol | Datasheet | Status |
|---|---|---|---|---|
| 1 Q_CB crowbar | TI **CSD16301Q2** | Transistor_FET:CSD16301Q2 (stock) | SLPS235E (Nov 2024) | Verified; VGS(th) min 0.9 V is just below the 1–2 V requirement (see mismatch M1) |
| 1 R_CB 0.33 Ω pulse | **3 × Vishay RCS12061R00FKEA** (1 Ω, 1206, anti-surge) in parallel = 0.333 Ω | Device:R | Vishay RCS e3, doc 20065 (rev 11-Jun-2025) | Verified (pulse curve). Deviation: 3 parts instead of 1 (M2) |
| 2 R_CBPU | 4.7 kΩ 1 % 0402 | Device:R | – | generic |
| 3/6 Q2, Q3 (+ inverter Q4) | Diodes **DMG1012T-7** | Transistor_FET:DMG1012T (stock) | DS31783 Rev 8-2 | Verified; meets 0.5–1.0 V exactly |
| 4 R_CBD / C_CBD | 10 kΩ 1 % / 1 nF 50 V C0G | Device:R / Device:C | – | generic |
| 5 dual supervisor | TI **TPS386000RGPR** (quad, open-drain, CT delay) | **openru_x6:TPS386000RGP** (new, project library) | SBVS105F (Oct 2018) | Verified; second (active-high) output realised with an inverter (M4) |
| 7 BAT54C | Diodes **BAT54C-7-F** | Diode:BAT54C (stock) | DS11005 Rev 35-2 | Verified |
| 8 IL_REF LDO | TI **TLV75518PDBVR** | Regulator_Linear:TLV70012_SOT23-5 (as U653) | SBVS320D (Sep 2024) | Verified (pinout DBV, Table 4-1) |
| 9 +3V3_RF UV divider | 49.9 kΩ / 10.2 kΩ 0.1 % (existing R971/R970 re-valued and re-wired) | Device:R | – | generic |

Rejected candidates (datasheets downloaded):
- CSD17578Q3A (SLPS525A): Ciss 1150 pF typ, 1590 pF max, above the ~1 nF limit; not in the KiCad library.
- CSD17581Q3A: Ciss 3640 pF max.
- CSD13381F4: VGS(th) 0.65–1.10 V. CSD13380F3: 0.55–1.30 V. CSD17483F4: 0.65–1.10 V. All exceed the 1.0 V corner.
- CSD15380F3: VGS(th) up to 1.35 V, and RDS(on) is specified only at 4.5 V.
- TPS3779/TPS3780 (SBVS250): no reset delay (pure detector), VDD min 1.5 V, and no low-VDD output spec.
- TPS3702/TPS3703: single-rail window monitors.
- Vishay CRCW-HP and RCS: no value below 1 Ω. Vishay WSL1206: max 0.2 Ω. KOA SG73P: min 1 Ω. KOA SR73 2B R33 exists, but it is a current-sense part with no pulse curve, so it is UNVERIFIED for pulse duty.

## 1. Crowbar MOSFET: CSD16301Q2 (SLPS235E)

| Parameter | Requirement / sim | Datasheet | OK? |
|---|---|---|---|
| VDS | ≥ 20 V | 25 V (abs max, p1) | ✓ |
| VGS abs max | gate ≤ 5.18 V | +10 / −8 V (p1) | ✓ |
| RDS(on) at VGS 4.5 V | ≤ 50 mΩ (sim: R_total 0.38 Ω incl. ≤ 50 mΩ) | 23 typ / **29 max** mΩ at 4 A (§5.1 p3) | ✓ |
| VGS(th) | 1–2 V | **0.9 / 1.1 / 1.55 V** (min/typ/max, 250 µA) | **M1**: min 0.9 V < 1.0 V |
| Ciss | ≤ ~1 nF | 260 typ / 340 max pF | ✓ (faster than sim) |
| IDM | ≥ 20 A for 10 µs | 85 A (≤ 100 µs, ≤ 1 %) | ✓ |
| SOA (Fig 4-10, p6) | 13 A theoretical / 7.5 A sim peak at ≤ 5.2 V, ≈ 10–30 µs | at VDS 5 V: the 100 µs line ≈ 50–60 A and the 1 ms line ≈ 12 A | ✓ wide margin |
| Energy | ≤ 0.25 mJ per event, almost all in R_CB (0.33/0.36) | EAS 10 mJ (avalanche; not the mechanism here) | ✓ |
| Pinout (Fig p1, top view) | – | 1, 2, 5, 6 = D; 3 = G; 4 = S; large pad = D; small pad = S | KiCad symbol pins 1/2/5/6/8 = D, 3 = G, 4/7 = S; Texas_DQK pad 8 = large D pad, pad 7 = S pad ✓ |

## 1b. R_CB: 3 × RCS1206 1 Ω (Vishay doc 20065)

- Range: 1 Ω to 10 MΩ (p2), so 0.33 Ω does not exist in this anti-surge series. Three 1 Ω in parallel give 0.333 Ω (sim 0.33 Ω, +1 %).
- Pulse (p4, "Single Pulse High Power Overload 10 µs / 700 µs"): RCS1206 at 1 Ω allows ≈ 10 V peak (10 pulses at 1-min intervals, ΔR ≤ 1 %).
- Ours: each resistor sees ≤ 5.18 V peak, decaying with τ ≈ 7 µs, which is far shorter than 700 µs.
- Energy: ≤ 0.08 mJ per resistor per event. Peak current per resistor ≤ 13/3 = 4.3 A theoretical, 2.5 A in the sim.
- Rating: P70 0.5 W. Repetition is limited by the datasheet's 1-min pulse interval: crowbar events happen per disarm or fault, not per TX burst. **Flag:** a test that cycles the arm signal faster than once a minute is outside this curve.

## 3/6. Q2, Q3 and the inverter: DMG1012T (DS31783)

| Parameter | Requirement / sim | Datasheet (p2) | OK? |
|---|---|---|---|
| VDS | ≥ 12 V | 20 V | ✓ |
| VGS(th) | 0.5–1.0 V (both corners simulated) | **0.5 – 1.0 V** (250 µA) | ✓ exactly the sim corners |
| RDS(on) at ≤ 1.8 V | fully on at 1.7 V | 0.5 typ / **0.7 Ω max at VGS 1.8 V**, 350 mA | ✓ (at 1.06 mA hold current the drop is < 1 mV) |
| VGSS | Q3 / inverter gate up to ≈ 5.0 V (supervisor VDD) | **±6 V** | ✓ (1 V margin) |
| Ciss | sim: Q2 gate RC 10 k / 1 nF dominates | 60.67 pF typ | ✓ |
| IGSS | – | ±1 µA at 4.5 V (ESD diode) | ✓; 0.1 V drop across the 100 k pull-up |
| Pinout (p1) | – | SOT-523: 1 G, 2 S, 3 D | matches Transistor_FET:DMG1012T ✓ |

## 5. Supervisor: TPS386000RGPR (SBVS105F)

| Parameter | Requirement / sim | Datasheet | OK? |
|---|---|---|---|
| Channels | 2 (+1V8_DIG, +3V3_AUX) | 4 (SVS-1…4), adjustable, VITN = 0.396/0.400/0.404 V (§6.5 p7) | ✓ (SVS-1, SVS-2 used) |
| Output | open-drain, wired-AND onto PG_3V3RF | TPS386000 = open-drain RESETn (p5) | ✓ |
| **Valid output at low VDD** | sim assumed ≈ 0.9 V | "Power-up reset voltage … VOL(max) = 0.2 V, IRESETn = 15 µA: **0.9 V max**" (§6.5 p7); "outputs are defined for VDD voltage higher than 0.9 V" (§8.3.4 p23) | ✓ matches the sim. Also VOL ≤ 0.3 V at 0.4 mA for 1.3 V < VDD < 1.8 V |
| Delay | ≈ 10 ms | CCT (nF) = (tD − 0.5 ms) × 0.242 (Eq 8, p27). 2.2 nF gives 9.6 ms nom; 7.1–12.2 ms from ICT 235–365 nA and VTH 1.18–1.299 V. CT open gives 14–24 ms (§6.7) | ✓ |
| **Detection (assert) delay** | sim: instantaneous | "transitions from released-state to asserted-state are performed almost immediately with minimal propagation delay" (§8.3.4). **No max is given.** tW input pulse width ≈ 4 µs typ (§6.6), a function of overdrive (Fig 14/37) | **M3 (flag)**: not specified, so a few µs plus the overdrive dependence is not modelled |
| Thresholds | 1.67 V / 2.97 V | SENSE1: 32.4k/10.2k → 0.400 × (1 + 3.176) = **1.6706 V** (range 1.654–1.687 V from VITN ±1 %). SENSE2: 64.2k/10.0k → 0.400 × 7.42 = **2.968 V** (range 2.938–2.998 V). 0.1 % resistors | ✓ |
| VDD range | diode-OR of +3V3_RF and +5V_PA | 1.8–6.5 V ROC, 7 V abs max | ✓ (≈ 3.0–4.95 V) |
| Output sink / pull-up | sim: PGOOD sinks ≈ 3.2 mA through the BAT54C clamps | VOL ≤ 0.4 V at 1 mA only; abs max 5 mA; ROC RPULL-UP ≥ 6.5 kΩ; "pullup resistor should be no smaller than 10 kΩ" (§8.3.4) | **M5 (flag)**, see below |
| Pinout (p4, RGP VQFN-20) | – | 1 MR, 2 CT4, 3 CT3, 4 CT2, 5 CT1, 6 SENSE4H, 7 SENSE4L, 8 SENSE3, 9 SENSE2, 10 SENSE1, 11 NC, 12 GND, 13 VREF, 14 VDD, 15 RESET1, 16 RESET2, 17 RESET3, 18 RESET4, 19 WDO, 20 WDI, PAD | symbol openru_x6:TPS386000RGP is built from this table (pad = pin 21); checked with get_symbol_info ✓ |

Unused pins:
- **SENSE4H → GND.** "Connect to GND if not being used" (p4).
- **NC (11) → GND.** "TI recommends connecting this pin to the GND pin" (p4).
- **PAD → GND.** "must be connected only to GND or to the floating thermal pattern".
- **CT3, CT4 open (NC flag).** "Connecting this pin to VDD through a 40-kΩ to 200-kΩ resistor, or leaving it open, selects a fixed delay time" (p4).
- **VREF open (NC flag).** It is "intended to only source current into resistor(s) … Do not connect only a capacitor" (p4), and the IDD spec is given with "VREF open" (§6.5).
- **MR → supervisor VDD.** There is no internal pull-up ("the TPS3860x0 does not integrate an internal pullup resistor", §8.3.2).
- **WDI → GND.** This is the characterisation condition "WDI = GND" (§6.5).
- **SENSE3, SENSE4L → GND (ROC 0…VDD).** RESET3/RESET4 stay asserted. They and WDO are joined on IL_SUP_OD with a 1 MΩ pull-up to the supervisor VDD (ROC RPULL-UP 6.5 k–10 MΩ), which costs ≈ 5 µA. The datasheet has no statement that allows these outputs to float, so they are not NC-flagged. Tying them to GND made KiCad ERC flag open collector against the GND PWR_FLAG.
- Watchdog consequence: WDO latches low 450–750 ms after RESET1 release (WDI static). It is unused; RESET1 is not affected (WDO is a separate output, §8.3.3).

**M4: second, active-high output.** The TPS386000 has only active-low outputs, and no single TI supervisor here offers "open-drain RESET + active-high output + 0.9 V validity". REC item 5 says "push-pull, or open-drain with 100 kΩ to the supervisor VDD"; the equivalent is built with one DMG1012T inverter:
- Gate = PG_3V3RF; drain = IL_Q3G, pulled up by 100 kΩ to the supervisor VDD; source = GND. IL_Q3G drives the Q3 gate.
- PG_3V3RF low (supervisor fault, U650 PGOOD low, or +1V8_DIG absent so the 100 k pull-up is unpowered): the inverter is off, IL_Q3G ≈ supervisor VDD, Q3 is on and the TPS22917 ON pin is clamped.
- PG_3V3RF high (1.8 V): VGS = 1.8 V, RDS ≤ 0.7 Ω, so Q3 is off.
- Difference from the sim: Q3 also clamps whenever U650 PGOOD is low. That is consistent with IL_EN = NEG_RAILS_OK · PG_3V3RF, so it costs nothing.
- Delay: the 100 k × (Q3 Ciss ≈ 61 pF + traces) rise is ≈ 10 µs to reach 1 V. That is slower than an ideal push-pull, but it is only needed in the slow invalid-1V8 band (sim: IL_REF decay τ = 120 µs). **Flag:** not re-simulated.

**M5: supervisor sink current.**
- With the BAT54C clamps active (PG_3V3RF low while U705/U911 still drive high through 1 kΩ), the TPS386000 sinks ≈ 2 × (1.8 − 0.33 − VOL)/1 kΩ ≈ 2.4–2.9 mA. That is inside the 5 mA abs max, but:
  - (a) above the 1 mA VOL test point;
  - (b) the effective "pull-up" (1 kΩ) is below the ROC minimum 6.5 kΩ and the 10 kΩ recommendation.
- VOL at 2.4 mA is not specified. The typical curve (Fig, VDD 3.3 V, 25 °C) gives ≈ 0.08 V at 1 mA, which extrapolates to ≈ 0.2 V.
- **Consequences, also flagged by the sim ("verify the PGOOD VOL at that current"):**
  - The clamp level on PA_DRAIN_EN / IL_CLR_N ≈ VOL + VF(BAT54C, ≈ 0.33 V max at 1.2 mA) ≈ 0.5 V typ. That is below VENF min 1.08 V and below the LVC VIL of 0.58 V, but **not guaranteed**.
  - The TLV755P EN VLO is **0.3 V max** (SBVS320D §6.5). The LDO EN on PG_3V3RF is guaranteed off only while PG_3V3RF ≤ 0.3 V. With the clamp current flowing, that needs VOL ≤ 0.3 V at ≈ 2.4 mA, which is not datasheet-guaranteed.
  - The clamp current flows only while logic is alive and driving high and the supervisor says fault (transient), but the guarantee is missing.
  - Options:
    - (i) raise the 1 kΩ series resistors: this conflicts with the TPS22810 EN fall time (RC loading by the four Q2 10 k / 1 nF branches; with 10 kΩ the node only falls to ≈ 1.44 V at once);
    - (ii) a dedicated clamp transistor driven from IL_Q3G;
    - (iii) a bench check.
- The same applies to U650 (TPS568230) PGOOD, which is wired in parallel (not re-checked here).

## 7. BAT54C (Diodes DS11005)

- VF max: 240 mV at 0.1 mA, 320 mV at 1 mA, 400 mV at 10 mA (p2). At ≈ 1.2–3 mA that is **≈ 0.33–0.36 V max** by interpolation.
- VRRM 30 V; IR ≤ 2 µA at 25 V; CT ≤ 10 pF.
- Pinout (p1 drawing): pins 1 and 2 = anodes (bottom), pin 3 = common cathode. This matches Diode:BAT54C (pins 1, 2 passive left/right, pin 3 top) ✓.
- Sim assumption ("clamp ≤ 0.5 V at ≈ 3.2 mA"): consistent with VF ≤ 0.36 V, if the sink VOL ≤ 0.14 V (see M5).
- As the supervisor VDD OR: from +5V_PA, VDD ≈ 5.18 − 0.24 V (µA load). The diode at 15–22 µA IDD has VF < 0.24 V.

## 8. IL_REF LDO: TLV75518PDBVR (SBVS320D)

- DBV pinout (Table 4-1): 1 IN, 2 GND, 3 EN, 4 NC ("No internal connection"), 5 OUT. This matches Regulator_Linear:TLV70012_SOT23-5, the same base symbol as U653.
- EN: VHI ≥ 1 V; VLO ≤ 0.3 V; IEN 10 nA. EN is driven by PG_3V3RF (1.8 V high via R654 100 k). See M5 for the low level.
- UVLO 1.21–1.44 V rising; tSTR 550 µs; RPULLDOWN 120 Ω (sim τ = 120 µs with 1 µF ✓).
- CIN and COUT ≥ 1 µF required (Table 4-1). New C938 1 µF is on IN. COUT is the existing C914 1 µF, moved from +1V8_DIG to IL_REF_SRC; it also serves as the TPS22917 VIN capacitor.

## Mismatches against the sim assumptions (summary)

| # | Item | Sim assumption | Real part | Effect |
|---|---|---|---|---|
| M1 | Q_CB VGS(th) | 1–2 V | 0.9–1.55 V | The crowbar conducts slightly earlier at the 0.9 V corner. With τ = 4.7 k × 340 pF ≈ 1.6 µs that is < 0.1 µs less break-before-make. Ciss ≤ 340 pF (vs ≤ 1 nF) makes turn-on faster, so T50 improves. Not re-simulated. |
| M2 | R_CB | one 0.33 Ω 1206 | 3 × 1 Ω RCS1206 in parallel (0.333 Ω) | +1 % R; energy shared by 3. No single pulse-rated 0.33 Ω 1206 was verifiable. |
| M3 | Supervisor detection delay | 0 (ideal) | "almost immediately … minimal propagation delay", no max; tW ≈ 4 µs typ, overdrive-dependent | REF/G margins in abrupt +1V8_DIG-loss ordering cases (sim limitation note) are not covered. |
| M4 | Supervisor 2nd output | active-high from the supervisor | DMG1012T inverter on PG_3V3RF, 100 k pull-up | Q3 is also on when U650 PGOOD is low (harmless); ≈ 10 µs rise. Not re-simulated. |
| M5 | Clamp sink | ideal open-drain sink of ≈ 3.2 mA | VOL spec only at 1 mA (≤ 0.4 V); effective pull-up 1 kΩ < ROC 6.5 kΩ | Clamp level and TLV755 EN ≤ 0.3 V are not datasheet-guaranteed under clamp current. |
| M6 | Q2 Vth | 0.5–1.0 V | 0.5–1.0 V | none |
| M7 | Supervisor valid VDD | 0.9 V | 0.9 V max (VOL ≤ 0.2 V at 15 µA) | none, but the sink capability at 0.9 V is only 15 µA (PG pull-up 18 µA via 100 k: marginal at exactly 0.9 V) |
