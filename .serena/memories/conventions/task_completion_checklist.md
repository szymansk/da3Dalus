# Task Completion Checklist

When a coding task is completed, perform the following steps:

## 1. Verify Code Quality
```bash
poetry run ruff check .       # Python lint
poetry run ruff format .      # Python format
cd frontend && npm run lint   # Frontend lint (if frontend changed)
```

## 2. Run Tests
```bash
poetry run pytest                    # Backend fast tests
poetry run pytest --cov=app          # With coverage (target 70–80%)
cd frontend && npm run test:unit     # Frontend unit tests (if changed)
cd frontend && npm run deps:check   # Dependency architecture (if changed)
```

## 3. Database Migrations
If models changed:
```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## 4. Git Commit
```bash
git status
git add <specific files>
git commit -m "<type>(<scope>): <description>"
# Types: feat, fix, refactor, docs, test, chore, perf
# Branch naming: <type>/gh-<N>-<short-slug>
```

## 5. Push (if on a feature branch)
```bash
git push github <branch>
```

## Iron Laws
1. No production code without a failing test first (TDD)
2. No completion claims without fresh verification evidence
3. No fixes without root cause investigation
4. Fix the code, not the tests — NEVER weaken assertions or skip tests
5. No bug fix without a GH ticket
