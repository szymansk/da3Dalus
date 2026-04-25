---
description: "Fix review findings on PR branches — switch to branch, apply fixes, run quality gates, push"
argument-hint: "<PR numbers, comma-separated: 200, 201>"
allowed-tools: Bash, Read, Edit, Write, Glob, Grep, Skill
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

For each finding — **prefer Serena tools** for navigation:
1. Use `serena:find_symbol` or `serena:file_outline` to locate the
   affected code (instead of reading entire files)
2. Use `serena:find_references` to assess blast radius
3. Determine if the finding is legitimate or a false positive
4. If false positive: document why and skip
5. If legitimate: implement the fix (use `serena:rename_symbol` for
   renames, `serena:replace_symbol_body` for function rewrites)

**Apply `superpowers:receiving-code-review` principle:**
Verify technically before implementing. Don't blindly agree.

### 2c — Quality Gates
```bash
# Backend
poetry run ruff check .
poetry run ruff format --check .
poetry run pytest -m "not slow"

# Frontend (if changed)
cd frontend && npm run lint && npm run test:unit && npm run deps:check
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

## GH Issue Tracking

**Reference:** See `tracking.md` in this directory for the label
catalog, comment template, and helper commands.

### At Phase 1 start (identifying findings):

For each linked issue (from `Closes #N` in PR body), rotate status
to `status:fixing`.

### After Phase 3 (report):

For each linked issue:

1. Post a comment with header `## 🏷️ has-fix` containing the full
   fix report (findings fixed with file:line references, findings
   skipped as false positives with rationale)
2. Add label `has-fix`

**IMPORTANT:** Always post the comment FIRST, then add the label.
Always ensure the label exists before adding it (idempotent create).

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
