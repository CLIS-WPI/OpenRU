#!/usr/bin/env python3
"""Check an exported KiCad netlist against expected_<block>.json files written from the design specs
BEFORE placement.

    python verify_expected.py <netlist.xml> <expected.json> [...]

Each expected file maps ref -> {lib_id, value, footprint, pins: {pin_number: net}}. Global nets (names without a
PWR_/IL_ prefix) must match by name. Local nets (PWR_*, IL_*) must map one-to-one onto a single exported net, and two
different expected nets must never share one exported net. Exits 1 on any failure.
"""
import json
import sys
import xml.etree.ElementTree as ET

root = ET.parse(sys.argv[1]).getroot()
pin_net = {(n2.get("ref"), n2.get("pin")): n.get("name") for n in root.iter("net") for n2 in n.iter("node")}
comps = {c.get("ref"): c for c in root.iter("comp")}
fails, checks = [], 0


SHEET_LOCAL = {"NEG_RAILS_OK", "GATES_OK", "GATES_PINCHED"}  # single-sheet nets on interlock.kicad_sch


def local(net):
    return net.startswith(("PWR_", "IL_")) or net in SHEET_LOCAL


for path in sys.argv[2:]:
    exp = json.load(open(path))
    seen = {}  # expected local net -> set of actual nets
    for ref, e in exp.items():
        checks += 1
        c = comps.get(ref)
        if c is None:
            fails.append(f"{path}: {ref} missing from netlist")
            continue
        if e.get("value") and c.findtext("value") != e["value"]:
            fails.append(f"{ref}: value {c.findtext('value')!r} != {e['value']!r}")
        if (e.get("footprint") or "").startswith(("Package", "Capacitor", "Resistor", "Inductor", "Diode", "Connector")) and c.findtext("footprint") != e["footprint"]:
            fails.append(f"{ref}: footprint {c.findtext('footprint')!r} != {e['footprint']!r}")
        for pin, net in e.get("pins", {}).items():
            checks += 1
            act = pin_net.get((ref, str(pin)))
            if act is None:
                fails.append(f"{ref}.{pin}: not in netlist (expected {net})")
            elif local(net):
                seen.setdefault(net, set()).add(act)
            elif act != net:  # a global net exports without a sheet path; "/sheet/GND" would be an unjoined local
                fails.append(f"{ref}.{pin}: on {act!r}, expected {net!r}")
    for net, acts in seen.items():
        if len(acts) != 1:
            fails.append(f"{path}: local net {net} split across {sorted(acts)}")
    owners = {}
    for net, acts in seen.items():
        for a in acts:
            owners.setdefault(a, set()).add(net)
    for a, nets in owners.items():
        if len(nets) > 1:
            fails.append(f"{path}: expected nets {sorted(nets)} merged into {a!r}")
print(f"{checks} checks, {len(fails)} failures")
for f in fails[:60]:
    print("FAIL", f)
sys.exit(1 if fails else 0)
