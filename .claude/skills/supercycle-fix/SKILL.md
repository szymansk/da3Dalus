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

## GATHER

### 1. Load PR Review Comments

For each PR number in arguments:

```bash
gh api repos/{owner}/{repo}/pulls/$PR/comments \
  --jq '.[] | {path: .path, line: .line, body: .body}'
gh pr view $PR --json reviews \
  --jq '.reviews[] | {state: .state, body: .body}'
```

### 2. Read Prior Review

Use `read-step-comments` on linked issues with filter `has-review`
to get the full review report with findings, severity, and
file:line references. This is the primary input.

### 3. Fetch SonarQube Issues

Use `/sonarqube:sonar-list-issues` to get current SonarQube issues
on the PR branch.

### 4. Set Status

Use `rotate-status` → `status:fixing` for each linked issue.

---

## DELEGATE

### 1. Evaluate Review Findings

Invoke `/receiving-code-review` with:
- Context: the `has-review` comment content as review findings
- For each finding: verify against codebase reality before
  implementing
- Push back on false positives with technical reasoning
- No performative agreement — technical rigor always

### 2. Fix SonarQube Issues

Invoke `/sonarqube:sonar-fix-issue` for each SonarQube issue on
the PR branch.

### 3. Verify

Invoke `/verification-before-completion`:
- Evidence that fixes work
- No regressions
- Quality gates pass

---

## TRACK

Use `post-step-comment`: `has-fix` — fix report:
- Findings fixed with file:line references
- Findings skipped as false positives with rationale
- SonarQube issues resolved

Report:
```
## Fix Results

| PR | Findings | Fixed | Skipped (false positive) |
|----|----------|-------|-------------------------|

### Next Steps
- /supercycle-merge <PR numbers>
```
