# Flowcharts — powertrain

## 1. Data pipeline — raw vendor files to a selectable component

```mermaid
flowchart TD
    RAW["data/apc_raw/**/PER3_*.dat<br/>GITIGNORED, ~58 MB, ~1600 props"]
    PE0["data/apc_raw/PE0-FILES_WEB/*.PE0<br/>GITIGNORED — weight, inertia, blade geometry"]

    RAW -->|"scripts/parse_apc_props.py<br/>header line 1 -> diameter x pitch + variant<br/>SI columns only (W, N-m, N)<br/>blades from trailing -[3-9]"| SNAP
    SNAP["data/cots/apc_props.json.gz<br/>COMMITTED — the durable reimport source"]
    PE0 -->|"scripts/enrich_apc_snapshot_pe0.py<br/>match on (diameter, pitch, variant)<br/>weight < 1 g -> unit_warning, REJECTED"| SNAP

    SNAP -->|"scripts/import_apc_props.py<br/>prop_polar_import.import_prop_polars<br/>upsert by (manufacturer, name)"| DB1
    DB1["propeller_polars + propeller_polar_samples"]

    DB1 -->|"scripts/seed_propeller_components.py<br/>prop_component_seed<br/>upsert by model_ref"| DB2
    DB2["components (component_type='propeller')<br/>mass_g <- weight_g (both grams)"]

    OTHER["data/cots/dpower.json<br/>generic_batteries.json<br/>spektrum_avian.json"] -->|"scripts/import_cots.py<br/>cots_import.import_snapshot<br/>upsert by (manufacturer, name)"| DB2

    DB1 -.->|"shared model_ref"| BRIDGE["component_service._resolve_polar_id<br/>ComponentRead.has_polar / polar_id"]
    DB2 -.-> BRIDGE

    note["No network at any stage after the snapshot is committed.<br/>Raw vendor files are never re-hosted."]
    SNAP -.- note
```

## 2. Reimport decision — when is a row rewritten?

```mermaid
flowchart TD
    R["snapshot record"] --> V{"manufacturer + name present<br/>AND component_type == 'propeller'?"}
    V -->|no| VE["ImportResult.errors += msg<br/>continue"]
    V -->|yes| E{"existing row by (manufacturer, name)?"}
    E -->|no| I["INSERT header + flush + _upsert_samples<br/>imported += 1"]
    E -->|yes| F{"force=True?"}
    F -->|yes| U
    F -->|no| Q{"_records_equal?"}

    Q -->|"source_version differs"| U
    Q -->|"source_url differs"| U
    Q -->|"variant differs (gh-999 backfill)"| U
    Q -->|"weight_g is NULL but snapshot has one (gh-1000)"| U
    Q -->|"all match"| SK["skipped += 1"]

    U["UPDATE all header fields<br/>DELETE ALL samples + re-insert<br/>updated += 1"]

    lim["LIMITATION (documented): if APC corrects polar data<br/>WITHOUT bumping source_version, the change is<br/>silently skipped. Run with --force."]
    Q -.- lim
```

## 3. Performance model — two motor models under one API

```mermaid
flowchart TD
    REQ["POST /aeroplanes/{uuid}/powertrain/performance<br/>motor_component_id, battery_component_id,<br/>propeller_polar_id, v range, altitude, throttle"]

    REQ --> RES["Endpoint resolution"]
    RES --> R1{"motor exists AND type == brushless_motor?"}
    R1 -->|no| E404["404"]
    RES --> R2{"kv_rpm_per_volt AND cells_lipo_max in specs?"}
    R2 -->|no| E422["422"]
    RES --> R3{"battery has cells AND capacity_mah?"}
    R3 -->|no| E422
    RES --> R4{"polar exists AND has samples AND diameter_in > 0?"}
    R4 -->|no| E422

    R1 --> SPEC["MotorSpec + BatterySpec + PropellerPolarRow[]"]
    SPEC --> Q{"motor.rm_ohm > 0<br/>(uses_qprop_model)"}

    Q -->|"NO — D-Power catalog has no Rm"| A["MODEL A — fixed RPM (gh-615)"]
    Q -->|"YES"| B["MODEL B — QPROP torque balance (gh-1006)"]

    A --> A1["V_bat = cells x 3.7 V (LOADED, not 4.2 peak)<br/>n = output_kv x V_bat x throttle  (CONSTANT over V)<br/>output_kv = kv / (gear_ratio or 1)"]
    A1 --> A2["P_elec_max = min(I_max x 3.7 x cells, cap_Ah x C x V_nom)<br/>P_shaft_max = P_elec_max x eta_motor"]
    A2 --> A3["per V:  P = clip(Cp*rho*n^3*D^5, 0, P_shaft_max)<br/>estimated = True"]

    B --> B1["per V: bisect 80x on RPM until<br/>Q_motor(I) = Q_prop(n)"]
    B1 --> B2["I(n) = (V_term - omega/Kv_si) / Rm<br/>Q_motor = (I - I0) / Kv_si<br/>Q_prop = Cp*rho*n^2*D^5 / (2*pi)"]
    B2 --> B3["P = Q x omega ; eta_motor = (V-I*Rm)(I-I0)/(V*I)<br/>estimated = False"]

    A3 --> C["COMMON per point"]
    B3 --> C
    C --> C1["J = V / (n*D)<br/>Ct, Cp, Pe interpolated at J from the NEAREST-RPM rows<br/>T = Ct*rho*n^2*D^4  (clamped >= 0)<br/>eta_prop = clip(Pe, 0, 1)  — J-dependent, not a flat 0.65"]
    C1 --> OUT["PerformanceSample[] + p_available_w + warnings + notes"]

    style E404 fill:#511,color:#fff
    style E422 fill:#511,color:#fff
```

## 4. QPROP bisection — the bracket

```mermaid
flowchart TD
    S["solve_qprop_operating_point"] --> H["rpm_hi = free run = V_term * Kv_si * 60 / 2*pi   (I -> 0)"]
    S --> L{"max_current_a set?"}
    L -->|yes| L1["back_emf_floor = V_term - I_max * Rm<br/>rpm_lo = max(back_emf_floor, 0) * Kv_si * 60 / 2*pi"]
    L -->|no| L2["rpm_lo = 0"]

    L1 --> CH{"rpm_hi <= rpm_lo?"}
    L2 --> CH
    CH -->|yes| D["DEGENERATE: rpm = rpm_lo<br/>(V_term too low, or the current ceiling binds everywhere)"]
    CH -->|no| R["r_lo = residual(rpm_lo) ; r_hi = residual(rpm_hi)"]

    R --> R1{"r_lo <= 0?"}
    R1 -->|yes| RA["clamp to rpm_lo<br/>motor cannot match prop demand even at the lowest RPM"]
    R1 -->|no| R2{"r_hi >= 0?"}
    R2 -->|yes| RB["clamp to rpm_hi<br/>motor over-powers; no current headroom hit"]
    R2 -->|no| RC["BISECT 80 iterations on residual = Q_motor - Q_prop"]

    RC --> OUT["QpropOperatingPoint(rpm, current_a, torque_nm, p_shaft_w, eta_motor)"]
    RA --> OUT
    RB --> OUT
    D --> OUT
```

## 5. Interpolation guards

```mermaid
flowchart TD
    I["interpolate_ct_cp_pe(rows, J)"] --> E{"rows empty?"}
    E -->|yes| E1["(0, 0, 0) + warning"]
    E -->|no| S["sort by J ; np.interp on Ct and Cp"]
    S --> W{"J outside [J_min, J_max]?"}
    W -->|yes| W1["extrapolation_warning = True<br/>J CLAMPED to the range — never runs off the dataset"]
    W -->|no| W2["J used as-is"]
    W1 --> CT
    W2 --> CT["Ct = max(Ct_interp, 0)<br/>negative windmilling tail DISCARDED"]
    CT --> PE{"Cp > 0 AND J > 0?"}
    PE -->|yes| PE1["Pe = Ct * J / Cp   — RECOMPUTED, not read from the column"]
    PE -->|no| PE2["Pe = 0"]

    n1["Callers that KNOW the RPM pre-filter to the nearest-RPM group.<br/>The J-only helper merges all RPMs because Ct(J) is<br/>nearly RPM-independent for standard APC props."]
    S -.- n1
    n2["Torque is ALWAYS P/(2*pi*n), never the stored Torque_Nm<br/>(3-dp precision loss at low RPM)."]
    CT -.- n2
```

## 6. Solution space vs catalog sweep — two opposite questions

```mermaid
flowchart TD
    subgraph SS["GET /powertrain/solution-space — 'what must I BUY?' (gh-975)"]
        X1["assumption_computation_context<br/>s_ref, e_oswald, AR, v_cruise, cd0"] --> X2["C_L = 2mg/(rho V^2 S)<br/>C_D = cd0 + C_L^2/(pi e AR)<br/>P_aero = 0.5 rho V^3 S C_D<br/>P_elec = P_aero/(eta_p eta_m eta_e)"]
        X2 --> X3["E_Wh = P_elec(V_cruise) * t_target_h / DoD"]
        X3 --> X4["per cell count S (band: eta_prop lo / mid / hi)<br/>V_nom = S*3.7 ; V_sag = S*3.5<br/>I_peak = P_top_elec / V_sag<br/>cap_mAh = E_Wh/V_nom*1000<br/>C_min = I_peak/(cap_Ah) * c_margin<br/>ESC_min = I_peak * esc_margin<br/>KV = RPM_target/(V_nom*load_rpm_factor)"]
        X4 --> X5["SolutionRow[] + FeasibleRegion[] (C-rate hyperbola, 40 pts)<br/>+ ShoppingSpec[] + has_motor/battery/esc_match"]
    end

    subgraph CS["POST /powertrain_sizing — 'which parts that EXIST fit?' (gh-490/960/992)"]
        Y1["motors x batteries CROSS PRODUCT<br/>(ESCs matched, not swept)"] --> Y2["total_mass = airframe + motor + battery<br/>(propeller mass NOT counted)"]
        Y2 --> Y3["P_cruise = endurance_service._power_required(...)<br/>ONE shared drag polar"]
        Y3 --> Y4["I = P/V_pack ; reject if > max_current_draw_a<br/>t_flight = cap_Ah/I * 0.8 * 60 min<br/>ESC = FIRST with continuous_current_a >= I"]
        Y4 --> Y5["confidence = min(t_flight/t_target, 1.0)<br/>sort desc, top 10"]
    end

    gap["gh-978 BLOCKER (fixed): P_top_elec is ALREADY battery power,<br/>so I = P/V_sag. Dividing again by eta_motor*eta_esc double-counts."]
    X4 -.- gap
    gap2["_PHASE1_PROP_DIAMETER_M = 0.30 m is a FIXED estimate for KV,<br/>even though the whole APC database is one table away."]
    X4 -.- gap2
```

## 7. Component-type validation

```mermaid
flowchart TD
    C["POST/PUT /components"] --> V["component_type_service.validate_specs"]
    V --> T{"component_type registered?"}
    T -->|no| T1["ValidationError:<br/>'use GET /component-types to discover'"]
    T -->|yes| P["for each PropertyDefinition in schema"]
    P --> P1{"required and missing?"}
    P1 -->|yes| E1["ValidationError (missing_required)"]
    P1 -->|no| P2{"type == number?"}
    P2 -->|yes| P3["non-numeric / bool -> error<br/>< min -> error ; > max -> error"]
    P2 -->|no| P4["string / boolean type check ; options membership"]
    P3 --> OK
    P4 --> OK["INSERT / UPDATE"]

    UNK["specs keys NOT in the schema<br/>are ACCEPTED without complaint<br/>(e.g. propeller 'variant')"]
    P -.- UNK

    SEED["prop_component_seed writes ComponentModel DIRECTLY<br/>-> BYPASSES validate_specs entirely"]
    SEED -.->|"a polar with NULL diameter_in produces a<br/>schema-INVALID component that 422s on the first PUT"| OK

    style T1 fill:#511,color:#fff
    style E1 fill:#511,color:#fff
    style SEED fill:#530,color:#fff
```
