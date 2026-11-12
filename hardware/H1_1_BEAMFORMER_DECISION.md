# H1.1 Beamformer Decision

Date: 2026-11-11. Baseline `2589aec`. Topology A unchanged. Provisional — not an approved design. PCB NO-GO.

Evidence tags: **OFFICIAL** = manufacturer document read in full (incl. ADI-authored PDF from a mirror,
revision stated); **OFFICIAL\*** = manufacturer page seen only as a search-engine summary (analog.com and
qorvo.com timed out / HTTP 429 for automated access throughout H1.1 — not bypassed); **DISTRIBUTOR**;
**DERIVED** = arithmetic from tagged values; **ASSUMPTION**.

## Decision

| Role | Part | Status |
|---|---|---|
| **Preferred** | **ADI ADAR1000** (4 per tile) | Selected for prototype schematic entry. **Not qualified at 8.4 GHz** (no manufacturer data below 9.5 GHz). |
| Fallback | Qorvo QPX0252 | **Not a candidate yet.** Blocked by export-control ambiguity, no published RF specifications, Preview lifecycle, and unresolved common-port architecture. Re-evaluate only after the vendor and university export-control questions in `H1_1_VENDOR_QUESTIONS.md` are answered. |

There is no qualified fallback today. If ADAR1000 procurement fails, the topology analysis reopens.

## 1. ADAR1000 — lifecycle vs availability

| Item | Finding | Tag |
|---|---|---|
| Lifecycle | "Recommended for New Designs" on analog.com/en/products/adar1000.html | OFFICIAL\* (reported by project lead from the live page; our fetch only saw the search summary, which agrees). **The H1 "No Longer Manufactured" snippet is superseded.** |
| ADI direct | Sample/buy: "View Price in Cart / Request Quote", **ships in 16 business weeks**; 1ku price "unavailable" | OFFICIAL\* |
| Authorised distributors | Digi-Key: IC not listed. Findchips: ADI channel 0, Richardson RFPD 0. Mouser/Arrow unreachable | DISTRIBUTOR |
| Brokers | Win Source $3,545.45; Vyrian, Chip Stock, Shengyu quantities without price | DISTRIBUTOR (unauthorised — **counterfeit risk; do not buy**) |
| Eval: ADAR1000-EVALZ | ADI channel 11 in stock, $1,745.70 (Findchips); Digi-Key "Discontinued at DigiKey", 0 stock | DISTRIBUTOR |
| Eval: ADAR1000EVAL1Z (Stingray, 8×ADAR1000 + 32×ADTR1107) | ADI channel 49 in stock, $39,929.73 | DISTRIBUTOR |
| SystemVue / S-parameters / IBIS | **Not determined** — design-resources page unreachable | — |
| 8.0–8.5 GHz data | **None found.** Rev B Table 1 gives 9.5/11.5 GHz only; operating range 8–16 GHz; gain flatness ±1.7 dB over 8–15 GHz | OFFICIAL (Rev B, mirror) |

**Conclusion:** official lifecycle supports design-in. "Obtainability of 4–8 parts" is **plausible via ADI
direct (16-week quote)** but **not confirmed** — no authorised channel shows stock, and no price was obtained.
Evaluation hardware (ADAR1000-EVALZ, 11 pcs at ADI) is the fastest path to 8.4 GHz data.

## 2. ADAR1000 vs QPX0252

| Criterion | ADAR1000 | QPX0252 |
|---|---|---|
| Band | 8–16 GHz (OFFICIAL) — 8.4 GHz is 0.4 GHz above the lower edge | 7.9–12 GHz (OFFICIAL\*/trade press) — 8.4 GHz well inside |
| Signal flow | 4 paths ↔ **one common RF_IO**, passive 4:1 split/combine (OFFICIAL) | 4 antenna paths; "single-beam Tx, dual-beam Rx" (OFFICIAL\*). Number of common ports **unknown**; header text "Quad Tx/Rx" conflicts with title |
| Topology A fit | **Exact**: 1 chip = 1 RF chain = V+H at 2 sites | TX fits. RX "dual beam" implies 2 Rx common ports per chip → would *add* a second receive beam per chain; harmless to topology A if one port is unused, but changes converter count if used. Unresolved |
| Phase / gain | 2.8° step (360°); ≥31 dB gain range, 0.5 dB steps (OFFICIAL) | 6-bit phase (5.625°), 6-bit gain (0.5 dB) (OFFICIAL\*) — both meet R-RF-8 (≥5 bits) |
| TX gain / OP1dB / Psat | 21 dB / **10 dBm** / 14 dBm @ 9.5 GHz (OFFICIAL Rev B Table 1). A search summary gives ~14 dBm "OP1dB" — likely the Psat row; **H1.1 uses 10 dBm** | Not published. Vendor claim: drives QPF5012 FEM "without external drivers" (trade press) |
| RX gain / NF | 10 dB single-channel / 8 dB @ 9.5 GHz (OFFICIAL Rev B; a summary says ~10 dB NF — conflict, recheck) | Not published |
| Power | 3.3 V × 350 mA TX / 260 mA RX per chip; −5 V for bias DACs (OFFICIAL) | 1.8 V core, 3.0 V Tx PA (OFFICIAL\*); consumption not published |
| Control | SPI 25 MHz, 4 chips per bus (ADDR0/1), TX_LOAD/RX_LOAD latch, 121-beam memory, 4×PA_BIAS + LNA_BIAS DACs, TR_SW outputs, temp sensor, 4 detectors (OFFICIAL) | SPI, "fast beam steering", "quiet mode", "Zero-Cal", bias/sequencing/telemetry via companion Qorvo bias ICs (OFFICIAL\*) |
| Calibration | No built-in calibration; external tables (OFFICIAL\*) | "Zero-Cal" claim, not specified |
| Support ICs for FEM | **None**: glueless to ADTR1107 (ADI Stingray reference, OFFICIAL developer.analog.com) | Companion gate-bias, drain-bias, switch-control ICs ("sampling") |
| Package | 88-terminal 7×7 mm LGA (OFFICIAL) | FC-CSP, size/pitch unknown — flip-chip CSP likely needs finer PCB rules than LGA (ASSUMPTION) |
| Availability | RFND; ADI direct 16 wk; eval boards in ADI stock | Preview; samples + dev kit (QPX0252-DL) announced 2026-10-02 "available immediately" (trade press); no distributor listing; no price |
| Export / openness | Distributed commercially; public datasheet and Linux/pyadi-iio drivers | Page snippet shows **"ITAR Restricted: Yes" and "ECCN: EAR99"** — contradictory; **must be resolved by the university export-control office before any QPX0252 data enters this open repository** |

## 3. What ADSY2301 tells us (reference only)

ADSY2301 (pre-release, Rev PrB preliminary datasheet, OFFICIAL\*) is a **16-element single-polarised 4×4**
tile: 4×ADAR1000 each driving a 2×2 quadrant, ADTR1101 front ends, no frequency conversion on the tile,
8–11 GHz, Tx Psat 2–4 W per element, 180 ns T/R switching. It confirms ADI pairs ADAR1000 with
ADTR1101 for higher power. It does **not** transfer to OpenRU's mapping: in ADSY2301 one BFIC feeds 4
co-polarised elements; in topology A one BFIC feeds V+H of 2 sites. OpenRU keeps topology A.
No schematics, BOM, lattice spacing, calibration method, clock/LO or thermal data are public
(enquiries to SystemOnModules@analog.com). Bias sequencing is taken from the **Stingray** board
(OFFICIAL, developer.analog.com): program ADAR1000 PA_BIAS to pinch-off **before** +5 V is enabled.
