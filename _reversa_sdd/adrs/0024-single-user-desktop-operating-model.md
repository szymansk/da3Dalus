# ADR 0024 — Single-user desktop operating model (corrects ADR 0016)

- **Status:** Accepted — **corrects** [ADR 0016](0016-no-application-auth-the-tunnel-is-the-boundary.md)
- **Decided:** 2026-08-13, during the specification validation interview (`Q-CC-1`, `Q-CC-2`, `Q-CC-8`)
- **Deciders:** Marc Szymanski (maintainer)
- **Confidence:** 🟢 CONFIRMED (maintainer's stated product position; the exposure surfaces verified in code and compose file)

## Context

ADR 0016 places the trust boundary in an ngrok → oauth2-proxy → Caddy chain and
documents the residual risks honestly. It is nevertheless **wrong about one thing,
and that thing is load-bearing**: it frames the proxy chain as *the system's access
control*. It is not. The tunnel is the **maintainer's own testing tool** for sharing
a preview and smoke-testing PR stages — started by hand, not part of the product,
not present in any normal run, and gitignored, so a fresh clone cannot reproduce it.
A specification that describes it as the access-control mechanism claims a
protection the product does not have, which is worse than having no protection at
all, because it terminates the reader's search.

## Decision

**da3Dalus is a single-user, standalone desktop application, run on one machine by
one private user, and it is unauthenticated *by design*.**

**1. Correction to ADR 0016.** The proxy chain is reclassified from *the system's
trust boundary* to *private maintainer tooling*. ADR 0016's technical description
stays accurate and is retained; its framing does not. `permissions.md` and ADR 0016
are reworded so the spec does not describe the preview tunnel as an access-control
mechanism of the product. `Q-CC-2` completes this: `deploy/` is versioned in a
**separate private repository** cloned into the already-gitignored path — **not a
submodule**, because `.gitmodules` is committed and `szymansk/da3Dalus` is
**public**, so a submodule would publish the private repo's URL and break
`git clone --recurse-submodules` for everyone without access. (Verified: `deploy/`
has never been committed and the client secret does not appear in the last 200
commits — no remediation needed.)

**2. The spec says "unauthenticated by design", not "unfinished".** Multi-user
capability is a **future vision**, revisited only once core functionality is stable.
It is deliberately out of scope now, and saying so is part of the decision.

**3. Single-worker operation is permanent, and asserted at startup.** The application
**refuses to start** when configured with more than one worker — failing loudly at
boot is preferable to the silent, data-dependent breakage a second worker causes.
Consequently the per-process stores are **legitimate documented architecture, not
debt**:

| Store | Documented consequence |
|---|---|
| `JobTracker` | a restart drops pending retrim/recompute jobs |
| the CAD task registry | a task started before a `--reload` becomes unqueryable (404) though its worker may still run |
| the MCP `ASSET_REGISTRY` | `img://…` asset URIs are process-scoped |

(`Q-CC-8` lists a fourth, the frontend tessellation cache; that subsystem is deleted
entirely under
[ADR 0021](0021-complete-but-unreachable-code-is-deleted-by-default.md).)

This resolves nothing about **intra**-process concurrency: `Q-CG-2` — the CAD export
race between the four workers *inside* the pool of a single process — **remains a
real defect** needing a per-task directory. There is likewise no conflict with
[ADR 0005](0005-cad-in-a-spawned-process-pool.md); its `ProcessPoolExecutor` is
intra-process and unaffected.

**4. An exposure guard at the launch surfaces.** An app-side *bind* guard is
impossible when uvicorn is started from the CLI — it opens the socket before the app
loads — so the guard lives where the socket is chosen:

1. **Local / bare uvicorn:** drop `--host 0.0.0.0` from the documented dev command in
   `CLAUDE.md` / `AGENTS.md`. Uvicorn's default is already `127.0.0.1`, so the safe
   default is obtained by **removing** the flag that disables it.
2. **Docker:** publish to host loopback only — `ports: ["127.0.0.1:8086:8000"]`.
   `--host 0.0.0.0` **stays inside the container**, where it is mandatory or the
   published port is dead. Under Docker the trust boundary is the *publish* address,
   not the bind address.
3. **`run_mcp_server()`:** stop hard-coding `0.0.0.0:8001`; respect `UVICORN_HOST`
   and default to loopback. This is the one path where the app calls `uvicorn.run()`
   itself, so it is genuinely enforceable.
4. **Say what happened.** Emit a startup log line stating the **effective
   reachability**, and warn on a non-loopback bind without an explicit
   `ALLOW_PUBLIC_BIND` opt-in. The app cannot *prevent* public exposure; it must not
   be silent about it.

**Linux note, recorded because the project may not always run on macOS:** Docker's
published ports install rules in the `DOCKER` iptables chain that **bypass `ufw` and
`firewalld`**, so a host firewall does not protect a `8086:8000` publish. The
loopback publish address is the control, not the firewall.

## Consequences

- The specification stops claiming a protection the product lacks, so a reader can
  reason correctly instead of looking for a boundary that is not shipped.
- **`Q-MC-1` becomes safe to fix**: with loopback defaults the ~40 destructive MCP
  tools are not reachable off-box, so repairing the transaction boundary reverts to
  an ordinary bug fix rather than a security decision (see the
  [ADR 0007 amendment](0007-copilot-proposes-human-adopts.md)). Eight separate
  "should this be a persisted job?" gaps collapse into one documented constraint, and
  the startup assertion converts the most dangerous misconfiguration into a boot
  failure.
- **The guard is advisory, not enforcement.** Three of the four measures are
  documentation and configuration; only `run_mcp_server()` is enforced in code — a
  deliberate limit, since the socket is opened before the application exists.
- **Everything ADR 0016 lists under its risks remains true**, and is now *accepted*
  rather than mitigated: public `/docs`, `/redoc`, `/openapi.json` and `/static`;
  `allow_origins=["*"]` with `allow_credentials=True`; no rate limiting on the LLM
  hub call; a live SQLite database committed and copied into the image.
- **The decision does not scale, and now says so.** A second user with different
  permissions turns every capability in `permissions.md` §3 into a hole at once, and
  adding a worker later is a real migration, not a flag.
- **Deliberately out of scope, documented as such:** per-user quota and cost
  accounting (`Q-CO-9`), asset-registry externalisation (`Q-MC-3`) and MCP standalone
  exposure (`Q-MC-7`) are parked — scoped-out, not gaps. **`created_by` stays agent
  provenance, never user identity** — there is one user, so the column answers "human
  or AI", not "who" (`Q-CC-9`). The preview tunnel keeps working exactly as before;
  this ADR removes a claim the spec was making about it, not a capability.

**Rejected:** hardening the tunnel into a security control (invests in a testing tool
for a one-user product); adding application-level auth now (premature, and
`Depends`-based auth would not protect `/mcp`, creating false coverage); a bind-guard
inside the application (**impossible** for the CLI case); committing a sanitised
`deploy/` scaffold (keeps a live client-secret-leak failure mode on a public repo);
supporting multiple workers now.

## Related

- [ADR 0016](0016-no-application-auth-the-tunnel-is-the-boundary.md) — corrected by
  this ADR on framing; its technical description of the chain and its risk inventory
  stand.
- [ADR 0005](0005-cad-in-a-spawned-process-pool.md) — intra-process pool, unaffected;
  `Q-CG-2` remains an open defect against it.
- [ADR 0007](0007-copilot-proposes-human-adopts.md), amended 2026-08-15 — the MCP
  write semantics this decision unblocks.
- [ADR 0021](0021-complete-but-unreachable-code-is-deleted-by-default.md) — removes
  the fourth per-process store.
- [`../questions.md`](../questions.md) §Q-CC-1 · Q-CC-2 · Q-CC-8 · Q-CC-9 · Q-CG-2 ·
  Q-MC-1 · Q-MC-3 · Q-MC-7 · Q-CO-9; [`../permissions.md`](../permissions.md).
