# ADR 0009 — `get_db()` owns the transaction boundary; services never commit

- **Status:** Accepted — in force, with one systematic violation
- **Decided:** early and never revisited; documented in root `CLAUDE.md`, `app/CLAUDE.md` and every service docstring
- **Deciders:** Marc Szymanski (maintainer)
- **Confidence:** 🟢 CONFIRMED (code + three levels of project documentation)

## Context

The service layer is large — 85 modules — and many operations span several tables:
creating an aeroplane touches `aeroplanes` and `branches`; cloning a version
writes 17 tables; applying a copilot edit rewrites a whole wing subtree and then
runs a recompute. If each service committed independently, a partial failure would
leave the aggregate inconsistent, and nothing would define where "the operation"
begins and ends.

## Decision

**The FastAPI dependency `get_db()` is the one transaction boundary** —
`db.commit()` on success, `db.rollback()` on exception, `db.close()` in `finally`
(`app/db/session.py`).

1. **Services call `db.add()` and `db.flush()`; they never call `db.commit()` or
   `db.begin()`.** Stated in root `CLAUDE.md`, `app/CLAUDE.md` and repeated in
   service docstrings.
2. **`autoflush=False`, `expire_on_commit=False`.** Services must flush explicitly
   before a query can see their pending writes — which is why `db.flush()` appears
   throughout the version and copilot services, and why the circular
   `aeroplanes ↔ branches` FK pair needs a deliberate three-step flush dance.
3. **Four paths legitimately own their own session**, because they run outside a
   request: the two lifespan seeders (`seed_default_types`,
   `seed_mission_presets`), `_recompute_sync` (wrapped in `asyncio.to_thread`), and
   `JobTracker._run_backfill_for_names`. `retrim_dirty_ops` likewise opens its own
   `SessionLocal` — it runs from a background job.
4. **SQLite is configured for long write transactions**: WAL journal,
   `synchronous=NORMAL`, `busy_timeout=30000`, `check_same_thread=False`,
   `timeout=30` — because an assumption recompute holds a write transaction open
   for several seconds while AeroBuildup runs, and without WAL a parallel write
   fails with *"database is locked"*.

## Consequences

- One request = one transaction, so a failure anywhere in a multi-table operation
  rolls the whole thing back with no per-service error handling; services compose
  atomically; tests can inspect pending state without commits leaking.
- 🔴 **MCP writes are silently discarded.** `mcp_server._call_endpoint` opens a
  bare `with SessionLocal() as db:` and calls the endpoint function directly — no
  routing, no `Depends`, no `get_db()` — and `Session.__exit__` rolls back, so
  ~40 of the 76 tools return a populated model whose row never reaches the
  database. No test can catch it: the tool tests monkeypatch `_call_endpoint`
  wholesale and the `_call_endpoint` tests use fake local functions. Fixed by the
  [ADR 0007 amendment](0007-copilot-proposes-human-adopts.md) / `Q-MC-1`, which
  gives MCP a `get_db()`-equivalent context manager.
- **`autoflush=False` is a footgun.** A service that queries before flushing reads
  stale state with no error — the copilot apply engine needs `db.expire_all()`
  after wing writes and `db.expunge_all()` before discarding a proposal for
  exactly this reason.
- **Long transactions are the norm**, so a second writer means contention rather
  than an error only because of the 30 s busy timeout.
- 🔴 `SQLALCHEMY_DATABASE_URL` is read with a bare `os.getenv` here, bypassing both
  settings classes and contradicting the documented "no scattered `os.getenv`"
  rule — arguably a bootstrap exception, but not documented as one.

## Related

[ADR 0007](0007-copilot-proposes-human-adopts.md) (the MCP fix) ·
[ADR 0016](0016-no-application-auth-the-tunnel-is-the-boundary.md) (the MCP
surface) · domain rules BR-78, BR-79, BR-80 ·
[`../permissions.md`](../permissions.md) gap P-15 ·
[`../questions.md`](../questions.md) §Q-MC-1.
Evidence: `app/db/session.py:8-64`; `app/mcp_server.py:96-110`;
`app/services/copilot_apply_service.py`; root `CLAUDE.md` § "Non-obvious
Conventions"; `app/CLAUDE.md`.
