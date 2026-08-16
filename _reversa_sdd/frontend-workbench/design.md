# frontend-workbench — Technical Design

> Module-level design. Focuses on HOW the module is built, derived from the
> legacy code. Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> API-consumption contract: [`contracts.md`](contracts.md).
> Use cases: [`workbench-shell-and-routing`](workbench-shell-and-routing/design.md) ·
> [`data-fetching-swr`](data-fetching-swr/design.md) ·
> [`cad-viewer-integration`](cad-viewer-integration/design.md) ·
> [`analysis-dashboards-plotly`](analysis-dashboards-plotly/design.md).

## Interface

### Stack 🟢

`next 16.2.1-canary.33` · `react 19.2.5` · `swr 2.4` · `tailwindcss 4` ·
`three 0.183` + `three-cad-viewer 4.3` · `plotly.js-gl3d-dist-min 3.5` ·
`@dnd-kit` · `@monaco-editor/react` · `streamdown` + `remark-math` + `katex`
(copilot markdown) · `react-resizable-panels` · `lucide-react` ·
`@zip.js/zip.js`.

### Directory contract 🟢

| Dir | Contents | May import |
|---|---|---|
| `app/` | 1 root layout, 1 shell layout, 7 tab pages | components, hooks, lib |
| `components/workbench/` | 129 components in 5 sub-folders | hooks, lib |
| `components/ui/` | **one** primitive (`PillToggle`) 🟡 | lib |
| `hooks/` | 48 hooks, one per backend capability | lib |
| `lib/` | 22 modules — `fetcher`, `api`, `sseStream`, pure helpers | (nothing above) |
| `types/` | `versioning.ts`, `versionGraph.ts` — the only shared types | — |

Enforced by `.dependency-cruiser.cjs` (`no-circular` and the two
`*-import-app` rules at **error**).

### The three HTTP access paths 🟢

```ts
// lib/fetcher.ts — what the SWR hooks actually use
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";
export async function fetcher<T>(path: string): Promise<T>           // GET
export async function putJson<T>(path: string, body: unknown): Promise<T>
export { API_BASE };

// lib/api.ts — the richer client, used by non-SWR call sites
export class ApiError extends Error { status: number; details?: unknown }
export async function fetchAPI<T>(path: string, init?: RequestInit): Promise<T>
export const api = { get, post, put, delete };                        // 204 -> undefined

// lib/sseStream.ts — POST-based SSE
export interface SseEvent<T> { event: string; data: T }
export async function* parseSseStream<T>(response: Response): AsyncGenerator<SseEvent<T>>
```

## Main Flow

### F1 — Render tree 🟢

```
app/layout.tsx                    (server) fonts + metadata + font CSS variables
└ app/page.tsx                    (5 lines)
└ app/workbench/layout.tsx        "use client" — THE SHELL
  Suspense
  └ AeroplaneProvider                     selection, URL sync, localStorage mirror, hydrated
    └ UnsavedChangesProvider
      ├ Header(onOpenHistory)
      ├ WorkbenchImportWarningBanner
      ├ main → {children}                 the active tab page
      ├ VersionGraphOverlay               conditional, key={rootId}
      ├ MetricsDashboardContainer         gh-881, docked band
      ├ CopilotStrip(onOpenHistory)       docked strip
      ├ UnsavedChangesModal
      └ AeroplanePickerHost
```

`key={rootId}` on the overlay forces a full remount when the lineage changes,
discarding stale layout state. 🟡

### F2 — Selection 🟢

```
?aeroplane=<uuid>   ← the SOURCE OF TRUTH
setAeroplaneId(id):
    router.replace(`?aeroplane=${id}`)          # URL first
    localStorage.setItem("da3dalus_aeroplane_id", id)   # mirror

on mount:
    id = searchParams.get("aeroplane") ?? localStorage.getItem(STORAGE_KEY)
    setHydrated(true)          # pages check this to avoid a "no aircraft" flash
```

### F3 — The hook convention 🟢

```ts
export function useLineageTree(rootId: number | null) {
  const path = rootId !== null ? `/lineages/${rootId}/tree` : null;   // null = disabled
  const { data, error, isLoading, mutate } = useSWR<TreeOut>(path, fetcher);
  return { tree: data, isLoading, error, mutate };                    // renamed
}
```

~30 of the 48 hooks use `useSWR` directly; the rest wrap actions
(`useVersionActions`, `useCopilot`, …). Writes call `putJson` / `api.*` and then
either the hook's own `mutate()` or `useSWRConfig().mutate(key)` for cross-hook
invalidation. 🟢

Detail in [`data-fetching-swr`](data-fetching-swr/design.md).

### F4 — SSE over POST 🟢

```ts
const res = await fetch(`${API_BASE}/aeroplanes/${id}/copilot/stream`, {
  method: "POST", headers: {"Content-Type": "application/json"},
  body: JSON.stringify({ message, context_hint }),
});
for await (const { event, data } of parseSseStream(res)) {
  token       -> append data.text to the in-progress assistant text
  tool_call   -> show toolLabel(data.name)
  tool_result -> clear the chip
  done        -> mutate the history SWR key   (+ surface data.truncated)
  error       -> set errorMessage
}
```

The parser splits on `\n\n`, keeps the trailing fragment in a buffer across
reads, joins multiple `data:` lines with `\n`, JSON-parses with a raw-string
fallback, and flushes a trailing record after the stream closes (*"some backends
close the stream without a final blank-line separator"*). 🟢

### F5 — The 3D viewer 🟢

```ts
import "three-cad-viewer/css";                    // STATIC — line 6
...
const tcv = await import("three-cad-viewer");     // DYNAMIC — line 90
const viewer = new tcv.Viewer(container, options, notifyCallback);
viewer.render(shapes, states);
```

plus `next.config.ts` aliasing `three` to one resolved path in **both** the
webpack and turbopack resolvers, so the app and the viewer share one three.js
instance. The asymmetry is deliberate and documented as fragile. 🟢

`useTessellation` keeps a **module-level** `Map` keyed by
`` `${aeroplaneId}/${wingName}` ``, storing the tessellation together with the
aeroplane's `updated_at`; a mismatch invalidates. `invalidateTessellationCache`
is exported so a geometry save restores the "Preview 3D" affordance. 🟡
Per-tab, unbounded, no eviction.

Detail in [`cad-viewer-integration`](cad-viewer-integration/design.md).

### F6 — Charts 🟢

```ts
useEffect(() => {
  let node = ref.current;
  (async () => {
    const Plotly = await import("plotly.js-gl3d-dist-min");   // 1.5 MB, runtime only
    await Plotly.newPlot(node, data, {
      paper_bgcolor: "#111111", plot_bgcolor: "#111111",
      font: { color: "#B8B9B6" }, ...
    }, config);
  })();
  return () => { Plotly.purge(node); };
}, [deps]);
```

Eight components chart; `AnalysisViewerPanel` performs the dynamic import at
five separate call sites. Dark theming is repeated per figure rather than
factored into a shared layout template. 🟡
`react-plotly.js` was a declared dependency that is never imported — 🟢 removed (`R2-13`).

Detail in [`analysis-dashboards-plotly`](analysis-dashboards-plotly/design.md).

### F7 — Feature areas 🟢

| Area | Route | Key components | Backend surface |
|---|---|---|---|
| Wing & fuselage editor | `/workbench` | `AeroplaneTree` (1 197 l.), `PropertyForm` (924), `SegmentPaginator`, `WingOutlineViewer` (1 005), `SparEditDialog`, `TedEditDialog`, `TurbulatorEditDialog`, `SparSizingPanel` (871) | `/wings`, `/wings/{n}/wingconfig`, `/wing-xsecs`, spares/TED/turbulator, `/fuselages` |
| Analysis | `/workbench/analysis` | `AnalysisViewerPanel` (1 567), `AnalysisConfigPanel` (1 063), `OperatingPointsPanel` (1 076), `StreamlinesViewer`, `VnDiagram`, `trim-interpretation/*` | aeroanalysis, operating points, stability, flight envelope, strip forces, speed polar |
| Components / COTS | `/workbench/components` | `ComponentTree`, `CotsPickerDialog`, `ComponentEditDialog`, `ComponentTypeManagementDialog` | `/components`, `/component-types`, `/component-tree` |
| Mission & sizing | `/workbench/mission` | `mission/*` (5), `MatchingChartTab` (1 518), `TailVolumeCard`, `EnduranceCard`, `AssumptionsPanel` | mission objectives/presets, design assumptions, matching chart, tail sizing, endurance |
| Powertrain | `/workbench/powertrain` | `PowertrainTab` (1 190), `PowertrainSizingModal` (760) | powertrain sizing / solution space / performance |
| Construction plans | `/workbench/construction-plans` | `construction-plans/*` (10), `PlanTree`, `ConstructionPartsGrid`, `CreatorGallery` | construction plans/parts/templates, creators |
| Airfoil preview | `/workbench/airfoil-preview` | `AirfoilPreviewViewerPanel` (1 039), `AirfoilSuitabilityCard`, `AirfoilProxyChart` | airfoils, suitability, section AoA |
| Versioning | overlay (any tab) | `VersionGraphOverlay` (1 117), `VersionGraph`, `VersionCompareView` (732), `SnapshotDialog` | `/lineages/{root}/tree`, `/branches`, `/aeroplanes/compare` |
| AI copilot | docked strip | `CopilotStrip` (467), `useCopilot` (215), `useCopilotProposal` (111) | `/copilot-history`, `/copilot/stream` |
| Metrics dashboard | docked band | `metrics-dashboard/*` (7) incl. `PlanformDiagram`, `metricsMock.ts` 🟡 | computation context, mass/CG, stability |
| OpenVSP import | picker + banners | `ImportOpenVspButton`, `ImportProgressBar`, `ImportScaleInputs`, `ImportWarningBanner` | `/api/v2` import SSE |

## Alternative Flows

- **No aircraft selected:** every hook's key is `null`; no requests fire; pages
  render an empty state gated on `hydrated`. 🟢
- **A legacy pre-versioning aeroplane** (no lineage): `useCopilotProposal`
  returns `null` and the version overlay has nothing to draw. 🟢
- **The backend is down:** `fetcher` throws a plain `Error`; each hook renders
  its own error state — there is **no** global handler. 🔴
- **A 204 response:** `lib/api.ts` returns `undefined`; `lib/fetcher.ts` would
  attempt `res.json()` and throw. 🟡
- **A backend schema change:** nothing fails at runtime until a field is read;
  `tsc` only catches it if a hand-written mirror or fixture disagrees. 🔴
- **The SSE stream ends without a final blank line:** the trailing record is
  flushed. 🟢
- **A non-JSON `data:` payload:** the raw string is yielded. 🟢
- **A stale tessellation** (`updated_at` changed): recomputed. 🟢
- **Two three.js instances** (alias missing in one resolver): the viewer fails
  at runtime. 🔴
- **A charting component unmounts mid-render:** `Plotly.purge(node)` in the
  effect cleanup. 🟢
- **Node ≥ 24 in CI or locally:** jsdom `localStorage` breaks and tests fail
  spuriously. 🔴

## Dependencies

- **The FastAPI v2 API**, called directly from the browser — the only backend
  dependency. See [`contracts.md`](contracts.md).
- `swr` for all server state; no other data layer.
- `three` + `three-cad-viewer`, sharing one instance via the dual alias.
- `plotly.js-gl3d-dist-min`, runtime-imported only.
- `streamdown` + `remark-math` + `katex` for copilot markdown (needs the
  Tailwind `@source` escape hatch).
- Node **22** for tests and typecheck.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| A client-only SPA inside the App Router | `"use client"` on everything under `/workbench` | 🟢 |
| Call the API directly from the browser, with no server proxy | `lib/fetcher.ts`; no `route.ts` anywhere | 🟢 (a 🟡 divergence from `frontend/CLAUDE.md`) |
| SWR as the only server-state layer, with no global config | 48 hooks, no `SWRConfig` | 🟢 (a 🟡 gap) |
| The URL is the source of truth for selection; `localStorage` is a mirror | `AeroplaneContext` | 🟢 |
| A `null` SWR key as the universal disabled state | every hook | 🟢 |
| Hand-rolled SSE because `EventSource` is GET-only | `sseStream.ts` docstring | 🟢 |
| Static CSS + dynamic library import for the CAD viewer | `CadViewer.tsx:6,90` | 🟢 (documented as fragile) |
| Alias `three` in both webpack and turbopack | `next.config.ts` | 🟢 |
| A module-level tessellation cache validated by `updated_at` | `useTessellation` | 🟢 |
| Runtime-only Plotly import, purge on unmount | `StreamlinesViewer:7` | 🟢 |
| Per-figure dark theming rather than a shared template | 8 chart components | 🟡 |
| Tailwind v4 tokens mapped 1:1 from the pencil design file | `globals.css` `@theme inline` | 🟢 |
| Dark theme only | no `prefers-color-scheme` handling | 🟢 |
| Enforce layering with dependency-cruiser rather than convention | `.dependency-cruiser.cjs` | 🟢 |
| `tsc --noEmit` as a CI gate distinct from lint and tests | CI `frontend` job | 🟢 |
| Hand-mirror backend types instead of generating a client | `useCopilot.ts` comment | 🟢 (a 🟡 risk) |
| Pin Next.js to a canary build | `package.json:33` | 🟢 (a 🟡 risk) |

## Internal State

| State | Where | Lifecycle |
|---|---|---|
| `aeroplaneId` and the selection fields | `AeroplaneContext` | per tab; mirrored to the URL and `localStorage` |
| `hydrated` | `AeroplaneContext` | false → true after the first client pass |
| `lastImportWarnings` | `AeroplaneContext` | in memory only (gh-695) |
| unsaved-changes flag | `UnsavedChangesContext` | per editing session |
| all server state | the SWR cache | per tab; revalidated on write |
| tessellations | a module-level `Map` in `useTessellation` | per tab, **unbounded** 🟡 |
| version-graph pan/zoom | `localStorage` via `lib/versionGraphViewState.ts` | persistent |
| strip / banner / overlay UI flags | `localStorage` | persistent |

## Observability

- 🟡 Browser-side only: `console` errors from failed fetches, plus each hook's
  own error state rendered in its panel.
- 🔴 No global error boundary, no client error reporting, no telemetry, and no
  global SWR `onError` — a failing hook is visible only in its own panel.
- 🔴 `useCopilot.TOOL_LABEL_MAP` covers **3 of 6** copilot tools
  (`get_wing_geometry`, `apply_design_edits`, `discard_proposal` fall through to
  `Calling <name>…`) — the two **write** tools, whose activity matters most, are
  the unlabelled ones.

## Risks and Gaps

- 🔴 **The documented CORS strategy is not implemented.** `frontend/CLAUDE.md`
  claims all API calls go through server-side route handlers or server actions;
  there are none. The backend's `allow_origins=["*"]` is the consequence, not an
  independent choice.
- 🟡 **The hooks migrate onto one typed client** (`Q-FW-2`, derived), which removes the second error shape and with it `lib/parseApiError.ts`. Previously two clients with two error shapes, bridged by
  `lib/parseApiError.ts`.
- 🔴 **No global `SWRConfig`** — no shared revalidation, retry or error policy
  across 48 hooks.
- 🔴 **Backend response types are hand-mirrored**; nothing is generated from
  `/openapi.json`, so a schema change is caught only by `tsc` against
  hand-written fixtures — exactly the failure mode the CI note warns about.
- 🔴 **`react-plotly.js` is an unused dependency.**
- 🟢 **Extract a design-system layer; decompose the panels opportunistically — no hard line-count budget** (`Q-FW-4`, maintainer-answered). `components/ui/` holds a single primitive while eight shared building blocks sit flat among feature components, which is why `frontend/CLAUDE.md` needs a manual "reuse before creating" checklist — the convention exists because the directory structure does not encode it. Previously** — the tab pages are thin, the panels
  are not.
- 🟢 **The eight shared building blocks move into `components/ui/`** (`Q-FW-4`). Previously**; shared building blocks
  (`TreeCard`, `SimpleTreeRow`, `Field`, `Chip`, `DialogField`, `InfoTooltip`,
  `AlertBanner`, `GroupAddMenu`) sit flat among feature components, which is why
  `frontend/CLAUDE.md` needs an explicit "reuse before creating" checklist.
- 🔴 **`metricsMock.ts` ships inside the production component tree.**
- 🔴 **`TOOL_LABEL_MAP` covers 3 of 6 tools**, missing both write tools.
- 🔴 **Dark theme only** — no light mode, no `prefers-color-scheme`.
- 🟢 **Move to a stable release** (`Q-FW-6`, maintainer-answered). Checked 2026-08-15: **16.3.0 LTS** shipped 2026-08-03, so the move is `16.2.1-canary.33` → `16.3.x` — the same major version, and the target is an LTS. Node 22 remains required for the test suite (Node ≥ 24 breaks jsdom `localStorage`) and must be re-checked, not assumed fixed. Previously build** whose behaviour differs from the
  documentation and from model training data.
- 🔴 **Tests require Node 22**; Node ≥ 24 breaks jsdom `localStorage`.
- 🟢 **Deliberately not built** (`Q-FW-7`): telemetry for an audience of one is instrumentation without a consumer (ADR 0024). Previously or telemetry.**
- 🟡 **The tessellation cache is unbounded** and per-tab; only an `updated_at`
  mismatch evicts.
- 🟡 **Plotly dark theming is duplicated per figure.**
- 🟡 **The frontend never touches `/mcp`** — MCP is for external agents; the
  in-app AI path is the copilot SSE endpoint.
