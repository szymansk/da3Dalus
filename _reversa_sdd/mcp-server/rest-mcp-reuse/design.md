# mcp-server / rest-mcp-reuse — Technical Design

> Use-case design. Parent module: [`../design.md`](../design.md).
> Protocol contract: [`../contracts.md`](../contracts.md).
> Transaction contract: [`../../platform-core/contracts.md`](../../platform-core/contracts.md).

## Interface

```python
async def _call_endpoint(endpoint_fn: Callable, **kwargs) -> Any     # l.96
def _normalize_result(result: Any) -> Any                            # l.110
```

Both are private and used only from tool bodies. A tool is always of the shape:

```python
@mcp_tool(name=..., description=...)
async def <name>_tool(<endpoint's pydantic params>) -> Any:
    from app.api.v2.endpoints.<module> import <endpoint_fn>
    return await _call_endpoint(<endpoint_fn>, **params)
```

## Main Flow

### F1 — The bridge 🟢

```python
async def _call_endpoint(endpoint_fn, **kwargs):
    with SessionLocal() as db:                                   # (1)
        if "db" in inspect.signature(endpoint_fn).parameters:    # (2)
            kwargs["db"] = db
        result = endpoint_fn(**kwargs)                           # (3)
        if inspect.isawaitable(result):
            result = await result                                # (4)
        return _normalize_result(result)                         # (5)
    # (6) __exit__ -> close() -> ROLLBACK
```

| Step | What happens | Consequence |
|---|---|---|
| (1) | a bare `SessionLocal()` context manager | **not** `get_db()`, so no commit and no rollback-on-exception semantics beyond `close()` |
| (2) | signature introspection | endpoints that take `db` get it; others don't. Any other `Depends(...)` is the tool's problem |
| (3) | plain call | no routing, no request parsing, no middleware, no exception handlers |
| (4) | `isawaitable` | supports both `def` and `async def` endpoints |
| (5) | normalisation | FastAPI response objects become MCP JSON |
| (6) | **`close()` rolls back** | 🟡 every uncommitted write is discarded |

`SessionLocal` is configured with `expire_on_commit=False` and
`autoflush=False` (`app/db/session.py:27-33`), so the ORM objects returned to
the tool are still readable *after* the rollback — which is exactly why a lost
write looks like a successful one: the payload is fully populated from
in-memory identity-map state. 🟡

### F2 — Why the writes are lost, concretely 🟢

```
create_aeroplane_tool(settings=AeroplaneSettings(name="X"))
  -> _call_endpoint(create_aeroplane, settings=..., db=<bare session>)
       -> aeroplane_service.create_aeroplane(db, name="X")
            db.add(aeroplane) ; db.flush()      # PK assigned
            db.add(branch)    ; db.flush()      # lineage bootstrap
            aeroplane.branch_id = branch.id ; db.flush()
            # docstring: "No db.commit() is called — get_db() owns the
            #             transaction boundary"
            return aeroplane                     # fully populated
       -> _normalize_result(aeroplane) -> jsonable_encoder(...)   # id, uuid, name all present
  <- returns a convincing payload
close() -> ROLLBACK -> the row never existed
```

The same applies to every wing, cross-section, fuselage, control-surface and
design-assumption mutation. The exceptions are services that commit themselves —
`retrim_service`, `operating_point_generator_service`, `tessellation_service` —
so MCP durability is **inconsistent**, which is worse than uniformly broken. 🟡

### F3 — Why no test catches it 🟢

| Test | What it does |
|---|---|
| `test_mcp_server_tools.py:89` | monkeypatches `_call_endpoint` **wholesale**, so the tool bodies are exercised and the bridge is not |
| `test_mcp_server_extended.py:643-673` | exercises `_call_endpoint` with **fake local functions**, so the session is real but the endpoint is not |
| — | **missing:** a real endpoint through a real session, asserted from a *second* session |

### F4 — `_normalize_result` 🟢

```python
def _normalize_result(result):                       # l.110
    if result is None:
        return {"status": "ok"}                       # 🟡 no-op == success
    if isinstance(result, JSONResponse):
        return json.loads(result.body)
    if isinstance(result, FileResponse):
        return {"file_path": str(result.path),
                "filename": result.filename,
                "media_type": result.media_type}
    if isinstance(result, Response):
        if (result.media_type or "").startswith("image/"):
            return {"mime_type": result.media_type,
                    "data": base64.b64encode(result.body).decode()}   # 🟡 full in memory
        return result.body.decode()
    return jsonable_encoder(result)
```

`NonFiniteSafeJSONResponse` (the `aeroanalysis` NaN guard) **is** a
`JSONResponse` subclass, so its already-sanitised body is parsed normally. A
solver NaN reaching the final `jsonable_encoder` branch on a non-`Response`
return would, however, produce a value MCP's JSON encoder cannot represent. 🟡

### F5 — Dependency hand-off 🟢

```python
# endpoints declaring settings: the tool supplies it
return await _call_endpoint(some_endpoint, aeroplane_id=..., settings=get_settings())

# endpoints declaring request: the tool supplies None
return await _call_endpoint(other_endpoint, request=None, ...)
```

The second form is safe only while the endpoint never dereferences `request`.
Nothing enforces that; an endpoint that starts reading `request.base_url` breaks
MCP **silently**, with no test coverage. 🟡

### F6 — Binary results 🟢

Three tools bypass `_normalize_result`'s byte handling entirely and go through
the asset registry instead:

```
get_aeroplane_three_view      -> register_bytes_asset(png,  kind="img")  -> _asset_payload
analyze_alpha_sweep_diagram   -> register_bytes_asset(png,  kind="img")  -> _asset_payload
download_export_zip           -> register_file_asset(zip_path)           -> _asset_payload
```

so the agent receives a `resource_uri` plus the dual URLs rather than a
multi-megabyte base64 blob. 🟢

## Alternative Flows

- **Endpoint without `db`:** a session is still opened and closed —
  harmless but wasteful. 🟡
- **Endpoint raising `NotFoundError`:** propagates out of `_call_endpoint`
  untranslated; the `with` block still rolls back. 🟡
- **Endpoint raising `HTTPException(503)`** from `Depends(require_cad)` — except
  that the dependency never runs here, so the 503 guard is bypassed and the
  underlying `ImportError` surfaces instead. 🟡
- **Endpoint returning `None`** (every 204 delete): `{"status": "ok"}`,
  regardless of whether anything happened. 🟡
- **Endpoint returning a large image `Response`:** fully base64-encoded in
  memory. 🟡
- **A self-committing service:** the write persists, so the same tool call is
  durable while its neighbours are not. 🟡
- **Concurrent tool calls:** independent sessions, no shared state — but on
  SQLite they contend for the write lock, mitigated by WAL + a 30 s busy
  timeout (`platform-core`). 🟡

## Dependencies

- `app/db/session.SessionLocal` — used **directly**, bypassing `get_db()`.
- Every re-entered v2 endpoint function.
- `app/settings.get_settings()` — hand-passed where an endpoint declares it.
- `fastapi.encoders.jsonable_encoder`, `fastapi.responses.{JSONResponse,
  FileResponse, Response}`.
- The asset registry (same module) for the three binary tools.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Re-enter the endpoint function rather than duplicate logic or self-call over HTTP | `_call_endpoint:96` | 🟢 |
| Inject `db` by signature introspection instead of a registry of dependencies | `inspect.signature(...).parameters` | 🟢 |
| Support both sync and async endpoints via `isawaitable` | l.96 | 🟢 |
| Normalise response objects rather than constrain endpoint return types | `_normalize_result:110` | 🟢 |
| Use a bare `SessionLocal()` instead of the `get_db()` generator | `with SessionLocal() as db:` | 🟢 — **the defect** 🟡 |
| An explicit result for `None` (`Q-MC-5`) | l.110 | 🟡 (previously ambiguity) |
| Move binary payloads out of tool JSON into resources | the three asset tools | 🟢 |

## Internal State

None beyond the per-call session. The bridge is stateless; the only cross-call
state in the module is `ASSET_REGISTRY`. 🟢

## Observability

- 🟡 `_call_endpoint` logs **nothing** — not the endpoint name, not the
  duration, not the exception. An agent-visible failure leaves no server-side
  trace unless the service layer happens to log.
- 🟡 Nothing records that a rollback occurred, which is why TD-01 is invisible
  in production.

## Risks and Gaps

- 🟡 **No commit — writes are silently discarded** (TD-01, G-7). ~40 of the 76
  tools are mutations; each returns a convincing payload built from
  flushed-but-uncommitted ORM state (`expire_on_commit=False` makes it fully
  readable after the rollback).
- 🟡 **Durability is inconsistent**: self-committing services persist, so an
  agent cannot form a simple mental model.
- 🟡 **No test drives a real endpoint through a real session** — the exact gap
  that let the defect ship.
- 🟡 **`_call_endpoint` maps domain exceptions to the single envelope** (`Q-MC-4`, derived). Previously **service exceptions are not translated**, so an agent gets a Python
  message instead of a machine-readable error.
- 🟡 **`None → {"status": "ok"}`** conflates a no-op with a success.
- 🟡 **Image bodies are base64-encoded in full in memory.**
- 🟡 **Nothing is logged on this path.**
- 🟡 **`request=None` is a latent break**: an endpoint that starts using the
  request object fails only through MCP, silently.
- 🟡 **`Depends(require_cad)` / `require_aerosandbox` never run**, so the clean
  503 the REST surface returns becomes a raw `ImportError` here.
- 🟡 **The session is opened even for endpoints that do not need it.**
