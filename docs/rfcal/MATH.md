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

## 2. Polarization Jones model

Each dual-polarized site has a V/H receive port pair. An incident field is a
Jones vector

```text
e_in = [e_V, e_H]^T,   ||e_in|| = 1.
```

Linear polarization at angle `psi` from V is

```text
e_in = [cos(psi), sin(psi) exp(j phi)]^T.
```

Circular polarization uses `[1, -j]^T / sqrt(2)` for RHCP and
`[1, +j]^T / sqrt(2)` for LHCP in this V/H convention. The orthogonal Jones
vector is

```text
e_perp = [-conj(e_H), conj(e_V)]^T.
```

A site Jones matrix maps the incident field to the two site ports:

```text
J_s = [[1,                  epsilon_s],
       [epsilon_s,          1        ]],
epsilon_s = 10^(-XPD_dB/20) exp(j(phi_x + s Delta_x)).
```

The default `XPD_dB = 25`, `phi_x = 90 deg`, and `Delta_x = 0` are engineering
assumptions, not measured isolation. The feed row for a V feed is the first row
of `J_s`; for an H feed it is the second row:

```text
g_f = J_{s(f), pol(f), :} e_in.
```

A receiver is represented by a Jones vector `r`. Its port weight for a V feed is
`r_V`; for an H feed it is `r_H`. A receiver matched to the incident field uses

```text
r = conj(e_in).
```

The polarized steering weights are

```text
w_f = a_f^*(target) r_{pol(f)} / max_g |a_g(target) r_{pol(g)}|.
```

The polarized array factor is

```text
F_pol(w, u) = sum_f w_f a_f(u) g_f h_f,
```

where `h_f` is the optional complex path response. The coherent gain is

```text
G_pol(w, u) = |F_pol(w, u)|^2 / ||w||^2.
```

For a V-matched receiver on 8 dual-polarized sites, only the 8 V ports receive
the co-pol field, so the ideal gain is `8`, or `9.0309 dB`, relative to one
unit-amplitude feed. For a circular field, all 16 ports receive one orthogonal
component each with amplitude `1/sqrt(2)`; the matched coherent gain is still
`8`, because the array has 8 spatial sites. The scalar baseline below instead
sums 16 unit-amplitude feeds and reaches `16`, or `12.0412 dB`; that baseline
double-counts the two polarization ports and is not the current-H2 vector
capability.

Cross-pol gain is computed with the same weights and the orthogonal incident
field `e_perp`. XPD is

```text
XPD_dB = G_co_pol_dB - G_cross_pol_dB.
```

## 3. Steering and calibration

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
the beam. In the hierarchical model, chain and feed corrections are kept
separate: an estimate of feed phase is never folded into a chain correction.

## 4. Quantization

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

## 5. Synthetic IQ model

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

## 6. Per-path estimation

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

## 7. Observability model

For chain `c` and its four feeds `f(c,s)`, write the true chain response `H_c`,
feed response `F_{c,s}`, and CAL path `K_c`. The current H2 provides

```text
chain loopback:  y_c = H_c K_c + noise
feed detector:   p_{c,s} = |H_c F_{c,s}|^2 + noise.
```

The chain observations give four complex products, not four independent chain
and CAL responses. The feed observations give sixteen real magnitudes. The
feed-phase subproblem is therefore underdetermined: changing the phase of
`F_{c,s}` while adjusting the phases of the other feeds on the same chain can
leave every H2 observation unchanged. Relative chain common-path phase is
observable at the CAL coupler after a fresh loopback; feed phase is not.

A per-feed complex architecture replaces the detector equation with

```text
feed IQ:  z_{c,s} = H_c F_{c,s} K_{c,s} + noise.
```

When the CAL/switch path `K_{c,s}` is characterized separately, the feed
response `H_c F_{c,s}` is observable. A proposed switched H3 path measures one
feed at a time:

```text
z_{c,s} = H_c F_{c,s} S_s K_c + noise,
```

where `S_s` is the characterized switch/combiner path. De-embedding `S_s K_c`
and the measured chain common path yields the per-feed response. This is the
architectural basis for the `proposed_switched_feed_loopback` model; it is not a
current-H2 capability.

## 8. Hierarchical calibration

The hierarchical estimator applies chain and feed corrections separately:

```text
w_f^hier = w_f c_chain(f) c_feed(f).
```

For `h2_available`, `c_feed` is amplitude-only and `angle(c_feed) = 0`; the
model reports feed phase as unobservable instead of inventing a phase estimate.
For per-feed-complex architectures, `c_feed` includes the measured feed phase.
Corrections for failed or missing chains are zeroed, and chain failure overrides
the status of all feeds on that chain. Feed faults are classified only from
feed-level observations; chain faults are not mislabelled as feed faults.

## 9. Fault classification

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
are software policy, not calibrated hardware limits. A phase-only feed fault is
invisible to the H2 power detectors; it is detectable only with a per-feed
complex observation.

## 10. Beam metrics

The coherent array gain is

```text
G(w, u) = |F(w, u)|^2 / ||w||^2.
```

For ideal conjugate scalar weights and 16 unit-amplitude feeds, `G = 16`, or
`12.0412 dB` relative to one feed. With measured path responses, `F` includes
`h_f`. The scalar result is retained as a labelled baseline; the polarized
model uses `G_pol` from Section 2.

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

## 11. Validation sweep

The scalar validation sweep evaluates:

- 10 random seeds.
- SNR values `10, 20, 30, 40 dB`.
- Mismatch scales `0, 0.5, 1, 2` relative to the base mismatch model.
- Five azimuth/elevation targets.
- Uncalibrated, equalized, phase-only, and phase-only quantized beams.
- Missing and faulty paths for each of the four RF chains.

The expected scalar records are

```text
10 seeds * 4 SNRs * 4 mismatch scales * 5 angles * 5 beam scenarios
= 4000 beam records,
plus 3 fault seeds * 2 fault types * 4 chains = 24 fault records.
```

The observability sweep repeats the beam sweep for five architectures:
`h2_available`, `factory_vna_feed_table`, `near_field_probe`,
`proposed_switched_feed_loopback`, and `ideal_16iq_nonrealizable`:

```text
10 seeds * 4 SNRs * 4 mismatch scales * 5 angles * 5 scenarios * 5 architectures
= 20,000 vector beam records.
```

It also evaluates chain and feed faults for every architecture:

```text
3 fault seeds * 5 architectures * (4 chains * 2 fault types
                                  + 16 feeds * 2 fault types)
= 600 fault records.
```

A separate 250-record scalar baseline is computed at the base SNR and mismatch
for the same seeds and five angles. It is labelled as the original per-feed-IQ
assumption and is not an available H2 measurement path.

## 12. Limitations

- All IQ, path responses, polarization leakage, and calibration tables are
  synthetic.
- The model does not include mutual coupling, measured element patterns,
  temperature drift, phase noise, ADC effects, or nonlinear RF compression.
- The assumed 25 dB cross-pol and 90 degree leakage phase are not measured.
- The ADAR1000 is not qualified at 8.4 GHz.
- The model does not write registers or control a transmitter.
- The current H2 cannot identify per-feed phase; only chain-relative complex
  response and per-feed amplitude are observable without an external fixture or
  an H3 hardware change.
- Measured hardware behavior must replace the synthetic truth before any
  hardware performance claim is made.
