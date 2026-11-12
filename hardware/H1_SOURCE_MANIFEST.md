# H1 Source Manifest

Retrieved 2026-11-11. **Access caveat:** analog.com and qorvo.com timed out or rate-limited automated
requests. ADI datasheet values were read from ADI-authored PDFs hosted by third-party mirrors (the
revision and page are given). Every analog.com product-page fact (1k price, lifecycle) is **UNVERIFIED**
until re-checked in a browser. "Snippet" = search-result excerpt of a manufacturer datasheet, not a full read.

| Part / topic | Document | Retrieved via | Used for |
|---|---|---|---|
| OpenRU baseline | `configs/radio.yaml`, `configs/power.yaml`, `openru_x6/rf.py`, `openru_x6/beamforming.py` @ 62c3668 | local repo | requirements, feed map, power target |
| ADAR1000 | Datasheet Rev B (7/2022), canonical https://www.analog.com/media/en/technical-documentation/data-sheets/adar1000.pdf | mirror https://www.datasheetall.com/pdf/adar1000.pdf | gain, NF, P1dB, supplies, SPI, bias DACs |
| ADAR1000 availability | https://www.findchips.com/search/ADAR1000ACCZN | direct | B1 |
| ADTR1107 | Datasheet Rev C (6/2023), canonical https://www.analog.com/en/products/adtr1107.html | mirror https://www.datasheetall.com/pdf/adtr1107.pdf | TX/RX tables, sequencing |
| ADTR1107 price | https://www.digikey.com/en/products/detail/analog-devices-inc/ADTR1107ACCZ/12419087 ; https://www.findchips.com/search/ADTR1107ACCZ | direct | BOM, M7 |
| ADI selection guide | 2021 edition (requested current URL timed out) | mirror https://manuals.plus/m/2b88d0230fbde0a96d972e9fcebd58c457016164d49f321912b02902bd600cf2.pdf | "5 V at 220 mA (PA), 3.3 V at 80 mA (LNA)" |
| ADF4371 | Datasheet Rev 0 (newer revision may exist) | mirror https://www.hkjdwchip.com/image//files/analogdevicesinc-adf4371bccz-datasheets-0617.pdf ; price https://www.findchips.com/search/ADF4371BCCZ | LO |
| ADI X-band platform / ADXUD1A / Stingray | https://developer.analog.com/docs/system-level/solutions/platforms/x-band/ (+ /hardware/converter/, /hardware/beamforming/) | direct, **summarised by fetch tool** | reference architecture |
| ADTR1101 / ADTR1104 | ADI description via https://elecena.pl/product/29345517/8ghz-to-12ghz-5w-front-end-ic ; 1104 snippets only | third party | confirms headline TX power at ≥ 8.5 GHz |
| HMC773A / HMC773ALC3B | Rev A (8/2018) https://datasheet.chipsmall.com/HMC773A/436424.pdf ; Rev D https://datasheet.chipsmall.com/HMC773ALC3B/260873.pdf | mirror | LO range, CL, LO drive |
| LTC5552 | Datasheet "5552f" https://cdn.components.ru/media/PDF/2540561.pdf ; price https://www.digikey.com/en/products/result?keywords=LTC5552IUDB | mirror / direct | preferred mixer |
| HMC8193LC4 | Rev B https://datasheet.chipsmall.com/HMC8193LC4/260874.pdf | mirror | rejected (RF ≤ 8.5 GHz edge) |
| USRP N310 | https://www.ettus.com/all-products/usrp-n310/ ; https://www.ettus.com/wp-content/uploads/2019/01/USRP_N310_Datasheet_v3.pdf ; https://uhd.readthedocs.io/en/latest/page_usrp_n3xx.html | direct | IF limits, phase coherence |
| 47 CFR 2.106 | https://www.ecfr.gov/ (§2.106); table image https://img.federalregister.gov/ER01OC20.024/ER01OC20.024_large.png | direct | regulatory boundary |
| QPA0813 | https://www.digikey.com/en/products/detail/qorvo/QPA0813/29436045 ; https://www.rfmw.com/products/detail/qpa0813-qorvo/862832/ ; datasheet Prelim Rev A specs via snippet | distributor | cost-down PA |
| PMA3-14LN+ | https://www.minicircuits.com/pdfs/PMA3-14LN+.pdf (Rev B, full read) | direct | cost-down LNA |
| GRF2111 | https://www.rfmw.com/products/detail/grf2111-guerrilla-rf/856053 | distributor | LNA alternative |
| ADRF5019 | https://www.digikey.com/en/products/detail/analog-devices-inc/ADRF5019BCPZN/10659106 ; datasheet snippet | distributor | T/R and converter switches |
| QPF5005, MAMF-011015, Qorvo X-band kit | rfmw.com, digikey.com | distributor | integrated alternatives (rejected: cost or band) |
| BFCN-8350+, BFCN-8450+, HFCN-7150+, ZVBP-8250-S+ | https://www.minicircuits.com/pdfs/<part>.pdf | direct | RF/LO/image filtering |

## Re-verification checklist before schematics

1. ADAR1000 lifecycle, lead time, 1k price (analog.com / ADI sales).
2. ADTR1107 1k list price ($126.47 claim).
3. QPA0813 final datasheet and 8.4 GHz performance.
4. LTC5552 upconversion data at 8.4 GHz / 1.8 GHz IF.
5. ADF4371 current revision; output power at 6.6 GHz.
6. N310 REF/PPS input levels.
