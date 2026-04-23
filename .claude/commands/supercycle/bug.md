---
description: "Bug intake: investigate root cause, create GH ticket, fix, review, and merge — all in one flow"
argument-hint: "<error log, description, or GH issue number>"
allowed-tools: Bash, Read, Edit, Write, Glob, Grep, Agent, WebSearch
---

# /supercycle:bug — Bug Intake & Fix

Argument: **$ARGUMENTS**

Fast-track supercycle for bugs. Takes a raw error log, bug
description, or existing GH issue number and drives it through
investigation → ticket → fix → review → merge.

For non-bug work, use:
- `/supercycle:work` — features, brainstorming
- `/supercycle:implement` — well-defined issues, skip brainstorming

---

## Phase 1 — Intake & Triage

### If numeric (e.g. `210`, `#210`):

```bash
gh issue view <number> --json number,title,body,labels,state
```

Read the issue. If it references external systems (SonarQube, Sentry),
fetch current data NOW.

### If free-text (error log / description):

Parse the input for:
- **Error message** — the exact exception or log line
- **Stack trace** — file paths, line numbers, function names
- **Endpoint / trigger** — what action caused the error
- **HTTP status** — 500, 404, etc.

Immediately locate the affected code:
```
grep for error message → find the raise / log site
read the function → understand the call chain
```

---

## Phase 2 — Root Cause Investigation

**Invoke `/systematic-debugging` principles. NO FIXES WITHOUT ROOT
CAUSE.**

### 2a — Reproduce Understanding

Answer these questions before proceeding:
1. **What fails?** — exact error, affected endpoint/function
2. **Where?** — file, line, function name
3. **Why?** — the root cause, not the symptom
4. **When did it break?** — `git log` / `git blame` to find the
   introducing commit
5. **What's the blast radius?** — which other endpoints/features
   are affected?

### 2b — Classify Severity

| Severity | Criteria | Response |
|----------|----------|----------|
| **Critical** | Core feature broken, no workaround | Fix immediately |
| **High** | Feature degraded, workaround exists | Fix now |
| **Medium** | Edge case, minor impact | Fix in normal flow |
| **Low** | Cosmetic, logging, non-functional | Queue for later |

### 2c — Report to User

Present findings concisely:
```
## Bug Analysis

**Error:** <exact message>
**Root cause:** <why it happens>
**Introduced by:** <commit / PR if applicable>
**Severity:** Critical / High / Medium / Low
**Affected:** <list of broken endpoints/features>
**Fix:** <proposed approach in 1-2 sentences>
```

Wait for user confirmation before proceeding. If the user says to
go ahead or the severity is critical, proceed without delay.

---

## Phase 3 — Create GH Issue

**Skip if the input was already a GH issue number.**

Create a bug ticket:

```bash
gh issue create \
  --title "bug: <concise title>" \
  --body "<structured body>" \
  --label "bug"
```

Issue body MUST include:
- **Description** — what's broken
- **Root Cause** — why (from Phase 2)
- **Reproduction** — endpoint + request that triggers it
- **Affected** — list of broken features
- **Fix** — proposed approach

---

## Phase 4 — Implement Fix

### 4a — Branch

```bash
git switch -c fix/gh-<N>-<slug>
```

### 4b — Write Failing Test First

**Invoke `/test-driven-development` — RED phase.**

Write a test that reproduces the bug. The test MUST fail before
the fix and pass after. This is non-negotiable for bugs — it
prevents regressions.

```
# Backend
poetry run pytest <test_file>::<test_name> -v  → MUST FAIL (RED)

# Frontend
cd frontend && npm run test:unit -- <test_file>  → MUST FAIL (RED)
```

If the bug cannot be unit-tested (e.g. async runtime behavior),
document why and ensure integration test coverage.

### 4c — Apply Fix

Fix the root cause identified in Phase 2. Keep the fix minimal —
change only what's necessary. Do NOT refactor surrounding code.

### 4d — Verify — GREEN

```
# Run the new test → MUST PASS
# If frontend changed: check for dependency violations
cd frontend && npm run deps:check
poetry run pytest <test_file>::<test_name> -v

# Run full fast suite → no regressions
poetry run ruff check .
poetry run pytest -m "not slow"
```

**Invoke `/verification-before-completion` — evidence before claims.**

### 4e — Commit & Push

```bash
git add <files>
git commit -m "fix(gh-<N>): <what was fixed>

<root cause explanation>

Closes #<N>"
git push -u github <branch>
```

### 4f — Create PR

```bash
gh pr create --title "fix(gh-<N>): <title>" --body "..."
```

PR body MUST include:
- Summary with root cause
- Test plan with the new test
- `Closes #N`

---

## Phase 5 — Review & Merge

### 5a — Dispatch Review

Launch the `code-reviewer` agent on the PR:

```
Agent(subagent_type: "pr-review-toolkit:code-reviewer", ...)
```

For critical bugs: report review findings but proceed to merge
unless findings are blocking.

### 5b — Merge

```bash
gh pr checks <N>          # Wait for CI
gh pr merge <N> --merge --delete-branch
git switch main && git pull github main
```

### 5c — Post-Merge Verification

```bash
poetry run pytest -m "not slow"   # Full suite green
```

---

## Phase 6 — Report

```
## Bug Fixed

| Issue | PR | Root Cause | Test | Status |
|-------|----|------------|------|--------|
| #N    | #M | <cause>    | <test name> | merged |

### Verification
<pytest output summary>
```

---

## Supercycle Position

```
/supercycle:bug <error or #N>     ← YOU ARE HERE
  │
  ├─ Phase 1: Intake & triage
  ├─ Phase 2: Root cause investigation (/systematic-debugging)
  ├─ Phase 3: Create GH Issue
  ├─ Phase 4: TDD fix (/test-driven-development)
  │    ├─ RED: Write failing test
  │    ├─ Fix root cause
  │    └─ GREEN: Verify (/verification-before-completion)
  ├─ Phase 5: Review & merge
  └─ Phase 6: Report

Other entry points:
  /supercycle:work      ← features, brainstorming
  /supercycle:implement ← well-defined issues
  /supercycle:review    ← review existing PRs
  /supercycle:fix       ← fix review findings
  /supercycle:merge     ← CI check + merge
```
