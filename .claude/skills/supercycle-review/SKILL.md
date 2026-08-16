---
name: supercycle-review
description: "Comprehensive PR review: dispatch specialized review agents, check issue task completeness, aggregate findings"
argument-hint: "<PR numbers, comma-separated: 200, 201>"
---

# /supercycle-review — Comprehensive PR Review

Argument: **$ARGUMENTS**

Dispatch specialized review agents on existing PRs. Checks issue
task completeness and aggregates findings by severity.

---

<gather>

<step name="load-prs">
For each PR number in arguments:
Use `load-pr` from `../supercycle-common/tracking.md`.
</step>

<step name="extract-linked-issues">
Parse `Closes #N` from PR body to find linked issues.
</step>

<step name="read-prior-context">
Use `read-step-comments` on linked issues with filters
`has-spec`, `has-plan`, `has-pr` to get context from prior phases.
</step>

<step name="read-prior-context">
Check if the branch exists as a local worktree. 
  <condition name="has-worktree">
    If exists use it for your review.
  </condition>
</step>

<step name="set-status">
Use `rotate-status` → `status:in-review` for each linked issue.
</step>

<step name="question-protocol">
Any question from agent to user MUST be posted to the linked GH Issue
first using `post-question-comment` from `../supercycle-common/tracking.md`.
Post to GH, then ask in conversation. Remove `has-question` label
after answer.
</step>

</gather>

---

<delegate>

<phase name="comprehensive-review" order="1">
<step name="invoke-review">
Invoke `/pr-review-toolkit:review-pr` with:
- Context: spec + plan from step comments so reviewers know
  what was intended, not just what was built
- The plan's **`## Binding ADRs`** section as an explicit review lens
- If `detect-frontend` is true: add `/vercel-react-best-practices`
  and `/vercel-composition-patterns` as review lenses
- Dispatches applicable specialized agents automatically
</step>

<step name="spec-conformance">
Check the diff against the plan's **`## Spec-Anker`** section, if present.

A departure from a cited spec rule is a **finding**, at a severity that follows the
marker:

| marker on the cited rule | severity of a departure |
|---|---|
| 🟢 CONFIRMED | **blocking** — the rule was read from the code and confirmed by the maintainer |
| 🟡 INFERRED | **report it** — the spec may be the thing that is wrong; say which you believe and why |
| 🔴 GAP | not a finding — the area is unspecified; note that the change now defines it |

**A spec statement is superseded only by a new decision recorded in `_reversa_sdd/`.**
If this change is right and the spec is wrong, the resolution is a spec update — never
an implementation that quietly departs from it.
</step>

<step name="adr-conformance">
**An ADR violation is a BLOCKING finding.** It is reported at the highest
severity and must be fixed before merge — it is never downgraded to a note.

Check the diff against:
1. Every ADR named in the plan's `## Binding ADRs` section.
2. **Always, regardless of the plan** — these catch defects that are invisible
   while writing and only surface on re-reading:
   - **ADR 0019** — implementation details in the public API: a storage or
     mechanism marker in a path (`db/`, `cache/`), an internal filesystem path
     as a field value, a static path segment colliding with a sibling path
     parameter, or a second error-envelope shape.
   - **ADR 0022** — a second producer of a quantity the user can see. Ask
     directly: *does this change write a number that another code path already
     writes?*
   - **ADR 0020** — a new fallback, clamp, retry, truncation or swallowed
     exception that does not emit a `DesignWarning`.
   - **ADR 0021** — code added complete but unreachable, or an existing
     unreachable mechanism left untouched ("inert" is forbidden).
   - **ADR 0023** — a new engineering constant, default or correlation without
     its source and without a statement that it is valid at RC/UAV scale.

If the change is genuinely right and the ADR is wrong, the resolution is a **new
ADR superseding the old one** — proposed to the user, not an undocumented
exception.
</step>
</phase>

<phase name="task-completeness-check" order="2">
<description>Inline — no skill covers this.</description>

<step name="parse-checkboxes">
For each linked issue, parse all checkbox items (`- [ ]` and
`- [x]`) from the issue body.
</step>

<step name="classify-tasks">
For each unchecked task, classify:

| Category | Criteria | Action |
|----------|----------|--------|
| **Done in PR** | PR diff clearly implements this | Check the box — update issue body |
| **Agent-fixable** | Can be fixed without human judgment | Add to fix list for `/supercycle-fix` |
| **Human Only** | Requires human judgment, manual testing, or a decision | Mark as human-only, assign to user |
</step>

<step name="post-human-actions">
For "Human Only" tasks:
```bash
gh issue comment $ISSUE --body "## Human Action Required
The following tasks require human action:
- [ ] <task> — **Reason:** <why agent can't do this>"
```
</step>

<step name="update-done-tasks">
For "Done in PR" tasks:
Update issue body with checked boxes via `gh issue edit`.
</step>
</phase>

</delegate>

---

<track>
Use `post-step-comment`: `has-review` — full review report:
verdict, findings by severity, task completeness matrix.

Report:

| Section | Content |
|---------|---------|
| Task Completeness | Table: task / status / who |
| Findings by Severity | Table: severity / count / details |
| Verdict | APPROVED / CHANGES REQUESTED / BLOCKED ON HUMAN |
| Next Steps | `/supercycle-fix` or `/supercycle-merge` commands |
</track>
