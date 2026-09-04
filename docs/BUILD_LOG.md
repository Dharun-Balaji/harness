# Build Log

## Phase 0 — Scaffold

Set up the repo skeleton on `main` (git init, gitignore for venv/SQLite/weights/secrets, `src/authorize/` + `src/tools/` + `tests/` + `docs/` layout, README with design points and dsh attribution, MIT LICENSE, third-party notices); no application code yet.

## Phase 1 — dsh pinned and verified

Pinned `@deepseek-ai/dsh` at exactly `0.1.2-rc.1` in `package.json` (no `^`/`~`). Chosen via `npm view @deepseek-ai/dsh versions --json`: newest non-alpha release candidate published at the time (2026-09-03; skipped the `0.1.2-alpha.*` line as less stable). Exact pin because dsh is a developer preview with breaking changes expected between releases. Verified for real: `npm install` resolves to `0.1.2-rc.1`, and a standalone `dsh --profile web --no-open --port 3080` run printed `dsh web: http://127.0.0.1:3080/?token=...` with an unauthenticated request correctly answered 401 by the token fence; the server was then stopped and the port confirmed closed. Intended integration point for later phases: Python spawns this exact `dsh` binary as the out-of-process plugin host for tools under `src/tools/`.
