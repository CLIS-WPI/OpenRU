#!/usr/bin/env python3
"""H2-A RF cascade, LO budget and spur-frequency table (closed-form; no EM, no measurement).

    python rf_budget.py <out_dir>
Writes H2A_RF_CASCADE_BUDGET.csv, H2A_LO_BUDGET.csv, H2A_SPUR_TABLE.csv. Every number carries an
evidence tag: DATASHEET (table value), PLOT (read from a datasheet plot, +-0.5 dB), ASSUMPTION, DERIVED.
"""
import csv
import math
import sys
from pathlib import Path

out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
db = lambda x: 10 * math.log10(x)
lin = lambda x: 10 ** (x / 10)


def friis(stages):
    """stages: [(gain_dB, nf_dB)] -> list of cumulative (gain_dB, nf_dB)."""
    f, g, res = 1.0, 1.0, []
    for i, (gd, nfd) in enumerate(stages):
        f = lin(nfd) if i == 0 else f + (lin(nfd) - 1) / g
        g *= lin(gd)
        res.append((db(g), db(f)))
    return res


rows = []
# ---------------------------------------------------------------- RX (one element, feed -> N310)
rx = [
    ("feed trace + connector", -0.7, 0.7, "ASSUMPTION", "replace after H2 stackup/EM"),
    ("ADTR1107 RX (switch+LNA)", 17.5, 2.5, "DATASHEET", "ADTR1107 Rev C Table 3, 6-14 GHz"),
    ("ADAR1000 RX single channel", 10.0, 8.0, "DATASHEET", "ADAR1000 Rev B Table 1 at 9.5 GHz (8.4 GHz not tabulated)"),
    ("RF trace BF->coupler", -0.5, 0.5, "ASSUMPTION", ""),
    ("EDC21-24+ mainline", -0.7, 0.7, "DATASHEET", "EDC21-24+ REV.A 8-10 GHz typ"),
    ("HFCN-7150+", -1.5, 1.5, "DATASHEET", "HFCN-7150+ REV.J 8.5-10.5 GHz max (7.9-11 GHz: 2.0 max)"),
    ("BFCN-8350+", -1.8, 1.8, "DATASHEET", "BFCN-8350+ REV.D 8250-8450 MHz typ"),
    ("LTC5553 downconversion", -8.0, 10.9, "PLOT+DATASHEET", "CL ~8.0 dB plot at RF 8.4 GHz; NF 10.9 dB table at RF 10 GHz/IF 1890 MHz"),
    ("BFCN-1840+", -1.9, 1.9, "DATASHEET", "BFCN-1840+ REV.E 1750-1880 MHz typ 2.09-1.73 dB"),
    ("IF trace + DC block + coax", -0.5, 0.5, "ASSUMPTION", ""),
    ("USRP N310 RX (TX/RX port)", 30.0, 6.8, "DATASHEET", "N310 datasheet v3, 1.8 GHz"),
]
for (name, g, nf, ev, src), (cg, cnf) in zip(rx, friis([(g, nf) for _, g, nf, _, _ in rx])):
    rows.append(["RX", name, g, nf, "", round(cg, 2), round(cnf, 2), ev, src])
nf_sys = friis([(g, nf) for _, g, nf, _, _ in rx])[-1][1]
rows.append(["RX", "RESULT feed-referred NF (one element)", "", "", "", "", round(nf_sys, 2), "DERIVED", "Friis; H1 (LTC5552 + 2 SPDT) gave 3.85 dB"])
ip1_feed = -16.0 - (-0.7 + 17.5)
rows.append(["RX", "RESULT input compression per feed", "", "", "", "", "", "DERIVED",
             f"ADAR1000 RX IP1dB -16 dBm (9.5 GHz) - 16.8 dB = {ip1_feed:.1f} dBm per feed; bench inputs must stay below"])
mix_in_max = ip1_feed + (-0.7 + 17.5 + 10.0 + 6.02 - 0.5 - 0.7 - 1.5 - 1.8)
rows.append(["RX", "RESULT mixer input at ADAR1000 compression (4 coherent elements)", "", "", "", "", "", "DERIVED",
             f"{mix_in_max:.1f} dBm vs LTC5553 input P1dB ~16 dBm -> mixer is not the RX compression limit"])

# ---------------------------------------------------------------- TX (target 10 dBm avg per feed)
target_feed = 10.0
fe_out = target_feed + 0.7
fe_in = fe_out - 21.5
rows.append(["TX", "target avg per feed (PROTOTYPE envelope)", "", "", "", "", "", "REQUIREMENT", "H1_1_POWER_ENVELOPES.md"])
mix_in = -10.0   # chosen mixer IF drive (avg)
mix_out = mix_in - 10.0
rf_io = mix_out - 0.7 - 1.5 - 1.8 - 0.5
adar_gain_needed = fe_in - rf_io
n310_out = mix_in + 1.9 + 0.5
tx = [
    ("USRP N310 TX/RX out (avg)", n310_out, "DERIVED", "N310 max 18 dBm at 1-4 GHz (datasheet v3) -> %.1f dB headroom for ~10 dB PAPR" % (18 - n310_out)),
    ("IF trace + DC block + BFCN-1840+", n310_out - 2.4, "DATASHEET+ASSUMPTION", "1.9 + 0.5 dB"),
    ("LTC5553 IF input (avg)", mix_in, "DESIGN CHOICE", "26 dB below upmix input P1dB 14.8 dBm (plot, IF 1.8 GHz); IM3 ~ 2x(25-(-10)) = 70 dBc"),
    ("LTC5553 RF out (avg)", mix_out, "PLOT", "upmix CL ~10.0 dB at IF 1.8 GHz (plot read, RF 9.8 GHz)"),
    ("ADAR1000 RF_IO in (after BPF, HPF, coupler, trace)", rf_io, "DATASHEET+ASSUMPTION", "-4.5 dB"),
    ("ADAR1000 required RF_IO->TXx gain", adar_gain_needed, "DERIVED", "max single-channel gain 21 dB at 9.5 GHz -> %.1f dB of gain backed off (attenuator/VGA range at 8.4 GHz UNVERIFIED)" % (21 - adar_gain_needed)),
    ("ADAR1000 TXx out = ADTR1107 TX_IN (avg)", fe_in, "DERIVED", "%.1f dB below ADAR1000 OP1dB 10 dBm (9.5 GHz)" % (10 - fe_in)),
    ("ADTR1107 ANT out (avg)", fe_out, "DATASHEET", "gain 21.5 dB; %.1f dB below OP1dB 23 dBm typ (%.1f dB below 21 dBm min)" % (23 - fe_out, 21 - fe_out)),
    ("feed (avg)", target_feed, "DERIVED", "PROTOTYPE >= 10 dBm met if OFDM EVM/ACLR allows ~12 dB back-off (bench C2)"),
]
for name, p, ev, src in tx:
    rows.append(["TX", name, "", "", "", round(p, 1), "", ev, src])
lo_leak_rf = -25.0
rows.append(["TX", "LO leakage at ADAR1000 RF_IO", "", "", "", round(lo_leak_rf - 22.0 - 18.85, 1), "", "DATASHEET+DERIVED",
             "LTC5553 LO-RF < -25 dBm (upmix, whole band); BFCN-8350+ ~22 dB (interp. 20.0@6.05/23.97@6.75 GHz) + HFCN-7150+ 18.85 dB @6.65 GHz -> %.0f dBc below wanted at RF_IO" % (rf_io - (lo_leak_rf - 22.0 - 18.85))])
rows.append(["TX", "NOTE", "", "", "", "", "", "ASSUMPTION", "converter T/R switches of H1 (2x ADRF5019) removed: passive LTC5553 is used bidirectionally and the N310 TX/RX port switches internally"])

with open(out / "H2A_RF_CASCADE_BUDGET.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["path", "stage", "gain_db", "nf_db", "op1db_dbm", "cum_gain_or_level", "cum_nf_db", "evidence", "source"]); w.writerows(rows)

# ---------------------------------------------------------------- LO budget
lo = []
for case, adf_set, adf_se, amp_g, amp_cap in (
        ("nominal", "RF_OUT_POWER=-1 dBm setting", 0.0, 13.5, 17.6),
        ("power-up default", "RF_OUT_POWER=5 dBm (reset default, RF_EN=1)", 4.0, 13.5, 17.6),
        ("low", "RF_OUT_POWER=-4 dBm setting", -5.0, 12.9, 17.6)):
    p = adf_se - 0.3
    amp_out = min(p + amp_g, amp_cap + 1.0)
    pad = amp_out - 3.0
    mix = pad - 9.4 - 1.0
    lo.append([case, adf_set, adf_se, round(p, 1), round(amp_out, 1), round(pad, 1), round(mix, 1),
               "OK" if -6 <= mix <= 6 else ("ABOVE RANGE, BELOW +10 dBm ABS MAX" if mix < 10 else "EXCEEDS ABS MAX")])
with open(out / "H2A_LO_BUDGET.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["case", "ADF4371 setting", "RF8P single-ended dBm (ASSUMPTION/PLOT)", "after 10 pF + trace", "AVA-183A+ out (gain interp. 5-8 GHz; P1dB ~17.6-18)",
                "after 3 dB pad", "per LTC5553 LO (EP4RKU+ 9.4 dB + 1 dB trace)", "vs LTC5553 LO range -6..+6 dBm (abs max +10)"])
    w.writerows(lo)
    w.writerow([])
    w.writerow(["note", "RF8P single-ended level at 6.6 GHz is not tabulated in ADF4371 Rev 0 (Fig 13 shows ~+6..7 dBm de-embedded, differential combined); AVA-183A+ has no spec between 5 and 8 GHz -> both need bench confirmation (C4)"])
    w.writerow(["note", "EP4RKU+ phase unbalance 1.9 deg typ / 19 deg max and amplitude 0.2/1.2 dB -> static, removed by the CAL-port calibration"])
    w.writerow(["note", "DC: ADF4371 ~0.9-1.3 W (AIDD 190-260 mA @3.3 V + VCO 135-180 mA @5 V + RF8 65 mA), AVA-183A+ 131-166 mA @5 V"])

# ---------------------------------------------------------------- spur table
LO, IF0, RF0 = 6.6, 1.8, 8.4
IFB, RFB = (1.75, 1.85), (8.35, 8.45)
sp = []
for m in range(0, 6):
    for n in range(0, 6):
        if m == 0 and n == 0:
            continue
        for sgn in (+1, -1):
            # TX: products of LO and IF at the mixer RF port
            for f_if in IFB:
                pass
            lo_ = m * LO + sgn * n * IF0
            if lo_ > 0 and (m, n, sgn) != (1, 1, +1):
                lo_lo = m * LO + sgn * n * IFB[0]; lo_hi = m * LO + sgn * n * IFB[1]
                a, b = sorted((lo_lo, lo_hi))
                near = not (b < 7.9 or a > 9.0)
                inband = not (b < RFB[0] or a > RFB[1])
                if near or (m <= 2 and n <= 2):
                    sp.append(["TX", f"{m}xLO {'+' if sgn > 0 else '-'} {n}xIF", round(a, 3), round(b, 3), "IN BAND" if inband else ("NEAR BAND" if near else "out of band"),
                               "wanted" if (m, n, sgn) == (1, 1, 1) else ""])
            # RX: products of LO and RF landing in the IF band
            f_lo = abs(m * LO + sgn * n * RFB[0]); f_hi = abs(m * LO + sgn * n * RFB[1])
            a, b = sorted((f_lo, f_hi))
            if not (b < 1.5 or a > 2.1) and (m, n) != (1, 1):
                sp.append(["RX", f"|{m}xLO {'+' if sgn > 0 else '-'} {n}xRF|", round(a, 3), round(b, 3),
                           "IN IF BAND" if not (b < IFB[0] or a > IFB[1]) else "NEAR IF BAND", ""])
# key individual frequencies
keys = [("TX/RX", "LO leakage", LO, LO, "out of band", "BFCN-8350+ ~22 dB (interp.) + HFCN-7150+ 18.85 dB"),
        ("TX", "image LO-IF", LO - IFB[1], LO - IFB[0], "out of band", "HFCN-7150+ 38.96 dB @4.54 GHz, 29.87 dB @5.1 GHz; BFCN-8350+ 20.28 dB @4.3 GHz"),
        ("RX", "image RF = LO-IF", LO - IFB[1], LO - IFB[0], "out of band", "same filters before the mixer + ADTR1107/ADAR1000 band edges (6/8 GHz)"),
        ("TX", "2xLO", 2 * LO, 2 * LO, "out of band", "BFCN-8350+ upper stop band 10.3-15.05 GHz 18 dB typ"),
        ("TX", "N310 2nd harmonic of IF", 2 * IFB[0], 2 * IFB[1], "out of band", "BFCN-1840+ stop band 3.5-5.7 GHz 25 dB typ"),
        ("TX", "2xLO-IF", 2 * LO - IFB[1], 2 * LO - IFB[0], "out of band", "BFCN-8350+ upper stop band"),
        ("TX", "LO+2xIF", LO + 2 * IFB[0], LO + 2 * IFB[1], "out of band", "BFCN-8350+ upper stop band 10.3-15.05 GHz")]
for k in keys:
    sp.append(list(k))
with open(out / "H2A_SPUR_TABLE.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["path", "product", "f_low_GHz", "f_high_GHz", "location", "rejection available / note"]); w.writerows(sp)
print(f"RX NF {nf_sys:.2f} dB; TX: N310 {n310_out:.1f} dBm avg, ADAR gain needed {adar_gain_needed:.1f} dB; LO per mixer {[r[6] for r in lo]}")
print("in-band spurs:", [r for r in sp if r[4] in ("IN BAND", "IN IF BAND")])
