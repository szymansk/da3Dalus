---
globs:
  - "**/*.py"
---

# Python Conventions for cad-modelling-service

## Layered architecture

The project is a layered FastAPI application. Respect the layers.

```
endpoint (app/api/v2/endpoints/)  →  service (app/services/)
                                   →  model   (app/models/)     — SQLAlchemy
                                   →  schema  (app/schemas/)    — Pydantic
                                   →  converter (app/converters/)
```

- **Endpoints are thin.** Validate input, delegate to a service, return a
  Pydantic response. No database queries, no CAD calls, no long loops in
  endpoint functions.
- **Services hold the business logic.** Orchestration, external tool
  calls (CadQuery, Aerosandbox, AVL, subprocesses), transactions.
- **Models are SQLAlchemy classes** under `app/models/`. Always add an
  Alembic migration when changing a model.
- **Schemas are Pydantic classes** under `app/schemas/`. They are the
  contract for every request and response body. Never pass raw `dict`
  across a boundary.
- **Converters** in `app/converters/` translate between schemas, models,
  and CAD geometry. Reuse existing converters before writing new ones.

## Type hints

- Type-annotate every public function (`def foo(x: int) -> str: ...`).
- Use `from __future__ import annotations` in modules with forward
  references to avoid circular-import pain.
- Prefer `list[str]` / `dict[str, int]` over `List[...]` / `Dict[...]`
  (Python 3.11+).
- Use `Optional[X]` or `X | None` consistently within a file.

## Pydantic

- Inherit from `pydantic.BaseModel` (v2).
- Prefer explicit field types and defaults over `Any`.
- Use `Field(..., description=...)` for endpoint request/response models
  so Swagger UI and MCP tool descriptions are meaningful.
- Validators belong on the schema, not in the endpoint.

## SQLAlchemy

- Query via the session injected by `app/db/`. Do not construct
  engines in endpoints or services.
- Commit in the service layer, not the endpoint.
- When changing a model: `alembic revision --autogenerate -m "..."` and
  review the generated migration before committing.

## Tests

- Test modules live in `app/tests/test_*.py` (pytest auto-discovery).
- Use fixtures for the FastAPI `TestClient` and DB session; do not
  build them ad-hoc in each test.
- `poetry run pytest` is the authoritative test command. `external/`
  and `docker_smoke_test.py` are intentionally excluded via
  `pyproject.toml`.

## Platform guards

`cadquery` and `aerosandbox` are **intentionally excluded** on
`linux/aarch64` in `pyproject.toml` environment markers. Code that
imports them must tolerate being unavailable on that platform:

```python
try:
    import cadquery as cq
    HAS_CADQUERY = True
except ImportError:
    HAS_CADQUERY = False
```

Or keep platform-specific code in a module that is only loaded on
supported platforms.

## CAD code (cad_designer/)

- Use the existing decorators in `cad_designer/decorators/` and plugins
  in `cad_designer/cq_plugins/` before writing new geometry helpers.
- CAD computations are CPU-bound — run them from services, never block
  the FastAPI event loop.
- Prefer returning CadQuery workplanes / compounds from helpers and
  letting the service layer decide on export format (STEP, STL, etc.).

## Configuration

- All configuration goes through `app/core/config.py` using
  `pydantic-settings`.
- New settings get a field in the settings class, a default, and an
  entry in `.env.example`. Do not read environment variables via
  `os.getenv` scattered across the codebase.

## Imports

- Absolute imports rooted at `app.` or `cad_designer.` (not relative
  `..foo`).
- Standard library → third-party → local, separated by blank lines.
- No unused imports.

## Style

- PEP 8 for everything. When a linter is added (see backlog), it will
  target `py311`, line length 100.
- Docstrings on public functions and classes; keep them short and
  focused on *why*, not *what*.
- No `print()` for logging — use the `logging` module with the
  project's `app/logging_config.py` setup.
