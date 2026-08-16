# Flowcharts — avl-integration

## 1. When AVL runs at all (project rule: prefer AeroSandbox)

```mermaid
flowchart TD
    A["caller"] --> B{"which path?"}

    B --> C1["alpha_sweep / simple_sweep"]
    C1 --> D1["AEROBUILDUP — hard-coded<br/>(AVL cannot do array sweeps)"]

    B --> C2["streamlines / four-view"]
    C2 --> D2["VORTEX_LATTICE — hard-coded"]

    B --> C3["recompute_assumptions (gh-924 context)"]
    C3 --> D3["AEROBUILDUP — hard-coded"]

    B --> C4["OP generation + background retrim"]
    C4 --> D4["asb.Opti / AeroBuildup — hard-coded"]

    B --> C5["strip forces / spanwise loads"]
    C5 --> E1{"solver param"}
    E1 -->|"'vlm' (DEFAULT)"| D5["in-process ASB VLM"]
    E1 -->|"'avl'"| F["AVL subprocess"]

    B --> C6["analyze_wing / analyze_airplane / stability_summary"]
    C6 --> E2{"analysis_tool"}
    E2 -->|aerobuildup / vortex_lattice| D6["ASB"]
    E2 -->|avl| F

    B --> C7["POST .../trim/avl"]
    C7 --> F

    F --> G["AVL's genuine advantages:<br/>native indirect constraints,<br/>per-section CDCL viscous polars,<br/>roll/yaw axis of MIXED surfaces"]
```

## 2. Building the `.avl` file

```mermaid
flowchart TD
    A["build_avl_geometry_file(plane_schema, spacing_config)"] --> B["aeroplane_schema_to_asb_airplane_async<br/>-> s_ref, c_ref, b_ref"]
    B --> C["AvlReference(s_ref, c_ref, b_ref, xyz_ref)"]
    C --> D["for each wing"]

    D --> E["_build_controls_for_wing (gh-772)"]
    E --> E1["axes_for_xsec -> ControlAxis list"]
    E1 --> E2{"dual role? (elevon | flaperon | ruddervator)"}
    E2 -->|yes| E3["TWO CONTROL vars:<br/>[role]pitch|lift_… SgnDup=+1 (symmetric)<br/>[role]roll|yaw_… SgnDup=−1 (antisymmetric, deflection=0)"]
    E2 -->|no| E4["ONE CONTROL var: existing tagged name, SgnDup = ±1"]
    E3 --> E5["append to section i AND i+1<br/>(AVL interpolates across the panel strip)"]
    E4 --> E5

    D --> F["_build_section per xsec"]
    F --> F1{"name matches ^naca\\s*(\\d{4,5})$ ?"}
    F1 -->|yes| F2["AvlNaca(digits)"]
    F1 -->|no| F3["_resolve_airfoil_reference -> is a file?"]
    F3 -->|yes| F4["AvlAfile(path)"]
    F3 -->|no| F5["AvlNaca('0012') fallback"]
    F --> F6["CLAF = 1 + 0.77·max_thickness (default 1.0 on failure)"]
    F --> F7["CDCL = AvlCdcl.zeros() placeholder"]

    E5 --> G["AvlSurface(name, n_chord, c_space, sections,<br/>yduplicate = 0.0 if wing.symmetric else None)"]
    F2 --> G
    F4 --> G
    F5 --> G

    G --> H["optimise_surface_spacing"]
    H --> I["assert_unique_control_names ACROSS surfaces<br/>(dedup within a surface first — panel duplication is legitimate)"]
    I -->|duplicate| X["ValueError: names would collapse into ONE AVL DOF<br/>(avl_doc 778-789)"]
    I -->|ok| J["AvlGeometryFile(title, mach=0, symmetry, reference, surfaces)"]
    J --> K["repr(file) == the .avl text"]

    note["gh-588: the old regex \\d{4,5}(?:\\.\\d+)? routed 'naca23013.5'<br/>into AvlNaca and crashed AVL with 'Read error on line N'.<br/>Decimal names are custom .dat files -> AFIL."]
    F1 -.- note
```

## 3. Panel-spacing rules (`optimise_surface_spacing`)

```mermaid
flowchart TD
    A["SpacingConfig: n_chord 12, c_space 1.0, n_span 20, s_space 1.0"] --> B{"auto_optimise?"}
    B -->|no| Z["apply config verbatim"]
    B -->|yes| C{"any section has controls?"}
    C -->|yes| C1["n_chord = max(n_chord, 16)  — hinge-line resolution"]
    C -->|no| D
    C1 --> D{"unswept AND no centreline break?"}
    D --> D1["unswept: atan2(dx, sqrt(dy²+dz²)) < 5°"]
    D --> D2["centreline break: any INTERIOR section at |y| < 1e-6"]
    D -->|yes| D3["s_space = −2.0  (−sine: panels at root and tip,<br/>where the induced-drag gradient is steepest)"]
    D -->|no| E
    D3 --> E["n_span = max(n_span, ceil(span / min_gap) + 2)"]
    E --> E1["min_gap ignores COINCIDENT sections (gap <= 1e-9)<br/>so a chord/twist discontinuity cannot force n_span -> infinity"]
    E1 --> Z2["surface copy with adjusted panelling"]

    why["gh-590: without the n_span bump AVL aborts with<br/>'Cannot adjust spanwise spacing at section N' /<br/>'Insufficient number of spanwise vortices'"]
    E -.- why
```

## 4. CDCL injection via NeuralFoil

```mermaid
flowchart TD
    A["inject_cdcl(avl_file, plane_schema, op, cdcl_config)"] --> B{"len(surfaces) == len(wings)?"}
    B -->|no| B1["WARN only — injection may be incomplete, loop truncates"]
    B -->|yes| C["for surface i, section j"]
    B1 --> C
    C --> D{"section.cdcl present AND not all-zero?"}
    D -->|yes| D1["PRESERVE (user-edited values win)"]
    D -->|no| E["Re = V · chord / nu(altitude)   (asb.Atmosphere)"]
    E --> F["_get_polar_data  @lru_cache(maxsize=128)<br/>key = (airfoil NAME, Re, mach, alpha range, model_size,<br/>n_crit, xtr_upper, xtr_lower, include_360)"]
    F --> G["airfoil.get_aero_from_neuralfoil(alpha sweep)"]
    G --> H{"all CL/CD finite?"}
    H -->|no| H1["WARN + return ZERO CDCL"]
    H -->|yes| I["3-point fit"]
    I --> I1["point 2 (bucket): argmin(CD) -> (cl_0, cd_0)"]
    I --> I2["point 3 (+stall): argmax(CL) -> (cl_max, cd_max)"]
    I --> I3["point 1 (−stall): argmin(CL) -> (cl_min, cd_min)"]
    I1 --> J["AvlCdcl emitted as 'CL1 CD1  CL2 CD2  CL3 CD3'"]
    I2 --> J
    I3 --> J
    H1 --> J
```

## 5. AVLRunner — keystrokes, subprocess, parsing

```mermaid
flowchart TD
    A["AVLRunner.run(avl_file_content, overrides, include_strip_forces, extra_ks)"] --> B["working dir: caller-supplied OR TemporaryDirectory"]
    B --> C["write airplane.avl"]
    C --> D["_build_keystrokes"]

    D --> D1["OPER"]
    D1 --> D2["m -> mn <mach>, v <V>, d <rho>, g 9.81, (blank)"]
    D2 --> D3["a a <alpha> ; b b <beta><br/>r r <p·b/2V> ; p p <q·c/2V> ; y y <r·b/2V><br/>(V=0 with non-zero rates -> WARN, rates zeroed)"]
    D3 --> D4["build_control_deflection_commands:<br/>first occurrence of each name -> d1 d1 δ1, d2 d2 δ2, …<br/>(same order as get_control_surface_index_map)"]
    D4 --> D5["extra_keystrokes (trim constraints)"]
    D5 --> D6["x  (execute)"]
    D6 --> D7["st output.txt o   (stability file, overwrite)"]
    D7 --> D8{"include_strip_forces?"}
    D8 -->|yes| D9["fs  (strip forces to STDOUT)"]
    D8 -->|no| D10["quit"]
    D9 --> D10

    D10 --> E["Popen([avl_command, 'airplane.avl'], piped stdio)"]
    E --> F{"communicate(timeout)"}
    F -->|TimeoutExpired| X1["kill + RuntimeError('AVL timed out after Ns')"]
    F -->|returncode != 0| F1["log warning ONLY — AVL routinely exits non-zero"]
    F --> G{"output.txt exists?"}
    G -->|no| X2["FileNotFoundError + first 500 chars of stdout as hint"]
    G -->|yes| H["parse_stability_output(raw)"]

    H --> H1["scan for ' = ' ; key read BACKWARDS, value FORWARDS<br/>float() or NaN ; FIRST occurrence wins"]
    H1 --> I["_post_process_results"]
    I --> I1["lowercase Alpha/Beta/Mach ; strip 'tot' suffix (CLtot -> CL)"]
    I1 --> I2["p = (pb/2V)·2V/b ; q = (qc/2V)·2V/c ; r = (rb/2V)·2V/b"]
    I2 --> I3["L=q·S·CL, Y=q·S·CY, D=q·S·CD<br/>l_b=q·S·b·Cl, m_b=q·S·c·Cm, n_b=q·S·b·Cn"]
    I3 --> I4["spiral parameter Clb·Cnr/(Clr·Cnb)  (NaN on ZeroDivisionError)"]
    I4 --> I5["F_w=[−D, Y, −L] -> F_b -> F_g ; M_b -> M_g, M_w  (op.convert_axes)"]

    I5 --> J{"include_strip_forces?"}
    J -->|yes| K["parse_strip_forces_output(stdout)"]
    J -->|no| L["result dict"]
    K --> L
    L --> M["finally: TemporaryDirectory cleanup"]
```

## 6. Strip-forces stdout parser (line state machine)

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> InSurface: Surface-header line matched, push a new surface dict
    InSurface --> InSurface: Chordwise / Spanwise counts parsed into metadata
    InSurface --> InSurface: Surface area Ssurf parsed into metadata
    InSurface --> InTable: header starts with j AND contains Xle AND cl
    InTable --> InTable: line starts with a digit, split into the 15 STRIP_COLUMNS
    InTable --> InSurface: blank line closes the table
    InTable --> InSurface: next Surface header
    InSurface --> [*]: EOF
```

## 7. Indirect-constraint trim and replay safety

```mermaid
flowchart TD
    A["POST .../trim/avl  (AVLTrimRequest)"] --> B["get_user_avl_content(db, uuid)"]
    B -->|"None (no row, not user-edited, or dirty)"| B1["build_avl_geometry_file + inject_cdcl -> fresh content"]
    B -->|content| C
    B1 --> C["AVLRunner(timeout=60)"]
    C --> D["build_indirect_constraint_commands"]
    D --> D1["alpha->a, beta->b, roll_rate->r, pitch_rate->p, yaw_rate->y"]
    D --> D2["control-surface name -> d{index} from get_control_surface_index_map"]
    D --> D3["unknown -> ValueError listing both valid sets"]
    D1 --> E["'<var> <target> <value>'  e.g. 'd1 PM 0'"]
    D2 --> E
    E --> F["run_trim -> run(extra_keystrokes = constraints)"]
    F --> G["_categorize_results(raw, control_names)"]
    G --> G1["aero / forces / state / derivatives / deflections buckets"]
    G1 --> H{"converged = ('CL' in raw)"}
    H -->|False| H1["WARN with the raw key list"]
    H -->|True| I["compute_enrichment (best-effort; failure only warns)"]
    I --> J["AVLTrimResult"]
    H1 --> J

    subgraph REPLAY["gh-529 replay safety (built, not yet wired into a production path)"]
        R1["build_avl_artefact(airplane, alpha, beta, V, x_cg, deflections)"]
        R2["index_snapshot: name_to_index, yduplicate_sign,<br/>geometry_hash = sha256(wing/xsec order + name+symmetric+hinge_point)<br/>COORDINATES DELIBERATELY EXCLUDED"]
        R3["verify_avl_replay(airplane, artefact)"]
        R4["geometry_hash_mismatch OR index_map_drift -> HARD FAIL:<br/>replaying against drifted geometry silently mis-maps surfaces"]
        R1 --> R2 --> R3 --> R4
    end
```

## 8. Stored geometry file lifecycle

```mermaid
stateDiagram-v2
    [*] --> NoRow: aeroplane created
    NoRow --> Clean: PUT avl_geometry, is_user_edited true, is_dirty false
    Clean --> Dirty: wing / xsec / fuselage write sets is_dirty true
    Dirty --> Clean: PUT again, the user re-saves
    Dirty --> NoRow: POST regenerate, the row is DELETED
    Clean --> NoRow: POST regenerate or DELETE
    NoRow --> NoRow: GET generates on the fly, nothing persisted

    note right of Dirty
        get_user_avl_content returns content ONLY when
        is_user_edited AND NOT is_dirty.
        Otherwise every solver path regenerates.
        is_dirty is never auto-cleared.
    end note
```
