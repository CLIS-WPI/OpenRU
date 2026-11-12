# RF Calibration Model Mathematics

## 1. Geometry and sign convention

The documented H1 topology has 16 feeds at positions

```text
r_f = (0, y_f, z_f),  f = 0, ..., 15
```

with broadside along `+x`. For azimuth `phi` and elevation `theta`, the unit
direction is

```text
u(phi, theta) = (cos(theta) cos(phi),
                 cos(theta) sin(phi),
                 sin(theta)).
```

The per-feed array response is

```text
a_f(phi, theta) = exp(j k r_f . u(phi, theta)),
k = 2 pi / lambda,
lambda = c / f_c.
```

The complex array factor for weights `w` is

```text
F(w, u) = sum_f w_f a_f(phi, theta).
```

The package uses `w^T a`, not `w^H a`, because the steering weights already
contain the conjugate phase. This convention is used consistently in the code
and metrics.

## 2. Steering and calibration

Conjugate steering at a target direction is

```text
w_f = a_f^*(target) / max_f |a_f(target)|.
```

A calibrated beam applies a per-path correction `c_f`:

```text
w_f^cal = w_f c_f.
```

Two correction modes are produced:

- Equalized correction:

```text
c_f^eq = h_target / h_f,
```

where `h_f` is the estimated complex path response and `h_target` is a robust
common target amplitude and circular-mean phase.

- Phase-only correction:

```text
c_f^phase = exp(j angle(h_target)) exp(-j angle(h_f)).
```

The equalized form normalizes both amplitude and phase. The phase-only form
preserves measured path amplitude and is usually better for coherent gain when
the metric is normalized by total applied weight power.

Failed, missing, and inconsistent paths receive `c_f = 0` and are excluded from
the beam.

## 3. Quantization

The complex weight is represented by an attenuation and a phase:

```text
w_f = A_f exp(j psi_f).
```

Attenuation is measured relative to the largest requested feed amplitude:

```text
att_f = -20 log10(|w_f| / max_g |w_g|).
```

The configured attenuation range is `[0, att_max]`, quantized in `Delta_A` dB
steps:

```text
att_f^q = round(clip(att_f, 0, att_max) / Delta_A) Delta_A.
```

Phase is quantized in `Delta_psi` steps:

```text
psi_f^q = round(psi_f / Delta_psi) Delta_psi.
```

The default software constraints are `Delta_psi = 2.8125 deg`,
`Delta_A = 0.5 dB`, and `att_max = 31 dB`. They reflect reported ADAR1000
capabilities and are not a measured qualification at 8.4 GHz.

## 4. Synthetic IQ model

For path `f`, capture `c`, and sample `n`, the emulator generates

```text
y_{f,c,n} = h_{f,c} x_n + n_{f,c,n},
```

where `x_n` is a known complex pilot, `h_{f,c}` is the simulated complex path
response, and `n_{f,c,n}` is circular complex Gaussian noise. Noise power is set
from the configured per-path SNR. The truth response contains chain-level and
feed-level gain and phase mismatch. Injections support:

- `missing`: zero response and zero IQ.
- `faulty`: a deterministic large gain and/or phase offset.
- `inconsistent`: capture-to-capture random phase and gain variation.

All generated data is labelled `SIMULATED`; no hardware measurement is created.

## 5. Per-path estimation

For each path, the least-squares complex response per capture is

```text
h_c = sum_n x_n^* y_{c,n} / sum_n |x_n|^2.
```

The reported path response is the mean of the capture estimates. The pilot
coherence is

```text
rho = |sum_{c,n} x_n^* y_{c,n}|
      / sqrt(sum_{c,n} |x_n|^2 sum_{c,n} |y_{c,n}|^2).
```

The residual after subtracting `h_c x` gives an estimated SNR. Capture-to-capture
phase variability is measured with the circular standard deviation:

```text
R = |mean_c exp(j angle(h_c))|,
sigma_psi = sqrt(-2 log R).
```

The gain variability is the standard deviation of the per-capture amplitudes in
dB.

## 6. Fault classification

The classifier uses robust relative thresholds:

1. A path is `missing` when its amplitude is more than
   `missing_relative_db` below the healthy-path median.
2. A path is `inconsistent` when pilot coherence or capture-to-capture
   variability exceeds the configured threshold.
3. A path is `faulty` when its amplitude or phase is an outlier relative to the
   healthy-path median.
4. Otherwise it is `ok`.

The defaults are deliberately wider than the synthetic normal mismatch
distribution so ordinary path-to-path variation is not flagged. The thresholds
are software policy, not calibrated hardware limits.

## 7. Beam metrics

The coherent array gain is

```text
G(w, u) = |F(w, u)|^2 / ||w||^2.
```

For ideal conjugate weights and 16 unit-amplitude feeds, `G = 16`, or
`12.0412 dB` relative to one feed. With measured path responses, `F` includes
`h_f`.

Pointing error is the great-circle angle

```text
Delta = arccos(u_target . u_peak)
```

between the target and the nearest pattern peak. The search is a fine
azimuth/elevation grid around the target.

For the broadside azimuth cut, the main-lobe exclusion is derived from the
first null of the sampled aperture. The peak sidelobe is the maximum outside
that exclusion, normalized to the pattern peak.

Quantization loss is

```text
L_Q = G_ideal(dB) - G_quantized(dB)
```

at the target direction.

Calibration accuracy against truth is evaluated only on paths classified as
healthy. It reports RMS phase error and RMS gain error of
`h_f^truth c_f` relative to the calibration target.

## 8. Validation sweep

The default validation run evaluates:

- 10 random seeds.
- SNR values `10, 20, 30, 40 dB`.
- Mismatch scales `0, 0.5, 1, 2` relative to the base mismatch model.
- Five azimuth/elevation targets.
- Uncalibrated, equalized, phase-only, and phase-only quantized beams.
- Missing and faulty paths for each of the four RF chains.

The expected generated records are therefore:

```text
10 seeds * 4 SNRs * 4 mismatch scales * 5 angles * 5 beam scenarios
= 4000 beam records,
plus 3 fault seeds * 2 fault types * 4 chains = 24 fault records.
```

## 9. Limitations

- All IQ and path responses are synthetic.
- The model does not include mutual coupling, element patterns, polarization
  leakage, temperature drift, phase noise, ADC effects, or nonlinear RF
  compression.
- The ADAR1000 is not qualified at 8.4 GHz.
- The model does not write registers or control a transmitter.
- Measured hardware behavior must replace the synthetic truth before any
  hardware performance claim is made.
