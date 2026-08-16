# aero-analysis — Implementation Tasks

> Executable sequence to re-implement the module from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.
> Nested use cases carry their own task lists:
> [`operating-point-solve`](operating-point-solve/tasks.md) ·
> [`stability-derivatives`](stability-derivatives/tasks.md) ·
> [`aero-context-single-source`](aero-context-single-source/tasks.md) ·
> [`retrim-invalidation`](retrim-invalidation/tasks.md).

## Prerequisites

- [ ] **AeroSandbox ≥ 4.0.7** available. The lower bound is a **correctness**
      pin, not an API pin: the VLM `Cnbeta` sign flip was fixed in 4.0.7
      (ADR 0003).
- [ ] SciPy (`optimize.brentq`) for the AeroBuildup trim.
- [ ] Matplotlib for the α-sweep diagram; a writable `tmp/` mounted as
      `/static` (`.claude/rules/worktree-setup.md`).
- [ ] `wing-design` + `fuselage-design` able to produce an `asb.Airplane`
      (`aeroplane_service.get_aeroplane_airplane_configuration`).
- [ ] `mission-and-sizing` design assumptions seeded (`mass`, `cg_x`, `cl_max`,
      `g_limit`, `target_static_margin`, `power_to_weight`, `prop_efficiency`).
- [ ] `platform-core`: `get_db()` transaction boundary (BR-78), the event bus,
      the debounced job tracker, `NonFiniteSafeJSONResponse`.
- [ ] `avl-integration` present **only** for the opt-in AVL paths; the module
      must be fully functional without an AVL binary.
- [ ] Tables `operating_points`, `operating_pointsets`, `stability_results`,
      and the `aeroplanes.assumption_computation_context` JSON column.

## Tasks

- [ ] **T-01 — The solver-agnostic result envelope.**
  Implement `AnalysisModel` with `method ∈ {avl, aerobuildup, vortex_lattice}`,
  `reference` (`Sref/Cref/Bref/Xref/Yref/Zref/Xnp/Xnp_lat/Strips`), `forces`,
  `moments`, `coefficients`, `derivatives`, `control_surfaces`,
  `flight_condition`, plus the two adapters `from_avl_dict` and `from_abu_dict`.
  - Legacy origin: `cad_designer/airplane/aircraft_topology/models/analysis_model.py:242, :301, :480`
  - Definition of done: the same aircraft analysed with all three tools yields
    identical field names; downstream code reads only `reference.Xnp`,
    `coefficients.*`, `derivatives.*` and never branches on `method`.
  - Confidence: 🟢

- [ ] **T-02 — The one solver dispatcher.**
  `analyse_aerodynamics(analysis_tool, operating_point, asb_airplane, …)`
  returning `(AnalysisModel, Figure | None)`. Always build
  `asb.OperatingPoint(velocity, alpha, beta, p, q, r,
  atmosphere=asb.Atmosphere(altitude))`, always set
  `asb_airplane.xyz_ref = operating_point.xyz_ref`, and apply
  `with_control_deflections` only when overrides are present.
  - Legacy origin: `app/api/utils.py:97-127`
  - Definition of done: this is the **only** function in the codebase that names
    a solver class; a grep for `AeroBuildup(` / `VortexLatticeMethod(` /
    `AVLRunner(` outside it and `vlm_strip_forces` returns nothing.
  - Confidence: 🟢

- [ ] **T-03 — `_as_array_if_needed` and the AVL sweep rejection.**
  Wrap any non-`float` `alpha`/`beta` in `np.array`. On the AVL branch raise
  `ValueError("AVL analysis does not support parameter sweeps")` and require
  `avl_file_content`.
  - Legacy origin: `app/api/utils.py:19`, AVL branch of `analyse_aerodynamics`
  - Definition of done: a list-valued `alpha` produces same-shape result arrays
    from AeroBuildup and the exact error string from AVL.
  - Confidence: 🟢

- [ ] **T-04 — Uniform-density remesh for the VLM path (gh-855/gh-857).**

  ```
  budget = _SPANWISE_PANELS_PER_HALF = 40
  n_i    = max(_MIN_PANELS_PER_SEGMENT = 2, round(budget · span_i / Σ span))
  span_i = hypot(Δy, Δz)
  ```

  Insert blended sections (`_blend_xsec`: linear `chord`/`twist`/`xyz_le`,
  `Airfoil.blend_with_another_airfoil`, falling back to the inboard airfoil on
  any blend exception), then run with `spanwise_resolution=1` and
  `spanwise_spacing_function=np.linspace`. Re-assert `s_ref`, `b_ref`, `c_ref`,
  `xyz_ref` from the original airplane afterwards.
  - Legacy origin: `app/services/vlm_strip_forces.py` (`_panels_per_segment`,
    `remesh_uniform_density`, `_remesh_airplane`, `_blend_xsec`)
  - Definition of done: a wing with a 5 cm and a 95 cm segment gets panel counts
    in ≈ 1:19 ratio (floor 2); `cl(y)` shows no spike at the short segment; the
    reference geometry after the remesh equals the geometry before it.
  - Confidence: 🟢

- [ ] **T-05 — VLM strip forces in AVL's shape (gh-674).**
  Close a strip on every `is_trailing_edge` flag (panels are chordwise-fastest);
  compute the expected count as
  `segments · spanwise_resolution · (2 if symmetric else 1)` and **degrade to a
  single aggregate surface** on mismatch. Decompose forces with
  `d_hat = steady_freestream_direction`, `l_hat = normalise([−d_z, 0, d_x])`;
  emit `cdv = cm_c/4 = cm_LE = 0.0` and `C.P.x/c = 0.25`.
  - Legacy origin: `app/services/vlm_strip_forces.py:59-60, :171, :239-243`
  - Definition of done: the emitted dict is consumable by
    `_strip_surfaces_from_result` unchanged, side by side with the AVL parser's
    output; `aero_model == "ASB"`; a deliberately mismatched geometry returns one
    aggregate surface instead of raising.
  - Confidence: 🟢

- [ ] **T-06 — Six characteristic points from an α sweep.**
  Implement the fixed six-key dict exactly as tabulated in
  [`design.md`](design.md) §A1, including the `|CD| > 1e-12` guard, the
  interpolation `t = −CL_i/(CL_{i+1}−CL_i)` at the first sign change, the
  `argmin(|CL|)` fallback, and the two-condition stall rule.
  - Legacy origin: `app/services/analysis_service.py:107-250`
  - Definition of done: every key is present on every response; each is `None`
    only when its inputs are absent; a synthetic polar with a known crossing
    reproduces the interpolated `CD` to floating-point tolerance.
  - Confidence: 🟢

- [ ] **T-07 — The pure speed-polar function.**
  `V = sqrt(2·m·g/(ρ·S_ref·CL))`, `w = V·(CD/CL)` for every point with `CL > 0`;
  one curve per mass with the base mass flagged; `V_stall` from `CL_max`;
  `i_min_sink = argmin(w)`, `i_best = argmax(CL/CD)`. Display bounds
  `0.7·min(V_stall)` / `1.3·V_dive`, dropped **as a pair** when either is missing
  or the pair is inverted (gh-799). Label α via the cached lift curve (gh-871).
  - Legacy origin: `app/services/analysis_service.py:430-583`
  - Definition of done: no DB and no solver import in the function; doubling the
    mass scales `V` and `w` by `sqrt(2)`; a missing `v_axis_max` also removes
    `v_axis_min`.
  - Confidence: 🟢

- [ ] **T-08 — Best-effort speed-polar glue, with the mass gap made loud.**
  Wrap T-07 so any failure logs and returns `None` rather than breaking the
  sweep response.
  - Legacy origin: `app/services/analysis_service.py:604-669`
  - Definition of done: an exception inside the polar leaves the α-sweep
    response intact with `speed_polar = null`.
  - 🟡 **The 1.0 kg fallback is removed so no invented mass reaches a polar** (`Q-AA-3`, derived from `P-WARN-0`). The legacy defaults a missing `mass` to **1.0 kg**
    with only a log warning (l.617-623), producing a structurally valid but
    physically meaningless polar. Re-implement as an explicit
    **design warning on the response** (ADR 0012) rather than a silent default.
  - Confidence: 🟢 for the behaviour, 🔴 for the intended fix

- [ ] **T-09 — Spanwise load integration and the sizing entry point.**
  Reuse the selected strip-force path, inject `q = ½·ρ·V²`, call the pure
  `compute_spanwise_loads`. With `spar_params`: require a `material`
  `ComponentModel` with a **positive** `allowable_bending_stress_mpa` (or
  `sigma_allow_mpa_override`) — **422** otherwise; read `g_limit` from
  `get_effective_assumption` falling back to `_G_LIMIT_DEFAULT = 3.0` with
  `g_limit_fallback = True`; size on the half with the larger root bending
  moment `max(|M_sb|, |M_pt|)`; build real `t/c` per station via
  `_get_tc_by_y_for_surface` and **omit** unresolvable stations so the
  `_TC_FALLBACK = 0.12` in the sizing layer applies.
  - Legacy origin: `app/services/analysis_service.py:1987-2091, :2099-2101, :2129-2150`
  - Definition of done: `sigma_allow = 0` returns 422 and never divides;
    `g_limit_fallback` is `true` when the assumption is missing; the sized half
    is the one with the larger root moment.
  - Confidence: 🟢

- [ ] **T-10 — Vectorised sweeps.**
  `_coarse_alpha_sweep`, `_fine_sweep_cl_max` and
  `_extract_cl_alpha_from_linear_sweep` each issue **one** `AeroBuildup.run()`
  over an array-shaped `OperatingPoint`. Build the fine grid with
  `np.meshgrid(alphas, velocities, indexing="xy")` — **V-outer / α-inner** ravel
  order. `v_stall_approx = max(0.5·V_cruise, 3.0)`;
  `velocities = linspace(v_stall_approx, v_max, fine_velocity_count)`;
  `alphas = arange(stall_α ± margin, step)`.
  - Legacy origin: `app/services/assumption_compute_service.py` (gh-690)
  - Definition of done: one solver call per sweep (assert on a mock); the ravel
    order matches what the polar fit and the Re-table indexing expect.
  - Confidence: 🟢

- [ ] **T-11 — Parasite CD0.**

  ```
  CD_induced = CL² / (π · AR · e)      # e = AeroBuildup's oswalds_efficiency
  CD0        = CD_total − CD_induced   # only when CL/AR/e are sane AND result > 0
  ```

  - Legacy origin: `app/services/assumption_compute_service.py:1098-1112`
  - Definition of done: a cambered wing lifting at α = 0 yields
    `context.cd0 < coefficients.CD`; on a symmetric wing at CL ≈ 0 the two
    converge.
  - Confidence: 🟢

- [ ] **T-12 — `(L/D)max` from the self-consistent scalars.**
  `E_max = ½·sqrt(π·AR·e/CD0)`, `CL_at_E_max = sqrt(CD0·π·AR·e)`. Keep the
  measured sweep argmax **only** as the fallback when the parabolic scalars are
  unavailable.
  - Legacy origin: `app/services/assumption_compute_service.py:282-300` (Scholz eq. 5.39)
  - Definition of done: the eHawk regression case reports ≈ 23.4 @ CL 0.55, not
    18.8 @ CL 0.98.
  - Confidence: 🟢

- [ ] **T-13 — The parabolic fit with six gates and refinement.**
  Fit `CD = CD0 + k·CL²` by OLS over `CL ∈ [max(0.10, 0.10·CL_max),
  0.85·CL_max]`, `e = 1/(π·AR·k)`. Implement all six gates with their canonical
  categories (table in [`requirements.md`](requirements.md) BR-16), enforce the
  gate→category pair with a model validator, and surface **only**
  `category == "design"`. Refine **only** `insufficient_points` and
  `non_monotonic_polar`: halve the α step, multiply the margin by 1.5, max 2
  attempts, set `auto_refined` only on an actual fit.
  - Legacy origin: `app/services/assumption_compute_service.py:1417-1610, :1618-1694`
  - Definition of done: a `negative_slope_k` rejection is never retried; no test
    can make a threshold move; a rejected fit leaves `cd0`/`e_oswald` as `None`
    with a `PolarRejection` attached.
  - Confidence: 🟢

- [ ] **T-14 — The Oswald provenance chain.**
  `aerobuildup_trefftz` → `fit` → `fallback`, recorded per configuration in
  `e_oswald_provenance` and mirrored by `context["e_oswald_fallback_used"]`.
  Derive `e = CL²/(π·AR·CDi)` at the `(L/D)max` sample with
  `CDi = D_induced/(q·S_ref)` collected **during** the fine sweep (zero extra
  solver calls, gh-636); clip to `0 < e ≤ 1.10`;
  `e_oswald_effective = e or 0.8`.
  - Legacy origin: `app/services/assumption_compute_service.py:1412` (clip),
    `_e_oswald_from_sweep`
  - Definition of done: no additional `AeroBuildup.run()` is issued for `e`;
    `e = 1.3` is rejected; the provenance value is present on every polar.
  - Confidence: 🟢

- [ ] **T-15 — Turbulator ΔCD0 without poisoning the gate (gh-935).**
  Add `ΔCD0` (area-weighted, ×2 for a symmetric wing) to the stored `cd0`, but
  keep `raw_cd0` and pass **that** as `cd0_stability` to every fit.
  - Legacy origin: `app/services/assumption_compute_service.py:2099-2168`
  - Definition of done: enabling a turbulator with a meaningful ΔCD0 does not
    trip `cd0_stability_mismatch`.
  - Confidence: 🟢

- [ ] **T-16 — Closed-form V-speeds with the Picard pass and the sub-stall clamp.**
  Implement the V-speed block verbatim from [`design.md`](design.md) §A6.
  `_picard_iterate_speed` does **exactly one** pass (look up `cd0`/`e` at `V₀` in
  the Re-table, re-solve, accept `V₁`, warn at `|ΔV|/V₀ ≥ 5 %`) for `V_md`,
  `V_min_sink`, `V_max`. Clamp `V_md` and `V_min_sink` to `max(V, V_stall)`
  (gh-683). Read `V_x`/`V_y` back from the OP rows, leaving them `None` before
  generation.
  - Legacy origin: `app/services/assumption_compute_service.py:2033` and the
    V-speed block
  - Definition of done: `V_ms ≈ 0.760 · V_md` on a clean polar; a high-AR draggy
    polar produces `V_md ≥ V_stall`; the Picard loop runs once, never twice.
  - Confidence: 🟢

- [ ] **T-17 — The context cache and its error policy.**
  Implement `recompute_assumptions` as the 13-step pipeline of
  [`design.md`](design.md) §A6, including step 1's
  `main_wing = argmax(wing.area())` override and the three-layer error policy
  (fatal / degraded / guarded). Write **only** through `_cache_context`.
  - Legacy origin: `app/services/assumption_compute_service.py:59-809`
  - Definition of done: a stability-run failure leaves the previous context
    untouched; a takeoff-polar failure still produces a landing polar; a
    flap-name parity mismatch produces the no-flap fallback with an
    "investigate the converter" warning instead of an `AssertionError` (gh-537);
    an aircraft without wings is skipped silently.
  - Confidence: 🟢

- [ ] **T-18 — Re-table backfill (gh-924).**
  After building the Re-banded table, overwrite every row with
  `fallback_used or cd0 is None` using the single-source parasite `cd0` and the
  Trefftz `e`.
  - Legacy origin: `app/services/assumption_compute_service.py:444-449`
  - Definition of done: no consumer can read `0.03 / 0.8` from a table row while
    the context holds different authoritative values.
  - Confidence: 🟢

- [ ] **T-19 — Stability summary, persistence and geometry hash.**
  Implement the formula block of [`requirements.md`](requirements.md) BR-AA14;
  hash only the stability-relevant geometry (per-wing
  `x_le/y_le/z_le/chord/twist`, per-fuselage `x_c/width/height`) to
  `sha256[:16]`; upsert on `uq_stability_aeroplane_solver`.
  - Legacy origin: `app/services/stability_service.py:102-141, :289-362`
  - Definition of done: two runs with the same solver leave one row; changing a
    chord changes the hash; changing an unrelated field (e.g. a spar) does not.
  - Confidence: 🟢
  - 🟡 **Drop the dead lookup and promote the 5 % / 15 % band** (`Q-AA-2`, derived). The legacy reads `min_static_margin` /
    `max_static_margin` assumptions that are never seeded, so the 5 % / 25 %
    bounds are unreachable. Either seed them or make the defaults explicit
    constants.

- [ ] **T-20 — Remove `_auto_populate_cd0` (BR-14 violation).**
  The legacy writes `result.CD` (**total** CD) into the `cd0` assumption with
  source `"stability_analysis"` on a different trigger from the recompute.
  - Legacy origin: `app/services/stability_service.py:257-281`
  - Definition of done: `cd0` has exactly **one** writer,
    `assumption_compute_service`; a stability run leaves the assumption
    untouched.
  - Confidence: 🟢 (confirmed defect; decided in the validation interview)

- [ ] **T-21 — Operating-point resolution (gh-577).**
  Implement `resolve_operating_point` with all four guards: pass-through when
  no id; load **constrained to `aircraft_pk`**; require `TRIMMED` unless
  `require_trimmed=False`; convert `alpha`/`beta` rad→deg. `_pick_deflections`:
  non-empty `control_deflections` wins, otherwise `controls`; an **empty** dict
  is a no-op. `_require_field` raises instead of substituting `0.0`.
  - Legacy origin: `app/services/operating_point_resolver.py:138-213`
  - Definition of done: an OP id from another aeroplane is not found; `{}` does
    not erase a trim; `0.0873 rad` reads back as `5.0 deg`.
  - Confidence: 🟢

- [ ] **T-22 — Deflection-name validation (BR-20).**
  `validate_deflections_against_airplane` raises a **422** listing unknown vs
  available names. Call it from the streamline, four-view, strip-force and
  AeroBuildup-trim paths.
  - Legacy origin: `app/services/operating_point_resolver.py`
  - Definition of done: a renamed surface cannot produce a clean run labelled
    "trimmed"; the error body names both sets.
  - Confidence: 🟢

- [ ] **T-23 — AeroBuildup trim by bracketed Brent root-find.**
  `brentq(residual, lower, upper, xtol=1e-6, maxiter=50)` with
  `residual(δ) = coeff(δ) − target`, one
  `run_with_stability_derivatives()` per evaluation. When
  `f(lower)·f(upper) > 0`, return `converged=False` with a detailed warning —
  **do not raise**. Resolve the trim variable from the tagged name, the display
  name **or** a role name; a role resolves to that surface's **primary
  (pitch/lift)** axis.
  - Legacy origin: `app/services/aerobuildup_trim_service.py`
  - Definition of done: `Cm → 0` within tolerance on a trimmable aircraft; an
    untrimmable one returns a structured non-convergence, never a 500.
  - Confidence: 🟢

- [ ] **T-24 — Invalidation fan-in.**
  `mark_ops_dirty(session, aeroplane_id)` sets `DIRTY` on every OP **not
  already** `DIRTY`/`COMPUTING`. Register `after_insert/update/delete` listeners
  on `WingModel`, `WingXSecModel`, `FuselageModel` **once**; each marks its own
  table dirty, calls `mark_ops_dirty` and publishes `GeometryChanged`. Route
  `GeometryChanged` → `schedule_retrim` **and**
  `schedule_recompute_assumptions`; `AssumptionChanged` → retrim only for
  `_OP_AFFECTING_PARAMS = {mass, cg_x}` and recompute only for
  `_RECOMPUTE_TRIGGERING_PARAMS = {target_static_margin, mass}`.
  - Legacy origin: `app/services/invalidation_service.py:26-36`,
    `app/models/stability_events.py`, `app/models/avl_geometry_events.py`
  - Definition of done: `cg_x`, `cd0` and `cl_max` are **excluded** from the
    recompute set (they are the recompute's own outputs — including them loops);
    one geometry write publishes `GeometryChanged` **once**.
  - 🟡 **Factor the shared listener out so a geometry write publishes `GeometryChanged` once** (`Q-AA-4`, derived; ADR 0022 applied to invalidation paths). The legacy registers the listeners **twice**; do not reproduce that.
  - Confidence: 🟢

- [ ] **T-25 — Background retrim.**
  `retrim_dirty_ops(aeroplane_id)` opens its **own** `SessionLocal` (it runs
  outside a request and owns the commit/rollback), finds the first TED whose
  `role ∈ _PITCH_ROLES = {elevator, stabilator, elevon, ruddervator}`, and per
  DIRTY OP: `COMPUTING` → `trim_with_aerobuildup(Cm = 0)` → `TRIMMED` (writing
  the deflection into `control_deflections`) or `LIMIT_REACHED`. A
  `ValidationDomainError` / Pydantic error → `INVALID` (**terminal for retry**);
  any other exception → `NOT_TRIMMED` (retryable). When at least one OP trimmed,
  recompute stability from the first trimmed OP.
  - Legacy origin: `app/services/retrim_service.py:53-158`
  - Definition of done: a corrupt row ends `INVALID` and is not picked up again;
    a transient failure ends `NOT_TRIMMED`; with no pitch-role TED the OPs stay
    `DIRTY` and a warning is logged.
  - 🟢 Resolved via the mixing resolver (`Q-WD-1`) — use the
    gh-772 mixing name instead.
  - Confidence: 🟢

- [ ] **T-26 — Trim enrichment.**
  Implement `compute_enrichment` as the single entry point for all three trim
  paths, with the threshold block from [`requirements.md`](requirements.md)
  BR-AA20, the gh-863 union (`dict.fromkeys(limits, 0.0)` updated with
  `controls`), and `decompose_dual_role`:

  ```
  d_sym  = mix_gain_primary   · δ_primary
  d_anti = mix_gain_secondary · δ_secondary
  right  =  d_anti ; left = −d_anti
  the negative (up-going) side is scaled by differential_ratio
  deflection_left/right = d_sym + left/right       # differential never scales d_sym
  ```

  Keep `trim_residuals` typed `dict[str, float]` — the solver path belongs on
  `trim_method`, **never** in the residuals (gh-627).
  - Legacy origin: `app/services/trim_enrichment_service.py:380-572`, `:72-118`
  - Definition of done: usage > 0.95 emits a `critical`/`authority` warning
    naming the surface; three surfaces are reported when one is trimmed; a
    string in `trim_residuals` fails validation.
  - 🟢 **Decided (`Q-WD-1`):** key `limits` by the **gh-772 mixing
    name**, not by the raw DB TED name, so the hard-coded ±25° fallback and the
    phantom 0° surface disappear on dual-role aircraft.
  - Confidence: 🟢 for the behaviour, 🔴 for the naming fix

- [ ] **T-27 — Non-finite-safe responses.**
  Mount every analysis route on a router whose `default_response_class`
  serialises NaN/Inf as `null`. Extend it to the operating-point router.
  - Legacy origin: `app/api/v2/endpoints/aeroanalysis.py:43`,
    `app/core/json_safe.py`
  - Definition of done: a NaN `Cm` arrives as `null`; the payload is valid JSON.
  - 🟡 The legacy operating-point router uses a plain `APIRouter()` — a
    deliberate extension, not a reproduction.
  - Confidence: 🟢

- [ ] **T-28 — The α-sweep diagram.**
  Render the 3×2 matplotlib figure (coefficients, CL–CD polar, CL–Cm, L/D,
  `Xnp`/`Xnp_lat`, summary) with collision-avoiding annotations and the
  colour-coded trend strips (`dCm/dα < −0.01` green / `≤ 0.01` amber / else
  red), save under `tmp/{uuid}/png/alpha_sweep_<hex>.png`, return a
  `/static/...` URL.
  - Legacy origin: `get_alpha_sweep_diagram_url` in `analysis_service.py`
  - Definition of done: the URL resolves through the static mount; the trend
    colour matches the sign of `dCm/dα`.
  - Confidence: 🟢

- [ ] **T-29 — The REST surface.**
  Wire all 17 analysis routes, 19 operating-point routes and the speed-polar
  route exactly as tabulated in [`contracts.md`](contracts.md), at the
  application root (`prefix=""`), with `_raise_http_from_domain` on every
  handler.
  - Legacy origin: `app/api/v2/endpoints/aeroanalysis.py`,
    `…/operating_points.py`, `…/aeroplane/speed_polar.py`, `app/main.py:225-227`
  - Definition of done: the generated OpenAPI matches the contract table
    (method, path, request model, response model, documented status codes).
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Dispatcher happy path (all three tools).** One aircraft, three
      tools, identical `AnalysisModel` field set; `method` differs.
- [ ] **TT-02 — AVL rejects a sweep.** Array-valued `alpha` + `analysis_tool=avl`
      → the exact `ValueError` message.
- [ ] **TT-03 — Unknown deflection name → 422** listing unknown vs available.
- [ ] **TT-04 — Characteristic points, synthetic polar.** Known CL/Cm crossings
      reproduce the interpolated values; each key is `None` only when its inputs
      are absent.
- [ ] **TT-05 — Speed polar purity and mass scaling.** No DB/solver import;
      `V, w ∝ sqrt(m)`; axis bounds dropped as a pair.
- [ ] **TT-06 — Parasite CD0.** Cambered wing: `context.cd0 < CD_total`.
- [ ] **TT-07 — `(L/D)max` closed form.** eHawk regression: ≈ 23.4 @ CL 0.55.
- [ ] **TT-08 — Six gates, two refinable.** Each gate fires on a crafted polar;
      `negative_slope_k` is never retried; thresholds are immutable across the
      whole suite.
- [ ] **TT-09 — Only `design` rejections are user-visible.**
- [ ] **TT-10 — Turbulator ΔCD0 does not trip the 20 % gate.**
- [ ] **TT-11 — One solver call per sweep.** Mocked `AeroBuildup.run` asserts
      `call_count == 1` for coarse, fine and lift-curve sweeps.
- [ ] **TT-12 — Recompute error policy.** Fatal → nothing written; takeoff
      failure → landing polar still produced; flap-parity mismatch → warning,
      not `AssertionError`; no wings → silent skip.
- [ ] **TT-13 — Re-table backfill.** No row can report `0.03/0.8` while the
      context holds different values.
- [ ] **TT-14 — Stability upsert + hash.** Two runs, one row; chord change
      changes the hash; spar change does not.
- [ ] **TT-15 — OP resolution.** rad→deg; cross-aeroplane id refused; `{}`
      override is a no-op; NULL NOT-NULL column raises.
- [ ] **TT-16 — Brent trim.** Converges on a trimmable aircraft; unbracketed →
      `converged=False` + warning, no exception.
- [ ] **TT-17 — Invalidation.** A wing edit dirties every non-DIRTY/COMPUTING
      OP; `GeometryChanged` is published exactly **once**.
- [ ] **TT-18 — Retrim status transitions.** Pydantic error → `INVALID` and not
      retried; other exception → `NOT_TRIMMED`; no pitch role → still `DIRTY` +
      warning.
- [ ] **TT-19 — Enrichment thresholds.** 0.96 usage → critical; 0.85 → warning;
      three surfaces reported when one is trimmed.
- [ ] **TT-20 — `trim_residuals` rejects strings** (gh-627 regression).
- [ ] **TT-21 — Dual-role naming (bug #955 regression).** A ruddervator's
      reserve is computed against its **real** TED limits, not ±25°, and no
      phantom 0° surface appears.
- [ ] **TT-22 — NaN → `null`** on an analysis response; the body parses as JSON.
- [ ] **TT-23 — VLM strip-count mismatch** degrades to one aggregate surface.
- [ ] **TT-24 — Sizing rejects `σ_allow ≤ 0` with 422**, never dividing.
- [ ] **TT-25 — Fast-tier coverage.** Every task above has at least one test that
      runs **without** AeroSandbox installed, stubbing the solver boundary
      (ADR 0015 — the CI fast tier has no aero dependencies, so unmocked tests
      leave this code uncovered against the 80 % new-code gate).

## Data Migration Tasks

- [ ] **TM-01 — `operating_points`.** Columns per
      [`contracts.md`](contracts.md); `alpha`/`beta` in **radians**; `warnings`,
      `controls`, `xyz_ref`, `trim_enrichment` as JSON; `status` defaulting to
      `NOT_TRIMMED`.
      🟡 The legacy FK `aircraft_id → aeroplanes.id` has **no `ondelete`**
      clause — add `ON DELETE CASCADE`.
- [ ] **TM-02 — `operating_pointsets`.** 🟡 The legacy stores
      `operating_points` as a **JSON id list** with no referential integrity;
      consider a real association table.
- [ ] **TM-03 — `stability_results`** with
      `UniqueConstraint(aeroplane_id, solver)` and `ON DELETE CASCADE`.
      🟡 Replace the `status ASC` string ordering with an explicit enum rank.
- [ ] **TM-04 — `aeroplanes.assumption_computation_context`** JSON column; keys
      per [`../data-dictionary.md`](../data-dictionary.md).

## Suggested Order

1. **T-01 → T-03** first: the envelope and the dispatcher are the seam every
   later task plugs into.
2. **T-04, T-05** (VLM remesh + strips) before **T-09** (loads) — the loads path
   consumes the strip dict.
3. **T-06, T-07, T-08** (sweep post-processing) are pure and can be built in
   parallel with the solver work.
4. **T-10 → T-18** are the context pipeline and must be done in that order:
   sweeps → parasite CD0 → `(L/D)max` → fit gates → Oswald chain → turbulator →
   V-speeds → cache → Re-table backfill.
5. **T-19** (stability) depends on T-01 and T-17; **T-20** is a deletion and
   should land with T-19 so `cd0` never has two writers.
6. **T-21, T-22, T-23** (resolution, validation, trim) before **T-25** (retrim),
   which calls them.
7. **T-24** (invalidation) before **T-25**; the retrim has nothing to do until
   rows are marked DIRTY.
8. **T-26** (enrichment) last among the services — it consumes trim output from
   all three paths and carries the #955 deviation.
9. **T-27 → T-29** (transport) after the services are green.

Blocking edges: T-09 ⇠ T-05 · T-12 ⇠ T-11 · T-13 ⇠ T-10 · T-16 ⇠ T-13, T-18 ·
T-17 ⇠ T-10…T-16 · T-25 ⇠ T-23, T-24 · T-26 ⇠ T-23 · T-29 ⇠ everything.

## Pending Gaps

- **#955 control-surface naming divergence.** T-25 and T-26 must key on the
  gh-772 mixing name. Until it is fixed, deflection reserves on every dual-role
  aircraft are computed against a hard-coded ±25° and a phantom 0° surface is
  reported. Decide whether the fix also renames `trim_elevator_deg` extraction in
  `stability_service`.
- **`_auto_populate_cd0` (T-20).** Confirmed BR-14 violation. Removing it is the
  documented intent, but nothing records *why* it was added — check whether a
  consumer depends on `cd0` being populated by a stability run alone.
- **Missing-`mass` default of 1.0 kg (T-08).** Should this be a design warning
  (ADR 0012) or a hard 422? The current behaviour returns a physically
  meaningless polar with no user-visible signal.
- **`min_static_margin` / `max_static_margin` (T-19).** Never seeded; the
  5 % / 25 % CG-range bounds are therefore not configurable. Seed them, or delete
  the lookup and promote the numbers to named constants.
- **Duplicate listener registration (T-24).** Two modules attach the same three
  models. Which one should own the registration?
- **German `hint` strings** on `PolarRejection` in an English-only UI.
- **`DIRTY` is absorbing with no pitch control (T-25).** Should the OP move to a
  distinct terminal state (e.g. `NO_CONTROL`) so the UI can explain it, instead
  of looking perpetually stale?
- **Warnings are never cleared** by a successful retrim, so stale
  `STALE_NO_POLAR` markers persist on rows whose polar now exists.
