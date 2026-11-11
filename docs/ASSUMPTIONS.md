# Assumptions

- All quantitative results are simulation outputs unless explicitly labelled
  `PHY_VALIDATED` or `OCUDU_TESTED`.
- `HARDWARE_MEASURED` is not produced by this repository.
- Sionna PHY/RT checks corroborate abstractions; they do not calibrate a physical
  array.
- OCUDU test mode exercises DU/MAC/PHY scheduling with a dummy RU and a test UE.
  It does not exercise Open Fronthaul, real timing, RF calibration or a core
  network.
- Timestamps with 4 ns resolution are model resolution, not physical RF switching
  times.
- Thermal and energy values are behavioral estimates; PCB, PA, filter and
  antenna feasibility require hardware measurements.
- The seeded random model is reproducible for a fixed config digest and code
  revision, but is not a statistical guarantee about a real deployment.
- The first physical prototype should be a 4T4R/16-feed tile, not the full array.
