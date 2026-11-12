# H2-A Reference-design and source manifest

Retrieved 2026-11-12.

**Access:** analog.com timed out (HTTP/2 stream errors, then timeouts). Mouser datasheet links returned HTML
or timed out, and minicircuits.com refused curl (403). None of these were bypassed. ADI documents were read from
ADI-authored PDFs on third-party mirrors, so the revision is stated and the copy should be re-checked against
analog.com before sign-off. Mini-Circuits PDFs were read through the WebFetch tool.

Every pin table is in `../datasheet_pins/*_pins.csv` (with `ds_page`), and the extracted facts are in `*_notes.md`.

| Part | Document / revision | Retrieved via | Used for |
|---|---|---|---|
| ADAR1000 | Rev B (7/2022), 79 pp | mirror https://www.datasheetall.com/pdf/adar1000.pdf | 88-pin symbol; PA_BIAS power-up state (p41); ADTR1107 hookup and sequence (p44–45); SPI/ADDR (p13–14, p32); load pins (p32–35); errata (p43, p47–49); CREG caps (p14) |
| ADTR1107 | Rev C (6/2023), 27 pp | mirror https://www.datasheetall.com/pdf/adtr1107.pdf | 24-pin symbol; Table 1/3 (6–14 GHz); sequences (p24); Fig 89 (10 nF VGG_PA); Fig 91 (ADAR1000 connection); θJC (Table 7) |
| ADF4371 | Rev 0 (1/2019), 48 pp | mirror https://www.hkjdwchip.com/image//files/analogdevicesinc-adf4371bccz-datasheets-0617.pdf | 48-pin symbol; supplies and decoupling (p9–10, p24); REFIN SE/AC (p10, p19); RF8 output stage (Fig 44); register defaults (REG0025: RF8 on at power-up) |
| LTC5553 | 5553f (2017), 16 pp | distributor mirror https://pf.unikeyic.com/datasheet/a0/d2/c9a8/a0/5eb1242828282bd94b0a2ebb380c0bb2.pdf | 12-pin symbol; IF 1890 MHz tables; Fig 1 test circuit (C1–C3); EN; port DC conditions |
| LTC5552 | 5552f | mirror https://cdn.components.ru/media/PDF/2540561.pdf | mixer comparison; recommends LTC5553 for IF > 500 MHz (p1) |
| LTC5553 eval board | DC2566A — https://www.analog.com/en/resources/evaluation-hardware-and-software/evaluation-boards-kits/dc2566a.html | **not accessed** (analog.com unreachable) | listed only |
| BFCN-8350+ | REV. D, M151107 | https://www.minicircuits.com/pdfs/BFCN-8350+.pdf (WebFetch) | pins 1/3, GND 2,4; IL; stop bands |
| BFCN-1840+ | REV. E, M151107 | https://www.minicircuits.com/pdfs/BFCN-1840+.pdf | IF filter 1750–1930 MHz; pins 1/3, GND 2,4 |
| HFCN-7150+ | REV. J, ECO-023938 | https://www.minicircuits.com/pdfs/HFCN-7150+.pdf | pins 1/3, GND 2,4,5,6; 18.85 dB at 6650 MHz |
| EP4RKU+ | REV. C, ECO-028633 | https://www.minicircuits.com/pdfs/EP4RKU+.pdf | 4-way splitter (LO and cal); pad table; 3.4 dB excess loss, 1.9°/19° phase unbalance |
| EDC21-24+ | REV. A, ECO-012570 | https://www.minicircuits.com/pdfs/EDC21-24+.pdf | 21 dB coupler; pads 3/7/16; directivity 19 dB typ |
| AVA-183A+ | REV. D, ECO-024424 | https://www.minicircuits.com/pdfs/AVA-183A+.pdf | LO buffer; pads; Fig 2 values (wiring UNRESOLVED) |
| KiCad library parts | KiCad 9.0.9 official symbol libraries (Docker image `kicad/kicad:9.0`) | local | STM32G431 (base symbol `STM32G431C_6-8-B_Ux`), TPS22810DRV, TPS3430WDRC, 74LVC1G11/08/125, INA226, PCA9306, TMP117 (via base `TMP102xxDRL`), connectors, R/C/L. Pin maps come from the KiCad library; application values (strap tables, timing) are **not** verified against the TI/ST datasheets |
| Feed ownership | `hardware/H1_FEED_POLARIZATION_MAP.csv` (from `openru_x6/rf.py::build_feed_map`) | local | topology A, enforced by `verify_netlist.py` |
| H1/H1.1 baseline | commit a7990911b39865cade9f08b94dd8522956c959f7 | local | requirements, envelopes, BOM prices |

## Tools

| Tool | Version | Use |
|---|---|---|
| mcp-server-kicad (plugin `kicad@ProductOfAmerica`) | 0.21.1, from PyPI | all `.kicad_*` writes, ERC, netlist, PDF export, hierarchy validation |
| KiCad `kicad-cli` | 9.0.9 (Docker) | ERC / netlist / PDF |
| `pdftotext` | poppler | datasheet text extraction |

The MCP server was installed in the middle of the session, so it was not connected as live MCP tools. The same tool
functions were called from Python (`tools/build_schematics.py`). No KiCad file was hand-edited.

## Not used / deferred

- QPX0252: no material obtained or committed, pending university export-control review.
- ADIsimRF, ADIsimPLL: not available here. The loop filter is UNRESOLVED.
- scikit-rf: not installed, and not needed for the closed-form cascade. No S-parameter or EM simulation was run, and
  none is claimed.
