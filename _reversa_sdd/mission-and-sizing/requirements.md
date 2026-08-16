# mission-and-sizing

> Module-level specification. Focuses on WHAT the module does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Cluster C / §Module:
> mission-and-sizing, `_reversa_sdd/data-dictionary.md` §Module:
> mission-and-sizing, `_reversa_sdd/domain.md` §2.4–2.5,
> `_reversa_sdd/state-machines.md` §5, ADR 0004, ADR 0010, ADR 0011, ADR 0012.

## Overview

`mission-and-sizing` is the **design-intent layer**: what the aircraft is *for*
(mission objectives and presets), what the designer *assumes* (design
assumptions and the computation config), what loadings it must tolerate (loading
scenarios and the CG envelope), what it must survive (flight envelope / V-n and
gust), and the classical sizing surfaces built on top (matching chart, field
lengths, the 15-target operating-point sweep, mission KPIs). 🟢

Every number it publishes either **is** a design choice or **reads** the
single-source aero context (BR-14). It does not run solvers itself, with the one
exception of the operating-point generator's trim solve. 🟢

## Responsibilities

- Own `design_assumptions` — the ESTIMATE/CALCULATED duality, the divergence
  ladder, the seven design-choice parameters, and the event routing on change.
  🟢
- Own `aircraft_computation_config` — per-aircraft sweep tuning. 🟢
- Own `mission_objectives` (one row per aeroplane) and the seeded
  `mission_presets` library, and apply a preset's suggested estimates. 🟢
- Own the global `rc_flight_profiles` library and its assignment to an
  aeroplane. 🟢
- Generate the 15-target operating-point set from the profile goals and the
  reference stall speeds, with capability gating and a two-stage trim solve. 🟢
- Compute the V-n manoeuvre envelope, the Pratt-Walker gust envelope and six
  performance KPIs, and persist them. 🟢
- Compute loading scenarios, the CG envelope and the SM classification. 🟢
- Compute the landing field length and the T/W-vs-W/S matching chart. 🟢
- Compute the 7-axis mission KPI spider against the preset polygon. 🟢

**Explicitly NOT this module's responsibility:** running the solvers and owning
the aero context pipeline (→ `aero-analysis`, although
`assumption_compute_service` is documented by both), the AVL stack
(→ `avl-integration`), mass aggregation and the component tree
(→ `mass-and-balance`), and the geometry itself (→ `wing-design`,
`fuselage-design`).

## Business Rules

> `BR-14`…`BR-28` are global ids reused verbatim from
> [`../domain.md`](../domain.md). `BR-MS*` are module-local.

### Design assumptions

- **BR-24 — Every parameter has an estimate and a calculation (ADR 0010).** 🟢

  ```
  effective_value = calculated_value  if active_source == "CALCULATED" and it exists
                    else estimate_value
  divergence_pct  = |estimate − calculated| / |calculated| · 100
  divergence_level: < 5 none · < 15 info · ≤ 30 warning · else alert
  ```

- **BR-25 — Auto-switch happens once.** 🟢
  `update_calculated_value(..., auto_switch_source=True)` flips `active_source`
  to `CALCULATED` **only** on the first calculated value
  (`row.calculated_value is None`), only from `ESTIMATE`, and never for a design
  choice. Afterwards the user's manual choice sticks.
- **BR-26 — Design choices can never be calculated.** 🟢 Seven
  `DESIGN_CHOICE_PARAMS` never receive a `calculated_value` and can never be
  switched to `CALCULATED`: `target_static_margin`, `g_limit`,
  `battery_capacity_wh`, `battery_specific_energy_wh_per_kg`,
  `propulsion_eta_motor`, `propulsion_eta_esc`, `motor_continuous_power_w`.
- **BR-27 — Events fire only when the *effective* value changes.** 🟢
  `update_assumption` publishes `AssumptionChanged` (and marks OPs dirty for
  `mass`/`cg_x`) **only** when `active_source == "ESTIMATE"` — editing an
  estimate while the calculated value is active changes nothing effective, so the
  retrim chain must not fire. `switch_source` **always** fires, and additionally
  schedules a recompute for every parameter **except `cg_x`**.
- **BR-83 — Recompute triggers exclude their own outputs.** 🟢
  `_RECOMPUTE_TRIGGERING_PARAMS = {target_static_margin, mass}`; `cg_x`, `cd0`
  and `cl_max` are excluded to break the
  `recompute → AssumptionChanged(cg_x) → recompute` loop.
- **BR-28 — CG is a top-down design target, not a bottom-up sum (gh-465,
  ADR 0011).** 🟢 `cg_x` is *CG_aero* — the CG that stability demands,
  `x_np − SM·MAC` — written by `assumption_compute_service`. The aggregated CG
  from mass items (`CG_agg`) is **never** written back into `cg_x`; it is exposed
  for comparison only, with a 1 cm tolerance verdict.
- **BR-MS1 — Seeding is idempotent and unconditional.** 🟢 `seed_defaults` also
  seeds `aircraft_computation_config`; `recompute_assumptions` calls it on every
  run, because wings can be created before the user ever opens the Assumptions
  tab.
- **BR-MS2 — 17 parameters, 15 of them catalogued with defaults.** 🟢
  See [`contracts.md`](contracts.md) for the full table.
  🟡 `min_static_margin` / `max_static_margin` are **read** by
  `stability_service` but are not in the catalogue and are never seeded.

### Mission objectives and presets

- **BR-MS3 — One `mission_objectives` row per aeroplane.** 🟢 Unique FK. It
  holds seven performance targets plus the field-performance inputs migrated out
  of assumptions (`available_runway_m`, `runway_type`, `t_static_N`,
  `takeoff_mode`) and the optional gh-477 landing inputs (`landing_surface`,
  `landing_safety_factor`, `available_field_length_m`).
- **BR-MS4 — Changing `mission_type` rewrites estimates, never calculations.** 🟢
  `upsert_mission_objective` → `_apply_preset_estimates` writes the preset's
  `suggested_estimates` (`g_limit`, `target_static_margin`, `cl_max`,
  `power_to_weight`, `prop_efficiency`) into `design_assumptions.estimate_value`
  **only**; `calculated_value`, `calculated_source` and `active_source` stay
  owned by `assumption_compute_service`.
  🟢 **An unknown `mission_type` fails visibly** (`Q-MS-10`/`P-WARN-0`) and `mission_type` gains a real reference constraint to `mission_presets.id` (`Q-CC-7`/`Q-CC-9`). Previously a silent no-op:
- **BR-MS5 — Nine seeded presets, seven KPI axes.** 🟢 `SEED_PRESETS` (idempotent
  `seed_mission_presets`): `trainer`, `sport`, `sailplane`, `wing_racer`,
  `acro_3d`, `stol_bush`, `slope_soarer`, `motor_glider`, `flying_wing`. Each
  carries a `target_polygon` (0–1 per axis), the `axis_ranges` used to normalise
  real values onto that scale, and the `suggested_estimates`. Axes:
  `stall_safety`, `glide`, `climb`, `cruise`, `maneuver`, `wing_loading`,
  `field_friendliness`.
  🟢 `mission_type` gains a real reference constraint (`Q-CC-7`, `Q-CC-9`). Previously `mission_presets.id` was a free-text `String` PK with no FK from
  `mission_objectives.mission_type`.

### Flight profiles

- **BR-MS6 — Profiles are a global library, assigned per aircraft.** 🟢
  `rc_flight_profiles` has a unique `name`; `aeroplanes.flight_profile_id`
  assigns one. Four JSON blobs: `environment` (`altitude_m`, `wind_mps`),
  `goals`, `handling`, `constraints`. Deleting a profile still referenced by an
  aircraft returns **409**.
- **BR-MS7 — "No profile assigned" is load-bearing.** 🟢
  `_load_effective_flight_profile` returns `(profile_dict, source_profile_id)`;
  with no assignment it returns `_default_profile()` and
  `source_profile_id = None`. That `None` makes
  `_load_flight_profile_speeds` report `user_set_cruise = False`, so
  `recompute_assumptions` **replaces** the cruise speed with `V_md` (best L/D =
  best range for a prop aircraft) and flags `v_cruise_auto = True`;
  `_resolve_cruise_speed_with_md_fallback` does the same in the OP generator.
- **BR-MS8 — `v_max` fallback.** 🟢 With no `max_level_speed_mps` in the profile:
  `max(1.35 · V_cruise, V_cruise + 8)`.

### Operating-point generation

- **BR-MS9 — 15 targets, derived from the profile goals and the reference stall
  speeds.** 🟢 Full table in [`operating-point-sweep/requirements.md`](operating-point-sweep/requirements.md).
- **BR-23 — Stall speeds come from physics, not from 0.95/0.90.** 🟢
  `_estimate_reference_speeds` prefers `v_s1_mps` / `v_s_to_mps` / `v_s0_mps`
  from the cached context (`provenance="polar"`); with only the legacy
  `v_stall_mps` it uses the clean value for **all three** configurations — the
  historical 0.95 / 0.90 multipliers are **deliberately not applied** (audit
  §5.5). With no context at all it falls back to
  `max(3.0, V_cruise / min_speed_margin_vs_clean)` with
  `provenance="cold_start"`, and `_stamp_stale_no_polar` appends a
  `STALE_NO_POLAR` warning to **every** target. Floors: `vs_clean ≥ 3.0`,
  `vs_to ≥ 2.5`, `vs_ldg ≥ 2.0`.
- **BR-22 — Flap targets clip to the real hinge limit (gh-527/gh-536).** 🟢
  `_clip_flap_to_ted_limit` clips `flap_deflection_deg` to the **most
  restrictive** flap-role TED (`min` across all of them, so the smallest surface
  never over-deflects) and appends `FLAP_DEFLECTION_CLIPPED`. With no flap-role
  TED **no limit is manufactured** — the target passes through and the trim
  solver no-ops the missing surface. AVL has no internal hinge clamp and
  NeuralFoil silently extrapolates τ(x_h/c) past its training range, so an
  unclipped target produces over-attached flow with no warning.
- **BR-21 — Capability gating skips, never fails.** 🟢
  `_detect_control_capabilities` walks the ASB airplane's `[role]` tags into
  `{has_pitch_control, has_roll_control, has_yaw_control, has_flap,
  available_controls}` using
  `PITCH_ROLES = {elevator, stabilator, elevon, ruddervator}`,
  `ROLL_ROLES = {aileron, elevon, flaperon}`,
  `YAW_ROLES = {rudder, ruddervator}`, `FLAP_ROLES = {flap}`. Targets are
  **skipped** (not failed) when unmet: `turn_*` needs roll **or** yaw,
  `dutch_role_start` needs yaw, `stall_with_flaps` needs a flap.
- **BR-MS10 — Two-stage trim, `trim_score < 0.35` ⇒ TRIMMED.** 🟢

  ```
  stage 1  asb.Opti (IPOPT), max_iter = 120, max_runtime = 0.35 s,
           behavior_on_failure = "return_last"
           variables: α ∈ [−8°, max_alpha_deg]; pitch δ ∈ [−25, 25];
                      (turn) roll δ ∈ [−20, 20]; (turn/dutch) yaw δ ∈ [−25, 25]
           objective: 50·Cm² + 3·CY² [+ 15·(CL − CL_target)²]
                      [+ 2·Cl² + 2·Cn² for turns] + 0.001·Σδ²
  stage 2  if score > 0.35: grid search over
           velocities × α = linspace(−4°, 20°, 13) × β candidates,
           velocity factors [1.0, 1.05, 1.10, 1.15]
                            (descending for max_level_speed)
           → the grid fallback updates BOTH α and the velocity (gh-528)

  trim_score = |Cm| + 0.5·|CY| [+ 0.3·|CL − CL_target|]
  CL_target  = m·g·n / (q·S_ref)
  status     = TRIMMED if score < 0.35 else NOT_TRIMMED
               LIMIT_REACHED when |α| > max_alpha_deg or |β| > max_beta_deg
  ```

- **BR-MS11 — The solver path lives on `trim_method`, never in
  `trim_residuals` (gh-627).** 🟢 `trim_method ∈ {"opti", "grid_fallback"}`;
  `trim_residuals` is typed `dict[str, float]` and Pydantic-rejects strings — a
  `best_residuals["solver_path"] = "opti"` line once broke every OP enrichment.
- **BR-MS12 — Turn feasibility is checked before trusting a solution.** 🟢 A
  `bank_deg` target derives `(p, q, r)` from `turn_kinematics`;
  `_apply_turn_feasibility` marks the point `LIMIT_REACHED` with
  `STALL_IN_TURN` when `V < V_s1 · sqrt(n)`, `n = 1/cos φ` — otherwise the
  trimmer would happily return a solution at the wrong load factor.
- **BR-MS13 — Parallelism uses processes, not threads (gh-867).** 🟢 The
  CasADi/IPOPT solve does **not** release the GIL (a thread pool benchmarked at
  0.35–0.89×), so the **streaming** path uses a bounded `ProcessPoolExecutor`
  (spawn context, `max_workers = max(1, min(4, cpu − 1))`) with BLAS pinned to
  one thread per worker
  (`OMP/OPENBLAS/MKL/VECLIB/NUMEXPR_NUM_THREADS=1`, applied both to the parent
  env at spawn and in the initializer, then restored) → ≈ 2.9× at 4 workers.
  Workers receive a picklable `_WorkerSolveCtx` (the `asb.Airplane` pickles
  cleanly; the SQLAlchemy model does not, so only `total_mass_kg` is carried via
  `_AircraftMassOnly`) and **never touch the database**. The main thread owns
  persistence. The **non-streaming** batch path stays **sequential on purpose**
  so its contract and its mocks are unchanged.
- **BR-MS14 — The SSE contract (gh-865).** 🟢 `targets` → one `op` per solved
  point → `done`, with `skip` for capability-filtered targets and `error` for
  setup failures. Each OP is committed as soon as it is solved, so a dropped
  connection still leaves a valid partial set.

### Flight envelope

- **BR-MS15 — V-n manoeuvre envelope, 60 points.** 🟢

  ```
  V_stall = sqrt(2·W / (ρ·S·CL_max));   V_dive = 1.4·V_max;   CL_min = −0.8·CL_max
  n⁺(V) = min(q·S·CL_max / W,  g_limit)
  n⁻(V) = max(q·S·CL_min / W, −0.4·g_limit)
  ```

- **BR-MS16 — Pratt-Walker gust envelope with the *mean geometric* chord.** 🟢
  (NACA TN 2964; `K_g` per FAR-25.341(a)(2) / CS-VLA.333)

  ```
  c̄    = S_ref / b_ref            # MEAN GEOMETRIC chord, NOT the MAC
  μ_g  = 2·(W/S) / (ρ · c̄ · CL_α · g)
  K_g  = 0.88·μ_g / (5.3 + μ_g)
  Δn   = ½·ρ·V·CL_α·U_gust·K_g / (W/S)
  n±   = 1 ± Δn                    over 60 points from V_stall to V_dive
  U_gust: 15.24 m/s (50 ft/s) at V ≤ V_C = V_D/1.4,
          linearly tapered to 7.62 m/s (25 ft/s) at V_D
  CL_α : context["cl_alpha_per_rad"] → else Helmbold-Diederich 2π·AR/(AR+2)
  ```

  Explicitly **not** the thin-airfoil `2π` limit, which overestimates `CL_α` at
  AR = 6 by ≈ 39 % and inflates gust loads.
- **BR-MS17 — Two structured gust warnings reach the API, not just the log.** 🟢
  `GustCriticalWarning` at the first `V` where `1+Δn > g_limit` (or
  `1−Δn < −0.4·g_limit`) — the structure is **gust-sized, not
  manoeuvre-sized**; `GustValidityWarning` when `μ_g ∉ [3, 200]`, which is the
  **normal** case for low-W/S RC models (gh-497), so their gust loads may be
  optimistic.
- **BR-MS18 — Six KPIs with an explicit confidence ladder.** 🟢

  ```
  best_ld_speed / min_sink_speed:
    1. a TRIMMED operating-point marker            confidence "trimmed"
    2. ctx["v_md_mps"] / ctx["v_min_sink_mps"]     confidence "computed"
    3. 1.4·V_s / 1.2·V_s                           confidence "estimated"  ← cold start only
  stall_speed, max_speed, dive_speed (= 1.4·V_max), max_load_factor → "limit"
  ```

  The heuristic tier is documented as wrong by up to 15 % for high-AR airframes
  (gh-475 audit §4.1) and is kept **only** for the pre-polar case.
- 🟢 **Persist both `n_target` and `cl_trimmed`; the marker is placed at the real load factor** (`Q-MS-6`, expert consensus endorsed by the maintainer). In a steady coordinated turn `n = 1/cos φ` exactly, so plotting `turn_60` at n = 1.0 is a **factor-of-two error in the plotted quantity**, not an approximation — and the generator already computes `n_target` before discarding it. Previously BR-MS19: all markers at `load_factor = 1.0`, because the
  stored OP carries no CL — so turn operating points plot on the 1-g line.

### Loading, CG and field length

- **BR-MS20 — The SM classification ladder (Scholz §4.2).** 🟢
  (`loading_scenario_service.py:51-53`)

  ```
  sm < 0.02          → "error"  (Phugoid divergent)
  sm < target_sm     → "warn"
  sm ≤ 0.20          → "ok"
  sm ≤ 0.30          → "warn"   (heavy nose, trim drag)
  else               → "error"  (elevator authority)
  ```

- **BR-MS21 — The stability envelope's forward limit is a stub that gets
  overridden.** 🟢

  ```
  compute_stability_envelope(x_np, mac, target_sm):
      cg_stability_aft_m = x_np − target_sm · MAC
      cg_stability_fwd_m = x_np − 0.30 · MAC          ← conservative STUB
  ```

  `recompute_assumptions` overrides the forward limit with
  `elevator_authority_service.compute_forward_cg_limit` (gh-500); on failure the
  stub is kept, and the full `forward_cg_result` (confidence, warnings) is stored
  either way. A `ValueError` mentioning `x_np=None` / `mac=None` is demoted to
  **INFO** — the documented cold-start chicken-and-egg (gh-685), not a bug.
- **BR-MS22 — CG enrichment is additive.** 🟢
  `enrich_context_with_cg_envelope` adds `cg_forward_m`, `cg_aft_m`,
  `sm_at_fwd = (x_np − cg_fwd)/MAC`, `sm_at_aft`, `cg_stability_fwd_m`,
  `cg_stability_aft_m` **without disturbing `cg_agg_m`**. When `x_np`/`MAC` are
  absent the SM values are stored as `None` rather than as deceptive stubs.
- **BR-MS23 — Four scenario override types.** 🟢 `compute_scenario_cg` supports
  toggles (`enabled=False` removes the component), mass overrides, position
  overrides and additive adhoc items, over a per-component list — falling back to
  a `base_mass_kg / base_cg_x` aggregation for pre-migration aeroplanes.
- **BR-MS24 — Landing field length by energy balance (gh-477).** 🟢

  ```
  V_S0     = sqrt(2·m·g / (ρ·S·CL_max_landing))
  V_TD     = 1.15 · V_S0                             # RC rule of thumb
  s_ground = V_TD² / (2·g·μ_eff)                     # energy balance; mass cancels
  L_landing = safety · (15 m flare + s_ground)
  net_recovery → s_ground = 0 (catch/arrester); L collapses to the padded flare

  LANDING_SURFACE_MU = grass_short 0.15 · grass_long 0.22 · hard_paved 0.07
                       soft_soil 0.30 · belly_grass 0.40 · net_recovery 0.0
  defaults: surface grass_short, safety 1.5 (rejected below 1.0)
  ```

  The result is compared against `available_field_length_m` into a **tri-state**
  `landing_field_sufficient` (`True`/`False`/`None`) so the UI can render
  green/red/neutral. Provenance note in code: these μ values come from
  operational RC/UAV practice (Raymer ch. 17 / Roskam P.7 territory), **not**
  from Anderson.

### Matching chart

- **BR-MS25 — The Loftin/Roskam constants are imported, never re-declared.** 🟢
  `_K_TO_50FT = 1.66`, `_K_LDG_50FT = 2.73`, `_K_LDG_HARD = 0.5847`,
  `_C_TO = 1.21` come from `field_length_service` explicitly to prevent drift.
- **BR-MS26 — The classical constraint set (Loftin / Scholz §5.2–5.4).** 🟢 over
  `W/S ∈ [10, 1500] N/m²` in 200 steps, with `T/W = T_static_SL / W_MTOW`:

  ```
  takeoff (line)      T/W = C_TO·K_TO_50FT·(W/S) / (ρ·g·CL_max_TO·s_TO_50ft)
                      s_runway = 0 → 0  (hand launch: no constraint)
  landing (vertical)  W/S_max = s_LDG_50ft·ρ·CL_max_LDG / (K_LDG_HARD·K_LDG_50FT)
  cruise  (line)      T/W = q·CD0/(W/S) + (W/S)·k/q          k = 1/(π·e·AR)
  climb   (line)      T/W = sin γ + [q·CD0/(W/S) + (W/S)·k/q]   (clean polar)
  stall   (vertical)  W/S_max = ½·ρ·V_s_target²·CL_max_clean    (CLEAN, not landing)
  V_md                = sqrt(2·(W/S) / (ρ·sqrt(CD0/k)))
  ```

- **BR-MS27 — Five RC-additive constraints with a per-profile applicability
  table (gh-613 Phase B).** 🟢 So a sailplane is not evaluated against a
  takeoff-field constraint. Table and formulas in
  [`design.md`](design.md) §Matching chart.
- **BR-MS28 — Feasibility tolerances.** 🟢 A line constraint binds within **3 %**
  in T/W; a vertical constraint within **5 %** in W/S.
- **BR-17 — `DEFAULT_E_OSWALD = 0.8` should raise a design warning (gh-956,
  ADR 0012).** 🟢 The constant exists, but the module documents that consumers
  should surface a **design warning** rather than silently using it.
- **BR-MS29 — Log-forging safety (Sonar S5145).** 🟢 The user-controlled
  `flight_profile` string is never logged directly — `_sanitize_profile_for_log`
  maps it through the constant `_LOG_PROFILE_LABELS` table.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Seed 15 catalogued assumptions + the computation config idempotently | Must | A second seed creates no duplicates |
| RF-02 | Compute `effective_value`, `divergence_pct` and the divergence level | Must | 12 % divergence → `info`; 31 % → `alert` |
| RF-03 | Auto-switch to CALCULATED on the **first** calculated value only | Must | A second calculation does not override a manual switch back to ESTIMATE |
| RF-04 | Refuse a calculated value or a switch for a design-choice parameter | Must | `PATCH …/g_limit/source` → 422 |
| RF-05 | Publish `AssumptionChanged` only when the effective value changes | Must | Editing an estimate under an active CALCULATED fires nothing |
| RF-06 | Schedule a recompute for every parameter except `cg_x` on `switch_source` | Must | Switching `cg_x` schedules no recompute |
| RF-07 | Read and update the per-aircraft computation config | Should | `PUT …/computation-config` partial payload merges |
| RF-08 | Upsert one `mission_objectives` row per aeroplane | Must | A second `PUT` updates rather than inserts |
| RF-09 | Apply a preset's suggested estimates to `estimate_value` only | Must | `calculated_value` and `active_source` are untouched |
| RF-10 | List the nine seeded presets | Must | `GET /mission-presets` returns 9 |
| RF-11 | Compute the 7-axis mission KPI set against the preset polygon | Should | Each axis is normalised to 0–1 through `axis_ranges` |
| RF-12 | CRUD the global flight-profile library | Must | A duplicate `name` is rejected |
| RF-13 | Assign and detach a profile per aeroplane | Must | Deleting an assigned profile → **409** |
| RF-14 | Substitute `V_md` for the cruise speed when no profile is assigned | Must | `v_cruise_auto` is `true` and `v_cruise_mps == v_md_mps` |
| RF-15 | Generate 15 operating-point targets from the profile and stall speeds | Must | The set matches the target table exactly |
| RF-16 | Take stall speeds from the polar, without the 0.95/0.90 multipliers | Must | `v_s_to` equals the context value, not `0.95 · v_s1` |
| RF-17 | Stamp `STALE_NO_POLAR` on every target when there is no context | Must | Cold start: all 15 targets carry the warning |
| RF-18 | Clip a flap target to the most restrictive flap TED | Must | Two flaps at 25° and 30° clip to 25° with `FLAP_DEFLECTION_CLIPPED` |
| RF-19 | Manufacture no flap limit when no flap TED exists | Must | The target passes through unclipped |
| RF-20 | Skip a target whose control capability is unmet | Must | No roll and no yaw → the three turn targets are skipped, not failed |
| RF-21 | Solve each target with `asb.Opti`, falling back to a grid search | Must | `trim_method` is `"opti"` or `"grid_fallback"` |
| RF-22 | Update **both** α and velocity in the grid fallback | Must | gh-528: the fallback is not α-only |
| RF-23 | Mark `LIMIT_REACHED` on an α/β bound or a stall in a turn | Must | `V < V_s1·√n` → `STALL_IN_TURN` |
| RF-24 | Keep `trim_residuals` numeric-only | Must | A string fails validation (gh-627) |
| RF-25 | Persist one OP row per solved point plus one point-set row | Must | `xyz_ref = [design_cg_x, 0, 0]` on every row |
| RF-26 | Stream generation over SSE, committing each point as it is solved | Should | A dropped connection leaves a valid partial set |
| RF-27 | Parallelise the streaming path with processes, not threads | Should | ≈ 2.9× at 4 workers; workers never touch the DB |
| RF-28 | Keep the non-streaming batch path sequential | Must | Its contract and mocks are unchanged |
| RF-29 | Compute the V-n manoeuvre envelope over 60 points | Must | `n⁺` is capped at `g_limit`; `n⁻` at `−0.4·g_limit` |
| RF-30 | Compute the Pratt-Walker gust envelope with the mean geometric chord | Must | `c̄ = S_ref/b_ref`, **not** the MAC |
| RF-31 | Prefer the context `CL_α`, else Helmbold-Diederich | Must | The thin-airfoil `2π` is never used |
| RF-32 | Emit `GustCriticalWarning` and `GustValidityWarning` to the API | Must | A low-W/S RC model reports `μ_g < 3` as a structured warning |
| RF-33 | Return exactly six KPIs with a confidence label | Must | Cold start yields `estimated`; with a context, `computed`; with a trimmed OP, `trimmed` |
| RF-34 | Upsert one `flight_envelopes` row with an assumptions snapshot | Must | `{mass, cl_max, g_limit}` at compute time |
| RF-35 | Classify the static margin on the Scholz ladder | Must | `sm = 0.015` → `error`; `0.25` → `warn` |
| RF-36 | Compute the stability envelope, overriding the forward stub | Must | On elevator-authority success the forward limit is not `0.30·MAC` |
| RF-37 | Support four scenario override types | Must | A toggle removes the component from the aggregation |
| RF-38 | Enrich the context additively without disturbing `cg_agg_m` | Must | `cg_agg_m` is byte-identical before and after |
| RF-39 | Compute the landing field length and the tri-state sufficiency | Must | No `available_field_length_m` → `null`, not `false` |
| RF-40 | Compute the matching chart over `W/S ∈ [10, 1500]` in 200 steps | Must | Both line and vertical constraints are returned |
| RF-41 | Apply only the profile-applicable constraints | Must | A sailplane is evaluated against `stall` only |
| RF-42 | Import the Loftin/Roskam constants from `field_length_service` | Must | They are declared in exactly one module |
| RF-43 | Report feasibility within 3 % (line) / 5 % (vertical) | Should | A constraint 2 % away binds |
| RF-44 | Never log the raw `flight_profile` string | Must | Only `_LOG_PROFILE_LABELS` values appear in logs |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Performance | OP generation parallelises with **processes** because CasADi/IPOPT does not release the GIL; a thread pool measured 0.35–0.89× | gh-867, `operating_point_generator_service.py:1188-1252` | 🟢 |
| Performance | Workers pin BLAS to one thread each, preventing oversubscription | same | 🟢 |
| Performance | The Re-banded table re-bins existing samples — no extra solver calls | `polar_re_table_service` (gh-493) | 🟢 |
| Performance | Recompute is debounced (`debounce_seconds = 2.0`) | `aircraft_computation_config` | 🟢 |
| Scalability | `max_workers = max(1, min(4, cpu − 1))` bounds the pool | gh-867 | 🟢 |
| Correctness | Loftin/Roskam constants are imported from one module to prevent drift | `matching_chart_service` | 🟢 |
| Correctness | The gust chord is the **mean geometric** chord, not the MAC | `flight_envelope_service` | 🟢 |
| Correctness | `CL_α` uses Helmbold-Diederich rather than the thin-airfoil `2π` (39 % error at AR 6) | same | 🟢 |
| Correctness | Flap targets clip to the real hinge limit, because neither AVL nor NeuralFoil clamps | gh-527/gh-536 | 🟢 |
| Correctness | `trim_residuals` is float-typed so the solver path cannot leak into it | gh-627 | 🟢 |
| Robustness | Capability gating **skips** rather than failing the whole generation | BR-21 | 🟢 |
| Robustness | Each SSE point is committed as it is solved | gh-865 | 🟢 |
| Robustness | The cold-start `x_np=None` `ValueError` is demoted to INFO | gh-685 | 🟢 |
| Security | The user-controlled profile string is never logged directly (Sonar S5145) | `_sanitize_profile_for_log` | 🟢 |
| Isolation | Generation workers never touch the database; only `total_mass_kg` crosses the process boundary | `_WorkerSolveCtx`, `_AircraftMassOnly` | 🟢 |
| Traceability | Every generated OP carries its provenance (`polar` / `cold_start`) and warnings | `_stamp_stale_no_polar` | 🟢 |
| Auditability | `flight_envelopes.assumptions_snapshot` records the inputs at compute time | table column | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Design assumptions

  Scenario: The effective value follows the active source
    Given an assumption with estimate 1.5 and calculated 1.8
    When active_source is CALCULATED
    Then the effective value is 1.8
    And the divergence is about 16.7 percent with level "warning"

  Scenario: Auto-switch happens once
    Given a parameter with no calculated value
    When the first calculated value arrives
    Then active_source becomes CALCULATED
    But after the user switches back to ESTIMATE
    And a second calculated value arrives
    Then active_source stays ESTIMATE

  Scenario: A design choice can never be calculated
    When I switch g_limit to CALCULATED
    Then the response status is 422

  Scenario: An estimate edit under an active calculation is silent
    Given mass with active_source CALCULATED
    When I update its estimate
    Then no AssumptionChanged is published
    And no operating point becomes DIRTY

Feature: Mission presets

  Scenario: Changing the mission rewrites estimates only
    Given an aircraft with calculated cl_max 1.32 active
    When I set mission_type to "sailplane"
    Then the cl_max estimate becomes the preset's suggested value
    And the calculated value and active_source are unchanged

  Scenario: An unknown mission type does nothing
    When I set mission_type to "spaceplane"
    Then no estimate changes
    And no error is returned
    # 🟢 rejects unknown mission_type (Q-MS-10 / P-WARN-0)

Feature: Flight profiles

  Scenario: No profile means the cruise speed is best glide
    Given an aeroplane with no flight profile assigned
    When the context is computed
    Then v_cruise_auto is true
    And v_cruise_mps equals v_md_mps

  Scenario: An assigned profile cannot be deleted
    Given a profile assigned to an aircraft
    When I delete the profile
    Then the response status is 409

Feature: Operating-point generation

  Scenario: Fifteen targets from the profile
    Given a default flight profile and a full control set
    When the default point set is generated
    Then 15 targets are produced with the documented velocities

  Scenario: Stall speeds come from the polar
    Given a context with v_s1 12.0, v_s_to 11.0 and v_s0 10.0
    Then the takeoff target uses 11.0, not 0.95 times 12.0

  Scenario: Cold start stamps every target
    Given no computation context
    Then every generated operating point carries STALE_NO_POLAR
    And the provenance is "cold_start"

  Scenario: Flaps clip to the most restrictive surface
    Given two flap TEDs limited to 25 and 30 degrees
    When a landing target requests 30 degrees
    Then the target is clipped to 25
    And FLAP_DEFLECTION_CLIPPED is appended

  Scenario: No flap TED means no manufactured limit
    Given an aircraft with no flap-role TED
    Then the flap target passes through unclipped
    And the trim solver no-ops the missing surface

  Scenario: Missing capabilities skip, not fail
    Given an aircraft with neither roll nor yaw control
    Then the three turn targets and the dutch-roll target are skipped
    And the remaining targets are generated normally

  Scenario: The grid fallback moves velocity too
    Given a target whose Opti solve scores above 0.35
    When the grid fallback runs
    Then both alpha and the velocity are updated
    And trim_method is "grid_fallback"

  Scenario: A stall in a turn is caught
    Given a 60 degree bank target whose velocity is below V_s1 times sqrt(2)
    Then the point is LIMIT_REACHED with STALL_IN_TURN

  Scenario: The solver path never enters the residuals
    Given a completed trim
    Then trim_method carries the path
    And trim_residuals contains only floats

Feature: Flight envelope

  Scenario: The manoeuvre envelope is capped
    Given g_limit 3.0
    Then no positive load factor exceeds 3.0
    And no negative load factor is below -1.2

  Scenario: The gust chord is geometric, not the MAC
    Given S_ref 0.30 and b_ref 2.0
    Then the gust calculation uses a chord of 0.15

  Scenario: A low wing loading warns about validity
    Given an RC model whose mu_g is 2.1
    Then a GustValidityWarning is returned to the API
    And it states that the gust loads may be optimistic

  Scenario: A gust-sized structure is flagged
    Given a velocity where 1 plus delta-n exceeds g_limit
    Then a GustCriticalWarning names that velocity

  Scenario: KPI confidence ladder
    Given no context and no trimmed operating point
    Then best_ld_speed has confidence "estimated"
    And with a context it becomes "computed"
    And with a trimmed marker it becomes "trimmed"

Feature: Loading and CG

  Scenario: The SM ladder
    Given a static margin of 0.015
    Then the classification is "error"
    And 0.10 is "ok" and 0.25 is "warn" and 0.35 is "error"

  Scenario: The forward stub is overridden
    Given a successful elevator-authority computation
    Then cg_stability_fwd_m is not x_np minus 0.30 times MAC

  Scenario: Enrichment is additive
    Given a context with cg_agg_m
    When the CG envelope is enriched
    Then cg_agg_m is unchanged
    And the new keys are added alongside it

Feature: Field length and matching chart

  Scenario: Net recovery collapses the ground roll
    Given landing_surface "net_recovery"
    Then the ground roll is zero
    And the landing length is the safety factor times the 15 m flare

  Scenario: Sufficiency is tri-state
    Given no available_field_length_m
    Then landing_field_sufficient is null, not false

  Scenario: A sailplane is not judged on takeoff
    Given flight profile "sailplane"
    When the matching chart is computed
    Then only the stall constraint is applied

  Scenario: Hand launch removes the takeoff constraint
    Given takeoff mode "rc_hand_launch" and s_runway 0
    Then the takeoff constraint is zero
    And a hand-launch wing-loading cap of 80 N/m^2 applies

  Scenario: The profile string is never logged raw
    Given a flight profile named with an injected newline
    Then the log contains only a mapped label
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Design assumptions: duality, auto-switch, design choices, event gating (RF-01…RF-06) | Must | Every number in the system is derived from these; the gating prevents a solver storm |
| CG as a top-down target (BR-28) | Must | ADR 0011; writing `CG_agg` into `cg_x` would silently destroy the stability target |
| Mission objectives + preset estimates (RF-08, RF-09) | Must | The entry point for design intent; must never touch calculated values |
| Flight-profile assignment + `V_md` substitution (RF-12…RF-14) | Must | Drives the cruise speed, hence every OP target and the whole context |
| 15-target generation with gating and clipping (RF-15…RF-20) | Must | The aircraft's entire operating envelope; an unclipped flap produces silently wrong aerodynamics |
| Two-stage trim + status rules (RF-21…RF-25) | Must | Produces the persisted trim state the rest of the system reads |
| V-n + gust envelope (RF-29…RF-32) | Must | Structural sizing input; the geometric-chord and `CL_α` choices are correctness-critical |
| SM classification + stability envelope (RF-35, RF-36) | Must | The CG limits a builder actually uses |
| Landing field length + tri-state (RF-39) | Must | A go/no-go answer for the field the user flies from |
| Matching chart with profile applicability (RF-40…RF-42) | Must | The classical sizing surface; constant drift would silently change every answer |
| KPI confidence ladder (RF-33) | Must | Distinguishes a computed number from a 15 %-wrong heuristic |
| Structured gust warnings (RF-32) | Must | `μ_g < 3` is the **normal** RC case — silence here would mislead every RC user |
| SSE streaming + process pool (RF-26, RF-27) | Should | A responsiveness feature; the sequential batch path remains correct |
| Mission KPI spider (RF-11) | Should | A comparison view over numbers already computed |
| Computation-config CRUD (RF-07) | Should | Tuning; sensible defaults exist |
| Scenario override types (RF-37) | Should | Advanced loading analysis over a working default scenario |
| Feasibility tolerances (RF-43) | Should | Presentation of the constraint diagram |
| Log-forging safety (RF-44) | Must | Security control (Sonar S5145) |
| Plotting turn OPs at their real load factor | **Must** | 🟢 decided (`Q-MS-6`); markers were hard-coded to 1.0 g |
| A FK from `mission_objectives.mission_type` to `mission_presets.id` | **Must** | 🟢 decided (`Q-CC-7`); free text today |
| Rejecting an unknown `mission_type` | **Must** | 🟢 decided (`Q-MS-10`, `P-WARN-0`) |
| Varying control surfaces in the grid fallback | **Won't** | 🟢 decided (`Q-MS-5`): no deflection grid; the defect is elsewhere. `best_controls = {}` — the fallback trims by α/β/V only |
| Calculating a design-choice parameter | Won't | BR-26 |
| Writing `CG_agg` into `cg_x` | Won't | BR-28 / ADR 0011 |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/design_assumptions_service.py` | CRUD, `update_calculated_value`, `switch_source`, divergence | 🟢 |
| `app/schemas/design_assumption.py` | `VALID_PARAMETERS`, `PARAMETER_DEFAULTS` (`:72-108`), `DESIGN_CHOICE_PARAMS` | 🟢 |
| `app/models/computation_config.py` | `AircraftComputationConfigModel`, defaults (`:8-16`) | 🟢 |
| `app/models/mission_objective.py`, `app/services/mission_objective_service.py` | `upsert_mission_objective`, `_apply_preset_estimates` | 🟢 |
| `app/models/mission_preset.py`, `app/services/mission_preset_seed.py` | `SEED_PRESETS`, `seed_mission_presets` | 🟢 |
| `app/services/mission_kpi_service.py` | the 7-axis spider | 🟢 |
| `app/models/flightprofilemodel.py`, `app/services/flight_profile_service.py` | `rc_flight_profiles`, `_default_profile`, `_load_effective_flight_profile` | 🟢 |
| `app/services/operating_point_generator_service.py` | `_build_target_definitions`, `_estimate_reference_speeds`, `_clip_flap_to_ted_limit`, `_detect_control_capabilities`, the two-stage trim, `_apply_turn_feasibility`, `_persist_point_set`, the process pool (`:1188-1252`), trim threshold (`:853`) | 🟢 |
| `app/services/flight_envelope_service.py` | `compute_vn_curve` (`:283-368`), the gust block (`:43-48`), `derive_performance_kpis` | 🟢 |
| `app/models/flight_envelope_model.py` | `FlightEnvelopeModel` | 🟢 |
| `app/services/loading_scenario_service.py` | `compute_scenario_cg`, `compute_stability_envelope`, `enrich_context_with_cg_envelope`, SM thresholds (`:51-53`) | 🟢 |
| `app/services/matching_chart_service.py` | the constraint set, `_PROFILE_CONSTRAINT_MAP`, `_wcl_constraint`, `_sanitize_profile_for_log`, W/S sweep (`:71-73`), `DEFAULT_E_OSWALD` (`:77`) | 🟢 |
| `app/services/field_length_service.py` | the Loftin/Roskam constants (single declaration) | 🟢 |
| `app/services/assumption_compute_service.py` | `_compute_landing_field_length` (`:1797-1848`), `LANDING_SURFACE_MU` (`:1782`) | 🟢 (pipeline shared with `aero-analysis`) |
| `app/services/elevator_authority_service.py` | `compute_forward_cg_limit` (gh-500) | 🟢 |
| endpoints | `aeroplane/design_assumptions.py`, `aeroplane/mission_objectives.py`, `aeroplane/loading_scenarios.py`, `aeroplane/flight_envelope.py`, `aeroplane/matching_chart.py`, `aeroplane/field_lengths.py`, `aeroplane/sm_suggestions.py`, `aeroplane/forward_cg.py`, `flight_profiles.py`, `operating_points.py` | 🟢 |
