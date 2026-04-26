# Domain Model

## Core Entities (SQLAlchemy models in `app/models/`)

### Aeroplane (`aeroplanemodel.py`)
Top-level entity. Contains wings, fuselages, flight profiles, weight items, and is associated with analysis results.

### Wing (managed by `wing_service.py`)
Defined by WingConfiguration topology (from `cad_designer/airplane/aircraft_topology/wing/`):
- **WingSegment** — individual wing panel with span, sweep, dihedral, taper
- **Airfoil** — airfoil profile (from .dat files in `components/airfoils/`)
- **Spare** (spar) — structural spar within a segment
- **TrailingEdgeDevice** (TED) — flap/aileron with hinge line, deflection
- **Servo** — servo motor attached to a TED
- **CoordinateSystem** — wing coordinate frame

### Fuselage
- **FuselageConfiguration** — fuselage shape defined by cross-sections

### Component System
- **ComponentType** (`component_type.py`) — catalog of part types (COTS, custom)
- **Component** (`component.py`) — instances placed in the design
- **ComponentTree** (`component_tree.py`) — hierarchical assembly tree with weight

### Construction
- **ConstructionPlan** (`construction_plan.py`) — plan for manufacturing
- **ConstructionPart** (`construction_part.py`) — individual manufactured part (STEP file)

### Analysis
- **AnalysisModels** (`analysismodels.py`) — stored analysis results
- **FlightProfile** (`flightprofilemodel.py`) — mission flight profile

### Other
- **TessellationCache** (`tessellation_cache.py`) — cached mesh data for 3D viewer
- **DesignVersion** — version tracking for aeroplane designs

## Converters (`app/converters/model_schema_converters.py`)
Single file handling all model ↔ schema conversions. Key conversions:
- Wing DB model ↔ WingConfiguration topology ↔ Pydantic schemas
- Scale factors: mm→m (0.001) for DB storage, m→mm (1000.0) for topology
