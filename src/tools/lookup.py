"""Authorization-gated SOP document lookup.

The gate comes first, structurally: :func:`lookup_document` calls Phase 2's
``authorize()`` and returns early on denial, so the ``open()`` call is
textually *below* the check and unreachable without an ALLOW. The file is
never read-then-filtered.

Existence-leak decision (deliberate): denial is INDISTINGUISHABLE from
"does not exist". Both yield ``DocumentResult(found=False, text=None)``
with no ``authorized`` flag exposed — if denial said "forbidden" while a
missing ID said "not found", a junior subject could enumerate which
restricted SOPs exist by probing IDs. Callers who legitimately need the
distinction (auditors, admins) query the policy database directly, not
this tool. (Timing side-channels between the two paths are out of MVP
scope and documented as such.)

Defense in depth on the filename: ``resource_id`` must match
``[A-Za-z0-9][A-Za-z0-9_-]*`` or it is treated as not-found before any
path is built, so traversal strings can never escape the SOP directory —
and unknown IDs fail the ``authorize()`` check first in any case.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from authorize.gate import authorize

SOP_DIR_ENV_VAR = "WORKBENCH_SOP_DIR"
DEFAULT_SOP_DIR = os.path.join("docs", "sops")

_RESOURCE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*\Z")


@dataclass(frozen=True)
class DocumentResult:
    """Lookup outcome. ``found=False`` covers denied AND missing alike."""

    resource_id: str
    found: bool
    text: str | None


def get_sop_dir() -> str:
    """Resolve the SOP directory per call (env var wins) — never cached."""
    return os.environ.get(SOP_DIR_ENV_VAR, DEFAULT_SOP_DIR)


def _not_found(resource_id: str) -> DocumentResult:
    return DocumentResult(resource_id=resource_id, found=False, text=None)


def lookup_document(subject: str, resource_id: str, context: dict) -> DocumentResult:
    """Return the SOP text iff ``subject`` is authorized to see it.

    Check-first, read-only-if-allowed: anything below the ``authorize()``
    early-return runs solely on the ALLOW path.
    """
    if not isinstance(resource_id, str) or not _RESOURCE_RE.match(resource_id):
        return _not_found(resource_id if isinstance(resource_id, str) else "?")
    if not isinstance(context, dict):
        raise TypeError("context must be a dict")
    # GATE: no disk access happens before or during this call.
    if not authorize(subject, "read", resource_id, context):
        return _not_found(resource_id)
    # ALLOW path only: the file is opened here and nowhere else.
    path = os.path.join(get_sop_dir(), resource_id + ".txt")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return DocumentResult(resource_id=resource_id, found=True,
                                  text=fh.read())
    except OSError:
        # Authorized but unreadable/missing on disk: same shape, no leak
        # beyond what authorization already permits.
        return _not_found(resource_id)
