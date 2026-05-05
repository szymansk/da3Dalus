---
name: supercycle-fix
description: "Fix review findings on PR branches — evaluate with technical rigor, fix SonarQube issues, verify"
argument-hint: "<PR numbers, comma-separated: 200, 201>"
---

# /supercycle-fix — Fix Review Findings

Argument: **$ARGUMENTS**

Apply review findings and SonarQube fixes to PR branches.
Evaluates each finding with technical rigor — verifies before
implementing, pushes back on false positives.

---

<gather>

<step name="load-pr-review-comments">
For each PR number in arguments:
```bash
gh api repos/{owner}/{repo}/pulls/$PR/comments \
  --jq '.[] | {path: .path, line: .line, body: .body}'
gh pr view $PR --json reviews \
  --jq '.reviews[] | {state: .state, body: .body}'
```
</step>

<step name="read-prior-review">
Use `read-step-comments` on linked issues with filter `has-review`
to get the full review report with findings, severity, and
file:line references. This is the primary input.
</step>

<step name="fetch-sonarqube-issues">
Use `/sonarqube:sonar-list-issues` to get current SonarQube issues
on the PR branch.
</step>

<step name="set-status">
Use `rotate-status` → `status:fixing` for each linked issue.
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

<phase name="evaluate-review-findings" order="1">
<step name="invoke-receiving-code-review">
Invoke `/receiving-code-review` with:
- Context: the `has-review` comment content as review findings
- For each finding: verify against codebase reality before implementing
- Push back on false positives with technical reasoning
- No performative agreement — technical rigor always
</step>
</phase>

<phase name="fix-sonarqube-issues" order="2">
<step name="fix-issues">
Invoke `/sonarqube:sonar-fix-issue` for each SonarQube issue on
the PR branch.
</step>
</phase>

<phase name="verify" order="3">
<step name="invoke-verification">
Invoke `/verification-before-completion`:
- Evidence that fixes work
- No regressions
- Quality gates pass
</step>
</phase>

</delegate>

---

<track>
Use `post-step-comment`: `has-fix` — fix report:
- Findings fixed with file:line references
- Findings skipped as false positives with rationale
- SonarQube issues resolved

Report:

| PR | Findings | Fixed | Skipped (false positive) |
|----|----------|-------|--------------------------|

Next steps: `/supercycle-merge <PR numbers>`
</track>
