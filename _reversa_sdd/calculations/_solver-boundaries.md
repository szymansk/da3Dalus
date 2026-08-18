# Solver boundaries — what this application hands to AVL and AeroSandbox

> **The solver's arithmetic is not under test. Everything handed to it is.**

A value that comes out of AeroBuildup, VLM, LiftingLine, NeuralFoil or AVL has no formula
in this repository and nothing to source — the solver is trusted. That trust moves the whole
testable surface to the interface. Every defect this application can commit here is an
**input** defect: the wrong object, an unconverted unit, an operating point that does not
match the geometry, or a value never passed at all so the solver's own default silently
applies.

The precedent is in this codebase's own history: a reference area taken from `surfaces[0]`
instead of the main wing made a tail-first import's coefficients wrong by a factor of eight.
The solver was blameless.

## The boundary in numbers

| solver | call sites | inputs | app-derived | hardcoded | never passed | risks flagged |
|---|---|---|---|---|---|---|
| **AeroSandbox AeroBuildup 4.2.9** | 18 | 137 | 45 | 21 | 30 | 49 |
| **aerosandbox.VortexLatticeMethod** | 4 | 63 | 22 | 9 | 21 | 24 |
| **aerosandbox.LiftingLine** | 7 | 59 | 15 | 11 | 19 | 24 |
| **NeuralFoil** | 6 | 61 | 14 | 9 | 21 | 17 |
| **AVL** | 9 | 97 | 46 | 11 | 13 | 39 |
| **total** | **44** | **417** | **142** | 61 | **104** | 153 |

**The two columns that matter.** `app-derived` is where this application does arithmetic
before handing over — the only place it can be wrong. `never passed` is the quieter one:
**104 inputs the solver defaults on**, each an assumption nobody recorded as a decision.

🟡 The `risks flagged` column is *reported by the mapping pass, not independently verified*.
A work list, not a defect count.

---

## AeroSandbox AeroBuildup 4.2.9 — `asb.AeroBuildup(airplane, op_point, xyz_ref=None, model_size='small', include_wave_drag=True).run()` / `.run_with_stability_derivatives(alpha=True, beta=True, p=True, q=True, r=True)`

```text
SHAPE OF THE BOUNDARY. Two entry styles: (a) the funnel `analyse_aerodynamics` → `app/api/utils.py:63`, used by analysis_service, stability_service, assumption_compute_service._stability_run_at_cruise and copilot_tools._run_polar_async; (b) direct `asb.AeroBuildup(...)` in assumption_compute_service (3 sites), operating_point_generator_service (3), aerobuildup_trim_service (1), elevator_authority_service (4), section_aoa_service (1), plus legacy cad_designer (2).

WHAT IS NEVER PASSED ANYWHERE IN app/. `model_size` (solver default 'small') and `include_wave_drag` (True). Neither appears at any app/ call site — only cad_designer sets 'xsmall'. `run_with_stability_derivatives()` is always called bare, so all five derivative axes are always computed.

REFERENCE-AREA STORY (the gh-788 class). Fixed centrally at `model_schema_converters.py:814-819` (`_find_reference_wing` = largest area). Three places still re-derive or bypass it: (1) `assumption_compute_service.py:80-84` re-asserts the same values independently — harmless duplication but a second producer; (2) `analysis_service.py:319-321` (analyze_wing) prunes `asb_airplane.wings` to one wing and does NOT recompute s_ref/c_ref/b_ref, so a single-surface analysis is normalised by the whole-aircraft main wing; (3) `section_aoa_service.py:490-499` computes its own area from *the first symmetric wing*, with a 0.3 m² fallback — an unpatched instance of exactly the original defect.

MOMENT REFERENCE. Only the OP generator (`operating_point_generator_service.py:1116`) sets xyz_ref to the design CG. Every other path uses `aeroplanes.xyz_ref` (DB column default `[0,0,0]`, `app/models/aeroplanemodel.py:671`) or a schema default `[0,0,0]`. So the assumption sweeps, the elevator-authority runs and both copilot tools take moments about the origin while the app separately publishes a `cg_x`. `stability_service.py:323` then reads `xcg = operating_point.xyz_ref[0]` — 0.0 — into the static margin; copilot patches around it at `copilot_tools.py:445-447` but still reports `cg_x = 0.0`.

READBACK, index-0 class. `analysis_model.py:595` takes Oswald efficiency as `wing_aero_components[0].oswalds_efficiency`, and line 629 takes the flight condition from the same index. That `e` feeds `_parasite_cd0` (`assumption_compute_service.py:1104`), i.e. the published CD0 depends on wing ordering. Line 633 hardcodes Mach = V/347 instead of using the atmosphere handed to the solver.

ATMOSPHERE. Three of the five assumption-service sweeps con
```

### `app/api/utils.py:63` — `_run_aerobuildup`

The single shared funnel: every AeroBuildup call routed through analyse_aerodynamics(AEROBUILDUP, …) lands here (analysis_service.analyze_wing/analyze_airplane/analyze_alpha_sweep/analyze_simple_sweep, stability_service.get_stability_summary, assumption_compute_service._stability_run_at_cruise, copilot_tools._run_polar_async).

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airplane` | passed-through | asb_airplane param; built by aeroplane_schema_to_asb_airplane_async (model_schema_converters.py:781) and mutat | m (ASB SI) |  |
| `airplane.s_ref / b_ref / c_ref` | app-derived | model_schema_converters.py:814-819 — ref_wing = _find_reference_wing(asb_wings) = max(wings, key=area); s_ref= | m², m, m | ⚠️ This is the gh-788 fix site. Bypassed in analysis_service.analyze_wing:319-321, which filters asb_airplane.wings to ONE wing but never recomputes s_ref/c_ref/b_ref — a single-tail analysis is therefore normalised by the  |
| `airplane.xyz_ref` | passed-through | utils.py:111 `asb_airplane.xyz_ref = operating_point.xyz_ref` | m | ⚠️ OperatingPointSchema.xyz_ref defaults to [0,0,0] (aeroanalysisschema.py:243-246) and AeroplaneSchema.xyz_ref defaults to [0,0,0] (aeroplaneschema.py:93). Nothing in the assumption/copilot paths substitutes the design CG  |
| `xyz_ref` | passed-through | operating_point.xyz_ref (utils.py:63) — passed a second time, redundantly with utils.py:111 | m |  |
| `op_point.velocity` | passed-through | _as_array_if_needed(operating_point.velocity), utils.py:28; schema default 10.0 | m/s |  |
| `op_point.alpha` | passed-through | _as_array_if_needed(operating_point.alpha), utils.py:29; scalar or array (sweeps) | deg |  |
| `op_point.beta` | passed-through | utils.py:30; schema default 0.0 | deg |  |
| `op_point.p / q / r` | passed-through | utils.py:31-33; schema defaults 0.0 | rad/s |  |
| `op_point.atmosphere` | app-derived | asb.Atmosphere(altitude=operating_point.altitude), utils.py:26; altitude schema default 0.0 | m | ⚠️ Atmosphere.method left at solver default 'differentiable' (not 'isa') at every call site in the repo. |
| `control deflections` | passed-through | utils.py:113-114 `overrides = operating_point.control_deflections; asb_airplane.with_control_deflections(overr | deg |  |
| `model_size` | solver-default | not passed → 'small' | — | ⚠️ No app/ call site ever sets model_size. The only place in the repo that does is legacy cad_designer/…/AirplaneConfiguration.py:193 ('xsmall'), so app and legacy run at different fidelities. |
| `include_wave_drag` | solver-default | not passed → True | — | ⚠️ Harmless at RC/UAV Mach but never declared. |
| `stability-derivative axes` | solver-default | run_with_stability_derivatives() called with no args → alpha/beta/p/q/r all True | — |  |

**Read back.** `CL` · `CD` · `CY` · `CX` · `CZ` · `Cl` · `Cm` · `Cn` · `F_b/F_g/F_w` · `M_b/M_g/M_w` · `L/D/Y` · `x_np` · `x_np_lateral` · `CLa/CLb/CLp/CLq/CLr` · `CYa..CYr` · `Cla..Clr` · `Cma..Cmr` · `Cna..Cnr` · `wing_aero_components[0].oswalds_efficiency` · `wing_aero_components[0].op_point`

**Consumed by.** `cad_designer/airplane/aircraft_topology/models/analysis_model.py:480 (from_abu_dict → AnalysisModel)` · `app/services/stability_service.py:322-327` · `app/services/assumption_compute_service.py:1079-1082` · `app/services/analysis_service.py:77 (_extract_alpha_sweep_arrays)` · `app/services/copilot_tools.py:363`

### `cad_designer/airplane/aircraft_topology/models/analysis_model.py:595` — `AnalysisModel.from_abu_dict (readback, not a call)`

Readback layer that turns the AeroBuildup dict into the app's AnalysisModel; two of its derivations are of the surfaces[0] class.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `coefficients.e` | app-derived | `[data.get('wing_aero_components')[0].oswalds_efficiency]` — index 0, the FIRST wing in airplane.wings order | — | ⚠️ Same wrong-object class as gh-788: for a tail-first wing ordering this is the TAIL's Oswald efficiency. It is consumed by assumption_compute_service.py:1082 → _parasite_cd0 (line 1104), so the published cd0 depends on wh |
| `flight_condition.mach` | app-derived | `op_point.velocity/347.` (analysis_model.py:633) | — | ⚠️ Hardcoded speed of sound 347 m/s instead of op_point.atmosphere.speed_of_sound(); ignores the altitude actually handed to the solver. |
| `flight_condition.alpha/beta/p/q/r` | app-derived | read back off `wing_aero_components[0].op_point` (analysis_model.py:629), falling back to the caller's operati | deg / rad/s | ⚠️ Also index 0. |
| `reference.Sref/Bref/Cref/Xref` | passed-through | asb_airplan.s_ref / b_ref / c_ref / xyz_ref[0..2] | m², m, m, m |  |

**Read back.** `AnalysisModel.reference.Xnp` · `AnalysisModel.coefficients.{CL,CD,e,…}` · `AnalysisModel.derivatives.{Cma,Cnb,Clb,…}`

**Consumed by.** `app/services/stability_service.py:322-327` · `app/services/assumption_compute_service.py:1079-1082`

### `app/services/assumption_compute_service.py:1077` — `_stability_run_at_cruise`

Phase-1 cruise stability run → the authoritative x_np, MAC, parasite CD0, S_ref for the whole app (gh-924).

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airplane` | app-derived | _build_asb_airplane(aircraft) (line 812) then s_ref/c_ref/b_ref OVERRIDDEN at recompute_assumptions lines 80-8 | m²/m/m | ⚠️ Redundant with the converter's own _find_reference_wing — two independent producers of the same three reference numbers (ADR 0022 smell), but they agree by construction. |
| `op_schema.velocity` | user-input | v_cruise from _load_flight_profile_speeds (line 1023) → profile goals['cruise_speed_mps'], default 18.0 | m/s |  |
| `op_schema.alpha` | hardcoded | alpha=0.0 at line 1077 | deg | ⚠️ Docstring at line 1059 concedes α=0 already carries lift on a cambered wing; the induced part is subtracted afterwards by _parasite_cd0. |
| `op_schema.xyz_ref` | passed-through | `list(asb_airplane.xyz_ref) if not None else [0,0,0]` (line 1075) — i.e. aeroplanes.xyz_ref, DB default [0,0,0 | m | ⚠️ Not the design CG. recompute_assumptions itself computes cg_x = x_np − SM·mac at line 121, so the moment reference used for the run and the CG it publishes are different points. |
| `altitude` | solver-default | OperatingPointSchema.altitude not passed → 0.0 → asb.Atmosphere(0) | m |  |
| `beta / p / q / r` | solver-default | not passed → schema defaults 0.0 | deg, rad/s |  |
| `control deflections` | solver-default | operating_point.control_deflections is None → geometry defaults apply | deg |  |

**Read back.** `result.reference.Xnp` · `result.coefficients.CD` · `result.coefficients.CL` · `result.coefficients.e`

**Consumed by.** `app/services/assumption_compute_service.py:1079-1082` · `app/services/assumption_compute_service.py:1104 (_parasite_cd0)` · `app/services/assumption_compute_service.py:121 (cg_x = x_np − target_sm·mac)` · `app/services/assumption_compute_service.py:192-206 (writes cd0/cg_x to design_assumptions)`

### `app/services/assumption_compute_service.py:1136` — `_coarse_alpha_sweep`

Vectorised α sweep at cruise speed to locate the α of peak CL (stall_alpha seed for the fine sweep).

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airplane` | passed-through | asb_airplane (main-wing refs already overridden), or the `deflected` deepcopy from _run_polar_for_deflection l | — |  |
| `op.alpha` | app-derived | np.arange(config.coarse_alpha_min_deg, config.coarse_alpha_max_deg + 0.01, config.coarse_alpha_step_deg) — def | deg |  |
| `op.velocity` | user-input | np.full_like(alphas, v_cruise) — flight-profile cruise speed | m/s |  |
| `xyz_ref` | passed-through | list(asb_airplane.xyz_ref) or [0,0,0] (line 1129) | m | ⚠️ Again aeroplanes.xyz_ref, not cg_x. |
| `op.beta / p / q / r` | solver-default | not passed to asb.OperatingPoint → 0.0 | deg, rad/s |  |
| `op.atmosphere` | solver-default | not passed → Atmosphere(altitude=0) | m | ⚠️ The flight profile's environment.altitude_m (used by the OPG, opg line 396) is silently ignored here; every assumption sweep is sea-level. |
| `model_size / include_wave_drag` | solver-default | not passed → 'small' / True | — |  |

**Read back.** `CL (array)`

**Consumed by.** `app/services/assumption_compute_service.py:1137-1138 (argmax → stall_alpha)` · `app/services/assumption_compute_service.py:96`

### `app/services/assumption_compute_service.py:1193` — `_fine_sweep_cl_max`

Vectorised V×α grid sweep → CL_max, and the cl/cd/cdi arrays that feed the parabolic polar fit, the Oswald extraction and the Re table.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airplane` | passed-through | asb_airplane, or the flap-deflected deepcopy (line 849) | — |  |
| `op.alpha` | app-derived | np.arange(stall_alpha − alpha_margin, stall_alpha + alpha_margin + 0.01, alpha_step); margin/step from config  | deg |  |
| `op.velocity` | app-derived | np.linspace(max(v_cruise*0.5, 3.0), v_max, config.fine_velocity_count) — v_max from goals['max_level_speed_mps | m/s | ⚠️ The lower anchor `max(v_cruise*0.5, 3.0)` is a heuristic stall-speed proxy, not a computed V_s. |
| `grid ravel order` | app-derived | np.meshgrid(alphas, velocities, indexing='xy') then .ravel() — V-outer/α-inner (line 1186-1191) | — | ⚠️ Downstream consumers (polar_re_table_service) index against this exact order; it is a positional contract with no assertion. |
| `xyz_ref` | passed-through | list(asb_airplane.xyz_ref) or [0,0,0] (line 1180) | m |  |
| `s_ref (post-processing, not a solver input)` | app-derived | float(asb_airplane.s_ref) (line 1181), used at line 1204 as CDi = D_induced/(q·s_ref) | m² |  |
| `q for CDi` | hardcoded | `q = 0.5 * 1.225 * v_flat**2` (line 1200) | Pa | ⚠️ ρ=1.225 is hardcoded rather than read from the op's atmosphere. Consistent only because the atmosphere was left at the sea-level default; if an altitude is ever passed the CDi (and therefore e_oswald) silently goes wrong |
| `beta / p / q / r / atmosphere` | solver-default | not passed | — |  |
| `model_size / include_wave_drag` | solver-default | not passed | — |  |

**Read back.** `CL array` · `CD array` · `D_induced array`

**Consumed by.** `app/services/assumption_compute_service.py:1196-1210` · `app/services/assumption_compute_service.py:96-97` · `app/services/assumption_compute_service.py:201-235 (_fit_parabolic_polar_with_refinement)` · `app/services/assumption_compute_service.py:239-249 (_ld_max_from_sweep / _e_oswald_from_sweep)` · `app/services/polar_re_table_service.py (build_re_table, called at assumption_compute_service.py:412)`

### `app/services/assumption_compute_service.py:1248` — `_extract_cl_alpha_from_linear_sweep`

Linear-range α sweep at cruise → CL_α and α₀ (gust-load inputs, gh-487/gh-871).

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airplane` | passed-through | asb_airplane | — |  |
| `op.alpha` | hardcoded | np.arange(alpha_min_deg=-2.0, alpha_max_deg=6.0 + 0.01, alpha_step_deg=1.0) — defaults in the signature (lines | deg | ⚠️ A second, independent α-resolution policy alongside AircraftComputationConfigModel; the config's step is not consulted here. |
| `op.velocity` | user-input | np.full_like(alphas_deg, v_cruise) | m/s |  |
| `xyz_ref` | passed-through | list(asb_airplane.xyz_ref) or [0,0,0] (line 1236) | m |  |
| `beta / p / q / r / atmosphere / model_size / include_wave_drag` | solver-default | not passed | — |  |

**Read back.** `CL array`

**Consumed by.** `app/services/assumption_compute_service.py:1249-1300 (OLS fit + R² gate → cl_alpha_per_rad, alpha_0_deg)`

### `app/services/assumption_compute_service.py:849` — `_run_polar_for_deflection`

Per-high-lift-configuration polar (takeoff / landing): deflect the flap, then re-run the coarse + fine sweeps against the deflected copy.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airplane (deflected)` | app-derived | asb_airplane.with_control_deflections({flap_name: flap_deflection_deg}) — deepcopy, so s_ref/c_ref/b_ref overr | — |  |
| `flap_name` | app-derived | _detect_first_flap_name(asb_airplane) (line 903) — FIRST control surface whose role tag is '[flap]', walking w | — | ⚠️ Wrong-object class: on a multi-flap aircraft only the first flap surface is deflected; the rest stay at their geometry default. Also duplicates operating_point_generator_service._pick_control_name (acknowledged in the do |
| `flap_deflection_deg` | app-derived | takeoff: min(15.0, ted_max); landing: float(ted_max), where ted_max = _extract_flap_ted_max(aircraft) (lines 3 | deg |  |
| `v_cruise / v_max / config` | passed-through | forwarded unchanged into _coarse_alpha_sweep / _fine_sweep_cl_max | m/s |  |
| `cd0_stability (fit gate, not a solver input)` | app-derived | raw_cd0 — the pre-turbulator parasite cd0 from _stability_run_at_cruise (line 128) | — |  |

**Read back.** `CL_max per config` · `CL/CD/CDi arrays per config`

**Consumed by.** `app/services/assumption_compute_service.py:356-390 (polar_takeoff / polar_landing)` · `app/services/assumption_compute_service.py:394-398 (polar_by_config persisted)` · `app/services/field_length_service.py:365`

### `app/services/aerobuildup_trim_service.py:58` — `_run_single_aerobuildup (residual, called by brentq)`

One evaluation inside the Brent root-find that drives a target coefficient (default Cm=0) to zero by varying one control deflection.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airplane` | app-derived | `asb_airplane.with_control_deflections({trim_variable: deflection_deg})` (line 57), where asb_airplane = aerop | — | ⚠️ The operating point's OTHER control deflections are validated at line 94 (validate_deflections_against_airplane) but NEVER applied to the airplane. `op.control_deflections` is read for validation only; the deepcopy carri |
| `airplane.s_ref / c_ref / b_ref` | passed-through | whatever the converter set (largest-area wing); not re-derived here | m², m, m |  |
| `airplane.xyz_ref` | passed-through | line 80 `asb_airplane.xyz_ref = op.xyz_ref` — the stored OperatingPointModel.xyz_ref, which the OPG wrote as [ | m |  |
| `xyz_ref (kwarg)` | passed-through | op.xyz_ref, line 155 | m |  |
| `op_point.velocity/alpha/beta/p/q/r` | passed-through | lines 97-105, straight off request.operating_point (a persisted OP row via operating_point_model_to_schema in  | m/s, deg, deg, rad/s | ⚠️ alpha is fixed for the whole root-find — the trim varies the control surface only, never re-solving α, so the trimmed state does not hold lift. |
| `op_point.atmosphere` | app-derived | asb.Atmosphere(altitude=op.altitude), line 96 | m |  |
| `trim_variable` | app-derived | resolved_trim_var (lines 131-145): request.trim_variable, else display_to_tagged[…], else role_to_primary[…] — | — | ⚠️ For a dual-role surface only the PRIMARY axis is deflected; the secondary (roll/yaw) axis stays at 0 (see control_surface_mixing.py:128). |
| `deflection_deg` | app-derived | the brentq iterate over request.deflection_bounds (default [-25, 25], aeroanalysisschema.py:119) | deg | ⚠️ Bounds are a schema default, not the surface's actual deflection limits — build_deflection_limits_from_schema is loaded later (line 292) for enrichment only, never to bound the search. |
| `model_size / include_wave_drag` | solver-default | not passed | — |  |
| `convergence` | hardcoded | brentq(residual, lower, upper, xtol=1e-6, maxiter=50) at line 212 | deg |  |

**Read back.** `CL` · `CD` · `CY` · `Cm` · `Cl` · `Cn` · `CL_a` · `CL_b` · `CY_a` · `CY_b` · `Cm_a` · `Cn_b` · `Cl_b` · `Clb` · `Cnr` · `Clr` · `Cnb`

**Consumed by.** `app/services/aerobuildup_trim_service.py:159-162 (residual)` · `app/services/aerobuildup_trim_service.py:261-272 (aero / derivs filtered by _AERO_COEFF_KEYS / _STABILITY_DERIV_KEYS)` · `app/services/aerobuildup_trim_service.py:300-311 (compute_enrichment)` · `app/services/retrim_service.py:99-106 (writes op.status + op.control_deflections)` · `app/api/v2/endpoints/operating_points.py:216`

### `app/services/operating_point_generator_service.py:664` — `_solve_trim_candidate_with_opti`

Primary OP trim: AeroBuildup evaluated inside an asb.Opti problem, minimising 50·Cm² + 3·CY² (+ CL-target and turn terms) over α and the control deflections.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airplane` | app-derived | asb_airplane.with_control_deflections(control_values) (line 639/648) where control_values mixes Opti *variable | — |  |
| `airplane.s_ref/c_ref/b_ref` | passed-through | converter's largest-area wing; the OPG never re-derives them | m², m, m |  |
| `xyz_ref` | app-derived | airplane_for_eval.xyz_ref (line 667) ← _prepare_generation line 1116 `asb_airplane.xyz_ref = [design_cg_x, 0.0 | m | ⚠️ y and z of the CG are hardcoded 0 — a laterally/vertically offset CG is not representable. |
| `op.velocity` | user-input | float(velocity_mps) from target['velocity'] (built by _build_target_definitions from the flight-profile goals) | m/s |  |
| `op.alpha` | app-derived | opti.variable(init_guess=min(max(3.0, alpha_lower), alpha_upper), bounds from profile constraints) | deg |  |
| `op.beta` | user-input | float(beta_target_deg) from target['beta_target_deg'] | deg |  |
| `op.p / q / r` | app-derived | _op_turn_rates(target, velocity_mps) (line 141) → turn_kinematics(bank_deg, velocity), rounded to 1e-6; (0,0,0 | rad/s |  |
| `op.atmosphere` | app-derived | asb.Atmosphere(altitude=altitude_m), altitude_m = float(target['altitude']) ← profile['environment']['altitude | m |  |
| `control deflection bounds` | hardcoded | pitch ±25.0 (line 619), roll ±20.0 (line 624), yaw ±25.0 (line 630) | deg | ⚠️ Literal bounds, not the TED limits from build_deflection_limits_from_schema — which the same context already loads (line 1122) and uses for enrichment. |
| `flap deflection` | app-derived | target['flap_deflection_deg'] clipped by _clip_flap_to_ted_limit (line 1115) | deg |  |
| `cl_target (objective, not a solver input)` | app-derived | _cl_target_for_velocity (line 784): (mass·9.81·n_target)/(0.5·rho·V²·s_ref); rho = asb.Atmosphere(altitude).de | — | ⚠️ g=9.81 hardcoded; s_ref read defensively with a 0.0 fallback that silently returns cl_target=None (line 792), disabling the lift constraint without any warning (ADR 0020). |
| `model_size / include_wave_drag` | solver-default | not passed | — |  |
| `opti convergence` | hardcoded | opti.solve(verbose=False, max_iter=120, max_runtime=0.35, behavior_on_failure='return_last') at lines 682-687 | s | ⚠️ max_runtime=0.35 s with behavior_on_failure='return_last' means a timeout yields an UNCONVERGED point that is scored and can win, indistinguishable from a converged one except via trim_score. |

**Read back.** `Cm` · `CY` · `CL` · `Cl` · `Cn`

**Consumed by.** `app/services/operating_point_generator_service.py:670-681 (objective)` · `app/services/operating_point_generator_service.py:691-700 (solved alpha/controls/metrics)` · `app/services/operating_point_generator_service.py:908-922 (best_score / best_controls)`

### `app/services/operating_point_generator_service.py:731` — `_evaluate_trim_candidate (grid-search fallback)`

Scores one (α, β, V, controls) grid candidate when the Opti trim score exceeds 0.35.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airplane` | app-derived | asb_airplane.with_control_deflections(controls) if controls else asb_airplane (lines 728-730) | — |  |
| `xyz_ref` | passed-through | airplane_for_eval.xyz_ref = [design_cg_x, 0, 0] | m |  |
| `op.velocity / alpha / beta` | passed-through | the grid iterate (lines 718-720) | m/s, deg, deg |  |
| `op.p / q / r` | hardcoded | p=0.0, q=0.0, r=0.0 (lines 721-723) | rad/s | ⚠️ The Opti path passes the real turn rates from _op_turn_rates (line 653); this fallback zeroes them. A turn target that falls through to the grid search is therefore trimmed as if in straight flight, and the persisted OP  |
| `op.atmosphere` | app-derived | asb.Atmosphere(altitude=altitude_m) | m |  |
| `model_size / include_wave_drag` | solver-default | not passed | — |  |

**Read back.** `Cm` · `CL` · `CY`

**Consumed by.** `app/services/operating_point_generator_service.py:737-743` · `app/services/operating_point_generator_service.py:925-945 (_grid_search_trim result overrides alpha AND velocity)`

### `app/services/operating_point_generator_service.py:772` — `_aero_coefficients_at`

One extra eval at the final trimmed state to populate trim_enrichment.aero_coefficients (CL/CD/L-D) for the OP comparison table (gh-861).

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airplane` | app-derived | asb_airplane.with_control_deflections(controls) if controls else asb_airplane (line 771) | — |  |
| `xyz_ref` | passed-through | airplane.xyz_ref = [design_cg_x, 0, 0] | m |  |
| `op.velocity / alpha / beta` | app-derived | the winning best_alpha/best_beta and the possibly grid-overridden velocity (call at line 977) | m/s, deg |  |
| `op.p / q / r` | hardcoded | 0.0, 0.0, 0.0 (lines 765-767) | rad/s | ⚠️ Same divergence as above: the persisted OP records _op_turn_rates(target, velocity) at line 980, but the CL/CD/Cm shown next to it were computed at zero body rates. |
| `op.atmosphere` | app-derived | asb.Atmosphere(altitude=altitude_m) | m |  |
| `model_size / include_wave_drag` | solver-default | not passed | — |  |

**Read back.** `CL` · `CD` · `Cm`

**Consumed by.** `app/services/operating_point_generator_service.py:774-779 (finite-filtered, rounded to 6dp)` · `app/services/operating_point_generator_service.py:1001 (TrimmedPoint.aero_coefficients → trim_enrichment)`

### `app/services/copilot_tools.py:361` — `_run_polar_async`

AI copilot 'polar' tool: α sweep −10…+15° via analyse_aerodynamics(AEROBUILDUP).

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airplane` | passed-through | aeroplane_schema_to_asb_airplane_async(plane_schema) (line 346) — s_ref/c_ref/b_ref from the converter's large | — | ⚠️ Unlike recompute_assumptions (lines 80-84) this path does NOT re-assert the main-wing reference; it relies solely on the converter. |
| `op.alpha` | hardcoded | np.linspace(-10.0, 15.0, 26) via AlphaSweepRequest literals at lines 337-343 | deg |  |
| `op.velocity` | hardcoded | velocity=20.0 (line 339) | m/s | ⚠️ Fixed 20 m/s regardless of the aircraft's cruise speed — the sibling tool _run_stability_async (line 425) deliberately reads v_cruise from assumption_computation_context for exactly this reason (gh-924), so the two copil |
| `op.altitude` | hardcoded | altitude=0.0 (line 338) | m |  |
| `op.beta / p / q / r` | solver-default | sweep_request.beta/p/q/r not set → AlphaSweepRequest defaults 0.0 (AeroplaneRequest.py:72-75) | deg, rad/s |  |
| `xyz_ref` | solver-default | sweep_request.xyz_ref (line 356) → AlphaSweepRequest default [0.0, 0.0, 0.0] (AeroplaneRequest.py:76-78) | m | ⚠️ Moments are taken about the origin, not the design CG, even though cg_x exists in design_assumptions. Any Cm-derived number the copilot reports (the 'trim' characteristic point) is referenced to the nose. |
| `control deflections` | solver-default | OperatingPointSchema.control_deflections left None → geometry defaults | deg |  |
| `model_size / include_wave_drag` | solver-default | not passed | — |  |

**Read back.** `CL array` · `CD array` · `Cm array` · `alpha array`

**Consumed by.** `app/services/copilot_tools.py:363-368 (_extract_alpha_sweep_arrays, _compute_alpha_sweep_characteristic_points)` · `app/services/copilot_tools.py:372-380 (cl_max, cl_min, cd_min, cl_cd_max)` · `app/services/copilot_tools.py:382-384 (_polar_drag_breakdown, which re-reads ar/e from assumption_computation_context, not from this run)`

### `app/services/copilot_tools.py:431` — `_run_stability_async`

AI copilot 'stability' tool: routes to stability_service.get_stability_summary with AEROBUILDUP.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `op.velocity` | passed-through | float(v_cruise) from plane.assumption_computation_context['v_cruise_mps'], else 20.0 (lines 426-428) | m/s | ⚠️ Silent hardcoded 20.0 fallback when the context is missing — no DesignWarning (ADR 0020). |
| `op.alpha` | hardcoded | alpha=0.0 (line 428) — matched to _stability_run_at_cruise per gh-924 | deg |  |
| `op.altitude` | hardcoded | 0.0 (line 426) | m |  |
| `op.xyz_ref` | solver-default | not passed → OperatingPointSchema default [0,0,0] | m | ⚠️ stability_service.py:323 then reads `xcg = operating_point.xyz_ref[0]` = 0.0 and computes static_margin against it. copilot_tools.py:445-447 patches over this by recomputing SM from the cached context, but summary.cg_x i |
| `beta / p / q / r / control deflections` | solver-default | not passed → schema defaults | — |  |
| `airplane refs` | passed-through | stability_service.py:314 aeroplane_schema_to_asb_airplane_async — converter's largest-area wing | m², m, m | ⚠️ Comment at copilot_tools.py:439-443 states the two stability paths normalise x_np against different reference chords. |

**Read back.** `result.reference.Xnp` · `result.reference.Cref` · `result.derivatives.Cma / Cnb / Clb` · `result.coefficients.CD` · `result.flight_condition.alpha`

**Consumed by.** `app/services/stability_service.py:322-327` · `app/services/stability_service.py:359 (_auto_populate_cd0 writes design_assumptions.cd0 with calculated_source='stability_analysis')` · `app/services/copilot_tools.py:444-460`

### `app/services/elevator_authority_service.py:639` — `_compute_forward_cg_limit_asb — baseline-clean run`

Cm reference at clean stall alpha, used as the ΔCm_flap baseline.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airplane` | app-derived | asb_airplane.with_control_deflections({elevator_surface_name: 0.0}) (line 638) | — |  |
| `elevator_surface_name` | app-derived | f"[{elevator_role}]{getattr(elevator_ted,'name',elevator_role)}" (line 605) — the tag is reconstructed by stri | — | ⚠️ Silent-miss: asb.Airplane.with_control_deflections drops unmatched keys without error, so a name mismatch produces a zero-deflection run indistinguishable from a real one. This is the exact hazard gh-624 guards against i |
| `op_stall.velocity` | app-derived | v_cruise * 0.6 (line 620); v_cruise = assumption 'v_cruise' else 15.0 (line 589) | m/s | ⚠️ 0.6 is an undocumented literal approach-speed factor; the 15.0 cruise fallback is silent. |
| `op_stall.alpha` | user-input | _load_assumption_value(db, id, 'stall_alpha') else 12.0 (line 618) | deg |  |
| `xyz_ref` | passed-through | list(asb_airplane.xyz_ref) or [0,0,0] (line 594) | m | ⚠️ The comment at line 729-730 claims 'xyz_ref which we set to x_np for the stability run' — the code never does that. cm_ac is taken about aeroplanes.xyz_ref (DB default [0,0,0]), while x_np_m is loaded separately from des |
| `beta / p / q / r / atmosphere` | solver-default | asb.OperatingPoint(velocity=…, alpha=…) only (lines 619-622) | — |  |
| `model_size / include_wave_drag` | solver-default | not passed | — |  |

**Read back.** `Cm`

**Consumed by.** `app/services/elevator_authority_service.py:644 (_extract_cm → cm_baseline_clean)` · `app/services/elevator_authority_service.py:653 (cm_baseline for _run_flap_analysis)`

### `app/services/elevator_authority_service.py:686` — `_compute_forward_cg_limit_asb — baseline + TE-UP pair`

Finite-difference Cm_δe: two runs at the landing-stall alpha, one at δe=0 and one at the max TE-UP deflection.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airplane (baseline)` | app-derived | asb_airplane.with_control_deflections({elevator_surface_name: 0.0}) (line 685) | — |  |
| `airplane (deflected)` | app-derived | asb_airplane.with_control_deflections({elevator_surface_name: delta_e_neg_deg}) (line 696) | — |  |
| `delta_e_neg_deg` | app-derived | -abs(_delta_e_max_rad(negative_deflection_deg=elevator_ted.negative_deflection_deg) * 180/pi) (lines 608-611) | deg | ⚠️ rad→deg round-trip: the helper returns radians and the caller converts back. Sign convention (negative = TE-UP) is enforced by abs() then negation. |
| `op_stall_landing.velocity` | app-derived | v_cruise * 0.6 (line 681) | m/s |  |
| `op_stall_landing.alpha` | app-derived | alpha_stall_landing_deg — the α at CL_max from the flap sweep (_run_flap_analysis), else the clean stall_alpha | deg |  |
| `xyz_ref` | passed-through | list(asb_airplane.xyz_ref) or [0,0,0] | m | ⚠️ Same as above — not x_np, despite the comment. |
| `flap state` | solver-default | the flaps are NOT deflected on these two runs — only asb_airplane (clean) with the elevator override | deg | ⚠️ Cm_δe is measured clean while cl_max_landing and delta_cm_flap come from the flap-deployed sweep; the conditioning guard at line 745 mixes them. |
| `beta / p / q / r / atmosphere / model_size / include_wave_drag` | solver-default | not passed | — |  |

**Read back.** `Cm (baseline)` · `Cm (deflected)`

**Consumed by.** `app/services/elevator_authority_service.py:692,703 (_extract_cm)` · `app/services/elevator_authority_service.py:709 (cm_delta_e_raw = (cm_deflected − cm_baseline) / delta_e_max_rad)` · `app/services/elevator_authority_service.py:726 (_cm_delta_e_for_asb_path)` · `app/services/elevator_authority_service.py:731 (cm_ac = cm_baseline)` · `app/services/elevator_authority_service.py:745 (_apply_conditioning_guard)`

### `app/services/elevator_authority_service.py:882` — `_run_flap_analysis`

Flap-deployed α sweep to find CL_max_landing, the Cm at that point and α_stall_landing.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airplane` | app-derived | asb_airplane.with_control_deflections(flap_deflections) (line 872), flap_deflections built by string-formattin | — | ⚠️ Same unmatched-key silent-drop hazard as line 638. |
| `flap deflection` | app-derived | ted.positive_deflection_deg or 30.0 (line 869) | deg | ⚠️ `or 30.0` also swallows a legitimate 0.0 deflection. |
| `op.alpha` | hardcoded | loop over np.arange(-5.0, 20.0, 1.0) (line 875) | deg | ⚠️ 25 separate scalar AeroBuildup constructions in a Python loop — the only un-vectorised sweep left after gh-690 vectorised the assumption sweeps. |
| `op.velocity` | passed-through | op_stall.velocity (line 881) = v_cruise * 0.6 | m/s |  |
| `xyz_ref` | passed-through | xyz_ref param = list(asb_airplane.xyz_ref) or [0,0,0] | m |  |
| `beta / p / q / r / atmosphere / model_size / include_wave_drag` | solver-default | not passed | — |  |

**Read back.** `CL` · `Cm`

**Consumed by.** `app/services/elevator_authority_service.py:888-895 (argmax CL → cl_max_flap, cm_at_cl_max, alpha_at_cl_max)` · `app/services/elevator_authority_service.py:898 (delta_cm_flap = cm_at_cl_max − cm_baseline)` · `app/services/elevator_authority_service.py:663-666`

### `app/services/section_aoa_service.py:515` — `_resolve_level_flight_op._cl_at_alpha`

Brent root-find on α to hit a level-flight CL when no stored TRIMMED operating point exists.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airplane` | passed-through | asb_airplane param | — |  |
| `s_ref (CL-target computation, not a solver input)` | app-derived | lines 490-499: iterates asb_airplane.wings and takes `float(w.area())` of the FIRST wing with symmetric=True,  | m² | ⚠️ Textbook wrong-object: a symmetric horizontal tail listed before the main wing becomes the reference area. This is the same defect class as gh-788 and is NOT covered by the converter's _find_reference_wing, because this  |
| `mass_kg` | app-derived | getattr(plane_schema,'total_mass_kg',None) or 1.5 (line 487) | kg | ⚠️ Silent 1.5 kg default. |
| `cruise_v` | hardcoded | cruise_v = 15.0 (line 502) | m/s | ⚠️ Ignores the aircraft's own cruise speed, which assumption_computation_context already carries. |
| `cl_target` | app-derived | (2·mass·9.80665)/(1.225·s_ref·cruise_v²), clipped to [0.1, 2.0] (lines 504-505) | — | ⚠️ rho=1.225 and g=9.80665 hardcoded (note: g differs from the 9.81 used in operating_point_generator_service.py:795); the np.clip silently caps an out-of-range target. |
| `op.alpha` | app-derived | the brentq iterate over [-5.0, 15.0], xtol=0.05, maxiter=30 (line 528) | deg |  |
| `op.atmosphere` | hardcoded | asb.Atmosphere(altitude=0.0) (line 507) | m |  |
| `xyz_ref` | passed-through | getattr(asb_airplane,'xyz_ref',[0.0,0.0,0.0]) (line 518) | m |  |
| `beta / p / q / r / model_size / include_wave_drag` | solver-default | not passed | — |  |
| `failure handling` | hardcoded | except → `return -cl_target` (line 523); ValueError → alpha_trimmed = 4.0 (line 530) | deg | ⚠️ A solver exception is converted into a finite residual, so brentq can 'converge' on a failed evaluation; the 4.0° default is undeclared. |

**Read back.** `CL`

**Consumed by.** `app/services/section_aoa_service.py:521-522` · `app/services/section_aoa_service.py:534-545 (OperatingPointSchema 'level_flight_fallback')` · `app/services/section_aoa_service.py:445`

### `cad_designer/airplane/aircraft_topology/airplane/AirplaneConfiguration.py:193` — `AirplaneConfiguration.airplane_analysis`

Legacy frozen-layer analysis (α sweep then β sweep); the only place in the repo that sets model_size.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airplane` | passed-through | self.asb_airplane | — |  |
| `op.alpha` | hardcoded | np.linspace(-20, 20, 300) | deg |  |
| `op.velocity` | hardcoded | velocity=10 (comment: 'm/s is not important at this point') | m/s |  |
| `op.beta` | hardcoded | beta=0 (first run); np.linspace(-5, 5, 100) at line 210 | deg |  |
| `model_size` | hardcoded | model_size='xsmall' | — | ⚠️ Divergence: every app/ call site runs at the solver default 'small'. Numbers from this legacy path are not comparable to the app's. |
| `xyz_ref` | solver-default | not passed → airplane.xyz_ref | m |  |
| `p / q / r / atmosphere / include_wave_drag` | solver-default | not passed | — |  |

**Read back.** `CL array` · `CD array`

**Consumed by.** `cad_designer/airplane/aircraft_topology/airplane/AirplaneConfiguration.py:204-207 (calculate_cl_max, calculate_CL_per_CD_max)` · `cad_designer/airplane/aircraft_topology/airplane/AirplaneConfiguration.py:219+`

## aerosandbox.VortexLatticeMethod (asb 4.2.x, installed at .../site-packages/aerosandbox/aerodynamics/aero_3D/vortex_lattice_method.py; ctor signature read at lines 41-56)

```text
Cross-cutting observations (all file:line verified).

1. Control deflections are structurally inert at this boundary. asb's VLM meshes via Wing.mesh_thin_surface -> Wing.mesh_line (wing.py:1148-1170), which applies twist and camber but never a hinge deflection; vortex_lattice_method.py contains no reference to control surfaces. So app/api/utils.py:115's with_control_deflections buys nothing, and vlm_strip_forces' path never applies them at all. The gh-577 promise "trim-consistent Trefftz/streamline visualisations" (aeroanalysisschema.py:266-272) holds for alpha/velocity/xyz_ref but not for deflections.

2. Two silent, undeclared fallbacks (ADR 0020). (a) vlm_strip_forces.py:105-108 swallows any airfoil-blend failure and substitutes the inboard airfoil. (b) vlm_strip_forces.py:239-241: if the app's expected strip count disagrees with the solver's, the whole aircraft collapses into ONE aggregate surface named after the airplane — the response shape changes with no warning to the caller.

3. Placeholder values ride the AVL schema. vlm_strip_forces.py:292-298 hardcodes cdv=0.0, cm_c/4=0.0, cm_LE=0.0, C.P.x/c=0.25 into StripForceEntry — fields whose AVL-produced counterparts are real numbers. The response only distinguishes them via aero_model ("ASB" vs "AVL", analysis_service.py:1888).

4. Duplicate producers of the same quantity (ADR 0022 smell): dynamic pressure is computed inside the solve as op_point.dynamic_pressure() (vlm_strip_forces.py:214, used to form per-strip cl) and again by the caller as 0.5*rho*V**2 (analysis_service.py:2052-2053, used to re-dimensionalise those same cl values). Mach likewise: op_point.mach() (vlm_strip_forces.py:317) versus velocity/347. hardcoded in analysis_model.py:635.

5. Dead readback: compute_vlm_strip_forces returns CL and CD (lines 318-319) but no consumer reads them — StripForcesResponse has no such fields (schemas/strip_forces.py:41-47) and spanwise_loads.py does not touch them.

6. Path asymmetry: analyze_airplane_strip_forces resolves the stored OP (analysis_service.py:1857-1862) while analyze_wing_strip_forces does not (line 1930 onward uses the raw request) — operating_point_id is silently ignored for the wing-scoped endpoint.

7. Chord at vlm_strip_forces.py:262 is abs(x_te - x_le), the x-projection, not the true chord; with twist it is chord*cos(twist). It feeds Chord, c_cl and cl_norm in the response.

8. asb.LiftingLine (app/services/section_aoa_service.py:261) is a separate solver boundary, out of scope here
```

### `app/services/vlm_strip_forces.py:205` — `compute_vlm_strip_forces`

Primary production VLM solve: reconstructs AVL-equivalent per-strip spanwise force data for the Trefftz-Plane chart and the spanwise shear/bending-moment integrator (gh-674/gh-855).

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airplane` | app-derived | meshed = _remesh_airplane(asb_airplane, budget=spanwise_panels, min_per_segment=min_panels_per_segment)  (vlm_ | m | ⚠️ _remesh_airplane rebuilds every Wing as asb.Wing(name, xsecs, symmetric) only (line 137) — analysis_specific_options and any other Wing state are dropped. _blend_xsec wraps blend_with_another_airfoil in a bare `except Ex |
| `airplane.wings[].xsecs[].xyz_le / chord / twist` | app-derived | linear blend in _blend_xsec: xyz_le*a+xyz_le*b, chord*a+chord*b, twist*a+twist*b (vlm_strip_forces.py:110-112) | m / m / deg |  |
| `airplane.wings[].symmetric` | passed-through | wing.symmetric from the DB schema (model_schema_converters.py:800), copied at vlm_strip_forces.py:137 | - |  |
| `airplane.wings[].xsecs[].control_surfaces` | passed-through | asb.ControlSurface(name/symmetric/deflection/hinge_point, trailing_edge=True) from axes_for_xsec (model_schema | deg | ⚠️ Twice inert. (a) asb's VLM never reads control surfaces — the mesh path Wing.mesh_thin_surface -> Wing.mesh_line (wing.py:1148-1170) applies twist and camber only, no hinge deflection. (b) This call path never even appli |
| `airplane.fuselages` | passed-through | list(getattr(asb_airplane, 'fuselages', []) or [])  (vlm_strip_forces.py:157) |  | ⚠️ VLM iterates only self.airplane.wings (vortex_lattice_method.py:146) — fuselages contribute zero force/moment. The reference geometry and the result are fuselage-blind while the app treats the run as whole-aircraft. |
| `airplane.s_ref` | app-derived | float(ref_wing.area()) where ref_wing = max(wings, key=area) (model_schema_converters.py:760-778, 817); carrie | m^2 | ⚠️ This is the gh-788 fix for the surfaces[0] defect. Still fragile: analyze_wing_strip_forces mutates asb_airplane.wings AFTER construction (analysis_service.py:1935) — s_ref is not recomputed, it stays whatever the schema |
| `airplane.b_ref` | app-derived | float(ref_wing.span())  (model_schema_converters.py:818), preserved at vlm_strip_forces.py:160 | m |  |
| `airplane.c_ref` | app-derived | float(ref_wing.mean_aerodynamic_chord())  (model_schema_converters.py:819), preserved at vlm_strip_forces.py:1 | m | ⚠️ Also used app-side at vlm_strip_forces.py:277 for cl_norm = cl*chord/c_ref — one value serving both solver nondimensionalisation and a per-strip app output. |
| `airplane.xyz_ref` | app-derived | asb_airplane.xyz_ref = xyz_ref (vlm_strip_forces.py:198-199), xyz_ref := resolved_op.xyz_ref (analysis_service | m | ⚠️ In-place mutation of the caller's Airplane object; the caller already set it at analysis_service.py:1866/1934, so the same value is written twice via two paths. |
| `xyz_ref` | solver-default | not passed — VLM falls back to airplane.xyz_ref (vortex_lattice_method.py:62-63) | m | ⚠️ The moment reference reaches the solver only because of the line-199 mutation AND because _remesh_airplane copies xyz_ref (line 158). Either one regressing silently moves every moment to [0,0,0]. |
| `op_point` | app-derived | asb.OperatingPoint(...) built at analysis_service.py:1869-1877 (airplane scope) / 1939-1947 (wing scope) |  |  |
| `op_point.velocity` | passed-through | resolved_op.velocity (analysis_service.py:1870) / operating_point.velocity (1940) | m/s |  |
| `op_point.alpha` | app-derived | resolved_op.alpha; = math.degrees(op.alpha) when bound to a stored OP (operating_point_resolver.py:124), else  | deg | ⚠️ OperatingPointSchema types alpha as `float \| list[float]` (aeroanalysisschema.py:237). A list reaches asb.OperatingPoint unchecked, and the readback float(op_point.alpha) at vlm_strip_forces.py:315 then raises — an unval |
| `op_point.beta` | app-derived | resolved_op.beta; = math.degrees(op.beta) for stored OPs (operating_point_resolver.py:125) | deg |  |
| `op_point.p / q / r` | passed-through | resolved_op.p/.q/.r (analysis_service.py:1873-1875) | rad/s |  |
| `op_point.atmosphere` | app-derived | asb.Atmosphere(altitude=resolved_op.altitude) (analysis_service.py:1868 / 1938) | m |  |
| `spanwise_resolution` | hardcoded | 1  (vlm_strip_forces.py:208) | - |  |
| `spanwise_spacing_function` | hardcoded | np.linspace  (vlm_strip_forces.py:210) |  | ⚠️ Inert: subdivide_sections is only invoked when spanwise_resolution > 1 (vortex_lattice_method.py:147-151). With 1 hardcoded, this argument can never take effect. |
| `chordwise_resolution` | app-derived | chordwise_resolution parameter, default 8 (vlm_strip_forces.py:172); no caller in app/ ever overrides it | panels | ⚠️ The other production VLM (app/api/utils.py:79) leaves this at the solver default 10 — the same aircraft is chordwise-discretised two different ways depending on which endpoint is hit. |
| `chordwise_spacing_function` | solver-default | not passed — np.cosspace (vortex_lattice_method.py:53-55) |  |  |
| `vortex_core_radius` | solver-default | not passed — 1e-8 (vortex_lattice_method.py:56) | m |  |
| `align_trailing_vortices_with_wind` | solver-default | not passed — False; trailing vortices fixed along np.array([1,0,0]) (vortex_lattice_method.py:248-252) |  | ⚠️ The app has alpha available and does not use it; wake is body-x aligned. AVL (the alternate solver behind the same StripForcesResponse) does not make the same choice. |
| `run_symmetric_if_possible` | solver-default | not passed — False (vortex_lattice_method.py:46); True raises NotImplementedError (line 80) |  |  |
| `verbose` | solver-default | not passed — False (vortex_lattice_method.py:47) |  |  |

**Read back.** `run()["CL"] (line 318)` · `run()["CD"] (line 319)` · `vlm.forces_geometry (line 219)` · `vlm.areas (220)` · `vlm.front_left_vertices / front_right_vertices (221-222)` · `vlm.back_left_vertices / back_right_vertices (223-224)` · `vlm.steady_freestream_direction (227)` · `vlm.is_trailing_edge (232)` · `op_point.dynamic_pressure() (214)` · `op_point.mach() (317)`

**Consumed by.** `app/services/analysis_service.py:1890 (_strip_surfaces_from_result)` · `app/services/analysis_service.py:1974` · `app/services/analysis_service.py:1891-1897 (_build_strip_forces_response)` · `app/services/analysis_service.py:1746-1768 (reads Cref/Sref/Bref/alpha/beta/mach)` · `app/services/analysis_service.py:2056-2063 (result_with_meta -> compute_spanwise_loads)` · `app/services/spanwise_loads.py:108-118 (strip_forces key)` · `app/services/spanwise_loads.py:58-59 (per-strip Area, cl, Yle)` · `app/services/spanwise_loads.py:136-138 (Yle sign split)` · `app/schemas/strip_forces.py:11-38 (StripForceEntry / SurfaceStripForces validation)`

### `app/api/utils.py:79` — `_run_vlm`

Whole-aircraft VLM with stability derivatives — backs the streamline figure, the four-view PNG, the generic /wings/{name}/{tool} and /aeroplanes/{id}/{tool} analysis endpoints, and the stability summary when the user selects the vortex_lattice tool.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airplane` | app-derived | meshed = _remesh_airplane(asb_airplane)  (app/api/utils.py:78), with module defaults budget=_SPANWISE_PANELS_P |  | ⚠️ Same remesh caveats as call site 1 (silent airfoil-blend fallback, Wing state dropped). |
| `airplane (control deflections)` | user-input | asb_airplane = asb_airplane.with_control_deflections(overrides) where overrides = operating_point.control_defl | deg | ⚠️ Inert for this solver: asb's VLM mesh path (wing.py:1148-1170) ignores ControlSurface.deflection entirely. Streamlines and stability derivatives labelled 'vortex_lattice' are identical for any deflection set — including  |
| `airplane.s_ref / b_ref / c_ref` | app-derived | largest-planform wing (model_schema_converters.py:814-819), preserved through _remesh_airplane (vlm_strip_forc | m^2 / m / m |  |
| `airplane.fuselages` | passed-through | _build_asb_fuselages(plane_schema.fuselages) (model_schema_converters.py:803), copied at vlm_strip_forces.py:1 |  | ⚠️ Ignored by the solver (vortex_lattice_method.py:146) but still drawn by vlm.draw(), so the streamline picture shows a body that contributed nothing to the solution. |
| `airplane.xyz_ref` | passed-through | asb_airplane.xyz_ref = operating_point.xyz_ref (app/api/utils.py:111) | m |  |
| `xyz_ref` | passed-through | operating_point.xyz_ref  (app/api/utils.py:82) | m |  |
| `op_point.velocity` | app-derived | _as_array_if_needed(operating_point.velocity) — float passes through, anything else becomes np.array (app/api/ | m/s |  |
| `op_point.alpha` | app-derived | _as_array_if_needed(operating_point.alpha) (app/api/utils.py:29); degrees, rad->deg converted upstream for sto | deg |  |
| `op_point.beta / p / q / r` | app-derived | _as_array_if_needed(operating_point.beta/.p/.q/.r) (app/api/utils.py:30-33) | deg / rad/s |  |
| `op_point.atmosphere` | app-derived | asb.Atmosphere(altitude=operating_point.altitude) (app/api/utils.py:26) | m |  |
| `spanwise_resolution` | hardcoded | 1  (app/api/utils.py:83) |  |  |
| `spanwise_spacing_function` | hardcoded | np.linspace  (app/api/utils.py:84) |  | ⚠️ Inert — spanwise_resolution is 1, so subdivide_sections is never called (vortex_lattice_method.py:147). |
| `chordwise_resolution` | solver-default | not passed — 10 (vortex_lattice_method.py:51) | panels | ⚠️ The app has an explicit chordwise budget for the sibling path (8, vlm_strip_forces.py:172) and does not apply it here; the invisible default silently governs every streamline/stability VLM run. |
| `chordwise_spacing_function` | solver-default | not passed — np.cosspace (vortex_lattice_method.py:53-55) |  |  |
| `vortex_core_radius` | solver-default | not passed — 1e-8 (vortex_lattice_method.py:56) | m |  |
| `align_trailing_vortices_with_wind` | solver-default | not passed — False (vortex_lattice_method.py:57) |  |  |
| `run_symmetric_if_possible` | solver-default | not passed — False (vortex_lattice_method.py:46) |  |  |
| `verbose` | hardcoded | vlm.verbose = True set after construction (app/api/utils.py:86) |  | ⚠️ Forces meshing/solve progress prints to stdout inside a FastAPI request. |
| `run_with_stability_derivatives(alpha,beta,p,q,r)` | solver-default | vlm.run_with_stability_derivatives() with no arguments (app/api/utils.py:87) — all five default True (vortex_l |  | ⚠️ Every derivative is computed even when the caller only wants a streamline figure (analysis_service.py:411, 1663 discard the result and keep only the figure) — ~10 extra VLM solves per request. |

**Read back.** `run_with_stability_derivatives() dict: F_g, F_b, F_w, M_g, M_b, M_w, L, Y, D, l_b, m_b, n_b, CL, CY, CD, Cl, Cm, Cn, x_np, x_np_lateral and the CLa/CYb/Clp/Cmq/Cnr... derivative family` · `vlm.draw(show=False, backend=...) figure (app/api/utils.py:88)`

**Consumed by.** `cad_designer/airplane/aircraft_topology/models/analysis_model.py:480-655 (from_abu_dict, called at app/api/utils.py:89-94)` · `cad_designer/.../analysis_model.py:495-507 (reference: Bref/Cref/Sref/Xref from asb_airplane, Xnp from data['x_np'])` · `cad_designer/.../analysis_model.py:580-596 (coefficients)` · `cad_designer/.../analysis_model.py:598-626 (derivatives)` · `cad_designer/.../analysis_model.py:630-645 (flight condition, mach = op_point.velocity/347.)` · `app/services/analysis_service.py:322-325 (analyze_wing)` · `app/services/analysis_service.py:365-368 (analyze_airplane)` · `app/services/analysis_service.py:411-416 (calculate_streamlines_json — figure only)` · `app/services/analysis_service.py:1663-1670 (get_streamlines_three_view_image — figure only)` · `app/services/stability_service.py:315-330 (Xnp, Cma, Cnb, Clb, Cref -> static margin)`

### `scripts/vspaero_benchmark/pipeline_asb.py:272` — `_rows_vlm_per_alpha`

Offline cross-validation harness: per-alpha ASB VLM polar written to CSV and compared against VSPAERO and the app's AeroBuildup arm.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airplane` | passed-through | asb_airplane, taken as built by aeroplane_schema_to_asb_airplane_async — NOT remeshed |  | ⚠️ Diverges from both production call sites, which run _remesh_airplane first. The benchmark therefore does not measure the paneling the app actually ships. |
| `airplane.s_ref / b_ref / c_ref` | app-derived | largest-planform wing (model_schema_converters.py:814-819); the script re-reads them at pipeline_asb.py:85, 10 | m^2 / m / m |  |
| `op_point.velocity` | passed-through | flight.velocity_mps  (pipeline_asb.py:271) | m/s |  |
| `op_point.alpha` | app-derived | float(a) from the alpha sweep loop (pipeline_asb.py:270-271) | deg |  |
| `op_point.atmosphere` | solver-default | not passed — asb.OperatingPoint defaults to sea level, although flight.altitude_m exists and is used on the Ae | m | ⚠️ The two arms of the comparison run at different densities. Inviscid VLM coefficients are density-independent so the polars still compare, but any dimensional or Re-dependent quantity would not. |
| `op_point.beta / p / q / r` | solver-default | not passed — 0 (pipeline_asb.py:271) | deg / rad/s |  |
| `xyz_ref` | app-derived | [flight.x_cg_m, 0.0, 0.0]  (pipeline_asb.py:275) | m |  |
| `spanwise_resolution` | app-derived | _vlm_spanwise_resolution(asb_airplane) = max(1, round(24 / max(len(w.xsecs)))) (pipeline_asb.py:246, 250-252) |  | ⚠️ Per-section, not per-span — exactly the distribution gh-855 removed from the app path (see vlm_strip_forces.py:176-181). Tiny segments are over-resolved relative to large ones. |
| `chordwise_resolution` | hardcoded | _VLM_CHORDWISE_RESOLUTION = 6  (pipeline_asb.py:247, 277) | panels |  |
| `spanwise_spacing_function` | solver-default | not passed — np.cosspace |  | ⚠️ Production passes np.linspace; the benchmark uses cosine spacing. |
| `chordwise_spacing_function / vortex_core_radius / align_trailing_vortices_with_wind / run_symmetric_if_possible / verbose` | solver-default | not passed — cosspace / 1e-8 / False / False / False |  |  |

**Read back.** `d["CL"], d["CD"] (pipeline_asb.py:280-281)` · `d.get("CDi", cd) (282)` · `d.get("Cm", nan) (283)`

**Consumed by.** `scripts/vspaero_benchmark/pipeline_asb.py:284-296 (row assembly, e = CL^2/(pi*AR*CDi))` · `scripts/vspaero_benchmark/compare.py:22` · `scripts/vspaero_benchmark/build_dashboard.py:20, 240`

### `test/Test_RV7ConstructionSteps_V2.py:484` — `module-level RV-7 construction script`

Developer scratch script: runs VLM and AVL on the RV-7 demo airplane and draws the result.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airplane` | app-derived | asb_airplane.with_control_deflections({"flaps": 0, "aileron": 0.0})  (line 485) |  | ⚠️ with_control_deflections has no effect on VLM (wing.py:1148-1170 ignores hinge deflection); the same expression is reused for the asb.AVL call at line 498 where it does matter. |
| `op_point.velocity` | hardcoded | 15  (line 487) | m/s |  |
| `op_point.alpha` | hardcoded | 5  (line 488) | deg |  |
| `op_point.p / q / r` | hardcoded | 0.  (lines 489-491) | rad/s |  |
| `op_point.beta` | solver-default | not passed — 0 | deg |  |
| `op_point.atmosphere` | solver-default | not passed — sea level |  |  |
| `xyz_ref` | solver-default | not passed — airplane.xyz_ref (vortex_lattice_method.py:62-63) | m |  |
| `airplane.s_ref / b_ref / c_ref` | solver-default | not set on this Airplane — asb.Airplane falls back to wings[0] geometry | m^2 / m / m | ⚠️ This is the surfaces[0] pattern the app fixed in gh-788, still live in the script; correct only because wings[0] happens to be the main wing here. |
| `spanwise_resolution / chordwise_resolution / spacing functions / vortex_core_radius / align_trailing_vortices_with_wind / run_symmetric_if_possible / verbose` | solver-default | not passed — 10 / 10 / cosspace / cosspace / 1e-8 / False / False / False |  |  |

**Read back.** `vlm.run() dict (line 495)` · `vlm.draw(backend="plotly", show=True) (line 496)`

**Consumed by.** `test/Test_RV7ConstructionSteps_V2.py:495-496 (assigned to aero_vlm, only drawn)`

## aerosandbox.LiftingLine (asb 4.2.9) — single construction site: app/services/section_aoa_service.py:261

```text
Boundary shape: exactly ONE `asb.LiftingLine(...)` in the repo (section_aoa_service.py:261). Three app paths feed it: the REST endpoint (section_aoa.py:110), the turbulator optimizer endpoint (turbulator_optimizer.py:115), and the assumption recompute (assumption_compute_service.py:149). `ll.run()`'s return dict is discarded; only mesh/circulation attributes are read, so the unpassed s_ref/b_ref/c_ref on the single-wing Airplane is a latent, not active, gh-788 repeat. The active gh-788 repeat is `_resolve_level_flight_op` (:491-497): s_ref = first *symmetric* wing, not largest.

Highest-value app-side defect found on the output side, caused by an input assumption: for `symmetric=True` wings LiftingLine meshes both halves (lifting_line.py:579-595; wing.py:992-1006), so `y_arr` runs −b/2…+b/2. But the twist interpolation at :324 (`np.interp(y_arr, xsec_y, xsec_twist)`) and the alpha_L0 interpolation at :298 use `xsec_y`, which is non-negative (xsec .xyz_le[1], :320). `np.interp` clamps below the range, so every left-half panel receives the ROOT twist and ROOT alpha_L0 — `alpha_geometric_deg` and `alpha_effective_deg` are wrong on half the returned span for any washed-out wing, and the sign of `induced_angle_deg` follows. The returned list is sorted ascending y (:342) so the defect is the first half of the response.

Related consequence: `build_wing_section_data` (turbulator_optimizer_service.py:383-384, 420-423) documents "section_aoa covers one half-span" and normalises ΣS_i = s_ref/2; the entries actually cover the full span. Because `compute_turbulator_delta_cd0` then applies symmetry_factor=2.0 (turbulator_optimizer_service.py:330), the aggregate ΔCD0 area sums to s_ref and is not obviously wrong, but the premise is inverted and the per-section areas are half their true value.

Unit handling at this boundary is clean: the converter emits metres, the rad→deg conversion happens once in operating_point_resolver.py:124-125, and OperatingPointSchema rejects |alpha|>180 (aeroanalysisschema.py:275-291). No mm/m leak observed at the solver interface.

Undeclared fallbacks (ADR 0020 relevant), none emitting a DesignWarning: mass 1.5 kg (:485), s_ref 0.3 (:499), cl_target clip [0.1,2.0] (:504), alpha 4.0 (:528), velocity 15.0 (:144, :502), chord 0.20 (:160), alpha_L0 0.0 (:190), design_speed `or 15.0` (turbulator_optimizer.py:87), airfoil name → "naca0012" (turbulator_optimizer_service.py:405-407).
```

### `app/services/section_aoa_service.py:261` — `compute_section_aoa → asb.LiftingLine(...) ; ll.run() at :266`

Solve the spanwise circulation of one named wing to derive per-section cl, effective/geometric/induced AoA.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airplane` | app-derived | single_wing_airplane = asb.Airplane(wings=[target_wing], xyz_ref=asb_airplane.xyz_ref)  (:256-259) — target_wi | m (ASB geometry) | ⚠️ Fuselages and all other wings dropped. Reference values (s_ref/b_ref/c_ref) NOT passed to this Airplane, so ASB re-derives them from wings[0] = target_wing; the gh-788 largest-wing s_ref computed in model_schema_converte |
| `op_point` | passed-through | asb_op_point — the caller's asb.OperatingPoint (built at :452, or turbulator_optimizer.py:108, or assumption_c | m/s, deg, rad/s |  |
| `spanwise_resolution` | hardcoded | spanwise_resolution=_SPANWISE_RESOLUTION = 8 (:63, default arg at :208) | count | ⚠️ Comment at :63 and docstring at :221 say 'panels per half-span'. It is a subdivision RATIO: wing.subdivide_sections(ratio=8) at lifting_line.py:545-548. Actual panel count = (n_xsecs−1)·8, doubled for symmetric wings. Gr |
| `xyz_ref` | solver-default | not passed → LiftingLine falls back to airplane.xyz_ref (lifting_line.py:84-85) = plane_schema.xyz_ref | m | ⚠️ The resolved TRIMMED OP carries its own xyz_ref (CG) — read at operating_point_resolver.py:114/129 into op_schema.xyz_ref — and is then never used. Moment reference is the geometry ref, not the trim CG. Latent (moments u |
| `model_size` | solver-default | not passed → 'medium' (lifting_line.py:52); drives the NeuralFoil calls at lifting_line.py:726,805 |  | ⚠️ The app's own NeuralFoil call in the same module uses model_size='small' (:183). Two different viscous fidelities inside one result. |
| `spanwise_spacing_function` | solver-default | not passed → np.cosspace (lifting_line.py:56-58) |  |  |
| `vortex_core_radius` | solver-default | not passed → 1e-8 (lifting_line.py:59) | m |  |
| `align_trailing_vortices_with_wind` | solver-default | not passed → False (lifting_line.py:60) |  |  |
| `run_symmetric_if_possible` | solver-default | not passed → False (lifting_line.py:53); True raises NotImplementedError (lifting_line.py:100) |  |  |
| `verbose` | solver-default | not passed → False (lifting_line.py:54) |  |  |
| `airplane.wings[0].symmetric` | passed-through | wing.symmetric from the DB schema (model_schema_converters.py:801) |  | ⚠️ When True the solver meshes BOTH halves (lifting_line.py:579-595, wing.py:992-1006), so the panel set spans −b/2…+b/2. Every downstream app assumption of 'one half-span' is then wrong (see notes). |
| `xsec control_surfaces / deflections` | passed-through | carried on target_wing.xsecs; consumed at lifting_line.py:574,725,804. Set only on the get_section_aoa path vi | deg | ⚠️ The two turbulator callers never apply deflections — geometry is at neutral, not at trim. |
| `convergence / iteration settings` | solver-default | LiftingLine exposes none; no tolerance or iteration cap is passable or passed |  |  |

**Read back.** `ll.vortex_centers → y_arr (:271)` · `ll.vortex_strengths → gamma_arr (:272)` · `ll.chords → chord_arr (:273)` · `ll.get_velocity_at_points(ll.vortex_centers) → v_local, vmag (:275-276)` · `ll.run() return dict is discarded entirely (:266) — no CL/CD/Cm read`

**Consumed by.** `app/services/section_aoa_service.py:279 (cl_arr = 2·Γ/(Vmag·c))` · `app/services/section_aoa_service.py:300 (alpha_eff)` · `app/services/section_aoa_service.py:326 (alpha_geom)` · `app/services/section_aoa_service.py:337 (induced)` · `app/services/section_aoa_service.py:344-354 (SectionAoaEntry list)` · `app/api/v2/endpoints/section_aoa.py:128 (SectionAoaPoint response)` · `app/services/turbulator_optimizer_service.py:411-412,439-440 (build_wing_section_data reads .y_m/.chord_m/.cl)` · `app/api/v2/endpoints/aeroplane/turbulator_optimizer.py:127,135` · `app/services/assumption_compute_service.py:156,163`

### `app/services/section_aoa_service.py:256` — `asb.Airplane (single-wing wrapper built solely to feed LiftingLine)`

Isolate the requested wing so cross-wing interference does not confuse section attribution.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `wings` | app-derived | [target_wing] — first wing whose .name == wing_name (:241-244) |  | ⚠️ wing_name is an unvalidated URL path param (section_aoa.py:93); any wing including a tail is accepted. |
| `xyz_ref` | passed-through | asb_airplane.xyz_ref (= plane_schema.xyz_ref, model_schema_converters.py:825) | m |  |
| `s_ref` | solver-default | not passed → ASB derives from wings[0].area() | m² | ⚠️ asb_airplane.s_ref (largest-wing, gh-788 fix) is available and silently not forwarded. |
| `b_ref` | solver-default | not passed → wings[0].span() | m |  |
| `c_ref` | solver-default | not passed → wings[0].mean_aerodynamic_chord() | m |  |
| `fuselages` | solver-default | not passed → empty; the parent airplane's fuselages (model_schema_converters.py:824) are dropped |  |  |
| `name` | solver-default | not passed |  |  |

**Read back.** `single_wing_airplane`

**Consumed by.** `app/services/section_aoa_service.py:262`

### `app/services/section_aoa_service.py:452` — `get_section_aoa → asb.OperatingPoint / asb.Atmosphere`

Build the operating point handed to LiftingLine on the REST path (GET .../section-aoa).

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `velocity` | passed-through | op_schema.velocity — DB OperatingPointModel.velocity | m/s |  |
| `alpha` | passed-through | op_schema.alpha — rad→deg converted once in operating_point_resolver.py:124 | deg |  |
| `beta` | passed-through | op_schema.beta — rad→deg at operating_point_resolver.py:125 | deg |  |
| `p / q / r` | passed-through | op_schema.p/q/r (:456-458) | rad/s |  |
| `atmosphere` | app-derived | asb.Atmosphere(altitude=op_schema.altitude) (:451) | m |  |
| `control_deflections` | passed-through | op_schema.control_deflections → asb_airplane.with_control_deflections(...) (:463-464) | deg |  |
| `operating point selection` | app-derived | explicit operating_point_id (:414-430), else FIRST TRIMMED OP by unordered query (:433-440), else _resolve_lev |  | ⚠️ 'first TRIMMED OP' has no ORDER BY (:433-440) — the chosen flight condition is DB-order dependent and not reported back (the response echoes the request's operating_point_id, section_aoa.py:127, which is None in that bra |
| `xyz_ref` | app-derived | op_schema.xyz_ref is resolved but never applied — asb.OperatingPoint has no xyz_ref and none is passed to Lift |  | ⚠️ Trim CG discarded; see risk on LiftingLine.xyz_ref. |

**Read back.** `asb_op` · `deflected asb_airplane`

**Consumed by.** `app/services/section_aoa_service.py:466`

### `app/api/v2/endpoints/aeroplane/turbulator_optimizer.py:108` — `asb.OperatingPoint → compute_section_aoa (:115)`

Provide the operating point for the turbulator trip-position optimizer's section sweep.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `velocity` | user-input | design_speed = get_effective_assumption(db, aircraft.id, 'design_speed_mps') or 15.0 (:87) | m/s | ⚠️ `or 15.0` also swallows a stored 0.0. |
| `alpha` | hardcoded | alpha=3.0 (:110) | deg | ⚠️ The comment at :105-107 claims 'LiftingLine re-solves the circulation at the true condition, so only the CL-distribution shape depends on this seed alpha'. LiftingLine performs no trim; α=3° IS the condition, and the abs |
| `beta / p / q / r` | solver-default | not passed → 0.0 (operating_point.py:15-19) |  |  |
| `atmosphere` | solver-default | not passed → Atmosphere(altitude=0) (operating_point.py:12) |  | ⚠️ Sea level assumed even where a stored OP altitude exists. |
| `control_deflections` | solver-default | never applied on this path — asb_airplane used raw (:91) |  |  |
| `wing_name` | app-derived | max(asb_airplane.wings, key=w.area()).name or 'main_wing' (:99-100) |  |  |
| `s_ref (for the downstream reader, not LiftingLine)` | app-derived | float(main_wing.area()) (:101) | m² |  |

**Read back.** `section_entries (y_m, chord_m, cl, alphas)`

**Consumed by.** `app/api/v2/endpoints/aeroplane/turbulator_optimizer.py:127-132 (build_wing_section_data)` · `app/api/v2/endpoints/aeroplane/turbulator_optimizer.py:135-140 (run_turbulator_optimizer)`

### `app/services/assumption_compute_service.py:139` — `asb.OperatingPoint → compute_section_aoa (:149)`

Recompute the turbulator ΔCD0 that is added to the stored cd0 assumption.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `velocity` | app-derived | v_cruise from _load_flight_profile_speeds(db, aircraft) (:90) | m/s |  |
| `alpha` | hardcoded | alpha=3.0 (:139) | deg | ⚠️ Same false 're-solves at the true condition' comment (:136-138); the cl distribution feeding ΔCD0 is at 3°, while cd0 itself is the AeroBuildup value at v_cruise. |
| `beta / p / q / r` | solver-default | not passed → 0.0 |  |  |
| `atmosphere` | solver-default | not passed → Atmosphere(altitude=0) |  |  |
| `control_deflections` | solver-default | never applied |  |  |
| `airplane` | passed-through | asb_airplane from aeroplane_schema_to_asb_airplane_async |  |  |
| `wing_name` | app-derived | max(asb_airplane.wings, key=w.area()).name or 'main_wing' (:144-145) |  |  |

**Read back.** `_section_entries`

**Consumed by.** `app/services/assumption_compute_service.py:156-161 (build_wing_section_data, s_ref from _stability_run_at_cruise :93)` · `app/services/assumption_compute_service.py:163-170 (apply_turbulator_delta_to_cd0 → stored cd0 at :191-198)`

### `app/services/section_aoa_service.py:515` — `_resolve_level_flight_op → asb.AeroBuildup + scipy.brentq`

Fallback that manufactures the alpha/velocity later handed to LiftingLine when no TRIMMED OP exists.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `mass_kg` | app-derived | getattr(plane_schema, 'total_mass_kg', None) or 1.5 (:485) | kg | ⚠️ Silent 1.5 kg substitution, no DesignWarning. |
| `s_ref` | app-derived | first wing in asb_airplane.wings with symmetric=True → float(w.area()) (:491-497); else 0.3 (:499) | m² | ⚠️ This is exactly the gh-788 failure mode re-introduced: FIRST symmetric wing, not the largest. A symmetric HTP ordered before the wing (tail-first import) yields the tail area → wrong cl_target → wrong fallback alpha. asb |
| `rho` | hardcoded | rho = 1.225 (:486) | kg/m³ | ⚠️ Duplicates asb.Atmosphere(0).density(); a second density authority alongside the atmosphere object built at :506. |
| `g` | hardcoded | g = 9.80665 (:487) | m/s² |  |
| `cruise_v` | hardcoded | cruise_v = 15.0 (:502); also becomes the returned OperatingPointSchema.velocity (:533) | m/s | ⚠️ Ignores the design_speed_mps assumption that the turbulator endpoint does read (turbulator_optimizer.py:87) — two speed authorities for one aircraft. |
| `cl_target` | app-derived | (2·mass_kg·g)/(rho·s_ref·cruise_v²), clipped to [0.1, 2.0] (:503-504) |  | ⚠️ Silent clip; no warning emitted. |
| `atmosphere` | hardcoded | asb.Atmosphere(altitude=0.0) (:506) |  |  |
| `xyz_ref (AeroBuildup)` | passed-through | getattr(asb_airplane, 'xyz_ref', [0,0,0]) (:518) |  |  |
| `alpha bracket / tolerance` | hardcoded | brentq(_cl_at_alpha, -5.0, 15.0, xtol=0.05, maxiter=30) (:526); on ValueError → alpha = 4.0 (:528) | deg | ⚠️ Non-bracketing returns a silent 4.0°; the exception handler at :522-523 also returns −cl_target for every failed AeroBuildup, which makes the root finder converge on a fabricated bracket. |
| `beta / p / q / r` | hardcoded | 0.0 (:536-538) |  |  |

**Read back.** `OperatingPointSchema(velocity, alpha, beta, p, q, r, xyz_ref, altitude=0.0)`

**Consumed by.** `app/services/section_aoa_service.py:446 → :452-460 → LiftingLine op_point`

### `app/services/section_aoa_service.py:180` — `_compute_alpha_l0_per_section → airfoil.get_aero_from_neuralfoil`

Zero-lift angle per xsec; added directly to the reported alpha_effective_deg.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `alpha` | hardcoded | np.linspace(-6.0, 2.0, 40) (:179) | deg | ⚠️ Fixed window; a strongly cambered section with alpha_L0 < −6° gets alpha_L0 clamped by np.interp to −6°. |
| `Re` | app-derived | re_local = max(velocity·chord/nu, 1e4) with nu = 1.5e-5 hardcoded (:141,162) |  | ⚠️ nu hardcoded although op_point.atmosphere.kinematic_viscosity() is available; same hardcode repeated at turbulator_optimizer_service.py:396. |
| `velocity` | app-derived | float(np.atleast_1d(op_point.velocity)[0]), except → 15.0 (:143-145) | m/s |  |
| `chord` | passed-through | float(xs.chord), except → 0.20 (:158-160) | m |  |
| `model_size` | hardcoded | 'small' (:183) |  | ⚠️ LiftingLine's internal NeuralFoil runs at 'medium' (solver default). Mixed fidelity in one result. |
| `airfoil` | passed-through | xs.airfoil from the ASB wing xsecs |  |  |
| `failure path` | app-derived | any exception → alpha_l0 = 0.0 (:190) | deg | ⚠️ Undeclared fallback: a NeuralFoil failure silently reports a symmetric-section zero-lift angle. |

**Read back.** `(y_arr, alpha_l0_arr)`

**Consumed by.** `app/services/section_aoa_service.py:296-300 (alpha_eff = degrees(cl/2π) + alpha_L0)`

## NeuralFoil (via `aerosandbox.Airfoil.get_aero_from_neuralfoil`; ASB signature: `(alpha, Re, mach=0.0, n_crit=9.0, xtr_upper=1.0, xtr_lower=1.0, model_size='large', control_surfaces=None, include_360_deg_effects=True)`)

```text
Scope note: `app/services/polar_re_table_service.py` contains NO NeuralFoil call. It rebins an existing AeroBuildup V-sweep into Re-bands (module docstring :3-5) and computes Re itself from `rho*V*MAC/mu` with `mu=1.81e-5` hardcoded at :46 — a third, independent viscosity/Re authority alongside `asb.Atmosphere` (neuralfoil_cdcl_service.py:21) and `nu=1.5e-5` (turbulator_optimizer_service.py:396, section_aoa_service.py:141). Listed here only to close the search.

Cross-cutting observations:

1. `control_surfaces` is never passed at ANY of the six sites. For the AVL CDCL path this is load-bearing: those exact sections carry CONTROL entries, so the profile-drag table AVL reads is always the undeflected polar.

2. `include_360_deg_effects` diverges three ways for the same switch — False (CdclConfig), True explicit (endpoint), True by omission (low-Re backfill, turbulator, section_aoa). The backfill's is the consequential one: it sweeps to +18° and its post-stall shape sets stored `cl_max`, `stall_gentleness`, `drag_bucket_width`.

3. Reynolds is app-derived at every non-endpoint site and never agrees with itself. Only `compute_reynolds_number` honours altitude; the turbulator and section-AoA paths use a literal `nu=1.5e-5` (≈+2.7 % vs ISA-SL 1.4607e-5) and floor at `1e4`.

4. `model_size` runs "xxxlarge" (backfill), "large" (endpoint/CDCL), "small" (turbulator, section_aoa). The "small" choices are hardcoded defaults on private helpers no caller overrides, and their output reaches user-visible cd0 (assumption_compute_service.py:2159).

5. Undeclared fallbacks worth ADR-0020 attention: NaN/Inf polar → zero CDCL (neuralfoil_cdcl_service.py:56-64, warning only); missing airfoil name → "naca0012" (turbulator_optimizer_service.py:405-407, :435); out-of-range cl_target → nearest-neighbour cd (:165-173, debug only); missing `analysis_confidence` key → `[1.0]`, i.e. the confidence gate cannot fire (:221); velocity→15.0 / chord→0.20 literals (section_aoa_service.py:145, :160); `np.interp` clamp of alpha_L0 to -6° (:188).

6. Wrong-object exposure is latent, not live: the CDCL positional pairing `wing_list[surf_idx]` / `wing.x_secs[sec_idx]` (avl_geometry_service.py:250-256) is correct only because surfaces are built from the same `plane_schema.wings.items()` order at :195. Both turbulator entry points do correctly pick the main wing by `max(..., key=w.area())` (turbulator_optimizer.py:99, turbulator_optimizer_service.py:399).

7. `_get_polar_data`'s `@lru_cache` keys o
```

### `app/services/neuralfoil_cdcl_service.py:44` — `_get_polar_data`

Produce the CL/CD polar from which a 3-point AVL CDCL card (profile drag) is fitted per wing section.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airfoil (geometry)` | app-derived | _build_asb_airfoil(airfoil_name) at neuralfoil_cdcl_service.py:42 — rebuilt from the NAME only; the asb.Airfoi | normalised coords | ⚠️ @lru_cache(maxsize=128) at :25 is keyed on airfoil_name, not on coordinates — two .dat files with the same stem, or a user replacing an airfoil file, return the other/stale geometry for the process lifetime; no invalidat |
| `alpha` | app-derived | np.arange(alpha_start, alpha_end + alpha_step/2, alpha_step) at :43, from CdclConfig (default -10..16 step 1 → | deg |  |
| `Re` | app-derived | compute_reynolds_number(velocity=op.velocity, chord=xsec.chord, altitude=op.altitude) at avl_geometry_service. | – (chord in m, WingXSecSchema.chord is metres, aeroplaneschema.py:528-531) | ⚠️ Section pairing is positional: wing_list[surf_idx] (avl_geometry_service.py:250) and wing.x_secs[sec_idx] (:256). Safe today only because surfaces are built from the same plane_schema.wings.items() ordering (:195); any w |
| `mach` | hardcoded | avl_file.mach passed at avl_geometry_service.py:263; AvlGeometryFile is constructed with mach=0.0 at avl_geome | – | ⚠️ Operating-point velocity and altitude are both available on the schema and never enter Mach; the value is a literal 0.0 regardless of the requested condition. |
| `model_size` | user-input | config.model_size (CdclConfig default "large", aeroanalysisschema.py:197) |  |  |
| `n_crit` | user-input | config.n_crit (default 9.0, aeroanalysisschema.py:198-200) |  |  |
| `xtr_upper` | user-input | config.xtr_upper (default 1.0, aeroanalysisschema.py:201-203) | x/c |  |
| `xtr_lower` | user-input | config.xtr_lower (default 1.0, aeroanalysisschema.py:204-206) | x/c |  |
| `include_360_deg_effects` | user-input | config.include_360_deg_effects (CdclConfig default False, aeroanalysisschema.py:207-209) — explicitly override |  | ⚠️ Three call paths in this repo run three different effective values for the same physical switch: False here, True (explicit) at airfoils.py:345, True (unpassed default) at airfoil_low_re_service.py:469. |
| `control_surfaces` | solver-default | not passed → None |  | ⚠️ The same AVL sections carry CONTROL entries built at avl_geometry_service.py:131-142 (flaps/elevons/ruddervators). The CDCL profile-drag table is always the undeflected-section polar, so deflected-flap profile drag is ab |

**Read back.** `aero["CL"] (:54)` · `aero["CD"] (:55)` · `derived cl_min/cd_min/cl_0/cd_0/cl_max/cd_max at :92-101`

**Consumed by.** `app/services/avl_geometry_service.py:262 (section.cdcl assignment)` · `app/services/avl_trim_service.py:93` · `app/services/stability_service.py:310` · `app/services/analysis_service.py:313` · `app/services/analysis_service.py:360` · `app/services/analysis_service.py:1822` · `app/services/analysis_service.py:1957`

### `app/services/airfoil_low_re_service.py:469` — `compute_airfoil_low_re`

Sweep the stored airfoil library over a 13-point absolute Re grid to backfill the low-Re polar metrics table used for airfoil suitability scoring.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airfoil (geometry)` | passed-through | asb.Airfoil(name=name, coordinates=coords) at :465; coords = np.asarray(af.coordinates, dtype=float) from Airf | assumed unit chord | ⚠️ Only guard is len(coords) < 10 (background_jobs.py:347). The docstring asserts "normalised 0..1" (:425) but nothing normalises or checks chord length / Selig ordering, and _sanitize_airfoil (model_schema_converters.py:67 |
| `alpha` | app-derived | np.arange(alpha_start, alpha_end + alpha_step*0.5, alpha_step) at :464; bounds are the signature defaults -5.0 | deg |  |
| `Re` | user-input | float(re) at :471, iterating settings.low_re_grid (13 values, app/settings.py:90/117, default _DEFAULT_LOW_RE_ | – |  |
| `mach` | hardcoded | mach=0.0 at :472 |  |  |
| `n_crit` | user-input | float(n_crit) at :473 ← settings.low_re_n_crit (9.0, settings.py:96) |  |  |
| `model_size` | user-input | model_size at :474 ← settings.low_re_neuralfoil_model_size ("xxxlarge", settings.py:95) |  |  |
| `xtr_upper` | solver-default | not passed → 1.0 (free transition) | x/c |  |
| `xtr_lower` | solver-default | not passed → 1.0 | x/c |  |
| `include_360_deg_effects` | solver-default | not passed → True |  | ⚠️ The sweep runs to +18°, past stall at these Re. The 360° blend therefore shapes the post-stall CL/CD from which cl_max (:614-616), stall_gentleness (:620-623) and drag_bucket_width (:638-641) are extracted — an invisible |
| `control_surfaces` | solver-default | not passed → None |  |  |

**Read back.** `raw["CL"] (:477)` · `raw["CD"] (:478)` · `raw["analysis_confidence"] (:479)`

**Consumed by.** `app/services/airfoil_low_re_service.py:486-489 (confidence gate ≥ settings.low_re_confidence_gate)` · `app/services/airfoil_low_re_service.py:493-517 (_extract_metrics + _windowed_min_confidence)` · `app/core/background_jobs.py:396-411 (upsert AirfoilLowRePolarModel)` · `scripts/backfill_airfoil_low_re.py:164-186` · `app/services/suitability_service.py:403`

### `app/services/turbulator_optimizer_service.py:140` — `_cd_at_cl_xtr`

Return section cd at a target CL for one trip location — the atomic lookup behind cd_clean, cd_tripped and the aircraft-level turbulator ΔCD0.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airfoil (geometry)` | app-derived | _build_asb_airfoil(sec.airfoil_name) at :498 / :555 / :567 / :692; the name comes from getattr(xs.airfoil,"nam |  | ⚠️ Undeclared fallback: an xsec whose airfoil object has no name silently becomes naca0012, and the resulting cd delta is applied to the real aircraft's cd0 with no warning (ADR 0020). |
| `alpha` | hardcoded | _ALPHA_GRID = np.linspace(-4.0, 14.0, 37) module constant at :60 | deg |  |
| `Re` | app-derived | sec.re_local = max(velocity * entry.chord_m / nu, 1e4) at :442, with nu = 1.5e-5 hardcoded at :396; velocity = | – (chord m, velocity m/s, nu m²/s) | ⚠️ Two problems. (1) nu=1.5e-5 is a literal ~2.7 % above ISA-SL 1.4607e-5 and ignores altitude entirely, while neuralfoil_cdcl_service.py:21-22 derives ν from asb.Atmosphere(altitude) — two competing Re authorities for the  |
| `xtr_upper` | app-derived | swept float(xtr) over XTR_GRID = np.linspace(0.2,0.9,15) at :53/:210; or 1.0 for the clean baseline (:232, :56 | x/c |  |
| `xtr_lower` | hardcoded | default parameter 1.0 at :125 — no caller ever passes it (:210, :232, :568, :570, :693, :694) | x/c |  |
| `model_size` | hardcoded | default parameter "small" at :126 — no caller overrides it |  | ⚠️ Coarsest NeuralFoil model. Its cd_tripped − cd_clean difference is added straight onto the AeroBuildup cd0 at assumption_compute_service.py:2159-2169, i.e. a user-visible drag number. The app's own configured accuracy se |
| `mach` | solver-default | not passed → 0.0 |  |  |
| `n_crit` | solver-default | not passed → 9.0 |  | ⚠️ The app has an explicit transition-criterion setting (settings.low_re_n_crit, settings.py:96) that it feeds to the airfoil-library sweep; this path — which is specifically about transition — takes the solver's default in |
| `include_360_deg_effects` | solver-default | not passed → True |  |  |
| `control_surfaces` | solver-default | not passed → None |  |  |
| `cl_target (selects the answer, not a solver arg)` | app-derived | sec.cl ← LiftingLine section CL, 2*gamma/(vmag*chord) at section_aoa_service.py:279, seeded at alpha=3.0 (turb |  | ⚠️ When cl_target falls outside the finite CL band the code returns the nearest-neighbour cd (:165-173) behind a logger.debug only — a silent extrapolation on a value that feeds cd0. |

**Read back.** `aero["CL"] (:147)` · `aero["CD"] (:148)` · `interpolated cd at cl_target (:175) or nearest-neighbour cd (:173)`

**Consumed by.** `app/services/turbulator_optimizer_service.py:210 (xtr sweep) → :256-258 argmin xtr_opt` · `app/services/turbulator_optimizer_service.py:232 (cd_clean), :273 (delta_cd)` · `app/services/turbulator_optimizer_service.py:328 (compute_turbulator_delta_cd0 area weighting)` · `app/api/v2/endpoints/aeroplane/turbulator_optimizer.py:143-165 (response)` · `app/services/assumption_compute_service.py:2141-2169 (apply_turbulator_delta_to_cd0 → aircraft cd0)`

### `app/services/turbulator_optimizer_service.py:215` — `optimize_section_xtr (confidence probe)`

Separate probe call whose only purpose is to read analysis_confidence and warn when the optimizer's answer is untrustworthy.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airfoil (geometry)` | app-derived | same _build_asb_airfoil(sec.airfoil_name) object passed into optimize_section_xtr at :517 / :557 |  |  |
| `alpha` | hardcoded | _ALPHA_GRID (:60) at :217 | deg |  |
| `Re` | app-derived | re at :217 = sec.re_local (see :442, nu=1.5e-5) | – |  |
| `xtr_upper` | app-derived | float(xtr_grid[len(xtr_grid)//2]) at :218 → 0.55 for the default 15-point grid | x/c | ⚠️ Confidence is sampled at ONE mid-grid trip location and generalised to all 15 sweep points including the xtr=1.0 clean baseline, which is never probed. |
| `model_size` | hardcoded | "small" at :219 |  |  |
| `xtr_lower` | solver-default | not passed → 1.0 |  |  |
| `mach` | solver-default | not passed → 0.0 |  |  |
| `n_crit` | solver-default | not passed → 9.0 |  |  |
| `include_360_deg_effects` | solver-default | not passed → True |  |  |
| `control_surfaces` | solver-default | not passed → None |  |  |

**Read back.** `aero_check.get("analysis_confidence", [1.0]) (:221)` · `conf_mean = np.nanmean(...) (:222)`

**Consumed by.** `app/services/turbulator_optimizer_service.py:223-227 (warning appended to SectionOptimizerResult.warnings)` · `app/api/v2/endpoints/aeroplane/turbulator_optimizer.py:155` · `app/services/assumption_compute_service.py:2149-2150 (logged)`

### `app/services/section_aoa_service.py:180` — `_compute_alpha_l0_per_section`

Obtain the section zero-lift angle alpha_L0 that shifts the thin-airfoil effective-AoA distribution.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airfoil (geometry)` | passed-through | xs.airfoil taken directly off the asb.Wing xsec at :165 |  |  |
| `alpha` | hardcoded | np.linspace(-6.0, 2.0, 40) at :179 | deg | ⚠️ A cambered low-Re section with alpha_L0 below -6° cannot be resolved; np.interp at :188 clamps to -6.0 with no warning (see outputs). |
| `Re` | app-derived | re_local = max(velocity * chord / nu, 1e4) at :162; nu = 1.5e-5 hardcoded at :141; velocity = float(np.atleast | – (m, m/s) | ⚠️ Two silent literal substitutions (velocity→15.0 m/s, chord→0.20 m) on the except paths, plus the same nu=1.5e-5 / altitude-blind constant as the turbulator path. |
| `model_size` | hardcoded | "small" at :183 |  |  |
| `mach` | solver-default | not passed → 0.0 |  |  |
| `n_crit` | solver-default | not passed → 9.0 |  |  |
| `xtr_upper` | solver-default | not passed → 1.0 |  |  |
| `xtr_lower` | solver-default | not passed → 1.0 |  | ⚠️ When the wing has an enabled turbulator, alpha_L0 is still computed for the free-transition airfoil — the trip state known to the turbulator path never reaches this call. |
| `include_360_deg_effects` | solver-default | not passed → True |  |  |
| `control_surfaces` | solver-default | not passed → None |  |  |

**Read back.** `polar["CL"] (:185)` · `alpha_l0 = np.interp(0.0, cl_2d, alphas) (:188)`

**Consumed by.** `app/services/section_aoa_service.py:296-298 (alpha_L0_at_y interpolation onto panel y)` · `app/services/section_aoa_service.py:300 (alpha_eff_arr = degrees(cl/2π) + alpha_L0_at_y)` · `app/services/turbulator_optimizer_service.py:411-412 and :439-441 (entries consumed as WingSectionData)`

### `app/api/v2/endpoints/airfoils.py:337` — `_run_neuralfoil_analysis`

Interactive per-request airfoil polar analysis endpoint (JSON results and PNG diagrams).

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airfoil (geometry)` | app-derived | asb.Airfoil(name=airfoil_path.stem, coordinates=airfoil_path) at :333; path from _resolve_airfoil_file(airfoil |  | ⚠️ _sanitize_airfoil (model_schema_converters.py:67-80, which the converter path deems required "for solver stability") is not applied here — consecutive duplicate points reach the solver unfiltered. |
| `alpha` | app-derived | _build_alpha_grid(request) at :332 → np.arange(alpha_start_deg, alpha_end_deg + alpha_step_deg*0.5, alpha_step | deg |  |
| `Re` | user-input | float(reynolds) at :339, looping request.reynolds_numbers (default [1e4,3e4,5e4,1e5,2e5,5e5], :108-112) | – |  |
| `mach` | user-input | request.mach at :340 (default 0.0, :118) |  |  |
| `n_crit` | user-input | float(request.n_crit) at :341 (default 9.0, :119) |  |  |
| `xtr_upper` | user-input | request.xtr_upper at :342 (default 1.0, :120-122) | x/c |  |
| `xtr_lower` | user-input | request.xtr_lower at :343 (default 1.0, :123-125) | x/c |  |
| `model_size` | user-input | request.model_size at :344 (default "large", :126) — deliberately different from the backfill's "xxxlarge" (se |  |  |
| `include_360_deg_effects` | user-input | request.include_360_deg_effects at :345 (default True, :127) |  |  |
| `control_surfaces` | solver-default | not passed → None |  |  |

**Read back.** `raw["CL"] (:348)` · `raw["CD"] (:349)` · `raw["CM"] (:350)` · `raw["analysis_confidence"] (:351-353)` · `derived cl_over_cd (:354-359), cl_max/alpha_at_cl_max (:361-365), cd_min/alpha_at_cd_min (:367-371)`

**Consumed by.** `app/api/v2/endpoints/airfoils.py:962-982 (AirfoilNeuralFoilAnalysisResponse)` · `app/api/v2/endpoints/airfoils.py:1009-1041 (diagram endpoint → PNGs under tmp/airfoils/neuralfoil/)`

## AVL (vendored binary, `avl-binary` wheel) — driven headless via stdin keystrokes by `app/services/avl_runner.py:AVLRunner`

```text
Boundary shape: exactly one process boundary (avl_runner.py:325). Everything AVL learns arrives through two channels — the .avl text (geometry + reference block, built by avl_geometry_service.build_avl_geometry_file) and the stdin keystroke script (operating point, atmosphere, control deflections, trim constraints). No .mass and no .run file is ever written; mass/inertia and multi-case run decks are therefore pure solver defaults, and eigenmode analysis is unreachable.

Highest-value observations, all from read code:
1. AVLRunner.xyz_ref is assigned (line 106) and never read. Every one of the six call sites passes the operating point's CG. AVL's actual moment reference is the file's Xref = plane_schema.xyz_ref (avl_geometry_service.py:184, schema default [0,0,0]). stability_service.py:328 then computes static margin as (Xnp − operating_point.xyz_ref[0])/Cref — mixing a CG AVL never saw with an Xnp AVL derived about a different point. Same class as the surfaces[0] defect: right solver, wrong object.
2. Two authorities for the reference set. AVL non-dimensionalises with the file's Sref/Cref/Bref; _post_process_results (avl_runner.py:199-219) re-dimensionalises L/D/Y and the moments with the ASB airplane's s_ref/b_ref/c_ref, and the rate keystrokes (pb/2V etc.) use the ASB values too. Identical only while the file is app-generated; the user-edited-file path (get_user_avl_content) makes them independent.
3. Control deflections have no representation in the .avl file — AvlControl carries name/gain/xhinge/hvec/sgn_dup only. They exist solely as d{i} keystrokes derived from the ASB airplane. Consequently the strip-force/spanwise-loads AVL path (analysis_service.py:1831) runs a *trimmed* operating point with *untrimmed* control deflections, and its docstring (1804-1807) asserts the opposite.
4. d-index binding is positional across two independently-built structures: AVL numbers CONTROL variables by first appearance in the file, the app numbers them by ASB traversal (avl_strip_forces.py:163-171, 243-253). They agree only for app-generated geometry. Overrides whose name is unknown are dropped with no warning.
5. Silent substitutions with no DesignWarning (ADR 0020 candidates): airfoil → NACA 0012, CLAF → 1.0, v_cruise → 15.0, stall_alpha → 12.0, CDCL surface/wing count mismatch → truncation, unmatched control override → ignored, non-convergence → inferred from the presence of 'CL'.
6. CDCL polars are fitted at mach = avl_file.mach = 0.0 (hardcoded, avl_geometry_serv
```

### `app/services/avl_runner.py:325` — `AVLRunner.run → subprocess.Popen`

The single process boundary: writes airplane.avl into a temp dir, pipes the whole OPER keystroke script to the AVL binary, reads back output.txt (+stdout).

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `avl_command (argv[0])` | app-derived | _resolve_default_avl_command(): str(avl_binary.avl_path()) → shutil.which('avl') → literal 'avl' (avl_runner.p | path | ⚠️ silent 3-step fallback; if the wheel is missing the run may hit an arbitrary PATH avl or fail late with FileNotFoundError on output.txt |
| `argv[1] geometry file` | hardcoded | 'airplane.avl' (line 303), content = avl_file_content parameter | - |  |
| `cwd` | app-derived | tempfile.TemporaryDirectory() unless working_directory given; no call site ever passes working_directory (grep | path |  |
| `timeout` | user-input | self.timeout, default 30 (line 101); callers pass 60 (trim, strip forces, elevator) or 30 | s |  |
| `OPER/m: mn (Mach)` | app-derived | f'mn {op.mach()}' — velocity / atmosphere.speed_of_sound(altitude) (line 141) | - | ⚠️ overrides the file's Mach (which build_avl_geometry_file hardcodes to 0.0); the CDCL polars were fitted at mach=0.0, so profile drag and the run Mach disagree |
| `OPER/m: v (velocity)` | passed-through | f'v {op.velocity}' (line 142) | m/s | ⚠️ no scalar guard: _run_avl only rejects list alpha/beta (api/utils.py:40-46); a list velocity is formatted into the keystroke as an array literal |
| `OPER/m: d (density)` | app-derived | f'd {op.atmosphere.density()}' — asb.Atmosphere(altitude) (line 143) | kg/m^3 |  |
| `OPER/m: g (gravity)` | hardcoded | 'g 9.81' (line 144) | m/s^2 |  |
| `alpha` | passed-through | f'a a {op.alpha}' (line 153) | deg |  |
| `beta` | passed-through | f'b b {op.beta}' (line 154) | deg |  |
| `pb/2V (roll rate)` | app-derived | op.p * self.airplane.b_ref / (2*v), 0 if v or b falsy (lines 147,155) | - | ⚠️ non-dimensionalised with the ASB airplane's b_ref, but AVL re-dimensionalises with the .avl file's Bref; the two differ whenever a user-edited geometry file is used |
| `qc/2V (pitch rate)` | app-derived | op.q * self.airplane.c_ref / (2*v) (lines 148,156) | - | ⚠️ same ASB-vs-file Cref mismatch |
| `rb/2V (yaw rate)` | app-derived | op.r * self.airplane.b_ref / (2*v) (lines 149,157) | - | ⚠️ same ASB-vs-file Bref mismatch |
| `control deflections d{i} d{i} {val}` | app-derived | build_control_deflection_commands(self.airplane, control_overrides) — cs.deflection walked over asb airplane.w | deg | ⚠️ d-index comes from ASB traversal order while AVL numbers CONTROL variables by first appearance in the .avl file — they only coincide for app-generated files; an override name not present in `seen` is dropped silently (li |
| `extra_keystrokes (trim constraints)` | app-derived | build_indirect_constraint_commands(...) — only via run_trim (line 273) | - |  |
| `execute / output commands` | hardcoded | 'x', 'st', 'output.txt', 'o', optional 'fs', '', 'quit' (lines 162-174) | - |  |
| `xyz_ref (moment reference)` | solver-default | AVLRunner.__init__ stores self.xyz_ref (line 106) and NEVER reads it again — grep xyz_ref in avl_runner.py ret | m | ⚠️ every call site passes operating_point.xyz_ref (the CG) expecting it to be the moment reference; AVL actually uses plane_schema.xyz_ref from the file (avl_geometry_service.py:184). A request-supplied CG silently has no e |
| `mass / inertia (.mass file)` | solver-default | never written — no .mass writer exists anywhere in app/ (grep) | - |  |
| `run-case file (.run)` | solver-default | never written; run cases exist only as the single keystroke-configured case | - |  |
| `CDp / profile-drag adder in OPER` | solver-default | not set at run time; only the file-level CDp (default 0.0, never assigned) and per-section CDCL | - |  |

**Read back.** `output.txt parsed by parse_stability_output (avl_runner.py:41-83, 354-356) → every ' = ' key/value AVL prints: Sref,Cref,Bref,Xref,Yref,Zref,Alpha,Beta,Mach,CLtot,CDtot,CDind,CDff,CDvis,CYtot,Cltot,Cmtot,Cntot,e,Xnp, all stability derivatives (CLa,CLb,Cma,Cnb,Clb,Clp,Cnr,...), per-control derivatives, Strips/Surfaces/Vortices counts` · `proc.returncode (logged only, avl_runner.py:344-345)` · `stdout FS table → parse_strip_forces_output (avl_strip_forces.py:127) → per-surface strips: j,Xle,Yle,Zle,Chord,Area,c_cl,ai,cl_norm,cl,cd,cdv,cm_c/4,cm_LE,C.P.x/c` · `post-processed keys added by the app: p,q,r,L,Y,D,l_b,m_b,n_b,F_w,F_b,F_g,M_b,M_g,M_w,'Clb Cnr / Clr Cnb' (avl_runner.py:198-257)`

**Consumed by.** `app/services/avl_runner.py:214-219 (L/D/Y/l_b/m_b/n_b = q·S·C with S,b,c from the ASB airplane, NOT the file's Sref/Cref/Bref that AVL used to non-dimensionalise)` · `app/api/utils.py:58` · `app/services/avl_trim_service.py:39-57` · `app/services/analysis_service.py:1771-1790` · `app/services/elevator_authority_service.py:901-907`

### `app/services/avl_geometry_service.py:168` — `build_avl_geometry_file`

Writes the entire .avl geometry input: reference block, symmetry, panelling, sections, airfoils, CLAF, CDCL, CONTROL.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `title` | passed-through | plane_schema.name (line 211) |  |  |
| `mach (file header)` | hardcoded | mach=0.0 (line 212) | - | ⚠️ run-time keystroke sets the real Mach, but inject_cdcl fits NeuralFoil polars at avl_file.mach = 0.0 (line 263) |
| `Iysym/Izsym/Zsym` | hardcoded | AvlSymmetry() → 0, 0, 0.0 (line 213, geometry.py:329-331) |  |  |
| `Sref` | app-derived | asb_airplane.s_ref ← float(_find_reference_wing(wings).area()) = max(wings, key=area) (model_schema_converters | m^2 | ⚠️ the gh-788 fix for the surfaces[0]/tail-first defect; still an inference — 'largest planform' is a proxy for 'main wing', and asb Wing.area() semantics for symmetric wings decide whether it is half- or full-span area |
| `Cref` | app-derived | ref_wing.mean_aerodynamic_chord() (converters:819) | m |  |
| `Bref` | app-derived | ref_wing.span() (converters:818) | m |  |
| `Xref/Yref/Zref` | passed-through | tuple(plane_schema.xyz_ref) or (0.0,0.0,0.0) (line 184); schema default is [0,0,0] (aeroplaneschema.py:93-96) | m | ⚠️ wrong-source: the operating point's xyz_ref (the CG the caller asked for, and the value stability_service.py:328 later uses as x_cg) never reaches the file; defaults to the aeroplane record, i.e. the origin |
| `CDp` | solver-default | AvlGeometryFile.cdp default 0.0, never assigned; suppressed from output when zero (geometry.py:443,454) | - |  |
| `surface order / names` | passed-through | iteration over plane_schema.wings.items() (line 195) |  |  |
| `YDUPLICATE` | app-derived | 0.0 if wing.symmetric else None (line 162) |  |  |
| `Nchord` | app-derived | SpacingConfig.n_chord (default 12), raised to max(n_chord,16) when the surface has any CONTROL (spacing.py:96- | panels |  |
| `Cspace` | user-input | SpacingConfig.c_space, default 1.0 (cosine) |  |  |
| `Nspan` | app-derived | max(SpacingConfig.n_span (default 20), ceil(span/min_inter_section_gap)+2) (spacing.py:43-68,104) | panels |  |
| `Sspace` | app-derived | SpacingConfig.s_space (default 1.0), overwritten to -2.0 when _is_unswept(<5°) and no centreline break (spacin |  |  |
| `SECTION Xle/Yle/Zle` | passed-through | tuple(xsec.xyz_le) (line 107) | m |  |
| `SECTION Chord` | passed-through | xsec.chord (line 108) | m |  |
| `SECTION Ainc` | passed-through | xsec.twist (line 109) | deg |  |
| `airfoil (NACA / AFIL)` | app-derived | _build_airfoil_node: ^naca\s*(\d{4,5})$ → AvlNaca, else _resolve_airfoil_reference → AvlAfile, else AvlNaca('0 |  | ⚠️ silent substitution to NACA 0012 when the .dat cannot be resolved — logged at debug only, no DesignWarning (ADR 0020) |
| `CLAF` | app-derived | 1.0 + 0.77 * asb_airfoil.max_thickness(); silently 1.0 on any exception (lines 94-104) |  | ⚠️ undeclared fallback to 1.0 (no thickness correction) on airfoil-build failure |
| `CDCL (per section)` | app-derived | AvlCdcl.zeros() at build time (line 112), replaced by inject_cdcl unless non-zero |  |  |
| `CONTROL name` | app-derived | axes_for_xsec → control_axes_for_surface: single-axis keeps '[role]{ted.name}', dual-role emits '[role]{axis}_ |  | ⚠️ the AVL CONTROL name is not the raw TED name; any consumer that reconstructs f'[{role}]{ted.name}' misses dual-role surfaces (see elevator sites below) |
| `CONTROL gain` | passed-through | axis.gain ← ted.mix_gain_primary / mix_gain_secondary, default 1.0 (converters:410-411) |  |  |
| `CONTROL Xhinge` | passed-through | axis.hinge_point ← ted.rel_chord_root, else fallback cs.hinge_point, else 0.8 (converters:349-354) | chord fraction |  |
| `CONTROL hinge vector` | hardcoded | xyz_hvec=(0.0,0.0,0.0) (line 137) |  |  |
| `CONTROL SgnDup` | app-derived | +1 symmetric / -1 antisymmetric; dual-role forced to +1 primary, -1 secondary (control_surface_mixing.py:114,1 |  |  |
| `CONTROL duplication across sections` | app-derived | each axis is appended to section i and i+1 (lines 140-142) |  |  |
| `BODY blocks` | solver-default | AvlGeometryFile.bodies left empty (line 210-216) even though plane_schema.fuselages is built into the ASB airp |  | ⚠️ AVL sees a wings-only aircraft while the post-processing airplane has fuselages |

**Read back.** `repr(AvlGeometryFile) → the .avl text handed to AVLRunner.run(avl_file_content=...)`

**Consumed by.** `app/services/analysis_service.py:311,322` · `app/services/analysis_service.py:363-366` · `app/services/stability_service.py:311-316` · `app/services/avl_trim_service.py:92-94` · `app/services/analysis_service.py:1820-1831` · `app/services/analysis_service.py:1958-1964` · `app/services/elevator_authority_service.py:951`

### `app/services/avl_geometry_service.py:227` — `inject_cdcl`

Overwrites each zero CDCL block with a 3-point NeuralFoil polar before the file is handed to AVL.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `re (Reynolds)` | app-derived | compute_reynolds_number(velocity=op.velocity, chord=xsec.chord, altitude=op.altitude) = V·c/ν (neuralfoil_cdcl | - |  |
| `mach` | app-derived | avl_file.mach — always 0.0 from build_avl_geometry_file (line 263) | - | ⚠️ polar fitted at M=0 while the OPER keystroke runs the case at op.mach() |
| `airfoil` | passed-through | _build_asb_airfoil(xsec.airfoil) (line 261) |  |  |
| `alpha sweep / n_crit / xtr / model_size` | user-input | CdclConfig defaults: -10→16 deg step 1, model 'large', n_crit 9.0, xtr_upper=xtr_lower=1.0, include_360=False  |  |  |
| `surface↔wing pairing` | app-derived | positional zip of avl_file.surfaces and list(plane_schema.wings.values()); count mismatch only logs a warning  |  | ⚠️ silent partial injection on mismatch (ADR 0020) |
| `preserve-user rule` | app-derived | skip when section.cdcl is not zero (line 252) |  |  |

**Read back.** `mutates AvlSection.cdcl in place (CL1 CD1 CL2 CD2 CL3 CD3)`

**Consumed by.** `app/avl/geometry.py:214 (serialised into the .avl file)`

### `app/api/utils.py:57` — `_run_avl → AVLRunner.run`

Generic single-point AVL analysis behind analyse_aerodynamics (used by analyze_wing, analyze_airplane, stability summary).

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airplane` | app-derived | asb_airplane from aeroplane_schema_to_asb_airplane_async, with xyz_ref overwritten to operating_point.xyz_ref  |  | ⚠️ only used for s_ref/b_ref/c_ref post-processing and d-index ordering; its xyz_ref is inert for AVL |
| `op_point` | app-derived | _build_operating_point(): asb.OperatingPoint(velocity, alpha, beta, p, q, r, atmosphere=asb.Atmosphere(altitud |  |  |
| `xyz_ref` | user-input | operating_point.xyz_ref (utils.py:55) | m | ⚠️ consumed by nothing — see AVLRunner note |
| `avl_file_content` | app-derived | caller-supplied: get_user_avl_content(db,...) if a clean user-edited file exists, else repr(build_avl_geometry |  | ⚠️ in the user-edited branch Sref/Cref/Bref/Xref are entirely user-owned while _post_process_results dimensionalises with the ASB values — two authorities for the same reference set |
| `control_overrides` | solver-default | not passed; deflections reach AVL only through asb_airplane.with_control_deflections (utils.py:115) → cs.defle |  |  |
| `include_strip_forces` | solver-default | not passed (False) |  |  |
| `timeout` | solver-default | not passed → 30 s |  |  |
| `sweep guard` | app-derived | raises ValueError if alpha or beta is list/tuple/ndarray (utils.py:40-46) |  | ⚠️ velocity/p/q/r arrays are not guarded |

**Read back.** `AnalysisModel.from_avl_dict(result) — requires Bref,Cref,Sref,Xref,Yref,Zref,Xnp,Strips,Surfaces,Vortices,CL,CD,CY,CX,CZ,Cl,Cl',Cm,Cn,Cn',CDff,CDind,CDvis,CLff,CYff,e and the full derivative set`

**Consumed by.** `cad_designer/airplane/aircraft_topology/models/analysis_model.py:301-381` · `app/services/stability_service.py:322-337 (Xnp, Cma, Cnb, Clb, Cref → static margin, CG range; x_cg taken from operating_point.xyz_ref[0], stability_service.py:328)` · `app/services/analysis_service.py:322` · `app/services/analysis_service.py:365`

### `app/services/avl_trim_service.py:118` — `trim_with_avl → AVLRunner.run_trim`

Trims an operating point using AVL's native indirect constraints.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airplane` | app-derived | aeroplane_schema_to_asb_airplane_async(plane_schema); xyz_ref set to op.xyz_ref (lines 96-97) |  |  |
| `op_point` | passed-through | asb.OperatingPoint(velocity, alpha, beta, p, q, r, Atmosphere(altitude)) from request.operating_point (lines 9 |  |  |
| `xyz_ref` | user-input | op.xyz_ref (line 113) | m | ⚠️ inert; the trimmed moment reference is the file's Xref = plane_schema.xyz_ref, although the schema docstring states xyz_ref must be the CG for trim (aeroanalysisschema.py:243-246) |
| `timeout` | hardcoded | 60 (line 114) | s |  |
| `avl_file_content` | app-derived | get_user_avl_content(db, uuid) else build_avl_geometry_file(plane_schema, spacing_config)+inject_cdcl (lines 8 |  |  |
| `trim_constraints` | user-input | request.trim_constraints → '<a\|b\|r\|p\|y\|d{i}> <CL\|CY\|PM\|RM\|YM> <value>' (avl_strip_forces.py:205-230) |  | ⚠️ control-surface constraints resolve through get_control_surface_index_map (ASB traversal order), not the .avl file order |
| `control_overrides` | user-input | op.control_deflections (line 121) | deg | ⚠️ names absent from the ASB map are dropped without error (avl_strip_forces.py:251) |
| `spacing_config / cdcl_config` | user-input | op.spacing_config or SpacingConfig(); op.cdcl_config or CdclConfig() (lines 90-91) |  |  |
| `convergence settings` | solver-default | none passed — AVL's own Newton iteration limits/tolerances apply; convergence is inferred afterwards by `'CL'  |  | ⚠️ a non-converged-but-printed case is reported converged |

**Read back.** `trimmed_deflections (keys ∩ cs_map), trimmed_state (alpha,beta,mach), aero (CL,CD,CY,Cm,Cl,Cn,CDind,CDff,e,CLff,CYff), forces (L,D,Y,l_b,m_b,n_b), derivatives (CL_a,Cm_a,Cn_b,Clb,Cnr,Clr,Cnb,...), raw_results`

**Consumed by.** `app/services/avl_trim_service.py:39-57` · `app/services/trim_enrichment_service.py via compute_enrichment (lines 152-166)` · `app/mcp_server.py:1229-1239 (avl_trim_operating_point tool)`

### `app/services/analysis_service.py:1831` — `_run_avl_strip_forces → AVLRunner.run(include_strip_forces=True)`

AVL subprocess path for spanwise strip forces; feeds both the strip-force endpoint and the spanwise-loads/spar-sizing integrator.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airplane` | app-derived | aeroplane_schema_to_asb_airplane_async(plane_schema); xyz_ref ← resolved_op.xyz_ref (line 1866) |  |  |
| `op_point` | app-derived | asb.OperatingPoint from resolved_op (velocity, alpha, beta, p, q, r, Atmosphere(altitude)) (lines 1868-1877);  |  |  |
| `xyz_ref` | passed-through | resolved_op.xyz_ref (line 1828) | m | ⚠️ inert in the runner, yet echoed to the client as xyz_ref_m (line 1762) — the response claims a reference point AVL never used |
| `timeout` | hardcoded | 60 at both call sites (lines 1880, 2043) | s |  |
| `avl_file_content` | app-derived | get_user_avl_content else build_avl_geometry_file(plane_schema, spacing_config)+inject_cdcl (lines 1815-1822) |  |  |
| `control_overrides` | solver-default | NOT passed (line 1831) — deflections come only from cs.deflection on the ASB airplane, i.e. the geometry defau | deg | ⚠️ resolved_op.control_deflections (the trimmed state) never reaches AVL; the docstring at lines 1804-1807 claims AVL reads deflections from the geometry file, but AvlControl has no deflection field (geometry.py:75-79) — de |
| `include_strip_forces` | hardcoded | True (line 1831) → adds the 'fs' keystroke |  |  |
| `q (dynamic pressure, spanwise path)` | app-derived | 0.5 * atmosphere.density() * resolved_op.velocity**2 (analysis_service.py:2050-2051) — recomputed app-side, no | Pa |  |

**Read back.** `result['strip_forces'] per surface: surface_name, surface_number, n_chordwise, n_spanwise, surface_area, strips[j,Xle,Yle,Zle,Chord,Area,c_cl,ai,cl_norm,cl,cd,cdv,cm_c/4,cm_LE,C.P.x/c]` · `Sref, Cref, Bref, alpha, beta, mach for the response echo`

**Consumed by.** `app/services/analysis_service.py:1771-1790 (_strip_surfaces_from_result)` · `app/services/analysis_service.py:1737-1768 (_build_strip_forces_response — sref/cref/bref/alpha/beta/mach read back from AVL, velocity/altitude/xyz_ref from the app)` · `app/services/spanwise_loads.py:88-113 (compute_spanwise_loads)` · `app/api/v2/endpoints/aeroanalysis.py:449,599`

### `app/services/analysis_service.py:1964` — `analyze_wing_strip_forces → AVLRunner.run(include_strip_forces=True)`

Single-wing strip forces; same as above but the geometry is a wing-only schema and the user-edited file is deliberately bypassed.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airplane` | app-derived | asb airplane from the wing-only schema, then filtered: wings=[w for w in wings if w.name==wing_name]; fuselage |  | ⚠️ s_ref/b_ref/c_ref were computed by the converter BEFORE this filtering (converters:815-819) — they stay whatever the unfiltered schema produced; for a wing-only schema that is the same wing, but the coupling is implicit |
| `op_point` | passed-through | asb.OperatingPoint from operating_point (NOT resolved via operating_point_resolver here) (lines 1935-1944) |  | ⚠️ unlike the airplane-level path, no stored-OP resolution — operating_point_id is ignored on this route |
| `xyz_ref` | user-input | operating_point.xyz_ref (line 1961) |  | ⚠️ inert |
| `timeout` | hardcoded | 30 (line 1962) | s |  |
| `avl_file_content` | app-derived | always freshly built: build_avl_geometry_file(plane_schema, spacing_config)+inject_cdcl (lines 1955-1958) — ge |  | ⚠️ inconsistent with the airplane-level path, which prefers the user-edited file |
| `control_overrides` | solver-default | not passed |  |  |
| `cdcl_config / spacing_config` | user-input | operating_point.cdcl_config or CdclConfig(); .spacing_config or SpacingConfig() |  |  |

**Read back.** `same strip-force + reference keys as the airplane-level path`

**Consumed by.** `app/services/analysis_service.py:1968-1975` · `app/api/v2/endpoints/aeroanalysis.py:104-143`

### `app/services/elevator_authority_service.py:1046` — `_compute_forward_cg_limit_avl → AVLRunner.run (baseline)`

Baseline (zero-elevator) AVL run for the finite-difference Cm_δe used by the forward-CG limit.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airplane` | app-derived | aeroplane_schema_to_asb_airplane_async(plane_schema) (line 1003) |  |  |
| `op_point` | app-derived | asb.OperatingPoint(velocity=v_cruise*0.6, alpha=stall_alpha_deg) (lines 1032-1035) | m/s, deg | ⚠️ 0.6·v_cruise approach speed is an unsourced literal; no atmosphere passed → ASB sea-level default regardless of the aircraft's altitude; beta/p/q/r default to 0 |
| `v_cruise` | user-input | assumption 'v_cruise', silent default 15.0 m/s when absent (line 997) | m/s | ⚠️ undeclared default |
| `stall_alpha_deg` | user-input | assumption 'stall_alpha', silent default 12.0 deg (line 999) | deg | ⚠️ undeclared default |
| `xyz_ref` | app-derived | list(asb_airplane.xyz_ref) or [0,0,0] (line 1004) |  | ⚠️ inert in the runner; the file's Xref is plane_schema.xyz_ref |
| `timeout` | hardcoded | 60 (line 1042) | s |  |
| `avl_file_content` | app-derived | _build_avl_file_for_elevator(plane_schema) → build_avl_geometry_file with default SpacingConfig() (lines 948-9 |  | ⚠️ ignores any user-edited AVL file and any request-level spacing config |
| `control_overrides` | app-derived | {f'[{elevator_role}]{elevator_ted.name}': 0.0} (lines 1020, 1048) | deg | ⚠️ this name only matches SINGLE-axis surfaces; dual-role elevon/flaperon/ruddervator get '[role]{axis}_{wing_key}_{idx}' names (control_surface_mixing.py:113,123), so the override silently misses (build_control_deflection_ |
| `include_strip_forces` | solver-default | not passed |  |  |

**Read back.** `Cm (via _extract_cm, falls back to result['Cmq'] then 0.0 — elevator_authority_service.py:901-907)`

**Consumed by.** `app/services/elevator_authority_service.py:1050,1060-1073` · `app/api/v2/endpoints/aeroplane/forward_cg.py:99`

### `app/services/elevator_authority_service.py:1053` — `_compute_forward_cg_limit_avl → AVLRunner.run (deflected)`

Second AVL run with TE-UP elevator deflection; the difference gives Cm_δe.

| input | origin | passed as | unit | risk |
|---|---|---|---|---|
| `airplane / op_point / xyz_ref / timeout / avl_file_content` | app-derived | identical objects reused from the baseline run (same runner instance, lines 1038-1043) |  |  |
| `control_overrides` | app-derived | {elevator_surface_name: delta_e_neg_deg} where delta_e_neg_deg = -abs(_delta_e_max_rad(ted.negative_deflection | deg | ⚠️ same name-matching risk as the baseline; when it misses, both runs are identical → cm_delta_e_raw = 0 and the code only logs a warning (lines 1061-1067) before continuing with cm_delta_e = 0 |
| `finite-difference step` | app-derived | (cm_deflected - cm_baseline) / delta_e_max_rad — deflection commanded in DEGREES, divided by RADIANS (lines 10 | deg vs rad | ⚠️ unit asymmetry between the commanded keystroke (deg) and the divisor (rad) — deliberate only if Cm_δe is wanted per radian; nothing at the call site states it |

**Read back.** `Cm at the deflected state`

**Consumed by.** `app/services/elevator_authority_service.py:1057-1059` · `app/services/elevator_authority_service.py:1085-1120 (conditioning / infeasibility guards)`

