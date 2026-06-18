# Built-spar display + "Add spar to wing" — design spec

**Date:** 2026-06-18
**Status:** Draft for review
**Builds on:** #1029/#1031 (spar-plan solver + endpoint), #1032 (`insert_spar_plan`),
#1046 (analytic section path), #1018 (spare persistence REST), gh-402 (spare units).

## Problem
The `SparSizingPanel` (#1008) shows only the per-station *required* dimensions. Two
things are missing: (1) a display of the **buildable** spar — what actually gets built —
and (2) a **button to add that spar to the wing** (persist it into the construction).

## Decisions (confirmed)
- The "built spar" display shows the **full two-spar plan** (#1029): front + rear,
  telescoping pieces, with OD/ID/wall/length, joint type, feasibility, placement.
- "Add to wing" is **preview → confirm**: first show exactly what will be inserted
  (which spares, dimensions, placement, target segment + index), then a second
  confirm persists.
- Persisted into the construction (DB `wing_xsec_spares`) → appears in the
  construction tree and the CAD/STEP download.

## HARD INVARIANT (cad_designer construction relies on it)
- The **main (front) spar MUST always be `spar_index = 0`** (the per-segment
  `sort_index` of the spare).
- The **same logical spar carries the same `spar_index` in EVERY segment** it passes
  through (front = 0, rear = 1, reinforcement = its own consistent index).
- Telescoping pieces of one logical spar keep that spar's index within their segment.
- **Implementer MUST first verify** how `cad_designer` consumes `spar_index`/`sort_index`
  in construction and match that exactly; the insert must guarantee this ordering (and
  must not shuffle existing spares into wrong indices — if a segment already has a spar
  at index 0, define and document the merge/replace behaviour, do not silently corrupt
  indices).

## Architecture

```
SparSizingPanel
  ├─ "Built spar" section  ← GET buildable plan (spar-plan #1031, analytic/fast)
  └─ "Add spar to wing" button
        ├─ click → PREVIEW (dry-run): backend maps plan → per-segment Spares + indices
        └─ confirm → COMMIT: backend persists the Spares (spar_index invariant)
```

### Backend — new insert path (build on #1031 + #1032 + #1018)
A spar-plan → wing insert that supports a **dry-run preview** and a **commit**:
- `POST /aeroplanes/{id}/spar-plan/insert` with `dry_run: bool` (or a `/preview` +
  `/commit` pair — implementer's call, keep it one service with a dry_run flag).
- Computes the SparPlan (reusing spar_plan_service), maps each piece to a `Spare`
  (reuse `spar_cad_insertion.spar_piece_to_spare`), assigns the **spar_index**
  per the invariant (front pieces → index 0 in each segment they occupy; rear → 1;
  reinforcement → next), and resolves the **target segment / cross-section** for each
  piece from its spanwise span (`spare_origin.y` / `governing_y` → segment via
  accumulated lengths).
- **dry_run=true** → returns the planned insertions (per spare: segment index, spar_index,
  dimensions in metres, origin/vector, joint note, feasible) WITHOUT writing.
- **dry_run=false** → persists via the existing spare path (`wing_service.create_spare`
  with mm conversion / `_convert_spare_to_mm`), honouring the spar_index as `sort_index`.
- Infeasible plan (#1037 flag) → refuse to insert, return the reason (don't build junk).
- Units: plan mm → response m (API convention) → DB mm.

### Frontend — SparSizingPanel additions
- **"Built spar" section:** call the spar-plan (a `useSparPlan` hook on #1031) for the
  current wing/loads/material/shape; render the buildable pieces grouped by spar
  (Front / Rear / Reinforcement): OD × ID (wall) × length, joint type (continuous /
  telescoping / bent-pin / reinforcement+joiner), feasibility. Clearly mark the front
  spar as the main spar (index 0).
- **"Add spar to wing" button:** disabled when the plan is infeasible. Click → call
  insert dry_run → show a preview list (segment, spar_index, dims, placement) → user
  confirms → call commit → success/error feedback; refresh the construction tree.
- Reuse existing UI patterns (collapsible section, modal/confirm).

## Testing
- Backend: fast tests (mock the solver/geometry boundary) for the mapping +
  **spar_index invariant** (front=0 in every segment; same spar same index; rear=1),
  dry_run vs commit, infeasible-plan refusal, unit conversion. A slow/requires_cadquery
  round-trip (compute → insert → wing carries spares at the right indices).
- Frontend: vitest for the built-spar rendering + the preview→confirm flow (mocked
  endpoint), feasibility gating.
- Persona UAT (Scholz + RC): the displayed buildable dims match the sizing, and the
  inserted spar is structurally + buildably sensible (main spar index 0, consistent
  indices, telescoping represented).

## Decomposition (epic + sub-issues)
1. Backend: spar-plan → wing insert endpoint (dry-run preview + commit) with the
   spar_index invariant.
2. Frontend: SparSizingPanel "Built spar" display + preview→confirm "Add to wing".

## Out of scope
- Editing/removing inserted spars from this panel (use the existing spare CRUD).
- Buckling/min-wall (#1011), real T(y) (#1041), Ø0-tip guard (#1045) — separate.
