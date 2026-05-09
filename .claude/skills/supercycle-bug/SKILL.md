---
name: supercycle-bug
description: "Bug intake: investigate root cause, create GH ticket, TDD fix, review, and merge — all in one auto-chained flow"
argument-hint: "<error log, description, or GH issue number>"
---

# /supercycle-bug — Bug Intake & Fix

Argument: **$ARGUMENTS**

Fast-track supercycle for bugs. Auto-chains all phases with no
user gates. Takes a raw error log, bug description, or existing
GH issue number and drives it through investigation → ticket →
fix → review → merge.

---

<gather>

<step name="resolve-input">
<condition trigger="numeric (e.g. 210, #210)">
Use `load-issue` from `../supercycle-common/tracking.md`.
Use `read-step-comments` to pick up any prior context.
</condition>
<condition trigger="free-text (error log / description)">
Parse the input for:
- Error message / exception
- Stack trace — file paths, line numbers
- Endpoint / trigger
- HTTP status
</condition>
</step>

<step name="fetch-sonar-context">
Use `fetch-sonar-context` from `../supercycle-common/tracking.md`.
</step>

<step name="question-protocol">
Any question from agent to user MUST be posted to the GH Issue first
using `post-question-comment` from `../supercycle-common/tracking.md`.
Post to GH, then ask in conversation. Remove `has-question` label
after answer.
</step>

</gather>

---

<delegate auto-chain="true">

<phase name="root-cause-investigation" order="1">
<description>Find the root cause of the bug.</description>

<step name="invoke-debugging">
Invoke `/systematic-debugging` with the parsed error context.
</step>

<step name="runtime-debugging">
<condition trigger="bug is in Python backend AND code reading alone cannot determine root cause (e.g. 500 error, wrong return value, unexpected state)">
Invoke `/supercycle-python-debug` with the symptom and suspected
module/function. Use the debug JSON findings to confirm or refine
the root cause hypothesis from systematic-debugging.
</condition>
</step>

<step name="post-root-cause">
After investigation:
- Use `post-step-comment`: `has-root-cause` — error, root cause,
  introducing commit, severity, affected features, proposed fix
- Include runtime debug JSON findings when available
- Note: If input was free-text, the GH Issue may not exist yet.
  Post this comment AFTER Phase 2 (issue creation).
</step>
</phase>

<phase name="create-gh-issue" order="2">
<condition trigger="input was free-text (skip if already a GH issue)">

<step name="create-issue">
```bash
gh issue create \
  --title "bug: <concise title>" \
  --body "<structured body with root cause>" \
  --label "bug"
```
</step>

<step name="set-status">
Use `rotate-status` → `status:implementing`
</step>

</condition>
</phase>

<phase name="worktree-setup" order="3">
<action>Invoke `/using-git-worktrees`</action>
</phase>

<phase name="tdd-fix" order="4">
<description>Fix the bug using strict TDD: RED → GREEN → REFACTOR.</description>

<step name="cleanup-before-tests">
Use `kill-orphaned-workers` from `../supercycle-common/tracking.md`
before running any tests. Orphaned CadQuery workers from prior runs
consume 100% CPU and ~500 MB RAM each, causing timeouts and crashes
in subsequent test runs.
</step>

<step name="red">
Invoke `/test-driven-development` directly (no plan layer).
Write failing test reproducing the bug.
After RED:
- Use `post-step-comment`: `has-reproduction` — test name, file
  path, test code, failing output
</step>

<step name="green">
Write minimal fix for root cause.
</step>

<step name="refactor">
Clean up.
</step>

<context-management>
Run `/compact with focus on issue number, PR number, branch name,
worktree path, and root cause summary` before proceeding. Root cause
and reproduction details are persisted in GH comments.
</context-management>
</phase>

<phase name="verification" order="5">
<step name="cleanup-before-verification">
Use `kill-orphaned-workers` from `../supercycle-common/tracking.md`
before running the verification test suite.
</step>
<action>Invoke `/verification-before-completion` — evidence before claims.</action>
</phase>

<phase name="comprehensive-review" order="6">
<step name="invoke-review">
Invoke `/pr-review-toolkit:review-pr`
</step>

<step name="post-review-artifacts">
After review:
- Use `post-step-comment`: `has-review` — full review report
- Use `post-step-comment`: `has-pr` — PR number, branch, changes
</step>
</phase>

<phase name="fix-findings" order="7">
<condition trigger="review reported findings">

<step name="evaluate-and-fix">
1. `/receiving-code-review` — evaluate + verify
2. `/sonarqube:sonar-fix-issue` — SonarQube issues
</step>

<step name="post-fix-artifacts">
After fixing:
- Use `post-step-comment`: `has-fix` — fix report
</step>

</condition>
</phase>

<phase name="finish" order="8">
<action>Invoke `/finishing-a-development-branch`</action>
</phase>

</delegate>

---

<track>
Use `rotate-status` → `status:merged`
Report: issue, PR, root cause, test name.
</track>
