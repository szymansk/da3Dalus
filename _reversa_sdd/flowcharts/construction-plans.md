# Flowcharts — construction-plans

## 1. The domain — three different things called "construction"

```mermaid
flowchart TD
    subgraph P["construction_plans table"]
        P1["plan_type = 'template'<br/>aeroplane_id NULL<br/>reusable build recipe"]
        P2["plan_type = 'plan'<br/>aeroplane_id set<br/>a template bound to one aeroplane"]
        P1 -->|"instantiate_template — deepcopy tree_json"| P2
        P2 -->|"to_template — deepcopy tree_json"| P1
    end

    subgraph R["construction_parts table"]
        R1["per-aeroplane uploaded CAD part<br/>STEP/STL + geometry metadata + locked flag"]
    end

    subgraph S["spar plan (NOT this table)"]
        S1["spar_plan_service → SparPlan → spar_insert_service<br/>writes wing_xsec_spares rows"]
    end

    P2 -.->|"execution writes files, never rows"| A["artifact directory"]
    R1 -.->|"component_tree.construction_part_id FK"| CT["component_tree node"]
    S1 -.->|"documented under Module: wing-design"| N["Cluster A"]
```

## 2. Plan execution — non-streaming

```mermaid
flowchart TD
    A["POST /construction-plans/{id}/execute<br/>or /aeroplanes/{aid}/construction-plans/{id}/execute"] --> B["_get_plan_or_raise"]
    B --> C["effective_aeroplane_id = plan.aeroplane_id or request.aeroplane_id"]
    C --> D{"plan_type == 'template' and no aeroplane_id?"}
    D -->|yes| D1["ValidationError 422"]
    D -->|no| E["get_aeroplane_or_raise"]
    E --> F{"plan_type"}
    F -->|template| F1["create_template_execution_dir<br/>rmtree _template_runs/{id} first"]
    F -->|plan| F2["create_execution_dir<br/>&lt;aeroplane&gt;/&lt;plan&gt;/&lt;exec_id&gt;"]
    F1 --> G
    F2 --> G["wing_config = {name: wing_model_to_wing_config(wing, scale=1000.0)}<br/>per-wing failure → warning only, wing dropped"]
    G --> H["_load_printer_settings — components row of type<br/>'printer_settings' else 0.24 / 0.42 / 0.075"]
    H --> I["_rewrite_export_paths<br/>relative file_path on the 4 export creators<br/>→ artifact_dir/fp  (+ mkdir)"]
    I --> J["json.loads(cls=GeneralJSONDecoder,<br/>wing_config, printer_settings,<br/>servo_information={}, engine_information=None,<br/>component_information=None)"]
    J -->|failure| J1["ValidationError 'Failed to decode construction plan'"]
    J --> K["root_node.create_shape()  — IN-PROCESS, no chdir"]
    K -->|exception| K1["ExecutionResult(status='error', error, duration_ms,<br/>artifact_dir, execution_id)"]
    K --> L["_tessellate_shapes — best-effort"]
    L --> M["ExecutionResult(status='success', shape_keys,<br/>tessellation, artifact_dir, execution_id)"]
```

## 3. Streaming execution — SSE and its global side effects

```mermaid
flowchart TD
    A["GET /aeroplanes/{aid}/construction-plans/{id}/execute-stream"] --> B["same setup as §2"]
    B --> C["set_display_callback(on_display)  ← MODULE GLOBAL"]
    C --> D["os.environ['DISPLAY_CONSTRUCTION_STEP'] = '1'  ← PROCESS GLOBAL"]
    D --> E["threading.Thread(run, daemon=True).start()"]

    E --> F["root_node.create_shape()"]
    F --> G["every Workplane.display(...) inside a Creator<br/>→ on_display(name, tessellation)"]
    G --> H["shape_queue.put(('shape', name, _numpy_to_list(t)))"]

    I["generator loop: shape_queue.get(timeout=300)"]
    H --> I
    I -->|"queue.Empty"| I1["event: error {'error': 'Execution timed out'}"]
    I -->|"('shape', …)"| I2["event: shape {'name','tessellation'}"]
    I -->|"('done', …)"| I3["event: complete {duration_ms, shape_keys,<br/>tessellation, artifact_dir, execution_id}<br/>OR event: error"]
    I3 --> J["thread.join(timeout=5)"]

    K["finally: restore DISPLAY_CONSTRUCTION_STEP,<br/>set_display_callback(None)"]
    F --> K

    X["two concurrent streams share the callback AND the env var<br/>→ shape events can be delivered to the wrong stream"]
    C -.- X
    D -.- X
```

## 4. Creator Catalog — reflection into the frontend gallery

```mermaid
flowchart TD
    A["GET /construction-plans/creators"] --> B["import AbstractShapeCreator<br/>ImportError → [] (aarch64 without CadQuery)"]
    B --> C["import cad_designer.airplane.creator  — registers subclasses"]
    C --> D["walk AbstractShapeCreator.__subclasses__() recursively"]
    D --> E{"name in {ConstructionRootNode,<br/>ConstructionStepNode, JSONStepNode}?"}
    E -->|yes| E1["skip the class, still recurse into its subclasses"]
    E -->|no| F["inspect.signature(cls.__init__)"]
    F --> G["drop _INTERNAL_PARAMS:<br/>self, loglevel, kwargs, creator_id,<br/>wing_config, printer_settings, servo_information,<br/>engine_information, component_information"]
    G --> H["CreatorParam{name, type, default, required,<br/>description, options}"]
    H --> H1["type via _type_to_str — generics BEFORE __name__,<br/>strips 'typing.' and 'cad_designer.airplane.types.'"]
    H --> H2["options via _extract_literal_values —<br/>Literal / Optional[Literal] / Annotated[Literal]"]
    H --> H3["description from the docstring 'Attributes:' section<br/>lines 'name (type): text'"]
    F --> I["description = first line of the class docstring"]
    F --> J["outputs from the 'Returns:' section, keys like {id}.cape"]
    F --> K["suggested_id = cls.suggested_creator_id (may contain {param})"]
    I --> L["CreatorInfo sorted by (category, class_name)"]
    J --> L
    K --> L
    G --> L
    M["category from the module path: '.creator.wing' → wing,<br/>fuselage, cad_operations, export_import, components, else 'other'"]
    L -.- M
```

## 5. Artifact browsing and download

```mermaid
flowchart TD
    A["GET /construction-plans/{id}/artifacts"] --> A1["list_executions — scans EVERY &lt;aero&gt;/&lt;plan_id&gt;/*<br/>including _template_runs (unlike _resolve_execution_dir)"]
    B["GET .../artifacts/{exec_id}"] --> B1["list_files(subpath, recursive)"]
    C["GET .../artifacts/{exec_id}/zip"] --> C1["zip_execution → tempfile ZIP_DEFLATED,<br/>arcnames relative to the exec dir; empty → valid empty zip"]
    D["GET .../artifacts/{exec_id}/{filename:path}"] --> D1["get_file_path — _ensure_within_base<br/>+ reject symlinks"]
    E["DELETE .../artifacts/{exec_id}/{filename:path}"] --> E1["delete_file"]
    F["DELETE .../artifacts/{exec_id}"] --> F1["delete_execution — rmtree"]

    G["_resolve_execution_dir:<br/>1) scan &lt;aero&gt;/&lt;plan_id&gt;/&lt;exec&gt; skipping _template_runs<br/>2) fall back to _template_runs/&lt;plan_id&gt;/&lt;exec&gt;"]
    B1 -.- G
    C1 -.- G
    D1 -.- G
```

## 6. Construction parts — upload lifecycle

```mermaid
flowchart TD
    A["POST /aeroplanes/{aid}/construction-parts (multipart)"] --> B["_validate_upload"]
    B -->|empty| B1["ValidationError 422"]
    B -->|"&gt; 50 MB"| B2["ConflictError details.reason='file_too_large' → 413"]
    B -->|"suffix ∉ {.step,.stp,.stl}"| B3["ValidationError 422"]
    B --> C["insert row, db.flush() to get part.id"]
    C --> D["_store_file → tmp/construction_parts/{aeroplane}/{id}_{uuid8}{ext}"]
    D --> E{"cad_available() and format == 'step'?"}
    E -->|no| E1["geometry fields stay NULL<br/>(STL volume needs a mesh lib — documented MVP limit)"]
    E -->|yes| F["cq.importers.importStep → Volume / Area / BoundingBox<br/>each guarded individually"]
    F --> G["volume_mm3, area_mm2, bbox_x/y/z_mm"]
    E1 --> H
    G --> H["ConstructionPartRead"]

    I["GET .../{id}/file?format=stl on a STEP source"] --> I1["regenerate via cq.exporters.export to a mkstemp .stl<br/>(temp file is never cleaned up)"]
    J["GET .../{id}/file?format=step on an STL source"] --> J1["ValidationError — STEP cannot be regenerated"]
    K["DELETE .../{id}"] --> K1{"locked?"}
    K1 -->|yes| K2["ConflictError 409 — unlock first"]
    K1 -->|no| K3["db.delete + os.unlink BEFORE the commit<br/>(documented trade-off)"]
```

## 7. REST surface

```mermaid
flowchart LR
    subgraph Plans["/construction-plans"]
        A1["GET /creators"]
        A2["GET · POST /"]
        A3["GET · PUT · DELETE /{plan_id}"]
        A4["POST /{plan_id}/execute"]
        A5["GET /{plan_id}/artifacts"]
        A6["GET /{plan_id}/artifacts/{exec}"]
        A7["GET /{plan_id}/artifacts/{exec}/zip"]
        A8["GET · DELETE /{plan_id}/artifacts/{exec}/{filename:path}"]
        A9["DELETE /{plan_id}/artifacts/{exec}"]
    end
    subgraph Aero["/aeroplanes/{aeroplane_id}/construction-plans"]
        B1["GET /"]
        B2["POST /from-template/{template_id}"]
        B3["POST /{plan_id}/execute"]
        B4["GET /{plan_id}/execute-stream  (SSE)"]
        B5["POST /{plan_id}/to-template"]
    end
    subgraph Tpl["/construction-templates"]
        C1["GET /"]
        C2["POST /"]
    end
    subgraph Parts["/aeroplanes/{aeroplane_id}/construction-parts"]
        D1["GET /  ·  POST /"]
        D2["GET · PUT · DELETE /{part_id}"]
        D3["PUT /{part_id}/lock  ·  PUT /{part_id}/unlock"]
        D4["GET /{part_id}/file"]
    end
```
