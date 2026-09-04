"""Re-export the gate's public API."""

from authorize.gate import (
    authorize,
    get_db_path,
    init_schema,
    list_authorized_resources,
)

__all__ = [
    "authorize",
    "get_db_path",
    "init_schema",
    "list_authorized_resources",
]
