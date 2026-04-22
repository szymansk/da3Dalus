---
description: "Brainstorm a GH issue or feature idea with the user, refine the ticket, then hand off to the work-orchestrator agent for parallel implementation"
argument-hint: "<GH issue number> OR <feature description in natural language>"
allowed-tools: Bash, Read, Glob, Grep, Agent, WebSearch
---

# /work — Issue Brainstorming & Orchestrated Implementation

Argument: **$ARGUMENTS**

---

## Phase 1 — Resolve Input

Determine whether the argument is a GitHub Issue number or a free-text
feature description.

### If numeric (e.g. `187`, `#187`):

```bash
gh issue view <number> --json number,title,body,labels,state
```

Read the full issue. If the issue references an external system
(SonarQube rule IDs, Sentry links, etc.), fetch current data from
that system NOW — issue descriptions go stale.

**SonarQube example:**
- If the issue body mentions `S1234` or links to sonarcloud.io →
  use `sonarqube:list-issues` to get current line numbers and rule details
- Use `sonarqube:show-rule` for the official fix recommendation

### If free-text (feature description):

No existing ticket yet — proceed to brainstorming with the user's
description as the starting point. A GH Issue will be created in
Phase 2.

---

## Phase 2 — Brainstorming with User

**This phase is interactive. Do NOT skip it. Do NOT proceed without
explicit user approval.**

Present the issue/feature to the user for joint review:

### 2a — Context Summary

Show the user:
- **What:** Issue title + description (or the feature idea)
- **Why:** Motivation, linked systems, severity
- **Where:** Affected files/modules (quick grep if needed)
- **How big:** Rough scope estimate (S/M/L)
- **External data:** If applicable, show current SonarQube findings,
  Sentry traces, etc. — the live data, not just the issue text

### 2b — Joint Discussion

Ask the user:
1. Is the scope correct? Should anything be added or removed?
2. Are there design decisions to make? (e.g. "rename vs. noqa?")
3. Priority — should this be done now or deferred?
4. Any constraints or preferences for the implementation?

### 2c — Refine or Create Ticket

**If existing GH Issue:** Update the issue body/title if the
brainstorming changed the scope:
```bash
gh issue edit <number> --title "..." --body "..."
```

**If new feature:** Create a GH Issue using the appropriate template:
```bash
gh issue create --title "..." --body "..." --label "..."
```

### 2d — Gate

**Stop here and confirm with the user:**
> "Issue #N is ready. Shall I start the implementation?"

Do NOT proceed until the user explicitly confirms.

---

## Phase 3 — Hand Off to Work Orchestrator

Once the user confirms, dispatch the `work-orchestrator` agent.

Pass the agent ALL context gathered in Phases 1–2:

```
Agent(
  subagent_type: "work-orchestrator",
  prompt: <see below>
)
```

The agent prompt MUST include:
1. The GH Issue number and full issue body
2. Any external system data (SonarQube findings, Sentry traces, etc.)
3. Design decisions made during brainstorming
4. User preferences/constraints expressed during discussion
5. Affected files discovered during exploration
6. The branch naming convention: `<type>/gh-<N>-<short-slug>`

**Example prompt structure:**
```
## Task: Implement GH Issue #<N>

### Issue
<full issue body>

### Brainstorming Decisions
- <decision 1>
- <decision 2>

### External Data
<SonarQube findings / Sentry traces / etc.>

### Affected Files
- <file1> (reason)
- <file2> (reason)

### User Constraints
- <constraint 1>

### Branch
<type>/gh-<N>-<slug>
```

---

## Summary

This command implements the first two phases of the da3Dalus agentic
development workflow:

```
/work #187
  │
  ├─ Phase 1: Read GH Issue + fetch external data
  ├─ Phase 2: /brainstorming with user → refine/create ticket
  └─ Phase 3: Hand off to work-orchestrator agent
                │
                ├─ Parallelization analysis
                ├─ Planning
                ├─ Worktree agents (parallel implementation)
                ├─ Code review agents
                ├─ Fix findings
                ├─ CI monitoring
                └─ Merge + verify
```
