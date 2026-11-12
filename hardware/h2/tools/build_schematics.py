#!/usr/bin/env python3
"""Build the OpenRU-X6 H2-A preliminary tile schematic (KiCad 9) from verified pin tables.

All KiCad files are written through the mcp-server-kicad (v0.21.1) tool functions, never by
hand. Custom symbols are generated only from hardware/h2/datasheet_pins/*_pins.csv, which were
transcribed from manufacturer datasheets (see H2A_SOURCE_MANIFEST.md). Anything that could not
be verified is left UNCONNECTED and listed in UNRESOLVED (ERC then reports it) rather than
being guessed.

Usage (needs kicad-cli on PATH or KICAD_CLI_PATH, and KICAD_SYMBOL_DIR = KiCad 9 symbol libs):
    python build_schematics.py <output_dir>
"""
import csv
import json
import math
import os
import re
import sys
from pathlib import Path

from mcp_server_kicad import project as P
from mcp_server_kicad import schematic as S
from mcp_server_kicad import symbol as SY

HERE = Path(__file__).resolve().parent
PINS = HERE.parent / "datasheet_pins"
FEEDMAP = HERE.parent.parent / "H1_FEED_POLARIZATION_MAP.csv"
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE.parent / "schematics"
KLIB = Path(os.environ["KICAD_SYMBOL_DIR"])
NAME = "openru_x6_tile"
PRO = str(OUT / f"{NAME}.kicad_pro")
ROOT = str(OUT / f"{NAME}.kicad_sch")
CLIB = str(OUT / "openru_x6.kicad_sym")

UNRESOLVED = []   # (sheet, ref, item, reason)
DECISIONS = []    # (sheet, ref, decision, basis)
PLACED = {}       # ref -> dict(lib_id, value, sheet, mpn, footprint)

# ----------------------------------------------------------------------------- symbols
GRID = 2.54
GND_NAMES = {"GND", "EPAD"}


def _snap(v):
    return round(v / GRID) * GRID


def make_symbol(name, csv_file, prefix="U", value_note="", datasheet="~"):
    """Generate a symbol from a datasheet pin CSV. Same-named pins are stacked at one point."""
    rows = list(csv.DictReader(open(PINS / csv_file)))
    groups = {"L": [], "R": [], "T": [], "B": [], "NC": []}
    seen = {}
    for r in rows:
        n, t = r["name"], r["kicad_type"]
        if n in ("EPAD", "EP") or (r["pin"] == "EP" and t == "power_in"):
            n = "GND"  # every exposed pad in these datasheets is specified as RF/DC ground
        if t == "no_connect":
            t = "unconnected"
        if n in GND_NAMES or (n == "NIC"):
            side = "B"
        elif t == "unconnected":
            side = "NC"
        elif t in ("power_in", "power_out"):
            side = "T"
        elif t in ("input", "passive"):
            side = "L"
        else:
            side = "R"
        key = (side, n)
        if key not in seen:
            seen[key] = []
            groups[side].append(n)
        seen[key].append((r["pin"], t))
    nL, nR = len(groups["L"]), len(groups["R"])
    nT, nB = len(groups["T"]), len(groups["B"]) + len(groups["NC"])
    maxlen = max([len(n) for n in groups["L"] + groups["R"]] + [4])
    half_w = max(_snap((max(nT, nB) + 1) * GRID / 2 + GRID), _snap(maxlen * 1.27 + 2 * GRID), 5 * GRID)
    half_h = max(_snap((max(nL, nR) + 1) * GRID / 2 + GRID), 4 * GRID)
    L = GRID * 2
    pins = []

    def column(names, x, rot, side):
        y0 = _snap((len(names) - 1) * GRID / 2)
        for i, n in enumerate(names):
            for num, t in seen[(side, n)]:
                pins.append({"number": num, "name": n, "type": t, "x": x, "y": y0 - i * GRID, "rotation": rot, "length": L})

    def row(names, y, rot, side_of):
        x0 = -_snap((len(names) - 1) * GRID / 2)
        for i, n in enumerate(names):
            for num, t in seen[(side_of(n), n)]:
                pins.append({"number": num, "name": n, "type": t, "x": x0 + i * GRID * 2 if len(names) * 2 * GRID < 2 * half_w else x0 + i * GRID, "y": y, "rotation": rot, "length": L})

    column(groups["L"], -(half_w + L), 0, "L")
    column(groups["R"], half_w + L, 180, "R")
    # top row: power pins (2-grid spacing where it fits)
    tn = groups["T"]
    step = 2 * GRID if (len(tn) * 2 * GRID) < 2 * half_w else GRID
    x0 = -_snap((len(tn) - 1) * step / 2)
    for i, n in enumerate(tn):
        for num, t in seen[("T", n)]:
            pins.append({"number": num, "name": n, "type": t, "x": x0 + i * step, "y": half_h + L, "rotation": 270, "length": L})
    bn = [("B", n) for n in groups["B"]] + [("NC", n) for n in groups["NC"]]
    step = 2 * GRID
    x0 = -_snap((len(bn) - 1) * step / 2)
    for i, (sd, n) in enumerate(bn):
        for num, t in seen[(sd, n)]:
            pins.append({"number": num, "name": n, "type": t, "x": x0 + i * step, "y": -(half_h + L), "rotation": 90, "length": L})
    SY.add_symbol(name, pins, reference_prefix=prefix, footprint="", datasheet=datasheet,
                  rectangles=[{"x1": -half_w, "y1": half_h, "x2": half_w, "y2": -half_h, "fill": "background"}],
                  symbol_lib_path=CLIB)
    return {"w": 2 * (half_w + L), "h": 2 * (half_h + L)}


def make_placeholder(name, pins_spec, prefix="U"):
    """Explicit TBD block (not a real part): pins_spec = [(num, name, type, side)]."""
    pins = []
    cnt = {"L": 0, "R": 0, "B": 0}
    for num, n, t, side in pins_spec:
        i = cnt[side]; cnt[side] += 1
        if side == "L":
            pins.append({"number": num, "name": n, "type": t, "x": -12.7, "y": 5.08 - i * 2.54, "rotation": 0, "length": 5.08})
        elif side == "R":
            pins.append({"number": num, "name": n, "type": t, "x": 12.7, "y": 5.08 - i * 2.54, "rotation": 180, "length": 5.08})
        else:
            pins.append({"number": num, "name": n, "type": t, "x": i * 2.54, "y": -12.7, "rotation": 90, "length": 5.08})
    SY.add_symbol(name, pins, reference_prefix=prefix, symbol_lib_path=CLIB,
                  rectangles=[{"x1": -7.62, "y1": 7.62, "x2": 7.62, "y2": -7.62, "fill": "background"}])


# ----------------------------------------------------------------------------- sheet helper
class Sheet:
    def __init__(self, path, title):
        self.path = str(path)
        self.title = title
        self.nets = {}        # name -> [pinref]
        self.glob = set()     # net names that are global
        self.nc = []          # (ref, pin)
        self.glob_done = {}
        self.cx = 210  # A3 centre; A2 sheets override

    def place(self, lib_id, ref, value, x, y, rot=0, mpn="", fp=""):
        lib, sym = lib_id.split(":")
        libpath = CLIB if lib == "openru_x6" else str(KLIB / f"{lib}.kicad_sym")
        S.place_component(lib_id, ref, value, x, y, rotation=rot, symbol_lib_path=libpath,
                          schematic_path=self.path, project_path=PRO)
        if fp:
            S.set_component_property(ref, "Footprint", fp, schematic_path=self.path)
        if mpn:
            S.set_component_property(ref, "MPN", mpn, schematic_path=self.path)
        PLACED[ref] = {"lib_id": lib_id, "value": value, "sheet": Path(self.path).name, "mpn": mpn or value, "footprint": fp}
        return ref

    def flag(self, ref, net, x, y):
        S.add_power_symbol("power:PWR_FLAG", ref, x, y, symbol_lib_path=str(KLIB / "power.kicad_sym"),
                           schematic_path=self.path, project_path=PRO)
        self.conn(net, f"{ref}.1", g=not net.startswith(("+5V_PA_IN", "PCA_")))

    def conn(self, net, *pins, g=False):
        for p in pins:
            ref, pin = p.split(".", 1)
            self.nets.setdefault(net, []).append({"reference": ref, "pin": pin})
        if g:
            self.glob.add(net)

    def noconn(self, ref, pin):
        self.nc.append((ref, pin))

    def note(self, text, x, y):
        # add_text centres the string on x; centre notes on the page so long ones stay inside the frame
        S.add_text(text, self.cx, y, schematic_path=self.path)

    def flush(self):
        for net, pins in self.nets.items():
            res = S.wire_pins_to_net(pins, net, schematic_path=self.path)
            if net in self.glob:
                # replace every local label this call wrote with a global label at the same point,
                # so no sheet carries a local and a global label of one name (ERC same_local_global_label)
                spots = [(float(x), float(y), {"right": 0, "up": 90, "left": 180, "down": 270}[d]) for d, x, y in
                         re.findall(r"stub (\w+) [\d.]+ mm from \([\d.]+, [\d.]+\) to \(([\d.]+), ([\d.]+)\), label '", res)]
                spots += [(float(x), float(y), 0) for x, y in re.findall(r"label '[^']*' on the pin end \(([\d.]+), ([\d.]+)\)", res)]
                if not spots and not self.glob_done.get(net):
                    raise RuntimeError(f"no label written for global net {net} on {self.path}: {res}")
                for x, y, rot in spots:
                    S.remove_label(net, x, y, schematic_path=self.path)
                    S.add_global_label(net, x, y, rotation=rot, shape="passive", schematic_path=self.path)
                self.glob_done[net] = True
        for ref, pin in self.nc:
            S.no_connect_pin(ref, pin, schematic_path=self.path)


def unresolved(sheet, ref, item, reason):
    UNRESOLVED.append({"sheet": Path(sheet.path).name, "ref": ref, "item": item, "reason": reason})


def decision(sheet, ref, text, basis):
    DECISIONS.append({"sheet": Path(sheet.path).name, "ref": ref, "decision": text, "basis": basis})


C0402, R0402, L0402 = "Capacitor_SMD:C_0402_1005Metric", "Resistor_SMD:R_0402_1005Metric", "Inductor_SMD:L_0402_1005Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"


def cap(sh, ref, val, x, y, a, b, mpn="", fp=C0402):
    sh.place("Device:C", ref, val, x, y, mpn=mpn, fp=fp)
    sh.conn(a[0], f"{ref}.1", g=a[1]); sh.conn(b[0], f"{ref}.2", g=b[1])


def res(sh, ref, val, x, y, a, b, mpn="", fp=R0402):
    sh.place("Device:R", ref, val, x, y, mpn=mpn, fp=fp)
    sh.conn(a[0], f"{ref}.1", g=a[1]); sh.conn(b[0], f"{ref}.2", g=b[1])


def ind(sh, ref, val, x, y, a, b, mpn="", fp=L0402):
    sh.place("Device:L", ref, val, x, y, mpn=mpn, fp=fp)
    sh.conn(a[0], f"{ref}.1", g=a[1]); sh.conn(b[0], f"{ref}.2", g=b[1])


G = True   # global net marker
GND = ("GND", G)


# ----------------------------------------------------------------------------- build
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    os.chdir(OUT)  # add_hierarchical_sheet resolves sheet files against the CWD
    P.create_project(str(OUT), NAME)
    P.create_symbol_library(CLIB)
    feeds = list(csv.DictReader(open(FEEDMAP)))
    ADI = "https://www.analog.com/media/en/technical-documentation/data-sheets/"
    MC = "https://www.minicircuits.com/pdfs/"
    make_symbol("ADAR1000", "adar1000_pins.csv", datasheet=ADI + "adar1000.pdf")
    make_symbol("ADTR1107", "adtr1107_pins.csv", datasheet=ADI + "adtr1107.pdf")
    make_symbol("ADF4371", "adf4371_pins.csv", datasheet=ADI + "adf4371.pdf")
    make_symbol("LTC5553", "ltc5553_pins.csv", datasheet=ADI + "ltc5553.pdf")
    make_symbol("BFCN-8350+", "bfcn8350_pins.csv", prefix="FL", datasheet=MC + "BFCN-8350+.pdf")
    make_symbol("BFCN-1840+", "bfcn1840_pins.csv", prefix="FL", datasheet=MC + "BFCN-1840+.pdf")
    make_symbol("HFCN-7150+", "hfcn7150_pins.csv", prefix="FL", datasheet=MC + "HFCN-7150+.pdf")
    make_symbol("EP4RKU+", "ep4rku_pins.csv", datasheet=MC + "EP4RKU+.pdf")
    make_symbol("EDC21-24+", "edc2124_pins.csv", prefix="DC", datasheet=MC + "EDC21-24+.pdf")
    make_symbol("AVA-183A+", "ava183a_pins.csv", datasheet=MC + "AVA-183A+.pdf")
    make_placeholder("TBD_REG_POS", [("1", "VIN", "power_in", "L"), ("2", "EN", "input", "L"), ("3", "VOUT", "power_out", "R"), ("4", "PG", "open_collector", "R"), ("5", "GND", "power_in", "B")])
    make_placeholder("TBD_REG_NEG", [("1", "VIN", "power_in", "L"), ("2", "EN", "input", "L"), ("3", "VOUT", "power_out", "R"), ("4", "GND", "power_in", "B")])
    make_placeholder("TBD_NEG_RAIL_MON", [("1", "SENSE_5V", "input", "L"), ("2", "SENSE_3V3", "input", "L"), ("3", "VDD", "power_in", "L"), ("4", "OK", "open_collector", "R"), ("5", "GND", "power_in", "B")])
    P.create_sym_lib_table(str(OUT), [{"name": "openru_x6", "uri": "${KIPRJMOD}/openru_x6.kicad_sym"}] + [
        {"name": n, "uri": "${KICAD9_SYMBOL_DIR}/%s.kicad_sym" % n} for n in
        ("Device", "Connector", "Connector_Generic", "power", "74xGxx", "Power_Management", "Power_Supervisor",
         "Sensor_Energy", "Sensor_Temperature", "Interface", "MCU_ST_STM32G4")])

    def sub(parent, name, fname, x, y):
        P.create_schematic(str(OUT / fname))
        P.add_hierarchical_sheet(parent, name, fname, [], x=x, y=y, project_path=PRO)
        S.set_page_size("A3", schematic_path=str(OUT / fname))
        return Sheet(OUT / fname, name)

    S.set_page_size("A3", schematic_path=ROOT)
    sheets = []
    # ---------------------------------------------------------------- per-chain sheets (1-4)
    for c in (1, 2, 3, 4):
        ch = sub(ROOT, f"RF_CHAIN_{c}", f"chain{c}.kicad_sch", 30 + (c - 1) * 60, 40)
        bf = sub(ch.path, f"BF_{c}", f"bf{c}.kicad_sch", 40, 40)
        fe = sub(ch.path, f"FE_{c}", f"fe{c}.kicad_sch", 100, 40)
        cv = sub(ch.path, f"CONV_{c}", f"conv{c}.kicad_sch", 160, 40)
        sheets += [ch, bf, fe, cv]
        b = 100 * c  # passive numbering block for this chain
        # -- chain sheet: N310 IF connector
        j = f"J{b + 1}"
        ch.place("Connector:Conn_Coaxial", j, f"SMA IF{c} (N310 ch{c - 1})", 120, 140)
        ch.conn(f"C{c}_IF_N310", f"{j}.1", g=G); ch.conn("GND", f"{j}.2", g=G)
        ch.note(f"RF chain {c} (topology A): N310 ch{c - 1} IF 1.8 GHz <-> LTC5553 <-> 8.4 GHz <-> cal coupler <-> ADAR1000 UBF{c} <-> 4x ADTR1107 <-> 4 feeds.", 25, 20)
        ch.note("SMA footprint (edge-launch vs vertical) UNRESOLVED.", 100, 160)
        unresolved(ch, j, "footprint", "SMA connector type/footprint not selected")
        # -- BF sheet (sheet 2)
        u = f"UBF{c}"
        bf.place("openru_x6:ADAR1000", u, "ADAR1000ACCZN", 200, 140, mpn="ADAR1000ACCZN")
        bf.conn(f"C{c}_RFIO_BF", f"{u}.RF_IO", g=G)
        for k in (1, 2, 3, 4):
            bf.conn(f"C{c}_TX{k}", f"{u}.TX{k}", g=G)
            bf.conn(f"C{c}_RX{k}", f"{u}.RX{k}", g=G)
            bf.conn(f"C{c}_PABIAS{k}", f"{u}.PA_BIAS{k}", g=G)
            bf.conn(f"C{c}_DET{k}", f"{u}.DET{k}", g=G)
        bf.conn(f"C{c}_LNABIAS", f"{u}.LNA_BIAS", g=G)
        bf.conn(f"C{c}_TRSW", f"{u}.TR_SW_POS", g=G)
        bf.noconn(u, "TR_SW_NEG"); bf.noconn(u, "TR_POL")
        bf.conn("TX_ALLOW", f"{u}.PA_ON", g=G)
        bf.conn("BF_TR", f"{u}.TR", g=G)
        bf.conn("BF_TX_LOAD", f"{u}.TX_LOAD", g=G)
        bf.conn("BF_RX_LOAD", f"{u}.RX_LOAD", g=G)
        bf.conn(f"BF_CS{c}_N", f"{u}.CSB", g=G)
        bf.conn("BF_SCLK", f"{u}.SCLK", g=G)
        bf.conn("BF_SDIO", f"{u}.SDIO", g=G)
        bf.conn("+3V3_RF", f"{u}.AVDD3", g=G)
        bf.conn("-5V_BF", f"{u}.AVDD1", g=G)
        bf.conn("GND", f"{u}.GND", g=G)
        addr = c - 1
        bf.conn("+1V8_DIG" if addr & 1 else "GND", f"{u}.ADDR0", g=G)
        bf.conn("+1V8_DIG" if addr & 2 else "GND", f"{u}.ADDR1", g=G)
        decision(bf, u, f"ADDR1:ADDR0 = {addr >> 1}{addr & 1} (chip ID {addr}); four chips share SCLK/SDIO, one CSB each",
                 "ADAR1000 Rev B p14, p32: up to 4 chips per bus, header bits[14:13]")
        rs = f"R{b + 1}"
        res(bf, rs, "50", 260, 200, (f"C{c}_SDO_RAW", False), ("BF_SDO", G))
        bf.conn(f"C{c}_SDO_RAW", f"{u}.SDO")
        decision(bf, rs, "50 ohm series resistor SDO -> shared MISO", "ADAR1000 Rev B p49 Fig 106 recommendation")
        for i, pin in enumerate(("CREG1", "CREG2", "CREG3", "CREG4")):
            cr = f"C{b + 1 + i}"
            cap(bf, cr, "1uF", 100 + i * 15, 220, (f"C{c}_{pin}", False), GND, fp=C0603)
            bf.conn(f"C{c}_{pin}", f"{u}.{pin}")
        decision(bf, f"C{b + 1}-C{b + 4}", "1 uF on each CREG1-4", "ADAR1000 Rev B p14")
        bf.note("UNRESOLVED: AVDD3 / AVDD1 bypass capacitor values are not given in the ADAR1000 datasheet -> take from ADAR1000-EVALZ schematic.", 25, 20)
        bf.note("PA_BIASx = 0 V at power-up (DS p41): PA drain stays OFF until firmware sets PA_BIAS OFF = -1.75 V (ADTR1107 VGG_PA abs max -2 V).", 25, 25)
        bf.note("SDO errata (DS p47-49): non-addressed SDO not tristated -> read back one chip at a time (separate CSB).", 25, 30)
        unresolved(bf, u, "AVDD1/AVDD3 decoupling", "values not in ADAR1000 Rev B; need ADAR1000-EVALZ schematic")
        unresolved(bf, u, "footprint", "88-terminal LGA CC-88-1 land pattern only as image in DS; use ADI footprint")
        # -- FE sheet (sheet 3): 4 ADTR1107 branches
        for k in (1, 2, 3, 4):
            n = 4 * (c - 1) + k
            f = next(r for r in feeds if r["front_end_ref"] == f"U_FE{n}")
            assert f["adar1000_ref"] == f"U_BF{c}" and f["adar1000_channel"] == str(k)
            u = f"UFE{n}"
            x = 60 + (k - 1) * 90
            fe.place("openru_x6:ADTR1107", u, "ADTR1107ACCZ", x, 110, mpn="ADTR1107ACCZ")
            fe.conn(f"C{c}_TX{k}", f"{u}.TX_IN", g=G)
            fe.conn(f"C{c}_RX{k}", f"{u}.RX_OUT", g=G)
            fe.conn(f"C{c}_PABIAS{k}", f"{u}.VGG_PA", g=G)
            fe.conn(f"C{c}_DET{k}", f"{u}.CPLR_OUT", g=G)
            fe.conn(f"C{c}_LNABIAS", f"{u}.VGG_LNA", g=G)
            fe.conn(f"C{c}_TRSW", f"{u}.CTRL_SW", g=G)
            fe.conn(f"+5V_PA_C{c}", f"{u}.VDD_PA", g=G)
            fe.conn("+3V3_RF", f"{u}.VDD_LNA", f"{u}.VDD_SW", g=G)
            fe.conn("-3V3_SW", f"{u}.VSS_SW", g=G)
            fe.conn("GND", f"{u}.GND", f"{u}.NIC", g=G)
            cg = f"C{b + 10 + k}"
            cap(fe, cg, "10nF", x + 25, 150, (f"C{c}_PABIAS{k}", G), GND)
            jf = f"JF{n}"
            fe.place("Connector:Conn_Coaxial", jf, f"FEED sim{f['sim_feed_index']} site{f['local_site']} {f['polarization']}", x, 190)
            fe.conn(f"C{c}_ANT{k}", f"{u}.ANT", f"{jf}.1"); fe.conn("GND", f"{jf}.2", g=G)
            unresolved(fe, jf, "antenna interface", "feed connector/antenna EM design not done (H1 M6)")
        decision(fe, f"C{b + 11}-C{b + 14}", "10 nF on each VGG_PA", "ADTR1107 Rev C Fig 89")
        rp, rd = f"R{b + 20}", f"R{b + 21}"
        res(fe, rp, "100k", 30, 230, (f"C{c}_TRSW", G), ("+3V3_RF", G))
        res(fe, rd, "10k", 50, 230, (f"C{c}_LNABIAS", G), GND)
        decision(fe, rp, "100k pull-up on CTRL_SW net -> RX (CTRL_SW high) while TR_SW_POS floats at power-up",
                 "ADAR1000 Rev B p41 (TR_SW_POS floating at power-up); ADTR1107 Rev C Table 8 (high = receive). Value is a design choice (33 uA load)")
        decision(fe, rd, "10k to GND on VGG_LNA net -> 0 V self-bias while LNA_BIAS is high-Z; LNA_BIAS can still pull to -2 V (0.8 mA for 4 gates)",
                 "ADTR1107 Rev C p24 self-bias at VGG_LNA = 0 V; ADAR1000 Rev B p41 LNA_BIAS floating at power-up, p45 OFF = 0x68 (~-2 V). Value is a design choice")
        fe.note("UNRESOLVED: VDD_PA / VDD_LNA / VDD_SW / VSS_SW bypass values not in ADTR1107 Rev C (Fig 89 shows only 10 nF on VGG_PA).", 25, 20)
        fe.note("Feed ownership = H1_FEED_POLARIZATION_MAP.csv (topology A). LNA kept powered in TX and pinched via LNA_BIAS (Stingray style) - confirm with ADI (ADTR1107 TX sequence lists VDD_LNA = 0 V).", 25, 25)
        unresolved(fe, f"UFE{4 * c - 3}-UFE{4 * c}", "VDD_PA/VDD_LNA/VDD_SW/VSS_SW decoupling", "values not in ADTR1107 Rev C; need ADTR1107-EVAL schematic")
        unresolved(fe, f"UFE{4 * c - 3}-UFE{4 * c}", "LNA supply in TX", "ADTR1107 TX power-up sequence sets VDD_LNA = 0 V; design keeps 3.3 V and pinches gate via LNA_BIAS (ADAR1000 p45). Needs ADI confirmation")
        # -- CONV sheet (sheet 4)
        u, fi, fr, fh = f"UMX{c}", f"FL{b + 1}", f"FL{b + 2}", f"FL{b + 3}"
        cv.place("openru_x6:LTC5553", u, "LTC5553IUDB", 200, 120, mpn="LTC5553IUDB#PBF")
        cv.place("openru_x6:BFCN-1840+", fi, "BFCN-1840+", 90, 120, mpn="BFCN-1840+")
        cv.place("openru_x6:BFCN-8350+", fr, "BFCN-8350+", 290, 120, mpn="BFCN-8350+")
        cv.place("openru_x6:HFCN-7150+", fh, "HFCN-7150+", 360, 120, mpn="HFCN-7150+")
        cap(cv, f"C{b + 31}", "18pF", 40, 160, (f"C{c}_IF_N310", G), (f"C{c}_IF_FILT", False), mpn="GJM1555C1H180FB01")
        decision(cv, f"C{b + 31}", "18 pF DC block on N310 IF line", "LTC5553 IF port DC-grounded (~6.2 ohm), abs max +-0.1 V DC; DC block needed if source carries DC (DS p8/p10). N310 port DC state UNRESOLVED")
        cv.conn(f"C{c}_IF_FILT", f"{fi}.RF_IN"); cv.conn(f"C{c}_IF_MIX", f"{fi}.RF_OUT", f"{u}.IF")
        cv.conn(f"C{c}_RF_MIX", f"{u}.RF", f"{fr}.RF_IN"); cv.conn(f"C{c}_RF_BPF", f"{fr}.RF_OUT", f"{fh}.RF_IN")
        cv.conn(f"C{c}_RFIO_MIX", f"{fh}.RF_OUT", g=G)
        cap(cv, f"C{b + 32}", "18pF", 160, 170, (f"C{c}_LO", G), (f"C{c}_LO_MIX", False), mpn="0402ZK180GBS")
        cv.conn(f"C{c}_LO_MIX", f"{u}.LO")
        cap(cv, f"C{b + 33}", "18pF", 230, 170, ("+3V3_RF", G), GND, mpn="GJM1555C1H180FB01")
        cap(cv, f"C{b + 34}", "1uF", 245, 170, ("+3V3_RF", G), GND, mpn="GRM188R71A105KA61", fp=C0603)
        cv.conn("+3V3_RF", f"{u}.VCC", g=G)
        cv.conn("MIX_EN", f"{u}.EN", g=G)
        cv.conn("GND", f"{u}.GND", f"{fi}.GND", f"{fr}.GND", f"{fh}.GND", g=G)
        decision(cv, f"C{b + 32}-C{b + 34}", "LO DC block 18 pF; VCC 18 pF + 1 uF", "LTC5553 5553f Fig 1 test circuit (C1, C2, C3)")
        decision(cv, u, "EN driven by MIX_EN (MCU GPIO + pull-down); internal 376k pull-down -> mixer off at reset", "LTC5553 5553f EN spec")
        cv.note("IF 1.75-1.85 GHz: N310 <-> DC block <-> BFCN-1840+ <-> LTC5553 IF (single-ended 50 ohm, no balun).", 25, 20)
        cv.note("RF: LTC5553 RF <-> BFCN-8350+ <-> HFCN-7150+ <-> cal coupler (cal sheet) <-> ADAR1000 RF_IO. No DC blocks: RF_IO and LTC5553 RF are both DC-grounded.", 25, 25)
        unresolved(cv, u, "footprint", "UDB 12-lead 3x2 QFN; use ADI land pattern")

    # ---------------------------------------------------------------- LO sheet (5)
    lo = sub(ROOT, "LO_SYNTH", "lo.kicad_sch", 30, 120); sheets.append(lo)
    u = "U501"
    lo.place("openru_x6:ADF4371", u, "ADF4371BCCZ", 120, 130, mpn="ADF4371BCCZ")
    avdd = ["VCC_CAL", "VCC_X4", "VDD_X4", "VCC_X1", "VDD_X1", "VCC_X2", "VCC_MUX", "VCC_3V", "VDD_NDIV", "VDD_LS", "VCC_LDO_3V", "VCC_REF", "VDD_PFD", "VDD_VP"]
    lo.conn("+3V3_LO", *[f"{u}.{p}" for p in avdd], g=G)
    lo.conn("+5V_LO", f"{u}.VCC_VCO", f"{u}.VCC_LDO", g=G)
    lo.noconn(u, "VCC_REG_OUT")
    lo.conn("GND", f"{u}.GND", f"{u}.TEST", g=G)
    cap(lo, "C501", "1uF", 60, 200, ("+5V_LO", G), GND, fp=C0603)
    cap(lo, "C502", "1uF", 75, 200, ("+3V3_LO", G), GND, fp=C0603)
    decision(lo, "C501/C502", "1 uF on 5 V VCO supply; 1 uF on VDD_VP; VCC_REG_OUT open; VCC_VCO and VCC_LDO on external 5 V LDO", "ADF4371 Rev 0 p9-10, p24")
    lo.conn("PLL_CE", f"{u}.CE", g=G)
    lo.conn("PLL_CS_N", f"{u}.CS", g=G); lo.conn("BF_SCLK", f"{u}.SCLK", g=G); lo.conn("BF_SDIO", f"{u}.SDIO", g=G)
    res(lo, "R501", "1k", 200, 200, ("PLL_MUXOUT_RAW", False), ("PLL_MUXOUT", G))
    lo.conn("PLL_MUXOUT_RAW", f"{u}.MUXOUT")
    decision(lo, "R501", "1k series on MUXOUT", "MUXOUT may drive 3.3 V (LEV_SEL default) into 1.8 V MCU pin before firmware sets LEV_SEL; current limit. Design choice")
    cap(lo, "C503", "100nF", 30, 100, ("REF_10M", G), ("PLL_REFP", False))
    cap(lo, "C504", "100nF", 30, 150, ("PLL_REFN", False), GND)
    lo.conn("PLL_REFP", f"{u}.REFP"); lo.conn("PLL_REFN", f"{u}.REFN")
    decision(lo, "C503/C504", "Single-ended 10 MHz on REFP (ac-coupled), REFN ac-coupled to GND; PFD 10 MHz integer-N (N=660 for 6.6 GHz)", "ADF4371 Rev 0 p10, p19 (SE 10-500 MHz). Cap value 100 nF is a design choice")
    # RF8P (used) / RF8N (terminated)
    ind(lo, "L501", "7.5nH", 200, 80, ("+3V3_LO", G), ("PLL_RF8P", False))
    ind(lo, "L502", "7.5nH", 215, 80, ("+3V3_LO", G), ("PLL_RF8N", False))
    cap(lo, "C505", "10pF", 230, 100, ("PLL_RF8P", False), ("LO_AMP_IN", False))
    cap(lo, "C506", "10pF", 245, 100, ("PLL_RF8N", False), ("PLL_RF8N_T", False))
    res(lo, "R502", "49.9", 245, 130, ("PLL_RF8N_T", False), GND)
    lo.conn("PLL_RF8P", f"{u}.RF8P"); lo.conn("PLL_RF8N", f"{u}.RF8N")
    decision(lo, "L501/L502/C505/C506/R502", "RF8P/N: 7.5 nH pull-up to VCC_X1 rail, 10 pF ac coupling; unused RF8N terminated in 50 ohm", "ADF4371 Rev 0 p21, p24, Fig 44, Table 1")
    # RFAUX8 -> LO monitor SMA
    ind(lo, "L503", "7.5nH", 200, 230, ("+3V3_LO", G), ("PLL_AUXP", False))
    ind(lo, "L504", "7.5nH", 215, 230, ("+3V3_LO", G), ("PLL_AUXN", False))
    cap(lo, "C507", "10pF", 230, 250, ("PLL_AUXP", False), ("LO_MON", False))
    cap(lo, "C508", "10pF", 245, 250, ("PLL_AUXN", False), ("PLL_AUXN_T", False))
    res(lo, "R503", "49.9", 260, 250, ("PLL_AUXN_T", False), GND)
    lo.conn("PLL_AUXP", f"{u}.RFAUX8P"); lo.conn("PLL_AUXN", f"{u}.RFAUX8N")
    lo.place("Connector:Conn_Coaxial", "J501", "SMA LO_MON (RFAUX8)", 290, 250)
    lo.conn("LO_MON", "J501.1"); lo.conn("GND", "J501.2", g=G)
    decision(lo, "J501", "RFAUX8 routed to an LO monitor SMA (off by default, PDB_AUX = 0)", "ADF4371 Rev 0 REG0072; RFAUX8 treated like RF8 (p9)")
    for p in ("RF16P", "RF16N", "RF32P", "RF32N"):
        lo.noconn(u, p)
    decision(lo, u, "RF16x / RF32x left open", "ADF4371 Rev 0 pin table: 'If unused, this pin can be left open'")
    unresolved(lo, u, "loop filter CPOUT->VTUNE, RS_SW", "no reference loop filter in ADF4371 Rev 0; design with ADIsimPLL for 10 MHz PFD / 6.6 GHz")
    lo.note("UNRESOLVED: loop filter (CPOUT -> VTUNE, RS_SW) needs ADIsimPLL design; pins intentionally left unconnected.", 25, 20)
    lo.note("ADF4371 RF8 is ENABLED at power-up by register default (REG0025 RF_EN=1): CE held low by pull-down until firmware programs the part.", 25, 25)
    # LO buffer + pad + 4-way splitter
    ua = "U502"
    lo.place("openru_x6:AVA-183A+", ua, "AVA-183A+", 300, 120, mpn="AVA-183A+")
    lo.conn("LO_AMP_IN", f"{ua}.RF_IN"); lo.conn("LO_AMP_OUT", f"{ua}.RF_OUT")
    lo.conn("GND", f"{ua}.GND", g=G)
    unresolved(lo, ua, "VD1/VD2 bias network (L1 3.3 nH, C1-C4, ML1-ML7)", "AVA-183A+ Fig 2 values known but node-by-node wiring not verified; pins left open. Gain/P1dB not specified 5-8 GHz")
    res(lo, "R504", "294", 340, 160, ("LO_AMP_OUT", False), GND)
    res(lo, "R505", "17.4", 355, 140, ("LO_AMP_OUT", False), ("LO_SPLIT_IN", False))
    res(lo, "R506", "294", 370, 160, ("LO_SPLIT_IN", False), GND)
    decision(lo, "R504-R506", "3 dB pi attenuator (294/17.4/294 ohm) after LO buffer to keep LTC5553 LO in -6..+6 dBm and below +10 dBm abs max", "computed (see reports/H2A_LO_BUDGET.csv)")
    us = "U503"
    lo.place("openru_x6:EP4RKU+", us, "EP4RKU+", 300, 220, mpn="EP4RKU+")
    lo.conn("LO_SPLIT_IN", f"{us}.SUM")
    for k in (1, 2, 3, 4):
        lo.conn(f"C{k}_LO", f"{us}.P{k}", g=G)
    lo.conn("GND", f"{us}.GND", g=G)
    unresolved(lo, "U501/U502/U503", "footprints", "LGA-48 CC-48-4 (EP size ambiguous in DS), DQ849, DG1677-2: use vendor land patterns")
    lo.note("LO path: ADF4371 RF8P 6.6 GHz -> AVA-183A+ -> 3 dB pad -> EP4RKU+ 4-way -> LTC5553 LO x4 (C1_LO..C4_LO). Equal-length routing required.", 25, 30)

    # ---------------------------------------------------------------- CAL / test I/O sheet (8)
    cal = sub(ROOT, "CAL_AND_TEST_IO", "cal.kicad_sch", 90, 120); sheets.append(cal)
    cal.place("Connector:Conn_Coaxial", "J801", "SMA CAL (inject / sample)", 30, 100)
    cal.conn("CAL_SUM", "J801.1"); cal.conn("GND", "J801.2", g=G)
    cal.place("openru_x6:EP4RKU+", "U801", "EP4RKU+", 100, 100, mpn="EP4RKU+")
    cal.conn("CAL_SUM", "U801.SUM"); cal.conn("GND", "U801.GND", g=G)
    for c in (1, 2, 3, 4):
        d = f"DC{800 + c}"
        cal.place("openru_x6:EDC21-24+", d, "EDC21-24+", 200 + (c - 1) * 50, 120, mpn="EDC21-24+")
        cal.conn(f"C{c}_RFIO_MIX", f"{d}.INPUT", g=G)
        cal.conn(f"C{c}_RFIO_BF", f"{d}.OUTPUT", g=G)
        cal.conn(f"CAL_INJ{c}", f"{d}.COUPLED", "U801.P%d" % c)
        cal.conn("GND", f"{d}.GND", g=G)
    decision(cal, "DC801-DC804/U801", "One 21 dB coupler per chain between converter and ADAR1000 RF_IO; coupled ports combined by EP4RKU+ to one CAL SMA. RX cal: tone into CAL appears at coupler INPUT (mixer side) of all 4 chains simultaneously -> measures relative phase of N310+LO+converter paths after every start/retune. TX cal: each chain's forward wave sampled at CAL",
             "EDC21-24+ REV.A (coupling 21 dB typ 8-10 GHz, directivity 19 dB typ); EP4RKU+ REV.C (phase unbalance 1.9 deg typ, 19 deg max -> must itself be calibrated once)")
    cal.place("Connector:Conn_Coaxial", "J802", "SMA REF 10 MHz IN", 30, 200)
    cal.conn("REF_10M", "J802.1", g=G); cal.conn("GND", "J802.2", g=G)
    res(cal, "R801", "49.9", 60, 220, ("REF_10M", G), GND)
    decision(cal, "R801", "50 ohm termination of the 10 MHz reference input (ADF4371 REFP is high impedance)", "ADF4371 Rev 0 Fig 35 (2.5k/85k input); value is a design choice. Level from shared 10 MHz distribution UNRESOLVED")
    cal.place("Connector:Conn_Coaxial", "J803", "SMA PPS IN", 30, 250)
    cal.conn("PPS_RAW", "J803.1"); cal.conn("GND", "J803.2", g=G)
    res(cal, "R802", "100", 70, 250, ("PPS_RAW", False), ("PPS_BUF_IN", False))
    res(cal, "R803", "10k", 85, 270, ("PPS_BUF_IN", False), GND)
    cal.place("74xGxx:74LVC1G125", "U802", "74LVC1G125", 130, 250, fp="Package_TO_SOT_SMD:SOT-23-5")
    cal.conn("PPS_BUF_IN", "U802.2"); cal.conn("GND", "U802.1", "U802.3", g=G)
    cal.conn("PPS_1V8", "U802.4", g=G); cal.conn("+1V8_DIG", "U802.5", g=G)
    decision(cal, "U802", "PPS received by 74LVC1G125 at 1.8 V (LVC inputs tolerate 3.3/5 V) -> MCU timer capture", "74LVC1G125 is a KiCad-library part; input tolerance from TI LVC family - verify in TI DS. N310 PPS level UNRESOLVED")
    cal.note("Calibration: N310 relative channel phase is random per start/retune -> run CAL-port RX/TX loopback after every N310 init or LO retune; coupler + EP4RKU+ paths must be phase-matched in layout and characterised once (VNA).", 25, 20)
    cal.note("Per-element: ADTR1107 CPLR_OUT -> ADAR1000 DETx (power only, -20..+10 dBm). Element phase cal needs a near-field/OTA probe in a shielded setup (no OTA at 8.4 GHz).", 25, 25)

    # ---------------------------------------------------------------- POWER sheet (6)
    pw = sub(ROOT, "POWER_SEQUENCING", "power.kicad_sch", 150, 120); sheets.append(pw)
    S.set_page_size("A2", schematic_path=pw.path); pw.cx = 297
    pw.place("Connector_Generic:Conn_01x02", "J601", "VIN 12V bench", 20, 60)
    pw.conn("VIN_12V", "J601.1", g=G); pw.conn("GND", "J601.2", g=G)
    pw.flag("#FLG601", "VIN_12V", 40, 40)
    pw.flag("#FLG602", "GND", 55, 40)
    regs = [  # ref, rail(out net), en net, PG net, note
        ("U601", "+3V3_RF_SRC", "PWR_EN_3V3", "PG_3V3RF", "+3.3 V RF, >= 4 A (4x ADAR1000 350 mA TX + 16x ADTR1107 LNA 80 mA + 4x LTC5553 150 mA). ADI suggests LT8609S (ADAR1000 DS Table 26, 4 devices)"),
        ("U602", "+5V_PA", "PWR_EN_5VPA", "PG_5VPA", "+5 V PA drain, >= 5 A (16x 220 mA quiescent + RF drive)"),
        ("U603", "+1V8_DIG", "VIN_12V", "PG_1V8", "+1.8 V always-on logic/MCU (ADAR1000 SPI is 1.8 V CMOS, abs max 2.0 V)"),
        ("U604", "+3V3_LO", "PWR_EN_LO", "PG_3V3LO", "+3.3 V ADF4371 AVDD, low noise (DS recommends ADM7150 / LT3045)"),
        ("U605", "+5V_LO", "PWR_EN_LO", "PG_5VLO", "+5 V ADF4371 VCC_VCO/VCC_LDO + AVA-183A+, low noise (ADM7150 / LT3045 per DS)"),
        ("U606", "+3V3_AUX", "VIN_12V", "PG_3V3AUX", "+3.3 V always-on telemetry (INA226 VS)"),
    ]
    for i, (ref, rail, en, pg, txt) in enumerate(regs):
        pw.place("openru_x6:TBD_REG_POS", ref, "UNRESOLVED_REG", 60 + (i % 3) * 70, 90 + (i // 3) * 60)
        pw.conn("VIN_12V", f"{ref}.VIN", g=G); pw.conn(en, f"{ref}.EN", g=(en != "VIN_12V") or True)
        pw.conn(rail, f"{ref}.VOUT", g=G); pw.conn("GND", f"{ref}.GND", g=G)
        if pg in ("PG_3V3RF",):
            pw.conn(pg, f"{ref}.PG", g=G)
        else:
            pw.noconn(ref, "PG")
        unresolved(pw, ref, f"regulator for {rail}", txt)
    for i, (ref, rail, en, txt) in enumerate([
            ("U607", "-5V_BF", "PWR_EN_NEG", "-5 V ADAR1000 AVDD1 (-50 mA max per chip, PA bias fully loaded) -> ~-0.2 A; ADI suggests LT1931/LT3462 (DS p45, Table 26)"),
            ("U608", "-3V3_SW", "PWR_EN_NEG", "-3.3 V ADTR1107 VSS_SW (16x 120 uA); negative LDO from -5 V (e.g. LT3094 class)")]):
        pw.place("openru_x6:TBD_REG_NEG", ref, "UNRESOLVED_NEG_REG", 60 + i * 70, 220)
        pw.conn("VIN_12V" if ref == "U607" else "-5V_BF", f"{ref}.VIN", g=G)
        pw.conn(en, f"{ref}.EN", g=G); pw.conn(rail, f"{ref}.VOUT", g=G); pw.conn("GND", f"{ref}.GND", g=G)
        unresolved(pw, ref, f"regulator for {rail}", txt)
    pw.place("openru_x6:TBD_NEG_RAIL_MON", "U609", "UNRESOLVED_NEG_MON", 220, 220)
    pw.conn("-5V_BF", "U609.SENSE_5V", g=G); pw.conn("-3V3_SW", "U609.SENSE_3V3", g=G)
    pw.conn("+1V8_DIG", "U609.VDD", g=G); pw.conn("NEG_OK", "U609.OK", g=G); pw.conn("GND", "U609.GND", g=G)
    res(pw, "R601", "10k", 250, 200, ("NEG_OK", G), ("+1V8_DIG", G))
    unresolved(pw, "U609", "negative-rail window monitor", "hardware NEG_OK so PA drain cannot be on with -5 V/-3.3 V absent; comparator/supervisor not yet selected")
    # shunts + telemetry + PA drain switches
    pw.place("Device:R", "R602", "10m", 330, 60, fp="Resistor_SMD:R_1206_3216Metric")
    pw.conn("+3V3_RF_SRC", "R602.1", g=G); pw.conn("+3V3_RF", "R602.2", g=G)
    pw.flag("#FLG603", "+3V3_RF", 350, 40)
    inas = [("U610", "+3V3_RF_SRC", "+3V3_RF", "GND", "GND")]
    for c in (1, 2, 3, 4):
        sh, sw = f"R{610 + c}", f"U{620 + c}"
        pw.place("Device:R", sh, "10m", 300 + (c - 1) * 25, 120, fp="Resistor_SMD:R_1206_3216Metric")
        pw.conn("+5V_PA", f"{sh}.1", g=G); pw.conn(f"+5V_PA_IN_C{c}", f"{sh}.2")
        pw.flag(f"#FLG{610 + c}", f"+5V_PA_IN_C{c}", 300 + (c - 1) * 25, 100)
        pw.place("Power_Management:TPS22810DRV", sw, "TPS22810DRV", 300 + (c - 1) * 25, 170, mpn="TPS22810DRVR")
        pw.conn(f"+5V_PA_IN_C{c}", f"{sw}.VIN"); pw.conn("PA_DRAIN_EN", f"{sw}.EN/UVLO", g=G)
        pw.conn(f"+5V_PA_C{c}", f"{sw}.VOUT", g=G); pw.conn("GND", f"{sw}.GND", g=G)
        unresolved(pw, sw, "CT (slew) capacitor and QOD resistor", "values need TI TPS22810 DS; pins left open")
        inas.append((f"U{610 + c}", "+5V_PA", f"+5V_PA_IN_C{c}", ["GND", "+3V3_AUX", "GND", "+3V3_AUX"][c - 1], ["GND", "GND", "+3V3_AUX", "+3V3_AUX"][c - 1]))
    decision(pw, "U621-U624", "One TPS22810 per chain on the PA drain, enable = PA_DRAIN_EN (hardware AND of MCU_PA_EN, WDT_OK, NEG_OK); EN pulled low -> drain OFF at reset",
             "ADTR1107 Rev C p24 (gate before drain) + ADAR1000 Rev B p41/p44-45 (PA_BIAS 0 V at power-up). TPS22810 is a KiCad-library part; EN threshold vs 1.8 V logic to verify in TI DS")
    for ref, hi, lo_, a0, a1 in inas:
        pw.place("Sensor_Energy:INA226", ref, "INA226", 60 + (int(ref[1:]) - 610) * 40, 280, mpn="INA226AIDGSR")
        pw.conn(hi, f"{ref}.Vin+", g=G); pw.conn(lo_, f"{ref}.Vin-", g=lo_.startswith("+3V3_RF"))
        pw.conn(lo_, f"{ref}.Vbus", g=lo_.startswith("+3V3_RF"))
        pw.conn("+3V3_AUX", f"{ref}.VS", g=G); pw.conn("GND", f"{ref}.GND", g=G)
        pw.conn("I2C3_SDA", f"{ref}.SDA"); pw.conn("I2C3_SCL", f"{ref}.SCL")
        pw.conn("INA_ALERT_N", f"{ref}.~{{Alert}}", g=G)
        pw.conn(a0, f"{ref}.A0", g=True); pw.conn(a1, f"{ref}.A1", g=True)
    unresolved(pw, "U610-U614", "INA226 address straps / shunt values", "A1:A0 = GND/VS combinations from memory of TI address table - verify in TI INA226 DS; 10 mOhm shunt is a design choice")
    pw.place("Interface:PCA9306", "U615", "PCA9306", 380, 280, fp="Package_SO:VSSOP-8_2.3x2mm_P0.5mm")
    pw.conn("I2C_SCL", "U615.SCL1", g=G); pw.conn("I2C_SDA", "U615.SDA1", g=G)
    pw.conn("I2C3_SCL", "U615.SCL2"); pw.conn("I2C3_SDA", "U615.SDA2")
    pw.conn("+1V8_DIG", "U615.VREF1", g=G); pw.conn("PCA_VREF2", "U615.VREF2", "U615.EN"); pw.conn("GND", "U615.GND", g=G)
    pw.flag("#FLG620", "PCA_VREF2", 400, 230)
    res(pw, "R603", "200k", 400, 250, ("PCA_VREF2", False), ("+3V3_AUX", G))
    res(pw, "R604", "4.7k", 415, 250, ("I2C3_SCL", False), ("+3V3_AUX", G))
    res(pw, "R605", "4.7k", 425, 250, ("I2C3_SDA", False), ("+3V3_AUX", G))
    res(pw, "R606", "10k", 435, 250, ("INA_ALERT_N", G), ("+1V8_DIG", G))
    unresolved(pw, "U615", "PCA9306 VREF2/EN 200k bias and pull-ups", "standard TI application from memory - verify in TI PCA9306 DS")
    pw.note("Power-up order (ADAR1000 Rev B p44-45 + ADTR1107 Rev C p24): +1V8_DIG/+3V3_AUX (always on) -> MCU -> +3V3_RF (VDD_SW, VDD_LNA, AVDD3) -> -5V_BF & -3V3_SW (PWR_EN_NEG) -> program PA_BIAS OFF = -1.75 V, CTRL_SW = RX -> +5V_PA rail -> PA_DRAIN_EN (hardware AND) -> raise VGG_PA for 220 mA.", 25, 20)
    pw.note("Power-down: TX off (BF_TR low) -> PA_BIAS to -1.75 V -> PA_DRAIN_EN low -> negative rails -> +3V3_RF. A watchdog or NEG_OK fault removes the PA drain in hardware.", 25, 25)
    pw.note("All regulator blocks are UNRESOLVED placeholders (TBD_*), not parts: topology, inductors, compensation and feedback values are not designed yet.", 25, 30)

    # ---------------------------------------------------------------- MCU / safety sheet (7)
    mc = sub(ROOT, "MCU_SAFETY", "mcu.kicad_sch", 210, 120); sheets.append(mc)
    S.set_page_size("A2", schematic_path=mc.path); mc.cx = 297
    u = "U701"
    mc.place("MCU_ST_STM32G4:STM32G431C_6-8-B_Ux", u, "STM32G431CBU6", 200, 150, mpn="STM32G431CBU6", fp="Package_DFN_QFN:QFN-48-1EP_7x7mm_P0.5mm_EP5.6x5.6mm")  # base of derived STM32G431CBUx
    mc.conn("+1V8_DIG", f"{u}.23", f"{u}.35", f"{u}.48", f"{u}.VDDA", f"{u}.VBAT", f"{u}.VREF+", g=G)
    mc.conn("GND", f"{u}.VSS", g=G)
    pinmap = {"PA5": "BF_SCLK", "PA7": "BF_SDIO", "PA6": "BF_SDO", "PB0": "BF_CS1_N", "PB1": "BF_CS2_N", "PB2": "BF_CS3_N",
              "PB10": "BF_CS4_N", "PB11": "PLL_CS_N", "PB12": "PLL_CE", "PB13": "MIX_EN", "PB14": "MCU_TX_EN", "PB15": "MCU_PA_EN",
              "PA8": "BF_TX_LOAD", "PA9": "BF_RX_LOAD", "PA10": "PLL_MUXOUT", "PC13": "WDI", "PB3": "PPS_1V8", "PB4": "PWR_EN_3V3",
              "PB5": "PWR_EN_NEG", "PB6": "PWR_EN_5VPA", "PC14": "PWR_EN_LO", "PA15": "I2C_SCL", "PB7": "I2C_SDA", "PA0": "NEG_OK",
              "PA1": "PG_3V3RF", "PA2": "INA_ALERT_N", "PA3": "WDT_OK", "PA4": "BF_TR"}
    for pin, net in pinmap.items():
        mc.conn(net, f"{u}.{pin}", g=G)
    for spare in ("PF0", "PF1", "PC4", "PC6", "PC10", "PC11", "PC15", "PB9", "PA11", "PA12"):
        mc.noconn(u, spare)
    unresolved(mc, u, "MCU pin / alternate-function map", "SPI1 PA5/6/7, I2C1 PA15/PB7, TIM capture on PB3 etc. are provisional - verify with STM32CubeMX / ST DS before sign-off")
    unresolved(mc, u, "MCU decoupling", "VDD/VDDA/VREF+ bypass per ST STM32G431 DS not yet placed")
    res(mc, "R701", "10k", 120, 250, ("BOOT0", False), GND); mc.conn("BOOT0", f"{u}.PB8")
    cap(mc, "C701", "100nF", 135, 250, ("NRST", False), GND); mc.conn("NRST", f"{u}.PG10")
    mc.place("Connector_Generic:Conn_01x05", "J701", "SWD", 60, 250)
    mc.conn("+1V8_DIG", "J701.1", g=G); mc.conn("SWDIO", "J701.2", f"{u}.PA13"); mc.conn("SWCLK", "J701.3", f"{u}.PA14")
    mc.conn("NRST", "J701.4"); mc.conn("GND", "J701.5", g=G)
    # default-safe pull-downs on every enable / load line
    pd = ["MCU_TX_EN", "MCU_PA_EN", "MIX_EN", "PLL_CE", "PWR_EN_3V3", "PWR_EN_NEG", "PWR_EN_5VPA", "PWR_EN_LO", "BF_TX_LOAD", "BF_RX_LOAD", "TDD_TR_IN", "TX_PERMIT_IN"]
    for i, net in enumerate(pd):
        res(mc, f"R{710 + i}", "100k", 30 + i * 12, 300, (net, G), GND)
    decision(mc, "R710-R721", "100k pull-down on every enable, load and TDD input -> radio powers up muted (TX off, PA drain off, mixers/PLL off, RX beams not loaded)",
             "MCU GPIOs are high-Z in reset; ADAR1000 TX_LOAD/RX_LOAD need external pull-down (DS p14)")
    for i, net in enumerate(["BF_CS1_N", "BF_CS2_N", "BF_CS3_N", "BF_CS4_N", "PLL_CS_N"]):
        res(mc, f"R{730 + i}", "100k", 30 + i * 12, 330, (net, G), ("+1V8_DIG", G))
    # watchdog
    mc.place("Power_Supervisor:TPS3430WDRC", "U702", "TPS3430WDRC", 80, 100, mpn="TPS3430WDRCR")
    mc.conn("+1V8_DIG", "U702.VDD1", "U702.VDD2", g=G); mc.conn("GND", "U702.GND", g=G)
    mc.conn("WDI", "U702.WDI", g=G); mc.conn("WDT_OK", "U702.~{WDO}", g=G)
    res(mc, "R702", "10k", 110, 70, ("WDT_OK", G), ("+1V8_DIG", G))
    unresolved(mc, "U702", "TPS3430 CWD/CRST/SET0/SET1 timing", "window timing selection needs TI TPS3430 DS; pins left open. VDD range vs 1.8 V to verify")
    # gating logic (LVC at 1.8 V; inputs are over-voltage tolerant)
    mc.place("74xGxx:74LVC1G11", "U703", "74LVC1G11", 80, 170, fp="Package_TO_SOT_SMD:SOT-23-6")
    mc.conn("MCU_TX_EN", "U703.1", g=G); mc.conn("WDT_OK", "U703.3", g=G); mc.conn("TX_PERMIT_IN", "U703.6", g=G)
    mc.conn("TX_ALLOW", "U703.4", g=G); mc.conn("+1V8_DIG", "U703.5", g=G); mc.conn("GND", "U703.2", g=G)
    mc.place("74xGxx:74LVC1G08", "U704", "74LVC1G08", 80, 210, fp="Package_TO_SOT_SMD:SOT-23-5")
    mc.conn("TDD_TR_IN", "U704.1", g=G); mc.conn("TX_ALLOW", "U704.2", g=G)
    mc.conn("BF_TR", "U704.4", g=G); mc.conn("+1V8_DIG", "U704.5", g=G); mc.conn("GND", "U704.3", g=G)
    mc.place("74xGxx:74LVC1G11", "U705", "74LVC1G11", 140, 70, fp="Package_TO_SOT_SMD:SOT-23-6")
    mc.conn("MCU_PA_EN", "U705.1", g=G); mc.conn("WDT_OK", "U705.3", g=G); mc.conn("NEG_OK", "U705.6", g=G)
    mc.conn("PA_DRAIN_EN", "U705.4", g=G); mc.conn("+1V8_DIG", "U705.5", g=G); mc.conn("GND", "U705.2", g=G)
    decision(mc, "U703/U704/U705", "TX_ALLOW = MCU_TX_EN & WDT_OK & TX_PERMIT_IN; BF_TR = TDD_TR_IN & TX_ALLOW (to all 4 ADAR1000 TR); TX_ALLOW also drives ADAR1000 PA_ON (forces PA_BIAS OFF when low); PA_DRAIN_EN = MCU_PA_EN & WDT_OK & NEG_OK",
             "ADAR1000 Rev B p13-14 (TR high = TX; PA_ON low forces OFF bias in TR mode), TR switching 180 ns; ADTR1107 tON 10 ns")
    # N310 GPIO / interlock header
    mc.place("Connector_Generic:Conn_01x04", "J702", "N310 GPIO / TX interlock", 30, 180)
    mc.conn("TDD_TR_IN", "J702.1", g=G); mc.conn("TX_PERMIT_IN", "J702.2", g=G); mc.conn("BF_TR", "J702.3", g=G); mc.conn("GND", "J702.4", g=G)
    decision(mc, "J702", "TDD TR from N310 front-panel GPIO (3.3 V) into 1.8 V LVC gate; TX_PERMIT_IN is an external interlock (open = TX inhibited); BF_TR brought out for timing check",
             "N310 GPIO level/ATR mapping UNRESOLVED (UHD GPIO docs)")
    # temperature sensors
    for i, (ref, add0) in enumerate((("U706", "GND"), ("U707", "+1V8_DIG"))):
        mc.place("Sensor_Temperature:TMP102xxDRL", ref, "TMP117AIDRVR", 300 + i * 50, 80, mpn="TMP117AIDRVR", fp="Package_SON:WSON-6-1EP_2x2mm_P0.65mm_EP1x1.6mm")  # KiCad TMP117xxDRV extends this symbol (same pins)
        mc.conn("I2C_SCL", f"{ref}.SCL", g=G); mc.conn("I2C_SDA", f"{ref}.SDA", g=G)
        mc.conn("+1V8_DIG", f"{ref}.V+", g=G); mc.conn("GND", f"{ref}.GND", g=G); mc.conn(add0, f"{ref}.ADD0", g=G)
        mc.conn("INA_ALERT_N", f"{ref}.ALERT", g=G)
    res(mc, "R703", "2.2k", 360, 40, ("I2C_SCL", G), ("+1V8_DIG", G))
    res(mc, "R704", "2.2k", 372, 40, ("I2C_SDA", G), ("+1V8_DIG", G))
    unresolved(mc, "U706/U707", "TMP117 placement", "must sit on the FE heat spreader; one per tile half. Thermal design open (H1 M5)")
    mc.note("Safety chain: reset/power-up -> all enables pulled low -> TX muted, PA drain off. Watchdog timeout -> WDT_OK low -> TX_ALLOW and PA_DRAIN_EN drop in hardware, independent of firmware.", 25, 20)
    mc.note("Beam updates: BF_TX_LOAD / BF_RX_LOAD are shared by all four ADAR1000 (synchronous latch); never pulse both within 8 SCLK (DS p33-34).", 25, 25)

    # ---------------------------------------------------------------- flush all sheets
    for sh in sheets:
        sh.flush()
    P.annotate_schematic(ROOT, PRO)
    (OUT / "build_log.json").write_text(json.dumps({"unresolved": UNRESOLVED, "decisions": DECISIONS, "placed": PLACED}, indent=1))
    print(f"built {len(PLACED)} parts on {len(sheets) + 1} sheets; {len(UNRESOLVED)} unresolved items")


if __name__ == "__main__":
    main()
