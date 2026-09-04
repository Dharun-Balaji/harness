# Sovereign Industrial Agent Workbench

Local-first workbench for defining, running, and inspecting task-oriented
agents for industrial settings (shop-floor checklists, equipment triage,
maintenance SOPs, document-grounded Q&A over local manuals).

## What this is

A Python orchestrator plus a plugin host. Python owns scheduling, state,
tool calls, and audit logging. Plugins (equipment drivers, document
parsers, domain checks) run out-of-process and are invoked by the
orchestrator over a subprocess boundary so a crashing or untrusted plugin
cannot take down a run.

Current status: Phase 0 scaffold only — repo layout, licensing, and a
`workbench` CLI that reports its version. No agent runtime yet.

## Problem it addresses

Industrial sites need agents that work offline, leave an audit trail, and
integrate with heterogeneous machines and documents without sending plant
data to a third-party cloud. Existing agent frameworks optimize for
chat demos: they assume always-online APIs, hide tool I/O, and make it
hard to pin exactly which plugin version and model produced a given
action. This workbench starts from the opposite constraints: local
execution first, explicit plugin boundary, reproducible runs.

## Technology Used

- **Python 3.10+** — orchestrator, CLI (`src/workbench/`), tests (`tests/`).
  Build backend: `setuptools` via `pyproject.toml`. Tests: `pytest`.
- **dsh (DeepSeek Harness, MIT-licensed) — plugin runtime.** dsh is a
  Node/TypeScript runtime used as the out-of-process plugin host,
  invoked by Python as a subprocess. It is **not** ported to Python and
  is **not** vendored in this repo at Phase 0. When later phases add the
  integration, Python will spawn `dsh` and speak to plugins over
  stdio/IPC. See `THIRD_PARTY_NOTICES.md` for the MIT attribution that
  travels with any MIT-licensed code.
- **Node.js 18+ / TypeScript** — required only for the dsh plugin host
  (later phases). Phase 0 does not add any Node dependencies.

## Project structure

```text
hrn/
  src/workbench/        Python package (orchestrator; Phase 0: version + CLI only)
    __init__.py         __version__
    cli.py              `workbench` entry point (--version / --help)
    __main__.py         `python -m workbench`
  tests/
    test_scaffold.py    asserts exactly what Phase 0 provides
  pyproject.toml        src layout, `workbench` script, pytest config
  THIRD_PARTY_NOTICES.md  MIT attribution for dsh
```

## Development

Prerequisites: Python 3.10+, Node 18+ (for later dsh phases), git.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]" 2>/dev/null || pip install -e .
# without installing (Phase 0 has no third-party runtime deps):
PYTHONPATH=src python3 -m workbench --version
PYTHONPATH=src python3 -m pytest -q
```

The `.gitignore` excludes venvs, Node modules, OS files, and local model
weights (`*.safetensors`, `*.gguf`, `*.bin`, `*.pt`, `models/`, …) so a
multi-GB checkpoint can never be committed by accident.

## License

Own code: MIT — see `LICENSE`. Third-party notices (dsh): see
`THIRD_PARTY_NOTICES.md`.
