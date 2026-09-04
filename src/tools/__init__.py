"""Tool plugins (dsh-hosted in later phases; plain Python modules for now)."""

from tools.calculate import (
    RULE_PRESSURE_VESSEL_MARGIN,
    CalculationResult,
    run_calculation,
)
from tools.lookup import DocumentResult, lookup_document
from tools.ocr import (
    OcrResult,
    extract_log_text,
    extract_log_text_with_confidence,
)
from tools.report import generate_report

__all__ = [
    "CalculationResult",
    "DocumentResult",
    "OcrResult",
    "RULE_PRESSURE_VESSEL_MARGIN",
    "extract_log_text",
    "extract_log_text_with_confidence",
    "generate_report",
    "lookup_document",
    "run_calculation",
]
