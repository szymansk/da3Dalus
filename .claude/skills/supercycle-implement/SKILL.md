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

<step name="cleanup-before-tests">
Use `kill-orphaned-workers` from `../supercycle-common/tracking.md`
before running any tests.
</step>

<step name="consult-adrs">
This flow has no separate planning phase, so **architectural conformance is
decided here, once, before any subagent starts** — never by the subagents
themselves.

1. Read the ADR index `_reversa_sdd/adrs/README.md`.
2. Read **in full** only the ADRs this change touches. Always consider
   **ADR 0019** (no implementation details in the public API) and **ADR 0022**
   (one authority per user-facing quantity).
3. Derive a **binding-ADR list**: per ADR, the concrete constraint on *this*
   change, not the general rule.
4. If the change would violate an ADR, **stop and raise it with the user**. An
   ADR is superseded by a new ADR, never by an implementation that quietly
   departs from it.
</step>

<step name="carry-spec-anchor">
If the plan carries a **`## Spec-Anker`** section, pass it **verbatim to every
subagent**, exactly as the binding ADRs are passed. It states, per unit, the concrete
rule that constrains this feature, with its citation and confidence marker.

Two things implementers must not do with it:

- **Do not re-derive it.** The planner resolved the anchor; an implementer who
  re-reads the spec and reaches a different conclusion has found a planning error to
  raise, not a licence to proceed on their own reading.
- **Do not treat 🟡 as 🟢.** An INFERRED rule is a best reading of the code, not a
  guarantee. If the implementation contradicts one, that is a finding worth reporting
  — it may mean the spec is wrong.

Items marked *"decided, not implemented"* describe the **target**, not the current
code. Implement against what exists unless the plan says this ticket carries the change.
</step>

<step name="invoke-implementation">
Invoke `/subagent-driven-development` with:
- Context: spec + plan from step comments passed to subagents
- **The binding-ADR list from `consult-adrs`, passed verbatim to every subagent**
  (so parallel subagents cannot interpret the same ADR differently)
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
3. Use `kill-orphaned-workers` from `../supercycle-common/tracking.md`
4. `/verification-before-completion` — evidence
</step>

<step name="post-fix-artifacts">
After fixing:
- Use `post-step-comment`: `has-fix` — fix report
</step>

</condition>
</phase>

<phase name="manual-smoke-test" order="5">
<description>Manual smoke test on the worktree before finishing.</description>

<step name="run-smoke-test">
Follow the procedure in `../supercycle-common/manual-smoke-test.md`:
1. Build a PR-specific smoke-test checklist (golden path + edge
   cases + regression risk) from the issue and PR diff.
2. Ask the user whether to start the stack.
3. If yes: pre-flight, allocate free ports, start backend + frontend
   in background, report URLs + checklist, iterate on findings,
   stop the stack when the user approves.
4. If no: skip directly to phase 6.
</step>
</phase>

<phase name="finish" order="6">
<action>Invoke `/finishing-a-development-branch`</action>
</phase>

</delegate>

---

<track>
Use `rotate-status` → `status:merged`
Report PRs created with links.
</track>
