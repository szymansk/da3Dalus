# Flowcharts — cad-generation

## 1. The two CAD execution models — and why they differ

```mermaid
flowchart TD
    subgraph A["cad_service / tessellation_service — PROCESS pool"]
        A1["REST call"] --> A2["parent: build blueprint dict<br/>+ pickle AsbWingSchema"]
        A2 --> A3["ProcessPoolExecutor<br/>max_workers=4, mp_context=spawn"]
        A3 --> A4["worker: rebuild WingConfiguration<br/>run CadQuery / OCCT"]
        A4 --> A5["return picklable result dict"]
        A5 --> A6["parent: future.add_done_callback<br/>writes into tasks{}"]
    end

    subgraph B["construction_plan_service — IN-PROCESS thread"]
        B1["POST /execute or /execute-stream"] --> B2["GeneralJSONDecoder<br/>builds live Creator tree"]
        B2 --> B3["root_node.create_shape<br/>SAME process, daemon thread for SSE"]
        B3 --> B4["ocp_tessellate + SSE events"]
    end

    R["cad_service module docstring:<br/>OCCT is NOT thread-safe.<br/>intersect().clean() hangs in a worker thread<br/>because OCCT holds global state."]
    A3 -.-|"documented rationale"| R
    B3 -.-|"CONTRADICTS the same rationale"| R
```

## 2. Wing export — `POST /aeroplanes/{id}/wings/{name}/{creator}/{exporter}`

```mermaid
flowchart TD
    A["POST .../{creator_url_type}/{exporter_url_type}"] --> B["get_aeroplane_with_wings<br/>joinedload xsecs→detail→spares / TED→servo"]
    B --> C["get_wing_from_aeroplane"]
    C --> D["check_task_available<br/>tasks[aeroplane_id] running? → ConflictError 409"]
    D --> E["register_pending_task → status PENDING"]
    E --> F["map_exporter_type"]
    F -->|"stl / step / iges"| G["build_wing_blueprint"]
    F -->|"3mf"| F1["returns 'ExportTo3MFCreator'<br/>real class is ExportTo3mfCreator → decode AttributeError"]
    F -->|"amf"| F2["not in the mapping → ValidationError 422<br/>although the enum advertises it"]

    G --> H["_convert_wing_to_pickle<br/>wing_model_to_asb_wing_schema + pickle.dumps"]
    H --> I["_extract_aeroplane_settings<br/>servo dicts + pickled Printer3dSettings"]
    I --> J["_get_executor().submit(_run_construction_worker,<br/>wing_scale = 1000.0)"]
    J --> K["202 ACCEPTED + CadTaskAcceptedResponse"]

    J --> L["worker: unpickle → asb_wing_schema_to_wing_config<br/>rebuild ServoInformation locally"]
    L --> M["json.loads(blueprint, cls=GeneralJSONDecoder,<br/>wing_config / fuselage_config / servo_information / printer_settings)"]
    M --> N["blue_print.create_shape()"]
    N --> O["zip ./tmp/exports/* → ./tmp/{aeroplane_id}.zip<br/>then unlink every file in exports"]
    O --> P["{status: SUCCESS, result: {zipfile}}"]

    Q["GET .../status"] --> Q1["get_task_result — RUNNING when future.running()"]
    S["GET .../zip"] --> S1["get_export_file_path + _ensure_file_under_tmp"]
```

## 3. `./tmp/exports` is a shared mutable directory

```mermaid
flowchart LR
    W1["worker A — aeroplane 1"] --> D["./tmp/exports"]
    W2["worker B — aeroplane 2"] --> D
    D --> Z1["A zips EVERYTHING in exports<br/>then unlinks EVERYTHING"]
    D --> Z2["B's partial output is zipped into A's archive<br/>and/or deleted before B finishes"]
    N["check_task_available is per-aeroplane only —<br/>it never serialises across different aeroplanes,<br/>and the pool has 4 workers"]
    Z2 -.- N
```

## 4. Tessellation — request path and cache

```mermaid
flowchart TD
    A["POST /aeroplanes/{id}/wings/{name}/tessellation"] --> B["wing_model_to_asb_wing_schema → pickle"]
    B --> C["start_tessellation_task"]
    C --> C1["register_pending_task<br/>key = '{uuid}:tessellation:{wing}'<br/>NOTE: no check_task_available here"]
    C1 --> D["_get_executor().submit(_run_tessellation_worker,<br/>wing_scale = 1000.0)"]

    D --> E["worker: asb_wing_schema_to_wing_config(scale=1000)"]
    E --> F["WingLoftCreator(creator_id='tessellation',<br/>wing_side='BOTH')._create_shape(...)<br/>— calls the PRIVATE hook, bypassing create_shape()"]
    F --> G["ocp_tessellate.to_ocpgroup<br/>names=[wing], colors=['#FF8400'], alphas=[1.0]"]
    G --> H["tessellate_group(params = {deviation: 0.1,<br/>angular_tolerance: 0.2})"]
    H --> I["shapes['bb'] = combined_bb(shapes).to_dict()<br/>→ keys xmin/xmax/ymin/ymax/zmin/zmax"]
    I --> J["_numpy_to_list → JSON-safe"]
    J --> K["{data:{instances,shapes}, type:'data',<br/>config:{theme:dark, control:orbit}, count}"]

    K --> L["_on_done callback"]
    L --> M["tasks[key] = worker_result"]
    L --> N["own SessionLocal → cache_tessellation(<br/>aeroplane.id, 'wing', wing_name,<br/>geometry_hash or 'manual') + commit"]
```

## 5. Cache lifecycle and the debounce

```mermaid
flowchart TD
    A["wing geometry write"] --> B["tessellation_hooks.on_wing_changed"]
    B --> C["cache_svc.invalidate(aeroplane.id, 'wing', name)<br/>UPDATE ... SET is_stale = 1"]
    C --> D["GH #202 — background re-tessellation NOT wired<br/>(literal comment in the hook)"]

    E["trigger_background_tessellation<br/>(exists, currently unreachable from the hook)"] --> F["cancel pending threading.Timer for key"]
    F --> G["cancel in-flight Future for key"]
    G --> H["new Timer(_DEBOUNCE_SECONDS = 2.0, daemon)"]
    H --> I["_start_tessellation_and_cache → pool"]
    I --> J{"is_hash_current(geometry_hash)?"}
    J -->|no| J1["discard — geometry changed while tessellating"]
    J -->|yes| J2["cache_tessellation + commit"]

    K["compute_geometry_hash(data) =<br/>sha256(json.dumps(data, sort_keys=True, default=str))[:16]"]
    C -.- K
    J -.- K
```

## 6. Scene assembly — `GET /aeroplanes/{id}/tessellation`

```mermaid
flowchart TD
    A["GET /aeroplanes/{id}/tessellation"] --> B["get_all_cached(aeroplane.id)"]
    B -->|empty| B1["404 — no cached tessellations"]
    B --> C["_merge_tessellation_entries"]
    C --> D["per entry: deepcopy(shapes)<br/>colour '#FF8400' for wing else '#888888'"]
    D --> E["_offset_refs(shapes, len(combined_instances))<br/>— rebase every {ref: N} into the merged instance array"]
    E --> F["_expand_bounding_box(bb_min, bb_max, shapes)"]
    F --> F1{"entry_bb has keys 'min' and 'max'?"}
    F1 -->|"NO — worker wrote xmin/xmax/…"| F2["early return, bb never expands"]
    F2 --> G["combined_bb falls back to<br/>{min:[0,0,0], max:[0,0,0]}"]
    E --> H["scene: {data:{shapes:{version:3, name, id,<br/>parts[], loc, bb}, instances}, count, is_stale}"]
    G --> H

    H --> I["CadViewer.tsx: structuredClone + resolveRefs<br/>instances[shape.ref] inlined client-side"]
    I --> J["tcv.Display + tcv.Viewer<br/>up='Z', theme='dark', tools=true, treeWidth=200"]
    J --> K["viewer.addPart(rootId, shapes, {skipBounds:true})<br/>for every part after the first"]
```

## 7. Artifact directory layout

```mermaid
flowchart TD
    R["ARTIFACTS_BASE_DIR (default /tmp/da3dalus_artifacts, always .resolve()d)"]
    R --> P["&lt;aeroplane_id&gt;/&lt;plan_id&gt;/&lt;execution_id&gt;/  — plan runs"]
    R --> T["_template_runs/&lt;template_id&gt;/&lt;execution_id&gt;/  — template runs (wiped on next run)"]
    R --> S["openvsp_imports/&lt;aeroplane_uuid&gt;/  — per-geom STEP + _solid.stp"]

    X["execution_id = UTC '%Y%m%dT%H%M%SZ'<br/>+ '-N' suffix on same-second collision<br/>(module-global counter — per-process only)"]
    P -.- X
    T -.- X

    G["every path goes through _ensure_within_base:<br/>resolve() then relative_to(base) → ValidationError on escape"]
    G -.- P
    G -.- T

    O["NOT under ARTIFACTS_BASE_DIR:<br/>./tmp/exports, ./tmp/{aeroplane}.zip (cad_service)<br/>tmp/construction_parts/{aeroplane}/ (construction_part_service)"]
```
