# A-IL12 candidate circuit: audit of the proposal and corrected connection table

- Applies to the Candidate-A fixture (`fixture_h2e/candA_fixture`). The same topology applies to the tile's +5V_IL.
- **Nothing here is drawn in KiCad.** The schematics are unchanged.
- Numbers come from `calc.py` (`out/calc.txt`, section § numbers) and `run_sim.py` (`out/runs.csv`).

## 1. Proposal as received, and the audit result

| Item in the proposal | Finding | Evidence | Action |
|---|---|---|---|
| TPS259470LRPW after U1 | A valid choice. OVLO de-asserts AUXOFF (Table 7-4); FLT stays **high** on OVLO (Table 7-3). **The "L" (latch-off) suffix does not latch OVLO**: OVLO recovers automatically (tSWOV 90 µs typ) with a current-limited start that bypasses dVdt (§7.3.3). | SLVSFC9C | Kept. Recovery handled in §3 |
| OVLO divider 10.0 k / 2.94 k | Trip 5.18–5.41 V rising, 4.71–4.94 V falling. The minimum trip is 99 mV above U1 OUT max (5.08 V). The OVLO pin reaches 3.0 V at 13.2 V, **above the 0.5–1.5 V ROC** but below the 6.5 V abs max. The EC rows cover only 0.5–1.5 V, so behaviour above that is uncharacterised. | calc §1 | Kept. The ROC excursion is an open TI question (gate G-T3) |
| "BZX84C1V5" OVLO clamp | **The MPN does not exist** in the BZX84 series of Diodes (DS18001) or onsemi (BZX84C2V4LT1/D); the series starts at 2V4. The nearest real part (2V4: VZ 2.2–2.6 V, IR ≤ 50 µA at 1 V) cannot hold 1.5 V. Its leakage is up to 12 % of the 408 µA divider current at the trip point, which shifts the trip upward by an amount that is not bounded. A 1.24 V shunt reference overlaps the 1.223 V maximum trip. | calc §2 | **Removed.** No clamp. No unverified clamp is substituted |
| 6.65 kΩ ILM | This is exactly the RILM ROC maximum (6650 Ω), so any positive tolerance leaves the ROC. | calc §4 | **6.49 kΩ 0.1 %.** ILIM 0.514 A typ. The ±15 % band is DERIVED by scaling, not guaranteed |
| 2.2 nF dVdt | It must be rated ≥ VIN + 5 V = 18.2 V. | SLVSFC9C 6.3 | 50 V C0G. SR 0.26–1.77 V/ms (derived) |
| Added 47 µF on +5V_IL | Effective +5V_IL capacitance with C3 and 6 × 100 nF is 19.4 / 33.4 / 62.2 µF min/nom/max. DC-bias retention is ASSUMED. | calc §7 | Kept, as 16 V X5R 1210. The DC-bias curve has not been read (gate G-C1) |
| U1 local output capacitance | C2 (4.7 µF) stays on U1 OUT. C3 moves behind the eFuse. U1 sees ≤ 68 µF nominal ≤ 100 µF COUT max. **C2 is the 10 V CL10A475KP8NNNC, and the fault puts 13.2 V (sim: up to 18 V with cable L) on it.** | calc §6–7, SBVS372C | **C2 changed to 25 V** (CL21A475KAQNNNE, MPN unverified) |
| eFuse IN tied directly to U1 OUT | The IN slew abs max is 100 V/µs rising and 10 V/µs falling. With only C2 at the input, a short harder than 57 mΩ exceeds 100 V/µs, and R_short has no bound. The sim measures 116 V/µs rising and 16 V/µs falling for a 10 mΩ short (`TR_G8`). | calc §5, sim G8 | **Added R80 2.2 Ω + C40 1 µF 25 V.** Bounds: ≤ 14 V/µs rising, ≤ 8.6 V/µs falling for any R_short |
| EN/UVLO (not specified in the proposal) | EN must not be tied to IN: 13.2 V would exceed the 6.5 V abs max. | calc §3 | **R81 100 k / R82 37.4 k.** On 4.32–4.52 V. EN 3.61 V at 13.2 V; 4.98 V at the 18.2 V ringing peak, 20 mV under the 5 V ROC |
| AUXOFF → BSS84 gate, source = P, drain = GND | **Fails.** A PMOS with its source on P is a source follower. It stops conducting when V(P) − V(AUXOFF) falls to \|VGS(th)\|, and \|VGS(th)\| ≥ 0.9 V (25 °C, 250 µA). P therefore **cannot reach 0.8 V**. Level-1 estimates give 1.28–2.56 V; the sim settles at about 1.3–2.3 V until U3 UV acts after about 2 ms. The PA is still shut off through the CD comparator (P < 0.8·VCB), but P sits in an undefined logic region. Release is immediate when AUXOFF returns, so there is no re-enable hold-off. AUXOFF pulled up to +5V_IL can also reach 5.08 V, above its 5 V ROC. | calc §8, sim G5 | **Replaced** by the 2N7002 inverter below |
| AUXOFF timing | **No specification.** The datasheet gives no delay from the OVLO trip to AUXOFF low. tOVLO (1.2 µs) and tSC/tFT (500 ns) are **typical only**. | SLVSFC9C 6.6 | Treated as unbounded. Swept as HYPOTHETICAL |

## 2. Corrected candidate: connection table

New references continue the fixture numbering (U20, R80–R88, C40–C42, Q20–Q22, TP30–TP33). Net names follow the fixture's `IL_` convention. **IL_LDO** is the renamed U1-output net. The fixture's IL_5V (+5V_IL) now starts at U20 OUT.

| Ref | Pin / terminal | Net | Note |
|---|---|---|---|
| U1 TPS7A2550DRVR | OUT | **IL_LDO** (was IL_5V) | IN/EN unchanged on PWR_VIN |
| C2 4.7 µF **25 V** | 1 / 2 | IL_LDO / GND | U1 local COUT stays at U1 |
| R80 2.2 Ω 1206 | 1 / 2 | IL_LDO / IL_EFIN | eFuse IN slew limiter |
| C40 1 µF 25 V | 1 / 2 | IL_EFIN / GND | |
| U20 TPS259470LRPWR | 5 IN | IL_EFIN | |
| | 6 OUT | IL_5V (+5V_IL) | Everything that was on IL_5V except U1 OUT and C2 |
| | 8 GND | GND | |
| | 1 EN/UVLO | IL_EN20 | R81 100 k from IL_LDO, R82 37.4 k to GND |
| | 2 OVLO | IL_OV20 | R83 10.0 k from IL_LDO, R84 2.94 k to GND, **no clamp** |
| | 3 AUXOFF | IL_AUXOFF | R86 100 k to IL_5V, R87 1.0 M to GND |
| | 4 FLT | TP30 only | Not used for P: it stays high on OVLO |
| | 7 DVDT | C41 2.2 nF 50 V C0G to GND | |
| | 9 ILM | R85 6.49 k 0.1 % to GND | |
| | 10 ITIMER | open | Fastest overcurrent response (datasheet: leave open) |
| C42 47 µF 16 V | 1 / 2 | IL_5V / GND | Plus existing C3 4.7 µF and 6 × 100 nF |
| Q20 2N7002LT1G (Q_A) | G / S / D | IL_AUXOFF / GND / IL_AUXN | Inverter |
| R88 10 k | 1 / 2 | IL_5V / IL_AUXN | |
| Q21 2N7002LT1G (Q_B) | G / S / D | IL_AUXN / GND / **IL_MR1** (U3 pin 6) | U3 RESET low for tD (140–260 ms) after AUXOFF returns |
| Q22 2N7002LT1G (Q_C) | G / S / D | IL_AUXN / GND / **IL_P** | Direct P sink, independent of the typical-only tPD(MR) |
| TP31 / TP32 / TP33 | — | IL_AUXOFF / IL_AUXN / IL_LDO | Probe access |

**Fault-free behaviour:**
- AUXOFF is high (≤ 4.62 V), so Q20 is on and IL_AUXN is low. Q21 and Q22 are off; U3 MR floats high on its internal pull-up.
- During eFuse start-up, OVLO, UV or loss of IN, AUXOFF is low. IL_AUXN then rises to +5V_IL, P and MR go low, and U3 RESET follows.
- After a fault, U3 keeps P low for tD ≥ 140 ms after AUXOFF returns.

**Failure modes of the interface:**
- **Q20 gate open, or R87 open:** no effect.
- **AUXOFF pin open:** R86 keeps Q20 on, so the AUXOFF path is lost **without any indication**. The U3 UV fallback remains. A bench proof-test is needed.
- **Q20 D–S short:** the same silent loss.
- **Q21/Q22 open:** that path is lost; the other remains.
- **Q21/Q22 D–S short:** P is held low (safe).
- **R88 open:** IL_AUXN cannot rise, so the path is lost silently.

These latent faults are why the U3 UV fallback in §4 of the report matters.
