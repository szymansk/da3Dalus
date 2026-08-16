# Flowcharts — mission-and-sizing

## 1. Design intent → assumptions → aero context → consumers

```mermaid
flowchart TD
    subgraph INTENT["Design intent (user-owned)"]
        M1["mission_objectives (1 per aeroplane)<br/>mission_type + 7 targets + field inputs"]
        M2["mission_presets (9 seeded)<br/>target_polygon, axis_ranges, suggested_estimates"]
        M3["rc_flight_profiles (global library)<br/>environment / goals / handling / constraints"]
        M4["loading_scenarios (N per aeroplane)<br/>toggles, mass/position overrides, adhoc items"]
    end

    M2 -->|"mission_type CHANGED -> _apply_preset_estimates"| A1
    subgraph ASSUME["design_assumptions (17 params, ESTIMATE | CALCULATED)"]
        A1["estimate_value  (user)"]
        A2["calculated_value + calculated_source  (services)"]
        A3["active_source -> effective_value"]
    end
    M1 --> A1

    A3 --> R["recompute_assumptions (AeroBuildup)"]
    M3 -->|"goals: cruise, V_max, margins"| R
    M4 -->|"compute_cg_agg_for_aeroplane"| R
    R -->|"CALCULATED: cl_max, cd0, cg_x, design_speed_mps"| A2

    R --> CTX["aeroplanes.assumption_computation_context (JSON)<br/>THE single source of truth (gh-924)"]

    CTX --> C1["flight_envelope_service — V-n + gust"]
    CTX --> C2["matching_chart_service — T/W vs W/S"]
    CTX --> C3["mission_kpi_service — 7-axis spider"]
    CTX --> C4["operating_point_generator — V_s1 / V_s_to / V_s0"]
    CTX --> C5["speed_polar / endurance / field_length / sm_sizing"]
    CTX --> C6["analysis_service._build_speed_polar (V_dive, CL_alpha, alpha_0)"]

    note["Nothing downstream re-derives cd0 / e / (L/D)max / x_np.<br/>They READ the context."]
    CTX -.- note
```

## 2. The ESTIMATE ↔ CALCULATED duality

```mermaid
flowchart TD
    A["design_assumptions row"] --> B{"active_source"}
    B -->|CALCULATED and calculated_value is not None| B1["effective = calculated_value"]
    B -->|else| B2["effective = estimate_value"]

    C["update_calculated_value(value, source, auto_switch_source=True)"] --> D{"row.calculated_value is None<br/>AND active_source == ESTIMATE<br/>AND param not in DESIGN_CHOICE_PARAMS"}
    D -->|yes| D1["active_source = CALCULATED  (first calculation only)"]
    D -->|no| D2["keep the user's choice"]

    E["update_assumption(estimate_value)"] --> F{"active_source was ESTIMATE?"}
    F -->|no| F1["NO events — the effective value did not change"]
    F -->|yes| F2{"param in {mass, cg_x}?"}
    F2 -->|yes| F3["mark_ops_dirty"]
    F2 --> F4["publish AssumptionChanged(param)"]
    F3 --> F4

    G["switch_source(ESTIMATE <-> CALCULATED)"] --> G1{"target == CALCULATED?"}
    G1 -->|yes| G2{"param in DESIGN_CHOICE_PARAMS?"}
    G2 -->|yes| GX["ValidationError: design choice cannot use CALCULATED"]
    G2 -->|no| G3{"calculated_value exists?"}
    G3 -->|no| GX2["ValidationError: no calculated value available"]
    G3 -->|yes| G4
    G1 -->|no| G4["set active_source"]
    G4 --> G5["mark_ops_dirty for mass/cg_x + publish AssumptionChanged"]
    G5 --> G6{"param != cg_x ?"}
    G6 -->|yes| G7["schedule_recompute_assumptions<br/>(cg_x is the recompute's OWN output — scheduling it would loop)"]

    H["divergence_pct = |est − calc| / |calc| · 100"] --> H1["<5 none · <15 info · <=30 warning · else alert"]
```

## 3. Operating-point generation — the sizing sweep

```mermaid
flowchart TD
    A["_prepare_generation(db, aircraft_uuid, profile_override)"] --> B["_load_effective_flight_profile"]
    B -->|"no profile assigned"| B1["_default_profile(), source_profile_id = None"]
    B1 --> B2["_resolve_cruise_speed_with_md_fallback<br/>-> ctx['v_md_mps'] becomes the cruise speed"]
    B --> C["_estimate_reference_speeds(profile, cached_context)"]

    C --> C1{"ctx has v_s1_mps / v_s_to_mps / v_s0_mps?"}
    C1 -->|yes| C2["provenance = 'polar'  (physics per configuration)"]
    C1 -->|"only v_stall_mps"| C3["use the CLEAN value for all three<br/>(the historical 0.95 / 0.90 multipliers are NOT applied — audit §5.5)"]
    C1 -->|no context| C4["cold_start: vs = max(3.0, V_cruise / min_speed_margin)"]

    C2 --> D["_build_target_definitions -> 15 targets"]
    C3 --> D
    C4 --> D
    C4 --> D0["_stamp_stale_no_polar: append STALE_NO_POLAR to EVERY target"]
    D0 --> D

    D --> E["_clip_flap_to_ted_limit (gh-527/536)"]
    E --> E1{"any flap-role TED in the geometry?"}
    E1 -->|no| E2["pass through — never manufacture a limit"]
    E1 -->|yes| E3["clip to the MOST RESTRICTIVE flap TED (min across all)<br/>+ FLAP_DEFLECTION_CLIPPED warning"]

    E2 --> F["_detect_control_capabilities from the ASB [role] tags"]
    E3 --> F
    F --> G["per target: _validate_target_capability"]
    G -->|"turn_* needs roll OR yaw"| G1["skip + WARN if missing"]
    G -->|"dutch_role_start needs yaw"| G1
    G -->|"stall_with_flaps needs flap"| G1
    G -->|ok| H["_trim_or_estimate_point"]

    H --> I["_solve_and_enrich -> compute_enrichment"]
    I --> J{"generation mode"}
    J -->|batch| J1["SEQUENTIAL (unchanged contract + mocks)"]
    J -->|stream SSE| J2["ProcessPoolExecutor, max(1, min(4, cpu−1)) workers,<br/>spawn ctx, BLAS pinned to 1 thread<br/>(CasADi/IPOPT does NOT release the GIL: threads gave 0.35–0.89x,<br/>processes give ~2.9x)"]

    J1 --> K["_persist_point_set (optionally clears ALL existing sets/OPs)"]
    J2 --> K2["per as_completed result: persist + COMMIT + emit 'op' event"]
    K --> L["operating_pointsets row: operating_points = [ids]"]
    K2 --> L
```

## 4. Two-stage trim solve per target

```mermaid
flowchart TD
    A["target: name, config, velocity, altitude, beta, n_target, flap"] --> B["rho = Atmosphere(altitude).density()<br/>CL_target(V) = m·g·n / (0.5·rho·V²·S_ref)"]
    B --> C["STAGE 1 — asb.Opti (IPOPT)"]
    C --> C1["variables: alpha in [−8°, max_alpha_deg]<br/>pitch δ in [−25, 25]<br/>(turn) roll δ in [−20, 20]<br/>(turn|dutch) yaw δ in [−25, 25]<br/>flap δ is FIXED, not an optimiser variable"]
    C1 --> C2["objective = 50·Cm² + 3·CY²<br/>[+ 15·(CL − CL_target)²]<br/>[+ 2·Cl² + 2·Cn² for turns]<br/>+ 0.001·sum(δ²)"]
    C2 --> C3["solve(max_iter=120, max_runtime=0.35 s,<br/>behavior_on_failure='return_last')"]
    C3 --> D["trim_score = |Cm| + 0.5·|CY| [+ 0.3·|CL − CL_target|]"]

    D --> E{"score > 0.35 ?"}
    E -->|no| H
    E -->|yes| F["STAGE 2 — grid search"]
    F --> F1["velocity factors [1.0, 1.05, 1.10, 1.15]<br/>(descending for max_level_speed)<br/>x alpha = linspace(−4°, 20°, 13) x beta candidates"]
    F1 --> F2{"gs_score < best_score ?"}
    F2 -->|yes| F3["adopt alpha, beta, AND velocity (gh-528)<br/>trim_method = 'grid_fallback'<br/>NOTE: the grid never varies control surfaces"]
    F2 -->|no| H
    F3 --> H["_apply_limit_warnings"]

    H --> H1{"score < 0.35 ?"}
    H1 -->|yes| H2["TRIMMED"]
    H1 -->|no| H3["NOT_TRIMMED + warning"]
    H2 --> H4{"|alpha| > max_alpha_deg or |beta| > max_beta_deg ?"}
    H3 --> H4
    H4 -->|yes| H5["LIMIT_REACHED + ALPHA_/BETA_LIMIT_REACHED"]
    H4 -->|no| I

    H5 --> I{"bank target?"}
    I -->|yes| I1["n = 1/cos(phi) ; V_stall_turn = V_s1·sqrt(n)"]
    I1 --> I2{"V < V_stall_turn ?"}
    I2 -->|yes| I3["LIMIT_REACHED + STALL_IN_TURN"]
    I2 -->|no| J
    I -->|no| J["surface the fixed flap δ into controls (gh-527)"]
    I3 --> J
    J --> K["_aero_coefficients_at -> CL/CD/Cm at the trimmed state (gh-861)"]
    K --> L["TrimmedPoint(alpha_rad, beta_rad, p, q, r, status, warnings,<br/>controls, trim_score, trim_residuals, trim_method)"]

    warn["gh-627: the solver-path label lives on trim_method.<br/>trim_residuals is typed dict[str, float] and Pydantic-REJECTS strings —<br/>a stray residuals['solver_path']='opti' once broke every OP enrichment."]
    L -.- warn
```

## 5. Flight envelope — manoeuvre + Pratt-Walker gust

```mermaid
flowchart TD
    A["compute_flight_envelope(db, uuid)"] --> B["_load_assumptions: mass, cl_max, g_limit<br/>(PARAMETER_DEFAULTS on NotFound)"]
    B --> C["s_ref, b_ref from the ASB airplane ; V_max from profile goals (else 28)"]
    C --> D["compute_vn_curve"]

    D --> E["MANOEUVRE envelope (60 points)"]
    E --> E1["V_stall = sqrt(2W/(rho·S·CL_max)) ; V_dive = 1.4·V_max ; CL_min = −0.8·CL_max"]
    E1 --> E2["n+ = min(q·S·CL_max/W, g_limit)<br/>n− = max(q·S·CL_min/W, −0.4·g_limit)"]

    D --> F{"CL_alpha available?"}
    F -->|"ctx['cl_alpha_per_rad']"| F1["use it (alpha-sweep regression, R² >= 0.995)"]
    F -->|"else, b_ref known"| F2["Helmbold-Diederich: 2·pi·AR/(AR+2)<br/>NOT the thin-airfoil 2·pi (overestimates by ~39% at AR=6)"]
    F -->|"neither"| F3["NO gust lines"]

    F1 --> G["_build_gust_lines"]
    F2 --> G
    G --> G1["c_bar = S_ref / b_ref   (MEAN GEOMETRIC chord, not MAC)"]
    G1 --> G2["mu_g = 2·(W/S) / (rho·c_bar·CL_alpha·g)"]
    G2 --> G3["K_g = 0.88·mu_g / (5.3 + mu_g)"]
    G3 --> G4["U_gust = 15.24 m/s below V_C = V_D/1.4,<br/>linearly tapered to 7.62 m/s at V_D"]
    G4 --> G5["Δn = 0.5·rho·V·CL_alpha·U·K_g / (W/S)<br/>n± = 1 ± Δn"]

    G5 --> H1{"1+Δn > g_limit  (or 1−Δn < −0.4·g_limit)?"}
    H1 -->|yes, first occurrence| H2["GustCriticalWarning:<br/>structure is sized by GUST, not manoeuvre"]
    G2 --> H3{"mu_g in [3, 200]?"}
    H3 -->|no| H4["GustValidityWarning<br/>(RC/UAV with low W/S routinely sit below 3 -> gust loads may be OPTIMISTIC)"]

    E2 --> I["derive_performance_kpis (always exactly 6)"]
    I --> I1["best_ld / min_sink confidence ladder:<br/>1 TRIMMED OP marker -> 'trimmed'<br/>2 ctx v_md_mps / v_min_sink_mps -> 'computed'<br/>3 1.4·V_s / 1.2·V_s -> 'estimated'  (cold start only; ~15% off at high AR)"]
    I1 --> J["UPSERT flight_envelopes (1 row per aeroplane)<br/>vn_curve_json, kpis_json, markers_json, assumptions_snapshot"]
    F3 --> I

    gap["VnMarker.load_factor is ALWAYS 1.0 —<br/>the stored OP carries no CL, so turn OPs plot on the 1-g line."]
    J -.- gap
```

## 6. CG envelope — loading inside stability

```mermaid
flowchart TD
    A["loading_scenarios for the aeroplane"] --> B["compute_scenario_cg per scenario"]
    B --> B1["toggles: enabled=False -> component removed"]
    B --> B2["mass_overrides: mass_kg_override"]
    B --> B3["position_overrides: x_m_override"]
    B --> B4["adhoc_items: always additive"]
    B1 --> C["cg_x = sum(m_i·x_i) / sum(m_i)<br/>(legacy fallback: base_mass_kg / base_cg_x)"]
    B2 --> C
    B3 --> C
    B4 --> C

    C --> D["LOADING envelope = [min cg_x, max cg_x] across scenarios"]

    E["x_np, MAC, target_SM (from recompute)"] --> F["compute_stability_envelope"]
    F --> F1["cg_stability_aft_m = x_np − target_SM · MAC"]
    F --> F2["cg_stability_fwd_m = x_np − 0.30 · MAC   (conservative STUB)"]
    F2 --> G["elevator_authority_service.compute_forward_cg_limit (gh-500)"]
    G -->|cg_fwd_m returned| G1["OVERRIDE the stub with the physics-based limit"]
    G -->|infeasible| G2["keep the stub + WARN"]
    G -->|"ValueError 'x_np=None' / 'mac=None'"| G3["INFO only — documented cold-start<br/>chicken-and-egg on the first recompute (gh-685)"]

    D --> H["validate_cg_envelope"]
    G1 --> H
    G2 --> H
    H --> H1{"cg_loading_aft > cg_stability_aft?"}
    H1 -->|yes| H2["WARN: exceeds aft stability limit by N mm"]
    H --> H3{"cg_loading_fwd < cg_stability_fwd?"}
    H3 -->|yes| H4["WARN: N mm forward of the fwd limit — elevator authority"]

    H --> I["enrich_context_with_cg_envelope (ADDITIVE — cg_agg_m preserved)"]
    I --> I1["cg_forward_m, cg_aft_m<br/>sm_at_fwd = (x_np − cg_fwd)/MAC ; sm_at_aft<br/>cg_stability_fwd_m, cg_stability_aft_m"]
    I1 --> I2["x_np or MAC missing -> SM values stored as None,<br/>never as a deceptive stub"]

    J["classify_sm(sm, target_sm) — Scholz §4.2"] --> J1["sm < 0.02 -> error (Phugoid divergent)<br/>sm < target -> warn<br/>sm <= 0.20 -> ok<br/>sm <= 0.30 -> warn (heavy nose, trim drag)<br/>else -> error (elevator authority)"]
```

## 7. Matching chart — T/W vs W/S with per-profile constraints

```mermaid
flowchart TD
    A["compute_chart(aircraft, mode, profile)"] --> B["_resolve_profile_key<br/>(None | 'custom' | unknown -> ALL constraints apply)"]
    B --> C["_mode_defaults(mode) -> s_runway, gamma_climb_deg, v_s_target"]
    C --> C1["rc_runway 50m/5°/7 · rc_hand_launch 0/5°/7<br/>uav_runway & uav_belly_land 200m/4°/12<br/>ga_runway 500m/1.5°/27.7 (FAR-23.65, 54 kt)<br/>unknown -> WARN + uav_runway"]
    C1 --> D["sweep W/S over [10, 1500] N/m², 200 steps"]

    D --> E{"per constraint, applicable for this profile?"}
    E --> F1["TAKEOFF (line): T/W = C_TO·K_TO_50FT·(W/S) / (rho·g·CL_max_TO·s_TO)<br/>s_runway = 0 -> 0 (hand launch)"]
    E --> F2["LANDING (vertical): W/S_max = s_LDG·rho·CL_max_LDG / (K_LDG_HARD·K_LDG_50FT)"]
    E --> F3["CRUISE (line): T/W = q·CD0/(W/S) + (W/S)·k/q,  k = 1/(pi·e·AR)"]
    E --> F4["CLIMB (line): T/W = sin(gamma) + [q·CD0/(W/S) + (W/S)·k/q]   (CLEAN polar)"]
    E --> F5["STALL (vertical): W/S_max = 0.5·rho·V_s_target²·CL_max_CLEAN"]
    E --> F6["MISSION_MIN_TW (horizontal): acro_3d 1.5 · wing_racer 0.8 · sport 0.5"]
    E --> F7["POWER_LOADING (horizontal): T/W = (P/m)·eta_prop / (g·1.3·V_stall)<br/>trainer 125 · sport 200 · wing_racer 275 · acro_3d 400 W/kg"]
    E --> F8["VERTICAL_CLIMB (line): T/W = 1 + D/W   (acro/3D)"]
    E --> F9["WCL (vertical): (WCL_lb·47.88)^(2/3) · AR^0.25"]
    E --> F10["HAND_LAUNCH (vertical): W/S <= 80 N/m²  (rc_hand_launch only)"]

    F1 --> G["_design_point_from_aircraft:<br/>T/W = t_static_N / (m·g) ; W/S = m·g / s_ref (or ws_n_m2)"]
    F5 --> G
    G --> H["_check_feasibility<br/>line binds within 3 % T/W · vertical within 5 % W/S"]
    H --> I["MatchingChartResponse: constraints + design point + feasibility"]

    prof["_PROFILE_CONSTRAINT_MAP<br/>trainer: stall climb power_loading wcl<br/>sport: + mission_min_tw<br/>wing_racer: stall cruise power_loading<br/>acro_3d: stall mission_min_tw power_loading vertical_climb<br/>stol_bush: stall takeoff landing climb<br/>slope_soarer | glider | sailplane: stall ONLY<br/>motor_glider | flying_wing: stall climb cruise"]
    E -.- prof
    src["K_TO_50FT 1.66 · K_LDG_50FT 2.73 · K_LDG_HARD 0.5847 · C_TO 1.21<br/>IMPORTED from field_length_service — never re-declared (drift guard)"]
    F1 -.- src
```

## 8. Reynolds-banded polar table (gh-493) and its lookups

```mermaid
flowchart TD
    A["fine-sweep samples v[], cl[], cd[] (already computed — NO extra AB calls)"] --> B["anchors = [max(0.5·V_cruise, 3), V_cruise,<br/>min(max(1.3·V_cruise, V_max), V_sweep_max)]"]
    B --> C["Re = rho·V·MAC/mu  (ISA SL, mu = 1.81e-5) — a LABEL, not an ASB parameter"]
    C --> D{"Re_max / Re_min < 2.5 ?"}
    D -->|yes| D1["DEGENERATE: single fallback row, degenerate = True"]
    D -->|no| E["bands = midpoints between anchors,<br/>outer edges extended by 50 % of the adjacent gap"]
    E --> F{"samples in band >= 6 ?"}
    F -->|no| F1["_fallback_row (cd0 = None, fallback_used = True)"]
    F -->|yes| F2["_fit_band_with_ar -> cd0, e = 1/(pi·AR·k), R²"]

    F1 --> G["PolarReTableRow validation at the cache boundary"]
    F2 --> G
    D1 --> G
    G --> H["gh-924 BACKFILL in recompute_assumptions:<br/>rows with fallback_used or cd0 = None get the<br/>authoritative cruise parasite cd0 + Trefftz e"]

    H --> I["lookup_cd0_at_v: LINEAR IN 1/sqrt(Re)<br/>(Blasius/Schlichting cf ∝ Re^−1/2);<br/>outside the table -> CLAMP + warn"]
    H --> J["lookup_e_oswald_at_v: constant MEAN of non-fallback rows<br/>(Hepperle/Drela: e is insensitive to Re subsonically);<br/>else the mean of ANY e present; last resort 0.8"]

    I --> K["_picard_iterate_speed — ONE pass"]
    J --> K
    K --> K1["V_1 = speed_fn(cd0(V_0), e(V_0), …)<br/>|ΔV|/V_0 >= 5 % -> WARN but still accept V_1"]
    K1 --> L["V_md, V_min_sink, V_max  ->  clamped to >= V_stall (gh-683)"]
```
