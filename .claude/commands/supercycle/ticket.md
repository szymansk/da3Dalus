---
description: "Ticket intake: brainstorm with user, explore codebase, create refined GH Issue — read-only, no code changes"
argument-hint: "<free-form description of the idea, feature, bug, or task>"
allowed-tools: Bash, Read, Glob, Grep, Agent
---

# /supercycle:ticket — Ticket Creation & Refinement

Argument: **$ARGUMENTS**

This command is **READ-ONLY on the repository**. The only external
writes are to GitHub Issues via `gh`. It does NOT create branches,
edit files, or produce PRs.

For implementation after ticket creation, use:
- `/supercycle:work` — brainstorm + implement + merge
- `/supercycle:implement` — skip brainstorming, go straight to implementation

---

## Phase 1 — Parse Input & Ask Preferences

Receive the free-form text from `$ARGUMENTS`.

### 1a — Ask Issue Type

Present a selector — do NOT auto-detect:

> **What type of issue is this?**
> 1. **Feature** — new capability or enhancement
> 2. **Bug** — something is broken
> 3. **Task** — infra, docs, CI/CD, refactoring, tooling

Map the choice to:

| Choice | Title prefix | Label | Template |
|--------|-------------|-------|----------|
| Feature | `feat:` | `enhancement` | `.github/ISSUE_TEMPLATE/feature.md` |
| Bug | `bug:` | `bug` | `.github/ISSUE_TEMPLATE/bug.md` |
| Task | `chore:` | `task` | `.github/ISSUE_TEMPLATE/task.md` |

### 1b — Ask Brainstorming Depth

> **How deep should we go?**
> 1. **Light** — analyze codebase, draft ticket, ask your approval
> 2. **Medium** — + propose 2-3 approaches with trade-offs
> 3. **Full** — + multiple clarifying questions, iterative refinement

---

## Phase 2 — Codebase Exploration

Dispatch the `code-base-explorer` agent to analyze the user's
description against the codebase.

```
Agent(
  description: "Explore codebase for ticket context",
  subagent_type: "Explore",
  prompt: <see below>
)
```

**Agent prompt MUST include:**
- The user's full description text
- Instruction to use Serena's LSP-backed symbol tools
  (find_symbol, find_referencing_symbols, get_symbols_overview)
  alongside Glob/Grep/Read
- Request to identify:
  - Affected files, modules, and functions
  - Related existing patterns and components
  - Potential dependencies on other code
  - Related open GH Issues (via `gh issue list --search "..."`)
- Instruction to report findings in a structured format
- Thoroughness level: "very thorough"

Present the exploration results to the user as a summary:
- **Affected areas:** files and functions
- **Related patterns:** existing code that's relevant
- **Open issues:** related GH Issues if any

---

## Phase 3 — Brainstorming (depth-dependent)

### Light

1. Present codebase findings from Phase 2
2. Draft the ticket body using the chosen GH Issue template
3. Present draft to user for approval
4. Proceed to Phase 4

### Medium (adds to Light)

1. Present codebase findings
2. Propose 2-3 implementation approaches with trade-offs
3. Lead with your recommendation and explain why
4. Ask the user to pick or adjust
5. Incorporate the chosen approach into the ticket draft
6. Present draft to user for approval
7. Proceed to Phase 4

### Full (adds to Medium)

1. Present codebase findings
2. Ask clarifying questions **one at a time**:
   - Purpose and motivation
   - Constraints and non-functional requirements
   - Edge cases and error scenarios
   - Success criteria
   - Interaction with existing features
3. Propose 2-3 approaches with trade-offs after enough context
4. Ask the user to pick or adjust
5. Incorporate everything into the ticket draft
6. Present draft to user for approval — iterate if needed
7. Proceed to Phase 4

---

## Phase 4 — Draft & Approve Ticket

Present the complete ticket to the user in the exact GH Issue
template format. The body MUST follow the template structure for
the chosen type:

**Feature template sections:**
- Problem
- Proposal
- Acceptance Criteria (checkboxes)
- Dependencies
- Out of Scope

**Bug template sections:**
- Description
- Steps to Reproduce
- Expected Behavior
- Actual Behavior
- Root Cause (if identifiable from codebase exploration)

**Task template sections:**
- Motivation
- Scope
- Acceptance Criteria (checkboxes)
- Notes

### Gate

**Stop here and ask:**
> "Here's the draft ticket. Shall I create it on GitHub?"

Do NOT create the issue until the user explicitly approves.
If the user requests changes, revise and re-present.

---

## Phase 5 — Create GH Issue

### 5a — Ensure labels exist

```bash
gh label create "<type-label>" --color "..." 2>/dev/null || true
gh label create "status:brainstorming" --description "Active brainstorming" --color "C2E0C6" 2>/dev/null || true
```

### 5b — Create the issue

```bash
gh issue create \
  --title "<prefix> <concise title>" \
  --body "<approved template body>" \
  --label "<type-label>"
```

### 5c — Apply tracking

```bash
gh issue edit <N> --add-label "status:brainstorming"
```

### 5d — Report to user

> "Created issue #N: <title> — <url>"
> "Dispatching refinement agent now..."

---

## Phase 6 — Autonomous Refinement (subagent)

Dispatch a `general-purpose` agent to refine the ticket. This agent
runs autonomously — the user does NOT interact with it.

```
Agent(
  description: "Refine GH ticket #<N>",
  subagent_type: "general-purpose",
  prompt: <see below>
)
```

**Subagent prompt MUST include:**

1. The issue number, title, and full body
2. Codebase exploration results from Phase 2
3. All brainstorming context from Phase 3
4. The six refinement directives:

   > ## Refinement Directives
   >
   > You are refining GH Issue #<N>. You are READ-ONLY on the
   > repository — you may read files via Read/Glob/Grep but MUST NOT
   > use Edit or Write. Your only writes are to GitHub via `gh`.
   >
   > Refine the ticket across these six dimensions:
   >
   > 1. **Structure** — ensure every section of the template is filled
   >    with substantive content. No "TBD", no empty sections.
   > 2. **Acceptance criteria** — rewrite vague criteria into specific,
   >    testable checkboxes. Each criterion should be verifiable by
   >    running a command or checking a concrete behavior.
   > 3. **Codebase references** — add specific file paths, function
   >    names, and line numbers where changes will likely be needed.
   >    Use Glob/Grep/Read to verify these references are current.
   > 4. **Scope guard** — ensure "Out of Scope" or "Notes" section
   >    explicitly states what is NOT part of this ticket.
   > 5. **Dependencies** — search for related open issues with
   >    `gh issue list --search "..."` and link them. Check for
   >    blocking relationships.
   > 6. **Effort estimate** — add a T-shirt size (S/M/L/XL) based on
   >    number of files affected, complexity, and test surface.
   >
   > After refining:
   > 1. Update the issue body: `gh issue edit <N> --body "..."`
   > 2. Post tracking comment (see format below)
   > 3. Add label: `has-spec`
   > 4. Rotate status: remove `status:brainstorming`, add `status:ready`

5. The tracking comment format:

   > Post this comment BEFORE adding labels:
   > ```
   > ## 🏷️ has-spec
   >
   > > Label `has-spec` added by **supercycle/ticket** · <date>
   >
   > ---
   >
   > Ticket refined by autonomous agent. Changes made:
   > - <list of refinements applied>
   >
   > Effort estimate: <S/M/L/XL>
   > ```

6. The status rotation commands:

   > ```bash
   > # Ensure labels exist
   > gh label create "has-spec" --description "Acceptance criteria written" --color "0E8A16" 2>/dev/null || true
   > gh label create "status:ready" --description "Ticket refined, ready for implementation" --color "0075CA" 2>/dev/null || true
   >
   > # Post comment
   > gh issue comment <N> --body "..."
   >
   > # Add step label
   > gh issue edit <N> --add-label "has-spec"
   >
   > # Rotate status
   > CURRENT=$(gh issue view <N> --json labels --jq '.labels[].name | select(startswith("status:"))' | tr '\n' ',' | sed 's/,$//')
   > if [ -n "$CURRENT" ]; then
   >   gh issue edit <N> --remove-label "$CURRENT"
   > fi
   > gh issue edit <N> --add-label "status:ready"
   > ```

---

## Phase 7 — Report

After the subagent completes, present the final result:

```
## Ticket Created & Refined

| Issue | Type | Effort | Status |
|-------|------|--------|--------|
| #N    | <type> | <S/M/L/XL> | ready |

**URL:** <issue url>

### Refinements Applied
<summary from subagent>

### Next Steps
- `/supercycle:work #N` — brainstorm implementation + build
- `/supercycle:implement #N` — skip brainstorming, start coding
```

---

## GH Issue Tracking

**Reference:** See `tracking.md` in this directory for the label
catalog, comment template, and helper commands.

### At Phase 5 (issue created):

Apply `status:brainstorming`.

### At Phase 6 (refinement complete):

1. Post comment with header `## 🏷️ has-spec`
2. Add label `has-spec`
3. Rotate status: `status:brainstorming` → `status:ready`

**IMPORTANT:** Always post the comment FIRST, then add the label.
Always ensure the label exists before adding it (idempotent create).

---

## Supercycle Position

```
/supercycle:ticket <description>     ← YOU ARE HERE
  │
  ├─ Phase 1: Ask type + depth
  ├─ Phase 2: Codebase exploration (code-base-explorer agent)
  ├─ Phase 3: Brainstorming (light/medium/full)
  ├─ Phase 4: Draft & approve ticket
  ├─ Phase 5: Create GH Issue
  ├─ Phase 6: Autonomous refinement (subagent)
  └─ Phase 7: Report

Continues with:
  /supercycle:work #N      ← brainstorm implementation + build
  /supercycle:implement #N ← skip brainstorming, start coding
```
