---
name: supercycle-merge
description: "Check CI, analyze SonarQube quality gate, and merge PRs with post-merge verification"
argument-hint: "<PR numbers, comma-separated: 200, 201>"
---

# /supercycle-merge — CI Check & Merge

Argument: **$ARGUMENTS**

Check CI status, analyze SonarQube quality gates, and merge PRs.

---

## GATHER

### 1. Load PRs

For each PR number in arguments:

Use `load-pr` from `../supercycle-common/tracking.md`.

### 2. Verify Prior Steps

Use `read-step-comments` on linked issues with filters
`has-review`, `has-fix` to verify review passed and findings
were addressed before merging.

### 3. CI Status

```bash
gh pr checks $PR
```

If any test check is failing, do NOT proceed. Report the failure:
```
Tests failing on PR #N. Options:
- /supercycle-fix <N> — investigate and fix
- gh pr checks <N> — check again after fix
```

### 4. SonarQube Quality Gate

Invoke `/sonarqube:sonar-quality-gate` for the project.

### 5. Set Status

Use `rotate-status` → `status:merging` for each linked issue.

---

## DELEGATE

### 1. Analyze SonarQube Gate (if failing)

For each failed condition:
- **Security / Reliability / Maintainability:** Block merge.
  Use `/sonarqube:sonar-list-issues` for specifics.
- **Coverage on new code:** Context-dependent. Refactoring/chore
  PRs: coverage gaps on moved code are expected. Feature PRs:
  new code should have tests. Use `/sonarqube:sonar-coverage`.
- **Duplication:** Check if mechanical via
  `/sonarqube:sonar-duplication`.

### 2. Finish

Invoke `/finishing-a-development-branch`:
- Verify tests pass
- Present merge options (merge/PR/keep/discard)
- Execute chosen option
- Clean up worktree

---

## TRACK

Use `rotate-status` → `status:merged` for each linked issue.

Post-merge verification:
```bash
git switch main && git pull github main
poetry run alembic upgrade head
poetry run pytest -m "not slow"
```

Report:
```
## Merge Complete

| PR | Issue | Title | Status |
|----|-------|-------|--------|

### Test Results
<pytest output summary>
```
