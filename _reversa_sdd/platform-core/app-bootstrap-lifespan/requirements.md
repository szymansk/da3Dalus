# platform-core / app-bootstrap-lifespan

> Use-case specification. Parent module: [`../requirements.md`](../requirements.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.

## Overview

Everything that happens between `import app.main` and the first served request:
logging setup, capability probing, conditional router imports, MCP app
construction, `create_app()`, and the six-step combined lifespan with its
guaranteed teardown. 🟢

Two properties are unusual and deliberate: the **API surface changes shape by
platform** (ADR 0017), and **nothing in startup is allowed to fail the process**
except the wiring that background jobs depend on. 🟢

## Responsibilities

- Configure logging at import. 🟢
- Probe `cadquery` / `aerosandbox` once and conditionally import five routers. 🟢
- Register SQLAlchemy event listeners via side-effect imports. 🟢
- Compose the app: routers in a load-bearing order, CORS, `tmp/`, three
  mounts, custom Swagger. 🟢
- Run the six lifespan steps, nest the MCP lifespan, and guarantee teardown. 🟢

## Business Rules

- **BR-PC1 — `versioning` is included before `aeroplane`** so
  `/aeroplanes/compare` matches ahead of `/aeroplanes/{aeroplane_id}`
  (gh-914). 🟢
- **BR-PC2 — All 230 routes sit at the application root.** 🟢 `openvsp_import`
  loses its `/api/v2` prefix, the one outlier among 230 route decorators — the
  inconsistency is resolved by aligning the outlier, not by prefixing the
  other 229 (Q-CC-6). Must land before `Q-CC-11`'s generated TypeScript client.
- **BR-PC3 — `os.makedirs("tmp", exist_ok=True)` precedes the `/static`
  mount.** 🟢 A git worktree without `tmp/` would otherwise fail at startup.
- **BR-PC4 — CORS is `allow_origins=["*"]` with `allow_credentials=True`**,
  carrying the comment *"copied from other python backends to resolve the cors
  origin problem"*. 🟢 🔴
- **BR-PC5 — `docs_url=None` plus a custom `/docs`** serving Swagger with
  `/assets/swagger-favicon.svg`, and the Swagger OAuth2 redirect route. 🟢
- **BR-PC6 — Two modules are imported only for their side effects**:
  `app.models.avl_geometry_events` and `app.models.stability_events` register
  SQLAlchemy event listeners (`# noqa: F401`). 🟢
- **BR-81 / BR-PC7 / ADR 0017 — Capabilities are probed once, before
  `create_app` exists**, and each heavy router import is individually guarded by
  `try/except ImportError` + a warning. On `linux/aarch64` five routers are
  absent, the service still starts and `/health` still answers. 🟢
- **BR-PC9 — Six lifespan steps, in order.** 🟢
  seed component types → seed mission presets → register invalidation handlers →
  `bind_loop` → `set_trim_function` → `set_recompute_function`.
- **BR-PC10 — A seeder failure only logs a WARNING** — *"never block startup on
  this"*. 🟢
- **BR-PC11 — The recompute wrapper offloads to a thread**, because ~200
  CPU-bound ASB calls per recompute would block every other request. 🟢
  `_recompute_sync` owns its own session and commits/rolls back itself.
- **BR-PC12 — Teardown is in a `finally`**: `await job_tracker.shutdown()`, then
  `cad_service.shutdown_executor()` and `shutdown_opg_executor()`, so
  `ProcessPoolExecutor` workers never outlive the server **or a test run**. 🟢
- **BR-PC13 — The MCP lifespan is nested** inside the combined one. 🟢
- **BR-PC32 — The MCP ASGI app is built before the `FastAPI(...)` call.** 🟢
  `create_mcp_http_app(path="/")` is `create_app()`'s first statement, and
  importing `app.mcp_server` already constructed the FastMCP server.
- **BR-PC46 — Startup logs a configuration summary; `GET /ready` reports schema
  agreement (Q-PC-2).** 🟢 Not a load-balancer readiness gate — there is none,
  per Q-CC-1/Q-CC-8 — but the answer to the recurring, documented stumbling
  block of a process left on the wrong Alembic schema after a
  migration-bearing merge (`alembic upgrade head` is manual; the local SQLite
  database is not auto-synced). The startup summary logs registered routers,
  detected capabilities (`cad_available`/`aerosandbox_available`), database
  URL and the Alembic revision. `/ready` reports the running revision against
  head plus the capability flags; `/health` keeps its always-200 semantics
  unchanged.
- **BR-PC47 — Single-worker operation is asserted at startup, not merely
  assumed (Q-CC-8/ADR 0024).** 🟢 The application **refuses to start** when
  configured with more than one worker: failing loudly at boot is preferable to
  the silent, data-dependent breakage a second worker causes today (each of
  `JobTracker`, the CAD task registry and the MCP `ASSET_REGISTRY` is
  per-process with no persistence or cross-worker sharing). This does **not**
  conflict with ADR 0005 — its `ProcessPoolExecutor` is *intra*-process and
  unaffected — and it does **not** resolve `Q-CG-2` (the CAD export race
  *inside* the pool of a single process), which remains a real defect owned by
  `cad-generation`.
- **BR-PC48 — An exposure guard replaces an application-level auth boundary
  (Q-CC-1/ADR 0024).** 🟢 An app-side *bind* guard is impossible when uvicorn
  is launched from the CLI — it opens the socket before the app loads — so the
  guard lives at the launch surfaces: the documented dev command drops
  `--host 0.0.0.0` (uvicorn's own default is already `127.0.0.1`); the Docker
  compose file publishes to `127.0.0.1` only while `--host 0.0.0.0` stays
  mandatory *inside* the container; and a startup log line states the
  effective reachability, warning on a non-loopback bind without an explicit
  `ALLOW_PUBLIC_BIND` opt-in. This composes with BR-PC46's startup summary —
  both are one log line each, near-zero marginal cost.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Configure logging at module import | Must | `setup_logging()` before anything logs |
| RF-02 | Probe each capability once per process | Must | `lru_cache(maxsize=1)` |
| RF-03 | Import heavy routers individually, guarded | Must | One failure does not affect the others |
| RF-04 | Register the two SQLAlchemy listener modules | Must | Listeners active before the first request |
| RF-05 | Build the MCP ASGI app first | Must | It exists before `FastAPI(...)` |
| RF-06 | Include routers in the legacy order | Must | `/aeroplanes/compare` resolves correctly |
| RF-07 | Register capability-gated routers only when available | Must | Absent otherwise |
| RF-08 | Apply the CORS middleware | Must | Preflight succeeds from any origin |
| RF-09 | Create `tmp/` then mount `/static`, `/assets`, `/mcp` | Must | All three resolve |
| RF-10 | Serve a custom `/docs` with the project favicon | Should | Page renders |
| RF-11 | Run the six lifespan steps in order | Must | Job tracker fully wired |
| RF-12 | Log and continue when a seeder fails | Must | Startup completes |
| RF-13 | Offload recompute to a thread | Must | The event loop is not blocked |
| RF-14 | Nest the MCP lifespan | Must | MCP startup/shutdown inside the app's |
| RF-15 | Tear down the job tracker and both executors | Must | No worker outlives the process |
| RF-16 | Provide `run_app` using `settings.UVICORN_HOST` | Could | `uvicorn.run(..., reload=True)` |
| RF-17 | Log a startup configuration summary (routers, capabilities, DB URL, Alembic revision) | Should | Q-PC-2 |
| RF-18 | Serve `GET /ready` reporting Alembic-head agreement and capability flags | Should | Q-PC-2 |
| RF-19 | Refuse to start with more than one worker | Must | Q-CC-8/ADR 0024 |
| RF-20 | Log the effective reachability at startup; warn on a non-loopback bind without `ALLOW_PUBLIC_BIND` | Must | Q-CC-1/ADR 0024 |

## Non-functional Requirements

| Type | Inferred requirement | Evidence | Confidence |
|------|----------------------|----------|-----------|
| Availability | The service starts without CadQuery/AeroSandbox | conditional imports; ADR 0017 | 🟢 |
| Availability | Startup survives a seeding failure | both `except … warning` blocks | 🟢 |
| Performance | Capability detection costs one import attempt per process | `lru_cache(maxsize=1)` | 🟢 |
| Performance | CPU-bound recompute never runs on the event loop | `asyncio.to_thread` | 🟢 |
| Cleanliness | Process-pool workers never leak across a test run | the `finally` teardown | 🟢 |
| Correctness | Route registration order is part of the contract | gh-914 | 🟢 |
| Security | Unauthenticated by design (Q-CC-1/ADR 0024), guarded at the launch surfaces; CORS remains wide open — unaddressed | `main.py:233-247`; ADR 0016/0024 | 🟢 (stance); 🟡 (CORS policy) |
| Consistency | `openvsp_import` loses its `/api/v2` prefix; all 230 routes sit at the root (Q-CC-6) | `main.py:212` | 🟢 |
| Operability | Single-worker operation is asserted at startup, not merely assumed (Q-CC-8/ADR 0024) | — (new requirement) | 🟢 |
| Startup cost | 🟡 Importing `app.main` builds the whole FastMCP server as a side effect | `main.py:73` | 🟡 |

## Acceptance Criteria

```gherkin
Feature: Import-time bootstrap

  Scenario: Logging is configured before use
    When app.main is imported
    Then the root logger level reflects LOG_LEVEL
    And matplotlib, websockets, asyncio, kaleido, choreographer and browser_proc
      are silenced to CRITICAL

  Scenario: Capabilities are probed once
    When cad_available() is called three times
    Then the underlying import attempt happened once

  Scenario: A heavy router import failure is contained
    Given the aeroanalysis module raises ImportError
    When app.main is imported
    Then a warning is logged
    And the other conditional routers are still imported

  Scenario: Event listeners are registered
    When app.main is imported
    Then the AVL-geometry and stability SQLAlchemy listeners are active

Feature: Application composition

  Scenario: The compare route is not shadowed
    When I GET /aeroplanes/compare?a=1&b=2
    Then the versioning compare handler runs

  Scenario: A CAD-less platform
    Given cad_available() is False
    When the app is created
    Then no /cad route exists
    And GET /health returns 200

  Scenario: tmp is created before mounting
    Given no tmp directory
    When the app is created
    Then tmp exists
    And GET /static/<a file placed there> is served

  Scenario: The three mounts
    Then /static, /assets and /mcp are all mounted

  Scenario: Custom docs
    When I GET /docs
    Then Swagger UI is returned referencing /assets/swagger-favicon.svg

Feature: Lifespan

  Scenario: Startup wiring
    When the app starts
    Then component types and mission presets are seeded
    And invalidation handlers are registered
    And the job tracker has a bound loop, a trim function and a recompute function

  Scenario: Idempotent seeding
    Given the 9 component types already exist
    When the app starts again
    Then no duplicate rows are created

  Scenario: A failing seeder
    Given seed_mission_presets raises
    When the app starts
    Then a WARNING is logged and startup completes

  Scenario: Recompute does not block the loop
    Given a recompute is scheduled
    When it runs
    Then it executes in a worker thread and the event loop keeps serving

  Scenario: Teardown
    When the app shuts down
    Then job_tracker.shutdown() was awaited
    And the CAD and operating-point-generator executors were shut down
    And no ProcessPoolExecutor worker process remains
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|---|---|---|
| Router order (RF-06) | Must | A wrong order silently shadows a route (gh-914) |
| Capability probing + conditional imports (RF-02/RF-03/RF-07) | Must | ADR 0017 — the service must run on `linux/aarch64` |
| `tmp/` before the static mount (RF-09) | Must | Otherwise a worktree cannot start |
| The six lifespan steps (RF-11) | Must | Without `bind_loop`, every background job is silently dropped |
| Seeder tolerance (RF-12) | Must | A dev DB built with `create_all` would otherwise block startup |
| Threaded recompute (RF-13) | Must | Otherwise ~200 ASB calls freeze the server |
| Guaranteed teardown (RF-15) | Must | Leaked process-pool workers break test runs |
| Nested MCP lifespan (RF-14) | Must | One process, one lifecycle |
| Side-effect listener imports (RF-04) | Must | Stability/AVL invalidation depends on them |
| Custom `/docs` (RF-10) | Should | Cosmetic |
| `run_app` (RF-16) | Could | Convenience wrapper |
| A startup readiness gate — summary + `/ready` (RF-17/RF-18) | Should | Q-PC-2 — decided |
| Single-worker startup assertion (RF-19) | Must | Q-CC-8/ADR 0024 — decided |
| Exposure guard + reachability log line (RF-20) | Must | Q-CC-1/ADR 0024 — decided |
| Failing fast on a seeding error | Won't | Deliberate: *"never block startup on this"* |

## Code Traceability

| File | Symbol | Coverage |
|---|---|---|
| `app/main.py:91` | `setup_logging()` at import | 🟢 |
| `…:25-72` | capability probes + five guarded router imports | 🟢 |
| `…:73` | `from app.mcp_server import create_mcp_http_app` (builds FastMCP) | 🟢 🟡 |
| `…:84-85` | the two `# noqa: F401` listener imports | 🟢 |
| `…:94-95` | `create_app`, `mcp_app` | 🟢 |
| `…:100-196` | `_combined_lifespan` | 🟢 |
| `…:198-232` | `FastAPI(...)` + router includes | 🟢 |
| `…:233-239` | CORS 🟡 | 🟢 |
| `…:241-247` | `tmp/` + three mounts | 🟢 |
| `…:249-261` | custom `/docs` + Swagger redirect | 🟢 |
| `…:342-349` | `run_app` | 🟢 |
| `app/core/platform.py` | `cad_available`, `aerosandbox_available`, `require_*` | 🟢 |
| `app/logging_config.py` | `setup_logging` | 🟢 |
| `app/services/component_type_service.py` | `seed_default_types` (gh#83) | 🟢 owned by `aeroplane-core` |
| `app/services/mission_objective_service.py` | `seed_mission_presets` (gh-546) | 🟢 owned by `mission-and-sizing` |
