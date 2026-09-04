"""Minimal CLI so `python -m workbench` and the `workbench` entry point do
something real and testable from Phase 0 onward."""

from __future__ import annotations

import argparse
import sys

from workbench import __version__


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="workbench",
        description="Sovereign Industrial Agent Workbench (Phase 0 scaffold)",
    )
    p.add_argument(
        "--version",
        action="store_true",
        help="Print the workbench version and exit.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.version:
        print(__version__)
        return 0
    print("workbench scaffold OK — use --version for version, --help for usage.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
