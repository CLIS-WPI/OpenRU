# H2-B Electrical safety review

- **Date:** 2026-11-12.
- **Branch:** `hardware/h2b-electrical`, from H2-A `376a42f`.
- **Scope:** schematic only. No PCB, no hardware, no measurement.

All schematic edits in H2-B were made through the KiCad MCP tools (plugin `kicad@ProductOfAmerica` 0.21.1, KiCad 9.0.9
host install). The H2-A generator is frozen (§6).

## 1. PRIORITY — ADAR1000 / ADTR1107 negative gate-bias conflict

### Verified facts (quoted)

| Source | Statement |
|---|---|
| ADAR1000 Rev B p45 | "For safe power up of the ADTR1107 PA, the PA_BIASx bias pins must be set to −2.5 V before the +5 V supply is powered up." EXT_PAx_BIAS_OFF = **0x85** "for approximately −2.5 V" … "which is a safe voltage for the VGG_PA pins when the +5 V supply is powered up." EXT_PAx_BIAS_ON = 0x39 ≈ −1.1 V |
| ADAR1000 Rev B p45 | "if the LNA must be debiased while in transmit mode … EXT_LNA_BIAS_OFF = **0x68**" "for approximately −2 V" |
| ADAR1000 Rev B p7–8, p31 | PA_BIASx / LNA_BIAS: 8-bit DAC, "−4.8 to 0" V; 0x00 = 0 V, 0xFF = −4.8 V; PA_BIASx = 0 V at power-up (p41) |
| ADTR1107 Rev C Table 6 (abs max) | VGG_PA **−2 V to +0 V** (transmit state, PA on); VGG_LNA **−2 V to +0.2 V** |
| ADTR1107 Rev C p24 | TX power-up: "Set the VGG_PA pin to −1.75 V" before "Set the VDD_PA pin to 5 V"; power-down returns VGG_PA to −1.75 V before VDD_PA → 0 V. IDQ set with VGG_PA between −1.75 V and −0.25 V; typical −1.1 V (p26) |

### Finding

The ADAR1000 datasheet's recommended PA OFF value (≈ −2.5 V) is **0.5 V beyond** the ADTR1107 VGG_PA absolute maximum
(−2 V). Its LNA OFF value (≈ −1.96 V nominal) sits at the VGG_LNA absolute-maximum edge, with no margin for DAC error.
Both values come from ADI documents and contradict each other. Neither document resolves the conflict. The ADAR1000
calls −2.5 V "safe", but the ADTR1107 rating is the device-level limit, so the ADTR1107 limit governs.

The DAC scale is consistent across ADI's own pairs: 0x39 → −1.07 V, 0x68 → −1.96 V, 0x85 → −2.50 V, all fitting
V ≈ −code × 4.8/255.

### Decision (H2-B)

- **No schematic path applies a gate voltage beyond −2 V.** The only sources of VGG_PA and VGG_LNA are the ADAR1000 DAC
  outputs, so the risk is entirely a firmware write. H2-B adds no clamp.
  - A diode/zener clamp at about −1.9 V would need a reference rail and would load a ±10 mA DAC.
  - Its interaction with the bias accuracy is not documented by ADI, so adding it would be an unverified circuit.
  - It is listed as an option for ADI (inquiry 5a).
- **Firmware limit (mandatory):** every EXT_PAx_BIAS_ON/OFF and EXT_LNA_BIAS_ON/OFF write must be ≤ **0x5D** (≈ −1.75 V
  nominal, the ADTR1107's own pinch value). Writes of 0x85 or 0x68 are **prohibited**. Firmware must reject them, and
  should read back each register after writing it.
- The schematic carries this rule as a note on all four beamformer sheets (`bf1..4`).
- **Bench pre-check before any drain is enabled:**
  1. Program the bias registers with `MCU_PA_EN` low, so the drains are off in hardware.
  2. Measure every PA_BIASx and LNA_BIAS pin with a DMM.
  3. Confirm each is within −1.80 … −0.20 V.
  4. Only then enable `PA_DRAIN_EN`.

  This also measures the real DAC offset/gain error, which the datasheet does not give.
- **LNA OFF in TX:** use ≤ 0x5D (≈ −1.75 V) instead of ADI's 0x68. Whether −1.75 V fully pinches the LNA is
  **unverified**. Check it on the bench: compare the +3V3_RF current with TR high against TR low, with no RF applied.

**Status:** the conflict is contained by a firmware limit plus a bench check; it is **not resolved by ADI**. It stays
open as **S1** until ADI answers inquiry 5a. Bias-generating firmware must not run on hardware until the limit is
implemented and reviewed.

## 2. ADTR1107 LNA behaviour during TX

- **ADI-documented operating mode (ADAR1000 Rev B p44–45):**
  - Step 1 connects 3.3 V to ADTR1107 VDD_SW **and VDD_LNA**, and it stays on through step 6 (5 V to VDD_PA).
  - "Connecting the ADAR1000 LNA_BIAS pin to the ADTR1107 VGG_LNA is optional because the ADTR1107 LNA is self biased.
    However, … if the LNA must be debiased while in transmit mode …"
  - So keeping the LNA powered during TX is the combined ADAR1000 + ADTR1107 mode that ADI documents.
- **ADTR1107 standalone sequences (Rev C p24):** they describe static TX and RX states. In TX, VDD_LNA = 0 V; in RX,
  VDD_PA = 0 V. That is a different way of operating the part, not a contradiction of the combined mode.
- **H2-B:**
  - VDD_LNA stays on `+3V3_RF`.
  - The LNA is debiased in TX through LNA_BIAS, with OFF ≤ 0x5D (§1).
  - The 10 kΩ to GND keeps VGG_LNA at 0 V (self-bias, RX) while LNA_BIAS is high-impedance at power-up.
  - Switch isolation in TX protects the LNA input: ANT→RX_OUT 64 dB is specified with the receive state off.
  - **Residual:** isolation with the LNA powered but debiased is not specified (S3).

## 3. Power-up / power-down sequences (checked against both datasheets)

| ADI step (ADAR1000 p44–45 / ADTR1107 p24) | H2-B mechanism | Enforced by |
|---|---|---|
| 3.3 V to VDD_SW, VDD_LNA, ADAR1000 AVDD3 first | `PWR_EN_3V3` (pull-down) | firmware order; regulator U601 is a placeholder |
| −3.3 V to VSS_SW after VDD_SW | `PWR_EN_NEG` (pull-down) | firmware order. The −3.3 V regulator U608 is a placeholder; **no hardware ordering** (S4) |
| CTRL_SW defined before RF / PA | 100 k pull-up → RX while TR_SW_POS floats (p41); then firmware sets TR_SOURCE/SW_DRV | hardware default + firmware |
| −5 V to ADAR1000 (AVDD3 before/with AVDD1) | `PWR_EN_NEG` after `PWR_EN_3V3` | firmware order |
| PA_BIAS to OFF before VDD_PA | firmware writes OFF ≤ 0x5D (§1) | firmware + bench pre-check |
| 5 V to VDD_PA last | TPS22810 ×4, EN = `PA_DRAIN_EN` = MCU_PA_EN · WDT_OK · NEG_OK | **hardware AND** + firmware |
| Power-down: VGG_PA → −1.75 V, then VDD_PA → 0 | TX_ALLOW low → PA_ON low → OFF values; then PA_DRAIN_EN low; QOD discharges VOUT through 250–400 Ω (H2-B) | hardware + firmware |
| Fault: watchdog / negative rail lost | WDT_OK or NEG_OK low → PA_DRAIN_EN low in hardware | hardware (NEG_OK monitor U609 still a placeholder, S2) |

**Gap:** in an uncontrolled power loss, −5 V may collapse before +5 V_PA. That would pull PA_BIAS toward 0 V (full
gate) while the drain is still up. The drain switch drops only if NEG_OK reacts faster than the +5 V bulk decays.
U609 is still a placeholder, so this is **S2**.

## 4. Changes made in H2-B

| Block | Change | Basis |
|---|---|---|
| ADF4371 loop filter | C509 120 pF, R507 5.6 k + C510 820 pF, R508 2.2 k, C511 22 pF (3rd-order passive) | **DERIVED** (`tools/loop_filter.py`). ADF4371 Rev 0 gives no reference filter ("use ADIsimPLL"). Inputs: Kv 50 MHz/V nominal (DS p23), Icp 1.75 mA default, N 660, fPFD 10 MHz. Numeric check: 98 kHz crossover, 46° PM, −81 dB loop gain at fPFD. Confirm in ADIsimPLL. No damage risk |
| AVA-183A+ bias | L505 3.3 nH (0805 WW), C512 0.1 µF on VD1; C513 1 nF on VD2; C514 18 pF, C515 5.6 pF on the +VS line; PWR_FLAG on the VD1 node (fed through L505) | Mini-Circuits AVA-183A+ REV D Fig 2, read from the rendered figure. ML1–ML7 microstrips and pads 1, 6 to GND are layout items (PL-328) |
| TPS22810 ×4 | QOD tied to VOUT; CT 2200 pF; CIN 1 µF | TI TPS22810 (SLVSDH0C, rev. Jan 2018) pin table and §7 test conditions; EN threshold 1.13–1.30 V checked against 1.8 V logic |
| TPS3430 | CWD and CRST each 10 k to VDD; SET0 = SET1 = GND; 0.1 µF on VDD1 | TI TPS3430 (SBVS366A) Table 6.6: window 9.0 ms (max 10.35) / 109 ms (min 92.7); tRST 10 ms. Strapping SET0/SET1 means firmware cannot disable the watchdog. VDD range 1.6–6.5 V includes 1.8 V |
| Beamformer sheets | gate-bias limit note | §1 |

## 5. Open safety items

| ID | Item | Severity |
|---|---|---|
| S1 | Gate-bias OFF values: firmware limit only; ADI confirmation pending (inquiry 5a) | **high** (device damage) |
| S2 | NEG_OK monitor U609 is a placeholder; collapse order on power loss not designed | **high** |
| S3 | LNA debias at −1.75 V and TX isolation with LNA powered: unverified | medium |
| S4 | No hardware ordering between ±3.3 V / −5 V rails (placeholder regulators) | medium |
| S5 | TPS3430 WDO state during power-up ramp not characterised; MCU enables are pulled low, so TX stays muted regardless | low |
| S6 | VGG_PA 10 nF vs PA_BIAS switching speed (≈0.65 µs per TDD edge or more) | medium (timing) |

## 6. Process note

- `tools/build_schematics.py` / `tools/run_h2a_checks.sh` regenerate the H2-A design from scratch. Running them now
  would erase the H2-B edits, so the check script refuses unless `FORCE_H2A_REBUILD=1` is set.
- From H2-B on, the KiCad files are the source of truth.
- ERC, the netlist and the PDF are produced with the MCP tools. `tools/verify_netlist.py` re-checks the exported netlist.

## 7. Sources used in H2-B

- TI TPS22810 SLVSDH0C (rev. Jan 2018): https://www.ti.com/lit/ds/symlink/tps22810.pdf
- TI TPS3430 SBVS366A: https://www.ti.com/lit/ds/symlink/tps3430.pdf
- Mini-Circuits AVA-183A+ REV D (ECO-024424), Fig 2: https://www.minicircuits.com/pdfs/AVA-183A+.pdf. Read from the copy
  fetched in H2-A, figure rendered at 300 dpi.
- ADI ADAR1000 Rev B, ADTR1107 Rev C, ADF4371 Rev 0: the same mirror copies as H2-A (`H2A_SOURCE_MANIFEST.md`).
- TI INA226 and PCA9306 datasheets were downloaded but **not yet** used to verify U21/U22.

The MCU sheet note cites "TPS3430 SLVSxxx". The correct document ID is SBVS366A; fix the note at the next MCU-sheet edit.
