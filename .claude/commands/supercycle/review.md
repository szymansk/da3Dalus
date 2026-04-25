---
description: "Run parallel code review agents on one or more open PRs — dispatches code-reviewer + conditional specialized reviewers"
argument-hint: "<PR numbers, comma-separated: 200, 201>"
allowed-tools: Bash, Read, Glob, Grep, Agent, Skill
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

## Phase 2 — Issue Task Completeness Check

For each PR, find the linked GH Issue (from PR body `Closes #N`):

```bash
gh pr view <N> --json body --jq '.body' | grep -oP 'Closes #\K\d+'
```

Then load the issue and extract its task list:

```bash
gh issue view <ISSUE> --json body --jq '.body'
```

Parse all checkbox items (`- [ ]` and `- [x]`) from the issue body.

### For each unchecked task:

Classify it into one of three categories:

| Category | Criteria | Action |
|----------|----------|--------|
| **Done in PR** | The PR diff clearly implements this task | Check the box — update issue body |
| **Agent-fixable** | Can be fixed by the agent without human judgment (code change, test, config) | Add to the fix list for `/supercycle:fix` |
| **Human Only** | Requires human judgment, manual testing, external system access, or a decision only the user can make | Mark as `🧑 Human Only` in the issue, assign to user, add comment |

### Handling "Human Only" tasks:

If any task requires human action:

1. **Update the issue body** — prepend `🧑 Human Only` to the task text:
   ```
   - [ ] 🧑 Human Only: Verify the deployment works in staging
   ```

2. **Assign the issue to the user:**
   ```bash
   gh issue edit <ISSUE> --add-assignee <user>
   ```

3. **Add a comment explaining what's needed:**
   ```bash
   gh issue comment <ISSUE> --body "## 🧑 Human Action Required

   The following tasks from this issue require human action:

   - [ ] <task description> — **Reason:** <why the agent can't do this>

   The PR is otherwise ready. Please complete these tasks and check
   them off, then the PR can be merged via \`/supercycle:merge <N>\`."
   ```

4. **Report in the review output** that the PR is blocked on human tasks.

### Update issue checkboxes

For tasks that ARE completed in the PR, update the issue body to
check them off:

```bash
# Read current body, update checkboxes, write back
gh issue edit <ISSUE> --body "<updated body with checked boxes>"
```

---

## Phase 3 — Classify PR Content

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
| PR changes frontend imports | dependency-cruiser check | files in `frontend/` with `import` changes |

### Dependency Architecture Check (frontend PRs):

If the PR modifies any `frontend/` files, run dependency-cruiser
to check for architecture violations:

```bash
cd frontend && npm run deps:check
```

Report any new violations (circular deps, layer violations) in the
review output. These are blocking — circular dependencies and
wrong-direction imports must be fixed before merge.

---

## Phase 4 — Dispatch Review Agents

Launch all review agents **in parallel** (single message block).

For each PR, launch at minimum the `code-reviewer`, plus any
conditional agents identified in Phase 2.

Each agent prompt MUST include:
- PR number and how to get the diff: `gh pr diff <N>`
- What to focus on (from the GH issue if available)
- Any known context (e.g. "this is a pure refactoring, no behavior changes")

---

## Phase 5 — Consolidate Findings

After all agents return, consolidate into a single report:

```
## Review Results

### PR #N — <title> (Closes #ISSUE)

#### Issue Task Completeness
| # | Task | Status | Who |
|---|------|--------|-----|
| 1 | <task from issue> | ✅ Done in PR | Agent |
| 2 | <task from issue> | 🔧 Agent-fixable | → /supercycle:fix |
| 3 | <task from issue> | 🧑 Human Only | → Assigned to user |

#### Code Review Findings

| Agent | Findings | Severity |
|-------|----------|----------|
| code-reviewer | <summary> | <highest severity> |
| silent-failure-hunter | <summary> | <highest severity> |

#### Must Fix (blocks merge)
- [Finding with file:line and remedy]

#### Should Fix (improves quality)
- [Finding with file:line and remedy]

### Verdict
- PR #N: APPROVED / CHANGES REQUESTED / BLOCKED ON HUMAN
- PR #M: APPROVED / CHANGES REQUESTED / BLOCKED ON HUMAN

### Next Steps
- /supercycle:fix <PR numbers with agent-fixable findings>
- /supercycle:merge <approved PR numbers>
- 🧑 Human tasks assigned on issue #ISSUE — complete manually, then merge
```

---

## Supercycle Position

```
/supercycle:work
  ├─ Brainstorming
  ├─ /supercycle:implement
  │
  ├─ /supercycle:review          ← YOU ARE HERE
  │    ├─ Issue task completeness check
  │    │    ├─ ✅ Done in PR → check off
  │    │    ├─ 🔧 Agent-fixable → /supercycle:fix
  │    │    └─ 🧑 Human Only → assign to user + comment
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
