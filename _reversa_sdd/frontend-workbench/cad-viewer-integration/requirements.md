# frontend-workbench / cad-viewer-integration

> Use-case specification. Parent module: [`../requirements.md`](../requirements.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.

## Overview

The 3D preview: a `three-cad-viewer` instance driven by tessellation data
fetched from the backend, with a **module-level cache** validated against the
aeroplane's `updated_at`, and a deliberately **asymmetric import pattern**
(static CSS, dynamic library) that project memory records as fragile — *never
change it without real browser testing*. 🟢

## Responsibilities

- Mount and dispose a `three-cad-viewer` instance. 🟢
- Guarantee one shared three.js instance between the app and the viewer. 🟢
- Fetch and cache tessellation per aeroplane + wing. 🟢
- Invalidate the cache when geometry is saved. 🟢

## Business Rules

- **BR-FE15 — The import pattern is asymmetric and load-bearing.** 🟢
  ```ts
  import "three-cad-viewer/css";                     // STATIC — CadViewer.tsx:6
  ...
  const tcv = await import("three-cad-viewer");      // DYNAMIC — CadViewer.tsx:90
  ```
  Documented in project memory as fragile: it must never be changed without
  **real browser testing**, because the failure mode does not appear in jsdom.
- **BR-FE16 — `three` is aliased in both resolvers.** 🟢 `next.config.ts` maps
  `three` to one resolved path for **webpack and turbopack**, so the app and
  `three-cad-viewer` share a single three.js instance. A single-resolver alias
  silently produces two copies and the viewer fails at runtime. 🔴
- **BR-FE17 — The tessellation cache is module-level and `updated_at`-keyed.** 🟢
  A `Map` keyed by `` `${aeroplaneId}/${wingName}` `` storing the tessellation
  together with the aeroplane's `updated_at`; a mismatch invalidates.
  `invalidateTessellationCache(aeroplaneId, wingName)` is exported so a geometry
  save restores the "Preview 3D" affordance.
- **BR-FE32 — The cache is per tab and unbounded.** 🟡 No eviction, no size cap,
  no age limit — only an `updated_at` mismatch removes an entry.
- **BR-FE33 — Tessellation is a backend responsibility.** 🟢 The client never
  meshes geometry; it requests a tessellation and renders it. (The backend's
  `tessellation_service` is one of the few services that commits its own
  session.)
- **BR-FE34 — The viewer must be disposed on unmount.** 🟡 A leaked WebGL
  context is a hard browser limit (typically ~16 contexts), so repeated
  navigation without disposal breaks the page.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Import the viewer library at runtime | Must | No `three-cad-viewer` in the initial bundle |
| RF-02 | Import the viewer CSS statically | Must | Styles present on first render |
| RF-03 | Alias `three` in webpack **and** turbopack | Must | One three.js instance |
| RF-04 | Fetch tessellation for the selected aeroplane + wing | Must | Rendered geometry matches the saved design |
| RF-05 | Cache by `` `${aeroplaneId}/${wingName}` `` | Must | A second preview does not refetch |
| RF-06 | Validate the cache against `updated_at` | Must | A changed aircraft refetches |
| RF-07 | Export `invalidateTessellationCache` | Must | A save restores "Preview 3D" |
| RF-08 | Dispose the viewer on unmount | Must | No leaked WebGL context |
| RF-09 | Show a loading state while tessellating | Should | CAD tessellation is slow |
| RF-10 | Surface a tessellation error in the panel | Should | Type-only error messages (log-hygiene rule) |

## Non-functional Requirements

| Type | Inferred requirement | Evidence | Confidence |
|------|----------------------|----------|-----------|
| Performance | Repeated previews must not re-tessellate | the module-level cache | 🟢 |
| Performance | The viewer library must not enter the initial bundle | the dynamic import | 🟢 |
| Correctness | Exactly one three.js instance must exist | the dual alias | 🟢 |
| Correctness | A stale tessellation must never be shown | the `updated_at` check | 🟢 |
| Stability | The import pattern must not be "cleaned up" without browser testing | project memory | 🟢 |
| Resource safety | 🟡 WebGL contexts are a scarce browser resource; the viewer must be disposed | — | 🟡 |
| Memory | 🟡 The cache is unbounded and per tab | `useTessellation` | 🟡 |
| Testability | 🟡 jsdom cannot exercise the viewer; only Playwright can | — | 🟡 |

## Acceptance Criteria

```gherkin
Feature: Import pattern

  Scenario: The library is dynamic
    When the viewer component mounts
    Then three-cad-viewer is imported at runtime
    And it is absent from the initial JavaScript payload

  Scenario: The CSS is static
    Then the viewer stylesheet is present on first render without a flash

  Scenario: One three.js instance
    Given the app and three-cad-viewer both import "three"
    Then both resolve to the same module instance
    And the alias is configured for webpack and for turbopack

Feature: Tessellation cache

  Scenario: A cache hit
    Given a tessellation for aeroplane A wing "main_wing" with updated_at T
    When the preview is opened again and updated_at is still T
    Then no request is made

  Scenario: A stale entry
    Given the aeroplane's updated_at has changed
    Then the tessellation is refetched

  Scenario: Explicit invalidation after a save
    When wing geometry is saved
    Then invalidateTessellationCache(aeroplaneId, wingName) is called
    And the "Preview 3D" affordance becomes available again

  Scenario: Independent keys
    Given tessellations for two wings of one aeroplane
    Then both are cached separately

Feature: Lifecycle

  Scenario: Disposal
    When the viewer unmounts
    Then its WebGL context is released

  Scenario: Loading state
    Given a slow tessellation
    Then the panel shows a loading indicator until data arrives

  Scenario: Error surfacing
    Given the tessellation endpoint fails
    Then the panel shows an error and does not render a stale mesh
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|---|---|---|
| Runtime import + static CSS (RF-01/RF-02) | Must | The documented, fragile pattern |
| Dual `three` alias (RF-03) | Must | Two instances break the viewer at runtime |
| Cache with `updated_at` validation (RF-05/RF-06) | Must | Re-tessellating on every preview is unusable |
| `invalidateTessellationCache` (RF-07) | Must | Otherwise a save leaves a stale preview |
| Disposal (RF-08) | Must | WebGL contexts are a hard browser limit |
| Loading and error states (RF-09/RF-10) | Should | CAD is slow; silence looks broken |
| A cache eviction policy | Could | 🟡 unbounded today |
| Cross-tab / persistent tessellation cache | Won't | Per tab, in memory |
| Client-side meshing | Won't | Tessellation is a backend responsibility |

## Code Traceability

| File | Symbol | Coverage |
|---|---|---|
| `frontend/components/workbench/CadViewer.tsx:6` | static CSS import | 🟢 |
| `…:90` | `await import("three-cad-viewer")` | 🟢 |
| `frontend/hooks/useTessellation.ts` | the module-level `Map`, `updated_at` validation, `invalidateTessellationCache` | 🟢 |
| `frontend/next.config.ts` | the `three` alias for webpack **and** turbopack | 🟢 |
| `app/services/tessellation_service.py` | the backend producer (commits its own session) | 🟢 owned by `cad-generation` |
