"""Tool plugins (dsh-hosted in later phases; plain Python modules for now)."""

from tools.calculate import (
    RULE_PRESSURE_VESSEL_MARGIN,
    CalculationResult,
    run_calculation,
)
from tools.ocr import (
    OcrResult,
    extract_log_text,
    extract_log_text_with_confidence,
)

__all__ = [
    "CalculationResult",
    "OcrResult",
    "RULE_PRESSURE_VESSEL_MARGIN",
    "extract_log_text",
    "extract_log_text_with_confidence",
    "run_calculation",
]
