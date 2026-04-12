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

## Testing Philosophy — TDD

**Failing tests are correct. Fix the code, not the tests.**

When a test fails, the test is doing its job — it found a bug or
a missing implementation. The correct response is:

1. **Read the test** to understand the expected behavior
2. **Fix the production code** to make the test pass
3. **NEVER weaken assertions** to make a failing test green
4. **NEVER delete or skip tests** because the code doesn't match yet

Anti-patterns that are **strictly forbidden:**
- Changing `expect(count).toBe(12)` to `toBe(13)` because the code returns 13
- Replacing `"all items have no spars"` with `"at least 1 item has spars"` because spars exist
- Adding `@skip` tags to tests that the code can't pass yet
- Rewriting step definitions to call the API directly instead of going through the UI

If a test describes the correct behavior and the code doesn't
implement it yet, the test MUST stay red until the code is fixed.
A green test suite achieved by weakening tests is worthless.

## Test Coverage Requirement

**Target: 70–80% coverage.** Writing tests for implemented code is
mandatory, not optional. Every feature, bugfix, and refactor must
include tests.

### Skills for writing tests

Use these skills when writing tests — they contain patterns and
best practices:

| Skill | When to use |
|-------|-------------|
| `/skill tdd` | Starting any feature — write tests FIRST |
| `/skill python-testing-patterns` | Writing pytest unit/integration tests for the Python backend |
| `/skill pytest-coverage` | Measuring + improving pytest coverage toward 70–80% target |
| `/skill webapp-testing` | Frontend component + integration tests (React/Next.js) |
| `/skill playwright-best-practices` | E2E tests with Playwright (locators, assertions, patterns) |
| `/skill e2e-testing-patterns` | Structuring E2E test suites, fixtures, data management |

### Workflow for every code change

1. **Before coding:** Invoke `/skill tdd` — write failing tests first
2. **During coding:** Run tests continuously, fix code until green
3. **After coding:** Check coverage with `poetry run pytest --cov=app`
   (backend) or equivalent frontend command
4. **Before PR:** Run `/review`, then verify coverage ≥ 70%

### Test types per layer

| Layer | Framework | Location | Command |
|-------|-----------|----------|---------|
| Backend unit | pytest | `app/tests/test_*.py` | `poetry run pytest` |
| Backend integration | pytest | `app/tests/test_*_integration.py` | `poetry run pytest -m "not slow"` |
| Backend slow/CAD | pytest | `app/tests/test_*_integration.py` | `poetry run pytest -m slow` |
| Frontend E2E | playwright-bdd | `frontend/e2e/features/*.feature` | `cd frontend && npm run test:e2e` |

## Pre-PR Review Gate

Before opening any GitHub PR, you MUST run `/review` (the review
skill) on your changes. Fix all findings before creating the PR.
This is mandatory — no exceptions.

## Issue Workflow & Branch Strategy

**Substantial issue work goes through a dedicated branch and a Pull
Request so the user can review the diff before it lands on `main`.**
Trivial changes ship directly on `main` so the cycle stays fast.
Overnight/unattended agentic sessions may stack multiple branches in a
single run; the user merges them as a batch in the morning.

This project has a single human maintainer who is also the only
reviewer. The rules below are tuned for that constellation, not for a
team workflow. The goal is to maximise PR review value on work that
actually benefits from review, while keeping the small stuff and the
autonomous sessions fluid.

### What goes through a branch + PR

Branch + PR is **required** for any change that matches *one or more*
of the following:

- Modifies anything under `app/services/`, `app/api/`, `app/models/`,
  `app/core/`, `app/schemas/`, `app/converters/`, or `cad_designer/`.
- Changes the database schema (`alembic/versions/*`).
- Adds or changes more than ~50 net lines of production code
  (anything under `app/` that is not a test).
- Touches `pyproject.toml` in a way that affects runtime dependencies
  or pytest configuration.
- Changes the public REST surface, the MCP tool list, or the
  serialisation contracts.
- Introduces a new third-party dependency.
- Corresponds to a beads issue of type `feature` or `bug` at priority
  0, 1, or 2 — regardless of size.

### What may land directly on `main`

Low-risk, low-review-value changes may be committed straight to the
default branch (`streb` locally, pushed to `github:main`) without a
PR. The allowed categories:

- **Docs-only** changes (`CLAUDE.md`, `README.md`, `docs/*.adoc`,
  inline docstrings) up to ~100 net lines.
- **Tests-only** changes under `app/tests/` or `test/` that add new
  cases or adjust fixtures, up to ~100 net lines, with no production
  code modified.
- **Lint / format** auto-fixes that change no semantics
  (`ruff format`, `ruff check --fix` where the fix is purely
  stylistic).
- **Chore** changes: `.gitignore`, `.vscode/*`, `.github/workflows/*`
  up to ~50 net lines, toolchain files, beads database updates, MIT
  housekeeping.
- **Comments, typos, whitespace** — trivially.
- **Revert commits** that undo a broken change (the subsequent fix
  still goes through a branch + PR).
- **Emergency CI unblock** (poetry.lock repair, missing dev
  dependency). Document after the fact in a `chore:` commit.
- **This CLAUDE.md section itself** and any meta-rule revision.

If a change straddles categories (e.g. docs + production code), the
stricter rule wins and it takes the branch + PR path.

### Branch naming

Branches are named `<type>/<issue-id>-<short-slug>` where:

- `<type>` is one of: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`
  (mirrors the conventional-commits vocabulary used in commit messages).
- `<issue-id>` is the full beads ID (`cad-modelling-service-7em`) or
  the GitHub issue number prefixed with `gh-` (`gh-42`). Work that
  has no issue still goes under a `scratch/` prefix, e.g.
  `scratch/investigate-occt-memory`.
- `<short-slug>` is 2–5 lowercase words separated by hyphens that hint
  at the work.

Examples:
```
fix/cad-modelling-service-7em-wing-roundtrip-dihedral-sign
feat/gh-18-operating-points-pagination
refactor/cad-modelling-service-0es-cad-service-registry
docs/gh-27-rest-api-naming-guide
```

### Workflow for a branch-based change

1. **Claim the issue first.** `bd update <id> --claim` for beads or
   assign yourself on GitHub. Do not start coding before the issue is
   `in_progress` — that is the record that work has begun.
2. **Start from an up-to-date default branch.**
   ```bash
   git switch streb
   git pull --rebase github main
   ```
3. **Create the branch.**
   ```bash
   git switch -c <type>/<issue-id>-<short-slug>
   ```
4. **Commit often.** Each commit references the issue ID in the body
   or footer (e.g. `Relates to cad-modelling-service-7em.`) so the
   history is navigable later.
5. **Run the pre-PR gate locally.** This is **mandatory** before
   pushing a branch and opening a PR — the exact commands CI runs,
   in the exact order, so a PR is never opened with a red CI
   signature that the agent could have caught in seconds:
   ```bash
   poetry run ruff check .
   poetry run pytest -m "not slow"
   ```
   If either fails, fix the issue *before* committing and pushing.
   Do not rely on "the CI will tell us" — the CI tells the user,
   and the user has to wait 2 minutes, review a failing PR, and
   ask the agent to go back. This costs several minutes per round
   and is avoidable with a 20-second local check. If the change
   touches any slow test (``@pytest.mark.slow``), run that test
   specifically as well:
   ```bash
   poetry run pytest app/tests/test_<the_relevant_slow_test>.py
   ```
6. **Push the branch** to `github` explicitly:
   ```bash
   git push -u github HEAD
   ```
7. **Open a Pull Request** via
   `gh pr create --base main --head <branch>` with a body that links
   the issue, summarises the change, and includes a test plan. Title
   uses the same conventional-commits prefix as the branch type.
8. **Update the beads issue** — add a note with the PR URL. Do NOT
   mark the issue `closed` yet; closure happens when the PR is
   merged. The beads status stays `in_progress`.
9. **Do NOT self-merge.** Merging is the user's checkpoint.
   A session ends at "branch pushed, PR opened, issue updated".

### Overnight / unattended agentic sessions

When the user launches a session with "work through the queue while I
sleep", the single-branch-per-issue rule is lifted to a **linear
branch chain** so the session is not blocked on merges the user has
not yet performed. Rules:

1. **Pick independent issues first.** Use `bd ready` and prefer
   issues that do not touch the same files. Independent issues each
   get their own branch off `main` and become parallel PRs the user
   can merge in any order.
2. **Sequential chains are allowed** when issues depend on each
   other. The second issue's branch starts from the first issue's
   branch, not from `main`. The PR for the second issue is still
   opened against `main`, with the body noting
   `Depends on #<first-pr>.` The user merges them in dependency
   order. GitHub auto-rebases the second PR after the first is
   merged.
3. **Never chain more than 3 deep.** If a session would need a
   4-deep stack, stop and leave a note in the last issue explaining
   why. Deep stacks become unmanageable during morning review.
4. **Every PR must pass the fast CI job** before the session closes.
   If a PR is red, leave it `draft` and put the failure in the
   beads notes so the user can pick it up.
5. **Session handoff note.** When the overnight session ends, append
   a summary comment on the beads issue of the most recent branch
   listing every PR opened in that session with its dependency
   chain, e.g. `Stack: #41 ← #42 ← #43 (merge in order).`

### Morning review loop (for the maintainer)

The user-facing counterpart to overnight agentic work:

```bash
gh pr list --state open --search "sort:created-asc"
gh pr diff <N>                  # inspect
gh pr merge <N> --squash --delete-branch
```

A suggested one-shot "merge everything that is green and approved":

```bash
gh pr list --state open --json number,statusCheckRollup,reviewDecision \
  --jq '.[] | select(.statusCheckRollup | all(.conclusion == "SUCCESS")) | .number' \
  | xargs -I {} gh pr merge {} --squash --delete-branch
```

Optional: enable `Settings → General → Pull Requests → Automatically
delete head branches` on the GitHub repo so merged branches clean
themselves up.

### Interaction with Session Completion

The Session Completion protocol still applies, with one adjustment:
the push target depends on the change category.

- For **branch-based** work the final state is:
  ```
  branch      <feat|fix|...>/<id>-<slug> pushed to github
  PR          #N opened (or draft if CI red), linked to <id>
  beads       <id> in_progress, notes point at the PR URL
  ```
  `git status` should show `up to date with github/<branch>`.

- For **direct-to-`main`** changes the state is:
  ```
  branch      streb pushed to github:main
  beads       <id> closed (if the change was tracked)
  ```
  `git status` shows `up to date with github/main`. The legacy
  `git push github streb:main` pattern still applies here.

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
