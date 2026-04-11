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

## Issue Workflow & Branch Strategy

**Every issue (beads or GitHub) is worked on in its own local branch.**
The default branch `main` on GitHub (and `streb` locally, tracking
`github/main`) must stay review-ready at all times. All implementation
work — code, tests, docs for a specific issue — goes through a dedicated
branch and is merged via Pull Request so the user can review the diff
before it lands on `main`.

### Branch naming

Branches are named `<type>/<issue-id>-<short-slug>` where:

- `<type>` is one of: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`
  (mirrors the conventional-commits vocabulary used in commit messages).
- `<issue-id>` is the full beads ID (`cad-modelling-service-7em`) or
  the GitHub issue number prefixed with `gh-` (`gh-42`).
- `<short-slug>` is 2–5 lowercase words separated by hyphens that hint
  at the work.

Examples:
```
fix/cad-modelling-service-7em-wing-roundtrip-dihedral-sign
feat/gh-18-operating-points-pagination
refactor/cad-modelling-service-0es-cad-service-registry
docs/gh-27-rest-api-naming-guide
```

### Mandatory workflow per issue

1. **Claim the issue first.** `bd update <id> --claim` (for beads) or
   assign yourself on GitHub. Do not start coding before the issue is
   in the `in_progress` state — that is the record that work has begun.
2. **Start from an up-to-date default branch.**
   ```bash
   git switch streb
   git pull --rebase github main
   ```
3. **Create the branch.**
   ```bash
   git switch -c <type>/<issue-id>-<short-slug>
   ```
4. **Commit often on the branch.** Each commit must reference the
   issue ID in the message body or footer (e.g.
   `Relates to cad-modelling-service-7em.`) so the history is
   navigable later.
5. **Push the branch** to the `github` remote explicitly:
   ```bash
   git push -u github HEAD
   ```
   Never push directly to `main`. If you accidentally made the
   change on `streb` / `main`, reset and move the commits to a
   feature branch before pushing.
6. **Open a Pull Request** via `gh pr create --base main --head
   <branch>` with a body that links the issue and summarises the
   change plus the test plan. The PR title follows the same
   conventional-commit format as the branch type.
7. **Close or update the beads issue** only after the PR is open.
   Do not mark the issue closed until the PR is merged — until
   then the work is still in review.
8. **Do NOT merge the PR yourself.** Merging is the user's checkpoint.
   Your session ends at "branch pushed, PR opened, issue updated".

### Exceptions (direct-to-`main` is allowed only for)

- Session-housekeeping that does NOT correspond to an issue:
  `bd dolt push`, pushing a beads data update, trivial `.gitignore`
  tweaks that unblock tooling.
- Reverting a broken commit on `main` (revert commit only; the fix
  that follows still goes through a branch + PR).
- Emergency CI unblock (lock file repair, missing dev dep) where a PR
  roundtrip would block everyone — document after the fact in a
  `chore:` commit.

All other changes — including "just a one-line fix" and
"just a test addition" — go through the branch + PR flow.

### Interaction with Session Completion

The Session Completion protocol above still applies, but the push
target is **the feature branch**, not `main`. The final state of a
session working on an issue is:

```
branch      <feat|fix|refactor>/<id>-<slug> pushed to github
PR          #N opened, linked to <id>
beads       <id> in_progress with notes pointing at the PR URL
```

`git status` should show `up to date with github/<branch>`, not
with `github/main`.

<!-- END ISSUE WORKFLOW -->

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

# Lint & format (ruff; config in pyproject.toml)
poetry run ruff check .
poetry run ruff format .    # optional: Black-style formatter

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
