# platform-core / transaction-and-error-handling

> Use-case specification. Parent module: [`../requirements.md`](../requirements.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.

## Overview

Two guarantees every other module is written against: **one request is one
transaction** (`get_db()` commits on success, rolls back on exception), and
**every service-layer failure becomes a typed HTTP response** through the
`ServiceException` hierarchy and its global handlers. 🟢

Plus a third, narrower one: a non-finite float must render as `null`, never
crash the response (ADR 0012). 🟢

## Responsibilities

- Own the engine, its SQLite pragmas, `SessionLocal` and `get_db()`. 🟢
- Own `ServiceException` and its five subclasses. 🟢
- Translate them into the `{"error": {code, message, details}}` envelope. 🟢
- Translate `IntegrityError` and `RequestValidationError`. 🟢
- Render non-finite floats as `null` with a WARNING. 🟢

## Business Rules

- **BR-78 / ADR 0009 — `get_db()` owns the transaction boundary.** 🟢
  `yield` → `commit` → `rollback` on exception → `close` in `finally`. Services
  call `db.add()` / `db.flush()` and **never** `db.commit()` / `db.begin()`.
  Four paths legitimately own their own session: the two lifespan seeders,
  `_recompute_sync` and `JobTracker._run_backfill_for_names`.
  🔴 One illegitimate: `mcp_server._call_endpoint`.
- **BR-79 — `autoflush=False`.** 🟢 Together with `expire_on_commit=False` and
  `autocommit=False`. Services must flush explicitly before a query can see
  their pending writes — the reason `db.flush()` appears throughout the version
  and copilot services.
- **BR-80 — SQLite runs in WAL with a 30 s busy timeout.** 🟢
  `connect_args={"check_same_thread": False, "timeout": 30}`, plus an
  `Engine.connect` listener setting `journal_mode=WAL`, `synchronous=NORMAL`,
  `busy_timeout=30000`. Reason (from the comment): the assumption recompute
  holds a write transaction for several seconds while AeroBuildup runs, and
  without WAL a parallel write fails with *"database is locked"*.
- **BR-PC37 — `check_same_thread=False` is required** because
  `asyncio.to_thread` workers cross threads. 🟢
- **BR-PC20 — One hierarchy, one envelope.** 🟢
  ```
  ServiceException(message, details or {})   → 500 "service_error"
  ├── NotFoundError                          → 404 "not_found"
  ├── ValidationError                        → 422 "validation_error"
  │   └── ValidationDomainError              → 422 "validation_error"
  ├── ConflictError                          → 409 "conflict"
  └── InternalError                          → 500 "internal_error"
  ```
- **BR-PC21 — `NotFoundError`'s convenience constructor.** 🟢
  `entity=` builds `"{entity} not found"`; with `resource_id=` it adds
  `{"id": str(resource_id), "entity": entity}` to `details`.
- **BR-PC38 — `details` is never `None` on the exception** (`details or {}`),
  but the **envelope** emits `null` when it is empty. 🟢
- **BR-PC39 — `details` is serialised defensively.** 🟢
  `jsonable_encoder(value, custom_encoder={BaseException: str})` — an exception
  object stored in `details` becomes a string instead of crashing the handler.
- **BR-PC40 — Log levels are split by class.** 🟢 4xx at `logger.info` with the
  `details`; 5xx with `logger.exception`.
- **BR-PC22 — 🟢 All German user-facing strings are translated (`Q-CC-5`, maintainer-answered). Previously two handlers emitted German.
  `IntegrityError → 409 "name existiert bereits"` — which assumes *every*
  integrity violation is a duplicate name, hiding FK, NOT-NULL and CHECK
  violations — and `RequestValidationError → 422 "Ungültige Eingabedaten"`
  (with `exc.errors()` in `details`).
- **BR-PC23 — 🟢 One envelope everywhere; the per-module mappers are deleted (`Q-CC-3`, maintainer-answered). Previously two coexisted: `versioning.py`,
  `copilot_history.py` and others define local `_raise_http` + `_call` helpers
  producing FastAPI's `{"detail": …}`. A client must handle both shapes.
- **BR-PC24 / ADR 0012 — `null` is an honest "no value".** 🟢
  `NonFiniteSafeJSONResponse` recurses dicts/lists/tuples (tuple → list), checks
  `bool` **before** `float`, handles `np.floating` explicitly (numpy floats are
  **not** `float` subclasses), converts `NaN`/±`Inf` to `None` and logs a
  WARNING with the replacement count. The docstring: `null` is *"an honest 'no
  value', never a fabricated fallback number that would hide the underlying
  design problem"*.
- **BR-PC25 — 🟢 `NonFiniteSafeJSONResponse` becomes the app-wide `default_response_class` and declares when it substituted (`Q-PC-1`, maintainer-answered). Previously guarding one router: `aeroanalysis.py:43` only.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Commit after a successful request | Must | The row is visible in a new session |
| RF-02 | Roll back on any exception | Must | Nothing persists |
| RF-03 | Close the session in `finally` | Must | No connection leak |
| RF-04 | Use `autoflush=False`, `expire_on_commit=False`, `autocommit=False` | Must | An unflushed add is invisible to a query |
| RF-05 | Apply the SQLite pragmas on every new connection | Must | WAL, `synchronous=NORMAL`, `busy_timeout=30000` |
| RF-06 | Allow cross-thread connection use on SQLite | Must | `check_same_thread=False` |
| RF-07 | Provide the six exception classes | Must | With the `NotFoundError` convenience constructor |
| RF-08 | Map each to its status and `code` | Must | 404/422/409/500 |
| RF-09 | Emit the `{"error": {code, message, details}}` envelope | Must | `details` is `null` when empty |
| RF-10 | Serialise exceptions inside `details` | Must | No handler crash |
| RF-11 | Log 4xx at INFO with `details`, 5xx with `exception` | Should | Both observed |
| RF-12 | Map `IntegrityError` → 409 | Must | 🟡 message is German and over-general |
| RF-13 | Map `RequestValidationError` → 422 with `exc.errors()` | Must | 🟡 message is German |
| RF-14 | Render `NaN`/±`Inf` as `null` and log the count | Must | Python and numpy floats both |
| RF-15 | Preserve `bool` and normalise `tuple` to a JSON array | Must | `True` stays `true` |
| RF-16 | Apply the safe response class where solver numbers are returned | Should | 🟡 only `aeroanalysis` today |
| RF-17 | Use one error envelope across the API | Should | 🟡 not met |

## Non-functional Requirements

| Type | Inferred requirement | Evidence | Confidence |
|------|----------------------|----------|-----------|
| Integrity | A request either fully applies or fully rolls back | `get_db()` | 🟢 |
| Concurrency | A multi-second write must not lock out readers | WAL + `busy_timeout=30000` | 🟢 |
| Concurrency | Worker threads may reuse the connection | `check_same_thread=False` | 🟢 |
| Predictability | Services flush deliberately, never implicitly | `autoflush=False` | 🟢 |
| Robustness | A handler must not fail while reporting a failure | `_safe_json` | 🟢 |
| Robustness | A NaN must not become an unhandled 500 | `NonFiniteSafeJSONResponse`; ADR 0012 | 🟢 (🟡 one router) |
| Honesty | A missing value is `null`, never a fabricated number | the `json_safe` docstring | 🟢 |
| Consistency | 🟡 Two envelopes and two languages coexist | BR-PC22/BR-PC23 | 🟡 |
| Durability | 🟡 A streaming endpoint commits only after the response is consumed | copilot SSE + `get_db()` | 🟡 |

## Acceptance Criteria

```gherkin
Feature: Transactions

  Scenario: Commit on success
    Given an endpoint that adds a row through get_db
    When the request succeeds
    Then the row is visible from a new session

  Scenario: Rollback on failure
    Given the endpoint raises after adding a row
    Then no row is visible from a new session
    And the exception still reaches the handler

  Scenario: No implicit flush
    Given autoflush is False
    When a service adds a row and immediately queries for it without flushing
    Then the query does not return it

  Scenario: Objects survive the commit
    Given expire_on_commit is False
    When the request completes
    Then attributes of returned ORM objects are still readable

  Scenario: SQLite pragmas
    When a new connection is opened
    Then journal_mode is WAL, synchronous is NORMAL and busy_timeout is 30000

  Scenario: A long write does not lock out a reader
    Given a write transaction held for several seconds
    When a reader queries concurrently
    Then the read succeeds

Feature: The error envelope

  Scenario: Not found
    Given a service raising NotFoundError(entity="Wing", resource_id=7)
    Then the status is 404
    And the body is {"error": {"code": "not_found", "message": "Wing not found",
      "details": {"id": "7", "entity": "Wing"}}}

  Scenario: Conflict
    Given a service raising ConflictError("branch is main")
    Then the status is 409 with code "conflict"

  Scenario: Validation
    Given a service raising ValidationDomainError("bad chord")
    Then the status is 422 with code "validation_error"

  Scenario: Empty details
    Given a ServiceException with no details
    Then the body's details field is null

  Scenario: An exception inside details
    Given details containing an exception object
    Then the response serialises it as a string
    And the handler does not raise

  Scenario: Integrity violation
    Given a NOT NULL violation reaches the handler
    Then the status is 409
    And the message is "name existiert bereits"

  Scenario: A module-local helper wins
    Given an endpoint using its own _raise_http
    When the service raises NotFoundError
    Then the body is {"detail": "..."} and not the envelope

Feature: Non-finite safety

  Scenario: NaN becomes null
    Given an aeroanalysis endpoint returning {"cl": float("nan")}
    Then the body is {"cl": null}
    And one WARNING records the replacement count

  Scenario: numpy floats
    Given a numpy float64 infinity
    Then it renders null

  Scenario: Booleans are preserved
    Given {"ok": True}
    Then the body is {"ok": true}

  Scenario: Tuples become arrays
    Given {"xy": (1.0, 2.0)}
    Then the body is {"xy": [1.0, 2.0]}

  Scenario: An unprotected router still crashes
    Given a NaN returned from the operating-points router
    Then the response is a 500
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|---|---|---|
| `get_db()` semantics (RF-01…RF-03) | Must | ADR 0009 — the contract every service assumes |
| Session flags (RF-04) | Must | `autoflush=False` changes how every service is written |
| SQLite WAL configuration (RF-05/RF-06) | Must | Otherwise normal use produces "database is locked" |
| The hierarchy and the envelope (RF-07…RF-10) | Must | The client's only machine-readable failure contract |
| Defensive `details` serialisation (RF-10) | Must | A crashing handler turns a 404 into a 500 |
| Non-finite rendering (RF-14/RF-15) | Must | ADR 0012 |
| Split log levels (RF-11) | Should | Keeps 4xx noise out of error dashboards |
| Applying the safe response class everywhere (RF-16) | Should | 🟡 one router today |
| One envelope everywhere (RF-17) | Should | 🟡 two shapes today |
| German handler messages | Won't (keep as-is) | 🟡 documented divergence; changing them is a client-visible change |
| Nested/savepoint transactions | Won't | No service uses them; `begin()` is forbidden |
| Per-request retry on a locked DB | Won't | The 30 s busy timeout is the whole strategy |

## Code Traceability

| File | Symbol | Coverage |
|---|---|---|
| `app/db/session.py:8-11` | `SQLALCHEMY_DATABASE_URL` (bare `os.getenv`) | 🟢 🟡 |
| `…:13-26` | SQLite `connect_args` + engine | 🟢 |
| `…:27-33` | `SessionLocal` flags | 🟢 |
| `…:36-52` | the `Engine.connect` pragma listener | 🟢 |
| `…:55-64` | `get_db()` | 🟢 |
| `app/db/base.py` | declarative `Base` | 🟢 |
| `app/core/exceptions.py:11-61` | the six classes | 🟢 |
| `app/main.py:269-271` | `_safe_json` | 🟢 |
| `…:274-307` | `service_exception_handler` | 🟢 |
| `…:310-321` | `integrity_error_handler` 🟡 | 🟢 |
| `…:324-336` | `request_validation_exception_handler` 🟡 | 🟢 |
| `app/core/json_safe.py` | `NonFiniteSafeJSONResponse`, `replace_nonfinite` | 🟢 |
| `app/api/v2/endpoints/aeroanalysis.py:43` | the only `default_response_class` use | 🟢 🟡 |
| `app/api/v2/endpoints/versioning.py`, `…/aeroplane/copilot_history.py` | local `_raise_http` / `_call` → `{"detail": …}` | 🟡 |
| `app/mcp_server.py:96` | the one path that should commit and does not | 🟡 |
