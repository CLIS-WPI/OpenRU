# H1 Risks and Exit Gate

Date: 2026-11-11. Baseline `p1-scientific-validation` @ `62c3668` (PR #1 unmerged — this branch depends on it).
Updated by H1.1 (component qualification) — see `H1_1_SCHEMATIC_ENTRY_GATE.md` for the full re-evaluation.

## Gate decision

| Gate | Status |
|---|---|
| Topology | **A (SIM-FAITHFUL) selected**; B kept as future option, not validated |
| H1 exit (commit `2589aec`) | NOT YET — blockers B1–B4 (historical record) |
| **H1.1 schematic entry** | **CONDITIONAL GO — PROTOTYPE envelope only** (ADAR1000 ×4 + ADTR1107 ×16, ≥ 10 dBm avg/feed). Conditions C1–C4 in `H1_1_SCHEMATIC_ENTRY_GATE.md`. No component is bench-qualified |
| Layout freeze (H2) | NO-GO until C1, C2 (and C4) close |
| PCB fabrication | **NO-GO** (unchanged) |

## Blockers (H1.1 status)

| ID | Risk | Evidence | Now blocks | Close by | Owner |
|---|---|---|---|---|---|
| **B1** | ADAR1000 procurement | Lifecycle "Recommended for New Designs" (official page per project lead; H1 "No Longer Manufactured" snippet superseded). ADI direct 16 business weeks; no authorised-distributor stock; no price; eval boards in ADI channel | **Fabrication / orders** | C1: ADI written lifecycle, lead time, quote ≥ 8 pcs | TBD (hardware lead) |
| **B2** | TX power vs sim | ADTR1107 12.3–14.3 dBm/feed (8–10 dB back-off from 23 dBm OP1dB) vs sim 18.9. **Correction:** QPA0813 OP1dB = 19 dBm (28.5 dBm is Psat) — the H1 discrete chain was ~5 dB *worse*, not better | PROTOTYPE: **resolved** by ≥ 10 dBm/feed envelope. SCALABLE: **open**, no qualified FE | C2 (prototype); vendor Q A6/B4 (scalable) | TBD (PI) |
| **B3** | Specs unverified at 8.4 GHz | ADTR1107 table covers 6–14 GHz (in spec). ADAR1000 data only ≥ 9.5 GHz; LTC5552 at 10 GHz; ADF4371 6.6 GHz not tabulated; ADTR1101 TX specified ≥ 8.5 GHz | **Qualification, layout freeze, fabrication** (not schematic entry) | C2, C4: eval-board bench data or manufacturer data at 8.35–8.45 GHz | TBD (RF lead) |
| **B4** | Energy model ≠ hardware | Prototype PA efficiency ~1.1% vs sim 0.25; tile 27.4 W TX | **No hardware gate.** P1 energy/energy-per-bit claims are simulation-only | C3: owner accepts re-scoping; optional single targeted model update after H1 | TBD (PI) |

## Major (non-blocking for schematics, blocking for PCB)

| ID | Risk | Evidence / note |
|---|---|---|
| M3 | N310 random inter-pair phase per run | Needs on-tile cal coupler network (L3 in clock doc) |
| M4 | LO/image filtering ~40 dB is an estimate | BFCN-8350+ and HFCN-7150+ typical data only; spur table not computed |
| M5 | Thermal density ~2.9 W/cm² behind aperture | needs heat spreader + forced air; ADTR1107 θJC not obtained |
| M6 | Antenna not designed | dual-pol patch, XPD, isolation, impedance at 17.845 mm pitch — openEMS work; topology A also routes 4 feeds per BFIC across 2 sites |
| M7 | ADTR1107 price | $126.47 @1k **not confirmed**; authorised prices seen $134.78–$195.69 (1k quotes elsewhere $109.97–$166.85, unverified) |
| M8 | QPA0813 | Preliminary datasheet; OP1dB 19 dBm (Qorvo table) vs distributor "P1dB 28.5" mislabel; **not qualified for OFDM** |
| M9 | Topology A shares one waveform across V/H per chain | rank ≤ 4 per tile; P1-C simulated 590 vs 676 Mbps — simulation only |
| M10 | QPX0252 export status | Page snippet "ITAR Restricted: Yes" + "ECCN: EAR99" — contradictory; no QPX0252 data in the open repo until the university export-control office rules |
| M11 | No linearity data for any candidate FE | All back-off figures are assumptions until C2 |

## Regulatory boundary

8400–8450 MHz is allocated (US) to FIXED and SPACE RESEARCH (deep space)(s-E); footnote 5.465:
"the use of the band 8400-8450 MHz is limited to deep space"; 8.35–8.40 GHz sits under US258/G117
(EESS, military FSS/MSS). **No OTA transmission.** All H1/H2 testing is cabled, attenuated, terminated or
shielded unless an experimental licence is obtained. 5G UE demonstrations use a separate sub-6 GHz path.

## Stop rule

H1/H1.1 end with this package. No broad suite reruns, no new PHY algorithms, no H2 layout, no purchases,
no external communication without approval. The one permitted targeted simulation (A vs B) is **not
needed**: topology A was chosen by direct correspondence to the existing feed map.
