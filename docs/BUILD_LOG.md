# Build Log

## Phase 0 — Scaffold

Set up the repo skeleton on `main` (git init, gitignore for venv/SQLite/weights/secrets, `src/authorize/` + `src/tools/` + `tests/` + `docs/` layout, README with design points and dsh attribution, MIT LICENSE, third-party notices); no application code yet.

## Phase 1 — dsh pinned and verified

Pinned `@deepseek-ai/dsh` at exactly `0.1.2-rc.1` in `package.json` (no `^`/`~`). Chosen via `npm view @deepseek-ai/dsh versions --json`: newest non-alpha release candidate published at the time (2026-09-03; skipped the `0.1.2-alpha.*` line as less stable). Exact pin because dsh is a developer preview with breaking changes expected between releases. Verified for real: `npm install` resolves to `0.1.2-rc.1`, and a standalone `dsh --profile web --no-open --port 3080` run printed `dsh web: http://127.0.0.1:3080/?token=...` with an unauthenticated request correctly answered 401 by the token fence; the server was then stopped and the port confirmed closed. Intended integration point for later phases: Python spawns this exact `dsh` binary as the out-of-process plugin host for tools under `src/tools/`.

## Phase 2 — authorize() gate

Built `src/authorize/gate.py`: `authorize(subject, action, resource, context) -> bool` plus the pre-filter `list_authorized_resources(subject, context) -> list[str]`, both backed by SQLite (`$WORKBENCH_AUTH_DB`, default `data/auth.db`, gitignored). Schema is two tables — `subjects(subject_id, clearance_level)` and `resources(resource_id, required_clearance)` — with the rule `clearance_level >= required_clearance` instead of a separate policy table, because at MVP scope a policy table adds joins without expressiveness and one auditable comparison covers every rule we need (documented in the module docstring; fail-closed on unknown subjects/resources). Pre-filter design: the clearance comparison runs *inside a single SQL query*, so denied rows never leave the database and can never enter a model's context — retrieval (Phase 3) will fetch only returned IDs. No caching anywhere: fresh connection per call, DB path re-resolved per call; the mid-session test below proves a clearance UPDATE is visible to the very next call. Seed data lives in separate `src/authorize/seed.py` (junior-inspector:1, senior-inspector:3; two open SOPs + one restricted SOP), never in the gate module. `src/tools/` untouched.

Actual pytest output (`.venv/bin/python -m pytest tests/test_authorize.py -v`):

```text
tests/test_authorize.py::test_allow_clearance_above_and_at_required PASSED [ 12%]
tests/test_authorize.py::test_deny_clearance_below_required PASSED       [ 25%]
tests/test_authorize.py::test_deny_unknown_subject_or_resource PASSED    [ 37%]
tests/test_authorize.py::test_clearance_change_visible_on_next_call PASSED [ 50%]
tests/test_authorize.py::test_list_authorized_resources_partial_clearance PASSED [ 62%]
tests/test_authorize.py::test_list_authorized_resources_full_clearance PASSED [ 75%]
tests/test_authorize.py::test_list_authorized_resources_unknown_subject PASSED [ 87%]
tests/test_authorize.py::test_rejects_bad_argument_types PASSED          [100%]

8 passed in 0.06s
```

Seeded-demo spot check also passed: junior sees exactly `['sop-shop-safety', 'sop-welding-procedure']` (restricted SOP absent), senior sees all three, junior→restricted is `False`, senior→restricted is `True`.

## Phase 3a — OCR tool

Built `src/tools/ocr.py` around the real stack: system `tesseract 5.5.3` (preinstalled, verified with `tesseract --version`) plus `pytesseract` + `pillow` installed into the project `.venv` and recorded in `pyproject.toml`. `extract_log_text(image_path) -> str` returns raw OCR text (grayscale + 2x upscale preprocessing); `extract_log_text_with_confidence()` additionally returns mean word-confidence and an explicit `low_confidence` flag (mean < 40, empty text, or no words), so Phase 4 can retry/escalate instead of reasoning over misread numbers. Missing files raise `FileNotFoundError`, unreadable files raise `ValueError`, a missing binary raises `RuntimeError` with the install command. Fixture is a real committed PNG (`tests/fixtures/inspection-log.png`, 1200x850): no handwriting font existed on the system, so the log (PUMP-214, 7.2 bar, 2026-09-03, DB) was rendered in Liberation Sans with irregular sizing, ±1.6° rotation, margin/spacing jitter, and paper noise.

Actual raw OCR output on the fixture (mean confidence 89.9, low_confidence=False):

```text
INSPECTION LOG

Equipment: PUMP-214

Pressure: 7.2 bar
Date: 2026-09-03

Inspector: DB
```

Actual pytest output (`.venv/bin/python -m pytest tests/test_ocr.py -v`):

```text
tests/test_ocr.py::test_fixture_exists PASSED                            [ 16%]
tests/test_ocr.py::test_extract_log_text_recovers_key_readings PASSED    [ 33%]
tests/test_ocr.py::test_structured_result_reports_high_confidence_on_fixture PASSED [ 50%]
tests/test_ocr.py::test_blank_image_flags_low_confidence PASSED          [ 66%]
tests/test_ocr.py::test_missing_file_raises PASSED                       [ 83%]
tests/test_ocr.py::test_unreadable_file_raises PASSED                    [100%]

6 passed in 9.19s
```

Full suite at commit time: 18 passed.
