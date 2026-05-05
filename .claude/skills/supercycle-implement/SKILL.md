---
name: supercycle-implement
description: "Skip brainstorming — go straight to implementation of a GH issue with TDD, review, and merge"
argument-hint: "<GH issue number(s), comma-separated: #188, #190>"
---

# /supercycle-implement — Direct Implementation

Argument: **$ARGUMENTS**

Enter the supercycle at the implementation phase, skipping
brainstorming. Use when the issue is already well-defined with a
spec and/or plan.

---

<gather>

<step name="load-issues">
For each issue number in arguments:
Use `load-issue` from `../supercycle-common/tracking.md`.
Use `read-step-comments` with filter `has-spec`, `has-plan` to
pick up spec and plan from prior phases.
</step>

<step name="fetch-sonar-context">
Use `fetch-sonar-context` from `../supercycle-common/tracking.md`.
</step>

<step name="set-status">
Use `rotate-status` → `status:implementing` for each issue.
</step>

<step name="question-protocol">
Any question from agent to user MUST be posted to the GH Issue first
using `post-question-comment` from `../supercycle-common/tracking.md`.
Post to GH, then ask in conversation. Remove `has-question` label
after answer.
</step>

</gather>

---

<delegate>

<phase name="worktree-setup" order="1">
<action>Invoke `/using-git-worktrees` to create an isolated workspace.</action>
</phase>

<phase name="implementation" order="2">
<description>Execute using TDD subagents.</description>

<step name="invoke-implementation">
Invoke `/subagent-driven-development` with:
- Context: spec + plan from step comments passed to subagents
- Subagents invoke `/test-driven-development` internally
- Per-task review via `/requesting-code-review`
- If `detect-frontend` is true: frontend subagents follow
  `/vercel-react-best-practices` and `/vercel-composition-patterns`
</step>

<context-management>
Run `/compact with focus on issue number, PR number, branch name, and
frontend detection result` before proceeding. Implementation details
are fully externalized in commits and the PR.
</context-management>
</phase>

<phase name="comprehensive-review" order="3">
<step name="invoke-review">
Invoke `/pr-review-toolkit:review-pr` with:
- Context: spec + plan from step comments
</step>

<step name="post-review-artifacts">
After review:
- Use `post-step-comment`: `has-review` — full review report
- Use `post-step-comment`: `has-pr` — PR number, branch, changes, quality gates
</step>
</phase>

<phase name="fix-findings" order="4">
<condition trigger="review reported findings">

<step name="evaluate-and-fix">
1. `/receiving-code-review` — evaluate + verify
2. `/sonarqube:sonar-fix-issue` — SonarQube issues
3. `/verification-before-completion` — evidence
</step>

<step name="post-fix-artifacts">
After fixing:
- Use `post-step-comment`: `has-fix` — fix report
</step>

</condition>
</phase>

<phase name="finish" order="5">
<action>Invoke `/finishing-a-development-branch`</action>
</phase>

</delegate>

---

<track>
Use `rotate-status` → `status:merged`
Report PRs created with links.
</track>
