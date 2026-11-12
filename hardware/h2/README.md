# H2-A — preliminary RF tile schematic (OpenRU-X6, 4T4R / 16 feeds)

This is a **preliminary engineering schematic**. It is not a released design, and layout is NO-GO.
Start with `reports/H2A_SCHEMATIC_REVIEW.md`, then the H2-B reports (`reports/H2B_*`).

**H2-B (branch `hardware/h2b-electrical`):** the schematic is now edited directly with the KiCad MCP tools, and the KiCad files are the source of truth. The H2-A generator (`tools/build_schematics.py`, `tools/run_h2a_checks.sh`) is frozen: the check script refuses to run unless `FORCE_H2A_REBUILD=1`, because a rebuild would delete the H2-B edits. Re-verify with ERC and a netlist export through MCP, then run `tools/verify_netlist.py`.

| Path | What |
|---|---|
| `schematics/openru_x6_tile.kicad_pro` | editable KiCad 9 project (root + 20 sub-sheets, project symbol library `openru_x6.kicad_sym`) |
| `datasheet_pins/` | pin tables and fact notes transcribed from the manufacturer datasheets; the only source for the custom symbols |
| `tools/build_schematics.py` | generates the whole project through mcp-server-kicad 0.21.1 (no hand-edited KiCad files) |
| `tools/verify_netlist.py` | checks the exported netlist against pin tables, feed map, interfaces and interlocks |
| `tools/rf_budget.py` | RF cascade, LO budget, spur table |
| `tools/make_bom_and_issues.py` | candidate BOM + unresolved-issues list from the build log |
| `tools/run_h2a_checks.sh` | rebuild + ERC + netlist + PDF + all reports |
| `reports/` | review, mixer decision, ERC report, unresolved issues, power/sequencing spec, BOM, budgets, spur table, source manifest, ADI inquiry draft (NOT SENT), netlist, PDF |

## Rebuild

You need three things:
- a KiCad 9 `kicad-cli`. The official `kicad/kicad:9.0` Docker image works, behind a small wrapper script.
- the KiCad 9 symbol libraries;
- `pip install mcp-server-kicad==0.21.1` (Python ≥ 3.11).

```bash
KICAD_CLI_PATH=/path/to/kicad-cli KICAD_SYMBOL_DIR=/path/to/kicad/symbols PY=python3.12 \
  hardware/h2/tools/run_h2a_checks.sh
```

Do not edit the `.kicad_sch` files by hand and then rebuild: the build deletes and regenerates `schematics/`. Once
the design moves to interactive KiCad editing, stop using the generator and treat the KiCad files as the source.

## Safety and regulatory

All testing must be cabled, attenuated or shielded. 8.40–8.45 GHz is deep-space only (47 CFR 2.106 fn 5.465), so there
is no OTA transmission at 8.4 GHz. QPX0252 material is deferred until the university export-control review is done.
