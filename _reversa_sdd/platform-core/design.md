# platform-core — Technical Design

> Module-level design. Focuses on HOW the module is built, derived from the
> legacy code. Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Cross-cutting HTTP contract: [`contracts.md`](contracts.md).
> Use cases: [`app-bootstrap-lifespan`](app-bootstrap-lifespan/design.md) ·
> [`config-and-settings`](config-and-settings/design.md) ·
> [`transaction-and-error-handling`](transaction-and-error-handling/design.md) ·
> [`background-jobs-invalidation`](background-jobs-invalidation/design.md).

## Interface

### `app/main.py` 🟢

| Symbol | Line | Note |
|---|---|---|
| `create_app()` | 94 | builds the MCP ASGI app first, then `FastAPI(...)` |
| `_combined_lifespan(app)` | 100 | 6 steps + nested MCP lifespan + teardown |
| `app` | 266 | the module-level instance |
| `_safe_json(value)` | 269 | `jsonable_encoder(..., custom_encoder={BaseException: str})` |
| `service_exception_handler` | 274 | the envelope |
| `integrity_error_handler` | 310 | 409, English message (Q-CC-5) 🟢; over-general duplicate-name assumption 🟡 |
| `request_validation_exception_handler` | 324 | 422, English message (Q-CC-5) 🟢 |
| `run_app(entry_point, port=8000)` | 342 | `uvicorn.run(host=settings.UVICORN_HOST, reload=True)` |

### `app/db/session.py` 🟢

```python
SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL", "sqlite:///./db/test.db")
engine       = create_engine(URL, connect_args={"check_same_thread": False, "timeout": 30})  # SQLite only
SessionLocal = sessionmaker(bind=engine, class_=Session,
                            expire_on_commit=False, autocommit=False, autoflush=False)

@event.listens_for(Engine, "connect")            # SQLite only
def _set_sqlite_pragmas(dbapi_connection, _):
    PRAGMA journal_mode=WAL ; PRAGMA synchronous=NORMAL ; PRAGMA busy_timeout=30000

def get_db() -> Session:
    db = SessionLocal()
    try:    yield db ; db.commit()
    except: db.rollback() ; raise
    finally: db.close()
```

### `app/core/exceptions.py`, `platform.py`, `events.py`, `json_safe.py` 🟢

| Symbol | Signature |
|---|---|
| `ServiceException(message, details=None)` | `.message`, `.details` (never `None` — `details or {}`) |
| `NotFoundError(message?, details?, entity?, resource_id?)` | builds `"{entity} not found"` + `{"id", "entity"}` |
| `ValidationError` / `ValidationDomainError` / `ConflictError` / `InternalError` | plain subclasses |
| `cad_available()` / `aerosandbox_available()` | `@lru_cache(maxsize=1) -> bool` |
| `require_cad` / `require_aerosandbox` | FastAPI dependencies raising `HTTPException(503)`. 🟡 **[Reviewer]** defined but almost unwired — `require_cad` has 0 production call sites, `require_aerosandbox` has 1 (`section_aoa.py:79`) |
| `EventBus.subscribe(event_type, handler)` / `.publish(event)` | synchronous; `publish` swallows handler errors |
| `GeometryChanged(aeroplane_id, source_model)` / `AssumptionChanged(aeroplane_id, parameter_name)` | dataclasses with a UTC `timestamp` |
| `NonFiniteSafeJSONResponse` | `JSONResponse` subclass; `render()` runs `_sanitize` first |

### `app/core/background_jobs.py` 🟢

| Symbol | Note |
|---|---|
| `JobStatus` | `DEBOUNCING`, `COMPUTING`, `DONE`, `FAILED` |
| `RetrimJob` | `+ dirty_op_ids`, `completed_op_ids`, `failed_op_ids` |
| `RecomputeAssumptionsJob` | `aeroplane_id`, `status`, timestamps, `error` |
| `JobTracker` | `debounce_seconds = 2.0`; `bind_loop`, `set_trim_function`, `set_recompute_function`, `schedule_retrim`, `schedule_recompute_assumptions`, `schedule_airfoil_low_re_compute`, `shutdown` |
| `job_tracker` | module singleton |

## Main Flow

### F1 — Import-time work 🟢

```
app/main.py import order:
  setup_logging()                        # l.91 — DEBUG by default, six loggers silenced
  cad_available() / aerosandbox_available()      # BEFORE create_app is even defined
  conditional heavy-router imports, each in its own try/except ImportError
  from app.mcp_server import create_mcp_http_app # builds the whole FastMCP server (import side effect)
  import app.models.avl_geometry_events          # noqa: F401 — registers SQLAlchemy listeners
  import app.models.stability_events             # noqa: F401 — idem
```

The probes run before `create_app` is defined, so the *set of routers that
exists* is decided at import, not at call. 🟢

### F2 — `create_app()` 🟢

```
mcp_app = create_mcp_http_app(path="/")                       # l.95, BEFORE FastAPI(...)

app = FastAPI(title="da3dalus Model Context Protocol (v2)", version="2.0.0",
              openapi_url="/openapi.json", docs_url=None, redoc_url="/redoc",
              lifespan=_combined_lifespan)

include: health, endurance,
         versioning_v2,          # BEFORE aeroplane_v2 — gh-914 route-order fix
         aeroplane_v2,
         openvsp_import,          # loses its /api/v2 prefix — all 230 routes at root (Q-CC-6) 🟢
         components, component_types, component_tree, construction_parts,
         aeroplane_construction_plans, construction_plans, construction_templates,
         flight_profiles, fuselage_slice
         + cad / aeroanalysis / operating_points / airfoils / section_aoa  (if not None)

add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
               allow_methods=[...], allow_headers=[...])   # 🟢 narrowed to concrete origins (R2-10)

os.makedirs("tmp", exist_ok=True)
mount /static -> tmp/ ; /assets -> app/static ; /mcp -> mcp_app

GET /docs   -> get_swagger_ui_html(..., swagger_favicon_url="/assets/swagger-favicon.svg")
GET {swagger_ui_oauth2_redirect_url} -> get_swagger_ui_oauth2_redirect_html()
```

Detail in
[`app-bootstrap-lifespan`](app-bootstrap-lifespan/design.md).

### F3 — The lifespan 🟢

```
1  seed_default_types(session) + commit          in its own SessionLocal   (gh#83)
2  seed_mission_presets(session) + commit        in its own SessionLocal   (gh-546)
     both wrapped: except Exception -> logger.warning ("never block startup on this")
3  invalidation_service.register_handlers()
4  job_tracker.bind_loop(asyncio.get_running_loop())
5  job_tracker.set_trim_function(retrim_dirty_ops)
6  job_tracker.set_recompute_function(_recompute_wrapper)

async with mcp_app.lifespan(app):
    yield
  finally:
    await job_tracker.shutdown()
    cad_service.shutdown_executor()
    operating_point_generator_service.shutdown_opg_executor()
```

with

```python
def _recompute_sync(aeroplane_id: int) -> None:
    db = SessionLocal()
    try:
        aeroplane = db.query(AeroplaneModel).filter(id == aeroplane_id).first()
        if aeroplane is None: return
        recompute_assumptions(db, str(aeroplane.uuid))
        db.commit()                      # owns its own transaction — a legitimate exception
    except: db.rollback() ; raise
    finally: db.close()

async def _recompute_wrapper(aeroplane_id: int) -> None:
    await asyncio.to_thread(_recompute_sync, aeroplane_id)
    # ASB is CPU-bound (~200 calls per recompute); on the loop it would block every request
```

### F4 — Capability probing 🟢

```
@lru_cache(maxsize=1)
def cad_available() -> bool:          try import cadquery      -> True / False
@lru_cache(maxsize=1)
def aerosandbox_available() -> bool:  try import aerosandbox   -> True / False

require_cad / require_aerosandbox: FastAPI dependencies raising HTTPException(503, <why>)
```

*"A broken install detected once stays broken for the life of the process."* On
`linux/aarch64` five routers do not exist at all, so the **API surface changes
shape by platform** — a property no OpenAPI document can express. 🟢

### F5 — The transaction boundary 🟢

`get_db()` is a generator dependency: commit after the endpoint returns,
rollback on exception, close in `finally`. Because it commits **after** the
response body is produced, a streaming endpoint (the copilot SSE turn) holds the
session for the entire stream and commits only once the generator is fully
consumed. 🔴 (see `ai-copilot`)

Four paths legitimately own their own session: the two seeders,
`_recompute_sync`, and `JobTracker._run_backfill_for_names`. One path should and
does not: `mcp_server._call_endpoint`. 🔴

### F6 — Error translation 🟢

```
ServiceException            -> 404 not_found | 422 validation_error | 409 conflict
                               | 500 internal_error | 500 service_error
   body {"error": {"code", "message", "details": _safe_json(details) or None}}
   4xx: logger.info(exc.details) ; 5xx: logger.exception

IntegrityError             -> 409 {"error": {"code":"conflict",
                                             "message": <English message>}}   🟢 (Q-CC-5)
RequestValidationError     -> 422 {"error": {"code":"validation_error",
                                             "message": <English message>,
                                             "details": exc.errors()}}               🟢 (Q-CC-5)
```
Both messages translate to English (Q-CC-5); `IntegrityError`'s assumption that
*every* violation is a duplicate name is a separate, still-open question — the
maintainer settled the language, not the over-generalisation. 🔴

Detail in
[`transaction-and-error-handling`](transaction-and-error-handling/design.md).

### F7 — Non-finite safety 🟢

```
NonFiniteSafeJSONResponse.render(content):
    safe, count = _sanitize(content)
    if count: logger.warning("Replaced %d non-finite value(s) with null", count)
    return super().render(safe)

_sanitize: recurses dict / list / tuple (tuple -> list)
           bool checked BEFORE float (bool is a float-adjacent int in Python)
           np.floating handled explicitly — numpy floats are NOT float subclasses
           NaN / ±Inf -> None
```

Used as `default_response_class` on **one** router (`aeroanalysis.py:43`) today;
becomes the app-wide default, collecting the sanitised paths into a
`DesignWarning` (`NON_FINITE_VALUE`) rather than only logging (Q-PC-1). 🟢

### F8 — Events and jobs 🟢

```
event_bus (singleton):  dict[type[DomainEvent], list[Callable]]
publish(event):         for h in handlers: try h(event) except Exception: logger.exception

register_handlers():
    GeometryChanged   -> schedule_retrim
    GeometryChanged   -> schedule_recompute_assumptions
    AssumptionChanged -> schedule_retrim                  if param in {mass, cg_x}
    AssumptionChanged -> schedule_recompute_assumptions   if param in {target_static_margin, mass}

mark_ops_dirty(db, aircraft_id):
    UPDATE operating_points SET status='DIRTY'
    WHERE aircraft_id = ? AND status NOT IN ('DIRTY','COMPUTING')
    # called by the PUBLISHERS (7 sites), immediately before event_bus.publish(...)

JobTracker.schedule_*(aeroplane_id):
    new_task = _create_task_safe(_debounced_run(aeroplane_id))
    if new_task is None: return                       # nothing clobbered
    if existing and not existing.done(): existing.cancel()
    _jobs[id] = Job(status=DEBOUNCING) ; _debounce_tasks[id] = new_task

_create_task_safe(coro):
    in the main loop      -> asyncio.create_task(coro)
    in a worker thread    -> loop.call_soon_threadsafe(_make_task)
                             threading.Event().wait(timeout=2.0)
                             on timeout -> None      # 🔴 the schedule is silently dropped
    no bound loop         -> None
```

Detail in
[`background-jobs-invalidation`](background-jobs-invalidation/design.md).

## Alternative Flows

- **CadQuery/AeroSandbox missing:** five routers absent; `/health` still 200;
  registered endpoints needing the capability answer **503**. 🟢
- **A heavy router import raises `ImportError`:** logged as a warning; the rest
  of the app is unaffected. 🟢
- **A seeder raises:** WARNING; startup continues with an unseeded table. 🟢
- **`asyncio.get_running_loop()` unavailable** (a non-async test harness): the
  job tracker has no bound loop and every schedule is a no-op. 🟡
- **A subscriber raises:** logged; the publishing request succeeds. 🟢
- **A worker-thread schedule times out after 2 s:** 🟢 **fails loudly** (`R2-11`) — 2 s is extremely generous for `call_soon_threadsafe`, so expiry means the loop is gone or broken, and in that state every background job is already being swallowed.
- **A NaN from an unprotected router:** today, Starlette's
  `json.dumps(allow_nan=False)` raises → unhandled **500**; resolved once
  `NonFiniteSafeJSONResponse` is the app-wide default (Q-PC-1). 🟢
- **An `IntegrityError` that is *not* a duplicate name** (FK, NOT NULL, CHECK):
  reported as 409 with an (now English) over-general message — the wording is
  translated (Q-CC-5), the over-generalisation is not addressed. 🔴
- **A per-module `_raise_http` helper handles the exception first:** today the
  client gets `{"detail": …}` instead of the envelope; these helpers are
  deleted, so this alternative flow disappears (Q-CC-3). 🟢
- **`db/test.db` missing and `SQLALCHEMY_DATABASE_URL` unset:** SQLite creates
  the file, and `create_all`-built schemas differ subtly from migrated ones (the
  reason both seeders exist). 🟡
- **`tmp/` missing in a worktree:** `create_app()` creates it — but only at app
  creation, so a tool that writes there earlier fails. 🟡

## Dependencies

- **FastAPI / Starlette** — app, routers, `StaticFiles`, `CORSMiddleware`,
  exception handlers, Swagger helpers.
- **SQLAlchemy** — engine, `sessionmaker`, `as_declarative`, the `Engine.connect`
  event.
- **pydantic-settings** — both `Settings` classes.
- **uvicorn** — `run_app`.
- **`app/mcp_server`** — imported at module level; mounting builds the FastMCP
  server as an import side effect.
- **`app/services/*`** — imported lazily *inside* the lifespan (`cad_service`,
  `component_type_service`, `mission_objective_service`,
  `invalidation_service`, `retrim_service`, `assumption_compute_service`,
  `operating_point_generator_service`) to keep import-time cost and cycles down.
- **`app/models/avl_geometry_events`, `stability_events`** — imported for
  registration side effects only.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Probe heavy dependencies once at import and gate routers on them | `platform.py` + `main.py:37-72`; ADR 0017 | 🟢 |
| Let the API surface differ by platform rather than fail to start | conditional includes | 🟢 |
| Put the transaction boundary in the dependency, not the service | `get_db()`; ADR 0009 | 🟢 |
| `autoflush=False` — make services flush deliberately | `SessionLocal` config | 🟢 |
| WAL + 30 s busy timeout to survive multi-second write transactions | the pragma listener comment | 🟢 |
| One exception hierarchy translated by global handlers | `exceptions.py` + `main.py:274` | 🟢 |
| Serialise exceptions inside `details` rather than risk a handler crash | `_safe_json` | 🟢 |
| Render non-finite floats as `null`, never as a fabricated fallback | `json_safe.py` docstring; ADR 0012 | 🟢 |
| A broken subscriber must never break the publishing request | `EventBus.publish` | 🟢 |
| Exclude recompute outputs from recompute triggers to break the loop | `_RECOMPUTE_TRIGGERING_PARAMS`; BR-83 | 🟢 |
| Create the new debounce task **before** cancelling the old one | the ordering comment | 🟢 |
| Run CPU-bound recompute in a thread | `_recompute_wrapper` comment | 🟢 |
| Guarantee executor teardown so workers never outlive a test run | the `finally` block | 🟢 |
| `/health` always 200 so a load balancer can distinguish down from degraded | `health.py` docstring | 🟢 |
| Ship without authentication, by design; guard exposure at the launch surfaces, not with an application-level boundary | ADR 0016/0024 (Q-CC-1) | 🟢 |

## Internal State

| State | Where | Lifecycle |
|---|---|---|
| `cad_available` / `aerosandbox_available` | `lru_cache(maxsize=1)` | first call → process end |
| the five conditional router globals | `app/main.py` module scope | set at import |
| `engine`, `SessionLocal` | `app/db/session.py` | process-wide |
| `settings` × 2, `get_settings()` cache | two modules | process-wide, merging into one instance (Q-CC-4) 🟢 |
| `event_bus._handlers` | `core/events.py` | populated once in the lifespan |
| `job_tracker._jobs`, `_recompute_jobs`, `_debounce_tasks`, `_main_loop`, the two injected functions | `core/background_jobs.py` | **in-memory, per-process by permanent design** (Q-CC-8/ADR 0024), lost on restart 🟡 |

## Observability

- `logging.warning` on a failed heavy-router import, a failed seeder, and a
  non-finite replacement (with the count). 🟢
- `logger.info` for 4xx, `logger.exception` for 5xx in the global handler. 🟢
- `logger.exception` from `EventBus.publish` when a subscriber raises. 🟢
- `JobTracker` logs schedule / start / finish per job family. 🟢
- 🟢 Unstructured stdout at DEBUG by default gains a **configurable log
  level**; a file handler, JSON output and request-correlation id stay a
  **deliberate scope exclusion** (Q-PC-3), not an open gap.
- 🟢 `/health` gains a readiness signal via a new `/ready` endpoint (Alembic
  head check, `cad_available` / `aerosandbox_available` flags) plus a startup
  summary line (Q-PC-2); dependency status beyond that stays unaddressed.
- 🔴 No metrics of any kind — no request counter, no latency histogram, no job
  queue depth.

## Risks and Gaps

- 🟢 **Two `Settings` classes, three version strings** (`1.0.0`, `0.1.0`,
  `2.0.0`) merge into one class and one `pyproject.toml`-derived version
  (Q-CC-4); `/health` currently reports the one nobody else uses (G-12).
- 🔴 **CORS `allow_origins=["*"]` with `allow_credentials=True`** — invalid for
  credentialed requests, wide open otherwise; the comment shows it was copied,
  not designed. Not addressed by the interview; remains open.
- 🟢 **Unauthenticated by design, not unfinished** (Q-CC-1/ADR 0024).
  `app/core/security.py::verify_token` compares against the literal
  `"valid_token"` and has no callers; REST, `/docs`, `/static`, `/assets` and
  `/mcp` stay open — a deliberate product position for a single-user desktop
  app, guarded at the launch surfaces (loopback defaults, a startup
  reachability log line) rather than in the application. ADR 0016's framing of
  the tunnel as *the* access control is corrected; the tunnel is the
  maintainer's private testing tool.
- 🟢 **One error envelope, everywhere** (Q-CC-3) — the per-module
  `{"detail": …}` helpers are deleted.
- 🟢 **German user-facing strings translated to English** (Q-CC-5), in the two
  main.py handlers, the `PolarRejection.hint` strings, seeded
  `component_types` labels, and the `flight_profiles` docstrings.
- 🔴 **`IntegrityError → "name existiert bereits"`** (now English-language,
  Q-CC-5) still hides FK, NOT-NULL and CHECK violations behind one message —
  the over-generalisation itself was not asked and remains open.
- 🟡 **Marking dirty and publishing are not atomic** (BR-82). `Q-PC-4` fixes the related short-circuit by coalescing rather than dropping; atomicity itself was not put to the maintainer. Seven publishers
  must remember to call `mark_ops_dirty` by hand, while the handlers' log lines
  claim they did it. Not addressed by the interview; remains open.
- 🟡 **Background jobs stay in-memory and per-process** — a **permanent,
  enforced** architectural constraint (Q-CC-8/ADR 0024), asserted at startup
  (the app refuses more than one worker), not debt. 🟢 A worker-thread schedule
  can still be dropped after a 2 s timeout, silently — not addressed.
- 🟢 **`schedule_airfoil_low_re_compute` becomes a tracked `Job`** produced by a
  service, no longer importing `scripts.backfill_airfoil_low_re` from
  application code (Q-PC-5).
- 🟢 **`NonFiniteSafeJSONResponse` becomes the app-wide default response
  class** (Q-PC-1), declaring what it sanitised via a `DesignWarning`.
- 🟢 **`/health` gains a readiness signal**: a small `/ready` endpoint plus a
  startup summary (Q-PC-2).
- 🟢 **`openvsp_import` loses its `/api/v2` prefix**; all 230 routes sit at the
  application root (Q-CC-6).
- 🟢 **Logging stays deliberately minimal** (Q-PC-3): a configurable log level
  and meaningful job messages, no correlation id or metrics stack — a decided
  scope exclusion, not an open gap.
- 🟢 **There is no v1, and the references are deleted** (`R2-12`). Verified: no `api/v1`, `api_v1` or `/v1/` anywhere in `app/`. The only surviving claim was prose in the root `CLAUDE.md` and
  `app/CLAUDE.md` both describe a "legacy v1 REST surface" — the documentation
  is stale. Not addressed by the interview; remains open.
- 🟢 **`app/api/v2/endpoints/aeroplane.py` is shadowed dead code — deleted**
  (P-DEAD-0 rule 3, via `Q-AC-1`); the package `aeroplane/` wins the import.
- 🟡 **`Base`'s implicit `__tablename__`** would produce `aeroplanemodel`, so
  every model overrides it — an inherited convenience that is never used.
- 🟡 **Importing `app.main` builds the entire FastMCP server** as a side effect.
