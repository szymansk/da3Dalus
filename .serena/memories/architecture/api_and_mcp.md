# API and MCP Architecture

## REST API (v2)
- Current API version: v2 (`app/api/v2/endpoints/`)
- v1 is legacy — new endpoints go in v2
- Endpoints are thin: validate → delegate to service → return Pydantic response

### Key endpoint groups:
- `aeroplane.py` — Aeroplane CRUD
- `aeroplane/wings.py` — Wing management (segments, cross-sections, spars, TEDs)
- `aeroplane/fuselages.py` — Fuselage management
- `aeroplane/component_tree.py` — Component tree with weight enrichment
- `aeroplane/construction_parts.py` — Construction part management (STEP files)
- `aeroplane/design_versions.py` — Design version tracking
- `aeroplane/weight_items.py` — Weight items
- `aeroplane/powertrain_sizing.py` — Powertrain sizing
- `aeroplane/mission_objectives.py` — Mission objectives
- `aeroanalysis.py` — Aerodynamic analysis (alpha sweep, parameter sweep, operating points)
- `cad.py` — CAD export (STEP, STL, 3MF)
- `construction_plans.py` — Construction plan CRUD
- `construction_templates.py` — Construction templates
- `operating_points.py` — Operating point management
- `flight_profiles.py` — Flight profile management
- `airfoils.py` — Airfoil data management
- `fuselage_slice.py` — Fuselage cross-section slicing
- `component_types.py` — Component type catalog (COTS, custom)
- `components.py` — Component instances

## MCP Server
- ~80+ MCP tools defined in `app/mcp_server.py`
- Uses `@mcp_tool` decorator pattern with `MCPToolSpec` dataclass
- Same host/port as REST API, mounted at `/mcp`
- FastMCP 3.x (Streamable HTTP transport)
- Asset registry for serving images/data from MCP responses
- Tools mirror REST endpoints but tailored for AI agent interaction
