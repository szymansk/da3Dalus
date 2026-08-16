# platform-core / transaction-and-error-handling — Technical Design

> Use-case design. Parent module: [`../design.md`](../design.md).
> Contract tables: [`../contracts.md`](../contracts.md) §"Transaction contract"
> and §"Error contract".

## Interface

```python
# app/db/session.py
SQLALCHEMY_DATABASE_URL: str          # bare os.getenv, default sqlite:///./db/test.db
engine:       Engine
SessionLocal: sessionmaker            # expire_on_commit=False, autocommit=False, autoflush=False
def get_db() -> Session               # generator dependency

# app/core/exceptions.py
class ServiceException(Exception):    # .message, .details (dict, never None)
class NotFoundError(ServiceException) # (message?, details?, entity?, resource_id?)
class ValidationError(ServiceException)
class ValidationDomainError(ValidationError)
class ConflictError(ServiceException)
class InternalError(ServiceException)

# app/main.py
def _safe_json(value)                                     # l.269
async def service_exception_handler(request, exc)         # l.274
async def integrity_error_handler(request, exc)           # l.310
async def request_validation_exception_handler(request, exc)  # l.324

# app/core/json_safe.py
class NonFiniteSafeJSONResponse(JSONResponse)
def replace_nonfinite(value) -> tuple[Any, int]
```

## Main Flow

### F1 — The transaction boundary 🟢

```python
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
        db.commit()          # AFTER the endpoint returns and the response body is produced
    except Exception:
        db.rollback()
        raise                # so the exception handlers still see it
    finally:
        db.close()
```

Three consequences worth stating explicitly:

1. **The commit happens after the response body is produced.** For a
   `StreamingResponse` that means *after the generator is fully consumed* — the
   copilot SSE turn therefore holds the session for the whole turn and loses its
   write on a client disconnect. 🔴
2. **The `raise` is load-bearing.** Swallowing here would turn every service
   error into a 200.
3. **Services must never commit**, because a mid-request commit would make the
   rollback path unable to undo the earlier half.

### F2 — Session and engine configuration 🟢

```python
_is_sqlite = SQLALCHEMY_DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    connect_args = {"check_same_thread": False,   # asyncio.to_thread workers cross threads
                    "timeout": 30}                # block up to 30s on a locked DB

engine = create_engine(URL, **kwargs)

SessionLocal = sessionmaker(bind=engine, class_=Session,
                            expire_on_commit=False,   # ORM objects usable after commit
                            autocommit=False,
                            autoflush=False)          # services flush EXPLICITLY

@event.listens_for(Engine, "connect")     # SQLite only
def _set_sqlite_pragmas(dbapi_connection, _connection_record):
    PRAGMA journal_mode=WAL
    PRAGMA synchronous=NORMAL
    PRAGMA busy_timeout=30000
```

The docstring states the reason for WAL: *"the assumption recompute keeps a
write transaction open for several seconds"*, so without WAL a parallel write —
e.g. the user clicking "Use calc" while a recompute is in flight — fails with
*"database is locked"*. 🟢

`expire_on_commit=False` has a second-order effect worth recording: after a
commit **or a rollback**, ORM objects remain readable from the identity map.
That is convenient for endpoints returning the object they just wrote, and it is
precisely what makes the MCP write bug (`mcp-server` TD-01) look like a
success. 🔴

### F3 — The exception hierarchy 🟢

```python
class ServiceException(Exception):
    def __init__(self, message, details=None):
        super().__init__(message)
        self.message = message
        self.details = details or {}          # never None on the exception

class NotFoundError(ServiceException):
    def __init__(self, message=None, details=None, entity=None, resource_id=None):
        if entity is not None:
            final_message = message or f"{entity} not found"
            final_details = details or {}
            if resource_id is not None:
                final_details = {**final_details,
                                 "id": str(resource_id), "entity": entity}
            super().__init__(final_message, final_details)
            return
        super().__init__(message or "Resource not found", details)
```

`ValidationError`, `ValidationDomainError` (a subclass, so a single `isinstance`
check catches both), `ConflictError` and `InternalError` are plain subclasses. 🟢

### F4 — Translation 🟢

```python
def _safe_json(value):
    return jsonable_encoder(value, custom_encoder={BaseException: lambda e: str(e)})

@app.exception_handler(ServiceException)
async def service_exception_handler(request, exc):
    NotFoundError                       -> 404 "not_found"        logger.info(exc.details)
    ValidationError|ValidationDomainErr -> 422 "validation_error"  logger.info(exc.details)
    ConflictError                       -> 409 "conflict"          logger.info(exc.details)
    InternalError                       -> 500 "internal_error"    logger.exception
    (bare ServiceException)             -> 500 "service_error"     logger.exception

    return JSONResponse(status_code, {"error": {
        "code": error_code,
        "message": exc.message,
        "details": _safe_json(exc.details) if exc.details else None}})
```

The `isinstance` order matters: `ValidationDomainError` is checked as part of the
`(ValidationError, ValidationDomainError)` tuple, and `InternalError` before the
bare-`ServiceException` fallback. 🟢

```python
@app.exception_handler(IntegrityError)          # sqlalchemy.exc
-> 409 {"error": {"code": "conflict", "message": "name existiert bereits",
                  "details": None}}             # 🟢 translated (Q-CC-5); handler removed from the aeroplane path (Q-AC-2)

@app.exception_handler(RequestValidationError)  # fastapi.exceptions
-> 422 {"error": {"code": "validation_error", "message": "Ungültige Eingabedaten",
                  "details": _safe_json(exc.errors())}}   # 🟢 translated (Q-CC-5)
```

Both handlers are registered on the **module-level `app`** (`main.py:274-336`),
not inside `create_app()`, so an app built by a second `create_app()` call in a
test has **no** handlers. 🟡

### F5 — One contract 🟢 (`Q-CC-3`)

```python
# app/api/v2/endpoints/aeroplane/copilot_history.py (and versioning.py, …)
def _raise_http(exc: ServiceException) -> None:
    NotFoundError                -> HTTPException(404, detail=exc.message)
    Validation(Domain)Error      -> HTTPException(422, detail=exc.message)
    ConflictError                -> HTTPException(409, detail=exc.message)
    otherwise                    -> HTTPException(500, detail=exc.message)

def _call(func, *args, **kwargs):
    try:                          return func(*args, **kwargs)
    except ServiceException as e: _raise_http(e)
    except Exception as e:        raise HTTPException(500, f"Unexpected error: {e}")
```

Because the endpoint catches the exception itself, the global handler never
runs and the body is FastAPI's `{"detail": …}`. The status codes agree; the
**shape** does not. The catch-all branch is also **not logged**. 🔴

### F6 — Non-finite rendering 🟢

```python
class NonFiniteSafeJSONResponse(JSONResponse):
    def render(self, content):
        safe, count = replace_nonfinite(content)
        if count:
            logger.warning("Replaced %d non-finite value(s) with null", count)
        return super().render(safe)

def replace_nonfinite(value):
    dict  -> recurse over values
    list  -> recurse
    tuple -> recurse, return a LIST (JSON has no tuple)
    bool  -> unchanged        # checked BEFORE float: bool is an int subclass
    float | np.floating -> None if not isfinite else float(value)
                            # numpy floats are NOT float subclasses — explicit branch
    else  -> unchanged
```

Starlette renders with `json.dumps(allow_nan=False)`, so without this class a NaN
from a degenerate geometry (`length³/volume` with zero volume) or a `log10(0)`
would raise inside the response and become an unhandled 500. The docstring
states the philosophy: `null` is *"an honest 'no value', never a fabricated
fallback number that would hide the underlying design problem"* (ADR 0012). 🟢

Used as `default_response_class` on **`aeroanalysis` only** — 🟢 becomes app-wide (`Q-PC-1`).

## Alternative Flows

- **Endpoint raises a non-`ServiceException`:** `get_db()` rolls back and
  re-raises; FastAPI's default 500 applies unless a local `_call` caught it
  first. 🟡
- **`IntegrityError` that is not a duplicate name** (FK, NOT NULL, CHECK): 409
  "name existiert bereits" — 🟢 translated (`Q-CC-5`) and the handler removed from the aeroplane path (`Q-AC-2`).
- **`details` containing an unserialisable object other than an exception:**
  `jsonable_encoder` raises inside the handler → an unhandled 500 while
  reporting a 404. 🟡
- **Two commits in one request** (a service that violates ADR 0009): the second
  half can no longer be rolled back — this is why the rule exists. 🟡
- **A streaming response:** the commit happens after the stream is consumed; a
  disconnect loses it. 🔴
- **SQLite lock contention beyond 30 s:** the driver raises
  `OperationalError: database is locked` → 500. 🟡
- **A NaN from an unprotected router:** 🟢 covered once `NonFiniteSafeJSONResponse` is app-wide (`Q-PC-1`).
- **A local `_call` catches first:** 🟢 the local mappers are deleted (`Q-CC-3`).

## Dependencies

- SQLAlchemy (`create_engine`, `sessionmaker`, `event`, `Engine`,
  `exc.IntegrityError`).
- FastAPI (`JSONResponse`, `jsonable_encoder`, `RequestValidationError`,
  exception handlers).
- `numpy` — only for the `np.floating` branch in `json_safe`.
- Every service in the system, which is written against `get_db()`'s guarantee.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Put the transaction boundary in the dependency, not in the services | `get_db()`; ADR 0009 | 🟢 |
| `autoflush=False` — make flushing an explicit act | `SessionLocal` | 🟢 |
| `expire_on_commit=False` — keep ORM objects usable after commit | `SessionLocal` | 🟢 (a 🟡 side effect for MCP) |
| WAL + 30 s busy timeout instead of shortening the write transaction | the pragma docstring | 🟢 |
| A typed service-exception hierarchy translated centrally | `exceptions.py` + `main.py:274` | 🟢 |
| A convenience constructor that builds both message and `details` | `NotFoundError` | 🟢 |
| Serialise exceptions inside `details` rather than risk a handler crash | `_safe_json` | 🟢 |
| Split log levels by status class | the handler branches | 🟢 |
| Render non-finite floats as `null`, never a fabricated fallback | `json_safe` docstring; ADR 0012 | 🟢 |
| Check `bool` before `float` and handle `np.floating` explicitly | `replace_nonfinite` | 🟢 |
| Register handlers on the module-level app rather than inside `create_app` | `main.py:274` | 🟡 |
| Allow per-module `_raise_http` helpers to bypass the envelope | `versioning.py`, `copilot_history.py` | 🟡 |

## Internal State

| State | Where | Lifecycle |
|---|---|---|
| `engine` and its connection pool | `db/session.py` | process-wide |
| the SQLite pragma listener | `Engine.connect` event | applied to every new connection |
| the per-request `Session` | `get_db()` | one per request; closed in `finally` |
| the identity map | inside each `Session` | survives commit **and rollback** (`expire_on_commit=False`) |

## Observability

- `logger.info` with `exc.details` for 404/409/422. 🟢
- `logger.exception` for 500s. 🟢
- `logger.warning("Replaced %d non-finite value(s) with null", count)`. 🟢
- 🔴 The per-module `_call` catch-all logs **nothing**.
- 🔴 No request-correlation id, so a 4xx INFO line cannot be tied to the 5xx it
  preceded.
- 🔴 Nothing records rollbacks, lock waits or transaction duration — the three
  signals that would have surfaced both the SQLite contention that forced WAL
  and the MCP commit defect.

## Risks and Gaps

- 🟢 **One error envelope everywhere; the per-module mappers are deleted** (`Q-CC-3`, maintainer-answered). Previously** — the global `{"error": {…}}` and the per-module
  `{"detail": …}`. A client must handle both.
- 🔴 **German messages** in the `IntegrityError` and `RequestValidationError`
  handlers, in an English product with an explicit English-only UI rule.
- 🔴 **`IntegrityError → "name existiert bereits"`** hides FK, NOT-NULL and
  CHECK violations behind a duplicate-name message.
- 🔴 **`NonFiniteSafeJSONResponse` protects one router**; `operating_points`,
  `section_aoa`, `airfoils`, the powertrain and speed-polar routers can still
  500 on a NaN.
- 🔴 **A streaming endpoint commits only after full consumption**, so a
  disconnect loses the work (copilot SSE).
- 🔴 **`mcp_server._call_endpoint` bypasses `get_db()`** and never commits
  (TD-01).
- 🔴 **The per-module `_call` catch-all does not log.**
- 🟡 **Handlers registered outside `create_app()`** — a test-built app behaves
  differently on errors.
- 🟡 **`details` with a non-exception unserialisable object** can still crash the
  handler.
- 🟡 **`expire_on_commit=False`** makes rolled-back objects look live, which is
  exactly how the MCP defect stayed invisible.
