# Supercycle Skill Migration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace 10 deprecated `.claude/commands/supercycle/*.md` command files with project-local skills in `.claude/skills/supercycle/` that delegate workflow logic to superpowers skills while orchestrating GitHub tracking, SonarQube integration, and Serena codebase exploration.

**Architecture:** Each skill follows a 3-phase GATHER → DELEGATE → TRACK pattern. A shared `tracking.md` file provides reusable operations (load-issue, rotate-status, post-step-comment, read-step-comments, etc.) that all skills reference. Skills invoke superpowers skills for actual work and only handle external-system orchestration themselves.

**Tech Stack:** Claude Code skills (markdown with YAML frontmatter), GitHub CLI (`gh`), SonarQube skills, superpowers skills.

**Spec:** `docs/superpowers/specs/2026-04-29-supercycle-skill-migration-design.md`

---

## File Structure

```
.claude/skills/supercycle/
  SKILL.md              ← ticket (entry point skill — brainstorm into GH Issue)
  work.md               ← full dev cycle skill
  implement.md          ← skip brainstorming, direct implementation
  bug.md                ← bug intake + TDD fix
  review.md             ← comprehensive PR review
  fix.md                ← apply review findings
  merge.md              ← CI + quality gate + merge
  status.md             ← project health dashboard
  init.md               ← toolchain setup
  tracking.md           ← shared library (not a skill — no frontmatter)
```

Note: Claude Code skills use `SKILL.md` as the entry point. Since
`ticket` is the most common standalone entry point (and the one
listed first in the supercycle flow), it becomes `SKILL.md`. All
other skills are additional files in the same directory that can
be invoked by name.

**Wait — correction:** Each skill needs its own `SKILL.md` to be
independently invocable. The directory structure should be:

```
.claude/skills/supercycle/
  tracking.md                  ← shared library (plain markdown, no frontmatter)
  ticket/SKILL.md              ← brainstorm into GH Issue
  work/SKILL.md                ← full dev cycle
  implement/SKILL.md           ← direct implementation
  bug/SKILL.md                 ← bug intake + TDD fix
  review/SKILL.md              ← comprehensive PR review
  fix/SKILL.md                 ← apply review findings
  merge/SKILL.md               ← CI + quality gate + merge
  status/SKILL.md              ← project health dashboard
  init/SKILL.md                ← toolchain setup
```

Each `SKILL.md` references `../tracking.md` for shared operations.

---

### Task 1: Create `tracking.md` shared library

**Files:**
- Create: `.claude/skills/supercycle/tracking.md`

This is the foundation all skills depend on. It defines reusable
operations as named sections with exact `gh` commands.

- [ ] **Step 1: Create the tracking.md file**

```markdown
# Supercycle Tracking Reference

Shared library imported by all supercycle skills. This is NOT a
skill — it has no frontmatter and cannot be invoked directly.
Skills reference operations here by section name.

---

## Label Catalog

### Step Labels (`has-*`)

Applied once when a step artifact is produced. They accumulate —
an issue may carry several `has-*` labels at once.

| Label | Color | Meaning |
|---|---|---|
| `has-spec` | `#0E8A16` | Acceptance criteria / spec written |
| `has-plan` | `#1D76DB` | Implementation plan attached |
| `has-pr` | `#6F42C1` | Pull request opened |
| `has-review` | `#E4A221` | Code review comment posted |
| `has-fix` | `#FBCA04` | Review findings addressed |
| `has-root-cause` | `#D93F0B` | Root cause identified (bug flow) |
| `has-reproduction` | `#B60205` | Reproduction test added (bug flow) |

### Status Labels (`status:*`)

Only ONE `status:*` label is active at a time. Each skill removes
the previous one and adds the next.

| Label | Color | Meaning |
|---|---|---|
| `status:brainstorming` | `#C2E0C6` | Active brainstorming / design |
| `status:planning` | `#BFD4F2` | Implementation plan being written |
| `status:ready` | `#0075CA` | Ticket refined, ready for implementation |
| `status:implementing` | `#6F42C1` | Code being written |
| `status:in-review` | `#E4A221` | PR under review |
| `status:fixing` | `#FBCA04` | Review findings being addressed |
| `status:merging` | `#0E8A16` | CI passing, merge in progress |
| `status:merged` | `#333333` | Issue closed, PR merged |

---

## Operations

### `ensure-labels`

Idempotent creation of all tracking labels. Safe to re-run.

```bash
gh label create "has-spec"         --description "Acceptance criteria written"      --color "0E8A16" 2>/dev/null || true
gh label create "has-plan"         --description "Implementation plan attached"      --color "1D76DB" 2>/dev/null || true
gh label create "has-pr"           --description "Pull request opened"               --color "6F42C1" 2>/dev/null || true
gh label create "has-review"       --description "Code review comment posted"        --color "E4A221" 2>/dev/null || true
gh label create "has-fix"          --description "Review findings addressed"         --color "FBCA04" 2>/dev/null || true
gh label create "has-root-cause"   --description "Root cause identified"             --color "D93F0B" 2>/dev/null || true
gh label create "has-reproduction" --description "Reproduction test added"           --color "B60205" 2>/dev/null || true

gh label create "status:brainstorming" --description "Active brainstorming"          --color "C2E0C6" 2>/dev/null || true
gh label create "status:planning"      --description "Plan in progress"              --color "BFD4F2" 2>/dev/null || true
gh label create "status:ready"         --description "Ready for implementation"      --color "0075CA" 2>/dev/null || true
gh label create "status:implementing"  --description "Code being written"            --color "6F42C1" 2>/dev/null || true
gh label create "status:in-review"     --description "PR under review"               --color "E4A221" 2>/dev/null || true
gh label create "status:fixing"        --description "Review findings being fixed"   --color "FBCA04" 2>/dev/null || true
gh label create "status:merging"       --description "CI passing, merging"           --color "0E8A16" 2>/dev/null || true
gh label create "status:merged"        --description "Issue closed, PR merged"       --color "333333" 2>/dev/null || true
```

### `load-issue`

Load a GH Issue and parse its contents.

**Inputs:** `ISSUE` — issue number

```bash
gh issue view $ISSUE --json number,title,body,labels,state,comments
```

Parse: body, labels (especially `has-*` and `status:*`), linked PRs,
checkbox items from body.

### `load-pr`

Load a PR and parse its contents.

**Inputs:** `PR` — PR number

```bash
gh pr view $PR --json number,title,url,headRefName,body,additions,deletions,files,reviews
gh pr diff $PR --stat
```

Parse: linked issues (from `Closes #N` in body), branch name,
files changed, line counts.

### `read-step-comments`

Read prior step comments from a GH Issue timeline to pick up
context from previous phases.

**Inputs:** `ISSUE`, optional `LABEL` filter (e.g. `has-spec`)

```bash
gh issue view $ISSUE --json comments --jq '.comments[].body'
```

Filter comments by looking for the `## 🏷️ <label>` header.
If `LABEL` is given, return only that step's comment body.
If no filter, return all `has-*` comments.

This is the primary cross-session context transfer mechanism.
Skills that depend on prior phases MUST call this in GATHER.

### `rotate-status`

Remove all current `status:*` labels and apply a new one.

**Inputs:** `ISSUE`, `NEW_STATUS` (e.g. `status:implementing`)

```bash
CURRENT=$(gh issue view "$ISSUE" --json labels \
  --jq '.labels[].name | select(startswith("status:"))' \
  | tr '\n' ',' | sed 's/,$//')
[ -n "$CURRENT" ] && gh issue edit "$ISSUE" --remove-label "$CURRENT"
gh issue edit "$ISSUE" --add-label "$NEW_STATUS"
```

### `post-step-comment`

Post a structured comment with substantive content, then add the
`has-*` label. Always post the comment FIRST, then the label.

**Inputs:** `ISSUE`, `LABEL`, `SKILL_NAME`, `BODY`

The comment body MUST contain the actual artifact — not a status
marker but the full content (spec text, plan, review findings, etc.):

| Label | Comment MUST contain |
|---|---|
| `has-spec` | Full design spec / acceptance criteria |
| `has-plan` | Implementation plan with task breakdown |
| `has-root-cause` | Error, root cause, introducing commit, severity, affected features, proposed fix |
| `has-reproduction` | Test name, file path, test code, failing output |
| `has-pr` | PR number/link, branch, summary of changes, files modified, quality gate results |
| `has-review` | Full review report: verdict, findings by severity, task completeness |
| `has-fix` | Fix report: findings fixed with file:line, findings skipped with rationale |

```bash
gh label create "$LABEL" --description "..." --color "..." 2>/dev/null || true

gh issue comment "$ISSUE" --body "$(cat <<'BODY'
## 🏷️ $LABEL

> Label `$LABEL` added by **supercycle/$SKILL_NAME** · $(date -u +%Y-%m-%d)

---

$BODY_CONTENT
BODY
)"

gh issue edit "$ISSUE" --add-label "$LABEL"
```

### `fetch-sonar-context`

Check if an issue or file list has SonarQube findings.

**Inputs:** `ISSUE` number or file list

If the issue body mentions SonarQube rule IDs (e.g. `S1234`) or
links to sonarcloud.io, use `/sonarqube:sonar-list-issues` to get
current line numbers and rule details, and `/sonarqube:sonar-analyze`
for deeper analysis on affected files.

If given a file list, run `/sonarqube:sonar-analyze` on each file.

Return findings as structured context for the delegated skill.

### `detect-frontend`

Check if frontend files are affected.

**Inputs:** diff output or file list

```bash
gh pr diff $PR --stat | grep -q '^frontend/' && echo "true" || echo "false"
```

Or for a file list: check if any path starts with `frontend/`.

When true, activate:
- `/vercel-react-best-practices` and `/vercel-composition-patterns`
  as additional context for implementation subagents
- Both Vercel skills as review lenses alongside
  `/pr-review-toolkit:review-pr`

---

## Comment Template

Every tracking comment follows this structure:

```markdown
## 🏷️ <label-name>

> Label `<label-name>` added by **supercycle/<skill-name>** · <ISO-8601 date>

---

<substantive content — the full artifact, not a summary>
```

---

## Tracking Points per Skill

| Skill | Reads | Writes (step labels) | Status transitions |
|---|---|---|---|
| `ticket` | — | `has-spec` | `→ status:ready` |
| `work` | prior comments | `has-spec`, `has-plan`, `has-pr`, `has-review`, `has-fix` | `→ brainstorming → planning → implementing → in-review → merged` |
| `implement` | `has-spec`, `has-plan` | `has-pr`, `has-review`, `has-fix` | `→ implementing → merged` |
| `bug` | prior comments | `has-root-cause`, `has-reproduction`, `has-pr`, `has-review`, `has-fix` | `→ implementing → merged` |
| `review` | `has-spec`, `has-plan`, `has-pr` | `has-review` | `→ in-review` |
| `fix` | `has-review` | `has-fix` | `→ fixing` |
| `merge` | `has-review`, `has-fix` | — | `→ merging → merged` |
| `status` | — (reads issues/PRs directly) | — | — |
| `init` | — | — (runs ensure-labels) | — |
```

- [ ] **Step 2: Verify the file was created correctly**

```bash
test -f .claude/skills/supercycle/tracking.md && echo "OK" || echo "MISSING"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/supercycle/tracking.md
git commit -m "chore: add supercycle tracking.md shared library

Shared reference for GH Issue lifecycle tracking — label catalog,
comment templates, and reusable operations (load-issue, rotate-status,
post-step-comment, read-step-comments, etc.)."
```

---

### Task 2: Create `init` skill

**Files:**
- Create: `.claude/skills/supercycle/init/SKILL.md`

The simplest skill — no skill delegation except SonarQube, no
chaining. Good starting point to validate the skill format works.

- [ ] **Step 1: Create the init skill file**

```markdown
---
name: supercycle-init
description: "Check and install all tools, dependencies, and services required by the supercycle workflow"
---

# /supercycle:init — Toolchain Setup & Verification

Argument: **$ARGUMENTS**

Verifies all tools and dependencies required by the supercycle
workflow are installed and configured. Installs anything missing.

---

## Phase 1 — System Tools

Check each tool. If missing, report it.

```bash
git --version || echo "MISSING: Install git"
gh --version || echo "MISSING: brew install gh"
gh auth status || echo "MISSING: Run 'gh auth login'"
python3 --version || echo "MISSING: Install Python 3.11+"
poetry --version || echo "MISSING: pipx install poetry"
node --version || echo "MISSING: brew install node"
npm --version
```

## Phase 2 — Backend Dependencies

```bash
poetry install --no-interaction --no-root
poetry run ruff --version || echo "MISSING: poetry add --group dev ruff"
poetry run pytest --version || echo "MISSING: poetry add --group dev pytest"
```

## Phase 3 — Frontend Dependencies

```bash
cd frontend
npm ci || npm install
npx eslint --version || echo "MISSING"
npx vitest --version || echo "MISSING"
npx depcruise --version || echo "MISSING"
npx playwright --version 2>/dev/null || echo "INFO: Playwright not installed"
```

## Phase 4 — External Services

### SonarQube

Invoke `/sonarqube:sonar-integrate` to ensure `sonarqube-cli` is
installed, authentication is valid, and MCP server is wired in.

After the skill completes:
```bash
test -f sonar-project.properties && echo "SonarQube configured" || echo "MISSING"
```

### GitHub Actions

```bash
test -f .github/workflows/test.yml && echo "CI workflow configured" || echo "MISSING"
```

## Phase 5 — Tracking Labels

Run the `ensure-labels` operation from `../tracking.md` to create
all tracking labels idempotently.

## Phase 6 — Smoke Test

```bash
poetry run ruff check --select E999 app/main.py
poetry run pytest --co -q 2>/dev/null | tail -1
cd frontend && npm run lint 2>&1 | tail -1
cd frontend && npm run deps:check 2>&1 | tail -1
```

## Phase 7 — Report

Present a tool/version/status table:

```
| Category | Tool | Version | Status |
|----------|------|---------|--------|
| System   | git  | X.Y.Z   | ✓      |
| ...      | ...  | ...     | ...    |
```
```

- [ ] **Step 2: Verify the skill file exists and has correct frontmatter**

```bash
head -4 .claude/skills/supercycle/init/SKILL.md
```

Expected: YAML frontmatter with `name: supercycle-init`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/supercycle/init/SKILL.md
git commit -m "chore: add supercycle/init skill — toolchain setup"
```

---

### Task 3: Create `status` skill

**Files:**
- Create: `.claude/skills/supercycle/status/SKILL.md`

Another self-contained skill — no superpowers delegation, pure
external-system dashboard.

- [ ] **Step 1: Create the status skill file**

```markdown
---
name: supercycle-status
description: "Project health dashboard — GH issues, SonarQube status, test health, and next-phase recommendations"
---

# /supercycle:status — Project Health Dashboard

Argument: **$ARGUMENTS**

Generate a comprehensive status report covering GitHub issues,
SonarQube code quality, test health, and strategic recommendations.

---

## Phase 1 — GitHub Issues Overview

### Issue Statistics

```bash
gh issue list --state open --json number --jq 'length'
gh issue list --state closed --json number --jq 'length'
```

### Open Issues Table

```bash
gh issue list --state open --limit 50 \
  --json number,title,labels,createdAt \
  --jq '.[] | "#\(.number) [\(.labels | map(.name) | join(","))] \(.title)"'
```

Present as:

```
| # | Labels | Title | Age |
|---|--------|-------|-----|
```

### Open PRs

```bash
gh pr list --state open --json number,title,headRefName,additions,deletions
```

## Phase 2 — SonarQube Code Quality

Invoke `/sonarqube:sonar-quality-gate` for overall project status.
Invoke `/sonarqube:sonar-list-issues` for issue distribution by
severity.

Present:
```
| Severity | Count |
|----------|-------|
```

## Phase 3 — Test Health

```bash
poetry run pytest --co -q 2>/dev/null | tail -1
poetry run pytest -m "not slow" --tb=no -q 2>&1 | tail -3
cd frontend && npm run test:unit 2>&1 | tail -5
cd frontend && npm run deps:check 2>&1 | tail -5
```

## Phase 4 — Recommendations

Based on the data gathered, classify work into a priority matrix:

| | Urgent | Not Urgent |
|---|--------|------------|
| **Important** | Bugs, BLOCKER issues | HIGH SonarQube issues, test gaps |
| **Not Important** | MEDIUM/LOW SonarQube | Nice-to-have features |

Suggest next phases with specific ticket numbers and scope estimates.
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/supercycle/status/SKILL.md
git commit -m "chore: add supercycle/status skill — project health dashboard"
```

---

### Task 4: Create `ticket` skill

**Files:**
- Create: `.claude/skills/supercycle/ticket/SKILL.md`

First skill that delegates to a superpowers skill (`/brainstorming`).
Thin wrapper: gather user preferences → delegate → create GH Issue.

- [ ] **Step 1: Create the ticket skill file**

```markdown
---
name: supercycle-ticket
description: "Ticket intake: brainstorm with user, explore codebase, create refined GH Issue — read-only, no code changes"
argument-hint: "<free-form description of the idea, feature, bug, or task>"
---

# /supercycle:ticket — Ticket Creation & Refinement

Argument: **$ARGUMENTS**

Brainstorm an idea into a refined GH Issue. This skill is
**read-only on the repository** — the only external writes are
to GitHub Issues via `gh`.

For implementation after ticket creation, use:
- `/supercycle:work` — brainstorm + implement + merge
- `/supercycle:implement` — skip brainstorming, start coding

---

## GATHER

### 1. Ask Issue Type

Present a selector — do NOT auto-detect:

> **What type of issue is this?**
> 1. **Feature** — new capability or enhancement
> 2. **Bug** — something is broken
> 3. **Task** — infra, docs, CI/CD, refactoring, tooling

Map the choice to:

| Choice | Label | Template |
|--------|-------|----------|
| Feature | `enhancement` | `.github/ISSUE_TEMPLATE/feature.md` |
| Bug | `bug` | `.github/ISSUE_TEMPLATE/bug.md` |
| Task | `task` | `.github/ISSUE_TEMPLATE/task.md` |

### 2. Ask Brainstorming Depth

> **How deep should we go?**
> 1. **Light** — analyze codebase, draft ticket, ask your approval
> 2. **Medium** — + propose 2-3 approaches with trade-offs
> 3. **Full** — + multiple clarifying questions, iterative refinement

---

## DELEGATE

Invoke `/brainstorming` with:
- The user's full description text from `$ARGUMENTS`
- The chosen issue type and brainstorming depth
- Instruction that output is for a GH Issue, not implementation

The brainstorming skill handles:
- Codebase exploration (uses Serena LSP tools)
- Clarifying questions (one at a time)
- 2-3 approaches with trade-offs and recommendation
- Design presentation in sections with user approval
- Spec writing to `docs/superpowers/specs/`

---

## TRACK

After brainstorming produces a spec:

### 1. Create GH Issue

Use the spec output to fill the chosen GH Issue template:

```bash
gh issue create \
  --title "<type-prefix>: <concise title>" \
  --body "<spec formatted as issue template>" \
  --label "<type-label>"
```

### 2. Post step comment and labels

Use `post-step-comment` from `../tracking.md`:
- **Label:** `has-spec`
- **Body:** Full spec / acceptance criteria from brainstorming output

### 3. Set status

Use `rotate-status` from `../tracking.md`:
- **New status:** `status:ready`

### 4. Report

> "Created issue #N: <title> — <url>"
>
> **Next steps:**
> - `/supercycle:work #N` — brainstorm implementation + build
> - `/supercycle:implement #N` — skip brainstorming, start coding
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/supercycle/ticket/SKILL.md
git commit -m "chore: add supercycle/ticket skill — brainstorm into GH Issue"
```

---

### Task 5: Create `work` skill

**Files:**
- Create: `.claude/skills/supercycle/work/SKILL.md`

The most complex skill — hybrid chain with user gate after
brainstorming, auto-chain for the rest.

- [ ] **Step 1: Create the work skill file**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/supercycle/work/SKILL.md
git commit -m "chore: add supercycle/work skill — full dev cycle orchestrator"
```

---

### Task 6: Create `implement` skill

**Files:**
- Create: `.claude/skills/supercycle/implement/SKILL.md`

- [ ] **Step 1: Create the implement skill file**

```markdown
---
name: supercycle-implement
description: "Skip brainstorming — go straight to implementation of a GH issue with TDD, review, and merge"
argument-hint: "<GH issue number(s), comma-separated: #188, #190>"
---

# /supercycle:implement — Direct Implementation

Argument: **$ARGUMENTS**

Enter the supercycle at the implementation phase, skipping
brainstorming. Use when the issue is already well-defined with a
spec and/or plan.

---

## GATHER

### 1. Load Issues

For each issue number in arguments:

Use `load-issue` from `../tracking.md`.
Use `read-step-comments` with filter `has-spec`, `has-plan` to
pick up spec and plan from prior phases.

### 2. Fetch SonarQube Context

Use `fetch-sonar-context` from `../tracking.md`.

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
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/supercycle/implement/SKILL.md
git commit -m "chore: add supercycle/implement skill — direct implementation"
```

---

### Task 7: Create `bug` skill

**Files:**
- Create: `.claude/skills/supercycle/bug/SKILL.md`

- [ ] **Step 1: Create the bug skill file**

```markdown
---
name: supercycle-bug
description: "Bug intake: investigate root cause, create GH ticket, TDD fix, review, and merge — all in one auto-chained flow"
argument-hint: "<error log, description, or GH issue number>"
---

# /supercycle:bug — Bug Intake & Fix

Argument: **$ARGUMENTS**

Fast-track supercycle for bugs. Auto-chains all phases with no
user gates. Takes a raw error log, bug description, or existing
GH issue number and drives it through investigation → ticket →
fix → review → merge.

---

## GATHER

### If numeric (e.g. `210`, `#210`):

Use `load-issue` from `../tracking.md`.
Use `read-step-comments` to pick up any prior context.

### If free-text (error log / description):

Parse the input for:
- Error message / exception
- Stack trace — file paths, line numbers
- Endpoint / trigger
- HTTP status

### Fetch SonarQube Context

Use `fetch-sonar-context` from `../tracking.md`.

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
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/supercycle/bug/SKILL.md
git commit -m "chore: add supercycle/bug skill — bug intake + TDD fix"
```

---

### Task 8: Create `review` skill

**Files:**
- Create: `.claude/skills/supercycle/review/SKILL.md`

- [ ] **Step 1: Create the review skill file**

```markdown
---
name: supercycle-review
description: "Comprehensive PR review: dispatch specialized review agents, check issue task completeness, aggregate findings"
argument-hint: "<PR numbers, comma-separated: 200, 201>"
---

# /supercycle:review — Comprehensive PR Review

Argument: **$ARGUMENTS**

Dispatch specialized review agents on existing PRs. Checks issue
task completeness and aggregates findings by severity.

---

## GATHER

### 1. Load PRs

For each PR number in arguments:

Use `load-pr` from `../tracking.md`.

### 2. Extract Linked Issues

Parse `Closes #N` from PR body to find linked issues.

### 3. Read Prior Context

Use `read-step-comments` on linked issues with filters
`has-spec`, `has-plan`, `has-pr` to get context from prior phases.

### 4. Set Status

Use `rotate-status` → `status:in-review` for each linked issue.

---

## DELEGATE

### 1. Comprehensive Review

Invoke `/pr-review-toolkit:review-pr` with:
- Context: spec + plan from step comments so reviewers know
  what was intended, not just what was built
- If `detect-frontend` is true: add `/vercel-react-best-practices`
  and `/vercel-composition-patterns` as review lenses
- Dispatches applicable specialized agents automatically

### 2. Issue Task Completeness Check

This is inline — no skill covers this.

For each linked issue, parse all checkbox items (`- [ ]` and
`- [x]`) from the issue body.

For each unchecked task, classify:

| Category | Criteria | Action |
|----------|----------|--------|
| **Done in PR** | PR diff clearly implements this | Check the box — update issue body |
| **Agent-fixable** | Can be fixed without human judgment | Add to fix list for `/supercycle:fix` |
| **Human Only** | Requires human judgment, manual testing, or a decision | Mark `🧑 Human Only`, assign to user, add comment |

For "Human Only" tasks:
```bash
gh issue comment $ISSUE --body "## 🧑 Human Action Required
The following tasks require human action:
- [ ] <task> — **Reason:** <why agent can't do this>"
```

For "Done in PR" tasks:
Update issue body with checked boxes via `gh issue edit`.

---

## TRACK

Use `post-step-comment`: `has-review` — full review report:
verdict, findings by severity, task completeness matrix.

Report:
```
## Review Results

### PR #N — <title> (Closes #ISSUE)

#### Task Completeness
| # | Task | Status | Who |
|---|------|--------|-----|

#### Findings by Severity
| Severity | Count | Details |
|----------|-------|---------|

### Verdict
PR #N: APPROVED / CHANGES REQUESTED / BLOCKED ON HUMAN

### Next Steps
- /supercycle:fix <PRs with findings>
- /supercycle:merge <approved PRs>
```
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/supercycle/review/SKILL.md
git commit -m "chore: add supercycle/review skill — comprehensive PR review"
```

---

### Task 9: Create `fix` skill

**Files:**
- Create: `.claude/skills/supercycle/fix/SKILL.md`

- [ ] **Step 1: Create the fix skill file**

```markdown
---
name: supercycle-fix
description: "Fix review findings on PR branches — evaluate with technical rigor, fix SonarQube issues, verify"
argument-hint: "<PR numbers, comma-separated: 200, 201>"
---

# /supercycle:fix — Fix Review Findings

Argument: **$ARGUMENTS**

Apply review findings and SonarQube fixes to PR branches.
Evaluates each finding with technical rigor — verifies before
implementing, pushes back on false positives.

---

## GATHER

### 1. Load PR Review Comments

For each PR number in arguments:

```bash
gh api repos/{owner}/{repo}/pulls/$PR/comments \
  --jq '.[] | {path: .path, line: .line, body: .body}'
gh pr view $PR --json reviews \
  --jq '.reviews[] | {state: .state, body: .body}'
```

### 2. Read Prior Review

Use `read-step-comments` on linked issues with filter `has-review`
to get the full review report with findings, severity, and
file:line references. This is the primary input.

### 3. Fetch SonarQube Issues

Use `/sonarqube:sonar-list-issues` to get current SonarQube issues
on the PR branch.

### 4. Set Status

Use `rotate-status` → `status:fixing` for each linked issue.

---

## DELEGATE

### 1. Evaluate Review Findings

Invoke `/receiving-code-review` with:
- Context: the `has-review` comment content as review findings
- For each finding: verify against codebase reality before
  implementing
- Push back on false positives with technical reasoning
- No performative agreement — technical rigor always

### 2. Fix SonarQube Issues

Invoke `/sonarqube:sonar-fix-issue` for each SonarQube issue on
the PR branch.

### 3. Verify

Invoke `/verification-before-completion`:
- Evidence that fixes work
- No regressions
- Quality gates pass

---

## TRACK

Use `post-step-comment`: `has-fix` — fix report:
- Findings fixed with file:line references
- Findings skipped as false positives with rationale
- SonarQube issues resolved

Report:
```
## Fix Results

| PR | Findings | Fixed | Skipped (false positive) |
|----|----------|-------|-------------------------|

### Next Steps
- /supercycle:merge <PR numbers>
```
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/supercycle/fix/SKILL.md
git commit -m "chore: add supercycle/fix skill — review findings + SonarQube fixes"
```

---

### Task 10: Create `merge` skill

**Files:**
- Create: `.claude/skills/supercycle/merge/SKILL.md`

- [ ] **Step 1: Create the merge skill file**

```markdown
---
name: supercycle-merge
description: "Check CI, analyze SonarQube quality gate, and merge PRs with post-merge verification"
argument-hint: "<PR numbers, comma-separated: 200, 201>"
---

# /supercycle:merge — CI Check & Merge

Argument: **$ARGUMENTS**

Check CI status, analyze SonarQube quality gates, and merge PRs.

---

## GATHER

### 1. Load PRs

For each PR number in arguments:

Use `load-pr` from `../tracking.md`.

### 2. Verify Prior Steps

Use `read-step-comments` on linked issues with filters
`has-review`, `has-fix` to verify review passed and findings
were addressed before merging.

### 3. CI Status

```bash
gh pr checks $PR
```

If any test check is failing, do NOT proceed. Report the failure:
```
Tests failing on PR #N. Options:
- /supercycle:fix <N> — investigate and fix
- gh pr checks <N> — check again after fix
```

### 4. SonarQube Quality Gate

Invoke `/sonarqube:sonar-quality-gate` for the project.

### 5. Set Status

Use `rotate-status` → `status:merging` for each linked issue.

---

## DELEGATE

### 1. Analyze SonarQube Gate (if failing)

For each failed condition:
- **Security / Reliability / Maintainability:** Block merge.
  Use `/sonarqube:sonar-list-issues` for specifics.
- **Coverage on new code:** Context-dependent. Refactoring/chore
  PRs: coverage gaps on moved code are expected. Feature PRs:
  new code should have tests. Use `/sonarqube:sonar-coverage`.
- **Duplication:** Check if mechanical via
  `/sonarqube:sonar-duplication`.

### 2. Finish

Invoke `/finishing-a-development-branch`:
- Verify tests pass
- Present merge options (merge/PR/keep/discard)
- Execute chosen option
- Clean up worktree

---

## TRACK

Use `rotate-status` → `status:merged` for each linked issue.

Post-merge verification:
```bash
git switch main && git pull github main
poetry run pytest -m "not slow"
```

Report:
```
## Merge Complete

| PR | Issue | Title | Status |
|----|-------|-------|--------|

### Test Results
<pytest output summary>
```
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/supercycle/merge/SKILL.md
git commit -m "chore: add supercycle/merge skill — CI + quality gate + merge"
```

---

### Task 11: Delete old commands and update CLAUDE.md

**Files:**
- Delete: `.claude/commands/supercycle/` (entire directory)
- Modify: `CLAUDE.md`

- [ ] **Step 1: Delete old command files**

```bash
rm -rf .claude/commands/supercycle/
```

Verify:
```bash
ls .claude/commands/supercycle/ 2>/dev/null && echo "STILL EXISTS" || echo "DELETED"
```

Expected: `DELETED`

- [ ] **Step 2: Update CLAUDE.md**

In `CLAUDE.md`, replace all references to `/supercycle:*` commands
with the new skill invocations. The key sections to update:

1. **"Development Workflow — Supercycle"** section — update the
   command table from `/supercycle:work` to `/supercycle:work`
   (same names, but note they're now skills not commands)

2. **"Supercycle Commands (preferred)"** — rename to
   "Supercycle Skills (preferred)" and update the code block

3. **"Flow"** diagram — keep the same flow but note skills
   delegate to superpowers

4. **"Underlying Skills"** table — update to reflect that
   supercycle skills now invoke these directly

5. **"Iron Laws"** — keep unchanged (still enforced)

The command names stay the same (`/supercycle:work`, etc.) —
the user experience doesn't change. The underlying mechanism
shifts from commands to skills.

- [ ] **Step 3: Commit**

```bash
git add -A .claude/commands/supercycle/ CLAUDE.md
git commit -m "chore: remove deprecated supercycle commands, update CLAUDE.md

Supercycle is now implemented as project-local skills in
.claude/skills/supercycle/ instead of deprecated commands in
.claude/commands/supercycle/."
```

---

### Task 12: Smoke test all skills

**Files:** None (verification only)

- [ ] **Step 1: Verify all skill files exist with correct frontmatter**

```bash
for skill in ticket work implement bug review fix merge status init; do
  file=".claude/skills/supercycle/$skill/SKILL.md"
  if [ -f "$file" ]; then
    name=$(head -3 "$file" | grep "^name:" | sed 's/name: *//')
    echo "✓ $skill → $name"
  else
    echo "✗ $skill MISSING"
  fi
done

# Check tracking.md exists (no frontmatter)
test -f .claude/skills/supercycle/tracking.md && echo "✓ tracking.md" || echo "✗ tracking.md MISSING"
```

Expected: All 9 skills present + tracking.md

- [ ] **Step 2: Verify old commands are gone**

```bash
ls .claude/commands/supercycle/ 2>/dev/null && echo "FAIL: old commands still exist" || echo "✓ old commands removed"
```

Expected: `✓ old commands removed`

- [ ] **Step 3: Verify CLAUDE.md references skills not commands**

```bash
grep -c "supercycle" CLAUDE.md
```

Verify the supercycle section references the new skills correctly.
