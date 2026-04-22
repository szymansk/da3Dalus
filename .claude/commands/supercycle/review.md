---
description: "Run parallel code review agents on one or more open PRs — dispatches code-reviewer + conditional specialized reviewers"
argument-hint: "<PR numbers, comma-separated: 200, 201>"
allowed-tools: Bash, Read, Glob, Grep, Agent
---

# /supercycle:review — Parallel PR Review

Arguments: **$ARGUMENTS**

Enter the supercycle at the **review phase**. Dispatches specialized
review agents on existing PRs. Use this when PRs are already open and
need automated review before merge.

---

## Phase 1 — Load PRs

Parse the PR numbers from arguments. For each PR:

```bash
gh pr view <N> --json number,title,url,headRefName,additions,deletions,files
```

Gather: PR number, title, branch, files changed, lines changed.

---

## Phase 2 — Classify PRs

For each PR, determine which review agents to dispatch based on the
diff content:

```bash
gh pr diff <N> --stat
```

### Mandatory (always dispatched):
- `pr-review-toolkit:code-reviewer` — general quality, conventions, correctness

### Conditional (based on PR content):

| Condition | Agent | How to detect |
|-----------|-------|---------------|
| PR adds error handling / catch blocks | `pr-review-toolkit:silent-failure-hunter` | `except`, `catch`, `try` in diff |
| PR is large (>200 lines changed) | `pr-review-toolkit:code-simplifier` | additions + deletions > 200 |
| PR adds new types / Pydantic models | `pr-review-toolkit:type-design-analyzer` | `class.*BaseModel`, `TypedDict` in diff |
| PR adds new tests | `pr-review-toolkit:pr-test-analyzer` | files in `tests/` or `__tests__/` in diff |
| PR adds docstrings / comments | `pr-review-toolkit:comment-analyzer` | `"""` or block comments in diff |

---

## Phase 3 — Dispatch Review Agents

Launch all review agents **in parallel** (single message block).

For each PR, launch at minimum the `code-reviewer`, plus any
conditional agents identified in Phase 2.

Each agent prompt MUST include:
- PR number and how to get the diff: `gh pr diff <N>`
- What to focus on (from the GH issue if available)
- Any known context (e.g. "this is a pure refactoring, no behavior changes")

---

## Phase 4 — Consolidate Findings

After all agents return, consolidate into a single report:

```
## Review Results

### PR #N — <title>

| Agent | Findings | Severity |
|-------|----------|----------|
| code-reviewer | <summary> | <highest severity> |
| silent-failure-hunter | <summary> | <highest severity> |

#### Must Fix (blocks merge)
- [Finding with file:line and remedy]

#### Should Fix (improves quality)
- [Finding with file:line and remedy]

### Verdict
- PR #N: APPROVED / CHANGES REQUESTED
- PR #M: APPROVED / CHANGES REQUESTED

### Next Steps
- /supercycle:fix <PR numbers with findings>   ← fix issues
- /supercycle:merge <PR numbers>               ← merge approved PRs
```

---

## Supercycle Position

```
/supercycle:work
  ├─ Brainstorming
  ├─ /supercycle:implement
  │
  ├─ /supercycle:review          ← YOU ARE HERE
  │    ├─ code-reviewer (always)
  │    ├─ silent-failure-hunter (conditional)
  │    ├─ code-simplifier (conditional)
  │    ├─ type-design-analyzer (conditional)
  │    ├─ pr-test-analyzer (conditional)
  │    └─ comment-analyzer (conditional)
  │
  ├─ /supercycle:fix
  └─ /supercycle:merge
```
