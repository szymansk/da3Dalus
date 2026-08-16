# spar-sizing — Technical Design

> Use-case design, nested under the module [`wing-design`](../design.md).
> Focuses on HOW this use case is built, derived from the legacy code.
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Full module REST contract: [`../contracts.md`](../contracts.md).

## Interface

### Sizing surface — `app/services/spar_sizing.py` 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `required_section_modulus` | `(moment_nm, sigma_allow_mpa, g_limit, j) -> float` | `erf_W` in **mm³** | raises `ValueError` when `σ_allow ≤ 0` (l.86-87) |
| `solve_dimension` | `(shape, erf_W, outer, **shape_kwargs) -> float` | the solved dimension in **mm** | one closed-form inverse per shape (l.96+) |
| `_TC_FALLBACK` | constant | `0.12` | thickness ratio when airfoil data is unavailable (l.32) |
| shape moduli | `W_rect`, `W_capped`, `W_rod`, `W_tube` | mm³ | l.40-70 |

### Solver surface — `cad_designer/airplane/geometry/spar_solver.py` 🟢

| Symbol | Purpose | Line |
|---|---|---|
| `build_stations_from_geometry` | sample `StationData` root→tip | l.681-746 |
| `rear_spar_x_c_with_clearance` | gh-1059 hinge-clearance guard | l.181-221 |
| `plan_spar` | plan one spar (front or rear) over a half-span | l.342 |
| `solve_spar_plan` | orchestrate both spars, both halves, joints | l.619-672 |
| `_piece_from_run_with_od` | build a piece; compute utilisation and feasibility | l.490-529 |
| `_bore_for` | reconstruct `erf_W` from the governing rod OD, solve the tube | l.460-487 |
| `_inboard_collinear` | front-joint decision from the two halves' root `center_z` | — |
| `NEGLIGIBLE_OD_FLOOR_MM` | constant `1.0` — below this, emit no piece | l.44-53, 438-457 |
| `_ROOT_EPS` | constant `1e-3` | — |
| `_REAR_CLEARANCE_FRACTION` / `_MIN_REAR_X_C` | `0.03` / `0.05` | l.181-221 |
| `telescope_clearance_mm` | `0.5` radial slip-fit gap | — |

### Geometry seam — `cad_designer/airplane/geometry/section_geometry.py` 🟢

| Symbol | Purpose | Line |
|---|---|---|
| `SectionGeometry` | recovers `(y/span, x/c)` points, `mode ∈ {"analytic", "solid"}` | l.160-219 |
| `SectionGeometry.sample` | batch sampling; groups requests by `y_span` in solid mode | — |
| `SectionGeometryUnavailableError` | raised when CadQuery is absent | l.181-184 |

### Parameters — `app/schemas/spar_sizing.py:12-51` 🟢

| Field | Type | Default | Constraint |
|---|---|---|---|
| `shape` | `"tube" \| "rod" \| "rectangular" \| "capped"` | — | required |
| `safety_factor_j` | float | `1.5` | `> 0` |
| `packing_factor` | float | `0.8` | `0 < x ≤ 1` |
| `cap_width_mm` | float \| None | `None` | **required only for** `capped` |
| `material_id` | int | — | must point to a `Component` of type `material` carrying `allowable_bending_stress_mpa` |

Station-sampling defaults: `n_span = 6`, `g_limit = 3.0`, `j = 1.5`.

### Orchestration and persistence 🟢

`app/services/spar_plan_service.py` orchestrates the plan;
`app/services/spar_insert_service.py` writes the result back onto the wing's
`wing_xsec_spares` rows (**millimetres** — see
[`../cross-section-crud/design.md`](../cross-section-crud/design.md) §F5/F6 for
the unit boundary and the gh-1053 preservation rule that keeps the solved
origins alive across the next read).

## Main Flow

### Stage 1 — Section-modulus sizing (`spar_sizing.py`, gh-1008) 🟢

Reference: *kirch Hauptholm*. **Units are load-bearing:** `M` in N·m, `σ` in
MPa (= N/mm²), dimensions in mm, `W` in mm³, mass in kg. The `1000` in `erf_W`
is exactly the N·m → N·mm conversion.

```
M_design(y) = |M(y)| · g_limit · j                    (l.9-13, docstring)
erf_W       = M_design · 1000 / σ_allow               (l.78-88)
outer(y)    = chord(y) · (t/c)(y) · packing_factor    (l.13)
```

Section moduli, mm³ (l.40-70):

```
rectangular   W = b · h² / 6
capped (I/C)  W = b · (H³ − h³) / (6 · H)
solid rod     W = d³ / 10
tube          W = π · (Da⁴ − Di⁴) / (32 · Da)
```

Closed-form inverses (`solve_dimension`, l.96+):

```
tube          Di = (Da⁴ − 32 · erf_W · Da / π) ^ (1/4)   (l.137-146)
rod           d  = (10 · erf_W) ^ (1/3)                  (l.159)
rectangular   b  = 6 · erf_W / h²                        (l.182)
capped        h  = (H³ − 6 · H · erf_W / b) ^ (1/3)      (l.196-208)
```

Guards: `σ_allow ≤ 0` raises `ValueError` (l.86-87) — the material schema
permits `0`, so the division is protected at the formula, not at the caller.
When airfoil thickness data is unavailable the ratio falls back to
`_TC_FALLBACK = 0.12` (l.32).

### Stage 2 — Station sampling (`build_stations_from_geometry`, l.681-746) 🟢

For `n_span` stations root→tip (default 6):

```
y_spans = linspace(0, 1, n_span);  y_spans[0] → _ROOT_EPS = 1e-3
   (the y_span = 0 slice is a pinched, zero-thickness section on a real loft
    and would poison the governing max-moment root station — gh-1037 #4)

x_c         = requested x/c, else the section's max-thickness location
clr         = (1 − packing_factor) / 2 · thickness
band_lo     = bottom_z + clr
band_hi     = top_z    − clr
M_design    = |moment_fn(y_span)| · g_limit · j        (defaults g = 3.0, j = 1.5)
required_od = solve_dimension("rod", erf_W, outer = band_hi − band_lo)
```

Note that the **required OD is always solved as a rod**, regardless of the
requested `shape` — the rod diameter is the strength-equivalent envelope the
containment band must accommodate. The requested shape re-enters at Stage 3 via
`_bore_for`.

### Stage 2b — Rear-spar hinge clearance (gh-1059) 🟢

A *computed* rear/torsion spar must never overlap the movable surface:

```
rear_spar_x_c_with_clearance(requested, hinge_x_c, clearance = 0.03):
    if hinge_x_c is None:
        return requested
    return max( min(requested, hinge_x_c − 0.03), 0.05 )
```

`_REAR_CLEARANCE_FRACTION = 0.03`, `_MIN_REAR_X_C = 0.05`
(`spar_solver.py:181-221`). The guard is explicitly documented as applying only
to computed spars — a designer may still place a reinforcing spar inside a
control surface manually.

### Stage 3 — Layout solve (`plan_spar` l.342, `solve_spar_plan` l.619-672) 🟢

Per half-span: greedy straight-piece fit, split into **telescoping runs** where
the strength-required OD exceeds the containment band. Then:

1. **Front joint** — `_inboard_collinear` compares the two halves' root
   `center_z` within `tol_mm = 5.0`:
   - equal → `"continuous"`;
   - otherwise → `"reinforcement+joiner"`, with a generated reinforcement piece.
   - A **single-half** surface (e.g. a vertical stabiliser, gh-1091) is forced
     to `"continuous"` rather than indexing into the empty half.
2. **Rear joint** — `"continuous"` when a straight collinear rod through `y = 0`
   stays inside the band on both halves, otherwise `"bent-pin"`.
3. **Utilisation** (`_piece_from_run_with_od`, l.490-529) — reported honestly
   and may exceed 1.0:

   ```
   utilisation = od / max(tightest_band, 1e-6)
   feasible    = od ≤ tightest_band
   ```

   The infeasibility message names the governing station and suggests a capped
   or box spar. **No silent clamping** (ADR 0012).
4. **Negligible-load tip** (gh-1076) — `NEGLIGIBLE_OD_FLOOR_MM = 1.0`. A tip
   station whose required OD falls below 1 mm produces **no piece**; the region
   is reported as `front_no_spar_from_y` / `rear_no_spar_from_y` instead of a
   degenerate Ø≈0 tube (l.44-53, 438-457).
5. **Bore** (`_bore_for`, l.460-487) — reconstruct `erf_W` from the governing
   rod OD and solve the tube path:

   ```
   required_section_modulus_from_od(od) = od³ / 10
   Di = (od⁴ − 32 · erf_W · od / π) ^ (1/4)
   fallback when strength wants a solid:  bore = wall_factor · od,  wall_factor = 0.6
   telescope_clearance_mm = 0.5          # radial slip-fit gap between nested tubes
   ```

The whole solver is deliberately **CAD-free decision logic**, so every branch
runs on the CI fast tier with hand-built `StationData` (`spar_solver.py:1-24`).

### Stage 4 — Section-geometry seam (`section_geometry.py`, gh-1046) 🟢

`SectionGeometry` recovers `(y/span, x/c)` points in two modes:

| Mode | Behaviour |
|---|---|
| `"analytic"` (default) | blends segment airfoils via `WingConfiguration.get_points_on_surface`; **no solid is built** |
| `"solid"` | builds the RIGHT-half loft once via `WingLoftCreator` and slices it; `sample` groups requests by `y_span` so each cutting plane is used once |

`points_per_edge` is clamped to `[8, 4096]`. The docstring records that the
analytic path exists to avoid the **~13 s** `WingLoftCreator` bottleneck.
`SectionGeometryUnavailableError` is raised when CadQuery is absent
(l.160-219, guard at l.181-184).

### Stage 5 — Persistence 🟢

`spar_insert_service` writes the solved geometry back onto `wing_xsec_spares`.
Solved spars are written with `spare_mode == "normal"` plus an explicit
3-component `spare_origin` and `spare_vector`, which is exactly the condition
`should_preserve_normal_spare` uses to exempt them from the clear-and-recompute
path on the next read (gh-1053, see
[`../cross-section-crud/design.md`](../cross-section-crud/design.md) §F3).
🟡 INFERRED — the preservation predicate is confirmed; that the insert service
is what produces the qualifying rows is the necessary consequence.

## Alternative Flows

- **`σ_allow ≤ 0`:** `ValueError` from `required_section_modulus` (l.86-87). It
  is a `ValueError`, **not** a domain `ValidationError` — the service layer is
  responsible for translating it if it must reach HTTP. 🟡
- **Airfoil thickness unavailable:** `_TC_FALLBACK = 0.12` is used; no error.
- **Required OD exceeds the tightest band:** the piece is still emitted, with
  `feasible = false` and `utilisation > 1.0`, and a message naming the governing
  station. The plan is deliberately *returned*, not rejected.
- **Required OD below 1.0 mm at the tip:** no piece; `front_no_spar_from_y` /
  `rear_no_spar_from_y` records where the spar stops.
- **Single-half surface:** front joint forced to `"continuous"`; the empty half
  is never indexed (gh-1091).
- **No hinge on the segment:** `rear_spar_x_c_with_clearance` returns the
  requested `x/c` unchanged.
- **Hinge so far forward that `hinge_x_c − 0.03 < 0.05`:** the `max(..., 0.05)`
  floor wins; the spar sits at `x/c = 0.05` and the clearance is *not* honoured.
  🟡 INFERRED consequence — the floor takes precedence over the clearance, and
  no warning is documented for this case.
- **CadQuery absent in `"solid"` mode:** `SectionGeometryUnavailableError`.
  In `"analytic"` mode the sampling proceeds normally.
- **`points_per_edge` outside `[8, 4096]`:** silently clamped to the bound.

## Dependencies

- **`app/schemas/spar_sizing.py` (`SparSizingParams`)** — the validated input
  contract.
- **`Component` of type `material`** — supplies `allowable_bending_stress_mpa`
  via `material_id`. Owned by the COTS/components module.
- **`cad_designer/airplane/geometry/section_geometry.py`** — the only place this
  use case can touch a geometry kernel; isolated deliberately so the solver
  stays CAD-free (BR-W12).
- **`cad_designer` topology (`WingConfiguration`, `WingLoftCreator`)** —
  read-only (ADR 0002); reached through the `SectionGeometry` seam only.
- **`aero-analysis`** — supplies `moment_fn(y_span)`, the bending-moment
  distribution. 🟡 INFERRED: the solver takes a callable; which service produces
  it was not captured in the source analysis.
- **[`../cross-section-crud/`](../cross-section-crud/design.md)** — owns the
  `wing_xsec_spares` rows this use case writes, and the mm↔m boundary.
- **`app/services/spar_plan_service.py` / `spar_insert_service.py`** —
  orchestration and persistence.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Strength is expressed as a required **section modulus**, inverted per shape, rather than a stress check per candidate dimension | `spar_sizing.py:78-88`, `:96+` (gh-1008) | 🟢 |
| The required OD is always solved as a **rod**, whatever shape is requested; the shape re-enters only at bore reconstruction | `spar_solver.build_stations_from_geometry:681-746`, `_bore_for:460-487` | 🟢 |
| The division guard lives at the formula, not the caller, because the material schema admits `σ_allow = 0` | `spar_sizing.py:86-87` | 🟢 |
| The root station is sampled at `1e-3`, not `0`, to avoid the pinched loft slice | `_ROOT_EPS`, gh-1037 #4 | 🟢 |
| Infeasibility is reported with a named governing station and a concrete remedy, never clamped | `_piece_from_run_with_od:490-529`; ADR 0012 | 🟢 |
| A negligible-load region is represented by **absence of a piece plus a boundary marker**, not by a tiny piece | `NEGLIGIBLE_OD_FLOOR_MM = 1.0`, l.438-457 (gh-1076) | 🟢 |
| The hinge-clearance guard is scoped to computed spars only, preserving manual designer intent | `spar_solver.py:181-221` (gh-1059) | 🟢 |
| The decision logic is kept free of CAD imports so it is fully testable on the fast tier | `spar_solver.py:1-24` | 🟢 |
| Section geometry defaults to an analytic blend rather than slicing a solid, to avoid a ~13 s build | `section_geometry.py:160-219` (gh-1046) | 🟢 |
| `points_per_edge` is clamped rather than validated, so a bad input degrades instead of failing | `section_geometry.py` | 🟢 (the choice of clamp-over-raise is 🟡) |

## Internal State

The sizing formulas and the solver are **pure functions** — no session, no
cache, no persistent state. `StationData` is an in-memory value object built
either from real section geometry or, in tests, by hand.

Persistent state is written only at Stage 5, into `wing_xsec_spares`
(**millimetres**, gh-402), with `spare_mode = "normal"` plus explicit
`spare_origin` / `spare_vector` so the gh-1053 preservation predicate keeps the
solved values alive.

`SectionGeometry` in `"solid"` mode holds one built loft for the lifetime of the
object and groups `sample` requests by `y_span` so each cutting plane is used
once — the only caching in this use case. 🟢

## Observability

- The infeasibility path produces a **message naming the governing station and
  suggesting a capped/box spar** — a user-facing design warning rather than a
  log line (`spar_solver.py:490-529`, ADR 0012). 🟢
- `front_no_spar_from_y` / `rear_no_spar_from_y` are reported fields, not logs —
  the absence of a spar is part of the contract. 🟢
- `SectionGeometryUnavailableError` is a named exception, so the missing
  geometry kernel is distinguishable from a generic import failure. 🟢
- No metrics or traces are emitted by this use case. 🟢
- 🔴 The `~13 s` loft cost is documented in a docstring but not instrumented;
  there is no timing signal when `"solid"` mode is used. **Not addressed by the
  validation interview** — instrumentation was never put to the maintainer, and
  under ADR 0024 (single-user desktop) telemetry has no consumer, so this is left
  open rather than assumed away.

## Risks and Gaps

- 🟡 **`required_section_modulus`'s bare `ValueError` is unreachable in
  production, and is nevertheless promoted to a domain exception** (`Q-WD-9 ②`,
  resolved by code lookup). Its only caller validates first with a real
  `ValidationError` → 422 (`analysis_service.py:2136-2150`), and
  `compute_spar_sizing` has exactly one caller, so there is no bypass today — it
  is **confirmed safe**, not a live defect. It becomes a domain exception anyway
  so that a future second caller cannot reintroduce the 500. Resolved by lookup
  rather than by decision, so INFERRED.
- 🟢 **The `_MIN_REAR_X_C` clamp order is a confirmed defect and is fixed**
  (`Q-WD-8 ②`, maintainer-answered). `return max(safe, _MIN_REAR_X_C)`
  (`spar_solver.py:221`) applies the floor **after** the clearance, so with
  `_MIN_REAR_X_C = 0.05` it erodes the clearance for any `hinge_x_c < 0.08` and
  places the rear spar **inside** the control surface with no warning. The hinge
  guard is wired and the clamp order corrected — the floor must not be able to
  override a clearance.
- 🟢 **`moment_fn` provenance is settled, and there is NO double application of
  the safety factor** (`Q-WD-8`, cleared by code lookup). `g_limit` / `j` are
  applied **exactly once**, at
  `cad_designer/airplane/geometry/spar_solver.py:730`. The producer,
  `app/services/spanwise_loads.py`, emits **un-factored** aerodynamic `M(y)`, and
  the second `g·j` in `app/services/spar_sizing.py:315` belongs to a **disjoint
  code path**. The feared ~4.5× oversizing does not exist. **The un-factored
  input contract is now stated explicitly:** `moment_fn(y_span) -> N·m` carries
  aerodynamic bending moment *before* `g_limit` and `j`.
- 🟡 **`packing_factor` appears in two places.** It scales `outer(y)` in the
  sizing formula (`spar_sizing.py:13`) *and* derives the containment band in
  station sampling (`clr = (1 − packing_factor)/2 · thickness`). Whether these
  are the same knob applied once conceptually, or a double application, is not
  spelled out in the source analysis and is worth a numerical check.
- 🟡 **The rod-equivalent OD is an assumption made explicit nowhere.** Solving
  every station's `required_od` as a rod and only later reconstructing the
  requested shape is correct for an envelope check, but a capped or rectangular
  spar with the same `W` has a different height, so the band check is
  conservative rather than exact.
- 🟢 **Known frozen bug, deliberately not fixed.**
  `cad_designer/.../WingConfiguration.py` contains a dead perpendicular-spare
  branch. The topology layer is frozen (ADR 0002); recorded so later analysis
  does not rediscover it as new.
