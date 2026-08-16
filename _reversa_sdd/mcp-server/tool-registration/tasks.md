# mcp-server / tool-registration — Implementation Tasks

> Parent module task list: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] `fastmcp` with `FastMCP.tool()`, `.resource()`, `.http_app()`, `.run()`.
- [ ] `read_image_asset` / `read_data_asset` from the asset registry
      ([`../rest-mcp-reuse`](../rest-mcp-reuse/tasks.md) is the sibling use
      case; the registry itself is a module-level task).
- [ ] The v2 endpoint functions the 76 tools delegate to.

## Tasks

- [ ] **T-01 — `MCPToolSpec`.**
  `@dataclass(frozen=True)` with `name: str`, `description: str`,
  `handler: Callable[..., Any]`.
  - Legacy origin: `app/mcp_server.py:64`
  - Definition of done: frozen (a spec cannot be mutated after registration).
  - Confidence: 🟢

- [ ] **T-02 — `mcp_tool(name, description)`.**
  Append an `MCPToolSpec` to `TOOL_SPECS` and **return the function
  unchanged**.
  - Legacy origin: `app/mcp_server.py:86`
  - Definition of done: `assert decorated is original` in a test. This is not a
    stylistic choice — the entire 1 017-line test suite calls tools directly, so
    turning this into a wrapper breaks it.
  - Confidence: 🟢

- [ ] **T-03 — Declare the 76 tools.**
  One decorated coroutine per tool. Parameters are the endpoint's Pydantic
  types (they become the MCP schema). The endpoint import goes **inside** the
  body. No docstrings — the prose lives in `description=`.
  - Legacy origin: `app/mcp_server.py` (the bulk of the file)
  - Definition of done: `len(TOOL_SPECS) == 76`; descriptions are meaningful
    sentences; the module imports on a platform without CadQuery/AeroSandbox.
  - Confidence: 🟢

- [ ] **T-04 — `MCP_TOOL_NAMES`.**
  `tuple(spec.name for spec in TOOL_SPECS)`, placed **after** the last
  declaration.
  - Legacy origin: `app/mcp_server.py:1500`
  - Definition of done: 76 entries, no duplicates; a test asserts the exact set
    so that adding or removing a tool is a deliberate, reviewed change.
  - Confidence: 🟢

- [ ] **T-05 — `create_mcp_server()`.**
  `FastMCP(name="da3dalus-cad-tools")`; register every spec with its name and
  description; register `img://{asset_id}` (`image/png`, `read_image_asset`) and
  `data://{asset_id}` (`application/octet-stream`, `read_data_asset`).
  - Legacy origin: `app/mcp_server.py:1503-1524`
  - Definition of done: the server name is asserted; both resource templates are
    present with the documented MIME types.
  - Confidence: 🟢

- [ ] **T-06 — `get_mcp()` memoisation.**
  Module global `mcp`, built on first call.
  - Legacy origin: `app/mcp_server.py:1527-1534`
  - Definition of done: two calls return the same object. Record that calling
    `create_mcp_server()` directly bypasses the memo and produces a second
    server.
  - Confidence: 🟢

- [ ] **T-07 — `create_mcp_http_app(path="/")`.**
  `get_mcp().http_app(path=path)`.
  - Legacy origin: `app/mcp_server.py:1537`
  - Definition of done: the returned app mounts at `/mcp` and responds to an MCP
    `tools/list`.
  - Confidence: 🟢

- [ ] **T-08 — Import-time construction.**
  `mcp = get_mcp()` at module scope (l.1548).
  - Legacy origin: `app/mcp_server.py:1548`
  - Definition of done: importing the module leaves `mcp` non-`None`. Record the
    consequence: `app/main.py:73` imports this module, so the server exists
    before `create_app()` and before configuration is applied.
  - Confidence: 🟢

- [ ] **T-09 — `run_mcp_server()`.**
  `transport="http", host="0.0.0.0", port=8001, path="/mcp"`.
  - Legacy origin: `app/mcp_server.py:1542`
  - Definition of done: reproduced verbatim **and recorded as a gap** — it binds
    all interfaces on an unauthenticated surface and ignores `UVICORN_HOST`.
  - Confidence: 🟢

- [ ] **T-10 — Host integration.**
  In `create_app()`: build `mcp_app` **before** the `FastAPI(...)` call, nest
  `async with mcp_app.lifespan(app)` inside the combined lifespan, and
  `app.mount("/mcp", mcp_app)` after the routers.
  - Legacy origin: `app/main.py:95`, `:186`, `:247`
  - Definition of done: an integration test starts the app, calls a tool over
    HTTP at `/mcp`, and shuts down cleanly — proving the nested lifespan runs
    and tears down.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Non-wrapping:** the decorated symbol is the original coroutine
      and is directly awaitable with `_call_endpoint` patched.
- [ ] **TT-02 — Spec contents:** name and description recorded verbatim.
- [ ] **TT-03 — Name tuple:** exactly 76, unique, and matching the expected set.
- [ ] **TT-04 — Installation:** every name in `MCP_TOOL_NAMES` appears in
      `tools/list`.
- [ ] **TT-05 — Resource templates:** both registered with the documented MIME
      types.
- [ ] **TT-06 — Memoisation:** `get_mcp()` is idempotent.
- [ ] **TT-07 — Import-time:** `app.mcp_server.mcp` is a `FastMCP` right after
      import.
- [ ] **TT-08 — Schema derivation:** a tool taking `OperatingPointSchema` has an
      input schema describing it.
- [ ] **TT-09 — Platform tolerance:** with the CAD endpoint module unimportable,
      the **module** still imports and only the tool call fails.
- [ ] **TT-10 — Mounting:** an end-to-end `tools/list` over HTTP at `/mcp`.

## Suggested Order

1. **T-01 → T-02** the spec and the decorator — a handful of lines that
   everything else depends on. Write TT-01 immediately; the non-wrapping
   property is easy to lose in a refactor.
2. **T-05 → T-07** installation and mounting with a *small* set of tools (two or
   three), so the plumbing is proven before the bulk work.
3. **T-03** the 76 declarations, grouped by domain (wings, fuselages, operating
   points, flight profiles, aeroplane base + airfoils, aero analysis, design
   assumptions, stability/envelope, CAD export, trim). The three
   asset-producing tools require the registry, so they come after it.
4. **T-04** freeze the names once the set is complete, and pin it with TT-03.
5. **T-08 → T-09** import-time construction and the standalone runner.
6. **T-10** host integration last — it changes application startup.

## Pending Gaps

- **Should the server be built lazily** instead of at import time, so
  configuration can influence the tool set?
- **Should duplicate tool names be rejected** at registration?
- **Should registration be logged** (count, names) so an operator can see what a
  process exposes?
- **Should `run_mcp_server` honour `UVICORN_HOST`** rather than binding
  `0.0.0.0:8001`?
- **Should a tool whose capability is missing be omitted from `tools/list`**
  instead of failing at call time, mirroring the REST side's clean 503?
- **Should tools carry authorisation metadata**, so a future auth layer has
  something to key on? Today none exists.
