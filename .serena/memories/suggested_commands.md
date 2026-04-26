# Suggested Commands

## Backend Development
```bash
# Install dependencies
poetry install && poetry shell

# Run dev server (hot reload)
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Run all fast tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=app

# Run only slow CAD/aero tests
poetry run pytest -m slow

# Run specific test file
poetry run pytest app/tests/test_wing_service_extended.py -v

# Lint and format
poetry run ruff check .
poetry run ruff format .

# Generate Alembic migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

## Frontend Development
```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev

# Unit tests
npm run test:unit

# E2E tests (requires backend running)
npm run test:e2e
npm run test:e2e:slow      # includes @slow tests
npm run test:e2e:headed    # with browser visible
npm run test:e2e:ui        # Playwright UI mode

# Lint
npm run lint

# Dependency graph check
npm run deps:check
```

## Docker
```bash
docker compose build && docker compose up -d   # port 8086
```

## Git
```bash
# Remote is 'github' not 'origin'
git push github <branch>

# Branch naming: <type>/gh-<N>-<short-slug>
# e.g. feat/gh-101-construction-plans
```

## Runtime Endpoints
| URL | What |
|-----|------|
| http://localhost:8001 | REST API |
| http://localhost:8001/docs | Swagger UI |
| http://localhost:8001/redoc | ReDoc |
| http://localhost:8001/openapi.json | OpenAPI schema |
| http://localhost:8001/mcp | MCP (Streamable HTTP) |

## System Utils (macOS / Darwin)
```bash
git status / git diff / git log
ls / find / grep
python3 / poetry
npm / npx
docker / docker compose
```
