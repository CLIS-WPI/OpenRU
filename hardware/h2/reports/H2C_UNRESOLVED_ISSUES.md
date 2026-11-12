# H2-C Unresolved-issues register

Supersedes `H2B_UNRESOLVED_ISSUES.md`.

**Status values:**
- **CLOSED** — drawn and checked against a datasheet;
- **PARTIAL** — drawn, with values derived or evidence preliminary;
- **OPEN** — not done.

## Safety blockers (see H2C_HARDWARE_SAFETY_REVIEW.md §5)

| ID | Item | Status |
|---|---|---|
| B-S1 | ADAR1000 OFF-bias values vs ADTR1107 VGG abs max (firmware limit only) | OPEN (ADI) |
| B-M5a/b | BAT54C clamp current: PG_3V3RF up to 0.66 V and PA_DRAIN_EN 0.8–0.97 V under pessimistic logic | OPEN (redesign) |
| B-TD | TPS386000 detection delay unspecified | OPEN (bench / part change) |
| B-TOFF | TPS22810 tOFF max unspecified; crowbar break-before-make margin 2.5 µs worst | OPEN (bench) |
| B-PA0 | PA current at 0 V gate and ADTR1107 transient SOA | OPEN (ADI / bench) |
| B-ADAR | ADAR1000 PA_BIAS behaviour during AVDD3 collapse | OPEN (ADI) |
| B-INDUCT | L650/L651 MPN and footprint; +5V_PA load-step overshoot vs 5.5 V | OPEN |

## Electrical items

| Item | Status | Note |
|---|---|---|
| Regulators (H2-A U11–U18) | **PARTIAL** | Drawn from TI datasheets. Open sub-items: inductor MPNs, DC-bias derating of output capacitors, TPS7A33 soft-start choice (CNR 100 nF → 120 ms) |
| NEG_OK monitor (U19 / S2) | **PARTIAL** | Independent interlock drawn, but not proven under pessimistic logic (B-M5, B-TD) |
| Rail ordering (S4) | **CLOSED (hardware)** | ENN = PWR_EN_NEG · PG_3V3RF. SIM-BEHAV shows AVDD3 before AVDD1 and VDD_SW before VSS_SW in all orderings |
| ADAR1000 / ADTR1107 decoupling (U2, U5) | **PARTIAL** | Stingray per-tile sets; per-pin values undocumented; 0402 instead of 0201; MPNs for 10 V parts not selected |
| MCU decoupling (U24) | **CLOSED** | ST DS12589 Fig 16; VBAT value undocumented (OPEN) |
| MCU pin map (U23) | **CLOSED** for the listed pins (DS12589, ST pin database) | Caveats: PA9 should use TIM2_CH3; PC13/PC14 sink-only; PA15/PB3/PB4 JTAG at reset; USB-C dead-battery pins (PB4/PB6, PA9/PA10) behaviour at reset OPEN (RM0440) |
| INA226 straps (U21) | **CLOSED** | Duplicate address fixed (U610 → 0x42) |
| PCA9306 (U22) | **CLOSED** | 100 pF added; VREF1 ≤ VREF2 − 0.6 V met |
| ADF4371 loop filter (U8) | **PARTIAL** | DERIVED; ngspice AC cross-check; ADIsimPLL unavailable |
| ADF4371 RS_SW | OPEN | ERC #1 |
| LNA debias / TX isolation (S3) | OPEN | bench |
| VGG_PA 10 nF vs switching speed (S6) | OPEN | ADI |
| Footprints for custom parts (U1, U3, U7, U10); TPS386000 RGP pad size | OPEN | vendor land patterns |
| Antenna / thermal | OPEN | separate work packages |
