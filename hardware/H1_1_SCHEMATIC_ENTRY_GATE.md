# H1.1 Schematic-Entry Gate

Date: 2026-11-11. Branch `hardware/h1-4t4r-architecture`, baseline `2589aec`.

## Decision: **CONDITIONAL GO** for schematic entry — PROTOTYPE envelope only

Scope of the GO: 4T4R tile, topology A, **ADAR1000 ×4 + ADTR1107 ×16**, LTC5552 converter at
IF 1.8 GHz / LO 6.6 GHz, prototype envelope (≥ 10 dBm average per feed). Schematic entry may start.
**Neither part is "qualified"**: qualification requires the 8.4 GHz bench evidence in condition C2.

| Gate | Status |
|---|---|
| Component selection (prototype) | **GO** — ADAR1000 + ADTR1107 |
| Schematic entry (prototype) | **CONDITIONAL GO** — conditions C1–C4 |
| Layout freeze (H2) | NO-GO until C1–C2 closed |
| PCB fabrication | **NO-GO** |
| Scalable-target front end | **NOT SELECTED** — no candidate qualified |

## Conditions

| ID | Condition | Must close before |
|---|---|---|
| C1 | ADI written confirmation of ADAR1000 lifecycle, lead time and a quote for ≥ 8 pcs through an authorised channel (vendor question A1) | layout freeze / any order |
| C2 | Bench measurement of ADAR1000-EVALZ + ADTR1107-EVALZ at 8.35–8.45 GHz: TX gain, OP1dB, 100 MHz OFDM EVM/ACLR vs back-off, RX gain/NF, phase/gain step accuracy — or manufacturer 8.4 GHz data (A3, A5) | layout freeze |
| C3 | Project-lead acceptance of the prototype envelope (≥ 10 dBm/feed) and of B4 re-scoping (P1 energy claims stay simulation-only) | schematic sign-off |
| C4 | LTC5552 up-conversion behaviour at 8.4 GHz / 1.8 GHz IF and ADF4371 output at 6.6 GHz confirmed (eval board or vendor data) | layout freeze |

## Blocker re-evaluation (B1–B4)

| ID | Verified evidence | Remaining uncertainty | Blocks | Action to close |
|---|---|---|---|---|
| **B1** ADAR1000 availability | Lifecycle RFND (project lead, official page; our fetch saw only the agreeing search summary). ADI sample/buy: 16 business weeks. ADAR1000-EVALZ 11 pcs and EVAL1Z 49 pcs in ADI channel. | No authorised distributor stock; no price; no confirmed allocation of 4–8 pcs. | **Fabrication only** (was: schematics) | C1 |
| **B2** TX power | ADTR1107 OP1dB 23 dBm typ / 21 min over 6–14 GHz (OFFICIAL Rev C) → 12.3–14.3 dBm/feed at 8–10 dB back-off. QPA0813 OP1dB is 19 dBm (Psat 28.5) — H1's discrete advantage was wrong. | Real OFDM back-off unknown (no EVM/ACLR data for any candidate). | **Split:** PROTOTYPE — **resolved** by envelope (≥ 10 dBm/feed met with ≥ 2.3 dB margin on typ). SCALABLE — **open**, does not block prototype schematics | C2 for prototype; scalable FE evaluation (A6, B4) later |
| **B3** 8.4 GHz data | ADTR1107 table covers 6–14 GHz with min values (in-spec at 8.4). ADAR1000 operating range 8–16 GHz. LTC5552 3–20 GHz. | ADAR1000 performance below 9.5 GHz, LTC5552 at 8.4 GHz, ADF4371 at 6.6 GHz all unmeasured. ADTR1101 TX only specified ≥ 8.5 GHz. | **Qualification / layout freeze / fabrication** — not schematic entry | C2, C4 |
| **B4** Energy model | Prototype effective PA efficiency ~1.1% vs sim 0.25; tile 27.4 W TX. | Scalable-target efficiency unknown. | **Nothing in hardware.** Re-scoped as a model-validity limitation: P1 energy/energy-per-bit results stay simulation-only | C3; optional single targeted model update after H1 (list in `H1_1_POWER_ENVELOPES.md`) |

## Explicitly not done in H1.1

No simulator changes, no simulations, no FPGA/RTL, no layout, no purchases, no vendor or export-office
contact (questions are drafts in `H1_1_VENDOR_QUESTIONS.md`), no merge or PR to `main`.
No manufacturer measurement at 8.4 GHz has been performed or obtained.
