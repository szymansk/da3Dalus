---
name: supercycle-merge
description: "Check CI, analyze SonarQube quality gate, and merge PRs with post-merge verification"
argument-hint: "<PR numbers, comma-separated: 200, 201>"
---

# /supercycle-merge — CI Check & Merge

Argument: **$ARGUMENTS**

Check CI status, analyze SonarQube quality gates, and merge PRs.

---

<gather>

<step name="load-prs">
For each PR number in arguments:
Use `load-pr` from `../supercycle-common/tracking.md`.
</step>

<step name="verify-prior-steps">
Use `read-step-comments` on linked issues with filters
`has-review`, `has-fix` to verify review passed and findings
were addressed before merging.
</step>

<step name="check-ci-status">
```bash
gh pr checks $PR
```
If any test check is failing, do NOT proceed. Report the failure:
```
Tests failing on PR #N. Options:
- /supercycle-fix <N> — investigate and fix
- gh pr checks <N> — check again after fix
```
</step>

<step name="check-sonarqube-quality-gate">
Invoke `/sonarqube:sonar-quality-gate` for the project.
</step>

<step name="set-status">
Use `rotate-status` → `status:merging` for each linked issue.
</step>

</gather>

---

<delegate>

<phase name="analyze-sonarqube-gate" order="1">
<condition trigger="quality gate is failing">

<step name="evaluate-failures">
For each failed condition:
- **Security / Reliability / Maintainability:** Block merge.
  Use `/sonarqube:sonar-list-issues` for specifics.
- **Coverage on new code:** Context-dependent. Refactoring/chore
  PRs: coverage gaps on moved code are expected. Feature PRs:
  new code should have tests. Use `/sonarqube:sonar-coverage`.
- **Duplication:** Check if mechanical via
  `/sonarqube:sonar-duplication`.
</step>

</condition>
</phase>

<phase name="finish" order="2">
<step name="invoke-finishing">
Invoke `/finishing-a-development-branch`:
- Verify tests pass
- Present merge options (merge/PR/keep/discard)
- Execute chosen option
- Clean up worktree
</step>
</phase>

</delegate>

---

<track>

<step name="set-final-status">
Use `rotate-status` → `status:merged` for each linked issue.
</step>

<step name="post-merge-verification">
```bash
git switch main && git pull github main
poetry run alembic upgrade head
poetry run pytest -m "not slow"
```
</step>

<step name="report">
Report:

| PR | Issue | Title | Status |
|----|-------|-------|--------|

Test results summary included.
</step>

</track>
