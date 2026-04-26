# Supercycle GH Issue Tracking — Design Spec

**Date:** 2026-04-25

## Context

The supercycle commands (`/work`, `/implement`, `/review`, `/fix`,
`/merge`, `/bug`) orchestrate the full development lifecycle but don't
leave a structured trail on GitHub Issues. Results from each step
(specs, plans, reviews, fixes) are ephemeral — visible only in the
Claude Code conversation, not on the issue where stakeholders track
progress.

This feature adds **structured comments** and **labels** to GH Issues
at each supercycle step, so that:
- The issue's comment thread becomes a complete history of the work
- Labels show at a glance which steps have been completed and what
  the current status is
- Each comment identifies which label it triggered

## Design

### Label System

Two label categories coexist on each issue:

**Step labels (`has-*`)** — accumulate over time, never removed:

| Label | Color | Set by | Comment contains |
|-------|-------|--------|-----------------|
| `has-spec` | `#0E8A16` (green) | `/work` after brainstorming | Full design spec |
| `has-plan` | `#1D76DB` (blue) | `/work` after writing-plans | Full implementation plan |
| `has-pr` | `#6F42C1` (purple) | `/implement` | PR link + change summary |
| `has-review` | `#E4A221` (orange) | `/review` | Full review verdict + findings |
| `has-fix` | `#FBCA04` (yellow) | `/fix` | Fix summary (fixed vs skipped) |
| `has-root-cause` | `#D93F0B` (red) | `/bug` after investigation | Root cause analysis |
| `has-reproduction` | `#B60205` (dark red) | `/bug` after TDD RED | Failing test that reproduces bug |

**Status labels (`status:*`)** — only one active at a time, rotated:

| Label | Color | Set when |
|-------|-------|----------|
| `status:brainstorming` | `#C2E0C6` | `/work` starts brainstorming |
| `status:planning` | `#BFD4F2` | After spec, before implementation |
| `status:implementing` | `#6F42C1` | `/implement` starts |
| `status:in-review` | `#E4A221` | `/review` starts |
| `status:fixing` | `#FBCA04` | `/fix` starts |
| `status:merging` | `#0E8A16` | `/merge` starts |
| `status:merged` | `#333333` | `/merge` completes |

### Comment Format

Every tracking comment follows this template:

```markdown
## 🏷️ has-spec

> Label `has-spec` added by `/supercycle:work`

---

[Full result content here — spec, plan, review, etc.]
```

The header names the label so that scrolling through comments
immediately reveals which comment triggered which label.

### Label Auto-Creation

Before setting a label, the skill checks if it exists. If not, it
creates it with `gh label create "<name>" --description "..." --color
"<hex>"`. This is idempotent — safe to run repeatedly.

### Status Label Rotation

When setting a new `status:*` label:
1. List current labels on the issue
2. Remove any existing `status:*` label
3. Add the new `status:*` label

### Ordering: Comment Before Label

Always post the comment first, then set the label. This ensures the
comment is present when the label appears — no label without its
corresponding documentation.

### Affected Skills

Each skill gets a new "GH Issue Tracking" section in its markdown
that specifies which labels and comments to produce at each phase:

| Skill | Step labels | Status transitions |
|-------|------------|-------------------|
| `/supercycle:work` | `has-spec`, `has-plan` | `status:brainstorming` → `status:planning` → `status:implementing` |
| `/supercycle:implement` | `has-pr` | `status:implementing` |
| `/supercycle:review` | `has-review` | `status:in-review` |
| `/supercycle:fix` | `has-fix` | `status:fixing` |
| `/supercycle:merge` | — | `status:merging` → `status:merged` |
| `/supercycle:bug` | `has-root-cause`, `has-reproduction`, `has-pr` | `status:brainstorming` → `status:implementing` → `status:in-review` → `status:merged` |

### Validation Hook

A PostToolUse hook in `settings.json` acts as a safety net. After
any `gh issue edit --add-label "has-*"` command, the hook verifies
that a corresponding comment was posted on the issue. If the comment
is missing, it outputs a warning to the conversation.

**Hook scope:** Only fires on `gh issue edit` commands that add
`has-*` or `status:*` labels. Does not interfere with other `gh`
usage.

## Flows

### Feature Flow (`/supercycle:work` → `/merge`)

```
/work starts
  ├─ status:brainstorming set
  ├─ Brainstorming with user
  ├─ has-spec comment + label
  ├─ status:planning set
  ├─ Writing plans
  ├─ has-plan comment + label
  └─ Hand off to work-orchestrator

/implement starts
  ├─ status:implementing set
  ├─ Worktree agents
  ├─ PRs created
  └─ has-pr comment + label

/review starts
  ├─ status:in-review set
  ├─ Review agents
  └─ has-review comment + label

/fix starts (if needed)
  ├─ status:fixing set
  ├─ Fixes applied
  └─ has-fix comment + label

/merge starts
  ├─ status:merging set
  ├─ CI check + merge
  └─ status:merged set
```

### Bug Flow (`/supercycle:bug`)

```
/bug starts
  ├─ status:brainstorming set
  ├─ Root cause investigation
  ├─ has-root-cause comment + label
  ├─ GH Issue created (if not existing)
  ├─ status:implementing set
  ├─ TDD RED: failing test
  ├─ has-reproduction comment + label
  ├─ Fix + GREEN
  ├─ has-pr comment + label
  ├─ status:in-review set
  ├─ Code review
  ├─ has-review comment + label
  ├─ status:merging set
  └─ status:merged set
```

## Out of Scope

- Removing `has-*` labels (they accumulate permanently)
- Custom label colors per project (fixed palette)
- Retroactive labeling of existing issues
- Dashboard or reporting on label distribution
