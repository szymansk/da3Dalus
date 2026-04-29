---
name: supercycle-review
description: "Comprehensive PR review: dispatch specialized review agents, check issue task completeness, aggregate findings"
argument-hint: "<PR numbers, comma-separated: 200, 201>"
---

# /supercycle-review — Comprehensive PR Review

Argument: **$ARGUMENTS**

Dispatch specialized review agents on existing PRs. Checks issue
task completeness and aggregates findings by severity.

---

## GATHER

### 1. Load PRs

For each PR number in arguments:

Use `load-pr` from `../supercycle-common/tracking.md`.

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
| **Agent-fixable** | Can be fixed without human judgment | Add to fix list for `/supercycle-fix` |
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
- /supercycle-fix <PRs with findings>
- /supercycle-merge <approved PRs>
```
