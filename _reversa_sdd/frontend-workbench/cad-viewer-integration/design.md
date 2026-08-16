# frontend-workbench / cad-viewer-integration — Technical Design

> Use-case design. Parent module: [`../design.md`](../design.md).

## Interface

```ts
// components/workbench/CadViewer.tsx
import "three-cad-viewer/css";                       // line 6 — STATIC
export function CadViewer(props: { shapes; states; ... }): JSX.Element

// hooks/useTessellation.ts
export function useTessellation(aeroplaneId: string | null, wingName: string | null)
export function invalidateTessellationCache(aeroplaneId: string, wingName: string): void
// module-level:  Map<`${aeroplaneId}/${wingName}`, { data, updatedAt }>
```

```ts
// next.config.ts
webpack:  config.resolve.alias.three = path.resolve("node_modules/three")
turbopack: { resolveAlias: { three: "node_modules/three" } }
```

## Main Flow

### F1 — Mount 🟢

```ts
import "three-cad-viewer/css";                 // l.6 — evaluated at module load

useEffect(() => {
  let disposed = false;
  (async () => {
    const tcv = await import("three-cad-viewer");     // l.90 — runtime only
    if (disposed) return;
    viewerRef.current = new tcv.Viewer(containerRef.current, options, notifyCallback);
    viewerRef.current.render(shapes, states);
  })();
  return () => { disposed = true; viewerRef.current?.dispose?.(); };
}, [deps]);
```

The asymmetry is the point:

| Part | Import style | Why |
|---|---|---|
| CSS | **static** | the stylesheet must exist before the first paint, or the viewer renders unstyled |
| library | **dynamic** | keeps three.js + the viewer out of the initial bundle |

Project memory records that this pattern must **never** be changed without real
browser testing — the failure mode (unstyled viewer, or a second three.js
instance) does not reproduce in jsdom. 🟢 🔴

### F2 — One three.js 🟢

```
app code        import * as THREE from "three"
three-cad-viewer import * as THREE from "three"
                 ↓ both must resolve to the SAME node_modules/three
next.config.ts: alias in the webpack resolver AND the turbopack resolver
```

Two instances produce silent failures — `instanceof` checks fail across
realms, materials and geometries from one instance are unusable by the other.
Because dev uses turbopack and production may use webpack, **both** aliases are
required; configuring only one makes the bug environment-specific. 🔴

### F3 — The tessellation cache 🟢

```ts
type Entry = { data: TessellationResult; updatedAt: string };
const cache = new Map<string, Entry>();              // MODULE level — survives remounts

function key(aeroplaneId: string, wingName: string) {
  return `${aeroplaneId}/${wingName}`;
}

export function useTessellation(aeroplaneId, wingName) {
  // aeroplane.updated_at comes from the aeroplane hook
  const cached = cache.get(key(aeroplaneId, wingName));
  if (cached && cached.updatedAt === aeroplane.updated_at) return cached.data;   // HIT
  // ... fetch, then cache.set(key, { data, updatedAt: aeroplane.updated_at })
}

export function invalidateTessellationCache(aeroplaneId, wingName) {
  cache.delete(key(aeroplaneId, wingName));
}
```

The `updated_at` comparison is what makes the cache safe: any backend mutation
bumps the aeroplane's timestamp, so a stale mesh can never be shown. The
explicit `invalidateTessellationCache` export exists for the case where the UI
knows it changed geometry and wants the **"Preview 3D"** affordance back
immediately, without waiting for a revalidation round trip. 🟢

🟡 The cache lives at module scope, so it survives component remounts and route
changes but not a reload. It has **no** eviction, size cap or age limit.

### F4 — Data flow 🟢

```
wing editor  ──save──▶  PUT /aeroplanes/{uuid}/wings/{name}/wingconfig     (mm)
                        └─ backend bumps aeroplanes.updated_at
                        └─ invalidateTessellationCache(uuid, name)
"Preview 3D" ─────────▶  useTessellation(uuid, name)
                        └─ cache miss ⇒ fetch tessellation (backend, commits its own session)
                        └─ CadViewer renders shapes + states
```

## Alternative Flows

- **Nothing selected:** the hook is disabled; the panel shows an empty state. 🟢
- **Cache hit:** no request; the viewer renders immediately. 🟢
- **`updated_at` changed:** refetch, then replace the entry. 🟢
- **Tessellation fails:** the panel shows an error; the previous mesh is **not**
  reused, so the user never sees geometry that no longer exists. 🟡
- **Rapid wing switching:** each key is cached independently, so switching back
  is instant. 🟢
- **Component unmounts mid-import:** the `disposed` flag prevents constructing a
  viewer into a detached container. 🟡
- **Alias configured in only one resolver:** two three.js instances; the viewer
  breaks in that environment only. 🔴
- **Many previews in one session:** the cache grows without bound. 🟡
- **Repeated navigation without disposal:** WebGL contexts leak until the
  browser refuses new ones. 🟡

## Dependencies

- `three` and `three-cad-viewer` (one shared instance).
- `hooks/useAeroplanes` for `updated_at`.
- The backend tessellation endpoint (`cad-generation`), whose service commits
  its own session — one of the four legitimate exceptions to ADR 0009.
- `next.config.ts` for both resolver aliases.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Static CSS + dynamic library import | `CadViewer.tsx:6,90` | 🟢 (documented as fragile) |
| Alias `three` in both webpack and turbopack | `next.config.ts` | 🟢 |
| A module-level cache rather than SWR for tessellations | `useTessellation` | 🟢 |
| Validate the cache with the aeroplane's `updated_at` | `useTessellation` | 🟢 |
| Export an explicit invalidation function for save paths | `invalidateTessellationCache` | 🟢 |
| Tessellate on the backend, never in the browser | the endpoint contract | 🟢 |
| No eviction policy | — | 🟡 no rationale found |

## Internal State

| State | Where | Lifecycle |
|---|---|---|
| the tessellation `Map` | module scope in `useTessellation` | per tab; survives remounts; **unbounded** 🟡 |
| the `Viewer` instance | a component ref | per mount; disposed in the effect cleanup |
| the `disposed` flag | closure per effect | guards the async import race |

## Observability

- 🟡 Errors surface in the panel; the project's log-hygiene rule keeps
  tessellation error messages **type-only** (no payload echoed).
- 🔴 No metric for cache hit rate, tessellation duration or cache size — so the
  unbounded growth and the value of the cache are both unmeasurable.
- 🔴 Nothing detects a duplicated three.js instance at runtime; the symptom is a
  render failure with no diagnostic.

## Risks and Gaps

- 🔴 **The import pattern is fragile and unverifiable in unit tests.** jsdom
  cannot render WebGL, so only Playwright can prove the viewer works — which is
  why project memory demands real browser testing before touching it.
- 🔴 **A single-resolver `three` alias breaks the viewer** in exactly one
  environment (dev or prod), making the failure look intermittent.
- 🟡 **The cache is unbounded and per tab**; only an `updated_at` mismatch
  evicts.
- 🟡 **WebGL context leaks** if disposal is missed on any path.
- 🟡 **An in-flight import racing an unmount** is guarded by a local flag rather
  than an `AbortController`.
- 🔴 **No cache or viewer instrumentation.**
