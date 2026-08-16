# platform-core / app-bootstrap-lifespan — Implementation Tasks

> Parent module task list: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] FastAPI, Starlette, uvicorn.
- [ ] `app/mcp_server.create_mcp_http_app`.
- [ ] `job_tracker`, `invalidation_service`, `retrim_service`,
      `assumption_compute_service`, `cad_service`,
      `operating_point_generator_service`.
- [ ] `seed_default_types` (gh#83) and `seed_mission_presets` (gh-546).
- [ ] `app/static/` (the Swagger favicon) and a writable working directory for
      `tmp/`.

## Tasks

- [ ] **T-01 — `setup_logging()` called at import.**
  - Legacy origin: `app/logging_config.py`, invoked at `app/main.py:91`
  - Definition of done: the call happens before any other module-level code that
    can log — otherwise the first warnings of a failed router import are lost.
  - Confidence: 🟢

- [ ] **T-02 — Capability probes.**
  `cad_available()` / `aerosandbox_available()` as `@lru_cache(maxsize=1)`;
  `require_cad` / `require_aerosandbox` raising `HTTPException(503, <message>)`.
  - Legacy origin: `app/core/platform.py` (67 l.); ADR 0017
  - Definition of done: the import attempt happens once per process. Carry the
    rationale — *"a broken install detected once stays broken for the life of the
    process"*.
  - Confidence: 🟢

- [ ] **T-03 — Conditional heavy-router imports.**
  Five module-level `None` globals; `if cad_available(): try: … except
  ImportError: logging.warning(...)`; likewise the four AeroSandbox routers.
  - Legacy origin: `app/main.py:31-72`
  - Definition of done: with one module patched to raise, only that router is
    `None` and a warning names it.
  - Confidence: 🟢

- [ ] **T-04 — Side-effect listener imports.**
  `import app.models.avl_geometry_events  # noqa: F401` and
  `import app.models.stability_events  # noqa: F401`.
  - Legacy origin: `app/main.py:84-85`
  - Definition of done: the listeners are registered before the first request.
    Keep the `# noqa` and the explanatory comment — a linter "cleanup" that
    removes these imports silently disables stability/AVL invalidation.
  - Confidence: 🟢

- [ ] **T-05 — `create_app()` skeleton.**
  Build `mcp_app` first, then `FastAPI(title="da3dalus Model Context Protocol
  (v2)", version="2.0.0", openapi_url="/openapi.json", docs_url=None,
  redoc_url="/redoc", lifespan=_combined_lifespan)`.
  - Legacy origin: `app/main.py:94-205`
  - Definition of done: `docs_url=None` is intentional — the custom `/docs`
    route (T-08) replaces it.
  - Confidence: 🟢

- [ ] **T-06 — Router includes in the legacy order, `openvsp_import` unprefixed
  (Q-CC-6).**
  `health`, `endurance`, **`versioning`**, `aeroplane`, `openvsp_import`
  (**no** `/api/v2` prefix — the root, like every other router), `components`,
  `component_types`, `component_tree`, `construction_parts`,
  `aeroplane_construction_plans`, `construction_plans`,
  `construction_templates`, `flight_profiles`, `fuselage_slice`, then the five
  conditional routers.
  - Legacy origin: `app/main.py:206-231`
  - Definition of done: a test proves `/aeroplanes/compare` resolves to the
    versioning handler (gh-914). Carry the comment stating why the order
    matters. `openvsp_import` answers at `/import/openvsp`, not
    `/api/v2/import/openvsp` — this must land before a generated TypeScript
    client (`Q-CC-11`) bakes the old shape in.
  - Confidence: 🟢

- [ ] **T-07 — CORS.**
  `allow_origins=["*"]`, `allow_credentials=True`, `allow_methods=["*"]`,
  `allow_headers=["*"]`.
  - Legacy origin: `app/main.py:233-239`
  - Definition of done: reproduced **with its inline comment**, and recorded as
    a gap — wildcard origin plus credentials is invalid for credentialed
    requests, and it exists only because the frontend calls the API directly
    from the browser.
  - Confidence: 🟢

- [ ] **T-08 — `tmp/`, the three mounts and the custom docs.**
  `os.makedirs("tmp", exist_ok=True)`; mount `/static → tmp/`,
  `/assets → app/static`, `/mcp → mcp_app`; add `GET /docs` (with
  `swagger_favicon_url="/assets/swagger-favicon.svg"`) and the Swagger OAuth2
  redirect route, both `include_in_schema=False`.
  - Legacy origin: `app/main.py:241-261`
  - Definition of done: a fresh worktree with no `tmp/` starts successfully —
    this is the concrete reason `.claude/rules/worktree-setup.md` exists.
  - Confidence: 🟢

- [ ] **T-09 — The two seeders in the lifespan.**
  Each in its own `SessionLocal` with an explicit `commit()` in a `try/finally`,
  the whole thing wrapped in `except Exception → logging.warning`.
  - Legacy origin: `app/main.py:107-140`
  - Definition of done: idempotent (only missing names inserted); a raising
    seeder logs a WARNING and startup continues. Carry both comments (gh#83 and
    gh-546) explaining that a `create_all`-built database needs this safety net.
  - Confidence: 🟢

- [ ] **T-10 — Invalidation registration and job-tracker wiring.**
  `register_handlers()`; `job_tracker.bind_loop(asyncio.get_running_loop())`;
  `set_trim_function(retrim_dirty_ops)`.
  - Legacy origin: `app/main.py:142-155`
  - Definition of done: without `bind_loop`, every subsequent schedule is
    silently dropped — assert the loop is bound after startup.
  - Confidence: 🟢

- [ ] **T-11 — `_recompute_sync` + `_recompute_wrapper`.**
  The sync function owns its session and commits/rolls back; the async wrapper
  is `await asyncio.to_thread(_recompute_sync, aeroplane_id)`.
  - Legacy origin: `app/main.py:163-184`
  - Definition of done: a recompute runs off the event loop. Carry the comment —
    ~200 CPU-bound ASB calls per recompute would block all other requests. This
    is one of the four legitimate own-session paths under ADR 0009.
  - Confidence: 🟢

- [ ] **T-12 — Nested MCP lifespan and teardown.**
  `async with mcp_app.lifespan(app): try: yield finally: await
  job_tracker.shutdown(); cad_service.shutdown_executor();
  shutdown_opg_executor()`.
  - Legacy origin: `app/main.py:186-196`
  - Definition of done: after shutdown no `ProcessPoolExecutor` worker remains —
    assert it, because a leaked worker breaks the *next* test run rather than
    this one.
  - Confidence: 🟢

- [ ] **T-13 — `run_app`.**
  `uvicorn.run(entry_point, host=settings.UVICORN_HOST, port=port,
  reload=True)`.
  - Legacy origin: `app/main.py:342-349`
  - Definition of done: reproduced; note the default `port=8000` versus the
    documented dev port 8001.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Probe caching:** one import attempt per process.
- [ ] **TT-02 — Import isolation:** one failing heavy module leaves the others
      registered and logs a warning.
- [ ] **TT-03 — Listener registration:** both SQLAlchemy listener modules
      active.
- [ ] **TT-04 — Route order:** `/aeroplanes/compare` reaches the versioning
      handler.
- [ ] **TT-05 — CAD-less start:** app starts, `/health` 200, CAD routes absent.
- [ ] **TT-06 — 503 guard:** a registered endpoint declaring `require_*` with
      the capability unavailable returns 503.
- [ ] **TT-07 — `tmp/` creation:** starts from a checkout without `tmp/`.
- [ ] **TT-08 — Mounts:** `/static`, `/assets`, `/mcp` all resolve.
- [ ] **TT-09 — Custom docs:** `/docs` renders with the project favicon.
- [ ] **TT-10 — Lifespan wiring:** all six steps observable after startup.
- [ ] **TT-11 — Idempotent seeding:** a second startup creates no duplicates.
- [ ] **TT-12 — Seeder failure:** WARNING + successful startup.
- [ ] **TT-13 — Threaded recompute:** runs off the loop.
- [ ] **TT-14 — Teardown:** job tracker shut down, both executors closed, no
      surviving worker.
- [ ] **TT-15 — Nested MCP lifespan:** MCP startup and shutdown observed inside
      the app's.

## Suggested Order

1. **T-01 → T-02** logging and probes: everything below either logs or branches
   on a probe.
2. **T-03 → T-04** the conditional imports and the two side-effect imports.
3. **T-05 → T-08** app construction. Write TT-04 (route order) **before** T-06 —
   the gh-914 shadowing bug is invisible unless the test exists first.
4. **T-09 → T-11** the lifespan body, seeders first (they are independent), then
   the job-tracker wiring, then the recompute closure.
5. **T-12** nesting and teardown, with TT-14 asserting no surviving worker.
6. **T-13** the runner.

## Decided by the specification validation interview (2026-08-13 → 15)

- **Startup logs a summary** — registered routers, detected capabilities,
  database URL, Alembic revision (Q-PC-2, BR-PC46). New task: **T-18**.
- **A new `GET /ready`** reports Alembic-head agreement plus the capability
  flags; `/health` is unchanged (Q-PC-2, BR-PC46). New task: **T-18**.
- **Single-worker operation is asserted at startup** — the app refuses to start
  with more than one worker (Q-CC-8/ADR 0024, BR-PC47). New task: **T-19**.
- **An exposure guard replaces application-level auth**: drop `--host 0.0.0.0`
  from the documented dev command; Docker publishes to `127.0.0.1` only; a
  startup log line states the effective reachability and warns on a
  non-loopback bind without `ALLOW_PUBLIC_BIND` (Q-CC-1/ADR 0024, BR-PC48). New
  task: **T-20**.
- **`openvsp_import` loses its `/api/v2` prefix** — all 230 routes sit at the
  application root (Q-CC-6, BR-PC2). Update to **T-06**.
- **`bind_loop`'s intolerance is confirmed correct**, and is no longer the
  only intolerant startup step — the single-worker assertion (T-19) now stands
  beside it (Q-PC-7).

New tasks:

- [ ] **T-18 — Startup summary + `GET /ready`.**
  Log registered routers, detected capabilities, database URL and the Alembic
  revision at the end of the lifespan's startup steps; add `GET /ready`
  returning schema agreement (running revision vs head) and the capability
  flags.
  - Legacy origin: — (new, Q-PC-2)
  - Definition of done: after a migration-bearing merge without
    `alembic upgrade head`, `/ready` reports the mismatch; `/health` keeps its
    always-200 semantics unchanged.
  - Confidence: 🟢 (decided; implementation detail)

- [ ] **T-19 — Single-worker startup assertion.**
  Refuse to start when configured with more than one worker.
  - Legacy origin: — (new, Q-CC-8/ADR 0024)
  - Definition of done: a multi-worker configuration fails fast at boot with an
    explanatory message, rather than degrading silently at runtime.
  - Confidence: 🟢 (decided; implementation detail)

- [ ] **T-20 — Exposure guard.**
  Drop `--host 0.0.0.0` from the documented dev command; Docker publishes to
  `127.0.0.1` only (`--host 0.0.0.0` stays mandatory inside the container); log
  the effective reachability at startup and warn on a non-loopback bind absent
  an explicit `ALLOW_PUBLIC_BIND` opt-in.
  - Legacy origin: — (new, Q-CC-1/ADR 0024)
  - Definition of done: the default dev/Docker configuration binds/publishes to
    loopback only; a deliberate public bind still works and is logged loudly.
  - Confidence: 🟢 (decided; implementation detail)

## Pending Gaps — not addressed by the interview

- **Should an absent capability 503 instead of 404?** Today the same missing
  library produces a 404 (router absent) or a 503 (router present, dependency
  raises) depending on how the endpoint was written.
- **Should the exception handlers move inside `create_app()`** so a
  test-constructed app behaves identically?
- **Should the CORS policy be narrowed** once the direct browser → FastAPI
  topology is acknowledged?
- **Should `run_app`'s default port match the documented 8001?** Deferred to
  whichever class wins `Q-CC-4`'s merge; the port itself was not decided.
- **Should importing `app.main` build the FastMCP server**, or should that be
  deferred to `create_app()`?
