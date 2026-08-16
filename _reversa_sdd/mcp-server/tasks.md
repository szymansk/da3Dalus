# mcp-server — Implementation Tasks

> Executable sequence to re-implement the module from the legacy behaviour.
> Every task cites the legacy file, a definition of done, and a confidence
> marker.
> Use-case task lists: [`tool-registration`](tool-registration/tasks.md) ·
> [`rest-mcp-reuse`](rest-mcp-reuse/tasks.md).

## Prerequisites

- [ ] `fastmcp` installed (`FastMCP`, `Context`, `ResourceResult`,
      `fastmcp.exceptions.NotFoundError`,
      `fastmcp.server.dependencies.get_http_request`).
- [ ] Every v2 endpoint module the tools re-enter: `aeroplane.base`,
      `aeroplane.wings`, `aeroplane.fuselages`, `aeroplane.design_assumptions`,
      `aeroanalysis`, `operating_points`, `flight_profiles`, `airfoils`, `cad`.
- [ ] `app/db/session.SessionLocal` and the `get_db()` contract (ADR 0009).
- [ ] `app/settings.get_settings()` with `base_url`.
- [ ] `tmp/` exists (`create_app()` `os.makedirs`-ensures it; a worktree must
      `mkdir -p tmp`) and is mounted at `/static`.

## Tasks

- [ ] **T-01 — `MCPToolSpec` + the `mcp_tool` decorator.**
  Frozen dataclass `(name, description, handler)`; the decorator appends to
  `TOOL_SPECS` and **returns the function unchanged**.
  - Legacy origin: `app/mcp_server.py:64`, `:86`
  - Definition of done: a decorated function is still directly callable and
    `TOOL_SPECS` grows by exactly one. The non-wrapping property is what keeps
    all 1 017 lines of tests able to call tools without FastMCP — do not
    "improve" it into a wrapper.
  - Confidence: 🟢

- [ ] **T-02 — `_call_endpoint`.**
  `with SessionLocal() as db:`; inject `db` only when
  `inspect.signature(endpoint_fn).parameters` contains it; await an awaitable;
  return `_normalize_result(result)`.
  - Legacy origin: `app/mcp_server.py:96`
  - Definition of done: an endpoint without a `db` parameter is called without
    the keyword; an async endpoint is awaited.
    **Reproduce the missing commit and record it as the module's top-severity
    gap (TD-01)** — do not silently add a commit while characterising the
    legacy; add it only as an explicit remediation task with its own test
    (TT-05).
  - Confidence: 🟢

- [ ] **T-03 — `_normalize_result`.**
  `None → {"status":"ok"}`; `JSONResponse → parsed body`; `FileResponse →
  {file_path, filename, media_type}`; image `Response →` base64 envelope; other
  `Response →` decoded content; else `jsonable_encoder`.
  - Legacy origin: `app/mcp_server.py:110`
  - Definition of done: six unit tests, one per branch. Record that
    `None → {"status":"ok"}` makes a silently failed delete indistinguishable
    from a successful one.
  - Confidence: 🟢

- [ ] **T-04 — `AssetEntry` + the registry.**
  Frozen dataclass `(asset_id, kind, file_path, mime_type, public_url,
  filename)`; `ASSET_REGISTRY: dict[str, AssetEntry]` guarded by
  `ASSET_REGISTRY_LOCK = threading.Lock()`.
  - Legacy origin: `app/mcp_server.py:71`
  - Definition of done: concurrent registrations from two threads produce two
    distinct entries. Record that the registry is never evicted and is
    process-local.
  - Confidence: 🟢

- [ ] **T-05 — `register_file_asset`.**
  Copy to `tmp/mcp_assets/external/<uuid4hex>_<name>` when the source is not
  already under `tmp/`; guess the MIME from the name; default `kind` to `img`
  for `image/*` else `data`.
  - Legacy origin: `app/mcp_server.py`
  - Definition of done: a file already under `tmp/` is **not** copied; a file
    outside is. Record the absence of a size cap.
  - Confidence: 🟢

- [ ] **T-06 — `register_bytes_asset`.**
  Write to `tmp/mcp_assets/<kind>/<asset_id[:2]>/<filename>`.
  - Legacy origin: `app/mcp_server.py`
  - Definition of done: the 2-hex fan-out directory is created on demand; the
    returned `public_url` resolves under `/static`.
  - Confidence: 🟢

- [ ] **T-07 — `resolve_public_base_url` + `_base_url_from_request_url`.**
  Three-step fallback (MCP `Context` request URL → `get_http_request()` →
  `settings.base_url`); strip a trailing `/mcp` from the path prefix.
  - Legacy origin: `app/mcp_server.py`
  - Definition of done: a request URL of `https://host/proxy/mcp` yields the
    base `https://host/proxy`. Record that the final fallback
    (`http://localhost:8000`) does not match the service's actual port (8001).
  - Confidence: 🟢

- [ ] **T-08 — `_asset_payload`.**
  `resource_uri`, `url_from_docker_container` (request-derived),
  `url_for_webui` + `url` (from `settings.base_url`), `mime_type`, and
  `filename` only when known.
  - Legacy origin: `app/mcp_server.py`
  - Definition of done: with a request host differing from `base_url`, the two
    URLs differ — this is the whole point of the dual URL (agent network view vs
    browser view).
  - Confidence: 🟢

- [ ] **T-09 — `read_image_asset` / `read_data_asset`.**
  Resolve the entry; raise `fastmcp.exceptions.NotFoundError` on an unknown id,
  a kind mismatch, or a vanished file; return a `ResourceResult`.
  - Legacy origin: `app/mcp_server.py`
  - Definition of done: all three failure modes tested. These are the **only**
    properly typed errors in the module — keep them.
  - Confidence: 🟢

- [ ] **T-10 — The 76 tool declarations.**
  One `@mcp_tool(name=…, description=…)` coroutine per tool, importing its
  endpoint function **inside the body** and delegating through
  `_call_endpoint`. Parameters are the Pydantic schemas of the endpoint.
  - Legacy origin: `app/mcp_server.py` (the bulk of 1 552 lines)
  - Definition of done: `len(MCP_TOOL_NAMES) == 76` with no duplicates; the
    descriptions are meaningful prose, because they are the **only** thing the
    agent reads (no docstrings). Local imports are deliberate — they keep the
    module importable when a capability-gated router is absent.
  - Confidence: 🟢

- [ ] **T-11 — Hand-supplied dependencies.**
  Tools whose endpoint declares a non-`db` dependency must pass it explicitly
  (`settings=get_settings()`); some pass `request=None`.
  - Legacy origin: `app/mcp_server.py` (several tool bodies)
  - Definition of done: every such call site is enumerated. Record the
    `request=None` calls as a risk — they work only while no endpoint touches
    the request object.
  - Confidence: 🟢

- [ ] **T-12 — The three asset-producing tools.**
  `get_aeroplane_three_view`, `analyze_alpha_sweep_diagram` (bytes) and
  `download_export_zip` (file) return `_asset_payload(entry)` instead of raw
  binary.
  - Legacy origin: `app/mcp_server.py`
  - Definition of done: each returns `resource_uri` plus both URLs, and the file
    ends up under `tmp/`.
  - Confidence: 🟢

- [ ] **T-13 — `MCP_TOOL_NAMES` + `create_mcp_server`.**
  Freeze the names; build `FastMCP(name="da3dalus-cad-tools")`, register every
  spec, then the two resource templates.
  - Legacy origin: `app/mcp_server.py:1500`, `:1503`
  - Definition of done: a test asserts the exact name set — this tuple is the
    module's public introspection surface.
  - Confidence: 🟢

- [ ] **T-14 — `get_mcp` / `create_mcp_http_app` / import-time construction.**
  Memoise into the module global; expose `http_app(path=…)`; execute
  `mcp = get_mcp()` at module scope.
  - Legacy origin: `app/mcp_server.py:1530-1548`
  - Definition of done: `get_mcp()` returns the same object twice; importing the
    module constructs the server. Record the import-time coupling — `app.main`
    imports this module at l.73, so the server exists before any configuration
    is applied.
  - Confidence: 🟢

- [ ] **T-15 — Mount and nested lifespan.**
  `mcp_app = create_mcp_http_app(path="/")` before the `FastAPI(...)` call;
  `app.mount("/mcp", mcp_app)`; `async with mcp_app.lifespan(app)` inside the
  combined lifespan.
  - Legacy origin: `app/main.py:95`, `:186`, `:247`
  - Definition of done: the MCP app's own startup/shutdown run inside the host
    app's — a test that starts the app and calls a tool over HTTP proves the
    nesting.
  - Confidence: 🟢

- [ ] **T-16 — `run_mcp_server` (standalone).**
  `server.run(transport="http", host="0.0.0.0", port=8001, path="/mcp")`.
  - Legacy origin: `app/mcp_server.py:1542`
  - Definition of done: reproduce the hard-coded bind **and record it** — it
    ignores `UVICORN_HOST` and binds to all interfaces on an unauthenticated
    surface.
  - Confidence: 🟢

### Remediation tasks (behaviour changes, not characterisation)

- [ ] **T-17 — Make MCP writes durable.**
  Replace the bare `with SessionLocal() as db:` with a commit-on-success /
  rollback-on-exception boundary equivalent to `get_db()`.
  - Legacy origin: `app/mcp_server.py:96`; ADR 0009; TD-01
  - Definition of done: a test that drives a **real** endpoint through a **real**
    session — `create_aeroplane_tool` followed by a fresh-session query that
    finds the row. This is the missing test that let the defect ship; write it
    first, watch it fail, then fix `_call_endpoint`.
  - Confidence: 🟡 (a decision, not a reproduction)

- [ ] **T-18 — Translate service exceptions.**
  Wrap the call so `NotFoundError` / `ValidationError` / `ConflictError` become
  structured MCP errors instead of raw Python exceptions.
  - Legacy origin: `app/main.py:274-307` (the handler that does **not** apply
    here)
  - Definition of done: an unknown aeroplane produces a machine-readable
    not-found result, matching what the REST envelope would have said.
  - Confidence: 🟡 (a decision)

- [ ] **T-19 — Bound the asset registry.**
  Add eviction (TTL or LRU), a size cap on `register_file_asset`'s copy, and a
  cleanup of `tmp/mcp_assets/`; decide what a multi-worker deployment should do.
  - Legacy origin: `app/mcp_server.py` (the registry)
  - Definition of done: the registry cannot grow unboundedly, and an id minted
    by one worker either resolves in another or fails with an explicit
    "not on this worker" error rather than a bare `NotFoundError`.
  - Confidence: 🟡 (a decision)

## Test Tasks

- [ ] **TT-01 — Decorator:** records a spec, returns the function unchanged.
- [ ] **TT-02 — Registration:** all 76 names installed; both resource templates
      present; no duplicate names.
- [ ] **TT-03 — Signature injection:** `db` passed only when declared.
- [ ] **TT-04 — Awaitable:** async endpoints resolved.
- [ ] **TT-05 — Durability (the missing test):** a **real** endpoint through a
      **real** session — assert the row exists in a fresh session. Today this
      test **fails**; that is the point.
- [ ] **TT-06 — Normalisation:** one test per `_normalize_result` branch.
- [ ] **TT-07 — Asset registration:** in-`tmp` file not copied, external file
      copied, bytes fan-out path correct.
- [ ] **TT-08 — Dual URLs:** request-derived vs `base_url`-derived differ.
- [ ] **TT-09 — Base-URL fallback:** all three steps, including the `/mcp` strip.
- [ ] **TT-10 — Resource errors:** unknown id, kind mismatch, vanished file.
- [ ] **TT-11 — Registry concurrency:** two threads register without loss.
- [ ] **TT-12 — Mounting:** a tool call over HTTP at `/mcp` succeeds with the
      nested lifespan running.
- [ ] **TT-13 — Exception passthrough (characterisation):** a `NotFoundError`
      escapes untranslated.
- [ ] **TT-14 — Surface drift (characterisation):** assert the documented
      absence of versioning / copilot / components / construction-plan /
      powertrain / OpenVSP tools, so re-adding one is a deliberate act.

## Suggested Order

1. **T-01 → T-03** the primitives: the decorator, the bridge and the
   normaliser. Everything else is either a tool that uses them or a resource.
2. **TT-05 before T-17.** Write the durability test first and watch it fail —
   the defect exists precisely because no such test was ever written.
3. **T-04 → T-09** the asset registry, which is independent of the tools and
   easy to test in isolation.
4. **T-10 → T-12** the 76 declarations, grouped by domain. The three
   asset-producing tools last, since they need the registry.
5. **T-13 → T-15** freeze the names, build the server, mount it. The import-time
   construction means this step changes application startup — do it once the
   tools are stable.
6. **T-16** the standalone runner.
7. **T-17 → T-19** the remediation tasks, each behind its own decision.

## Pending Gaps

- **Should `_call_endpoint` commit?** ~40 mutation tools currently return a
  success payload while persisting nothing (TD-01, G-7). This is the single
  highest-severity defect in the system.
- **How should MCP write failures be reported** once commits exist — partial
  batch semantics, or all-or-nothing per tool call?
- **Should service exceptions be translated** into structured MCP errors?
- **Should `None` keep returning `{"status": "ok"}`**, given a silently failed
  delete is indistinguishable from a successful one?
- **What is the asset lifecycle?** No eviction, no TTL, no size cap, no cleanup
  of `tmp/mcp_assets/`, and a process-local registry that breaks under multiple
  workers.
- **Should `/mcp` be authenticated**, given it exposes `delete_aeroplane` with
  `allow_origins=["*"]` and no login (ADR 0016)?
- **Should the MCP surface track REST?** 76 tools vs ≈230 routes: versioning,
  copilot, components/COTS, construction plans, powertrain and OpenVSP import
  are entirely absent.
- **Should `run_mcp_server` honour `UVICORN_HOST`** instead of binding
  `0.0.0.0:8001`?
- **Should `settings.base_url` default to port 8001**, matching where the
  service actually listens?
- **Should the server still be built at import time**, or lazily so
  configuration can influence it?
- **Is calling endpoints with `request=None` acceptable**, or should the bridge
  synthesise a minimal `Request`?
