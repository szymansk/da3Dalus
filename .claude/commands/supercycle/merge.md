---
description: "Check CI, analyse quality gates, and merge one or more PRs sequentially with rebase conflict resolution"
argument-hint: "<PR numbers, comma-separated: 200, 201>"
allowed-tools: Bash, Read, Glob, Grep, Skill
---

# /supercycle:merge — CI Check & Merge

Arguments: **$ARGUMENTS**

Enter the supercycle at the **merge phase**. Checks CI status,
analyses SonarQube quality gates, and merges PRs sequentially
with automatic rebase conflict resolution.

---

## Phase 1 — CI Status Check

For each PR number in arguments:

```bash
gh pr checks <N>
```

Classify each check:
- **Tests (3.11, 3.12):** Must be green. If failing → stop and report.
- **SonarCloud Quality Gate:** Soft gate — analyse further in Phase 2.
- **Other checks:** Report status.

If any test check is failing, do NOT proceed to merge. Report the
failure and suggest:
```
Tests failing on PR #N. Options:
- /supercycle:fix <N>   ← investigate and fix
- gh pr checks <N>      ← check again after fix
```

---

## Phase 2 — SonarQube Quality Gate Analysis

If SonarCloud Quality Gate is failing, use `/sonarqube:sonar-quality-gate`
to get the detailed status for the PR.

For each failed condition:
- **Security / Reliability / Maintainability:** Must fix before merge.
  Use `/sonarqube:sonar-list-issues` to get the specific issues on
  the PR branch and `/sonarqube:sonar-analyze` for deeper analysis.
- **Coverage on new code:** Analyse if acceptable:
  - Refactoring/chore PRs: coverage gaps on renamed/moved code are expected
  - Feature PRs: new code should have tests — flag if missing.
    Use `/sonarqube:sonar-coverage` to inspect uncovered lines.
- **Duplication:** Use `/sonarqube:sonar-duplication` to check if
  duplication is from mechanical changes (e.g. repeated `responses={}`
  patterns) or real copy-paste.

Report the analysis and a merge recommendation for each PR.

---

## Phase 3 — Merge Sequentially

For each PR (in the order provided):

### 3a — Merge
```bash
gh pr merge <N> --merge --delete-branch
```

### 3b — Handle Conflicts
If merge fails due to conflicts:
```bash
git switch <branch>
git rebase main
# resolve conflicts
git push github <branch> --force-with-lease
gh pr merge <N> --merge --delete-branch
```

### 3c — Verify After Each Merge
```bash
git switch main && git pull github main
```

---

## Phase 4 — Post-Merge Verification

After ALL PRs are merged:

```bash
git switch main && git pull github main
poetry run pytest -m "not slow"
```

Report:
```
## Merge Complete

| PR | Issue | Title | Status |
|----|-------|-------|--------|
| #M | #N    | ...   | merged |

### Test Results
<pytest output summary>

### Next Steps
- Batch 3 ready: /supercycle:implement #189, #193
- Or: session complete, all work merged
```

---

## GH Issue Tracking

**Reference:** See `tracking.md` in this directory for the label
catalog, comment template, and helper commands.

### At Phase 1 start (CI status check):

For each linked issue (from `Closes #N` in PR body), rotate status
to `status:merging`.

### After Phase 4 (post-merge verification):

For each linked issue, rotate status to `status:merged`.

No `has-*` label is set — the merged status and the closed issue
(via `Closes #N`) are sufficient.

---

## Supercycle Position

```
/supercycle:work
  ├─ Brainstorming
  ├─ /supercycle:implement
  ├─ /supercycle:review
  ├─ /supercycle:fix
  │
  └─ /supercycle:merge           ← YOU ARE HERE
       ├─ CI status check
       ├─ SonarQube QG analysis
       ├─ Sequential merge + rebase
       └─ Post-merge pytest
```
