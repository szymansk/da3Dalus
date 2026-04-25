---
description: "Project health dashboard — GH issues, SonarQube status, dependency graph, and next-phase recommendations"
argument-hint: ""
allowed-tools: Bash, Read, Glob, Grep, Agent, WebSearch, Skill
---

# /supercycle:status — Project Health Dashboard

Generate a comprehensive status report covering GitHub issues,
SonarQube code quality, and strategic recommendations.

---

## Phase 1 — GitHub Issues Overview

### 1a — Issue Statistics

```bash
# Counts by state
gh issue list --state open --json number --jq 'length'
gh issue list --state closed --json number --jq 'length'

# Open issues by label
gh issue list --state open --json number,title,labels --jq '
  group_by(.labels[0].name // "unlabeled") |
  map({label: .[0].labels[0].name // "unlabeled", count: length}) |
  sort_by(-.count)'
```

### 1b — Open Issues Table

```bash
gh issue list --state open --limit 50 \
  --json number,title,labels,createdAt \
  --jq '.[] | "#\(.number) [\(.labels | map(.name) | join(","))] \(.title)"'
```

Present as a table:

```
| # | Label | Title | Age |
|---|-------|-------|-----|
```

### 1c — Dependency Map

For any issue that references other issues (in body text like
"depends on #N", "blocked by #N", "part of EPIC #N"):

```bash
for issue in $(gh issue list --state open --json number --jq '.[].number'); do
  body=$(gh issue view $issue --json body --jq '.body')
  # Extract references to other issues
  refs=$(echo "$body" | grep -oE '#[0-9]+' | sort -u)
  if [ -n "$refs" ]; then
    echo "#$issue → $refs"
  fi
done
```

Present as a dependency tree or matrix showing which issues
block which.

### 1d — Open PRs

```bash
gh pr list --state open --json number,title,headRefName,additions,deletions
```

---

## Phase 2 — SonarQube Code Quality

### 2a — Quality Gate Status

Use `/sonarqube:sonar-quality-gate` for the overall project
quality gate.

Present:
```
| Condition | Status | Threshold | Actual |
|-----------|--------|-----------|--------|
```

### 2b — Issue Distribution

Use `/sonarqube:sonar-list-issues` to get issues by severity:

```
| Severity | Count | Trend |
|----------|-------|-------|
| BLOCKER  | N     | ↓/↑/→ |
| HIGH     | N     | ↓/↑/→ |
| MEDIUM   | N     | ↓/↑/→ |
| LOW      | N     | ↓/↑/→ |
| Total    | N     |       |
```

### 2c — Top Rules

From the `/sonarqube:sonar-list-issues` output, count by rule
to identify the most frequent issue types:

```
| Rule | Count | Description |
|------|-------|-------------|
```

### 2d — Top Files

From the same data, count by file:

```
| File | Issues | Top Rule |
|------|--------|----------|
```

### 2e — Frontend Dependency Health

```bash
cd frontend && npm run deps:check 2>&1 | tail -5
```

Report: errors, warnings, modules cruised.

---

## Phase 3 — Test Health

```bash
# Backend
poetry run pytest --co -q 2>/dev/null | tail -1   # test count
poetry run pytest -m "not slow" --tb=no -q 2>&1 | tail -3

# Frontend
cd frontend && npm run test:unit 2>&1 | tail -5
```

Present:
```
| Suite | Tests | Pass | Fail | Coverage |
|-------|-------|------|------|----------|
```

---

## Phase 4 — Recommendations

Based on the data gathered, suggest the next development phases:

### Priority Matrix

Classify work into quadrants:

| | Urgent | Not Urgent |
|---|--------|------------|
| **Important** | Bugs, BLOCKER issues, broken features | HIGH SonarQube issues, test gaps |
| **Not Important** | MEDIUM/LOW SonarQube, style fixes | Nice-to-have features, polish |

### Suggested Next Phases

1. **Immediate** — any open bugs or BLOCKER issues
2. **Short-term** — HIGH SonarQube issues, test coverage gaps
3. **Medium-term** — Feature work from open enhancement tickets
4. **Background** — MEDIUM/LOW SonarQube cleanup, documentation

For each phase, reference specific ticket numbers and estimate
scope (S/M/L).

### Blocked Work

List any issues that are blocked on:
- Human decisions (marked with 🧑 Human Only)
- External dependencies
- Other issues (dependency chain)

---

## Phase 5 — Report

Combine everything into a single dashboard:

```
# Project Health Dashboard

## GitHub Issues
- Open: N (bugs: X, enhancements: Y, epics: Z)
- Closed this week: N
- Open PRs: N

## SonarQube
- Quality Gate: PASS / FAIL
- Issues: N total (BLOCKER: X, HIGH: Y, MEDIUM: Z, LOW: W)
- Top rule: S#### (N occurrences)
- Trend: ↓ improving / → stable / ↑ degrading

## Tests
- Backend: N tests, N% coverage
- Frontend: N tests, N% coverage

## Dependencies
- Circular: N
- Layer violations: N warnings, N errors

## Recommended Next Phases
1. ...
2. ...
3. ...
```

---

## Supercycle Position

```
/supercycle:status                   ← YOU ARE HERE (read-only)
  │
  ├─ GitHub Issues overview
  ├─ SonarQube quality dashboard
  ├─ Test health
  ├─ Dependency health
  └─ Strategic recommendations

Action commands:
  /supercycle:init      ← setup toolchain
  /supercycle:work      ← features, brainstorming
  /supercycle:bug       ← bug intake + TDD fix
  /supercycle:implement ← well-defined issues
  /supercycle:review    ← review existing PRs
  /supercycle:fix       ← fix review findings
  /supercycle:merge     ← CI check + merge
```
