# mcp-server — MCP Protocol Contract

> This module publishes **no REST routes of its own**. Its contract is the
> **Model Context Protocol surface**: a FastMCP server named
> `da3dalus-cad-tools`, mounted as an ASGI sub-application at `/mcp`, offering
> **76 tools** and **2 resource templates**. 🟢
> Read from `app/mcp_server.py` and `app/main.py:95,186,247`, cross-checked
> against `code-analysis.md` §Module: mcp-server and
> `data-dictionary.md` §Module: mcp-server.

## Transport and mounting 🟢

| | |
|---|---|
| Server name | `da3dalus-cad-tools` |
| Mount | `app.mount("/mcp", mcp_app)` (`main.py:247`) |
| ASGI app | `create_mcp_http_app(path="/")` (`main.py:95`) |
| Lifespan | nested: `async with mcp_app.lifespan(app)` (`main.py:186`) |
| Construction | at **import time** — `mcp = get_mcp()` (`mcp_server.py:1548`) runs before `create_app()` |
| Standalone alternative | `run_mcp_server()` → `transport="http", host="0.0.0.0", port=8001, path="/mcp"` 🟡 hard-coded |
| Authentication | **none** (ADR 0016) 🟡 |
| CORS | inherited from the app: `allow_origins=["*"]`, `allow_credentials=True` 🟡 |

The protocol framing (JSON-RPC message shapes, `initialize`, `tools/list`,
`tools/call`, `resources/read`) is **entirely FastMCP's**; this module supplies
only names, descriptions, handlers and resource readers. A client speaks
standard MCP over the streamable-HTTP transport at `/mcp`. 🟡

## Tool declaration contract 🟢

```python
@mcp_tool(name="create_aeroplane",
          description="Create a new aeroplane by name and return its UUID.")
async def create_aeroplane_tool(settings: AeroplaneSettings) -> Any:
    from app.api.v2.endpoints.aeroplane.base import create_aeroplane
    return await _call_endpoint(create_aeroplane, settings=settings)
```

Three properties follow, and they are the whole agent-visible contract:

1. **The handler signature is the JSON input schema.** FastMCP derives it from
   the coroutine parameters, so the Pydantic types *are* the contract —
   `UUID4`, `OperatingPointSchema`, `AlphaSweepRequest`,
   `StoredOperatingPointCreate`, `OperatingPointSetSchema`,
   `RCFlightProfileCreate/Update`, `AssumptionWrite`, `AssumptionSourceSwitch`,
   `AeroplaneSettings`, `CreatorUrlType`, `ExporterUrlType`,
   `AnalysisToolUrlType`. Those schemas are documented in the owning modules'
   contracts and are **not** duplicated here. 🟢
2. **`description=` is the only prose the agent sees.** The tool functions carry
   no docstrings. 🟢
3. **The decorator does not wrap.** It appends an `MCPToolSpec` and returns the
   function unchanged, so every tool is directly callable in a unit test. 🟢

`MCP_TOOL_NAMES` (l.1500) is the frozen tuple of all 76 names — the
introspection surface the tests assert against.

## Tool inventory — 76 tools 🟢

| Domain | Count | Delegates to |
|---|---|---|
| Wings, cross-sections, control surfaces, CAD details, servos | 20 | `aeroplane.wings` |
| Fuselages + fuselage cross-sections | 11 | `aeroplane.fuselages` |
| Operating points + point sets (CRUD × 2) | 10 | `operating_points` |
| Flight profiles (CRUD + assign/detach) | 7 | `flight_profiles` |
| Aeroplane base (list/create/get/delete/mass × 2) + airfoil (known/upload) | 8 | `aeroplane.base`, `airfoils` |
| Aero analysis (wing, op-point, α-sweep, α-sweep diagram, parameter sweep) + three-view | 6 | `aeroanalysis` |
| Design assumptions (seed/get/set/switch source) | 4 | `aeroplane.design_assumptions` |
| Stability (get cached / compute) + flight envelope (get / compute) | 4 | `aeroanalysis` |
| CAD export (create wing loft, task status, download zip) | 3 | `cad` |
| Trim (ASB, AVL) | 2 | `aeroanalysis` |
| *(remainder: aeroplane delete/get variants)* | 1 | — |

Representative names and their exact descriptions (the agent-visible prose):

| Tool | Description |
|---|---|
| `get_all_aeroplanes` | "List all aeroplanes with IDs and timestamps, sorted alphabetically by name." |
| `create_aeroplane` | "Create a new aeroplane by name and return its UUID." 🟡 **write lost** |
| `get_aeroplane_by_id` | "Get the full aeroplane definition for a specific aeroplane UUID." |
| `delete_aeroplane` | "Delete an aeroplane and all associated data by aeroplane UUID." 🟡 **write lost** |
| `set_aeroplane_total_mass` | "Create or overwrite the total aeroplane mass in kilograms." 🟡 |
| `create_wing_cross_section` | "Insert a new wing cross-section at a given index (-1 appends at the end)." 🟡 |
| `delete_all_wing_cross_sections` | "Delete all cross-sections from a wing." 🟡 |
| `upload_airfoil_datfile` | "Upload a DAT airfoil definition into components/airfoils." (writes a **file**, so it *does* take effect) |
| `analyze_alpha_sweep_diagram` | "Generate an angle-of-attack sweep diagram as resource URI and public URL." |
| `get_aeroplane_three_view` | "Generate a three-view image as resource URI and public URL." |
| `download_export_zip` | "Get a ZIP export as resource URI and public URL." |
| `trim_operating_point` | "Trim one operating point … same trim logic as default operating-point generation." (service commits ⇒ **does** persist) |
| `generate_default_operating_point_set` | "Generate a default operating-point set for an aircraft UUID from its assigned flight profile." (commits ⇒ persists) |

## The durability contract — **currently broken** 🟡

```python
async def _call_endpoint(endpoint_fn, **kwargs):     # l.96
    with SessionLocal() as db:                       # ← no commit
        ...
```

`Session.__exit__` calls `close()`, which **rolls back** the pending
transaction. REST gets its commit from `get_db()`; this path has no equivalent.

| Tool class | Persists? |
|---|---|
| Reads | yes |
| Writes whose service relies on `get_db()`'s commit (~40 tools) | **no** — the payload is populated from flushed-but-uncommitted state |
| Writes whose service commits itself (`retrim_service`, `operating_point_generator_service`, `tessellation_service`) | yes |
| Writes to the **filesystem** (`upload_airfoil_datfile`, exports) | yes |

Verified against `aeroplane_service.create_aeroplane`, which flushes four times
and whose docstring states *"No db.commit() is called — get_db() owns the
transaction boundary"*. No test covers it: `test_mcp_server_tools.py:89`
monkeypatches `_call_endpoint` wholesale and
`test_mcp_server_extended.py:643-673` drives it with fake local functions.

**An agent cannot tell the difference from the response.** This is TD-01 / G-7.

## Error contract 🟡

There is none. The `ServiceException → {"error": {code, message, details}}`
handler is registered on the FastAPI **app**, and `_call_endpoint` does not pass
through it. A `NotFoundError` therefore reaches FastMCP as a raw Python
exception and surfaces as a generic tool failure with a Python message — never
a 404-shaped, machine-readable result.

| Failure | What the agent sees |
|---|---|
| Unknown aeroplane | a raw `NotFoundError` message |
| Validation failure | a raw `ValidationError` message |
| Conflict | a raw `ConflictError` message |
| Missing capability (`require_cad` / `require_aerosandbox`) | the `HTTPException(503)` object raised as a Python exception 🟡 |
| Unknown asset id / kind mismatch / vanished file | `fastmcp.exceptions.NotFoundError` — the **only** properly typed error in the module 🟢 |

## Result normalisation contract 🟢

| Endpoint returns | Tool result |
|---|---|
| `None` | 🟡 an explicit result (`Q-MC-5`); previously `{"status": "ok"}`, indistinguishable from a silent failure |
| `JSONResponse` | the parsed body |
| `FileResponse` | `{"file_path": …, "filename": …, "media_type": …}` |
| `Response` with an image media type | a base64 envelope 🟡 fully in memory (`Q-MC-3`) |
| any other `Response` | the decoded content |
| anything else (Pydantic model, ORM object, list, dict) | `jsonable_encoder(...)` |

Note that `NonFiniteSafeJSONResponse` — the NaN guard on the `aeroanalysis`
router — **is** a `JSONResponse` subclass, so its body is parsed normally; but a
solver NaN reaching `jsonable_encoder` on a non-`Response` return would produce
invalid JSON. 🟡

## Resource contract 🟢

| Template | Handler | Declared MIME | Errors |
|---|---|---|---|
| `img://{asset_id}` | `read_image_asset` | `image/png` | `NotFoundError` on unknown id, kind mismatch, missing file |
| `data://{asset_id}` | `read_data_asset` | `application/octet-stream` | same |

### Asset payload (returned by the three binary tools) 🟢

| Key | Value |
|---|---|
| `resource_uri` | `img://<asset_id>` or `data://<asset_id>` |
| `url_from_docker_container` | request-derived base URL + `/static/<rel>` — the **agent's** network view |
| `url_for_webui` | `settings.base_url` + `/static/<rel>` — the **browser's** view |
| `url` | backward-compatible alias of `url_for_webui` |
| `mime_type` | guessed from the filename, fallback `application/octet-stream` |
| `filename` | present only when known |

### Storage layout 🟢

| Path | Written by |
|---|---|
| `tmp/mcp_assets/external/<uuid4hex>_<name>` | `register_file_asset` when the source is outside `tmp/` |
| `tmp/mcp_assets/<kind>/<asset_id[:2]>/<filename>` | `register_bytes_asset` (2-hex fan-out) |

Everything served is under `tmp/`, which is also the `/static` mount — the
public URL is therefore just the static path.

### Base-URL resolution 🟢

```
1. the MCP Context's request URL
2. fastmcp.server.dependencies.get_http_request().url
3. settings.base_url          (default "http://localhost:8000" 🟡 — the app listens on 8001)
_base_url_from_request_url strips a trailing "/mcp" from the path prefix.
```

🟡 Assets move out of the process (`Q-MC-3`, derived; single-worker is assumed and now stated). Today `ASSET_REGISTRY` is a process-local dict guarded by a `threading.Lock`, never
evicted. An id minted by one worker is a `NotFoundError` in another, and the
files it points at are never cleaned up.

## Constants 🟢

| Constant | Value |
|---|---|
| server name | `da3dalus-cad-tools` |
| mount path | `/mcp` |
| `_MIME_IMAGE_PNG` | `image/png` |
| `_STATIC_PREFIX` | `/static/` |
| tool count | 76 (`len(MCP_TOOL_NAMES)`) |
| standalone bind | `0.0.0.0:8001`, path `/mcp` 🟡 ignores `UVICORN_HOST`; standalone mode is scaffolding, not supported surface (`Q-MC-7`) |

## Not exposed via MCP, although present in REST 🟡

versioning (`/branches`, `/lineages`), copilot history + stream, component tree,
components / component types, construction plans / parts / templates, mass & CG,
loading scenarios, mission objectives, weight items, endurance, matching chart,
tail sizing, field lengths, forward CG, speed polar, turbulator optimizer, all
powertrain routers, OpenVSP import, fuselage slice, health.

Roughly **230 v2 routes vs 76 MCP tools** — the surface is frozen at the
pre-copilot geometry/analysis core. Every module added since has no tools.

## Security posture 🟡

`/mcp` is unauthenticated, like the rest of the application (ADR 0016 — the
ngrok + oauth2-proxy tunnel is the only boundary, and it is gitignored). With
`allow_origins=["*"]` and `allow_credentials=True`, the entire 76-tool surface —
including `delete_aeroplane` and `delete_all_wing_cross_sections` — is reachable
by anyone who can reach the port. The write defect (TD-01) accidentally
mitigates the destructive tools; the read tools are fully effective.

## Not part of this contract

- The request/response **schemas** — owned by the modules whose endpoints the
  tools re-enter (`aeroplane-core`, `wing-design`, `fuselage-design`,
  `aero-analysis`, `mission-and-sizing`, `cad-generation`, `airfoil-catalog`).
- The transaction contract itself → `platform-core`
  ([`../platform-core/contracts.md`](../platform-core/contracts.md)).
- The **copilot's** 6-tool advisory registry → `ai-copilot`. It is a separate
  mechanism with a different registry, different units and a different safety
  model; the two share no code.
