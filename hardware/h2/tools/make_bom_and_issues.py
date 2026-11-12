#!/usr/bin/env python3
"""Generate H2A_CANDIDATE_BOM.csv and H2A_UNRESOLVED_ISSUES.md from reports/H2A_BUILD_LOG.json."""
import collections
import csv
import json
import sys
from pathlib import Path

rep = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "reports")
L = json.loads((rep / "H2A_BUILD_LOG.json").read_text())

# ---- unresolved issues (grouped across the four identical chains)
g = collections.OrderedDict()
for u in L["unresolved"]:
    g.setdefault((u["item"], u["reason"]), []).append(f"{u['ref']} ({u['sheet']})")
cls_map = [("footprint", "layout"), ("antenna", "EM"), ("LNA supply", "vendor"), ("INA226", "datasheet check"),
           ("PCA9306", "datasheet check"), ("TMP117", "thermal")]
lines = ["# H2-A Unresolved schematic issues", "",
         "Generated from `H2A_BUILD_LOG.json`. Every item here is left **unconnected** in the schematic or is an explicit "
         "`TBD_*` placeholder block (not a part), so KiCad ERC reports it instead of hiding it. Grouped across the four identical chains.", "",
         "| # | Item | Why unresolved / what closes it | Blocks | Where |", "|---|---|---|---|---|"]
for i, ((item, reason), refs) in enumerate(g.items(), 1):
    blk = next((v for k, v in cls_map if k.lower() in item.lower()), "schematic")
    where = ", ".join(refs) if len(refs) <= 4 else ", ".join(refs[:3]) + f" ... (+{len(refs) - 3})"
    lines.append(f"| U{i} | {item} | {reason} | {blk} | {where} |")
lines += ["", "**schematic** = close before schematic sign-off / layout preparation; **layout** = vendor land pattern needed before "
          "placement; **datasheet check** = KiCad-library part whose application values came from memory, check against the TI "
          "datasheet; **vendor** = ADI answer needed; **EM** / **thermal** = separate H2 work packages.", ""]
(rep / "H2A_UNRESOLVED_ISSUES.md").write_text("\n".join(lines))

# ---- candidate BOM
price = {"ADTR1107ACCZ": ("195.69", "Digi-Key qty 28 (H1.1)"), "ADF4371BCCZ": ("474.90", "Digi-Key qty 1 (H1)"),
         "BFCN-8350+": ("7.23", "Digi-Key qty 1 (H1)"), "HFCN-7150+": ("5.40", "Digi-Key qty 1 (H1)")}
ds_caps = {"GJM1555C1H180FB01", "0402ZK180GBS", "GRM188R71A105KA61"}
cnt = collections.OrderedDict()
for ref, p in L["placed"].items():
    if ref.startswith("#"):
        continue
    mpn = "SMA connector (type TBD)" if p["lib_id"] == "Connector:Conn_Coaxial" else p["mpn"]
    cnt.setdefault((mpn, p["lib_id"], p["footprint"]), []).append(ref)
tot = 0.0
with open(rep / "H2A_CANDIDATE_BOM.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["mpn_or_value", "symbol", "qty_per_tile", "refs", "footprint", "unit_price_usd", "extended_usd", "price_basis", "status"])
    for (mpn, lib, fp), refs in cnt.items():
        pr, basis = price.get(mpn, ("UNVERIFIED", ""))
        ext = f"{float(pr) * len(refs):.2f}" if pr != "UNVERIFIED" else "UNVERIFIED"
        tot += float(pr) * len(refs) if pr != "UNVERIFIED" else 0
        if "UNRESOLVED" in mpn:
            st = "PLACEHOLDER - NOT A PART"
        elif mpn in ds_caps:
            st = "DATASHEET-SPECIFIED (LTC5553 Fig 1)"
        elif lib.startswith("Device:"):
            st = "PROVISIONAL value (DS value or design choice, see H2A_SCHEMATIC_REVIEW)"
        elif lib.startswith("openru_x6:"):
            st = "SELECTED - custom symbol from DS pin table - not qualified"
        else:
            st = "SELECTED - KiCad library symbol - DS cross-check pending"
        rs = sorted(refs)
        w.writerow([mpn, lib, len(refs), " ".join(rs) if len(rs) <= 8 else " ".join(rs[:6]) + f" ... ({len(rs)})",
                    fp or "UNRESOLVED", pr, ext, basis, st])
    w.writerow(["SUMMARY known-price parts", "", "", "", "", "", f"{tot:.2f}", "ADTR1107 x16 + ADF4371 + BFCN-8350+ x4 + HFCN-7150+ x4",
                "ADAR1000, LTC5553, EP4RKU+ x2, EDC21-24+ x4, AVA-183A+, BFCN-1840+ x4, regulators, connectors: price UNVERIFIED"])
print(f"{len(g)} unresolved groups; known-price subtotal ${tot:.2f}")
