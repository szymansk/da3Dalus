# aero-analysis — Technical Design

> Focuses on HOW the module is built, read from the legacy code.
> Confidence markers: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Companion documents: [`requirements.md`](requirements.md),
> [`contracts.md`](contracts.md), [`tasks.md`](tasks.md).

## Interface

### Internal seams (the ones every other module calls)

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `analyse_aerodynamics` | `(analysis_tool, operating_point, asb_airplane, avl_file_content=None, …)` | `(AnalysisModel, Figure \| None)` | the **only** solver selector 🟢 |
| `recompute_assumptions` | `(db, aeroplane_uuid)` | `None` (writes the context) | **sync** — async callers must `asyncio.to_thread` 🟢 |
| `get_stability_summary` | `(db, aeroplane_uuid, operating_point, analysis_tool)` | `StabilitySummaryResponse` | also persists a `stability_results` row 🟢 |
| `resolve_operating_point` | `(db, aircraft_pk, schema, require_trimmed=True)` | `OperatingPointSchema` | gh-577 coherence guard 🟢 |
| `validate_deflections_against_airplane` | `(asb_airplane, deflections)` | `None` / raises | 422 on unknown names 🟢 |
| `mark_ops_dirty` | `(session, aeroplane_id)` | `None` | bulk `UPDATE`; called by the **publisher** 🟢 |
| `retrim_dirty_ops` | `(aeroplane_id)` | summary dict | opens its **own** `SessionLocal` 🟢 |
| `compute_enrichment` | `(…, controls, limits, trim_score, status, …)` | `TrimEnrichment` | single entry point for all three trim paths 🟢 |
| `trim_with_aerobuildup` | `(asb_airplane, op, variable, target_coefficient, target_value, bounds)` | result with `converged` | Brent root-find 🟢 |
| `compute_spanwise_loads` | `(strips, q, …)` | shear / bending-moment arrays | pure integrator 🟢 |

### HTTP surface

Full contract in [`contracts.md`](contracts.md). Summary: 17 routes on
`app/api/v2/endpoints/aeroanalysis.py`, 19 on
`app/api/v2/endpoints/operating_points.py`, 1 on `aeroplane/speed_polar.py`. All
mounted at the **application root** (`prefix=""`, `app/main.py:225-227`) — there
is no `/api/v2` path segment. 🟢

## Main Flow — a single-point analysis

```
1. endpoint resolves the aeroplane by UUID → the ASB airplane
   (aeroplane_service.get_aeroplane_airplane_configuration → asb.Airplane)
2. resolve_operating_point(db, aircraft_pk, body)               # gh-577
     · no operating_point_id  → the inline schema passes through
     · with an id             → row loaded CONSTRAINED to aircraft_pk,
                                status must be TRIMMED (unless waived),
                                alpha/beta rad → deg,
                                _pick_deflections(control_deflections, controls)
3. validate_deflections_against_airplane(...)                   # 422, never a drop
4. analyse_aerodynamics(tool, op, airplane[, avl_file_content])
     op_point = asb.OperatingPoint(velocity, alpha, beta, p, q, r,
                                   atmosphere=asb.Atmosphere(altitude))
     airplane.xyz_ref = op.xyz_ref
     if op.control_deflections: airplane = airplane.with_control_deflections(...)
     ├── AEROBUILDUP     asb.AeroBuildup(...).run_with_stability_derivatives()
     ├── VORTEX_LATTICE  _remesh_airplane(...) →
     │                   asb.VortexLatticeMethod(spanwise_resolution=1,
     │                        spanwise_spacing_function=np.linspace)
     └── AVL             AVLRunner(...).run(avl_file_content)      # → avl-integration
5. AnalysisModel.from_abu_dict(...) | .from_avl_dict(...)
6. NonFiniteSafeJSONResponse serialises NaN/Inf as null
```

`_as_array_if_needed` (`app/api/utils.py:19`) wraps any non-`float` `alpha`/
`beta` into `np.array` — this single line is what makes the vectorised sweeps
work, and it is why the AVL branch has to reject arrays explicitly. 🟢

## Algorithms

### A1 — Characteristic points from an α sweep 🟢

`_compute_alpha_sweep_characteristic_points` (`analysis_service.py:219-250`)
returns a **fixed six-key dict**; each entry is `None` when its inputs are
absent — the shape never varies.

| Point | Rule |
|---|---|
| `maximum_lift_to_drag_ratio_point` | `argmax(CL/CD)`, `CD` guarded at `\|CD\| > 1e-12` (l.107-118) |
| `minimum_drag_coefficient_point` | `argmin(CD)` (l.120) |
| `maximum_lift_coefficient_point` | `argmax(CL)` (l.129) |
| `drag_at_zero_lift_point` | linear interpolation at the **first** `CL` sign change, `t = −CL_i/(CL_{i+1}−CL_i)`; falls back to `argmin(\|CL\|)` when there is no crossing (l.143-164) |
| `stall_point` | the first index after `argmax(CL)` where **both** `CL` drops and `CD` rises; else `i_clmax+1` clamped (l.167-184) |
| `trim_point_cm_equals_zero` | the same interpolation on the first `Cm` sign change; `CD` is interpolated at the same `t` (l.187-216) |

### A2 — Speed polar 🟢

`_compute_speed_polar` (`analysis_service.py:430-583`) is a **pure** function —
no DB, no solver — and therefore fully unit-testable:

```
for every polar point with CL > 0:
    V = sqrt(2·m·g / (ρ · S_ref · CL))
    w = V · (CD / CL)                     # sink rate
V, w ∝ sqrt(m)  →  one curve per mass; the base mass is always present (is_base)

V_stall    = sqrt(2·m·g / (ρ · S_ref · CL_max))
i_min_sink = argmin(w)
i_best     = argmax(CL/CD)        ( = argmax(V/w) )
```

Display bounds (gh-799): `v_axis_min = 0.7 · min(V_stall)`,
`v_axis_max = 1.3 · V_dive` (or the largest `V` present). If either is missing or
the pair is inverted, **both** are dropped so Plotly autoranges. gh-871 converts
the characteristic `CL`s back to α through the cached linear lift curve
(`_cl_to_alpha_deg`) so the chart can label α at stall / min-sink / best-glide.

The glue `_build_speed_polar` (l.604-669) is deliberately best-effort: any
failure logs and returns `None` rather than breaking the sweep. 🔴 A missing
`mass` assumption defaults to **1.0 kg** with only a log warning (l.617-623) —
the polar is then structurally valid and physically meaningless.

### A3 — VLM strip forces without AVL (gh-674) 🟢

`vlm_strip_forces.py` reconstructs AVL-equivalent per-strip data from a
`VortexLatticeMethod` solve using only **public, version-stable** VLM geometry:

- `_strip_index_ranges(is_trailing_edge)` — panels are emitted
  **chordwise-fastest**, so every `is_trailing_edge` flag closes one strip.
- `_wing_strip_counts` — expected strips per wing =
  `segments · spanwise_resolution · (2 if symmetric else 1)`. If the sum does not
  match the actual strip count the code degrades to a **single aggregate
  surface** rather than crashing (l.239-243). 🟢
- Force decomposition:

  ```
  d_hat = vlm.steady_freestream_direction        (normalised)
  l_hat = [−d_z, 0, d_x]                         (normalised)   # lift ⟂ freestream in x–z
  lift  = f_strip · l_hat        drag = f_strip · d_hat
  cl    = lift / (q·A)           cd   = drag / (q·A)
  ai    = degrees(atan2(drag, lift))
  cl_norm = cl · chord / c_ref
  ```

- Inviscid consequence: `cdv`, `cm_c/4`, `cm_LE` = `0.0`, `C.P.x/c` = `0.25`.

The emitted dict is byte-compatible with AVL's `FS` parser output, so
`_strip_surfaces_from_result` consumes either unchanged.

### A4 — Uniform-density remesh (gh-855/gh-857) 🟢

Giving every segment the same `spanwise_resolution` over-resolved a 5 cm segment
as much as a 95 cm one and spiked the `cl(y)` plot. Instead the wing is rebuilt
with inserted sections so panels distribute ∝ segment span (formula in
[`requirements.md`](requirements.md) BR-AA3), then the VLM runs with
`spanwise_resolution = 1`. `_remesh_airplane` re-asserts `s_ref`, `b_ref`,
`c_ref`, `xyz_ref` from the original airplane afterwards.

### A5 — Spanwise loads → spar sizing 🟢

`analyze_airplane_spanwise_loads` (`analysis_service.py:1987-2091`) reuses
whichever strip-force path was selected, injects `q = ½·ρ·V²`, then calls the
pure `compute_spanwise_loads` integrator. With `spar_params` it additionally
resolves:

- **material** — must be a `ComponentModel` with `component_type == "material"`
  and a **positive** `allowable_bending_stress_mpa` (or an explicit
  `sigma_allow_mpa_override`); zero is rejected with **422** rather than dividing
  by zero (l.2129-2150);
- **`g_limit`** — from `get_effective_assumption`; missing ⇒
  `_G_LIMIT_DEFAULT = 3.0` with `g_limit_fallback = True`;
- **half selection** — `_surface_to_stations` sizes on the half with the larger
  root bending moment, `max(|M_sb|, |M_pt|)`;
- **real `t/c`** — `_get_tc_by_y_for_surface` (gh-1022) reads the built CAD
  section; unresolvable stations are simply **omitted** so `compute_spar_sizing`
  applies its documented `_TC_FALLBACK = 0.12`.

### A6 — The aero-context pipeline (gh-924) 🟢

`recompute_assumptions(db, aeroplane_uuid)`
(`assumption_compute_service.py:59-809`) — **sync**; async callers must wrap it
in `asyncio.to_thread`.

```
0.  build the ASB airplane; skip silently if it has no wings
1.  main_wing = argmax(wing.area())   →  s_ref / c_ref / b_ref OVERRIDDEN
2.  seed_defaults()  +  _load_or_create_config()          (both idempotent)
3.  _stability_run_at_cruise          → x_np, MAC, cd0_parasite, S_ref
4.  _coarse_alpha_sweep               → stall_alpha = argmax(CL)
5.  _fine_sweep_cl_max                → CL_max, cl[], cd[], v[], cdi[]
6.  cg_x = x_np − target_SM · MAC     → written back as CALCULATED
7.  parabolic fit (+ auto-refinement) → cd0_fit, e_fit, R²
8.  e from AeroBuildup Trefftz        → e_oswald_ab   (preferred)
9.  per-config polars {clean, takeoff, landing}
10. Re-band table (gh-493)            → polar_re_table (+ gh-924 backfill)
11. V-speeds, CG / loading / stability envelopes, landing field length
12. _cache_context()                  → aeroplanes.assumption_computation_context
```

Closed-form V-speeds (all sea level, `ρ = 1.225`, `g = 9.81`):

```
V_stall = sqrt(2·W / (ρ·S·CL_max))              CL_max floored at 0.5
V_md    = sqrt(2·W / (ρ·S·sqrt(CD0/k)))         k = 1/(π·AR·e)
V_ms    = sqrt(2·W / (ρ·S·sqrt(3·π·e·AR·CD0)))  ( = V_md / 3^¼ ≈ 0.760 · V_md )
w_min   = V_ms · 4·sqrt(CD0 / (3·π·e·AR))                       gh-692
V_max   solves  a·V⁴ − P_η·V + b = 0     a = ½·ρ·S·CD0
                                         b = 2·k·W² / (ρ·S)
                                         P_η = (P/W)·m·η_prop
V_a     = min(V_s1 · sqrt(n_max), V_C)          CS-25.335(c) / Scholz §6
V_dive  = 1.4 · V_max                           heuristic; flutter out of scope
Re      = ρ · V_cruise · MAC / μ,   μ = 1.81e-5
is_glider = (P/W ≤ 0)
```

`V_x` / `V_y` are **read back** from the `best_angle_climb_vx` /
`best_rate_climb_vy` operating-point rows (`_read_vx_vy_from_ops`); they stay
`None` until the OP generator has run. 🟢

**Error policy — three layers** 🟢

- **fatal** — an AeroBuildup failure in the stability run, the coarse sweep or
  the fine sweep logs and **returns without writing**, so the previous context
  stays valid;
- **degraded** — each per-configuration polar sits in its own `try` (a takeoff
  failure must not block the physically independent landing pass) and falls back
  to a clone of the clean polar with `provenance="aerobuildup_failed"`; the
  Re-table, the turbulator ΔCD0 and the elevator-authority forward-CG limit are
  non-fatal with named fallbacks;
- **guarded** — a schema/ASB **flap-name parity mismatch** (the model reports a
  flap TED but the ASB conversion produced no flap-role control surface) routes
  to the no-flap fallback with an explicit "investigate the converter" warning
  instead of letting `_run_polar_for_deflection` raise `AssertionError` on the
  live path (gh-537).

### A7 — Stability 🟢

Formulas in [`requirements.md`](requirements.md) BR-AA14. Persistence:
`persist_stability_result` upserts on
`uq_stability_aeroplane_solver (aeroplane_id, solver)`; `get_cached_stability`
orders by `status ASC, computed_at DESC`.

### A8 — Trim enrichment 🟢

`compute_enrichment` (`trim_enrichment_service.py:380-572`) is the single entry
point for all three trim paths (AVL trim, AeroBuildup trim, OP generation).
Thresholds in [`requirements.md`](requirements.md) BR-AA20.

`decompose_dual_role` reconstructs physical left/right angles from the two
control variables of a mixed surface:

```
d_sym  = mix_gain_primary   · δ_primary       # pitch / lift axis
d_anti = mix_gain_secondary · δ_secondary     # roll / yaw axis
right  =  d_anti ;  left = −d_anti
whichever side is negative is scaled by differential_ratio   (the up-going side)
deflection_left/right = d_sym + left/right    # differential never scales d_sym
```

## Alternative Flows

- **No `operating_point_id` given.** The inline `OperatingPointSchema` passes
  through unchanged — the explicit diagnostic / manual mode. 🟢
- **`require_trimmed=False`.** A non-`TRIMMED` row is accepted; used by
  diagnostic paths that deliberately want an untrimmed state. 🟢
- **`solver="avl"` on strip forces / spanwise loads.** The AVL subprocess path
  runs with a 60 s (airplane) / 30 s (wing) timeout. 🟢
- **AVL requested without `avl_file_content`.** `analyse_aerodynamics` raises;
  the caller is expected to have fetched or generated the geometry first
  (→ `avl-integration`). 🟢
- **The aircraft has no wings.** `recompute_assumptions` skips **silently** at
  step 0 — no context is written and no error is raised. 🟢
- **The strip count does not match the expected geometry.** One aggregate
  surface is emitted instead of per-wing surfaces. 🟢
- **The trim root is not bracketed.** `converged=False` plus a detailed warning;
  no exception. 🟢
- **No pitch-role TED exists.** `retrim_dirty_ops` logs a warning and every OP
  stays `DIRTY` forever — an **absorbing state**. 🟡 **The absorbing `DIRTY` state is removed** — a state indistinguishable from "still working" in the UI is the undeclared degradation `P-WARN-0` forbids.
- **The polar fit is rejected.** `cd0` / `e_oswald` are `None` on that
  `ParabolicPolar` and a `PolarRejection` is attached; only `design`-category
  rejections reach the user. 🟢

## Dependencies

- **AeroSandbox** (`asb.AeroBuildup`, `asb.VortexLatticeMethod`,
  `asb.OperatingPoint`, `asb.Atmosphere`, `asb.Airplane`) — the default solver
  stack. Pinned `>= 4.0.7` because the VLM `Cnbeta` sign flip was fixed there
  (ADR 0003) — a **correctness** dependency, not just an API one. 🟢
- **`avl-integration`** — only for `analysis_tool=avl` / `?solver=avl`, and for
  `avl_file_content`. 🟢
- **`wing-design` / `fuselage-design` / `aeroplane-core`** — supply the ASB
  airplane and the geometry-change events. 🟢
- **`mission-and-sizing`** — supplies `design_assumptions`
  (`mass`, `cg_x`, `cl_max`, `g_limit`, `target_static_margin`,
  `power_to_weight`, `prop_efficiency`) and the flight profile; consumes the
  cached context. The recompute pipeline itself lives in
  `assumption_compute_service`, which both modules document. 🟢
- **`airfoil-catalog`** — indirectly, through AeroBuildup's internal 2-D
  lookups; airfoil-level polars are **not** this module's business. 🟢
- **`mass-and-balance`** — `mass` and CG aggregation. 🟢
- **`platform-core`** — `get_db()` transaction boundary (BR-78),
  `event_bus`, `job_tracker`, `NonFiniteSafeJSONResponse`. 🟢
- **SciPy** — `optimize.brentq` for the AeroBuildup trim. 🟢
- **Matplotlib** — the 3×2 α-sweep diagram PNG. 🟢

## Identified Design Decisions

| Decision | Evidence in code | Confidence |
|---|---|---|
| One solver dispatcher, three tools, one envelope | `app/api/utils.py:97-127`; `AnalysisModel.from_avl_dict` / `from_abu_dict` | 🟢 |
| AeroSandbox by default; AVL opt-in only (ADR 0003) | five hard-coded ASB paths, four caller-selectable | 🟢 |
| One aero truth cached on the aeroplane row (ADR 0004) | `_cache_context` → `aeroplanes.assumption_computation_context` | 🟢 |
| Parasite CD0, not total CD | `_parasite_cd0` (`:1098-1112`) | 🟢 |
| `(L/D)max` from closed-form scalars, not the sweep argmax | `:282-300` (Scholz eq. 5.39) | 🟢 |
| Six fit gates with canonical categories; only `design` is user-visible (ADR 0012) | `PolarRejection` model validator | 🟢 |
| Refinement raises resolution and never loosens a threshold (gh-672) | `_REFINABLE_REJECTION_GATES` | 🟢 |
| Vectorised sweeps instead of per-point calls (gh-690) | `np.meshgrid(..., indexing="xy")` | 🟢 |
| Reference geometry from the largest wing, not `wings[0]` (gh-788) | recompute step 1 | 🟢 |
| AVL-shaped strip dict emitted by the VLM path for byte compatibility (gh-674) | `vlm_strip_forces` column order | 🟢 |
| Retrim runs in its own session outside the request | `retrim_service.py:53-158` | 🟢 |
| `INVALID` is terminal for retry | `retrim_service` exception branches | 🟢 |
| NaN/Inf → `null` rather than a fabricated number (ADR 0012) | `NonFiniteSafeJSONResponse` on the analysis router | 🟢 |
| Speed polar and load integration kept pure for testability | `_compute_speed_polar`, `compute_spanwise_loads` | 🟢 |
| The stability read prefers `CURRENT` via **string** ordering | `status ASC, computed_at DESC` | 🟡 |

## Internal State

- **`aeroplanes.assumption_computation_context`** (JSON) — the gh-924 contract.
  Key inventory in [`../data-dictionary.md`](../data-dictionary.md)
  §`assumption_computation_context` and in
  [`aero-context-single-source/design.md`](aero-context-single-source/design.md).
  Written **only** by `_cache_context`; read by nine consumers.
- **`operating_points`** — `status`, `warnings[]`, `controls{}`,
  `control_deflections{}`, `trim_enrichment`. `alpha`/`beta` are stored in
  **radians**; everything else is SI. `xyz_ref` is written as
  `[design_cg_x, 0, 0]`.
- **`operating_pointsets`** — `operating_points` is a **JSON id list**, not an
  association table. 🟡
- **`stability_results`** — one row per `(aeroplane_id, solver)`, with
  `geometry_hash` and `status ∈ {CURRENT, DIRTY}`.
- **`aircraft_computation_config`** — per-aircraft sweep tuning (owned by
  `mission-and-sizing`, read here).
- **In-memory only:** `job_tracker`'s debounced retrim / recompute jobs
  (`platform-core`); they do not survive a restart. 🟡

## Observability

- Every trim result carries `trim_method` (`"opti"` | `"grid_fallback"` |
  Brent), `trim_score`, `trim_residuals: dict[str, float]` (**floats only** —
  gh-627 forbids a `"solver_path"` string here) and a list of structured
  `DesignWarning{level, category, surface, message}`. 🟢
- Operating-point `warnings[]` accumulate the vocabulary `STALE_NO_POLAR`,
  `FLAP_DEFLECTION_CLIPPED`, `ALPHA_LIMIT_REACHED`, `BETA_LIMIT_REACHED`,
  `STALL_IN_TURN`, `NOT_TRIMMED`, `NO_CONTROL_TRIM_MVP`. They are **not** cleared
  by a successful retrim. 🟡
- Polar rejections carry `gate`, `category`, `fitted_value`, `threshold`,
  `hint`. 🟢 **The German `PolarRejection.hint` strings are translated** (`Q-AA-7` / `Q-CC-5`) — they are the most user-facing strings in the module. The strings are written in **German** while the UI is
  English-only.
- `e_oswald_provenance` and `e_oswald_fallback_used` make the Oswald chain
  auditable from the response. 🟢
- Picard refinement logs a warning when `|ΔV|/V₀ ≥ 5 %`. 🟢
- The α-sweep diagram encodes stability visually: colour-coded trend strips,
  `dCm/dα < −0.01` green / `≤ 0.01` amber / else red. 🟢
- 🔴 There is no metric or trace emission — logging only.

## Configuration and Constants 🟢

| Constant | Value | Where |
|---|---|---|
| `_SPANWISE_PANELS_PER_HALF` / `_MIN_PANELS_PER_SEGMENT` | `40` / `2` | `vlm_strip_forces.py:59-60` |
| VLM `chordwise_resolution` | `8` | `vlm_strip_forces.py:171` |
| AVL strip-force timeouts | `60 s` airplane / `30 s` wing | `analysis_service.py:1881, 1962` |
| `_G_LIMIT_DEFAULT` / `_TC_FALLBACK` | `3.0` / `0.12` | `analysis_service.py:2099-2101` |
| trim status threshold | `trim_score < 0.35` ⇒ TRIMMED | `operating_point_generator_service.py:853` |
| `CL_α` gate | `R² ≥ 0.995` over α ∈ [−2°, 6°] | `assumption_compute_service.py:1219` |
| polar-fit window | `CL ∈ [max(0.10, 0.10·CL_max), 0.85·CL_max]`, ≥ 6 points | `:1461-1468` |
| `e` sanity clip | `0 < e ≤ 1.10` (Trefftz) / `0.4 < e ≤ 1.0` (fit) | `:1412, :1553` |
| polar quality ladder | `R² > 0.99` high · `≥ 0.95` medium · else low | `:1697-1706` |
| Picard tolerance | `5 %`, one pass | `:2033` |
| Brent trim | `xtol = 1e-6`, `maxiter = 50` | `aerobuildup_trim_service.py` |
| `COMPUTATION_CONFIG_DEFAULTS` | α −5…25 °, step 1 °; fine margin 5 °, step 0.5 °; 8 velocities; debounce 2 s | `app/models/computation_config.py:8-16` |
| enrichment default limits | `(25.0, 25.0)` degrees | `trim_enrichment_service.py` 🔴 reached whenever #955 bites |

## Risks and Gaps

- 🟢 **Bug #955 is resolved structurally** (`Q-WD-1`, maintainer-answered): `control_surface_mixing` owns a resolver that trim, retrim and stability are **required** to call, and the silent ±25° fallback is removed. Keying on the raw DB TED name becomes impossible rather than merely discouraged. Previously: Deflection limits, the pitch
  control lookup and the trim-elevator extraction all key on the **raw DB TED
  name**, while the solver's `controls` dict carries **gh-772 mixing names**. On
  any dual-role aircraft the authority check silently degrades to ±25° and a
  phantom 0° surface is reported. See
  [`../avl-integration/control-surface-naming/`](../avl-integration/control-surface-naming/requirements.md).
- 🔴 **`_auto_populate_cd0` writes total CD into the `cd0` assumption**, on a
  different trigger from the recompute — a direct BR-14 / ADR 0004 violation.
- 🟡 **The 1.0 kg fallback is removed so no invented mass reaches a polar** (`Q-AA-3`, derived from `P-WARN-0`). Previously a 1.0 kg speed polar with only a log
  warning.
- 🔴 **`min_static_margin` / `max_static_margin` are read but never seeded**, so
  the 5 % / 25 % CG-range bounds are effectively hard-coded.
- 🔴 **Geometry listeners are registered twice** (`stability_events.py` **and**
  `avl_geometry_events.py` attach the same three models), so every geometry write
  publishes `GeometryChanged` twice and calls `mark_ops_dirty` twice.
- 🔴 **Polar-rejection `hint` strings are German** while the UI is English-only.
- 🔴 **`DIRTY` is absorbing without a pitch control** — the OPs never leave it
  and only a log warning records why.
- 🔴 **Dead code:** `assumption_compute_service._load_cg_agg` (l.1739) is unused
  (the pipeline calls `loading_scenario_service.compute_cg_agg_for_aeroplane`),
  and `_extract_scalar` (l.1316) survives only for tests.
- 🟡 **`get_cached_stability` relies on alphabetical status ordering**
  (`CURRENT` < `DIRTY`) rather than an explicit rank.
- 🟡 **`operating_pointsets.operating_points` is a JSON id list** with no FK
  integrity — a deleted OP leaves a dangling id.
- 🟡 **`operating_points.aircraft_id` has no `ondelete` clause**, so deleting an
  aeroplane does not cascade to its operating points at the DB level.
- 🟡 **Warnings are never cleared** by a successful retrim, so a row can carry a
  `STALE_NO_POLAR` long after the polar became available.
