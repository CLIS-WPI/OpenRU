# A-IL12 design-validation study (regulator short exposes +5V_IL to VIN)

- **Status:** analysis only. **BEHAVIOURAL / PRELIMINARY: not hardware-validated.**
- **Baseline:** `3062b65` (H2-E.1).
- **Not changed:**
  - the tile and fixture KiCad schematics;
  - the PCB layouts;
  - the existing safety requirements and BOMs.
- **Nothing was purchased, fabricated, energised or sent to a vendor.**

| File | Content |
|---|---|
| `AIL12_DESIGN_VALIDATION.md` | **Decision report.** It separates guaranteed, derived, simulated and unbounded results, and lists the gates |
| `CANDIDATE_CIRCUIT.md` | Audit of the proposal, the corrected connection table and the preliminary BOM notes |
| `ail12_candidate_bom.csv` | Preliminary BOM of the candidate. MPN and stock status are given per line |
| `params.py` | Every numeric input, with an evidence tag and its source |
| `calc.py` → `out/calc.txt`, `out/calc.json` | Analytic checks (DERIVED) |
| `model.py` | Event-driven behavioural transient model (not a vendor model; limitations in its docstring) |
| `run_sim.py` → `out/runs.csv`, `out/sweeps.csv`, `out/limits.csv`, `out/traces/`, `out/fig_*.png`, `out/sim_log.txt`, `out/summary.json` | Scenario runs, HYPOTHETICAL delay sweeps and bisection for the maximum permissible delay |
| `test_ail12.py` | Self-checks of the analysis code. They are not design acceptance |
| `SOURCES.md` | Datasheet revisions and hashes, vendor-model status, simulations not executed, tool versions |
| `run_all.sh` | Reproduces everything in the pinned image |

Reproduce from the repository root (no GPU needed; about 4 min on 16 cores):

```bash
bash hardware/h2/design/ail12/run_all.sh          # full set
bash hardware/h2/design/ail12/run_all.sh --quick  # reduced grid, for checking the code only
```
