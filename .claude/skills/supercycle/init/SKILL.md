---
name: supercycle-init
description: "Check and install all tools, dependencies, and services required by the supercycle workflow"
---

# /supercycle:init — Toolchain Setup & Verification

Argument: **$ARGUMENTS**

Verifies all tools and dependencies required by the supercycle
workflow are installed and configured. Installs anything missing.

---

## Phase 1 — System Tools

Check each tool. If missing, report it.

```bash
git --version || echo "MISSING: Install git"
gh --version || echo "MISSING: brew install gh"
gh auth status || echo "MISSING: Run 'gh auth login'"
python3 --version || echo "MISSING: Install Python 3.11+"
poetry --version || echo "MISSING: pipx install poetry"
node --version || echo "MISSING: brew install node"
npm --version
```

## Phase 2 — Backend Dependencies

```bash
poetry install --no-interaction --no-root
poetry run ruff --version || echo "MISSING: poetry add --group dev ruff"
poetry run pytest --version || echo "MISSING: poetry add --group dev pytest"
```

## Phase 3 — Frontend Dependencies

```bash
cd frontend
npm ci || npm install
npx eslint --version || echo "MISSING"
npx vitest --version || echo "MISSING"
npx depcruise --version || echo "MISSING"
npx playwright --version 2>/dev/null || echo "INFO: Playwright not installed"
```

## Phase 4 — External Services

### SonarQube

Invoke `/sonarqube:sonar-integrate` to ensure `sonarqube-cli` is
installed, authentication is valid, and MCP server is wired in.

After the skill completes:
```bash
test -f sonar-project.properties && echo "SonarQube configured" || echo "MISSING"
```

### GitHub Actions

```bash
test -f .github/workflows/test.yml && echo "CI workflow configured" || echo "MISSING"
```

## Phase 5 — Tracking Labels

Run the `ensure-labels` operation from `../tracking.md` to create
all tracking labels idempotently.

## Phase 6 — Smoke Test

```bash
poetry run ruff check --select E999 app/main.py
poetry run pytest --co -q 2>/dev/null | tail -1
cd frontend && npm run lint 2>&1 | tail -1
cd frontend && npm run deps:check 2>&1 | tail -1
```

## Phase 7 — Report

Present a tool/version/status table:

```
| Category | Tool | Version | Status |
|----------|------|---------|--------|
| System   | git  | X.Y.Z   | ✓      |
| ...      | ...  | ...     | ...    |
```
