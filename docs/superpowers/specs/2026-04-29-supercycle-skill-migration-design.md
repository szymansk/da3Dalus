# Supercycle Skill Migration Design

Migrate the 10 supercycle slash commands from deprecated
`.claude/commands/supercycle/*.md` to project-local skills in
`.claude/skills/supercycle/`. The new skills become thin orchestrators
that delegate actual work to superpowers skills while providing three
value-adds: GitHub Issue lifecycle tracking, SonarQube quality
integration, and Serena-backed codebase exploration.

## Motivation

The current supercycle commands are monolithic — each reimplements
workflow logic (brainstorming phases, TDD steps, review dispatch)
that superpowers skills already handle well. This creates duplication,
drift between the two systems, and makes it hard to benefit from
superpowers updates.

The new skills follow a single principle: **supercycle orchestrates
external systems; superpowers does the work.**

## Architecture

### The thin wrapper pattern

Every skill follows a 3-phase skeleton:

```
Phase 1 — GATHER
  Load GH issue/PR via tracking operations
  Fetch SonarQube context if relevant
  Set initial GH tracking status
  Detect frontend changes (activates Vercel skills)

Phase 2 — DELEGATE
  Invoke superpowers skill(s) with gathered context
  Chained skills: user gate between phases (features)
                   or auto-chain (bugs)

Phase 3 — TRACK
  Update GH tracking (post-step labels, rotate status)
  Report next steps to user
```

### Shared library: `tracking.md`

A non-invocable reference file imported by all skills. Provides
named operations that skills reference instead of inlining bash.

| Operation | Inputs | What it does |
|---|---|---|
| `load-issue` | `ISSUE` number | `gh issue view` — parse body, labels, linked PRs |
| `load-pr` | `PR` number | `gh pr view` — parse diff stats, linked issues, branch |
| `read-step-comments` | `ISSUE`, optional `LABEL` filter | Read all `has-*` comments from issue timeline. If `LABEL` given, return only that step's comment. Used by downstream skills to pick up context from previous phases. |
| `fetch-sonar-context` | `ISSUE` or file list | Check if issue/files have SonarQube findings, fetch via `/sonarqube:sonar-list-issues` and `/sonarqube:sonar-analyze` |
| `rotate-status` | `ISSUE`, `NEW_STATUS` | Remove old `status:*` label, add new one |
| `post-step-comment` | `ISSUE`, `LABEL`, `SKILL`, `BODY` | Post structured comment with substantive content (not just a marker — the full artifact: spec text, plan, review findings, fix report, etc.) then add `has-*` label |
| `ensure-labels` | — | Idempotent creation of all tracking labels |
| `detect-frontend` | diff or file list | Returns true if `frontend/` files are touched |

Label catalog and comment template format carry over from the
current `tracking.md` unchanged.

### GH comments as cross-session memory

GH Issue comments are the **primary context transfer mechanism**
between supercycle phases that may run in different sessions. Each
`post-step-comment` writes a substantive artifact — not a status
marker but the actual content:

| Step label | Comment contains |
|---|---|
| `has-spec` | Full design spec / acceptance criteria |
| `has-plan` | Implementation plan with task breakdown |
| `has-root-cause` | Bug analysis: error, root cause, introducing commit, severity, affected features, proposed fix |
| `has-reproduction` | Test name, file path, test code, failing output |
| `has-pr` | PR number/link, branch, summary of changes, files modified, quality gate results |
| `has-review` | Full review report: verdict, findings by severity, task completeness |
| `has-fix` | Fix report: findings fixed with file:line, findings skipped as false positives with rationale |

Every skill that depends on a prior phase's output MUST read the
relevant step comment via `read-step-comments` in its GATHER phase
rather than assuming the information is available from the current
session context. This ensures skills work correctly both within a
chained session and when invoked standalone across sessions.

### Review architecture: two tiers

| When | Skill | Scope |
|---|---|---|
| Between tasks during implementation | `/requesting-code-review` | Quick single-agent check |
| Final review before merge/PR | `/pr-review-toolkit:review-pr` | Comprehensive multi-agent (code-reviewer, silent-failure-hunter, test-analyzer, type-analyzer, comment-analyzer, code-simplifier) |

### TDD enforcement

TDD is not a top-level orchestration step. It is embedded into the
implementation layer:

- `/writing-plans` creates tasks that specify TDD requirements
- `/subagent-driven-development` dispatches subagents that invoke
  `/test-driven-development` internally
- Exception: `/supercycle:bug` invokes `/test-driven-development`
  directly because bugs skip the plan/subagent layer

### Frontend detection

When `detect-frontend` is true:

- **Implementation:** subagent context includes
  `/vercel-react-best-practices` and `/vercel-composition-patterns`
- **Review:** both Vercel skills invoked as additional review lenses
  alongside `/pr-review-toolkit:review-pr`

## Skill specifications

### `ticket`

Brainstorm an idea into a refined GH Issue. Read-only on the repo.

```
GATHER
  Parse user input (free-text description)
  Ask issue type (Feature / Bug / Task) and brainstorming depth
  (Light / Medium / Full)

DELEGATE
  /brainstorming
    - Handles: codebase exploration, clarifying questions,
      approaches with trade-offs, design presentation, spec writing
    - Writes spec to docs/superpowers/specs/

TRACK
  Create GH Issue from spec (gh issue create using template)
  post-step-comment: has-spec — full spec/acceptance criteria
  rotate-status: → status:ready
  Report: issue URL + next steps
```

### `work`

Full development cycle. Hybrid chain — user gate after brainstorming,
auto-chain for the rest.

```
GATHER
  load-issue (if numeric input) or accept free-text
  read-step-comments (pick up any prior context if issue exists)
  fetch-sonar-context
  rotate-status: → status:brainstorming

DELEGATE (chained, user gate after step 1)
  1. /brainstorming
     → USER GATE: "Issue #N spec ready. Proceed to planning?"
     → post-step-comment: has-spec — full spec/acceptance criteria

  2. /writing-plans
     - TDD directives baked into every task
     - Frontend tasks include Vercel skill directives
     → post-step-comment: has-plan — full plan with task breakdown
     → rotate-status: → status:planning

  3. /using-git-worktrees
     → rotate-status: → status:implementing

  4. /subagent-driven-development
     - Subagents invoke /test-driven-development internally
     - Per-task review via /requesting-code-review
     - Frontend subagents follow /vercel-react-best-practices
       and /vercel-composition-patterns

  5. /pr-review-toolkit:review-pr (comprehensive final review)
     - Frontend changes: add Vercel skills as review lenses
     → post-step-comment: has-review — full review report
     → post-step-comment: has-pr — PR number, branch, changes, quality gates
     → rotate-status: → status:in-review

  6. IF findings:
     /receiving-code-review (evaluate findings with technical rigor)
     /sonarqube:sonar-fix-issue (for each SonarQube issue)
     /verification-before-completion
     → post-step-comment: has-fix — fix report with rationale

  7. /finishing-a-development-branch
     → rotate-status: → status:merged

TRACK
  Final report with all artifacts linked
```

### `implement`

Skip brainstorming. Issue is already well-defined.

```
GATHER
  load-issue(s) — supports comma-separated list
  read-step-comments: has-spec, has-plan (pick up spec + plan from prior phases)
  fetch-sonar-context
  rotate-status: → status:implementing

DELEGATE
  1. /using-git-worktrees

  2. /subagent-driven-development
     - Context: pass spec + plan from step comments to subagents
     - Same TDD + frontend rules as work

  3. /pr-review-toolkit:review-pr
     → post-step-comment: has-review — full review report
     → post-step-comment: has-pr — PR number, branch, changes, quality gates

  4. IF findings:
     /receiving-code-review
     /sonarqube:sonar-fix-issue
     /verification-before-completion
     → post-step-comment: has-fix — fix report with rationale

  5. /finishing-a-development-branch

TRACK
  rotate-status: → status:merged
  Report PRs created
```

### `bug`

Fast-track bug fix. Auto-chains with no user gates.

```
GATHER
  Parse error log / description / issue number
  fetch-sonar-context
  IF numeric: load-issue + read-step-comments (prior context)

DELEGATE (auto-chain, no user gates)
  1. /systematic-debugging
     - Root cause investigation (what, where, why, when, blast radius)
     → post-step-comment: has-root-cause — error, root cause,
       introducing commit, severity, affected features, proposed fix

  2. Create GH Issue (inline gh issue create)
     - Only if input was free-text, skip if already a GH issue
     - Post has-root-cause comment AFTER issue creation if new issue
     → rotate-status: → status:implementing

  3. /using-git-worktrees

  4. /test-driven-development (directly — no plan layer)
     - RED: failing test reproducing bug
     → post-step-comment: has-reproduction — test name, file path,
       test code, failing output
     - GREEN: minimal fix for root cause
     - REFACTOR: clean up

  5. /verification-before-completion

  6. /pr-review-toolkit:review-pr
     → post-step-comment: has-review — full review report
     → post-step-comment: has-pr — PR number, branch, changes

  7. IF findings:
     /receiving-code-review
     /sonarqube:sonar-fix-issue
     → post-step-comment: has-fix — fix report

  8. /finishing-a-development-branch

TRACK
  rotate-status: → status:merged
  Report: issue, PR, root cause, test name
```

### `review`

Comprehensive review of existing PRs.

```
GATHER
  load-pr(s) — supports comma-separated list
  Extract linked issues (from Closes #N in PR body)
  read-step-comments: has-spec, has-plan, has-pr (context from prior phases)
  rotate-status: → status:in-review

DELEGATE
  1. /pr-review-toolkit:review-pr
     - Context: pass spec + plan from step comments so reviewers
       know what was intended, not just what was built
     - Dispatches applicable specialized agents
     - Frontend changes: add Vercel skills as review lenses
     - Aggregates findings by severity

  2. Issue task completeness check (inline — no skill for this)
     - Parse checkboxes from linked issue body
     - Classify each unchecked task:
       Done in PR → check off
       Agent-fixable → add to fix list
       Human Only → mark + assign + comment

TRACK
  post-step-comment: has-review — full review report: verdict,
    findings by severity, task completeness matrix
  Report: verdict per PR, findings by severity, next steps
```

### `fix`

Apply review findings and SonarQube fixes to PR branches.

```
GATHER
  load-pr(s) review comments
  read-step-comments: has-review (get the full review report with
    findings, severity, file:line references — this is the input)
  Fetch SonarQube issues on PR branch via
    /sonarqube:sonar-list-issues
  rotate-status: → status:fixing

DELEGATE
  1. /receiving-code-review
     - Context: pass has-review comment content as the review findings
     - Evaluate each finding with technical rigor
     - Verify before implementing
     - Push back on false positives with reasoning

  2. /sonarqube:sonar-fix-issue
     - For each SonarQube issue on the PR branch

  3. /verification-before-completion
     - Evidence that fixes work, no regressions

TRACK
  post-step-comment: has-fix — fix report: findings fixed with
    file:line, findings skipped as false positives with rationale,
    SonarQube issues resolved
  Report: fixed / skipped (false positive) / pushed back
```

### `merge`

CI check, SonarQube quality gate, and merge.

```
GATHER
  load-pr(s)
  read-step-comments: has-review, has-fix (verify review passed
    and findings were addressed before merging)
  CI status: gh pr checks
  SonarQube quality gate: /sonarqube:sonar-quality-gate
  rotate-status: → status:merging

DELEGATE
  1. IF SonarQube gate failing:
     Analyze conditions via /sonarqube:sonar-quality-gate
     - Security / Reliability / Maintainability: block merge
     - Coverage on new code: context-dependent (refactor OK, feature not)
     - Duplication: check if mechanical via /sonarqube:sonar-duplication

  2. /finishing-a-development-branch
     - Verify tests, present merge options, execute, cleanup

TRACK
  rotate-status: → status:merged
  Post-merge: poetry run pytest -m "not slow"
  Report: merged PRs, test results
```

### `status`

Project health dashboard. No skill delegation, pure external systems.

```
GH Issues: open/closed counts, open issues table, dependency map, open PRs
SonarQube: /sonarqube:sonar-quality-gate + /sonarqube:sonar-list-issues
Tests: poetry run pytest --co -q, cd frontend && npm run test:unit
Frontend deps: cd frontend && npm run deps:check
Recommendations: priority matrix (urgent/important), suggested phases
```

### `init`

Toolchain verification and setup. No skill delegation except SonarQube.

```
System tools: git, gh, python, poetry, node, npm
Backend deps: poetry install, ruff, pytest
Frontend deps: npm ci, eslint, vitest, dependency-cruiser, playwright
SonarQube: /sonarqube:sonar-integrate
Labels: ensure-labels from tracking.md
Smoke test: ruff check, pytest --co, npm run lint, npm run deps:check
Report: tool/version/status table
```

## File structure

```
.claude/skills/supercycle/
  ticket.md
  work.md
  implement.md
  bug.md
  review.md
  fix.md
  merge.md
  status.md
  init.md
  tracking.md          (shared library, not invocable)
```

## Scope changes from current commands

### Removed: parallel worktree agents in `implement`

The current `/supercycle:implement` builds a file-overlap matrix and
dispatches multiple worktree agents in parallel for conflict-free
issue batches. The new skill delegates to `/subagent-driven-development`
which processes tasks sequentially within a single worktree.

Rationale: parallel worktree orchestration is complex, fragile, and
duplicates what `/dispatching-parallel-agents` could handle. If
parallel execution is needed, the user can invoke
`/dispatching-parallel-agents` directly or we can add it back as
a future enhancement.

### Removed: autonomous refinement subagent in `ticket`

The current `/supercycle:ticket` dispatches a refinement subagent
after issue creation. The new skill relies on `/brainstorming` to
produce a complete spec — the brainstorming skill already handles
iterative refinement, so a separate post-creation pass is redundant.

## Migration plan

1. Create `.claude/skills/supercycle/` with all 10 files
2. Verify each skill invokes correctly
3. Delete `.claude/commands/supercycle/`
4. Update `CLAUDE.md` — replace command references with skill references

## Dependencies

Skills that must be installed for supercycle to work:

| Plugin | Skills used |
|---|---|
| superpowers | brainstorming, writing-plans, using-git-worktrees, subagent-driven-development, executing-plans, test-driven-development, systematic-debugging, requesting-code-review, receiving-code-review, verification-before-completion, finishing-a-development-branch |
| pr-review-toolkit | review-pr |
| sonarqube | sonar-list-issues, sonar-analyze, sonar-fix-issue, sonar-quality-gate, sonar-duplication, sonar-integrate, sonar-coverage |
| vercel (user skills) | vercel-react-best-practices, vercel-composition-patterns |
