# ADR 0016 — No application-level authentication; the tunnel is the trust boundary

- **Status:** Accepted — in force. **This is the highest-risk decision in the system.** **Framing corrected by [ADR 0024](0024-single-user-desktop-operating-model.md)** — the chain below is *maintainer tooling*, not the product's access control. The technical description and the risk inventory stand.
- **Decided:** 2024-12 → 2025-01 (CORS removal, commits `d4e111ae`, `efa4f553`, `90886197`); the tunnel half added 2026-06 (`deploy/`, gitignored)
- **Deciders:** Marc Szymanski (maintainer)
- **Confidence:** 🟢 CONFIRMED (code, commits, `deploy/README.md`); the *reasoning* is 🟡 partly reconstructed

## Context

da3Dalus is a single-maintainer personal design tool: one human designer, no
organisation, no tenancy, no customer data, no billing. Two forces pushed against
adding auth. **The frontend is a client-only SPA** making direct browser `fetch`
calls to `http://localhost:8001` — `frontend/CLAUDE.md` claims all calls go through
server-side route handlers, and there are none, so the wildcard CORS is the
*consequence* of that missing proxy layer, not an independent choice. **And every
access-control mechanism has a cost the product does not repay** — a login screen
on a tool with one user is friction. The pressure to expose it arrived later:
sharing a design with a teammate, and smoke-testing PRs on real data.

## Decision

**Do not implement authentication or authorisation in the application. Place the
trust boundary in front of the process, in a reverse-proxy chain terminating in a
GitHub login.**

```
Internet → ngrok (TLS, fixed domain)
         → oauth2-proxy :4180 (GitHub OAuth + GITHUB_USERS allowlist)
         → Caddy :8080
             ├─ /backend/*  → strip prefix → FastAPI :8001
             └─ /*          → Next.js (isolated build)
```

- **Authentication** = a GitHub OAuth App. **Authorisation** = a comma-separated
  `GITHUB_USERS` allowlist in `deploy/.env`. That is the entire policy.
- The frontend is built with `NEXT_PUBLIC_API_URL=/backend`, so the browser only
  talks to one public origin — no CORS, no `localhost` leakage in that deployment.
- A multi-stage mode (`stages.sh`) serves one stage per open PR behind the *same*
  login, each with its own worktree, uvicorn and **isolated DB copy**; the `main`
  stage uses the real database.
- `deploy/` is **gitignored** — infra plus secrets, never committed.

The application therefore has no login, session, token, API key, user table, role,
tenant or ownership check. `app/core/security.py` contains a four-line
`verify_token` comparing against the literal `"valid_token"`, with **no callers**.

## Consequences

- Zero auth complexity across 230 REST routes, 76 MCP tools, 48 frontend hooks and
  the test suite; the boundary is an externally maintained component; per-PR stages
  get isolated databases.
- `deploy/README.md` states the central risk itself: *"Behind the login this is
  your **real dev backend + real DB, with no per-user isolation** — anyone you let
  in can read and change everything."*
- 🔴 **Nothing enforces that the boundary is present.** No trusted-proxy check, no
  forwarded identity, no bind restriction; `run_mcp_server()` hard-codes
  `0.0.0.0:8001`, ignoring `UVICORN_HOST`. (Addressed by ADR 0024's exposure
  guard.)
- 🔴 **The boundary is not reproducible from the repository** — `deploy/` is
  gitignored, so a fresh clone cannot recreate the only access control there is.
- 🔴 **`/mcp` is unauthenticated**, exposing 76 tools including `delete_aeroplane`.
  Its one accidental mitigation is a bug — `_call_endpoint` never commits (see
  [ADR 0009](0009-get-db-owns-the-transaction-boundary.md)) — and that bug is being
  fixed.
- 🔴 Five further exposures, all **accepted** rather than mitigated by ADR 0024:
  `allow_origins=["*"]` with `allow_credentials=True`; public `/docs`, `/redoc`,
  `/openapi.json` and a `/static` mount on `tmp/`; no rate limiting or cost
  accounting, including on the LLM hub call; no audit log (the nearest thing,
  `created_by`, has three vocabularies and no enum); and a **live SQLite database
  committed to Git** and copied into the Docker image.
- **The decision does not scale.** The moment a second user needs different
  permissions, every capability in `permissions.md` §3 becomes a hole at once, and
  auth would have to be added to REST, MCP (which bypasses FastAPI routing,
  `Depends`, middleware and exception handlers entirely) and both frontend HTTP
  clients plus the hand-rolled SSE reader.

**Still open:** implementing the documented Next.js server-side proxy (route handlers
/ server actions) — it would close CORS and give a natural place to attach auth.
**Rejected:** FastAPI `Depends`-based auth, which would not protect `/mcp` and so
would create a false sense of coverage.

## Related

[ADR 0024](0024-single-user-desktop-operating-model.md) — **corrects the framing of
this ADR** · [ADR 0009](0009-get-db-owns-the-transaction-boundary.md) ·
[ADR 0007](0007-copilot-proposes-human-adopts.md) ·
[`../permissions.md`](../permissions.md) (the full picture) ·
[`../questions.md`](../questions.md) §Q-CC-1, §Q-CC-2.
Evidence: the CORS-removal commits `d4e111ae`, `efa4f553`, `90886197`;
`app/main.py`; `app/core/security.py`; `deploy/README.md` (gitignored).
