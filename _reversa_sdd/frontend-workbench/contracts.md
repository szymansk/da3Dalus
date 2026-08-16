# frontend-workbench — Client-side Integration Contract

> The frontend is **not an HTTP producer**. It publishes no routes, no route
> handlers and no server actions — `app/**/route.ts` does not exist and no file
> declares `"use server"` (verified). 🟢
> What follows is therefore an **API-consumption contract**: which backend
> endpoints the client calls, how it addresses them, how it caches and
> invalidates them, and what it assumes about their shapes.

## Topology 🟢

```
browser (Next.js client bundle)
   │  direct cross-origin fetch
   ▼
FastAPI  http://localhost:8001        (NEXT_PUBLIC_API_URL)
```

There is no BFF, no proxy and no server-side fetch. Consequences:

1. **The backend must allow every origin.** `allow_origins=["*"]` with
   `allow_credentials=True` exists because of this topology, not as an
   independent decision (see
   [`../platform-core/contracts.md`](../platform-core/contracts.md)). 🔴
2. **`frontend/CLAUDE.md:12-13` is stale.** It states *"All API calls go through
   server-side route handlers or server actions to avoid CORS"*. None exist. 🔴
3. **The base URL is baked into the bundle** at build time (`NEXT_PUBLIC_`
   prefix), so changing it requires a rebuild. 🟡

| Config | Read by | Default |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `lib/fetcher.ts:1`, re-declared in `next.config.ts` `env` | `http://localhost:8001` |
| `allowedDevOrigins` | `next.config.ts` | `["127.0.0.1", "localhost"]` — gh-825, keeps the dev server from rejecting the backend HMR websocket |
| `three` resolve alias | `next.config.ts` (webpack **and** turbopack) | `node_modules/three` |

## The three fetch wrappers 🟢

| Wrapper | File | Used by | Error shape | Notes |
|---|---|---|---|---|
| `fetcher(path)` / `putJson(path, body)` | `lib/fetcher.ts` | **all SWR hooks** | plain `Error("<status> <statusText>: <body>")` | `fetcher` is GET-only; `putJson` sets `Content-Type` and always parses JSON |
| `fetchAPI(path, init)` + `api.{get,post,put,delete}` | `lib/api.ts` | non-SWR call sites | typed `ApiError(status, message, details)` | sets `Content-Type`; **`204 → undefined`** |
| `parseSseStream(response)` | `lib/sseStream.ts` | copilot stream, OpenVSP import | throws only when `response.body` is absent | POST-based SSE, hand-parsed |

🟡 🟡 **The hooks migrate onto one typed client** (`Q-FW-2`, derived), which removes the second error shape and with it `lib/parseApiError.ts`. Previously: `lib/parseApiError.ts` exists solely to
normalise them for display. The richer client (`lib/api.ts`) is *not* the one the
48 hooks use.

🟡 `lib/fetcher.ts` always calls `res.json()`, so a `204` response would throw —
`lib/api.ts` handles that case, `fetcher` does not.

## SWR key conventions 🟢

```ts
// 1. The key IS the path — no key factory, no prefixing, no serialisation
const path = id !== null ? `/lineages/${id}/tree` : null;

// 2. A null key disables the hook entirely (the universal "nothing selected")
const { data, error, isLoading, mutate } = useSWR<TreeOut>(path, fetcher);

// 3. Hooks never return raw `data`
return { tree: data, isLoading, error, mutate };
```

| Convention | Rule |
|---|---|
| Key format | the **literal request path**, e.g. `` `/aeroplanes/${uuid}/wings` `` |
| Disabled state | key `=== null` |
| Query params | interpolated into the key, so a different filter is a different cache entry (e.g. `` `/construction-plans?plan_type=${t}` ``) |
| Return shape | domain-named fields (`tree`, `wings`, `plans`), never `data` |
| Write path | `putJson` / `api.*`, then `mutate()` |
| Cross-hook invalidation | `useSWRConfig().mutate(key)` with the **exact same literal path** |
| Global config | 🟡 **none** — no `SWRConfig` provider, so no shared `refreshInterval`, `revalidateOnFocus`, retry policy or `onError` |

Because keys are raw paths, an invalidation must reproduce the producing hook's
path string exactly — there is no shared key module. 🟡

## Endpoints consumed 🟢

Extracted from `hooks/` and `lib/`; `{}` marks an interpolated value.

### Aeroplane and geometry

| Path | Method(s) | Hook / caller |
|---|---|---|
| `/aeroplanes` | GET, POST | `useAeroplanes` |
| `/aeroplanes/{}/wings` | GET | `useWings` |
| `/aeroplanes/{}/wings/{}` | GET, PUT, DELETE | wing editor |
| `/aeroplanes/{}/wings/{}/wingconfig` | GET, PUT | `useWingConfig` — **millimetres** |
| `/aeroplanes/{}/wings/{}/section-aoa{}` | GET | `useSectionAoa` |
| `/aeroplanes/{}/fuselages`, `/aeroplanes/{}/fuselages/{}` | GET, PUT, DELETE | fuselage editor |
| `/aeroplanes/{}/component-tree` | GET, PUT | `useComponentTree` |
| `/aeroplanes/{}/construction-parts` | GET | construction tab |

### Mass, mission and sizing

| Path | Method(s) | Hook / caller |
|---|---|---|
| `/aeroplanes/{}/assumptions` | GET, PUT | `useAssumptions` |
| `/aeroplanes/{}/assumptions/computation-context` | GET | metrics dashboard — the gh-924 single source |
| `/aeroplanes/{}/assumptions/recompute-status` | GET | polled while a recompute runs |
| `/aeroplanes/{}/mission-objectives`, `/mission-presets` | GET, PUT | mission tab |
| `/aeroplanes/{}/mission-kpis{}` | GET | mission tab |
| `/aeroplanes/{}/matching-chart?{}` | GET | `MatchingChartTab` |
| `/aeroplanes/{}/tail-sizing` | GET | `TailVolumeCard` |
| `/aeroplanes/{}/endurance` | GET | `EnduranceCard` |
| `/aeroplanes/{}/cg-envelope`, `/aeroplanes/{}/cg_comparison` | GET | mass & CG |
| `/aeroplanes/{}/loading-scenarios`, `…/templates?aircraft_class={}` | GET, PUT | loading scenarios |
| `/aeroplanes/{}/speed-polar` | GET | analysis |

### Powertrain, components, construction

| Path | Method(s) | Hook / caller |
|---|---|---|
| `/aeroplanes/{}/powertrain/sizing-modal-params`, `…/solution-space` | GET | `PowertrainTab` |
| `/components`, `/component-types` | GET, POST, PUT, DELETE | components tab |
| `/construction-plans`, `/construction-plans?plan_type={}` | GET, POST | plans tab |
| `/construction-plans/{}`, `…/artifacts`, `…/artifacts/{}{}` | GET | plan detail |
| `/construction-plans/creators` | GET | `CreatorGallery` |

### Airfoils

| Path | Method(s) | Hook / caller |
|---|---|---|
| `/airfoils/db/suitability?{}` | GET | `AirfoilSuitabilityCard` |

### Versioning (gh-907)

| Path | Method(s) | Hook |
|---|---|---|
| `/lineages/{}/tree` | GET | `useLineageTree` |
| `/aeroplanes/{}/snapshot` | POST | `useVersionActions` |
| `/aeroplanes/{}/branch` | POST | `useVersionActions` |
| `/aeroplanes/{}/restore` | POST | `useVersionActions` |
| `/branches/{}` | PATCH, DELETE | `useVersionActions` |
| `/branches/{}/adopt` | POST | `useVersionActions` |
| `/aeroplanes/compare?a={}&b={}` | GET | `VersionCompareView` |

🟡 These are the only routes the client addresses by **integer PK**; everything
else uses the aeroplane **UUID**.

### Copilot

| Path | Method | Consumer |
|---|---|---|
| `/aeroplanes/{}/copilot-history` | GET, POST, DELETE | `useCopilot` (SWR) |
| `/aeroplanes/{}/copilot-history/{}` | DELETE | `useCopilot` |
| `/aeroplanes/{}/copilot/stream` | **POST → SSE** | `useCopilot` via `parseSseStream` |

### OpenVSP import

| Path | Method | Consumer |
|---|---|---|
| `/api/v2/...` import | **POST → SSE** | `ImportOpenVspButton` + `ImportProgressBar` (gh-737) |

🟢 One route family of 230 carries a version prefix because of how its router was included — an ADR 0019 leak, corrected (`Q-CC-6`). Previously the only routes carrying `/api/v2`, while every other call is at the
root.

### Not consumed

`/mcp` (external agents only), `/health`, `/docs`, `/redoc`, `/openapi.json`.
The frontend never reads the OpenAPI document, which is why no client is
generated from it. 🔴

## SSE consumption contract 🟢

Two POST streams, both read through `parseSseStream`:

| Stream | Events | Handling |
|---|---|---|
| copilot | `token {text}`, `tool_call {name,args}`, `tool_result {name,summary}`, `done {status[,truncated]}`, `error {message}` | tokens append; `tool_call` shows `toolLabel(name)`; `done` revalidates the history key and surfaces `truncated`; `error` sets `errorMessage` |
| OpenVSP import (gh-737) | progress events | drives `ImportProgressBar`; warnings land in `AeroplaneContext.lastImportWarnings` |

Parser guarantees: records split on `\n\n`; the trailing fragment is buffered
across reads; multiple `data:` lines are joined with `\n`; a non-JSON payload
yields the raw string; a trailing record is flushed after the stream closes; the
reader lock is always released.

🟢 All six copilot tools get explicit labels (`Q-FW-9`); a `Record<CopilotTool, string>` makes an unlabelled tool a TypeScript error. Previously `TOOL_LABEL_MAP` mapped only `get_design_snapshot`, `run_analysis`
and `get_version_tree`. `get_wing_geometry`, `apply_design_edits` and
`discard_proposal` fall through to `Calling <name>…` — the two **write** tools
are the unlabelled ones.

## Type-mirroring contract 🟡 (client generation scheduled, `Q-CC-11`)

| Shared type file | Mirrors |
|---|---|
| `types/versioning.ts` | `app/schemas/versioning.py` — `TreeOut`, `VersionNode`, `BranchOut`, `BranchRequest`, `SnapshotRequest`, `CompareOut` |
| `types/versionGraph.ts` | layout-only types for `lib/versionGraphLayout.ts` |

Everything else is **redeclared inside the hook that fetches it**;
`hooks/useCopilot.ts` says so explicitly (*"mirror
app/schemas/copilot_history.py"*). Nothing is generated from `/openapi.json`.

Consequence: a backend schema change produces **no** build error until a
hand-written mirror or a test fixture disagrees — which is exactly why
`npx tsc --noEmit` is a separate CI gate (a new required field on a response
interface breaks existing fixture literals while vitest and eslint stay green).

## Client-side persistence contract 🟢

| Key / owner | Value |
|---|---|
| `da3dalus_aeroplane_id` (`AeroplaneContext`, `STORAGE_KEY`) | the selected aeroplane UUID — restores selection when `?aeroplane=` is absent |
| per-uuid dismiss flag (`WorkbenchImportWarningBanner`, `ImportWarningBanner`) | "don't show this import warning again" |
| `lib/versionGraphViewState.ts` | version-graph pan / zoom |
| `CopilotStrip` | collapsed/expanded state |
| `StabilityOverlay` | overlay toggles |

URL state: `?aeroplane=<uuid>` is the **source of truth**; `setAeroplaneId`
performs a router replace and mirrors to `localStorage`.

## Error-handling contract 🟡 (one typed client, `Q-FW-2`)

The backend emits **two** error shapes
([`../platform-core/contracts.md`](../platform-core/contracts.md)):
`{"error": {code, message, details}}` from the global handlers, and
`{"detail": …}` from per-module `_raise_http` helpers (versioning,
copilot-history). The client handles both through `lib/parseApiError.ts`,
which is the visible cost of that backend divergence.

There is **no** global error boundary, no `SWRConfig.onError`, no retry policy
and no client error reporting. Each panel renders its own error state.

## Assumptions the client makes about the backend 🟡

| Assumption | Where it breaks if violated |
|---|---|
| Wing config is **millimetres**; DB/ASB values are metres | `useWingConfig` and the wing editor |
| `WingOutlineViewer` receives **metres** and needs no conversion | the outline chart |
| `assumption_computation_context` is the single source of `cd0`, `e`, `L/D` and the neutral point (gh-924) | the metrics dashboard and analysis panels |
| Versioning routes take integer PKs while everything else takes UUIDs | `useVersioning` |
| A copilot proposal is discoverable as a lineage branch with `created_by === "copilot"` and `is_main === false` | `useCopilotProposal` (gh-939) |
| Adoption is a **human** action through `POST /branches/{id}/adopt` (ADR 0007) | the Versions panel |
| A `204` has no body | `lib/api.ts` only — `lib/fetcher.ts` would throw |

## Not part of this contract

- The endpoints' request/response schemas — owned by the backend modules'
  `contracts.md`.
- CORS policy, error envelopes and the transaction guarantee →
  [`../platform-core/contracts.md`](../platform-core/contracts.md).
- The copilot's tool surface → [`../ai-copilot/contracts.md`](../ai-copilot/contracts.md);
  the client only renders tool names.
- MCP → [`../mcp-server/contracts.md`](../mcp-server/contracts.md); the frontend
  never calls it.
