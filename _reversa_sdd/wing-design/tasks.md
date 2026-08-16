# wing-design — Implementation Tasks

> Executable sequence to re-implement the module from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.
> Slice-level task lists: [`cross-section-crud/tasks.md`](cross-section-crud/tasks.md),
> [`spar-sizing/tasks.md`](spar-sizing/tasks.md),
> [`control-surface-mixing/tasks.md`](control-surface-mixing/tasks.md),
> [`turbulator-optimizer/tasks.md`](turbulator-optimizer/tasks.md).

## Prerequisites

- [ ] `aeroplane-core` available — every route resolves an aeroplane by UUID
      before touching a wing, and wing create/delete call back into
      `component_tree_service` for the group auto-sync (gh#108).
- [ ] `get_db()` request-scoped session owning the transaction
      (`app/db/session.py:55-64`, ADR 0009). Services never `commit()`.
- [ ] `app/core/exceptions.py` hierarchy plus the `_raise_http_from_domain`
      mapping (`aeroplane/base.py:52-67`).
- [ ] `app/converters/model_schema_converters.py` — the shared conversion hub.
- [ ] `cad_designer` topology package (`WingConfiguration`, `WingSegment`,
      `Spare`, `TrailingEdgeDevice`, `Turbulator`, `Airfoil`), millimetre world,
      treated as read-only (ADR 0002).
- [ ] `AIRFOILS_DIR` populated — station `airfoil` values resolve to `.dat`
      files (`app/core/config.py:6-14`).
- [ ] `components` catalogue with `material` entries carrying
      `allowable_bending_stress_mpa` (spar sizing) and servo parts.
- [ ] CadQuery **optionally** present. Absent (e.g. `linux/aarch64`) the module
      must still serve CRUD; only the spar-vector recompute and `"solid"`
      section sampling degrade (ADR 0017).

## Tasks

### Topology and persistence

- [ ] **T-01 — The six wing tables.**
  `wings` (`name`, `symmetric` default **`True`**, `design_model`,
  `aeroplane_id` FK `ON DELETE CASCADE`); `wing_xsecs` (`xyz_le` JSON metres,
  `chord` m, `twist` deg, `dihedral` deg nullable, `airfoil`, `sort_index`);
  `wing_xsec_details` (1:1, **unique** FK, `x_sec_type`, `tip_type`,
  `number_interpolation_points`); `wing_xsec_spares`; 
  `wing_xsec_trailing_edge_devices` (1:1 unique FK); `wing_xsec_ted_servos`
  (1:1 unique FK); `wing_xsec_turbulators` (1:1 unique FK). All children
  `cascade="all, delete-orphan"`.
  - Legacy origin: `app/models/aeroplanemodel.py:83, 99, 129, 147, 190, 214, 279`;
    data-dictionary §Module: wing-design
  - Definition of done: deleting a wing removes every descendant row; the
    1:1 side tables reject a second row for the same parent at the DB level.
  - Confidence: 🟢

- [ ] **T-02 — `wing_xsec_spares` stores millimetres.**
  `spare_support_dimension_width`, `spare_support_dimension_height`,
  `spare_length`, `spare_start`, `spare_origin` are **mm** inside the otherwise
  metre database; `spare_vector` is a dimensionless unit direction.
  - Legacy origin: gh-402; data-dictionary §Table `wing_xsec_spares`
  - Definition of done: a spar posted with `spare_length = 0.25` m has DB value
    `250.0`, and the GET returns `0.25`.
  - Confidence: 🟢

- [ ] **T-03 — Read-through station properties.**
  `WingXSecModel` delegates `x_sec_type`, `tip_type`,
  `number_interpolation_points`, `spare_list`, `trailing_edge_device`,
  `turbulator` to its `detail` row, and exposes a computed `control_surface`
  projection.
  - Legacy origin: `app/models/aeroplanemodel.py:241-276`
  - Definition of done: a station with no `detail` row returns `None` for every
    delegated property instead of raising.
  - Confidence: 🟢

- [ ] **T-04 — `WingXSecTrailingEdgeDeviceModel.servo` union property.**
  Returns `servo_data` when the 1:1 row exists, else the integer `servo_index`.
  - Legacy origin: `app/models/aeroplanemodel.py:183-187`
  - Definition of done: both shapes round-trip through the schema as
    `Servo | int`.
  - Confidence: 🟢 (which form is canonical for new records: 🔴)

### The terminal-station rule (BR-5)

- [ ] **T-05 — Layer 1, schema.**
  `AsbWingSchema.validate_last_xsec_has_no_segment_details` raises when any of
  the six segment fields is present on the last x-section; `x_secs` carries
  `min_length=2`.
  - Legacy origin: `app/schemas/aeroplaneschema.py:666-680`
  - Definition of done: a payload with `spare_list` on the terminal station is
    rejected at validation time (→ 422); a 1-station wing is rejected.
  - Confidence: 🟢

- [ ] **T-06 — Layer 2, model.**
  `WingModel.from_dict` blanks all six segment fields when
  `index == len(xsec_dicts) - 1`.
  - Legacy origin: `app/models/aeroplanemodel.py:489-490`
  - Definition of done: constructing a model from a dict that violates the rule
    yields a terminal station with all six fields `None` — no exception.
  - Confidence: 🟢

- [ ] **T-07 — Layer 3, service.**
  `_assert_non_terminal_xsec_or_raise` raises `ValidationError` for any write
  targeting the terminal index.
  - Legacy origin: `app/services/wing_service.py:151-156`
  - Definition of done: `PUT .../cross_sections/{last}` with a `spare_list`
    returns 422 with `error.code == "validation_error"`.
  - Confidence: 🟢

### Unit boundary

- [ ] **T-08 — `_convert_spare_to_meters` / `_convert_spare_to_mm`.**
  Exactly five dimensional fields converted with `_MM_TO_M = 0.001` and
  `_M_TO_MM = 1000.0`; `spare_vector` untouched.
  - Legacy origin: `wing_service.py:43, 46, 49-66, 69-88`
  - Definition of done: a property-based round-trip
    (`to_mm ∘ to_meters == identity` within float tolerance) passes, and a test
    asserts `spare_vector` is bit-identical across both directions.
  - Confidence: 🟢

- [ ] **T-09 — `scale_db_origin_to_config`.**
  `factor = 0.001 × scale`, so `scale = 1.0` yields metres and `scale = 1000.0`
  returns the stored millimetres verbatim.
  - Legacy origin: `app/converters/spare_origin_preservation.py:62-78`
  - Definition of done: both scales are covered by unit tests with a
    non-symmetric origin vector.
  - Confidence: 🟢

- [ ] **T-10 — `_scale_asb_wing_geometry_schema`.**
  Multiply `xyz_le` and `chord` by `scale`; leave angles alone.
  - Legacy origin: `model_schema_converters.py:452-470`
  - Definition of done: `twist` and `dihedral` are unchanged at any scale.
  - Confidence: 🟢

- [ ] **T-11 — `should_preserve_normal_spare` (gh-1053).**
  Exempt from the clear-and-recompute path exactly those spars that are
  `spare_mode == "normal"` **and** carry a fully explicit 3-component
  `spare_origin` **and** a `spare_vector`. Everything else
  (`standard`, `follow`, `standard_backward`, `orthogonal_backward`) is
  recomputed.
  - Legacy origin: `app/converters/spare_origin_preservation.py:43-59`
  - Definition of done: a solver-produced front/rear couple keeps two distinct
    origins after a model→config→model round-trip; a `standard` spar has its
    origin recomputed to the default station.
  - Confidence: 🟢

- [ ] **T-12 — `_recompute_spare_vectors` with graceful degradation.**
  Rebuild a `WingConfiguration` at `scale = 1.0`, read back each segment's
  computed `spare_vector` / `spare_origin`, write the origin back **× 1000** as
  mm. Catch `ImportError` and `FileNotFoundError`, log a warning, continue.
  - Legacy origin: `wing_service.py:854-873`
  - Definition of done: with CadQuery patched to raise `ImportError`, wing CRUD
    still returns 200 and a warning is logged.
  - Confidence: 🟢

- [ ] **T-13 — `_sync_spares_for_xsec`.**
  Write solved spar geometry back to the DB as metres × 1000.
  - Legacy origin: `wing_service.py:851`
  - Definition of done: after a spar solve, the stored `spare_origin` is in mm
    and the API still reports metres.
  - Confidence: 🟢

### Wing lifecycle and conversion

- [ ] **T-14 — `create_wing` (ASB path).**
  Stamp `design_model = 'asb'`; duplicate name → `ValidationError` (**422**).
  - Legacy origin: `wing_service.py:285-300`
  - Definition of done: a second wing with the same name under the same
    aeroplane returns 422; the round-trip read reproduces the stations.
  - Confidence: 🟢 (the 422-vs-409 divergence with fuselages: 🔴)

- [ ] **T-15 — `create_wing_from_wing_configuration` (mm → m).**
  `scale = 0.001`; stamp `design_model = 'wc'`.
  - Legacy origin: `wing_service.py:313, 341`
  - Definition of done: a payload chord of `250.0` mm is stored as `0.25` m and
    `design_model == 'wc'`.
  - Confidence: 🟢

- [ ] **T-16 — `get_wing_as_wingconfig` (m → mm).**
  `wing_model_to_wing_config(wing, scale=1000.0)`.
  - Legacy origin: `wing_service.py:372`
  - Definition of done: the emitted `WingConfiguration` re-imports through T-15
    to a byte-identical model.
  - Confidence: 🟢

- [ ] **T-17 — `_build_segment_details` and the ASB index offset (BR-W1).**
  ASB emits N+1 x-secs for N segments and `x_sec[i]`'s control surface belongs to
  segment *i−1*, so the x-sec-derived control surface must be **overwritten** by
  the segment's own TED-derived one.
  - Legacy origin: `model_schema_converters.py:960-995`
  - Definition of done: a wing with a TED on segment 0 only does **not** grow a
    phantom TED on segment 1 after a round-trip through
    `_merge_ted_with_control_surface`.
  - Confidence: 🟢

- [ ] **T-18 — `_station_dihedral` (gh-951).**
  `station i airfoil = segments[i].root_airfoil` for `i < N`;
  `station N airfoil = segments[-1].tip_airfoil`;
  `dihedral = airfoil.dihedral_as_rotation_in_degrees`. `NULL` on legacy rows
  means "derive from geometry".
  - Legacy origin: `model_schema_converters.py:998-1015`;
    `aeroplanemodel.py:219-225`
  - Definition of done: a terminal dihedral of 5.0° survives a write→read cycle
    even though `xyz_le` is unchanged by it.
  - Confidence: 🟢

- [ ] **T-19 — Component-tree group auto-sync (gh#108).**
  Create/update/delete a wing drives `sync_group_for_wing` and
  `delete_synced_nodes("wing:<name>")` via a lazy import.
  - Legacy origin: `wing_service.create_wing:298-300`
  - Definition of done: a group node with `synced_from = "wing:<name>"` appears
    on create and disappears on delete.
  - Confidence: 🟢

### Structural pipeline

- [ ] **T-20 — `required_section_modulus`.**
  `M_design = |M| · g_limit · j`; `erf_W = M_design · 1000 / σ_allow`.
  `σ_allow ≤ 0` raises `ValueError`. Fallback `t/c` = `_TC_FALLBACK = 0.12`.
  - Legacy origin: `app/services/spar_sizing.py:9-13, 32, 78-88`
  - Definition of done: the four unit conversions (N·m → N·mm) are covered, and
    `σ_allow = 0` raises rather than dividing by zero.
  - Confidence: 🟢

- [ ] **T-21 — Shape moduli and their closed-form inverses.**
  `rectangular W = b·h²/6`; `capped W = b·(H³ − h³)/(6·H)`; `rod W = d³/10`;
  `tube W = π·(Da⁴ − Di⁴)/(32·Da)`. Inverses:
  `tube Di = (Da⁴ − 32·erf_W·Da/π)^(1/4)`; `rod d = (10·erf_W)^(1/3)`;
  `rectangular b = 6·erf_W / h²`; `capped h = (H³ − 6·H·erf_W/b)^(1/3)`.
  - Legacy origin: `spar_sizing.py:40-70, 96-208`
  - Definition of done: for each shape, `W(solve_dimension(erf_W)) ≈ erf_W`
    within float tolerance.
  - Confidence: 🟢

- [ ] **T-22 — `SparSizingParams` validation.**
  `safety_factor_j = 1.5` (`> 0`), `packing_factor = 0.8` (`0 < x ≤ 1`),
  `shape ∈ {tube, rod, rectangular, capped}`, `cap_width_mm` required only for
  `capped`, `material_id` must resolve to a `Component` of type `material`
  carrying `allowable_bending_stress_mpa`.
  - Legacy origin: `app/schemas/spar_sizing.py:12-51`
  - Definition of done: `packing_factor = 1.2` and a `capped` request without
    `cap_width_mm` are both rejected.
  - Confidence: 🟢

- [ ] **T-23 — `build_stations_from_geometry`.**
  `y_spans = linspace(0, 1, n_span)` with `y_spans[0] → _ROOT_EPS = 1e-3`;
  `x_c` = requested, else the max-thickness location;
  `clr = (1 − packing_factor)/2 · thickness`;
  `band_lo = bottom_z + clr`, `band_hi = top_z − clr`;
  `M_design = |moment_fn(y_span)| · g_limit · j` (defaults `g = 3.0`, `j = 1.5`);
  `required_od = solve_dimension("rod", erf_W, outer = band_hi − band_lo)`.
  - Legacy origin: `cad_designer/airplane/geometry/spar_solver.py:681-746`;
    gh-1037 #4
  - Definition of done: the root station is sampled at `y = 1e-3`, not `0`, and a
    test documents that `y = 0` would return a zero-thickness band.
  - Confidence: 🟢

- [ ] **T-24 — `rear_spar_x_c_with_clearance` (gh-1059).**
  `max(min(requested, hinge_x_c − 0.03), 0.05)`, pass-through when
  `hinge_x_c is None`. `_REAR_CLEARANCE_FRACTION = 0.03`,
  `_MIN_REAR_X_C = 0.05`. Applies to **computed** spars only.
  - Legacy origin: `spar_solver.py:181-221`
  - Definition of done: requested `0.80` with hinge `0.72` yields `0.69`; a hinge
    at `0.06` clamps to the `0.05` floor.
  - Confidence: 🟢

- [ ] **T-25 — `plan_spar` / `solve_spar_plan` telescoping layout.**
  Per half-span, greedy straight-piece fit split into telescoping runs wherever
  the strength-required OD exceeds the containment band.
  - Legacy origin: `spar_solver.py:342, 619-672`
  - Definition of done: a strongly tapered wing yields ≥ 2 runs whose ODs
    decrease outboard.
  - Confidence: 🟢

- [ ] **T-26 — Joint-type decisions.**
  Front: `_inboard_collinear` compares the halves' root `center_z` within
  `tol_mm = 5.0` → `"continuous"` else `"reinforcement+joiner"` plus a generated
  reinforcement piece; a **single-half** surface is forced to `"continuous"`
  (gh-1091). Rear: `"continuous"` when a straight collinear rod through `y = 0`
  stays inside the band on both halves, else `"bent-pin"`.
  - Legacy origin: `spar_solver.py` (`_inboard_collinear`); gh-1091
  - Definition of done: a vertical stabiliser (one half) solves without an index
    error and reports `"continuous"`.
  - Confidence: 🟢

- [ ] **T-27 — Honest utilisation and feasibility.**
  `utilisation = od / max(tightest_band, 1e-6)`; `feasible = od ≤ tightest`;
  the infeasibility message names the governing station and suggests a
  capped/box spar. **No clamping.**
  - Legacy origin: `_piece_from_run_with_od`, `spar_solver.py:490-529`
  - Definition of done: an over-loaded root reports `feasible = false` and
    `utilisation > 1.0` rather than raising or silently shrinking the spar.
  - Confidence: 🟢

- [ ] **T-28 — Negligible-load tip (gh-1076).**
  `NEGLIGIBLE_OD_FLOOR_MM = 1.0`; below it emit **no piece** and report
  `front_no_spar_from_y` / `rear_no_spar_from_y`.
  - Legacy origin: `spar_solver.py:44-53, 438-457`
  - Definition of done: a tip whose required OD is 0.6 mm produces no piece and a
    populated `front_no_spar_from_y`.
  - Confidence: 🟢

- [ ] **T-29 — `_bore_for`.**
  Reconstruct `erf_W` from the governing rod OD via
  `required_section_modulus_from_od(od) = od³/10`, solve the tube path, and fall
  back to `wall_factor = 0.6 × od` when strength demands a solid.
  `telescope_clearance_mm = 0.5` is the radial slip-fit gap.
  - Legacy origin: `spar_solver.py:460-487`
  - Definition of done: both branches are covered, and nested runs differ by at
    least `2 × 0.5` mm in diameter.
  - Confidence: 🟢

- [ ] **T-30 — Keep the solver CAD-free.**
  No CadQuery import anywhere in the decision logic; every branch reachable with
  hand-built `StationData`.
  - Legacy origin: `spar_solver.py:1-24`
  - Definition of done: the solver test module runs on the CI **fast** tier with
    CadQuery uninstalled.
  - Confidence: 🟢

- [ ] **T-31 — `SectionGeometry` sampling modes (gh-1046).**
  `"analytic"` default (blend segment airfoils via
  `WingConfiguration.get_points_on_surface`, build no solid) and `"solid"`
  (build the RIGHT-half loft once via `WingLoftCreator`, slice it, and group
  `sample` requests by `y_span` so each plane is cut once). `points_per_edge`
  clamped to `[8, 4096]`. Raise `SectionGeometryUnavailableError` when CadQuery
  is absent.
  - Legacy origin: `cad_designer/airplane/geometry/section_geometry.py:160-219`
  - Definition of done: `points_per_edge = 5` is clamped to 8; the analytic path
    imports no CAD kernel; a repeated `y_span` cuts one plane in solid mode.
  - Confidence: 🟢

### Control surfaces

- [ ] **T-32 — Role → axis decomposition (gh-772, ADR 0008).**
  `_DUAL_ROLE_AXES = {elevon: (pitch, roll), flaperon: (lift, roll),
  ruddervator: (pitch, yaw)}`; `PRIMARY_AXES = {pitch, lift}`,
  `SECONDARY_AXES = {roll, yaw}`. Dual-role emits two variables per the
  sgn_dup / gain / symmetric / baseline table in
  [`design.md`](design.md) §F8 — the **secondary baseline is `0.0`**. A
  single-axis role passes through with its existing tagged name and `±1` sign.
  - Legacy origin: `app/services/control_surface_mixing.py:29-33, 126-128, 134-146`
  - Definition of done: an `elevon` at 10° yields a `pitch` variable with
    `sgn_dup = +1` and baseline 10, plus a `roll` variable with `sgn_dup = −1`
    and baseline `0.0`.
  - Confidence: 🟢

- [ ] **T-33 — `axis_control_name` + `assert_unique_control_names`.**
  `[{role}]{axis}_{wing_key}_{xsec_index}`; raise on any duplicate before an AVL
  file is written, because AVL silently collapses same-named `CONTROL` variables
  into a single DOF.
  - Legacy origin: `control_surface_mixing.py:76-84, 149-164`
  - Definition of done: two surfaces resolving to the same name raise; the raise
    happens before any file I/O.
  - Confidence: 🟢

- [ ] **T-34 — `_validate_mix_fields` role gating.**
  `differential_ratio ≠ 1.0` only for
  `{aileron, elevon, flaperon, ruddervator}`; `mix_gain_secondary ≠ 1.0` only for
  `{elevon, flaperon, ruddervator}`; comparison via
  `math.isclose(rel_tol=1e-9, abs_tol=1e-9)`; a `None` role skips the check.
  Ranges `mix_gain_* 0 < x ≤ 5`, `differential_ratio 0.3 < x ≤ 3`.
  - Legacy origin: `app/schemas/aeroplaneschema.py:51-78`
  - Definition of done: `differential_ratio = 1.5` on role `flap` → 422, on role
    `aileron` → 200; a partial patch without `role` is accepted.
  - Confidence: 🟢

- [ ] **T-35 — `differential_ratio` stays out of the solution.**
  Applied post-trim for left/right display only.
  - Legacy origin: `control_surface_mixing.py:14-15`;
    `aeroplaneschema.py:372-381`
  - Definition of done: changing `differential_ratio` leaves every trim and aero
    coefficient bit-identical.
  - Confidence: 🟢

### Turbulator

- [ ] **T-36 — Turbulator CRUD.**
  1:1 per segment; schema defaults `form = "zigzag"`, `height_mm = 0.3` (`≥ 0`),
  `position_root` required in `[0,1]`, `position_tip` falls back to
  `position_root`, `enabled = True`. Terminal station → 422.
  - Legacy origin: `app/models/aeroplanemodel.py:83` (gh-934);
    `app/schemas/aeroplaneschema.py:233`
  - Definition of done: `PUT` without `position_tip` stores
    `position_tip == position_root`; a terminal-station `PUT` returns 422.
  - Confidence: 🟢

- [ ] **T-37 — Turbulator optimiser.**
  `XTR_GRID = linspace(0.2, 0.9, 15)`, `_ALPHA_GRID = linspace(-4.0, 14.0, 37)`,
  `_CONFIDENCE_THRESHOLD = 0.80`;
  `cd_clean = cd(CL, Re, xtr_upper = 1.0)`; `i_opt = argmin` over **finite** `cd`;
  `delta_cd = cd_tripped − cd_clean`;
  `ΔCD0 = symmetry_factor · Σ(Δcd_i · S_i) / S_ref` with `symmetry_factor = 2`
  for a symmetric wing because `section_aoa_service` returns half-span sections
  only.
  - Legacy origin: `app/services/turbulator_optimizer_service.py:53, 56, 60`
  - Definition of done: `xtr_opt` is always one of the 15 grid values;
    `delta_cd` reproduces the difference exactly.
  - Confidence: 🟢

- [ ] **T-38 — Optimiser warnings, not fallbacks (ADR 0012).**
  Warn on all-NaN `cd`, on mean `analysis_confidence < 0.80`, and on a boundary
  optimum (`i_opt ∈ {0, len−1}`). Never substitute a default value.
  - Legacy origin: `turbulator_optimizer_service.py:223-268, 294-331`
  - Definition of done: a forced boundary optimum produces a warning naming the
    `[0.2, 0.9]` bound and still returns the numeric result.
  - Confidence: 🟢

### REST layer

- [ ] **T-39 — The ≈30 routes.**
  Wing, station, spar, TED, servo, `control_surface` / `cad_details` /
  `servo_details`, turbulator, plus `section-aoa` and
  `POST /aeroplanes/{id}/turbulator/optimize`, exactly as listed in
  [`contracts.md`](contracts.md), with the shared domain→HTTP mapping.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/wings.py` (1039 l.);
    `section_aoa.py:74`; `turbulator_optimizer.py:173`
  - Definition of done: contract tests assert every status code in
    `contracts.md`, including the 422 on terminal-station writes and the 422 on
    role-gated mixing violations.
  - Confidence: 🟢

- [ ] **T-40 — Geometry-change fan-out.**
  Route every geometry-mutating path through `invalidation_service.mark_ops_dirty`
  so dependent operating points become `DIRTY`.
  - Legacy origin: `app/services/invalidation_service.py:16-93`
  - Definition of done: creating or moving a station marks the aircraft's
    non-`DIRTY`/`COMPUTING` operating points `DIRTY`.
  - Confidence: 🟡 INFERRED — the cross-module note states the requirement; the
    exact wing-side call sites were not enumerated.

## Test Tasks

- [ ] **TT-01 — Happy path:** create a wing from a `WingConfiguration`, read it
      back as a `WingConfiguration`, and assert a byte-identical round-trip.
- [ ] **TT-02 — Failure:** segment data on the terminal station returns 422 at
      each of the three enforcement layers (one test per layer).
- [ ] **TT-03 — Unit boundary:** `spare_length = 0.25` on the wire ⇒ `250.0` in
      the DB ⇒ `0.25` on read; `spare_vector` unchanged in both directions.
- [ ] **TT-04 — Spar preservation:** a `normal` spar with explicit origin and
      vector survives model→config→model; a `standard` spar is recomputed.
- [ ] **TT-05 — Degraded platform:** with CadQuery raising `ImportError`, wing
      CRUD returns 200 and `_recompute_spare_vectors` logs a warning.
- [ ] **TT-06 — Terminal dihedral:** 5.0° on the last station survives a
      round-trip although `xyz_le` is unchanged.
- [ ] **TT-07 — Sizing inverse matrix:** for all four shapes,
      `W(solve_dimension(erf_W)) ≈ erf_W`; `σ_allow = 0` raises `ValueError`.
- [ ] **TT-08 — Root-eps guard:** the root station is sampled at `1e-3`; a test
      documents the zero-thickness failure at `y = 0`.
- [ ] **TT-09 — Rear clearance matrix:** `(0.80, 0.72) → 0.69`;
      `(0.80, 0.06) → 0.05`; `(0.80, None) → 0.80`.
- [ ] **TT-10 — Infeasibility is reported:** `feasible = false`,
      `utilisation > 1.0`, governing station named, no exception.
- [ ] **TT-11 — Negligible tip:** required OD `< 1.0` mm ⇒ no piece,
      `front_no_spar_from_y` populated.
- [ ] **TT-12 — Single-half surface** (vertical stabiliser) solves and reports
      a `"continuous"` front joint.
- [ ] **TT-13 — Solver runs CAD-free** on the fast tier with hand-built
      `StationData`.
- [ ] **TT-14 — Dual-role decomposition** produces the exact sgn_dup / gain /
      symmetric / baseline table, secondary baseline `0.0`.
- [ ] **TT-15 — Duplicate control names raise** before any file is written.
- [ ] **TT-16 — Role gating matrix:** `differential_ratio` and
      `mix_gain_secondary` × each role, plus the `None`-role skip.
- [ ] **TT-17 — `differential_ratio` is inert:** the trim solution is
      bit-identical across values.
- [ ] **TT-18 — Optimiser grid:** `xtr_opt ∈ XTR_GRID`;
      `delta_cd = cd_tripped − cd_clean`.
- [ ] **TT-19 — Boundary optimum warns** and still returns the value.
- [ ] **TT-20 — `points_per_edge` clamp:** `5 → 8`, `9000 → 4096`.
- [ ] **TT-21 — ASB index offset:** a TED on segment 0 does not produce a phantom
      TED on segment 1 after a round-trip.

## Data Migration Tasks

- [ ] **TM-01 — Backfill `wing_xsecs.dihedral` for pre-gh-951 rows.** `NULL`
      means "derive from geometry", which is correct for interior stations but
      loses a terminal-rib rotation that was never stored. Decide whether to
      leave `NULL` or write the geometry-derived value. 🟡
- [ ] **TM-02 — Backfill `wings.design_model` for legacy rows.** `NULL` today;
      consumers gating CAD capability on `'wc'` will treat legacy wings as
      non-CAD. 🟡
- [x] **TM-03 — Millimetre invariant on `wing_xsec_spares`: audited, no
      remediation needed.** 🟢 Measured against the live database on 2026-08-15
      (`Q-WD-7 ①`): all 47 spar rows have `spare_support_dimension_width`,
      `spare_support_dimension_height`, `spare_length` and `spare_start` **≥ 1.0**,
      so no row shows the sub-millimetre signature of metre-unit contamination.
      The heuristic is recorded so the check can be re-run if data is imported
      from elsewhere.
- [ ] **TM-04 — Normalise the `servo` union.** 🟢 Decided (`Q-WD-3 ①`): new
      records use `servo_data`; `servo_index` is deprecated and the union stays
      readable for existing rows. Migration of the minority form remains to be
      executed.

## Suggested Order

1. **T-01 → T-04** first — the six tables and the read-through properties are
   what everything else manipulates. T-02's millimetre decision must be settled
   before any conversion code is written.
2. **T-05 → T-07** immediately after: the terminal-station rule is enforced at
   three layers and each layer's tests are cheap. Writing them early prevents the
   most common round-trip defect class.
3. **T-08 → T-13** next — the unit boundary. T-11 blocks T-12 (preservation must
   be decided before the recompute runs), and T-13 blocks the structural
   pipeline's write-back.
4. **T-14 → T-19** — the wing lifecycle. T-17 depends on T-05/T-06 being in
   place; T-19 depends on `aeroplane-core`'s component tree existing.
5. **T-20 → T-31** — the structural pipeline, independent of the REST layer and
   parallelisable with step 4. T-21 blocks T-23; T-23 blocks T-25; T-25 blocks
   T-26 → T-29. T-30 is a constraint on all of them, not a step. T-31 is only
   needed by T-23's `"solid"` mode and by `section-aoa`.
6. **T-32 → T-35** — control-surface mixing, independent of the structural
   pipeline. T-32 blocks T-33.
7. **T-36 → T-38** — the turbulator, which depends on `section_aoa_service`
   (module `aero-analysis`) for the section operating points.
8. **T-39 → T-40** last — the REST layer is thin and only wires what is already
   tested; T-40 needs `invalidation_service` to exist.

## Resolved by the validation interview (2026-08-15)

- 🟢 **Bug #955 — `control_surface_mixing` owns a resolver** that trim, retrim
  and stability are **required** to call, and the silent ±25° fallback is
  removed (`Q-WD-1`, maintainer-answered).
- 🟢 **`servo_data` canonical, `servo_index` deprecated**; the union stays
  readable for existing rows (`Q-WD-3 ①`).
- 🟢 **A `NULL` servo dimension is rejected on read** rather than defaulted
  (`Q-WD-3 ②`) — an invented dimension would reach a CAD build.
- 🟢 **Topology classes are the single authority for TED defaults**
  (`Q-WD-3 ③`, ADR 0022); `NULL` means "not stated".
- 🟢 **`role` gains a CHECK constraint / enum** (`Q-WD-3 ④`) — today an unknown
  role is silently treated as single-axis, so a typo produces a wing that builds
  and flies differently from what was asked, with no error anywhere.
- 🟢 **Duplicate name is 409 everywhere** (`Q-FD-1`); `create_wing` aligns.
- 🟡 **`units` describes the wire format only** (`Q-WD-2`) — no storage-unit
  override; the `SpareDetailSchema` descriptions are clarified instead. Derived
  from ADR 0019.
- 🟡 **The degraded no-CadQuery state becomes a `DesignWarning` in the response
  body** (`Q-WD-6`), so a client can distinguish recomputed spar vectors from
  stale ones. Derived from `P-WARN-0`.

## Pending Gaps (🔴)
