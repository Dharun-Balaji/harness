"""Sandboxed pressure-vessel safety calculation.

Concrete rule (not a generic calculator): ``pressure_vessel_margin`` checks
an OCR-derived pressure reading against the rated maximum for the vessel
covered by ``sop-pressure-vessel-repair`` (demo threshold
``MAX_SAFE_PRESSURE_BAR = 10.0`` standing in for the SOP's rated value).
It reports pass/fail, the computed margin in bar, and — on failure — a
specific reason with the numbers, so Phase 4's recovery demo can explain
*why* a reading was rejected instead of just seeing ``False``.

Sandboxing — precisely what is and isn't enforced (read this before
claiming the child is "sandboxed"):

* REAL: the calculation runs in a separate OS process (``sys.executable
  -c WORKER_SOURCE``), never in the caller's interpreter, so a child crash
  cannot take down the orchestrator.
* REAL: wall-clock kill via ``subprocess.run(timeout=...)`` (default 10 s).
* REAL: on POSIX, ``preexec_fn`` applies ``RLIMIT_CPU`` (5 s) and
  ``RLIMIT_AS`` (256 MiB) to the child, so runaway compute/memory dies by
  the kernel even if the parent is slow to reap. On non-POSIX platforms
  the timeout alone applies (documented limitation).
* REAL: the child inherits a stripped environment (``PATH`` only) and the
  worker snippet imports only ``json``/``sys`` — modules with no socket or
  filesystem-writing capability — so the child has no network *capability*
  by construction. The payload travels over stdin, the result over stdout.
* LIMITATION (stated honestly): this is not a network namespace, seccomp
  filter, or container. Full OS-level network/filesystem isolation would
  need root or a container runtime, unavailable in this environment. The
  guarantee here is narrower and checkable: a fixed, auditable,
  import-free snippet + process boundary + CPU/memory/time caps.

Every failure mode maps to a structured :class:`CalculationResult` with
``error`` set — ``TimeoutExpired``, spawn ``OSError``, non-zero exit, and
unparseable worker output are all caught; the caller never sees a bare
exception from the child path.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass

#: Demo rated maximum for the vessel in sop-pressure-vessel-repair (bar).
MAX_SAFE_PRESSURE_BAR = 10.0

RULE_PRESSURE_VESSEL_MARGIN = "pressure_vessel_margin"

DEFAULT_TIMEOUT_S = 10.0
CHILD_CPU_TIME_S = 5
CHILD_ADDRESS_SPACE_BYTES = 256 * 1024 * 1024

#: Fixed worker snippet. Deliberately imports only json/sys: no socket, no
#: subprocess, no file IO — network/file capability absent by construction.
WORKER_SOURCE = (
    "import json, sys\n"
    "def main():\n"
    "    try:\n"
    f"        max_safe = {MAX_SAFE_PRESSURE_BAR!r}\n"
    "        payload = json.loads(sys.stdin.read())\n"
    "        rule = payload.get('rule')\n"
    "        reading = payload.get('reading')\n"
    f"        if rule != {RULE_PRESSURE_VESSEL_MARGIN!r}:\n"
    "            return {'error': f'unknown rule: {rule!r}'}\n"
    "        if not isinstance(reading, dict):\n"
    "            return {'error': 'reading must be an object'}\n"
    "        equip = reading.get('equipment_id', '?')\n"
    "        p = reading.get('pressure_bar')\n"
    "        if isinstance(p, bool) or not isinstance(p, (int, float)):\n"
    "            return {'error': 'reading.missing-or-invalid: pressure_bar must be a number', 'equipment_id': equip}\n"
    "        p = float(p)\n"
    "        if p < 0:\n"
    "            return {'passed': False, 'margin_bar': None, 'equipment_id': equip,\n"
    "                    'reason': f'non-physical negative pressure reading {p} bar for {equip}'}\n"
    "        margin = round(max_safe - p, 4)\n"
    "        if p > max_safe:\n"
    "            return {'passed': False, 'margin_bar': margin, 'equipment_id': equip,\n"
    "                    'reason': f'pressure {p} bar exceeds maximum safe {max_safe} bar for {equip} (over by {round(p - max_safe, 4)} bar)'}\n"
    "        return {'passed': True, 'margin_bar': margin, 'equipment_id': equip,\n"
    "                'reason': f'pressure {p} bar within safe range for {equip}; margin {margin} bar'}\n"
    "    except Exception as exc:\n"
    "        return {'error': f'worker-failed: {type(exc).__name__}: {exc}'}\n"
    "print(json.dumps(main()))\n"
)


@dataclass(frozen=True)
class CalculationResult:
    """Outcome of a sandboxed calculation.

    ``passed`` is the rule verdict (False also covers check-failures with a
    specific ``reason``). ``error`` is set only when the calculation itself
    could not run to a verdict (timeout, spawn failure, worker crash,
    malformed input, unknown rule) — never a bare exception.
    """

    rule: str
    equipment_id: str | None
    passed: bool
    margin_bar: float | None
    reason: str | None
    error: str | None


def _limit_child_resources() -> None:  # pragma: no cover - runs in child
    """preexec_fn: cap child CPU time and address space (POSIX only)."""
    import resource

    resource.setrlimit(resource.RLIMIT_CPU,
                       (CHILD_CPU_TIME_S, CHILD_CPU_TIME_S))
    resource.setrlimit(resource.RLIMIT_AS,
                       (CHILD_ADDRESS_SPACE_BYTES, CHILD_ADDRESS_SPACE_BYTES))


def run_calculation(
    reading: dict,
    rule: str,
    *,
    timeout: float = DEFAULT_TIMEOUT_S,
) -> CalculationResult:
    """Run named ``rule`` over structured ``reading`` in a child process."""
    if not isinstance(reading, dict):
        raise TypeError("reading must be a dict of structured values")
    if not isinstance(rule, str) or not rule:
        raise TypeError("rule must be a non-empty string")

    payload = json.dumps({"rule": rule, "reading": reading})
    child_env = {"PATH": "/usr/bin:/bin"}
    preexec = _limit_child_resources if os.name == "posix" else None
    try:
        proc = subprocess.run(
            [sys.executable, "-c", WORKER_SOURCE],
            input=payload,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=child_env,
            preexec_fn=preexec,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return CalculationResult(rule=rule, equipment_id=None, passed=False,
                                 margin_bar=None, reason=None,
                                 error=f"timeout: child killed after {timeout}s")
    except OSError as exc:
        return CalculationResult(rule=rule, equipment_id=None, passed=False,
                                 margin_bar=None, reason=None,
                                 error=f"spawn-failed: {exc}")
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip().splitlines()
        tail = tail[-1] if tail else "no stderr"
        return CalculationResult(rule=rule, equipment_id=None, passed=False,
                                 margin_bar=None, reason=None,
                                 error=f"worker exited {proc.returncode}: {tail}")
    try:
        data = json.loads(proc.stdout)
    except (json.JSONDecodeError, TypeError) as exc:
        return CalculationResult(rule=rule, equipment_id=None, passed=False,
                                 margin_bar=None, reason=None,
                                 error=f"bad-worker-output: {exc}")
    if not isinstance(data, dict):
        return CalculationResult(rule=rule, equipment_id=None, passed=False,
                                 margin_bar=None, reason=None,
                                 error="bad-worker-output: top-level JSON is not an object")
    if data.get("error"):
        return CalculationResult(rule=str(rule),
                                 equipment_id=data.get("equipment_id"),
                                 passed=False, margin_bar=None, reason=None,
                                 error=str(data["error"]))
    return CalculationResult(rule=str(rule),
                             equipment_id=data.get("equipment_id"),
                             passed=bool(data.get("passed")),
                             margin_bar=data.get("margin_bar"),
                             reason=data.get("reason"),
                             error=None)
