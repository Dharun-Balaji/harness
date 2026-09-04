"""MCP bridge: the four workbench tools as a dsh-consumable MCP server.

dsh has no Python-function tool API — its documented bridge for external
tools is ``@deepseek-ai/dsh-mcp-client`` ("connects to MCP servers and
registers their tools on ctx.tools"). So this module exposes the Phase 3
tools over MCP stdio; a one-entry patch (``dsh/workbench.patch.yml``)
mounts them into dsh as ``mcp__workbench__ocr_inspection_log`` and
siblings. DB/SOP locations flow through the existing ``WORKBENCH_*`` env
vars, inherited by the underlying modules. Every tool returns a JSON
object and never raises: failures come back as ``{"error": ...}`` payloads.

Run: ``PYTHONPATH=src .venv/bin/python -m dsh_bridge.mcp_server``
"""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from authorize.gate import get_db_path
from tools.calculate import RULE_PRESSURE_VESSEL_MARGIN, run_calculation
from tools.lookup import get_sop_dir, lookup_document
from tools.ocr import extract_log_text_with_confidence
from tools.report import generate_report

mcp = MCPServer("workbench")


def _err(message: str) -> dict[str, Any]:
    return {"error": message}


@mcp.tool()
def ocr_inspection_log(image_path: str) -> dict[str, Any]:
    """OCR a handwritten inspection-log photo; returns text + confidence."""
    try:
        r = extract_log_text_with_confidence(image_path)
        return {"text": r.text, "mean_confidence": r.mean_confidence,
                "low_confidence": r.low_confidence}
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        return _err(f"{type(exc).__name__}: {exc}")


@mcp.tool()
def check_pressure_margin(equipment_id: str, pressure_bar: float) -> dict[str, Any]:
    """Sandboxed pressure-vessel margin check for one reading."""
    try:
        r = run_calculation({"equipment_id": equipment_id,
                             "pressure_bar": pressure_bar},
                            RULE_PRESSURE_VESSEL_MARGIN)
        return {"passed": r.passed, "margin_bar": r.margin_bar,
                "reason": r.reason, "error": r.error,
                "equipment_id": r.equipment_id}
    except TypeError as exc:
        return _err(f"TypeError: {exc}")


@mcp.tool()
def lookup_sop(subject: str, resource_id: str) -> dict[str, Any]:
    """Gated SOP lookup; denied and missing both return found=false."""
    try:
        r = lookup_document(subject, resource_id, {})
        return {"resource_id": r.resource_id, "found": r.found, "text": r.text}
    except TypeError as exc:
        return _err(f"TypeError: {exc}")


@mcp.tool()
def write_inspection_report(
    equipment_id: str,
    subject: str,
    timestamp: str,
    ocr: dict[str, Any],
    calculation: dict[str, Any],
    sop_requested: str | None,
    sop: dict[str, Any] | None,
    output_path: str,
) -> dict[str, Any]:
    """Render the inspection .docx report; returns its path."""
    try:
        path = generate_report({
            "equipment_id": equipment_id, "subject": subject,
            "timestamp": timestamp, "ocr": ocr, "calculation": calculation,
            "sop_requested": sop_requested, "sop": sop,
        }, output_path)
        return {"report_path": str(path)}
    except (TypeError, ValueError) as exc:
        return _err(f"{type(exc).__name__}: {exc}")


@mcp.tool()
def bridge_info() -> dict[str, Any]:
    """Environment this bridge resolves (DB/SOP paths); for diagnostics."""
    return {"auth_db": get_db_path(), "sop_dir": get_sop_dir(),
            "rule": RULE_PRESSURE_VESSEL_MARGIN}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
