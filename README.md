# Sovereign Industrial Agent Workbench

An on-premise agentic workbench for confidential industrial work: handwritten
inspection logs, standard operating procedures (SOPs), and compliance reports
in settings where the data can't leave the building. Everything runs locally —
documents, authorization checks, tool calls, and the model — so plant-floor
knowledge never goes to a third-party cloud.

Status: Phase 0 scaffolding only. No application code yet.

## Deliberate design points

1. **Authorization gate before retrieval, not just at answer time.** The
   `authorize()` check in `src/authorize/` runs BEFORE any document reaches
   the model's context. Retrieval can only see resources the current subject
   is cleared for — an unauthorized SOP is filtered out of the candidate set,
   not merely hidden from the final answer. A model can't leak what was never
   in its context window.
2. **A working end-to-end demo scenario.** The MVP ships one concrete,
   runnable path — e.g. an inspector asking a question over local SOPs with
   mixed clearance levels — so reviewers can see the auth gate actually
   allowing and denying, not just read about it.
3. **NO self-modifying skill/learning layer, on purpose.** Production
   behavior needs to be identical every run. A workbench that rewrites its
   own tools or prompts between runs can't be audited, can't be qualified
   for compliance use, and can't be trusted on a shop floor. Learning and
   experimentation stay out of the production path by design.

## Technology Used

- **Python 3.10+** — the authorization layer (`src/authorize/`), tool
  adapters (`src/tools/`), and tests (`tests/`). Everything runs in a local
  `.venv`; see Development below.
- **dsh (DeepSeek Harness, https://github.com/deepseek-ai/deepseek-harness,
  MIT license) — the plugin runtime this workbench is built on top of.**
  To be clear: we did not write dsh. It is the upstream open-source agent
  harness ("everything is a plugin") that hosts tool plugins; we build our
  authorization gate and our industrial tools on top of it. dsh is consumed
  as a dependency / subprocess plugin host, not forked or ported. See
  `THIRD_PARTY_NOTICES.md` for the license disclosure.

## Project structure

```text
.
  src/authorize/   authorization gate (authorize() + SQLite policy store) — later phase
  src/tools/       dsh tool plugins (document/SOP adapters) — later phase
  tests/           pytest suite, including allow/deny/clearance-change auth tests
  docs/            build log and design notes
```

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m pytest -q
```

Local model weights, virtualenvs, SQLite dev databases, and secrets are all
gitignored (see `.gitignore`) so multi-GB checkpoints or credentials can
never be committed by accident.

## What this does NOT do

- **No self-modifying skills in production.** The agent never rewrites its
  own tools, prompts, or policy between runs. Deterministic, auditable,
  repeatable — that's the point.
- **No distributed-auth consistency guarantees.** Clearance checks are local
  and per-run; there is no cross-site policy replication or consensus story.
- **No multi-agent swarms.** One orchestrator, one plugin host, one audit
  trail. Coordination protocols between agents are out of scope.
- **No production-grade ReBAC.** Relationship-based access control at scale
  (graph stores, enterprise directory sync) is beyond an MVP. SQLite holding
  subjects, resources, and a clearance/policy table is enough for MVP scope,
  and we say so plainly: if you need enterprise ReBAC, this demo is not it.

## License

Our own code: MIT — see `LICENSE`. Upstream dsh licensing: see
`THIRD_PARTY_NOTICES.md`.
