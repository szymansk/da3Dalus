# CAD Engine (`cad_designer/`)

## Overview
The CAD engine uses CadQuery to generate parametric 3D geometry for aircraft components.
It follows a construction-tree pattern where shapes are built step-by-step.

## Key Abstractions

### AbstractShapeCreator (`airplane/AbstractShapeCreator.py`)
Base class for all CAD operations. Subclasses implement `_create_shape()` and define
`shapes_of_interest_keys` for their outputs. New creators MUST inherit from this.

### ConstructionStepNode / ConstructionRootNode
Tree structure for CAD construction sequences. Each node wraps a Creator and manages
input/output shape flow.

### GeneralJSONEncoderDecoder
Serialization for the construction tree. **READ-ONLY — never modify.**

## Creator Categories

### Wing Creators (`creator/wing/`)
- `WingLoftCreator` — main wing surface loft from cross-sections
- `VaseModeWingCreator` — hollow wing for 3D printing
- `StandWingSegmentOnPrinterCreator` — orient for print bed
- `ted_sketch_creators` — trailing edge device geometry

### Fuselage Creators (`creator/fuselage/`)
- `FuselageShellShapeCreator` — main fuselage shell
- `FuselageReinforcementShapeCreator` — structural reinforcement
- `EngineMountShapeCreator`, `EngineCapeShapeCreator` — engine integration
- Various cutout creators for access panels, bolt holes, etc.

### CAD Operations (`creator/cad_operations/`)
- Boolean ops: Fuse, Cut, Intersect (2-shape and multi-shape variants)
- `ScaleRotateTranslateCreator` — transform operations
- `SimpleOffsetShapeCreator` — shell offset
- `RepairFacesShapeCreator` — topology repair

### Export/Import (`creator/export_import/`)
- STEP, IGES, STL, 3MF export and STEP/IGES import

### Component Creators (`creator/components/`)
- `ServoImporterCreator` — import servo STEP models
- `ComponentImporterCreator` — import generic component STEP models

## Aircraft Topology (`airplane/aircraft_topology/`) — READ-ONLY
Domain model classes representing aircraft geometry in mm units:
- `WingConfiguration`, `WingSegment`, `Airfoil`, `Spare`, `TrailingEdgeDevice`
- `FuselageConfiguration`
- `AirplaneConfiguration`
- `Servo`, `ComponentInformation`, `EngineInformation`
- `Printer3dSettings`, `Position`, `CoordinateSystem`

## Aerosandbox Integration (`aerosandbox/`)
- `convert2aerosandbox.py` — convert topology to ASB geometry (mm→m)
- `aerodynamic_calculations.py` — VLM analysis via Aerosandbox
- `slicing.py` — wing slicing for analysis
- `classification.py` — airfoil classification
- `wing_roundtrip.py` — DB ↔ ASB wing roundtrip conversion

## CQ Plugins (`cq_plugins/`)
CadQuery extension plugins: wing loft, 3D offset, scale XYZ, shape repair, etc.
