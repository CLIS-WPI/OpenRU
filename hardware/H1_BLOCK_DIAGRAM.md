# H1 Block Diagram — Topology A (SIM-FAITHFUL)

Status: architecture sketch, **not a schematic. PCB FABRICATION NO-GO.**

## Decision

Topology **A** is selected: 1 RF chain → 1 ADAR1000 → {V,H} × 2 adjacent sites. It reproduces the
simulated tile-0 feed ownership exactly (`H1_FEED_POLARIZATION_MAP.csv`, checked against
`openru_x6/rf.py::build_feed_map` by `tests/unit/test_h1_feed_map.py`), so P1 evidence applies to it
without a new simulation. Topology B (2 chains V-only, 2 chains H-only) stays a documented future
option; it is **not** validated by P1 and needs one targeted A-vs-B run before it could be adopted.

## Signal path (one tile)

```
            10 MHz / PPS in ──► clock distribution ──► LO PLL ──► LO splitter/driver ─┐
                                      │                                           │ ×4
USRP N310 (bench only)                ▼                                           ▼
 TX IF0..3 ──► IF filter/amp ──► mixer ──► RF BPF ──► TX/RX switch ─┐
 RX IF0..3 ◄── IF filter/amp ◄── mixer ◄── RF BPF ◄── LNA ◄─────────┘   (per chain, ×4)
                                                       │
                                               RF0..RF3 @ 8.4 GHz
                                                       │
            ┌──────────────┬──────────────┬────────────┴─┬──────────────┐
            ▼              ▼              ▼              ▼
        U_BF1 (RF0)    U_BF2 (RF1)    U_BF3 (RF2)    U_BF4 (RF3)    ADAR1000 ×4
        ch1 ch2 ch3 ch4  ...                                       (common RF_IO per chip)
         │   │   │   │
       FE1 FE2 FE3 FE4 ... FE16                                    T/R front end ×16
         │   │   │   │
       s0V s0H s1V s1H  (row 0, cols 0–1)   ... see CSV            8 dual-pol sites
```

ADAR1000 channel convention (all four BFICs): ch1 = left site V, ch2 = left site H,
ch3 = right site V, ch4 = right site H. Chains 0,1 own the lower site row; chains 2,3 the upper
(sim `z` ordering).

## Control / safety path (independent of RF data)

```
host ──USB/Eth──► MCU ──SPI(+level shift)──► U_BF1..4  (write → read back → compare)
                   │ ──GPIO BEAM_LATCH ─────► U_BF1..4  (shared edge)
                   │ ◄─ ADC: rail currents, temps, detector couplers
                   │ ── watchdog kick ──► HW watchdog ─┐
N310 GPIO ── TR ───┼───────────────────────────────────┼─► TR switch / ADAR1000 TR pin
                   └── TX_EN ──► AND ◄── RF_MUTE (hardware, e.g. front-panel/interlock)
                                 │  ◄── WDOG_OK ◄────────┘
                                 └──► PA drain/gate enable (default OFF)
```

TX can only be enabled when MCU TX_EN **and** watchdog OK **and** hardware mute released are all
true. A frozen MCU, missing sensor or reset leaves PA gates pinched off (R-SAF-1..3).

## What topology A costs (must be carried to the risk register)

1. **Shared waveform on V and H.** Each chain radiates one waveform on both polarisations of its two
   sites; per-chain V/H relative phase is set only by ADAR1000 analog weights. Polarisation then
   acts as a beam-shaping degree of freedom, not an independent MIMO layer. Useful rank per tile is
   bounded by **4 chains**, not 8 polarised streams. P1-C (Jones/XPD model, simulated) gave 590 vs
   676 Mbps against the simple reference — this is the sim's estimate of that cost, not chamber data.
2. **Per-chain power is split 4 ways** (−6.0 dB to each feed before front-end gain). The RF_IO
   splitter loss inside ADAR1000 adds to this; see cascade budget.
3. **Calibration** has two layers: chain-to-chain (IF + mixer + LO path, 4 paths) and
   feed-to-feed within each BFIC (16 paths), including V/H relative phase per site.
4. **Feed routing:** each BFIC must reach two adjacent sites (4 feeds, ~36 mm span) with matched
   electrical length; V and H feeds of one site must be routed without crossing the other port's
   isolation keep-out.
