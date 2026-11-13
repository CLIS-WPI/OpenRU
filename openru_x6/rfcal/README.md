# OpenRU-X6 RF Beamforming and Calibration Model

This package is a hardware-independent, CPU-only model of the documented H1
4T4R / 16-feed OpenRU-X6 topology. It provides geometry-based steering,
configurable beamformer quantization, synthetic complex-IQ measurements,
hierarchical chain/feed calibration, polarization-aware Jones metrics, fault
detection, JSON/CSV serialization, and reproducible validation sweeps.

**Evidence label: SIMULATED.** The package does not measure hardware, control a
transmitter, write ADAR1000 registers, or prove performance at 8.4 GHz. The
ADAR1000 remains unqualified at the intended carrier frequency.

## Hardware observability boundary

The current H2 provides a complex calibration loopback per RF chain and a power
detector per feed. It does **not** provide 16 independent complex feed
observations. In this model:

- `h2_available` observes a relative complex chain common-path response at the
  CAL coupler and per-feed power. Feed phase is explicitly unobservable.
- `factory_vna_feed_table` and `near_field_probe` add per-feed complex data with
  an external fixture.
- `proposed_switched_feed_loopback` adds per-chain 4:1 switching to a shared
  complex CAL receiver; it requires an H3 hardware change.
- `ideal_16iq_nonrealizable` is a comparison baseline only.

See `docs/rfcal/CALIBRATION_OBSERVABILITY.md` for the schematic audit and
proposed switched-feed procedure, and `docs/rfcal/RFC_HARDWARE_INTEGRATION.md`
for the H2/H3 interface and integration decision record.

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

Write the schematic-observability audit:

```bash
python -m openru_x6.rfcal audit --output rfcal_out/observability_audit.json
```

Run the full deterministic validation sweep:

```bash
python -m openru_x6.rfcal validate --output results/rfcal_validation
```

Quick smoke sweep:

```bash
python -m openru_x6.rfcal validate --quick --output results/rfcal_quick
```

Run the hardware-impairment and uncertainty sweep:

```bash
python -m openru_x6.rfcal impairments --output results/rfcal_impairments
```

Quick impairment smoke sweep:

```bash
python -m openru_x6.rfcal impairments --quick --output results/rfcal_impairments_quick
```

The `impairments` command writes `impairments.json`,
`impairment_reference_summary.json`, `impairment_runs.csv`, and
`impairment_report.md`. It adds synthetic reference drift, switch leakage,
phase noise, mutual coupling, and correlated calibration errors, and audits the
angular-search resolution floor. These are simulated sensitivities, not
measured hardware distributions.

Use `--architectures` to restrict the observability sweep, for example:

```bash
python -m openru_x6.rfcal validate \
  --architectures h2_available,proposed_switched_feed_loopback \
  --output results/rfcal_observability
```

The `validate` command writes the scalar baseline:

- `validation.json`: all beam and fault records.
- `reference_summary.json`: compact aggregate summary without per-beam records.
- `validation_runs.csv`: flat beam-record table.
- `report.md`: generated summary tables.
- `calibration_example.json` and `calibration_example.csv`: one representative
  simulated calibration table.

It also writes the observability/Jones results:

- `observability_validation.json`: all vector/Jones beam and fault records.
- `observability_reference_summary.json`: compact aggregate without records.
- `observability_runs.csv`: flat vector beam-record table.
- `observability_report.md`: generated vector, scalar-baseline, and fault tables.
- `observability_audit.json`: H1/H2 observability audit evidence.

Both `scripts/rfcal_validate.py` and `scripts/rfcal_demo.sh` wrap the same CLI.

## Package layout

- `topology.py`: sites, feeds, chain ownership, JSON/CSV topology I/O.
- `beamforming.py`: scalar array response, steering weights, codebooks.
- `polarization.py`: Jones vectors, site/feed Jones matrices, polarized
  steering, polarized array factor and gain.
- `quantization.py`: phase and attenuation quantization constraints.
- `measurement.py`: synthetic pilot IQ generation and fault injection.
- `calibration.py`: per-path least-squares estimates, diagnostics, calibration,
  and fault classification.
- `hierarchical.py`: observable chain/feed measurement set, hierarchical
  calibration, chain/feed de-embedding, and accuracy.
- `observability.py`: H2 schematic audit and architecture identifiability model.
- `metrics.py`: scalar and polarized pointing, gain, sidelobe, XPD, and
  quantization metrics.
- `validation.py`: scalar baseline sweeps and reports.
- `observability_validation.py`: observability-aware vector/Jones sweeps and
  scalar-baseline comparison.
- `impairments.py`: synthetic hardware-impairment, uncertainty, and
  angular-search resolution sweeps.
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

`apply_hierarchical_calibration()` accepts `mode="chain_only"`, `mode="equalize"`,
and `mode="phase_only"`. On `h2_available`, feed corrections are amplitude-only;
feed phase remains explicitly unobservable.

## Default constraints

The default quantizer is a software model of reported ADAR1000 capabilities:

- Phase step: `2.8125 deg` (128 states, approximately the reported 2.8 degrees).
- Gain step: `0.5 dB`.
- Gain range: `31 dB`.

These values are configurable. They are not a measured 8.4 GHz device
characterization. Do not implement register writes from this model without a
firmware-level and measured qualification.

The default polarization model uses `25 dB` cross-pol leakage, `90 deg` leakage
phase, and zero site phase step. These are engineering assumptions, not measured
H1/H2 isolation values.

## Metric definitions

- Scalar `array_gain_db = 10 log10(|w^T a|^2 / ||w||^2)` with optional per-path
  complex responses. This is the original 16-feed baseline and is clearly
  labelled as the per-feed-IQ assumption.
- Polarized `array_gain_polarized_db` uses a site Jones matrix, an incident
  field, and a receiver Jones vector. A V-matched receiver on 8 dual-polarized
  sites reaches `9.0309 dB`, not the scalar `12.0412 dB`; the two metrics are
  not interchangeable.
- `pointing_error_deg`: great-circle angle between the target direction and the
  measured pattern peak near the target.
- `peak_sidelobe_db`: highest pattern value outside the broadside first-null
  exclusion on an azimuth cut, normalized to the peak.
- `cross_pol_discrimination_db`: co-pol gain minus cross-pol gain; with the
  default assumed leakage this is exactly `25 dB`.
- `phase_quantization_loss_db`: target-direction gain difference between ideal
  and quantized weights.
- Calibration accuracy is evaluated against synthetic truth on paths classified
  as healthy. It is not a hardware accuracy claim.

See `docs/rfcal/MATH.md` for the equations,
`docs/rfcal/CALIBRATION_OBSERVABILITY.md` for the H2 measurement boundary, and
`docs/rfcal/REPORT.md` for the measured synthetic results and hardware
integration requirements.
