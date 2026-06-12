# Version History — GitKraken-style Graph Redesign

**Date:** 2026-06-12
**Status:** Design / awaiting approval
**Area:** Frontend — `frontend/components/workbench/VersionHistoryPanel.tsx`, `VersionCompareView.tsx`
**Relates to:** epic #901 (DB aircraft versioning/branching), #902 (AI copilot)

Mockups: `assets/graph-compact.png`, `assets/compare-header.png`

---

## Problem

The current History & Variants panel renders the version lineage as a **flat
list grouped per branch** in a 360px right sidebar. There is no visual graph,
so the relationship between branches (which node forked from which) is not
legible. Two further pain points:

1. **Actions are scattered per-row** — each node carries its own
   Compare / Branch / Restore buttons; each branch its own Adopt / Discard.
   This clutters every row and makes the common case (act on one node) noisy.
2. **Compare cannot disambiguate same-named variants** — `VersionCompareView`
   labels each side only by `version_label ?? name`. Two snapshots both called
   "v1.0" are indistinguishable.

## Goals

- A **GitKraken-style commit graph**: colored branch rails, dots, fork curves,
  branch-name pills at tips — applied to the version lineage.
- **Toolbar acts on the selected node** (single selection), not per-row buttons.
- **Compare is the exception**: a checkbox column, exactly two selectable.
- **Compare view identifies each aircraft unambiguously** even with equal names.
- Render inside a **large closable overlay/modal** over the workbench.

## Non-goals (YAGNI)

- Merging / three-way merge / conflict resolution (no backend support).
- Geometry or parameter-level diff (compare stays metrics-only, as today).
- Real snapshot thumbnails (the tree endpoint omits `preview_png` for bandwidth;
  keep the placeholder).
- Drag-and-drop reordering, multi-select for anything but compare.
- Backend / data-model changes — the existing endpoints are sufficient.

---

## Container

A **large centered overlay/modal** (~80% viewport width, capped e.g. `max-w-[1100px]`,
~80vh tall), opened by the existing History toggle in `Header.tsx`, dismissable
via close button / backdrop click / Escape. Follows the existing modal pattern
(`fixed inset-0 z-50` backdrop + card) noted in `frontend/CLAUDE.md`. The 360px
sidebar is retired in favour of this overlay.

## Layout

```
┌─────────────────────────────────────────────── overlay ──┐
│  ⎇ Version graph — <aircraft name>                    [×] │
├───────────────────────────────────────────────────────────┤
│  [Snapshot] [Branch from] [Restore] [Adopt] [Discard]     │  ← toolbar (acts on selection)
│                                       [☑ Compare (n)]      │
├──┬──────────────┬─────────────────────────────────────────┤
│☑ │   graph      │ version                                   │  ← rows
│  │  ◯──┐ ★main   │ 👤 working head        [HEAD]             │
│  │  │  ●         │    you · today 14:02 · editable           │
│  │  │  ◯ ⎇ai/... │ ✦ winglet draft +6% L/D [HEAD]           │
│  …                                                           │
└──┴──────────────┴─────────────────────────────────────────┘
```

### Row model
- **Order:** strictly chronological by `created_at`, **newest at top**
  (flat across all branches, GitKraken-style — not grouped per branch).
- **Columns:** `[compare checkbox] [graph cell] [version cell]`. Row height ~38px.
- **Version cell** folds author + time + note into a small second line under the
  label — no separate author/date columns. Two lines:
  - line 1: `<avatar> <label> <tag>` (tag = `snapshot` or `HEAD`)
  - line 2: `<author> · <relative date+time> · <note|state>`
- **Avatars:** two simple kinds only — user (neutral person glyph) vs agent
  (violet bot/spark glyph), driven by `created_by` (`human` | `ai`).
- **Selected row:** orange left-rail + tint (reuse current `isCurrentHead` style).

### Graph cell (the rails)
- One **lane per branch**, colored: `main` → primary orange `#FF8400`;
  `ai/*` branches → violet `#a78bfa`; other human branches → a rotating palette
  (e.g. teal `#2dd4bf`, blue, amber…), assigned deterministically.
- **Node dot:** filled = immutable snapshot (`is_immutable`); hollow ring =
  editable head (`is_head && !is_immutable`). Active main tip keeps the ring.
- **Rails** are continuous vertical segments drawn per-row so they line up across
  row boundaries (each row's SVG draws its lane segments to overlap top/bottom).
- **Fork curve:** a child branch's first node connects back to its parent node
  (via `predecessor_id`) with a bézier from the parent's lane to the child lane.
- **Branch pill** rendered at a branch **tip** node: `★ main` / `⎇ <branch name>`,
  colored to match the lane.

### Lane assignment (client-side, pure function)
A new util `computeGraphLayout(tree: TreeOut)` returns, for each node:
`{ nodeId, lane, color, dotStyle, isBranchTip, branchPill, edges }` plus the set
of rail segments per row. Algorithm:
1. Sort nodes by `created_at` desc → row index.
2. Assign each branch a lane index; `main` lane = 0. Reuse freed lanes once a
   branch's range ends (compact lanes, like git log --graph).
3. For each node, derive its parent via `predecessor_id`; if parent is on another
   lane, emit a fork edge (parent row → this node's lane).
4. Pure + deterministic → unit-testable without a browser.

This util holds all graph geometry logic; the React components stay thin
(render the precomputed lanes/edges/dots).

## Toolbar (acts on the single selected node)

| Action | Enabled when | Maps to existing |
|---|---|---|
| Snapshot | selected node is the editable head of its branch | `actions.snapshot` |
| Branch from | any node selected | `actions.createBranch(nodeId)` |
| Restore | selected node `is_immutable` (snapshot) | `actions.restore(snapshotId)` |
| Adopt | selected node's branch not `is_main` | `actions.adoptBranch(branchId)` |
| Discard | selected node's branch not `is_main` | `actions.discardBranch(branchId)` (guarded confirm) |

Disabled actions are visibly greyed, with a tooltip explaining why. Branch/Restore
still prompt for a name (reuse the existing inline `BranchNameInput`, now anchored
in the toolbar instead of per-row). Discard keeps its two-step confirm.

## Compare (the exception)

- A **checkbox** per row; at most **two** may be checked (selecting a third is a
  no-op, as today). A `Compare (n)` button in the toolbar opens the compare view
  when exactly two are checked.
- Compare selection is independent of the single "selected" row used by the toolbar.

### Compare view — unambiguous identity
`VersionCompareView` keeps its two-column metric layout but its **header** is
reworked so each side is identified by more than the label. Per side:
`<A|B marker, colored to the lane> <lane-color dot> <branch pill> <snapshot|HEAD tag>`
then `<label>` and a meta line `#<node id> · <branch> · <author> · <timestamp> · <note>`.
The A/B marker colors match the graph lanes, so a side is traceable back to its
rail. Two "v1.0" snapshots are then distinguished by branch, id, author and time.
Metric rows and amber diff-highlighting are unchanged.

---

## Components

- **`VersionGraphOverlay`** (new; replaces `VersionHistoryPanel` as the entry
  point) — modal shell, header, toolbar, owns selection + compare state, wires
  the existing `useLineageTree` / `useVersionActions` / `useCompareNodes` hooks.
- **`VersionGraph`** (new) — renders rows from `computeGraphLayout` output.
- **`GraphRow`** (new) — checkbox + graph cell (SVG rails/dot/pill) + version cell.
- **`computeGraphLayout`** (new, `frontend/lib/`) — pure lane/edge layout util.
- **`VersionCompareView`** (edit) — replace `NodeHeader` with a richer
  `NodeIdentityHeader` (id, branch, author, timestamp, lane color). Metric body
  untouched.
- **Hooks** (`useVersioning.ts`) — unchanged.
- **Backend** — unchanged.

> Note: `VersionHistoryPanel.tsx` is effectively rewritten. The per-row action
> logic (`NodeRow`, `BranchSection`) is removed; the inline name-input and
> discard-confirm patterns are reused inside the toolbar.

## Data needs vs. what exists

`TreeOut { root_id, nodes[], branches[] }` already carries everything required:
`created_at` (ordering), `branch_id` + `predecessor_id` (lanes + fork edges),
`is_immutable` / `is_head` (dot style), `created_by` (avatar), `version_label` /
`version_note` (text), `BranchOut.name` / `is_main` (pills). The compare endpoint
already returns `node_a` / `node_b` (`VersionNode`) with id, branch context,
`created_by`, `created_at` — enough for the identity header. **No API changes.**

## Testing

- **Unit (vitest):** `computeGraphLayout` — lane assignment, lane reuse, fork
  edges, ordering, dot styles. Pure function, high coverage, no browser.
- **Component (vitest):** toolbar enable/disable per selection type; compare cap
  at two; `NodeIdentityHeader` renders id/branch/author for equal labels.
- **E2E (playwright-bdd, optional):** open overlay → select node → snapshot;
  check two → compare → header shows distinct ids. Per memory, layout/scroll
  behaviour is only trustworthy in a real browser.

## Open questions resolved during brainstorming

- Container → large overlay/modal. Ordering → chronological, newest top.
- Snapshot vs head → visually distinct (filled vs hollow dot). Rows → compact,
  two-line version cell. Avatars → simple user vs agent.
