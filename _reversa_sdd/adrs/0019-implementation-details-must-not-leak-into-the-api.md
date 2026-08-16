# ADR 0019 — Implementation details must not leak into the public API

- **Status:** Accepted — new decision. **Always a review criterion.**
- **Decided:** 2026-08-14, during the specification validation interview
- **Deciders:** Marc Szymanski (maintainer)
- **Confidence:** 🟢 CONFIRMED (routes, git history, schemas)

## Context

The public surface — REST paths, response shapes, MCP tool schemas — repeatedly
exposes *how* something is implemented rather than *what* it is. Each instance was
discovered separately and treated as an isolated defect. They are one defect.

**The clearest case: the storage engine in the URL.** `/airfoils/db/…` sits beside
`/airfoils/…`, so a client must know which store an airfoil lives in before it can
address it. A filesystem registry shipped 2026-02-16; a database store was added
**alongside** on 2026-04-25 (`06a25ff4`, gh-335) rather than migrating the existing
routes, and the gh-821 suitability search was filed under `db/`, inheriting the
split. `db` is literally a marker meaning "the new store"; the additive migration
was never completed and the marker became part of the contract. That leak then
produced a subtler one: `/airfoils/db/suitability` and `/airfoils/db/{name}` are the
same shape to FastAPI, so the search endpoint works **only** because it is declared
first — re-ordering the decorators makes the service look up an airfoil named
`"suitability"`, a 404 that reads as a harmless diff.

**Other instances of the same class:** `components.model_ref` is a raw filesystem
path, client-writable and persisted verbatim — the root of the confirmed
unauthenticated arbitrary-file-read on `GET /components/{id}/model`, so the leak *is*
the vulnerability (`Q-PT-13`); `/api/v2/import/openvsp`, one route of 230 carrying a
version prefix because of how its router was included (`Q-CC-6`); two error
envelopes, so the client can tell which code path raised (`Q-CC-3`); and `bb` on the
tessellation response, always zeroed by an unreconciled key-name mismatch
(`Q-CG-3`).

## Decision

**The public API describes the domain, never the mechanism.** The following must
not appear in a path, a field name, or a response shape:

1. **The storage engine or location** — no `db/`, `file/`, `cache/` segments; no
   filesystem paths as field values. A resource is addressed by its domain
   identity, and the service decides where it lives.
2. **The internal module or router that happens to serve it** — path prefixes are
   chosen for the domain, not inherited from how a router was mounted.
3. **Which internal code path produced a response** — one error envelope
   (`{"error": {code, message, details}}`), one response contract per endpoint,
   regardless of which layer raised.
4. **Fields that exist only because of an internal representation** and carry no
   meaning for a client.

**Corollaries.**

- A **static path segment must never occupy the same position as a path parameter**
  in a sibling route (`/x/search` vs `/x/{id}`). Correct behaviour must not depend
  on declaration order; where the two would collide, the operation gets a distinct
  path.
- When a new storage or computation mechanism is introduced, the **existing routes
  are migrated**; a parallel family is not opened. A transitional period, if
  unavoidable, is time-boxed and recorded, not left as the contract.
- Adding a mechanism marker to a path is a **review-blocking** finding, not a
  stylistic note.

## Consequences

- The `/airfoils/db/*` and `/airfoils/*` families merge into one airfoil resource
  model, so the `suitability` ↔ `{name}` collision disappears **by construction**
  and no ordering test is needed. `model_ref` stops being a client-writable path,
  removing the arbitrary-file-read by design rather than by a containment check on
  one endpoint.
- Merging the airfoil families is a breaking change to ~12 routes — affordable only
  because there are **no external API consumers**
  ([ADR 0024](0024-single-user-desktop-operating-model.md)); every client lives in
  this repository.
- The work must land **before** TypeScript client generation (`Q-CC-11`), or the
  leak is baked into generated code and becomes materially harder to remove.
- The rule governs *new* surface. Existing leaks are fixed as they are touched,
  except the airfoil split and `model_ref`, which are scheduled explicitly.

**Rejected:** keeping the split plus a route-ordering test (pins the symptom in
place and still requires clients to know the storage engine); constraining `{name}`
with a reserved-word regex (makes the collision survivable rather than impossible);
treating each instance individually — the point of this ADR is that the same defect
kept being rediscovered under different names.

## Related

- [ADR 0016](0016-no-application-auth-the-tunnel-is-the-boundary.md) /
  [ADR 0024](0024-single-user-desktop-operating-model.md) — no external API
  consumers, which is what makes the breaking change affordable.
- [ADR 0022](0022-one-authority-per-user-facing-quantity.md) — same argumentative
  shape: one defect repeatedly rediscovered.
- [`../questions.md`](../questions.md) §Q-AF-4 (the airfoil split), §Q-CC-6
  (`/api/v2` prefix), §Q-CC-3 (error envelope), §Q-CG-3 (`bb`), §Q-PT-13
  (`model_ref` / arbitrary-file-read), §Q-CC-11 (client generation).
