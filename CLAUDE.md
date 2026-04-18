# Project Instructions for AI Agents

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


## Development Workflow

Every non-trivial task follows this phased workflow using the
superpowers skill system. **If there is even a 1% chance a skill
applies, invoke it before proceeding.**

### Phase 1: Design

Invoke `/brainstorming` before any creative work — new features,
components, UI changes, or architectural decisions.

- Explore project context and ask clarifying questions
- Propose 2–3 approaches with tradeoffs
- Present design for user approval
- **No implementation until design is approved**

### Phase 2: Planning

Invoke `/writing-plans` after design approval.

- Create a detailed implementation plan with exact file paths
- Document dependencies between tasks
- Offer execution model: subagent-driven or inline

### Phase 3: Implementation

**Test-driven.** Write a failing test first, then make it pass,
then refactor. No production code without a failing test.

| Skill | When |
|-------|------|
| `/test-driven-development` | **Every** feature or bugfix — RED → GREEN → REFACTOR |
| `/systematic-debugging` | When encountering any bug or test failure |
| `/subagent-driven-development` | Multi-task parallel execution (optional) |

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

### Phase 4: Quality

| Skill | When |
|-------|------|
| `/verification-before-completion` | Before claiming work is done — run tests, show evidence |
| `/requesting-code-review` | After completing tasks — dispatch review agent on diff |

Before opening any PR, you MUST run `/requesting-code-review` (or
`/review`). Fix all findings before creating the PR. No exceptions.

### Phase 5: Completion

Invoke `/finishing-a-development-branch` when all tasks pass.

- Verify tests pass
- Push branch + open PR (or merge locally for trivial changes)
- Clean up worktree

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

### Other rules

- **App Router** (not Pages Router) — see `frontend/AGENTS.md`
- **Dark theme** with orange accent (`#FF8400`), fonts: JetBrains
  Mono + Geist
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
2. Agent runs /brainstorming → /writing-plans (non-trivial work)
3. Agent implements with /test-driven-development
4. Agent runs /verification-before-completion
5. Agent runs /requesting-code-review on the diff
6. Agent opens PR referencing the GH Issue (Closes #N)
7. Human reviews + merges PR → GH Issue auto-closes
```


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

### Branch workflow

1. Assign yourself on the GitHub Issue
2. `git switch main && git pull --rebase github main`
3. `git switch -c <type>/gh-<N>-<slug>`
4. Commit often; reference issue in commit body
5. **Pre-PR gate** (mandatory before push):
   ```bash
   poetry run ruff check .
   poetry run pytest -m "not slow"
   ```
6. `git push -u github HEAD`
7. `gh pr create --base main --head <branch>` with issue link + test plan
8. **Do NOT self-merge.** Session ends at "PR opened, GH Issue linked."

### Overnight sessions

When working unattended: pick independent issues first, create
parallel branches off `main`. Sequential chains allowed (max 3 deep).
Every PR must pass CI. Leave a handoff comment listing all PRs with
dependency chain: `Stack: #41 ← #42 ← #43 (merge in order).`


## Session Completion

**Work is NOT complete until `git push` succeeds.**

1. File GH Issues for remaining work
2. Run quality gates (tests, linters)
3. Close finished GH Issues
4. **PUSH TO REMOTE:**
   ```bash
   git pull --rebase
   git push
   git status  # MUST show "up to date with origin"
   ```
5. Clean up stashes, prune remote branches
6. Verify all changes committed AND pushed
7. Provide handoff context for next session

**NEVER** stop before pushing. **NEVER** say "ready to push when you
are" — YOU must push. If push fails, resolve and retry.


## Build & Test

Language: **Python 3.11–3.13**, managed with **Poetry 2.x**.

```bash
# Local development (hot reload)
poetry install && poetry shell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

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
| `http://localhost:8000` | REST API |
| `http://localhost:8000/docs` | Swagger UI |
| `http://localhost:8000/redoc` | ReDoc |
| `http://localhost:8000/openapi.json` | OpenAPI schema |
| `http://localhost:8000/mcp` | MCP (Streamable HTTP) |


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
