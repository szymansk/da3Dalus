# Version Compare — Geometry Parameter Diff ("what changed")

**Date:** 2026-06-13
**Status:** Design / approved (brainstorm)
**Issue:** #971 (promotes the gh-963 "stretch")
**Area:** Frontend — `frontend/components/workbench/VersionCompareView.tsx` (+ new util/hook/component)

---

## Problem

The version-compare view shows metric **outcomes** (L/D, V_stall, AR, e …) and now
discloses the analysis context (gh-963/#968), but it does not show WHICH design
**inputs** changed between the two versions. A reviewer sees that L/D dropped but
not that the tip chord shrank and a section was added. The persona UAT (hobbyist
+ pro) asked for a "what changed" parameter diff.

## Goals

- An expandable **"Geometry changes"** section in the compare view listing the
  wing-geometry parameters that differ between the two compared versions.
- Reuse the existing per-version full-geometry endpoint; **no backend change**.
- Keep the compare endpoint lightweight (lazy-load only when the section opens).

## Non-goals (YAGNI)

- Field-level diff of sub-elements (spar dimensions, control-surface hinge/servo,
  turbulator fields) — shown only as changed/added/removed **flags** in v1.
- Fuselage / mass / component diff (a later scope).
- Editing or 3D visualisation of the diff.
- Backend payload changes to `/aeroplanes/compare`.

## Scope (v1)

Per wing, per section (segment, root→tip order), diff these **core params**:
`chord`, `twist` (incidence), `dihedral`, `length`, `sweep`, `airfoil`. Plus:
- **Section** added / removed / changed (align by index).
- **Wing** added / removed / changed (align by `name`).
- **Sub-elements** as presence/count flags: spar (`1 → 2 spars`), control surface
  / trailing-edge device (`aileron → —`, `— → flap`, or `changed`), turbulator
  (`on → off` / `changed`). No field-level detail.

Units follow WingConfig (mm, degrees). Numeric tolerance to avoid float noise:
`|Δ| > 0.05` (mm and degrees).

---

## Architecture (frontend-only)

```
VersionCompareView
  └─ GeometryDiffSection (collapsed by default)
        on expand → useGeometryDiff(nodeAUuid, nodeBUuid, wingNames)
              └─ SWR fetch per wing per node:
                 GET /aeroplanes/{uuid}/wings/{wing}/wingconfig   (existing, mm)
              └─ computeGeometryDiff(wingsA, wingsB)  ← pure, testable
        renders the A | param | B table (changes-only | show-all)
```

- **`frontend/lib/geometryDiff.ts`** — pure `computeGeometryDiff(wingsA, wingsB)`
  + types. No React, no network. Aligns wings by name and sections by index;
  emits a `GeometryDiff` (see below). Holds all diff logic + the tolerance.
- **`frontend/hooks/useGeometryDiff.ts`** — lazy: only fetches when `enabled`
  (section expanded). Fetches each wing's `WingConfig` for both node UUIDs via
  SWR, memoises `computeGeometryDiff`. Returns `{ diff, isLoading, error }`.
- **`frontend/components/workbench/GeometryDiffSection.tsx`** — the collapsible
  section: header with change counts, the toggle, and the table. Reuses the
  metric-compare 3-column grid styling (`A | param | B`, amber on change). Owns
  the `expanded` and `showAll` state.
- **Edit `VersionCompareView.tsx`** — render `<GeometryDiffSection nodeA={…}
  nodeB={…} wingNamesA={…} wingNamesB={…} />` below the metric sections. Node
  UUIDs come from `compareOut.node_a/_b.uuid`; wing names from each side's
  `metrics.wing_names` (fallback: union).

## Diff data model (`geometryDiff.ts`)

```ts
type ChangeKind = "changed" | "added" | "removed";
interface ParamChange { key: string; a: string | null; b: string | null; }   // "chord", "162 mm" → "158 mm"
interface SubElementFlag { key: string; kind: ChangeKind; a: string | null; b: string | null; } // spar/ctrl/turbulator
interface SectionDiff {
  index: number;
  kind: ChangeKind;                 // section added/removed/changed
  label: string;                    // "Section 3 · mid"
  params: ParamChange[];            // only changed core params (changes-only); all (show-all)
  flags: SubElementFlag[];
}
interface WingDiff { name: string; kind: ChangeKind; sections: SectionDiff[]; }
interface GeometryDiff {
  wings: WingDiff[];                // only changed wings in changes-only; all in show-all
  counts: { sectionsChanged: number; sectionsAdded: number; sectionsRemoved: number };
  hasAnyChange: boolean;
}
computeGeometryDiff(wingsA, wingsB, opts?: { showAll?: boolean }): GeometryDiff
```

- Section alignment by index; the shorter side's missing indices → `added`
  (present in B) / `removed` (present in A).
- A param is "changed" when both present and differ beyond tolerance; airfoil by
  string equality. In **show-all**, every core param is emitted (changed flagged);
  in **changes-only**, only changed params/sections/wings are kept.
- Sub-element flags: compare counts/presence per section (spar count, TED
  name/presence, turbulator enabled/presence).

## UI

- Collapsible row **"▸ Geometry changes — N changed · M added · K removed"** under
  the metric sections; collapsed by default. Expanding triggers the lazy fetch
  (spinner while loading; inline error block on failure — does not crash compare).
- Body: 3-column grid (`A | param | B`) matching `MetricRow`. **Wing subheader**
  rows, then **section subheader** rows, then one row per param/flag; changed
  cells amber, added/removed shown with `—` on the empty side + a small badge.
- **Toggle "Changes only / Show all"** (default changes-only). Show-all renders
  every section and every core param for both sides (changes highlighted).
- "No geometry changes." when `hasAnyChange` is false.

## Data flow & errors

`compareOut` already has `node_a/_b` (with `uuid`) and `metrics.wing_names`.
On expand, `useGeometryDiff` fetches `GET /aeroplanes/{uuid}/wings/{wing}/wingconfig`
for each wing of each node. A per-wing fetch failure → inline error in the
section only. A wing present on one node only → wing added/removed (no fetch
needed for the missing side).

## Testing

- **Unit (vitest)** `geometryDiff.test.ts`: each core-param change
  (chord/twist/dihedral/length/sweep/airfoil); section add/remove; wing
  add/remove; sub-element flags (spar count, TED presence, turbulator); identical
  → `hasAnyChange=false`; tolerance (Δ=0.04 mm → no change, 0.06 → change);
  changes-only vs show-all filtering.
- **Component (vitest)** `GeometryDiffSection.test.tsx`: collapsed→expand lazy
  fetch; loading / error / empty ("no changes") states; changes-only vs show-all
  toggle; added/removed badges render.

## Files

| File | Change |
|---|---|
| `frontend/lib/geometryDiff.ts` | new — pure diff util + types |
| `frontend/hooks/useGeometryDiff.ts` | new — lazy SWR fetch + memoised diff |
| `frontend/components/workbench/GeometryDiffSection.tsx` | new — section + table + toggle |
| `frontend/components/workbench/VersionCompareView.tsx` | edit — mount the section |
| `frontend/__tests__/geometryDiff.test.ts`, `GeometryDiffSection.test.tsx` | new tests |

No backend changes.
