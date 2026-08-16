# frontend-workbench / workbench-shell-and-routing — Implementation Tasks

> Parent module task list: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] Node **22**; `next 16.2.1-canary.33`; React 19.
- [ ] `hooks/useAeroplanes` and `hooks/useLineageTree` (for `rootId`).
- [ ] Tailwind v4 tokens in `app/globals.css`.

## Tasks

- [ ] **T-01 — `app/layout.tsx` (server).**
  Load `Geist`, `Geist_Mono` and `JetBrains_Mono` via `next/font/google`; set
  metadata; apply the font CSS variables on `<html>`.
  - Legacy origin: `frontend/app/layout.tsx` (37 l.)
  - Definition of done: this stays the **only** meaningful server component; no
    data fetching happens here.
  - Confidence: 🟢

- [ ] **T-02 — `app/page.tsx`.**
  A five-line landing stub.
  - Legacy origin: `frontend/app/page.tsx`
  - Definition of done: it does not fetch, and it does not duplicate shell
    chrome.
  - Confidence: 🟢

- [ ] **T-03 — `AeroplaneContext`.**
  All ten fields and their setters; `STORAGE_KEY = "da3dalus_aeroplane_id"`; on
  mount read `?aeroplane` **then** `localStorage`, then set `hydrated = true`;
  `setAeroplaneId` does `router.replace` and mirrors to storage.
  - Legacy origin: `frontend/components/workbench/AeroplaneContext.tsx`
  - Definition of done: a shared link overrides a stored id; `replace` (not
    `push`) keeps selection out of the history stack; `hydrated` is false during
    the first client pass.
  - Confidence: 🟢

- [ ] **T-04 — `UnsavedChangesContext` + `UnsavedChangesModal`.**
  A dirty flag set by editing panels and a modal intercepting in-app
  navigation.
  - Legacy origin: `frontend/components/workbench/UnsavedChangesContext.tsx`
  - Definition of done: switching tabs with unsaved edits shows the modal.
    **Record** that a hard navigation (reload, address bar) is *not* guarded —
    there is no `beforeunload` handler.
  - Confidence: 🟢

- [ ] **T-05 — The shell layout.**
  `"use client"`; `Suspense` → `AeroplaneProvider` → `UnsavedChangesProvider` →
  `Header`, `WorkbenchImportWarningBanner`, `main`, `VersionGraphOverlay`
  (`key={rootId}`), `MetricsDashboardContainer`, `CopilotStrip`,
  `UnsavedChangesModal`, `AeroplanePickerHost`.
  - Legacy origin: `frontend/app/workbench/layout.tsx` (80 l.)
  - Definition of done: the `Suspense` wrapper is mandatory — `useSearchParams`
    fails the build without it. The overlay's `key={rootId}` must be present;
    without it a lineage change reuses stale graph layout.
  - Confidence: 🟢

- [ ] **T-06 — The seven tab pages.**
  `/workbench` (wing & fuselage editor), `/analysis`, `/components`,
  `/mission`, `/powertrain`, `/construction-plans`, `/airfoil-preview`.
  - Legacy origin: `frontend/app/workbench/*/page.tsx` (2 242 l. total)
  - Definition of done: pages stay thin — they select panels and pass context,
    nothing more.
  - Confidence: 🟢

- [ ] **T-07 — `Header` and `AeroplanePickerHost`.**
  The header takes `onOpenHistory`; the picker host renders from
  `pickerOpen` / `openPicker` / `closePicker`.
  - Legacy origin: `frontend/components/workbench/Header.tsx`,
    `AeroplanePickerHost.tsx`
  - Definition of done: `onOpenHistory` is threaded to both the header and the
    copilot strip — the one prop drilled through the shell.
  - Confidence: 🟢

- [ ] **T-08 — `WorkbenchImportWarningBanner`.**
  Render from `lastImportWarnings`; persist a **per-uuid dismissal flag** in
  `localStorage`.
  - Legacy origin: `frontend/components/workbench/WorkbenchImportWarningBanner.tsx`
  - Definition of done: the warnings are in-memory (gh-695) while the dismissal
    is persistent — a reload must not re-nag about a dismissed warning.
  - Confidence: 🟢

- [ ] **T-09 — Wire the docked components.**
  `MetricsDashboardContainer` (gh-881), `CopilotStrip`, `VersionGraphOverlay`.
  - Legacy origin: the shell layout
  - Definition of done: all three are reachable from every tab; the overlay is
    conditional on a `rootId` being available (a legacy pre-versioning aeroplane
    has none).
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Shell presence:** all seven routes render header, metrics dock,
      copilot strip and picker host.
- [ ] **TT-02 — URL write:** selection sets `?aeroplane` via `replace`; Back does
      not cycle selections.
- [ ] **TT-03 — Storage mirror:** the uuid is written to and read from
      `da3dalus_aeroplane_id`.
- [ ] **TT-04 — URL precedence:** a link overrides a stored id.
- [ ] **TT-05 — `hydrated`:** no "no aircraft selected" flash on first paint.
- [ ] **TT-06 — `treeMode`:** switching changes the tree between mm segments and
      metre cross-sections.
- [ ] **TT-07 — Picker:** `openPicker` / `closePicker` drive the host.
- [ ] **TT-08 — Import banner:** shown from `lastImportWarnings`; hidden after
      dismissal; still hidden after a reload.
- [ ] **TT-09 — Overlay remount:** changing `rootId` remounts the overlay.
- [ ] **TT-10 — Unsaved guard:** the modal appears on an in-app tab switch.
- [ ] **TT-11 — Hard navigation (characterisation):** a reload discards edits
      with no prompt.
- [ ] **TT-12 — E2E navigation:** the `navigation.feature` playwright-bdd suite
      passes on Node 22.

## Suggested Order

1. **T-01 → T-02** the server layout and the stub: cheap and unblocking.
2. **T-03** the context — every hook and panel depends on `aeroplaneId`. Write
   TT-04 and TT-05 with it; the URL-vs-storage precedence and the `hydrated`
   flag are exactly the two behaviours that regress silently.
3. **T-05** the shell, with `Suspense` from the start (the build fails
   otherwise).
4. **T-07 → T-09** the chrome and the docked components.
5. **T-04** the unsaved-changes guard once at least one editing panel exists to
   set the flag.
6. **T-06** the tab pages last — they are thin, and each pulls in its own panel
   tree.

## Pending Gaps

- **Should a stale or deleted aeroplane id be cleared** from the URL and
  `localStorage` instead of leaving every panel in an error state?
- **Should a `beforeunload` handler guard unsaved edits** on reload and
  address-bar navigation?
- **Should the shell have an error boundary?** Today an exception in the metrics
  band, the copilot strip or the version overlay unmounts the whole workbench.
- **Should the selected wing / station be deep-linkable**, not just the
  aircraft?
- **Should `treeMode` persist** across reloads?
- **Should `VersionGraphOverlay` (1 117 l.) be decomposed**, given it mounts on
  every tab?
- **Should `frontend/CLAUDE.md` be corrected** to state that all calls are direct
  browser fetches, so the wildcard CORS on the backend is understood as a
  consequence?
