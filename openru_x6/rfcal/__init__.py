"""Hardware-independent beamforming and calibration model for OpenRU-X6.

The package produces only simulated data.  It does not write RFIC registers,
control transmitters, or make hardware-measured performance claims.
"""

from .beamforming import (
    Codebook,
    CodebookConfig,
    generate_codebook,
    steering_weights,
)
from .calibration import (
    CalibrationConfig,
    CalibrationResult,
    apply_calibration,
    calibrate,
    corrections_for_mode,
)
from .measurement import (
    FaultSpec,
    MeasurementConfig,
    MeasurementSet,
    MismatchConfig,
    simulate_measurements,
)
from .metrics import (
    BeamMetrics,
    array_gain_db,
    beam_metrics,
    peak_sidelobe_db,
    pointing_error_deg,
    quantization_loss_db,
)
from .quantization import QuantizedWeights, QuantizerConfig, quantize_weights
from .topology import Feed, Site, Topology, load_topology
from .validation import ValidationConfig, ValidationReport, run_validation

__all__ = [
    "BeamMetrics",
    "CalibrationConfig",
    "CalibrationResult",
    "Codebook",
    "CodebookConfig",
    "FaultSpec",
    "Feed",
    "MeasurementConfig",
    "MeasurementSet",
    "MismatchConfig",
    "QuantizedWeights",
    "QuantizerConfig",
    "Site",
    "Topology",
    "ValidationConfig",
    "ValidationReport",
    "apply_calibration",
    "array_gain_db",
    "beam_metrics",
    "calibrate",
    "corrections_for_mode",
    "generate_codebook",
    "load_topology",
    "peak_sidelobe_db",
    "pointing_error_deg",
    "quantization_loss_db",
    "quantize_weights",
    "run_validation",
    "simulate_measurements",
    "steering_weights",
]

__version__ = "0.1.0"
