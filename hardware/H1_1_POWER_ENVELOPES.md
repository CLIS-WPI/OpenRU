# H1.1 Power Envelopes

The simulator's 43 dBm total over 64 chains (`configs/radio.yaml`) is a **modelling assumption**, not a
requirement for the first PCB. H1.1 separates two envelopes. The simulator is **not** modified.

Common assumptions (ASSUMPTION unless tagged): 100 MHz OFDM, no DPD, 8–10 dB backoff from FE OP1dB for
EVM/ACLR (to be measured); feed loss 0.7 dB; patch element gain 5 dBi; topology A — total power over
16 feeds, array gain over 8 sites (10·log10 8 = 9.0 dB); EIRP figures are **conducted-equivalent estimates
only**: no OTA transmission at 8.35–8.45 GHz without authorisation (`H1_RISKS_AND_GATE.md`).
Link examples use LOS free-space loss (90.9 dB @ 100 m, 103.0 dB @ 400 m at 8.4 GHz), UE 0 dBi, UE NF 7 dB,
noise −174 + 80 + 7 = −87 dBm.

## Envelopes

| Quantity | **PROTOTYPE** (4T4R lab demo) | **SCALABLE TARGET** (system objective) |
|---|---|---|
| Purpose | Prove beam control, calibration, LO/clock coherence, TDD switching, safety interlocks, RF cascade vs prediction — cabled/shielded | Reach the coverage the P1 simulation assumed |
| Avg TX per feed (at feed) | **≥ 10 dBm** (10 mW) | **18.9 dBm** (78 mW) = sim 43 dBm / 64 chains / 4 feeds |
| Front end | ADTR1107 (OP1dB 23 dBm typ, OFFICIAL) | **None qualified.** Needs FE OP1dB ≥ **27.6–29.6 dBm** (8–10 dB backoff) |
| Compression margin | FE avg out 10.7 dBm → **12.3 dB below OP1dB typ** (10.3 dB below 21 dBm min) | 8–10 dB by construction |
| FE input / BFIC drive | −10.8 dBm → ADAR1000 out **20.8 dB below its 10 dBm OP1dB** | depends on FE gain; ADTR1101-class needs ≥ +2 dBm (DERIVED) — near ADAR1000 OP1dB → driver stage likely |
| Conducted per tile | 22.0 dBm (0.16 W) | 30.9 dBm (1.24 W) |
| EIRP per tile (estimate) | 36.1 dBm | 45.0 dBm |
| EIRP 16-tile array (estimate) | 60.2 dBm | 69.1 dBm |
| Example DL SNR, tile only, 100 m / 400 m LOS | 32 dB / 20 dB | 41 dB / 29 dB |
| RX NF at feed | 3.85 dB (H1 cascade, Friis, off-frequency data) | same chain → same |
| Tile DC, TX / RX / TDD avg (0.75 DL) | **27.4 / 12.8 / 23.8 W** (H1 power doc; quiescent, no conversion loss) | **unknown** — no qualified FE. If FE efficiency at backoff were 7.5% (ASSUMPTION), PA DC ≈ 1.46 W RF/0.075 ≈ 19.5 W + ~10 W other ≈ 30 W TX |
| Heat (TX) | ≈ 27.2 W per tile (RF out 0.16 W) | ≈ 28–29 W per tile under the assumption above |
| Rails | +5 V, +3.3 V, −5 V, −3.3 V (H1 power doc) | + higher-voltage drain rail if GaN FE (e.g. QPF5001/ADTR1101 class; values not obtained) |
| Effective PA efficiency at avg out | ~1.1% (16 × 11.7 mW / 17.6 W) | unknown |

## Does the lower prototype target invalidate the prototype?

**No.** Every prototype objective (beam/phase/gain control, calibration of 4 chains and 16 feeds, coherent
LO/clock, TDD timing, PA bias sequencing and safety interlocks, measured gain/NF/compression vs this
budget) is independent of absolute output power, and all testing is cabled or shielded anyway.

What the prototype **cannot** demonstrate: the P1 coverage/goodput at 43 dBm, any energy-efficiency or
energy-per-bit claim, or 32-vs-64-chain energy trade-offs. Those remain simulation-only (blocker B4 re-scoped).

The prototype at 10 dBm/feed sits ~8.9 dB below the simulated per-feed power. If tested OTA in an
authorised setting, the example link budget still leaves ≥ 20 dB SNR at 400 m LOS for a single tile.

## Simulator assumptions that a later single targeted update would touch (not done in H1.1)

| File / key | Current | Hardware-informed replacement |
|---|---|---|
| `configs/radio.yaml` `total_tx_power_dbm` | 43.0 | prototype: 34.1 (64 chains at 10 dBm/feed) — or keep 43 as scalable target, labelled as such |
| `configs/radio.yaml` `per_chain_power_cap_dbm` | 30.0 | prototype ≈ 16.7 dBm per chain (4 × 10.7 dBm FE out) |
| `configs/radio.yaml` / `power.yaml` `noise_figure_db` / `receiver_noise_figure_db` | 7.0 | ≈ 3.9 dB (H1 cascade) after bench confirmation |
| `configs/power.yaml` `pa_efficiency` | 0.25 | backoff-dependent: ~0.01–0.02 for ADTR1107 at prototype power |
| `configs/power.yaml` `per_chain_electronics_w` / `per_feed_branch_w` | 0.9 / 0.12 W | ADAR1000 ~1.16 W TX / 0.86 W RX per chain; ADTR1107 1.1 W TX / 0.26 W RX per feed (quiescent) |
| `configs/power.yaml` `rf_settling_time_us` | 12 | < 1 µs (ADAR1000 TR 180 ns; ADTR1107 10 ns + 17 ns) |

Any such update changes the config digest and P1 energy results; it requires owner approval and is out
of H1.1 scope.
