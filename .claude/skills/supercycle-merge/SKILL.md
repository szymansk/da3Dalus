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

<step name="write-spec-addendum">
The extraction in `_reversa_sdd/` is now one merge out of date. Close that
interval with an **addendum** — seam ③ of the Reversa integration.

**Format authority: `_reversa_sdd/addenda/README.md`.** Read it; do not
reconstruct the format from this step.

**Decide whether one is owed.** Skip — and say so in the report — when the PR
carried no `## Spec-Anker`, or changed no production code (docs, tests, chore,
lint). `/spec-finder` reads every current addendum on every future ticket, so an
empty one is a tax on every future plan.

**Sources**, all already on the issue:

```bash
gh issue view $ISSUE --json comments \
  --jq '.comments[] | select(.body | test("has-plan|has-review")) | .body'
gh pr view $PR --json mergeCommit,files,title
```

The plan's `## Spec-Anker` names the units; the diff says which of them actually
moved. Write `_reversa_sdd/addenda/gh-<N>-<slug>.md` per the template.

**The one hard rule: an addendum points at decisions, it never holds them.** If
the change departs from a cited spec rule, the departure needs an ADR or a
`questions.md` entry to point at. If it has none, the departure was never
authorised — that is a review escape. Stop, report it, and resolve it with the
user before writing the addendum. Do not let the addendum become the only record
of a decision, because retirement then loses it.

Fill `## Decisions now implemented` from the ⚠ *decided, not implemented* entries
in the Spec-Anker that this PR made real — with `file:line`. That is the section
that pays for the rest.

**Never write the supersession line.** A new addendum is current, full stop.

Addenda are docs — commit them straight to `main`, no PR:

```bash
git add _reversa_sdd/addenda/ && \
  git commit -m "docs(gh-$ISSUE): spec addendum for #$ISSUE" && \
  git push github main
```
</step>

<step name="report">
Report:

| PR | Issue | Title | Status | Addendum |
|----|-------|-------|--------|----------|

Test results summary included. The **Addendum** column carries the path, or the
reason none was owed.
</step>

</track>
