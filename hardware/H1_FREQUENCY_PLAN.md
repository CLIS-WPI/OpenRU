# H1 Frequency Plan

Status: feasibility candidate for a **custom** 4-channel converter. Not a validated design. PCB NO-GO.

## Constraints (verified)

| Item | Value | Source |
|---|---|---|
| RF | 8.35–8.45 GHz (8.4 GHz ± 50 MHz) | `configs/radio.yaml` |
| N310 tuning | 10 MHz – 6 GHz, ≤ 100 MHz per channel | N310 datasheet v3 p.1 |
| N310 RX filter bank | 1600–2100 MHz and 2100–2700 MHz bands | N310 datasheet v3 |
| N310 TX max out | 18 dBm (1–4 GHz), 12 dBm (4–6 GHz) | N310 datasheet v3 |
| N310 RX NF | 6.8 dB (TX/RX) / 5.8 dB (RX2) at 1.8 GHz; 7.5/6.5 dB at 2.4 GHz; 2.0 GHz not tabulated | N310 datasheet v3 |
| HMC773A / HMC773ALC3B | RF & LO 6–16 GHz, IF DC–10 GHz (die) / DC–8 GHz (SMT); characterised at **IF 500 MHz, LO 13 dBm** | HMC773A Rev A, HMC773ALC3B Rev D Table 1 p.3 |
| LTC5552 | RF 3–20 GHz, LO 1–20 GHz, IF DC–6 GHz, **LO −6…+6 dBm (0 dBm typ)**, CL 8.0 dB @ 10 GHz | LTC5552 datasheet p.3 |
| ADXUD1A reference | RF 8–12 GHz, **IF 4.2–6.3 GHz**, HMC773A, LO split ×4; 8.4 GHz not specifically documented | developer.analog.com X-band converter page (summarised fetch) |

The kickoff's blocker is confirmed: 8.4 GHz from a 4.5 GHz IF needs a 3.9 GHz LO, which is outside the
HMC773A 6–16 GHz LO band. The unmodified ADXUD1A is **not** shown to work at 8.4 GHz RF with an
N310-compatible IF and is used only as a reference schematic.

## Candidates

| Plan | IF | LO | Wanted | Image | LO offset from RF | N310 fit | Verdict |
|---|---|---|---|---|---|---|---|
| P0 (kickoff) | 2.0 GHz | 6.4 GHz (low side) | LO+IF | 4.4 GHz | 2.0 GHz | IF edge 2.05 GHz is 50 MHz from the 2.1 GHz filter-bank boundary; no NF point at 2.0 GHz | acceptable, not preferred |
| **P1 (recommended)** | **1.8 GHz** | **6.6 GHz** (low side) | LO+IF | 4.8 GHz | 1.8 GHz | 1.75–1.85 GHz centred in the 1.6–2.1 GHz bank; NF tabulated at 1.8 GHz | **preferred** |
| P2 | 1.8 GHz | 10.2 GHz (high side) | LO−IF | 12.0 GHz | 1.8 GHz | same as P1 | fallback if 6.6 GHz LO leakage proves hard to filter; LO from ADF4371 RF16x (2×VCO), 0–4 dBm, needs more LO gain |
| P3 (kickoff alt.) | 4.5 GHz | 12.9 GHz (high side) | LO−IF | 17.4 GHz | 4.5 GHz | N310 TX max only 12 dBm above 4 GHz; ADXUD1A IF filters reusable | not preferred: worse N310 performance; no evidence |

## Recommended: P1 — IF 1.8 GHz, LO 6.6 GHz, LTC5552

- **LO source:** one ADF4371, RF8x output (62.5–8000 MHz; 5–7 dBm max at 4–8 GHz, Rev 0 p.5; 6.6 GHz
  not tabulated) referenced to 10 MHz (via 100 MHz VCXO, as on ADXUD1A — see clock doc).
- **LO distribution:** 1:4 split ≈ −6 dB −1 dB excess → ≈ −2…0 dBm per mixer from the bare PLL.
  LTC5552 needs −6…+6 dBm, so a single small LO buffer amp (part TBD) gives margin; HMC773A would need
  ≥ 13 dBm × 4 → ~20 dBm LO driver and its heat. **This is why LTC5552 is preferred over HMC773A.**
- **Mixer reuse:** one passive mixer per chain used in both directions, with ADRF5019 SPDTs on its RF
  and IF sides (TDD). Upconversion loss at 8.4 GHz is **UNVERIFIED**; the budget assumes 8 dB.
- **Filtering:** RF BFCN-8350+ (8250–8450 MHz, IL 1.8 dB) + HFCN-7150+ high-pass. Typical data
  give ~20–24 dB at 6.05–6.75 GHz and ~19 dB at 6.65 GHz respectively → ~40 dB LO/image rejection
  **estimate**; 4.8 GHz image rejection is higher (HFCN-7150+ 39 dB at 4.54 GHz typ). Needs bench
  measurement. Cavity ZVBP-8250-S+ (USD 420) is the lab fallback.
- **IF filter:** 1.75–1.85 GHz band-pass, part TBD; must suppress LO (6.6 GHz) and 2×IF.

## Open items (must close before schematics)

1. LTC5552 upconversion CL, IIP3 and LO leakage at 8.4 GHz RF / 1.8 GHz IF — no tabulated data.
2. ADF4371 output power and phase noise at 6.6 GHz — interpolation between 5.7 and 8.0 GHz points
   (−112/−136 and −109/−133 dBc/Hz at 100 kHz/1 MHz) is **not** a specification.
3. Spur table for LO ± n·IF within 8.35–8.45 GHz (2nd–5th order) — not yet computed.
4. N310 phase behaviour after retune with internal LOs (random per run) — see clock doc.
