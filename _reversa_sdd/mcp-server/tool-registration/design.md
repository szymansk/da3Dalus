# mcp-server / tool-registration — Technical Design

> Use-case design. Parent module: [`../design.md`](../design.md).
> Protocol contract: [`../contracts.md`](../contracts.md).

## Interface

```python
@dataclass(frozen=True)
class MCPToolSpec:                      # l.64
    name: str
    description: str
    handler: Callable[..., Any]

TOOL_SPECS: list[MCPToolSpec] = []

def mcp_tool(name: str, description: str) -> Callable[[F], F]:   # l.86
def create_mcp_server() -> FastMCP:                              # l.1503
def get_mcp() -> FastMCP:                                        # l.1530
def create_mcp_http_app(path: str = "/"):                        # l.1537
def run_mcp_server() -> None:                                    # l.1542

MCP_TOOL_NAMES: tuple[str, ...]                                  # l.1500
mcp: FastMCP | None                                              # module global
```

## Main Flow

### F1 — Recording 🟢

```python
def mcp_tool(name, description):                 # l.86
    def decorator(fn):
        TOOL_SPECS.append(MCPToolSpec(name, description, fn))
        return fn                                # ← UNCHANGED
    return decorator
```

Returning `fn` rather than a wrapper is the design decision that makes the whole
module testable: `test_mcp_server_tools.py` imports a tool and awaits it
directly, with `_call_endpoint` monkeypatched, and never touches FastMCP. 🟢

A declaration in situ:

```python
@mcp_tool(
    name="analyze_alpha_sweep",
    description="Run an angle-of-attack sweep analysis for one aeroplane.",
)
async def analyze_alpha_sweep_tool(aeroplane_id: UUID4, request: AlphaSweepRequest) -> Any:
    from app.api.v2.endpoints.aeroanalysis import analyze_alpha_sweep
    return await _call_endpoint(analyze_alpha_sweep,
                                aeroplane_id=aeroplane_id, request=request)
```

Three things are visible here and all three are contract:

1. the **parameters** (`UUID4`, `AlphaSweepRequest`) become the MCP input
   schema — FastMCP introspects the signature;
2. the endpoint import is **inside the body**, so a platform without
   AeroSandbox can still import the module (the failure moves to call time);
3. there is **no docstring** — `description=` is what the agent reads.

### F2 — Freezing 🟢

```python
MCP_TOOL_NAMES: tuple[str, ...] = tuple(spec.name for spec in TOOL_SPECS)   # l.1500
```

Placed after the last declaration, so it captures all 76. It is the module's
public introspection surface; the tests assert membership and count against it
rather than against FastMCP internals. 🟢

### F3 — Installation 🟢

```python
def create_mcp_server() -> FastMCP:                      # l.1503
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

### F4 — Memoisation and mounting 🟢

```python
mcp: FastMCP | None = None

def get_mcp() -> FastMCP:                    # l.1530
    global mcp
    if mcp is None:
        mcp = create_mcp_server()
    return mcp

def create_mcp_http_app(path="/"):           # l.1537
    return get_mcp().http_app(path=path)

def run_mcp_server() -> None:                # l.1542 — standalone
    get_mcp().run(transport="http", host="0.0.0.0", port=8001, path="/mcp")  # 🟡 hard-coded

mcp = get_mcp()                              # l.1548 — IMPORT-TIME CONSTRUCTION
```

`app/main.py:73` imports `create_mcp_http_app`, so importing `app.main`
constructs the entire FastMCP server as a side effect — before `create_app()`
runs, before any router is included, and before configuration is applied. 🟡

Host integration:

```
main.py:95   mcp_app = create_mcp_http_app(path="/")     # BEFORE FastAPI(...)
main.py:186  async with mcp_app.lifespan(app): ...       # nested in _combined_lifespan
main.py:247  app.mount("/mcp", mcp_app)                  # after the routers
```

The mount path is `/mcp` while the ASGI app's internal path is `/` — which is
why `_base_url_from_request_url` has to strip a trailing `/mcp` when deriving
public asset URLs behind a proxy. 🟢

## Alternative Flows

- **Two tools declared with the same name:** both are appended and both are
  registered; FastMCP's behaviour on a duplicate is undefined here and
  `MCP_TOOL_NAMES` would show the duplicate. Nothing guards it. 🟡
- **A capability-gated endpoint module is missing:** the module still imports;
  the tool raises `ImportError` when called. 🟡
- **`create_mcp_server()` called directly (in a test):** a **second**,
  independent server is built — `get_mcp()`'s memo is bypassed. 🟡
- **`run_mcp_server()` in a container:** binds `0.0.0.0:8001` regardless of
  `UVICORN_HOST`, exposing the unauthenticated tool surface on every
  interface. 🟡

## Dependencies

- `fastmcp.FastMCP` — `tool()`, `resource()`, `http_app()`, `run()`.
- `read_image_asset` / `read_data_asset` from the asset registry (same module).
- The 76 endpoint functions, imported lazily inside each tool body.
- `app/main.py` for mounting and lifespan nesting.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Record, don't wrap — keep handlers plain callables | `mcp_tool:86` returning `fn` | 🟢 |
| A module-level list as the registry, populated by import side effects | `TOOL_SPECS` | 🟢 |
| Freeze the names into a tuple for introspection and tests | `MCP_TOOL_NAMES:1500` | 🟢 |
| Derive schemas from signatures instead of writing them | FastMCP + Pydantic parameter types | 🟢 |
| Put the agent-facing prose in `description=`, not a docstring | every declaration | 🟢 |
| Import endpoints lazily inside tool bodies for platform tolerance | every declaration; ADR 0017 | 🟢 |
| Build the server once, at import, and memoise it | `get_mcp` + l.1548 | 🟢 (a 🟡 coupling) |
| Mount in-process rather than run a second service | `main.py:247` | 🟢 |

## Internal State

| State | Where | Lifecycle |
|---|---|---|
| `TOOL_SPECS` | module list | appended during import; effectively immutable afterwards |
| `MCP_TOOL_NAMES` | module tuple | frozen once, at import |
| `mcp` | module global | built once by `get_mcp()`; never rebuilt |

There is no per-request or per-agent state in this use case. 🟢

## Observability

- 🟡 Registration is completely silent: no log line records how many tools were
  installed, and a duplicate or missing tool would be invisible.
- 🟡 The only signal available to an operator is `tools/list` over the protocol
  itself.

## Risks and Gaps

- 🟡 **Import-time construction** makes the tool set unconfigurable and couples
  server creation to import order; a configuration-dependent tool set is
  impossible without restructuring.
- 🟡 **`run_mcp_server` hard-codes `0.0.0.0:8001`**, ignoring `UVICORN_HOST` on
  an unauthenticated surface.
- 🟡 **No registration logging or metric.**
- 🟡 **Nothing prevents duplicate tool names.**
- 🟡 **`create_mcp_server()` can be called directly**, producing a second server
  that bypasses the memo.
- 🟡 **A missing capability-gated endpoint fails at call time**, so an agent
  discovers the tool in `tools/list` and only then learns it cannot run — the
  REST side answers a clean 503 via `Depends(require_cad)` instead.
