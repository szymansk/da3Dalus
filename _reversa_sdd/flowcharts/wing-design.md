# Flowcharts — wing-design

## 1. The unit boundary (mm ↔ m)

```mermaid
flowchart LR
    subgraph API["REST API — metres"]
        A1["SpareDetailSchema<br/>width/height/length/start/origin in m"]
    end
    subgraph DB["Database"]
        B1["wing_xsecs.xyz_le, chord — METRES"]
        B2["wing_xsec_spares.* — MILLIMETRES (gh-402)"]
        B3["spare_vector — dimensionless unit vector"]
    end
    subgraph CFG["WingConfiguration / cad_designer — millimetres"]
        C1["segments, airfoils, spars"]
    end
    subgraph ASB["AeroSandbox / AVL — metres"]
        D1["asb.Wing"]
    end

    A1 -->|"_convert_spare_to_mm  x1000"| B2
    B2 -->|"_convert_spare_to_meters  x0.001"| A1
    B1 -->|"_scale_asb_wing_geometry_schema(scale=1000.0)"| C1
    B2 -->|"scale_db_origin_to_config: factor = 0.001 x scale"| C1
    C1 -->|"wing_config_to_wing_model(scale=0.001)"| B1
    C1 -->|"asb_wing(scale)"| D1
    B1 -->|"wing_model_to_asb_wing_schema"| D1
    B3 -.->|"never scaled"| C1
```

## 2. Wing create — two entry paths

```mermaid
flowchart TD
    subgraph P1["ASB geometry path"]
        A1["PUT /aeroplanes/{id}/wings/{name}<br/>AsbWingGeometryWriteSchema"] --> B1["create_wing"]
        B1 --> C1{"name unique on this aeroplane?"}
        C1 -->|no| E1["ValidationError -> 422"]
        C1 -->|yes| D1["WingModel.from_dict"]
        D1 --> F1["design_model = 'asb'"]
    end

    subgraph P2["WingConfiguration path"]
        A2["POST .../wings/{name}/from-wingconfig<br/>WingConfigurationSchema (mm)"] --> B2["create_wing_from_wing_configuration(scale=0.001)"]
        B2 --> C2{"name unique?"}
        C2 -->|no| E1
        C2 -->|yes| D2["create_wing_configuration(payload)"]
        D2 --> D3["wing_config_to_wing_model(scale=0.001)"]
        D3 --> F2["design_model = 'wc'"]
        F2 --> G2["db.flush()"]
        G2 --> H2["_recompute_spare_vectors(wing)"]
    end

    F1 --> Z["plane.updated_at = now()"]
    H2 --> Z
    Z --> Y["sync_group_for_wing — component-tree group (gh#108)"]
```

## 3. `WingModel.from_dict` — station vs segment split

```mermaid
flowchart TD
    A["from_dict(name, data)"] --> B["pop x_secs, name, units"]
    B --> C["for index, raw_xsec in enumerate(x_secs)"]
    C --> D["_extract_xsec_segment_fields:<br/>pop control_surface, trailing_edge_device,<br/>spare_list, x_sec_type, tip_type,<br/>number_interpolation_points, turbulator"]
    D --> E["_merge_ted_with_control_surface<br/>(TED wins; CS fills the gaps)"]
    E --> F{"index == last?"}
    F -->|yes| G["BLANK all six segment fields<br/>terminal station = geometry only"]
    F -->|no| H["keep segment fields"]
    G --> I["normalise airfoil reference"]
    H --> I
    I --> J["WingXSecModel(**payload, sort_index=index)"]
    J --> K["_build_xsec_detail — only if ANY segment field is non-None"]
    K --> K1["WingXSecDetailModel"]
    K1 --> K2["spares[] with sort_index"]
    K1 --> K3["_build_ted_model -> TED (+ servo_data or servo_index)"]
    K1 --> K4["_build_turbulator_model -> Turbulator"]
    K --> L["wing.x_secs.append(xsec)"]
```

## 4. Spar geometry round-trip (gh-402 / gh-1053)

```mermaid
flowchart TD
    A["create_spare / update_spare (metres in)"] --> B["_convert_spare_to_mm"]
    B --> C["INSERT wing_xsec_spares (mm)"]
    C --> D["db.flush()"]
    D --> E["_recompute_spare_vectors(wing)"]
    E --> F["wing_model_to_wing_config(wing, scale=1.0)  -> metres"]
    F --> G["_resolve_spare_vectors_and_origins"]
    G --> H{"should_preserve_normal_spare?<br/>mode=='normal' AND explicit origin AND explicit vector"}
    H -->|yes| I["_preserve_normal_spare_geometry:<br/>origin = scale_db_origin_to_config(mm, scale)<br/>vector normalised, NOT scaled"]
    H -->|no| J["CLEAR + recompute from<br/>spare_position_factor / mode<br/>(gh-352/gh-362 unit-leak guard)"]
    I --> K["segments carry solved spare geometry"]
    J --> K
    K --> L["_sync_spares_for_xsec:<br/>db_spare.spare_origin = origin_m x 1000<br/>db_spare.spare_vector = vector as-is"]
    E -.->|"ImportError (no cadquery) or FileNotFoundError (missing .dat)"| W["log warning, SKIP silently"]

    M["GET spars"] --> N["_convert_spare_to_meters x0.001"]
    N --> O["200 SpareDetailSchema (metres)"]
```

## 5. Structural spar pipeline (gh-1008 → gh-1030 → gh-1032)

```mermaid
flowchart TD
    subgraph IN["Inputs"]
        L1["spanwise bending moment M(y) — gh-1002"]
        L2["material: sigma_allow_mpa, density"]
        L3["g_limit (design assumptions), j = 1.5, packing = 0.8"]
        L4["SectionGeometry (analytic or solid)"]
    end

    L1 --> S1
    L2 --> S1
    L3 --> S1
    L4 --> S1["build_stations_from_geometry (n_span stations)"]

    S1 --> S1a["y_spans = linspace(0,1,n_span);<br/>y_spans[0] -> _ROOT_EPS = 1e-3<br/>(y=0 slice is pinched — gh-1037 #4)"]
    S1a --> S1b{"x_c given?"}
    S1b -->|no| S1c["x_c = section max-thickness location (front spar)"]
    S1b -->|yes| S1d["rear_spar_x_c_with_clearance:<br/>max( min(x_c, hinge-0.03), 0.05 )  gh-1059"]
    S1c --> S2
    S1d --> S2["per station:<br/>clr = (1-packing)/2 x thickness<br/>band = [bottom_z+clr, top_z-clr]<br/>M_design = |M| x g x j<br/>erf_W = M_design x 1000 / sigma<br/>required_od = solve_dimension('rod', erf_W)"]

    S2 --> S3["plan_spar — greedy straight-piece fit per half"]
    S3 --> S3a{"required OD fits the tightest band?"}
    S3a -->|no| S3b["split into telescoping runs<br/>(clearance 0.5 mm)"]
    S3a -->|yes| S3c["single piece"]
    S3b --> S4
    S3c --> S4{"required_od < NEGLIGIBLE_OD_FLOOR_MM = 1.0 ?"}
    S4 -->|yes| S4a["emit NO piece;<br/>report *_no_spar_from_y  (gh-1076)"]
    S4 -->|no| S5["_bore_for: erf_W = od^3/10,<br/>solve tube; fallback wall_factor 0.6"]

    S5 --> S6["solve_spar_plan"]
    S6 --> S6a{"front: _inboard_collinear<br/>(root center_z within 5 mm)?"}
    S6a -->|yes| S6b["front_joint = 'continuous'"]
    S6a -->|no, both halves exist| S6c["'reinforcement+joiner' + reinforcement piece"]
    S6a -->|single half, gh-1091| S6b
    S6 --> S6d{"rear: straight collinear rod stays in band?"}
    S6d -->|yes| S6e["rear_joint = 'continuous'"]
    S6d -->|no| S6f["rear_joint = 'bent-pin'"]

    S6b --> S7["utilisation = od / max(tightest, 1e-6)<br/>feasible = od <= tightest<br/>(>1.0 reported honestly, never clamped)"]
    S6c --> S7
    S6e --> S7
    S6f --> S7
    S7 --> S8["SparPlan -> spar_plan_service (stock snap)<br/>-> spar_insert_service (persist as Spares)"]
```

## 6. Control-surface mixing (gh-772)

```mermaid
flowchart TD
    A["TED with role + mix gains"] --> B{"role in {elevon, flaperon, ruddervator}?"}
    B -->|no — single axis| C["ONE ControlAxis<br/>name = existing tagged name<br/>sgn_dup = +1 if symmetric else -1<br/>gain = mix_gain_primary"]
    B -->|yes — dual role| D["TWO ControlAxis on the same section"]

    D --> D1["PRIMARY (symmetric)<br/>axis = pitch | lift<br/>sgn_dup = +1<br/>gain = mix_gain_primary<br/>deflection = surface deflection"]
    D --> D2["SECONDARY (antisymmetric)<br/>axis = roll | yaw<br/>sgn_dup = -1<br/>gain = mix_gain_secondary<br/>deflection = 0.0"]

    C --> E["axis_control_name:<br/>[role]axis_wingkey_xsecindex"]
    D1 --> E
    D2 --> E
    E --> F["assert_unique_control_names"]
    F -->|duplicate| G["ValueError — AVL would collapse<br/>same-named CONTROL vars into ONE DOF"]
    F -->|unique| H["AVL geometry builder / ASB airplane builder / trim enrichment"]

    I["differential_ratio"] -.->|"reporting-only kinematic,<br/>applied POST-trim for L/R display;<br/>never alters the aero solution"| H

    subgraph MAP["_DUAL_ROLE_AXES"]
        M1["elevon      -> (pitch, roll)"]
        M2["flaperon    -> (lift,  roll)"]
        M3["ruddervator -> (pitch, yaw)"]
    end
```

## 7. Turbulator optimiser (gh-934)

```mermaid
flowchart TD
    A["POST /aeroplanes/{id}/turbulator/optimize"] --> B["build_wing_section_data<br/>(from section_aoa_service)"]
    B --> C["for each section: optimize_section_xtr(airfoil, cl, re)"]
    C --> D["sweep XTR_GRID = linspace(0.2, 0.9, 15)"]
    D --> E["cd_i = _cd_at_cl_xtr(airfoil, CL, Re, xtr_i)<br/>via NeuralFoil over alpha grid linspace(-4,14,37)"]
    E --> F{"all cd NaN?"}
    F -->|yes| F1["WARNING: NeuralFoil did not converge;<br/>xtr_opt = NaN"]
    F -->|no| G["i_opt = argmin over FINITE cd"]
    G --> H["xtr_opt = XTR_GRID[i_opt]<br/>cd_tripped = cd[i_opt]<br/>cd_clean = cd(xtr_upper = 1.0)<br/>delta_cd = cd_tripped - cd_clean"]
    H --> I{"i_opt at grid boundary?"}
    I -->|yes| I1["WARNING: not an interior minimum —<br/>true optimum may lie outside [0.2, 0.9]"]
    H --> J{"mean analysis_confidence < 0.80?"}
    J -->|yes| J1["WARNING: results may be unreliable"]
    H --> K["compute_turbulator_delta_cd0:<br/>dCD0 = f x SUM(dcd_i x S_i)/S_ref<br/>f = 2 for a symmetric wing (half-span sections)"]
    K --> L["compute_ld_summary — L/D clean vs tripped"]
```
