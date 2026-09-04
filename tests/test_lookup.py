"""Tests for the gated SOP lookup.

The central claim — an unauthorized read never touches disk — is proven
two ways: structurally (the only open() sits below the authorize()
early-return) and empirically, by spying on builtins.open and asserting
zero calls on the denied path while asserting exactly one on the allowed
path (the positive control proves the spy was positioned to see reads).
"""

from __future__ import annotations

import os
import sqlite3
from unittest import mock

import pytest

from authorize.gate import init_schema
from authorize.seed import seed as seed_demo_db
from tools.lookup import DocumentResult, lookup_document

SOP_TEXTS = {
    "sop-shop-safety": "SHOP-SAFETY-CONTENT junior may read",
    "sop-welding-procedure": "WELDING-CONTENT junior may read",
    "sop-pressure-vessel-repair": "RESTRICTED-CONTENT seniors only",
}

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHIPPED_SOP_DIR = os.path.join(REPO_ROOT, "docs", "sops")


@pytest.fixture()
def gated(tmp_path, monkeypatch):
    """Isolated auth DB + SOP dir wired through the env vars."""
    db_path = str(tmp_path / "auth.db")
    sop_dir = str(tmp_path / "sops")
    os.makedirs(sop_dir)
    monkeypatch.setenv("WORKBENCH_AUTH_DB", db_path)
    monkeypatch.setenv("WORKBENCH_SOP_DIR", sop_dir)
    init_schema(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            "INSERT INTO subjects VALUES (?, ?)",
            [("junior-inspector", 1), ("senior-inspector", 3)],
        )
        conn.executemany(
            "INSERT INTO resources VALUES (?, ?)",
            [
                ("sop-shop-safety", 0),
                ("sop-welding-procedure", 1),
                ("sop-pressure-vessel-repair", 3),
            ],
        )
    for name, text in SOP_TEXTS.items():
        with open(os.path.join(sop_dir, name + ".txt"), "w") as fh:
            fh.write(text)
    return sop_dir


def test_authorized_returns_exact_content(gated):
    r = lookup_document("senior-inspector", "sop-pressure-vessel-repair", {})
    assert r == DocumentResult(
        resource_id="sop-pressure-vessel-repair", found=True,
        text=SOP_TEXTS["sop-pressure-vessel-repair"])


def test_denied_indistinguishable_from_missing(gated):
    """Denied and nonexistent yield the identical shape: no existence leak."""
    denied = lookup_document("junior-inspector",
                             "sop-pressure-vessel-repair", {})
    missing = lookup_document("junior-inspector", "sop-does-not-exist", {})
    assert denied.found is False and denied.text is None
    assert (denied.found, denied.text) == (missing.found, missing.text)


def test_unauthorized_never_opens_file(gated):
    """Spy on open(): zero calls when denied, one when allowed."""
    with mock.patch("builtins.open", wraps=open) as spy:
        r = lookup_document("junior-inspector",
                            "sop-pressure-vessel-repair", {})
        assert r.found is False
        assert spy.call_count == 0, \
            f"denied path opened a file: {spy.call_args_list}"


def test_authorized_opens_file_exactly_once(gated):
    """Positive control: the spy above would have seen a read if it happened."""
    with mock.patch("builtins.open", wraps=open) as spy:
        r = lookup_document("senior-inspector",
                            "sop-pressure-vessel-repair", {})
        assert r.found is True
        assert spy.call_count == 1


def test_unknown_subject_gets_not_found(gated):
    r = lookup_document("ghost", "sop-shop-safety", {})
    assert r.found is False and r.text is None


def test_path_traversal_treated_as_not_found(gated):
    with mock.patch("builtins.open", wraps=open) as spy:
        for evil in ("../secret", "../../etc/passwd", "sop-shop-safety.txt"):
            r = lookup_document("senior-inspector", evil, {})
            assert r.found is False, evil
        assert spy.call_count == 0


def test_shipped_docs_end_to_end(tmp_path, monkeypatch):
    """Seeded demo DB + committed docs/sops integrate: senior reads, junior can't."""
    db_path = str(tmp_path / "demo.db")
    monkeypatch.setenv("WORKBENCH_AUTH_DB", db_path)
    monkeypatch.setenv("WORKBENCH_SOP_DIR", SHIPPED_SOP_DIR)
    seed_demo_db(db_path)
    senior = lookup_document("senior-inspector",
                             "sop-pressure-vessel-repair", {})
    assert senior.found is True and "10.0 bar" in (senior.text or "")
    junior = lookup_document("junior-inspector",
                             "sop-pressure-vessel-repair", {})
    assert junior.found is False and junior.text is None
