# Flowcharts — aero-analysis

## 1. The solver dispatcher — one door, three solvers

```mermaid
flowchart TD
    A["analyse_aerodynamics(tool, op_schema, asb_airplane)"] --> B["_build_operating_point<br/>asb.Atmosphere(altitude) + asb.OperatingPoint(V, a, b, p, q, r)"]
    B --> C["asb_airplane.xyz_ref = op.xyz_ref<br/>(moment reference = CG)"]
    C --> D{"op.control_deflections ?"}
    D -->|yes| D1["airplane = airplane.with_control_deflections(overrides)<br/>NOTE: unknown keys are SILENTLY DROPPED"]
    D -->|no| E
    D1 --> E{"tool"}

    E -->|AEROBUILDUP| F1["asb.AeroBuildup(...).run_with_stability_derivatives()"]
    E -->|VORTEX_LATTICE| F2["_remesh_airplane (gh-857)<br/>asb.VortexLatticeMethod(spanwise_resolution=1,<br/>spacing=np.linspace)"]
    E -->|AVL| F3{"alpha or beta is a list/array?"}
    E -->|other| X["ValueError: invalid analysis tool"]

    F3 -->|yes| X2["ValueError: AVL does not support parameter sweeps"]
    F3 -->|no| F4{"avl_file_content given?"}
    F4 -->|no| X3["ValueError: avl_file_content required"]
    F4 -->|yes| F5["AVLRunner(...).run(content)"]

    F1 --> G["AnalysisModel.from_abu_dict(..., methode='aerobuildup')"]
    F2 --> G2["AnalysisModel.from_abu_dict(..., methode='vortex_lattice')<br/>+ optional vlm.draw() figure"]
    F5 --> G3["AnalysisModel.from_avl_dict(result)"]

    G --> H["(AnalysisModel, Figure|None)"]
    G2 --> H
    G3 --> H

    note["Defaults are hard-coded per endpoint:<br/>alpha/simple sweep -> AEROBUILDUP<br/>streamlines/four-view -> VORTEX_LATTICE<br/>strip forces -> ASB VLM (solver='avl' opt-in)"]
    E -.- note
```

## 2. The single-source-of-truth aero context (gh-924)

```mermaid
flowchart TD
    A["recompute_assumptions(db, uuid)<br/>SYNC — callers must asyncio.to_thread"] --> B["build ASB airplane"]
    B --> C{"any wings?"}
    C -->|no| C0["log info, return (no-op)"]
    C -->|yes| D["main_wing = argmax(wing.area())<br/>OVERRIDE s_ref / c_ref / b_ref<br/>(ASB defaults to wings[0] — the F1/gh-788 bug class)"]
    D --> E["seed_defaults() + _load_or_create_config()  (idempotent)"]
    E --> F["_load_flight_profile_speeds -> V_cruise, V_max, user_set_cruise"]

    F --> G["_stability_run_at_cruise (AeroBuildup, alpha=0)"]
    G --> G1["CD0 = CD_total − CL²/(pi·AR·e)<br/>PARASITE, not total drag"]
    G1 --> H["_coarse_alpha_sweep -> stall_alpha = argmax(CL)"]
    H --> I["_fine_sweep_cl_max (V x alpha grid, ONE vectorised run)<br/>-> CL_max, cl[], cd[], v[], cdi[]"]

    I --> J{"main-wing turbulator enabled? (gh-935)"}
    J -->|yes| J1["cd0 += ΔCD0(xtr_root, xtr_tip)<br/>raw_cd0 PRESERVED for the fit gate"]
    J -->|no| K
    J1 --> K["write CALCULATED: cl_max, cd0, cg_x = x_np − target_SM·MAC"]

    K --> L["_fit_parabolic_polar_with_refinement(cd0_stability = raw_cd0)"]
    L --> M["_e_oswald_from_sweep: e = CL²/(pi·AR·CDi) at (L/D)max"]
    M --> N{"e provenance"}
    N -->|Trefftz ok| N1["aerobuildup_trefftz"]
    N -->|else fit ok| N2["fit"]
    N -->|else| N3["fallback (e_eff = 0.8)"]

    N1 --> O["PUBLISH self-consistent scalars<br/>E_max = ½·sqrt(pi·AR·e/CD0)<br/>CL@E_max = sqrt(CD0·pi·AR·e)"]
    N2 --> O
    N3 --> O

    O --> P["per-config polars: clean / takeoff (min(15°,TED)) / landing (full TED)"]
    P --> Q["build_re_table (rebin fine sweep — NO extra AB calls)"]
    Q --> Q1["gh-924 backfill: rows with fallback_used/cd0=None<br/>get the cruise cd0 + Trefftz e"]
    Q1 --> R["V-speeds + Picard refine (1 pass) + clamp to V_stall"]
    R --> S["CG: loading envelope, stability envelope,<br/>forward CG from elevator authority (gh-500)"]
    S --> T["landing field length (gh-477)"]
    T --> U["_cache_context -> aeroplanes.assumption_computation_context"]
    U --> V{"cg_x changed?"}
    V -->|yes| V1["mark_ops_dirty + publish AssumptionChanged(cg_x)"]
    V -->|no| W["done"]
    V1 --> W

    err["FATAL: any AeroBuildup failure in steps G/H/I<br/>-> log + RETURN, previous context stays valid"]
    G -.- err
```

## 3. Parabolic-polar fit — six gates, resolution goes up only

```mermaid
flowchart TD
    A["cl[], cd[], AR, CL_max, cd0_stability"] --> B{"AR > 0 ?"}
    B -->|no| R1["reject: insufficient_points / sweep"]
    B -->|yes| C["window CL in [max(0.10, 0.10·CLmax), 0.85·CLmax]"]
    C --> D{"n >= 6 points?"}
    D -->|no| R2["reject: insufficient_points / sweep"]
    D -->|yes| E{"dCD/d(CL²) >= −1e-6 ?"}
    E -->|no| R3["reject: non_monotonic_polar / data<br/>(laminar bubble or stall contamination)"]
    E -->|yes| F["OLS: CD = k·CL² + cd0"]
    F --> G{"k > 0 ?"}
    G -->|no| R4["reject: negative_slope_k / DESIGN"]
    G -->|yes| H{"cd0_fit > 0 ?"}
    H -->|no| R5["reject: non_positive_cd0 / consistency"]
    H -->|yes| I["e = 1/(pi·AR·k)"]
    I --> J{"0.4 < e <= 1.0 ?"}
    J -->|no| R6["reject: unphysical_e_oswald / DESIGN"]
    J -->|yes| K{"|cd0_fit − cd0_stability|/cd0_stability <= 0.20 ?"}
    K -->|no| R7["reject: cd0_stability_mismatch / consistency"]
    K -->|yes| L["SUCCESS: (cd0_fit, e, R²)"]

    R1 --> M{"gate in {insufficient_points, non_monotonic_polar} ?"}
    R2 --> M
    R3 --> M
    R4 --> Z["no retry — genuine design/physics rejection"]
    R5 --> Z
    R6 --> Z
    R7 --> Z

    M -->|yes, attempt <= 2| N["re-run _fine_sweep_cl_max with<br/>step / 2^attempt, margin · 1.5^attempt<br/>RESOLUTION UP — thresholds NEVER loosened"]
    N --> A
    M -->|retries exhausted| Z

    L --> P["auto_refined = did_refine AND rejection is None"]
    Z --> Q["PolarRejection{gate, category, fitted_value, threshold, hint}<br/>only category=='design' is shown to the user"]
```

## 4. Operating-point lifecycle: invalidate → retrim → stability

```mermaid
stateDiagram-v2
    [*] --> NOT_TRIMMED: created
    NOT_TRIMMED --> TRIMMED: trim_score < 0.35
    NOT_TRIMMED --> LIMIT_REACHED: alpha or beta past the profile limit, or STALL_IN_TURN
    TRIMMED --> DIRTY: GeometryChanged or AssumptionChanged(mass, cg_x)
    LIMIT_REACHED --> DIRTY: same
    DIRTY --> COMPUTING: retrim_dirty_ops picks it up
    COMPUTING --> TRIMMED: AeroBuildup trim converged (Cm = 0)
    COMPUTING --> LIMIT_REACHED: not converged
    COMPUTING --> NOT_TRIMMED: unexpected solver failure
    COMPUTING --> INVALID: ValidationDomainError / Pydantic (corrupt row, gh-623)
    INVALID --> [*]: user must re-create the OP
```

```mermaid
flowchart TD
    A["WingModel / WingXSecModel / FuselageModel<br/>after_insert | after_update | after_delete"] --> B["stability_events._on_geometry_change<br/>AND avl_geometry_events._on_geometry_change<br/>(BOTH registered — fires twice)"]
    B --> C1["stability_results.status = DIRTY"]
    B --> C2["avl_geometry_files.is_dirty = True"]
    B --> C3["mark_ops_dirty(aeroplane_id)<br/>(skips rows already DIRTY/COMPUTING)"]
    B --> C4["event_bus.publish(GeometryChanged)"]

    C4 --> D1["_on_geometry_changed -> job_tracker.schedule_retrim"]
    C4 --> D2["_on_geometry_changed_recompute_assumptions -> schedule_recompute_assumptions"]

    E["AssumptionChanged(param)"] --> F1{"param in {mass, cg_x} ?"}
    F1 -->|yes| D1
    E --> F2{"param in {target_static_margin, mass} ?"}
    F2 -->|yes| D2

    D1 --> G["retrim_dirty_ops(aeroplane_id) — own SessionLocal"]
    G --> H{"pitch control TED present?<br/>role in {elevator, stabilator, elevon, ruddervator}"}
    H -->|no| H0["WARN — OPs stay DIRTY forever"]
    H -->|yes| I["for each DIRTY op: status=COMPUTING"]
    I --> J["trim_with_aerobuildup(trim_variable=pitch, target Cm=0)"]
    J -->|converged| K["TRIMMED + control_deflections[pitch] = delta"]
    J -->|not converged| L["LIMIT_REACHED"]
    J -->|domain/pydantic error| M["INVALID + warning"]
    J -->|other exception| N["NOT_TRIMMED"]
    K --> O{"any trimmed?"}
    L --> O
    O -->|yes| P["get_stability_summary(first trimmed OP, AEROBUILDUP)<br/>-> upsert stability_results"]
    O -->|no| Q["db.commit()"]
    P --> Q

    note["cg_x, cd0 and cl_max are EXCLUDED from the recompute trigger set<br/>to break recompute -> AssumptionChanged(cg_x) -> recompute"]
    F2 -.- note
```

## 5. Trim-consistent run (gh-577) — resolve, validate, solve

```mermaid
flowchart TD
    A["POST /aeroplanes/{id}/streamlines<br/>or /strip_forces or /spanwise_loads"] --> B["get_aeroplane_or_raise + schema"]
    B --> C{"op_schema.operating_point_id set?"}
    C -->|no| C0["inline schema used unchanged<br/>(explicit diagnostic / manual mode)"]
    C -->|yes| D["SELECT operating_points WHERE id = ? AND aircraft_id = ?<br/>(aircraft scoping blocks cross-aeroplane OP injection)"]
    D -->|missing| E1["NotFoundError -> 404"]
    D --> F{"status == TRIMMED ? (require_trimmed default True)"}
    F -->|no| E2["ValidationDomainError -> 422"]
    F -->|yes| G["operating_point_model_to_schema"]

    G --> G1["_require_field on every NOT-NULL state column<br/>(a NULL raises rather than defaulting to 0.0)"]
    G1 --> G2["alpha, beta: RADIANS -> DEGREES"]
    G2 --> G3["_pick_deflections:<br/>non-empty control_deflections (manual override) WINS,<br/>else controls (trim output);<br/>an EMPTY override falls through — it cannot erase a fresh trim"]

    C0 --> H["build asb.Airplane"]
    G3 --> H
    H --> I["validate_deflections_against_airplane"]
    I -->|unknown surface names| E3["ValidationDomainError -> 422<br/>lists unknown vs available"]
    I -->|ok| J["analyse_aerodynamics(VORTEX_LATTICE, ...)"]
    J --> K["figure / StripForcesResponse / SpanwiseLoadsResponse"]

    note["with_control_deflections SILENTLY drops unknown keys —<br/>without the validator a renamed surface would run CLEAN<br/>while the UI labelled the plot 'trimmed'"]
    I -.- note
```

## 6. VLM strip forces without AVL (gh-674 / gh-855)

```mermaid
flowchart TD
    A["asb.Airplane + asb.OperatingPoint"] --> B["_remesh_airplane"]
    B --> B1["per wing: spans_i = hypot(dy, dz)  (dihedral-inclusive)"]
    B1 --> B2["n_i = max(2, round(40 · span_i / sum(span)))"]
    B2 --> B3["insert blended xsecs (linear chord/twist/xyz_le,<br/>Airfoil.blend_with_another_airfoil; fallback = inboard airfoil)"]
    B3 --> B4["re-assert s_ref / b_ref / c_ref / xyz_ref (gh-788)"]

    B4 --> C["VortexLatticeMethod(spanwise_resolution=1, chordwise_resolution=8)"]
    C --> D["run()"]
    D --> E["_strip_index_ranges(is_trailing_edge)<br/>panels are chordwise-fastest -> each TE flag closes a strip"]
    E --> F{"sum(_wing_strip_counts) == len(strips) ?"}
    F -->|no| F1["degrade to ONE aggregate surface (never crash)"]
    F -->|yes| F2["assign contiguous blocks to wings in airplane.wings order"]

    F1 --> G
    F2 --> G["per strip"]
    G --> G1["d_hat = steady_freestream_direction (normalised)<br/>l_hat = [−d_z, 0, d_x] (normalised)"]
    G1 --> G2["lift = F·l_hat ; drag = F·d_hat<br/>cl = lift/(q·A) ; cd = drag/(q·A)<br/>ai = degrees(atan2(drag, lift))<br/>cl_norm = cl·chord/c_ref"]
    G2 --> G3["cdv = 0, cm_c/4 = 0, cm_LE = 0, C.P.x/c = 0.25<br/>(VLM is INVISCID — no viscous or chordwise pressure data)"]
    G3 --> H["dict with Sref/Cref/Bref/alpha/beta/mach/CL/CD/strip_forces<br/>— byte-compatible with the AVL parser output"]
    H --> I["_strip_surfaces_from_result -> StripForcesResponse(aero_model='ASB')"]
```

## 7. Speed polar from a drag polar (pure function)

```mermaid
flowchart TD
    A["cl[], cd[], masses[], base_mass, S_ref, rho"] --> B["keep only CL > 0 (steady glide)"]
    B --> C["for each mass m (deduped, base always present)"]
    C --> D["V = sqrt(2·m·g / (rho·S·CL))<br/>w = V·(CD/CL)"]
    D --> E["co-sort by V ascending"]
    E --> F["i_min_sink = argmin(w)<br/>i_best = argmax(CL/CD) = argmax(V/w)<br/>V_stall = sqrt(2·m·g/(rho·S·CL_max))"]
    F --> G["alpha at stall / min-sink / best-glide<br/>via _cl_to_alpha_deg(cl_alpha_per_rad, alpha_0_deg)  (gh-871)"]
    G --> H["SpeedPolarCurve{mass, is_base, V[], w[], cl[], cd[],<br/>v_stall, v_min_sink, w_min, v_best_glide, ld_max, alphas}"]
    H --> I{"axis bounds (gh-799)"}
    I --> I1["v_axis_min = 0.7·min(V_stall)<br/>v_axis_max = 1.3·V_dive (else max V)"]
    I1 --> I2{"either None, or min >= max?"}
    I2 -->|yes| I3["BOTH set to None -> Plotly autoranges"]
    I2 -->|no| J["SpeedPolar{base_mass, s_ref, rho, altitude, curves, bounds}"]
    I3 --> J

    note["V, w scale as sqrt(m): the coefficients are mass-independent,<br/>only the speed needed to fly a given CL changes"]
    D -.- note
    warn["MISSING mass assumption -> silently defaults to 1.0 kg<br/>(log warning only) — the polar is then meaningless"]
    A -.- warn
```
