# spar-plan — Implementation Tasks

> Executable sequence to re-implement this use case from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.
> Parent module task list: [`../tasks.md`](../tasks.md).
>
> **Scope.** Stages 1, 2 and 4 of the structural pipeline (the strength law,
> station sampling, the hinge clearance, the section-geometry seam) are tasked in
> [`../../wing-design/spar-sizing/tasks.md`](../../wing-design/spar-sizing/tasks.md).
> This list covers Stage 3 (the buildable layout) and Stage 5 (the commit).

## Prerequisites

- [ ] `wing-design/spar-sizing` implemented — `required_section_modulus`,
      `solve_dimension`, `build_stations_from_geometry` and
      `rear_spar_x_c_with_clearance` are the inputs this use case consumes.
- [ ] `wing_xsec_spares` persistence available, in **millimetres** (gh-402), with
      `spare_mode`, `spare_origin` and `spare_vector` columns.
- [ ] `should_preserve_normal_spare`
      (`app/converters/spare_origin_preservation.py:43-59`) in place — the commit
      is written to satisfy it.
- [ ] `versioning` available with **immutable** snapshots (ADR 0006).
- [ ] `get_db()` request-scoped session owning the transaction (ADR 0009); the
      service flushes but never commits.
- [ ] **No** CadQuery dependency in the layout path — that is a hard constraint,
      not a convenience (`spar_solver.py:1-24`).

## Tasks

### Stage 3 — the buildable layout

- [ ] **T-SP-01 — Greedy straight-piece fit per half-span.**
  Walk each half root→tip and fit straight pieces; a half whose required OD stays
  inside the band throughout is one piece.
  - Legacy origin: `cad_designer/airplane/geometry/spar_solver.py:342`
    (`plan_spar`), `:619-672` (`solve_spar_plan`)
  - Definition of done: a constant-band wing yields exactly one piece per half,
    spanning root to tip.
  - Confidence: 🟢

- [ ] **T-SP-02 — Telescoping runs.**
  Split a half wherever the strength-required OD exceeds the containment band, so
  outboard pieces nest inside inboard ones.
  - Legacy origin: `spar_solver.py:619-672`
  - Definition of done: a tapering wing yields nested runs with monotonically
    decreasing OD outboard.
  - Confidence: 🟢

- [ ] **T-SP-03 — `_piece_from_run_with_od`: utilisation and feasibility.**
  ```
  utilisation = od / max(tightest_band, 1e-6)
  feasible    = od ≤ tightest_band
  ```
  No clamping. The infeasibility message names the governing station and suggests
  a capped or box spar.
  - Legacy origin: `spar_solver.py:490-529`; ADR 0012
  - Definition of done: an over-loaded root reports `feasible = false`,
    `utilisation > 1.0`, and a message containing the station identifier. A test
    asserts that the emitted OD is **not** reduced to fit.
  - Confidence: 🟢

- [ ] **T-SP-04 — Negligible-load tip (gh-1076).**
  `NEGLIGIBLE_OD_FLOOR_MM = 1.0`; a tip station below it yields **no piece**, and
  the region is reported as `front_no_spar_from_y` / `rear_no_spar_from_y`.
  - Legacy origin: `spar_solver.py:44-53, 438-457`
  - Definition of done: a tip requiring 0.4 mm produces no piece and a populated
    `*_no_spar_from_y`; a tip requiring 1.4 mm still produces one.
  - Confidence: 🟢

- [ ] **T-SP-05 — Front joint via `_inboard_collinear`.**
  Compare the two halves' root `center_z` within `tol_mm = 5.0`: equal →
  `"continuous"`; otherwise `"reinforcement+joiner"` **plus** a generated
  reinforcement piece.
  - Legacy origin: `spar_solver.py` (`_inboard_collinear`)
  - Definition of done: a 3 mm offset is continuous, a 10 mm offset produces the
    reinforcement piece. Both branches asserted.
  - Confidence: 🟢

- [ ] **T-SP-06 — Single-half surfaces force a continuous front joint (gh-1091).**
  A vertical stabiliser has one half; `_inboard_collinear` must not index into
  the empty one.
  - Legacy origin: gh-1091; `spar_solver.py` (`_inboard_collinear`)
  - Definition of done: planning a single-half surface returns
    `"continuous"` and raises no `IndexError`. This is a regression test — the
    bug was an index into an empty list.
  - Confidence: 🟢

- [ ] **T-SP-07 — Rear joint via the through-rod test.**
  `"continuous"` when a straight collinear rod through `y = 0` stays inside the
  band on **both** halves; otherwise `"bent-pin"`.
  - Legacy origin: `spar_solver.py` (the rear-joint branch)
  - Definition of done: both outcomes are covered; the test is performed against
    the band on each half, not only the root.
  - Confidence: 🟢

- [ ] **T-SP-08 — `_bore_for`.**
  ```
  erf_W = required_section_modulus_from_od(od) = od³ / 10
  Di    = (od⁴ − 32 · erf_W · od / π) ^ (1/4)
  fallback when strength wants a solid:  bore = 0.6 · od      # wall_factor
  ```
  - Legacy origin: `spar_solver.py:460-487`
  - Definition of done: the bore reproduces the closed form for a known OD; the
    solid case falls back to `0.6 × od`; a test pins that the modulus is
    reconstructed **from the governing OD**, not carried through from sizing.
  - Confidence: 🟢

- [ ] **T-SP-09 — Telescope slip-fit clearance.**
  `telescope_clearance_mm = 0.5`, applied radially between nested pieces.
  - Legacy origin: `spar_solver.py:460-487`
  - Definition of done: nested pieces differ radially by at least 0.5 mm; a test
    asserts the gap is radial, not diametral (a factor-2 error here makes the
    parts un-assemblable).
  - Confidence: 🟢

- [ ] **T-SP-10 — Keep the layout path CAD-free.**
  No CadQuery import anywhere in the decision logic; every branch is reachable
  from hand-built `StationData`.
  - Legacy origin: `spar_solver.py:1-24`
  - Definition of done: the module imports cleanly with CadQuery uninstalled, and
    the whole branch set runs on the CI fast tier. Add an import-guard test —
    this constraint is easy to break by accident.
  - Confidence: 🟢

### Stage 5 — the commit

- [ ] **T-SP-11 — Plan orchestration.**
  Gather the wing's stations, run the solver for both spars and both halves,
  assemble the result.
  - Legacy origin: `app/services/spar_plan_service.py`
  - Definition of done: a wing with a full station set produces a result carrying
    pieces, both joint types, utilisation, feasibility and the `*_no_spar_from_y`
    fields.
  - Confidence: 🟢

- [ ] **T-SP-12 — Write solved spars as explicit `normal` spars.**
  `spare_mode == "normal"` plus a fully explicit 3-component `spare_origin`
  **and** `spare_vector`, stored in millimetres (gh-402).
  - Legacy origin: `app/services/spar_insert_service.py`;
    `app/converters/spare_origin_preservation.py:43-59`
  - Definition of done: every written row satisfies
    `should_preserve_normal_spare`. Assert the predicate directly against the
    committed rows — a test on the predicate with hand-made input would not catch
    a change in the writer.
  - Confidence: 🟢

- [ ] **T-SP-13 — Round-trip survival (gh-1053).**
  A committed front/rear couple keeps its distinct origins across a
  model → config → model conversion.
  - Legacy origin: gh-1053; `_resolve_spare_vectors_and_origins`
  - Definition of done: after a commit and a read-back, the two origins are
    unchanged and have **not** collapsed onto the default quarter-chord station.
    This is the integration test that pins T-SP-12's purpose.
  - Confidence: 🟢

- [ ] **T-SP-14 — Snapshot before a destructive commit (gh-1058).**
  A segment split or a spare `REPLACE` takes an **immutable** snapshot labelled
  `"Before spar insert"` *before* any mutation.
  - Legacy origin: `spar_insert_service.py:485-497`
  - Definition of done: the snapshot exists and its creation timestamp precedes
    every mutated row's `updated_at`; a non-destructive commit takes **no**
    snapshot.
  - Confidence: 🟢

- [ ] **T-SP-15 — Fail closed when the snapshot fails.**
  If snapshot creation fails, abort the whole commit — *"never mutate without a
  recovery point"*.
  - Legacy origin: `spar_insert_service.py:485-497`
  - Definition of done: with snapshot creation forced to raise, no spar row is
    written and the request errors. This is a **safety** test, not a happy-path
    one.
  - Confidence: 🟢

- [ ] **T-SP-16 — Return the snapshot id.**
  `SparInsertResponse` carries the id so the UI can offer a one-click revert.
  - Legacy origin: `spar_insert_service.py`
  - Definition of done: the response id resolves to the created version node.
  - Confidence: 🟢

- [ ] **T-SP-17 — Do not own the transaction.**
  Flush, never commit; the request-scoped session decides (ADR 0009).
  - Legacy origin: `app/db/session.py`; the project rule
  - Definition of done: an exception raised later in the same request leaves no
    spar rows written.
  - Confidence: 🟡

- [ ] **T-SP-18 — 🔴 Decide whether the plan itself is persisted.**
  There is no `spar_plans` table today: the result is derived, returned and
  projected onto the spar rows, so a committed spar carries no provenance.
  - Legacy origin: absence — no plan table exists in
    `_reversa_sdd/data-dictionary.md`
  - Definition of done: either a stored plan (with its parameters and the moment
    distribution) linked from the committed spars, or an explicit decision that
    plans stay ephemeral. Do not invent a table without a decision.
  - Confidence: 🟡 — requires a human decision

- [ ] **T-SP-19 — 🔴 Confirm the `SparPlanResult` field names.**
  Only `front_no_spar_from_y` and `rear_no_spar_from_y` are confirmed by name
  (from the gh-1076 test mocks); the rest are inferred from behaviour.
  - Legacy origin: the schema module was not read; behaviour from
    `spar_solver.py:619-672`
  - Definition of done: the response schema is read from the source and the field
    table in [`design.md`](design.md) §Result shape is corrected.
  - Confidence: 🟡

## Test Tasks

- [ ] **TT-SP-01** — Happy path: a constant-band wing yields one piece per half
      with a continuous front joint (see `requirements.md`, Acceptance Criteria).
- [ ] **TT-SP-02** — Failure path: an over-loaded root reports
      `feasible = false`, `utilisation > 1.0` and names the governing station —
      and the OD is **not** reduced.
- [ ] **TT-SP-03** — Regression (gh-1076): a 0.4 mm tip yields no piece and sets
      `front_no_spar_from_y`.
- [ ] **TT-SP-04** — Regression (gh-1091): a single-half surface plans without an
      `IndexError`.
- [ ] **TT-SP-05** — Regression (gh-1053): a committed front/rear couple survives
      a model → config → model round-trip with distinct origins.
- [ ] **TT-SP-06** — Safety (gh-1058): a failing snapshot aborts the commit and
      mutates nothing.
- [ ] **TT-SP-07** — Snapshot ordering: the snapshot precedes every mutation.
- [ ] **TT-SP-08** — Non-destructive commits take no snapshot.
- [ ] **TT-SP-09** — Joints: all four combinations (front continuous /
      reinforced × rear continuous / bent-pin).
- [ ] **TT-SP-10** — Bore: the closed form for a known OD, plus the `0.6 × od`
      solid fallback.
- [ ] **TT-SP-11** — Clearance: nested pieces differ **radially** by ≥ 0.5 mm.
- [ ] **TT-SP-12** — Import guard: the layout module imports with CadQuery
      absent, and the full branch set runs on the fast tier.

## Suggested Order

1. **T-SP-10 first.** Establish the no-CAD constraint before any code exists;
   retrofitting it is what makes solver code untestable.
2. **T-SP-01 → T-SP-04** — the per-half layout, ending with the negligible-tip
   rule. Write TT-SP-02 before T-SP-03 so "report, never clamp" is pinned from
   the start (ADR 0012).
3. **T-SP-05 → T-SP-07** — the joints, which are the only place the two halves
   interact. T-SP-06 (single-half) should be written as a failing test first.
4. **T-SP-08 / T-SP-09** — bore and clearance; independent of the joints.
5. **T-SP-11** — orchestration, once the solver is complete.
6. **T-SP-14 → T-SP-16 before T-SP-12.** Get the snapshot guard in place *before*
   the code that mutates spars exists, so there is never a window in which a
   destructive commit can run unguarded.
7. **T-SP-12 / T-SP-13** — the commit and its round-trip test, together. They are
   one unit of work: T-SP-12 without T-SP-13 looks correct and silently loses the
   result on the next read.
8. **T-SP-17** falls out of the session design.
9. **T-SP-18 / T-SP-19** are blocked on a decision and a source read; do not
   guess either.

## Resolved by the validation interview

- **Should the plan be persisted?** Today a committed spar has geometry but no
  provenance — not the parameters, not the moment distribution, not a plan id.
  A re-solve silently supersedes the previous answer with nothing to diff.
- **What are `SparPlanResult`'s actual field names?** Only the two
  `*_no_spar_from_y` keys are confirmed; the rest are inferred from behaviour and
  cannot be reproduced exactly from this spec.
- **What counts as a "destructive" spar edit?** The list (segment split, spare
  `REPLACE`) is hard-coded rather than derived, so a future destructive edit type
  would silently miss the snapshot guard. Should the guard default to
  snapshotting unless proven safe?
- **Should the plan round to stock tube sizes?** It emits computed diameters; a
  builder buys discrete sizes, and nothing reports the plan against a stock list.
- **Is the 5 mm front-joint tolerance appropriate at all scales?** It is a bare
  constant, not derived from section thickness or tube diameter, so its meaning
  changes with aircraft size.
