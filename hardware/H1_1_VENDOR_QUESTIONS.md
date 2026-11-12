# H1.1 Vendor and Compliance Questions — DRAFT, NOT SENT

**Nothing in this file has been sent.** Sending requires explicit project-lead approval. Do not attach
project-internal documents; ask only what is listed. Do not request ITAR/export-controlled material.

## A. Analog Devices — beamformer@analog.com (ADAR1000 / ADTR1107 / ADTR1101 / ADSY2301)

1. Please confirm ADAR1000ACCZN lifecycle ("Recommended for New Designs"), current factory lead time,
   and 1k and 10-unit pricing. Is a quantity of 4–8 obtainable for a university prototype, and through
   which authorised channel?
2. Are ADAR1000 S-parameters, a SystemVue/ADS behavioural model, or IBIS models available, and are any
   gated?
3. Do you have ADAR1000 TX gain, OP1dB, RX gain, NF and phase/gain error data at **8.0–8.5 GHz**
   (Rev B Table 1 lists 9.5 and 11.5 GHz only)? Rev B lists TX OP1dB 10 dBm and Psat 14 dBm at 9.5 GHz —
   please confirm which applies as linear output.
4. Is ADAR1000-EVALZ still orderable from ADI (Digi-Key lists it as discontinued at Digi-Key)?
5. ADTR1107: θJC (JEDEC 2S2P definition), any EVM/ACLR or OFDM back-off data, and confirmation that
   Table 1 min/typ values (6–14 GHz) apply at 8.4 GHz. Current 1k price.
6. ADTR1101: release/lifecycle status, distribution availability, OP1dB/Psat/gain/PAE at 8.4 GHz (CW and
   pulsed), linearity data, quiescent current and supplies, and whether ADAR1000 PA_BIAS outputs can
   bias it directly.
7. ADSY2301: are lattice spacing, calibration method, LO/clock distribution, thermal data and schematics
   available to a university under standard (non-NDA) terms? Any characterisation at 8.0–8.5 GHz?

## B. Qorvo — beamforming-sales@qorvo.com (QPX0252 / QPA0813 / QPF5001)

1. QPX0252: what is the export classification? The product page shows "ITAR Restricted: Yes" alongside
   "ECCN: EAR99" — which is correct? Can datasheet-level information be used in an open-source
   (Apache-2.0) university design?
2. QPX0252: number of RF common ports (single Tx + dual Rx beams?), TX/RX gain, NF, OP1dB at 8.4 GHz,
   supply current per mode, package dimensions/pitch, sample and dev-kit (QPX0252-DL) availability and price.
3. QPA0813: the product table lists OP1dB 19 dBm and Psat 28.5 dBm; distributors list P1dB 28.5 dBm.
   Please confirm OP1dB and Psat, their test frequency and CW/pulsed conditions, and performance at
   8.0–8.5 GHz (datasheet plots start at 8.5 GHz).
4. QPF5001: full datasheet values at 8.4 GHz — TX gain, P1dB, Psat (CW vs pulsed, duty), drain voltage,
   quiescent current, PAE at back-off, RX gain, limiter rating, θJC; any linearity data.

## C. University export-control office (internal — still requires approval to send)

1. Before any QPX0252 information (datasheet, dev-kit files, de-embedding data) is obtained or stored in
   the public repository, please determine its actual export classification and whether ITAR restrictions
   apply to a university lab, foreign-national students, and open publication.
2. Confirm that ADI ADAR1000/ADTR1107 public datasheets and drivers may be used in the open repository
   (expected EAR99/public, but please confirm).

## D. Answers needed to close blockers

| Question | Closes |
|---|---|
| A1, A4 | B1 (procurement) |
| A3, A5, B3, B4 | B3 (8.4 GHz data) |
| A6, B4 | scalable-target front end (B2-scalable) |
| B1, B2, C1 | QPX0252 eligibility as fallback |
