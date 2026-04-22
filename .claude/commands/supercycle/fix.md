---
description: "Fix review findings on PR branches — switch to branch, apply fixes, run quality gates, push"
argument-hint: "<PR numbers, comma-separated: 200, 201>"
allowed-tools: Bash, Read, Edit, Write, Glob, Grep
---

# /supercycle:fix — Fix Review Findings

Arguments: **$ARGUMENTS**

Enter the supercycle at the **fix phase**. Use this after a review
has identified findings that need to be addressed before merge.

**Important:** Verify each finding before implementing it. Do NOT
blindly apply suggestions — some may be false positives.

---

## Phase 1 — Identify Findings

For each PR number in arguments:

1. Check for review comments on the PR:
   ```bash
   gh api repos/{owner}/{repo}/pulls/<N>/comments --jq '.[] | {path: .path, line: .line, body: .body}'
   gh pr view <N> --json reviews --jq '.reviews[] | {state: .state, body: .body}'
   ```

2. If no formal review comments exist, ask the user what findings to fix.
   (The review may have been done conversationally in a previous
   `/supercycle:review` invocation.)

---

## Phase 2 — Fix Each PR

For each PR with findings:

### 2a — Switch to Branch
```bash
git switch <branch-name>
git pull github <branch-name>
```

### 2b — Verify Findings

For each finding:
1. Read the affected file and line
2. Determine if the finding is legitimate or a false positive
3. If false positive: document why and skip
4. If legitimate: implement the fix

**Apply `superpowers:receiving-code-review` principle:**
Verify technically before implementing. Don't blindly agree.

### 2c — Quality Gates
```bash
poetry run ruff check .
poetry run ruff format --check .
poetry run pytest -m "not slow"
```

### 2d — Commit and Push
```bash
git add <fixed-files>
git commit -m "fix(<issue>): address review findings — <summary>"
git push github <branch>
```

---

## Phase 3 — Report

```
## Fix Results

| PR | Findings | Fixed | Skipped (false positive) |
|----|----------|-------|-------------------------|
| #N | M        | X     | Y                       |

### Fixed
- [file:line] — <what was fixed and why>

### Skipped (false positives)
- [file:line] — <why this is not a real issue>

### Next Steps
- /supercycle:merge <PR numbers>   ← merge the fixed PRs
```

---

## Supercycle Position

```
/supercycle:work
  ├─ Brainstorming
  ├─ /supercycle:implement
  ├─ /supercycle:review
  │
  ├─ /supercycle:fix             ← YOU ARE HERE
  │    ├─ Verify findings
  │    ├─ Implement fixes
  │    ├─ Quality gates
  │    └─ Push
  │
  └─ /supercycle:merge
```
