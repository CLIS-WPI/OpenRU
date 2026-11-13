# A-IL12 sources, models and tool versions

## Documents read (not committed; fetched 2026-11-13)

| Document | Part | SHA-256 (first 16) | Used for |
|---|---|---|---|
| TI SLVSFC9C (Oct 2020, rev. May 2026) | TPS25947xx / TPS259470LRPW | 8f96de3899030916 | thresholds, abs max, ROC, timing (typ only), OVLO/AUXOFF/FLT behaviour, orderable TPS259470LRPWR (Active) |
| TI SBVS372C | TPS7A2550 (U1) | 909c2cec04938853 | COUT 1–100 µF, ICL, dropout, VOUT abs max |
| TI SBVS249B | TPS3703 (U3) | cc65714774e50c97 | VDD abs max 6 V, MR (VMR_L 0.3 V, 100 k typ, tPD(MR) 500 ns typ), tPD 30 µs, tD, VOL |
| TI SLVSET9G | TPS16630 (U10) | 8f91a0db2daf2da3 | V(SHUTF), V(SHUTR), I(SHDN), tSD |
| TI SBOS561C | TLV3201/3202 | 358c30340b482fc4 | supply abs max 7 V, ROC 5.5 V |
| onsemi BSS84LT1/D Rev. 23 | BSS84LT1G | d6b768c5da79e9fa | VGS(th) −0.9…−2.0 V, RDS(on) ≤ 10 Ω (25 °C) |
| onsemi 2N7002L/D Rev. 11 | 2N7002LT1G | cb5dde65ff045a7a | VGS(th) 1.0–2.5 V, rDS(on) 7.5/13.5 Ω, Ciss 50 pF |
| Diodes DS18001 Rev. 33 | BZX84C2V4–C51 | 70c346b571aa2f8b | series starts at 2V4; IR 50 µA at 1 V for 2V4 |
| onsemi BZX84C2V4LT1/D Rev. 23 | BZX84C2V4LT1G… | f43f3963cf2d5a7d | same range check |

The Nexperia BZX84 and BSS84 pages returned HTML redirects instead of PDFs. They were not used.

## Device models

| Model | Status |
|---|---|
| TI TPS25947x PSpice transient model, SLVMDJ6 (`TPS25947x_TRANS.lib`, Final 1.00, 09 Feb 2021; zip SHA-256 9bfd3f61435af481) | **Obtained, NOT executed.** The subcircuit body is Cadence-encrypted (`$CDNENCSTART_ADV2`) and runs only in PSpice (PSpice for TI). ngspice cannot run it. Its own notes say temperature-dependent characteristics are not modelled. Not committed (TI licence). |
| TPS7A25, TPS3703, TPS1663 TI models | Not used. The study needs only their datasheet thresholds and delays. |
| onsemi BSS84 / 2N7002 SPICE models | Not used. The BSS84 conclusion (P ≥ \|VGS(th)\|) does not depend on a device model. Level-1 fits to the datasheet maxima are used for the numbers. |
| `model.py` (this study) | Event-driven behavioural model in Python/SciPy, written here. **Not a vendor model.** Limitations are listed in its docstring and in the report §5. |

**Simulations that remain unexecuted:**
1. TPS25947 vendor-model transients in PSpice for TI:
   - OVLO and fast-trip response with the real internal delays, compared against `out/sweeps.csv`;
   - AUXOFF timing and level at the real sink current;
   - OVLO recovery with a current-limited start.
2. TPS3703 vendor-model MR → RESET timing.
3. Any thermal or temperature-dependent simulation. The vendor model does not model temperature, and neither does `model.py`.

## Tools (canonical run)

- **Image:** pinned `openru-x6-sim:0.1.0`, Python 3.12.3, NumPy 2.5.4, SciPy 1.18.1, Matplotlib 3.11.2. `out/summary.json` records the exact versions of the run that produced `out/`.
- **Command:** `bash hardware/h2/design/ail12/run_all.sh`, run from the repository root.
