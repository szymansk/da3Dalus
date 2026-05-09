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

<gather>

<step name="resolve-input">
<condition trigger="numeric (e.g. 187, #187)">
Use `load-issue` from `../supercycle-common/tracking.md` to fetch the issue.
Use `read-step-comments` to pick up any prior context.
</condition>
<condition trigger="free-text">
Accept as brainstorming input. A GH Issue will be created during
the brainstorming phase.
</condition>
</step>

<step name="fetch-sonar-context">
Use `fetch-sonar-context` from `../supercycle-common/tracking.md`.
If the issue body mentions SonarQube rule IDs or sonarcloud links,
fetch current findings. Pass these to the brainstorming skill as context.
</step>

<step name="set-initial-status">
Use `rotate-status` → `status:brainstorming`
</step>

<step name="question-protocol">
Any question from agent to user — in any phase or delegated skill —
MUST be posted to the GH Issue first using `post-question-comment`
from `../supercycle-common/tracking.md`.
Post to GH, then ask in conversation. After the user answers,
remove the `has-question` label.
</step>

</gather>

---

<delegate>

<phase name="worktree-setup" order="1">
<description>Create feature branch and worktree BEFORE spec/plan so that
committed files live on the feature branch — not on main. This makes
`github-blob-link` references in step comments work immediately.</description>

<action>Invoke `/using-git-worktrees` to create an isolated workspace.</action>
</phase>

<phase name="brainstorming" order="2">
<description>Explore the problem space, download visual assets, and produce
a design spec with acceptance criteria.</description>

<step name="download-linked-assets">
Before invoking brainstorming, scan the issue body for linked images
(wireframes, screenshots, diagrams) and documents (PDFs, design files).
Use `WebFetch` to download each image/document, then `Read` to view them.
These visual assets are critical context — never brainstorm from text
descriptions alone when visual references exist.
</step>

<step name="invoke-brainstorming">
Invoke `/brainstorming` with:
- Full issue body (if existing) or user's free-text description
- Downloaded images/documents as visual context
- SonarQube findings (if any)
- Instruction that this feeds into `/writing-plans` next
</step>

<step name="commit-spec">
After brainstorming completes:
- Commit and push the spec file to the feature branch
- Use `post-step-comment`: `has-spec` — full spec/acceptance criteria,
  with a `github-blob-link` to the spec file on the feature branch
- If a new GH Issue was created during brainstorming, capture its number
</step>

<gate type="user">
"Issue #N spec ready. Proceed to planning?"
Do NOT proceed until the user explicitly confirms.
</gate>

<context-management>
Run `/compact with focus on issue number, branch name, worktree path,
spec acceptance criteria, user gate feedback, and frontend detection
result` before proceeding. If spec details are needed after compaction,
re-read from the spec file or use `read-step-comments` with filter
`has-spec`.
</context-management>
</phase>

<phase name="planning" order="3">
<description>Produce a detailed implementation plan with TDD-structured tasks.</description>

<step name="invoke-planning">
Invoke `/writing-plans` with:
- The approved spec from Phase 2
- TDD directives: every implementation task must follow RED-GREEN-REFACTOR
- If `detect-frontend` is true: include `/vercel-react-best-practices`
  and `/vercel-composition-patterns` as directives for frontend tasks
</step>

<step name="commit-plan">
After planning completes:
- Commit and push the plan file to the feature branch
- Use `post-step-comment`: `has-plan` — full plan with task breakdown,
  with a `github-blob-link` to the plan file on the feature branch
- Use `rotate-status` → `status:planning`
</step>

<context-management>
Run `/compact with focus on issue number, branch name, worktree path,
plan file path, task count and structure, and frontend detection result`
before proceeding. If plan details are needed after compaction, re-read
from the plan file or use `read-step-comments` with filter `has-plan`.
</context-management>
</phase>

<phase name="implementation" order="4">
<description>Execute the plan using TDD subagents.</description>

<step name="cleanup-before-tests">
Use `kill-orphaned-workers` from `../supercycle-common/tracking.md`
before running any tests. Orphaned CadQuery workers from prior runs
consume 100% CPU and ~500 MB RAM each, causing timeouts and crashes.
</step>

<step name="invoke-implementation">
Invoke `/subagent-driven-development` with:
- The plan from Phase 3
- Subagents invoke `/test-driven-development` internally
- Per-task review via `/requesting-code-review`
- If `detect-frontend` is true: frontend subagents follow
  `/vercel-react-best-practices` and `/vercel-composition-patterns`
</step>

<context-management>
Run `/compact with focus on issue number, PR number, branch name, and
frontend detection result` before proceeding. Implementation details are
fully externalized in commits and the PR.
</context-management>
</phase>

<phase name="comprehensive-review" order="5">
<description>Review the PR against spec and plan.</description>

<step name="invoke-review">
Invoke `/pr-review-toolkit:review-pr` with:
- Context: spec + plan from step comments so reviewers know
  what was intended, not just what was built
- If `detect-frontend` is true: add Vercel skills as review lenses
</step>

<step name="post-review-artifacts">
After review:
- Use `post-step-comment`: `has-review` — full review report
- Use `post-step-comment`: `has-pr` — PR number, branch, changes, quality gates
- Use `rotate-status` → `status:in-review`
</step>
</phase>

<phase name="fix-findings" order="6">
<condition trigger="review reported findings">

<step name="evaluate-findings">
Invoke `/receiving-code-review` — evaluate findings with technical
rigor, verify before implementing, push back on false positives.
</step>

<step name="fix-sonarqube">
Invoke `/sonarqube:sonar-fix-issue` for each SonarQube issue.
</step>

<step name="cleanup-before-verification">
Use `kill-orphaned-workers` from `../supercycle-common/tracking.md`.
</step>

<step name="verify-fixes">
Invoke `/verification-before-completion` — evidence that fixes work,
no regressions.
</step>

<step name="post-fix-artifacts">
After fixing:
- Use `post-step-comment`: `has-fix` — fix report with rationale
</step>

<context-management>
Run `/compact with focus on PR number, issue number, branch name, and
worktree path` before proceeding. Fix details are persisted in the
`has-fix` comment.
</context-management>

</condition>
</phase>

<gate type="user">
"Issue #N ready. Proceed to cleanup and merge?"
Do NOT proceed until the user explicitly confirms.
</gate>

<phase name="finish" order="7">
<action>Invoke `/finishing-a-development-branch`</action>
<action>Use `rotate-status` → `status:merged`</action>
</phase>

</delegate>

---

<track>
Final report with all artifacts linked:

| Phase | Artifact | Link |
|-------|----------|------|
| Spec  | has-spec | Issue #N comment |
| Plan  | has-plan | Issue #N comment |
| PR    | has-pr   | PR #M |
| Review| has-review| Issue #N comment |
| Fix   | has-fix  | Issue #N comment |
| Merge | merged   | main |

Token usage:
- Brainstorming: X tokens
- Planning: Y tokens
- Implementation: Z tokens
- Review: A tokens
- Fixing: B tokens
- Merging: C tokens

total: X+Y+Z+A+B+C tokens
total cost: $W (at $0.000X per token)
</track>
