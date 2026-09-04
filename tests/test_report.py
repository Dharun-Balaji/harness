"""Report tests — inputs are REAL 3a/3b/3c outputs, and the .docx is
reopened with python-docx and content-checked (never just exists/size).
"""

from __future__ import annotations

import os

import pytest
from docx import Document

from authorize.seed import seed as seed_demo_db
from tools.calculate import RULE_PRESSURE_VESSEL_MARGIN, run_calculation
from tools.lookup import lookup_document
from tools.ocr import extract_log_text_with_confidence
from tools.report import generate_report

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE_PNG = os.path.join(REPO_ROOT, "tests", "fixtures", "inspection-log.png")
SHIPPED_SOP_DIR = os.path.join(REPO_ROOT, "docs", "sops")
TS = "2026-09-04T12:00:00+00:00"


@pytest.fixture()
def diagnosis(tmp_path, monkeypatch):
    """Real OCR + real sandboxed calc + real gated lookups (seeded demo DB)."""
    db_path = str(tmp_path / "demo.db")
    monkeypatch.setenv("WORKBENCH_AUTH_DB", db_path)
    monkeypatch.setenv("WORKBENCH_SOP_DIR", SHIPPED_SOP_DIR)
    seed_demo_db(db_path)
    ocr = extract_log_text_with_confidence(FIXTURE_PNG)
    calc = run_calculation({"equipment_id": "PUMP-214", "pressure_bar": 7.2},
                           RULE_PRESSURE_VESSEL_MARGIN)
    assert ocr.text.strip() and calc.error is None  # real outputs, sanity
    senior_sop = lookup_document("senior-inspector",
                                 "sop-pressure-vessel-repair", {})
    junior_sop = lookup_document("junior-inspector",
                                 "sop-pressure-vessel-repair", {})
    assert senior_sop.found is True and junior_sop.found is False
    return {"ocr": ocr, "calc": calc,
            "senior_sop": senior_sop, "junior_sop": junior_sop}


def read_docx_text(path) -> str:
    """Reopen the generated Word file and return all paragraph text."""
    doc = Document(str(path))  # raises if not a real .docx
    return "\n".join(p.text for p in doc.paragraphs)


def test_report_contains_real_pipeline_values(diagnosis, tmp_path):
    out = tmp_path / "report.docx"
    path = generate_report({
        "equipment_id": "PUMP-214",
        "subject": "senior-inspector",
        "timestamp": TS,
        "ocr": diagnosis["ocr"],
        "calculation": diagnosis["calc"],
        "sop_requested": "sop-pressure-vessel-repair",
        "sop": diagnosis["senior_sop"],
    }, str(out))
    assert path.suffix == ".docx"
    text = read_docx_text(path)
    assert "PUMP-214" in text
    assert "senior-inspector" in text
    assert TS in text
    assert "7.2" in text  # OCR'd reading quoted in the report
    assert "PASS" in text and "2.8" in text  # calc verdict + margin
    assert "sop-pressure-vessel-repair" in text  # SOP cited
    assert "10.0 bar" in text  # quoted SOP content


def test_report_states_sop_unavailable_explicitly(diagnosis, tmp_path):
    """Denied lookup must produce an explicit section, not silence."""
    out = tmp_path / "report-junior.docx"
    path = generate_report({
        "equipment_id": "PUMP-214",
        "subject": "junior-inspector",
        "timestamp": TS,
        "ocr": diagnosis["ocr"],
        "calculation": diagnosis["calc"],
        "sop_requested": "sop-pressure-vessel-repair",
        "sop": diagnosis["junior_sop"],
    }, str(out))
    text = read_docx_text(path)
    assert "SOP reference" in text  # section present, not omitted
    assert "SOP reference unavailable to this user" in text
    assert "isolate the vessel" not in text  # restricted content absent
    assert "RESTRICTED" not in text


def test_report_states_no_sop_consulted(diagnosis, tmp_path):
    out = tmp_path / "report-nosop.docx"
    path = generate_report({
        "equipment_id": "PUMP-214",
        "subject": "senior-inspector",
        "timestamp": TS,
        "ocr": diagnosis["ocr"],
        "calculation": diagnosis["calc"],
        "sop_requested": None,
        "sop": None,
    }, str(out))
    text = read_docx_text(path)
    assert "No SOP reference was consulted for this inspection." in text


def test_report_rejects_bad_input(tmp_path):
    with pytest.raises(TypeError):
        generate_report({"subject": "x"})  # missing equipment_id
    with pytest.raises(ValueError):
        generate_report({"equipment_id": "PUMP-214"},
                        str(tmp_path / "report.txt"))
