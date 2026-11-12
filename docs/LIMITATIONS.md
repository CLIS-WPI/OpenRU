# Limitations

- No physical RF, PCB, EM, thermal or antenna measurement is made.
- The channel and RF impairment models are behavioral abstractions; absolute
  throughput and SINR are not hardware predictions.
- RIS and ISAC results are model outputs. The RIS oracle is not implementable.
- The OCUDU integration is DU/PHY test-mode only. Open Fronthaul and
  interoperability are not tested; `ru_emu` is unavailable in the pinned image.
- The Docker socket mount needed by E10 grants the container host-level Docker
  control. Use only in a trusted lab environment.
- Full-suite confidence intervals use seeded simulation runs; they quantify
  model Monte Carlo uncertainty, not deployment uncertainty.
- Low-SINR cell-edge users can be in outage because of modeled path loss and
  blockage. This is a model result, not evidence that a real array cannot serve
  them.
- Low-load energy savings are not free: the suite reports a matched-traffic
  goodput delta and a deadline-expired-fraction delta alongside the saving. In
  the current model the predictive policy saves energy but is not QoS-neutral;
  it is not presented as a QoS-safe default.
- Normal self-healing actions go through the control plane. Only the independent
  emergency mute retains direct hardware actuation as a fail-safe path; E05 is
  a role-policy simulator, not credential/mTLS/secure-element evidence.
- Telemetry seeding/drift/quantization are behavioral models. P1 adds missing,
  biased, frozen, stale, quantized and inconsistent sensor cases plus held-out
  fault families, but these remain simulation sensitivity tests, not established
  hardware robustness.
- Completed-service P99 can exceed the deadline because late service is
  included. Expired/dropped/queued censoring is reported separately; it is not
  a claim that all users meet their deadline.
- P1 is a reduced local suite. Its 500-slot paired comparisons and single
  20,000-slot profile are explicitly not a deployment-scale matrix. A `PASS` in
  a reduced suite does not establish complete verification; mandatory full-suite
  status is authoritative.
