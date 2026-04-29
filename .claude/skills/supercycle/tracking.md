# Supercycle Tracking Reference

Shared library imported by all supercycle skills. This is NOT a
skill — it has no frontmatter and cannot be invoked directly.
Skills reference operations here by section name.

---

## Label Catalog

### Step Labels (`has-*`)

Applied once when a step artifact is produced. They accumulate —
an issue may carry several `has-*` labels at once.

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

Only ONE `status:*` label is active at a time. Each skill removes
the previous one and adds the next.

| Label | Color | Meaning |
|---|---|---|
| `status:brainstorming` | `#C2E0C6` | Active brainstorming / design |
| `status:planning` | `#BFD4F2` | Implementation plan being written |
| `status:ready` | `#0075CA` | Ticket refined, ready for implementation |
| `status:implementing` | `#6F42C1` | Code being written |
| `status:in-review` | `#E4A221` | PR under review |
| `status:fixing` | `#FBCA04` | Review findings being addressed |
| `status:merging` | `#0E8A16` | CI passing, merge in progress |
| `status:merged` | `#333333` | Issue closed, PR merged |

---

## Operations

### `ensure-labels`

Idempotent creation of all tracking labels. Safe to re-run.

```bash
gh label create "has-spec"         --description "Acceptance criteria written"      --color "0E8A16" 2>/dev/null || true
gh label create "has-plan"         --description "Implementation plan attached"      --color "1D76DB" 2>/dev/null || true
gh label create "has-pr"           --description "Pull request opened"               --color "6F42C1" 2>/dev/null || true
gh label create "has-review"       --description "Code review comment posted"        --color "E4A221" 2>/dev/null || true
gh label create "has-fix"          --description "Review findings addressed"         --color "FBCA04" 2>/dev/null || true
gh label create "has-root-cause"   --description "Root cause identified"             --color "D93F0B" 2>/dev/null || true
gh label create "has-reproduction" --description "Reproduction test added"           --color "B60205" 2>/dev/null || true

gh label create "status:brainstorming" --description "Active brainstorming"          --color "C2E0C6" 2>/dev/null || true
gh label create "status:planning"      --description "Plan in progress"              --color "BFD4F2" 2>/dev/null || true
gh label create "status:ready"         --description "Ready for implementation"      --color "0075CA" 2>/dev/null || true
gh label create "status:implementing"  --description "Code being written"            --color "6F42C1" 2>/dev/null || true
gh label create "status:in-review"     --description "PR under review"               --color "E4A221" 2>/dev/null || true
gh label create "status:fixing"        --description "Review findings being fixed"   --color "FBCA04" 2>/dev/null || true
gh label create "status:merging"       --description "CI passing, merging"           --color "0E8A16" 2>/dev/null || true
gh label create "status:merged"        --description "Issue closed, PR merged"       --color "333333" 2>/dev/null || true
```

### `load-issue`

Load a GH Issue and parse its contents.

**Inputs:** `ISSUE` — issue number

```bash
gh issue view $ISSUE --json number,title,body,labels,state,comments
```

Parse: body, labels (especially `has-*` and `status:*`), linked PRs,
checkbox items from body.

### `load-pr`

Load a PR and parse its contents.

**Inputs:** `PR` — PR number

```bash
gh pr view $PR --json number,title,url,headRefName,body,additions,deletions,files,reviews
gh pr diff $PR --stat
```

Parse: linked issues (from `Closes #N` in body), branch name,
files changed, line counts.

### `read-step-comments`

Read prior step comments from a GH Issue timeline to pick up
context from previous phases.

**Inputs:** `ISSUE`, optional `LABEL` filter (e.g. `has-spec`)

```bash
gh issue view $ISSUE --json comments --jq '.comments[].body'
```

Filter comments by looking for the `## 🏷️ <label>` header.
If `LABEL` is given, return only that step's comment body.
If no filter, return all `has-*` comments.

This is the primary cross-session context transfer mechanism.
Skills that depend on prior phases MUST call this in GATHER.

### `rotate-status`

Remove all current `status:*` labels and apply a new one.

**Inputs:** `ISSUE`, `NEW_STATUS` (e.g. `status:implementing`)

```bash
CURRENT=$(gh issue view "$ISSUE" --json labels \
  --jq '.labels[].name | select(startswith("status:"))' \
  | tr '\n' ',' | sed 's/,$//')
[ -n "$CURRENT" ] && gh issue edit "$ISSUE" --remove-label "$CURRENT"
gh issue edit "$ISSUE" --add-label "$NEW_STATUS"
```

### `post-step-comment`

Post a structured comment with substantive content, then add the
`has-*` label. Always post the comment FIRST, then the label.

**Inputs:** `ISSUE`, `LABEL`, `SKILL_NAME`, `BODY`

The comment body MUST contain the actual artifact — not a status
marker but the full content (spec text, plan, review findings, etc.):

| Label | Comment MUST contain |
|---|---|
| `has-spec` | Full design spec / acceptance criteria |
| `has-plan` | Implementation plan with task breakdown |
| `has-root-cause` | Error, root cause, introducing commit, severity, affected features, proposed fix |
| `has-reproduction` | Test name, file path, test code, failing output |
| `has-pr` | PR number/link, branch, summary of changes, files modified, quality gate results |
| `has-review` | Full review report: verdict, findings by severity, task completeness |
| `has-fix` | Fix report: findings fixed with file:line, findings skipped with rationale |

```bash
gh label create "$LABEL" --description "..." --color "..." 2>/dev/null || true

gh issue comment "$ISSUE" --body "$(cat <<'BODY'
## 🏷️ $LABEL

> Label `$LABEL` added by **supercycle/$SKILL_NAME** · $(date -u +%Y-%m-%d)

---

$BODY_CONTENT
BODY
)"

gh issue edit "$ISSUE" --add-label "$LABEL"
```

### `fetch-sonar-context`

Check if an issue or file list has SonarQube findings.

**Inputs:** `ISSUE` number or file list

If the issue body mentions SonarQube rule IDs (e.g. `S1234`) or
links to sonarcloud.io, use `/sonarqube:sonar-list-issues` to get
current line numbers and rule details, and `/sonarqube:sonar-analyze`
for deeper analysis on affected files.

If given a file list, run `/sonarqube:sonar-analyze` on each file.

Return findings as structured context for the delegated skill.

### `detect-frontend`

Check if frontend files are affected.

**Inputs:** diff output or file list

```bash
gh pr diff $PR --stat | grep -q '^frontend/' && echo "true" || echo "false"
```

Or for a file list: check if any path starts with `frontend/`.

When true, activate:
- `/vercel-react-best-practices` and `/vercel-composition-patterns`
  as additional context for implementation subagents
- Both Vercel skills as review lenses alongside
  `/pr-review-toolkit:review-pr`

---

## Comment Template

Every tracking comment follows this structure:

```markdown
## 🏷️ <label-name>

> Label `<label-name>` added by **supercycle/<skill-name>** · <ISO-8601 date>

---

<substantive content — the full artifact, not a summary>
```

---

## Tracking Points per Skill

| Skill | Reads | Writes (step labels) | Status transitions |
|---|---|---|---|
| `ticket` | — | `has-spec` | `→ status:ready` |
| `work` | prior comments | `has-spec`, `has-plan`, `has-pr`, `has-review`, `has-fix` | `→ brainstorming → planning → implementing → in-review → merged` |
| `implement` | `has-spec`, `has-plan` | `has-pr`, `has-review`, `has-fix` | `→ implementing → merged` |
| `bug` | prior comments | `has-root-cause`, `has-reproduction`, `has-pr`, `has-review`, `has-fix` | `→ implementing → merged` |
| `review` | `has-spec`, `has-plan`, `has-pr` | `has-review` | `→ in-review` |
| `fix` | `has-review` | `has-fix` | `→ fixing` |
| `merge` | `has-review`, `has-fix` | — | `→ merging → merged` |
| `status` | — (reads issues/PRs directly) | — | — |
| `init` | — | — (runs ensure-labels) | — |
