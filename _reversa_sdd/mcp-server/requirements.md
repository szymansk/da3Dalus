# mcp-server

> Module-level specification. Focuses on WHAT the module does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: mcp-server,
> `_reversa_sdd/data-dictionary.md` §Module: mcp-server,
> `_reversa_sdd/architecture.md` §4.2, `_reversa_sdd/permissions.md` §3,
> ADR 0009, ADR 0016.

## Overview

`mcp-server` exposes the service as a **Model Context Protocol** server for
external AI agents: **76 FastMCP tools** that re-enter the existing v2 endpoint
functions **in-process**, plus an asset registry that turns binary results (PNGs,
ZIPs) into MCP resources with dual public URLs. 🟢

The whole module is one file, `app/mcp_server.py` (1 552 lines), mounted at
`/mcp` with its lifespan nested inside the app's. The server object is built at
**import time** — `mcp = get_mcp()` runs before `create_app()`. 🟢

Its defining property, and its defining defect, is the bridge: `_call_endpoint`
calls a FastAPI endpoint function as a plain callable inside a bare
`SessionLocal()` — with **no commit**. Every write tool therefore returns a
success payload while persisting nothing. 🟡 (TD-01, G-7)

## Responsibilities

- Declare and install the 76 tools (`@mcp_tool` decorator → `TOOL_SPECS` →
  `create_mcp_server()`). 🟢
- Bridge each tool to its v2 endpoint function in-process. 🟢
- Normalise FastAPI return types into MCP JSON. 🟢
- Register binary artefacts as MCP resources (`img://`, `data://`) and resolve
  the public URLs an agent and a browser respectively need. 🟢
- Provide the ASGI app mounted at `/mcp` and a standalone runner. 🟢

**Explicitly NOT this module's responsibility:** the business logic (it owns
none — every tool delegates), the transaction boundary (which it fails to
honour), authentication (there is none anywhere, ADR 0016), and the copilot's
6-tool advisory registry (→ `ai-copilot`, a completely separate mechanism).

## Business Rules

> `BR-78` is a global id reused verbatim from [`../domain.md`](../domain.md).
> `BR-MCP*` are module-local.

### Registration

- **BR-MCP1 — Declaration is separated from installation.** 🟢
  ```python
  @dataclass(frozen=True)
  class MCPToolSpec: name: str; description: str; handler: Callable

  TOOL_SPECS: list[MCPToolSpec] = []

  def mcp_tool(name, description):            # l.86 — the decorator only RECORDS
      def decorator(fn):
          TOOL_SPECS.append(MCPToolSpec(name, description, fn))
          return fn                            # handler returned UNCHANGED
      return decorator

  def create_mcp_server() -> FastMCP:          # l.1503 — installation
      mcp = FastMCP(name="da3dalus-cad-tools")
      for spec in TOOL_SPECS:
          mcp.tool(name=spec.name, description=spec.description)(spec.handler)
      ...
  ```
  Because the decorator returns the handler unchanged, every tool stays directly
  callable and unit-testable without FastMCP. 🟢
- **BR-MCP2 — The handler signature *is* the input schema.** 🟢 FastMCP derives
  each tool's JSON schema from the coroutine's parameters, so the Pydantic types
  (`UUID4`, `OperatingPointSchema`, `AlphaSweepRequest`, `AssumptionWrite`,
  `RCFlightProfileCreate`, …) are the contract.
- **BR-MCP3 — The `description=` string is the only prose the agent sees.** 🟢
  The tool functions carry **no docstrings**.
- **BR-MCP4 — `MCP_TOOL_NAMES` is the introspection surface.** 🟢
  `tuple(spec.name for spec in TOOL_SPECS)` (l.1500), 76 entries, asserted
  against by the tests.
- **BR-MCP5 — The server is built at import time and memoised.** 🟢
  `get_mcp()` caches into the module global; `mcp = get_mcp()` at l.1548 runs
  **before** `create_app()`.

### The bridge

- **BR-MCP6 — One function bridges MCP to REST.** 🟢
  ```python
  async def _call_endpoint(endpoint_fn, **kwargs):        # l.96
      with SessionLocal() as db:
          if "db" in inspect.signature(endpoint_fn).parameters:
              kwargs["db"] = db
          result = endpoint_fn(**kwargs)
          if inspect.isawaitable(result): result = await result
          return _normalize_result(result)
  ```
  It imports the FastAPI **endpoint function** and calls it as a plain callable:
  no routing, no `Depends`, no middleware, no exception handlers.
- **BR-MCP7 — 🟡 MCP writes are silently discarded.** REST gets its commit from
  `get_db()`; here a bare `with SessionLocal() as db:` is used and
  `Session.__exit__` calls `close()`, which **rolls back**. Verified against a
  concrete path: `aeroplane_service.create_aeroplane` flushes four times and its
  docstring states *"No db.commit() is called — get_db() owns the transaction
  boundary"*, so `create_aeroplane_tool` returns a populated `AeroplaneModel`
  whose row never reaches the database. Only services that commit themselves
  (`retrim_service`, `operating_point_generator_service`,
  `tessellation_service`) persist through MCP.
  **No test can catch it:** `test_mcp_server_tools.py:89` monkeypatches
  `_call_endpoint` wholesale and `test_mcp_server_extended.py:643-673` exercises
  it with fake local functions — no test drives a real endpoint through a real
  session.
- **BR-MCP8 — Only `db` is injected; other dependencies are hand-supplied.** 🟢
  Several tools pass `settings=get_settings()` explicitly, and some pass
  `request=None` where the endpoint expects a `Request`.
- **BR-MCP9 — Service exceptions surface raw.** 🟢 The `ServiceException → HTTP`
  handler is registered on the FastAPI **app**, not on this path, so a
  `NotFoundError` reaches FastMCP as a Python exception rather than a 404-shaped
  result. 🟡
- **BR-MCP10 — `_normalize_result` maps FastAPI return types to MCP JSON.** 🟢
  | Input | Output |
  |---|---|
  | `None` | 🟡 an explicit result (`Q-MC-5`); previously `{"status": "ok"}`, indistinguishable from a silent failure |
  | `JSONResponse` | the parsed body |
  | `FileResponse` | `{file_path, filename, media_type}` |
  | `Response` with an image media type | a base64 envelope |
  | any other `Response` | decoded content |
  | anything else | `jsonable_encoder(...)` |

### The asset registry

- **BR-MCP11 — Binary results become resources, not tool JSON.** 🟢 Three tools
  (`get_aeroplane_three_view`, `download_export_zip`,
  `analyze_alpha_sweep_diagram`) route their output through
  `ASSET_REGISTRY: dict[str, AssetEntry]`, guarded by `ASSET_REGISTRY_LOCK`
  (`threading.Lock`).
- **BR-MCP12 — Everything served is under `tmp/`.** 🟢
  `register_file_asset` copies a file that is **not** already under `tmp/` to
  `tmp/mcp_assets/external/<uuid4hex>_<name>`; `register_bytes_asset` writes to
  `tmp/mcp_assets/<kind>/<asset_id[:2]>/<name>` (a 2-hex-char fan-out). MIME is
  guessed from the name; `kind` defaults to `img` for `image/*`, else `data`.
- **BR-MCP13 — Dual URLs answer "the agent and the browser see different
  addresses".** 🟢 `_asset_payload` returns `resource_uri`
  (`img://<id>` / `data://<id>`), **`url_from_docker_container`** (derived from
  the live request) and **`url_for_webui`** / `url` (from
  `settings.base_url`).
- **BR-MCP14 — The public base URL is resolved with a three-step fallback.** 🟢
  `resolve_public_base_url(ctx)` tries the MCP `Context` request URL, then
  `fastmcp.server.dependencies.get_http_request()`, then `settings.base_url`.
  `_base_url_from_request_url` strips a trailing `/mcp` from the path prefix so a
  reverse-proxied deployment produces correct `/static` URLs.
- **BR-MCP15 — Resource reads fail with `fastmcp.exceptions.NotFoundError`** on
  an unknown id, a kind mismatch (`img://` on a `data` entry) **and** a vanished
  file. 🟢

### Deployment

- **BR-MCP16 — Mounted in-process at `/mcp` with a nested lifespan.** 🟢
  `app.mount("/mcp", mcp_app)` (`main.py:247`) and
  `async with mcp_app.lifespan(app)` (`main.py:186`).
- **BR-MCP17 — The standalone runner hard-codes its bind.** 🟢
  `run_mcp_server()` uses `transport="http", host="0.0.0.0", port=8001,
  path="/mcp"`, ignoring `UVICORN_HOST`. 🟡/🟡
- **BR-78 / ADR 0009 — `get_db()` owns the transaction** — the rule this module
  breaks, and the reason BR-MCP7 exists. 🟢

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Record a tool with `@mcp_tool(name, description)` without wrapping it | Must | The decorated function is still directly callable |
| RF-02 | Install every recorded spec onto a `FastMCP(name="da3dalus-cad-tools")` | Must | `create_mcp_server()` registers all 76 |
| RF-03 | Expose `MCP_TOOL_NAMES` as a frozen tuple | Must | 76 entries; tests assert against it |
| RF-04 | Derive each tool's input schema from the handler signature | Must | Pydantic parameter types appear in the MCP schema |
| RF-05 | Memoise the server and build it at import time | Must | `get_mcp()` returns the same object; `mcp` exists before `create_app()` |
| RF-06 | Provide `create_mcp_http_app(path)` for mounting | Must | `app.mount("/mcp", …)` succeeds |
| RF-07 | Nest the MCP lifespan inside the app lifespan | Must | `async with mcp_app.lifespan(app)` |
| RF-08 | Call the endpoint function in-process with a fresh session | Must | `db` injected only when the parameter exists |
| RF-09 | Await an awaitable result | Must | Async endpoints work |
| RF-10 | Normalise `None`, `JSONResponse`, `FileResponse`, `Response` and plain objects | Must | See the BR-MCP10 table |
| RF-11 | Register a file asset, copying it under `tmp/` when necessary | Must | The stored path is always inside `tmp/` |
| RF-12 | Register a bytes asset with a 2-hex fan-out | Must | `tmp/mcp_assets/<kind>/<xx>/<name>` |
| RF-13 | Return `resource_uri` + both URLs from an asset payload | Must | `url_from_docker_container` ≠ `url_for_webui` when the request host differs from `base_url` |
| RF-14 | Serve `img://{asset_id}` and `data://{asset_id}` | Must | Correct MIME per template |
| RF-15 | Raise `NotFoundError` on unknown id, kind mismatch or missing file | Must | Three cases |
| RF-16 | Resolve the public base URL with the three-step fallback | Must | A `/mcp`-suffixed path prefix is stripped |
| RF-17 | Guard the registry with a lock | Must | Concurrent registrations do not corrupt the dict |
| RF-18 | **Persist writes** | Must | 🟢 fixed (`Q-MC-1`) — the transaction boundary is fixed, plus a write master-switch and auto-snapshot. Previously `_call_endpoint` never commits |
| RF-19 | Translate service exceptions into structured MCP errors | Should | 🟡 `_call_endpoint` maps domain exceptions to the single envelope (`Q-MC-4`, derived). Previously not met — they propagate raw |
| RF-20 | Offer a standalone HTTP runner | Could | 🟢 kept as scaffolding, marked not-supported (`Q-MC-7`); `run_mcp_server()` (hard-coded bind) |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Reusability | An MCP tool must not duplicate endpoint logic | `_call_endpoint` re-enters the endpoint function | 🟢 |
| Performance | In-process dispatch avoids an HTTP round trip and a second event loop | `_call_endpoint` | 🟢 |
| Concurrency | The asset registry is thread-safe | `ASSET_REGISTRY_LOCK` (`threading.Lock`) | 🟢 |
| Portability | Asset URLs must work from both a container network and a browser | the dual-URL payload | 🟢 |
| Testability | Every handler stays a plain callable | the decorator returns `fn` unchanged | 🟢 |
| Integrity | **Writes must survive** | 🟢 fixed (`Q-MC-1`); previously `Session.__exit__` rolled back | 🟢 |
| Scalability | `ASSET_REGISTRY` is process-local, never evicted, and files under `tmp/mcp_assets/` are never cleaned up; an asset id from one worker is a 404 in another | — | 🟡 |
| Security | No authentication or authorisation on `/mcp`; combined with `allow_origins=["*"]` the full 76-tool surface — including `delete_aeroplane` and `delete_all_wing_cross_sections` — is reachable by anyone who can reach the port | ADR 0016 | 🟡 |
| Resource safety | `register_file_asset` copies without a size cap and `_normalize_result` base64-encodes image bodies fully in memory | — | 🟡 |
| Maintainability | 🟢 The tool contract stops tracking the REST contract (ADR 0025) — deliberate, since the two have different consumers | previously 76 tools vs ≈230 routes; every module added after the geometry/analysis core is absent | 🟡 |

## Acceptance Criteria

```gherkin
Feature: Tool registration

  Scenario: The decorator only records
    Given a function decorated with @mcp_tool("x", "does x")
    Then TOOL_SPECS contains a spec named "x"
    And the function is unchanged and directly callable

  Scenario: Installation registers everything
    When create_mcp_server() runs
    Then every entry of TOOL_SPECS is registered on the FastMCP server
    And the two resource templates img:// and data:// are registered

  Scenario: The name tuple is the introspection surface
    Then MCP_TOOL_NAMES has 76 entries
    And it contains no duplicates

  Scenario: The server is a singleton built before the app
    When get_mcp() is called twice
    Then the same object is returned

Feature: The REST bridge

  Scenario: db is injected only when declared
    Given an endpoint function with a db parameter
    When _call_endpoint runs it
    Then a fresh session is passed
    Given an endpoint function without a db parameter
    Then no db keyword is passed

  Scenario: Awaitable results are awaited
    Given an async endpoint function
    Then the resolved value is normalised, not the coroutine

  Scenario: None becomes a status envelope
    Given an endpoint returning None
    Then the tool result is {"status": "ok"}

  Scenario: A JSONResponse is unwrapped
    Given an endpoint returning JSONResponse({"a": 1})
    Then the tool result is {"a": 1}

  Scenario: A FileResponse becomes a descriptor
    Given an endpoint returning FileResponse(path)
    Then the tool result carries file_path, filename and media_type

  Scenario: A write is lost   # characterisation of TD-01
    Given create_aeroplane_tool is invoked through a real session
    When the tool returns successfully
    Then no aeroplane row exists in the database

Feature: Assets

  Scenario: An external file is copied under tmp
    Given a PNG outside tmp/
    When register_file_asset runs
    Then the stored path is under tmp/mcp_assets/external/
    And the payload carries resource_uri img://<id>

  Scenario: Bytes are fanned out
    When register_bytes_asset writes a ZIP
    Then the path is tmp/mcp_assets/data/<two-hex>/<filename>

  Scenario: Dual URLs
    Given a request whose host differs from settings.base_url
    Then url_from_docker_container derives from the request
    And url_for_webui derives from settings.base_url

  Scenario: A kind mismatch is a NotFoundError
    Given a data asset
    When it is read through img://<id>
    Then fastmcp.exceptions.NotFoundError is raised

  Scenario: A vanished file is a NotFoundError
    Given a registered asset whose file was deleted
    Then reading it raises NotFoundError

  Scenario: The /mcp suffix is stripped from a proxied base URL
    Given the request URL path ends with /mcp
    Then the derived base URL does not contain /mcp
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|---|---|---|
| The two-stage registration pattern (RF-01…RF-03) | Must | Keeps every tool testable without FastMCP |
| The in-process bridge (RF-08…RF-10) | Must | The module's entire reason to exist — no duplicated logic |
| **A commit on the write path (RF-18)** | Must | 🟡 the top-severity defect in the whole system (TD-01): ~40 mutation tools lie |
| Signature-derived schemas (RF-04) | Must | The agent-visible contract |
| Asset registry with dual URLs (RF-11…RF-17) | Must | Binary results cannot travel as tool JSON |
| Mount + nested lifespan (RF-06/RF-07) | Must | One process, one port |
| Structured MCP errors (RF-19) | **Should** | 🟡 decided (`Q-MC-4`); today a `NotFoundError` is an opaque Python exception |
| Standalone runner (RF-20) | Could | Convenience; the mounted path is the deployment |
| Parity with the REST surface | **N/A** | 🟢 rebuilt on `copilot_tools` (ADR 0025) — the surface is designed as an agent capability set, not derived from the route table (`Q-MC-2`). Previously 76 vs ≈230 — versioning, copilot, components, construction plans, powertrain and OpenVSP import are all absent |
| Authentication on `/mcp` | Won't (today) | ADR 0016 — the tunnel is the boundary; 🟡 nothing enforces the tunnel exists |
| Asset eviction / TTL / size cap | Won't (today) | 🟡 unbounded registry and directory |
| Multi-worker asset sharing | Won't | 🟡 single-worker is assumed and now stated (`Q-MC-3`); process-local registry ⇒ 404 in another worker |

## Code Traceability

| File | Symbol | Coverage |
|---|---|---|
| `app/mcp_server.py` (1 552 l.) | the entire module | 🟢 |
| `…:60-61` | `_MIME_IMAGE_PNG`, `_STATIC_PREFIX` | 🟢 |
| `…:64` | `MCPToolSpec` (frozen dataclass) | 🟢 |
| `…:71` | `AssetEntry` (frozen dataclass) | 🟢 |
| `…:86` | `mcp_tool` decorator | 🟢 |
| `…:96` | `_call_endpoint` | 🟢 (🟢 fixed (`Q-MC-1`)) |
| `…:110` | `_normalize_result` | 🟢 |
| `…` | `register_file_asset`, `register_bytes_asset`, `_asset_payload`, `read_image_asset`, `read_data_asset`, `resolve_public_base_url`, `_base_url_from_request_url` | 🟢 |
| `…:1500` | `MCP_TOOL_NAMES` (76) | 🟢 |
| `…:1503` | `create_mcp_server` | 🟢 |
| `…:1530` | `get_mcp` (memoised) | 🟢 |
| `…:1537` | `create_mcp_http_app` | 🟢 |
| `…:1542` | `run_mcp_server` (🟡 hard-coded bind; scaffolding only, `Q-MC-7`) | 🟢 |
| `…:1548` | `mcp = get_mcp()` — import-time construction | 🟢 |
| `app/main.py:95,247` | `create_mcp_http_app` + `app.mount("/mcp", …)` | 🟢 |
| `app/main.py:186` | the nested lifespan | 🟢 |
| `app/tests/test_mcp_server_tools.py` · `_extended.py` · `_resources.py` (1 017 l.) | the test surface — 🟡 `_call_endpoint` is monkeypatched wholesale at `test_mcp_server_tools.py:89` | 🟢 |
