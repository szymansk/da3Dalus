# platform-core — Cross-cutting HTTP Contract

> This module publishes almost no domain routes of its own. What it publishes is
> the **frame every other module's routes live inside**: the app, its lifespan,
> its mounts, its CORS policy, its error envelope and its transaction
> guarantee. 🟢
> Read from `app/main.py`, `app/db/session.py`, `app/core/exceptions.py`,
> `app/core/json_safe.py`, `app/core/platform.py` and
> `app/api/v2/endpoints/health.py`.

## The application object 🟢

| | |
|---|---|
| Title | `da3dalus Model Context Protocol (v2)` |
| Version | `2.0.0` today; one source, derived from `pyproject.toml` (Q-CC-4) — see §Configuration |
| `openapi_url` | `/openapi.json` |
| `docs_url` | `None` — replaced by a custom `/docs` route |
| `redoc_url` | `/redoc` |
| `lifespan` | `_combined_lifespan` |
| Default listen | documented dev command **drops `--host 0.0.0.0`** (uvicorn's own default is already `127.0.0.1`, Q-CC-1/ADR 0024); `run_app` uses `settings.UVICORN_HOST` and port **8000** while the documented dev port is 8001 🟡 (unaddressed by the interview — settled by whichever class wins Q-CC-4's merge) |

## Routing contract 🟢

| Router | Prefix | Tags |
|---|---|---|
| `health` | `""` | `health` |
| `endurance` | `""` | `endurance` |
| **`versioning`** | `""` | `versioning` — **included before `aeroplane`** (gh-914) |
| `aeroplane` (24 aggregated sub-routers) | `""` | — |
| **`openvsp_import`** | *(none)* | `import` — loses its `/api/v2` prefix; all 230 routes sit at the root (Q-CC-6) 🟢 |
| `components`, `component_types`, `component_tree` | `""` | respective |
| `construction_parts`, `aeroplane_construction_plans`, `construction_plans`, `construction_templates` | `""` | `construction-*` |
| `flight_profiles`, `fuselage_slice` | `""` | respective |
| `cad` | `""` | only when `cad_available()` |
| `aeroanalysis`, `operating_points`, `airfoils`, `section_aoa` | `""` | only when `aerosandbox_available()` |

Two ordering facts are **load-bearing**:

1. `versioning` before `aeroplane`, so the static path `/aeroplanes/compare`
   matches ahead of `/aeroplanes/{aeroplane_id}` (gh-914). Reversing them
   silently routes `compare` into the by-id handler.
2. `openvsp_import` carried `/api/v2` while everything else was at the root —
   `/aeroplanes/...` vs `/api/v2/import/...`. **Resolved: the outlier is
   aligned to the root** (Q-CC-6), not the reverse, because lifting 229 routes
   would touch every route and all 48 SWR hooks for no benefit; this must land
   before `Q-CC-11`'s generated TypeScript client, or the inconsistency is
   baked into generated code. 🟢

Total ≈ **230 route decorators**.

### Platform-dependent surface 🟢 (ADR 0017)

On a platform where `cadquery` / `aerosandbox` cannot be imported (e.g.
`linux/aarch64`, excluded by `pyproject.toml` env markers), **the affected
routers do not exist** — their paths 404 rather than 503.

🟡 **[Reviewer] The 503 fallback covers one route, not the surface.**
`require_cad` / `require_aerosandbox` exist and behave as documented, but
`require_cad` has **no** production call site and `require_aerosandbox` has
exactly one (`app/api/v2/endpoints/section_aoa.py:79`). Treat the clean 503 as
the *intended* contract for a re-implementation, not as observed behaviour of
the legacy system: today a registered endpoint that hits a missing heavy
dependency raises `ImportError` → **500**.

Consequence for any client: the OpenAPI document is **not** a constant. It
describes the surface of the process that served it.

## CORS contract 🟢 (`R2-10`)

**`allow_origins` is narrowed to concrete origins** — the dev frontend and the ngrok
domain — held in the merged `Settings` class (`Q-CC-4`), not as a literal in `main.py`.
ADR 0024's *"the tunnel is the boundary"* covers **inbound** access; CORS governs which
**other websites** a browser lets read the API's responses, and with `"*"` any page the
browser visits could call it while the tunnel is up, with the proxy session riding along.
`Q-FW-1` (SPA-direct **is** the architecture) means there is exactly one legitimate origin
per environment. Note: with `allow_origins=["*"]` the browser **ignores**
`allow_credentials`, so today's config is less exposed than it reads — narrowing makes
that flag meaningful again and it must then be set deliberately.

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # "copied from other python backends to resolve the cors origin problem"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Wildcard origin combined with `allow_credentials=True` is **rejected by browsers
for credentialed requests** and wide open for everything else. It exists because
the frontend calls the API directly from the browser with no server-side proxy
(see [`../frontend-workbench/contracts.md`](../frontend-workbench/contracts.md)),
contradicting `frontend/CLAUDE.md`'s claim that route handlers avoid CORS.

## Static mounts 🟢

| Path | Target | Note |
|---|---|---|
| `/static` | `tmp/` | `os.makedirs("tmp", exist_ok=True)` at app creation — a worktree must have `tmp/` |
| `/assets` | `app/static` | Swagger favicon |
| `/mcp` | the FastMCP ASGI app | lifespan nested in `_combined_lifespan` |
| `/docs` | custom Swagger HTML | `swagger_favicon_url="/assets/swagger-favicon.svg"` |
| `/redoc`, `/openapi.json` | FastAPI defaults | |

All three mounts are **unauthenticated, by design** (Q-CC-1/ADR 0024) — a
single-user desktop application has no per-object ownership to enforce — so
anything written under `tmp/`, including MCP assets and CAD exports, is
readable by anyone who can reach the port. The exposure guard lives at the
launch surfaces, not here: the documented dev command drops `--host 0.0.0.0`,
Docker publishes to `127.0.0.1` only, and a startup log line states the
effective reachability. 🟢

## Lifespan contract 🟢

Before `yield`:

| # | Step | Failure mode |
|---|---|---|
| 1 | `seed_default_types` (gh#83) — 9 component types, own session + commit | WARNING only |
| 2 | `seed_mission_presets` (gh-546) — 6 presets, own session + commit | WARNING only |
| 3 | `invalidation_service.register_handlers()` | propagates |
| 4 | `job_tracker.bind_loop(asyncio.get_running_loop())` | propagates |
| 5 | `job_tracker.set_trim_function(retrim_dirty_ops)` | propagates |
| 6 | `job_tracker.set_recompute_function(_recompute_wrapper)` | propagates |

Then `async with mcp_app.lifespan(app): yield`.

After `yield` (in `finally`, always):

```
await job_tracker.shutdown()
cad_service.shutdown_executor()
operating_point_generator_service.shutdown_opg_executor()
```

so `ProcessPoolExecutor` workers never outlive the server **or a test run**.

Both seeders are idempotent — they insert only rows whose `name` is not already
present — because a database built with `Base.metadata.create_all` (a dev
container without Alembic) would otherwise have empty `component_types` and
`mission_presets` tables.

## Transaction contract 🟢 (ADR 0009, BR-78)

```python
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
        db.commit()          # on success
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

**The rule every service is written against:** services call `db.add()` /
`db.flush()` and **never** `db.commit()` or `db.begin()`.

| Session option | Value | Why |
|---|---|---|
| `expire_on_commit` | `False` | ORM objects stay usable after commit |
| `autocommit` | `False` | |
| `autoflush` | **`False`** | services must `db.flush()` explicitly before a dependent query — this is why `flush()` appears throughout the version and copilot services |

SQLite specifics:

| Setting | Value | Why |
|---|---|---|
| `connect_args.check_same_thread` | `False` | `asyncio.to_thread` workers cross threads |
| `connect_args.timeout` | `30` s | block rather than fail on a locked DB |
| `PRAGMA journal_mode` | `WAL` | the assumption recompute holds a write transaction for several seconds while AeroBuildup runs |
| `PRAGMA synchronous` | `NORMAL` | |
| `PRAGMA busy_timeout` | `30000` ms | |

Legitimate exceptions that own their own session and commit: the two lifespan
seeders, `_recompute_sync`, and `JobTracker._run_backfill_for_names`.
🟢 **The `mcp_server._call_endpoint` transaction boundary is fixed** (`Q-MC-1`) — the bare session was why ~40 write tools persisted nothing. Previously an illegitimate exception:
`SessionLocal()` and never commits, so **every MCP write is rolled back**
(TD-01, owned by `mcp-server`). `Q-CC-1`/ADR 0024 makes fixing it **safe**: with
loopback defaults the ~40 destructive MCP tools are not reachable off-box, so
repairing the transaction boundary reverts to an ordinary bug fix rather than a
security decision — but the fix itself is out of this module's scope.

🟡 **A streaming endpoint holds the session for the whole response.** The assistant row is committed in its own session at `done` (`Q-CO-4`); the session hold itself was accepted as single-user behaviour (ADR 0024). The
copilot SSE turn commits only after the generator is fully consumed; a client
disconnect loses the turn.

`SQLALCHEMY_DATABASE_URL` is read with a bare `os.getenv` (default
`sqlite:///./db/test.db`), bypassing both `Settings` classes today; it folds
into the merged `Settings` (Q-CC-4), remaining a bare `os.getenv` only if
verified to be a genuine Alembic bootstrap exception. 🟢

## Error contract 🟢

### The envelope

```json
{"error": {"code": "...", "message": "...", "details": ... | null}}
```

| Exception | HTTP | `code` | Log level |
|---|---|---|---|
| `NotFoundError` | 404 | `not_found` | `info` |
| `ValidationError` / `ValidationDomainError` | 422 | `validation_error` | `info` |
| `ConflictError` | 409 | `conflict` | `info` |
| `InternalError` | 500 | `internal_error` | `exception` |
| bare `ServiceException` | 500 | `service_error` | `exception` |
| `sqlalchemy.exc.IntegrityError` | 409 | `conflict` | — |
| `RequestValidationError` | 422 | `validation_error` | — |

`details` passes through
`jsonable_encoder(..., custom_encoder={BaseException: str})`, so an exception
object stored in `details` serialises instead of crashing the handler.
`NotFoundError(entity="Wing", resource_id=7)` builds the message
`"Wing not found"` and `details = {"id": "7", "entity": "Wing"}`.

### Two divergences — both resolved

1. **German messages — translated to English (Q-CC-5).** `IntegrityError →
   409` and `RequestValidationError → 422` get English messages, consistent
   with the project's English-only UI rule; accepted as client-visible because
   there are no external API consumers (Q-CC-1). 🟢 🔴 **Still open:**
   `IntegrityError` still assumes *every* integrity violation is a duplicate
   name, hiding FK, NOT-NULL and CHECK violations — the over-generalisation
   itself was not asked.
2. **A second, incompatible shape — deleted (Q-CC-3).** 🟢 Several endpoint
   modules (`versioning.py`, `copilot_history.py`, five distinct mappers in
   `mission-and-sizing`, and others in `mass-and-balance`, `ai-copilot`,
   `construction-plans`) defined local `_raise_http` + `_call` helpers
   producing FastAPI's `{"detail": …}`. These are **deleted**; every response
   goes through the one envelope. The deliberate 422 that `matching_chart.py` /
   `field_lengths.py` signalled via a bare `ServiceException` becomes the named
   `ValidationDomainError` type instead.

## Response-rendering contract 🟢

`NonFiniteSafeJSONResponse` (`app/core/json_safe.py`):

| Value | Rendered as |
|---|---|
| finite `float` / `np.floating` | the number (numpy → native `float`) |
| `NaN`, `+Inf`, `−Inf` (Python **or** numpy) | `null` + one WARNING with the total replacement count |
| `bool` | unchanged (checked **before** `float`) |
| `tuple` | normalised to a JSON array |
| everything else | unchanged |

Rationale (module docstring): `null` is *"an honest 'no value', never a
fabricated fallback number that would hide the underlying design problem"*
(ADR 0012).

Today it is set as `default_response_class` on **exactly one** router
(`aeroanalysis.py:43`); `operating_points`, `section_aoa`, `airfoils`, the
powertrain and speed-polar routers all return solver numbers through the plain
`JSONResponse` and can still produce an unhandled **500**, because Starlette
renders with `json.dumps(allow_nan=False)`. **Resolved:** it becomes the
app-wide `default_response_class` (Q-PC-1), additionally attaching a
`DesignWarning` (`code: NON_FINITE_VALUE`) naming the sanitised JSON paths —
this is *more* honest than the status quo, not less: a 500 destroys the entire
response and hides the cause, while `null` + a declaration keeps both. 🟢

## `GET /health` 🟢

| | |
|---|---|
| Status | **always 200** |
| Body | `{"status": "ok", "version": <settings.version>, "database": "reachable" \| "unreachable"}` |
| Check | a `SELECT 1` |

Deliberate: *"so that a load balancer can tell the difference between 'service is
down' (HTTP error) and 'service is up but degraded'"*. The module header forbids
importing CadQuery/AeroSandbox here so the endpoint stays importable on
`linux/aarch64`.

Today `version` is `app.settings.get_settings().version` = `"0.1.0"`, which
matches neither `core.config.VERSION` (`"1.0.0"`) nor `FastAPI(version=...)`
(`"2.0.0"`) — resolved by the single `pyproject.toml`-derived version (Q-CC-4).
🟢 There was no readiness probe; **resolved:** a new `/ready` endpoint reports
Alembic-head agreement and the capability flags, and a startup log line states
registered routers, capabilities, database URL and Alembic revision (Q-PC-2).
🟢

## Configuration surface 🟢

### The complete environment-variable surface

| Variable | Read by | Default | Note |
|---|---|---|---|
| `SQLALCHEMY_DATABASE_URL` | `db/session.py:8` (**bare `os.getenv`**) | `sqlite:///./db/test.db` | SQLite branch enables the WAL pragmas; folds into the merged `Settings` unless verified as a genuine Alembic bootstrap exception (Q-CC-4) 🟢 |
| `LOG_LEVEL` | `logging_config.py:7` (**bare `os.getenv`**) | `DEBUG` | `getattr(logging, name, DEBUG)` — an invalid name silently falls back (unaddressed 🟡); the variable itself folds into the merged `Settings` (Q-CC-4) 🟢 |
| `UVICORN_HOST` | `core.config.Settings` | `127.0.0.1` | used only by `main.run_app` |
| `PROJECT_NAME` | `core.config.Settings` | `"My FastAPI Project"` | 🟡 unused placeholder — removal not decided |
| `VERSION` | `core.config.Settings` | `"1.0.0"` | 🟡 unused today; collapses into the one `pyproject.toml`-derived version (BR-PC15, Q-CC-4) 🟢 |
| `ARTIFACTS_BASE_DIR` | `core.config.Settings` | `/tmp/da3dalus_artifacts` | `field_validator(mode="after")` → `.resolve()` |
| `COPILOT_API_KEY` / `_BASE_URL` / `_MODEL` / `_EMBEDDING_MODEL` | `core.config.Settings` | see `ai-copilot` | |
| `base_url` | `app.settings.Settings` | `http://localhost:8000` | host-visible base for MCP asset URLs 🟡 (the app listens on 8001) |
| `openai_api_key` | `app.settings.Settings` | `"sk*"` | 🟡 no reader in app code |
| `version` | `app.settings.Settings` | `"0.1.0"` | what `/health` returns |
| `low_re_*` (13) | `app.settings.Settings` | see `airfoil-catalog` | |
| `BROWSER_PATH`, `QT_QPA_PLATFORM` | headless rendering | `/usr/bin/chromium`, `offscreen` | |
| `OCP_VSCODE_HOST` / `_PORT` | `cad_designer/cq_plugins/display` | `127.0.0.1` / `3939` | dev-only |
| `DISPLAY_CONSTRUCTION_STEP` | `construction_plan_service` (**bare `os.environ`**) | unset | debug; folds into the merged `Settings` (Q-CC-4) 🟢 |

### Two `Settings` classes — merging into one (Q-CC-4)

Same class name, same `.env`, `extra="ignore"` on both, disjoint fields,
different naming conventions, different consumers — and **three** version
strings, nothing reconciling them today. **Resolved:** one class, one naming
convention, one instance, one `pyproject.toml`-derived version — the merge
also removes a genuine double-instance bug (`app/settings.py`'s module
singleton and its separately `lru_cache`d `get_settings()` return two
different objects that diverge the moment either is mutated). 🟢

Absolute-path guarantees:
`REPO_ROOT = Path(__file__).resolve().parents[2]` and
`AIRFOILS_DIR = REPO_ROOT / "components" / "airfoils"` **must** be absolute — a
CWD-relative airfoils dir made procedurally-generated airfoils from the OpenVSP
importer land outside the read directory, so they appeared "missing" after
import.

## Security posture 🟢 (ADR 0016, corrected by ADR 0024; Q-CC-1, Q-CC-2)

There is **no authentication and no authorisation** in the application: no
login, session, token, API key, user table, role, tenant or per-object ownership
check. The one artefact that looks like auth
(`app/core/security.py::verify_token`, comparing against the literal
`"valid_token"`) has **no callers**. **This is deliberate, not unfinished:**
da3Dalus is a single-user, standalone desktop application run on one machine by
one private user; multi-user capability is a future vision, out of scope now.

A **gitignored** reverse-proxy chain exists — ngrok (TLS, fixed domain) →
oauth2-proxy with a GitHub OAuth App and a comma-separated `GITHUB_USERS`
allowlist → Caddy → the app — but it is the **maintainer's own testing tool**
for sharing a preview and smoke-testing PR stages, **not the product's access
control**. ADR 0016's original framing of this chain as *the system's trust
boundary* is corrected by ADR 0024. `deploy/` is versioned in a **separate
private repository** (Q-CC-2), cloned into the already-gitignored `deploy/`
path — not a git submodule, since `.gitmodules` is committed and
`szymansk/da3Dalus` is public. Verified during the interview: `deploy/` has
never been committed and the GitHub client secret does not appear in the last
200 commits.

Nothing in the application *enforces* that the proxy chain is present — no
`TRUSTED_PROXY` check, no forwarded-identity header, no bind-address
restriction — and that is accepted, not remediated by an application-level
control. Instead, an **exposure guard lives at the launch surfaces**, the only
place a guard is actually enforceable given uvicorn opens the socket before the
app loads: the documented dev command drops `--host 0.0.0.0` (uvicorn's default
is already loopback); Docker publishes to `127.0.0.1` only while
`--host 0.0.0.0` stays mandatory *inside* the container; and a startup log line
states the effective reachability, warning on a non-loopback bind without an
explicit `ALLOW_PUBLIC_BIND` opt-in. On Linux, Docker's published ports bypass
`ufw`/`firewalld` via the `DOCKER` iptables chain, so the loopback publish
address is the control, not a host firewall.

## Not part of this contract

- Every domain route's request/response schema → the owning module's
  `contracts.md`.
- The MCP protocol surface → [`../mcp-server/contracts.md`](../mcp-server/contracts.md)
  (this module only mounts it).
- The client side of the CORS story →
  [`../frontend-workbench/contracts.md`](../frontend-workbench/contracts.md).
