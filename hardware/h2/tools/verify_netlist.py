#!/usr/bin/env python3
"""Verify the exported KiCad netlist against datasheet pin tables, the topology-A feed map and the
intended interfaces. Writes H2A_PIN_INTERFACE_VERIFICATION.csv; exit code 1 on any FAIL.

    python verify_netlist.py <netlist.xml> <build_log.json> <out.csv>
"""
import csv
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
PINS = HERE.parent / "datasheet_pins"
FEEDMAP = HERE.parent.parent / "H1_FEED_POLARIZATION_MAP.csv"
net_xml, log_json, out_csv = sys.argv[1:4]

root = ET.parse(net_xml).getroot()
comps = {c.get("ref"): c for c in root.iter("comp")}
pin_net = {}   # (ref, pin number) -> net name
pin_fn = {}    # (ref, pin number) -> pin function (name) as KiCad exported it
for n in root.iter("net"):
    for node in n.iter("node"):
        k = (node.get("ref"), node.get("pin"))
        pin_net[k] = n.get("name")
        pin_fn[k] = node.get("pinfunction") or ""
log = json.loads(Path(log_json).read_text())
rows = []


def add(check, item, expected, actual, ok, basis):
    rows.append({"check": check, "item": item, "expected": expected, "actual": actual,
                 "result": "PASS" if ok else "FAIL", "basis": basis})


def nets_of(ref, name):
    return {pin_net.get((ref, p)) for (r, p), f in pin_fn.items() if r == ref and f == name}


def net1(ref, name):
    s = nets_of(ref, name)
    return s.pop() if len(s) == 1 else ("<none>" if not s else "<split:" + "|".join(sorted(map(str, s))) + ">")


# 1. symbol fidelity: every pin number on every custom part carries the datasheet name
CSVS = {"ADAR1000": "adar1000", "ADTR1107": "adtr1107", "ADF4371": "adf4371", "LTC5553": "ltc5553",
        "BFCN-8350+": "bfcn8350", "BFCN-1840+": "bfcn1840", "HFCN-7150+": "hfcn7150", "EP4RKU+": "ep4rku",
        "EDC21-24+": "edc2124", "AVA-183A+": "ava183a"}
for ref, c in sorted(comps.items()):
    ls = c.find("libsource")
    part = ls.get("part") if ls is not None else ""
    if part not in CSVS:
        continue
    ds = {r["pin"]: r["name"] for r in csv.DictReader(open(PINS / f"{CSVS[part]}_pins.csv"))}
    lp = next(l for l in root.iter("libpart") if l.get("part") == part)
    got = {pn.get("num"): pn.get("name") for pn in lp.iter("pin")}  # symbol as embedded in the netlist
    for pin, name in ds.items():
        exp = "GND" if (pin == "EP" or name in ("EPAD",)) else name
        act = got.get(pin, "<missing in netlist>")
        add("symbol-pin", f"{ref}.{pin}", exp, act, act == exp, f"{CSVS[part]}_pins.csv")
    extra = set(got) - set(ds)
    add("symbol-pin-count", ref, str(len(ds)), str(len(got)), not extra and len(got) == len(ds), f"{CSVS[part]}_pins.csv")

# 2. topology-A feed ownership and per-branch RF/bias wiring
for f in csv.DictReader(open(FEEDMAP)):
    c, k, n = int(f["sim_chain"]) + 1, int(f["adar1000_channel"]), int(f["front_end_ref"].split("FE")[1])
    bf, fe, jf = f"UBF{c}", f"UFE{n}", f"JF{n}"
    basis = f"H1_FEED_POLARIZATION_MAP sim_feed {f['sim_feed_index']}"
    for a, b, src in ((f"TX{k}", "TX_IN", "ADTR1107 Fig 91 / ADAR1000 p44"), (f"RX{k}", "RX_OUT", "ADTR1107 Fig 91"),
                      (f"PA_BIAS{k}", "VGG_PA", "ADTR1107 p26 / Fig 91"), (f"DET{k}", "CPLR_OUT", "ADTR1107 p26"),
                      ("TR_SW_POS", "CTRL_SW", "ADTR1107 p26"), ("LNA_BIAS", "VGG_LNA", "ADTR1107 p26 (optional)")):
        na, nb = net1(bf, a), net1(fe, b)
        add("bf-fe", f"{bf}.{a} <-> {fe}.{b}", "same net", f"{na} / {nb}", na == nb and not na.startswith("<"), f"{basis}; {src}")
    na = net1(fe, "ANT")
    jn = pin_net.get((jf, "1"))
    val = comps[jf].findtext("value")
    want = f"FEED sim{f['sim_feed_index']} site{f['local_site']} {f['polarization']}"
    add("feed", f"{fe}.ANT -> {jf}", f"{want}", f"{val} on {na}", na == jn and val == want, basis)
    for pin, rail in (("VDD_PA", f"+5V_PA_C{c}"), ("VDD_LNA", "+3V3_RF"), ("VDD_SW", "+3V3_RF"), ("VSS_SW", "-3V3_SW"), ("GND", "GND"), ("NIC", "GND")):
        a = net1(fe, pin)
        add("rail", f"{fe}.{pin}", rail, a, a == rail, "ADTR1107 Rev C Fig 89 / p24")

# 3. per-chain converter, coupler, LO
for c in (1, 2, 3, 4):
    bf, mx, b = f"UBF{c}", f"UMX{c}", 100 * c
    chk = [
        ("RF path", (f"{mx}", "RF"), (f"FL{b + 2}", "RF_IN"), "LTC5553 RF -> BFCN-8350+"),
        ("RF path", (f"FL{b + 2}", "RF_OUT"), (f"FL{b + 3}", "RF_IN"), "BFCN-8350+ -> HFCN-7150+"),
        ("RF path", (f"FL{b + 3}", "RF_OUT"), (f"DC{800 + c}", "INPUT"), "HFCN-7150+ -> coupler INPUT"),
        ("RF path", (f"DC{800 + c}", "OUTPUT"), (bf, "RF_IO"), "coupler OUTPUT -> ADAR1000 RF_IO"),
        ("IF path", (f"FL{b + 1}", "RF_OUT"), (mx, "IF"), "BFCN-1840+ -> LTC5553 IF"),
        ("cal", (f"DC{800 + c}", "COUPLED"), ("U801", f"P{c}"), "coupler -> EP4RKU+ cal combiner"),
        ("LO", ("U503", f"P{c}"), (f"C{b + 32}", "1"), "LO splitter -> DC block"),
        ("LO", (f"C{b + 32}", "2"), (mx, "LO"), "DC block -> LTC5553 LO (5553f Fig 1 C1)"),
    ]
    for kind, (ra, pa), (rb, pb), basis in chk:
        na = net1(ra, pa) if not pa.isdigit() else pin_net.get((ra, pa), "<none>")
        nb = net1(rb, pb) if not pb.isdigit() else pin_net.get((rb, pb), "<none>")
        add(kind, f"{ra}.{pa} <-> {rb}.{pb}", "same net", f"{na} / {nb}", na == nb and not str(na).startswith("<"), basis)
    jn = pin_net.get((f"J{b + 1}", "1")); cn = pin_net.get((f"C{b + 31}", "1"))
    add("IF path", f"J{b + 1} (N310 IF) <-> C{b + 31} DC block", "same net", f"{jn} / {cn}", jn == cn, "chain IF interface")
    for pin, rail in (("AVDD3", "+3V3_RF"), ("AVDD1", "-5V_BF"), ("GND", "GND"), ("TR", "BF_TR"), ("PA_ON", "TX_ALLOW"),
                      ("TX_LOAD", "BF_TX_LOAD"), ("RX_LOAD", "BF_RX_LOAD"), ("SCLK", "BF_SCLK"), ("SDIO", "BF_SDIO"), ("CSB", f"BF_CS{c}_N")):
        a = net1(bf, pin)
        add("bf-control", f"{bf}.{pin}", rail, a, a == rail, "ADAR1000 Rev B pin table")
    want = ["GND", "+1V8_DIG"]
    for bit, pin in ((0, "ADDR0"), (1, "ADDR1")):
        e = want[(c - 1) >> bit & 1]
        a = net1(bf, pin)
        add("bf-address", f"{bf}.{pin}", e, a, a == e, "unique chip ID per ADAR1000 (DS p32)")
    for pin, rail in (("VCC", "+3V3_RF"), ("EN", "MIX_EN"), ("GND", "GND")):
        a = net1(mx, pin)
        add("mixer", f"{mx}.{pin}", rail, a, a == rail, "LTC5553 5553f")

# 4. safety interlocks
def drivers(net):
    return sorted(f"{r}.{p}" for (r, p), n in pin_net.items() if n == net)


for net, must in (("BF_TR", ["U704.4", "UBF1.N6", "UBF2.N6", "UBF3.N6", "UBF4.N6"]),
                  ("TX_ALLOW", ["U703.4", "U704.2", "UBF1.B3", "UBF2.B3", "UBF3.B3", "UBF4.B3"]),
                  ("PA_ARMED", ["U909.5", "U705.1"]),
                  ("PA_DRAIN_EN", ["R735.1", "R965.1", "U621.5", "U622.5", "U623.5", "U624.5"]),  # H2-C: U705 drives via R735; R965 pull-down
                  ("WDT_OK", ["U702.8", "U703.3", "U705.3"]),
                  ("NEG_OK", ["U912.4", "U705.6", "U911.6"])):  # H2-C: NEG_OK = IL_EN . GATES_OK from U912
    have = drivers(net)
    miss = [m for m in must if m not in have]
    add("safety", net, ", ".join(must), ", ".join(have), not miss, "H2A safety chain (mcu/power sheets)")
pd_nets = ["MCU_TX_EN", "MCU_PA_EN", "MIX_EN", "PLL_CE", "PWR_EN_3V3", "PWR_EN_NEG", "PWR_EN_5VPA", "PWR_EN_LO",
           "BF_TX_LOAD", "BF_RX_LOAD", "TDD_TR_IN", "TX_PERMIT_IN"]
for net in pd_nets:
    rs = [r for (r, p), n in pin_net.items() if n == net and r.startswith("R")]
    ok = any(pin_net.get((r, "2")) == "GND" or pin_net.get((r, "1")) == "GND" for r in rs)
    add("safety-default", f"{net} pull-down", "resistor to GND", ",".join(rs), ok, "default-off at reset")
for c in (1, 2, 3, 4):
    a = net1(f"UFE{4 * c}", "VDD_PA")
    sw = pin_net.get((f"U{620 + c}", "1"))
    add("safety", f"chain {c} PA drain", f"+5V_PA_C{c} from U{620 + c} VOUT only", f"{a} / {sw}", a == sw == f"+5V_PA_C{c}", "PA drain gated per chain")

# 4b. H2-B circuits (pin numbers: Device R/C/L 1/2; ADF4371 CPOUT 2, VTUNE 5; AVA-183A+ VD1 8, VD2 7;
#     TPS22810 WSON VOUT 1, QOD 2, CT 3, VIN 6; TPS3430 CWD 2, SET0 3, CRST 4, SET1 6, VDD1 1)
P = lambda r, p: pin_net.get((r, p), "<none>")
h2b = [
    ("loop filter", "CPOUT-C1-R2-R3", P("U501", "2") == P("C509", "1") == P("R507", "1") == P("R508", "1") != "<none>", "tools/loop_filter.py (DERIVED)"),
    ("loop filter", "R2-C2 series", P("R507", "2") == P("C510", "1") != "<none>", "3rd-order passive"),
    ("loop filter", "R3-C3-VTUNE", P("R508", "2") == P("C511", "1") == P("U501", "5") != "<none>", "3rd-order passive"),
    ("loop filter", "C1/C2/C3 to GND", P("C509", "2") == P("C510", "2") == P("C511", "2") == "GND", "3rd-order passive"),
    ("LO amp bias", "VD1-C4(0.1u)-L1", P("U502", "8") == P("C512", "1") == P("L505", "1") != "<none>", "AVA-183A+ Fig 2"),
    ("LO amp bias", "VD2-C3-C2-C1-L1-+5V_LO", P("U502", "7") == P("L505", "2") == P("C513", "1") == P("C514", "1") == P("C515", "1") == "+5V_LO", "AVA-183A+ Fig 2"),
    ("watchdog", "CWD 10k to VDD, CRST 10k to VDD", P("R705", "1") == P("R706", "1") == "+1V8_DIG" and P("R705", "2") == P("U702", "2") and P("R706", "2") == P("U702", "4"), "TPS3430 Table 6.6"),
    ("watchdog", "SET0 = SET1 = GND (cannot be disabled)", P("U702", "3") == P("U702", "6") == "GND", "TPS3430 Table 6.6"),
]
for c in (1, 2, 3, 4):
    u = f"U{620 + c}"
    h2b += [("PA switch", f"{u} QOD tied to VOUT", P(u, "2") == P(u, "1") == f"+5V_PA_C{c}", "TPS22810 pin table option 2"),
            ("PA switch", f"{u} CT 2200 pF to GND", P(u, "3") == P(f"C{620 + c}", "1") and P(f"C{620 + c}", "2") == "GND", "TPS22810 test condition"),
            ("PA switch", f"{u} CIN 1 uF on VIN", P(u, "6") == P(f"C{624 + c}", "1") and P(f"C{624 + c}", "2") == "GND", "TPS22810 CIN")]
for kind, item, ok, basis in h2b:
    add(kind, item, "connected as specified", "ok" if ok else "MISMATCH", ok, basis)

# 5. unconnected pins must all be declared UNRESOLVED
unc = sorted(k for k, n in pin_net.items() if n.startswith("unconnected-"))
declared = {u["ref"] for u in log["unresolved"]}
extra = json.load(open(sys.argv[4])) if len(sys.argv) > 4 else {}  # datasheet-permitted open pins (H2-C)
for ref, pin in unc:
    hit = f"{ref}.{pin}" in extra or any(ref == d or ref in d.replace("-", "/").split("/") for d in declared)
    add("unconnected", f"{ref}.{pin} ({pin_fn[(ref, pin)]})", "declared UNRESOLVED", "declared" if hit else "NOT declared", hit, "build_log.json")

with open(out_csv, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader(); w.writerows(rows)
fails = [r for r in rows if r["result"] == "FAIL"]
by = {}
for r in rows:
    by.setdefault(r["check"], [0, 0])[r["result"] == "FAIL"] += 1
print(json.dumps({k: {"pass": v[0], "fail": v[1]} for k, v in by.items()}))
for r in fails[:40]:
    print("FAIL", r["check"], r["item"], "| expected", r["expected"], "| got", r["actual"])
sys.exit(1 if fails else 0)
