"""Tool plugins (dsh-hosted in later phases; plain Python modules for now)."""

from tools.ocr import (
    OcrResult,
    extract_log_text,
    extract_log_text_with_confidence,
)

__all__ = [
    "OcrResult",
    "extract_log_text",
    "extract_log_text_with_confidence",
]
