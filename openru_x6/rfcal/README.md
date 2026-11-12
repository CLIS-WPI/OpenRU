# OpenRU-X6 RF Beamforming and Calibration Model

This package is a hardware-independent, CPU-only model of the documented H1
4T4R / 16-feed OpenRU-X6 topology. It provides geometry-based steering,
configurable beamformer quantization, synthetic complex-IQ measurements,
per-path calibration, fault detection, beam metrics, JSON/CSV serialization,
and reproducible validation sweeps.

**Evidence label: SIMULATED.** The package does not measure hardware, control a
transmitter, write ADAR1000 registers, or prove performance at 8.4 GHz. The
ADAR1000 remains unqualified at the intended carrier frequency.

## Topology

The default topology mirrors `hardware/H1_FEED_POLARIZATION_MAP.csv`:

- 4 RF chains, 16 feeds, 8 dual-polarized sites.
- 2x4 site grid with V and H feeds at every site.
- Each RF chain owns four feeds: V/H at two adjacent sites.
- Site pitch is 17.845 mm, approximately half a wavelength at 8.4 GHz.
- Broadside is `+x`; the array lies in the `y-z` plane.

Use `Topology.load(path)` to read a JSON topology or an H1 feed-map CSV. The
embedded default can be inspected with:

```bash
python -m openru_x6.rfcal topology --output rfcal_out/topology.json
```

## Install and test

The package uses NumPy and the standard library. It is included automatically
by the repository's existing `openru_x6*` package discovery.

```bash
python -m pytest tests/rfcal -q
```

With the repository's pinned container:

```bash
docker run --rm -v "$PWD":/workspace -w /workspace openru-x6-sim:0.1.0 \
  python -m pytest tests/rfcal -q
```

## CLI

```bash
python -m openru_x6.rfcal --help
mkdir -p rfcal_out
```

Generate a codebook:

```bash
python -m openru_x6.rfcal codebook \
  --az-min -60 --az-max 60 --az-step 5 \
  --el-min -20 --el-max 20 --el-step 5 \
  --output rfcal_out/codebook.json
```

Generate synthetic measurements and calibrate them:

```bash
python -m openru_x6.rfcal simulate \
  --seed 0 --snr-db 30 --captures 4 --samples 64 \
  --output rfcal_out/measurements.json

python -m openru_x6.rfcal calibrate \
  --measurements rfcal_out/measurements.json \
  --output rfcal_out/calibration
```

Inspect a failed-chain scenario:

```bash
cat > rfcal_out/faults.json <<'JSON'
{
  "chain_faults": {"0": "missing"},
  "path_faults": {"5": "inconsistent"}
}
JSON

python -m openru_x6.rfcal simulate \
  --faults-json rfcal_out/faults.json \
  --output rfcal_out/fault_measurements.json
```

Run the full deterministic validation sweep:

```bash
python -m openru_x6.rfcal validate --output results/rfcal_validation
```

Quick smoke sweep:

```bash
python -m openru_x6.rfcal validate --quick --output results/rfcal_quick
```

The `validate` command writes:

- `validation.json`: all beam and fault records.
- `reference_summary.json`: compact aggregate summary without per-beam records.
- `validation_runs.csv`: flat beam-record table.
- `report.md`: generated summary tables.
- `calibration_example.json` and `calibration_example.csv`: one representative
  simulated calibration table.

Both `scripts/rfcal_validate.py` and `scripts/rfcal_demo.sh` wrap the same CLI.

## Package layout

- `topology.py`: sites, feeds, chain ownership, JSON/CSV topology I/O.
- `beamforming.py`: array response, steering weights, codebooks.
- `quantization.py`: phase and attenuation quantization constraints.
- `measurement.py`: synthetic pilot IQ generation and fault injection.
- `calibration.py`: least-squares path estimates, diagnostics, calibration and
  fault classification.
- `metrics.py`: pointing error, coherent array gain, peak sidelobe, calibration
  accuracy.
- `validation.py`: deterministic sweeps, aggregation, JSON/CSV/Markdown reports.
- `cli.py`: `python -m openru_x6.rfcal` entry point.

## Calibration modes

`calibrate()` produces measured path amplitudes and phases, fault statuses, and
two correction forms:

- `equalize`: inverse complex path response. This normalizes path amplitude and
  phase to a common target.
- `phase_only`: unit-magnitude phase alignment. This preserves the measured
  path amplitude and is generally better for coherent gain under a total-power
  normalization.

Use `apply_calibration(weights, calibration, mode="phase_only")` or
`mode="equalize"`. Faulty, missing, and inconsistent paths receive zero
corrections and are excluded from the beam.

## Default constraints

The default quantizer is a software model of reported ADAR1000 capabilities:

- Phase step: `2.8125 deg` (128 states, approximately the reported 2.8 degrees).
- Gain step: `0.5 dB`.
- Gain range: `31 dB`.

These values are configurable. They are not a measured 8.4 GHz device
characterization. Do not implement register writes from this model without a
firmware-level and measured qualification.

## Metric definitions

- `array_gain_db = 10 log10(|w^T a|^2 / ||w||^2)` with optional per-path
  complex responses. This is coherent gain relative to one unit-amplitude feed.
- `pointing_error_deg`: great-circle angle between the target direction and the
  measured pattern peak near the target.
- `peak_sidelobe_db`: highest pattern value outside the broadside first-null
  exclusion on an azimuth cut, normalized to the peak.
- `phase_quantization_loss_db`: target-direction gain difference between ideal
  and quantized weights.
- Calibration accuracy is evaluated against synthetic truth on paths classified
  as healthy. It is not a hardware accuracy claim.

See `docs/rfcal/MATH.md` for the equations and `docs/rfcal/REPORT.md` for the
measured synthetic results and eventual hardware-integration requirements.
