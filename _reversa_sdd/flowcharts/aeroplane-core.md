# Flowcharts — aeroplane-core

## 1. Aeroplane creation (with versioning lineage)

`POST /aeroplanes` → `aeroplane_service.create_aeroplane`

```mermaid
flowchart TD
    A["POST /aeroplanes?name=..."] --> B["create_aeroplane(db, name)"]
    B --> C["INSERT aeroplanes<br/>is_immutable = False"]
    C --> D["db.flush() — obtain aeroplane.id"]
    D --> E["aeroplane.root_id = aeroplane.id<br/>(lineage root points at itself)"]
    E --> F["db.flush()"]
    F --> G["INSERT branches<br/>root_id = head_id = aeroplane.id<br/>name='main', is_main=True<br/>created_by='human'"]
    G --> H["db.flush() — obtain branch.id"]
    H --> I["aeroplane.branch_id = branch.id"]
    I --> J["db.refresh(aeroplane)"]
    J --> K["201 CreateAeroplaneResponse(id=uuid)"]
    C -. "SQLAlchemyError" .-> X["InternalError -> HTTP 500"]

    subgraph DDL["Why the flush dance"]
        Y["aeroplanes.branch_id -> branches.id"]
        Z["branches.root_id / head_id -> aeroplanes.id"]
        Y -. "circular FK, resolved with use_alter=True" .- Z
    end
```

## 2. Full aeroplane read

`GET /aeroplanes/{id}` → `aeroplane_service.get_aeroplane_schema`

```mermaid
flowchart TD
    A["GET /aeroplanes/{uuid}"] --> B["get_aeroplane_by_uuid"]
    B -->|not found| E404["NotFoundError -> 404"]
    B --> C["Materialise lazy relations INSIDE the session"]
    C --> C1["for wing in wings:<br/>for xsec in x_secs:<br/>touch detail.spares<br/>touch ted.servo_data"]
    C1 --> D["OrderedDict wings: name -> AsbWingSchema"]
    D --> F["OrderedDict fuselages: name -> FuselageSchema"]
    F --> G["AeroplaneSchema(name, xyz_ref, wings, fuselages)"]
    G --> H["200 JSON"]

    note["Materialisation is required because FastAPI serialises<br/>AFTER get_db() closes the session"]
    C1 -.- note
```

## 3. AirplaneConfiguration export (CAD assembly)

`GET /aeroplanes/{id}/airplane_configuration`

```mermaid
flowchart TD
    A["GET .../airplane_configuration"] --> B["get_aeroplane_by_uuid"]
    B --> C{"total_mass_kg set?"}
    C -->|no| V["ValidationError -> HTTP 422"]
    C -->|yes| D["for each wing:<br/>wing_model_to_wing_config(wing)"]
    D -->|exception| E1["InternalError 'Wing data conversion failed'"]
    D --> E["fuselages present?"]
    E -->|yes| F["fuselage_model_to_fuselage_config(each)"]
    E -->|no| G["fuselage_configurations = None"]
    F -->|exception| E2["InternalError 'Fuselage data conversion failed'"]
    F --> H["AirplaneConfiguration(name, total_mass_kg, wings, fuselages)"]
    G --> H
    H --> I["to_dict()"]
    I --> J["_to_json_compatible:<br/>ndarray -> list, np.generic -> scalar"]
    J --> K["200 AirplaneConfigurationResponse"]
```

## 4. Component-tree weight roll-up

`GET /aeroplanes/{id}/component-tree` → `component_tree_service.get_tree`

```mermaid
flowchart TD
    A["get_tree(db, aeroplane_id)"] --> B["SELECT component_tree<br/>WHERE aeroplane_id ORDER BY sort_index"]
    B --> C["_build_tree — flat list to nested"]
    C --> C1["map id -> node"]
    C1 --> C2["attach child to parent_id;<br/>missing parent => treated as ROOT"]
    C2 --> C3["sort children and roots by sort_index"]
    C3 --> D["Pre-compute own_weights for ALL nodes<br/>(one pass, avoids N queries)"]
    D --> E["_roll_up_weights(root) — post-order"]
    E --> F["ComponentTreeResponse(root_nodes, total_nodes)"]

    subgraph OWN["_calculate_own_weight — precedence chain"]
        O1{"weight_override_g set?"} -->|yes| OA["source = 'override'"]
        O1 -->|no| O2{"node_type == 'cots'<br/>and component.mass_g?"}
        O2 -->|yes| OB["mass_g x quantity<br/>source = 'cots'"]
        O2 -->|no| O3{"node_type == 'cad_shape'<br/>and material density?"}
        O3 -->|"print_type == 'surface'"| OC["area_mm2 x print_resolution_mm x density / 1e6 x scale_factor"]
        O3 -->|"volume"| OD["volume_mm3 x density / 1e6 x scale_factor"]
        O3 -->|no| OE["(None, 'none')"]
    end

    subgraph ROLL["_roll_up_weights — status algebra"]
        R0["total = own + SUM(children totals)"]
        R1{"leaf?"} -->|yes| R2["valid if own else invalid"]
        R1 -->|no| R3{"all children valid?"}
        R3 -->|yes| R4["valid"]
        R3 -->|no| R5{"all children invalid?"}
        R5 -->|yes| R6["partial if own else invalid"]
        R5 -->|no| R7["partial"]
    end

    D -.- OWN
    E -.- ROLL
```

## 5. Component-tree mutation and its side effects

```mermaid
flowchart TD
    A["add_node / update_node / delete_node / move_node"] --> B{"operation"}

    B -->|add| C{"parent_id given?"}
    C -->|yes| C1["_validate_parent_exists<br/>else NotFoundError"]
    C --> D{"construction_part_id given?"}
    D -->|yes| D1["_snapshot_construction_part_fields<br/>copy volume/area/material ONLY for<br/>fields not explicitly passed"]
    D --> E["INSERT node"]

    B -->|move| M1{"new parent is a descendant<br/>of the moved node?"}
    M1 -->|yes| M2["ValidationError<br/>'Cannot move a node under its own subtree'"]
    M1 -->|no| M3["set parent_id + sort_index"]

    B -->|delete| N1["_delete_subtree — recursive child delete"]
    N1 --> N2["db.delete(node)"]

    E --> Z["_sync_aircraft_mass"]
    M3 --> Z
    N2 --> Z
    Z --> Z1["lazy import mass_cg_service.sync_component_tree_to_mass"]
    Z1 --> Z2{"raised?"}
    Z2 -->|yes| Z3["log warning ONLY —<br/>never blocks the CRUD operation"]
    Z2 -->|no| Z4["mass assumption updated"]
```

## 6. Domain-error to HTTP mapping

```mermaid
flowchart LR
    S["service raises ServiceException"] --> M["_raise_http_from_domain"]
    M -->|NotFoundError| H404["404"]
    M -->|"ValidationError / ValidationDomainError"| H422["422"]
    M -->|ConflictError| H409["409"]
    M -->|InternalError| H500["500"]
    M -->|other ServiceException| H500
    E["any other Exception"] --> H500b["500 'Unexpected error'"]
```
