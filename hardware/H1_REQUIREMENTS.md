# H1 Requirements — 4T4R / 16-feed RF tile

Status: **H1 architecture study. PCB FABRICATION NO-GO.** Nothing here is a signed-off specification.
Baseline: `p1-scientific-validation` @ `62c3668` (PR #1 not merged; this branch depends on it).
Topology decision: **A — SIM-FAITHFUL** (see `H1_BLOCK_DIAGRAM.md`, `H1_FEED_POLARIZATION_MAP.csv`).

Each requirement says where it comes from:
`SIM` = copied from `configs/radio.yaml` / `configs/power.yaml` / `openru_x6/rf.py` (a modelling **assumption**, not a hardware spec);
`KICKOFF` = H1 kickoff v0.1; `DERIVED` = arithmetic from the preceding rows (shown); `TBD` = open.

## 1. RF / waveform

| ID | Requirement | Value | Source |
|---|---|---|---|
| R-RF-1 | Centre frequency | 8.4 GHz (research reference; not a spectrum authorization) | SIM `cell.carrier_freq_hz` |
| R-RF-2 | Occupied envelope | 100 MHz nominal → ~8.35–8.45 GHz; NR grid 273 PRB × 12 × 30 kHz = 98.28 MHz | SIM, P1-B |
| R-RF-3 | Duplex | TDD; DL fraction 0.75, 14-symbol 0.5 ms slots | SIM |
| R-RF-4 | RF chains per tile | 4 coherent TX/RX chains | SIM `chains_per_tile` |
| R-RF-5 | Feeds per tile | 16 = 8 dual-pol sites (2 rows × 4 cols) × {V,H} | SIM |
| R-RF-6 | Site pitch | λ/2 at 8.4 GHz = **17.845 mm** (site grid span 53.5 × 17.8 mm) | SIM `element_spacing_lambda`, DERIVED |
| R-RF-7 | Feed ownership | Each chain drives V+H at two horizontally adjacent sites; chains do **not** carry independent V/H streams | SIM `build_feed_map`; enforced by `tests/unit/test_h1_feed_map.py` |
| R-RF-8 | Analog phase control | ≥ 5 bits (sim value); finer is acceptable | SIM `phase_shifter_bits` |
| R-RF-9 | Analog residual error after calibration | ≤ 5° rms phase, ≤ 0.3 dB rms amplitude (sim nominal; sim sensitivity range 2–15°) | SIM `analog_phase_error_deg`, `analog_amplitude_error_db` |
| R-RF-10 | Chain-to-chain calibration phase error | ≤ 2° rms (sim P1-C nominal) | SIM `calibration_phase_error_deg` |
| R-RF-11 | Receiver system NF (referred to feed) | ≤ 7 dB sim assumption (range 4–10 dB) — H1 must compute a real cascade | SIM `receiver_noise_figure_db` |
| R-RF-12 | Beam/TR switch settling | Sim assumes 12 µs (range 2–50 µs); must fit inside TDD guard period — TBD vs NR guard symbols | SIM `rf_settling_time_us` |

## 2. TX power — the simulation sets the target, hardware must prove it

The simulator normalises **43 dBm total** across active chains and caps each chain at **30 dBm**
(`openru_x6/beamforming.py:169-183`).

| Case | Per chain (avg) | Per feed (avg, ÷4) | Per H1 tile (4 chains) |
|---|---|---|---|
| All 64 chains active (nominal) | 43 − 10·log10(64) = **24.9 dBm** | **18.9 dBm** (78 mW) | 31.0 dBm (1.26 W) |
| 32 chains active (BALANCED_32) | 27.9 dBm | 21.9 dBm | — |
| Per-chain cap | 30.0 dBm | **24.0 dBm** (251 mW) | 36.0 dBm |

R-TX-1: H1 must show, in `H1_RF_CASCADE_BUDGET.csv`, the **average** OFDM output per feed that meets EVM/ACLR
with realistic backoff from the selected front end. If that is below 18.9 dBm, the P1 model's power
assumption is **not hardware-supported** and must be recorded as a model–hardware gap (not silently fixed).

## 3. Clock, control, safety

| ID | Requirement | Source |
|---|---|---|
| R-CLK-1 | One shared LO and one 10 MHz/PPS reference for all 4 chains; bounded, calibratable skew | KICKOFF §4.2 |
| R-CTL-1 | BFIC programming by local MCU over SPI with readback of every written beam/bias register | KICKOFF §3; mirrors `control.py` apply→verify |
| R-CTL-2 | Synchronised beam latch across all 4 BFICs (one GPIO edge) | KICKOFF §3 |
| R-SAF-1 | Power-on, reset, MCU-hang and watchdog-expiry states = **TX inhibited, PA gates pinched off** | KICKOFF §3; sim `safety.py` independent veto |
| R-SAF-2 | Independent hardware RF mute not routed through the MCU firmware path | KICKOFF §3 |
| R-SAF-3 | Missing, frozen, stale or out-of-range temperature/current sensor → TX inhibit, not "assume OK" | KICKOFF §3; P1-E sensor-fault cases (58.3% false alarms in sim — hardware thresholds must be set from bench data, not sim) |
| R-SAF-4 | Per-rail current and per-tile temperature telemetry readable by the MCU | KICKOFF §3 |

## 4. Interfaces (fixed in H1, implemented later)

| ID | Interface | H1 decision |
|---|---|---|
| R-IF-1 | Digital/IF | 4 × TX IF + 4 × RX IF (SMA) to USRP N310 for bench use; IF frequency per `H1_FREQUENCY_PLAN.md` |
| R-IF-2 | Reference | 10 MHz + PPS in (SMA), distributed to LO PLL and N310 |
| R-IF-3 | Control | MCU USB/UART or Ethernet to host; TX/RX TDD control GPIO from N310 GPIO header (TBD pin map) |
| R-IF-4 | Antenna | 16 RF feeds; connectorised or direct-to-patch — open in `H1_RISKS_AND_GATE.md` (physical gate) |

## 5. Out of scope for H1

Digital core / FPGA RTL, O-RAN 7.2x / OCUDU fronthaul, PCB layout (H2), OTA transmission at 8.4 GHz,
any full 64T64R build commitment, new simulation campaigns.
