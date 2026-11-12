# H1 Risks and Exit Gate

Date: 2026-11-11. Baseline `p1-scientific-validation` @ `62c3668` (PR #1 unmerged — this branch depends on it).

## Gate decision

| Gate | Status |
|---|---|
| Topology | **A (SIM-FAITHFUL) selected**; B kept as future option, not validated |
| **H1 EXIT → schematics** | **NOT YET — blocked by open blockers B1–B4**. Clears to CONDITIONAL GO only when every blocker has an owner-accepted resolution |
| PCB fabrication | **NO-GO** (unchanged) |

## Blocking risks

| ID | Risk | Evidence | Resolution path | Owner |
|---|---|---|---|---|
| **B1** | ADAR1000 may not be procurable | No Digi-Key listing; ADI channel stock 0; broker-only ($3,545); one snippet says "No Longer Manufactured" (unconfirmed) | Confirm lifecycle + lead time directly with ADI/sales. If NRND: evaluate an 8.4-GHz-capable alternative BFIC (none identified in H1; MACOM MAMF-011015 8–11 GHz core chip at $266 is a partial candidate) — **this would reopen the topology analysis** | TBD (hardware lead) |
| **B2** | Front end cannot deliver the sim's per-feed power | ADTR1107: 12.3–14.3 dBm avg at feed vs 18.9 dBm sim → **−4.6 to −6.6 dB** (`H1_RF_CASCADE_BUDGET.csv`). Discrete QPA0813: −0.1 to −2.1 dB but needs ~0 dBm drive (above ADAR1000 linear range) and has no 8.4 GHz data | Choose one: (a) accept lower EIRP and record a model–hardware gap against P1; (b) adopt discrete PA + driver stage; (c) DPD to reduce backoff (out of H1 scope). Do **not** re-run P1 inside H1 | TBD (PI) |

| **B3** | Key RF specifications are unverified at 8.4 GHz | ADAR1000 data at 9.5 GHz (band edge 8 GHz); ADTR1107 6–14 GHz table; LTC5552 at 10 GHz; QPA0813 ≥ 8.5 GHz; ADF4371 output at 6.6 GHz not tabulated | Bench-characterise eval boards (ADAR1000/ADTR1107, LTC5552, QPA0813) at 8.35–8.45 GHz, or obtain manufacturer 8.4 GHz data | TBD (RF lead) |
| **B4** | Energy model does not match hardware | Effective PA efficiency ~2% at required backoff vs sim `pa_efficiency` 0.25; tile ~27 W TX vs sim RF portion (`H1_POWER_THERMAL.md` §2–3). All P1 energy/energy-per-bit conclusions are model-only | Owner decides whether P1 energy claims are re-scoped or a single targeted model update is authorised after H1 (not inside H1) | TBD (PI) |

## Major (non-blocking for schematics, blocking for PCB)

| ID | Risk | Evidence / note |
|---|---|---|
| M3 | N310 random inter-pair phase per run | Needs on-tile cal coupler network (L3 in clock doc) |
| M4 | LO/image filtering ~40 dB is an estimate | BFCN-8350+ and HFCN-7150+ typical data only; spur table not computed |
| M5 | Thermal density ~2.9 W/cm² behind aperture | needs heat spreader + forced air; θJC not extracted |
| M6 | Antenna not designed | dual-pol patch, XPD, isolation, impedance at 17.845 mm pitch — openEMS work; topology A also routes 4 feeds per BFIC across 2 sites |
| M7 | ADTR1107 price | $126.47 @1k **not confirmed**; lowest authorised seen $134.78–$195.69 → ≥ $2,157–3,131 per tile |
| M8 | QPA0813 preliminary datasheet, 26-week lead time, 8–11 vs 8.5–10.5 GHz range conflict | |
| M9 | Topology A shares one waveform across V/H per chain | rank ≤ 4 per tile; P1-C simulated 590 vs 676 Mbps — simulation only |

## Regulatory boundary

8400–8450 MHz is allocated (US) to FIXED and SPACE RESEARCH (deep space)(s-E); footnote 5.465:
"the use of the band 8400-8450 MHz is limited to deep space"; 8.35–8.40 GHz sits under US258/G117
(EESS, military FSS/MSS). **No OTA transmission.** All H1/H2 testing is cabled, attenuated, terminated or
shielded unless an experimental licence is obtained. 5G UE demonstrations use a separate sub-6 GHz path.

## Stop rule (kickoff §7)

H1 ends with this package. No broad suite reruns, no new PHY algorithms, no H2 layout. The one
permitted targeted simulation (A vs B) is **not needed**: topology A was chosen by direct
correspondence to the existing feed map.
