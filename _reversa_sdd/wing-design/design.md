# wing-design — Technical Design

> Module-level design. Focuses on HOW the module is built, derived from the
> legacy code. Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Endpoint contracts in full: see [`contracts.md`](contracts.md).
> Behavioural slices: [`cross-section-crud/`](cross-section-crud/),
> [`spar-sizing/`](spar-sizing/), [`control-surface-mixing/`](control-surface-mixing/),
> [`turbulator-optimizer/`](turbulator-optimizer/).

## Interface

### Service surface — `app/services/wing_service.py` (1585 l.) 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `_convert_spare_to_meters` | `(spare_dict)` | dict | mm → m on the 5 dimensional fields; `spare_vector` untouched (l.49-66) |
| `_convert_spare_to_mm` | `(spare_dict)` | dict | m → mm, same 5 fields (l.69-88) |
| `_assert_non_terminal_xsec_or_raise` | `(wing, index)` | `None` | raises `ValidationError` for the terminal station (l.151-156) |
| `create_wing` | `(db, aeroplane_uuid, wing_name, payload)` | `WingModel` | stamps `design_model = 'asb'`; duplicate name → `ValidationError` (→422) (l.285-300) |
| `create_wing_from_wing_configuration` | `(db, …, wing_config, scale=0.001)` | `WingModel` | mm → m; stamps `design_model = 'wc'` (l.313, :341) |
| `get_wing_as_wingconfig` | `(db, …, wing_name)` | `WingConfiguration` | `wing_model_to_wing_config(wing, scale=1000.0)` — mm world (l.372) |
| `_sync_spares_for_xsec` | `(detail, spares_m)` | `None` | writes solved spar geometry back as metres × 1000 (l.851) |
| `_recompute_spare_vectors` | `(wing)` | `None` | rebuilds a `WingConfiguration` at `scale=1.0`, reads back vector/origin, writes origin ×1000 (l.854-873) |

Station, spar, TED, servo, `control_surface` and turbulator CRUD all live in the
same module; the REST layer is a thin projection over them
(see [`contracts.md`](contracts.md)). 🟢

### Conversion surface — `app/converters/` 🟢

| Symbol | File | Purpose |
|---|---|---|
| `wing_model_to_wing_config` | `model_schema_converters.py` | DB model → `cad_designer` `WingConfiguration` |
| `_scale_asb_wing_geometry_schema` | `model_schema_converters.py:452-470` | multiplies `xyz_le` and `chord` by `scale` |
| `_build_segment_details` | `model_schema_converters.py:960-995` | segment assembly; **overwrites** the x-sec-derived control surface with the TED-derived one |
| `_merge_ted_with_control_surface` | `model_schema_converters.py` | the inverse merge that would resurrect a phantom TED without the overwrite above |
| `_station_dihedral` | `model_schema_converters.py:998-1015` | per-station dihedral from the segment airfoils |
| `should_preserve_normal_spare` | `spare_origin_preservation.py:43-59` | gh-1053 exemption from the recompute path |
| `scale_db_origin_to_config` | `spare_origin_preservation.py:62-78` | `factor = 0.001 × scale` |

### Structural surface 🟢

| Symbol | File | Purpose |
|---|---|---|
| `required_section_modulus` | `app/services/spar_sizing.py:78-88` | `erf_W = M_design · 1000 / σ_allow` |
| `solve_dimension` | `app/services/spar_sizing.py:96+` | closed-form inverse per shape |
| `build_stations_from_geometry` | `spar_solver.py:681-746` | `n_span` station sampling root→tip |
| `rear_spar_x_c_with_clearance` | `spar_solver.py:181-221` | hinge clearance for **computed** rear spars |
| `plan_spar` / `solve_spar_plan` | `spar_solver.py:342, 619-672` | telescoping layout per half-span |
| `_piece_from_run_with_od` | `spar_solver.py:490-529` | utilisation + feasibility, never clamped |
| `_bore_for` | `spar_solver.py:460-487` | tube bore from the governing OD |
| `_inboard_collinear` | `spar_solver.py` | front-joint type decision, `tol_mm = 5.0` |
| `SectionGeometry.sample` | `section_geometry.py:160-219` | `(y/span, x/c)` sampling, analytic \| solid |

### Control-surface + turbulator surface 🟢

| Symbol | File | Purpose |
|---|---|---|
| `_DUAL_ROLE_AXES`, `PRIMARY_AXES`, `SECONDARY_AXES` | `control_surface_mixing.py:29-33` | role → axis decomposition |
| `axis_control_name` | `control_surface_mixing.py:76-84` | `[{role}]{axis}_{wing_key}_{xsec_index}` |
| `assert_unique_control_names` | `control_surface_mixing.py:149-164` | raises on any duplicate |
| `_validate_mix_fields` | `app/schemas/aeroplaneschema.py:51-78` | role-gated mixing validation |
| turbulator optimiser | `app/services/turbulator_optimizer_service.py` | xtr sweep, `ΔCD0`, warnings |

### Data model 🟢

Six tables, all cascading on delete:

```
wings ──1:N──▶ wing_xsecs ──1:1──▶ wing_xsec_details ──1:N──▶ wing_xsec_spares
                                          │
                                          ├──1:1──▶ wing_xsec_trailing_edge_devices ──1:1──▶ wing_xsec_ted_servos
                                          └──1:1──▶ wing_xsec_turbulators
```

`wings`: `name`, `symmetric` (default **`True`**), `design_model`
(`'wc'` | `'asb'` | `NULL`), `aeroplane_id` FK `ON DELETE CASCADE`.
`wing_xsecs`: `xyz_le` (JSON, **metres**), `chord` (m), `twist` (deg),
`dihedral` (deg, nullable — gh-951), `airfoil` (str/URL), `sort_index`.
`wing_xsec_details` (1:1, unique FK): `x_sec_type`, `tip_type`,
`number_interpolation_points`.
`wing_xsec_spares`: **all six dimensional columns in millimetres** (gh-402);
`spare_vector` dimensionless.
Full column lists: `data-dictionary.md` §Module: wing-design. 🟢

## Main Flow

### F1 — Create a wing from ASB geometry (`PUT /{wing_name}`) 🟢

1. Resolve the aeroplane by UUID (404 if absent).
2. Validate `AsbWingSchema`: `x_secs` `min_length=2`, and
   `validate_last_xsec_has_no_segment_details` rejects any segment field on the
   terminal station (`aeroplaneschema.py:666-680`).
3. Duplicate wing name → `ValidationError` → **422**
   (`wing_service.py:285-289`). *Note the asymmetry with `fuselage-design`,
   which raises `ConflictError` → 409 for the same situation.*
4. `WingModel.from_dict` blanks all six segment fields on the last x-section
   (`aeroplanemodel.py:489-490`) — layer 2 of the terminal-station rule.
5. Stamp `design_model = 'asb'`.
6. Auto-sync the component-tree group `wing:<name>` (gh#108,
   `wing_service.create_wing:298-300`) via a lazy import into
   `component_tree_service`.

### F2 — Create a wing from a `WingConfiguration` (`POST /{wing_name}/from-wingconfig`) 🟢

Identical to F1 except the payload is the millimetre `WingConfiguration`, the
converter runs at `scale = 0.001` (mm → m, `wing_service.py:313`) and
`design_model = 'wc'` is stamped (`:341`).

### F3 — Read a wing as a `WingConfiguration` (`GET /{wing_name}/wingconfig`) 🟢

`wing_model_to_wing_config(wing, scale=1000.0)` (`wing_service.py:372`).
`_scale_asb_wing_geometry_schema` multiplies `xyz_le` and `chord` by `scale`
(`model_schema_converters.py:452-470`); spar origins go through
`scale_db_origin_to_config` with `factor = 0.001 × scale`, so `scale = 1000.0`
returns the stored millimetres verbatim and `scale = 1.0` returns metres
(`spare_origin_preservation.py:62-78`).

### F4 — Spar write path (unit boundary) 🟢

```
request (metres) ──_convert_spare_to_mm──▶ DB (millimetres)
DB (millimetres) ──_convert_spare_to_meters──▶ response (metres)

_MM_TO_M = 0.001   (wing_service.py:43)
_M_TO_MM = 1000.0  (wing_service.py:46)

converted fields: spare_support_dimension_width, spare_support_dimension_height,
                  spare_length, spare_start, spare_origin
untouched:        spare_vector   (dimensionless unit direction)
```

### F5 — Spar geometry preservation and recompute (gh-1053 / gh-352 / gh-362) 🟢

1. On model→config conversion, `_resolve_spare_vectors_and_origins` normally
   **clears and recomputes** every spar's origin and vector — the unit-leak guard.
2. `should_preserve_normal_spare` exempts a spar that is **all three** of:
   `spare_mode == "normal"`, a fully explicit 3-component `spare_origin`, and a
   `spare_vector` (`spare_origin_preservation.py:43-59`). Everything else
   (`standard` / `follow` / `standard_backward` / `orthogonal_backward`) still
   goes through the recompute path.
3. `_recompute_spare_vectors` (`wing_service.py:854-873`) rebuilds a
   `WingConfiguration` at `scale = 1.0` (metres), reads back each segment's
   computed `spare_vector` / `spare_origin`, and writes the origin back
   **× 1000** as millimetres.
4. On `ImportError` (aarch64 without CadQuery) or `FileNotFoundError` (missing
   airfoil `.dat`) step 3 logs a warning and continues — wing CRUD stays
   available on platforms without a geometry kernel.

### F6 — Terminal dihedral persistence (gh-951) 🟢

```
station i airfoil = segments[i].root_airfoil        for i < N
station N airfoil = segments[-1].tip_airfoil        (terminal rib)
dihedral          = airfoil.dihedral_as_rotation_in_degrees
```

(`_station_dihedral`, `model_schema_converters.py:998-1015`.) The terminal rib's
local-x rotation moves no outboard station, leaves no trace in `xyz_le` and is
therefore unrecoverable from positions — hence the explicit
`wing_xsecs.dihedral` column. `NULL` on legacy rows means "derive from geometry".

### F7 — Structural pipeline 🟢

**Stage 1 — section-modulus sizing** (`spar_sizing.py`, gh-1008). Units: `M` in
N·m, `σ` in MPa (= N/mm²), dimensions in mm, `W` in mm³, mass in kg.

```
M_design(y) = |M(y)| · g_limit · j                    (l.9-13)
erf_W       = M_design · 1000 / σ_allow               (l.78-88)
outer(y)    = chord(y) · (t/c)(y) · packing_factor    (l.13)

Section moduli (mm³):
  rectangular  W = b·h²/6                             (l.40-45)
  capped (I/C) W = b·(H³ − h³)/(6·H)                  (l.48-54)
  solid rod    W = d³/10                              (l.57-62)
  tube         W = π·(Da⁴ − Di⁴)/(32·Da)              (l.65-70)

Inverse solves (solve_dimension, l.96+):
  tube         Di = (Da⁴ − 32·erf_W·Da/π)^(1/4)       (l.137-146)
  rod          d  = (10·erf_W)^(1/3)                  (l.159)
  rectangular  b  = 6·erf_W / h²                      (l.182)
  capped       h  = (H³ − 6·H·erf_W/b)^(1/3)          (l.196-208)

Guard: σ_allow ≤ 0 → ValueError                       (l.86-87)
Fallback t/c when airfoil data is unavailable: _TC_FALLBACK = 0.12  (l.32)
```

`SparSizingParams` defaults (`app/schemas/spar_sizing.py:12-51`):
`safety_factor_j = 1.5` (`> 0`), `packing_factor = 0.8` (`0 < x ≤ 1`),
`shape ∈ {tube, rod, rectangular, capped}`, `cap_width_mm` required only for
`capped`, `material_id` → a `Component` of type `material` carrying
`allowable_bending_stress_mpa`.

**Stage 2 — station sampling** (`build_stations_from_geometry`, l.681-746),
`n_span` stations root→tip (default 6):

```
y_spans   = linspace(0, 1, n_span);  y_spans[0] → _ROOT_EPS = 1e-3
x_c       = requested x/c, else the section's max-thickness location
clr       = (1 − packing_factor)/2 · thickness
band_lo   = bottom_z + clr ;  band_hi = top_z − clr
M_design  = |moment_fn(y_span)| · g_limit · j       (defaults g = 3.0, j = 1.5)
required_od = solve_dimension("rod", erf_W, outer = band_hi − band_lo)
```

`_ROOT_EPS` exists because the `y_span = 0` slice is a pinched, zero-thickness
section on a real loft and would poison the governing max-moment root station
(gh-1037 #4).

**Rear-spar clearance (gh-1059)**, applied to *computed* spars only:

```
rear_spar_x_c_with_clearance(requested, hinge_x_c, clearance = 0.03):
    if hinge_x_c is None: return requested
    return max( min(requested, hinge_x_c − 0.03), 0.05 )

_REAR_CLEARANCE_FRACTION = 0.03 ;  _MIN_REAR_X_C = 0.05   (spar_solver.py:181-221)
```

**Stage 3 — layout solve** (`plan_spar` / `solve_spar_plan`, l.342, 619-672).
Per half-span: greedy straight-piece fit, split into telescoping runs wherever
the strength-required OD exceeds the containment band. Then:

- **front joint** — `_inboard_collinear` compares the two halves' root
  `center_z` within `tol_mm = 5.0`; equal → `"continuous"`, else
  `"reinforcement+joiner"` with a generated reinforcement piece. A single-half
  surface (vertical stabiliser, gh-1091) is forced to `"continuous"` rather than
  indexing into the empty half.
- **rear joint** — `"continuous"` when a straight collinear rod through `y = 0`
  stays inside the band on both halves, otherwise `"bent-pin"`.
- **utilisation** — `utilisation = od / max(tightest_band, 1e-6)`;
  `feasible = od ≤ tightest`. Reported honestly and may exceed 1.0; the
  infeasibility message names the governing station and suggests a capped/box
  spar (`_piece_from_run_with_od`, l.490-529). No silent clamping.
- **negligible-load tip (gh-1076)** — `NEGLIGIBLE_OD_FLOOR_MM = 1.0`; a tip
  station whose required OD falls below 1 mm produces **no piece** and the
  region is reported as `front_no_spar_from_y` / `rear_no_spar_from_y` instead
  of a degenerate Ø≈0 tube (l.44-53, 438-457).
- **bore** — `_bore_for` reconstructs `erf_W` from the governing rod OD via
  `required_section_modulus_from_od(od) = od³/10` and solves the tube path;
  falls back to `wall_factor = 0.6` of the OD when strength wants a solid
  (l.460-487). `telescope_clearance_mm = 0.5` is the radial slip-fit gap.

The whole solver is deliberately **CAD-free decision logic** so every branch
runs on the CI fast tier with hand-built `StationData` (`spar_solver.py:1-24`).

**Stage 4 — section-geometry seam** (`section_geometry.py:160-219`, gh-1046).
`SectionGeometry` recovers `(y/span, x/c)` in `"analytic"` mode (default —
blends segment airfoils via `WingConfiguration.get_points_on_surface`, builds no
solid) or `"solid"` mode (builds the RIGHT-half loft once via `WingLoftCreator`
and slices it; `sample` groups requests by `y_span` so each plane is cut once).
`points_per_edge` is clamped to `[8, 4096]`. Raises
`SectionGeometryUnavailableError` when CadQuery is absent. The analytic path
exists to avoid the documented **~13 s** `WingLoftCreator` bottleneck.

### F8 — Control-surface role → axis decomposition (gh-772) 🟢

```
_DUAL_ROLE_AXES = { "elevon":      ("pitch", "roll"),
                    "flaperon":    ("lift",  "roll"),
                    "ruddervator": ("pitch", "yaw") }      (l.29-33)
PRIMARY_AXES   = {"pitch", "lift"}   # symmetric component
SECONDARY_AXES = {"roll",  "yaw"}    # antisymmetric component
```

A dual-role surface emits **two** AVL `CONTROL` variables on the same section
(AVL sums multiple CONTROL lines per section):

| axis | `sgn_dup` | gain | `symmetric` | baseline deflection |
|---|---|---|---|---|
| primary | `+1.0` | `mix_gain_primary` | `True` | the surface's deflection |
| secondary | `−1.0` | `mix_gain_secondary` | `False` | **`0.0`** |

The secondary baseline is 0 so the AeroBuildup fallback never feeds a roll/yaw
deflection into the single-axis ASB model (l.126-128). A single-axis role keeps
its existing tagged name and `±1` sign verbatim (l.134-146).

Naming: `axis_control_name` → `[{role}]{axis}_{wing_key}_{xsec_index}`, e.g.
`[ruddervator]pitch_htail_1` (l.76-84). AVL silently collapses identically named
`CONTROL` variables into a single DOF, so `assert_unique_control_names` raises on
any duplicate **before** the geometry file is written (l.149-164).

Write-time gating (`_validate_mix_fields`, `aeroplaneschema.py:51-78`):
`differential_ratio ≠ 1.0` only for
`DIFFERENTIAL_ROLE_VALUES = {aileron, elevon, flaperon, ruddervator}`;
`mix_gain_secondary ≠ 1.0` only for
`DUAL_ROLE_VALUES = {elevon, flaperon, ruddervator}`. Comparison uses
`math.isclose(rel_tol=1e-9, abs_tol=1e-9)`; a `None` role (partial patch) skips
the check entirely. Schema ranges: `mix_gain_*` `0 < x ≤ 5`,
`differential_ratio` `0.3 < x ≤ 3`.

### F9 — Turbulator optimiser (gh-934) 🟢

```
XTR_GRID              = linspace(0.2, 0.9, 15)     # x/c sweep         (l.53)
_ALPHA_GRID           = linspace(-4.0, 14.0, 37)   # cd-at-CL lookup   (l.60)
_CONFIDENCE_THRESHOLD = 0.80                       # warning gate      (l.56)

cd_clean = cd(CL, Re, xtr_upper = 1.0)             # natural-transition baseline
i_opt    = argmin over FINITE cd values
xtr_opt  = XTR_GRID[i_opt]
delta_cd = cd_tripped − cd_clean

ΔCD0 = symmetry_factor · Σ (Δcd_i · S_i) / S_ref
       symmetry_factor = 2 for a symmetric wing, because section_aoa_service
       returns half-span sections only
```

Warnings — never silent fallbacks (ADR 0012) — for all-NaN `cd` (no optimum),
mean `analysis_confidence < 0.80`, and a boundary optimum
(`i_opt ∈ {0, len−1}` → the true minimum may lie outside `[0.2, 0.9]`)
(`turbulator_optimizer_service.py:223-268, 294-331`).

## Alternative Flows

- **Terminal-station write:** any segment-scoped field on the last station is
  rejected at whichever layer is reached first — schema (422 via
  `RequestValidationError`), model (silently blanked on `from_dict`), or service
  (`ValidationError` → 422). 🟢
- **Duplicate wing name:** aligns to `ConflictError` → **409**, matching
  `fuselage_service` (`Q-FD-1`, maintainer-answered). 🟢 The divergence is
  resolved in favour of 409: a *create* whose name collides with an existing
  sibling is a conflict with persisted state, not an unreadable payload. Today
  it is still a 422; the change is client-visible and must land before
  TypeScript client generation (`Q-CC-11`).
- **Missing geometry kernel:** `_recompute_spare_vectors` logs and continues;
  `SectionGeometry` raises `SectionGeometryUnavailableError`. Wing CRUD stays
  functional, the structural pipeline does not. 🟢
- **Infeasible spar layout:** `feasible = false`, `utilisation > 1.0`, a message
  naming the governing station. No exception, no clamp. 🟢
- **Negligible-load tip:** no piece emitted; the region is reported through
  `front_no_spar_from_y` / `rear_no_spar_from_y`. 🟢
- **Optimiser anomaly:** warning appended to the response; the numeric result is
  still returned unmodified. 🟢
- **Duplicate control-variable name:** raises before any AVL file is written. 🟢
- **`servo` union:** `WingXSecTrailingEdgeDeviceModel.servo` returns
  `servo_data` when present, otherwise the integer `servo_index`
  (`aeroplanemodel.py:183-187`). 🟢 **`servo_data` is canonical for new records;
  `servo_index` is deprecated** (`Q-WD-3 ①`). The union stays readable so
  existing rows resolve, but nothing new writes the bare index.

## Dependencies

- **`aeroplane-core`** — every route resolves an aeroplane by UUID first; wing
  create/delete call back into `component_tree_service` for group auto-sync
  (gh#108), a two-way dependency broken by lazy imports.
- **`app/converters/model_schema_converters.py`** — the conversion hub shared
  with `fuselage-design`, `cad-generation`, `aero-analysis`, `avl-integration`
  and `openvsp-import`.
- **`cad-designer-topology`** — `WingConfiguration`, `WingSegment`, `Spare`,
  `TrailingEdgeDevice`, `Turbulator`, `Airfoil` (millimetre world, frozen —
  ADR 0002).
- **`airfoil-catalog`** — station `airfoil` values resolve to `.dat` files under
  `AIRFOILS_DIR`; a missing file degrades the spar-vector recompute.
- **`avl-integration` / `aero-analysis`** — consume `control_surface_mixing` as
  the single source of truth for control names and axes.
- **`powertrain` / components catalogue** — `material_id` for spar sizing,
  `component_id` for servos.
- **CadQuery** (optional, absent on `linux/aarch64`) — needed by
  `SectionGeometry` `"solid"` mode and the spar-vector recompute (ADR 0017).

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Millimetres in `cad_designer`, metres in the DB and AeroSandbox | ADR 0001; `wing_service.py:43, 46` | 🟢 |
| `wing_xsec_spares` stores millimetres inside the metre database, converted at the service boundary | gh-402; `wing_service.py:49-88` | 🟢 |
| The terminal-station rule is enforced three times rather than once | `aeroplaneschema.py:666-680`, `aeroplanemodel.py:489-490`, `wing_service.py:151-156` | 🟢 |
| Terminal dihedral is persisted, not derived | gh-951; `aeroplanemodel.py:219-225` | 🟢 |
| Explicit `normal` spars are exempted from the unit-leak recompute | gh-1053; `spare_origin_preservation.py:43-59` | 🟢 |
| A control-surface role decomposes into one or two axes, not into a single tagged name | ADR 0008; `control_surface_mixing.py:29-33` | 🟢 |
| `SgnDup` is a sign flag; `differential_ratio` never enters the aero solution | `control_surface_mixing.py:14-15`; `aeroplaneschema.py:372-381` | 🟢 |
| Structural decision logic is CAD-free so it runs on the CI fast tier | `spar_solver.py:1-24` | 🟢 |
| Infeasibility and optimiser anomalies are reported, never clamped or defaulted | ADR 0012; `spar_solver.py:490-529`, `turbulator_optimizer_service.py:223-268` | 🟢 |
| Section sampling defaults to an analytic path | gh-1046; `section_geometry.py:160-219` | 🟢 |
| A wing records how it was authored (`design_model`) rather than inferring CAD capability | `wing_service.py:292, 341` | 🟢 |
| Duplicate name answers 409 on both paths | `wing_service.py:285-289` aligns to `fuselage_service.py:80-84` | 🟢 (`Q-FD-1`) |
| `servo` union is readable; `servo_data` is canonical for new records | `aeroplanemodel.py:183-187` | 🟢 (`Q-WD-3 ①`) |

## Internal State

The module is stateless between requests. Persistent state:

- `wings` / `wing_xsecs` / `wing_xsec_details` — the station-segment topology.
- `wing_xsec_spares` — spar geometry in **millimetres**; the solver writes
  `spare_origin` / `spare_vector` back here through `_sync_spares_for_xsec`.
- `wing_xsec_trailing_edge_devices` (+ `wing_xsec_ted_servos`) — control-surface
  geometry, mixing gains and the commanded `deflection_deg`.
- `wing_xsec_turbulators` — per-segment forced-transition definition.

Derived-at-read, never persisted: the `control_surface` projection on
`WingXSecModel` (`aeroplanemodel.py:241-276`), control-axis names and gains, the
spar plan, and the turbulator optimiser result.

## Observability

- `logger.warning` on the degraded spar-vector recompute path
  (`ImportError` / `FileNotFoundError`, `wing_service.py:872`). 🟢
- Structured **design warnings** in the response bodies of the spar solver and
  the turbulator optimiser, rather than log-only failures (ADR 0012). 🟢
- 5xx are logged with `logger.exception` by the shared endpoint error mapping;
  no module-specific metrics, traces or events. 🟢
- Geometry mutations must be fanned out through `invalidation_service`
  (`mark_ops_dirty`) so dependent operating points become `DIRTY`. 🟡 INFERRED
  as a requirement on new mutating paths, from the cross-module note.

## Risks and Gaps

- 🟡 **`units` describes the wire format only** (`Q-WD-2`). `WingUnitsSchema` /
  `WingModel.units` declare `detail_length: "m"` while `wing_xsec_spares` stores
  mm, but the API delivers metres, so the wire contract is consistent. **No
  per-field storage-unit override is added** — ADR 0019 rule 4 forbids exposing
  an internal representation. The `SpareDetailSchema` descriptions are clarified
  instead. Derived from the ADR, so INFERRED.
- 🟢 **Open bug #955 is resolved structurally** (`Q-WD-1`,
  maintainer-answered): `control_surface_mixing` owns a resolver that trim,
  retrim and stability are **required** to call, and **the silent ±25° fallback
  is removed**. The mixing layer generates the canonical names; keying on the raw
  DB TED name stops being possible rather than merely being discouraged.
- 🟢 **`servo_data` is canonical for new records; `servo_index` is deprecated**
  (`Q-WD-3 ①`, maintainer-answered). The `Servo | int` union stays *readable* so
  existing rows resolve, but nothing new writes the bare index — a union by
  convention is a contract a client cannot type against.
- 🟢 **A `NULL` servo dimension is rejected on read, not silently defaulted**
  (`Q-WD-3 ②`). Substituting a plausible number for a missing servo dimension
  would put an invented value into a CAD build — the undeclared substitution
  ADR 0020 forbids. The error names the row and the field.
- 🟢 **The topology classes are the single authority for defaults**
  (`Q-WD-3 ③`, ADR 0022). `NULL` in the DB means *"not stated"*; the effective
  value comes from `TrailingEdgeDevice` at build time. The DB must **not** acquire
  a second set of defaults, which would diverge silently on any edit.
- 🟢 **Duplicate-name divergence resolved: 409 everywhere** (`Q-FD-1`,
  maintainer-answered). `create_wing`'s 422 is the outlier and aligns to
  `ConflictError` → 409. Discriminator: **409** for a *create* conflicting with
  persisted state, **422** for *processing* an internally inconsistent
  configuration — so `Q-WD-9`'s duplicate-control-name 422 correctly stays 422.
- 🟢 **Known frozen bug, deliberately unfixed.**
  `cad_designer/.../WingConfiguration.py` contains a dead perpendicular-spare
  branch. The topology layer is frozen (ADR 0002) and the project does not fix
  it; recorded so later analysis does not re-discover it as new.
- 🟡 **Platform-conditional capability.** Without CadQuery the module serves CRUD
  but cannot recompute spar vectors or run `"solid"` section sampling; the
  degradation is a log line, not an API-visible flag.
