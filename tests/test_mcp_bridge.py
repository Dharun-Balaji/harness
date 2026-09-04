"""MCP bridge tests — spawn the real server over stdio, speak real MCP.

Proves the dsh-facing contract without dsh itself: tool list, JSON
shapes, and the denied-lookup path, all through MCP client calls.
"""

from __future__ import annotations

import json
import os

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from authorize.seed import seed as seed_demo_db

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE_PNG = os.path.join(REPO_ROOT, "tests", "fixtures", "inspection-log.png")
SHIPPED_SOP_DIR = os.path.join(REPO_ROOT, "docs", "sops")


@pytest.fixture()
async def mcp_tools(tmp_path, monkeypatch):
    db_path = str(tmp_path / "demo.db")
    seed_demo_db(db_path)
    env = dict(os.environ)
    env["PYTHONPATH"] = os.path.join(REPO_ROOT, "src")
    env["WORKBENCH_AUTH_DB"] = db_path
    env["WORKBENCH_SOP_DIR"] = SHIPPED_SOP_DIR
    params = StdioServerParameters(
        command=os.path.join(REPO_ROOT, ".venv", "bin", "python"),
        args=["-m", "dsh_bridge.mcp_server"],
        env=env, cwd=REPO_ROOT,
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


def payload(result) -> dict:
    assert len(result.content) == 1
    return json.loads(result.content[0].text)


@pytest.mark.anyio
async def test_lists_all_four_tools(mcp_tools):
    names = sorted(t.name for t in (await mcp_tools.list_tools()).tools)
    assert names == ["bridge_info", "check_pressure_margin",
                     "lookup_sop", "ocr_inspection_log",
                     "write_inspection_report"]


@pytest.mark.anyio
async def test_ocr_and_margin_through_mcp(mcp_tools):
    ocr = payload(await mcp_tools.call_tool(
        "ocr_inspection_log", {"image_path": FIXTURE_PNG}))
    assert "PUMP-214" in ocr["text"] and ocr["low_confidence"] is False
    good = payload(await mcp_tools.call_tool(
        "check_pressure_margin",
        {"equipment_id": "PUMP-214", "pressure_bar": 7.2}))
    assert good["passed"] is True and good["error"] is None
    bad = payload(await mcp_tools.call_tool(
        "check_pressure_margin",
        {"equipment_id": "PUMP-214", "pressure_bar": 12.5}))
    assert bad["passed"] is False and "exceeds" in (bad["reason"] or "")


@pytest.mark.anyio
async def test_gated_lookup_through_mcp(mcp_tools):
    senior = payload(await mcp_tools.call_tool(
        "lookup_sop", {"subject": "senior-inspector",
                       "resource_id": "sop-pressure-vessel-repair"}))
    assert senior["found"] is True and "10.0 bar" in (senior["text"] or "")
    junior = payload(await mcp_tools.call_tool(
        "lookup_sop", {"subject": "junior-inspector",
                       "resource_id": "sop-pressure-vessel-repair"}))
    assert junior == {"resource_id": "sop-pressure-vessel-repair",
                      "found": False, "text": None}
