"""OCR tool: extract text from photographed/handwritten inspection logs.

Wraps the system ``tesseract`` binary (via ``pytesseract``) with light
preprocessing (grayscale + 2x upscale, which measurably helps tesseract on
phone-camera-style input). The important contract for downstream phases:
never return garbage silently. :func:`extract_log_text_with_confidence`
pairs the text with a mean word-confidence score and an explicit
``low_confidence`` flag so Phase 4's recovery/retry logic can decide to
re-shoot, escalate to a human, or refuse — instead of reasoning over
misread numbers.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass

from PIL import Image

try:
    import pytesseract
    from pytesseract import Output
except ImportError:  # pragma: no cover - import-time guard
    pytesseract = None  # type: ignore[assignment]
    Output = None  # type: ignore[assignment]

#: Below this mean word-confidence (0-100), results are flagged for review.
LOW_CONFIDENCE_THRESHOLD = 40.0


@dataclass(frozen=True)
class OcrResult:
    """Structured OCR outcome — text plus a quality signal."""

    text: str
    mean_confidence: float
    low_confidence: bool


def _require_tesseract() -> None:
    if pytesseract is None:
        raise RuntimeError(
            "pytesseract is not installed; run `pip install pytesseract`"
            " inside the project .venv."
        )
    if shutil.which("tesseract") is None:
        raise RuntimeError(
            "tesseract OCR binary not found on PATH; install it with the"
            " OS package manager (e.g. `pacman -S tesseract"
            " tesseract-data-eng`)."
        )


def extract_log_text_with_confidence(
    image_path: str,
    *,
    low_confidence_threshold: float = LOW_CONFIDENCE_THRESHOLD,
) -> OcrResult:
    """OCR ``image_path`` and return text with a confidence signal.

    Raises:
        FileNotFoundError: if ``image_path`` does not exist.
        ValueError: if the file is not a readable image.
        RuntimeError: if pytesseract or the tesseract binary is missing.
    """
    _require_tesseract()
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"inspection log image not found: {image_path}")
    try:
        with Image.open(image_path) as img:
            gray = img.convert("L")
            w, h = gray.size
            prepared = gray.resize((w * 2, h * 2), Image.LANCZOS)
    except Exception as exc:
        raise ValueError(f"cannot read image file: {image_path}") from exc

    assert pytesseract is not None and Output is not None  # for type checkers
    text = pytesseract.image_to_string(prepared) or ""
    data = pytesseract.image_to_data(prepared, output_type=Output.DICT)
    # tesseract reports conf -1 for non-word blocks; only real words count.
    confs = [float(c) for c in data.get("conf", []) if float(c) >= 0]
    mean_conf = sum(confs) / len(confs) if confs else 0.0
    low = (not text.strip()) or (not confs) or (mean_conf < low_confidence_threshold)
    return OcrResult(text=text, mean_confidence=mean_conf, low_confidence=low)


def extract_log_text(image_path: str) -> str:
    """Return the raw OCR'd text of the inspection log at ``image_path``."""
    return extract_log_text_with_confidence(image_path).text
