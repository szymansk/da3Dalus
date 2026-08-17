# wing-design

> Module-level specification. Focuses on WHAT the module does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: wing-design,
> `_reversa_sdd/data-dictionary.md` §Module: wing-design, `_reversa_sdd/domain.md` §2.1–2.3.

## Overview

`wing-design` owns every lifting surface — main wing, horizontal tail, vertical
tail, canard and winglet are all `wings` rows; there is no `surface_role` column.
It covers stations (ribs), spars, trailing-edge devices, servos and turbulators;
the `WingConfiguration` topology bridge into the CAD world; the structural
spar-sizing and buildable-layout pipeline; the control-surface role→axis
decomposition; and — critically — the **millimetre ↔ metre conversion boundary**.
🟢

## Responsibilities

- CRUD for wings and their stations (`wing_xsecs`) with `sort_index` ordering. 🟢
- CRUD for all segment-scoped children: spars (`spare_list`), trailing-edge
  devices, TED servos, turbulators, and the ASB `control_surface` projection. 🟢
- Enforce the station/segment model and the terminal-station rule in three
  independent layers. 🟢
- Convert between the metre DB world and the millimetre `WingConfiguration`
  world, in exactly the named conversion functions and nowhere else. 🟢
- Persist the terminal rib's dihedral explicitly, since it cannot be recovered
  from station positions. 🟢
- Size spars by section modulus and solve a buildable, telescoping spar layout
  that respects the containment band and control-surface clearance. 🟢
- Decompose a control-surface **role** into one or two **control axes** and
  guarantee globally unique control-variable names (gh-772). 🟢
- Optimise per-segment turbulator (forced-transition) position for minimum
  section drag, emitting design warnings instead of silent fallbacks (gh-934). 🟢
- Record how a wing was authored (`design_model` = `'wc'` | `'asb'`). 🟢

**Explicitly NOT this module's responsibility:** building the actual CAD solid
(→ `cad-generation`), running the aerodynamic solvers (→ `aero-analysis`,
`avl-integration`), the frozen topology classes themselves
(→ `cad-designer-topology`, read-only per ADR 0002), and **any stiffness,
deflection or flutter criterion** — spar sizing answers strength only, by
decision (BR-W18).

## Business Rules

### Topology

- **BR-4 — N stations describe N−1 segments.** 🟢 A wing is a list of stations
  ordered by `sort_index`. All segment-scoped data (spars, TED, turbulator,
  `x_sec_type`, `tip_type`, `number_interpolation_points`) hangs off the
  **inboard** station of its segment, in the 1:1 `wing_xsec_details` side table.
- **BR-5 — The terminal station carries geometry only.** 🟢 Enforced in three
  independent layers:
  1. schema — `AsbWingSchema.validate_last_xsec_has_no_segment_details`
     (`app/schemas/aeroplaneschema.py:666-680`) raises on any segment field
     present on the last x-section;
  2. model — `WingModel.from_dict` blanks all six segment fields when
     `index == len(xsec_dicts) - 1` (`app/models/aeroplanemodel.py:489-490`);
  3. service — `_assert_non_terminal_xsec_or_raise`
     (`app/services/wing_service.py:151-156`) raises `ValidationError` for writes
     targeting the terminal index.
  This triple enforcement is deliberate defence-in-depth for the rule that most
  often breaks round-trips.
- **BR-W1 — ASB index offset.** 🟢 AeroSandbox emits N+1 x-secs for N segments,
  and `x_sec[i]`'s control surface belongs to segment *i−1*.
  `_build_segment_details` therefore **overwrites** the x-sec-derived control
  surface with the segment's own TED-derived one; otherwise
  `_merge_ted_with_control_surface` resurrects a phantom TED on round-trip
  (`app/converters/model_schema_converters.py:960-995`).
- **BR-6 — A segment's root chord is not independently settable.** 🟢 Chord
  continuity means a segment's root chord *is* the previous segment's tip chord;
  tapering is expressed by setting the tip chord. The schema cannot express this,
  so the copilot's `get_wing_geometry` carries it as free-text `note`.
- **BR-7 — Terminal dihedral must be persisted explicitly (gh-951).** 🟢 The last
  rib's local-x rotation moves no outboard station, leaves no trace in `xyz_le`
  and cannot be reconstructed from positions. It is stored in
  `wing_xsecs.dihedral` (`app/models/aeroplanemodel.py:219-225`); `NULL` on
  legacy rows means "derive from geometry". Write path
  (`model_schema_converters.py:998-1015`):

  ```
  station i airfoil = segments[i].root_airfoil        for i < N
  station N airfoil = segments[-1].tip_airfoil        (terminal rib)
  dihedral          = airfoil.dihedral_as_rotation_in_degrees
  ```

- **BR-8 — A wing knows how it was authored.** 🟢 `wings.design_model` is `'wc'`
  when created from a `WingConfiguration` (CAD-capable) and `'asb'` when created
  from bare ASB geometry; `NULL` for legacy rows
  (`wing_service.py:292, :341`; `aeroplaneschema.py:652-655`).
- **BR-W2 — Minimum two stations.** 🟢 `AsbWingSchema.x_secs` carries
  `min_length=2` — a wing with fewer stations has no segment.

### Units

- **BR-1 — The unit duality (ADR 0001).** 🟢 DB and AeroSandbox speak **metres**;
  `WingConfig` and every `cad_designer` topology class speaks **millimetres**.
  Conversion happens only in `app/converters/` and the `_convert_spare_to_*`
  helpers of `wing_service` (`scale = 0.001` mm→m, `scale = 1000.0` m→mm).
  There is no type-level unit.
- **BR-2 — The `wing_xsec_spares` exception (gh-402).** 🟢 All six dimensional
  spar columns (`width`, `height`, `length`, `start`, `spare_origin`) are stored
  in **millimetres inside the metre database**. `spare_vector` is a
  **dimensionless unit direction vector**. The API contract is unchanged — every
  spar endpoint still delivers metres.
- **BR-3 — Wing-local frame.** 🟢 `cad_designer` geometry uses a wing-local frame:
  origin at the root leading edge, z up.
- **BR-W3 — Spar geometry preservation (gh-1053).** 🟢
  `_resolve_spare_vectors_and_origins` normally clears and recomputes every
  spar's origin/vector on model→config conversion (the gh-352/gh-362 unit-leak
  guard). `should_preserve_normal_spare` exempts spars that are
  `spare_mode == "normal"` **and** carry a fully explicit 3-component
  `spare_origin` **and** `spare_vector`
  (`app/converters/spare_origin_preservation.py:43-59`); everything else
  (`standard` / `follow` / `*_backward`) still goes through the recompute path.
  Without the exemption a solver-produced front/rear spar couple collapses onto
  the default quarter-chord station.
- **BR-W4 — Recompute degrades silently on a missing platform dependency.** 🟢
  `_recompute_spare_vectors` (`wing_service.py:854-873`) rebuilds a
  `WingConfiguration` at `scale=1.0` (metres), reads back each segment's computed
  `spare_vector` / `spare_origin` and writes the origin back **×1000** as mm. On
  `ImportError` (aarch64 without CadQuery) or `FileNotFoundError` (missing
  airfoil `.dat`) it logs a warning and continues.

### Control surfaces

- **BR-9 — A role decomposes into control axes (gh-772).** 🟢
  `elevon → (pitch, roll)`, `flaperon → (lift, roll)`,
  `ruddervator → (pitch, yaw)`
  (`app/services/control_surface_mixing.py:29-33`).
  `PRIMARY_AXES = {pitch, lift}` (symmetric), `SECONDARY_AXES = {roll, yaw}`
  (antisymmetric). A dual-role surface emits **two** AVL `CONTROL` variables on
  the same section:

  | axis | `sgn_dup` | gain | `symmetric` | baseline deflection |
  |---|---|---|---|---|
  | primary | `+1.0` | `mix_gain_primary` | `True` | the surface's deflection |
  | secondary | `−1.0` | `mix_gain_secondary` | `False` | **`0.0`** |

  The secondary baseline is 0 so the AeroBuildup fallback never feeds a roll/yaw
  deflection into the single-axis ASB model (l.126-128). A single-axis role keeps
  its existing tagged name and `±1` sign verbatim (l.134-146).
- **BR-10 — `SgnDup` is a sign flag, never a magnitude.** 🟢 `differential_ratio`
  is a **reporting-only kinematic** applied *after* trim for left/right display;
  it never alters the aero or trim solution
  (`control_surface_mixing.py:14-15`; `aeroplaneschema.py:372-381`).
- **BR-11 — Control-variable names must be globally unique.** 🟢
  `axis_control_name` produces `[{role}]{axis}_{wing_key}_{xsec_index}`, e.g.
  `[ruddervator]pitch_htail_1` (l.76-84). AVL silently collapses identically
  named `CONTROL` variables into a single DOF, so
  `assert_unique_control_names` raises on any duplicate (l.149-164).
- **BR-12 — Mixing fields are role-gated.** 🟢 `differential_ratio ≠ 1.0` is legal
  only for `DIFFERENTIAL_ROLE_VALUES = {aileron, elevon, flaperon, ruddervator}`;
  `mix_gain_secondary ≠ 1.0` only for
  `DUAL_ROLE_VALUES = {elevon, flaperon, ruddervator}`. Compared with
  `math.isclose(rel_tol=1e-9, abs_tol=1e-9)`; a `None` role (partial patch) skips
  the check entirely (`_validate_mix_fields`, `aeroplaneschema.py:51-78`).
  Schema ranges: `mix_gain_*` `0 < x ≤ 5`, `differential_ratio` `0.3 < x ≤ 3`.
- 🟢 **BR-13 — bug #955 is resolved structurally** (`Q-WD-1`,
  maintainer-answered). `control_surface_mixing` owns a resolver that
  `trim_enrichment_service`, `retrim_service` and `stability_service` are
  **required** to call, and the silent hard-coded ±25° fallback is **removed**.
  The mixing layer generates the canonical names, so keying on the raw DB TED
  name stops being possible rather than merely discouraged — which is what
  prevents #955 recurring. Until it lands, a dual-role aircraft still reports
  ±25° limits and a phantom 0° surface.

### Structure

- **BR-W16 — The structural model is a two-spar wing whose skin carries no load.** 🟢
  Front spar takes bending alone, rear spar takes torsion over the chordwise spacing.
  Neither route has a stressed skin: the printed shell is deliberately **unbonded**,
  and a built-up wing's ribs transfer load **into** the spar under a film covering
  that conforms to load rather than resisting it. **No D-box exists in either route.**
  Premise of every rule below — full statement and consequences in
  [`spar-sizing/requirements.md`](spar-sizing/requirements.md).
- **BR-W17 — The margin is a two-sided partial-factor format.** 🟡
  `M_break = M(1g) · n_limit · j · k`, with `j = 1.5` on the **load** and `k` on the
  **resistance**. `g_limit` is consumed pre-multiplied by `j·k ≈ 3.75`, so the field
  name misstates what it means; `n_break` is the quantity to display (gh-1079).
  Full statement in [`spar-sizing/requirements.md`](spar-sizing/requirements.md).
- **BR-W18 — Sizing is strength-only by decision; stiffness stays with the designer.** 🟢
  Maintainer decision, 2026-08-17. No deflection is computed and no material record needs
  an E-modulus. Accepted consequences: a tube can pass sizing and still be too soft, the
  1 g case at V = 0 is out of scope, flutter is out of scope — so `feasible = True` means
  *does not break*, never *stiff enough*. Adding a deflection limit or a minimum-`EI`
  floor is a **new decision**, not an enhancement. Full statement in
  [`spar-sizing/requirements.md`](spar-sizing/requirements.md).
- **BR-W19 — The plan always yields an orderable section, and says how over-dimensioned
  it is.** 🔴 **Soll (gh-1137)** — a load-carrying span always gets a piece; where strength
  asks for less than the smallest stock, the smallest stock is chosen and the **strength
  reserve** `W_stock / erf_W` is reported. That reserve is a *new* quantity — the existing
  `utilisation` measures containment-band fit, not strength (ADR 0022).
- **BR-W20 — One continuous section is the preferred plan.** 🔴 **Soll (gh-1137)** —
  a joint is a weak point and telescoped pieces must overlap, so per-piece weight
  optimisation is not a global optimum. Splitting stays a containment-forced fallback that
  names the station which forced it.
- **BR-W5 — Section-modulus sizing is the strength law (gh-1008).** 🟢 Units: `M`
  in N·m, `σ` in MPa (= N/mm²), dimensions in mm, `W` in mm³, mass in kg. All
  formulas in `design.md` §Structural pipeline.
- **BR-W6 — `σ_allow ≤ 0` raises.** 🟢 The material schema permits 0, so the
  division is protected at the formula (`app/services/spar_sizing.py:86-87`).
  Fallback `t/c` when airfoil data is unavailable: `_TC_FALLBACK = 0.12` (l.32).
- **BR-W7 — The root slice is nudged off `y_span = 0`.** 🟢 `_ROOT_EPS = 1e-3`,
  because the `y_span = 0` slice is a pinched, zero-thickness section on a real
  loft and would poison the governing max-moment root station (gh-1037 #4).
- **BR-W8 — A computed rear spar must clear the movable surface (gh-1059).** 🟢

  ```
  rear_spar_x_c_with_clearance(requested, hinge_x_c, clearance = 0.03):
      if hinge_x_c is None: return requested
      return max( min(requested, hinge_x_c − 0.03), 0.05 )
  ```

  `_REAR_CLEARANCE_FRACTION = 0.03`, `_MIN_REAR_X_C = 0.05`
  (`cad_designer/airplane/geometry/spar_solver.py:181-221`). Documented as
  applying only to **computed** spars — a designer may still place a reinforcing
  spar inside a control surface manually.
- **BR-W9 — Utilisation is reported honestly and may exceed 1.0.** 🟢
  `utilisation = od / max(tightest_band, 1e-6)`; `feasible = od ≤ tightest`. The
  infeasibility message names the governing station and suggests a capped/box
  spar (`spar_solver.py:490-529`). No silent clamping.
- **BR-W10 — A negligible-load tip produces no spar (gh-1076).** 🟢
  `NEGLIGIBLE_OD_FLOOR_MM = 1.0`; a tip station whose required OD falls below
  1 mm yields **no piece**, and the region is reported as
  `front_no_spar_from_y` / `rear_no_spar_from_y` rather than a degenerate Ø≈0
  tube (`spar_solver.py:44-53, 438-457`). 🔴 **Soll (gh-1136) — wrong authority.**
  Where the spar ends is topology (`wing_segment_type == 'tip'`, BR-W16), not a
  strength inference; the stated reason names a D-box neither route builds; and the
  region's start is a sampling artefact of `n_span`. Details in
  [`spar-sizing/requirements.md`](spar-sizing/requirements.md).
- **BR-W11 — Single-half surfaces force a continuous front joint (gh-1091).** 🟢 A
  vertical stabiliser has one half, so `_inboard_collinear` must not index into
  the empty half.
- **BR-W12 — The spar solver is deliberately CAD-free.** 🟢 Every branch runs on
  the CI fast tier with hand-built `StationData`
  (`spar_solver.py:1-24`) — no CadQuery import in the decision logic.
- **BR-W13 — Section geometry has an analytic fast path (gh-1046).** 🟢
  `SectionGeometry` recovers `(y/span, x/c)` in `"analytic"` mode (default —
  blends segment airfoils via `WingConfiguration.get_points_on_surface`, builds
  no solid) or `"solid"` mode (builds the RIGHT-half loft once via
  `WingLoftCreator` and slices it; `sample` groups requests by `y_span` so each
  plane is cut once). `points_per_edge` is clamped to `[8, 4096]`. The analytic
  path exists to avoid the documented **~13 s** `WingLoftCreator` bottleneck.
  Raises `SectionGeometryUnavailableError` when CadQuery is absent
  (`cad_designer/airplane/geometry/section_geometry.py:160-219`).

### Turbulator

- **BR-W14 — The turbulator optimiser minimises section drag at the section's
  operating (CL, Re) (gh-934).** 🟢

  ```
  XTR_GRID              = linspace(0.2, 0.9, 15)     # x/c sweep       (l.53)
  _ALPHA_GRID           = linspace(-4.0, 14.0, 37)   # cd-at-CL lookup (l.60)
  _CONFIDENCE_THRESHOLD = 0.80                       # warning gate    (l.56)

  cd_clean = cd(CL, Re, xtr_upper = 1.0)             # natural-transition baseline
  i_opt    = argmin over FINITE cd values
  xtr_opt  = XTR_GRID[i_opt]
  delta_cd = cd_tripped − cd_clean

  ΔCD0 = symmetry_factor · Σ (Δcd_i · S_i) / S_ref
         symmetry_factor = 2 for a symmetric wing
         (section_aoa_service returns half-span sections only)
  ```

- **BR-W15 — Unphysical optimiser results surface as warnings, never silent
  fallbacks.** 🟢 Warnings for: all-NaN `cd` (no optimum), mean
  `analysis_confidence < 0.80`, and a boundary optimum
  (`i_opt ∈ {0, len−1}` → the true minimum may lie outside `[0.2, 0.9]`)
  (`app/services/turbulator_optimizer_service.py:223-268, 294-331`). ADR 0012.

## Design principle — minimise part count 🟢

**Every joint is a weak point in the wing** (maintainer, 2026-08-16). Both manufacturing
routes therefore aim at few, large pieces rather than many small ones — a printed wing is
not decomposed further than it must be, and a wooden rib construction defines the *wing*,
with the ribs emerging as a nested cutting file rather than as modelled components.

🟢 No Creator produces rib wings yet, so neither the rib decomposition nor its DXF output
exists. That is the correct state: both arrive together, with the Creator.

This is why the component tree stays small (measured maximum: 10 nodes) and why part
count is not a free variable a Creator may optimise against.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | List a wing's names / read a wing by name under an aeroplane | Must | `GET /aeroplanes/{id}/wings` → 200; unknown wing → 404 |
| RF-02 | Create a wing from an ASB geometry payload (`PUT /{wing_name}`), stamping `design_model = 'asb'` | Must | Round-trip read returns the same stations; `design_model == 'asb'` |
| RF-03 | Create a wing from a `WingConfiguration` payload, stamping `design_model = 'wc'` and converting mm→m with `scale = 0.001` | Must | `POST .../from-wingconfig` → 201; stored `chord` is the payload's mm value ÷ 1000 |
| RF-04 | Read a wing back as a `WingConfiguration` in the millimetre world (`scale = 1000.0`) | Must | `GET .../wingconfig` returns mm geometry that re-imports byte-identically |
| RF-05 | Update / delete a wing, keeping the component-tree group in sync | Must | `DELETE .../{wing_name}` → 200; the `wing:<name>` tree group is removed |
| RF-06 | Station CRUD by index, ordered by `sort_index` | Must | `POST/PUT/DELETE .../cross_sections/{i}` behave per index; out-of-range → 404 |
| RF-07 | Reject any write of segment-scoped data to the terminal station | Must | `PUT .../cross_sections/{last}` with `spare_list` → 422 `validation_error` |
| RF-08 | Spar CRUD per station, delivering **metres** on the wire while storing **millimetres** | Must | POST a spar with `spare_length = 0.25`; the DB column reads `250.0`; the GET returns `0.25` |
| RF-09 | Preserve an explicit `normal` spar's origin/vector across a model→config round-trip | Must | A solver-produced front/rear couple keeps its distinct origins after a read-back |
| RF-10 | Trailing-edge-device CRUD (`GET/PATCH/DELETE`) with role-gated mixing validation | Must | `differential_ratio = 1.5` on role `flap` → 422; on role `aileron` → 200 |
| RF-11 | TED servo CRUD as a 1:1 child of the TED | Should | `PATCH .../trailing_edge_device/servo` → 200; `DELETE` removes only the servo |
| RF-12 | ASB `control_surface` projection read/patch/delete, plus the CAD-only `cad_details` and `servo_details` subsets | Should | Patching `cad_details` leaves the ASB projection fields untouched |
| RF-13 | Turbulator CRUD per segment (`GET/PUT/DELETE`) | Should | `PUT .../turbulator` with `position_root = 0.35` → 200; terminal station → 422 |
| RF-14 | Persist the terminal rib's dihedral explicitly | Must | Set a terminal dihedral, read back the wing: the value survives (it is absent from `xyz_le`) |
| RF-15 | Size a spar by required section modulus for the four shapes (tube, rod, rectangular, capped) | Must | Given `M`, `σ_allow`, `g_limit`, `j`, the returned dimension reproduces the closed-form inverse in `design.md` |
| RF-16 | Reject `σ_allow ≤ 0` | Must | `ValueError` is raised rather than a division by zero |
| RF-17 | Produce a buildable spar plan per half-span with telescoping runs, joint type, utilisation and feasibility | Must | An over-loaded root reports `feasible = false`, `utilisation > 1.0`, names the governing station and suggests a capped/box spar |
| RF-18 | Emit no spar piece for a negligible-load tip and report the region instead | Must | A tip whose required OD < 1.0 mm yields no piece and sets `front_no_spar_from_y` |
| RF-19 | Keep a computed rear spar clear of the hinge line | Must | With `hinge_x_c = 0.72`, the rear spar `x/c` is `≤ 0.69` and `≥ 0.05` |
| RF-20 | Decompose a dual-role surface into two control variables with the documented sign/gain/baseline table | Must | An `elevon` yields `[elevon]pitch_…` (`+1`, baseline = deflection) and `[elevon]roll_…` (`−1`, baseline `0.0`) |
| RF-21 | Reject duplicate control-variable names across surfaces | Must | Two surfaces resolving to the same name → raise before the AVL file is written |
| RF-22 | Optimise the turbulator position per section and report `ΔCD0` with warnings | Should | `POST /aeroplanes/{id}/turbulator/optimize` → 200 with per-section `xtr_opt`, `delta_cd` and any boundary/confidence warnings |
| RF-23 | Sample section geometry `(y/span, x/c)` analytically by default, with a solid-slicing mode available | Should | `mode="analytic"` returns points without importing CadQuery; `points_per_edge = 5` is clamped to 8 |
| RF-24 | Serve per-section angle of attack for a wing | Could | `GET .../wings/{wing_name}/section-aoa` → 200 |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Correctness | Unit conversion happens only at the named boundaries; no ad-hoc scaling elsewhere | `wing_service.py:43-88`, `spare_origin_preservation.py:62-78`, `model_schema_converters.py:452-470` | 🟢 |
| Correctness | The terminal-station rule is enforced in three independent layers | `aeroplaneschema.py:666-680`, `aeroplanemodel.py:489-490`, `wing_service.py:151-156` | 🟢 |
| Correctness | Control-variable names are asserted unique before an AVL file is emitted, because AVL fails silently | `control_surface_mixing.py:149-164` | 🟢 |
| Correctness | Infeasible spar layouts are reported, never clamped | `spar_solver.py:490-529` | 🟢 |
| Performance | Section sampling defaults to an analytic path to avoid a documented ~13 s loft build | `section_geometry.py:160-219` | 🟢 |
| Performance | Solid-mode sampling groups requests by `y_span` so each cutting plane is used once | `section_geometry.py` (`sample`) | 🟢 |
| Performance | `points_per_edge` is clamped to `[8, 4096]` to bound sampling cost | `section_geometry.py` | 🟢 |
| Portability | Spar-vector recompute degrades to a warning on `ImportError` / `FileNotFoundError` so aarch64 without CadQuery still serves wing CRUD | `wing_service.py:854-873` | 🟢 |
| Portability | The spar solver contains no CAD import, so every branch is testable on the CI fast tier | `spar_solver.py:1-24` | 🟢 |
| Robustness | Optimiser anomalies (all-NaN, low confidence, boundary optimum) become explicit warnings | `turbulator_optimizer_service.py:223-268, 294-331` (ADR 0012) | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Station and segment model

  Scenario: Segment data lives on the inboard station
    Given a wing with 3 stations
    When I POST a spar to cross_sections index 0
    Then the spar is stored on the wing_xsec_details row of station 0
    And it describes the segment between stations 0 and 1

  Scenario: Writing segment data to the terminal station is rejected
    Given a wing with 3 stations
    When I PUT cross_sections index 2 with a spare_list
    Then the response status is 422
    And the error code is "validation_error"

Feature: Unit conversion boundary

  Scenario: Spars are metres on the wire, millimetres in storage
    Given a wing with one station
    When I POST a spar with spare_length 0.25 and spare_support_dimension_width 0.008
    Then the stored wing_xsec_spares row has spare_length 250.0 and width 8.0
    And GET of that spar returns spare_length 0.25

  Scenario: A solved normal spar keeps its explicit origin
    Given a spar with spare_mode "normal", a 3-component spare_origin and a spare_vector
    When the wing is converted to a WingConfiguration and back
    Then the spar's origin is unchanged
    And a spar with spare_mode "standard" has its origin recomputed

Feature: Dihedral persistence

  Scenario: The terminal rib's dihedral survives a round-trip
    Given a wing whose last station has dihedral 5.0
    When I read the wing back
    Then the last station reports dihedral 5.0
    # It is not derivable from xyz_le — the terminal rotation moves no station

Feature: Spar sizing and layout

  Scenario: A rod is sized from the required section modulus
    Given M = 40 N·m, sigma_allow = 300 MPa, g_limit = 3.0 and j = 1.5
    When I size a "rod" spar
    Then required W equals |M| * g_limit * j * 1000 / sigma_allow
    And the diameter equals (10 * W) ** (1/3)

  Scenario: Zero allowable stress is rejected
    Given a material whose allowable_bending_stress_mpa is 0
    When I request a spar size
    Then a ValueError is raised
    And no division by zero occurs

  Scenario: An over-loaded root reports infeasibility honestly
    Given a station whose required OD exceeds the containment band
    When I solve the spar plan
    Then feasible is false
    And utilisation is greater than 1.0
    And the message names the governing station and suggests a capped or box spar

  Scenario: A negligible-load tip gets no spar
    Given a tip station whose required OD is below 1.0 mm
    When I solve the spar plan
    Then no piece is emitted for that region
    And front_no_spar_from_y reports where the spar stops

  Scenario: A computed rear spar clears the hinge
    Given a requested rear spar at x/c 0.80 and a hinge at x/c 0.72
    When the plan is solved
    Then the rear spar sits at x/c 0.69

Feature: Control-surface mixing

  Scenario: A dual-role surface emits two control variables
    Given a trailing-edge device with role "elevon" and deflection 10 degrees
    When the control axes are resolved
    Then a "[elevon]pitch_<wing>_<i>" variable exists with sgn_dup +1, gain mix_gain_primary, symmetric true and baseline 10
    And a "[elevon]roll_<wing>_<i>" variable exists with sgn_dup -1, gain mix_gain_secondary, symmetric false and baseline 0.0

  Scenario: Duplicate control names are rejected
    Given two surfaces that resolve to the same control name
    When assert_unique_control_names runs
    Then it raises before any AVL geometry is written

  Scenario: Mixing fields are role-gated
    Given a trailing-edge device with role "flap"
    When I PATCH differential_ratio to 1.5
    Then the response status is 422
    And the same patch on role "aileron" returns 200

Feature: Turbulator optimisation

  Scenario: A section gets an optimal trip location
    Given a wing section with a valid operating CL and Re
    When I POST /aeroplanes/{id}/turbulator/optimize
    Then xtr_opt is one of the 15 grid values in [0.2, 0.9]
    And delta_cd equals cd_tripped minus cd_clean

  Scenario: A boundary optimum is flagged, not hidden
    Given the minimum cd occurs at the first or last grid point
    When the optimisation completes
    Then a warning states the true minimum may lie outside [0.2, 0.9]
    And no fallback value is substituted
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Wing + station CRUD (RF-01…RF-06) | Must | The critical path — `aero-analysis`, `cad-generation`, `mass-and-balance` and `openvsp-import` all read wings |
| Terminal-station enforcement (RF-07) | Must | Triple-enforced in the legacy code precisely because violations break every round-trip |
| Unit conversion at the named boundaries (RF-08) | Must | Wrong by 1000× when omitted; the single most common defect class in this codebase |
| `WingConfiguration` round-trip (RF-03/RF-04) | Must | The only bridge into the CAD stack; `design_model` gates CAD capability |
| Explicit terminal dihedral (RF-14) | Must | Information-losing when omitted — it is unrecoverable from geometry (gh-951) |
| Spar preservation for explicit `normal` spars (RF-09) | Must | Without it the solver's output is destroyed on the next read (gh-1053) |
| Spar sizing + layout solve (RF-15…RF-19) | Must | Structural safety output consumed directly by the builder; several guards exist only here |
| Control-axis decomposition + name uniqueness (RF-20/RF-21) | Must | Single source of truth shared by the AVL builder, the ASB builder and trim enrichment; AVL fails **silently** on a collision |
| TED CRUD with role gating (RF-10) | Must | Role drives trim, OP capability gating and the axis decomposition |
| Servo and `control_surface` subset routes (RF-11/RF-12) | Should | Convenience projections over data already writable through the TED route |
| Turbulator CRUD + optimiser (RF-13/RF-22) | Should | An optional per-segment refinement (gh-934); the aircraft is complete without one |
| Section-geometry sampling modes (RF-23) | Should | Needed by the spar solver's `"solid"` mode and section-AoA; the analytic default has no hard dependency |
| `section-aoa` route (RF-24) | Could | A read-only diagnostic surface |
| Fixing the #955 name divergence in trim/retrim/stability | **Must** (cross-module) | 🟢 decided (`Q-WD-1`): the resolver lives here in `control_surface_mixing` and the consumers are required to call it. Implementation spans `aero-analysis`; the ownership question is settled |
| Perpendicular-spare branch in `WingConfiguration` | Won't | Known dead branch inside the frozen topology layer; deliberately not fixed (ADR 0002) |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/wing_service.py` (1585 l.) | wing/xsec/spar/TED/servo/turbulator CRUD, `_convert_spare_to_meters/_mm`, `_assert_non_terminal_xsec_or_raise`, `get_wing_as_wingconfig`, `create_wing_from_wing_configuration`, `_sync_spares_for_xsec`, `_recompute_spare_vectors` | 🟢 |
| `app/api/v2/endpoints/aeroplane/wings.py` (1039 l.) | ≈30 routes | 🟢 |
| `app/converters/model_schema_converters.py` (1104 l.) | `_build_segment_details`, `_merge_ted_with_control_surface`, `_station_dihedral`, `_scale_asb_wing_geometry_schema`, `wing_model_to_wing_config` | 🟢 |
| `app/converters/spare_origin_preservation.py` | `should_preserve_normal_spare`, `scale_db_origin_to_config` | 🟢 |
| `app/services/spar_sizing.py` | `required_section_modulus`, `solve_dimension`, shape moduli | 🟢 |
| `cad_designer/airplane/geometry/spar_solver.py` | `plan_spar`, `solve_spar_plan`, `build_stations_from_geometry`, `_piece_from_run_with_od`, `_bore_for`, `_inboard_collinear`, `rear_spar_x_c_with_clearance` | 🟢 |
| `cad_designer/airplane/geometry/section_geometry.py` | `SectionGeometry`, `sample` | 🟢 |
| `app/services/spar_plan_service.py`, `app/services/spar_insert_service.py` | plan orchestration + persistence | 🟢 |
| `app/services/control_surface_mixing.py` | `axis_control_name`, `assert_unique_control_names`, `_DUAL_ROLE_AXES` | 🟢 |
| `app/services/turbulator_optimizer_service.py` | xtr sweep optimiser | 🟢 |
| `app/models/aeroplanemodel.py` | `WingModel`, `WingXSecModel`, `WingXSecDetailModel`, `WingXSecSpareModel`, `WingXSecTrailingEdgeDeviceModel`, `WingXSecTedServoModel`, `WingXSecTurbulatorModel` | 🟢 |
| `app/schemas/aeroplaneschema.py` | `AsbWingSchema`, `WingXSecSchema`, `SpareDetailSchema`, `TrailingEdgeDeviceDetailSchema`, `TurbulatorDetailSchema`, `ControlSurfaceSchema`, `_validate_mix_fields` | 🟢 |
| `cad_designer/airplane/aircraft_topology/wing/*` | frozen topology classes (mm) | 🟢 read-only (ADR 0002) |
