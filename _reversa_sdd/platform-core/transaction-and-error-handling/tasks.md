# platform-core / transaction-and-error-handling — Implementation Tasks

> Parent module task list: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] SQLAlchemy 2.x and FastAPI.
- [ ] A database URL (SQLite by default; PostgreSQL is also targeted).
- [ ] `numpy` (only for the `np.floating` branch).

## Tasks

- [ ] **T-01 — Engine + SQLite pragmas.**
  Read `SQLALCHEMY_DATABASE_URL` (bare `os.getenv`, default
  `sqlite:///./db/test.db`); on SQLite add
  `connect_args={"check_same_thread": False, "timeout": 30}` and an
  `Engine.connect` listener issuing `PRAGMA journal_mode=WAL`,
  `PRAGMA synchronous=NORMAL`, `PRAGMA busy_timeout=30000`.
  - Legacy origin: `app/db/session.py:1-52`
  - Definition of done: a test queries `PRAGMA journal_mode` on a fresh
    connection and gets `wal`. **Carry both comments** — `check_same_thread`
    exists because `asyncio.to_thread` workers cross threads, and WAL exists
    because the recompute holds a write transaction for several seconds.
  - Confidence: 🟢

- [ ] **T-02 — `SessionLocal`.**
  `sessionmaker(bind=engine, class_=Session, expire_on_commit=False,
  autocommit=False, autoflush=False)`.
  - Legacy origin: `app/db/session.py:27-33`
  - Definition of done: a test proves an unflushed `add` is invisible to a
    query — `autoflush=False` is the single flag that most shapes how services
    are written.
  - Confidence: 🟢

- [ ] **T-03 — `get_db()`.**
  `yield` → `commit` → `except: rollback; raise` → `finally: close`.
  - Legacy origin: `app/db/session.py:55-64`; ADR 0009
  - Definition of done: commit-on-success and rollback-on-failure tests, plus a
    test that the exception still reaches the handler (the `raise` is
    load-bearing). Document the four legitimate own-session paths and the one
    illegitimate one (`mcp_server._call_endpoint`).
  - Confidence: 🟢

- [ ] **T-04 — The exception hierarchy.**
  `ServiceException(message, details or {})`; `NotFoundError` with the
  `entity=` / `resource_id=` convenience constructor; `ValidationError`,
  `ValidationDomainError(ValidationError)`, `ConflictError`, `InternalError`.
  - Legacy origin: `app/core/exceptions.py`
  - Definition of done: `NotFoundError(entity="Wing", resource_id=7)` yields
    `"Wing not found"` and `{"id": "7", "entity": "Wing"}`;
    `ValidationDomainError` is caught by an `isinstance(..., ValidationError)`
    check.
  - Confidence: 🟢

- [ ] **T-05 — `_safe_json`.**
  `jsonable_encoder(value, custom_encoder={BaseException: lambda e: str(e)})`.
  - Legacy origin: `app/main.py:269-271`
  - Definition of done: `details` containing an exception object serialises. A
    handler that crashes while reporting an error turns a 404 into a 500 — this
    one line prevents it.
  - Confidence: 🟢

- [ ] **T-06 — `service_exception_handler`.**
  Branch in order: `NotFoundError` → 404 `not_found`;
  `(ValidationError, ValidationDomainError)` → 422 `validation_error`;
  `ConflictError` → 409 `conflict`; `InternalError` → 500 `internal_error`;
  else → 500 `service_error`. 4xx `logger.info(exc.details)`, 5xx
  `logger.exception`. Body:
  `{"error": {"code", "message", "details": _safe_json(details) or None}}`.
  - Legacy origin: `app/main.py:274-307`
  - Definition of done: one test per branch, plus one asserting `details` is
    `null` when empty.
  - Confidence: 🟢

- [ ] **T-07 — `integrity_error_handler` and
  `request_validation_exception_handler`.**
  409 `{"code": "conflict", "message": "name existiert bereits", "details":
  null}` and 422 `{"code": "validation_error", "message": "Ungültige
  Eingabedaten", "details": _safe_json(exc.errors())}`.
  - Legacy origin: `app/main.py:310-336`
  - Definition of done: reproduced verbatim **and recorded as gaps** — both
    messages are German in an English product, and the `IntegrityError` message
    assumes every violation is a duplicate name. Add a characterisation test
    using a NOT NULL violation.
  - Confidence: 🟢

- [ ] **T-08 — `replace_nonfinite` + `NonFiniteSafeJSONResponse`.**
  Recurse dicts/lists/tuples (tuple → list); check `bool` **before** `float`;
  explicit `np.floating` branch; `NaN`/±`Inf` → `None`; return
  `(safe, count)`; the response class logs one WARNING with the count.
  - Legacy origin: `app/core/json_safe.py` (92 l.); ADR 0012
  - Definition of done: five tests — Python NaN, numpy NaN, `+Inf`, a `bool`
    that must stay a bool, and a tuple that must become an array. Carry the
    docstring's philosophy: `null` is an honest "no value", never a fabricated
    fallback.
  - Confidence: 🟢

- [ ] **T-09 — Wire the safe response class.**
  `default_response_class=NonFiniteSafeJSONResponse` on the router(s) that
  return solver numbers.
  - Legacy origin: `app/api/v2/endpoints/aeroanalysis.py:43`
  - Definition of done: reproduce the single use **and record** that
    `operating_points`, `section_aoa`, `airfoils`, the powertrain and
    speed-polar routers are unprotected. Add a characterisation test showing a
    NaN from an unprotected router produces a 500.
  - Confidence: 🟢

- [ ] **T-10 — `Base`.**
  `@as_declarative` with the implicit `id` column and
  `__tablename__ = cls.__name__.lower()`.
  - Legacy origin: `app/db/base.py`
  - Definition of done: reproduced; record that essentially every model
    overrides `__tablename__` because the default would be `aeroplanemodel`.
  - Confidence: 🟢

### Remediation (behaviour changes — each needs a decision)

- [ ] **T-11 — Unify the error envelope.**
  Remove the per-module `_raise_http` / `_call` helpers (`versioning.py`,
  `copilot_history.py`, …) so every error goes through the global handler.
  - Legacy origin: BR-PC23
  - Definition of done: every 4xx/5xx body is `{"error": {…}}`. This is a
    **client-visible** change — the frontend's `lib/parseApiError.ts` currently
    papers over both shapes.
  - Confidence: 🟡 (a decision)

- [ ] **T-12 — Translate the German messages and narrow the `IntegrityError`
  handler.**
  Distinguish unique-constraint violations from FK / NOT NULL / CHECK.
  - Legacy origin: `app/main.py:310-321`
  - Definition of done: a NOT NULL violation no longer claims a duplicate name.
  - Confidence: 🟡 (a decision)

- [ ] **T-13 — Apply non-finite safety app-wide.**
  Make `NonFiniteSafeJSONResponse` the app's `default_response_class`.
  - Legacy origin: BR-PC25
  - Definition of done: a NaN from any router renders `null` with a WARNING.
    Verify the overhead on large payloads before adopting.
  - Confidence: 🟡 (a decision)

- [ ] **T-14 — Log the per-module catch-all.**
  The local `_call` helpers swallow unexpected exceptions into a 500 without
  logging.
  - Legacy origin: `versioning.py`, `copilot_history.py`
  - Definition of done: every 500 leaves a server-side traceback.
  - Confidence: 🟡 (a decision)

## Test Tasks

- [ ] **TT-01 — Commit:** a successful request persists.
- [ ] **TT-02 — Rollback:** a failing request persists nothing and the exception
      still reaches the handler.
- [ ] **TT-03 — Close:** the session is closed even on failure.
- [ ] **TT-04 — `autoflush=False`:** an unflushed add is invisible to a query.
- [ ] **TT-05 — `expire_on_commit=False`:** attributes readable after commit.
- [ ] **TT-06 — Pragmas:** WAL, `synchronous=NORMAL`, `busy_timeout=30000`.
- [ ] **TT-07 — Concurrent reader:** a read succeeds while a multi-second write
      transaction is open.
- [ ] **TT-08 — Envelope:** one test per exception class, with `code`, `message`
      and `details`.
- [ ] **TT-09 — Empty details:** `null` in the body.
- [ ] **TT-10 — Exception in details:** serialises; the handler does not raise.
- [ ] **TT-11 — Log levels:** 4xx INFO, 5xx `exception`.
- [ ] **TT-12 — `IntegrityError` (characterisation):** a NOT NULL violation
      returns 409 "name existiert bereits".
- [ ] **TT-13 — `RequestValidationError`:** 422 with `exc.errors()` in
      `details`.
- [ ] **TT-14 — Non-finite:** Python NaN, numpy NaN, `+Inf`, `bool`, tuple.
- [ ] **TT-15 — WARNING count:** the replacement count is logged once.
- [ ] **TT-16 — Unprotected router (characterisation):** a NaN produces a 500.
- [ ] **TT-17 — Competing envelope (characterisation):** a `versioning` 404 is
      `{"detail": …}`, not `{"error": {…}}`.

## Suggested Order

1. **T-01 → T-03** the persistence foundation. `get_db()` before anything else:
   every other test in the repository runs inside it.
2. **T-10** `Base`, trivially, so models can be defined.
3. **T-04 → T-06** the hierarchy, `_safe_json`, then the main handler. T-05
   before T-06 — the defensive encoder is what keeps the handler from failing.
4. **T-07** the two extra handlers, each with a characterisation test.
5. **T-08 → T-09** non-finite safety, with the single-router wiring reproduced
   and its gap recorded.
6. **T-11 → T-14** the remediations. T-11 (envelope unification) is the largest:
   it changes the wire format for the versioning and copilot-history routes and
   requires a coordinated frontend change.

## Pending Gaps

- **Which error envelope is authoritative?** The global `{"error": {…}}` or the
  per-module `{"detail": …}`? Today clients handle both, via
  `frontend/lib/parseApiError.ts`.
- **Should the German handler messages be translated**, given the project's
  explicit English-only UI rule?
- **Should `IntegrityError` distinguish violation kinds** instead of claiming
  every one is a duplicate name?
- **Should `NonFiniteSafeJSONResponse` be the app-wide default response class?**
- **Should the per-module `_call` catch-all log** before returning a 500?
- **How should a streaming endpoint commit?** Today the commit waits for full
  consumption, so a disconnect loses the work.
- **Should `mcp_server._call_endpoint` use `get_db()`'s semantics?** It is the
  one path that bypasses this contract (TD-01).
- **Should the exception handlers move inside `create_app()`** so a
  test-constructed app behaves identically?
- **Should transaction duration, rollbacks and lock waits be instrumented?**
  None of the three is observable today.
