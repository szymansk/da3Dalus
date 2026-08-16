# mcp-server / rest-mcp-reuse

> Use-case specification. Parent module: [`../requirements.md`](../requirements.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.

## Overview

Every MCP tool is a **thin re-entry into the FastAPI endpoint function** that
already implements the behaviour. One 8-line bridge — `_call_endpoint` — opens a
session, injects it if the endpoint declares one, awaits the result and
normalises it into MCP JSON. 🟢

The reuse is genuinely good architecture: no logic is duplicated, and 76 tools
cost almost no additional code. The **execution context**, however, is not the
one the endpoints were written for — and one missing line makes ~40 of those
tools lie about what they did. 🟡

## Responsibilities

- Call an endpoint function in-process with a fresh session. 🟢
- Inject `db` by signature introspection; let the tool supply anything else. 🟢
- Await an awaitable result. 🟢
- Normalise FastAPI response objects and ORM/Pydantic values into MCP JSON. 🟢
- Route binary artefacts through the asset registry instead of tool JSON. 🟢

**NOT this use case:** the business logic (owned by the services), the schemas
(owned by the endpoints' modules), and the tool declarations
(→ [`../tool-registration`](../tool-registration/requirements.md)).

## Business Rules

- **BR-MCP6 — One bridge function.** 🟢
  ```python
  async def _call_endpoint(endpoint_fn, **kwargs):        # l.96
      with SessionLocal() as db:
          if "db" in inspect.signature(endpoint_fn).parameters:
              kwargs["db"] = db
          result = endpoint_fn(**kwargs)
          if inspect.isawaitable(result): result = await result
          return _normalize_result(result)
  ```
- **BR-MCP7 — 🟡 There is no commit.** `Session.__exit__` calls `close()`,
  which **rolls back**. REST gets its commit from `get_db()`; this path has no
  equivalent, so every endpoint that relies on the framework boundary persists
  nothing (BR-78 / ADR 0009).
- **BR-MCP20 — Durability is inconsistent, not merely absent.** 🟢
  | Path | Persists |
  |---|---|
  | reads | yes |
  | writes relying on `get_db()`'s commit (~40 tools) | **no** |
  | services that commit themselves (`retrim_service`, `operating_point_generator_service`, `tessellation_service`) | yes |
  | filesystem writes (`upload_airfoil_datfile`, exports) | yes |
- **BR-MCP8 — Only `db` is auto-injected.** 🟢 Other `Depends(...)` parameters
  must be supplied by the tool: several pass `settings=get_settings()`, some pass
  `request=None`. 🟡 The latter is safe only while no re-entered endpoint touches
  the request object.
- **BR-MCP9 — Everything else FastAPI does is bypassed.** 🟢 No routing, no
  request-body validation by FastAPI (FastMCP validates against the *handler*
  signature instead), no middleware, no CORS, and — decisively — **no exception
  handlers**, so `NotFoundError` escapes as a raw Python exception. 🟡
- **BR-MCP10 — `_normalize_result` is the response adapter.** 🟢
  `None → {"status":"ok"}` 🔴; `JSONResponse →` parsed body;
  `FileResponse → {file_path, filename, media_type}`; image `Response →` base64
  envelope 🔴; other `Response →` decoded content; else `jsonable_encoder`.
- **BR-MCP11 — Binary results become MCP resources.** 🟢 Three tools return
  `_asset_payload(entry)` rather than bytes.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Open one session per tool call | Must | The session is closed afterwards |
| RF-02 | Inject `db` only when the endpoint declares it | Must | An endpoint without `db` receives no such keyword |
| RF-03 | Await awaitable results | Must | Async endpoints return values, not coroutines |
| RF-04 | Normalise all six result shapes | Must | See BR-MCP10 |
| RF-05 | Let the tool supply non-`db` dependencies | Must | `settings=get_settings()` call sites work |
| RF-06 | Route binary results through the asset registry | Must | `resource_uri` + both URLs returned |
| RF-07 | **Commit successful writes** | Must | 🟢 fixed (`Q-MC-1`) — the defining defect (TD-01) |
| RF-08 | Roll back on exception | Must | Met incidentally — everything is rolled back |
| RF-09 | Translate service exceptions into structured errors | Should | 🟡 decided (`Q-MC-4`, derived) |
| RF-10 | Distinguish a no-op from a success | Should | 🟡 a `None` return gets an explicit result (`Q-MC-5`, derived). Previously `None → {"status":"ok"}` |

## Non-functional Requirements

| Type | Inferred requirement | Evidence | Confidence |
|------|----------------------|----------|-----------|
| Reusability | No endpoint logic may be duplicated for MCP | `_call_endpoint` re-entry | 🟢 |
| Performance | No HTTP round trip, no second event loop | in-process call | 🟢 |
| Correctness | 🟡 A tool's response must reflect what was persisted | violated — flushed-but-uncommitted state is returned | 🟡 |
| Isolation | A tool call must not leak session state into another | one `SessionLocal()` per call | 🟢 |
| Diagnosability | 🟢 Registration gains a log line and duplicate tool names a registration-time assertion (`Q-MC-8`); per-invocation telemetry is not addressed and has no consumer at single-user scale | previously nothing on this path was logged — no invocation, duration or error record | — | 🟡 |
| Compatibility | Endpoints must remain callable as plain functions | every endpoint is a plain `async def` | 🟢 (a coupling: an endpoint that starts depending on `Request` breaks MCP silently) |

## Acceptance Criteria

```gherkin
Feature: In-process re-entry

  Scenario: A read tool returns endpoint data
    Given an aeroplane exists
    When get_all_aeroplanes runs through _call_endpoint
    Then the result contains that aeroplane

  Scenario: db injection follows the signature
    Given an endpoint function declaring db
    Then _call_endpoint passes a session
    Given an endpoint function without db
    Then no db keyword is passed

  Scenario: Async endpoints are awaited
    Given an async endpoint returning {"a": 1}
    Then the tool result is {"a": 1}, not a coroutine

  Scenario: Extra dependencies are supplied by the tool
    Given an endpoint declaring settings
    Then the tool passes settings=get_settings() explicitly

Feature: Result normalisation

  Scenario Outline: Every shape maps
    Given an endpoint returning <input>
    Then the tool result is <output>

    Examples:
      | input                              | output                                     |
      | None                               | {"status": "ok"}                           |
      | JSONResponse({"a": 1})             | {"a": 1}                                   |
      | FileResponse(path)                 | {file_path, filename, media_type}          |
      | Response(png_bytes, image/png)     | a base64 envelope                          |
      | Response(b"text", text/plain)      | "text"                                     |
      | a Pydantic model                   | the jsonable_encoder form                  |

Feature: Durability   # characterisation of TD-01

  Scenario: A write through MCP is lost
    Given no monkeypatching of _call_endpoint
    When create_aeroplane_tool runs against a real database
    And the tool returns a populated aeroplane payload
    Then querying that database in a NEW session finds no such row

  Scenario: A self-committing service does persist
    When trim_operating_point runs through MCP
    Then the trimmed operating point is present in a new session

Feature: Errors

  Scenario: A service exception is not translated
    Given an unknown aeroplane UUID
    When get_aeroplane_by_id runs
    Then a raw NotFoundError propagates
    And no {"error": {"code": "not_found", ...}} envelope is produced

Feature: Binary results

  Scenario: A three-view returns a resource, not bytes
    When get_aeroplane_three_view runs
    Then the result carries resource_uri "img://<id>"
    And url_from_docker_container and url_for_webui
    And the file is under tmp/
```

> The "Durability" and "Errors" scenarios describe **current behaviour**, not
> desired behaviour. They exist so the defect is pinned before it is fixed.

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|---|---|---|
| **Commit on success (RF-07)** | Must | 🟡 the top-severity defect in the system: ~40 tools report success and persist nothing |
| In-process re-entry (RF-01…RF-03) | Must | The reason 76 tools cost so little code |
| Result normalisation (RF-04) | Must | Endpoints legitimately return five different shapes |
| Asset routing (RF-06) | Must | Binary cannot travel as tool JSON |
| Hand-supplied dependencies (RF-05) | Must | Several endpoints need more than `db` |
| Structured errors (RF-09) | Should | An agent cannot branch on a Python exception text |
| No-op vs success (RF-10) | Should | A silently failed delete looks successful |
| A real-endpoint-through-real-session test | Must | The missing test that let TD-01 ship |
| Re-implementing endpoint logic for MCP | Won't | The reuse is the architecture |
| Calling the API over HTTP from the tools | Won't | A second event loop and a self-referential port |

## Code Traceability

| File | Symbol | Coverage |
|---|---|---|
| `app/mcp_server.py:96` | `_call_endpoint` | 🟢 (🟢 fixed (`Q-MC-1`)) |
| `…:110` | `_normalize_result` | 🟢 |
| `…` | tool bodies passing `settings=get_settings()` / `request=None` | 🟢 🟡 |
| `…` | `_asset_payload` and the three binary tools | 🟢 |
| `app/db/session.py:27-33` | `SessionLocal` (`expire_on_commit=False`, `autoflush=False`) | 🟢 owned by `platform-core` |
| `app/db/session.py:55-64` | `get_db()` — the commit this path lacks | 🟢 owned by `platform-core` |
| `app/services/aeroplane_service.py` | `create_aeroplane` — flush-only, explicit "no commit" docstring | 🟢 owned by `aeroplane-core` |
| `app/main.py:274-307` | `service_exception_handler` — registered on the app, **not** on this path | 🟢 owned by `platform-core` |
| `app/tests/test_mcp_server_tools.py:89` | `_call_endpoint` monkeypatched wholesale | 🟡 why no test catches TD-01 |
| `app/tests/test_mcp_server_extended.py:643-673` | `_call_endpoint` exercised with fake local functions | 🟡 same |
