# Codebase Structure

## Backend (`app/`)
Layered FastAPI application: **endpoint → service → model/schema/converter**

```
app/
├── main.py                  # FastAPI entrypoint, router wiring, exception handlers
├── mcp_server.py            # FastMCP server with ~80+ MCP tools (same host/port)
├── settings.py              # App settings
├── logging_config.py        # Logging setup
├── api/v2/endpoints/        # REST API v2 (current), grouped by domain
│   ├── aeroplane.py         # Aeroplane CRUD
│   ├── aeroplane/           # Sub-endpoints: wings, fuselages, components, etc.
│   ├── aeroanalysis.py      # Aerodynamic analysis endpoints
│   ├── cad.py               # CAD export endpoints
│   ├── construction_plans.py # Construction plan management
│   ├── construction_templates.py
│   ├── operating_points.py  # Operating point management
│   ├── flight_profiles.py
│   ├── airfoils.py
│   └── ...
├── services/                # Business logic, CAD orchestration
│   ├── wing_service.py      # Wing CRUD + CAD (uses `with db.begin()`)
│   ├── cad_service.py       # CAD export orchestration
│   ├── analysis_service.py  # Aero analysis orchestration
│   ├── stability_service.py # Stability analysis
│   ├── construction_plan_service.py
│   ├── tessellation_service.py
│   └── ~25 more services
├── models/                  # SQLAlchemy ORM models
│   ├── aeroplanemodel.py, airfoil.py, component.py, component_tree.py
│   ├── construction_plan.py, construction_part.py, tessellation_cache.py
│   └── flightprofilemodel.py, analysismodels.py
├── schemas/                 # Pydantic request/response DTOs (~24 files)
├── converters/              # schema ⇄ model ⇄ CAD transforms
│   └── model_schema_converters.py
├── core/                    # Config, logging, exceptions, security, platform
├── db/                      # SQLAlchemy session, engine, repository, exceptions
└── tests/                   # ~80+ pytest test modules + fixtures/
```

## CAD Engine (`cad_designer/`)
```
cad_designer/
├── airplane/
│   ├── AbstractShapeCreator.py      # Base class for all shape creators
│   ├── ConstructionStepNode.py      # Construction tree node
│   ├── ConstructionRootNode.py      # Root of construction tree
│   ├── GeneralJSONEncoderDecoder.py # JSON serialization (READ-ONLY)
│   ├── creator/                     # Shape creators (subclass AbstractShapeCreator)
│   │   ├── wing/                    # Wing loft, vase mode, TED sketches
│   │   ├── fuselage/                # Fuselage shell, reinforcement, cutouts
│   │   ├── components/              # Servo/component importers
│   │   ├── cad_operations/          # Boolean ops (fuse, cut, intersect, scale)
│   │   ├── export_import/           # STEP/IGES/STL/3MF export/import
│   │   └── _creator_template.py     # Template for new creators
│   └── aircraft_topology/           # Domain model classes (READ-ONLY)
│       ├── wing/                    # WingConfig, WingSegment, Airfoil, Spare, TED
│       ├── fuselage/                # FuselageConfiguration
│       ├── airplane/                # AirplaneConfiguration
│       ├── components/              # Servo, ComponentInformation
│       └── Position.py
├── aerosandbox/                     # ASB integration, wing roundtrip, slicing
├── decorators/                      # general_decorators.py
└── cq_plugins/                      # CadQuery plugins (wing, offset3D, scale, etc.)
```

**IMPORTANT:** `aircraft_topology/` and `GeneralJSONEncoderDecoder` are read-only. New Creators are allowed.

## Frontend (`frontend/`)
```
frontend/
├── app/                    # Next.js App Router pages
│   ├── page.tsx            # Landing/project list
│   ├── layout.tsx          # Root layout
│   └── workbench/          # Main design workbench
│       ├── page.tsx        # Wing editor / main view
│       ├── layout.tsx      # Workbench layout
│       ├── analysis/       # Aero analysis tab
│       ├── construction-plans/  # Construction plan management
│       ├── mission/        # Mission objectives
│       ├── components/     # Component catalog
│       └── airfoil-preview/ # Airfoil geometry viewer
├── components/workbench/   # ~47 UI components
│   ├── TreeCard.tsx, SimpleTreeRow.tsx    # Reusable tree panels
│   ├── AirfoilSelector.tsx               # Searchable dropdown
│   ├── CadViewer.tsx                     # 3D Three.js viewer
│   ├── AnalysisViewerPanel.tsx           # Analysis results display
│   ├── ConfigPanel.tsx                   # Wing config editor
│   ├── ComponentTree.tsx                 # Component tree with DnD
│   └── ...
├── hooks/                  # ~20 SWR data hooks
│   ├── useWings.ts, useWingConfig.ts
│   ├── useAeroplanes.ts, useFuselages.ts
│   ├── useAnalysis.ts, useStripForces.ts
│   ├── useConstructionPlans.ts, useConstructionParts.ts
│   └── ...
├── lib/                    # Shared utilities
├── e2e/                    # Playwright BDD E2E tests
└── __tests__/              # Vitest unit tests
```

## Data (`components/`)
Static data files: airfoils (.dat), servos, lipo specs, brushless motors, CPACS files, test files.

## Other
- `alembic/` — DB migration scripts
- `Avl/` — Vendored AVL (Athena Vortex Lattice) source + binary
- `planning/`, `docs/`, `images/`, `screenshots/` — Documentation assets
