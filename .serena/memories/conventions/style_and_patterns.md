# Code Style and Conventions

## Python Backend

### Architecture
- **Layered:** endpoint (thin) → service (business logic) → model/schema/converter
- Endpoints validate + delegate; no DB queries or CAD calls in endpoints
- Services hold business logic, CAD orchestration, transactions
- `wing_service` uses `with db.begin():` for all writes

### Type Hints
- Type-annotate every public function
- Use `from __future__ import annotations` for forward refs
- Prefer `list[str]` / `dict[str, int]` over `List`/`Dict` (Python 3.11+)
- Use `Optional[X]` or `X | None` consistently within a file

### Pydantic
- Inherit from `pydantic.BaseModel` (v2)
- Use `Field(..., description=...)` for API models
- Validators on the schema, not in endpoints

### SQLAlchemy
- Query via injected session from `app/db/`
- Commit in service layer, not endpoints
- Always add Alembic migration when changing a model

### Style
- PEP 8, line-length 100 (Ruff)
- Absolute imports (`app.` or `cad_designer.`), no relative
- No `print()` — use `logging` module
- Docstrings: short, focused on *why* not *what*

### Testing
- Test modules in `app/tests/test_*.py`
- Use fixtures for TestClient and DB session
- Markers: unit, integration, slow, requires_cadquery, requires_aerosandbox, requires_avl
- pytest-timeout: 360s per test, faulthandler at 300s
- Coverage target: 70–80%

### Security
- Secrets in `.env`, read via pydantic-settings
- Never log credentials
- Sanitize user input before shell commands (no `shell=True` with interpolation)
- Path safety: always resolve + containment check

## Frontend

### Framework
- Next.js 16 App Router (NOT Pages Router)
- React 19, TypeScript
- All API calls go through the backend (no direct CORS)

### Component Patterns
- Reuse existing components before creating new ones
- Key reusable components: TreeCard, SimpleTreeRow, AirfoilSelector, Field, GroupAddMenu
- Click-dummy for major UI changes before implementing real logic
- Dark theme with orange accent (#FF8400)

### Data Fetching
- SWR hooks in `frontend/hooks/`
- Plotly for all analysis charts (dynamic import `plotly.js-gl3d-dist-min`)

### Testing
- Vitest for unit tests
- Playwright + playwright-bdd for E2E
- dependency-cruiser for architecture checks

## cad_designer Rules
- `aircraft_topology/` classes are READ-ONLY (never modify)
- `GeneralJSONEncoderDecoder` is READ-ONLY
- New Creators (subclasses of AbstractShapeCreator) ARE allowed
- Use `_creator_template.py` as starting point for new creators
- Units in topology: millimetres; in DB/ASB: metres
