# H1 Power and Thermal (first pass)

Status: datasheet-quiescent arithmetic. **Not a measurement.** Rev10/P1 abstract power figures
(`configs/power.yaml`) are **not** carried over as hardware specs. PCB NO-GO.

## 1. Per-tile DC power by state (topology A)

| Block | Basis | TX state (W) | RX state (W) | Source |
|---|---|---|---|---|
| 16 × ADTR1107 PA | 5 V × 220 mA quiescent each | 17.6 | ~0 (PA_BIAS → OFF in RX) | ADTR1107 Rev C Table 1; selection-guide box "5 V at 220 mA (PA)" |
| 16 × ADTR1107 LNA | 3.3 V × 80 mA each | ~0 | 4.2 | ADTR1107 Rev C Table 3 |
| 4 × ADAR1000 | 3.3 V × 350 mA (TX) / 260 mA (RX) each | 4.6 | 3.4 | ADAR1000 Rev B p.8 (selection guide: 300/200 mW per channel — consistent) |
| ADF4371 | 3.3 V × 190 mA + 5 V × 135 mA + RF8 out ~0.2 W | 1.5 | 1.5 | ADF4371 Rev 0 p.4 (RF8 output current 25–65 mA → estimate) |
| 4 × LTC5552 | 3.3 V × 132 mA each | 1.7 | 1.7 | LTC5552 datasheet |
| LO buffer, IF amps, switches, MCU, monitors, VCXO | engineering allowance | 2.0 | 2.0 | ASSUMPTION |
| **Tile total** | | **27.4** | **12.8** | |
| TDD average (DL fraction 0.75, sim) | 0.75·TX + 0.25·RX | **23.8** | | `configs/radio.yaml` `tdd_dl_fraction` |

Not included: PA drain current rise under RF drive, regulator/DC-DC conversion loss (typically
10–20%), fan, digital core. Real numbers will be **higher**.

**Cost-down front end** (QPA0813 5 V × 140 mA + PMA3-14LN+ 6 V × 67 mA): 16 branches ≈ 11.2 W TX /
6.4 W RX → tile ≈ 21.0 W TX / 15.0 W RX / 19.5 W TDD avg. Lower in TX, higher in RX.

## 2. Efficiency — the sim assumption is not supported

RF output at the feeds (ADTR1107, 8–10 dB backoff): 16 × 12.3–14.3 dBm ≈ **0.27–0.43 W** per tile.
PA DC alone in TX = 17.6 W → effective drain efficiency ≈ **1.5–2.4 %** at that average power.
The simulator assumes `pa_efficiency = 0.25` (range 0.15–0.40, `configs/power.yaml`).
This is an order-of-magnitude gap. It will move every P1 energy-per-bit and energy-policy number
(and their sign comparisons, e.g. 32 vs 64 chains) once real PA data is used. Record as a
**model–hardware gap**; do not retune the model inside H1.

## 3. Full-array scaling (warning only)

| Item | 16 tiles | Note |
|---|---|---|
| ADTR1107 PA rail, TX | 282 W | matches kickoff's warning; exceeds earlier speculative 240 W full-RU budget **on its own** |
| Tile totals, TX state | 438 W | + conversion loss + digital core (sim assumes 140 W DSP + 25 W always-on) |
| Tile totals, TDD avg | 381 W | |
| Sim RF/front-end portion (all 64 chains, nominal) | ≈ 168 W | 64 × 0.9 W + 256 × 0.12 W + 20 W / 0.25 |

## 4. Thermal

- Abs. max ADTR1107 dissipation 1.71 W (TX); quiescent 1.1 W leaves ~0.6 W margin before RF heating
  terms. Junction-to-case θ and derating curve: **not extracted — TBD from datasheet**.
- Heat density: ~27 W in TX over a tile whose radiator site grid is 53.5 × 17.8 mm (9.5 cm²) →
  ~2.9 W/cm² if the electronics sit behind the aperture. Even with a 2–3× larger board this needs a
  conductive back-side heat spreader and forced air; natural convection is not credible.
- Sim lumped `thermal_resistance_k_per_w = 0.45` is an abstraction, not a design value.

## 5. Rails needed (union of candidates)

+5 V (PA drain, ADF4371 VCO), +3.3 V (ADAR1000, LNA, switches, mixers, ADF4371), −5 V (ADAR1000 AVDD1),
−3.3 V (ADTR1107 VSS_SW); cost-down adds +6 V (PMA3-14LN+) and −2.5 V (ADRF5019) and needs its own
gate-bias generation. Sequencing per `H1_CLOCK_CALIBRATION.md` §4.
