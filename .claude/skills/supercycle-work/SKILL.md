---
name: supercycle-work
description: "Full supercycle: brainstorm, plan, implement, review, fix, merge — all phases with GH tracking"
argument-hint: "<GH issue number> OR <feature description>"
---

# /supercycle-work — Full Development Cycle

Argument: **$ARGUMENTS**

Full supercycle entry point. Drives a GH issue or feature idea
through all phases to merged PR. Delegates actual work to
superpowers skills; handles GH tracking and SonarQube integration.

For entering the cycle at a later phase:
- `/supercycle-implement` — skip brainstorming
- `/supercycle-review` — review existing PRs
- `/supercycle-fix` — fix review findings
- `/supercycle-merge` — CI check + merge

---

## GATHER

### 1. Resolve Input

**If numeric (e.g. `187`, `#187`):**

Use `load-issue` from `../supercycle-common/tracking.md` to fetch the issue.
Use `read-step-comments` to pick up any prior context.

**If free-text:** Accept as brainstorming input. A GH Issue will
be created during the brainstorming phase.

### 2. Fetch SonarQube Context

Use `fetch-sonar-context` from `../supercycle-common/tracking.md`. If the issue body
mentions SonarQube rule IDs or sonarcloud links, fetch current
findings. Pass these to the brainstorming skill as context.

### 3. Set Initial Status

Use `rotate-status` → `status:brainstorming`

### 4. Question Protocol

**Any question from agent to user — in any phase or delegated
skill — MUST be posted to the GH Issue first** using
`post-question-comment` from `../supercycle-common/tracking.md`.
Post to GH, then ask in conversation. After the user answers,
remove the `has-question` label.

---

## DELEGATE

### Phase 1 — Worktree Setup (early — before spec/plan)

Create the feature branch and worktree FIRST so that spec and plan
files are committed directly on the feature branch — not on main.
This makes `github-blob-link` references in step comments work
immediately.

Invoke `/using-git-worktrees` to create an isolated workspace.

### Phase 2 — Brainstorming

Invoke `/brainstorming` with:
- Full issue body (if existing) or user's free-text description
- SonarQube findings (if any)
- Instruction that this feeds into `/writing-plans` next

After brainstorming completes:
- Commit and push the spec file to the feature branch
- Use `post-step-comment`: `has-spec` — full spec/acceptance criteria,
  with a `github-blob-link` to the spec file on the feature branch
- If a new GH Issue was created during brainstorming, capture its number

**USER GATE:**
> "Issue #N spec ready. Proceed to planning?"

Do NOT proceed until the user explicitly confirms.

**Context:** Run `/compact with focus on issue number, branch name,
worktree path, spec acceptance criteria, user gate feedback, and
frontend detection result` before proceeding. If spec details are
needed after compaction, re-read from the spec file or use
`read-step-comments` with filter `has-spec`.

### Phase 3 — Planning

Invoke `/writing-plans` with:
- The approved spec from Phase 2
- TDD directives: every implementation task must follow RED-GREEN-REFACTOR
- If `detect-frontend` is true: include `/vercel-react-best-practices`
  and `/vercel-composition-patterns` as directives for frontend tasks

After planning completes:
- Commit and push the plan file to the feature branch
- Use `post-step-comment`: `has-plan` — full plan with task breakdown,
  with a `github-blob-link` to the plan file on the feature branch
- Use `rotate-status` → `status:planning`

**Context:** Run `/compact with focus on issue number, branch name,
worktree path, plan file path, task count and structure, and frontend
detection result` before proceeding. If plan details are needed after
compaction, re-read from the plan file or use `read-step-comments`
with filter `has-plan`.

### Phase 4 — Implementation

Invoke `/subagent-driven-development` with:
- The plan from Phase 3
- Subagents invoke `/test-driven-development` internally
- Per-task review via `/requesting-code-review`
- If `detect-frontend` is true: frontend subagents follow
  `/vercel-react-best-practices` and `/vercel-composition-patterns`

**Context:** Run `/compact with focus on issue number, PR number,
branch name, and frontend detection result` before proceeding.
Implementation details are fully externalized in commits and the PR.

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

**Context:** Run `/compact with focus on PR number, issue number,
branch name, and worktree path` before proceeding. Fix details are
persisted in the `has-fix` comment.

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
