---
description: "Check and install all tools, dependencies, and services required by the supercycle workflow"
argument-hint: ""
allowed-tools: Bash, Read, Glob, Grep
---

# /supercycle:init — Toolchain Setup & Verification

Verifies that all tools and dependencies required by the supercycle
workflow are installed and configured. Installs anything missing.

---

## Phase 1 — System Tools

Check each tool. If missing, install it.

### 1.1 — Git
```bash
git --version || echo "MISSING: Install git"
```

### 1.2 — GitHub CLI
```bash
gh --version || echo "MISSING: brew install gh"
gh auth status || echo "MISSING: Run 'gh auth login'"
```

### 1.3 — Python (3.11+)
```bash
python3 --version || echo "MISSING: Install Python 3.11+"
```

### 1.4 — Poetry (2.x)
```bash
poetry --version || echo "MISSING: pipx install poetry"
```

### 1.5 — Node.js (22+) & npm
```bash
node --version || echo "MISSING: brew install node"
npm --version
```

---

## Phase 2 — Backend Dependencies

```bash
# Install Python dependencies (includes ruff, pytest, pydeps)
poetry install --no-interaction --no-root

# Verify key tools
poetry run ruff --version || echo "MISSING: poetry add --group dev ruff"
poetry run pytest --version || echo "MISSING: poetry add --group dev pytest pytest-cov pytest-timeout"
```

---

## Phase 3 — Frontend Dependencies

```bash
cd frontend

# Install all npm packages
npm ci || npm install

# Verify key tools
npx eslint --version || echo "MISSING: npm install --save-dev eslint"
npx vitest --version || echo "MISSING: npm install --save-dev vitest @vitest/coverage-v8"
npx depcruise --version || echo "MISSING: npm install --save-dev dependency-cruiser"
```

### 3.1 — dependency-cruiser config
```bash
test -f .dependency-cruiser.cjs || echo "MISSING: dependency-cruiser config — run /supercycle:init to create it"
```

If `.dependency-cruiser.cjs` is missing, create it with the standard
layer rules (no-circular, no-components-import-app,
no-hooks-import-app, no-hooks-import-components,
no-lib-import-components).

### 3.2 — Playwright (E2E, optional)
```bash
npx playwright --version 2>/dev/null || echo "INFO: Playwright not installed — E2E tests won't run. Install with: npx playwright install"
```

---

## Phase 4 — External Services

### 4.1 — SonarQube / SonarCloud
```bash
# Check if sonar-project.properties exists
test -f sonar-project.properties && echo "SonarQube configured" || echo "MISSING: sonar-project.properties"

# Check MCP server
# SonarQube MCP should be available — verify by trying to list projects
```

Use `mcp__sonarqube__search_my_sonarqube_projects` to verify the
SonarQube MCP connection works. If it fails, suggest running
`/sonarqube:integrate`.

### 4.2 — GitHub Actions
```bash
# Verify workflow exists
test -f .github/workflows/test.yml && echo "CI workflow configured" || echo "MISSING: .github/workflows/test.yml"
```

---

## Phase 5 — Supercycle Commands

Verify all supercycle commands are present:

```bash
for cmd in work bug implement review fix merge init; do
  test -f .claude/commands/supercycle/$cmd.md && echo "✓ /supercycle:$cmd" || echo "✗ /supercycle:$cmd MISSING"
done
```

---

## Phase 6 — Quick Smoke Test

Run a fast validation of each tool:

```bash
# Backend
poetry run ruff check --select E999 app/main.py   # syntax check only
poetry run pytest --co -q 2>/dev/null | tail -1    # collect tests (no run)

# Frontend
cd frontend
npm run lint 2>&1 | tail -1                        # eslint
npm run deps:check 2>&1 | tail -1                  # dependency-cruiser
npm run test:unit -- --run 2>&1 | tail -3          # vitest (fast)
```

---

## Phase 7 — Report

```
## Supercycle Toolchain Status

| Category | Tool | Version | Status |
|----------|------|---------|--------|
| System | git | X.Y.Z | ✓ |
| System | gh | X.Y.Z | ✓ authenticated |
| System | python | 3.X.Y | ✓ |
| System | poetry | X.Y.Z | ✓ |
| System | node | X.Y.Z | ✓ |
| System | npm | X.Y.Z | ✓ |
| Backend | ruff | X.Y.Z | ✓ |
| Backend | pytest | X.Y.Z | ✓ (N tests collected) |
| Backend | pydeps | X.Y.Z | ✓ |
| Frontend | eslint | X.Y.Z | ✓ |
| Frontend | vitest | X.Y.Z | ✓ (N tests pass) |
| Frontend | dep-cruiser | X.Y.Z | ✓ (N violations) |
| Frontend | playwright | X.Y.Z | ✓ / not installed |
| Service | SonarCloud | — | ✓ connected / ✗ not configured |
| Service | GitHub Actions | — | ✓ workflow exists |
| Commands | supercycle/* | — | ✓ all 7 present |

### Issues Found
- <any missing tools or failed checks>

### Actions Taken
- <any installations performed>
```

---

## Supercycle Position

```
/supercycle:init                     ← YOU ARE HERE
  │
  ├─ System tools (git, gh, python, poetry, node)
  ├─ Backend deps (ruff, pytest, pydeps)
  ├─ Frontend deps (eslint, vitest, dep-cruiser, playwright)
  ├─ External services (SonarCloud, GitHub Actions)
  ├─ Supercycle commands verification
  ├─ Smoke test
  └─ Report

Other entry points:
  /supercycle:work      ← features, brainstorming
  /supercycle:bug       ← bug intake + TDD fix
  /supercycle:implement ← well-defined issues
  /supercycle:review    ← review existing PRs
  /supercycle:fix       ← fix review findings
  /supercycle:merge     ← CI check + merge
```
