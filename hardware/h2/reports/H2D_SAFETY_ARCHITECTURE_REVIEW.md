# H2-D Independent PA safety architecture review

- **Date:** 2026-11-12.
- **Branch:** `hardware/h2d-safety-arch` (from H2-C `cd897f8`).
- **Scope:** review, analysis and behavioural simulation only.
- **Schematic: unchanged in H2-D** (see §6). ERC and netlist are therefore identical to H2-C (5 findings: RS_SW
  unresolved, 4 TI-approved QOD↔VOUT).
- **Evidence classes:**
  - **DS-G:** datasheet guaranteed min/max;
  - **DS-T:** typical only;
  - **NS:** not specified;
  - **SIM-B:** behavioural ngspice, preliminary, not hardware-validated.

Working papers are in `design/h2d/`:

| File | Content |
|---|---|
| `AUDIT_FMEA.md` | signal-state audit, 68-row FMEA, fault trees, datasheet quotes D1–D22 |
| `CHARACTERISTICS.md` | guaranteed vs typical parameters for 13 parts plus candidate parts |
| `GATE_BIAS_ANALYSIS.md` | gate-bias conflict investigation |
| `ARCH_COMPARE.md` | comparison of the two candidate architectures against H2-C |
| `BENCH_PLAN.md` | dummy-load bench validation plan |
| `sim/` | timing budget and Candidate-A behavioural sim |

## 1. Audit of the as-built H2-C interlock: key findings

| # | Finding | Class |
|---|---|---|
| 1 | One feedback-resistor fault (R655 open or R656 short) drives +5V_PA toward 12 V. TPS568230 OVP works from FB, so it cannot see it. TPS22810 passes 12 V to all 16 VDD_PA (abs max 5.5 V). PG_5VPA only reaches the MCU | physically reachable, single fault |
| 2 | IL_REF is not monitored. Its loss collapses both gate thresholds, so every gate reads OK and pinched | single fault, latent |
| 3 | No current limit in the PA path. Several single faults give a permanent crowbar shoot-through of about 13 A | single fault |
| 4 | **TPS3430 WDO is HIGH (not asserted) for VDD between VPOR and 1.6 V, and for about 100–137 ms after power-up** (TPS3430 §7.4.2). The H2-C behavioural model assumed the opposite, **so the H2-C nominal 0/920 ordering result is not valid evidence** | datasheet-defined |
| 5 | All protection converges on U705 and one shared PA_DRAIN_EN net, with no readback | architecture |
| 6 | MCU pins sit directly on WDT_OK, NEG_OK and PG_3V3RF; an MCU fault can override them | single fault / firmware |
| 7 | Supervisor detection delay (NS), VOL above 1 mA (NS) and BAT54C/MOSFET thresholds (25 °C only) carry the H2-C clamp argument | NS / DS-T |
| 8 | No temperature coverage for the clamp and crowbar timing devices | NS |
| 9 | PWR_ENN_NEG floats when +1V8_DIG is absent, so the negative rails can start before +3V3_RF (defeats A2). STM32 PB4's JTAG pull-up puts PWR_EN_3V3 inside the TPS568230 EN undefined band | physically reachable |
| 10 | **TPS22810 QOD is unavailable in thermal shutdown and below VIN UVLO**, and the crowbar shares that VIN. TPS22810 tON/tOFF/tD are 25 °C typical only | DS quote / DS-T |

## 2. Fault-tree minimal cut sets (summary; full trees in AUDIT_FMEA.md)

| Top event | Order-1 cut sets in H2-C |
|---|---|
| TE1: drain energised with a gate above −1.5 V outside armed TX | TPS22810 short; EN-to-VIN short (all four chains); U705 stuck high; PA_DRAIN_EN bridged; firmware bias code or SPI corruption [FW] |
| TE2: VGG_PA outside −2.0…0 V | firmware code above 0x6A including ADI's 0x85 [FW]; SPI corruption; −5V_BF over-magnitude; PA_BIAS trace open (+0.6 V through the divider) |
| TE3: crowbar on with the switch on | Q2 open; R996–R999 open; C931–C934 short; crowbar short; crowbar gate pull-up open; plus timing cut sets on NS parameters |
| TE4: drain not below 0.5 V within 50 µs | U705 stuck high; EN-to-VIN short; switch short; Q2 stuck; crowbar or R_CB open |

H2-C therefore has multiple **order-1** cut sets for every top event, and its timing arguments rest on NS/DS-T
parameters.

## 3. Architectures compared (at most two alternatives; details in ARCH_COMPARE.md)

| | H2-C as built | **A: supervised permit + eFuse + timed crowbar** | B: permit + eFuse + per-PA switch, no crowbar |
|---|---|---|---|
| Rail supervision | LM339B (DS-T timing) + TPS386000 (delay NS) | TPS3703 (delay ≤ 30 µs, VOL ≤ 250 mV at 3 mA: DS-G); TLV3202 comparators for gates, negative rails and fast OV | same as A |
| Permit node | LVC logic plus BAT54C clamps (R2 violation) | single open-drain wired-AND node from a dedicated +5V_IL rail (TPS7A25); no diode-clamped logic | same as A |
| Drain switch | TPS22810 (tOFF NS; no current limit; QOD lost in TSD/UVLO) | TPS16630 eFuse per chain: SHDN→FET off ≤ 1.5 µs (DS-G), ILIM 1.84–2.16 A, fast-trip, latch, OVP | TPS16630 + TPS22918 per PA (tOFF NS) |
| Crowbar break-before-make | RC + 25 °C thresholds; overlap 1.5–4 µs in sim; unbounded | crowbar timed from SHDN with a 1 % / C0G RC: **BBM ≥ 1.28 µs on fault, ≥ 2.71 µs on re-arm**, from DS-G limits, inside eFuse VIN 4.5–60 V | no crowbar; R4 rests on TPS22918 tOFF (NS) |
| Worst-case R4 budget (50 µs) | not boundable | rail UV/OV 46.5 µs; gate lost 16.6 µs; +5V_PA OV ≤ 31.2 µs; watchdog/eFuse fault 16.7 µs; +5V_IL loss 16.9 µs | 38.7 µs + tOFF(NS) |
| Overlap if timing fails | about 13 A, unlimited | bounded by eFuse: ≤ 25 A for ≤ 1.5 µs, then current limit and latch | n/a |

**Selected target architecture: A.** Its evidence is stronger than H2-C: R1/R3/R4 close on DS-G limits except the
items in §5, and every overlap is current-bounded.

**SIM-B (one chain plus the permit, preliminary):** 0 crowbar/eFuse overlap in 272 runs. The first permit-network
values latched the permit low; the sim found this and it is corrected (2.2 k pull-up; 47 k/47 k/1 nF per chain).

The A discharge term (12.9 µs) still uses a placeholder of 2× the 25 °C RDS(on) for the crowbar FET, because no
temperature-specified part was found (§5). Crowbar resistor: 6 × 1 Ω (0.168 Ω). Peak about 24 A, ≤ 0.36 mJ per chain.

## 4. Gate-bias absolute-maximum conflict (handled separately; GATE_BIAS_ANALYSIS.md)

- **ADI's own design:** Stingray connects PA_BIAS **directly** to VGG_PA, with no resistor or capacitor. No ADI document
  reconciles 0x85 (−2.5 V) with the −2 V abs max.
- **Divider evaluated:** a passive divider (619 Ω / 365 Ω, k = 0.371) is the only firmware-independent bound found.
  - Worst-case VGG is −1.954 V at the AVDD1 spec limit (−5.25 V), a 46 mV margin.
  - It fails if the −5 V rail goes out of spec (−2.05 V at −5.5 V; −2.49 V with a shorted LDO pass element).
  - It relies on the "simplified" ADAR1000 Fig 86 output stage, and the PA_BIAS range has no pin abs max.
  - It costs OFF reach (code 251/255), +69…115 mV bias drift under gate current, and about 10.6 µs settling per TDD
    edge with the 10 nF.
- **Recommendation:** footprint option only (0 Ω fitted; 365 Ω not fitted), pending ADI answers and bench data.
- **The firmware limit (≤ 0x5D, readback, drain-off pre-check) is NOT independently fail-safe** and is not described
  as such. TE2 keeps order-1 firmware cut sets in every architecture considered. Candidate A does not change this.

## 5. Remaining manufacturer and bench dependencies (blocking)

**Manufacturer:**

| Vendor | Question |
|---|---|
| TI TPS1663 / TPS16630 | definition of "FET OFF" in the 1.5 µs SHDN spec at 1–2.2 A; behaviour below 4.5 V VIN (POR typical only); SHDN threshold hysteresis guarantee; FLT timing in TSD/OCP |
| TI TPS3703 | delay bound below 5 % overdrive and on slow ramps; latch behaviour |
| Crowbar MOSFET | none found with VGS(th) and RDS(on) specified over −40…125 °C. Nexperia datasheets were blocked; not bypassed |
| Vishay RCS1206 | repetitive pulse rating at the crowbar duty |
| ADI | PA_BIAS with AVDD3 lost; VGG_PA abs max when VDD_PA = 0 V (root of the 0x85 conflict); PA_BIAS pin abs max and DAC full-scale min/max; ADTR1107 VDD_PA transient rating (fast OV holds ≤ 5.46 V only if +5V_PA slews ≤ 64 mV/µs) |
| TI TPS568230 | current limit and inductor peak with FB open (sets that slew) |

**Mandatory bench tests** (`BENCH_PLAN.md`; dummy PA emulator, no ADTR1107 energised):

| Test | Measures |
|---|---|
| T1a/T1b | eFuse SHDN→off over temperature and load; behaviour at 0–4.5 V VIN |
| T3 | supervisor detection delay vs overdrive and ramp |
| T4 | VOL at the real sink current |
| T5 | MOSFET VGS(th) and RDS(on) at −40/+85 °C |
| T6 | crowbar pulse, overlap and resistor drift |
| T7 | crowbar timer at temperature |
| T8 | rail-collapse and ordering matrix |
| T9 | PA_BIAS with AVDD3 lost (ADAR1000 eval board only) |
| T11 | undefined monitor outputs never enable the supply |

**Residual possible crowbar/supply conduction in A:**
1. +5V_PA brown-out below the eFuse's 4.5 V rated VIN (unbounded until T1b).
2. Single faults that defeat the timer (timer C open, timer R short, crowbar stuck on). Bounded at ≤ 25 A for ≤ 1.5 µs,
   then current limit and latch; detectable by crowbar-gate readback.
3. Shorted eFuse FET: the crowbar fires into U651 until its UVP trips (256 µs, typical). Fix: gate PWR_EN_5VPA by the
   permit in hardware.

## 6. Decisions

- **Selected safety architecture: Candidate A** as the target.
- **Schematic: NOT modified in H2-D.** A's R3/R4 closure depends on a crowbar MOSFET with temperature-guaranteed
  parameters (none identified) and on TI clarification of the TPS1663 "FET OFF" definition. Redrawing now would encode
  unverified assumptions. Per requirement 10, the missing evidence is listed in §5 instead.
- **Must be included when A is implemented** (audit fixes):
  - PG_5VPA and a +5V_PA OV path into the permit;
  - IL_REF (or its replacement) monitored;
  - per-chain enables with readback of permit, eFuse FLT and crowbar gate;
  - MCU pins on safety nets via series resistors or input-only, never able to assert permit;
  - ENN pull-down;
  - PWR_EN_3V3 pull-down strong enough to override PB4's JTAG pull-up;
  - PWR_EN_5VPA gated by the permit;
  - a watchdog whose output is low (asserted) during brown-out, or a supervisor covering the TPS3430 VDD 0.8–1.6 V
    window.
- **Schematic readiness:** H2-C schematic stays as the documented baseline. The PA safety subsystem is **NOT
  schematic-final**.
- **PCB layout preparation: NO-GO.**
