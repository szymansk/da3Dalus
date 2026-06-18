# Spar insert v2 — main-spar segment split + snapshot + readability — design spec

**Date:** 2026-06-18
**Status:** Draft for review
**Builds on:** #1048 (built-spar display + insert), #1049 (insert endpoint), #1053
(origin preservation), #1029/#1031 (solver/plan), #901 (versioning: snapshot/restore),
gh-402 (spare units). Resolves the single-segment / telescoping-main-spar gap.

## Background / decisions (from design discussion)
- **VaseMode construction: `spar_index = 0` IS the main spar** and drives the wing's
  internal structure. VaseMode treats *any* index-0 spar in a segment as the main spar.
  → a telescoping main spar of varying diameter **cannot** live as multiple pieces in
  one segment; each diameter needs its **own segment** with the main piece at index 0.
- **Main (front) spar → Option A (segment split).** Split the segment at each
  telescoping joint so every resulting segment carries exactly one main-spar piece at
  index 0. Segment boundary = component boundary (user prints & assembles segment by
  segment; telescoping then assembles cleanly).
- **Secondary spars (rear/torsion, reinforcement) → Option B.** Persist as partial-span
  Spares with `spare_start` + `spare_length` under their own ids (rear root = index 1,
  further pieces = next free ids). No segment split. The construction already builds
  partial-span spares (`VaseModeWingCreator`: `extrude_length = spare.spare_length`,
  `.workplane(offset=spare.spare_start)`).
- **Children at a split (resolved):**
  - **Control surface** always spans a whole segment; **computed spars never overlap a
    control surface** (the torsion/rear spar placement MUST stay clear of it). On split,
    duplicate the control surface onto each new sub-segment (each over its sub-span);
    handle naming/mixing carefully (cf. gh-955). (A designer may manually place a
    reinforcing spar inside a control surface — that is not a computed spar.)
  - **Turbulator** is only a surface bump, no spar influence → carries along, no special
    handling.
  - Therefore the split is unrestricted — perform it wherever the main-spar telescoping
    requires it.
- **Auto-snapshot before destructive change.** Before any insert-commit that mutates
  structure (segment split) — and, by extension, any REPLACE-on-commit that clears
  existing spares — automatically create a snapshot of the current head so the user can
  **accept** (keep) or **reject** (restore). Uses the existing
  `aeroplane_version_service.snapshot()` / `restore()` (clones the full subgraph incl.
  wings/segments/spares); endpoints `POST /aeroplanes/{id}/snapshot` +
  `POST /aeroplanes/{snapshot_id}/restore`.

## Scope

### 1. Readability fixes (quick, independent)
- **#1045:** the solver must not emit a Ø0 terminal tip piece (where M→0 the required
  OD rounds to 0). Drop/merge zero-OD pieces; never mark one "OK". Applies to plan,
  built-spar display, and insert.
- **Built-spar display:** show each piece's **spanwise extent** (y_start → y_end, mm)
  and the **telescoping joint position** (= next piece's start y, from `spare_origin`).
  Data already present (`spare_origin`, derive end from next piece / governing_y; expose
  `length`/`y_start`/`y_end` on the piece schema if cleaner).
- Clarify the last-piece **"Continuous"** label → e.g. "to tip — no joint".

### 2. Auto-snapshot + accept/reject on destructive insert
- The insert-commit service first calls `snapshot()`, returns the snapshot id alongside
  the result. Frontend surfaces it: "Snapshot #N created — Revert" → `restore()`.
- Applies to the segment-split commit AND the existing REPLACE-on-commit (covers #1054:
  no more silent loss of manual spares — there's always a one-click revert).

### 3. Main-spar segment split (the structural feature)
- When the solved **main (front)** spar is multi-piece (telescopes), the insert splits
  the host segment at each joint y into N sub-segments (preserving total span/geometry),
  so each sub-segment gets one main piece at `spar_index 0`.
- **Split mechanics (new helper in cad_designer / converter layer; topology classes
  stay read-only — construct new WingSegments, don't mutate the classes):**
  - New segment lengths sum to the original; airfoils interpolated at the split y
    (reuse the analytic section path #1046 for the intermediate airfoil/chord/twist so
    the loft is unchanged); dihedral/sweep/incidence carried consistently.
  - **Children transfer:** duplicate the control surface onto each sub-segment over its
    sub-span (chordwise params copied; spanwise = sub-segment; names disambiguated per
    gh-955 mixing rules). Turbulator carried along. Existing (manual) spares re-homed to
    the sub-segment they fall in.
  - The same logical main spar keeps index 0 in every (sub-)segment (the cross-segment
    invariant from #1049).
- **Rear/torsion spar solver constraint:** never place a computed spar overlapping a
  control surface — add an explicit "stay forward of the control-surface region" guard
  to the rear-spar placement.
- **Preview (dry-run) must show the splits:** the resulting segment list (with the new
  boundaries), per sub-segment the main piece + duplicated control surface, the snapshot
  that will be taken, and the REPLACE scope.

## Testing
- Backend fast (mock solver/geometry): Ø0 suppression; split math (lengths sum, airfoil
  interpolation at joint y); control-surface duplication onto sub-segments; turbulator
  carry-along; secondary-spar Option-B start/length + index assignment; rear-spar
  control-surface-clearance; snapshot-taken-before-commit; index-0-per-subsegment
  invariant; dry-run shows splits.
- Backend slow/requires_cadquery: compute→split→insert round-trip on a real wing; the
  built solid lofts identically across the split (no geometry change); each sub-segment's
  index-0 spar is the main piece; revert via `restore()` returns the original.
- Frontend vitest: built-spar extent/joint display; #1045 hidden; split + snapshot shown
  in preview; accept/reject (revert) flow.
- Persona UAT (Scholz + RC): split is structurally transparent (geometry unchanged),
  main spar index 0 per sub-segment, secondary spars clear of control surfaces,
  snapshot/revert works, telescoping buildable segment-by-segment.

## Decomposition (epic + sub-issues)
1. Readability: #1045 Ø0 suppression + built-spar extent/joint display + label.
2. Auto-snapshot + accept/reject on destructive insert-commit (wires #901 snapshot/restore).
3. Main-spar segment split (split math + child transfer: control-surface duplication,
   turbulator carry-along, spare re-home; index-0-per-subsegment) + rear-spar
   control-surface-clearance constraint + secondary-spar Option-B start/length.
4. Frontend: preview shows splits + snapshot/revert; consume the v2 insert.

## Out of scope
- Manual segment splitting UI (this split is solver-driven on main-spar insert).
- Buckling (#1011), real T(y) (#1041).
