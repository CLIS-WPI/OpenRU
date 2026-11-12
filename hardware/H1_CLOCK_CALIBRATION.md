# H1 Clock, Control and Calibration

Status: interface definition for schematics entry. Not validated. PCB NO-GO.

## 1. Reference and LO tree

```
10 MHz + PPS (lab reference) ─┬─► N310 REF/PPS in          (N310: ext 10 MHz and PPS in/out supported)
                              └─► 100 MHz VCXO (PLL-locked) ─► ADF4371 REF (10–500 MHz SE accepted)
                                                              └─► RF8x 6.6 GHz ─► buffer ─► 1:4 split ─► LTC5552 ×4
```

- One LO for all four tile chains → the converter adds only a **static** per-chain phase (trace +
  splitter + mixer), calibratable once per temperature point.
- **N310 limitation (verified):** "The N310 itself has no way of aligning phase between channels, and
  phase will be random between runs" (UHD N3xx manual). Its 4 channels are 2 AD9371 pairs; LO sharing
  is only within a pair. External-LO mode limits operation to 300 MHz–4 GHz and leaves a 180°
  ambiguity. **Consequence: chain-to-chain IF phase must be re-measured at every N310 start/retune.**
  This is a property of the bench digital core, not of the tile.
- N310 REF/PPS electrical levels: **UNVERIFIED** (Ettus KB unreachable) — confirm before choosing the
  distribution buffer.

## 2. Calibration layers

| Layer | What varies | When | Method (proposed) | Requirement |
|---|---|---|---|---|
| L1 feed-to-feed in BFIC | ADAR1000 ch1–4 + ADTR1107 + feed trace, incl. V/H relative phase per site | factory/bench, per temperature point | cabled VNA or reference RX per feed; store gain/phase offsets in MCU table; ADAR1000 step 2.8° → quantisation 0.81° rms | ≤ 5° rms, ≤ 0.3 dB rms (R-RF-9) |
| L2 chain-to-chain (converter) | IF filters, mixers, LO split, RF traces | bench, per temperature point | inject common tone at RF port of each chain; compare at N310 | ≤ 2° rms (R-RF-10) |
| L3 N310 runtime | AD9371 pair phases (random per run) | **every N310 start/retune** | cal coupler on each of RF0..RF3 → 4:1 combiner → CAL SMA; loop-back one TX through CAL into all 4 RX, then each TX into one RX | same |
| L4 drift | temperature | runtime | ADAR1000 temp sensor (8-bit, 0.8 LSB/°C) + table interpolation | TBD from bench |

Power monitoring (not phase): ADTR1107 CPLR_OUT (coupling 28 → 18 dB over 6–18 GHz) → ADAR1000 DET1–4
(−20…+10 dBm, specified at 11.5 GHz). Detectors give amplitude only; **they cannot do phase calibration**.

**Design decision required in H2:** include the L3 cal coupler/combiner network on the tile (adds
loss ~0.2–0.5 dB per chain, assumed) or do L3 externally with cabled splitters on the bench.
Recommendation: on-tile couplers; without them, the N310 bench system cannot be phase-coherent.

## 3. Control interface (MCU ↔ 4 × ADAR1000)

| Signal | Count | Notes | Source |
|---|---|---|---|
| SCLK, SDIO, SDO, CSB | 1 bus | 4-wire SPI ≤ 25 MHz; one bus serves all 4 chips | ADAR1000 Table 2 p.9 |
| ADDR0, ADDR1 | strapped per chip | selects 1 of 4 chips on shared bus; broadcast write supported | ADAR1000 p.10 |
| TR | 1 shared | TX/RX state; 180 ns switching | p.7 |
| TX_LOAD, RX_LOAD | 1 each, shared | synchronous beam latch across 4 chips (20 ns) — satisfies R-CTL-2 | p.7, p.28 |
| PA_ON | 1 shared, through safety AND gate | gate with WDOG_OK and RF_MUTE (block diagram) | pin B3 p.12 |
| PA_BIAS1–4 | per chip → 4 × ADTR1107 VGG_PA | OFF ≈ −2.5 V (0x85), ON ≈ −1.1 V (0x39) → 220 mA | p.44–45 |
| LNA_BIAS | per chip → 4 × ADTR1107 | single DAC | p.7–8 |
| TR_SW_POS/NEG | per chip → ADTR1107 CTRL_SW | | p.8 |
| Beam memory | 121 positions + 7 bias settings per direction | allows TDD beam switching without SPI traffic | p.32 |

TDD timing: ADAR1000 TR 180 ns, ADTR1107 switch 10 ns + 17 ns settling. Sim assumes 12 µs
(`rf_settling_time_us`); hardware is ~2 orders faster, so the sim assumption is conservative. The PA
gate-bias swing (−2.5 → −1.1 V) settling under load is **not** tabulated and must be measured.

## 4. Safe states (R-SAF-1..3)

- ADTR1107 power-up sequence (Rev C p.24): VDD_SW → VSS_SW → CTRL_SW 0 → VGG_LNA 0 → VDD_LNA 0 →
  **VGG_PA −1.75 V before VDD_PA 5 V** → raise VGG_PA to bias → RF. Power-down reverses with RF off first.
  Hardware sequencer must enforce this; firmware alone must not be able to apply VDD_PA with VGG_PA
  undefined (ADTR1107 VGG_PA abs. range −2…0 V).
- ADAR1000 needs AVDD1 = −5 V present for its PA_BIAS DACs; loss of −5 V must remove VDD_PA.
- MCU reset / watchdog expiry → PA_ON low and VDD_PA disabled by hardware, independent of SPI state.
- Missing/frozen temperature or current reading (no change for N samples, out of range, or SPI
  read-back mismatch) → TX inhibit. Thresholds come from bench data, not from P1-E simulation (which
  showed 58.3% false alarms on healthy sensor-fault cases).
