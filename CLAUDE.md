# Project Instructions for AI Agents

## What this project is

**da3Dalus** is an aircraft design toolchain with a Python backend and
a React frontend.

**Backend** (`app/`) — FastAPI service:
- Generates parametric aircraft CAD (wings, fuselages, complete assemblies)
  using **CadQuery**.
- Runs aerodynamic analysis — vortex lattice method, stability, operating
  point sweeps — using **Aerosandbox** with a vendored **AVL** binary.
- Persists projects, aeroplanes, wings, and analyses via **SQLAlchemy** +
  **Alembic** migrations.
- Exposes everything over a REST API (v2 current, v1 legacy) and a
  **Model Context Protocol (MCP)** server for AI-agent integration
  (via `FastMCP`).

**Frontend** (`frontend/`) — Next.js 16 App Router + React 19:
- Interactive workbench for aircraft design (wing editor, component
  tree, analysis dashboards).
- 3D CAD viewer via **three-cad-viewer** (Three.js-based).
- Aerodynamic charts via **Plotly** (`plotly.js-gl3d-dist-min`).
- Data fetching with **SWR**, styling with **Tailwind CSS**.
- Dark theme with orange accent (`#FF8400`), fonts: JetBrains Mono +
  Geist.

## Codebase Exploration
NEVER use the Explore agent. Always launch  @"code-base-explorer (agent)". It is faster and more precise than grep-based search. 

## AVL Questions

For ANY question about AVL (Athena Vortex Lattice) — geometry files,
input format, running simulations, interpreting output, Oswald factor,
induced drag, box wings, Trefftz Plane, spacing, control surfaces,
trim, or eigenmodes — **invoke `/avl-advisor`**. It has an indexed
knowledge base over the official AVL User Primer and the Budziak thesis.

## Using Superpowers

Call '/using-superpowers' at start to get a clue about the past steps,
current state and the steps to proceed with.

## Development Workflow — Supercycle

**The primary development workflow is the Supercycle** — project-local
skills (`.claude/skills/supercycle-*/`) that orchestrate the full
lifecycle from issue to merged PR. Each skill self-documents its
usage; invoke `/supercycle-status` for an overview.

Entry points:
- **`/supercycle-ticket`** — Idea → refined GH Issue (no code)
- **`/supercycle-work #N`** — Full cycle: brainstorm → implement → review → merge
- **`/supercycle-bug`** — Bug report → fast-track TDD fix → merge
- **`/supercycle-implement #N`** — Issue is clear, skip brainstorming
- **`/supercycle-review`, `/supercycle-fix`, `/supercycle-merge`** — PR lifecycle

### Iron Laws

1. **No production code without a failing test first**
2. **No completion claims without fresh verification evidence**
3. **No fixes without root cause investigation**
4. **Fix the code, not the tests** — if a test fails, the test found
   a bug. Fix the production code. NEVER weaken assertions, delete
   tests, add `@skip`, or rewrite step definitions to bypass the UI.
   A green suite from weakened tests is worthless.
5. **No bug fix without a GH ticket** — `/supercycle-bug` must
   create a GitHub Issue (report ticket number to user) after root
   cause analysis and before any code changes.

### Test coverage target: >80%

Every feature, bugfix, and refactor must include tests. Check
coverage with `poetry run pytest --cov=app` (backend) or the
equivalent frontend command.

| Layer | Framework | Location | Command |
|-------|-----------|----------|---------|
| Backend unit | pytest | `app/tests/test_*.py` | `poetry run pytest` |
| Backend integration | pytest | `app/tests/test_*_integration.py` | `poetry run pytest -m "not slow"` |
| Backend slow/CAD | pytest | `app/tests/test_*_integration.py` | `poetry run pytest -m slow` |
| Frontend unit | vitest | `frontend/__tests__/` | `cd frontend && npm run test:unit` |
| Frontend deps | dependency-cruiser | `frontend/.dependency-cruiser.cjs` | `cd frontend && npm run deps:check` |
| Frontend E2E | playwright-bdd | `frontend/e2e/features/*.feature` | `cd frontend && npm run test:e2e` |
| cad_designer | pytest | `cad_designer/tests/test_*.py` | `poetry run pytest cad_designer/tests/` |



## Issue Tracking — GitHub Issues

GitHub Issues are the **single source of truth** for all ticket
management: features, bugs, epics, and technical tasks.

- **Feature requests:** `.github/ISSUE_TEMPLATE/feature.md`
- **Bug reports:** `.github/ISSUE_TEMPLATE/bug.md`
- **Technical tasks:** `.github/ISSUE_TEMPLATE/task.md`
- Always use templates — they ensure consistent structure
- The agent MAY create GitHub Issues for discovered **bugs** only;
  feature ideas need user confirmation via `/supercycle-ticket`
- PRs reference the issue: `Closes #N`
- Epics are GH Issues labeled `epic` with **native sub-issues**

### GitHub Issue Relationships

When creating epics or related tickets, **always add structural
relationships** via the GitHub API:

- **Sub-issues:** Use the `addSubIssue` GraphQL mutation to link
  child tickets to their epic. Every sub-ticket must have exactly
  one parent epic.
- **Dependencies:** Add a `## Dependencies` or `## Relationships`
  section to each ticket body with explicit `Depends on #N` /
  `Blocks #N` references. Also add relationship comments when
  cross-ticket dependencies exist.
- **Labels:** Epics get the `epic` label. Sub-tickets inherit the
  parent's domain (e.g. `enhancement`, `bug`).

```bash
# Add sub-issue to an epic
gh api graphql -f query='mutation {
  addSubIssue(input: {
    issueId: "<EPIC_NODE_ID>"
    subIssueId: "<TICKET_NODE_ID>"
  }) { subIssue { number title } }
}'

# Get a ticket's node ID
gh api graphql -f query='{ repository(owner:"szymansk", name:"da3Dalus") {
  issue(number: 123) { id }
}}' --jq '.data.repository.issue.id'
```

### End-to-end workflow

```
1. GitHub Issue created (by human or agent)
2. /supercycle-work #N        ← brainstorm + implement + PR
   OR /supercycle-implement #N  ← if issue is already clear
3. /supercycle-review <PR>    ← task completeness + code review
4. /supercycle-fix <PR>       ← fix findings (if any)
5. /supercycle-merge <PR>     ← CI check + merge
6. GH Issue auto-closes via "Closes #N" in PR
```

For multiple issues: the supercycle automatically analyses file
overlaps and dispatches parallel worktree agents per batch.


## Branch Strategy

Substantial work goes through a **branch + PR**. Trivial changes
ship directly on `main`. Single human maintainer; rules tuned for
that constellation.

### What requires a branch + PR

- Modifies `app/services/`, `app/api/`, `app/models/`, `app/core/`,
  `app/schemas/`, `app/converters/`, or `cad_designer/`
- Changes the database schema (`alembic/versions/*`)
- Adds/changes > ~50 net lines of production code
- Changes `pyproject.toml` runtime deps or pytest config
- Changes the public REST surface, MCP tools, or serialisation
- Introduces a new third-party dependency
- Corresponds to a GitHub Issue of type `feature` or `bug`

### What may land directly on `main`

Docs-only (≤100 lines), tests-only (≤100 lines), lint/format
auto-fixes, chore files (≤50 lines), comments/typos, reverts,
emergency CI unblock, or this CLAUDE.md itself.

### Branch naming

`<type>/gh-<N>-<short-slug>` — e.g. `feat/gh-101-construction-plans`

Types: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`

The supercycle agents create branches automatically following this
convention. For manual work, use the same pattern.


## Session Completion

**Work is NOT complete until `git push` succeeds.**
`/supercycle-merge` handles CI checks, rebase, and push. For manual
work: `git push` before saying "done". If push fails, resolve and retry.
**NEVER** say "ready to push when you are" — YOU must push.


## Git

- Remote is named `github` (not `origin`): `git push github <branch>`
- SonarQube project key: `szymansk_da3Dalus` (see `sonar-project.properties`)


## Build & Test

Language: **Python 3.11–3.12**, managed with **Poetry 2.x**.

```bash
# Local development (hot reload)
poetry install && poetry shell
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Tests
poetry run pytest                    # all fast tests
poetry run pytest -m slow            # CAD/aero tests
cd frontend && npm run test:unit     # frontend unit
cd frontend && npm run test:e2e      # frontend E2E

# Lint
poetry run ruff check .
poetry run ruff format .

# Docker
docker compose build && docker compose up -d  # port 8086
```

API runs on `http://localhost:8001` — Swagger at `/docs`, MCP at `/mcp`.


## Architecture

Layered FastAPI application. Request flow: **endpoint → service →
model / schema / converter**. All endpoints are under `v2`.
Details in `.claude/rules/python-conventions.md`.


## Non-obvious Conventions

- **`cad_designer/` — existing code is read-only, new Creators are
  allowed.** Never modify topology classes (`Airfoil`, `WingSegment`,
  `Spare`, `TrailingEdgeDevice`, `Servo`, `WingConfiguration`, etc.)
  or the `GeneralJSONEncoder/Decoder`. Validation and constraints
  are enforced **above** this layer — in Pydantic schemas
  (`app/schemas/`) and frontend UX.
  **New Creators** (subclasses of `AbstractShapeCreator`) may be
  added. Use `cad_designer/airplane/creator/_creator_template.py`
  as the starting point.
- **Units: mm in WingConfig, meters in DB/ASB.** The WingConfig
  schemas and topology classes use **millimetres**. The database and
  Aerosandbox integration use **metres**. Conversion happens in the
  converters via `scale=0.001` (mm→m) and `scale=1000.0` (m→mm).
  **Exception:** `wing_xsec_spares` stores all 6 dimensional fields
  in **mm** (gh-402): width, height, length, start, spare_origin.
  `spare_vector` is a dimensionless unit direction vector (no unit).
  The service layer (`_convert_spare_to_meters`) converts to metres
  for API responses. Always be explicit about which unit context
  you're in.
- **Transaction management** is handled by the `get_db()` dependency
  in `app/db/session.py` — it commits on success and rollbacks on
  exception. Services must not call `db.begin()`.


