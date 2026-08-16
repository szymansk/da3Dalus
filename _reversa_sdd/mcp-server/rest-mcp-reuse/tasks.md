# mcp-server / rest-mcp-reuse — Implementation Tasks

> Parent module task list: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] `app/db/session.SessionLocal` with `expire_on_commit=False`,
      `autoflush=False`, and the `get_db()` contract it bypasses (ADR 0009).
- [ ] The v2 endpoint functions being re-entered, each a plain
      `def` / `async def` taking Pydantic parameters.
- [ ] `fastapi.encoders.jsonable_encoder` and the response classes.
- [ ] `app/settings.get_settings()`.

## Tasks

- [ ] **T-01 — `_call_endpoint`.**
  `with SessionLocal() as db:`; inject `db` iff
  `"db" in inspect.signature(endpoint_fn).parameters`; call; `await` when
  `inspect.isawaitable`; return `_normalize_result(result)`.
  - Legacy origin: `app/mcp_server.py:96`
  - Definition of done: injection follows the signature in both directions;
    sync and async endpoints both work. **Reproduce the absent commit** and
    record it as TD-01 — the remediation is T-07, gated by its own test.
  - Confidence: 🟢

- [ ] **T-02 — `_normalize_result`.**
  Six branches: `None`, `JSONResponse`, `FileResponse`, image `Response`, other
  `Response`, fallback `jsonable_encoder`.
  - Legacy origin: `app/mcp_server.py:110`
  - Definition of done: one test per branch. Note that
    `NonFiniteSafeJSONResponse` is a `JSONResponse` subclass and must take the
    parsed-body branch, and record that `None → {"status": "ok"}` hides a
    no-op.
  - Confidence: 🟢

- [ ] **T-03 — Tool bodies: the delegation shape.**
  Local import of the endpoint function, then
  `await _call_endpoint(fn, **params)`.
  - Legacy origin: `app/mcp_server.py` (all 76)
  - Definition of done: no tool contains business logic, a query or a
    conversion — anything beyond parameter pass-through belongs in the service.
  - Confidence: 🟢

- [ ] **T-04 — Hand-supplied dependencies.**
  Pass `settings=get_settings()` where the endpoint declares it; pass
  `request=None` where it declares a `Request`.
  - Legacy origin: `app/mcp_server.py` (several bodies)
  - Definition of done: enumerate every such call site in a comment or table.
    Record the `request=None` sites as a latent break — they work only while the
    endpoint never dereferences the request.
  - Confidence: 🟢 / 🟡

- [ ] **T-05 — Binary tools route through the registry.**
  `get_aeroplane_three_view` and `analyze_alpha_sweep_diagram` via
  `register_bytes_asset`; `download_export_zip` via `register_file_asset`; all
  three return `_asset_payload(entry)`.
  - Legacy origin: `app/mcp_server.py`
  - Definition of done: none of the three returns raw bytes or a base64 blob;
    each returns `resource_uri` plus both URLs.
  - Confidence: 🟢

- [ ] **T-06 — Characterisation tests for the current behaviour.**
  Pin: a write through a real session is **lost**; a self-committing service
  **persists**; a `NotFoundError` escapes untranslated; a `None` return becomes
  `{"status": "ok"}`.
  - Legacy origin: `app/mcp_server.py:96`; `app/services/aeroplane_service.py`
  - Definition of done: these tests **document a defect**. Label them as
    characterisation so nobody "fixes" the test instead of the code.
  - Confidence: 🟢

### Remediation (behaviour change — each needs a decision)

- [ ] **T-07 — Commit on success.**
  Replace the bare context manager with commit-on-success /
  rollback-on-exception, mirroring `get_db()`.
  - Legacy origin: `app/mcp_server.py:96`; `app/db/session.py:55-64`; TD-01
  - Definition of done: **write the failing test first** —
    `create_aeroplane_tool` against a real database, asserted from a *second*
    session — then change `_call_endpoint`. Re-check the self-committing
    services for double-commit or nested-transaction problems.
  - Confidence: 🟡 (a decision)

- [ ] **T-08 — Translate service exceptions.**
  Catch `ServiceException` and map it to a structured MCP error carrying the
  same `code` / `message` / `details` the REST envelope would have used.
  - Legacy origin: `app/main.py:274-307`
  - Definition of done: an unknown aeroplane produces a machine-readable
    not-found result rather than a raw Python exception.
  - Confidence: 🟡 (a decision)

- [ ] **T-09 — Distinguish a no-op from a success.**
  Decide what `None` should mean for a delete that matched nothing.
  - Legacy origin: `app/mcp_server.py:110`
  - Definition of done: a delete of a non-existent id is distinguishable from a
    successful one, on both REST and MCP.
  - Confidence: 🟡 (a decision)

- [ ] **T-10 — Instrument the bridge.**
  Log the endpoint name, duration and outcome; count calls and failures.
  - Legacy origin: — (nothing exists)
  - Definition of done: an MCP call leaves a server-side trace. Without this,
    a defect like TD-01 is invisible in production.
  - Confidence: 🟡 (a decision)

## Test Tasks

- [ ] **TT-01 — Injection:** `db` passed iff declared.
- [ ] **TT-02 — Await:** async endpoint resolved.
- [ ] **TT-03 — Normalisation:** six branches.
- [ ] **TT-04 — `NonFiniteSafeJSONResponse`:** takes the `JSONResponse` branch.
- [ ] **TT-05 — Durability (currently failing):** real endpoint, real session,
      asserted from a second session.
- [ ] **TT-06 — Self-committing service (characterisation):** `trim_operating_point`
      persists while `create_aeroplane` does not.
- [ ] **TT-07 — Exception passthrough (characterisation):** raw `NotFoundError`.
- [ ] **TT-08 — Binary tools:** `resource_uri` + dual URLs; file under `tmp/`.
- [ ] **TT-09 — Extra dependencies:** a `settings`-declaring endpoint works.
- [ ] **TT-10 — Isolation:** two sequential tool calls do not share ORM state.

## Suggested Order

1. **TT-05 first.** Write the durability test before touching anything. It is
   the test whose absence allowed ~40 tools to ship broken, and it must be seen
   failing.
2. **T-01 → T-02** the bridge and the normaliser, characterising the legacy
   exactly (no commit yet).
3. **T-06** the characterisation suite, so the current contract is pinned before
   it changes.
4. **T-03 → T-05** the tool bodies, grouped by domain; the three binary tools
   after the asset registry exists.
5. **T-07** the commit — the single highest-value change in the module. Re-run
   the whole MCP suite afterwards, paying attention to the self-committing
   services.
6. **T-08 → T-10** error translation, no-op semantics and instrumentation, in
   that order: errors first because an agent cannot act on a Python message.

## Pending Gaps

- **Should `_call_endpoint` commit?** Today ~40 mutation tools return success
  and persist nothing (TD-01, G-7).
- **What happens to the self-committing services once a commit is added** — is a
  nested commit safe, or should those services be normalised to flush-only?
- **Should service exceptions become structured MCP errors?**
- **Should `None` keep meaning `{"status": "ok"}`?** A delete that matched
  nothing is currently indistinguishable from one that worked.
- **Should the bridge synthesise a minimal `Request`** instead of passing
  `None`, so an endpoint that starts using it does not break silently?
- **Should capability guards (`require_cad` / `require_aerosandbox`) be applied**
  on this path, so an agent gets the same clean 503 a browser would?
- **Should the bridge log and count invocations?** Today nothing on this path is
  observable.
- **Should large image responses stream** rather than base64-encode in memory?
