# da3Dalus — Project Overview

**da3Dalus** is an aircraft design toolchain with a Python backend and a React frontend.

## Backend (`app/`) — FastAPI service
- Generates parametric aircraft CAD (wings, fuselages, assemblies) using **CadQuery**
- Runs aerodynamic analysis (vortex lattice, stability, operating point sweeps) using **Aerosandbox** + vendored **AVL** binary
- Persists projects, aeroplanes, wings, analyses via **SQLAlchemy** + **Alembic** migrations
- REST API (v2 current, v1 legacy) + **MCP server** (FastMCP) for AI-agent integration

## Frontend (`frontend/`) — Next.js 16 App Router + React 19
- Interactive workbench for aircraft design (wing editor, component tree, analysis dashboards)
- 3D CAD viewer via **Three.js** (`@react-three/fiber` + `drei`)
- Aerodynamic charts via **Plotly** (`plotly.js-gl3d-dist-min`)
- Data fetching with **SWR**, styling with **Tailwind CSS**
- Dark theme with orange accent (`#FF8400`), fonts: JetBrains Mono + Geist

## Tech Stack
- **Python 3.11–3.13**, managed with **Poetry 2.x**
- **FastAPI** + **Pydantic v2** + **SQLAlchemy** + **Alembic**
- **Next.js 16** + **React 19** + **TypeScript** + **Tailwind CSS**
- **CadQuery** for CAD geometry, **Aerosandbox** for aero analysis
- **pytest** for backend tests, **vitest** for frontend unit tests, **Playwright** for E2E

## Codebase Structure
```
app/
├── main.py              # FastAPI entrypoint + router wiring
├── mcp_server.py        # FastMCP server
├── api/v2/endpoints/    # Current API, grouped by domain
├── services/            # Business logic, CAD orchestration
├── models/              # SQLAlchemy ORM models
├── schemas/             # Pydantic request/response DTOs
├── converters/          # schema ⇄ model ⇄ CAD transforms
├── core/                # Config, logging, exceptions
├── db/                  # SQLAlchemy session + engine
└── tests/               # pytest test modules

alembic/                 # DB migrations
cad_designer/            # CadQuery primitives, plugins, decorators
components/              # Airfoils, servos, templates (data)
frontend/                # Next.js App Router frontend
```
