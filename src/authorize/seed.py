"""Seed script for the demo authorization database.

Kept separate from the gate module on purpose: ``gate.py`` implements the
decision procedure and must stay free of demo data, while everything here
is sample content for the eventual end-to-end demo (senior vs junior
inspector over open and restricted SOPs). Run:

    python -m authorize.seed [path/to/auth.db]

Defaults to ``data/auth.db`` (or ``$WORKBENCH_AUTH_DB``). The ``.db`` file
is gitignored — each developer/demo regenerates it locally.
"""

from __future__ import annotations

import sqlite3
import sys

from authorize.gate import get_db_path, init_schema

# (subject_id, clearance_level). Levels: 0 = public, 1 = shop floor,
# 3 = restricted back-office.
DEMO_SUBJECTS = [
    ("junior-inspector", 1),
    ("senior-inspector", 3),
]

# (resource_id, required_clearance).
DEMO_RESOURCES = [
    ("sop-shop-safety", 0),  # open to everyone on site
    ("sop-welding-procedure", 1),  # open to inspectors and up
    ("sop-pressure-vessel-repair", 3),  # restricted: senior inspectors only
]


def seed(db_path: str | None = None) -> str:
    path = init_schema(db_path or get_db_path())
    with sqlite3.connect(path) as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO subjects (subject_id, clearance_level)"
            " VALUES (?, ?)",
            DEMO_SUBJECTS,
        )
        conn.executemany(
            "INSERT OR REPLACE INTO resources (resource_id, required_clearance)"
            " VALUES (?, ?)",
            DEMO_RESOURCES,
        )
    return path


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    path = seed(args[0] if args else None)
    print(f"seeded {path}: {len(DEMO_SUBJECTS)} subjects,"
          f" {len(DEMO_RESOURCES)} resources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
