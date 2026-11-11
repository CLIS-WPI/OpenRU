# Models

## RF and array

- 16 tiles x 4 chains/tile = 64 RF chains; 4 feeds/chain = 256 feeds.
- Every feed is owned by exactly one chain; every chain drives four feeds.
- Chain masks are row-normalized to preserve tile spread at 8/16/32/64 chains.
- Analog beam weights are indexed by the physical chain ID, not by the
  chain-assignment order; this preserves the intended direction for reduced
  masks.
- Per-chain power is limited by `configs/radio.yaml`; zero TX power yields zero
  PA DC draw in the energy model.

## Channel and link

- Path loss uses a close-in/log-distance model with shadowing and optional
  blockage; blockage is applied once, in the LOS/NLOS decision, not again to the
  ray path. Large path-loss outliers are retained rather than clipped.
- Small-scale fading is generated as complex Gaussian channel matrices with
  mobility and CSI age/delay/phase/quantization errors.
- Effective SINR includes inter-user interference, analog beam gain, noise
  figure and per-chain power scaling.
- Link adaptation uses calibrated SINR-to-BLER curves. Resource accounting uses
  an explicit NR grid (273 PRB, 11 DL symbols, TDD/control/DMRS/SSB overheads);
  `capacity_bps` is a spectral-efficiency bound and delivered goodput is reported
  separately. Abstract rates are not claimed as measured 5G throughput.

## Energy and thermal

- State power is built from always-on, DSP/FPGA, RF-chain electronics, feed
  branches, PA DC, cooling and sleep standby terms.
- Thermal behavior is a lumped RC model with fan failure, throttle and trip
  thresholds; it is not CFD.
- The energy manager enforces minimum dwell, wake-up delay, hysteresis and the
  sole-coverage-cell sleep prohibition. A waking state provides no RF service,
  and transition energy is charged explicitly.
- Energy-policy load is backlog bits divided by peak schedulable airtime, not
  the fraction of UEs with a non-empty queue.
- Traffic QoS uses per-user deadline cohorts. Bits still queued when a deadline
  passes are counted as expired, and overflow drops are counted separately;
  the violation numerator is the union of expired and dropped bits. Queue
  accounting enforces `arrived = served + dropped + queued`. Reported latency
  percentiles are weighted completion delays for all served bits, including
  late service; expired, dropped and end-of-run queued bits are reported as
  censoring/deadline-miss fractions rather than completion samples.

## Diagnostics, RIS, ISAC, fronthaul

- The detector uses robust per-tile z-scores over gain, phase, VSWR, temperature,
  supply, PTP, noise figure and fan telemetry; calibration is empirical from
  healthy runs with seeds independent of evaluation runs.
- Each hardware instance has a seedable telemetry RNG plus slow correlated
  drift and quantization floors, so calibration, healthy and fault runs do not
  share one sensor-noise realization.
- The detector/planner proposes a normal recovery action; isolation, chain
  reduction, recalibration, PTP resync and power reduction execute through the
  authorized control plane with readback and audit. Only the independent
  emergency mute actuates hardware directly.
- `set_tx_power` updates `RFHardware.tx_power_limit_dbm`, which caps the power
  used by the PHY model. The command is counted as committed only after
  readback verification; rollback restores the prior cap.
- RIS is a geometry-consistent double-hop model with quantized phase and stale
  CSI. The oracle is an unavailable upper bound.
- ISAC senses during a configured fraction of slots with monostatic range
  estimation; episode Pd and per-look Pd/Pfa are reported separately, and the
  communication/sensing tradeoff is reported as modeled.
- Fronthaul models packet loss, jitter, compression EVM and sync loss, including
  eCPRI-like timing effects at the abstraction level.
