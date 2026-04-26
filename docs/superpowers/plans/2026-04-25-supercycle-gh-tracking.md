# Supercycle GH Issue Tracking — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add structured comments and labels to GH Issues at each supercycle step, so the issue thread becomes a complete history of the work.

**Architecture:** Each supercycle skill (`.claude/commands/supercycle/*.md`) gets a new "GH Issue Tracking" section with instructions for posting comments and setting labels. A shared reference document defines the label catalog and comment template. A validation hook warns when labels are added without corresponding comments.

**Tech Stack:** GitHub CLI (`gh`), Claude Code hooks (settings.json), Markdown skill files

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `.claude/commands/supercycle/tracking.md` | Create | Shared reference: label catalog, comment template, helper commands |
| `.claude/commands/supercycle/work.md` | Modify | Add tracking for `has-spec`, `has-plan`, status transitions |
| `.claude/commands/supercycle/implement.md` | Modify | Add tracking for `has-pr`, `status:implementing` |
| `.claude/commands/supercycle/review.md` | Modify | Add tracking for `has-review`, `status:in-review` |
| `.claude/commands/supercycle/fix.md` | Modify | Add tracking for `has-fix`, `status:fixing` |
| `.claude/commands/supercycle/merge.md` | Modify | Add tracking for `status:merging` → `status:merged` |
| `.claude/commands/supercycle/bug.md` | Modify | Add tracking for `has-root-cause`, `has-reproduction`, `has-pr` |
| `.claude/hooks/post-command/validate-issue-tracking.sh` | Create | Validation hook script |
| `.claude/settings.json` | Modify | Register validation hook |

---

### Task 1: Create Shared Tracking Reference

**Files:**
- Create: `.claude/commands/supercycle/tracking.md`

This file is NOT a user-invocable command — it's a reference document included by the other skills. It defines the label catalog, comment template, and reusable `gh` command patterns.

- [ ] **Step 1: Create the tracking reference file**

```markdown
---
description: "Shared reference for GH Issue tracking — labels, comment templates, helper commands. NOT a user command."
---

# Supercycle GH Issue Tracking Reference

This document defines the labels, comment format, and helper commands
used by all supercycle skills to track progress on GH Issues.

**Every supercycle skill MUST follow these conventions.**

---

## Label Catalog

### Step Labels (`has-*`) — accumulate, never removed

| Label | Color | Description |
|-------|-------|-------------|
| `has-spec` | `0E8A16` | Design specification posted |
| `has-plan` | `1D76DB` | Implementation plan posted |
| `has-pr` | `6F42C1` | Pull request created |
| `has-review` | `E4A221` | Code review completed |
| `has-fix` | `FBCA04` | Review fixes applied |
| `has-root-cause` | `D93F0B` | Root cause analysis posted |
| `has-reproduction` | `B60205` | Bug reproduction test posted |

### Status Labels (`status:*`) — only ONE active at a time

| Label | Color | Description |
|-------|-------|-------------|
| `status:brainstorming` | `C2E0C6` | Brainstorming phase active |
| `status:planning` | `BFD4F2` | Implementation planning |
| `status:implementing` | `6F42C1` | Code being written |
| `status:in-review` | `E4A221` | PR under review |
| `status:fixing` | `FBCA04` | Fixing review findings |
| `status:merging` | `0E8A16` | CI check and merge |
| `status:merged` | `333333` | Work merged to main |

---

## Comment Template

Every tracking comment MUST use this format:

```
## 🏷️ <label-name>

> Label `<label-name>` added by `/supercycle:<skill>`

---

<full result content>
```

The header names the label so readers can match comments to labels.

---

## Helper Commands

### Ensure a label exists (idempotent)

```bash
gh label create "<name>" --description "<desc>" --color "<hex>" 2>/dev/null || true
```

### Set a step label on an issue

Always post the comment FIRST, then add the label:

```bash
# 1. Post comment
gh issue comment <N> --body "$(cat <<'EOF'
## 🏷️ <label-name>

> Label `<label-name>` added by `/supercycle:<skill>`

---

<content>
EOF
)"

# 2. Ensure label exists
gh label create "<label-name>" --description "<desc>" --color "<hex>" 2>/dev/null || true

# 3. Add label to issue
gh issue edit <N> --add-label "<label-name>"
```

### Rotate status label

Remove all existing `status:*` labels, then add the new one:

```bash
# 1. Get current labels
CURRENT_LABELS=$(gh issue view <N> --json labels --jq '.labels[].name' | grep '^status:' || true)

# 2. Remove each existing status label
for label in $CURRENT_LABELS; do
  gh issue edit <N> --remove-label "$label"
done

# 3. Ensure new status label exists
gh label create "status:<new>" --description "<desc>" --color "<hex>" 2>/dev/null || true

# 4. Add new status label
gh issue edit <N> --add-label "status:<new>"
```

---

## Tracking Points per Skill

| Skill | Step Labels | Status Transitions |
|-------|------------|-------------------|
| `/work` | `has-spec`, `has-plan` | `status:brainstorming` → `status:planning` → `status:implementing` |
| `/implement` | `has-pr` | `status:implementing` |
| `/review` | `has-review` | `status:in-review` |
| `/fix` | `has-fix` | `status:fixing` |
| `/merge` | — | `status:merging` → `status:merged` |
| `/bug` | `has-root-cause`, `has-reproduction`, `has-pr` | `status:brainstorming` → `status:implementing` → `status:in-review` → `status:merged` |
```

- [ ] **Step 2: Verify the file was created correctly**

```bash
cat .claude/commands/supercycle/tracking.md | head -5
```

Expected: The YAML frontmatter and title.

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/supercycle/tracking.md
git commit -m "feat(gh-321): add shared tracking reference for supercycle GH issue labels"
```

---

### Task 2: Add Tracking to `/supercycle:work`

**Files:**
- Modify: `.claude/commands/supercycle/work.md`

The `/work` skill has three tracking points:
1. After brainstorming → `has-spec` + `status:brainstorming` → `status:planning`
2. After writing plans → `has-plan` + `status:planning` → `status:implementing`
3. Before hand-off → `status:implementing`

- [ ] **Step 1: Add tracking section to work.md**

Append this section **before** the existing "## Supercycle Overview" section at the end of the file (before line 145):

```markdown
---

## GH Issue Tracking

**Reference:** See `.claude/commands/supercycle/tracking.md` for the
label catalog, comment template, and helper commands.

This skill sets the following labels and comments on the GH Issue:

### At Phase 2 start (brainstorming begins):

Rotate status to `status:brainstorming`:
```bash
# Remove existing status:* labels, add status:brainstorming
# (see tracking.md for helper commands)
```

### After Phase 2c (spec/design finalized, before writing plans):

1. Post the full design spec as a comment with header `## 🏷️ has-spec`
2. Add label `has-spec`
3. Rotate status to `status:planning`

### After writing plans (before handing off to work-orchestrator):

1. Post the full implementation plan as a comment with header `## 🏷️ has-plan`
2. Add label `has-plan`
3. Rotate status to `status:implementing`

**IMPORTANT:** Always post the comment FIRST, then add the label.
Always ensure the label exists before adding it (idempotent create).
```

- [ ] **Step 2: Verify the edit**

```bash
grep -n "GH Issue Tracking" .claude/commands/supercycle/work.md
```

Expected: One match at the line where the section was inserted.

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/supercycle/work.md
git commit -m "feat(gh-321): add GH issue tracking to /supercycle:work"
```

---

### Task 3: Add Tracking to `/supercycle:implement`

**Files:**
- Modify: `.claude/commands/supercycle/implement.md`

The `/implement` skill has two tracking points:
1. At start → `status:implementing`
2. After PRs created → `has-pr`

- [ ] **Step 1: Add tracking section to implement.md**

Insert this section **before** the "## Supercycle Position" section (before line 87):

```markdown
---

## GH Issue Tracking

**Reference:** See `.claude/commands/supercycle/tracking.md` for the
label catalog, comment template, and helper commands.

### At Phase 1 start (loading issues):

For each issue, rotate status to `status:implementing`.

### After Phase 3 (PRs created):

For each issue that got a PR:

1. Post a comment with header `## 🏷️ has-pr` containing:
   - PR number and link
   - Branch name
   - Summary of changes (files modified, tests added)
   - Quality gate results
2. Add label `has-pr`

**IMPORTANT:** Always post the comment FIRST, then add the label.
Always ensure the label exists before adding it (idempotent create).
```

- [ ] **Step 2: Verify the edit**

```bash
grep -n "GH Issue Tracking" .claude/commands/supercycle/implement.md
```

Expected: One match.

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/supercycle/implement.md
git commit -m "feat(gh-321): add GH issue tracking to /supercycle:implement"
```

---

### Task 4: Add Tracking to `/supercycle:review`

**Files:**
- Modify: `.claude/commands/supercycle/review.md`

The `/review` skill has two tracking points:
1. At start → `status:in-review`
2. After review complete → `has-review`

- [ ] **Step 1: Add tracking section to review.md**

Insert this section **before** the "## Supercycle Position" section (before line 187):

```markdown
---

## GH Issue Tracking

**Reference:** See `.claude/commands/supercycle/tracking.md` for the
label catalog, comment template, and helper commands.

### At Phase 1 start (loading PRs):

For each linked issue (from `Closes #N` in PR body), rotate status
to `status:in-review`.

### After Phase 5 (review consolidated):

For each linked issue:

1. Post a comment with header `## 🏷️ has-review` containing:
   - The full consolidated review report (verdict, findings, task
     completeness)
   - Must-fix vs should-fix breakdown
   - Next steps (fix / merge / human action)
2. Add label `has-review`

**IMPORTANT:** Always post the comment FIRST, then add the label.
Always ensure the label exists before adding it (idempotent create).
```

- [ ] **Step 2: Verify the edit**

```bash
grep -n "GH Issue Tracking" .claude/commands/supercycle/review.md
```

Expected: One match.

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/supercycle/review.md
git commit -m "feat(gh-321): add GH issue tracking to /supercycle:review"
```

---

### Task 5: Add Tracking to `/supercycle:fix`

**Files:**
- Modify: `.claude/commands/supercycle/fix.md`

The `/fix` skill has two tracking points:
1. At start → `status:fixing`
2. After fixes applied → `has-fix`

- [ ] **Step 1: Add tracking section to fix.md**

Insert this section **before** the "## Supercycle Position" section (before line 97):

```markdown
---

## GH Issue Tracking

**Reference:** See `.claude/commands/supercycle/tracking.md` for the
label catalog, comment template, and helper commands.

### At Phase 1 start (identifying findings):

For each linked issue (from `Closes #N` in PR body), rotate status
to `status:fixing`.

### After Phase 3 (report):

For each linked issue:

1. Post a comment with header `## 🏷️ has-fix` containing:
   - The full fix report (findings fixed, findings skipped as
     false positives, with file:line references)
2. Add label `has-fix`

**IMPORTANT:** Always post the comment FIRST, then add the label.
Always ensure the label exists before adding it (idempotent create).
```

- [ ] **Step 2: Verify the edit**

```bash
grep -n "GH Issue Tracking" .claude/commands/supercycle/fix.md
```

Expected: One match.

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/supercycle/fix.md
git commit -m "feat(gh-321): add GH issue tracking to /supercycle:fix"
```

---

### Task 6: Add Tracking to `/supercycle:merge`

**Files:**
- Modify: `.claude/commands/supercycle/merge.md`

The `/merge` skill has two tracking points:
1. At start → `status:merging`
2. After merge complete → `status:merged`

No `has-*` step label — merge is the terminal state.

- [ ] **Step 1: Add tracking section to merge.md**

Insert this section **before** the "## Supercycle Position" section (before line 112):

```markdown
---

## GH Issue Tracking

**Reference:** See `.claude/commands/supercycle/tracking.md` for the
label catalog, comment template, and helper commands.

### At Phase 1 start (CI status check):

For each linked issue (from `Closes #N` in PR body), rotate status
to `status:merging`.

### After Phase 4 (post-merge verification):

For each linked issue:

1. Rotate status to `status:merged`

No `has-*` label is set — the merged status and the closed issue
(via `Closes #N`) are sufficient.
```

- [ ] **Step 2: Verify the edit**

```bash
grep -n "GH Issue Tracking" .claude/commands/supercycle/merge.md
```

Expected: One match.

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/supercycle/merge.md
git commit -m "feat(gh-321): add GH issue tracking to /supercycle:merge"
```

---

### Task 7: Add Tracking to `/supercycle:bug`

**Files:**
- Modify: `.claude/commands/supercycle/bug.md`

The `/bug` skill has the most tracking points:
1. At Phase 2 start → `status:brainstorming`
2. After root cause → `has-root-cause`
3. After TDD RED → `has-reproduction`
4. After PR created → `has-pr` + `status:implementing`
5. After review → `status:in-review`
6. After merge → `status:merged`

- [ ] **Step 1: Add tracking section to bug.md**

Insert this section **before** the "## Supercycle Position" section (before line 235):

```markdown
---

## GH Issue Tracking

**Reference:** See `.claude/commands/supercycle/tracking.md` for the
label catalog, comment template, and helper commands.

### At Phase 2 start (root cause investigation):

Rotate status to `status:brainstorming`.

### After Phase 2c (root cause identified, before creating ticket):

1. Post a comment with header `## 🏷️ has-root-cause` containing:
   - The full bug analysis (error, root cause, introducing commit,
     severity, affected features, proposed fix)
2. Add label `has-root-cause`

**Note:** If the bug input was free-text, the GH Issue doesn't exist
yet at this point. Post the comment AFTER Phase 3 (ticket creation),
but use the root cause content from Phase 2.

### After Phase 4b (failing test written — TDD RED):

1. Post a comment with header `## 🏷️ has-reproduction` containing:
   - The test name and file path
   - The test code
   - The failing output (proof of RED)
2. Add label `has-reproduction`
3. Rotate status to `status:implementing`

### After Phase 4f (PR created):

1. Post a comment with header `## 🏷️ has-pr` containing:
   - PR number and link
   - Root cause summary
   - Test name
   - Fix description
2. Add label `has-pr`

### After Phase 5a (review dispatched):

Rotate status to `status:in-review`.

### After Phase 5b (merged):

Rotate status to `status:merged`.

**IMPORTANT:** Always post the comment FIRST, then add the label.
Always ensure the label exists before adding it (idempotent create).
```

- [ ] **Step 2: Verify the edit**

```bash
grep -n "GH Issue Tracking" .claude/commands/supercycle/bug.md
```

Expected: One match.

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/supercycle/bug.md
git commit -m "feat(gh-321): add GH issue tracking to /supercycle:bug"
```

---

### Task 8: Create Validation Hook Script

**Files:**
- Create: `.claude/hooks/post-command/validate-issue-tracking.sh`

This hook fires after Bash tool uses that match `gh issue edit --add-label`. It checks whether a corresponding comment was posted before the label was added.

- [ ] **Step 1: Create the validation hook script**

```bash
#!/usr/bin/env bash
# validate-issue-tracking.sh
#
# PostToolUse hook for Bash commands that add has-* or status:* labels
# to GH issues. Warns if a label is added without a corresponding
# comment containing the label name in a ## 🏷️ header.
#
# Input: $CLAUDE_TOOL_INPUT contains the Bash command that was run.
# This hook only acts on `gh issue edit ... --add-label "has-*"` calls.

set -euo pipefail

INPUT="${CLAUDE_TOOL_INPUT:-}"

# Only act on gh issue edit commands that add has-* labels
if ! echo "$INPUT" | grep -q 'gh issue edit.*--add-label.*"has-'; then
  exit 0
fi

# Extract issue number and label name
ISSUE_NUM=$(echo "$INPUT" | grep -oP 'gh issue edit \K\d+' || true)
LABEL_NAME=$(echo "$INPUT" | grep -oP -- '--add-label "\K[^"]+' || true)

if [[ -z "$ISSUE_NUM" || -z "$LABEL_NAME" ]]; then
  exit 0
fi

# Check if the most recent comment on the issue contains the label header
LATEST_COMMENT=$(gh issue view "$ISSUE_NUM" --json comments --jq '.comments[-1].body // ""' 2>/dev/null || true)

if ! echo "$LATEST_COMMENT" | grep -q "🏷️ $LABEL_NAME"; then
  echo "⚠️  WARNING: Label '$LABEL_NAME' added to issue #$ISSUE_NUM but no matching comment found."
  echo "   Expected a comment with header '## 🏷️ $LABEL_NAME' before setting the label."
  echo "   Please post the tracking comment first, then add the label."
fi
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x .claude/hooks/post-command/validate-issue-tracking.sh
```

- [ ] **Step 3: Verify the script is valid**

```bash
bash -n .claude/hooks/post-command/validate-issue-tracking.sh && echo "Syntax OK"
```

Expected: `Syntax OK`

- [ ] **Step 4: Commit**

```bash
git add .claude/hooks/post-command/validate-issue-tracking.sh
git commit -m "feat(gh-321): add validation hook for GH issue tracking"
```

---

### Task 9: Register Hook in settings.json

**Files:**
- Modify: `.claude/settings.json`

Add the validation hook to the existing PostToolUse Bash matcher.

- [ ] **Step 1: Add hook to settings.json**

In `.claude/settings.json`, find the existing `PostToolUse` → `Bash` matcher entry (line 5-12). Add the validation hook to its `hooks` array:

Current:
```json
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "command": "bash -c \"./.claude/hooks/post-command/log-tool-result.sh 2>/dev/null || true\""
    }
  ]
}
```

Updated:
```json
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "command": "bash -c \"./.claude/hooks/post-command/log-tool-result.sh 2>/dev/null || true\""
    },
    {
      "type": "command",
      "command": "bash -c \"./.claude/hooks/post-command/validate-issue-tracking.sh 2>/dev/null || true\""
    }
  ]
}
```

- [ ] **Step 2: Verify the JSON is valid**

```bash
python3 -m json.tool .claude/settings.json > /dev/null && echo "JSON OK"
```

Expected: `JSON OK`

- [ ] **Step 3: Commit**

```bash
git add .claude/settings.json
git commit -m "feat(gh-321): register issue tracking validation hook in settings"
```

---

### Task 10: Verify End-to-End

- [ ] **Step 1: Test label auto-creation**

```bash
gh label create "has-spec" --description "Design specification posted" --color "0E8A16" 2>/dev/null || true
gh label list --search "has-"
```

Expected: `has-spec` label appears (may already exist from earlier manual work).

- [ ] **Step 2: Test comment + label flow on a test issue**

Create and immediately close a test issue:

```bash
# Create test issue
TEST_ISSUE=$(gh issue create --title "test: verify supercycle tracking" --body "Automated test — will be closed immediately" --label "test" | grep -oP '\d+$')
echo "Test issue: #$TEST_ISSUE"

# Post tracking comment
gh issue comment "$TEST_ISSUE" --body "## 🏷️ has-spec

> Label \`has-spec\` added by \`/supercycle:work\`

---

Test spec content."

# Add label
gh issue edit "$TEST_ISSUE" --add-label "has-spec"

# Verify
gh issue view "$TEST_ISSUE" --json labels,comments --jq '{labels: [.labels[].name], last_comment_has_label: (.comments[-1].body | test("has-spec"))}'

# Clean up
gh issue close "$TEST_ISSUE" --reason "not planned"
```

Expected output:
```json
{
  "labels": ["test", "has-spec"],
  "last_comment_has_label": true
}
```

- [ ] **Step 3: Test status rotation**

```bash
# Use the same test issue (reopen it briefly)
gh issue reopen "$TEST_ISSUE"

# Add initial status
gh label create "status:brainstorming" --description "Brainstorming phase active" --color "C2E0C6" 2>/dev/null || true
gh issue edit "$TEST_ISSUE" --add-label "status:brainstorming"

# Rotate to new status
gh label create "status:planning" --description "Implementation planning" --color "BFD4F2" 2>/dev/null || true
gh issue edit "$TEST_ISSUE" --remove-label "status:brainstorming"
gh issue edit "$TEST_ISSUE" --add-label "status:planning"

# Verify only status:planning remains
gh issue view "$TEST_ISSUE" --json labels --jq '[.labels[].name | select(startswith("status:"))]'

# Clean up
gh issue close "$TEST_ISSUE" --reason "not planned"
```

Expected: `["status:planning"]`

- [ ] **Step 4: Test validation hook**

```bash
# Simulate adding a label WITHOUT posting comment first
# The hook should warn
CLAUDE_TOOL_INPUT='gh issue edit 999 --add-label "has-spec"' bash .claude/hooks/post-command/validate-issue-tracking.sh 2>&1 || true
```

Expected: Warning message about missing comment.

- [ ] **Step 5: Final commit — close issue**

```bash
git push github main
```
