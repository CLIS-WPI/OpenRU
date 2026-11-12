#!/bin/bash
# Rebuild the H2-A schematic and regenerate every report. Needs:
#   KICAD_CLI_PATH  -> kicad-cli 9.x (e.g. a wrapper around the kicad/kicad:9.0 Docker image)
#   KICAD_SYMBOL_DIR -> KiCad 9 symbol libraries
#   PY -> a Python 3.11+ with mcp-server-kicad==0.21.1 installed
set -euo pipefail
H2=$(cd "$(dirname "$0")/.." && pwd)
SCH=$H2/schematics; REP=$H2/reports
rm -rf "$SCH"; mkdir -p "$SCH" "$REP"
"$PY" "$H2/tools/build_schematics.py" "$SCH" | grep -v "planned only"
mv "$SCH/build_log.json" "$REP/H2A_BUILD_LOG.json"
"$PY" - "$SCH" "$REP" <<'PYEOF'
import json, sys
from mcp_server_kicad import project as P, schematic as S
sch, rep = sys.argv[1], sys.argv[2]
root, pro = f"{sch}/openru_x6_tile.kicad_sch", f"{sch}/openru_x6_tile.kicad_pro"
h = P.validate_hierarchy(root)
e = S.run_erc(root, output_dir=rep, project_path=pro).model_dump()
json.dump({"hierarchy": h.model_dump(), "erc": e}, open(f"{rep}/H2A_ERC.json", "w"), indent=1)
S.export_netlist(root, output_dir=rep, format="kicadxml")
S.export_schematic("pdf", schematic_path=root, output_dir=rep)
print("hierarchy", h.status, "issues", h.issue_count, "| ERC violations", e["violation_count"])
PYEOF
sed -i "s#$SCH/#hardware/h2/schematics/#g" "$REP/openru_x6_tile.xml"  # no local absolute paths in committed files
python3 "$H2/tools/verify_netlist.py" "$REP/openru_x6_tile.xml" "$REP/H2A_BUILD_LOG.json" "$REP/H2A_PIN_INTERFACE_VERIFICATION.csv"
python3 "$H2/tools/rf_budget.py" "$REP"
python3 "$H2/tools/make_bom_and_issues.py" "$REP"
