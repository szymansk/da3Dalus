---
name: supercycle-implement
description: "Skip brainstorming — go straight to implementation of a GH issue with TDD, review, and merge"
argument-hint: "<GH issue number(s), comma-separated: #188, #190>"
---

# /supercycle-implement — Direct Implementation

Argument: **$ARGUMENTS**

Enter the supercycle at the implementation phase, skipping
brainstorming. Use when the issue is already well-defined with a
spec and/or plan.

---

## GATHER

### 1. Load Issues

For each issue number in arguments:

Use `load-issue` from `../supercycle-common/tracking.md`.
Use `read-step-comments` with filter `has-spec`, `has-plan` to
pick up spec and plan from prior phases.

### 2. Fetch SonarQube Context

Use `fetch-sonar-context` from `../supercycle-common/tracking.md`.

### 3. Set Status

Use `rotate-status` → `status:implementing` for each issue.

---

## DELEGATE

### Phase 1 — Worktree Setup

Invoke `/using-git-worktrees` to create an isolated workspace.

### Phase 2 — Implementation

Invoke `/subagent-driven-development` with:
- Context: spec + plan from step comments passed to subagents
- Subagents invoke `/test-driven-development` internally
- Per-task review via `/requesting-code-review`
- If `detect-frontend` is true: frontend subagents follow
  `/vercel-react-best-practices` and `/vercel-composition-patterns`

### Phase 3 — Comprehensive Review

Invoke `/pr-review-toolkit:review-pr` with:
- Context: spec + plan from step comments

After review:
- Use `post-step-comment`: `has-review` — full review report
- Use `post-step-comment`: `has-pr` — PR number, branch, changes, quality gates

### Phase 4 — Fix Findings (if any)

If findings reported:
1. `/receiving-code-review` — evaluate + verify
2. `/sonarqube:sonar-fix-issue` — SonarQube issues
3. `/verification-before-completion` — evidence

After fixing:
- Use `post-step-comment`: `has-fix` — fix report

### Phase 5 — Finish

Invoke `/finishing-a-development-branch`

---

## TRACK

Use `rotate-status` → `status:merged`

Report PRs created with links.
