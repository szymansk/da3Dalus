# frontend-workbench — Implementation Tasks

> Executable sequence to re-implement the module from the legacy behaviour.
> Every task cites the legacy file, a definition of done, and a confidence
> marker.
> Use-case task lists:
> [`workbench-shell-and-routing`](workbench-shell-and-routing/tasks.md) ·
> [`data-fetching-swr`](data-fetching-swr/tasks.md) ·
> [`cad-viewer-integration`](cad-viewer-integration/tasks.md) ·
> [`analysis-dashboards-plotly`](analysis-dashboards-plotly/tasks.md).

## Prerequisites

- [ ] **Node 22** (`nvm use 22`) — Node ≥ 24 breaks jsdom `localStorage` and
      produces spurious test failures.
- [ ] The FastAPI backend reachable at `NEXT_PUBLIC_API_URL`
      (default `http://localhost:8001`) with wide-open CORS.
- [ ] `next 16.2.1-canary.33` and `eslint-config-next` at the **same** canary
      version.
- [ ] `three` + `three-cad-viewer`, `plotly.js-gl3d-dist-min`, `swr`,
      `tailwindcss 4`, `streamdown` + `remark-math` + `katex`.

## Tasks

- [ ] **T-01 — `lib/fetcher.ts`.**
  `API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001"`;
  `fetcher<T>(path)` (GET, throws
  `Error("<status> <statusText>: <body>")`); `putJson<T>(path, body)`.
  - Legacy origin: `frontend/lib/fetcher.ts`
  - Definition of done: this is the client **the SWR hooks use** — not
    `lib/api.ts`. Record the plain-`Error` shape as the source of the two-client
    divergence.
  - Confidence: 🟢

- [ ] **T-02 — `lib/api.ts`.**
  `ApiError(status, message, details)`; `fetchAPI` setting `Content-Type` and
  returning `undefined` on **204**; the `api.{get,post,put,delete}` helper.
  - Legacy origin: `frontend/lib/api.ts`
  - Definition of done: a 204 yields `undefined` (the behaviour `lib/fetcher.ts`
    lacks). Record that the richer client is the less-used one.
  - Confidence: 🟢

- [ ] **T-03 — `lib/sseStream.ts`.**
  `parseSseStream<T>(response)` as an async generator: split on `\n\n`, buffer
  the trailing fragment across reads, join multiple `data:` lines with `\n`,
  JSON-parse with a raw-string fallback, flush a trailing record after the
  stream ends, release the reader lock in `finally`.
  - Legacy origin: `frontend/lib/sseStream.ts`
  - Definition of done: a record split across two chunks yields exactly one
    event; a stream closing without a final blank line still yields its last
    record. Carry the docstring — `EventSource` is GET-only and both streams
    here are POST.
  - Confidence: 🟢

- [ ] **T-04 — `lib/parseApiError.ts`.**
  Normalise both the backend's `{"error": {...}}` envelope and its
  `{"detail": ...}` shape, and both client error types.
  - Legacy origin: `frontend/lib/parseApiError.ts`
  - Definition of done: all four combinations produce a displayable message.
    Record that this module exists **only** because of two backend envelopes and
    two frontend clients.
  - Confidence: 🟢

- [ ] **T-05 — `AeroplaneContext`.**
  `aeroplaneId`, `hydrated`, `selectedWing`, `selectedXsecIndex`,
  `selectedFuselage`, `selectedFuselageXsecIndex`,
  `treeMode: "wingconfig" | "asb" | "fuselage"`, `pickerOpen`,
  `lastImportWarnings`, plus the setters. `STORAGE_KEY =
  "da3dalus_aeroplane_id"`; `setAeroplaneId` does a router replace **and**
  mirrors to `localStorage`.
  - Legacy origin: `frontend/components/workbench/AeroplaneContext.tsx`
  - Definition of done: the URL is the source of truth; a fresh tab with no
    query restores from `localStorage`; `hydrated` is false during the first
    client pass so pages do not flash "no aircraft selected".
  - Confidence: 🟢

- [ ] **T-06 — The shell layout.**
  `app/workbench/layout.tsx` (`"use client"`): `Suspense` →
  `AeroplaneProvider` → `UnsavedChangesProvider` → `Header`,
  `WorkbenchImportWarningBanner`, `main`, `VersionGraphOverlay`
  (`key={rootId}`), `MetricsDashboardContainer`, `CopilotStrip`,
  `UnsavedChangesModal`, `AeroplanePickerHost`.
  - Legacy origin: `frontend/app/workbench/layout.tsx` (80 l.)
  - Definition of done: every one of the seven tabs renders the same shell. The
    `key={rootId}` remount on the overlay is deliberate — it discards stale
    layout state when the lineage changes.
  - Confidence: 🟢

- [ ] **T-07 — The root layout and landing page.**
  `app/layout.tsx`: `Geist`, `Geist_Mono`, `JetBrains_Mono` via
  `next/font/google`, metadata, font CSS variables. `app/page.tsx`: five lines.
  - Legacy origin: `frontend/app/layout.tsx`, `frontend/app/page.tsx`
  - Definition of done: this is the **only** meaningful server component.
  - Confidence: 🟢

- [ ] **T-08 — The 48 hooks.**
  One per backend capability, following the convention: literal-path SWR key,
  `null` key when disabled, renamed return fields, `mutate()` after a write,
  `useSWRConfig().mutate(key)` for cross-hook invalidation.
  - Legacy origin: `frontend/hooks/` (48 files)
  - Definition of done: no hook returns raw `data`; no hook fires a request with
    nothing selected. Record the **absence** of a global `SWRConfig` as a gap.
  - Confidence: 🟢

- [ ] **T-09 — `useCopilot`.**
  SWR history (`GET /aeroplanes/{id}/copilot-history`) + `sendMessage` POSTing
  to `/copilot/stream` and consuming `parseSseStream`; streaming text and
  current-tool state exposed; `mutate` on `done`; `errorMessage` from `error`
  events; `TOOL_LABEL_MAP` + `toolLabel(name)`.
  - Legacy origin: `frontend/hooks/useCopilot.ts` (215 l.)
  - Definition of done: tokens render incrementally and the persisted history
    replaces them on `done`. **Record** that `TOOL_LABEL_MAP` covers only 3 of
    the 6 tools — the two write tools fall through to `Calling <name>…`.
  - Confidence: 🟢

- [ ] **T-10 — `useCopilotProposal` (gh-939).**
  Detect a branch with `created_by === "copilot"` and `is_main === false` in the
  lineage tree; expose `adopt` / `discard` / `busy`; return `null` when no
  aircraft is selected, no tree exists, or no copilot branch is present.
  - Legacy origin: `frontend/hooks/useCopilotProposal.ts` (111 l.)
  - Definition of done: it reuses `useLineageTree` and `useVersionActions` —
    **no new API endpoints** (the docstring says so). This hook is the human
    half of ADR 0007.
  - Confidence: 🟢

- [ ] **T-11 — The seven tab pages.**
  Thin pages delegating to panels: wing & fuselage editor, analysis,
  components/COTS, mission, powertrain, construction plans, airfoil preview.
  - Legacy origin: `frontend/app/workbench/*/page.tsx` (2 242 l. total)
  - Definition of done: the pages stay thin; the weight lives in the panels.
    Record the seven >1 000-line panels as a maintainability gap.
  - Confidence: 🟢

- [ ] **T-12 — `next.config.ts`.**
  `NEXT_PUBLIC_API_URL` in `env`; the `three` resolve alias for **webpack and
  turbopack**; `allowedDevOrigins: ["127.0.0.1", "localhost"]` (gh-825).
  - Legacy origin: `frontend/next.config.ts`
  - Definition of done: both resolvers alias `three` — a single-resolver alias
    silently gives the viewer a second three.js instance.
  - Confidence: 🟢

- [ ] **T-13 — `app/globals.css`.**
  Tailwind v4 with the design tokens under `@theme inline` (mapped 1:1 from the
  pencil `da3Dalus.pen` tokens), plus the two escape hatches:
  `@source "../node_modules/streamdown/dist"` and
  `dialog:not([open]) { display: none !important }`.
  - Legacy origin: `frontend/app/globals.css`
  - Definition of done: copilot markdown keeps its classes after a production
    build (the `@source` line is what prevents Tailwind from purging them), and
    a closed native `<dialog>` stays hidden.
  - Confidence: 🟢

- [ ] **T-14 — `.dependency-cruiser.cjs`.**
  `no-circular` (**error**), `no-components-import-app` (**error**),
  `no-hooks-import-app` (**error**), `no-hooks-import-components` (warn),
  `no-lib-import-components` (warn), `no-orphans` (info, excluding `page.tsx`,
  `layout.tsx`, `.d.ts`, tests); `tsPreCompilationDeps: true`; exclude `e2e/`
  and `.features-gen`.
  - Legacy origin: `frontend/.dependency-cruiser.cjs`
  - Definition of done: `npm run deps:check` fails on a cycle. This is the only
    automated architectural guard on 47 kLOC.
  - Confidence: 🟢

- [ ] **T-15 — The CI gate scripts.**
  `test:unit` (vitest), `npx tsc --noEmit`, `lint` (eslint 9 +
  `eslint-plugin-sonarjs`, `--max-warnings=0` on staged files via husky +
  lint-staged), `deps:check`, `test:e2e` (playwright-bdd, `--grep-invert @slow`),
  `bdd:missing` (gh-564).
  - Legacy origin: `frontend/package.json`, the CI `frontend` job
  - Definition of done: all three gates run on **Node 22**. `tsc --noEmit` is a
    *separate* gate because vitest and eslint stay green while a new required
    response field breaks existing fixture literals.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Shell:** all seven routes render header, metrics dock and
      copilot strip.
- [ ] **TT-02 — Selection:** URL is the source of truth; `localStorage` mirrors;
      a fresh tab restores.
- [ ] **TT-03 — `hydrated`:** no "no aircraft selected" flash on first paint.
- [ ] **TT-04 — Null key:** no request fires with nothing selected.
- [ ] **TT-05 — Hook shape:** every hook returns renamed fields, never `data`.
- [ ] **TT-06 — Revalidation:** a write calls `mutate()`; a version action
      revalidates the tree **and** the aeroplanes list.
- [ ] **TT-07 — SSE parsing:** split records, multiple `data:` lines, non-JSON
      payload, trailing record without a blank line.
- [ ] **TT-08 — Copilot stream:** tokens append; `done` revalidates history;
      `truncated` surfaced; `error` sets `errorMessage`.
- [ ] **TT-09 — Proposal detection:** a `created_by === "copilot"`,
      `is_main === false` branch is found; adopt/discard call the versioning
      routes.
- [ ] **TT-10 — Error normalisation:** both backend envelopes × both client
      error types.
- [ ] **TT-11 — Viewer import:** dynamic `three-cad-viewer`, static CSS.
- [ ] **TT-12 — Tessellation cache:** reused on an unchanged `updated_at`,
      recomputed otherwise, cleared by `invalidateTessellationCache`.
- [ ] **TT-13 — No top-level Plotly:** a static check that no module imports
      `plotly.js` or `react-plotly.js` at top level.
- [ ] **TT-14 — Plotly cleanup:** `Plotly.purge` on unmount.
- [ ] **TT-15 — Layering:** `deps:check` reports no `error`-level violation.
- [ ] **TT-16 — Types:** `tsc --noEmit` exits zero on Node 22.
- [ ] **TT-17 — E2E:** the 10 feature files pass with `@slow` excluded;
      `bdd:missing` exits zero.

## Suggested Order

1. **T-01 → T-04** the three fetch wrappers and the error normaliser. Everything
   else consumes them, and their shapes determine every hook's error handling.
2. **T-05 → T-07** the context and the shell. Selection is the precondition for
   every hook's key.
3. **T-08** the hooks, grouped by feature area, following the convention
   strictly. Add TT-04 and TT-05 as lint-like guards early — 48 hooks drift
   otherwise.
4. **T-09 → T-10** the copilot hooks, which need both SSE (T-03) and the
   versioning hooks (part of T-08).
5. **T-11** the tab pages and their panels — the bulk of the work; keep the
   pages thin.
6. **T-12 → T-13** build configuration and tokens. The dual `three` alias must
   land before the viewer work
   ([`cad-viewer-integration`](cad-viewer-integration/tasks.md)).
7. **T-14 → T-15** the guards last, but **before** the codebase grows: the
   layering rules are far cheaper to satisfy early than to retrofit.

## Pending Gaps

- **Should the frontend introduce route handlers or server actions**, as
  `frontend/CLAUDE.md` claims it already does? Doing so would let the backend
  drop `allow_origins=["*"]`.
- **Should there be one HTTP client?** Two exist with two error shapes, bridged
  by `parseApiError`.
- **Should a global `SWRConfig` define revalidation, retry and error policy**
  instead of 48 independent decisions?
- **Should the API client be generated from `/openapi.json`** instead of
  hand-mirroring every response type?
- **Should `react-plotly.js` be removed** — it is declared and never imported.
- **Should the seven >1 000-line panels be decomposed?**
- **Should `components/ui/` become a real design-system boundary?** It holds one
  primitive while eight shared building blocks sit flat among feature
  components.
- **Should `metricsMock.ts` move out of the production component tree?**
- **Should `TOOL_LABEL_MAP` cover all six copilot tools**, especially the two
  write tools whose activity matters most?
- **Should the tessellation cache have an eviction policy?** It is module-level
  and unbounded.
- **Should Plotly dark theming be a shared layout template** rather than
  repeated per figure?
- **Is a light theme wanted?** Today the app is dark-only with no
  `prefers-color-scheme` handling.
- **Should `next` be pinned to a stable release** instead of
  `16.2.1-canary.33`?
- **Should there be client-side error reporting** — an error boundary, a global
  SWR `onError`, telemetry? None exists.
