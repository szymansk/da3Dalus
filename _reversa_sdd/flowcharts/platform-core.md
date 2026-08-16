# Flowcharts — platform-core

## 1. Application composition (`create_app`, `app/main.py:94`)

```mermaid
flowchart TD
    A["import app.main"] --> B["setup_logging() — module level, before anything else"]
    B --> C["capability probes at IMPORT time"]
    C --> C1{"cad_available()?"}
    C1 -- yes --> C2["import endpoints.cad → _cad_router"]
    C1 -- no --> C3["_cad_router stays None"]
    C --> D1{"aerosandbox_available()?"}
    D1 -- yes --> D2["import aeroanalysis, operating_points,<br/>airfoils, section_aoa routers"]
    D1 -- no --> D3["those 4 routers stay None"]

    C2 --> E["event-listener modules imported for side effects:<br/>models.avl_geometry_events · models.stability_events"]
    D2 --> E
    C3 --> E
    D3 --> E

    E --> F["create_app()"]
    F --> G["mcp_app = create_mcp_http_app(path='/')"]
    G --> H["FastAPI(title='da3dalus Model Context Protocol (v2)',<br/>version='2.0.0', docs_url=None, redoc_url='/redoc',<br/>lifespan=_combined_lifespan)"]
    H --> I["include_router × 15 unconditional<br/>+ up to 5 capability-gated"]
    I --> J["CORSMiddleware(allow_origins=['*'],<br/>allow_credentials=True, allow_methods=['*'], allow_headers=['*'])"]
    J --> K["os.makedirs('tmp', exist_ok=True)"]
    K --> L["mount /static → tmp/ · /assets → app/static · /mcp → mcp_app"]
    L --> M["custom /docs (Swagger with project favicon) + oauth2 redirect"]
    M --> N["app = create_app()"]
    N --> O["register 3 exception handlers<br/>ServiceException · IntegrityError · RequestValidationError"]
```

Router order matters once: `versioning_v2.router` is included **before**
`aeroplane_v2.router` so the static path `/aeroplanes/compare` wins over the
dynamic `/aeroplanes/{aeroplane_id}` (gh-914).

## 2. Lifespan — startup and shutdown

```mermaid
sequenceDiagram
    autonumber
    participant U as uvicorn
    participant L as _combined_lifespan
    participant DB as SessionLocal
    participant JT as job_tracker
    participant M as mcp_app.lifespan

    U->>L: enter
    L->>DB: seed_default_types(session) + commit
    Note over L: wrapped in try/except — a failure only logs a WARNING,<br/>startup never blocks (gh#83)
    L->>DB: seed_mission_presets(session) + commit
    Note over L: same never-block contract (gh-546)
    L->>L: invalidation_service.register_handlers()
    L->>JT: bind_loop(asyncio.get_running_loop())
    L->>JT: set_trim_function(retrim_dirty_ops)
    L->>JT: set_recompute_function(_recompute_wrapper)
    Note over L,JT: _recompute_wrapper = asyncio.to_thread(_recompute_sync)<br/>_recompute_sync owns its OWN session and commits itself
    L->>M: async with mcp_app.lifespan(app)
    M-->>U: application serving
    U->>L: shutdown
    L->>JT: await job_tracker.shutdown()
    L->>L: cad_service.shutdown_executor()
    L->>L: operating_point_generator_service.shutdown_opg_executor()
```

## 3. Transaction ownership — the single most repeated invariant

```mermaid
flowchart TD
    A["request hits a v2 endpoint"] --> B["Depends(get_db)"]
    B --> C["db = SessionLocal()"]
    C --> D["yield db → endpoint → service → models"]
    D -- "returns normally" --> E["db.commit()"]
    D -- "raises" --> F["db.rollback(); re-raise"]
    E --> G["finally: db.close()"]
    F --> G

    subgraph RULE["service-layer contract"]
        R1["services may db.add / db.flush / db.expire_all / db.expunge_all"]
        R2["services must NOT db.commit() or db.begin()"]
    end

    subgraph EXCEPTIONS["paths that own their own session"]
        X1["lifespan seeders — SessionLocal() + explicit commit"]
        X2["_recompute_sync — SessionLocal() + commit/rollback/close"]
        X3["JobTracker._run_backfill_for_names — with SessionLocal() + commit"]
        X4["MCP _call_endpoint — with SessionLocal(), NEVER commits"]
    end
```

## 4. Error translation

```mermaid
flowchart TD
    subgraph HIER["app/core/exceptions.py"]
        SE["ServiceException(message, details)"]
        NF["NotFoundError(entity, resource_id)"]
        VE["ValidationError"]
        VD["ValidationDomainError(ValidationError)"]
        CE["ConflictError"]
        IE["InternalError"]
        SE --- NF
        SE --- VE
        VE --- VD
        SE --- CE
        SE --- IE
    end

    NF --> H404["404 · code 'not_found' · log INFO"]
    VE --> H422["422 · code 'validation_error' · log INFO"]
    VD --> H422
    CE --> H409["409 · code 'conflict' · log INFO"]
    IE --> H500["500 · code 'internal_error' · log EXCEPTION"]
    SE --> H500b["500 · code 'service_error' · log EXCEPTION"]

    IEX["sqlalchemy IntegrityError"] --> H409b["409 · message 'name existiert bereits' (German!)"]
    RVE["RequestValidationError"] --> H422b["422 · message 'Ungültige Eingabedaten' (German!)"]

    H404 --> BODY["{'error': {'code', 'message', 'details'}}"]
    H422 --> BODY
    H409 --> BODY
    H500 --> BODY
    H409b --> BODY
    H422b --> BODY
```

`details` is passed through `jsonable_encoder(..., custom_encoder={BaseException: str})`
so an exception stored in `details` serialises instead of crashing the handler.

## 5. Configuration — two independent Settings classes

```mermaid
flowchart TD
    ENV[".env (SettingsConfigDict(env_file='.env', extra='ignore'))"]

    subgraph A["app/core/config.py :: Settings — singleton 'settings'"]
        A1["PROJECT_NAME · VERSION · UVICORN_HOST"]
        A2["ARTIFACTS_BASE_DIR (field_validator → .resolve())"]
        A3["COPILOT_API_KEY (SecretStr) · COPILOT_BASE_URL"]
        A4["COPILOT_MODEL · COPILOT_EMBEDDING_MODEL"]
        A5["module constants REPO_ROOT, AIRFOILS_DIR (absolute, CWD-independent)"]
    end

    subgraph B["app/settings.py :: Settings — singleton 'settings' + lru_cache get_settings()"]
        B1["base_url · openai_api_key · version"]
        B2["low_re_* (13 fields) + _DEFAULT_LOW_RE_GRID + _DEFAULT_MISSION_WEIGHTS"]
    end

    subgraph C["bare os.getenv — outside both"]
        C1["SQLALCHEMY_DATABASE_URL (app/db/session.py:8)"]
        C2["LOG_LEVEL (app/logging_config.py:7)"]
        C3["DISPLAY_CONSTRUCTION_STEP · BLAS thread vars"]
    end

    ENV --> A
    ENV --> B

    A --> USE1["copilot_service · openvsp_* · artifact_service<br/>create_wing_configuration · main.run_app"]
    B --> USE2["mcp_server · health · cad · airfoils · aeroanalysis<br/>suitability_service · airfoil_low_re_service · background_jobs"]
```

Two classes both named `Settings`, both exporting a module-level `settings`,
both reading the same `.env`, with **disjoint fields** and different version
strings (`VERSION = "1.0.0"` vs `version = "0.1.0"`; `/health` reports the
latter). See `questions.md` — platform-core.

## 6. Platform capability guard

```mermaid
flowchart TD
    A["@lru_cache(maxsize=1) cad_available()"] --> B{"import cadquery"}
    B -- ok --> C["True"]
    B -- ImportError --> D["False"]
    C --> E["main.py registers the cad router"]
    D --> F["router not registered → 404 on those paths"]
    C --> G["Depends(require_cad) passes"]
    D --> H["require_cad → HTTP 503<br/>'CAD backend (CadQuery) is not available on this platform.'"]
```

Identical shape for `aerosandbox_available()` / `require_aerosandbox()`. The
probes are cached for the life of the process — a broken install detected once
stays broken.

## 7. Invalidation and background jobs

```mermaid
flowchart TD
    subgraph PUB["publishers (SQLAlchemy events + services)"]
        G1["WingModel / WingXSecModel / FuselageModel change"]
        A1["design assumption change"]
    end

    G1 -->|"GeometryChanged(aeroplane_id, source_model)"| BUS["event_bus (in-process, synchronous)"]
    A1 -->|"AssumptionChanged(aeroplane_id, parameter_name)"| BUS

    BUS --> H1["_on_geometry_changed → schedule_retrim"]
    BUS --> H2["_on_geometry_changed_recompute_assumptions → schedule_recompute_assumptions"]
    BUS --> H3["_on_assumption_changed<br/>only if param in {mass, cg_x} → schedule_retrim"]
    BUS --> H4["_on_assumption_changed_recompute<br/>only if param in {target_static_margin, mass}<br/>→ schedule_recompute_assumptions"]

    H1 --> JT["JobTracker (module singleton)"]
    H2 --> JT
    H3 --> JT
    H4 --> JT
```

`EventBus.publish` wraps every handler in try/except and only logs on failure —
a broken subscriber can never break the publishing request.

### Debounce state machine

```mermaid
stateDiagram-v2
    [*] --> DEBOUNCING: schedule_*(aeroplane_id)
    DEBOUNCING --> DEBOUNCING: re-scheduled — new task created FIRST,<br/>then the old one is cancelled
    DEBOUNCING --> COMPUTING: after debounce_seconds (2.0)
    COMPUTING --> DONE: handler returned
    COMPUTING --> FAILED: handler raised (error recorded)
    COMPUTING --> FAILED: server shutdown
    DONE --> [*]
    FAILED --> [*]
```

`schedule_retrim` additionally short-circuits while a job is already
`COMPUTING`. `schedule_recompute_assumptions` does **not** — it cancels and
re-debounces regardless.

### Cross-thread scheduling (`_create_task_safe`)

```mermaid
flowchart TD
    A["_create_task_safe(coro)"] --> B{"asyncio.get_running_loop() succeeds?"}
    B -- yes --> C["running.create_task(coro) → Task"]
    B -- "RuntimeError (worker thread)" --> D{"_main_loop bound?"}
    D -- no --> E["log DEBUG, return None → schedule silently DROPPED"]
    D -- yes --> F["threading.Event + call_soon_threadsafe(_make_task)"]
    F --> G["ready.wait(timeout=2.0)"]
    G --> H["return result['task'] (may be None on timeout)"]
```

The create-before-cancel ordering in both `schedule_*` methods exists precisely
because this can return `None`: cancelling first would strand the job in
`DEBOUNCING` with no task to fire it.

## 8. Non-finite float safety on the JSON boundary

```mermaid
flowchart LR
    A["solver output (AeroBuildup, NeuralFoil)"] --> B{"NaN / ±Inf present?"}
    B -- yes --> C["NonFiniteSafeJSONResponse.render → _sanitize"]
    C --> D["value → null, counter++"]
    D --> E["log WARNING with the replacement count"]
    B -- no --> F["normal render"]
    E --> G["valid JSON"]
    F --> G

    B -.->|"plain JSONResponse"| X["json.dumps(allow_nan=False)<br/>ValueError → unhandled HTTP 500"]
```

`null` is chosen deliberately as an honest "no value" — never a fabricated
fallback number that would hide the degenerate geometry upstream.

## 9. Database engine bootstrap

```mermaid
flowchart TD
    A["SQLALCHEMY_DATABASE_URL = os.getenv(..., 'sqlite:///./db/test.db')"] --> B{"startswith 'sqlite'?"}
    B -- yes --> C["connect_args = {check_same_thread: False, timeout: 30}"]
    B -- no --> D["no extra kwargs (PostgreSQL)"]
    C --> E["create_engine"]
    D --> E
    E --> F["SessionLocal = sessionmaker(expire_on_commit=False,<br/>autocommit=False, autoflush=False)"]
    B -- yes --> G["@event.listens_for(Engine, 'connect') _set_sqlite_pragmas"]
    G --> H["PRAGMA journal_mode=WAL<br/>PRAGMA synchronous=NORMAL<br/>PRAGMA busy_timeout=30000"]
```

`check_same_thread=False` is required because `asyncio.to_thread` workers use
the session across threads; WAL + `busy_timeout` exist because the assumption
recompute holds a write transaction open for several seconds while AeroBuildup
runs.

`Base` (`app/db/base.py`) is 11 lines: a declarative base with an implicit
`id = Column(Integer, primary_key=True, index=True)` and a `__tablename__`
derived from `cls.__name__.lower()` — which is why almost every model
overrides `__tablename__` explicitly.
