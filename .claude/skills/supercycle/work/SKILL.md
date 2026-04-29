---
name: supercycle-work
description: "Full supercycle: brainstorm, plan, implement, review, fix, merge — all phases with GH tracking"
argument-hint: "<GH issue number> OR <feature description>"
---

# /supercycle:work — Full Development Cycle

Argument: **$ARGUMENTS**

Full supercycle entry point. Drives a GH issue or feature idea
through all phases to merged PR. Delegates actual work to
superpowers skills; handles GH tracking and SonarQube integration.

For entering the cycle at a later phase:
- `/supercycle:implement` — skip brainstorming
- `/supercycle:review` — review existing PRs
- `/supercycle:fix` — fix review findings
- `/supercycle:merge` — CI check + merge

---

## GATHER

### 1. Resolve Input

**If numeric (e.g. `187`, `#187`):**

Use `load-issue` from `../tracking.md` to fetch the issue.
Use `read-step-comments` to pick up any prior context.

**If free-text:** Accept as brainstorming input. A GH Issue will
be created during the brainstorming phase.

### 2. Fetch SonarQube Context

Use `fetch-sonar-context` from `../tracking.md`. If the issue body
mentions SonarQube rule IDs or sonarcloud links, fetch current
findings. Pass these to the brainstorming skill as context.

### 3. Set Initial Status

Use `rotate-status` → `status:brainstorming`

---

## DELEGATE

### Phase 1 — Brainstorming

Invoke `/brainstorming` with:
- Full issue body (if existing) or user's free-text description
- SonarQube findings (if any)
- Instruction that this feeds into `/writing-plans` next

After brainstorming completes:
- Use `post-step-comment`: `has-spec` — full spec/acceptance criteria
- If a new GH Issue was created during brainstorming, capture its number

**USER GATE:**
> "Issue #N spec ready. Proceed to planning?"

Do NOT proceed until the user explicitly confirms.

### Phase 2 — Planning

Invoke `/writing-plans` with:
- The approved spec from Phase 1
- TDD directives: every implementation task must follow RED-GREEN-REFACTOR
- If `detect-frontend` is true: include `/vercel-react-best-practices`
  and `/vercel-composition-patterns` as directives for frontend tasks

After planning completes:
- Use `post-step-comment`: `has-plan` — full plan with task breakdown
- Use `rotate-status` → `status:planning`

### Phase 3 — Worktree Setup

Invoke `/using-git-worktrees` to create an isolated workspace.
- Use `rotate-status` → `status:implementing`

### Phase 4 — Implementation

Invoke `/subagent-driven-development` with:
- The plan from Phase 2
- Subagents invoke `/test-driven-development` internally
- Per-task review via `/requesting-code-review`
- If `detect-frontend` is true: frontend subagents follow
  `/vercel-react-best-practices` and `/vercel-composition-patterns`

### Phase 5 — Comprehensive Review

Invoke `/pr-review-toolkit:review-pr` with:
- Context: spec + plan from step comments so reviewers know
  what was intended, not just what was built
- If `detect-frontend` is true: add Vercel skills as review lenses

After review:
- Use `post-step-comment`: `has-review` — full review report
- Use `post-step-comment`: `has-pr` — PR number, branch, changes, quality gates
- Use `rotate-status` → `status:in-review`

### Phase 6 — Fix Findings (if any)

If the review reported findings:

1. Invoke `/receiving-code-review` — evaluate findings with
   technical rigor, verify before implementing, push back on
   false positives
2. Invoke `/sonarqube:sonar-fix-issue` for each SonarQube issue
3. Invoke `/verification-before-completion` — evidence that
   fixes work, no regressions

After fixing:
- Use `post-step-comment`: `has-fix` — fix report with rationale

### Phase 7 — Finish

Invoke `/finishing-a-development-branch`
- Use `rotate-status` → `status:merged`

---

## TRACK

Final report with all artifacts linked:

```
## Supercycle Complete

| Phase | Artifact | Link |
|-------|----------|------|
| Spec  | has-spec | Issue #N comment |
| Plan  | has-plan | Issue #N comment |
| PR    | has-pr   | PR #M |
| Review| has-review| Issue #N comment |
| Fix   | has-fix  | Issue #N comment |
| Merge | merged   | main |
```
