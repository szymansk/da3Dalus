---
name: supercycle-status
description: "Project health dashboard — GH issues, SonarQube status, test health, and next-phase recommendations"
---

# /supercycle:status — Project Health Dashboard

Argument: **$ARGUMENTS**

Generate a comprehensive status report covering GitHub issues,
SonarQube code quality, test health, and strategic recommendations.

---

## Phase 1 — GitHub Issues Overview

### Issue Statistics

```bash
gh issue list --state open --json number --jq 'length'
gh issue list --state closed --json number --jq 'length'
```

### Open Issues Table

```bash
gh issue list --state open --limit 50 \
  --json number,title,labels,createdAt \
  --jq '.[] | "#\(.number) [\(.labels | map(.name) | join(","))] \(.title)"'
```

Present as:

```
| # | Labels | Title | Age |
|---|--------|-------|-----|
```

### Open PRs

```bash
gh pr list --state open --json number,title,headRefName,additions,deletions
```

## Phase 2 — SonarQube Code Quality

Invoke `/sonarqube:sonar-quality-gate` for overall project status.
Invoke `/sonarqube:sonar-list-issues` for issue distribution by
severity.

Present:
```
| Severity | Count |
|----------|-------|
```

## Phase 3 — Test Health

```bash
poetry run pytest --co -q 2>/dev/null | tail -1
poetry run pytest -m "not slow" --tb=no -q 2>&1 | tail -3
cd frontend && npm run test:unit 2>&1 | tail -5
cd frontend && npm run deps:check 2>&1 | tail -5
```

## Phase 4 — Recommendations

Based on the data gathered, classify work into a priority matrix:

| | Urgent | Not Urgent |
|---|--------|------------|
| **Important** | Bugs, BLOCKER issues | HIGH SonarQube issues, test gaps |
| **Not Important** | MEDIUM/LOW SonarQube | Nice-to-have features |

Suggest next phases with specific ticket numbers and scope estimates.
