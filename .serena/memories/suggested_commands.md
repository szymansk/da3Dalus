# Suggested Commands

## Development Server
```bash
# Backend (hot reload)
poetry install && poetry shell
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Frontend
cd frontend && npm run dev
```

## Testing
```bash
# Backend — all fast tests
poetry run pytest

# Backend — integration/slow/CAD tests
poetry run pytest -m slow

# Backend — with coverage
poetry run pytest --cov=app

# Frontend — unit tests
cd frontend && npm run test:unit

# Frontend — E2E tests
cd frontend && npm run test:e2e
```

## Linting & Formatting
```bash
# Backend
poetry run ruff check .
poetry run ruff format .

# Frontend
cd frontend && npm run lint
cd frontend && npm run deps:check   # dependency-cruiser architecture check
```

## Database Migrations
```bash
# Create migration after model change
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

## Docker
```bash
docker compose build && docker compose up -d  # port 8086
```

## Git
```bash
# Remote is named 'github' (not 'origin')
git push github <branch>
```

## System Utilities (macOS/Darwin)
```bash
git, ls, cd, grep, find, cat, head, tail, sed, awk
# Standard Unix commands, macOS versions
```

## Runtime Endpoints
| URL | What |
|-----|------|
| http://localhost:8001 | REST API |
| http://localhost:8001/docs | Swagger UI |
| http://localhost:8001/mcp | MCP (Streamable HTTP) |
| http://localhost:3000 | Frontend dev server |
