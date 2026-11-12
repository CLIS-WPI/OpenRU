# ADI technical and commercial inquiry — DRAFT, NOT SENT

**Nothing in this file has been sent.** Sending it needs explicit approval from the project lead. Attach no
project-internal files. Do not request export-controlled material. QPX0252 (Qorvo) is deferred until the university
export-control office has reviewed it, and is not mentioned here.

Proposed recipients: ADI beamforming applications (beamformer@analog.com), plus an ADI sales channel or authorised
distributor for item 1.

---

Subject: University prototype — ADAR1000 / ADTR1107 / LTC5553 / ADF4371 at 8.35–8.45 GHz

Hello,

We are a university research group building a cabled/shielded lab prototype of a 4-channel × 4-element X-band tile:
- 4× ADAR1000 and 16× ADTR1107;
- LTC5553 converters at a 1.8 GHz IF, with a 6.6 GHz LO from an ADF4371;
- operation at 8.35–8.45 GHz.

There is no over-the-air transmission. We would appreciate help with the following.

**1. ADAR1000 lifecycle and quote (highest priority)**
- Please confirm the current lifecycle status of ADAR1000ACCZN and the factory lead time.
- Please quote 8 units (and 1k list for reference) through an authorised channel.
- Is a quantity of 8 available to a university?

**2. Evaluation hardware**
- Are ADAR1000-EVALZ and ADTR1107-EVALZ (or a combined ADAR1000 + ADTR1107 kit) currently orderable?
- Can their schematics and BOMs be shared? We need the AVDD1/AVDD3 and VDD_PA/VDD_LNA/VDD_SW/VSS_SW bypass values,
  which the datasheets do not list.

**3. Performance at 8.35–8.45 GHz**
- ADAR1000 Rev B tabulates 9.5/11.5/14 GHz. Do you have TX gain, OP1dB, the TX gain/attenuation range, RX gain/NF, and
  phase/gain-step accuracy at 8.0–8.5 GHz?
- ADTR1107 Rev C Table 1/3 covers 6–14 GHz. Do the min/typ values apply at 8.4 GHz?

**4. ADTR1107 thermal and linearity**
- θJA, or a recommended thermal design. Table 7 gives θJC of 52.7 °C/W (TX).
- Any EVM/ACLR versus output power for a 100 MHz OFDM (5G NR) signal without DPD.
- The back-off you recommend from OP1dB.

**5. ADAR1000 ↔ ADTR1107 bias questions**

(a) ADAR1000 Rev B p45 recommends EXT_PAx_BIAS_OFF = 0x85 (≈ −2.5 V) for the ADTR1107, but ADTR1107 Rev C Table 6
lists the VGG_PA abs max as −2 V to 0 V. Which OFF value should we use? We currently plan −1.75 V.

(b) The ADTR1107 TX power-up sequence sets VDD_LNA = 0 V. Is it acceptable to keep VDD_LNA = 3.3 V during TX and pinch
the LNA with LNA_BIAS (≈ −2 V)?

(c) ADTR1107 Fig 89 shows 10 nF on VGG_PA, while ADAR1000 PA_BIAS switching (60 ns) is specified into 1 nF. What
capacitance do you recommend when PA_BIAS toggles with TR at each TDD transition?

**6. LTC5553 vs LTC5552 at IF 1.8 GHz**
- We selected LTC5553 (single-ended IF; table data at IF 1890 MHz) over LTC5552, following the LTC5552 datasheet
  guidance for IF > 500 MHz. Please confirm.
- Is there up-conversion data at RF 8.4 GHz / IF 1.8 GHz / LO 6.6 GHz (low side): CL, OIP3, LO–RF leakage?
- Is the DC2566A the current LTC5553 evaluation board?

**7. ADF4371 at a 6.6 GHz LO**
- What is the RF8P single-ended output power at 6.6 GHz for each RF_OUT_POWER setting? Rev 0 shows only Fig 13
  (differential, combined through a balun).
- Phase noise at 6.6 GHz with a 10 MHz single-ended reference at PFD = 10 MHz (integer N = 660).
- A recommended loop-filter starting point (ADIsimPLL file).
- Is there a newer datasheet revision than Rev 0?

Thank you,
[name, affiliation — to be filled by the project lead]
