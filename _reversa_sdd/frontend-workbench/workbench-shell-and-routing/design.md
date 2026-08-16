# frontend-workbench / workbench-shell-and-routing — Technical Design

> Use-case design. Parent module: [`../design.md`](../design.md).
> Consumption contract: [`../contracts.md`](../contracts.md).

## Interface

```ts
// components/workbench/AeroplaneContext.tsx
const STORAGE_KEY = "da3dalus_aeroplane_id";

interface AeroplaneContextValue {
  aeroplaneId: string | null;                  // UUID
  hydrated: boolean;                           // false during the first client pass
  selectedWing: string | null;                 // wing NAME
  selectedXsecIndex: number | null;
  selectedFuselage: string | null;
  selectedFuselageXsecIndex: number | null;
  treeMode: "wingconfig" | "asb" | "fuselage";
  pickerOpen: boolean;
  lastImportWarnings: { uuid: string; warnings: string[] } | null;   // gh-695, in memory
  setAeroplaneId(id: string | null): void;
  selectWing(name: string | null): void;
  selectXsec(i: number | null): void;
  selectFuselage(name: string | null): void;
  selectFuselageXsec(i: number | null): void;
  setTreeMode(m: TreeMode): void;
  openPicker(): void; closePicker(): void;
  setLastImportWarnings(w): void;
}
```

`UnsavedChangesContext` exposes a dirty flag plus a guarded-navigation helper
consumed by `UnsavedChangesModal`. 🟡

## Main Flow

### F1 — The route tree 🟢

```
app/
├ layout.tsx          SERVER: next/font/google (Geist, Geist_Mono, JetBrains_Mono),
│                             metadata, font CSS variables on <html>
├ page.tsx            5 lines
└ workbench/
  ├ layout.tsx        "use client" — THE SHELL
  ├ page.tsx                          wing & fuselage editor
  ├ analysis/page.tsx
  ├ components/page.tsx
  ├ mission/page.tsx
  ├ powertrain/page.tsx
  ├ construction-plans/page.tsx
  └ airfoil-preview/page.tsx
```

No `route.ts` anywhere, no `"use server"` anywhere. 🟢 (`Q-FW-1` — SPA-direct is the architecture)

### F2 — The shell 🟢

```tsx
export default function WorkbenchLayout({ children }) {
  return (
    <Suspense>                                   {/* useSearchParams requires it */}
      <AeroplaneProvider>
        <UnsavedChangesProvider>
          <Header onOpenHistory={...} />
          <WorkbenchImportWarningBanner />
          <main>{children}</main>
          {rootId !== null && <VersionGraphOverlay key={rootId} ... />}
          <MetricsDashboardContainer />          {/* gh-881 */}
          <CopilotStrip onOpenHistory={...} />
          <UnsavedChangesModal />
          <AeroplanePickerHost />
        </UnsavedChangesProvider>
      </AeroplaneProvider>
    </Suspense>
  );
}
```

`onOpenHistory` is threaded from the shell into both the header and the copilot
strip so either can open the conversation panel — the only prop drilled through
the shell. 🟡

### F3 — Selection 🟢

```ts
// mount
const fromUrl     = searchParams.get("aeroplane");
const fromStorage = localStorage.getItem(STORAGE_KEY);
setAeroplaneIdState(fromUrl ?? fromStorage ?? null);
setHydrated(true);

// write
function setAeroplaneId(id) {
  setAeroplaneIdState(id);
  const params = new URLSearchParams(searchParams);
  if (id) params.set("aeroplane", id); else params.delete("aeroplane");
  router.replace(`${pathname}?${params}`);        // REPLACE, not push
  if (id) localStorage.setItem(STORAGE_KEY, id);
  else    localStorage.removeItem(STORAGE_KEY);
}
```

The URL wins over `localStorage`, so a shared link always opens the intended
aircraft. `replace` keeps selection out of the history stack, so Back leaves the
workbench rather than cycling through aircraft. 🟢

`hydrated` exists because the first client render happens **before**
`localStorage` is read; without it every page would flash its "no aircraft
selected" state. 🟢

### F4 — Selection sub-state 🟢

`selectedWing` is a **name**, not an index or id — the same identifier the
backend and the copilot use (`wing_names`, gh-938). `selectedXsecIndex` is a
station index whose meaning depends on `treeMode`:

| `treeMode` | The tree shows | Index means |
|---|---|---|
| `"wingconfig"` | mm **segments** | segment index |
| `"asb"` | metre **cross-sections** | station index |
| `"fuselage"` | fuselage stations | fuselage xsec index |

This is the frontend face of the mm/metre duality (ADR 0001). 🟢

### F5 — Import warnings 🟢

```
OpenVSP import (SSE) finishes
   -> setLastImportWarnings({ uuid, warnings })      # in memory only (gh-695)
   -> WorkbenchImportWarningBanner renders unless localStorage holds a
      per-uuid dismissal flag
```

The *warnings* are ephemeral; the *dismissal* is persistent — the asymmetry is
deliberate: a reload should not re-nag about a warning the user already
dismissed, but the warning list itself is not worth persisting. 🟡

### F6 — Unsaved changes 🟡

`UnsavedChangesProvider` holds a dirty flag; panels set it while editing;
`UnsavedChangesModal` intercepts in-app navigation attempts. There is **no**
`beforeunload` handler, so a reload or an address-bar navigation silently
discards the edits. 🔴

## Alternative Flows

- **No `?aeroplane` and no stored id:** `aeroplaneId` is `null`; every hook is
  disabled; pages render their empty state once `hydrated` is true. 🟢
- **A stored id that no longer exists:** the aeroplane hooks 404 and each panel
  renders its own error; nothing clears the stale id. 🔴
- **A shared link to a deleted aircraft:** 🟢 the stale id is cleared from the URL and `localStorage` (`Q-FW-7`).
- **Lineage change while the overlay is open:** `key={rootId}` remounts it. 🟡
- **A tab switch with unsaved edits:** the modal appears. 🟢
- **A reload with unsaved edits:** 🟢 a `beforeunload` guard is added (`Q-FW-7`, maintainer-answered).
- **`useSearchParams` outside `Suspense`:** Next.js errors at build — the
  `Suspense` wrapper in the shell is what prevents it. 🟢

## Dependencies

- `next/navigation` (`useRouter`, `usePathname`, `useSearchParams`).
- `next/font/google` for the three fonts.
- `hooks/useAeroplanes`, `useLineageTree` (for `rootId`) and the version hooks
  consumed by the overlay.
- `lib/versionGraphViewState.ts` for persisted pan/zoom.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| One shell for all seven tabs, so the copilot and metrics are always docked | `app/workbench/layout.tsx` | 🟢 |
| The URL is the source of truth; `localStorage` is only a fallback mirror | `AeroplaneContext` | 🟢 |
| `replace` rather than `push`, so selection does not pollute history | `setAeroplaneId` | 🟢 |
| A `hydrated` flag instead of a loading skeleton | `AeroplaneContext` | 🟢 |
| Wings addressed by **name**, matching the backend and the copilot | `selectedWing: string` | 🟢 |
| `treeMode` as an explicit unit-context switch | `AeroplaneContext` | 🟢 |
| Import warnings ephemeral, dismissals persistent | gh-695 + the banner's `localStorage` flag | 🟡 |
| Remount the version overlay per lineage rather than resetting its state | `key={rootId}` | 🟡 |
| Guard unsaved changes with a context + modal, not a router/browser hook | `UnsavedChangesContext` | 🟡 |
| Only fonts and metadata run on the server | `app/layout.tsx` | 🟢 |

## Internal State

| State | Where | Lifecycle |
|---|---|---|
| `aeroplaneId` | context + URL + `localStorage` | per tab; URL wins on mount |
| `hydrated` | context | `false` → `true` once, after mount |
| `selectedWing` / xsec / fuselage indices | context | per tab; reset when the aircraft changes 🟡 |
| `treeMode` | context | per tab; not persisted |
| `pickerOpen` | context | transient |
| `lastImportWarnings` | context | in memory only (gh-695) |
| banner dismissals, strip collapse, overlay toggles, graph pan/zoom | `localStorage` | persistent |
| unsaved-changes flag | context | per editing session |

## Observability

- 🟡 Browser console only.
- 🔴 No error boundary around the shell: an exception in any docked component
  (metrics band, copilot strip, version overlay) unmounts the whole workbench.
- 🔴 No telemetry on tab usage, selection changes or picker opens.

## Risks and Gaps

- 🔴 **`frontend/CLAUDE.md` is stale**: it documents server-side route handlers
  and server actions that do not exist, which is why the backend needs wildcard
  CORS.
- 🔴 **A stale or deleted aeroplane id is never cleared** from `localStorage` or
  the URL; every panel just errors.
- 🔴 **No `beforeunload` guard** — a reload discards unsaved edits silently.
- 🔴 **No error boundary** around the shell or its docked components.
- 🔴 **`VersionGraphOverlay` is 1 117 lines**, mounted on every tab.
- 🟡 **Selection sub-state is not deep-linkable** — only the aircraft is in the
  URL, not the selected wing or station.
- 🟡 **`onOpenHistory` is prop-drilled** through the shell to two consumers.
- 🟡 **`treeMode` is not persisted**, so the unit view resets on every reload.
