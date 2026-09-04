"""Real OCR tests — tesseract runs against a committed fixture image."""

from __future__ import annotations

import difflib
import os
import re

import pytest
from PIL import Image

from tools.ocr import (
    extract_log_text,
    extract_log_text_with_confidence,
)

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures",
                       "inspection-log.png")


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.upper()).strip()


def contains_fuzzy(haystack: str, needle: str, threshold: float = 0.8) -> bool:
    """True if needle appears verbatim or closely in haystack (OCR fuzz)."""
    hay = normalize(haystack)
    ndl = normalize(needle)
    if ndl in hay:
        return True
    return any(
        difflib.SequenceMatcher(None, ndl, token).ratio() >= threshold
        for token in hay.split(" ")
    )


def test_fixture_exists():
    assert os.path.isfile(FIXTURE), "OCR fixture image missing from repo"


def test_extract_log_text_recovers_key_readings():
    """Key equipment ID and numeric readings must survive real OCR."""
    text = extract_log_text(FIXTURE)
    assert contains_fuzzy(text, "PUMP-214"), f"equipment ID lost: {text!r}"
    assert contains_fuzzy(text, "7.2"), f"pressure reading lost: {text!r}"
    assert contains_fuzzy(text, "2026-09-03"), f"date lost: {text!r}"
    assert contains_fuzzy(text, "DB"), f"inspector initials lost: {text!r}"


def test_structured_result_reports_high_confidence_on_fixture():
    result = extract_log_text_with_confidence(FIXTURE)
    assert result.text.strip(), "expected non-empty OCR text"
    assert result.mean_confidence > 40.0, result.mean_confidence
    assert result.low_confidence is False


def test_blank_image_flags_low_confidence(tmp_path):
    """Unreadable input must be flagged, not returned as silent garbage."""
    blank = str(tmp_path / "blank.png")
    Image.new("RGB", (600, 400), (255, 255, 255)).save(blank)
    result = extract_log_text_with_confidence(blank)
    assert result.low_confidence is True
    assert result.mean_confidence < 40.0


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        extract_log_text(str(tmp_path / "nope.png"))


def test_unreadable_file_raises(tmp_path):
    fake = str(tmp_path / "fake.png")
    with open(fake, "w") as fh:
        fh.write("not an image at all")
    with pytest.raises(ValueError):
        extract_log_text(fake)
