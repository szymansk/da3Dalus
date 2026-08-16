# spar-sizing — Implementation Tasks

> Executable sequence to re-implement this use case from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.
> Parent module tasks: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] A `Component` catalogue with a `material` type carrying
      `allowable_bending_stress_mpa`, addressable by `material_id`.
- [ ] `wing_xsec_spares` table available (module `wing-design`, use case
      [`cross-section-crud`](../cross-section-crud/tasks.md) T-04) —
      **millimetres**, gh-402.
- [ ] `cad_designer` topology package importable for the section-geometry seam
      (**read-only**, ADR 0002). The geometry kernel (`cadquery`) is
      **optional**: the solver must not import it (ADR 0017).
- [ ] A bending-moment source providing `moment_fn(y_span) -> N·m`
      (→ `aero-analysis`), carrying **un-factored** aerodynamic bending moment.
      🟢 Settled (`Q-WD-8`): the producer is `app/services/spanwise_loads.py` and
      it emits `M(y)` **before** `g_limit` and `j`, which are applied exactly
      once downstream at `spar_solver.py:730`. There is no double application and
      no ~4.5× oversizing. This contract must be asserted by a test, because a
      producer that started pre-factoring would silently oversize every spar.
- [ ] The gh-1053 spar-preservation predicate
      (`should_preserve_normal_spare`) in place, otherwise the solved plan is
      destroyed on the next read.

## Tasks

- [ ] **T-01 — Shape section moduli.**
  Implement the four forward formulas, in **mm³**:

  ```
  rectangular   W = b · h² / 6
  capped (I/C)  W = b · (H³ − h³) / (6 · H)
  solid rod     W = d³ / 10
  tube          W = π · (Da⁴ − Di⁴) / (32 · Da)
  ```

  - Legacy origin: `app/services/spar_sizing.py:40-70`
  - Definition of done: each formula is checked against a hand-computed value;
    a rod of Ø10 mm yields `W = 100 mm³`.
  - Confidence: 🟢

- [ ] **T-02 — `required_section_modulus` with the `σ_allow` guard.**

  ```
  M_design = |M| · g_limit · j
  erf_W    = M_design · 1000 / σ_allow          # 1000 = N·m → N·mm
  ```

  Raise `ValueError` when `σ_allow ≤ 0` **before** dividing — the material
  schema permits `0`.
  - Legacy origin: `app/services/spar_sizing.py:78-88`, guard at `:86-87`
  - Definition of done: `M = 40 N·m`, `σ = 300 MPa`, `g = 3.0`, `j = 1.5` yields
    `erf_W = 600 mm³`; `σ_allow = 0` and `σ_allow = -1` both raise `ValueError`
    and never reach a division.
  - Confidence: 🟢

- [ ] **T-03 — `solve_dimension`, the four closed-form inverses.**

  ```
  tube          Di = (Da⁴ − 32 · erf_W · Da / π) ^ (1/4)
  rod           d  = (10 · erf_W) ^ (1/3)
  rectangular   b  = 6 · erf_W / h²
  capped        h  = (H³ − 6 · H · erf_W / b) ^ (1/3)
  ```

  - Legacy origin: `app/services/spar_sizing.py:96+`, `:137-146`, `:159`,
    `:182`, `:196-208`
  - Definition of done: for each shape, `solve_dimension` inverted through the
    matching T-01 modulus returns the original `erf_W` to floating-point
    tolerance (round-trip property test).
  - Confidence: 🟢

- [ ] **T-04 — `_TC_FALLBACK` thickness-ratio fallback.**
  Use `0.12` when airfoil thickness data is unavailable, rather than failing.
  - Legacy origin: `app/services/spar_sizing.py:32`
  - Definition of done: sizing a station with no resolvable airfoil returns a
    dimension computed from `t/c = 0.12`, with no exception.
  - Confidence: 🟢

- [ ] **T-05 — `SparSizingParams` schema.**
  `shape ∈ {tube, rod, rectangular, capped}` (required),
  `safety_factor_j = 1.5` (`> 0`), `packing_factor = 0.8` (`0 < x ≤ 1`),
  `cap_width_mm` **required only when** `shape == "capped"`, `material_id`
  pointing at a `Component` of type `material`.
  - Legacy origin: `app/schemas/spar_sizing.py:12-51`
  - Definition of done: `shape="capped"` without `cap_width_mm` → 422;
    `packing_factor = 0` and `= 1.1` → 422; `packing_factor = 1.0` → accepted.
  - Confidence: 🟢

- [ ] **T-06 — `StationData` value object and `build_stations_from_geometry`.**

  ```
  y_spans = linspace(0, 1, n_span);  y_spans[0] → _ROOT_EPS = 1e-3
  x_c         = requested x/c, else the section's max-thickness location
  clr         = (1 − packing_factor) / 2 · thickness
  band_lo     = bottom_z + clr
  band_hi     = top_z    − clr
  M_design    = |moment_fn(y_span)| · g_limit · j        # defaults g=3.0, j=1.5
  required_od = solve_dimension("rod", erf_W, outer = band_hi − band_lo)
  ```

  Note the **required OD is always solved as a rod**, whatever `shape` was
  requested; the shape re-enters at T-11.
  - Legacy origin: `cad_designer/airplane/geometry/spar_solver.py:681-746`;
    `_ROOT_EPS` (gh-1037 #4)
  - Definition of done: `n_span = 6` yields 6 stations with
    `y_spans[0] == 1e-3`; `band_hi − band_lo == packing_factor × thickness`.
  - Confidence: 🟢

- [ ] **T-07 — `rear_spar_x_c_with_clearance` (gh-1059).**

  ```
  if hinge_x_c is None: return requested
  return max( min(requested, hinge_x_c − 0.03), 0.05 )
  ```

  `_REAR_CLEARANCE_FRACTION = 0.03`, `_MIN_REAR_X_C = 0.05`. Applies to
  **computed** spars only — a manually placed reinforcing spar inside a control
  surface stays legal.
  - Legacy origin: `cad_designer/airplane/geometry/spar_solver.py:181-221`
  - Definition of done: `(0.80, 0.72) → 0.69`; `(0.80, None) → 0.80`;
    `(0.80, 0.06) → 0.05`; `(0.40, 0.72) → 0.40` (the `min` does not raise a
    forward spar).
  - Confidence: 🟢

- [ ] **T-08 — `_piece_from_run_with_od`: utilisation and feasibility.**

  ```
  utilisation = od / max(tightest_band, 1e-6)
  feasible    = od ≤ tightest_band
  ```

  On infeasibility, produce a message naming the **governing station** and
  suggesting a capped or box spar. **Never clamp the dimension.**
  - Legacy origin: `cad_designer/airplane/geometry/spar_solver.py:490-529`
    (ADR 0012)
  - Definition of done: an over-loaded root returns `feasible = false`,
    `utilisation > 1.0`, a message containing the station identifier, and an
    `od` equal to the strength-required value — a test asserts the returned `od`
    was **not** reduced to the band.
  - Confidence: 🟢

- [ ] **T-09 — Negligible-load tip (gh-1076).**
  `NEGLIGIBLE_OD_FLOOR_MM = 1.0`. A station whose required OD falls below 1 mm
  produces **no piece**; the region is reported via `front_no_spar_from_y` /
  `rear_no_spar_from_y`.
  - Legacy origin: `cad_designer/airplane/geometry/spar_solver.py:44-53,
    438-457`
  - Definition of done: a tip with `required_od = 0.4` emits no piece and sets
    `front_no_spar_from_y` to the y where the spar stops; no Ø≈0 tube appears in
    the plan.
  - Confidence: 🟢

- [ ] **T-10 — Telescoping run split.**
  Greedy straight-piece fit per half-span, split into telescoping runs wherever
  the strength-required OD exceeds the containment band.
  - Legacy origin: `cad_designer/airplane/geometry/spar_solver.py:342`
    (`plan_spar`)
  - Definition of done: a wing whose required OD crosses the band mid-span
    yields ≥ 2 runs with decreasing OD outboard.
  - Confidence: 🟡 — the split rule is confirmed as "where OD exceeds the band";
    the exact greedy piece-length policy was not captured in the source
    analysis.

- [ ] **T-11 — `_bore_for`: bore reconstruction.**

  ```
  required_section_modulus_from_od(od) = od³ / 10
  Di = (od⁴ − 32 · erf_W · od / π) ^ (1/4)
  fallback when strength wants a solid:  bore = 0.6 · od     # wall_factor
  telescope_clearance_mm = 0.5                                # radial slip fit
  ```

  - Legacy origin: `cad_designer/airplane/geometry/spar_solver.py:460-487`
  - Definition of done: a lightly loaded station returns the tube inverse; a
    station whose strength demands a solid returns `0.6 × od`; nested runs are
    separated by 0.5 mm radially.
  - Confidence: 🟢

- [ ] **T-12 — `_inboard_collinear` and the front joint.**
  Compare the two halves' root `center_z` within `tol_mm = 5.0`:
  equal → `"continuous"`; otherwise `"reinforcement+joiner"` plus a generated
  reinforcement piece. A **single-half** surface is forced to `"continuous"` and
  must never index into the empty half (gh-1091).
  - Legacy origin: `cad_designer/airplane/geometry/spar_solver.py`
    (`_inboard_collinear`); gh-1091
  - Definition of done: a 2 mm offset → `"continuous"`; a 20 mm offset →
    `"reinforcement+joiner"` with a reinforcement piece; a vertical stabiliser
    (one half) → `"continuous"` and no `IndexError`.
  - Confidence: 🟢

- [ ] **T-13 — Rear joint decision.**
  `"continuous"` when a straight collinear rod through `y = 0` stays inside the
  band on both halves, otherwise `"bent-pin"`.
  - Legacy origin: `cad_designer/airplane/geometry/spar_solver.py:619-672`
    (`solve_spar_plan`)
  - Definition of done: a flat-bottomed wing → `"continuous"`; a dihedral wing
    whose collinear rod exits the band → `"bent-pin"`.
  - Confidence: 🟢

- [ ] **T-14 — `solve_spar_plan` orchestration.**
  Drive both spars (front and rear) over both halves, apply T-07 to the rear
  spar, assemble pieces, joints, bores, utilisation, feasibility and the
  `*_no_spar_from_y` markers into the plan result.
  - Legacy origin: `cad_designer/airplane/geometry/spar_solver.py:619-672`
  - Definition of done: a full plan for a two-half wing contains front and rear
    piece lists, both joint types, per-piece utilisation, an overall `feasible`
    flag, and the negligible-load markers where applicable.
  - Confidence: 🟢

- [ ] **T-15 — Keep the solver CAD-free.**
  No `cadquery` (or other geometry-kernel) import anywhere in the solver module;
  all geometry arrives as `StationData`.
  - Legacy origin: `cad_designer/airplane/geometry/spar_solver.py:1-24`
  - Definition of done: a CI guard test asserts the module imports successfully
    in an environment with no geometry kernel installed, and the full solver
    suite runs on the fast tier.
  - Confidence: 🟢

- [ ] **T-16 — `SectionGeometry` seam (gh-1046).**
  `mode="analytic"` (default) blends segment airfoils via
  `WingConfiguration.get_points_on_surface` and builds **no solid**;
  `mode="solid"` builds the RIGHT-half loft once via `WingLoftCreator` and
  slices it, with `sample` grouping requests by `y_span` so each plane is cut
  once. Clamp `points_per_edge` to `[8, 4096]`. Raise
  `SectionGeometryUnavailableError` when CadQuery is absent.
  - Legacy origin: `cad_designer/airplane/geometry/section_geometry.py:160-219`,
    guard at `:181-184`
  - Definition of done: analytic sampling returns points with no kernel present;
    `points_per_edge = 5` becomes 8 and `= 10000` becomes 4096; solid mode
    without CadQuery raises the named error; a solid-mode `sample` of 10 points
    across 3 distinct `y_span` values cuts exactly 3 planes.
  - Confidence: 🟢

- [ ] **T-17 — `spar_plan_service` orchestration.**
  Resolve the wing, build stations (T-06), resolve the material and hinge, run
  `solve_spar_plan`, and return the plan.
  - Legacy origin: `app/services/spar_plan_service.py`
  - Definition of done: an end-to-end plan request on a seeded wing returns a
    complete plan; an unknown `material_id` → 404/422 per the module error
    contract.
  - Confidence: 🟡 — the file's role is confirmed; its exact signature was not
    captured in the source analysis.

- [ ] **T-18 — `spar_insert_service` persistence.**
  Write the solved geometry onto `wing_xsec_spares` with
  `spare_mode = "normal"` plus a fully explicit 3-component `spare_origin` and
  `spare_vector`, so `should_preserve_normal_spare` exempts the rows from the
  clear-and-recompute path on the next read (gh-1053).
  - Legacy origin: `app/services/spar_insert_service.py`;
    `app/converters/spare_origin_preservation.py:43-59`
  - Definition of done: after a solve, a read-back of the wing returns the
    solved front/rear origins unchanged — a regression test that fails if any of
    the three preservation conditions is not written.
  - Confidence: 🟡 — the preservation predicate is 🟢; that the insert service
    is what produces qualifying rows is the necessary consequence.

## Test Tasks

- [ ] **TT-01 — Happy path:** size a rod from `M = 40 N·m`, `σ = 300 MPa`,
      `g = 3.0`, `j = 1.5` and assert `erf_W = 600 mm³` and
      `d = (10 · 600)^(1/3)` (see [`requirements.md`](requirements.md)
      Acceptance Criteria).
- [ ] **TT-02 — Failure:** `σ_allow = 0` and `σ_allow < 0` raise `ValueError`
      for **every** shape, and no division is attempted.
- [ ] **TT-03 — Inverse round-trip property:** for each of the four shapes,
      `modulus(solve_dimension(erf_W)) == erf_W` to tolerance, over a swept
      range of `erf_W`.
- [ ] **TT-04 — Root nudge:** `y_spans[0] == 1e-3`; a companion test asserts
      that sampling at exactly `0.0` would yield a zero-thickness band (pins
      *why* the nudge exists).
- [ ] **TT-05 — Band derivation:** `band_hi − band_lo == packing_factor ×
      thickness` for `packing_factor ∈ {0.6, 0.8, 1.0}`.
- [ ] **TT-06 — Hinge-clearance table:** `(0.80, 0.72) → 0.69`,
      `(0.80, None) → 0.80`, `(0.80, 0.06) → 0.05`, `(0.40, 0.72) → 0.40`.
- [ ] **TT-07 — Infeasibility is honest:** an over-loaded root returns
      `feasible = false`, `utilisation > 1.0`, a message naming the governing
      station, **and an unreduced `od`** (the anti-clamping assertion).
- [ ] **TT-08 — Utilisation guard:** `tightest_band = 0` does not divide by
      zero (`max(tightest_band, 1e-6)`).
- [ ] **TT-09 — Negligible tip:** `required_od = 0.4` emits no piece and sets
      `front_no_spar_from_y`; `required_od = 1.5` does emit a piece.
- [ ] **TT-10 — Front-joint matrix:** 2 mm offset → continuous; 20 mm offset →
      reinforcement+joiner with a piece; single half → continuous, no
      `IndexError`.
- [ ] **TT-11 — Rear-joint matrix:** collinear-in-band → continuous;
      out-of-band → bent-pin.
- [ ] **TT-12 — Bore matrix:** tube inverse for a lightly loaded station;
      `0.6 × od` fallback when strength wants a solid; 0.5 mm radial clearance
      between nested runs.
- [ ] **TT-13 — `t/c` fallback:** no airfoil data → `0.12` used, no exception.
- [ ] **TT-14 — `SparSizingParams` validation:** `capped` without
      `cap_width_mm` → 422; `packing_factor` out of `(0, 1]` → 422; unknown
      `shape` → 422.
- [ ] **TT-15 — CAD-free guard:** the solver module imports and its full suite
      passes with no geometry kernel installed (fast tier).
- [ ] **TT-16 — Section-geometry modes:** analytic needs no kernel; solid without
      CadQuery raises `SectionGeometryUnavailableError`; `points_per_edge` is
      clamped at both ends; solid `sample` cuts one plane per distinct `y_span`.
- [ ] **TT-17 — Preservation round-trip:** a solved plan persisted by T-18
      survives a model→config→model read-back with its origins intact.

## Data Migration Tasks

- [ ] **TM-01 — Re-solve plans produced before gh-1076.** Pre-gh-1076 plans may
      contain degenerate Ø≈0 tip tubes instead of a `*_no_spar_from_y` marker.
      Identify stored spars with an OD below `NEGLIGIBLE_OD_FLOOR_MM = 1.0` and
      re-solve. 🟡
- [ ] **TM-02 — Re-solve plans produced before gh-1059.** A computed rear spar
      stored before the hinge-clearance guard may overlap a control surface.
      Flag any rear spar whose `x/c` exceeds `hinge_x_c − 0.03` on a segment
      carrying a trailing-edge device. 🟡
- [x] **TM-03 — Solved spars all satisfy the preservation predicate.** 🟢
      **Measured 2026-08-15** (`Q-WD-7 ②`): of 11 `normal`-mode spars, **0** lack
      an explicit `spare_origin` or `spare_vector`, so none fails
      `should_preserve_normal_spare` and no origin is being recomputed away on
      read. No remediation needed; re-run if data is imported from elsewhere.

## Suggested Order

1. **T-01 → T-04** first, in that order: they are pure functions with no
   dependencies, and T-03 cannot be verified without T-01 (the round-trip test
   is the real specification of the inverses).
2. **T-05** next — the parameter schema gates every later entry point, and
   `packing_factor` is consumed by T-06.
3. **T-06 → T-07**: station sampling and the hinge guard. T-06 blocks on T-02
   and T-03 (it calls `solve_dimension`), and on a `moment_fn` stub.
4. **T-08 → T-13**: the solver's decision logic. T-08 blocks on T-06 (it needs
   the band); T-09 and T-11 block on T-08; T-12 and T-13 are independent of each
   other and can proceed in parallel. **Build all of these with hand-built
   `StationData`** — that is what keeps T-15 achievable.
5. **T-14** once T-08…T-13 are green — it is pure orchestration and should add
   no new decision logic.
6. **T-15** as a standing CI guard, added as soon as T-08 exists so the CAD-free
   property cannot regress while the solver is still being written.
7. **T-16** independently of the solver (it is the seam, not the logic); it
   blocks T-17 because real station data comes through it.
8. **T-17 → T-18** last: orchestration and persistence. T-18 blocks on the
   `cross-section-crud` preservation predicate existing, otherwise the very
   first read undoes the work.

## Pending Gaps (🔴)

- **`ValueError` is not a domain exception.** `required_section_modulus` raises a
  bare `ValueError` on `σ_allow ≤ 0` (`spar_sizing.py:86-87`). Does a
  translation layer map it to a 422, or does it surface as a 500?
- **The `_MIN_REAR_X_C` floor can silently defeat the clearance.** When
  `hinge_x_c − 0.03 < 0.05`, the floor wins and the computed rear spar sits
  inside the control surface with no warning. Per ADR 0012 this looks like it
  should be a design warning — is the current silence intentional?
- **`moment_fn` provenance and factor ownership.** Which service produces the
  bending-moment distribution, at which load case, and does it already apply
  `g_limit` / `j`? A double application would be silent and would oversize every
  spar by 4.5×.
- **`packing_factor` may be applied twice.** It scales `outer(y)` in the sizing
  formula (`spar_sizing.py:13`) *and* derives the containment band during
  station sampling. Are these the same knob applied once conceptually, or is
  there a double reduction?
- **Rod-equivalent OD is conservative, not exact.** Every station's
  `required_od` is solved as a rod regardless of the requested shape. For capped
  and rectangular spars the band check is therefore conservative — is that the
  intent, or should the check use the requested shape's actual height?
- **Telescoping piece-length policy is unspecified.** The split rule ("where OD
  exceeds the band") is confirmed, but the greedy piece-length policy and any
  minimum overlap length were not captured.
- **The `"solid"` path is uninstrumented.** The ~13 s cost is a docstring claim
  with no timing signal, so a regression onto the slow path would be invisible.
- **TM-03 may already be silently active.** If solved spars predating gh-1053
  do not satisfy the preservation predicate, their origins are being recomputed
  away on every read today. Has this been audited?
