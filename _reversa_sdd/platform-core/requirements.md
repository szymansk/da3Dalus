# platform-core

> Module-level specification. Focuses on WHAT the module does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: platform-core,
> `_reversa_sdd/data-dictionary.md` §Module: platform-core,
> `_reversa_sdd/domain.md` §2.12, `_reversa_sdd/state-machines.md` §7,
> `_reversa_sdd/architecture.md` §9–§10, `_reversa_sdd/permissions.md`,
> ADR 0009, ADR 0012, ADR 0015, ADR 0016, ADR 0017.

## Overview

`platform-core` is the cross-cutting foundation everything else stands on:
FastAPI app composition and lifespan, router wiring, CORS and static mounts,
configuration, the exception hierarchy and its HTTP translation, the SQLAlchemy
engine/session with its transaction contract, platform capability probes, the
in-process event bus and the debounced background-job tracker. 🟢

It owns no domain concept. Its guarantees are the ones every other module
assumes: *a request is one transaction*, *a service never commits*, *a heavy
dependency may be absent*, and *a NaN never becomes a 500*. 🟢

## Responsibilities

- Compose the FastAPI app: 15 unconditional routers + up to 5 capability-gated
  + 24 `aeroplane/` sub-routers ≈ **230 route decorators**. 🟢
- Run the combined lifespan: two idempotent seeders, invalidation handler
  registration, and the job tracker's loop binding and function injection. 🟢
- Probe optional heavy dependencies **once**, at import, and gate routers on
  them (ADR 0017). 🟢
- Own configuration — merging into **one** `Settings` class (Q-CC-4); today
  split across two classes with the same name. 🟢
- Own `ServiceException` and its translation into the
  `{"error": {code, message, details}}` envelope. 🟢
- Own the engine, `SessionLocal` and `get_db()` — the transaction boundary
  (ADR 0009). 🟢
- Render non-finite floats as `null` instead of crashing (ADR 0012). 🟢
- Provide the synchronous in-process `EventBus` and the debounced
  `JobTracker`. 🟢
- Serve `/health`, `/docs`, `/redoc`, `/openapi.json`, `/static`, `/assets`. 🟢

**Explicitly NOT this module's responsibility:** authentication (there is none —
ADR 0016), any domain logic, and the MCP surface (→ `mcp-server`, though this
module mounts it).

## Business Rules

> `BR-78`…`BR-84` are global ids reused verbatim from
> [`../domain.md`](../domain.md). `BR-PC*` are module-local.

### Composition

- **BR-PC1 — Router order is load-bearing.** 🟢 `versioning_v2.router` is
  included **before** `aeroplane_v2.router` so the static route
  `/aeroplanes/compare` matches ahead of `/aeroplanes/{aeroplane_id}` (gh-914).
- **BR-PC2 — All 230 routes sit at the application root.** 🟢 `openvsp_import`'s
  `/api/v2` prefix — the one outlier among 230 route decorators — is removed;
  the inconsistency is resolved by aligning the outlier, not by prefixing the
  other 229 (Q-CC-6). This must land **before** `Q-CC-11`'s generated
  TypeScript client, or the inconsistency is baked into generated code.
- **BR-PC3 — `tmp/` is created at app creation.** 🟢
  `os.makedirs("tmp", exist_ok=True)` before `app.mount("/static", …)` — which
  is why a git worktree must `mkdir -p tmp` before running.
- **BR-PC4 — CORS is fully open.** 🟢 `allow_origins=["*"]`,
  `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`, with
  the inline comment *"copied from other python backends to resolve the cors
  origin problem"*. 🔴 Wildcard origin **with** credentials is rejected by
  browsers for credentialed requests and wide open otherwise.
- **BR-PC5 — Swagger is re-served by hand.** 🟢 `docs_url=None` on the app plus
  a custom `/docs` route using `/assets/swagger-favicon.svg`;
  `redoc_url="/redoc"`, `openapi_url="/openapi.json"`.
- **BR-PC6 — Two modules are imported purely for side effects.** 🟢
  `app.models.avl_geometry_events` and `app.models.stability_events` register
  SQLAlchemy event listeners at startup (`# noqa: F401`).

### Capability probing (ADR 0017)

- **BR-81 — Heavy dependencies are optional and probed once.** 🟢
  `cad_available()` / `aerosandbox_available()` are `@lru_cache(maxsize=1)` —
  *"a broken install detected once stays broken for the life of the process"*.
- **BR-PC7 — The API surface changes shape by platform.** 🟢 On
  `linux/aarch64` (where `pyproject.toml` env markers exclude CadQuery and
  AeroSandbox) five routers are simply not registered, the service still starts
  and `/health` still answers.
  🔴 **[Reviewer] The 503 half of this rule is essentially unwired.**
  `require_cad` / `require_aerosandbox` are *defined* in `app/core/platform.py`
  (l.49, l.61) and raise `HTTPException(503)` as documented, but a
  repository-wide grep finds **zero** production call sites for `require_cad`
  and **exactly one** for `require_aerosandbox`
  (`app/api/v2/endpoints/section_aoa.py:79`,
  `dependencies=[Depends(require_aerosandbox)]`). Every other reference is in
  `app/tests/test_platform_guards.py`. So the "endpoints that *are* registered
  but need a capability answer a clean 503" contract holds for **one** route;
  everywhere else a registered endpoint that reaches a missing heavy dependency
  raises `ImportError` and surfaces as a 500. The same overstated claim appears
  in this module's `contracts.md`, `design.md`, `tasks.md`,
  `app-bootstrap-lifespan/design.md`, and in the global `architecture.md`
  §Capability probing and ADR 0017.
- **BR-PC8 — Each conditional import is individually guarded.** 🟢 Every heavy
  router import sits in its own `try/except ImportError` that logs a warning.

### Lifespan

- **BR-PC9 — Six steps before `yield`.** 🟢
  1. `seed_default_types` (gh#83) — idempotent insert of the 9 default component
     types, in its own `SessionLocal` with an explicit commit;
  2. `seed_mission_presets` (gh-546) — same shape, six mission presets, needed
     when a DB was built with `create_all` instead of Alembic;
  3. `invalidation_service.register_handlers()`;
  4. `job_tracker.bind_loop(asyncio.get_running_loop())`;
  5. `job_tracker.set_trim_function(retrim_dirty_ops)`;
  6. `job_tracker.set_recompute_function(_recompute_wrapper)`.
- **BR-PC10 — A seeder failure never blocks startup.** 🟢 Both are wrapped so a
  failure only logs a WARNING — *"never block startup on this"*.
- **BR-PC11 — Recompute runs in a thread.** 🟢 `_recompute_wrapper` wraps
  `_recompute_sync` in `asyncio.to_thread` because *"ASB calls are CPU-bound
  (~200 calls per recompute); running them directly on the event loop would
  block all other requests"*. `_recompute_sync` owns its own session and
  commits/rolls back itself.
- **BR-PC12 — Teardown is guaranteed.** 🟢 `await job_tracker.shutdown()`, then
  `cad_service.shutdown_executor()` and `shutdown_opg_executor()`, so
  `ProcessPoolExecutor` workers never outlive the server **or a test run**.
- **BR-PC13 — The MCP lifespan is nested inside.** 🟢
  `async with mcp_app.lifespan(app): yield`.

### Configuration

- **BR-PC14 — One `Settings` class, one instance (Q-CC-4).** 🟢 The two classes
  below — same name, same `.env`, disjoint fields, SCREAMING_CASE vs
  snake_case, and a genuine **double-instance bug** (`app/settings.py` exports
  a module singleton **and** a separately `lru_cache`d `get_settings()`
  returning a *different* object, so the two access paths diverge the moment
  either is mutated, notably in tests) — merge into **one class, one naming
  convention, one instance**. This is the legacy state being merged, kept here
  for migration reference:
  | | `app/core/config.py` | `app/settings.py` |
  |---|---|---|
  | Singleton | `settings` | `settings` **and** `@lru_cache get_settings()` |
  | `env_file` | `.env`, `extra="ignore"` | identical |
  | Naming | SCREAMING_CASE | snake_case |
  | Fields | `PROJECT_NAME`, `VERSION="1.0.0"`, `UVICORN_HOST`, `ARTIFACTS_BASE_DIR`, `COPILOT_*` (4) | `base_url`, `openai_api_key`, `version="0.1.0"`, `low_re_*` (13) |
  | Also exports | `REPO_ROOT`, `AIRFOILS_DIR` | `_DEFAULT_LOW_RE_GRID`, `_DEFAULT_MISSION_WEIGHTS` |
  | Consumers | `copilot_service`, `openvsp_*`, `artifact_service`, `create_wing_configuration`, `main.run_app` | `mcp_server`, `health`, `cad`, `airfoils`, `aeroanalysis`, `suitability_service`, `airfoil_low_re_service`, `background_jobs` |

  Every consumer on both sides migrates to the merged class.
- **BR-PC15 — One version source, derived from `pyproject.toml` (Q-CC-4).** 🟢
  The three coexisting strings — `core.config.VERSION = "1.0.0"` (unused),
  `settings.version = "0.1.0"` (the one `/health` reports) and
  `FastAPI(version="2.0.0")` — collapse to a single source, so `/health`, the
  OpenAPI document and a release build cannot disagree. Composes with `Q-CC-14`②
  (removing `Dockerfile`'s `COPY db/test.db` in favour of a volume mount +
  env var) and `Q-CC-4`'s fold-in of the stray `SQLALCHEMY_DATABASE_URL`.
- **BR-PC16 — `AIRFOILS_DIR` must be absolute.** 🟢
  `REPO_ROOT / "components" / "airfoils"`, with a long comment: a CWD-relative
  airfoils dir made procedurally-generated airfoils from the OpenVSP importer
  land outside the read directory, so they appeared "missing" after import.
- **BR-PC17 — A relative `ARTIFACTS_BASE_DIR` is rejected, not resolved
  (Q-PC-6).** 🟢 Calling `.resolve()` on a relative override is an *undeclared
  substitution* under ADR 0020: the operator supplies one path, the process
  silently uses a different one, and which one depends on the working
  directory (repo root, worktree, systemd unit, Docker entrypoint) — the same
  bug class `AIRFOILS_DIR` (BR-PC16) was already hardened against. The
  `field_validator(mode="after")` instead **raises** when the value is not
  absolute, naming the setting and the value received, so startup fails loudly
  rather than every later write landing somewhere unpredictable. Where a
  relative path is genuinely convenient in a developer shell, the resolution
  base is the **repository root**, never the process CWD — and that is an
  explicit opt-in, not a silent default.
- **BR-PC18 — Three settings escape both classes; all three fold into the
  merged `Settings` (Q-CC-4).** 🟢
  `SQLALCHEMY_DATABASE_URL` (`db/session.py:8`), `LOG_LEVEL`
  (`logging_config.py:7`) and `DISPLAY_CONSTRUCTION_STEP` use bare `os.getenv`,
  contradicting the documented rule *"no scattered `os.getenv`"* in
  `app/CLAUDE.md`. All three move into the merged class.
  `SQLALCHEMY_DATABASE_URL` may remain a deliberate bootstrap exception **if**
  Alembic genuinely needs it before the settings object can be constructed —
  to be verified during implementation, not assumed; the other two are not
  exceptions.

### Persistence

- **BR-78 / ADR 0009 — `get_db()` owns the transaction boundary.** 🟢
  `yield` → `commit` on success → `rollback` on exception → `close` in
  `finally`. Services call `db.flush()` / `db.add()` but **never**
  `db.commit()` / `db.begin()`. Four paths legitimately own their own session:
  the two lifespan seeders, `_recompute_sync` and
  `JobTracker._run_backfill_for_names`. 🟡 One path that should commit and does
  not: `mcp_server._call_endpoint`.
- **BR-79 — `autoflush=False`.** 🟢 Services must flush explicitly before a
  query can see their pending writes — which is why `db.flush()` appears
  throughout the version and copilot services. Also `expire_on_commit=False`,
  `autocommit=False`.
- **BR-80 — SQLite runs in WAL with a 30 s busy timeout.** 🟢
  `connect_args={"check_same_thread": False, "timeout": 30}` plus an
  `Engine.connect` listener setting `journal_mode=WAL`, `synchronous=NORMAL`,
  `busy_timeout=30000` — because the assumption recompute holds a write
  transaction open for several seconds while AeroBuildup runs.
- **BR-PC19 — `Base` is 11 lines with an implicit PK and tablename.** 🟢
  `@as_declarative` with `id = Column(Integer, primary_key=True, index=True)`
  and `__tablename__ = cls.__name__.lower()` — which would produce
  `aeroplanemodel`, so essentially every model overrides it. The convenience is
  inherited but unused. 🟡

### Errors

- **BR-PC20 — One exception hierarchy, one envelope.** 🟢
  ```
  ServiceException(message, details)      → 500 "service_error"
  ├── NotFoundError(entity=, resource_id=)→ 404 "not_found"
  ├── ValidationError                     → 422 "validation_error"
  │   └── ValidationDomainError           → 422 "validation_error"
  ├── ConflictError                       → 409 "conflict"
  └── InternalError                       → 500 "internal_error"
  ```
  Body: `{"error": {"code": …, "message": …, "details": … | null}}`, with
  `details` passed through
  `jsonable_encoder(..., custom_encoder={BaseException: str})` so an exception
  stored in `details` serialises instead of crashing the handler. 4xx log at
  INFO, 5xx with `logger.exception`.
- **BR-PC21 — `NotFoundError` has a convenience constructor.** 🟢
  `entity=` builds `"{entity} not found"` and stuffs
  `{"id": str(resource_id), "entity": entity}` into `details`.
- **BR-PC22 — Both German-language handlers are translated to English
  (Q-CC-5).** 🟢 `IntegrityError → 409` and `RequestValidationError → 422` get
  English messages, consistent with the project's English-only UI rule;
  accepted as a client-visible change because there are no external API
  consumers (Q-CC-1). 🔴 **Still open:** whether `IntegrityError` should stop
  assuming *every* integrity violation is a duplicate name (it currently hides
  FK, NOT-NULL and CHECK violations behind that one message) — `Q-CC-5` settles
  the language, not the over-generalisation.
- **BR-PC23 — One error envelope, everywhere (Q-CC-3).** 🟢
  `{"error": {code, message, details}}` is the single contract. The per-module
  `_raise_http` / `_call` helpers that emit FastAPI's `{"detail": …}` — five
  distinct local mappers in `mission-and-sizing` alone, plus separate ones in
  `mass-and-balance`, `versioning`, `ai-copilot` and `construction-plans` — are
  **deleted**. The deliberate 422 that `matching_chart.py` and
  `field_lengths.py` currently signal by mapping a bare `ServiceException`
  survives as the named `ValidationDomainError` type already in the hierarchy
  (BR-PC20), so the behaviour is reproducible and applies uniformly rather than
  as a habit in two files. Accepted as an internal, mechanical migration
  because every consumer (frontend, MCP) lives in this repository (Q-CC-1).

### Numeric safety

- **BR-PC24 / ADR 0012 / ADR 0020 — `null` is an honest "no value", declared by
  a `DesignWarning` (Q-PC-1, P-WARN-0).** 🟢
  `NonFiniteSafeJSONResponse` converts `NaN` / ±`Inf` to `null` and logs a
  WARNING with the replacement count; the module docstring states the
  philosophy: `null` is *"an honest 'no value', never a fabricated fallback
  number that would hide the underlying design problem"*. It recurses
  dicts/lists/tuples and handles `np.floating` explicitly (numpy floats are
  **not** `float` subclasses); `bool` is checked **before** `float`. The
  response class already knows which JSON paths it replaced, so it additionally
  collects them and attaches a `DesignWarning` (`code: NON_FINITE_VALUE`,
  `context: {paths: [...]}`) to the response — the substitution is declared by
  construction, without touching every producer.
- **BR-PC25 — It becomes the app-wide `default_response_class`, declaring what
  it sanitised (Q-PC-1).** 🟢 Today it protects exactly `aeroanalysis.py:43`;
  `operating_points`, `section_aoa`, `airfoils`, the powertrain routers and the
  speed polar all return solver numbers over plain `JSONResponse` and can still
  500 (Starlette renders with `json.dumps(allow_nan=False)`); `powertrain` can
  additionally emit `float("inf")` from `_p_aero` / `_p_elec` — a **design
  statement** (division by zero capacity), not a serialisation mishap, and must
  surface as a warning rather than being quietly nulled. Making it the app's
  `default_response_class` closes the gap for all ≈230 routes at once. This
  does **not** conflict with `P-WARN-0`: a bare 500 loses the *entire* response
  and hides the cause, which is less honest than `null` + a declaration — see
  BR-PC24.

### Events and jobs

- **BR-84 — A broken subscriber can never break the publishing request.** 🟢
  `EventBus.publish` wraps every handler in `try/except` and only logs.
- **BR-82 — Marking dirty and publishing are separate responsibilities.** 🟢/🟡
  `mark_ops_dirty` is a bulk `UPDATE operating_points SET status='DIRTY' WHERE
  aircraft_id = ? AND status NOT IN ('DIRTY','COMPUTING')`, called by the
  **publishers** (seven call sites) immediately *before*
  `event_bus.publish(...)`; the handlers only schedule jobs — yet their log
  lines read *"OPs marked DIRTY"*.
- **BR-83 — Recompute triggers exclude their own outputs.** 🟢
  `_RECOMPUTE_TRIGGERING_PARAMS = {target_static_margin, mass}` deliberately
  excludes `cg_x`, `cd0` and `cl_max` — including them would create a
  `recompute → AssumptionChanged(cg_x) → recompute` loop.
- **BR-PC26 — Debounce = 2.0 s, and the new task is created first.** 🟢
  ```
  new_task = self._create_task_safe(...)
  if new_task is None: return          # nothing was clobbered
  if existing_task and not done: existing_task.cancel()
  self._jobs[id] = Job(...) ; self._debounce_tasks[id] = new_task
  ```
  because `_create_task_safe` can legitimately return `None` (no bound loop,
  unit-test context) and cancelling first would strand the job in `DEBOUNCING`
  with no task to fire it.
- **BR-PC27 — Cross-thread scheduling has a 2 s timeout.** 🟢
  From a worker thread, `_create_task_safe` posts `call_soon_threadsafe`
  onto the bound main loop and waits on a `threading.Event`; on timeout it
  returns `None` and **the schedule is silently dropped**. 🔴
- **BR-PC28 — `schedule_retrim`'s short-circuit coalesces rather than drops
  (Q-PC-4).** 🟢 The asymmetry with `schedule_recompute_assumptions` was a
  **defect**, not a design choice: today a retrim requested while one is
  already `COMPUTING` is discarded, so the edit that triggered it may never be
  retrimmed — and it compounds with a dropped retrim leaving operating points
  `DIRTY` with nothing left to pick them up. Required: when a job is already
  running and another request arrives, record "re-run needed" and run **once**
  on completion, rather than discarding the request. Shutdown still cannot
  interrupt a worker already inside a compute.
- **BR-PC29 — The third job family becomes a tracked `Job` produced by a
  service, not a `scripts/` import (Q-PC-5).** 🟢
  `background_jobs.py:362`'s `from scripts.backfill_airfoil_low_re import
  _compute_geometry_stats` — application code depending on a **private**
  function of a script, inverting the dependency direction — moves into a
  service that `background_jobs` calls. The backfill becomes the third of
  three job families to get a `Job` record, closing the one place a background
  operation could fail with no trace.

### Health and logging

- **BR-PC30 — `/health` stays always 200; a new `/ready` reports schema
  agreement (Q-PC-2).** 🟢 `SELECT 1` →
  `{status: "ok", version: settings.version, database:
  "reachable"|"unreachable"}` — deliberately, *"so that a load balancer can tell
  the difference between 'service is down' (HTTP error) and 'service is up but
  degraded'"*. The module header forbids importing CadQuery/AeroSandbox here so
  the endpoint stays importable on `linux/aarch64`. `/health`'s semantics are
  **unchanged** — the motivation for a readiness signal is not load-balancer
  gating (there is none, per Q-CC-1/Q-CC-8) but the recurring, documented
  stumbling block of a running process left on the wrong Alembic schema after a
  migration-bearing merge. A small **`/ready`** endpoint reports the running
  Alembic revision against head plus the `cad_available` /
  `aerosandbox_available` flags. A startup log line states the same facts an
  operator needs: registered routers, detected capabilities, database URL and
  the Alembic revision (BR-PC46, `app-bootstrap-lifespan`).
- **BR-PC31 — Logging stays deliberately minimal (Q-PC-3).** 🟢
  `setup_logging()` runs at module import of `app.main`, honours `LOG_LEVEL`,
  and silences `matplotlib`, `websockets`, `asyncio`, `kaleido`,
  `choreographer`, `browser_proc` to CRITICAL. Format
  `"%(asctime)s %(levelname)s %(name)s: %(message)s"`. A full observability
  stack — JSON/file handlers, request-correlation ids, and metrics for queue
  depth, job duration, failure rate, transaction duration, rollbacks or lock
  waits — is **out of scope for a single-user desktop application**: a
  **documented scope exclusion**, not an unaddressed gap, to be revisited
  together with the multi-user vision (Q-CC-1). In scope: a **configurable log
  level** replacing DEBUG-by-default, and meaningful, attributable messages in
  the background-job system. Acknowledged trade-off: the missing transaction /
  rollback / lock-wait signals are exactly what would have surfaced both the
  SQLite contention that forced WAL and the MCP commit defect (`Q-MC-1`) —
  accepted because those defects are being fixed directly.
- **ADR 0016 / ADR 0024 — Unauthenticated by design, with an exposure guard
  (Q-CC-1).** 🟢 `app/core/security.py` contains a 4-line `verify_token`
  comparing against the literal `"valid_token"`; it has **no callers**. The
  REST surface, `/docs`, `/static`, `/assets` and `/mcp` are all
  unauthenticated — **deliberately**: da3Dalus is a single-user, standalone
  desktop application; multi-user capability is a future vision, out of scope
  now. ADR 0016's framing of the ngrok/oauth2-proxy/Caddy chain as *the
  system's access control* is corrected — it is the maintainer's own testing
  tool for sharing a preview, not a product boundary; `deploy/` is versioned in
  a separate private repository (Q-CC-2), never in this repo. Because an
  app-side bind guard is impossible when uvicorn opens the socket before the
  app loads, the guard lives at the launch surfaces: the documented dev command
  drops `--host 0.0.0.0` (uvicorn's own default is already loopback), Docker
  publishes to `127.0.0.1` only while `--host 0.0.0.0` stays mandatory inside
  the container, and a startup log line states the effective reachability and
  warns on a non-loopback bind without an explicit `ALLOW_PUBLIC_BIND` opt-in
  (BR-PC48, `app-bootstrap-lifespan`). Everything ADR 0016 lists under its
  risks — public `/docs`/`/redoc`/`/openapi.json`/`/static`, `allow_origins=
  ["*"]` with `allow_credentials=True`, no rate limiting — remains true and is
  now **accepted**, not mitigated.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Compose the app with all unconditional routers | Must | ≈230 routes registered |
| RF-02 | Include `versioning` before `aeroplane` | Must | `/aeroplanes/compare` resolves to the compare handler |
| RF-03 | Register heavy routers only when their capability is available | Must | On a CAD-less platform the app still starts |
| RF-04 | Return 503 from `Depends(require_*)` when a registered endpoint needs a missing capability | Must | Explanatory message present |
| RF-05 | Probe each capability once per process | Must | `lru_cache(maxsize=1)` |
| RF-06 | Create `tmp/` before mounting `/static` | Must | A fresh worktree starts |
| RF-07 | Mount `/static`, `/assets` and `/mcp` | Must | All three resolve |
| RF-08 | Serve `/docs` with the project favicon, `/redoc`, `/openapi.json` | Should | Custom Swagger page renders |
| RF-09 | Run the six lifespan steps in order | Must | Job tracker has a bound loop and both functions |
| RF-10 | Never block startup on a seeder failure | Must | A raising seeder logs a WARNING and startup continues |
| RF-11 | Nest the MCP lifespan | Must | MCP startup/shutdown run inside the app's |
| RF-12 | Shut down both process-pool executors and the job tracker | Must | No worker outlives a test run |
| RF-13 | Commit on success and roll back on exception in `get_db()` | Must | ADR 0009 |
| RF-14 | Configure SQLite with WAL, `synchronous=NORMAL`, `busy_timeout=30000` | Must | Pragmas applied on every new connection |
| RF-15 | Use `autoflush=False`, `expire_on_commit=False`, `autocommit=False` | Must | A pending write is invisible to a query until `flush()` |
| RF-16 | Translate the `ServiceException` hierarchy into the envelope | Must | 404/409/422/500 with `code` |
| RF-17 | Serialise exception objects inside `details` | Must | No handler crash |
| RF-18 | Log 4xx at INFO and 5xx with `logger.exception` | Should | Both observed |
| RF-19 | Map `IntegrityError` → 409 and `RequestValidationError` → 422, in English | Must | Translated per Q-CC-5; 🟡 `IntegrityError`'s duplicate-name over-generalisation is still open |
| RF-20 | Render non-finite floats as `null` with a WARNING | Must | `NaN` → `null`, count logged |
| RF-21 | Publish domain events without letting a handler break the request | Must | A raising subscriber is logged only |
| RF-22 | Route invalidation to the four subscribers with their guards | Must | `cg_x` triggers retrim but not recompute |
| RF-23 | Debounce jobs at 2.0 s, creating the new task before cancelling the old | Must | A `None` task leaves the previous job intact |
| RF-24 | Short-circuit `schedule_retrim` while `COMPUTING` | Should | Recompute deliberately does not |
| RF-25 | Answer `/health` with 200 always | Must | Even when the DB is unreachable |
| RF-26 | Configure logging at import with `LOG_LEVEL` and the noisy-logger silences | Should | Six loggers at CRITICAL |
| RF-27 | Provide `REPO_ROOT` / `AIRFOILS_DIR` as absolute paths | Must | CWD-independent |
| RF-28 | Resolve `ARTIFACTS_BASE_DIR` to an absolute path | Must | A relative override becomes absolute |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Availability | The service must start and answer `/health` even without CadQuery/AeroSandbox | conditional imports + ADR 0017 | 🟢 |
| Availability | Startup must not fail on a seeding error | both seeders' `except … warning` | 🟢 |
| Integrity | One request = one transaction | `get_db()` | 🟢 |
| Concurrency | A multi-second write transaction must not lock out readers | WAL + `busy_timeout=30000` | 🟢 |
| Performance | CPU-bound recompute must not block the event loop | `asyncio.to_thread` in `_recompute_wrapper` | 🟢 |
| Performance | Rapid edits must not trigger a storm of recomputes | `debounce_seconds = 2.0` | 🟢 |
| Robustness | A NaN must not become a 500 anywhere in the API | `NonFiniteSafeJSONResponse` as `default_response_class` (Q-PC-1) | 🟢 (today, 🟡 one router only) |
| Robustness | A broken event subscriber must not break the request | `EventBus.publish` | 🟢 |
| Cleanliness | Process-pool workers must not outlive the server or a test run | the teardown block | 🟢 |
| Security | Unauthenticated **by design** (Q-CC-1/ADR 0024), with an exposure guard at the launch surfaces; CORS remains `*` with credentials — unaddressed | ADR 0016/0024; `main.py:233-239` | 🟢 (auth stance); 🟡 (CORS policy) |
| Operability | A configurable log level and meaningful job messages; a full metrics/correlation-id stack is a **deliberate scope exclusion** (Q-PC-3) | `logging_config.py` | 🟢 |
| Operability | `/health` stays always-200; a new `/ready` reports Alembic-head agreement and capability flags (Q-PC-2) | `health.py` | 🟢 |
| Durability | Background-job state stays in-memory and per-process — a **permanent, enforced** architectural constraint (Q-CC-8/ADR 0024), not debt; the app refuses to start with more than one worker. A cross-thread schedule dropped after 2 s remains unaddressed | `background_jobs.py` | 🟡 (constraint decided; the silent 2 s drop is still 🟡) |

## Acceptance Criteria

```gherkin
Feature: Composition

  Scenario: The compare route wins
    When I GET /aeroplanes/compare?a=1&b=2
    Then the compare handler runs
    And not the get-aeroplane-by-id handler

  Scenario: A CAD-less platform still starts
    Given cadquery cannot be imported
    When the app is created
    Then startup succeeds
    And GET /health returns 200
    And the CAD routes are absent

  Scenario: A registered endpoint without its capability answers 503
    Given an endpoint declaring Depends(require_aerosandbox)
    And aerosandbox is unavailable
    Then the response status is 503 with an explanatory message

  Scenario: tmp is created before the static mount
    Given a fresh checkout with no tmp directory
    When the app is created
    Then tmp exists and /static is mounted

Feature: Lifespan

  Scenario: The six steps run
    When the app starts
    Then the default component types and mission presets are seeded
    And invalidation handlers are registered
    And the job tracker has a bound loop, a trim function and a recompute function

  Scenario: A failing seeder does not block startup
    Given seed_default_types raises
    When the app starts
    Then a WARNING is logged
    And the application still serves requests

  Scenario: Teardown stops the executors
    When the app shuts down
    Then job_tracker.shutdown() was awaited
    And both process-pool executors were shut down

Feature: Transactions

  Scenario: A successful request commits
    Given an endpoint that adds a row via get_db
    When the request succeeds
    Then the row is visible in a new session

  Scenario: A failing request rolls back
    Given the endpoint raises after adding a row
    Then no row is visible in a new session

  Scenario: Pending writes need an explicit flush
    Given autoflush is False
    When a service adds a row and queries for it without flushing
    Then the query does not return it

Feature: Errors

  Scenario: The envelope
    Given a service raising NotFoundError(entity="Wing", resource_id=7)
    Then the status is 404
    And the body is {"error": {"code": "not_found", "message": "Wing not found",
      "details": {"id": "7", "entity": "Wing"}}}

  Scenario: An exception inside details serialises
    Given details containing an exception object
    Then the handler returns a JSON body and does not crash

  Scenario: An integrity violation
    Given a NOT NULL violation
    Then the status is 409
    And the message is "name existiert bereits"

Feature: Numeric safety

  Scenario: A NaN becomes null
    Given an aeroanalysis endpoint returning {"cl": NaN}
    Then the body is {"cl": null}
    And a WARNING records one replacement

  Scenario: A numpy float is handled
    Given a numpy float64 NaN
    Then it is also rendered null

  Scenario: An unprotected router still crashes
    Given a NaN returned from the operating-points router
    Then the response is a 500

Feature: Events and jobs

  Scenario: A broken subscriber is contained
    Given a subscriber that raises
    When GeometryChanged is published
    Then the publish call returns normally and logs the error

  Scenario: Recompute triggers exclude their own outputs
    When AssumptionChanged("cg_x") is published
    Then a retrim is scheduled
    And no recompute is scheduled

  Scenario: Debounce coalesces
    Given two GeometryChanged events 0.5 s apart
    Then exactly one retrim runs, about 2 s after the second

  Scenario: A dropped cross-thread schedule
    Given no bound event loop
    When schedule_retrim is called from a worker thread
    Then _create_task_safe returns None
    And the previously scheduled job is left intact

Feature: Health

  Scenario: Degraded is still 200
    Given the database is unreachable
    When I GET /health
    Then the status is 200
    And the body reports database "unreachable"
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|---|---|---|
| `get_db()` transaction boundary (RF-13) | Must | ADR 0009 — every service is written against it |
| Router composition and order (RF-01/RF-02) | Must | gh-914: wrong order silently shadows a route |
| Capability probing and 503 gating (RF-03…RF-05) | Must | ADR 0017 — the service must run on `linux/aarch64` |
| Lifespan steps + guaranteed teardown (RF-09…RF-12) | Must | Without the loop binding, every background job is dropped |
| SQLite WAL configuration (RF-14/RF-15) | Must | Otherwise "database is locked" under normal use |
| The error envelope (RF-16…RF-18) | Must | The client's only machine-readable failure contract |
| Non-finite safety (RF-20) | Must | ADR 0012 — a NaN would otherwise be an unhandled 500 |
| Event containment + invalidation routing (RF-21/RF-22) | Must | BR-83's loop prevention is not optional |
| Debounce ordering (RF-23) | Must | The reverse order strands jobs |
| `/health` always 200 (RF-25) | Must | The documented load-balancer contract |
| Absolute paths (RF-27/RF-28) | Must | The OpenVSP "missing airfoils" bug |
| Custom `/docs` (RF-08) | Should | Cosmetic |
| Retrim short-circuit (RF-24) | Should | A deliberate asymmetry |
| Structured logging (metrics, correlation ids) | Won't, deliberately (Q-PC-3) | 🟢 out of scope for a single-user desktop app; log level + job messages are in scope |
| Authentication / authorisation | Won't, by design (Q-CC-1/ADR 0024) | 🟢 unauthenticated is the product position; an exposure guard (loopback defaults) is Must |
| A readiness probe (migration head, capability flags) | Should (Q-PC-2) | 🟢 decided — a small `/ready` endpoint plus a startup summary |
| Persistent / cross-worker background jobs | Won't — a permanent, enforced constraint (Q-CC-8/ADR 0024) | 🟢 single-worker operation is asserted at startup, not merely assumed |
| One `Settings` class, one version string | Must (Q-CC-4) | 🟢 decided — merge into one class, one `pyproject.toml`-derived version |
| Envelope everywhere | Must (Q-CC-3) | 🟢 decided — the per-module `{"detail": …}` helpers are deleted |

## Code Traceability

| File | Symbol | Coverage |
|---|---|---|
| `app/main.py` (349 l.) | `create_app`, `_combined_lifespan`, 3 exception handlers, `run_app` | 🟢 |
| `…:37-72` | conditional heavy-router imports | 🟢 |
| `…:100-196` | `_combined_lifespan` (6 steps + teardown) | 🟢 |
| `…:198-263` | app construction, routers, CORS, mounts, `/docs` | 🟢 |
| `…:274-336` | `service_exception_handler`, `integrity_error_handler`, `request_validation_exception_handler` | 🟢 |
| `app/core/config.py` (48 l.) | `Settings` #1, `REPO_ROOT`, `AIRFOILS_DIR` | 🟢 |
| `app/settings.py` (126 l.) | `Settings` #2, `get_settings`, `_DEFAULT_LOW_RE_GRID`, `_DEFAULT_MISSION_WEIGHTS` | 🟢 |
| `app/core/exceptions.py` (61 l.) | the `ServiceException` hierarchy | 🟢 |
| `app/core/platform.py` (67 l.) | `cad_available`, `aerosandbox_available`, `require_*` | 🟢 |
| `app/core/events.py` (49 l.) | `EventBus`, `GeometryChanged`, `AssumptionChanged` | 🟢 |
| `app/core/background_jobs.py` (431 l.) | `JobTracker`, `JobStatus`, `RetrimJob`, `RecomputeAssumptionsJob` | 🟢 |
| `app/core/json_safe.py` (92 l.) | `NonFiniteSafeJSONResponse`, `replace_nonfinite` | 🟢 |
| `app/db/session.py` (63 l.) | engine, pragmas, `SessionLocal`, `get_db` | 🟢 |
| `app/db/base.py` (11 l.) | declarative `Base` | 🟢 |
| `app/logging_config.py` (22 l.) | `setup_logging` | 🟢 |
| `app/api/v2/endpoints/aeroplane/__init__.py` | 24 aggregated sub-routers | 🟢 |
| `app/api/v2/endpoints/health.py` | `/health`, `HealthResponse` | 🟢 |
| `app/services/invalidation_service.py` | `register_handlers`, `mark_ops_dirty`, the two param sets | 🟢 |
| `app/core/security.py` (4 l.) | `verify_token` | 🟡 dead — no callers |
| `app/api/v1/` | — | 🟡 **does not exist**, although both `CLAUDE.md` files describe it |
| `app/api/v2/endpoints/aeroplane.py` | — | 🟢 shadowed dead code, **deleted** (P-DEAD-0 rule 3, via `Q-AC-1`) — unreachable by construction (the package `aeroplane/` wins the import), no live ticket, not a safety mechanism; "kept for backward compatibility" is exactly the inert state the policy forbids, and misleading besides — it registers only 3 of the 24 sub-routers |
