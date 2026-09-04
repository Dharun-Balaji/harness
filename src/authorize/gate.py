"""SQLite-backed authorization gate — the core of the workbench.

Decision procedure (deliberately simple, and why): a subject may perform an
action on a resource iff ``subject.clearance_level >=
resource.required_clearance``. We picked this single-rule comparison over a
separate policy table because, at MVP scope, a policy table would add joins
without adding expressiveness: every rule we need today ("junior inspectors
see open SOPs, not restricted ones") is exactly a clearance comparison, and
one comparison in one place is auditable. Per the README we are explicitly
*not* building production-grade ReBAC here; when per-action overrides or
relationship rules become necessary, that is the point to add a policy
table — not before.

Fail-closed: unknown subjects and unknown resources are denied. There is no
caching anywhere in this module — every call opens a fresh SQLite
connection and re-reads the rows, so a clearance change in the DB is
visible to the very next call.

The gate is designed as a PRE-FILTER: callers must call
:func:`list_authorized_resources` before retrieval and only fetch the
returned IDs, so unauthorized documents never enter a model's context.
"""

from __future__ import annotations

import os
import sqlite3

DB_ENV_VAR = "WORKBENCH_AUTH_DB"
DEFAULT_DB_PATH = os.path.join("data", "auth.db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS subjects (
    subject_id TEXT PRIMARY KEY,
    clearance_level INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS resources (
    resource_id TEXT PRIMARY KEY,
    required_clearance INTEGER NOT NULL
);
"""


def get_db_path() -> str:
    """Resolve the SQLite file per call (env var wins) — never cached."""
    return os.environ.get(DB_ENV_VAR, DEFAULT_DB_PATH)


def init_schema(db_path: str | None = None) -> str:
    """Create the subjects/resources tables if missing. Returns the path."""
    path = db_path or get_db_path()
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA_SQL)
    return path


def _check_subject_context(subject: str, context: dict) -> None:
    if not isinstance(subject, str) or not subject:
        raise TypeError("subject must be a non-empty string")
    if not isinstance(context, dict):
        raise TypeError("context must be a dict")


def _check_args(subject: str, resource: str, context: dict) -> None:
    _check_subject_context(subject, context)
    if not isinstance(resource, str) or not resource:
        raise TypeError("resource must be a non-empty string")


def authorize(subject: str, action: str, resource: str, context: dict) -> bool:
    """Return True iff ``subject`` may perform ``action`` on ``resource``.

    ``action`` and ``context`` are accepted for API stability (later phases
    may add purpose- or time-window checks) but the current decision is the
    clearance comparison documented above. Unknown subjects or resources
    are denied. Every call re-reads the database; nothing is cached.
    """
    if not isinstance(action, str) or not action:
        raise TypeError("action must be a non-empty string")
    _check_args(subject, resource, context)
    with sqlite3.connect(get_db_path()) as conn:
        row = conn.execute(
            """
            SELECT s.clearance_level >= r.required_clearance
            FROM subjects s, resources r
            WHERE s.subject_id = ? AND r.resource_id = ?
            """,
            (subject, resource),
        ).fetchone()
    return bool(row and row[0])


def list_authorized_resources(subject: str, context: dict) -> list[str]:
    """Return the IDs of resources ``subject`` may currently see.

    This is the pre-filter: call it BEFORE retrieval and fetch only the
    returned IDs, so unauthorized rows never leave the database, let alone
    reach a model's context. A single SQL query applies the clearance
    comparison inside the database — Python never sees denied rows.
    Unknown subjects get an empty list. Re-reads the DB on every call.
    """
    _check_subject_context(subject, context)
    with sqlite3.connect(get_db_path()) as conn:
        rows = conn.execute(
            """
            SELECT r.resource_id
            FROM resources r
            WHERE r.required_clearance <= (
                SELECT s.clearance_level FROM subjects s
                WHERE s.subject_id = ?
            )
            ORDER BY r.resource_id
            """,
            (subject,),
        ).fetchall()
    return [r[0] for r in rows]
