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

<step name="consult-specs">
**`_reversa_sdd/` is the maintained specification of this system. Brainstorming
starts from what is already known and decided, not from a blank page.**

Invoke `/spec-finder` with the issue title and body. It returns a compact
`## Spec-Anker` brief: the governing units, the blast radius, the rules that apply
**with their confidence markers**, and — most importantly — the decisions already
taken in the 206-question validation interview.

Two rules on using it:

- **Never re-open a settled decision.** If the brief's *"Already decided"* section
  covers the ticket, that is the answer; brainstorming explores what is still open.
  Re-deciding produces a plan that contradicts the spec and fails review.
- **Distinguish decided from implemented.** Many answers are *"decided, not yet
  implemented"*. Planning against a decision as though it were current behaviour
  produces work that does not fit the code that exists.

If `/spec-finder` reports the area is unspecified, say so in the spec file. A
genuinely new area is a normal outcome — silently inventing an anchor is not.
</step>

<step name="invoke-brainstorming">
Invoke `/brainstorming` with:
- Full issue body (if existing) or user's free-text description
- The **`## Spec-Anker` brief** from `consult-specs` — existing rules, prior
  decisions, known gaps
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
<description>Produce a detailed implementation plan with TDD-structured tasks,
binding it to the architecture decisions that govern the change.</description>

<step name="consult-adrs">
**The planner owns architectural conformance — implementers only execute the plan.**

1. Read the ADR index `_reversa_sdd/adrs/README.md` (one line per ADR).
2. Read **in full** only the ADRs this change actually touches.
3. Two are **always** applicable and must be considered for every change:
   - **ADR 0019** — implementation details must not leak into the public API
     (no storage/mechanism markers in paths, no internal paths as field values,
     one response contract per endpoint).
   - **ADR 0022** — one authority per user-facing quantity (never add a second
     producer of a number a user can see).
4. If the change would violate an ADR, **stop and raise it with the user** before
   planning further. An ADR is superseded by a new ADR, never by an
   implementation that quietly departs from it.
</step>

<step name="carry-spec-anchor">
Carry the `## Spec-Anker` brief from Phase 2 into the plan, refreshed if planning
revealed units the brainstorm did not touch (re-invoke `/spec-finder` with the
concrete files the plan will change — Route A is the most precise).

**The plan file MUST contain a `## Spec-Anker` section** in the same shape as
`## Binding ADRs`: per unit, the concrete rule that constrains *this* feature, with
its citation and marker. Implementers inherit it through the plan and need no spec
access of their own.

```markdown
## Spec-Anker
- `wing-design/spar-sizing/` — 🟡 `moment_fn` carries **un-factored** M(y);
  `g_limit`/`j` are applied once at `spar_solver.py:730` (`Q-WD-8`). Do not
  re-apply them in the new caller.
- `aero-analysis/` — 🟢 the cruise point is the single source of `cd0`, `e` and
  `L/D` (`Q-AA-1`, gh-924). Read the context; do not recompute.
- ⚠ **Decided, not implemented:** `Q-WD-8 ②` fixes the `_MIN_REAR_X_C` clamp
  order. The current code still has the defect — plan against the code, and note
  whether this ticket should carry the fix.
```

**A spec statement is superseded only by a new decision recorded in
`_reversa_sdd/`, never by an implementation that quietly departs from it** — the
same rule ADRs follow. If the ticket requires departing from the spec, raise it
with the user; the outcome is a spec update, not an undocumented exception.
</step>

<step name="invoke-planning">
Invoke `/writing-plans` with:
- The approved spec from Phase 2
- TDD directives: every implementation task must follow RED-GREEN-REFACTOR
- The **binding ADRs** identified in `consult-adrs`
- The **`## Spec-Anker`** from `carry-spec-anchor`
- If `detect-frontend` is true: include `/vercel-react-best-practices`
  and `/vercel-composition-patterns` as directives for frontend tasks

The plan file MUST contain a **`## Binding ADRs`** section listing, per ADR, the
**concrete constraint on this feature** — not the general rule. Example:

```
## Binding ADRs
- ADR 0019 — the new endpoint is `/airfoils/{name}/polars`; no `db/` or
  storage marker in the path.
- ADR 0022 — mass stays produced solely by the component tree; this feature
  reads it and must not write `design_assumptions["mass"]`.
- ADR 0020 — the Re-clamp fallback emits a `DesignWarning`
  (`category: substituted_assumption`, `severity: notice`), never a silent default.
```

Implementers receive these constraints through the plan and need no ADR access
of their own — which also prevents two parallel implementers from interpreting
the same ADR differently.
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
<action>Run the `write-spec-addendum` step of `/supercycle-merge` — this path
merges without going through that skill, and the addendum is what keeps
`_reversa_sdd/` readable until the next re-extraction. Follow the step there
rather than repeating it here.</action>
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
