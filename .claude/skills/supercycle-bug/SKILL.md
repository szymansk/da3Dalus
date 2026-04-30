---
name: supercycle-bug
description: "Bug intake: investigate root cause, create GH ticket, TDD fix, review, and merge — all in one auto-chained flow"
argument-hint: "<error log, description, or GH issue number>"
---

# /supercycle-bug — Bug Intake & Fix

Argument: **$ARGUMENTS**

Fast-track supercycle for bugs. Auto-chains all phases with no
user gates. Takes a raw error log, bug description, or existing
GH issue number and drives it through investigation → ticket →
fix → review → merge.

---

## GATHER

### If numeric (e.g. `210`, `#210`):

Use `load-issue` from `../supercycle-common/tracking.md`.
Use `read-step-comments` to pick up any prior context.

### If free-text (error log / description):

Parse the input for:
- Error message / exception
- Stack trace — file paths, line numbers
- Endpoint / trigger
- HTTP status

### Fetch SonarQube Context

Use `fetch-sonar-context` from `../supercycle-common/tracking.md`.

### Question Protocol

**Any question from agent to user** MUST be posted to the GH Issue
first using `post-question-comment` from
`../supercycle-common/tracking.md`. Post to GH, then ask in
conversation. Remove `has-question` label after answer.

---

## DELEGATE (auto-chain, no user gates)

### Phase 1 — Root Cause Investigation

Invoke `/systematic-debugging` with the parsed error context.

After investigation:
- Use `post-step-comment`: `has-root-cause` — error, root cause,
  introducing commit, severity, affected features, proposed fix
- **Note:** If input was free-text, the GH Issue may not exist yet.
  Post this comment AFTER Phase 2 (issue creation).

### Phase 2 — Create GH Issue

**Only if input was free-text** (skip if already a GH issue):

```bash
gh issue create \
  --title "bug: <concise title>" \
  --body "<structured body with root cause>" \
  --label "bug"
```

Use `rotate-status` → `status:implementing`

### Phase 3 — Worktree Setup

Invoke `/using-git-worktrees`

### Phase 4 — TDD Fix

Invoke `/test-driven-development` directly (no plan layer):

**RED:** Write failing test reproducing the bug.
After RED:
- Use `post-step-comment`: `has-reproduction` — test name, file
  path, test code, failing output

**GREEN:** Write minimal fix for root cause.

**REFACTOR:** Clean up.

**Context:** Run `/compact` before proceeding — root cause and
reproduction are persisted in GH comments.

### Phase 5 — Verification

Invoke `/verification-before-completion` — evidence before claims.

### Phase 6 — Comprehensive Review

Invoke `/pr-review-toolkit:review-pr`

After review:
- Use `post-step-comment`: `has-review` — full review report
- Use `post-step-comment`: `has-pr` — PR number, branch, changes

### Phase 7 — Fix Findings (if any)

If findings reported:
1. `/receiving-code-review` — evaluate + verify
2. `/sonarqube:sonar-fix-issue` — SonarQube issues
After fixing:
- Use `post-step-comment`: `has-fix` — fix report

### Phase 8 — Finish

Invoke `/finishing-a-development-branch`

---

## TRACK

Use `rotate-status` → `status:merged`

Report: issue, PR, root cause, test name.
