---
description: "Skip brainstorming — go straight to parallel implementation of one or more GH issues via worktree agents"
argument-hint: "<GH issue numbers, comma-separated: #188, #190>"
allowed-tools: Bash, Read, Glob, Grep, Agent, WebSearch, Skill
---

# /supercycle:implement — Direct Implementation

Arguments: **$ARGUMENTS**

Enter the supercycle at the **implementation phase**, skipping
brainstorming. Use this when the issue is already well-defined and
approved, and you just need the agents to build it.

---

## Phase 1 — Load Issues

For each issue number in the arguments:

```bash
gh issue view <N> --json number,title,body,labels
```

If any issue references an external system (SonarQube, Sentry, etc.),
fetch current data NOW. For SonarQube issues, use
`/sonarqube:sonar-list-issues` to get current line numbers and
`/sonarqube:sonar-analyze` for deeper analysis of affected files.

---

## Phase 2 — Parallelization Analysis

If multiple issues are provided:

```
Per issue: list affected files (from issue body + quick grep)
     ↓
Build file-overlap matrix
     ↓
Form conflict-free batches (max parallelism, min merge risk)
     ↓
Order batches by dependency + severity
```

If a single issue: proceed directly to implementation.

---

## Phase 3 — Dispatch Worktree Agents

For each issue in the current batch, launch a worktree agent in
parallel (all in a single message block):

Each agent MUST:
1. Read the GH Issue (`gh issue view <N>`)
2. If issue references external system → fetch current data from there
3. Create branch: `git switch -c <type>/gh-<N>-<slug>`
4. Implement the fix/feature
5. Run quality gates:
   - Backend: `poetry run ruff check . && poetry run pytest -m "not slow"`
   - Frontend (if changed): `cd frontend && npm run lint && npm run test:unit && npm run deps:check`
   - The `deps:check` catches circular dependencies and layer violations
6. Push and create PR: `gh pr create --base main` with `Closes #N`
7. Do NOT merge — leave PR open for review

---

## Phase 4 — Report

After all agents complete, report:

```
## Implementation Complete

| Issue | PR | Tests | Status |
|-------|----|-------|--------|
| #N    | #M | pass  | PR open |

Next steps:
- /supercycle:review #M1, #M2   ← review the PRs
- /supercycle:merge #M1, #M2    ← skip review, go to merge
```

---

## Supercycle Position

```
/supercycle:work
  ├─ Brainstorming
  ├─ Ticket refinement
  │
  ├─ /supercycle:implement       ← YOU ARE HERE
  │    ├─ Parallelization
  │    └─ Worktree agents
  │
  ├─ /supercycle:review
  ├─ /supercycle:fix
  └─ /supercycle:merge
```
