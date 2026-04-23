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
- 3D CAD viewer via **Three.js** (`@react-three/fiber` + `drei`).
- Aerodynamic charts via **Plotly** (`plotly.js-gl3d-dist-min`).
- Data fetching with **SWR**, styling with **Tailwind CSS**.
- Dark theme with orange accent (`#FF8400`), fonts: JetBrains Mono +
  Geist.

## Using Superpowers

Call '/using-superpowers' at start to get a clue about the past steps,
current state and the steps to proceed with.

## Development Workflow — Supercycle

**The primary development workflow is the Supercycle** — a set of
slash commands that orchestrate the full lifecycle from issue to
merged PR. Use these commands as the default entry point for all
non-trivial work.

### Supercycle Commands (preferred)

```
/supercycle:status               ← Project health dashboard — issues, SonarQube, recommendations
/supercycle:init                 ← Check & install all required tools and dependencies
/supercycle:work #187          ← Full cycle: brainstorm → implement → review → merge
/supercycle:bug <error log>    ← Bug intake: investigate → ticket → TDD fix → merge
/supercycle:implement #188,#190  ← Skip brainstorming, parallel implementation
/supercycle:review 200, 201      ← Dispatch code review agents on open PRs
/supercycle:fix 201              ← Fix review findings on PR branches
/supercycle:merge 200, 201       ← CI check + sequential merge with rebase
```

**Flow:**
```
/supercycle:work (or :implement)
  ├─ Brainstorming with user (work only)
  ├─ GH Issue creation/refinement
  ├─ Parallelization analysis (file-overlap matrix)
  ├─ Worktree agents (parallel implementation)
  │
  ├─ /supercycle:review
  │    ├─ Issue task completeness check
  │    │    ├─ ✅ Done in PR → check off
  │    │    ├─ 🔧 Agent-fixable → /supercycle:fix
  │    │    └─ 🧑 Human Only → assign to user + comment
  │    └─ Code review agents (code-reviewer + conditional)
  │
  ├─ /supercycle:fix (if findings)
  │
  └─ /supercycle:merge
       ├─ CI + SonarQube quality gate analysis
       └─ Sequential merge with rebase conflict resolution

/supercycle:bug <error log or #N>
  ├─ Root cause investigation (/systematic-debugging)
  ├─ GH Issue creation
  ├─ TDD fix (/test-driven-development)
  │    ├─ RED: failing test that reproduces bug
  │    ├─ Fix root cause
  │    └─ GREEN: verify (/verification-before-completion)
  ├─ Code review
  └─ CI check + merge
```

**When to use which entry point:**
- **`/supercycle:work`** — New feature, needs discussion with user
- **`/supercycle:bug`** — Bug report (error log or ticket) — fast-track to fix
- **`/supercycle:implement`** — Issue is clear, skip brainstorming
- **`/supercycle:review`** — PRs exist, need automated review
- **`/supercycle:fix`** — Review found issues to address
- **`/supercycle:merge`** — PRs approved, ready to merge

### Underlying Skills (used within the supercycle)

The supercycle commands orchestrate these skills internally.
You may also invoke them directly for granular control:

| Phase | Skill | When |
|-------|-------|------|
| Design | `/brainstorming` | Creative work — features, UI, architecture |
| Planning | `/writing-plans` | Multi-step tasks after design approval |
| Implementation | `/test-driven-development` | **Every** feature or bugfix — RED → GREEN → REFACTOR |
| Implementation | `/systematic-debugging` | Any bug or test failure |
| Implementation | `/subagent-driven-development` | Multi-task parallel execution |
| Quality | `/verification-before-completion` | Before claiming work is done |
| Quality | `/requesting-code-review` | Dispatch review agent on diff |
| Completion | `/finishing-a-development-branch` | All tasks pass, ready to merge |

**Backend (Python):**

| Skill | When |
|-------|------|
| `/python-testing-patterns` | pytest fixtures, mocking, parametrize, test strategies |
| `/pytest-coverage` | Measuring + improving coverage toward 70–80% target |
| `/security-review` | Security analysis (OWASP, auth, injection) |

**Frontend (React / Next.js):**

| Skill | When |
|-------|------|
| `/vercel-react-best-practices` | Performance, data fetching, bundle size |
| `/vercel-composition-patterns` | Component API design, compound components |
| `/nextjs-app-router-patterns` | Server Components, streaming, App Router |
| `/webapp-testing` | Component + integration tests |
| `/playwright-best-practices` | E2E tests, Page Object Model, flaky tests |
| `/web-design-guidelines` | UI review, accessibility, UX compliance |

### Iron Laws

1. **No production code without a failing test first**
2. **No completion claims without fresh verification evidence**
3. **No fixes without root cause investigation**
4. **Fix the code, not the tests** — if a test fails, the test found
   a bug. Fix the production code. NEVER weaken assertions, delete
   tests, add `@skip`, or rewrite step definitions to bypass the UI.
   A green suite from weakened tests is worthless.

### Test coverage target: 70–80%

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


## Frontend Design Rules

### Reuse before creating

Before building a new component, **search the existing frontend**
for patterns that match. This project has battle-tested components:

- `TreeCard` + `SimpleTreeRow` — collapsible tree panels with DnD
- `AirfoilSelector` — searchable dropdown (reuse for any picker)
- `Field` — labeled number/text input with suffix
- `GroupAddMenu` — contextual add-action popover
- Collapsible sections (`ChevronDown`/`ChevronRight` toggle)
- Modal dialogs (`fixed inset-0 z-50` backdrop + card)
- SWR hooks (`useWing`, `useComponents`, `useComponentTypes`, etc.)

Check `frontend/components/workbench/` and `frontend/hooks/` first.
Only create new components when no existing pattern fits.

### Click-dummy for large UI changes

For new screens, major layout changes, or complex interactions:
build a **click-dummy** (functional prototype with hardcoded data)
and review it with the user before implementing the real logic.
Small additions (new form fields, extra buttons) that follow
existing patterns don't need a click-dummy.

### Adding Analysis Types

Each analysis type is a tab in the Analysis page
(`frontend/app/workbench/analysis/`) with its own:

1. **Tab entry** in `AnalysisViewerPanel.tsx` TABS array
2. **Config section** in `AnalysisConfigPanel.tsx` (keyed by
   `activeTab` prop)
3. **Hook** in `frontend/hooks/` for the backend endpoint
4. **Plotly charts** for result visualization

Pattern: Tab selection → "Configure & Run" opens tab-specific
modal → user sets parameters → Run → results displayed as Plotly
charts. Future analysis types (e.g. stability/trim with operating
point) follow the same pattern.

All analysis charts use **Plotly** (dynamic import via
`import("plotly.js-gl3d-dist-min")`). Dark theme via layout
props (`paper_bgcolor`, `plot_bgcolor`, `font.color`).

### Other rules

- **App Router** (not Pages Router) — see `frontend/AGENTS.md`
- All API calls go through the backend (no direct CORS calls)


## Issue Tracking — GitHub Issues

GitHub Issues are the **single source of truth** for all ticket
management: features, bugs, epics, and technical tasks.

- **Feature requests:** `.github/ISSUE_TEMPLATE/feature.md`
- **Bug reports:** `.github/ISSUE_TEMPLATE/bug.md`
- **Technical tasks:** `.github/ISSUE_TEMPLATE/task.md`
- Always use templates — they ensure consistent structure
- The agent MAY create GitHub Issues for discovered improvements
- PRs reference the issue: `Closes #N`
- Epics are GH Issues with sub-ticket links in comments

### End-to-end workflow

```
1. GitHub Issue created (by human or agent)
2. /supercycle:work #N        ← brainstorm + implement + PR
   OR /supercycle:implement #N  ← if issue is already clear
3. /supercycle:review <PR>    ← task completeness + code review
4. /supercycle:fix <PR>       ← fix findings (if any)
5. /supercycle:merge <PR>     ← CI check + merge
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
`/supercycle:merge` handles CI checks, rebase, and push. For manual
work: `git push` before saying "done". If push fails, resolve and retry.
**NEVER** say "ready to push when you are" — YOU must push.


## Build & Test

Language: **Python 3.11–3.13**, managed with **Poetry 2.x**.

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

**Runtime endpoints:**

| URL | What |
|-----|------|
| `http://localhost:8001` | REST API |
| `http://localhost:8001/docs` | Swagger UI |
| `http://localhost:8001/redoc` | ReDoc |
| `http://localhost:8001/openapi.json` | OpenAPI schema |
| `http://localhost:8001/mcp` | MCP (Streamable HTTP) |


## Architecture

Layered FastAPI application. Request flow: **endpoint → service →
model / schema / converter**.

```
app/
├── main.py                  # FastAPI entrypoint + router wiring
├── mcp_server.py            # FastMCP server (same host/port)
├── api/v2/endpoints/        # Current API, grouped by domain
├── services/                # Business logic, CAD orchestration
├── models/                  # SQLAlchemy ORM models
├── schemas/                 # Pydantic request/response DTOs
├── converters/              # schema ⇄ model ⇄ CAD transforms
├── core/                    # Config, logging, exceptions
├── db/                      # SQLAlchemy session + engine
└── tests/                   # pytest test modules

alembic/                     # DB migrations
cad_designer/                # CadQuery primitives, plugins, decorators
components/                  # Airfoils, servos, templates (data)
```

- `v2` is current; `v1` is legacy. New endpoints → `app/api/v2/endpoints/`
- MCP via FastMCP 3.x on the same host/port as REST


## Conventions & Patterns

- **`cad_designer/` — existing code is read-only, new Creators are
  allowed.** Never modify topology classes (`Airfoil`, `WingSegment`,
  `Spare`, `TrailingEdgeDevice`, `Servo`, `WingConfiguration`, etc.)
  or the `GeneralJSONEncoder/Decoder`. Validation and constraints
  are enforced **above** this layer — in Pydantic schemas
  (`app/schemas/`) and frontend UX.
  **New Creators** (subclasses of `AbstractShapeCreator`) may be
  added. Use `cad_designer/airplane/creator/_creator_template.py`
  as the starting point — it documents the constructor pattern,
  `shapes_of_interest_keys`, `_create_shape()` contract, logging,
  and output key conventions.
- **Units: mm in WingConfig, meters in DB/ASB.** The WingConfig
  schemas and topology classes use **millimetres**. The database and
  Aerosandbox integration use **metres**. Conversion happens in the
  converters via `scale=0.001` (mm→m) and `scale=1000.0` (m→mm).
  Always be explicit about which unit context you're in.
- **Endpoints stay thin.** Validate → delegate to service → return
  Pydantic response. No business logic in endpoints.
- **Pydantic at every boundary.** Never pass raw `dict`.
- **SQLAlchemy models in `app/models/`.** Always add an Alembic
  migration when changing a model.
- **Reuse before reinventing.** Check `app/converters/`,
  `app/services/`, `cad_designer/decorators/`, `cad_designer/cq_plugins/`.
- **CPU-bound CAD in services**, not endpoints.
- **Platform guard.** On `linux/aarch64`, `cadquery` and `aerosandbox`
  are excluded. Code that imports them must tolerate `ImportError`.
- **Secrets in `.env`**, never in git. Document in `.env.example`.


<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Beads — Local Work Distribution (Optional)

Beads (`bd`) is available as an **optional local work queue** during
sessions. Use it to break a GH Issue into parallel sub-tasks, track
claims, and manage dependencies. **GitHub Issues remain the primary
tracker.**

```bash
bd ready              # Find available local work
bd close <id>         # Complete work
bd remember "insight" # Persist knowledge across sessions
```
<!-- END BEADS INTEGRATION -->
