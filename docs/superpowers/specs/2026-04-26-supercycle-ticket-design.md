# Supercycle Ticket Command Design

**Date:** 2026-04-26
**Status:** Approved
**Scope:** New `/supercycle:ticket` slash command

## Problem

The supercycle has entry points for implementation (`work`, `implement`),
bugs (`bug`), review (`review`), fixes (`fix`), and merging (`merge`).
But there is no dedicated command for the earliest phase: turning a
rough idea into a well-structured, codebase-aware GitHub Issue without
touching any code.

Currently, ticket creation is either manual or bundled into
`/supercycle:work` Phase 2, which immediately continues to
implementation. There is no way to produce a refined ticket and stop.

## Proposal

A new `/supercycle:ticket` command that:

1. Takes free-form descriptive text from the user
2. Asks the user to pick the issue type (Feature / Bug / Task)
3. Asks the user for brainstorming depth (Light / Medium / Full)
4. Explores the codebase via the `code-base-explorer` agent
5. Brainstorms with the user at the chosen depth
6. Creates a GitHub Issue after user approval
7. Dispatches an autonomous subagent to refine the ticket
8. Applies tracking labels throughout

The command is **read-only on the repository**. The only external
writes are to GitHub Issues via `gh`.

## Flow

### Phase 1 — Parse Input & Ask Preferences

- Receive `$ARGUMENTS` (free-form text)
- Ask user to pick issue type:
  - **Feature** (`enhancement` label, `feature.md` template)
  - **Bug** (`bug` label, `bug.md` template)
  - **Task** (`task` label, `task.md` template)
- Ask user for brainstorming depth:
  - **Light** — analyze, draft, approve
  - **Medium** — + propose 2-3 approaches with trade-offs
  - **Full** — + multiple clarifying questions, iterative refinement

### Phase 2 — Codebase Exploration

Dispatch the `code-base-explorer` agent (`.claude/agents/code-base-explorer.md`)
with the user's description. The agent identifies:

- Affected files and functions
- Related existing patterns
- Potential dependencies on other code
- Related open GH Issues

Results are summarized for the user.

### Phase 3 — Brainstorming (depth-dependent)

**Light:**
- Present codebase findings
- Draft ticket in template format
- Ask for approval

**Medium (adds):**
- Propose 2-3 implementation approaches with trade-offs
- Recommend one, explain why
- Incorporate chosen approach into the ticket

**Full (adds):**
- Ask clarifying questions one at a time
- Explore constraints, success criteria, edge cases
- Iterate until the user is satisfied

### Phase 4 — Draft & Approve Ticket

- Present the complete ticket body in the GH Issue template format
- User reviews and can request changes
- **Gate:** No GitHub write until user explicitly approves

### Phase 5 — Create GH Issue

```bash
gh issue create --title "<type>: <title>" --body "<template body>" --label "<type-label>"
```

- Apply the type label (`enhancement`, `bug`, or `task`)
- Apply `status:brainstorming`
- Report the issue number and URL to the user

### Phase 6 — Autonomous Refinement (subagent)

Dispatch a `general-purpose` agent with:

- The created issue number and full body
- Codebase exploration results from Phase 2
- All brainstorming context from Phase 3

The subagent refines the ticket across six dimensions:

1. **Structure** — ensure all template sections are filled, no placeholders
2. **Acceptance criteria** — sharpen vague criteria into specific, testable checkboxes
3. **Codebase references** — add file paths, function names, line numbers
4. **Scope guard** — add/refine "Out of Scope" section
5. **Dependencies** — identify and link related GH Issues
6. **Effort estimate** — add T-shirt size (S/M/L/XL) based on codebase analysis

The subagent:
- Updates the issue body via `gh issue edit`
- Posts a `## has-spec` tracking comment
- Adds the `has-spec` label
- Rotates status from `status:brainstorming` to `status:ready`

The subagent is **read-only on the repository** — it may read files
and run grep/glob, but must not edit, write, or create any files.

### Phase 7 — Report

Show the user:
- Final ticket URL
- Summary of refinements made by the subagent

## New Tracking Label

| Label | Color | Meaning |
|---|---|---|
| `status:ready` | `#0075CA` | Ticket refined, ready for `/supercycle:work` or `:implement` |

Added to `tracking.md` label catalog.

## Safety Constraints

- `allowed-tools` in the command frontmatter: `Bash, Read, Glob, Grep, Agent`
- Excludes `Edit`, `Write`, `Skill` — no file modifications
- Subagent prompt explicitly repeats the read-only constraint
- The only external writes are `gh issue create`, `gh issue edit`,
  `gh issue comment`, `gh label create`

## Acceptance Criteria

- [ ] Command file exists at `.claude/commands/supercycle/ticket.md`
- [ ] Command asks user for issue type (Feature/Bug/Task)
- [ ] Command asks user for brainstorming depth (Light/Medium/Full)
- [ ] Codebase exploration uses `code-base-explorer` agent
- [ ] GH Issue is created only after explicit user approval
- [ ] Subagent autonomously refines the ticket (all 6 dimensions)
- [ ] Tracking labels applied: type label, `status:brainstorming`, `has-spec`, `status:ready`
- [ ] `tracking.md` updated with `status:ready` label
- [ ] No `Edit` or `Write` in allowed-tools
- [ ] CLAUDE.md updated with the new command in the supercycle table

## Out of Scope

- Code changes, branches, or PRs
- Implementation planning (that's `/supercycle:work`)
- Modifying existing GH Issues (this command creates new ones only)
