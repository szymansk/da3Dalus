# platform-core — Implementation Tasks

> Executable sequence to re-implement the module from the legacy behaviour.
> Every task cites the legacy file, a definition of done, and a confidence
> marker.
> Use-case task lists: [`app-bootstrap-lifespan`](app-bootstrap-lifespan/tasks.md) ·
> [`config-and-settings`](config-and-settings/tasks.md) ·
> [`transaction-and-error-handling`](transaction-and-error-handling/tasks.md) ·
> [`background-jobs-invalidation`](background-jobs-invalidation/tasks.md).

## Prerequisites

- [ ] Python 3.11/3.12, FastAPI, SQLAlchemy 2.x, pydantic-settings, uvicorn.
- [ ] A database URL — SQLite by default (`sqlite:///./db/test.db`) with
      Alembic-managed schema; PostgreSQL is also targeted.
- [ ] `pyproject.toml` env markers excluding `cadquery` / `aerosandbox` on
      `linux/aarch64` (ADR 0017).
- [ ] `tmp/` and `app/static/` directories.

## Tasks

- [ ] **T-01 — `Base`.**
  `@as_declarative` with an implicit
  `id = Column(Integer, primary_key=True, index=True)` and
  `__tablename__ = cls.__name__.lower()`.
  - Legacy origin: `app/db/base.py` (11 l.)
  - Definition of done: reproduce it and **record** that the implicit tablename
    would yield `aeroplanemodel`, so essentially every model overrides it — the
    convenience is inherited but unused.
  - Confidence: 🟢

- [ ] **T-02 — Engine, pragmas and `SessionLocal`.**
  `SQLALCHEMY_DATABASE_URL` via bare `os.getenv`; SQLite `connect_args`
  (`check_same_thread=False`, `timeout=30`); an `Engine.connect` listener
  setting `journal_mode=WAL`, `synchronous=NORMAL`, `busy_timeout=30000`;
  `sessionmaker(expire_on_commit=False, autocommit=False, autoflush=False)`.
  - Legacy origin: `app/db/session.py:1-52`
  - Definition of done: a test opens two connections and confirms WAL. Carry the
    comment explaining *why* (a multi-second recompute write transaction would
    otherwise produce "database is locked"). Record the bare `os.getenv` as a
    deliberate bootstrap exception.
  - Confidence: 🟢

- [ ] **T-03 — `get_db()`.**
  `yield` → `commit` → `rollback` on exception → `close` in `finally`.
  - Legacy origin: `app/db/session.py:55-64`; ADR 0009
  - Definition of done: two tests — a successful request persists, a failing one
    does not. Document the rule that services never call `commit()` / `begin()`,
    and enumerate the four legitimate own-session paths.
  - Confidence: 🟢

- [ ] **T-04 — The exception hierarchy.**
  `ServiceException(message, details or {})`, `NotFoundError` (with the
  `entity=` / `resource_id=` convenience constructor), `ValidationError`,
  `ValidationDomainError`, `ConflictError`, `InternalError`.
  - Legacy origin: `app/core/exceptions.py` (61 l.)
  - Definition of done: `NotFoundError(entity="Wing", resource_id=7)` produces
    `"Wing not found"` and `{"id": "7", "entity": "Wing"}`.
  - Confidence: 🟢

- [ ] **T-05 — The three global exception handlers.**
  `service_exception_handler` (the envelope, `_safe_json` on `details`, INFO for
  4xx / `exception` for 5xx); `integrity_error_handler` (409, **English**,
  Q-CC-5); `request_validation_exception_handler` (422, **English**, Q-CC-5,
  `exc.errors()` in `details`).
  - Legacy origin: `app/main.py:269-336`
  - Definition of done: an exception object stored in `details` serialises
    instead of crashing the handler. Both messages translate to English
    (Q-CC-5) — a client-visible change accepted because there are no external
    API consumers (Q-CC-1). **Still record as an open gap:** the
    `IntegrityError` handler still assumes every violation is a duplicate name,
    hiding FK / NOT-NULL / CHECK violations — not addressed by the interview.
  - Confidence: 🟢

- [ ] **T-06 — Capability probes and guards.**
  `cad_available()` / `aerosandbox_available()` as `@lru_cache(maxsize=1)`;
  `require_cad` / `require_aerosandbox` raising `HTTPException(503, <why>)`.
  - Legacy origin: `app/core/platform.py` (67 l.); ADR 0017
  - Definition of done: the probe runs once per process; a registered endpoint
    lacking its capability answers a clean 503 with an explanatory message.
  - Confidence: 🟢

- [ ] **T-07 — `NonFiniteSafeJSONResponse`.**
  Recurse dicts/lists/tuples (tuple → list); check `bool` **before** `float`;
  handle `np.floating` explicitly; `NaN`/±`Inf` → `None`; log one WARNING with
  the replacement count; collect the sanitised JSON paths and attach a
  `DesignWarning` (`code: NON_FINITE_VALUE`) to the response (Q-PC-1).
  - Legacy origin: `app/core/json_safe.py` (92 l.); ADR 0012, ADR 0020
  - Definition of done: a numpy `float64` NaN renders `null`; a `bool` stays a
    bool. Carry the docstring's philosophy — `null` is an honest "no value",
    never a fabricated fallback. **Wire it as the app-wide
    `default_response_class`** (T-14) rather than only on `aeroanalysis`
    (Q-PC-1) — a bare 500 loses the whole response and hides the cause, so this
    is *more* honest, not less, and does not conflict with `P-WARN-0`.
  - Confidence: 🟢

- [ ] **T-08 — `EventBus` + the two events.**
  `dict[type[DomainEvent], list[Callable]]`; `publish` wraps every handler in
  `try/except` and only logs. `GeometryChanged(aeroplane_id, source_model)`,
  `AssumptionChanged(aeroplane_id, parameter_name)`, both with a UTC timestamp.
  - Legacy origin: `app/core/events.py` (49 l.)
  - Definition of done: a raising subscriber does not propagate into the
    publishing request.
  - Confidence: 🟢

- [ ] **T-09 — `JobTracker`.**
  `debounce_seconds = 2.0`; two families (retrim, recompute), each
  `dict[aeroplane_id → Job]` + `dict[aeroplane_id → asyncio.Task]`; statuses
  `DEBOUNCING → COMPUTING → DONE | FAILED`; **create the new task first, then
  cancel the old**; `_create_task_safe` posting `call_soon_threadsafe` from a
  worker thread and waiting on a `threading.Event` with a **2.0 s** timeout;
  `bind_loop`, `set_trim_function`, `set_recompute_function`, `shutdown`.
  - Legacy origin: `app/core/background_jobs.py` (431 l.)
  - Definition of done: a test that swaps the create/cancel order must strand a
    job in `DEBOUNCING` — that is the proof the ordering is load-bearing.
    Record the silent drop on timeout as a gap.
  - Confidence: 🟢

- [ ] **T-10 — `invalidation_service.register_handlers` + `mark_ops_dirty`.**
  Four subscriptions with their guards (`_OP_AFFECTING_PARAMS = {mass, cg_x}`,
  `_RECOMPUTE_TRIGGERING_PARAMS = {target_static_margin, mass}`); the bulk
  `UPDATE operating_points SET status='DIRTY' WHERE aircraft_id = ? AND status
  NOT IN ('DIRTY','COMPUTING')`.
  - Legacy origin: `app/services/invalidation_service.py`
  - Definition of done: `cg_x` triggers a retrim and **not** a recompute — carry
    the comment explaining that including `cg_x`/`cd0`/`cl_max` would create a
    recompute loop (BR-83). Record that `mark_ops_dirty` is called by the seven
    **publishers**, not by the handlers, while the handlers' log lines claim
    otherwise (BR-82).
  - Confidence: 🟢

- [ ] **T-11 — One merged `Settings` class (Q-CC-4).**
  Merge `app/core/config.py` (`PROJECT_NAME`, `VERSION`, `UVICORN_HOST`,
  `ARTIFACTS_BASE_DIR` + `field_validator(mode="after")` → **reject** if
  relative, Q-PC-6, the four `COPILOT_*`, `REPO_ROOT` / `AIRFOILS_DIR`) and
  `app/settings.py` (`base_url`, `openai_api_key`, `version`, the 13
  `low_re_*`) into **one class, one naming convention, one instance** — the
  double-instance bug (`settings` singleton vs a separately `lru_cache`d
  `get_settings()` returning a different object) disappears by construction.
  Fold in `SQLALCHEMY_DATABASE_URL`, `LOG_LEVEL`, `DISPLAY_CONSTRUCTION_STEP`.
  One version string, derived from `pyproject.toml`.
  - Legacy origin: `app/core/config.py` (48 l.), `app/settings.py` (126 l.)
  - Definition of done: one class, both `.env` field sets present, `.env`
    still read with `extra="ignore"`. Carry the `AIRFOILS_DIR` comment verbatim
    (the OpenVSP "missing airfoils" bug). Every consumer on both legacy sides
    migrates to the merged class (`config-and-settings/requirements.md`'s
    consumer table). `SQLALCHEMY_DATABASE_URL` may stay a bootstrap exception
    only if Alembic genuinely needs it before settings exist — verify, don't
    assume.
  - Confidence: 🟢

- [ ] **T-12 — `setup_logging`, deliberately minimal (Q-PC-3).**
  `LOG_LEVEL` via the merged `Settings` (T-11), **configurable** rather than
  DEBUG-fixed; format `"%(asctime)s %(levelname)s %(name)s: %(message)s"`;
  silence `matplotlib`, `websockets`, `asyncio`, `kaleido`, `choreographer`,
  `browser_proc` to CRITICAL; called at module import of `app.main`. No JSON/
  file handler, no request-correlation id, no metrics stack — a documented
  scope exclusion for a single-user desktop app (Q-PC-3), not a gap.
  - Legacy origin: `app/logging_config.py` (22 l.)
  - Definition of done: an invalid `LOG_LEVEL` silently falls back to DEBUG
    (`getattr(logging, name, DEBUG)`) — reproduce and record it (not addressed
    by the interview, still an open gap whether this should warn).
  - Confidence: 🟢

- [ ] **T-13 — Import-time capability probing and conditional router imports.**
  Call the probes **before** `create_app` is defined; wrap each heavy router
  import in its own `try/except ImportError` that logs a warning; import
  `app.models.avl_geometry_events` and `app.models.stability_events` for their
  registration side effects (`# noqa: F401`).
  - Legacy origin: `app/main.py:25-85`
  - Definition of done: with `cadquery` unimportable the module still imports
    and the CAD router global stays `None`.
  - Confidence: 🟢

- [ ] **T-14 — `create_app()`.**
  Build `mcp_app` first; construct `FastAPI(title=…, version=<from
  pyproject.toml, Q-CC-4>, openapi_url="/openapi.json", docs_url=None,
  redoc_url="/redoc", lifespan=_combined_lifespan)`; include the routers **in
  the legacy order** (versioning before aeroplane; `openvsp_import` **without**
  a prefix — all 230 routes at the root, Q-CC-6); add CORS;
  `default_response_class=NonFiniteSafeJSONResponse` (T-07, Q-PC-1);
  `os.makedirs("tmp")`; mount `/static`, `/assets`, `/mcp`; add the custom
  `/docs` and the Swagger OAuth redirect routes.
  - Legacy origin: `app/main.py:94-263`
  - Definition of done: a route-order test proves `/aeroplanes/compare` resolves
    to the compare handler (gh-914). Reproduce the CORS block **with its
    comment**; the policy itself is an unaddressed gap (not resolved by the
    interview).
  - Confidence: 🟢

- [ ] **T-15 — `_combined_lifespan`.**
  Six steps, both seeders wrapped in `except … logger.warning`, the recompute
  wrapper using `asyncio.to_thread`, the nested `async with
  mcp_app.lifespan(app)`, and the `finally` teardown of the job tracker plus
  both process-pool executors.
  - Legacy origin: `app/main.py:100-196`
  - Definition of done: a raising seeder logs a WARNING and startup continues;
    after shutdown no `ProcessPoolExecutor` worker remains. Carry the comment
    explaining that ~200 CPU-bound ASB calls per recompute would otherwise block
    every request.
  - Confidence: 🟢

- [ ] **T-16 — `/health` plus a new `/ready` (Q-PC-2).**
  `/health`: `SELECT 1`; `{status, version, database}`; **always 200**; no
  CadQuery or AeroSandbox import in the module. New `/ready`: reports the
  running Alembic revision against head, plus `cad_available` /
  `aerosandbox_available`. A startup log line states the same facts —
  registered routers, capabilities, database URL, Alembic revision.
  - Legacy origin: `app/api/v2/endpoints/health.py`
  - Definition of done: with the database down `/health` is still 200 with
    `"unreachable"`. Carry the load-balancer rationale for `/health`'s
    always-200 semantics — `/ready` is the new signal, not a replacement for it.
  - Confidence: 🟢

- [ ] **T-17 — `run_app`.**
  `uvicorn.run(entry_point, host=settings.UVICORN_HOST, port=port, reload=True)`.
  - Legacy origin: `app/main.py:342-349`
  - Definition of done: reproduced. Note the default `port=8000` while the
    documented dev command uses 8001. 🟡
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Route order:** `/aeroplanes/compare` hits the compare handler.
- [ ] **TT-02 — Platform tolerance:** with the probes patched false, the app
      starts, `/health` is 200 and the CAD routes are absent.
- [ ] **TT-03 — 503 guard:** a registered endpoint with an unavailable
      capability returns 503 with a message.
- [ ] **TT-04 — Probe caching:** the probe body runs once.
- [ ] **TT-05 — `tmp/` creation:** a fresh checkout starts and `/static` mounts.
- [ ] **TT-06 — Lifespan order:** all six steps ran; the job tracker has a bound
      loop and both functions.
- [ ] **TT-07 — Seeder failure:** WARNING, startup continues.
- [ ] **TT-08 — Teardown:** job tracker shut down; both executors closed.
- [ ] **TT-09 — Commit:** a successful request persists.
- [ ] **TT-10 — Rollback:** a failing request persists nothing.
- [ ] **TT-11 — `autoflush=False`:** an unflushed add is invisible to a query.
- [ ] **TT-12 — SQLite pragmas:** WAL, `synchronous=NORMAL`, `busy_timeout`.
- [ ] **TT-13 — Envelope:** 404/409/422/500 with the right `code` and `details`.
- [ ] **TT-14 — `details` with an exception:** serialises, no handler crash.
- [ ] **TT-15 — `IntegrityError`:** 409 with the German message
      (characterisation).
- [ ] **TT-16 — Non-finite:** `NaN` → `null` + a WARNING with the count; numpy
      float handled; `bool` unaffected.
- [ ] **TT-17 — Unprotected router (characterisation):** a NaN from
      `operating_points` produces a 500.
- [ ] **TT-18 — Event containment:** a raising subscriber is logged only.
- [ ] **TT-19 — Invalidation routing:** `cg_x` ⇒ retrim only;
      `target_static_margin` ⇒ recompute.
- [ ] **TT-20 — Debounce coalescing:** two events within the window ⇒ one run.
- [ ] **TT-21 — Debounce ordering:** swapping create/cancel strands a job (must
      fail).
- [ ] **TT-22 — Cross-thread drop (characterisation):** no bound loop ⇒
      `_create_task_safe` returns `None` and the previous job survives.
- [ ] **TT-23 — `/health` degraded:** 200 with `"unreachable"`.
- [ ] **TT-24 — Settings:** both classes load; `ARTIFACTS_BASE_DIR` resolves;
      `AIRFOILS_DIR` is absolute and CWD-independent.

## Data Migration Tasks

- [ ] **TM-01 — Seed the 9 default component types** idempotently (gh#83),
      inserting only names not already present.
- [ ] **TM-02 — Seed the 6 mission presets** idempotently (gh-546) — required
      when the schema was built with `create_all` rather than Alembic.
- [ ] **TM-03 — Ensure `tmp/` exists** before the static mount (worktrees).

## Suggested Order

1. **T-01 → T-03** the persistence foundation. `get_db()` is the contract every
   service in the system is written against, so nothing else can be tested
   meaningfully first.
2. **T-04 → T-05** exceptions and their handlers — the second universal
   contract.
3. **T-06** capability probing, because it decides *which routers exist* and
   therefore shapes T-14.
4. **T-07 → T-10** the cross-cutting utilities: non-finite safety, the event
   bus, the job tracker and invalidation routing. T-09 before T-10: the routing
   only means something once scheduling works.
5. **T-11 → T-12** configuration and logging — both are read at import by
   everything above.
6. **T-13 → T-15** the application itself: import-time probing, `create_app`,
   then the lifespan. The lifespan is last because it wires together everything
   built in steps 1–4.
7. **T-16 → T-17** health and the runner.

## Decided by the specification validation interview (2026-08-13 → 15)

The items below were open gaps when this task list was written. Each now has a
maintainer decision; the corresponding `T-*` task should be read together with
the cited question.

- **One `Settings` class, one version string.** Merge (Q-CC-4): one class, one
  naming convention, one instance; version derived from `pyproject.toml`. New
  task: `config-and-settings/tasks.md` T-07/T-08.
- **`SQLALCHEMY_DATABASE_URL`, `LOG_LEVEL`, `DISPLAY_CONSTRUCTION_STEP` move
  into the merged settings** (Q-CC-4), except `SQLALCHEMY_DATABASE_URL` may
  stay a bootstrap exception if Alembic needs it before settings exist — verify,
  don't assume.
- **`/static`, `/assets`, `/docs` and `/mcp` stay publicly readable** — a
  deliberate consequence of "unauthenticated by design" (Q-CC-1/ADR 0024), not
  an open question.
- **Authentication stays out of the application; the boundary moves to the
  launch surfaces** (Q-CC-1/ADR 0024): drop `--host 0.0.0.0` from the
  documented dev command, publish Docker to `127.0.0.1` only, and log the
  effective reachability at startup with an `ALLOW_PUBLIC_BIND` opt-in guard.
  ADR 0016's framing of the tunnel as the product's access control is
  corrected — it is the maintainer's private testing tool.
- **The global `{"error": {…}}` envelope wins** (Q-CC-3); the per-module
  `_raise_http` / `_call` helpers are deleted; the deliberate 422 of
  `matching_chart.py` / `field_lengths.py` becomes the named
  `ValidationDomainError` type.
- **The German handler messages translate to English** (Q-CC-5) — a
  client-visible change accepted because there are no external API consumers.
  🔴 **Still open:** whether `IntegrityError` should stop assuming every
  violation is a duplicate name — not addressed by the interview.
- **`NonFiniteSafeJSONResponse` becomes the app-wide `default_response_class`**
  (Q-PC-1), additionally attaching a `DesignWarning` naming the sanitised
  paths — resolves the apparent conflict with `P-WARN-0` (a lost 500 is less
  honest than `null` + a declaration).
- **Background jobs stay in-memory and per-process — permanently, and
  enforced.** Single-worker operation is a deliberate architectural constraint
  (Q-CC-8/ADR 0024): the app refuses to start with more than one worker.
  🔴 **Still open:** whether a dropped cross-thread schedule (2 s timeout)
  should be surfaced — not addressed.
- **`schedule_airfoil_low_re_compute` becomes a tracked `Job`**, and the
  backfill logic moves out of `scripts/` into a service (Q-PC-5).
- **`/health` gains a readiness signal**: a small `/ready` endpoint (Alembic
  head vs running revision, capability flags) plus a startup summary log line
  (Q-PC-2).
- **`openvsp_import` loses its `/api/v2` prefix**; all 230 routes sit at the
  application root (Q-CC-6) — must land before `Q-CC-11`'s generated
  TypeScript client.
- **Logging stays deliberately minimal** (Q-PC-3): a configurable log level and
  meaningful background-job messages; a JSON/file handler, request-correlation
  id and metrics stack are an explicit, documented scope exclusion for a
  single-user desktop app — not an open question.
- **`app/api/v2/endpoints/aeroplane.py` (shadowed dead code) is deleted**
  (P-DEAD-0 rule 3, via Q-AC-1) — unreachable by construction, no live ticket,
  not a safety mechanism.

## Pending Gaps — not addressed by the interview

- **What should the CORS policy be** once the frontend's actual topology
  (direct browser → FastAPI) is acknowledged? `allow_origins=["*"]` with
  `allow_credentials=True` is invalid for credentialed requests.
- **Should `IntegrityError` stop assuming every violation is a duplicate
  name**, distinguishing FK / NOT-NULL / CHECK from a genuine unique-constraint
  conflict?
- **Should `mark_ops_dirty` move into the event handlers** so publishing and
  marking cannot drift apart (BR-82)?
- **Should a dropped cross-thread schedule (`_create_task_safe`'s 2 s timeout)
  be logged or retried** instead of vanishing silently?
- **Should `app/api/v1`'s stale documentation be fixed?** It does not exist,
  although both root and `app/CLAUDE.md` describe a "legacy v1 REST surface".
