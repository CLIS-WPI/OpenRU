"""Real OCUDU test-mode integration constants and configuration location."""
from pathlib import Path

from ..config import CONFIG_DIR

IMAGE = "registry.gitlab.com/ocudu/ocudu/ocudu_nightly_avx2:latest"
CONFIG_PATH = Path(CONFIG_DIR) / "ocudu_gnb_testmode.yml"
EVIDENCE_NOTE = (
    "ru_dummy + test_mode DU/PHY evidence only; not OFH interoperability "
    "and not an RF measurement"
)

__all__ = ["IMAGE", "CONFIG_PATH", "EVIDENCE_NOTE"]
