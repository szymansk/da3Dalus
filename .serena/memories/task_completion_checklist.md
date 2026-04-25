# Task Completion Checklist

When a task is completed, run these checks before committing:

## Backend Changes
```bash
poetry run ruff check .          # Lint
poetry run ruff format .         # Format
poetry run pytest -m "not slow"  # Fast tests (no CAD/aero)
```

## Frontend Changes
```bash
cd frontend
npm run lint                     # ESLint
npm run deps:check               # dependency-cruiser (architecture violations)
npm run test:unit -- --run       # Vitest unit tests
```

## Database Model Changes
```bash
alembic revision --autogenerate -m "description"
# Review the generated migration before committing
```

## Git Workflow
```bash
git add <specific-files>         # Stage (never git add -A)
git commit -m "type(scope): description"
git push github <branch>         # Remote is 'github', not 'origin'
```

## Iron Laws
1. No production code without a failing test first
2. No completion claims without fresh verification evidence
3. No fixes without root cause investigation
4. Fix the code, not the tests — NEVER weaken assertions
5. No bug fix without a GH ticket

## Test Coverage Target: 70–80%
Every feature, bugfix, and refactor must include tests.
