# frontend-workbench / cad-viewer-integration — Implementation Tasks

> Parent module task list: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] `three 0.183` and `three-cad-viewer 4.3` installed.
- [ ] A backend tessellation endpoint for `(aeroplane, wing)`.
- [ ] `hooks/useAeroplanes` exposing `updated_at`.
- [ ] Playwright available — **jsdom cannot verify this use case**.

## Tasks

- [ ] **T-01 — The `three` alias in both resolvers.**
  `next.config.ts`: alias `three` to one resolved path for **webpack** and for
  **turbopack**.
  - Legacy origin: `frontend/next.config.ts`
  - Definition of done: a browser check confirms the app and the viewer share
    one instance. Configuring only one resolver makes the failure appear in
    dev **or** prod but not both — do this task first, because every later
    symptom looks like a viewer bug.
  - Confidence: 🟢

- [ ] **T-02 — `CadViewer` imports.**
  `import "three-cad-viewer/css"` at module scope (line 6);
  `const tcv = await import("three-cad-viewer")` inside the mount effect
  (line 90).
  - Legacy origin: `frontend/components/workbench/CadViewer.tsx:6,90`
  - Definition of done: the library is absent from the initial bundle and the
    stylesheet is present on first paint. **Carry the warning comment**: this
    pattern must never be changed without real browser testing — project memory
    records it explicitly.
  - Confidence: 🟢

- [ ] **T-03 — Viewer lifecycle.**
  Construct into the container ref after the dynamic import; guard the async
  race with a `disposed` flag; dispose in the effect cleanup.
  - Legacy origin: `frontend/components/workbench/CadViewer.tsx`
  - Definition of done: mounting and unmounting the panel ten times does not
    exhaust WebGL contexts — this is a hard browser limit and the failure is a
    blank canvas with no error.
  - Confidence: 🟢

- [ ] **T-04 — `useTessellation` and the module-level cache.**
  `Map<`${aeroplaneId}/${wingName}`, {data, updatedAt}>` at module scope;
  return the cached entry when `updatedAt` matches the aeroplane's `updated_at`;
  otherwise fetch and store.
  - Legacy origin: `frontend/hooks/useTessellation.ts`
  - Definition of done: a second preview of an unchanged aircraft makes **no**
    request; a changed `updated_at` refetches. The cache must live at module
    scope so it survives remounts and route changes.
  - Confidence: 🟢

- [ ] **T-05 — `invalidateTessellationCache`.**
  Exported; deletes one `(aeroplaneId, wingName)` entry.
  - Legacy origin: `frontend/hooks/useTessellation.ts`
  - Definition of done: a wing-config save calls it, and the "Preview 3D"
    affordance becomes available again without waiting for a revalidation round
    trip.
  - Confidence: 🟢

- [ ] **T-06 — Loading and error states.**
  A loading indicator while tessellating; an error state that does **not**
  render a stale mesh; error text kept type-only per the log-hygiene rule.
  - Legacy origin: the viewer panel
  - Definition of done: a failing tessellation shows an error and clears the
    canvas — never geometry that no longer exists.
  - Confidence: 🟡

- [ ] **T-07 — Wire the save path.**
  After `PUT …/wingconfig`, call `invalidateTessellationCache(uuid, wingName)`
  in addition to the SWR `mutate()`.
  - Legacy origin: the wing editor
  - Definition of done: saving geometry and immediately previewing shows the
    **new** shape.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Bundle check:** `three-cad-viewer` does not appear in the initial
      JavaScript payload.
- [ ] **TT-02 — One instance (browser):** the app and the viewer resolve to the
      same `three`.
- [ ] **TT-03 — Cache hit:** an unchanged `updated_at` makes no request.
- [ ] **TT-04 — Cache staleness:** a changed `updated_at` refetches.
- [ ] **TT-05 — Independent keys:** two wings of one aeroplane cache
      separately.
- [ ] **TT-06 — Explicit invalidation:** the entry is removed and the next
      preview refetches.
- [ ] **TT-07 — Save → preview (Playwright):** the new geometry is rendered.
- [ ] **TT-08 — Disposal (Playwright):** ten mount/unmount cycles still render.
- [ ] **TT-09 — Error state:** a failing tessellation shows an error and no
      stale mesh.
- [ ] **TT-10 — Unmount race:** unmounting during the dynamic import does not
      construct a viewer into a detached node.

> TT-02, TT-07 and TT-08 **must** run in a real browser. jsdom cannot render
> WebGL, which is precisely why this use case's regressions have historically
> escaped unit tests.

## Suggested Order

1. **T-01** the dual alias first. Every later symptom — unstyled viewer, failing
   `instanceof`, blank canvas — looks like a viewer bug when it is actually a
   duplicated three.js.
2. **T-02 → T-03** the import pattern and lifecycle, verified in a browser
   before anything is built on top.
3. **T-04 → T-05** the cache and its invalidation, which are pure logic and
   unit-testable.
4. **T-06** the loading and error states.
5. **T-07** the save-path wiring, with the Playwright save→preview test (TT-07)
   as the acceptance gate.

## Pending Gaps

- **Should the tessellation cache have an eviction policy** (size cap, TTL, LRU)?
  It is module-level and unbounded today.
- **Should cache hit rate and tessellation duration be measured**, so the
  cache's value and cost are visible?
- **Should a duplicated three.js instance be detected at runtime** with a clear
  diagnostic instead of an opaque render failure?
- **Should the dynamic import use an `AbortController`** rather than a local
  `disposed` flag?
- **Should viewer disposal be asserted in CI**, given WebGL context exhaustion
  is silent?
- **Can the fragile import pattern be made robust**, or must it stay exactly as
  documented in project memory?
