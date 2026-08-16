# spar-plan

> Use-case specification, nested under the module [`construction-plans`](../requirements.md).
> Focuses on WHAT this use case does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: wing-design
> (Structural pipeline, Stages 3 and 5) and §Module: versioning
> (Provenance — human vs AI), `_reversa_sdd/domain.md` §2.2,
> [ADR 0012](../../adrs/0012-design-warnings-instead-of-silent-fallbacks.md),
> [ADR 0006](../../adrs/0006-versioning-by-row-copy-not-json-snapshots.md).
>
> **Deliberate non-duplication.** The strength law, the section-modulus formulas,
> station sampling and the section-geometry seam are specified once, in
> [`../../wing-design/spar-sizing/`](../../wing-design/spar-sizing/requirements.md).
> This use case covers what happens **after** the solver has a layout: turning it
> into a buildable construction output and committing it back onto the aircraft.

## Overview

`spar-plan` is the construction-facing half of the spar pipeline. Where
`wing-design/spar-sizing` answers *"how thick must the spar be?"*, this use case
answers *"what does the builder actually cut, and how do the pieces join?"* — a
per-half-span list of straight pieces with outer diameters, bores, telescoping
runs, a front and a rear joint type, an honest feasibility verdict, and the
regions where no spar is needed at all. It then **commits** that layout back onto
the wing's spars, and because a commit can be destructive it takes an automatic
immutable snapshot first. 🟢

## Responsibilities

- Orchestrate a spar plan for a wing: gather stations, run the solver, assemble
  the result. 🟢
- Express the layout as buildable pieces per half-span, with telescoping runs
  where one straight rod cannot carry the whole span. 🟢
- Decide the **front joint** and the **rear joint** type at the centreline. 🟢
- Compute a bore per piece, including the slip-fit clearance between nested
  tubes. 🟢
- Report utilisation and feasibility honestly, naming the governing station —
  never clamp. 🟢
- Emit **no piece** for a negligible-load tip and report where the spar stops. 🟢
- Commit the solved layout back onto `wing_xsec_spares` in a form that survives
  the next read. 🟢
- Take an automatic immutable snapshot **before** any destructive commit, and
  abort the commit if the snapshot fails. 🟢

**Explicitly NOT this use case's responsibility:** the strength law and the
section-modulus formulas, station sampling, the rear-spar hinge clearance and the
section-geometry seam (→ [`../../wing-design/spar-sizing/`](../../wing-design/spar-sizing/requirements.md));
spar CRUD and the mm ↔ m conversion boundary
(→ `wing-design/cross-section-crud`); the aerodynamic load that produces the
moment distribution (→ `aero-analysis`); building a CAD solid that contains the
spar (→ `cad-generation`); the version DAG and snapshot storage itself
(→ `versioning`); construction **plans** in the `$TYPE` sense, which share this
module but nothing else (→ [`../plan-execution/`](../plan-execution/requirements.md)).

## Business Rules

> Rules inherited from the module `wing-design` keep their original `BR-W*` ids;
> rules local to this use case carry an `SP-` prefix.

### The buildable layout

- **BR-SP1 — A plan is per half-span, made of straight pieces.** 🟢
  `plan_spar` / `solve_spar_plan` (`cad_designer/airplane/geometry/spar_solver.py:342,
  619-672`) perform a greedy straight-piece fit along each half-span and split it
  into **telescoping runs** wherever the strength-required OD exceeds the
  containment band. A single rod that fits the whole half is one piece; anything
  else nests.
- **BR-SP2 — The front joint is decided by root collinearity.** 🟢
  `_inboard_collinear` compares the two halves' root `center_z` within
  `tol_mm = 5.0`:

  ```
  |center_z(left root) − center_z(right root)| ≤ 5.0 mm  → "continuous"
  otherwise                                              → "reinforcement+joiner"
                                                            (+ a generated
                                                             reinforcement piece)
  ```

- **BR-W11 — A single-half surface forces a continuous front joint (gh-1091).** 🟢
  A vertical stabiliser has one half, so `_inboard_collinear` must not index into
  the empty half; the joint is forced to `"continuous"`.
- **BR-SP3 — The rear joint is decided by a through-rod test.** 🟢
  `"continuous"` when a straight collinear rod through `y = 0` stays inside the
  containment band on **both** halves; otherwise `"bent-pin"`.
- **BR-W9 — Utilisation is reported honestly and may exceed 1.0.** 🟢

  ```
  utilisation = od / max(tightest_band, 1e-6)
  feasible    = od ≤ tightest_band
  ```

  (`_piece_from_run_with_od`, `spar_solver.py:490-529`.) The infeasibility
  message **names the governing station** and suggests a capped or box spar.
  There is no silent clamping — ADR 0012.
- **BR-W10 — A negligible-load tip produces no spar (gh-1076).** 🟢
  `NEGLIGIBLE_OD_FLOOR_MM = 1.0`. A tip station whose required OD falls below
  1 mm yields **no piece**; the region is reported as `front_no_spar_from_y` /
  `rear_no_spar_from_y` rather than a degenerate Ø≈0 tube
  (`spar_solver.py:44-53, 438-457`).
- **BR-SP4 — Bore is derived from the governing OD, with a wall-factor
  fallback.** 🟢 `_bore_for` (`spar_solver.py:460-487`) reconstructs the required
  section modulus from the governing rod OD and solves the tube path:

  ```
  required_section_modulus_from_od(od) = od³ / 10
  Di = (od⁴ − 32 · erf_W · od / π) ^ (1/4)
  fallback, when strength wants a solid:  bore = wall_factor · od,
                                          wall_factor = 0.6
  telescope_clearance_mm = 0.5            # radial slip-fit gap between nested tubes
  ```

- **BR-W12 — The solver is deliberately CAD-free.** 🟢 Every branch of the
  decision logic runs on the CI fast tier against hand-built `StationData`
  (`spar_solver.py:1-24`) — no CadQuery import. A re-implementation must keep the
  layout decisions testable without a geometry kernel.

### The commit

- **BR-SP5 — A solved spar is written as an explicit `normal` spar.** 🟢
  `spar_insert_service` writes the solved geometry back onto `wing_xsec_spares`
  with `spare_mode == "normal"` plus a fully explicit 3-component `spare_origin`
  **and** `spare_vector`. That is exactly the condition
  `should_preserve_normal_spare` uses to exempt a spar from the
  clear-and-recompute path on the next model → config conversion
  (gh-1053, `app/converters/spare_origin_preservation.py:43-59`). 🟡 The
  predicate is confirmed; that the insert service is what produces the qualifying
  rows is the necessary consequence.
- **BR-SP6 — Without the exemption the solver's output is destroyed.** 🟢
  `_resolve_spare_vectors_and_origins` normally clears and recomputes every
  spar's origin and vector (the gh-352/gh-362 unit-leak guard). A
  solver-produced front/rear couple that lost the exemption would collapse onto
  the default quarter-chord station on the very next read.
- **BR-SP7 — Never mutate without a recovery point (gh-1058).** 🟢 A
  **destructive** spar commit — a segment split, or a spare `REPLACE` — takes an
  automatic **immutable** snapshot labelled `"Before spar insert"` *before*
  mutating anything, and **aborts the whole commit if the snapshot fails**
  (`app/services/spar_insert_service.py:485-497`). This is the only non-copilot
  automated snapshot in the system. The snapshot id is returned in
  `SparInsertResponse` so the UI can offer a one-click revert.
- **BR-SP8 — The commit is transactional with the request.** 🟡 The service
  follows the project rule that `get_db()` owns the transaction boundary
  (ADR 0009): it flushes but never commits, so a later failure in the same
  request rolls the spar writes back. The snapshot taken in BR-SP7 is what makes
  a *successful but unwanted* commit recoverable — rollback covers the failure
  case, the snapshot covers the regret case.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-SP-01 | Produce a spar plan for a wing from its stations and a design moment | Must | The result carries pieces per half-span, both joint types, utilisation and a feasibility verdict |
| RF-SP-02 | Fit straight pieces greedily along each half-span | Must | A half-span that one rod can carry yields exactly one piece |
| RF-SP-03 | Split into telescoping runs where the required OD exceeds the band | Must | A tapering wing yields nested pieces with decreasing OD outboard |
| RF-SP-04 | Decide the front joint from root collinearity within 5 mm | Must | Equal root `center_z` → `"continuous"`; a 10 mm offset → `"reinforcement+joiner"` plus a reinforcement piece |
| RF-SP-05 | Force a continuous front joint for a single-half surface | Must | A vertical stabiliser plans without indexing into an empty half (gh-1091) |
| RF-SP-06 | Decide the rear joint from a through-rod test | Must | A straight rod through `y = 0` inside the band on both halves → `"continuous"`, else `"bent-pin"` |
| RF-SP-07 | Report utilisation and feasibility without clamping | Must | An over-loaded root reports `feasible = false`, `utilisation > 1.0`, names the governing station and suggests a capped or box spar |
| RF-SP-08 | Emit no piece for a negligible-load tip | Must | A tip whose required OD < 1.0 mm yields no piece and sets `front_no_spar_from_y` |
| RF-SP-09 | Compute a bore per piece from the governing OD | Must | The bore follows the tube inverse; a strength-solid case falls back to `0.6 × od` |
| RF-SP-10 | Apply the telescope slip-fit clearance between nested pieces | Must | Nested pieces differ by at least `telescope_clearance_mm = 0.5` radially |
| RF-SP-11 | Keep the layout decisions free of any CAD import | Must | Every branch is reachable in a unit test built from hand-made `StationData` |
| RF-SP-12 | Commit the solved layout onto the wing's spars | Must | After a commit, `wing_xsec_spares` carries the solved geometry |
| RF-SP-13 | Write solved spars as explicit `normal` spars | Must | Each written spar has `spare_mode == "normal"` and a 3-component `spare_origin` and `spare_vector` |
| RF-SP-14 | Survive the next model → config round-trip | Must | A read-back after a commit leaves the front/rear couple's distinct origins intact rather than collapsing them to quarter chord |
| RF-SP-15 | Snapshot before any destructive commit | Must | A segment split or a spare `REPLACE` creates an immutable snapshot labelled `"Before spar insert"` before any mutation |
| RF-SP-16 | Abort the commit when the snapshot fails | Must | With snapshot creation forced to fail, nothing is mutated and the request errors |
| RF-SP-17 | Return the snapshot id to the caller | Must | `SparInsertResponse` carries the id so the UI can offer a one-click revert |
| RF-SP-18 | Roll back a partially applied commit on a later failure | Should | An exception later in the request leaves no spar rows written (ADR 0009) |
| RF-SP-19 | Snapshot before a non-destructive commit | Won't | The snapshot is scoped to destructive edits — split and `REPLACE` — only |
| RF-SP-20 | Clamp an infeasible layout to something buildable | Won't | Deliberately refused: the verdict is reported, never hidden (ADR 0012) |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Safety | An infeasible layout is reported with its governing station, never silently clamped | `spar_solver.py:490-529` (ADR 0012) | 🟢 |
| Safety | A destructive edit is never applied without a recovery point, and the guard fails closed | `spar_insert_service.py:485-497` (gh-1058) | 🟢 |
| Correctness | A negligible-load tip yields no piece rather than a degenerate Ø≈0 tube | `spar_solver.py:44-53, 438-457` (gh-1076) | 🟢 |
| Correctness | Solved spars are written in exactly the shape the preservation predicate exempts | `spare_origin_preservation.py:43-59` (gh-1053) | 🟢 / 🟡 for the coupling |
| Correctness | A single-half surface does not index into an empty half | gh-1091 | 🟢 |
| Testability | The layout logic has no CAD dependency, so every branch runs on the CI fast tier | `spar_solver.py:1-24` | 🟢 |
| Consistency | The commit does not own its transaction; the request-scoped session does | ADR 0009 | 🟡 |
| Usability | The infeasibility message is written for a builder — it names a station and suggests an alternative section | `spar_solver.py:490-529` | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Buildable layout

  Scenario: A half-span that one rod can carry yields one piece
    Given a wing whose required OD is within the band at every station
    When the spar plan is solved
    Then exactly one piece is emitted per half-span
    And the piece spans from root to tip

  Scenario: A tapering wing telescopes
    Given a wing whose containment band narrows outboard below the required OD
    When the plan is solved
    Then the half-span is split into nested runs
    And each outboard piece has a smaller outer diameter than its inboard neighbour
    And nested pieces differ radially by at least 0.5 mm

  Scenario: Collinear roots give a continuous front joint
    Given both halves' root center_z are within 5 mm
    When the plan is solved
    Then the front joint is "continuous"
    And no reinforcement piece is generated

  Scenario: Offset roots give a reinforced front joint
    Given the two halves' root center_z differ by 10 mm
    When the plan is solved
    Then the front joint is "reinforcement+joiner"
    And a reinforcement piece is generated

  Scenario: A single-half surface is forced continuous
    Given a vertical stabiliser with only one half
    When the plan is solved
    Then the front joint is "continuous"
    And no index error occurs
    # gh-1091

  Scenario: A through-rod decides the rear joint
    Given a straight collinear rod through y = 0 stays inside the band on both halves
    When the plan is solved
    Then the rear joint is "continuous"

  Scenario: A rod that leaves the band gives a bent pin
    Given a straight collinear rod through y = 0 leaves the band on one half
    When the plan is solved
    Then the rear joint is "bent-pin"

Feature: Honest reporting

  Scenario: An over-loaded root reports infeasibility
    Given a station whose required OD exceeds the containment band
    When the plan is solved
    Then feasible is false
    And utilisation is greater than 1.0
    And the message names the governing station
    And it suggests a capped or box spar

  Scenario: A negligible-load tip gets no spar
    Given a tip station whose required OD is below 1.0 mm
    When the plan is solved
    Then no piece is emitted for that region
    And front_no_spar_from_y reports where the spar stops

Feature: Bore

  Scenario: A bore follows the tube inverse
    Given a governing rod outer diameter od
    When the bore is computed
    Then the required section modulus is reconstructed as od cubed over 10
    And the bore solves the tube inverse for that modulus

  Scenario: A strength-solid case falls back to the wall factor
    Given strength requires a solid section
    When the bore is computed
    Then the bore equals 0.6 times the outer diameter

Feature: Commit

  Scenario: A solved plan is written back as explicit normal spars
    Given a solved spar plan
    When it is committed
    Then every written spar has spare_mode "normal"
    And a three-component spare_origin and spare_vector

  Scenario: The commit survives the next read
    Given a committed front and rear spar couple with distinct origins
    When the wing is converted to a WingConfiguration and back
    Then both origins are unchanged
    # gh-1053: without the preservation exemption both collapse to quarter chord

  Scenario: A destructive commit snapshots first
    Given a spar commit that splits a segment
    When the commit runs
    Then an immutable snapshot labelled "Before spar insert" exists
    And it was created before any mutation
    And its id is returned in the response

  Scenario: A failing snapshot aborts the commit
    Given snapshot creation fails
    When a destructive spar commit is attempted
    Then nothing is mutated
    And the request reports an error
    # "never mutate without a recovery point"

  Scenario: A later failure rolls the commit back
    Given a spar commit succeeded but a later step in the same request raises
    When the request ends
    Then no spar rows were written
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| The buildable layout: pieces, telescoping, both joints (RF-SP-01…RF-SP-06) | Must | This *is* the deliverable — a person cuts carbon tube from it |
| Honest utilisation and feasibility (RF-SP-07) | Must | Structural-safety output. A clamped verdict would be a silently under-strength wing (ADR 0012) |
| Negligible-load tip handling (RF-SP-08) | Must | The alternative is a Ø≈0 tube in a cut list, which is worse than nothing (gh-1076) |
| Bore and slip-fit clearance (RF-SP-09/RF-SP-10) | Must | Telescoping pieces that do not slide are not buildable |
| CAD-free decision logic (RF-SP-11) | Must | Without it none of the safety branches are testable on the fast CI tier |
| Commit as explicit `normal` spars (RF-SP-12/RF-SP-13/RF-SP-14) | Must | Getting this wrong destroys the solver's output on the very next read (gh-1053) |
| Snapshot before a destructive commit, failing closed (RF-SP-15/RF-SP-16/RF-SP-17) | Must | The one automated recovery point outside the copilot; a split is unrecoverable by hand |
| Rollback on a later failure (RF-SP-18) | Should | Follows from ADR 0009 rather than from this use case's own code |
| Single-half handling (RF-SP-05) | Must | A vertical stabiliser is an ordinary case, not an edge case |
| Snapshotting non-destructive commits (RF-SP-19) | Won't | Deliberately scoped to split and `REPLACE`; snapshotting every edit would flood the version DAG |
| Clamping an infeasible layout (RF-SP-20) | Won't | Refused by design — the whole point of ADR 0012 |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `cad_designer/airplane/geometry/spar_solver.py` | `plan_spar` (l.342), `solve_spar_plan` (l.619-672), `_piece_from_run_with_od` (l.490-529), `_bore_for` (l.460-487), `_inboard_collinear`, `NEGLIGIBLE_OD_FLOOR_MM` (l.44-53), the no-spar regions (l.438-457) | 🟢 |
| `app/services/spar_plan_service.py` | plan orchestration | 🟢 |
| `app/services/spar_insert_service.py` | commit; the automatic snapshot at l.485-497 (gh-1058) | 🟢 |
| `app/converters/spare_origin_preservation.py` | `should_preserve_normal_spare` (l.43-59) — the predicate the commit must satisfy | 🟢 |
| `app/models/aeroplanemodel.py` | `WingXSecSpareModel` — the target rows (millimetres, gh-402) | 🟢 |
| `app/services/aeroplane_version_service.py` | the immutable snapshot this use case triggers (ADR 0006) | 🟢 |
| Formulas, station sampling, hinge clearance, section geometry | → [`../../wing-design/spar-sizing/`](../../wing-design/spar-sizing/requirements.md) | 🟢 specified there |
