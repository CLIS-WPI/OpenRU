# H2-A Task 1 — Mixer decision: LTC5553 replaces LTC5552

Date 2026-11-12. Operating point: RF 8.35–8.45 GHz, IF 1.75–1.85 GHz, LO 6.6 GHz (low-side), used for both
up- and down-conversion through one N310 TX/RX port per chain.

## Decision

**LTC5553IUDB is selected.** LTC5552 is withdrawn from the BOM.

Reasons, in order of weight:

1. **The manufacturer says so, in the LTC5552 datasheet itself.** The 5552f datasheet, p1, says:
   "The LTC5552 is recommended for applications where the IF frequency range extends below 500MHz. For
   applications where the IF frequency is always above 500MHz, the LTC5553 is recommended, since it includes an
   integrated IF balun." Our IF is always 1.75–1.85 GHz.
2. **LTC5553 is documented at our IF; LTC5552 is not.**
   - LTC5553: the 5553f AC tables are measured at IF = 1890 MHz with low-side LO, which is 40–140 MHz from our IF.
   - LTC5552: all tables are at IF = 240 MHz. Its behaviour at 1.8 GHz IF is only in plots.
3. **LTC5553 is the simpler implementation.**
   - LTC5553: single-ended 50 Ω IF, "impedance matched from 500MHz to 9GHz" (5553f). It needs no balun and no IF matching.
   - LTC5552: differential IF, about 25 Ω ∥ 0.25 pF per pin. It needs an external 1:1 balun: TC1-1-13M+ (≤3 GHz) on its
     eval board, or TCM1-83X+. That adds one part, its loss and its amplitude/phase imbalance to each of the four chains.
4. **Same package, supply and EN behaviour.** Both are 3×2 mm UDB-12, 3.3 V at 132 mA, with EN turn-on 0.2 µs and
   turn-off 0.1 µs (TDD-capable), and a 0 dBm LO (−6…+6 dBm). The schematic change is therefore local to the
   converter sheet.

The choice did not rest on specification alone: the two parts' headline figures are within about 1 dB of each other, and the decision is driven by points 1–3.

## Comparison (verified datasheet values; plot reads marked)

| Parameter | LTC5553 (5553f) | LTC5552 (5552f) |
|---|---|---|
| RF / LO range | 3–20 GHz / 1–20 GHz | 3–20 GHz / 1–20 GHz |
| IF port | single-ended 50 Ω, matched 0.5–9 GHz, DC-grounded (~6.2 Ω) | differential DC–6 GHz, needs 1:1 balun |
| Table IF | **1890 MHz** | 240 MHz |
| Down: CL / IIP3 / IP1dB / SSB NF @ RF 10 GHz | 9.0 dB / 24.3 dBm / 16 dBm / 10.9 dB | 8.0 dB / 22.5 dBm / 14.6 dBm / 9.8 dB |
| Down @ RF 8.4 GHz (plot) | CL ≈ 8.0 dB, IIP3 ≈ 23.5 dBm, IP1dB ≈ 16.2 dBm | not read |
| Up: CL / IIP3 / IP1dB @ RF 10 GHz | 9.3 dB / 25.6 dBm / 14.8 dBm | 8.6 dB / 21.1 dBm / 14.5 dBm |
| Up @ IF 1.8 GHz (plot, RF 9.8 GHz) | CL ≈ 10.0 dB, IIP3 ≈ 25 dBm, IP1dB ≈ 14.8 dBm | not tabulated |
| LO–RF leakage | < −23 dBm (down), < −25 dBm (up) | < −24 dBm |
| LO–IF leakage | < −13 dBm (down), < −26 dBm (up) | < −19 dBm |
| IF–RF isolation (up) | > 40 dB | > 33 dB |
| DC on ports | RF and IF DC-grounded; LO ≈ 1.6 V and needs a series cap (18 pF) | same RF/LO; IF pins at 0 V |
| Reference circuit | 5553f Fig 1: C1 18 pF LO block, C2 18 pF + C3 1 µF on VCC, no RF/IF caps | 5552f test circuit + TC1-1-13M+ balun |
| Eval board | DC2566A (ADI page cited in the H2-A brief; not accessed — analog.com unreachable) | named in datasheet: no |

## Signal-chain compatibility

- **N310:** the N310 TX/RX port drives the LTC5553 IF port through an 18 pF DC block and a BFCN-1840+ filter. The DC
  block is there because the LTC5553 IF abs max is ±0.1 V DC and the N310 port's DC state is not verified.
- **RF side:**
  - Connection to ADAR1000 RF_IO is DC-safe without blocking caps: RF_IO sits at 0 V through its on-chip shunt
    inductor, and the LTC5553 RF port is DC-grounded.
  - The path from the mixer is BFCN-8350+ → HFCN-7150+ → EDC21-24+ coupler → RF_IO.
- **LO:** each mixer needs −6 to +6 dBm. The H2A LO budget gives −5.8 to +3.8 dBm across the ADF4371 settings,
  which is below the +10 dBm abs max.
- **TDD:** the H1 converter T/R switches (2× ADRF5019 per chain) are removed. The passive mixer works in both directions,
  and the N310 TX/RX port does the T/R switching. This saves about 1.8 dB.

## Files changed by the decision

- `reports/H2A_RF_CASCADE_BUDGET.csv`: new cascade with LTC5553. The feed-referred RX NF goes from 3.85 to 4.05 dB.
  The RX NF gets slightly worse even though the switches are gone, because LTC5553 NF is taken from its 10 GHz table
  (10.9 dB), where H1 assumed NF = CL.
- `reports/H2A_CANDIDATE_BOM.csv`: LTC5553 ×4 and BFCN-1840+ ×4; no balun; no converter SPDTs.
- `../H1_CANDIDATE_BOM.csv`: the LTC5552 row is marked superseded.

## Still to verify (condition C4)

Bench data is still needed for LTC5553 up-conversion at RF 8.4 GHz / IF 1.8 GHz (CL, OIP3, LO leakage). All 8.4 GHz
figures above are plot reads (about ±0.5 dB) or nearby table points; none is a guaranteed specification.
