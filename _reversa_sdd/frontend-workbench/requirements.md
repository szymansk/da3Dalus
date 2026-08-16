# frontend-workbench

> Module-level specification. Focuses on WHAT the module does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: frontend-workbench,
> `_reversa_sdd/data-dictionary.md` §Module: frontend-workbench,
> `_reversa_sdd/architecture.md` §3.1, §9, `.reversa/context/surface.json`.

## Overview

The Next.js 16 / React 19 design workbench: **one client-side shell** with seven
tabs (wing & fuselage editor, analysis, components/COTS, mission, powertrain,
construction plans, airfoil preview), a 3D CAD viewer, a Plotly chart layer, a
docked AI copilot strip and a version-graph overlay — all driven by SWR hooks
that call the FastAPI v2 API **directly from the browser**. 🟢

~47 700 LOC across `app/ components/ hooks/ lib/ types/`, documented at
architectural level. 🟢

The single most important structural fact: **there are no route handlers, no
server actions and no server-side fetching.** `app/**/route.ts` does not exist.
This directly contradicts `frontend/CLAUDE.md:12-13` — *"All API calls go
through server-side route handlers or server actions to avoid CORS"* — and it is
the reason the backend must run `allow_origins=["*"]`. 🔴

## Responsibilities

- Own the workbench shell: providers, header, docked metrics band, docked
  copilot strip, version overlay. 🟢
- Own the seven tab routes and their panels (129 components in 5 sub-folders,
  34 204 lines). 🟢
- Own 48 SWR/feature hooks — one per backend capability. 🟢
- Own the three HTTP access paths (`lib/fetcher.ts`, `lib/api.ts`,
  `lib/sseStream.ts`). 🟢
- Own client-side state: React context, URL search params, the SWR cache and
  `localStorage`. 🟢
- Own the 3D viewer integration and its module-level tessellation cache. 🟢
- Own the Plotly chart layer, dynamically imported per figure. 🟢
- Own the design tokens and the dark-only theme. 🟢
- Own the enforced layering (`app → components → hooks → lib`) and the five test
  layers. 🟢

**NOT this module's responsibility:** any business rule. Every number displayed
is computed by the backend (ADR 0004); the frontend contains no aerodynamics,
no unit conversion beyond display formatting, and no persistence.

## Business Rules

> `BR-FE*` are module-local. The frontend owns **no** global domain rule.

### Architecture

- **BR-FE1 — A client-only SPA inside the App Router.** 🟢 `app/layout.tsx` is
  the only meaningful server component (fonts `Geist`, `Geist_Mono`,
  `JetBrains_Mono` via `next/font/google`, metadata, font CSS variables);
  `app/page.tsx` is five lines; everything under `/workbench` is `"use client"`.
- **BR-FE2 — No route handlers, no server actions, no server-side fetch.** 🟢
  Verified: `app/**/route.ts` does not exist and no file declares `"use
  server"`. Every request is a cross-origin browser fetch to
  `http://localhost:8001`. 🟢 SPA-direct **is** the architecture; the documentation is what is wrong (`Q-FW-1`, maintainer-answered).
- **BR-FE3 — The shell mounts on every tab.** 🟢
  ```
  Suspense
  └ AeroplaneProvider                  (selection + URL/localStorage sync)
    └ UnsavedChangesProvider
      ├ Header(onOpenHistory)
      ├ WorkbenchImportWarningBanner
      ├ main → {children}              ← the active tab
      ├ VersionGraphOverlay            (conditional, key={rootId})
      ├ MetricsDashboardContainer      (gh-881, docked)
      ├ CopilotStrip(onOpenHistory)    (docked)
      ├ UnsavedChangesModal
      └ AeroplanePickerHost
  ```
- **BR-FE4 — The layering is enforced by dependency-cruiser.** 🟢
  | Rule | Severity |
  |---|---|
  | `no-circular` | **error** |
  | `no-components-import-app` | **error** |
  | `no-hooks-import-app` | **error** |
  | `no-hooks-import-components` | warn |
  | `no-lib-import-components` | warn |
  | `no-orphans` | info (`page.tsx`, `layout.tsx`, `.d.ts`, tests excluded) |
  `tsPreCompilationDeps: true`; `e2e/` and `.features-gen` excluded.

### Data access

- **BR-FE5 — One base URL, baked in at build time.** 🟢
  `const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001"`
  — the `NEXT_PUBLIC_` prefix means it is inlined into the bundle.
- **BR-FE6 — The null-key guard is the universal "nothing selected" idiom.** 🟢
  ```ts
  const path = id !== null ? `/lineages/${id}/tree` : null;   // null key = disabled
  const { data, error, isLoading, mutate } = useSWR<TreeOut>(path, fetcher);
  return { tree: data, isLoading, error, mutate };            // renamed, never raw `data`
  ```
- **BR-FE7 — Writes go through `putJson` / `lib/api.ts`, then `mutate()`.** 🟢
  Cross-hook invalidation uses `useSWRConfig().mutate(key)` — e.g. every version
  action revalidates both the lineage tree and the aeroplanes list.
- **BR-FE8 — 🟡 The hooks migrate onto one typed client (`Q-FW-2`).** Previously two coexisted:
  `lib/api.ts` is the richer one (typed `ApiError(status, message, details)`, a
  `Content-Type` header, `204 → undefined`), but the SWR hooks use
  `lib/fetcher.ts`, which throws a plain
  `Error("<status> <statusText>: <body>")`. `lib/parseApiError.ts` exists purely
  to paper over the difference.
- **BR-FE9 — SSE is parsed by hand.** 🟢 `lib/sseStream.ts` reads
  `response.body` as a `ReadableStream` because *"the browser's built-in
  `EventSource` only works with GET requests"* and both streams here are POST.
  It buffers the trailing incomplete record across chunk boundaries, tolerates
  multiple `data:` lines (joined with `\n`), falls back to the raw string when a
  payload is not JSON, and flushes a trailing record after stream end. Two
  consumers: the copilot stream and the OpenVSP import progress (gh-737).
- **BR-FE10 — 🟢 A global `SWRConfig` provider plus a shared key module (`Q-FW-3`).** Previously none: No shared
  `refreshInterval`, `revalidateOnFocus` policy, error-retry policy or global
  `onError`; each of the 48 hooks decides for itself.
- **BR-FE11 — 🟡 Client generation scheduled (`Q-CC-11`).** Previously hand-mirrored: Only `types/versioning.ts`
  and `types/versionGraph.ts` are shared; every other interface is redeclared
  inside its hook (`useCopilot.ts` says *"mirror
  app/schemas/copilot_history.py"*). Nothing is generated from `/openapi.json`,
  so a backend schema change is caught only by `tsc` against hand-written
  fixtures.

### State

- **BR-FE12 — Four state mechanisms, no state library.** 🟢 No Redux, Zustand or
  Jotai.
  1. **React context** — `AeroplaneContext` (`aeroplaneId`, `selectedWing`,
     `selectedXsecIndex`, `selectedFuselage`, `selectedFuselageXsecIndex`,
     `treeMode: "wingconfig" | "asb" | "fuselage"`, `pickerOpen`,
     `lastImportWarnings`, `hydrated`) and `UnsavedChangesContext`.
  2. **URL search params** — `?aeroplane=<uuid>` is the **source of truth**;
     `setAeroplaneId` does a router replace and mirrors to `localStorage`.
  3. **The SWR cache** — all server state.
  4. **`localStorage`** — `da3dalus_aeroplane_id`, plus per-feature keys in
     `CopilotStrip`, `WorkbenchImportWarningBanner`, `ImportWarningBanner`,
     `StabilityOverlay` and `lib/versionGraphViewState.ts`.
- **BR-FE13 — `hydrated` prevents a first-render flash.** 🟢 It is exposed so
  pages do not show "no aircraft selected" during the first client pass.
- **BR-FE14 — `treeMode` is the frontend face of the mm/metre duality.** 🟢
  `wingconfig` = mm segments, `asb` = metre cross-sections, `fuselage` = the
  fuselage tree.

### Viewer and charts

- **BR-FE15 — The CAD viewer's import pattern is asymmetric and fragile.** 🟢
  CSS is imported **statically** (`import "three-cad-viewer/css"`, l.6) while
  the library is imported **dynamically at runtime**
  (`const tcv = await import("three-cad-viewer")`, l.90). Project memory records
  that this must never be changed without real browser testing.
- **BR-FE16 — `three` is aliased in both resolvers.** 🟢 `next.config.ts`
  aliases `three` to one resolved path for **webpack and turbopack**, so the app
  and `three-cad-viewer` share a single three.js instance.
- **BR-FE17 — The tessellation cache is module-level and validated by
  `updated_at`.** 🟢 `useTessellation` keys a module `Map` on
  `` `${aeroplaneId}/${wingName}` `` and checks the aeroplane's `updated_at`
  before reuse; `invalidateTessellationCache(id, wing)` is exported so a
  geometry save restores the "Preview 3D" affordance. 🟡 Per-tab and unbounded —
  no eviction, no size cap.
- **BR-FE18 — Plotly is always a runtime import.** 🟢 Every use is
  `await import("plotly.js-gl3d-dist-min")` inside an effect, with
  `Plotly.purge(node)` on unmount. `StreamlinesViewer:7` states the rule: *"DO
  NOT import react-plotly.js or plotly.js at top level — it is 1.5 MB."* Eight
  components chart; `AnalysisViewerPanel` alone performs the dynamic import at
  five call sites. 🔴 `react-plotly.js` is a declared dependency and is **never
  imported**.
- **BR-FE19 — Dark theming is applied per figure.** 🟢 `paper_bgcolor`,
  `plot_bgcolor`, `font.color` per figure rather than a shared template. 🟡

### Styling and testing

- **BR-FE20 — Tailwind v4 with tokens in `@theme inline`.** 🟢 *"mapped 1:1 from
  pencil da3Dalus.pen design tokens"*: `background #111111`, `card #1A1A1A`,
  `card-muted #17171A`, `foreground #FFFFFF`, `muted-foreground #B8B9B6`,
  `subtle-foreground #7A7B78`, `border #2E2E2E`, `border-strong #3A3A3A`,
  `primary #FF8400`, `primary-foreground #111111`, `destructive #E5484D`,
  `success #30A46C`, `sidebar #18181B`, `sidebar-accent #2A2A30`,
  `input #1C1C20`; radii `xs 6 · sm 8 · md 10 · lg 12 · xl 16 · 2xl 20`
  (+ `s/m/l/pill` aliases). **Dark only** — no light theme, no
  `prefers-color-scheme` — 🟢 **removed: the workbench is dark-only** (`R2-14`). The dark values become the values, not a `[data-theme]` fallback. Decided **before** `Q-FW-4`'s design-system extraction on purpose: one token set now is cheap, a second one afterwards means revisiting every extracted component — and layout tests need a real browser, so doubling the surface doubles the expensive kind of test.
- **BR-FE21 — Two CSS escape hatches are required.** 🟢
  `@source "../node_modules/streamdown/dist"` so Tailwind does not purge the
  copilot markdown renderer's classes, and a global
  `dialog:not([open]) { display: none !important }` keeping native `<dialog>`
  hidden against Tailwind positioning.
- **BR-FE22 — Five test layers, three of them CI gates.** 🟢
  vitest (180 files) · **`npx tsc --noEmit`** · eslint 9 +
  `eslint-plugin-sonarjs` (`--max-warnings=0` on staged files via husky +
  lint-staged) · dependency-cruiser · playwright-bdd (10 `.feature` files,
  `@slow` excluded by default, `e2e/.cleanup-done` removed before and after each
  run). `npm run bdd:missing` (gh-564) lists Gherkin steps with no definition and
  exits non-zero, because `bddgen` truncates its own snippet list at 10.
- **BR-FE23 — Node 22 is mandatory.** 🟢 Node ≥ 24 breaks jsdom `localStorage`
  and produces spurious failures (`frontend/CLAUDE.md:19`).
- **BR-FE24 — `next` is pinned to a canary build.** 🟢 `16.2.1-canary.33`,
  matched by `eslint-config-next`; `frontend/AGENTS.md` warns that this Next.js
  differs from documented/trained behaviour. 🔴

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Render the workbench shell on every tab | Must | Header, metrics dock, copilot strip and picker present on all seven routes |
| RF-02 | Keep the selected aircraft in the URL and mirror it to `localStorage` | Must | `?aeroplane=<uuid>` survives a reload; a fresh tab restores from storage |
| RF-03 | Expose `hydrated` so pages do not flash "no aircraft" | Must | No flash on first paint |
| RF-04 | Disable a hook by passing a `null` SWR key | Must | No request fires with nothing selected |
| RF-05 | Return renamed fields from every hook, never raw `data` | Must | 48 hooks follow the convention |
| RF-06 | Revalidate after a write via `mutate()` | Must | The UI reflects the new state without a reload |
| RF-07 | Invalidate cross-hook keys where a write affects them | Must | A version action revalidates the tree **and** the aeroplanes list |
| RF-08 | Parse SSE over POST by hand | Must | Copilot tokens and OpenVSP progress both stream |
| RF-09 | Buffer partial SSE records across chunk boundaries | Must | A record split mid-payload is not lost |
| RF-10 | Fall back to the raw string when an SSE payload is not JSON | Must | No throw |
| RF-11 | Render the 3D viewer with a runtime `three-cad-viewer` import | Must | CSS static, library dynamic |
| RF-12 | Share one three.js instance between app and viewer | Must | Aliased in webpack **and** turbopack |
| RF-13 | Cache tessellation per aeroplane+wing and validate by `updated_at` | Must | A stale entry is not reused |
| RF-14 | Expose `invalidateTessellationCache` for geometry saves | Must | "Preview 3D" reappears after a save |
| RF-15 | Import Plotly at runtime only and purge on unmount | Must | No top-level `plotly` import; `Plotly.purge` called |
| RF-16 | Theme every figure explicitly for dark | Should | `paper_bgcolor` / `plot_bgcolor` / `font.color` set |
| RF-17 | Enforce the layering in CI | Must | `npm run deps:check` passes with no `error`-level violation |
| RF-18 | Pass `tsc --noEmit`, eslint and vitest in CI | Must | All three gates green on Node 22 |
| RF-19 | Detect a copilot proposal from the lineage tree | Must | `created_by === "copilot" && is_main === false` |
| RF-20 | Drive adopt/discard through the existing versioning routes | Must | No new endpoints (gh-939) |
| RF-21 | Show live copilot activity as tool chips | Should | 🟡 only 3 of 6 tools are labelled |
| RF-22 | Persist per-feature UI state in `localStorage` | Should | Strip collapse, banner dismissal, version-graph pan/zoom |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Performance | The 1.5 MB Plotly bundle must never enter the initial payload | `StreamlinesViewer:7` + 8 dynamic import sites | 🟢 |
| Performance | Repeated 3D previews must not re-tessellate | the module-level cache in `useTessellation` | 🟢 |
| Correctness | App and viewer must share one three.js instance | the dual `three` alias | 🟢 |
| Maintainability | Layer violations must fail the build | `.dependency-cruiser.cjs`, `no-circular` at **error** | 🟢 |
| Maintainability | Type drift against the backend must be caught | `npx tsc --noEmit` as a CI gate | 🟢 (🟡 against **hand-written** mirrors) |
| Compatibility | Tests require **Node 22** — Node ≥ 24 breaks jsdom `localStorage` | `frontend/CLAUDE.md:19` | 🟢 |
| UX | No "nothing selected" flash on first client render | `hydrated` | 🟢 |
| Security | 🟡 No authentication in the client; the API is called directly with no proxy | `lib/fetcher.ts` | 🟡 |
| Resilience | 🟡 No global SWR error/retry policy | no `SWRConfig` provider | 🟡 |
| Bundle hygiene | 🟡 `react-plotly.js` is a declared, never-imported dependency | `package.json:37` | 🟡 |
| Maintainability | 🟡 Seven components exceed 1 000 lines | `AnalysisViewerPanel` 1 567, `MatchingChartTab` 1 518, `AeroplaneTree` 1 197, `PowertrainTab` 1 190, `VersionGraphOverlay` 1 117, `OperatingPointsPanel` 1 076, `AnalysisConfigPanel` 1 063 | 🟡 |
| Maintainability | 🟡 `components/ui/` holds a single primitive (`PillToggle`); there is no design-system boundary | — | 🟡 |
| Stability | 🟡 `next` is pinned to a canary build whose behaviour differs from the documentation | `package.json:33` | 🟡 |

## Acceptance Criteria

```gherkin
Feature: Shell and selection

  Scenario: The shell is present on every tab
    Given an aircraft is selected
    When I visit each of the seven workbench routes
    Then the header, metrics dock and copilot strip are rendered

  Scenario: Selection lives in the URL
    When I select an aircraft
    Then the URL contains ?aeroplane=<uuid>
    And localStorage holds da3dalus_aeroplane_id

  Scenario: A fresh tab restores the selection
    Given localStorage holds an aeroplane id and the URL has no query
    When the workbench loads
    Then that aircraft is selected

  Scenario: No first-render flash
    Given hydrated is false on the first client pass
    Then the page does not render "no aircraft selected"

Feature: Data fetching

  Scenario: A disabled hook makes no request
    Given no aircraft is selected
    When a hook computes a null SWR key
    Then no network request is made

  Scenario: A write revalidates
    When I save a wing
    Then the wing hook's mutate() is called
    And the displayed geometry updates without a reload

  Scenario: Cross-hook invalidation
    When I adopt a branch
    Then both the lineage tree and the aeroplanes list are revalidated

  Scenario: Two error shapes
    Given lib/fetcher throws a plain Error and lib/api throws an ApiError
    Then parseApiError normalises both for display

Feature: Streaming

  Scenario: Copilot tokens stream
    When I send a copilot message
    Then token events append text incrementally
    And the done event triggers a history revalidation

  Scenario: A split SSE record survives
    Given a record arrives across two chunks
    Then exactly one event is yielded

  Scenario: A non-JSON payload
    Given a data line that is not JSON
    Then the raw string is yielded and nothing throws

Feature: 3D viewer

  Scenario: Runtime import
    When the viewer mounts
    Then three-cad-viewer is imported dynamically
    And its CSS was imported statically at module scope

  Scenario: Cache validity
    Given a cached tessellation and an unchanged updated_at
    Then the cache is reused
    Given updated_at has changed
    Then the tessellation is recomputed

  Scenario: A save restores Preview 3D
    When I save geometry
    Then invalidateTessellationCache is called for that aeroplane and wing

Feature: Charts

  Scenario: No top-level Plotly
    Then no module imports plotly.js or react-plotly.js at top level

  Scenario: Cleanup
    When a charting component unmounts
    Then Plotly.purge is called on its node

Feature: Quality gates

  Scenario: Layering
    When npm run deps:check runs
    Then there is no circular dependency and no components/hooks import from app

  Scenario: Types
    When npx tsc --noEmit runs on Node 22
    Then it exits zero
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|---|---|---|
| Shell + selection in the URL (RF-01…RF-03) | Must | Every tab depends on the selected aircraft |
| The null-key hook convention (RF-04/RF-05) | Must | The universal "nothing selected" contract across 48 hooks |
| Write + revalidate, incl. cross-hook (RF-06/RF-07) | Must | Otherwise the UI shows stale server state |
| Hand-rolled SSE (RF-08…RF-10) | Must | `EventSource` cannot POST; both streams need it |
| Viewer import pattern + three alias (RF-11/RF-12) | Must | Documented as fragile; two three.js instances break the viewer |
| Tessellation cache + invalidation (RF-13/RF-14) | Must | Re-tessellating on every preview is unusable |
| Runtime Plotly import + purge (RF-15) | Must | 1.5 MB in the initial bundle otherwise |
| Layering + type/lint/test gates (RF-17/RF-18) | Must | The only automated guard on a 47 kLOC client |
| Proposal detection and adopt/discard (RF-19/RF-20) | Must | ADR 0007's human-adoption half lives here |
| Per-figure dark theming (RF-16) | Should | Works, but duplicated per figure |
| Copilot tool chips (RF-21) | Should | 🟡 3 of 6 tools labelled |
| `localStorage` UI state (RF-22) | Should | Convenience |
| Server-side route handlers / actions | Won't | 🟡 documented in `frontend/CLAUDE.md`, **not implemented** — and the backend's wildcard CORS is the consequence |
| A generated API client from `/openapi.json` | Won't (today) | 🟡 every type is hand-mirrored |
| A global `SWRConfig` policy | Won't (today) | 🟡 none exists |
| Light theme | Won't | 🟡 dark only, by design |
| A design-system layer | Won't (today) | 🟡 `components/ui/` holds one primitive |

## Code Traceability

| File / dir | Role | Coverage |
|---|---|---|
| `frontend/app/layout.tsx` (37 l.) | root server layout — fonts, metadata | 🟢 |
| `frontend/app/page.tsx` (5 l.) | redirect stub | 🟢 |
| `frontend/app/workbench/layout.tsx` (80 l., `"use client"`) | the shell | 🟢 |
| `frontend/app/workbench/*/page.tsx` (2 242 l.) | 7 tab pages | 🟢 |
| `frontend/components/workbench/` (129 files, 34 204 l.) | all panels | 🟢 |
| `frontend/components/ui/PillToggle.tsx` | the only shared primitive | 🟡 |
| `frontend/hooks/` (48 files) | SWR/feature hooks | 🟢 |
| `frontend/hooks/useCopilot.ts` (215 l.) | streaming + `TOOL_LABEL_MAP` | 🟢 🟡 |
| `frontend/hooks/useCopilotProposal.ts` (111 l., gh-939) | proposal detection, adopt/discard | 🟢 |
| `frontend/hooks/useTessellation.ts` | the module-level cache | 🟢 |
| `frontend/lib/fetcher.ts` | `API_BASE`, `fetcher`, `putJson` | 🟢 |
| `frontend/lib/api.ts` | `ApiError`, `fetchAPI`, the `api` helper | 🟢 🟡 |
| `frontend/lib/sseStream.ts` | `parseSseStream`, `SseEvent` | 🟢 |
| `frontend/lib/parseApiError.ts` | bridges the two error shapes | 🟡 |
| `frontend/lib/versionGraphViewState.ts` | pan/zoom persistence | 🟢 |
| `frontend/types/versioning.ts`, `types/versionGraph.ts` | the only shared types | 🟢 |
| `frontend/app/globals.css` | `@theme inline` tokens, the two CSS escape hatches | 🟢 |
| `frontend/next.config.ts` | `NEXT_PUBLIC_API_URL`, the dual `three` alias, `allowedDevOrigins` | 🟢 |
| `frontend/.dependency-cruiser.cjs` | the enforced layering | 🟢 |
| `frontend/__tests__/` (180 files) | vitest | 🟢 |
| `frontend/e2e/` (10 `.feature` files) | playwright-bdd | 🟢 |
| `frontend/components/workbench/metrics-dashboard/metricsMock.ts` | mock data in the production tree | 🟡 |
