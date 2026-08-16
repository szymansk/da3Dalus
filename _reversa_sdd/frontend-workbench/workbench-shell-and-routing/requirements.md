# frontend-workbench / workbench-shell-and-routing

> Use-case specification. Parent module: [`../requirements.md`](../requirements.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.

## Overview

One client-side shell wraps all seven tabs and owns everything that must be
present regardless of which tab is active: the aircraft selection, the header,
the docked metrics band, the docked copilot strip, the version overlay, the
unsaved-changes guard and the aeroplane picker. 🟢

Routing is App Router **structure without App Router behaviour**: there is one
meaningful server component (the root layout, for fonts and metadata) and
everything below it is `"use client"`. 🟢

## Responsibilities

- Own `AeroplaneContext` — selection, `treeMode`, picker state, import warnings
  and `hydrated`. 🟢
- Keep the selected aircraft in the URL and mirror it to `localStorage`. 🟢
- Mount the shell chrome on every tab. 🟢
- Own `UnsavedChangesContext` and its modal. 🟢
- Load the three fonts and the page metadata (the one server-side concern). 🟢

## Business Rules

- **BR-FE1 — Only `app/layout.tsx` is a meaningful server component.** 🟢 It
  loads `Geist`, `Geist_Mono` and `JetBrains_Mono` through `next/font/google`,
  sets the metadata and applies the font CSS variables. `app/page.tsx` is five
  lines; everything under `/workbench` is `"use client"`.
- **BR-FE2 — No route handlers, no server actions, no server-side fetch.** 🟢
  Verified: `app/**/route.ts` does not exist and nothing declares `"use
  server"`. 🔴 `frontend/CLAUDE.md:12-13` claims otherwise.
- **BR-FE3 — The shell mounts identically on every tab.** 🟢
  ```
  Suspense
  └ AeroplaneProvider
    └ UnsavedChangesProvider
      ├ Header(onOpenHistory)
      ├ WorkbenchImportWarningBanner
      ├ main → {children}
      ├ VersionGraphOverlay          (conditional, key={rootId})
      ├ MetricsDashboardContainer    (gh-881)
      ├ CopilotStrip(onOpenHistory)
      ├ UnsavedChangesModal
      └ AeroplanePickerHost
  ```
- **BR-FE25 — `?aeroplane=<uuid>` is the source of truth.** 🟢
  `setAeroplaneId` performs a router **replace** (not push, so selection does not
  pollute history) and mirrors to `localStorage` under
  `da3dalus_aeroplane_id`.
- **BR-FE13 — `hydrated` gates the empty state.** 🟢 It is `false` during the
  first client pass so a page never flashes "no aircraft selected" before
  `localStorage` has been read.
- **BR-FE14 — `treeMode` encodes the unit duality.** 🟢
  `"wingconfig"` = mm segments, `"asb"` = metre cross-sections,
  `"fuselage"` = the fuselage tree.
- **BR-FE26 — `lastImportWarnings` is in-memory only.** 🟢 (gh-695) Shape
  `{uuid, warnings[]} | null`; a reload loses it, while the *dismissal* flag for
  the banner is persisted per uuid in `localStorage`.
- **BR-FE27 — `VersionGraphOverlay` is keyed by `rootId`.** 🟢 Changing the
  lineage forces a full remount, discarding stale graph layout state. 🟡
- **BR-FE28 — Unsaved changes are guarded by a context + modal**, not by a
  router event. 🟡 A hard navigation (URL bar, reload) bypasses it.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Render the shell chrome on all seven routes | Must | Header, metrics dock, copilot strip, picker host present |
| RF-02 | Provide `AeroplaneContext` to every descendant | Must | A panel can read `aeroplaneId` without prop drilling |
| RF-03 | Write the selection to the URL with `replace` | Must | Back does not step through selections |
| RF-04 | Mirror the selection to `localStorage` | Must | A new tab restores it |
| RF-05 | Prefer the URL over `localStorage` on mount | Must | A shared link wins over the stored value |
| RF-06 | Expose `hydrated` | Must | No empty-state flash |
| RF-07 | Track wing / xsec / fuselage / fuselage-xsec selection | Must | Deep-linkable within a tab 🟡 |
| RF-08 | Track `treeMode` | Must | The tree switches between mm and metre views |
| RF-09 | Own picker open/close state | Must | `AeroplanePickerHost` renders from it |
| RF-10 | Carry `lastImportWarnings` in memory | Should | Banner appears after an import |
| RF-11 | Remount the version overlay on lineage change | Should | `key={rootId}` |
| RF-12 | Warn before losing unsaved edits | Should | The modal blocks in-app navigation |
| RF-13 | Load the three fonts and metadata server-side | Should | No layout shift on first paint |
| RF-14 | Wrap the shell in `Suspense` | Should | `useSearchParams` requires it |

## Non-functional Requirements

| Type | Inferred requirement | Evidence | Confidence |
|------|----------------------|----------|-----------|
| UX | The selected aircraft survives a reload and is shareable as a link | URL + `localStorage` | 🟢 |
| UX | No first-render flash of an empty state | `hydrated` | 🟢 |
| Performance | Fonts are self-hosted through `next/font` | `app/layout.tsx` | 🟢 |
| Consistency | Every tab shows the same chrome, so the copilot and metrics are always reachable | the shell layout | 🟢 |
| Correctness | A lineage change must not reuse stale graph layout | `key={rootId}` | 🟡 |
| Robustness | 🟡 A hard navigation bypasses the unsaved-changes guard | context-based guard only | 🟡 |
| Security | 🟡 No auth in the client; the selection is not scoped to a user (there are none) | ADR 0016 | 🟡 |

## Acceptance Criteria

```gherkin
Feature: The shell

  Scenario: Present on every tab
    When I visit /workbench, /workbench/analysis, /workbench/components,
      /workbench/mission, /workbench/powertrain, /workbench/construction-plans
      and /workbench/airfoil-preview
    Then each renders the header, the metrics dock and the copilot strip

  Scenario: Context without prop drilling
    Given a deeply nested panel
    Then it can read aeroplaneId from AeroplaneContext

Feature: Selection

  Scenario: The URL is written with replace
    When I select an aircraft
    Then the URL contains ?aeroplane=<uuid>
    And pressing Back does not step through previous selections

  Scenario: localStorage mirrors
    Then da3dalus_aeroplane_id holds the same uuid

  Scenario: A shared link wins
    Given localStorage holds aircraft A
    When I open a link containing ?aeroplane=B
    Then aircraft B is selected

  Scenario: A fresh tab restores
    Given localStorage holds aircraft A and the URL has no query
    Then aircraft A is selected

  Scenario: No empty-state flash
    Given hydrated is false on the first client pass
    Then the page does not render "no aircraft selected"

Feature: Tree mode

  Scenario: Switching units
    When treeMode is "wingconfig"
    Then the tree shows mm segments
    When treeMode is "asb"
    Then the tree shows metre cross-sections

Feature: Overlay and guards

  Scenario: The version overlay remounts per lineage
    Given the overlay is open with a pan/zoom state
    When the selected aircraft belongs to a different lineage
    Then the overlay remounts with fresh layout state

  Scenario: Unsaved changes block in-app navigation
    Given a panel has unsaved edits
    When I switch tabs
    Then the unsaved-changes modal appears

  Scenario: A hard navigation is not guarded
    Given unsaved edits
    When I reload the page
    Then no modal appears and the edits are lost
```

> The last scenario is a **characterisation** of a 🔴 gap.

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|---|---|---|
| Shell chrome on every tab (RF-01) | Must | The copilot and metrics must always be reachable |
| Context selection (RF-02, RF-07…RF-09) | Must | Every hook keys off `aeroplaneId` |
| URL as the source of truth + mirror (RF-03…RF-05) | Must | Shareable links and reload survival |
| `hydrated` (RF-06) | Must | Otherwise every page flashes an empty state |
| `Suspense` wrapper (RF-14) | Must | `useSearchParams` requires it in the App Router |
| Version-overlay remount (RF-11) | Should | Prevents stale layout |
| Unsaved-changes modal (RF-12) | Should | 🟡 in-app only |
| In-memory import warnings (RF-10) | Should | Lost on reload by design (gh-695) |
| Server-side fonts and metadata (RF-13) | Should | The only server-side work |
| Server-side data fetching / route handlers | Won't | 🟡 documented but absent — the cause of the backend's wildcard CORS |
| Per-user scoping of the selection | Won't | No users exist (ADR 0016) |
| `beforeunload` guarding | Won't (today) | 🟡 a hard navigation loses edits |

## Code Traceability

| File | Role | Coverage |
|---|---|---|
| `frontend/app/layout.tsx` (37 l.) | fonts, metadata, font CSS variables — the only server component | 🟢 |
| `frontend/app/page.tsx` (5 l.) | landing stub | 🟢 |
| `frontend/app/workbench/layout.tsx` (80 l., `"use client"`) | the shell | 🟢 |
| `frontend/app/workbench/*/page.tsx` (2 242 l.) | the seven tab pages | 🟢 |
| `frontend/components/workbench/AeroplaneContext.tsx` | selection context + `STORAGE_KEY` | 🟢 |
| `frontend/components/workbench/UnsavedChangesContext.tsx` + `UnsavedChangesModal` | the edit guard | 🟢 |
| `frontend/components/workbench/Header.tsx`, `AeroplanePickerHost.tsx`, `WorkbenchImportWarningBanner.tsx` | shell chrome | 🟢 |
| `frontend/components/workbench/VersionGraphOverlay.tsx` (1 117 l.) | keyed by `rootId` | 🟢 🟡 (size) |
| `frontend/components/workbench/metrics-dashboard/` (7 files, gh-881) | the docked band | 🟢 |
| `frontend/components/workbench/CopilotStrip.tsx` (467 l.) | the docked strip | 🟢 |
