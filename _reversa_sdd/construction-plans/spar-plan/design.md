# spar-plan — Technical Design

> Use-case design, nested under the module [`construction-plans`](../design.md).
> Focuses on HOW this use case is built, derived from the legacy code.
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
>
> **Deliberate non-duplication.** The strength law, the section-modulus
> formulas, station sampling, the rear-spar hinge clearance and the
> section-geometry seam are specified once, in
> [`../../wing-design/spar-sizing/design.md`](../../wing-design/spar-sizing/design.md)
> (Stages 1, 2 and 4). This document covers Stage 3 (the buildable layout) and
> Stage 5 (the commit).

## Interface

### Layout solve — `cad_designer/airplane/geometry/spar_solver.py` 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `plan_spar` | `(stations, params, …)` | plan | one spar, one half-span (l.342) |
| `solve_spar_plan` | `(…)` | `SparPlanResult` | orchestrates both spars, both halves, both joints (l.619-672) |
| `_piece_from_run_with_od` | `(run, od, band)` | piece | utilisation + feasibility, no clamping (l.490-529) |
| `_bore_for` | `(od, …)` | `float` | tube inverse, `wall_factor` fallback (l.460-487) |
| `_inboard_collinear` | `(left, right, tol_mm=5.0)` | `bool` | front-joint decision; single-half safe (gh-1091) |

Constants: `NEGLIGIBLE_OD_FLOOR_MM = 1.0` (l.44-53) ·
`telescope_clearance_mm = 0.5` · `wall_factor = 0.6` (l.460-487) ·
front-joint `tol_mm = 5.0`.

### Orchestration and commit 🟢

| Symbol | File | Note |
|---|---|---|
| plan orchestration | `app/services/spar_plan_service.py` | gathers stations, calls the solver, assembles the result |
| commit | `app/services/spar_insert_service.py` | writes `wing_xsec_spares`; auto-snapshot at l.485-497 |
| `should_preserve_normal_spare` | `app/converters/spare_origin_preservation.py:43-59` | the predicate the commit must satisfy |

### Result shape 🟡

`SparPlanResult` carries, per spar (front / rear) and per half-span:

| Field | Meaning |
|---|---|
| pieces | straight pieces, outboard-ordered, each with OD, bore, y-extent |
| front joint | `"continuous"` \| `"reinforcement+joiner"` (+ a reinforcement piece) |
| rear joint | `"continuous"` \| `"bent-pin"` |
| `utilisation` | `od / max(tightest_band, 1e-6)` — may exceed 1.0 |
| `feasible` | `od ≤ tightest_band` |
| message | names the governing station on infeasibility |
| `front_no_spar_from_y` / `rear_no_spar_from_y` | where the spar stops (gh-1076) |

🟡 The exact field names beyond the two `*_no_spar_from_y` keys (confirmed from
the gh-1076 test mocks) were not read from the schema module.

## Main Flow

### F1 — Stage 3, the layout solve 🟢

```
per half-span, per spar (front, rear):

  1. greedy straight-piece fit along the half
  2. wherever required_od(y) > containment_band(y):
         split into TELESCOPING RUNS
  3. per run:  _piece_from_run_with_od(run, od, band)
         utilisation = od / max(tightest_band, 1e-6)
         feasible    = od ≤ tightest_band          ← reported, NEVER clamped
  4. per piece:  _bore_for(od)
  5. tip:  required_od < NEGLIGIBLE_OD_FLOOR_MM (1.0 mm)
              → emit NO piece
              → report front_no_spar_from_y / rear_no_spar_from_y
```

Everything above runs on plain `StationData` values. There is no CadQuery import
anywhere in the decision path (`spar_solver.py:1-24`), which is what makes each
of these branches reachable from a fast unit test.

### F2 — The two joints 🟢

The joints are the only place the two halves interact, and they are decided
differently:

```
FRONT — a geometric collinearity test at the root:

    _inboard_collinear(left, right, tol_mm = 5.0):
        |center_z(left root) − center_z(right root)| ≤ 5.0   → "continuous"
        otherwise                                            → "reinforcement+joiner"
                                                                + generate a
                                                                  reinforcement piece

    single-half surface (vertical stabiliser, gh-1091):
        forced "continuous" — do NOT index into the empty half


REAR — a feasibility test through the centreline:

    can a straight collinear rod through y = 0 stay inside the band
    on BOTH halves?
        yes → "continuous"
        no  → "bent-pin"
```

The asymmetry is deliberate: the front spar sits near the thickest part of the
section, where the two halves' spar axes either line up or do not; the rear spar
sits in a thinner, more sharply changing region, so the question is whether a
straight rod fits at all.

### F3 — Bore and telescoping 🟢

```
_bore_for(od):
    erf_W = required_section_modulus_from_od(od) = od³ / 10     # rod inverse
    Di    = (od⁴ − 32 · erf_W · od / π) ^ (1/4)                 # tube inverse

    if strength wants a solid section (no real Di):
        bore = wall_factor · od,   wall_factor = 0.6

telescope_clearance_mm = 0.5      # RADIAL slip-fit gap between nested tubes
```

The bore is reconstructed from the **governing OD** rather than carried through
from the sizing stage — that is why `required_section_modulus_from_od` exists as
its own inverse. 🟡 It means a piece's bore is consistent with its own OD even
when the OD was rounded up to a stock size upstream.

### F4 — Stage 5, the commit 🟢

```
spar_insert_service:

  is this edit DESTRUCTIVE?   (a segment split, or a spare REPLACE)
      │
      ├── yes ──►  snapshot(label = "Before spar insert", immutable)   (l.485-497)
      │              │
      │              ├── snapshot FAILED ──►  ABORT the whole commit
      │              │                         "never mutate without a
      │              │                          recovery point"  (gh-1058)
      │              └── ok ──► carry the snapshot id into SparInsertResponse
      │
      └── no ───►  proceed without a snapshot

  write each solved spar onto wing_xsec_spares:
      spare_mode    = "normal"
      spare_origin  = explicit 3-component vector
      spare_vector  = explicit 3-component unit direction
      (millimetres — the gh-402 storage exception)

  db.flush()   # get_db() owns the commit (ADR 0009)
```

### F5 — Why the commit shape is load-bearing 🟢

```
next model → config conversion:

  _resolve_spare_vectors_and_origins
      normally CLEARS and RECOMPUTES every spar's origin/vector
      (the gh-352 / gh-362 unit-leak guard)

  should_preserve_normal_spare exempts a spar that is
      spare_mode == "normal"
      AND a fully explicit 3-component spare_origin
      AND a spare_vector
      (spare_origin_preservation.py:43-59, gh-1053)
```

A solved front/rear couple has two **distinct** origins by construction. If the
commit wrote them as `standard` (or left the origin partial), the next read would
recompute both onto the default quarter-chord station — silently collapsing the
solver's output into a single spar position. The commit shape in F4 is therefore
not a style choice; it is what keeps the result alive. 🟡 The predicate is
confirmed; that the insert service is the producer of qualifying rows is the
necessary consequence rather than a line that was read.

### F6 — Two different recovery mechanisms 🟢/🟡

```
FAILURE  during the request   →  get_db() rolls back        (ADR 0009)
REGRET   after a good commit  →  the "Before spar insert" snapshot (ADR 0006)
```

They cover disjoint cases, which is why both exist. The snapshot is *immutable*
so it cannot itself be edited away, and its id is returned so the UI can offer a
one-click revert without the user having to find it in the version DAG.

## Alternative Flows

- **One rod carries the whole half:** a single piece, no telescoping. 🟢
- **Required OD exceeds the band:** the piece is still emitted, with
  `feasible = false` and `utilisation > 1.0`; the message names the governing
  station and suggests a capped or box spar. 🟢 No clamping (ADR 0012).
- **Tip below the 1 mm floor:** no piece; the region is reported through
  `front_no_spar_from_y` / `rear_no_spar_from_y`. 🟢
- **Single-half surface:** the front joint is forced `"continuous"`
  (gh-1091). 🟢
- **Roots offset by more than 5 mm:** `"reinforcement+joiner"` plus a generated
  reinforcement piece. 🟢
- **A straight rear rod leaves the band:** `"bent-pin"`. 🟢
- **Strength wants a solid:** the bore falls back to `0.6 × od`. 🟢
- **Non-destructive commit:** no snapshot is taken. 🟢
- **Snapshot creation fails on a destructive commit:** the whole commit is
  aborted, nothing is mutated. 🟢
- **A later step in the request raises:** the request-scoped session rolls the
  spar writes back (ADR 0009). 🟡

## Dependencies

- **[`../../wing-design/spar-sizing/`](../../wing-design/spar-sizing/design.md)** —
  Stages 1, 2 and 4: the strength law, `solve_dimension`, station sampling
  (`_ROOT_EPS`), the rear-spar hinge clearance and the `SectionGeometry` seam.
  This use case consumes their output and adds nothing to the formulas.
- **`wing-design/cross-section-crud`** — the `wing_xsec_spares` rows the commit
  writes, and the millimetre storage exception (gh-402).
- **`app/converters/spare_origin_preservation.py`** — the predicate that decides
  whether the commit survives the next read.
- **`versioning`** — the immutable snapshot (ADR 0006); this is its only
  non-copilot automated caller.
- **`aero-analysis`** — supplies the moment distribution the plan is sized
  against (consumed via the sizing stage, not called from here).
- **`app/db/session.py` `get_db()`** — owns the transaction boundary (ADR 0009).
- **Not** CadQuery: the layout logic is deliberately kernel-free
  (`spar_solver.py:1-24`).

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| The layout is expressed as straight pieces with telescoping runs, not as a continuous taper | `plan_spar` / `solve_spar_plan` (l.342, 619-672) | 🟢 |
| The front joint is decided geometrically (root collinearity, 5 mm), the rear joint by feasibility (a through-rod test) | `_inboard_collinear`; the rear-joint branch | 🟢 |
| A single-half surface is special-cased rather than allowed to index an empty half | gh-1091 | 🟢 |
| Utilisation may exceed 1.0 and is reported, never clamped | `_piece_from_run_with_od` (l.490-529), ADR 0012 | 🟢 |
| A negligible-load tip yields no piece rather than a degenerate tube | `NEGLIGIBLE_OD_FLOOR_MM = 1.0` (gh-1076) | 🟢 |
| The bore is reconstructed from the governing OD via its own inverse | `_bore_for` (l.460-487) | 🟢 |
| A `0.6` wall factor is the fallback when strength wants a solid | l.460-487 | 🟢 |
| The decision logic carries no CAD dependency so it is fast-tier testable | `spar_solver.py:1-24` | 🟢 |
| Solved spars are written as explicit `normal` spars so the preservation predicate exempts them | gh-1053; `spare_origin_preservation.py:43-59` | 🟢 / 🟡 coupling |
| A destructive spar edit snapshots first and fails closed | `spar_insert_service.py:485-497` (gh-1058) | 🟢 |
| The snapshot is immutable and its id is returned for one-click revert | same | 🟢 |
| Rollback and snapshot cover disjoint cases (failure vs regret) | ADR 0009 + ADR 0006 | 🟡 |

## Internal State

This use case holds no state of its own. It reads stations and writes two kinds
of persistent state:

| State | Owner | Written by this use case |
|---|---|---|
| `wing_xsec_spares` rows (mm, gh-402) | `wing-design` | yes — as explicit `normal` spars |
| an immutable version node labelled `"Before spar insert"` | `versioning` | yes — before destructive edits only |

The plan result itself is **derived, not persisted**: it is computed, returned
and (on commit) projected onto the spar rows. There is no `spar_plans` table.
🟡 A consequence: a plan a user looked at cannot be re-displayed later without
re-solving, and nothing records which plan version produced the committed spars.

## Observability

- The infeasibility message is the primary output signal and is written for a
  human builder: it names the governing station and suggests a capped or box
  spar. 🟢
- The `*_no_spar_from_y` fields make "no spar here" explicit rather than
  inferable from a missing piece. 🟢
- The returned snapshot id makes the recovery point discoverable from the
  response rather than only from the version list. 🟢
- 🔴 **No record of which plan produced the committed spars.** After a commit,
  the spar rows carry geometry but no provenance — not the parameters, not the
  moment distribution, not a plan id.
- 🔴 **No metric on feasibility.** How often a designed wing comes back
  infeasible is not counted anywhere, so the practical usefulness of the default
  parameters is unmeasurable.

## Risks and Gaps

- 🔴 **The plan is not persisted.** There is no `spar_plans` table, so a
  committed spar cannot be traced back to the inputs that produced it, and a
  re-solve after a geometry change silently supersedes the old answer with
  nothing to diff against.
- 🟡 **The commit ↔ preservation coupling is implicit.** `spar_insert_service`
  must keep writing `spare_mode == "normal"` with fully explicit origin and
  vector, or `should_preserve_normal_spare` stops exempting the rows and the
  next read destroys them (gh-1053). Nothing asserts this at the boundary — a
  test on the predicate alone would not catch a change in the writer.
- 🟡 **`SparPlanResult`'s full field set was not read.** Only
  `front_no_spar_from_y` / `rear_no_spar_from_y` are confirmed by name (from the
  gh-1076 test mocks); the remaining field names are inferred from behaviour.
- 🟡 **The snapshot is scoped to "destructive" edits**, and what counts as
  destructive (segment split, spare `REPLACE`) is a list in code rather than a
  derived property. A future destructive edit type would silently miss the
  guard.
- 🟡 **Stock sizes are not modelled.** The plan emits computed diameters; a
  builder buys tube in discrete sizes, and nothing in the result rounds to or
  reports against a stock list.
- 🟡 **The front-joint tolerance is a bare 5 mm constant**, not derived from the
  section thickness or the tube diameter, so its appropriateness varies with
  aircraft size.
