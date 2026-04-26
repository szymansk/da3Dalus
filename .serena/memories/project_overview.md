# da3Dalus — CAD Modelling Service

## Purpose
da3Dalus is an aircraft design toolchain with a Python backend (FastAPI) and React frontend (Next.js 16).
It generates parametric aircraft CAD geometry (wings, fuselages, assemblies) using CadQuery, runs aerodynamic
analysis (vortex lattice method via AVL, stability, operating point sweeps) using Aerosandbox, and persists
projects via SQLAlchemy + Alembic migrations.

## Tech Stack

### Backend (Python 3.11–3.13, Poetry 2.x)
- **Framework:** FastAPI
- **ORM:** SQLAlchemy + Alembic migrations
- **Schemas:** Pydantic v2
- **CAD Engine:** CadQuery (parametric 3D geometry)
- **Aero Analysis:** Aerosandbox (VLM) + vendored AVL binary (`Avl/`)
- **MCP Server:** FastMCP 3.x (same host/port as REST)
- **Config:** pydantic-settings (`app/core/config.py`)
- **Linting:** Ruff (line-length 100, target py311)
- **Testing:** pytest with markers (unit, integration, slow, requires_cadquery, etc.)

### Frontend (Next.js 16 App Router + React 19)
- **3D Viewer:** Three.js (`@react-three/fiber`, `three-cad-viewer`)
- **Charts:** Plotly (`plotly.js-gl3d-dist-min`)
- **Data Fetching:** SWR
- **Styling:** Tailwind CSS v4, dark theme with orange accent (#FF8400)
- **Fonts:** JetBrains Mono + Geist
- **DnD:** @dnd-kit
- **Testing:** Vitest (unit), Playwright + playwright-bdd (E2E)
- **Lint:** ESLint, dependency-cruiser

### Infrastructure
- Docker + docker-compose (port 8086)
- Azure Pipelines CI
- SonarQube (project key: `szymansk_da3Dalus`)
- Git remote named `github` (not `origin`)

## Units Convention
- **WingConfig / topology classes:** millimetres (mm)
- **Database / Aerosandbox:** metres (m)
- Conversion in converters via `scale=0.001` (mm→m) and `scale=1000.0` (m→mm)

## Platform Guards
`cadquery` and `aerosandbox` are excluded on `linux/aarch64`. Code importing them must handle `ImportError`.
