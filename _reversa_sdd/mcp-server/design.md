# mcp-server — Technical Design

> Module-level design. Focuses on HOW the module is built, derived from the
> legacy code. Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Protocol contract: [`contracts.md`](contracts.md).
> Use cases: [`tool-registration`](tool-registration/design.md) ·
> [`rest-mcp-reuse`](rest-mcp-reuse/design.md).

## Interface

### Module-level structures 🟢

```python
_MIME_IMAGE_PNG = "image/png"          # l.60
_STATIC_PREFIX  = "/static/"           # l.61

@dataclass(frozen=True)
class MCPToolSpec:                     # l.64
    name: str; description: str; handler: Callable[..., Any]

@dataclass(frozen=True)
class AssetEntry:                      # l.71
    asset_id: str; kind: str; file_path: Path
    mime_type: str; public_url: str; filename: str | None

TOOL_SPECS:     list[MCPToolSpec] = []
ASSET_REGISTRY: dict[str, AssetEntry] = {}
ASSET_REGISTRY_LOCK = threading.Lock()

MCP_TOOL_NAMES: tuple[str, ...]        # l.1500 — 76 names
mcp: FastMCP | None                    # module global, memoised by get_mcp()
```

### Public functions 🟢

| Symbol | Line | Signature |
|---|---|---|
| `mcp_tool` | 86 | `(name, description) -> decorator` — records only |
| `_call_endpoint` | 96 | `async (endpoint_fn, **kwargs) -> Any` |
| `_normalize_result` | 110 | `(result) -> Any` |
| `register_file_asset` | — | `(path, *, kind?, filename?, ctx?) -> AssetEntry` |
| `register_bytes_asset` | — | `(content, *, kind, filename, mime_type?, ctx?) -> AssetEntry` |
| `_asset_payload` | — | `(entry) -> dict` |
| `read_image_asset` / `read_data_asset` | — | `(asset_id) -> ResourceResult` |
| `resolve_public_base_url` | — | `(ctx) -> str` |
| `_base_url_from_request_url` | — | `(url) -> str` — strips a trailing `/mcp` |
| `create_mcp_server` | 1503 | `() -> FastMCP` |
| `get_mcp` | 1530 | `() -> FastMCP` (memoised) |
| `create_mcp_http_app` | 1537 | `(path="/") -> ASGI app` |
| `run_mcp_server` | 1542 | `() -> None` — standalone, `0.0.0.0:8001` 🟡 |

## Main Flow

### F1 — Declaration → installation 🟢

```
import time:
  @mcp_tool("get_all_aeroplanes", "List all aeroplanes ...")
  async def get_all_aeroplanes_tool() -> Any:
      from app.api.v2.endpoints.aeroplane.base import list_aeroplanes
      return await _call_endpoint(list_aeroplanes)
  #  ^ the decorator appends an MCPToolSpec and returns fn UNCHANGED

  ... 76 times ...

  MCP_TOOL_NAMES = tuple(spec.name for spec in TOOL_SPECS)     # l.1500
  mcp = get_mcp()                                              # l.1548 — BUILT AT IMPORT

create_mcp_server():
  mcp = FastMCP(name="da3dalus-cad-tools")
  for spec in TOOL_SPECS:
      mcp.tool(name=spec.name, description=spec.description)(spec.handler)
  mcp.resource("img://{asset_id}",  name="image_asset",
               description="Read a generated image asset by asset ID.",
               mime_type="image/png")(read_image_asset)
  mcp.resource("data://{asset_id}", name="data_asset",
               description="Read a generated HTML or ZIP asset by asset ID.",
               mime_type="application/octet-stream")(read_data_asset)
  return mcp
```

Consequences of building at import time: the tool set is fixed before any
configuration is read, and importing `app.mcp_server` (which `app.main` does at
module level, l.73) constructs the whole FastMCP server as a side effect. 🟡

Detail in [`tool-registration`](tool-registration/design.md).

### F2 — The bridge 🟢

```python
async def _call_endpoint(endpoint_fn, **kwargs):            # l.96
    with SessionLocal() as db:                              # ← NO COMMIT, EVER
        if "db" in inspect.signature(endpoint_fn).parameters:
            kwargs["db"] = db
        result = endpoint_fn(**kwargs)
        if inspect.isawaitable(result):
            result = await result
        return _normalize_result(result)
```

What is bypassed, compared to an HTTP call to the same endpoint:

| Layer | REST | MCP |
|---|---|---|
| Routing / path params | FastAPI | the tool passes them directly |
| Body validation | Pydantic via FastAPI | Pydantic via the **handler signature** (FastMCP) |
| `Depends(get_db)` | yes — **commits** | replaced by a bare `SessionLocal()` — **rolls back** 🟡 |
| Other `Depends(...)` | resolved | must be passed by hand (`settings=get_settings()`, `request=None`) |
| CORS / middleware | yes | no |
| Exception handlers | `ServiceException → {"error": {...}}` | none — raw Python exceptions 🟡 |
| Response class | `JSONResponse` / `NonFiniteSafeJSONResponse` | `_normalize_result` |

Detail in [`rest-mcp-reuse`](rest-mcp-reuse/design.md).

### F3 — Result normalisation 🟢

```
None                                   -> {"status": "ok"}          🟡 hides a silent failure
JSONResponse                           -> json.loads(response.body)
FileResponse                           -> {"file_path": str, "filename": ..., "media_type": ...}
Response with media_type image/*       -> {"mime_type": ..., "data": base64(body)}   🟡 full in-memory
Response (other)                       -> body.decode()
anything else                          -> jsonable_encoder(result)
```

### F4 — The asset registry 🟢

```
register_file_asset(path, kind=None, filename=None, ctx=None):
    if path is NOT under tmp/:
        dest = tmp/mcp_assets/external/<uuid4().hex>_<path.name>
        shutil.copy(path, dest)                       # 🟡 no size cap
        path = dest
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    kind = kind or ("img" if mime.startswith("image/") else "data")
    entry = AssetEntry(uuid4().hex, kind, path, mime,
                       public_url=resolve_public_base_url(ctx) + "/static/" + rel_to_tmp(path),
                       filename)
    with ASSET_REGISTRY_LOCK: ASSET_REGISTRY[entry.asset_id] = entry     # 🟡 never evicted
    return entry

register_bytes_asset(content, kind, filename, mime_type=None, ctx=None):
    asset_id = uuid4().hex
    dest = tmp/mcp_assets/<kind>/<asset_id[:2]>/<filename>      # 2-hex fan-out
    dest.write_bytes(content)
    ... same registration ...

_asset_payload(entry) -> {
    "resource_uri": f"{entry.kind}://{entry.asset_id}",     # img:// or data://
    "url_from_docker_container": <request-derived base> + "/static/" + rel,
    "url_for_webui":             settings.base_url + "/static/" + rel,
    "url":                       <same as url_for_webui>,   # backward-compatible alias
    "mime_type": entry.mime_type,
    "filename":  entry.filename,                            # only when known
}

read_image_asset(asset_id) / read_data_asset(asset_id):
    entry = ASSET_REGISTRY.get(asset_id)      or raise fastmcp NotFoundError
    if entry.kind != expected_kind:              raise fastmcp NotFoundError
    if not entry.file_path.exists():             raise fastmcp NotFoundError
    return ResourceResult(content=bytes, mime_type=entry.mime_type)
```

`resolve_public_base_url(ctx)`:

```
1. ctx.request_context.request.url          (the MCP Context)
2. fastmcp.server.dependencies.get_http_request().url
3. settings.base_url                        (app/settings.py, default http://localhost:8000)
_base_url_from_request_url strips a trailing "/mcp" from the path prefix so a
reverse-proxied deployment produces correct /static URLs.
```

The dual URL exists because the agent and the browser see the service at
different addresses — an agent inside a container needs the container-network
host, a human clicking the link needs the externally routable one. 🟢

### F5 — Deployment 🟢

```
app/main.py:95   mcp_app = create_mcp_http_app(path="/")
app/main.py:186  async with mcp_app.lifespan(app):   ...     # nested in _combined_lifespan
app/main.py:247  app.mount("/mcp", mcp_app)
```

`run_mcp_server()` also exists for a standalone process:
`server.run(transport="http", host="0.0.0.0", port=8001, path="/mcp")` — the
host and port are **hard-coded**, ignoring `UVICORN_HOST`. 🟡

## Alternative Flows

- **Endpoint without a `db` parameter:** no session keyword is passed; the
  session is still opened and closed. 🟡 (wasteful but harmless)
- **Endpoint needing a non-`db` dependency:** the tool must pass it explicitly;
  several pass `settings=get_settings()` and some pass `request=None` where a
  `Request` is expected — any endpoint that actually *uses* the request would
  fail. 🟡
- **Endpoint raises `NotFoundError`:** it escapes as a raw Python exception;
  FastMCP surfaces a generic tool error rather than a 404-shaped result. 🟡
- **Endpoint returns `None`** (every `204` delete): `{"status": "ok"}` — a
  delete that silently did nothing is indistinguishable from one that
  worked. 🟡
- **A write tool succeeds:** the payload is populated from flushed-but-
  uncommitted ORM state, and the row disappears when the session closes. 🟡
- **A service that commits itself** (`retrim_service`,
  `operating_point_generator_service`, `tessellation_service`): the write
  **does** persist — so MCP writes are inconsistently durable. 🟡
- **Asset id unknown / kind mismatch / file gone:** `fastmcp.exceptions
  .NotFoundError`. 🟢
- **Second worker process:** its `ASSET_REGISTRY` is empty, so an id minted by
  worker A is a `NotFoundError` in worker B. 🟡
- **No MCP `Context` and no HTTP request** (e.g. a background call):
  `settings.base_url` is used, which defaults to `http://localhost:8000` while
  the service actually listens on 8001. 🟡
- **A capability-gated router is absent** (`linux/aarch64`): the tool's
  module-level import of the endpoint function fails at **call** time, since the
  imports are inside the tool bodies. 🟡

## Dependencies

- **`fastmcp`** — `FastMCP`, `Context`, `ResourceResult`,
  `fastmcp.exceptions.NotFoundError`, `fastmcp.server.dependencies
  .get_http_request`.
- **Every v2 endpoint module it re-enters** — `aeroplane.base`,
  `aeroplane.wings`, `aeroplane.fuselages`, `aeroplane.design_assumptions`,
  `aeroanalysis`, `operating_points`, `flight_profiles`, `airfoils`, `cad`.
- **`app/db/session.SessionLocal`** — used directly, bypassing `get_db()`
  (ADR 0009 violation).
- **`app/settings.get_settings()`** — `base_url` for `url_for_webui`, and passed
  by hand to several tools.
- **`tmp/`** — must exist; `create_app()` `os.makedirs`-ensures it, which is why
  a worktree must `mkdir -p tmp` before running.
- **`app/main.py`** — mounts the ASGI app and nests the lifespan.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Separate declaration from installation so handlers stay plain callables | `mcp_tool:86`, `create_mcp_server:1503` | 🟢 |
| Let the handler signature be the schema instead of hand-writing JSON schemas | FastMCP behaviour + the Pydantic parameter types | 🟢 |
| Re-enter the endpoint function rather than re-implement or self-call over HTTP | `_call_endpoint:96` | 🟢 |
| Inject `db` by signature introspection | `inspect.signature(...).parameters` | 🟢 |
| Use a bare `SessionLocal()` instead of the `get_db()` generator | `_call_endpoint` | 🟢 — **the defect** 🟡 |
| Normalise FastAPI response objects instead of restricting endpoints to plain data | `_normalize_result:110` | 🟢 |
| Move binary results out of tool JSON into MCP resources | the asset registry | 🟢 |
| Answer the network-view problem with two URLs rather than one | `_asset_payload` | 🟢 |
| Keep every served file under `tmp/` and expose it through the existing `/static` mount | `register_*_asset` | 🟢 |
| Build the server at import time | `mcp = get_mcp()` l.1548 | 🟢 (a 🟡 coupling) |
| The surface is neither frozen nor drifting — it is *derived*; ADR 0025 replaces it | 76 tools vs ≈230 routes | 🟢 (`Q-MC-2`) ( 🟡 drift) |

## Internal State

| State | Where | Lifecycle |
|---|---|---|
| `TOOL_SPECS` | module global | appended at import; never mutated afterwards |
| `MCP_TOOL_NAMES` | module global | frozen at import |
| `mcp` (the `FastMCP` server) | module global | built once at import, memoised by `get_mcp()` |
| `ASSET_REGISTRY` | module global dict | grows for the life of the process; **never evicted** 🟡 |
| files under `tmp/mcp_assets/` | filesystem | **never cleaned up** 🟡 |
| the per-call `Session` | `_call_endpoint` | opened and rolled back per tool call 🟡 |

## Observability

- 🟡 The module logs **nothing** on the tool path: no invocation record, no
  duration, no error log. A failing tool is visible only to the agent.
- 🟡 No metric counts tool calls, asset registrations or registry size — so the
  unbounded growth of `ASSET_REGISTRY` is invisible until memory pressure.
- 🟡 Failures inside the re-entered endpoint may log from the **service** layer,
  which is the only reason MCP activity appears in the log at all.

## Risks and Gaps

- 🟡 **MCP writes are silently discarded** (TD-01, G-7). ~40 of the 76 tools are
  mutations — `create_aeroplane`, `set_aeroplane_total_mass`, all wing /
  cross-section / fuselage / control-surface writes, all design assumptions —
  and each returns a success payload while persisting nothing. Services that
  commit themselves are the exception, which makes the behaviour *inconsistent*
  as well as wrong.
- 🟡 **No test can catch it.** `test_mcp_server_tools.py:89` monkeypatches
  `_call_endpoint` wholesale; `test_mcp_server_extended.py:643-673` exercises it
  with fake local functions. A real-endpoint-through-real-session test is the
  missing coverage.
- 🟡 **`ASSET_REGISTRY` is process-local and unbounded**, and the files it points
  at are never cleaned up. Multi-worker deployment is silently broken for
  assets.
- 🟡 **No authentication or authorisation on `/mcp`.** With
  `allow_origins=["*"]`, the whole surface — including `delete_aeroplane` and
  `delete_all_wing_cross_sections` — is reachable by anyone who can reach the
  port. The write defect accidentally mitigates the destructive tools.
- 🟡 **`_call_endpoint` maps domain exceptions to the single envelope** (`Q-MC-4`, derived). Previously **service exceptions are not translated.** `NotFoundError` and friends
  escape as raw Python exceptions instead of structured MCP errors.
- 🟡 **`_normalize_result` returns `{"status": "ok"}` for `None`**, so a delete
  that silently failed looks identical to one that succeeded.
- 🟡 **No size cap** on `register_file_asset`'s copy, and image bodies are
  base64-encoded fully in memory.
- 🟡 **The surface has drifted behind REST** — versioning, the copilot,
  components/COTS, construction plans, powertrain and OpenVSP import have no
  tools at all.
- 🟡 **`run_mcp_server` hard-codes `0.0.0.0:8001`**, bypassing `UVICORN_HOST`.
- 🟡 **`settings.base_url` defaults to `http://localhost:8000`** while the app
  listens on 8001 — the fallback URL is wrong out of the box.
- 🟡 **Import-time construction** couples the tool set to import order and makes
  the server unconfigurable.
- 🟡 **Endpoints are called with `request=None`**, which is safe only as long as
  none of them touches the request object.
