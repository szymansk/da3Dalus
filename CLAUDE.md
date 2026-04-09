# Project Instructions for AI Agents

This file provides instructions and context for AI coding agents working on
this project.

## What this project is

**cad-modelling-service** is the Python backend of the **da3Dalus** aircraft
design toolchain. It is a FastAPI service that:

- Generates parametric aircraft CAD (wings, fuselages, complete assemblies)
  using **CadQuery**.
- Runs aerodynamic analysis — vortex lattice method, stability, operating
  point sweeps — using **Aerosandbox** with a vendored **AVL** binary.
- Persists projects, aeroplanes, wings, and analyses via **SQLAlchemy** +
  **Alembic** migrations.
- Exposes everything over a REST API (v2 current, v1 legacy) and a
  **Model Context Protocol (MCP)** server for AI-agent integration
  (via `FastMCP`).

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->

## Build & Test

Language: **Python 3.11–3.13**, managed with **Poetry 2.x**.

```bash
# Local development (hot reload)
poetry install
poetry shell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Tests (pytest, under app/tests/)
poetry run pytest
./run_all_tests.sh          # equivalent wrapper

# Docker (production-style)
docker compose build
docker compose up -d        # service on http://localhost:8086
docker compose logs -f aero-cad-service
docker compose down

# Documentation (AsciiDoctor, via Docker)
make doc                    # output in docs/html/
```

**Runtime endpoints** (when launched via `uvicorn`):

- REST API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI schema: `http://localhost:8000/openapi.json`
- MCP (Streamable HTTP): `http://localhost:8000/mcp`

## Architecture Overview

Layered FastAPI application. Request flow: **endpoint → service → model /
schema / converter**.

```
app/
├── main.py                  # FastAPI app entrypoint + router wiring
├── mcp_server.py            # FastMCP server mounted into the same app
├── logging_config.py
├── api/
│   ├── v1/                  # Legacy API (kept for compatibility)
│   └── v2/
│       └── endpoints/       # Current API, grouped by domain
│                            # (aeroplane, wings, fuselages, cad, aeroanalysis)
├── services/                # Business logic, external tool orchestration
├── models/                  # SQLAlchemy ORM models
├── schemas/                 # Pydantic request/response DTOs
├── converters/              # Transforms between schema ⇄ model ⇄ CAD
├── core/                    # Config, logging, exceptions, security
├── db/                      # SQLAlchemy session + engine setup
└── tests/                   # pytest test modules

alembic/                     # DB migrations (versions/ holds the scripts)
cad_designer/                # CadQuery modelling primitives, plugins, decorators
components/                  # Airfoils, servos, construction templates (data, not code)
Avl/                         # Vendored AVL binary + sources (used by Aerosandbox)
docs/                        # AsciiDoctor documentation sources
```

**API versioning.** `v2` is current; `v1` is legacy and kept only for
backward compatibility. Put new endpoints in `app/api/v2/endpoints/`.

**MCP integration.** `app/mcp_server.py` uses FastMCP 3.x to expose
selected v2 endpoints as MCP tools on the same host/port as the REST API.
See `README.md` for MCP Inspector testing.

## Conventions & Patterns

- **Endpoints stay thin.** Validate input → delegate to a service →
  return a Pydantic response. No business logic in endpoints.
- **Pydantic at every boundary.** Request and response bodies are Pydantic
  models, never raw `dict`. Put them in `app/schemas/`.
- **SQLAlchemy models live in `app/models/`.** Alembic migrations in
  `alembic/versions/`. Always add a migration when you change a model.
- **Reuse before reinventing.** Check `app/converters/`, `app/services/`,
  and `cad_designer/` (including `cad_designer/decorators/` and
  `cad_designer/cq_plugins/`) before writing new transforms or CAD
  primitives.
- **CPU-bound CAD work belongs in services**, not endpoints. Endpoints
  should stay responsive.
- **Tests.** `app/tests/test_*.py`. Run with `poetry run pytest`. Pytest
  config in `pyproject.toml` already ignores `external/` and
  `docker_smoke_test.py`.
- **Platform guard.** On `linux/aarch64`, `cadquery` and `aerosandbox` are
  intentionally excluded from dependencies (see `pyproject.toml`
  environment markers). Code that imports them must tolerate being
  unavailable on that platform — either with a conditional import or by
  living in a module that is only loaded on supported platforms.
- **Secrets in `.env`, never in git.** `.env` is already gitignored.
  Document new variables in `.env.example` with placeholder values.
- **Chromium rendering.** Some visualisation flows shell out to a headless
  Chromium via `BROWSER_PATH` and require `QT_QPA_PLATFORM=offscreen`.
  Keep those requirements behind env vars, not hardcoded paths.
