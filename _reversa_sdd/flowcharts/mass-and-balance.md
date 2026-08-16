# Flowcharts — mass-and-balance

## 1. The two mass producers and the one CG rule

```mermaid
flowchart TD
    subgraph PRODUCERS["Mass producers (both write the SAME column)"]
        WI["weight_items (flat inventory)<br/>name, mass_kg, x_m/y_m/z_m, category"]
        CT["component_tree (hierarchical)<br/>CAD shapes + COTS components + overrides"]
    end

    WI -->|"any POST/PUT/DELETE<br/>weight_items_service._try_sync_assumptions"| S1["sync_weight_items_to_assumptions"]
    CT -->|"any tree mutation<br/>component_tree_service._sync_aircraft_mass"| S2["sync_component_tree_to_mass"]

    S1 -->|"aggregate_weight_items -> total_mass<br/>source = 'weight_items'"| UPD
    S2 -->|"get_aircraft_total_weight_kg -> total_kg<br/>source = 'component_tree'"| UPD

    UPD["update_calculated_value(db, uuid, 'mass',<br/>value, source, auto_switch_source=True)"]
    UPD --> DA["design_assumptions['mass']<br/>calculated_value + calculated_source<br/>active_source flips to CALCULATED on first sync"]

    DA --> EV1["mark_ops_dirty(aeroplane.id)"]
    DA --> EV2["event_bus.publish(AssumptionChanged('mass'))"]
    EV2 --> RC["assumption_compute_service<br/>retrim + V_stall recompute"]

    RC --> NP["x_np, MAC, target_static_margin"]
    NP --> CGA["CG_aero = x_np - SM * MAC<br/>WRITTEN to assumption 'cg_x'"]

    WI -.->|"aggregate_weight_items"| CGG["CG_agg (mass-weighted)<br/>NEVER written to cg_x (gh-465)"]
    CT -.->|"loading_scenario_service<br/>compute_cg_agg_for_aeroplane"| CGG
    CGG --> CTX["assumption_computation_context.cg_agg_m<br/>comparison only"]

    CGA --> CMP["get_cg_comparison<br/>delta_x = cg_x_design - CG_agg_x<br/>within_tolerance = |delta_x| < 0.01 m"]
    CGG --> CMP

    note["Top-down, not bottom-up: stability DEMANDS the CG;<br/>the component sum only REPORTS where it currently is."]
    CGA -.- note
```

## 2. Last-write-wins between the two producers

```mermaid
sequenceDiagram
    participant U as User
    participant WIS as weight_items_service
    participant CTS as component_tree_service
    participant MCG as mass_cg_service
    participant DA as design_assumptions['mass']

    U->>WIS: POST /weight-items (battery 0.30 kg)
    WIS->>MCG: sync_weight_items_to_assumptions
    MCG->>DA: calculated_value = 0.30, source = "weight_items"
    Note over DA: active_source auto-switches to CALCULATED

    U->>CTS: POST /component-tree (add a wing shape)
    CTS->>MCG: sync_component_tree_to_mass
    MCG->>DA: calculated_value = 1.85, source = "component_tree"
    Note over DA: the weight_items value is GONE — no warning,<br/>only calculated_source records who won
```

## 3. `sync_*` — the shared five-step shape

```mermaid
flowchart TD
    A["sync_component_tree_to_mass / sync_weight_items_to_assumptions"] --> B{"aeroplane found by UUID?"}
    B -->|no| B1["raise NotFoundError"]
    B -->|yes| C{"design_assumptions row 'mass' exists?"}
    C -->|no| C1["return — NO-OP<br/>(aircraft not seeded yet)"]
    C -->|yes| D["aggregate the source"]
    D --> E{"source empty?"}
    E -->|yes| E1["total = None, source = None<br/>-> clears calculated_value"]
    E -->|no| E2["total = value, source = 'weight_items' | 'component_tree'"]
    E1 --> F
    E2 --> F["update_calculated_value(auto_switch_source=True)"]
    F --> G["mark_ops_dirty"]
    G --> H["publish AssumptionChanged('mass')"]

    style B1 fill:#511,color:#fff
    style C1 fill:#530,color:#fff
```

Both call sites swallow their exceptions on purpose — `_try_sync_assumptions`
catches `NotFoundError`/`SQLAlchemyError`, `_sync_aircraft_mass` catches
`Exception` — so a failed sync never blocks the CRUD operation that triggered
it. A persistently failing sync is visible only in the log. 🔴

## 4. Component-tree weight ladder (per node)

```mermaid
flowchart TD
    N["_calculate_own_weight(node)"] --> A{"weight_override_g is not None?"}
    A -->|yes| A1["return (override, 'override')<br/>the USER always wins"]
    A -->|no| B{"COTS component linked?"}
    B -->|yes| B1["return (components.mass_g x quantity, 'cots')"]
    B -->|no| C{"CAD shape with volume + material?"}
    C -->|yes| C1["return (volume_mm3 x density, 'calculated')"]
    C -->|no| C2["return (None, 'none')  — mass UNKNOWN"]

    A1 --> R["get_aircraft_total_weight_kg:<br/>sum over ROOT nodes (parent_id IS NULL)<br/>own + recursive children, / 1000"]
    B1 --> R
    C1 --> R
    C2 --> R
    R --> R1{"total_g > 0?"}
    R1 -->|yes| R2["total_kg"]
    R1 -->|no| R3["None — caller CLEARS calculated_value<br/>(never asserts a 0 kg aircraft)"]
```

## 5. `design_metrics` — the only ASB-touching route

```mermaid
flowchart LR
    REQ["POST /aeroplanes/{uuid}/design_metrics<br/>{velocity, altitude}"] --> M["mass = effective assumption 'mass'"]
    REQ --> CL["cl_max = effective assumption 'cl_max'"]
    REQ --> S["get_s_ref_for_aeroplane:<br/>build the FULL ASB airplane, read s_ref"]
    REQ --> RHO["rho = asb.Atmosphere(altitude).density()"]

    M --> C["compute_design_metrics"]
    CL --> C
    S --> C
    RHO --> C

    C --> O["W = m*g (g = 9.81)<br/>W/S = W / S_ref<br/>V_stall = sqrt(2W / (rho*S*CL_max))<br/>q = 0.5*rho*V^2<br/>CL_req = W / (q*S)<br/>CL_margin = CL_max - CL_req"]

    C -.->|"any input <= 0"| ERR["ValidationError -> 422<br/>(no silent clamp)"]
    S -.->|"s_ref <= 0"| ERR2["ValidationError:<br/>'add wings first'"]
```
