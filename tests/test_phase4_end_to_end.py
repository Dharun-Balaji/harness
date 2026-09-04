"""Phase 4 end-to-end: the scenario runs THROUGH dsh, not around it.

This test boots real dsh (``--profile headless`` + the committed MCP patch
overlay), whose agent loop calls the four workbench tools as registered
``mcp__workbench__*`` plugins over MCP stdio. Nothing here imports the
tool functions directly — the only assertions are on artifacts the dsh
run produced (the .docx report, dsh's own session trajectory). Requires
a working model route in the ambient dsh setup (here: the local
colab-qwen route); slow (LLM + OCR + subprocesses), timeout 9 minutes.
"""

from __future__ import annotations

import glob
import os
import subprocess

from docx import Document

from authorize.seed import seed as seed_demo_db

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DSH_BIN = os.path.join(REPO_ROOT, "node_modules", ".bin", "dsh")
PATCH = os.path.join(REPO_ROOT, "dsh", "workbench.patch.yml")
FIXTURE = os.path.join(REPO_ROOT, "tests", "fixtures",
                       "inspection-log-overpressure.png")
SESSIONS = os.path.expanduser("~/.dsh/sessions/--home-dharun-Downloads-web-hrn--")

TASK = (
    "You are running an industrial inspection diagnosis as subject "
    "senior-inspector. Use ONLY these four tools, in order, no other tools: "
    "mcp__workbench__ocr_inspection_log, mcp__workbench__check_pressure_margin, "
    "mcp__workbench__lookup_sop, mcp__workbench__write_inspection_report. "
    "Steps: 1) OCR this inspection log photo: {fixture}. "
    "2) From the OCR text take equipment ID and pressure and call "
    "check_pressure_margin. If the margin check FAILS, recover by looking up "
    "SOP sop-pressure-vessel-repair as subject senior-inspector and follow "
    "its guidance. If it passes, still look up the SOP for citation. "
    "3) Write the final report to {report} via write_inspection_report with "
    "equipment_id PUMP-214, subject senior-inspector, timestamp "
    "2026-09-04T13:00:00+00:00, the OCR result object, the calculation "
    "result object, sop_requested sop-pressure-vessel-repair, and the lookup "
    "result object. Reply with the single word DONE."
)


def test_end_to_end_through_dsh(tmp_path):
    report = str(tmp_path / "e2e-report.docx")
    seed_demo_db(os.path.join(REPO_ROOT, "data", "auth.db"))  # patch default DB
    before = set(glob.glob(os.path.join(SESSIONS, "*")))

    proc = subprocess.run(
        [DSH_BIN, "--profile", "headless", "--patch", PATCH,
         TASK.format(fixture=FIXTURE, report=report)],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=540,
    )
    assert proc.returncode == 0, f"dsh run failed: {proc.stderr[-2000:]}"
    assert proc.stdout.strip().endswith("DONE")

    # The report dsh's agent wrote, reopened and content-checked.
    text = "\n".join(p.text for p in Document(report).paragraphs)
    assert "PUMP-214" in text
    assert "12.5" in text
    assert "FAIL" in text and "exceeds maximum safe 10.0 bar" in text
    assert "sop-pressure-vessel-repair" in text
    assert "isolate the vessel" in text  # cited restricted SOP made it in

    # dsh's own trajectory captured the four tool calls in order.
    new_dirs = sorted(set(glob.glob(os.path.join(SESSIONS, "*"))) - before,
                      key=os.path.getmtime)
    assert new_dirs, "dsh wrote no session trajectory"
    import subprocess as sp  # local import to keep top tidy
    raw = sp.run(["unzstd", "-c",
                  os.path.join(new_dirs[-1], "session.jsonl.zstd")],
                 capture_output=True, text=True, check=True).stdout
    order = []
    for tool in ("ocr_inspection_log", "check_pressure_margin",
                 "lookup_sop", "write_inspection_report"):
        assert f"mcp__workbench__{tool}" in raw, f"{tool} missing from trajectory"
        order.append(raw.index(f"mcp__workbench__{tool}"))
    assert order == sorted(order), "tool calls out of order in trajectory"
