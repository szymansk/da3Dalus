# Code Style & Conventions

## Python (Backend)
- **PEP 8**, line length 100
- Type-annotate every public function
- Use `from __future__ import annotations` for forward references
- Prefer `list[str]` / `dict[str, int]` over `List` / `Dict` (Python 3.11+)
- Docstrings on public functions — short, focused on *why*
- No `print()` — use `logging` module with `app/logging_config.py`
- Absolute imports: `app.` or `cad_designer.` (not relative `..foo`)
- Standard library → third-party → local, separated by blank lines

## Architecture Layers
```
endpoint (app/api/v2/endpoints/) → service (app/services/)
                                 → model (app/models/) — SQLAlchemy
                                 → schema (app/schemas/) — Pydantic
                                 → converter (app/converters/)
```
- **Endpoints are thin**: validate → delegate to service → return Pydantic response
- **Services hold business logic**: orchestration, CAD calls, transactions
- **Schemas are Pydantic v2**: `Field(..., description=...)` for Swagger/MCP
- **Validators belong on the schema**, not in the endpoint
- Commit in service layer, not endpoint

## Units Convention
- **WingConfig / topology classes**: millimetres
- **Database / Aerosandbox**: metres
- Conversion via converters: `scale=0.001` (mm→m), `scale=1000.0` (m→mm)

## cad_designer/ Rules
- Existing topology classes are **read-only** (never modify)
- New Creators (subclasses of `AbstractShapeCreator`) are allowed
- Use `cad_designer/airplane/creator/_creator_template.py` as starting point

## Frontend (TypeScript/React)
- **App Router** (not Pages Router)
- All API calls go through the backend (no direct CORS calls)
- Dark theme with orange accent `#FF8400`
- Fonts: JetBrains Mono + Geist

## Git
- Branch naming: `<type>/gh-<N>-<short-slug>` (e.g. `feat/gh-101-construction-plans`)
- Types: feat, fix, refactor, chore, docs, test
- Remote is named `github` (not `origin`)
- Conventional commits: `feat(gh-N): description`
