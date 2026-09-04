"""Real tests for the authorization gate — every case hits SQLite.

Each test gets a fresh, isolated database via tmp_path (pointed at by the
WORKBENCH_AUTH_DB env var), so tests never touch the developer/demo .db
and never leak state into each other.
"""

from __future__ import annotations

import os
import sqlite3

import pytest

from authorize.gate import (
    authorize,
    init_schema,
    list_authorized_resources,
)


@pytest.fixture()
def auth_db(tmp_path, monkeypatch):
    """Fresh DB with junior (1) and senior (3) inspectors and 3 SOPs."""
    db_path = str(tmp_path / "test-auth.db")
    monkeypatch.setenv("WORKBENCH_AUTH_DB", db_path)
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
    return db_path


def test_allow_clearance_above_and_at_required(auth_db):
    assert authorize("senior-inspector", "read",
                     "sop-pressure-vessel-repair", {}) is True
    # boundary: clearance == required still allows
    assert authorize("junior-inspector", "read",
                     "sop-welding-procedure", {}) is True


def test_deny_clearance_below_required(auth_db):
    assert authorize("junior-inspector", "read",
                     "sop-pressure-vessel-repair", {}) is False


def test_deny_unknown_subject_or_resource(auth_db):
    assert authorize("ghost", "read", "sop-shop-safety", {}) is False
    assert authorize("junior-inspector", "read", "sop-does-not-exist",
                     {}) is False


def test_clearance_change_visible_on_next_call(auth_db):
    """Mid-session clearance change must take effect immediately.

    Proves the gate re-reads the DB on every call and caches nothing: flip
    the junior's clearance in the DB and the very next authorize() call
    must reflect it, in both directions.
    """
    assert authorize("junior-inspector", "read",
                     "sop-welding-procedure", {}) is True
    with sqlite3.connect(auth_db) as conn:
        conn.execute("UPDATE subjects SET clearance_level = 0"
                     " WHERE subject_id = 'junior-inspector'")
    assert authorize("junior-inspector", "read",
                     "sop-welding-procedure", {}) is False
    with sqlite3.connect(auth_db) as conn:
        conn.execute("UPDATE subjects SET clearance_level = 1"
                     " WHERE subject_id = 'junior-inspector'")
    assert authorize("junior-inspector", "read",
                     "sop-welding-procedure", {}) is True


def test_list_authorized_resources_partial_clearance(auth_db):
    """A partial-clearance subject sees exactly its subset in one call."""
    visible = list_authorized_resources("junior-inspector", {})
    assert visible == ["sop-shop-safety", "sop-welding-procedure"]
    assert "sop-pressure-vessel-repair" not in visible


def test_list_authorized_resources_full_clearance(auth_db):
    visible = list_authorized_resources("senior-inspector", {})
    assert visible == ["sop-pressure-vessel-repair", "sop-shop-safety",
                       "sop-welding-procedure"]


def test_list_authorized_resources_unknown_subject(auth_db):
    assert list_authorized_resources("ghost", {}) == []


def test_rejects_bad_argument_types(auth_db):
    with pytest.raises(TypeError):
        authorize("", "read", "sop-shop-safety", {})
    with pytest.raises(TypeError):
        authorize("junior-inspector", "read", "sop-shop-safety", "ctx")
    with pytest.raises(TypeError):
        list_authorized_resources("junior-inspector", [])
