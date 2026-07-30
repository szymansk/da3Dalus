# `app/` — FastAPI backend

Layered FastAPI service. **Read the root `CLAUDE.md` and
`.claude/rules/python-conventions.md` first** — this file only adds the
directory map and app-local gotchas.

## Layout

| Dir | What | Count |
|-----|------|-------|
| `api/v2/endpoints/` | REST endpoints (current). Thin: validate → delegate → return schema | 18 |
| `api/v1/` | **legacy** REST surface — don't add here | — |
| `services/` | business logic, external tools (CadQuery/AeroSandbox/AVL), transactions | 85 |
| `models/` | SQLAlchemy models — change ⇒ add an Alembic migration | 21 |
| `schemas/` | Pydantic request/response contracts (never pass raw `dict` across a boundary) | 49 |
| `converters/` | schema ↔ model ↔ CAD translation + unit scaling | 12 |
| `core/` | `config.py` (pydantic-settings), exceptions | 8 |
| `db/` | `session.py` — the `get_db()` dependency | 5 |
| `tests/` | pytest (`test_*.py`); `*_integration.py` are `-m slow` | 302 |

**Entry points:** `main.py` (FastAPI app + static mounts), `mcp_server.py`
(FastMCP tools at `/mcp`), `settings.py`, `logging_config.py`.

Request flow: **endpoint → service → model / schema / converter**.

## App-local gotchas

- **Transactions live in `get_db()`** (`db/session.py`) — it commits on success,
  rolls back on exception. Services must **not** call `db.begin()`.
- **Platform guards:** `cadquery` and `aerosandbox` are excluded on
  `linux/aarch64` (pyproject env markers). Import them defensively
  (`try/except ImportError`) or keep them in a module only loaded on supported
  platforms.
- **Units:** WingConfig schemas + `cad_designer` topology are **mm**; DB and
  AeroSandbox are **m**. Converters scale `0.001` (mm→m) / `1000.0` (m→mm).
  Exception: `wing_xsec_spares` dimensional fields are mm (gh-402).
- **Invalidation:** geometry edits go through `services/invalidation_service.py`
  (marks operating points DIRTY, schedules assumption recompute). Wire new
  geometry-mutating paths through it.
- **Coverage gate:** the SonarCloud `new_coverage` gate runs the CI fast tier
  **without** aero deps — aero-dependent service code needs mocked fast tests
  (stub the solver boundary) to be counted.
- **Config:** all settings go through `core/config.py`; no scattered
  `os.getenv`. New setting ⇒ field + default + `.env.example` entry.

## Commands (from repo root)

```bash
poetry run pytest                 # fast tests
poetry run pytest -m slow         # CAD/aero tests (sequential — see root CLAUDE.md)
poetry run ruff check . && poetry run ruff format .
```
