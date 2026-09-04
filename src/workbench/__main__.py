"""Allow `python -m workbench` to work via the cli module."""

from workbench.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
