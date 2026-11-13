# FIXTURE_BOM notes — H2-E Candidate-A test fixture

- **Date:** 2026-11-12. Research only: nothing ordered, no accounts, no one contacted, KiCad files untouched, nothing committed.
- **Input:** `FIXTURE_PARTS.csv` (73 lines), `FIXTURE_DESIGN.md`, `../design/h2e/BENCH_PROCEDURES.md` §7 (EVMs).
- **Output:** `FIXTURE_BOM.csv`. All prices are **indicative** and in USD, at the smallest available price break (qty 1–10 or the distributor MOQ, as given in `price_qty`).

## Method

1. **MPN existence:** checked against the manufacturer page or datasheet ordering table where reachable (TI datasheets and product pages, onsemi, Panasonic model pages, Vishay and Yageo datasheets). Otherwise checked against a distributor page that shows the exact MPN, mostly LCSC product pages.
2. **Package against footprint:** every KiCad footprint named exists in the installed KiCad library (`/usr/share/kicad/footprints`). For the TI ICs, the datasheet drawing ID was matched to the footprint: RGE0024H, DRC0010J, DRV0006A, DSE0006A and DQK. For RGE0024H, the 2.7 mm thermal pad land was also checked against `EP2.7x2.7`. Land dimensions were not re-measured for the other ICs.
3. **Stock and price:**
   - **ti.com product pages:** the embedded orderable-part data gives the tiered price, marketing status and schema.org availability.
   - **LCSC public product pages:** read for stock and price ladder.
   - **Finding the LCSC C-number:** web search.
4. **Lifecycle:** taken from ti.com, the onsemi product pages, and the Panasonic datasheet (series status). For the Murata parts it comes from aggregator flags quoted in web-search summaries, which are second-hand and sometimes stale.

## Sources that refused or gave nothing (not bypassed)

- **Returned 403 or a bot wall:**
  - Distributors: Digi-Key, Mouser, Octopart, Newark/Farnell, TME, OEMsecrets, Future, TTI, Digipart, Allied, Win-Source.
  - Manufacturers: keyelco.com, phoenixcontact.com, amphenolrf.com.
- **Loads but shows no results without JavaScript:** Findchips, which now returns no distributor results to non-browser clients. murata.com and the Yageo search results are also JavaScript-only.
- **Error:** samsungsem.com returned HTTP 500.
- **Not used:** LCSC's JSON search API. Access was denied, so it was left alone.

## Totals (fitted parts only, DNP excluded)

| | 1 board | 3 boards |
|---|---|---|
| Parts, indicative | $54.18 | $162.55 |
| 3-board purchase including distributor MOQ | — | $172.17 |
| PCB fabrication / assembly | NOT QUOTED | NOT QUOTED |

- **Lines not costed:** the Würth headers J3–J5 and J9–J11, Vishay RCS12061R00FKEA (R65–R70) and Vishay WSK2512R0100FEA (RS1–RS3). No reachable source showed a price for them.
- **Estimated prices:** about $5.22 per board of the total uses EST prices. These are the 15 Panasonic ERA-3AEB values with no LCSC listing, priced at a sibling's $0.12, plus RC0603FR-079K09L and both RC2512 values.
- **Effect on the real total:** expect it to be higher. Most of the gap is the WSK2512 shunts and the RCS anti-surge resistors.

## EVMs (ti.com tool pages, list price)

| EVM | Price |
|---|---|
| TPS16630-32EVM | $108.90 |
| TPS3703Q1-A4120EVM | $27.50 |
| TPS3430EVM | $31.90 |
| **Total** | **$168.30** |

Inventory on these pages is rendered client-side, so EVM stock is UNVERIFIED.

## Changes proposed (value and rating unchanged)

| Ref | Was | Proposed | Reason |
|---|---|---|---|
| C1 | GRM188R71E105KA12D | Samsung CL10B105KA8NNNC | EOL (aggregators) |
| C2–C4 | GRM188R61A475KE15D | Samsung CL10A475KP8NNNC | obsolete |
| C5 | GRM31CR71A106KA01L | Samsung CL31B106KPHNNNE | obsolete, no stock |
| C10 | GRM188R71H104KA93D | Samsung CL10B104KB8NNNC | EOL (LTB 2019), LCSC 0 |
| C33 | CL05B105KP5NNNC | Murata GRM155Z71A105KE01D | MPN not found anywhere. Samsung lists only X6S (CL05X105KP5NNN#) for 1 µF 10 V 0402. Samsung's site failed, so this is not fully proven. |
| J2 | Phoenix 1714971 | Phoenix 1711725 | 1714971 is MKDS 5/ 2-9,5 (9.52 mm pitch) and **does not fit** the MKDS-3 5.08 mm footprint. MKDS 3/ 2-5,08 is 1711725. |
| R55, R56 | ERA-3AEB1002V | ERA-3AEB103V | Code does not exist. Per the Panasonic datasheet, E24 values must use the 3-digit code. |

- **Samsung substitutes:** their DC-bias derating differs from Murata's. Re-check the effective capacitance wherever it matters, for example C1 and C2–C4.
- **C6–C9 (DNP):** GRM32ER61A476KE20L is NRND and out of stock. No identical 10 V / 10 % replacement is in stock, so it is left for the designer.

## Unverified / blocking

- **U10 TPS16630RGER: build blocker.** Out of stock at ti.com and LCSC. The same-package alternates RGERG4 and RGET are also out of stock at ti.com. The PWP (HTSSOP) variant is in stock but needs a different footprint, so it is not substituted. Digi-Key and Mouser could not be checked.
- **R58 ERA-3AEB1011V (1.01 k): build blocker.** This is an E192 value, which Panasonic supplies only on inquiry. It is not a catalog part (the model page returns 404). The designer has to decide: ask Panasonic, find another 0.1 %/25 ppm 0603 source (Susumu RG1608P-1011-B-T5 is plausible but unverified), or move to an E96 value.
- **U1, U2 TPS7A2550DRVR / TPS7A2518DRVR:** active, but out of stock at ti.com and not listed on LCSC.
- **TP23, TP24 Keystone 5001:** LCSC stock is 0. Any black miniature loop fits the footprint.
- **Stock unverified (part exists, no reachable stock source):**
  - Panasonic: the remaining ERA-3AEB values.
  - Yageo: RC0603FR-079K09L, RC2512FK-0744R2L and RC2512FK-0749R9L. Their exact MPN existence is also unverified.
  - Vishay: RCS12061R00FKEA and WSK2512R0100FEA.
  - Würth: 6130xx11121 headers.
  - Phoenix: 1711725.
- **Thin LCSC stock:** TPS3703A7330DSER (37 in stock, 6 needed for 3 boards), TPS3430WDRCR (10 at LCSC, but in stock at ti.com) and BAS116LT1G (5040).

## Long-lead / risk parts

- **TPS16630RGER:** no stock found anywhere checked.
- **TPS7A25 fixed-voltage options:** no stock found anywhere checked.
- **ERA-3AEB thin-film values (18 values):** usually built to order. Expect factory lead times; check Digi-Key or Mouser by hand.
- **WSK2512R0100FEA:** a 4-terminal Kelvin shunt with no LCSC listing.
- **GRM155R71H223KA12D:** distributors quote a 17–24 week factory lead, but LCSC has 337k in stock.

## Footprint notes

- **WSK2512:** KiCad's `T1.19mm` is the terminal length T for the 0.005–0.2 Ω range, so it is correct for 10 mΩ. The body height is H = 0.635 mm.
- **Datasheet URL:** the parts list uses the 1x2 header datasheet URL (61300211121.pdf) for the 1x10 and 1x6 headers, and that URL returned 404.

## H2-E.1 update (2026-11-12)

- **Schematic MPN fields synced.** The 7 CHANGED lines (C1, C2–C4, C5, C10, C33, J2, R55/R56) and TP10–TP24 now match
  this BOM. `tools/check_bom_sync.py out/candA_fixture.xml FIXTURE_BOM.csv` reports 0 mismatches.
- **A-SENSE:**
  - U4 is now **TPS3703A7120DSERQ1**: ti.com InStock, $1.151, qty break UNVERIFIED.
  - R10/R11 are now 3.16 k / 1.00 k (ERA-3AEB3161V / ERA-3AEB102V).
  - **D1 BAS116 is removed.**
  - U3 keeps TPS3703A7330DSER: ti.com OOS, LCSC 37, so 3 are needed for 3 boards.
- **R58:**
  - **No stocked 1.01 k source exists.** It is an E192 value; KOA RN73R1JTTD1011B25, Vishay TNPW06031K01BEEA and
    Stackpole RNCF0603BTE1K01 list it as standard, but no stock was visible.
  - **Applied:** R57/R58 are now 18.0 k / 2.00 k (ERA-3AEB183V / ERA-3AEB202V), same k = 0.1. Revalidation is in
    `../design/h2e1/h2e1_checks.py`.
- **U10:**
  - TPS16630RGER, RGERG4, RGET and PWPR are still OOS.
  - **TPS16630PWPT (HTSSOP-20) is InStock** ($2.428) and electrically identical per SLVSET9G; only the thermal figures
    differ.
  - It is not drawn: it needs a new symbol and footprint, to be done together with the layout approval.
  - TPS16632 and TPS16637 are not equivalent (their OVP differs).
- **New stock flag:** TLV3201AIDBVR (U9, U11) is 0 at ti.com; LCSC is in stock.
- **Totals (by delta, indicative):** $52.16 per board, $156.50 for 3 boards, $165.74 for 3 boards incl. MOQ. Lines that
  are still not costed are unchanged.
