# Flowcharts — cad-designer-topology

## 1. Package map — what is frozen and what is not

```mermaid
flowchart TD
    subgraph FROZEN["🚫 read-only by project rule"]
        T1["aircraft_topology/wing/<br/>Airfoil, WingSegment, WingConfiguration,<br/>Spare, TrailingEdgeDevice, Turbulator, CoordinateSystem"]
        T2["aircraft_topology/components/<br/>Servo, ComponentInformation,<br/>ServoInformation, EngineInformation"]
        T3["aircraft_topology/airplane/AirplaneConfiguration<br/>aircraft_topology/fuselage/FuselageConfiguration"]
        T4["GeneralJSONEncoderDecoder.py — the serialisation contract"]
    end

    subgraph OPEN["✅ additions / edits allowed"]
        C1["airplane/creator/** — new Creators<br/>(start from _creator_template.py)"]
        C2["airplane/geometry/**<br/>section_geometry, segment_split,<br/>spar_solver, spar_cad_insertion"]
        C3["cq_plugins/**, decorators/**"]
    end

    E["gh-934 approved exception:<br/>Turbulator + the turbulator param on<br/>WingSegment / WingConfiguration"]
    E -.-> T1

    Q["sonar.exclusions = cad_designer/**<br/>ruff extend-exclude = cad_designer<br/>→ ~22k LOC unlinted and unmeasured"]
    Q -.- FROZEN
```

## 2. The Creator contract — `AbstractShapeCreator`

```mermaid
flowchart TD
    A["create_shape(input_shapes, **kwargs)  ← public template method"] --> B{"shapes_of_interest_keys is None?"}
    B -->|yes| B1["shapes_of_interest = None"]
    B -->|no| C["return_needed_shapes(...)"]

    C --> C1{"count(None slots) &gt; len(input_shapes)?"}
    C1 -->|yes| C2["KeyError: less input_shapes than shapes_needed"]
    C1 -->|no| C3["fill each None slot from<br/>reversed(input_shapes.keys())<br/>— most significant LAST"]
    C3 --> C4["check_if_shapes_are_available(**kwargs)<br/>→ KeyError naming the missing keys"]

    B1 --> D
    C4 --> D["save root logger level;<br/>if self.loglevel &lt; effective: setLevel(self.loglevel)"]
    D --> E["_create_shape(shapes_of_interest, input_shapes, **kwargs)  ← subclass hook"]
    E --> F["restore the previous root logger level"]
    F --> G["return dict[ShapeId, Workplane]"]

    N["side effect: the root logger level is mutated<br/>process-wide for the duration of the step"]
    D -.- N

    K["output-key convention<br/>{identifier} · {identifier}.name · {identifier}[i]"]
    G -.- K
```

## 3. Plan tree execution — depth-first with a growing kwargs registry

```mermaid
flowchart TD
    A["ConstructionRootNode.create_shape()"] --> B["_create_shape: for each successor<br/>kwargs.update(succ.create_shape(input_shapes={}, **kwargs))"]
    B --> C["ConstructionStepNode._create_shape"]
    C --> D["output_shapes = self.creator.create_shape(input_shapes, **kwargs)"]
    D --> E["_input_shapes = input_shapes.copy()<br/>delete keys that were just re-created<br/>then update → newest keys land LAST"]
    E --> F["kwargs.update(output_shapes)"]
    F --> G["for each successor:<br/>kwargs.update(succ.create_shape(_input_shapes, **kwargs))"]
    G --> H["return kwargs — every shape produced so far"]

    R["the ROOT hands every top-level successor input_shapes={},<br/>a StepNode hands its children the ordered _input_shapes.<br/>Ordering matters: None slots resolve from the END."]
    B -.- R

    I["identifier collision = silent overwrite<br/>(documented on AbstractShapeCreator.identifier)"]
    F -.- I
```

## 4. Two independent serialisation systems

```mermaid
flowchart TD
    subgraph S1["System 1 — plan tree ($TYPE envelope)"]
        A1["GeneralJSONEncoder.default<br/>public attrs only (no leading _)<br/>+ '$TYPE' = o.__class__.__name__"]
        A1 --> A2["construction_plans.tree_json (DB)<br/>components/constructions/*.json (files)"]
        A2 --> A3["GeneralJSONDecoder.object_hook"]
        A3 --> A4["cls = getattr(sys.modules['…GeneralJSONEncoderDecoder'], $TYPE)"]
        A4 --> A5{"'kwargs' in __init__ signature?"}
        A5 -->|yes| A6["pass the whole dict + all decoder kwargs"]
        A5 -->|no| A7["intersect dict keys ∩ init params,<br/>then overlay matching decoder kwargs"]
        A6 --> A8["_coerce_params: str→float/int/bool/str by annotation,<br/>locale-aware ('1.234,56' → 1234.56),<br/>str→[str] when the annotation is list[...]"]
        A7 --> A8
        A8 --> A9["resolve {placeholder} in creator_id<br/>from sibling param values"]
        A9 --> A10["cls(**params)"]
    end

    subgraph S2["System 2 — topology objects (no type marker)"]
        B1["__getstate__() → plain dict"]
        B2["from_json_dict(data) → instance"]
        B1 --- B2
        B3["WingConfiguration, WingSegment, Airfoil, Spare,<br/>TrailingEdgeDevice, Turbulator, Servo,<br/>CoordinateSystem, AirplaneConfiguration, FuselageConfiguration"]
    end

    X["Topology objects NEVER appear in a plan JSON.<br/>They are injected as decoder kwargs at execution time<br/>(wing_config, printer_settings, servo_information, …)<br/>and stored as PRIVATE self._foo so the encoder skips them."]
    S1 -.- X
    S2 -.- X
```

## 5. Class resolution — why a new Creator must be exported

```mermaid
flowchart TD
    A["GeneralJSONEncoderDecoder.py imports"] --> B["ConstructionRootNode, ConstructionStepNode"]
    A --> C["from cad_designer.airplane.creator import *"]
    A --> D["import cad_designer.cq_plugins"]
    C --> C1["creator/__init__: cad_operations, components,<br/>export_import, fuselage, wing — each an explicit re-export list"]
    B --> E["module namespace = the ONLY resolvable $TYPE set"]
    C1 --> E
    E --> F["getattr(module, name) → AttributeError if absent"]

    G["consequence 1: a new Creator not listed in its<br/>subpackage __init__.py cannot be decoded"]
    H["consequence 2: renaming or deleting a Creator breaks<br/>every stored plan referencing the old $TYPE"]
    F --> G
    F --> H

    I["verified today: 9 of 32 $TYPE names used by<br/>components/constructions/*.json no longer exist —<br/>wings.root.json, fuselage.root.json and full_wing.json<br/>cannot be decoded"]
    H -.- I
```

## 6. `cq_plugins` — what gets monkey-patched onto CadQuery

```mermaid
flowchart LR
    A["import cad_designer.cq_plugins"] --> B["Workplane.fix_shape"]
    A --> C["Workplane.offset3D"]
    A --> D["Workplane.display  (gated by @conditional_execute('DISPLAY_CONSTRUCTION_STEP'))"]
    A --> E["Workplane.sewAndFix"]
    A --> F["Workplane.airfoil / .wing_root_segment / .wing_segment"]
    A --> G["Sketch.segmentToEdge  (via segmentToEdge/__init__)"]

    H["scaleXyz/__init__ registers Workplane.scaleXyz<br/>but cq_plugins/__init__ never imports it<br/>and nothing else does → never registered"]
    A -.-|"NOT wired"| H
```

## 7. Where the spar/geometry pipeline sits

```mermaid
flowchart TD
    A["app/services/spar_sizing.py — section modulus"] --> B["cad_designer/airplane/geometry/spar_solver.py<br/>CAD-free layout decision logic"]
    B --> C["app/services/spar_plan_service.py — SparPlan"]
    C --> D["app/services/spar_insert_service.py"]
    D --> E["cad_designer/airplane/geometry/segment_split.py<br/>geometrically transparent split of a ruled loft"]
    D --> F["persisted Spare rows on wing_xsec_spares (mm)"]
    B --> G["cad_designer/airplane/geometry/section_geometry.py<br/>analytic (default) vs solid slice"]

    N["Full formulas, thresholds and the joint rules are documented<br/>in code-analysis.md → Module: wing-design (Cluster A).<br/>This module only records that geometry/ is EDITABLE<br/>feature code, unlike the frozen topology classes."]
    B -.- N
```
