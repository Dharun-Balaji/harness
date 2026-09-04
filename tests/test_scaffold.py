"""Phase 0 scaffold tests — only assert what Phase 0 actually provides."""

from __future__ import annotations

import subprocess
import sys

import workbench
from workbench.cli import main


def test_version_exposed():
    assert workbench.__version__ == "0.0.1"


def test_cli_version_flag(capsys):
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == "0.0.1"


def test_cli_default_ok(capsys):
    assert main([]) == 0
    assert "scaffold OK" in capsys.readouterr().out


def test_module_entrypoint():
    r = subprocess.run(
        [sys.executable, "-m", "workbench", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    assert r.stdout.strip() == "0.0.1"
