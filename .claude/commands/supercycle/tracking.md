---
description: >
  Shared reference for supercycle GH Issue tracking — label catalog,
  comment templates, and reusable gh command snippets. This is NOT a
  user-invocable command; it is imported by other supercycle skills.
---

# Supercycle Tracking Reference

All supercycle skills post structured comments and apply labels to the
GH Issue at each lifecycle step. This document is the single source of
truth for label names, colors, comment format, and helper commands.

---

## Label Catalog

### Step Labels (`has-*`)

Applied once when a step artifact is produced. They accumulate — an issue
may carry several `has-*` labels at once.

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

Only ONE `status:*` label is active at a time. Each skill removes the
previous one and adds the next.

| Label | Color | Meaning |
|---|---|---|
| `status:brainstorming` | `#C2E0C6` | In active brainstorming / design discussion |
| `status:planning` | `#BFD4F2` | Implementation plan being written |
| `status:implementing` | `#6F42C1` | Code being written in worktrees |
| `status:in-review` | `#E4A221` | PR under automated + human review |
| `status:fixing` | `#FBCA04` | Review findings being addressed |
| `status:merging` | `#0E8A16` | CI passing, merge in progress |
| `status:merged` | `#333333` | Issue closed, PR merged |
| `status:ready` | `#0075CA` | Ticket refined, ready for implementation |

---

## Comment Template

Every tracking comment follows this structure so they are easy to scan in
the GH Issue timeline:

```
## 🏷️ <label-name>

> Label `<label-name>` added by **supercycle/<skill-name>** · <ISO-8601 date>

---

<human-readable summary of what happened at this step, 2-5 sentences>

<optional: bullet list of artifacts, links, or decisions>
```

### Examples

```markdown
## 🏷️ has-plan

> Label `has-plan` added by **supercycle/work** · 2026-04-25

---

Implementation plan finalised. Three tasks identified; no file overlaps
detected, so parallel worktree agents will be dispatched.

- Task 1: add `tracking.md` shared reference
- Task 2: instrument `work.md` with tracking calls
- Task 3: instrument remaining skills
```

```markdown
## 🏷️ status:in-review

> Label `status:in-review` added by **supercycle/review** · 2026-04-25

---

PR #322 opened and dispatched to automated review agents.
Checklist completeness: 3/3 tasks confirmed in diff.
```

---

## Helper Commands

### Idempotent label creation

Run once per repo to ensure all labels exist. Safe to re-run.

```bash
gh label create "has-spec"         --description "Acceptance criteria written"      --color "0E8A16" 2>/dev/null || true
gh label create "has-plan"         --description "Implementation plan attached"      --color "1D76DB" 2>/dev/null || true
gh label create "has-pr"           --description "Pull request opened"               --color "6F42C1" 2>/dev/null || true
gh label create "has-review"       --description "Code review comment posted"        --color "E4A221" 2>/dev/null || true
gh label create "has-fix"          --description "Review findings addressed"         --color "FBCA04" 2>/dev/null || true
gh label create "has-root-cause"   --description "Root cause identified"             --color "D93F0B" 2>/dev/null || true
gh label create "has-reproduction" --description "Reproduction test added"           --color "B60205" 2>/dev/null || true

gh label create "status:brainstorming" --description "Active brainstorming"          --color "C2E0C6" 2>/dev/null || true
gh label create "status:planning"      --description "Implementation plan in progress" --color "BFD4F2" 2>/dev/null || true
gh label create "status:implementing"  --description "Code being written"            --color "6F42C1" 2>/dev/null || true
gh label create "status:in-review"     --description "PR under review"               --color "E4A221" 2>/dev/null || true
gh label create "status:fixing"        --description "Review findings being fixed"   --color "FBCA04" 2>/dev/null || true
gh label create "status:merging"       --description "CI passing, merging"           --color "0E8A16" 2>/dev/null || true
gh label create "status:merged"        --description "Issue closed, PR merged"       --color "333333" 2>/dev/null || true
gh label create "status:ready"         --description "Ticket refined, ready for implementation" --color "0075CA" 2>/dev/null || true
```

### Post comment then add label

**Always post the comment first, then apply the label.** This preserves
chronological order in the GH Issue timeline.

```bash
# 1. Post the comment
gh issue comment <issue-number> --body "$(cat <<'BODY'
## 🏷️ <label-name>

> Label `<label-name>` added by **supercycle/<skill>** · $(date -u +%Y-%m-%d)

---

<summary>
BODY
)"

# 2. Add the step label
gh issue edit <issue-number> --add-label "<label-name>"
```

### Status rotation

Remove all current `status:*` labels, then apply the new one.

```bash
ISSUE=<issue-number>
NEW_STATUS="status:implementing"   # change as appropriate

# Collect existing status labels
CURRENT=$(gh issue view "$ISSUE" --json labels \
  --jq '.labels[].name | select(startswith("status:"))' \
  | tr '\n' ',' | sed 's/,$//')

# Remove old status labels (if any)
if [ -n "$CURRENT" ]; then
  gh issue edit "$ISSUE" --remove-label "$CURRENT"
fi

# Apply new status label
gh issue edit "$ISSUE" --add-label "$NEW_STATUS"
```

---

## Tracking Points per Skill

| Skill | Step label(s) applied | Status transition |
|---|---|---|
| `work.md` — brainstorm phase | — | `→ status:brainstorming` |
| `work.md` — spec written | `has-spec` | `→ status:planning` |
| `work.md` — plan written | `has-plan` | `→ status:implementing` |
| `implement.md` — PRs created | `has-pr` | `→ status:implementing` |
| `review.md` — review complete | `has-review` | `→ status:in-review` |
| `fix.md` — fixes applied | `has-fix` | `→ status:fixing` |
| `merge.md` — merge started | — | `→ status:merging` |
| `merge.md` — merge complete | — | `→ status:merged` |
| `ticket.md` — issue created | — | `→ status:brainstorming` |
| `ticket.md` — refinement complete | `has-spec` | `→ status:ready` |
| `bug.md` — root cause found | `has-root-cause` | — |
| `bug.md` — reproduction added | `has-reproduction` | `→ status:implementing` |
| `bug.md` — PR created | `has-pr` | — |
| `bug.md` — review done | — | `→ status:in-review` |
| `bug.md` — merged | — | `→ status:merged` |
