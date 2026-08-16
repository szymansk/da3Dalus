# Flowcharts — fuselage-design

## 1. The two fuselage representations and who consumes them

```mermaid
flowchart TD
    subgraph SRC["Sources"]
        S1[".vsp3 OpenVSP import"]
        S2["STEP upload (POST /slice)"]
        S3["hand-authored xsecs (REST)"]
    end

    S1 --> A1["per-geom Surface STEP<br/>fuselages.step_path (gh-729)"]
    A1 --> A2["openvsp_solid_sewing_service<br/>sew + heal"]
    A2 --> A3["closed Solid STEP<br/>fuselages.solid_step_path (gh-731)"]
    A2 -.->|"sewing failed"| A4["solid_step_path = NULL"]

    S2 --> B1["slice_step_to_fuselage"]
    B1 --> B2["fuselage_xsecs (a, b, n)"]
    S3 --> B2
    S1 --> B2

    A3 --> C1["CAD construction pipeline:<br/>battery-bay cuts, servo unions,<br/>carbon-tube bores"]
    A1 --> C2["STEP download endpoint"]
    B2 --> C3["AeroSandbox drag / stability model"]
    B2 --> C4["viewer outline, layout, Einbauten planning"]

    note["Both representations are required:<br/>xsecs are the ONLY parametric description,<br/>STEP is the ONLY precise one.<br/>FuselageConfiguration has no xsec constructor (TODO)."]
    C1 -.- note
    C3 -.- note
```

## 2. STEP → superellipse slicing

`POST /slice` → `fuselage_slice_service.slice_step_file`

```mermaid
flowchart TD
    A["POST /slice (multipart STEP)"] --> B["lazy import cad_designer.aerosandbox.slicing"]
    B -->|ImportError| B1["InternalError: 'CadQuery is not available on this platform'"]
    B --> C["safe_name = Path(filename).name  — basename only"]
    C --> D{"suffix in .step / .stp?"}
    D -->|no| D1["ValidationError: unsupported file type"]
    D -->|yes| E["mkdtemp + write bytes"]
    E --> F{"resolved path inside temp dir?"}
    F -->|no| F1["ValidationError: path traversal detected"]
    F -->|yes| G["slice_step_to_fuselage(number_of_slices=50,<br/>points_per_slice=30, slice_axis='auto')"]
    G -->|FileNotFoundError| G1["ValidationError"]
    G -->|other Exception| G2["InternalError: slicing failed"]
    G --> H["finally: rmtree(tmp_dir)"]
    H --> I["_sanitize_float: NaN/Inf -> None (GH#301)"]
    I --> J["FuselageXSecSuperEllipseSchema per slice"]
    J --> K["FuselageSliceResponse:<br/>fuselage + original/reconstructed volume & area<br/>+ fidelity {volume_ratio, area_ratio}"]
    K --> L["tessellation URLs = None (STL export not wired)"]

    subgraph COST["CPU-bound: 5-30 s (CadQuery + scipy)"]
    end
    G -.- COST
```

## 3. Inside `slice_step_to_fuselage`

```mermaid
flowchart TD
    A["load_step_model"] --> B["_ensure_sliceable_shape"]
    B --> C{"solid or shell?"}
    C -->|solid| C1["Workplane.split(keepTop=True)"]
    C -->|shell| C2["BRepAlgoAPI_Section fallback (gh-727)"]
    C1 --> D
    C2 --> D["detect_longest_axis / slice_axis='auto'"]
    D --> E["adaptive_x_stations<br/>driven by _curvature_density"]
    E --> F["per station: slice_at_x -> outline edges"]
    F --> G["discretize_wire -> points"]
    G --> H["select_outer_contour:<br/>pick the cluster ENCLOSING the longitudinal axis"]
    H --> I["thin_oversampled_points + arc_length_weights"]
    I --> J["fit_symmetric_superellipse"]
    J --> K["xsec = {xyz, a, b, n}"]
    K --> L["fidelity metrics vs the original solid"]
```

## 4. Superellipse fitting (the maths)

```mermaid
flowchart TD
    A["2D outline points (N x 2)"] --> B["center = [0, mean(z)]<br/>— centre FORCED onto the Z axis"]
    B --> C["shifted = points - center"]
    C --> D["theta = atan2(dz, dy);  r = |shifted|"]
    D --> E["MIRROR: theta -> -theta with the same r<br/>(enforces left/right symmetry)"]
    E --> F["minimize over (a, b, n)"]

    F --> G["r_fit(theta) = ( |cos(theta)/a|^n + |sin(theta)/b|^n )^(-1/n)"]
    G --> H["radius_loss = mean( (r - r_fit)^2 )"]
    G --> I["length_loss = (perimeter_fit - perimeter_actual)^2"]
    H --> J["objective = radius_loss + 0.01 x length_loss"]
    I --> J
    J --> K["L-BFGS-B<br/>x0 = [1.0, 1.0, 2.0]<br/>bounds: a,b in (1e-3, inf), n in [0.5, 8.0]"]
    K --> L["{center, a, b, n, success, fun}"]

    subgraph MEAN["Meaning of the parameters"]
        M1["shape law: |y/a|^n + |z/b|^n = 1"]
        M2["a = Y half-axis (semi-width)  -> ASB FuselageXSec.width"]
        M3["b = Z half-axis (semi-height) -> ASB FuselageXSec.height"]
        M4["n = 2 -> ellipse;  n large -> rectangle"]
        M5["area = 4ab x Gamma(1+1/n)^2 / Gamma(1+2/n)"]
    end
```

## 5. Fuselage CRUD and its side effects

```mermaid
flowchart TD
    A["PUT /aeroplanes/{id}/fuselages/{name}"] --> B["create_fuselage"]
    B --> C{"name already used?"}
    C -->|yes| C1["ConflictError -> HTTP 409<br/>(note: create_wing raises ValidationError -> 422)"]
    C -->|no| D["FuselageModel.from_dict — xsecs get sort_index"]
    D --> E["plane.updated_at = now()"]
    E --> F["sync_group_for_fuselage — component tree (gh#108)"]
    F --> G["db.flush()"]

    H["POST .../fuselages/{name}"] --> I["update_fuselage"]
    I --> J["DESTRUCTIVE REPLACE:<br/>remove old FuselageModel, append a new one"]
    J -.->|"consequence"| J1["step_path / solid_step_path not in the<br/>payload are LOST"]
    J --> E

    K["DELETE .../fuselages/{name}"] --> L["db.delete(fuselage)<br/>xsecs cascade"]
    L --> M["delete_synced_nodes('fuselage:{name}')"]
    M --> E
```

## 6. `symmetric` — the XZ-mirror flag (gh-715)

```mermaid
flowchart LR
    A["fuselages.symmetric"] --> B{"True?"}
    B -->|"False (DEFAULT)"| C["single body — the main fuselage<br/>sits ON the symmetry plane"]
    B -->|True| D["downstream consumers duplicate with y -> -y"]
    D --> D1["ASB converter (_fuselage_configs_with_mirrors)"]
    D --> D2["CAD builder"]
    D --> D3["3D viewer"]
    D -.-> E["use case: landing-gear struts, wheel fairings,<br/>engine cowlings — OpenVSP stores only one side"]

    F["wings.symmetric default = True"] -.->|"opposite default — deliberate"| A
```
