"""Real tests for the sandboxed calculation tool.

Pass/fail/malformed cases spawn an actual child process. The timeout and
crash cases simulate a hung/dead child by monkeypatching subprocess.run /
CompletedProcess — deterministic, and honest about it: what they prove is
that the parent maps child failure to a structured CalculationResult
instead of letting an exception escape to the caller.
"""

from __future__ import annotations

import subprocess

import pytest

from tools.calculate import (
    RULE_PRESSURE_VESSEL_MARGIN,
    run_calculation,
)


def reading(pressure_bar):
    return {"equipment_id": "PUMP-214", "pressure_bar": pressure_bar}


def test_pass_with_margin():
    r = run_calculation(reading(7.2), RULE_PRESSURE_VESSEL_MARGIN)
    assert r.error is None
    assert r.passed is True
    assert r.margin_bar == pytest.approx(2.8)
    assert "within safe range" in (r.reason or "")
    assert r.equipment_id == "PUMP-214"


def test_fail_out_of_range_reports_specific_reason():
    """Phase 4's recovery demo input: must fail WITH numbers, not bare False."""
    r = run_calculation(reading(12.5), RULE_PRESSURE_VESSEL_MARGIN)
    assert r.error is None
    assert r.passed is False
    assert r.margin_bar == pytest.approx(-2.5)
    assert r.reason is not None
    assert "exceeds" in r.reason
    assert "12.5" in r.reason and "10.0" in r.reason


def test_boundary_at_maximum_passes():
    r = run_calculation(reading(10.0), RULE_PRESSURE_VESSEL_MARGIN)
    assert r.error is None and r.passed is True and r.margin_bar == pytest.approx(0.0)


def test_malformed_input_returns_structured_error():
    r = run_calculation({"equipment_id": "PUMP-214"},
                        RULE_PRESSURE_VESSEL_MARGIN)
    assert r.passed is False
    assert r.error is not None and "pressure_bar" in r.error


def test_unknown_rule_returns_structured_error():
    r = run_calculation(reading(7.2), "not-a-rule")
    assert r.passed is False
    assert r.error is not None and "unknown rule" in r.error


def test_rejects_bad_argument_types():
    with pytest.raises(TypeError):
        run_calculation("7.2 bar", RULE_PRESSURE_VESSEL_MARGIN)
    with pytest.raises(TypeError):
        run_calculation(reading(7.2), "")


def test_hung_child_maps_to_timeout_error(monkeypatch):
    """Simulated hung child: TimeoutExpired must become error, not raise."""

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs.get("timeout"))

    monkeypatch.setattr(subprocess, "run", fake_run)
    r = run_calculation(reading(7.2), RULE_PRESSURE_VESSEL_MARGIN, timeout=1.0)
    assert r.passed is False
    assert r.error is not None and "timeout" in r.error


def test_crashed_child_maps_to_exit_error(monkeypatch):
    """Simulated dead child (non-zero exit) must become error, not raise."""

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args=args[0], returncode=137,
                                           stdout="", stderr="Killed")

    monkeypatch.setattr(subprocess, "run", fake_run)
    r = run_calculation(reading(7.2), RULE_PRESSURE_VESSEL_MARGIN)
    assert r.passed is False
    assert r.error is not None and "137" in r.error
