# Flowcharts — frontend-workbench

## 1. Layer map and the enforced dependency direction

```mermaid
flowchart TD
    subgraph APP["app/ — App Router (12 files)"]
        RL["app/layout.tsx (server)<br/>fonts + metadata only"]
        RP["app/page.tsx (5 lines) → redirect"]
        WL["app/workbench/layout.tsx ('use client')<br/>the real shell"]
        P1["/workbench — wing & fuselage editor"]
        P2["/workbench/analysis"]
        P3["/workbench/components"]
        P4["/workbench/mission"]
        P5["/workbench/powertrain"]
        P6["/workbench/construction-plans"]
        P7["/workbench/airfoil-preview"]
    end

    subgraph COMP["components/ (129 files)"]
        WB["workbench/ + 5 sub-folders<br/>construction-plans · metrics-dashboard ·<br/>mission · stability-overlay · trim-interpretation"]
        UI["ui/ — PillToggle (the only primitive)"]
    end

    HOOKS["hooks/ (48 files) — one per backend feature"]
    LIB["lib/ (22 files) — fetcher, api, sseStream, pure helpers"]
    TYPES["types/ — versioning.ts, versionGraph.ts"]
    BE["FastAPI v2 @ NEXT_PUBLIC_API_URL<br/>(default http://localhost:8001)"]

    RL --> WL
    WL --> P1 & P2 & P3 & P4 & P5 & P6 & P7
    P1 & P2 & P3 & P4 & P5 & P6 & P7 --> WB
    WB --> UI
    WB --> HOOKS
    HOOKS --> LIB
    LIB -->|"fetch, direct from the browser"| BE
    HOOKS --> TYPES

    WB -.->|"error: no-components-import-app"| APP
    HOOKS -.->|"error: no-hooks-import-app"| APP
    HOOKS -.->|"warn: no-hooks-import-components"| COMP
    LIB -.->|"warn: no-lib-import-components"| COMP
```

Dotted arrows are the `dependency-cruiser` rules (`.dependency-cruiser.cjs`),
checked by `npm run deps:check`: `no-circular` (**error**),
`no-components-import-app` / `no-hooks-import-app` (**error**),
`no-hooks-import-components` / `no-lib-import-components` (**warn**),
`no-orphans` (info, with `page.tsx` / `layout.tsx` / `.d.ts` / tests excluded).

## 2. Route tree — one shell, seven tabs

```mermaid
flowchart TD
    A["/"] --> B["/workbench"]
    subgraph SHELL["app/workbench/layout.tsx"]
        direction TB
        S0["Suspense"] --> S1["AeroplaneProvider"]
        S1 --> S2["UnsavedChangesProvider"]
        S2 --> H["Header (onOpenHistory)"]
        S2 --> W["WorkbenchImportWarningBanner"]
        S2 --> M["main → {children} (the active tab)"]
        S2 --> D["MetricsDashboardContainer (gh-881, docked, every tab)"]
        S2 --> C["CopilotStrip (docked, every tab)"]
        S2 --> V["VersionGraphOverlay (conditional, keyed by rootId)"]
        S2 --> U["UnsavedChangesModal + AeroplanePickerHost"]
    end
    M --> T1["/workbench — wing/fuselage editor (422 l.)"]
    M --> T2["/workbench/analysis (199 l.)"]
    M --> T3["/workbench/components (303 l.)"]
    M --> T4["/workbench/mission (55 l.)"]
    M --> T5["/workbench/powertrain (26 l.)"]
    M --> T6["/workbench/construction-plans (739 l.)"]
    M --> T7["/workbench/airfoil-preview (493 l.)"]
```

`app/layout.tsx` is the only server component of consequence — it loads
`Geist`, `Geist_Mono` and `JetBrains_Mono` via `next/font/google`, sets the
metadata and applies the CSS variables. **Everything below `/workbench` is
`"use client"`**: there are no route handlers (`app/**/route.ts` does not
exist), no server actions and no server-side data fetching.

## 3. Data flow — browser talks to FastAPI directly

```mermaid
sequenceDiagram
    autonumber
    participant C as Component
    participant H as hooks/use*.ts
    participant S as SWR cache
    participant F as lib/fetcher.ts
    participant B as FastAPI :8001

    C->>H: useWing(aeroplaneId, wingName)
    H->>S: useSWR(path | null, fetcher)
    Note over H,S: a null key disables the request —<br/>the standard "not selected yet" guard
    S->>F: fetcher(path)
    F->>B: GET ${API_BASE}${path}
    B-->>F: JSON (or !ok → throw Error("<status> <text>: <body>"))
    F-->>S: data
    S-->>H: {data, error, isLoading, mutate}
    H-->>C: named result ({wing, mutate, …})

    C->>H: save()
    H->>F: putJson(path, body)  /  lib/api.ts api.post/put/delete
    F->>B: PUT/POST/DELETE
    H->>S: mutate() — revalidate this key
    H->>S: useSWRConfig().mutate(otherKey) — cross-hook invalidation
```

`API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001"`
(`lib/fetcher.ts:1`), also pinned in `next.config.ts` via the `env` block.
**Every call is a cross-origin browser fetch**, which is precisely why the
backend runs `allow_origins=["*"]`.

Two parallel clients coexist:

```mermaid
flowchart LR
    subgraph L1["lib/fetcher.ts"]
        F1["fetcher<T>(path) — GET, used as the SWR fetcher"]
        F2["putJson<T>(path, body)"]
        F3["API_BASE"]
        E1["throws plain Error('404 Not Found: …')"]
    end
    subgraph L2["lib/api.ts"]
        A1["fetchAPI<T>(path, init)"]
        A2["api.get / post / put / delete"]
        E2["throws ApiError(status, message, details)<br/>+ 204 → undefined"]
    end
    L2 -->|"imports API_BASE"| L1
```

`lib/api.ts` is the richer client (typed `ApiError`, 204 handling) but the SWR
hooks use `lib/fetcher.ts`, so error shape depends on which client a given call
path went through. `lib/parseApiError.ts` exists to normalise the difference.

## 4. Selection state — URL is the source of truth

```mermaid
stateDiagram-v2
    [*] --> Hydrating: AeroplaneProvider mounts
    Hydrating --> Ready: read ?aeroplane= from useSearchParams()
    Hydrating --> Ready: else read localStorage['da3dalus_aeroplane_id']
    Ready --> Ready: setAeroplaneId → router replace(?aeroplane=…) + localStorage write
    Ready --> Ready: selectWing / selectXsec / selectFuselage / selectFuselageXsec
    Ready --> Ready: setTreeMode('wingconfig' | 'asb' | 'fuselage')
    Ready --> Picker: openPicker() → AeroplanePickerHost
    Picker --> Ready: closePicker()
```

`hydrated` is exposed so children can avoid rendering "no aircraft selected"
during the first client pass. There is **no** Redux / Zustand / Jotai — state
is React context (`AeroplaneContext`, `UnsavedChangesContext`) + SWR cache +
URL search params + a handful of `localStorage` keys
(`AeroplaneContext`, `CopilotStrip`, `WorkbenchImportWarningBanner`,
`ImportWarningBanner`, `StabilityOverlay`, `lib/versionGraphViewState.ts`).

## 5. Wing editor — the main tab

```mermaid
flowchart TD
    A["/workbench page.tsx"] --> B["useAeroplaneContext() — aeroplaneId, selection, treeMode"]
    B --> C["useWings / useFuselages — name lists"]
    C --> D["AeroplaneTree (TreeCard + SimpleTreeRow, @dnd-kit)"]
    B --> E{"treeMode"}
    E -->|"wingconfig"| F["useWingConfig(id, wing) — mm segments"]
    E -->|"asb"| G["useWing(id, wing) — metre x_secs"]
    E -->|"fuselage"| H["useFuselage(id, fuselage)"]
    F & G & H --> I["SegmentPaginator — one station/segment at a time"]
    I --> J["PropertyForm (ref: PropertyFormHandle)"]
    J --> K["SparEditDialog · TedEditDialog · TurbulatorEditDialog"]
    J --> L["save → putJson → mutate() → invalidateTessellationCache"]
    B --> M["WingOutlineViewer (Plotly, metres)"]
    B --> N["StabilityOverlay"]
    B --> O["useOverlayRegistry"]
```

The `treeMode` switch is the frontend face of the backend's unit duality:
`wingconfig` shows the **mm** `WingConfig` view, `asb` shows the **metre**
cross-section view, and the two are separate hooks over separate endpoints.

## 6. 3D CAD viewer — tessellation pipeline

```mermaid
sequenceDiagram
    autonumber
    participant U as User ("Preview 3D")
    participant T as useTessellation
    participant M as module-level Map cache
    participant B as backend
    participant V as CadViewer.tsx
    participant L as three-cad-viewer

    U->>T: request(aeroplaneId, wingName)
    T->>B: GET /aeroplanes/{id} → updated_at
    T->>M: cacheKey = `${aeroplaneId}/${wingName}`
    alt cached entry has the SAME updatedAt
        M-->>T: cached tessellation, no request
    else stale or absent
        T->>B: tessellate (streamed progress)
        B-->>T: {data: {instances, shapes}, …}
        T->>M: store {aeroplaneId, wingName, updatedAt, data}
    end
    T-->>V: data
    V->>L: const tcv = await import("three-cad-viewer")
    Note over V,L: RUNTIME dynamic import (l.90) —<br/>the CSS is a STATIC import ("three-cad-viewer/css", l.6).<br/>Do not "tidy" this pattern without real browser testing.
    L-->>U: rendered geometry
```

`three` is aliased to a single resolved path in **both** the webpack and the
turbopack config (`next.config.ts`) — without it the app and
`three-cad-viewer` would each load their own copy of three.js.
`invalidateTessellationCache(aeroplaneId, wingName)` is exported so a geometry
save can force the "Preview 3D" affordance back.

## 7. Charts — Plotly is always lazily imported

```mermaid
flowchart LR
    A["chart component mounts"] --> B["useEffect → await import('plotly.js-gl3d-dist-min')"]
    B --> C["Plotly.react(node, data, layout)"]
    C --> D["dark layout props: paper_bgcolor, plot_bgcolor, font.color"]
    A --> E["unmount → Plotly.purge(node)"]
```

Eight components chart with Plotly: `AnalysisViewerPanel` (5 separate
imports), `WingOutlineViewer`, `StreamlinesViewer`, `VnDiagram`,
`MatchingChartTab`, `PowertrainTab`, `ImportFuselageDialog`,
`trim-interpretation/ControlAuthorityChart`. `StreamlinesViewer` carries the
rule in a comment: *"DO NOT import react-plotly.js or plotly.js at top level —
it is 1.5 MB."* `react-plotly.js` is a declared dependency but is **not**
imported anywhere.

Adding an analysis type follows a fixed four-step recipe (`frontend/CLAUDE.md`):
tab entry in `AnalysisViewerPanel.TABS` → config section in
`AnalysisConfigPanel` keyed by `activeTab` → a hook in `hooks/` → Plotly charts.

## 8. Copilot strip — SSE consumed by hand

```mermaid
sequenceDiagram
    autonumber
    participant S as CopilotStrip (467 l.)
    participant H as useCopilot (215 l.)
    participant W as SWR
    participant P as lib/sseStream.parseSseStream
    participant B as backend

    S->>H: mount
    H->>W: useSWR('/aeroplanes/{id}/copilot-history', fetcher)
    W-->>S: persisted messages
    S->>H: sendMessage(text)
    H->>B: POST /aeroplanes/{id}/copilot/stream {message, context_hint}
    B-->>P: response.body (ReadableStream)
    loop per SSE record
        P-->>H: {event, data}
        alt token
            H-->>S: append to the in-progress text (live render)
        else tool_call
            H-->>S: tool chip via toolLabel(name)
        else tool_result
            H-->>S: update the chip
        else error
            H-->>S: errorMessage
        end
    end
    P-->>H: done
    H->>W: mutate() — reload persisted history
```

`lib/sseStream.ts` exists because *"the browser's built-in `EventSource` only
works with GET requests"* — the backend streams are POST. The parser buffers a
trailing incomplete block across chunk boundaries and falls back to the raw
string when a `data:` payload is not JSON. The same helper serves the OpenVSP
import progress stream (gh-737).

`useCopilotProposal` (111 l.) is the second half: it surfaces the open
`copilot-proposal` branch so the user can adopt or discard it — the human side
of the backend's "propose, never mutate" rule.

`TOOL_LABEL_MAP` in `useCopilot.ts` labels only three of the six copilot tools
(`get_design_snapshot`, `run_analysis`, `get_version_tree`); the other three
fall through to the generic `Calling <name>…`.

## 9. Versioning UI

```mermaid
flowchart TD
    A["Header → onOpenHistory"] --> B["VersionGraphOverlay (key = rootId)"]
    B --> C["useLineageTree(rootId) → GET /lineages/{rootId}/tree"]
    C --> D["lib/versionGraphLayout.ts — node/edge placement"]
    D --> E["VersionGraph"]
    E --> F["lib/versionGraphViewState.ts — pan/zoom in localStorage"]
    E --> G["VersionCompareView → GET /aeroplanes/compare?a=&b="]
    E --> H["useVersionActions → snapshot / branch / adopt / restore / discard"]
    H --> I["revalidate the lineage tree AND the aeroplanes list"]
    E --> J["lib/versionProvenance.ts — human vs ai vs copilot badges"]
    E --> K["SnapshotDialog"]
```

Note the **id duality** crossing the boundary: the aeroplane list is addressed
by UUID (`aeroplaneId`), while every versioning route takes the integer PK —
so the layout resolves `int_id` and `root_id` off the aeroplane record before
handing them to the overlay.

## 10. Test topology

```mermaid
flowchart LR
    subgraph UNIT["vitest — __tests__/ (180 test files)"]
        U1["jsdom environment"]
        U2["@testing-library/react + user-event"]
        U3["Node 22 REQUIRED — Node ≥24 breaks jsdom localStorage"]
    end
    subgraph E2E["playwright-bdd — e2e/"]
        F1["features/*.feature (10 Gherkin files)"]
        F2["steps/*.ts"]
        F3["bddgen → generated specs → playwright test"]
        F4["@slow excluded from the default run"]
        F5["npm run bdd:missing — steps without definitions (gh-564)"]
    end
    subgraph CI["CI gates"]
        G1["npx tsc --noEmit"]
        G2["npm run lint (eslint + sonarjs, --max-warnings=0 on staged files)"]
        G3["npm run test:unit"]
        G4["npm run deps:check"]
    end
```

Feature files: `airfoil-suitability`, `analysis-status`, `component-types`,
`ehawk-construction`, `navigation`, `operating-points`,
`polar-design-warning`, `ted-role-ui`, `trim-interpretation`, `turbulator-ui`.
`polar-design-warning` has its own Playwright config.
