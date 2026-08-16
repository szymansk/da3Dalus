# aero-analysis

> Module-level specification. Focuses on WHAT the module does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Cluster C / §Module:
> aero-analysis, `_reversa_sdd/data-dictionary.md` §Module: aero-analysis,
> `_reversa_sdd/domain.md` §2.4, `_reversa_sdd/state-machines.md` §1 and §8,
> ADR 0003, ADR 0004, ADR 0012.

## Overview

`aero-analysis` is the AeroSandbox solver stack and the operating-point
lifecycle. It owns the **one** solver dispatcher, the solver-agnostic result
envelope, the α/parameter sweeps and the characteristic points derived from
them, strip forces and spanwise loads, the stability summary and its cache, and
— the load-bearing part — the **single-source-of-truth aero context** that every
other module reads instead of re-deriving `cd0`, `e_oswald`, `(L/D)max` and
`x_np`. It also owns the operating-point status machine: trim → persist →
invalidate → background retrim. 🟢

## Responsibilities

- Dispatch **exactly three** solvers (`AeroBuildup`, in-process
  `VortexLatticeMethod`, `AVL`) from one function, and normalise all three into
  one `AnalysisModel` envelope. 🟢
- Run α sweeps and multi-parameter sweeps vectorised, and derive the six
  characteristic points from them. 🟢
- Produce a speed polar (V, sink) per mass from a drag polar, purely
  analytically. 🟢
- Produce AVL-shaped per-strip forces from an in-process VLM solve, and
  integrate them into shear/bending-moment distributions for spar sizing. 🟢
- Compute, cache and publish the **aero context** on
  `aeroplanes.assumption_computation_context` (gh-924). 🟢
- Compute, persist and serve the stability summary (`x_np`, static margin,
  stability class, `Cma`/`Cnb`/`Clb`), keyed by a geometry hash. 🟢
- Resolve a stored operating point into an analysis-ready schema, converting
  radians→degrees and picking the correct deflection source. 🟢
- Mark operating points DIRTY on geometry/assumption change and re-trim them in
  the background. 🟢
- Enrich every trim result with deflection reserves, control effectiveness,
  stability classification, mixer decomposition and **design warnings**. 🟢

**Explicitly NOT this module's responsibility:** emitting or running `.avl`
files (→ `avl-integration`), design assumptions / mission presets / matching
chart / V-n envelope (→ `mission-and-sizing`), airfoil-level low-Re polars and
NeuralFoil suitability scoring (→ `airfoil-catalog`), mass and CG aggregation
(→ `mass-and-balance`), the wing geometry itself (→ `wing-design`).

## Business Rules

> `BR-13`…`BR-23` are global ids reused verbatim from
> [`../domain.md`](../domain.md). `BR-AA*` are module-local.

### The two cluster invariants

- **BR-14 — One aero truth per aircraft (gh-924, ADR 0004).** 🟢 `cd0`
  (**parasite**, not total CD), `e_oswald`, `(L/D)max` and `x_np` are produced
  **once** by `assumption_compute_service.recompute_assumptions` at the cruise
  point and cached on `aeroplanes.assumption_computation_context`. Every
  downstream consumer — speed polar, V-n envelope, matching chart, mission KPIs,
  endurance, spar sizing, powertrain, copilot — **reads that context**; none
  re-derives its own.
- **BR-15 — AeroSandbox is the default solver; AVL is the exception
  (ADR 0003).** 🟢 `analyze_alpha_sweep`, `analyze_simple_sweep`, strip forces,
  spanwise loads, retrim, assumption recompute, OP generation and streamlines
  all default to AeroBuildup or the in-process VLM. AVL is reached only when the
  caller explicitly passes `analysis_tool=avl` / `?solver=avl`, or calls the
  dedicated AVL trim endpoint. Five paths hard-code ASB with **no** AVL option.

### Solver dispatch and the result envelope

- **BR-AA1 — One dispatcher, one envelope.** 🟢
  `analyse_aerodynamics(analysis_tool, operating_point, asb_airplane, …)`
  (`app/api/utils.py:97-127`) is the only place a solver is selected. It always
  returns `(AnalysisModel, Figure | None)`. Before dispatch it always performs:

  ```
  op_point             = asb.OperatingPoint(velocity, alpha, beta, p, q, r,
                                            atmosphere=asb.Atmosphere(altitude))
  asb_airplane.xyz_ref = operating_point.xyz_ref        # moment reference = CG
  if operating_point.control_deflections:
      asb_airplane = asb_airplane.with_control_deflections(overrides)
  ```

  `AnalysisModel` (`cad_designer/.../models/analysis_model.py:242`) carries
  `method ∈ {avl, aerobuildup, vortex_lattice}`, `reference`, `forces`,
  `moments`, `coefficients`, `derivatives`, `control_surfaces`,
  `flight_condition`, with two adapters `from_avl_dict` (l.301) and
  `from_abu_dict` (l.480). Everything downstream reads only
  `result.reference.Xnp`, `result.coefficients.*` and `result.derivatives.*` —
  it is solver-agnostic **by construction**.
- **BR-AA2 — An array-valued `alpha`/`beta` *is* a sweep, and AVL rejects it.**
  🟢 `_as_array_if_needed` (`app/api/utils.py:19`) wraps any non-`float` into
  `np.array`; AeroBuildup then returns same-shape result arrays. The `AVL`
  branch raises
  `ValueError("AVL analysis does not support parameter sweeps")` and
  additionally requires `avl_file_content`.
- **BR-AA3 — VLM density comes from the remesh, not from `spanwise_resolution`
  (gh-855/gh-857).** 🟢 The `VORTEX_LATTICE` branch runs
  `_remesh_airplane` → `asb.VortexLatticeMethod(spanwise_resolution=1,
  spanwise_spacing_function=np.linspace)`. Panels are distributed **∝ segment
  span**:

  ```
  budget = _SPANWISE_PANELS_PER_HALF = 40          # panels per half wing
  n_i    = max(_MIN_PANELS_PER_SEGMENT = 2, round(budget · span_i / Σ span))
  span_i = hypot(Δy, Δz)                           # dihedral-inclusive true span
  ```

  Intermediate sections come from `_blend_xsec` (linear `chord`, `twist`,
  `xyz_le`; `Airfoil.blend_with_another_airfoil` for the profile, falling back to
  the inboard airfoil on any blend exception). `_remesh_airplane` re-asserts
  `s_ref`, `b_ref`, `c_ref`, `xyz_ref` from the original airplane so the gh-788
  main-wing reference geometry survives the remesh.
- **BR-AA4 — The VLM is inviscid, and the contract says so.** 🟢 On the ASB
  strip-force path `cdv`, `cm_c/4` and `cm_LE` are emitted as `0.0` and
  `C.P.x/c` as a constant `0.25`. The Trefftz chart therefore shows no viscous
  component. Documented, not hidden (ADR 0003, Consequences).

### The single-source aero context (gh-924)

- **BR-AA5 — The main wing is `argmax(wing.area())`, never `wings[0]`.** 🟢
  `s_ref` / `c_ref` / `b_ref` are **overridden** from the largest wing, because
  AeroSandbox defaults to `wings[0]`, which may be a tail — the gh-788/F1 bug
  class that produced ~8× wrong coefficients for tail-first imports.
- **BR-AA6 — CD0 is the parasite drag, not the total drag.** 🟢
  `_parasite_cd0` (`assumption_compute_service.py:1098-1112`):

  ```
  CD_induced = CL² / (π · AR · e)      # e = AeroBuildup's own oswalds_efficiency
  CD0        = CD_total − CD_induced   # only when CL/AR/e are sane AND result > 0
  ```

  On a cambered wing α = 0 already carries lift (CL ≈ 0.55 on a glider), so
  publishing `coefficients.CD` as CD0 double-counts induced drag and collapses
  `(L/D)max` (17 instead of 24 on a high-AR glider). Ratified against
  Anderson §6.7.2.
- **BR-AA7 — `(L/D)max` is published from self-consistent scalars, not from the
  sweep argmax.** 🟢 (`:282-300`, Scholz eq. 5.39)

  ```
  E_max       = ½ · sqrt(π · AR · e / CD0)
  CL_at_E_max = sqrt(CD0 · π · AR · e)
  ```

  The flattened-sweep `argmax(CL/CD)` mixes Reynolds bands and lands on a
  spurious high-CL sample (documented eHawk case: 18.8 @ CL 0.98 vs the correct
  23.4 @ CL 0.55). The measured argmax survives **only** as the fallback when the
  parabolic scalars are unavailable.
- **BR-AA8 — Oswald provenance is a chain, recorded on the result.** 🟢
  `aerobuildup_trefftz` → `fit` → `fallback`, stored in
  `polar_by_config[*].e_oswald_provenance` and mirrored by
  `context["e_oswald_fallback_used"]`.

  ```
  e   = CL² / (π · AR · CDi)   at the (L/D)max sample     # _e_oswald_from_sweep
  CDi = D_induced / (q · S_ref)                           # free from the fine sweep
  sanity clip: reject unless 0 < e ≤ 1.10
  e_oswald_effective = e or 0.8
  ```

  `D_induced` comes free with the vectorised fine sweep, so this costs **zero**
  extra AeroBuildup calls (gh-636).
- **BR-16 — Resolution goes up; thresholds never move (gh-672).** 🟢
  `_fit_parabolic_polar` (`:1417-1610`) fits `CD = CD0 + k·CL²` by OLS over
  `CL ∈ [max(0.10, 0.10·CL_max), 0.85·CL_max]`, then `e = 1/(π·AR·k)`. Six
  rejection gates:

  | Gate | Accept condition | Category |
  |---|---|---|
  | `insufficient_points` | ≥ 6 samples in the window (also fires on `AR ≤ 0`) | `sweep` |
  | `non_monotonic_polar` | `dCD/d(CL²) ≥ −1e-6` | `data` |
  | `negative_slope_k` | `k > 0` | `design` |
  | `non_positive_cd0` | `cd0_fit > 0` | `consistency` |
  | `unphysical_e_oswald` | `0.4 < e ≤ 1.0` | `design` |
  | `cd0_stability_mismatch` | `\|cd0_fit − cd0_stability\| / cd0_stability ≤ 0.20` | `consistency` |

  `_fit_parabolic_polar_with_refinement` (`:1618-1694`) retries **only** for
  `_REFINABLE_REJECTION_GATES = {insufficient_points, non_monotonic_polar}`,
  halving the α step and multiplying the margin by 1.5 per attempt (max 2), and
  sets `auto_refined=True` only when a refinement actually produced a fit.
- **BR-17 — An unphysical result is a design warning, not a fallback
  (gh-956, ADR 0012).** 🟢 `PolarRejection` enforces the canonical
  gate→category pair with a model validator, and **only `category == "design"`**
  is surfaced to the user. A `k ≤ 0` or an out-of-range `e` therefore becomes a
  visible design warning instead of a silent `0.8` substitution.
- **BR-18 — Turbulator deltas never poison the fit gate (gh-935).** 🟢 With a
  turbulator enabled the stored `cd0` gains `+ ΔCD0`
  (`apply_turbulator_delta_to_cd0`, `:2099-2168`; area-weighted, ×2 for a
  symmetric wing), but `raw_cd0` is preserved and passed as `cd0_stability` to
  every fit — otherwise a meaningful ΔCD0 would spuriously trip the 20 %
  consistency gate.
- **BR-AA9 — Sweeps are vectorised (gh-690).** 🟢 `_coarse_alpha_sweep`,
  `_fine_sweep_cl_max` and `_extract_cl_alpha_from_linear_sweep` each issue
  **one** `AeroBuildup.run()` over an array-shaped `OperatingPoint` (was ~150
  calls per polar config). `_fine_sweep_cl_max` builds the grid with
  `np.meshgrid(alphas, velocities, indexing="xy")` — **V-outer / α-inner** ravel
  order, which downstream consumers index against.
- **BR-AA10 — The lift-curve regression has a hard quality gate
  (gh-487/gh-871).** 🟢 `CL = CL_α·α + CL_0` by least squares over
  α ∈ [−2°, +6°]; returns `(None, None)` when `R² < 0.995`, when `CL_α ≤ 0`, or
  when fewer than 3 finite points survive. `α₀ = degrees(−CL_0 / CL_α)`.
  Consumers (`compute_vn_curve`) then fall back to Helmbold-Diederich.
- **BR-AA11 — Picard refinement is exactly one pass (gh-493 A7).** 🟢
  `_picard_iterate_speed` looks up `cd0`/`e` at the scalar `V₀` in
  `polar_re_table`, re-solves, accepts `V₁`, and logs a warning when
  `|ΔV|/V₀ ≥ 5 %`. Applied to `V_md`, `V_min_sink`, `V_max`.
- **BR-AA12 — Sub-stall clamp (gh-683).** 🟢 `V_md` and `V_min_sink` are clamped
  to `max(V, V_stall)`, because the closed-form optimum CL can exceed `CL_max`
  on high-AR / draggy polars and back-solve a physically unreachable speed.
- **BR-AA13 — Re-table fallback rows are backfilled with the authoritative
  values (gh-924).** 🟢 A rejected band's `cd0`/`e` are `None` and the lookups
  would otherwise fall back to a hard-coded `0.03 / 0.8` that contradicts the
  cruise values. `recompute_assumptions` overwrites every row with
  `fallback_used or cd0 is None` using the single-source parasite `cd0` and the
  Trefftz `e` (`:444-449`).

### Stability

- **BR-AA14 — The stability summary is derived, persisted and hash-keyed.** 🟢
  `get_stability_summary` (`stability_service.py:289-362`):

  ```
  static_margin           = (Xnp − Xcg) / MAC        Xcg = operating_point.xyz_ref[0]
  static_margin_pct       = 100 · static_margin
  stability_class         = stable (>5 %) | neutral (0–5 %) | unstable (<0)
  cg_range_forward        = Xnp − (max_margin/100) · MAC       default 25 %
  cg_range_aft            = Xnp − (min_margin/100) · MAC       default  5 %
  is_statically_stable    = Cma < 0
  is_directionally_stable = Cnb > 0
  is_laterally_stable     = Clb < 0
  ```

  `compute_geometry_hash` (`:102-141`) hashes only the stability-relevant
  geometry (per-wing `x_le/y_le/z_le/chord/twist`, per-fuselage
  `x_c/width/height`) → `sha256[:16]`, stored on the row so a later read can tell
  whether the cached result still matches. `persist_stability_result` upserts on
  `uq_stability_aeroplane_solver (aeroplane_id, solver)`.
- **BR-AA15 — The cached-stability read prefers `CURRENT` by string ordering.**
  🟡 `get_cached_stability` orders by `status ASC, computed_at DESC`, which
  alphabetically puts `CURRENT` before `DIRTY`. Correct today, but it relies on
  string ordering rather than an explicit enum rank.
- 🔴 **BR-AA16 — `min_static_margin` / `max_static_margin` are queried but never
  seeded.** Neither name exists in `VALID_PARAMETERS` / `PARAMETER_DEFAULTS`, so
  `seed_defaults` never creates the rows and `_get_margin_bounds`
  (`:225-254`) always returns empty: the 5 % / 25 % defaults are **effectively
  hard-coded**.
- 🔴 **BR-AA17 — `_auto_populate_cd0` violates BR-14.** `stability_service`
  (`:257-281`) writes `result.CD` — the **total** CD at the operating point —
  into the `cd0` assumption's `calculated_value` with source
  `"stability_analysis"` when the tool is AeroBuildup. That is exactly the
  quantity gh-924 removed from the authoritative path, and it runs on a
  different trigger, so the stored `cd0` can be overwritten with a total-drag
  value between recomputes.

### Operating points

- **BR-AA18 — The operating point is the only entity with a persisted,
  multi-valued status.** 🟢 `NOT_TRIMMED | COMPUTING | TRIMMED | LIMIT_REACHED |
  DIRTY | INVALID` (`app/models/analysismodels.py:20`, default `NOT_TRIMMED`).
  Full machine in [`../state-machines.md`](../state-machines.md) §1 and in
  [`retrim-invalidation/design.md`](retrim-invalidation/design.md).
- **BR-19 — Trim must reflect one coherent state (gh-577).** 🟢
  `resolve_operating_point` (`operating_point_resolver.py:138-213`): with no
  `operating_point_id` the inline schema passes through (explicit
  diagnostic/manual mode). With an id, the row is loaded **constrained to
  `aircraft_pk`** (no cross-aeroplane OP injection), must have status `TRIMMED`
  unless `require_trimmed=False`, and is converted by
  `operating_point_model_to_schema`, which is the single place where two
  easily-forgotten translations happen:
  - `alpha` / `beta` are stored in **radians** on the model and converted to
    **degrees** for the schema and every `asb.OperatingPoint` consumer;
  - `_pick_deflections`: a **non-empty** `control_deflections` (manual override)
    wins, otherwise `controls` (the trim solver's output). An **empty** override
    dict is a no-op so it cannot silently erase a fresh trim.
  - `_require_field` raises rather than substituting `0.0` for a NULL NOT-NULL
    column.
- **BR-20 — Unknown deflection names are a 422, not a silent drop.** 🟢
  `Airplane.with_control_deflections` silently drops unknown keys, which would
  let a renamed surface run clean while the UI labelled the plot "trimmed".
  `validate_deflections_against_airplane` raises a 422 listing unknown vs
  available names; it is called from the streamline, four-view, strip-force and
  AeroBuildup-trim paths.
- **BR-AA19 — AeroBuildup trim is a bracketed Brent root-find that reports
  non-convergence instead of raising.** 🟢 `scipy.optimize.brentq`,
  `xtol=1e-6`, `maxiter=50`, on `residual(δ) = coeff(δ) − target`, one
  `AeroBuildup.run_with_stability_derivatives()` per evaluation. If
  `f(lower)·f(upper) > 0` the root is not bracketed and the service returns
  `converged=False` with a detailed warning. Name resolution accepts the tagged
  name, the display name, or a **role** name — a role resolves to that surface's
  **primary (pitch/lift) axis**, because AeroBuildup can only trim the symmetric
  axis (gh-772).
- **BR-AA20 — Enrichment thresholds are fixed and reported, never clamped.** 🟢
  (`trim_enrichment_service.compute_enrichment`, `:380-572`)

  ```
  usage_fraction = |δ| / (max_pos if δ ≥ 0 else max_neg)     default limits (25, 25)
    > 0.95  → critical  "near mechanical limit"
    > 0.80  → warning   "surface may be undersized"
  trim_score > 0.5 → critical "failed to converge";  > 0.1 → warning
  LIMIT_REACHED    → critical "optimizer hit a constraint boundary"
  static_margin = −Cm_a / CL_a
    ≤ 0    → critical  (statically unstable)
    < 0.05 → warning   (marginal)
    > 0.30 → warning   (very nose-heavy)
  aerobuildup + mixed surfaces → warning: roll/yaw of mixed surfaces is AVL-only
  ```

  gh-863: **every** geometry surface is reported, not only the trimmed one —
  `surface_deflections = dict.fromkeys(limits, 0.0)` updated with `controls`.
- 🟢 **Bug #955 is resolved structurally** (`Q-WD-1`, maintainer-answered): `control_surface_mixing` owns a resolver that trim, retrim and stability are **required** to call, and the silent ±25° fallback is removed. Keying on the raw DB TED name becomes impossible rather than merely discouraged. Previously BR-13 (open bug
  #955).** `build_deflection_limits_from_schema`
  (`trim_enrichment_service.py:72-118`) keys `limits` by the **raw TED name from
  the DB**, while `controls` carries **mixing names**
  (`[ruddervator]pitch_htail_1`). On a dual-role aircraft (V-tail, elevon,
  flaperon) the reserve is computed against a hard-coded **±25°** and the gh-863
  union injects a **phantom 0° surface** under the DB name that no solver ever
  trims. The same DB-name assumption appears in
  `retrim_service._find_pitch_control_name` and
  `stability_service._find_trim_elevator` (substring match on `"elevator"`,
  which never matches `[ruddervator]pitch_…`). **Always use the mixing names.**

### Response hygiene

- **BR-AA21 — NaN/Inf serialise as `null`, never as a fabricated number.** 🟢
  The analysis router is created as
  `APIRouter(default_response_class=NonFiniteSafeJSONResponse)`. This is
  ADR 0012 applied to serialisation: `null` is "an honest no value".
- **BR-AA22 — The schema guards the rad/deg trap itself.** 🟢 A field validator
  on `OperatingPointSchema.alpha` / `.beta` rejects any magnitude `> 180` with
  the message "almost certainly means radians were passed instead of degrees
  (gh-577/gh-587)".
- 🔴 **BR-AA23 — A missing `mass` assumption silently yields a 1.0 kg speed
  polar.** `_build_speed_polar` (`analysis_service.py:617-623`) defaults `mass`
  to `1.0` with only a log warning; the returned polar is then physically
  meaningless but structurally valid.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Dispatch a single-point analysis to AeroBuildup, VLM or AVL from one function and return one `AnalysisModel` | Must | The same aircraft analysed by all three yields the same field names; `method` differs |
| RF-02 | Reject array-valued `alpha`/`beta` on the AVL branch | Must | `ValueError("AVL analysis does not support parameter sweeps")` |
| RF-03 | Set the moment reference from `operating_point.xyz_ref` before every run | Must | `Cm` changes when `xyz_ref[0]` changes, with geometry unchanged |
| RF-04 | Apply control deflections through `with_control_deflections` and validate names first | Must | Unknown name → 422 listing unknown vs available; known name → deflection applied |
| RF-05 | Run an α sweep in **one** vectorised solver call and derive six characteristic points | Must | The response carries all six keys; each is `null` when its inputs are absent |
| RF-06 | Run a multi-parameter sweep over `alpha·velocity·beta·p·q·r·altitude·x·y·z` | Should | A 2-parameter request returns the cross product |
| RF-07 | Render the α-sweep 3×2 diagram to a PNG and return a `/static/...` URL | Should | `POST …/alpha_sweep/diagram` → 200 with a resolvable URL |
| RF-08 | Compute a speed polar (V, sink) per mass, purely analytically | Should | Doubling mass scales `V` and `w` by `sqrt(2)`; the base mass is always present |
| RF-09 | Produce AVL-shaped strip forces from an in-process VLM solve by default | Must | `POST …/strip_forces` → `aero_model == "ASB"`; `?solver=avl` → `"AVL"` |
| RF-10 | Degrade to a single aggregate surface when the expected strip count does not match | Should | A mismatched geometry still returns a well-formed `StripForcesResponse` |
| RF-11 | Integrate strip forces into spanwise shear/bending moment, optionally with spar sizing | Must | `POST …/spanwise_loads_with_sizing` returns per-station required dimensions |
| RF-12 | Reject a material with non-positive `allowable_bending_stress_mpa` with 422 | Must | `sigma_allow = 0` → 422, never a division by zero |
| RF-13 | Compute and cache the aero context at the cruise point in one pipeline | Must | `GET …/assumptions/computation-context` returns all documented keys after a recompute |
| RF-14 | Publish `cd0` as **parasite** drag | Must | For a cambered wing with CL(α=0) > 0, `context.cd0 < coefficients.CD` |
| RF-15 | Publish `(L/D)max` from `½·sqrt(π·AR·e/CD0)` when the parabolic scalars exist | Must | `ld_max` matches the closed form, not the sweep argmax |
| RF-16 | Reject a polar fit through six gates and refine only the two refinable ones | Must | `negative_slope_k` is never retried; `insufficient_points` halves the α step |
| RF-17 | Surface only `category == "design"` rejections to the user | Must | A `cd0_stability_mismatch` is not shown; an `unphysical_e_oswald` is |
| RF-18 | Compute, persist and serve a stability summary keyed by `(aeroplane_id, solver)` | Must | Two runs with the same solver upsert one row; `geometry_hash` is stored |
| RF-19 | Prefer a `CURRENT` cached stability result over a `DIRTY` one | Should | With both present, `GET …/stability` returns the `CURRENT` row |
| RF-20 | Resolve a stored OP into an analysis-ready schema, rad→deg, constrained to the aircraft | Must | An OP belonging to another aeroplane → 404/422, never silently used |
| RF-21 | Prefer a non-empty manual `control_deflections` override; treat an empty dict as a no-op | Must | `{}` does not erase a fresh trim; `{"elevator": 3}` overrides `controls` |
| RF-22 | Trim one control to a target coefficient by bracketed Brent root-find | Must | `Cm → 0` within `xtol = 1e-6`; unbracketed → `converged=False` + warning, no raise |
| RF-23 | Mark every non-`DIRTY`/`COMPUTING` OP dirty on a geometry or mass/cg change | Must | Editing a wing station sets every TRIMMED OP to `DIRTY` |
| RF-24 | Re-trim DIRTY OPs in the background in their own session | Must | A dropped request does not roll back a completed retrim |
| RF-25 | Mark a corrupt OP row `INVALID` (terminal for retry) and any other failure `NOT_TRIMMED` | Must | A Pydantic error → `INVALID`; a transient solver error → `NOT_TRIMMED` |
| RF-26 | Enrich a trim with reserves, effectiveness, stability class, mixer values and warnings | Must | Usage > 0.95 emits a `critical` `authority` warning naming the surface |
| RF-27 | Report every geometry surface in the enrichment, not only the trimmed one | Should | A 3-surface aircraft trimmed on one reports 3 entries, two at `0.0` |
| RF-28 | Decompose a dual-role trim into physical left/right angles | Should | `differential_ratio` scales only the up-going side, never `d_sym` |
| RF-29 | Serialise NaN/Inf as `null` on every analysis response | Must | A NaN `Cm` arrives as `null`, not as `NaN` (invalid JSON) |
| RF-30 | Serve a coarse analysis-status roll-up per aircraft | Could | `GET …/analysis-status` → counts by OP status |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Performance | The default solver path runs **in-process**; the AVL subprocess (~1–3 s) is opt-in only | ADR 0003 (measured `~58 ms` VLM vs `~1–3 s` AVL); `app/api/utils.py:97-127` | 🟢 |
| Performance | Sweeps are vectorised into one solver call (was ~150) | `assumption_compute_service` `_coarse_alpha_sweep`, `_fine_sweep_cl_max` (gh-690) | 🟢 |
| Performance | The Oswald factor is derived from data already collected by the fine sweep — zero extra solver calls | `_e_oswald_from_sweep` (gh-636) | 🟢 |
| Performance | Panel budget is bounded: 40 spanwise panels per half, chordwise 8 | `vlm_strip_forces.py:59-60, 171` | 🟢 |
| Performance | AVL strip-force calls carry explicit timeouts (60 s airplane / 30 s wing) | `analysis_service.py:1881, 1962` | 🟢 |
| Correctness | Reference geometry is taken from the **largest** wing, not `wings[0]` | `recompute_assumptions` step 1 (gh-788) | 🟢 |
| Correctness | Unknown deflection names raise instead of being dropped | `validate_deflections_against_airplane` (BR-20) | 🟢 |
| Correctness | A stored OP is loaded constrained to its aircraft PK | `operating_point_resolver.py:138-213` | 🟢 |
| Correctness | `alpha`/`beta` magnitudes > 180 are rejected as a rad/deg mix-up | `OperatingPointSchema` field validator (gh-577/gh-587) | 🟢 |
| Robustness | A fatal solver failure in the recompute pipeline returns **without writing**, so the previous context stays valid | `recompute_assumptions` error policy | 🟢 |
| Robustness | Per-configuration polars each sit in their own `try`; a takeoff failure cannot block the landing pass | same | 🟢 |
| Robustness | The speed polar is best-effort: any failure logs and returns `None` rather than breaking the sweep | `_build_speed_polar` (`analysis_service.py:604-669`) | 🟢 |
| Robustness | A VLM strip-count mismatch degrades to one aggregate surface instead of crashing | `vlm_strip_forces.py:239-243` | 🟢 |
| Robustness | An unbracketed trim returns `converged=False`, it does not raise | `aerobuildup_trim_service` | 🟢 |
| Availability | Retrim runs outside the request in its own `SessionLocal` and owns its commit/rollback | `retrim_service.py:53-158` | 🟢 |
| Availability | `INVALID` is terminal for retry — "retrying cannot fix a corrupt row" | `retrim_service` | 🟢 |
| Observability | Every trim carries `trim_method`, `trim_score` and structured `DesignWarning`s | `TrimEnrichment` schema | 🟢 |
| Observability | Warnings accumulate on the OP row (`STALE_NO_POLAR`, `ALPHA_LIMIT_REACHED`, …) | `operating_points.warnings` JSON | 🟢 |
| Interoperability | NaN/Inf serialise as `null` on every analysis route | `NonFiniteSafeJSONResponse` | 🟢 |
| Testability | The speed polar and the load integrator are pure functions (no DB, no solver) | `_compute_speed_polar` (`:430-583`), `compute_spanwise_loads` | 🟢 |
| Testability | CI's fast tier runs **without** AeroSandbox, so ASB-dependent service code needs mocked tests that stub the solver boundary | ADR 0003 / ADR 0015 | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Solver dispatch

  Scenario: The default path never spawns a subprocess
    Given an aircraft with three lifting surfaces
    When I POST /aeroplanes/{id}/alpha_sweep
    Then the analysis runs with method "aerobuildup"
    And no AVL process is started

  Scenario: AVL refuses a sweep
    Given an operating point whose alpha is a list of values
    When I request the analysis with analysis_tool "avl"
    Then a ValueError is raised with the message
         "AVL analysis does not support parameter sweeps"

Feature: Characteristic points

  Scenario: Zero-lift drag is interpolated at the CL sign change
    Given an alpha sweep whose CL changes sign between samples i and i+1
    When the characteristic points are computed
    Then drag_at_zero_lift_point is interpolated at t = -CL_i / (CL_i+1 - CL_i)

  Scenario: No CL sign change falls back to the closest sample
    Given an alpha sweep whose CL never crosses zero
    When the characteristic points are computed
    Then drag_at_zero_lift_point is taken at argmin(|CL|)

Feature: The single aero truth

  Scenario: CD0 excludes induced drag
    Given a cambered wing that lifts at alpha = 0
    When recompute_assumptions runs at the cruise point
    Then context.cd0 equals CD_total minus CL^2 / (pi * AR * e)
    And context.cd0 is strictly less than the analysis CD

  Scenario: L over D max comes from the closed form
    Given a parabolic polar with CD0 and e available
    When the context is published
    Then ld_max equals 0.5 * sqrt(pi * AR * e / CD0)
    And it is not the argmax of CL/CD over the raw sweep

  Scenario: A design-category rejection is shown, a consistency one is not
    Given a polar fit whose Oswald factor is 1.4
    When the fit is rejected
    Then the rejection gate is "unphysical_e_oswald" with category "design"
    And it is surfaced to the user
    But a "cd0_stability_mismatch" rejection stays internal

  Scenario: Refinement raises resolution, never lowers a threshold
    Given a fit rejected with gate "insufficient_points"
    When the refinement runs
    Then the alpha step is halved and the margin multiplied by 1.5
    And the six gate thresholds are unchanged
    And auto_refined is true only if a fit was actually produced

Feature: Operating-point coherence

  Scenario: A stored operating point is resolved in degrees
    Given a stored operating point with alpha 0.0873 radians
    When it is resolved for analysis
    Then the schema reports alpha 5.0 degrees

  Scenario: An empty override cannot erase a fresh trim
    Given a TRIMMED operating point with controls {"elevator": -3.2}
    And control_deflections set to an empty dict
    When the operating point is resolved
    Then the deflections used are {"elevator": -3.2}

  Scenario: Cross-aeroplane injection is refused
    Given an operating point id belonging to a different aeroplane
    When it is resolved for this aircraft
    Then the row is not found and no analysis runs

Feature: Invalidation and retrim

  Scenario: A geometry edit dirties every operating point
    Given three TRIMMED operating points
    When a wing cross-section is updated
    Then all three have status DIRTY

  Scenario: A corrupt row is not retried forever
    Given a DIRTY operating point whose stored row fails Pydantic validation
    When retrim_dirty_ops processes it
    Then its status becomes INVALID
    And a later retrim does not pick it up

  Scenario: No pitch control leaves the operating points dirty
    Given an aircraft with no TED whose role is elevator, stabilator, elevon or ruddervator
    When retrim_dirty_ops runs
    Then the operating points stay DIRTY
    And a warning is logged

Feature: Trim enrichment

  Scenario: A near-limit deflection is a critical warning
    Given a surface with limits (25, 25) trimmed to -24.5 degrees
    When the enrichment is computed
    Then usage_fraction is above 0.95
    And a critical design warning of category "authority" names that surface

  Scenario: Untrimmed surfaces are still reported
    Given an aircraft with three control surfaces, trimmed on one
    When the enrichment is computed
    Then three surface deflections are reported
    And the two untrimmed ones are 0.0

  Scenario: A dual-role aircraft falls back to the wrong limits today
    Given a ruddervator whose control variable is "[ruddervator]pitch_htail_1"
    And deflection limits keyed by the DB name "ruddervator_right"
    When the enrichment is computed
    Then the reserve uses the hard-coded (25, 25) limits
    And a phantom surface at 0 degrees appears under the DB name
    # 🟢 resolved structurally (Q-WD-1)
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| One dispatcher + one result envelope (RF-01…RF-04) | Must | Every analysis path in the system funnels through it; solver-agnostic downstream code depends on it |
| The aero context pipeline (RF-13…RF-17) | Must | BR-14: nine consumers read it. A wrong `cd0` silently corrupts sizing, endurance, matching chart and V-n at once |
| Parasite-vs-total CD0 (RF-14) | Must | The gh-924 defect class; collapses `(L/D)max` by ~30 % when wrong |
| OP resolution + deflection validation (RF-20, RF-21, RF-04) | Must | BR-19/BR-20 — silent wrongness otherwise: a plot labelled "trimmed" that never was |
| Invalidation + background retrim (RF-23…RF-25) | Must | Without it every stored trim silently ages out of date after a geometry edit |
| Stability persistence (RF-18) | Must | Read by the CG envelope, SM suggestion and the copilot |
| Strip forces + spanwise loads (RF-09, RF-11, RF-12) | Must | Feeds structural spar sizing — a safety output |
| Trim enrichment (RF-26) | Must | The only place control authority is checked against real limits |
| α sweep + characteristic points (RF-05) | Must | The workbench's primary aerodynamic view |
| Speed polar (RF-08) | Should | A derived chart; failure is already best-effort and returns `None` |
| α-sweep PNG diagram (RF-07) | Should | A rendering convenience over data already returned by RF-05 |
| Simple parameter sweep (RF-06) | Should | A diagnostic surface; not on any automatic path |
| Aggregate-surface degradation (RF-10) | Should | Preserves a usable response on unusual geometry |
| Dual-role decomposition in enrichment (RF-28) | Should | Display-only kinematics (BR-10); does not affect the solution |
| Analysis-status roll-up (RF-30) | Could | A convenience read for the workbench header |
| Fixing #955 in trim/retrim/stability | **Must (open)** | Confirmed defect owned by this module; blocks correct authority reporting on every V-tail / elevon aircraft |
| Removing `_auto_populate_cd0` | **Must (open)** | Confirmed BR-14 violation writing total CD into the `cd0` assumption |
| Seeding `min/max_static_margin` | Should (open) | Today the 5 % / 25 % bounds are unreachable configuration |
| Re-deriving `cd0`/`e` anywhere outside the context | Won't | Explicitly forbidden by BR-14 / ADR 0004 |
| A fourth solver, or AVL on a default path | Won't | ADR 0003 |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/api/utils.py` | `analyse_aerodynamics`, `_as_array_if_needed` | 🟢 |
| `app/services/analysis_service.py` | `_compute_alpha_sweep_characteristic_points`, `_compute_speed_polar`, `_build_speed_polar`, `_cl_to_alpha_deg`, `analyze_airplane_spanwise_loads`, `_surface_to_stations`, `_get_tc_by_y_for_surface` | 🟢 |
| `app/services/vlm_strip_forces.py` | `_strip_index_ranges`, `_wing_strip_counts`, `_panels_per_segment`, `remesh_uniform_density`, `_remesh_airplane`, `_blend_xsec` | 🟢 |
| `app/services/stability_service.py` | `get_stability_summary`, `compute_geometry_hash`, `persist_stability_result`, `get_cached_stability`, `_get_margin_bounds`, `_find_trim_elevator`, `_auto_populate_cd0` | 🟢 |
| `app/services/assumption_compute_service.py` | `recompute_assumptions`, `_parasite_cd0`, `_fit_parabolic_polar(_with_refinement)`, `_e_oswald_from_sweep`, `_coarse_alpha_sweep`, `_fine_sweep_cl_max`, `_extract_cl_alpha_from_linear_sweep`, `_picard_iterate_speed`, `_cache_context`, `apply_turbulator_delta_to_cd0` | 🟢 |
| `app/services/aerobuildup_trim_service.py` | `trim_with_aerobuildup` (Brent) | 🟢 |
| `app/services/operating_point_resolver.py` | `resolve_operating_point`, `operating_point_model_to_schema`, `_pick_deflections`, `_require_field`, `validate_deflections_against_airplane` | 🟢 |
| `app/services/retrim_service.py` | `retrim_dirty_ops`, `_find_pitch_control_name` | 🟢 |
| `app/services/invalidation_service.py` | `mark_ops_dirty`, `_OP_AFFECTING_PARAMS`, `_RECOMPUTE_TRIGGERING_PARAMS` | 🟢 |
| `app/services/trim_enrichment_service.py` | `compute_enrichment`, `build_deflection_limits_from_schema`, `decompose_dual_role` | 🟢 / 🔴 (#955) |
| `app/services/polar_re_table_service.py` | `build_re_table`, `lookup_cd0_at_v`, `lookup_e_oswald_at_v` | 🟢 |
| `app/models/analysismodels.py` | `OperatingPointModel`, `OperatingPointSetModel` | 🟢 |
| `app/models/stability_result.py`, `app/models/stability_events.py` | `StabilityResultModel` + dirty listeners | 🟢 |
| `cad_designer/airplane/aircraft_topology/models/analysis_model.py` | `AnalysisModel`, `from_avl_dict`, `from_abu_dict` | 🟢 read-only (ADR 0002) |
| `app/api/v2/endpoints/aeroanalysis.py` | 17 routes | 🟢 |
| `app/api/v2/endpoints/operating_points.py` | 19 routes | 🟢 |
| `app/api/v2/endpoints/aeroplane/speed_polar.py` | `GET …/speed-polar` | 🟢 |
