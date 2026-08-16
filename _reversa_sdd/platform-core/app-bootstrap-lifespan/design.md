# platform-core / app-bootstrap-lifespan — Technical Design

> Use-case design. Parent module: [`../design.md`](../design.md).
> HTTP contract: [`../contracts.md`](../contracts.md).

## Interface

| Symbol | File:line | Signature |
|---|---|---|
| `setup_logging` | `logging_config.py` | `() -> None` |
| `cad_available` / `aerosandbox_available` | `core/platform.py` | `@lru_cache(maxsize=1) () -> bool` |
| `require_cad` / `require_aerosandbox` | `core/platform.py` | FastAPI dependencies raising `HTTPException(503)` |
| `create_app` | `main.py:94` | `() -> FastAPI` |
| `_combined_lifespan` | `main.py:100` | `@asynccontextmanager async (app) -> AsyncIterator[None]` |
| `run_app` | `main.py:342` | `(entry_point="app.main:app", port=8000) -> None` |
| `app` | `main.py:266` | the module-level instance |

## Main Flow

### F1 — Import 🟢

```
1  setup_logging()                                       # l.91
2  cad_available() / aerosandbox_available()             # BEFORE create_app is defined
3  five conditional router imports, each:
       if <probe>():
           try:    from app.api.v2.endpoints import X as _mod ; _X_router = _mod.router
           except ImportError as exc: logging.warning("X router unavailable: %s", exc)
4  from app.mcp_server import create_mcp_http_app         # l.73 — builds the FastMCP server
5  import app.models.avl_geometry_events   # noqa: F401 — SQLAlchemy listeners
   import app.models.stability_events      # noqa: F401
6  app = create_app()                                     # l.266
```

Steps 2–3 mean the router set is decided **at import**, so two processes running
different wheels expose different APIs. `require_cad` / `require_aerosandbox`
are *meant* to cover the other half: an endpoint that *is* registered but needs
a missing capability answers a clean **503** rather than crashing.
🟡 **[Reviewer]** In the legacy system that half is essentially unimplemented —
`require_cad` has **no** production call site and `require_aerosandbox` has
exactly one (`app/api/v2/endpoints/section_aoa.py:79`). Reproduce the intent,
not the current coverage.

### F2 — `create_app()` 🟢

```python
def create_app() -> FastAPI:
    mcp_app = create_mcp_http_app(path="/")               # FIRST

    @asynccontextmanager
    async def _combined_lifespan(app): ...                # closure over mcp_app

    app = FastAPI(title="da3dalus Model Context Protocol (v2)",
                  version="2.0.0",
                  openapi_url="/openapi.json",
                  docs_url=None,                          # custom /docs below
                  redoc_url="/redoc",
                  lifespan=_combined_lifespan)

    # ---- routers, in this exact order ----
    health, endurance,
    versioning_v2,        # ← BEFORE aeroplane_v2 (gh-914)
    aeroplane_v2,
    openvsp_import,                    # ← prefix removed; root, like the other 229 (Q-CC-6) 🟢
    components, component_types, component_tree, construction_parts,
    aeroplane_construction_plans, construction_plans, construction_templates,
    flight_profiles, fuselage_slice,
    + _cad_router / _aeroanalysis_router / _operating_points_router
      / _airfoils_router / _section_aoa_router          (each `if ... is not None`)

    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                       allow_methods=[...], allow_headers=[...])  # 🟢 narrowed to concrete origins (R2-10)

    os.makedirs("tmp", exist_ok=True)
    app.mount("/static", StaticFiles(directory="tmp"),        name="static")
    app.mount("/assets", StaticFiles(directory="app/static"), name="assets")
    app.mount("/mcp",    mcp_app)

    @app.get("/docs", include_in_schema=False) -> get_swagger_ui_html(
        openapi_url=app.openapi_url, title=f"{app.title} - Swagger UI",
        swagger_favicon_url="/assets/swagger-favicon.svg",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_ui_parameters=app.swagger_ui_parameters)
    @app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
        -> get_swagger_ui_oauth2_redirect_html()

    return app
```

The exception handlers are **not** registered here — they are module-level
decorators on the already-constructed `app` (`main.py:274-336`), which means a
second `create_app()` call in a test produces an app **without** them. 🟡

### F3 — The lifespan 🟢

```python
@asynccontextmanager
async def _combined_lifespan(app):
    # 1 + 2: idempotent seeders, each in its own session with an explicit commit
    for seeder in (seed_default_types, seed_mission_presets):
        try:
            s = SessionLocal()
            try:    seeder(s) ; s.commit()
            finally: s.close()
        except Exception as exc:            # noqa: BLE001 — never block startup on this
            logging.warning("%s at startup failed: %s", seeder.__name__, exc)

    # 3
    invalidation_service.register_handlers()

    # 4 + 5
    job_tracker.bind_loop(asyncio.get_running_loop())
    job_tracker.set_trim_function(retrim_dirty_ops)

    # 6
    def _recompute_sync(aeroplane_id: int) -> None:
        db = SessionLocal()
        try:
            ap = db.query(AeroplaneModel).filter(id == aeroplane_id).first()
            if ap is None: return
            recompute_assumptions(db, str(ap.uuid))
            db.commit()
        except: db.rollback() ; raise
        finally: db.close()

    async def _recompute_wrapper(aeroplane_id: int) -> None:
        # ASB calls are CPU-bound (~200 per recompute); on the loop they would
        # block ALL other requests.
        await asyncio.to_thread(_recompute_sync, aeroplane_id)

    job_tracker.set_recompute_function(_recompute_wrapper)

    async with mcp_app.lifespan(app):
        try:
            yield
        finally:
            await job_tracker.shutdown()
            cad_service.shutdown_executor()
            operating_point_generator_service.shutdown_opg_executor()
```

Every service import inside the lifespan is **local**, keeping import-time cost
and cycles down and letting the module import on a platform where a heavy
service cannot. 🟢

Both seeders exist because a database built with `Base.metadata.create_all` (a
dev container without Alembic) would otherwise have empty `component_types`
(gh#83) and `mission_presets` (gh-546) tables, and `GET /mission-presets` would
return `[]`. 🟢

## Alternative Flows

- **A heavy library is missing:** its router is never created; the paths **404**
  rather than 503 (the 503 path only applies to *registered* endpoints declaring
  `Depends(require_*)`). 🟡
- **A heavy router imports but raises at runtime:** unaffected by this use case;
  the global exception handler applies.
- **A seeder raises:** WARNING; the table stays as it was. 🟢
- **`asyncio.get_running_loop()` raises** (a synchronous test harness): the
  lifespan propagates, so the app fails to start. **Confirmed correct**
  (Q-PC-7): without a bound loop every background job is silently dropped, so
  intolerance here follows the same disposition rule as `Q-CC-8`'s
  single-worker assertion — *"failing loudly at boot is preferable to the
  silent, data-dependent breakage."* It is **no longer the only** intolerant
  startup step: the single-worker assertion (BR-PC47) now stands beside it. 🟢
- **`mcp_app.lifespan` raises:** startup fails; there is no fallback to running
  without MCP. 🟡
- **Shutdown while a job is `COMPUTING`:** `job_tracker.shutdown()` cancels the
  debounce tasks; an in-flight compute in a worker thread is not interruptible
  and is awaited or abandoned by process exit. 🟡
- **`create_app()` called twice** (tests): a second app is built **without** the
  module-level exception handlers, so error bodies differ. 🟡
- **`tmp/` exists as a file rather than a directory:** `os.makedirs` raises and
  startup fails. 🟡

## Dependencies

- FastAPI, Starlette (`StaticFiles`, `CORSMiddleware`), the Swagger helpers.
- `app.mcp_server.create_mcp_http_app`.
- `app.core.platform`, `app.logging_config`.
- Lazily, inside the lifespan: `cad_service`, `component_type_service`,
  `mission_objective_service`, `invalidation_service`, `retrim_service`,
  `assumption_compute_service`, `operating_point_generator_service`,
  `core.background_jobs.job_tracker`, `db.session.SessionLocal`,
  `models.aeroplanemodel.AeroplaneModel`.
- `app.models.avl_geometry_events`, `app.models.stability_events` (side effects).

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Probe capabilities at import and let the router set vary by platform | `main.py:37-72`; ADR 0017 | 🟢 |
| Guard each heavy import individually so one failure is isolated | five `try/except ImportError` blocks | 🟢 |
| Register model event listeners by importing for side effects | the two `# noqa: F401` lines | 🟢 |
| Build the MCP app first and nest its lifespan | `main.py:95`, `:186` | 🟢 |
| Order routers so a static path wins over a parameterised one | gh-914 | 🟢 |
| Create `tmp/` in code rather than requiring it in the environment | `main.py:242` | 🟢 |
| Seed idempotently at startup as a safety net for non-Alembic databases | gh#83, gh-546 | 🟢 |
| Never block startup on seeding | both `except … warning` blocks | 🟢 |
| Offload recompute to a thread and give it its own session | `_recompute_wrapper` / `_recompute_sync` | 🟢 |
| Guarantee executor teardown in a `finally` | `main.py:189-196` | 🟢 |
| Register exception handlers on the module-level app, not inside `create_app` | `main.py:274` | 🟡 (a testing trap) |

## Internal State

| State | Where | Lifecycle |
|---|---|---|
| `_cad_router`, `_aeroanalysis_router`, `_operating_points_router`, `_airfoils_router`, `_section_aoa_router` | `main.py` module globals | set at import; `None` when unavailable |
| the `lru_cache`d probe results | `core/platform.py` | first call → process end |
| `app` | `main.py:266` | one per process (plus any test-created extras) |
| the injected job-tracker functions and bound loop | `job_tracker` | set in the lifespan, cleared only by process exit |

## Observability

- `logging.warning("<name> router unavailable: %s", exc)` per failed heavy
  import. 🟢
- `logging.warning("seed_default_types at startup failed: %s", exc)` and the
  mission-preset equivalent. 🟢
- 🟢 A successful startup now logs a summary (Q-PC-2, BR-PC46): registered
  routers, detected capabilities, database URL, Alembic revision — the four
  facts an operator most needs. Previously nothing logged this.
- 🟢 `/health` stays as-is; a new `/ready` exposes the same facts (BR-PC46).

## Risks and Gaps

- 🔴 **CORS is wide open with credentials.** Not addressed by the interview —
  remains open. `/static`, `/assets`, `/docs` and `/mcp` staying unauthenticated
  is, separately, a **deliberate** product position (Q-CC-1/ADR 0024), not a
  gap.
- 🟢 **`openvsp_import` loses its `/api/v2` prefix**; all 230 routes sit at the
  root (Q-CC-6).
- 🟢 **A startup summary and a `/ready` signal now exist** (Q-PC-2) — an
  operator can tell from the outside whether CAD is available and whether the
  running schema matches Alembic head.
- 🔴 **A missing capability produces a 404, not a 503**, when the whole router is
  absent — the same failure has two different shapes depending on *why* the
  capability is missing. Not addressed by the interview.
- 🟡 **Importing `app.main` builds the entire FastMCP server** as a side effect
  of `main.py:73`. Not addressed.
- 🟡 **Exception handlers live outside `create_app()`**, so a test-created app
  behaves differently on errors. Not addressed.
- 🟢 **`bind_loop`'s intolerance is confirmed correct** (Q-PC-7) and is **no
  longer the only** intolerant startup step — the single-worker assertion
  (BR-PC47, Q-CC-8) now stands beside it.
- 🟡 **`run_app` defaults to port 8000** while the documented dev command uses
  8001 — settled by whichever class wins `Q-CC-4`'s one-class-one-instance
  merge, not by this use case; which port that merge should pick was not
  asked.
