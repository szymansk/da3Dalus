# Remove Field Length from Analysis View — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Delete the redundant `FieldLengthsPanel` and its orphan `useFieldLengths` hook from the Next.js 16 / React 19 frontend. Add a Playwright BDD regression scenario that guards against re-introduction. Backend stays untouched.

**Architecture:** Pure frontend deletion. Three file mutations (one edit, two deletions) plus two new test files (feature + step defs). Each TDD cycle is a single commit on `feat/gh-562-remove-field-length-from-analysis`.

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript, Playwright + playwright-bdd, vitest, dependency-cruiser.

**Spec:** `docs/superpowers/specs/2026-05-16-remove-field-length-from-analysis-view-design.md`
**GitHub Issue:** [#562](https://github.com/szymansk/da3Dalus/issues/562)
**Branch:** `feat/gh-562-remove-field-length-from-analysis`
**Worktree:** `/Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-562-remove-field-length-from-analysis/`

---

## Dev-server / port override (mandatory)

A Next.js dev server is **already running on `:3000`** from the user's main repo (not this worktree). Playwright's `webServer.reuseExistingServer: true` would silently reuse it — which would test the WRONG codebase.

**All dev-server and BDD commands in this plan use port 3001**, served from this worktree, with `PLAYWRIGHT_BASE_URL` set explicitly:

```bash
# Start the worktree dev server on 3001 (run in a separate terminal or in background)
cd frontend
PORT=3001 npm run dev

# Run Playwright against the worktree's :3001
cd frontend
PLAYWRIGHT_BASE_URL=http://localhost:3001 npm run test:e2e -- <feature-name>
```

The `PLAYWRIGHT_BASE_URL` env var overrides `baseURL` in `playwright.config.ts` via Playwright's standard env-override behaviour (the `baseURL: "http://localhost:3000"` line in the config is a default that env vars supersede). If the env-var override does not take effect at runtime (verify by checking the test output for the URL being hit), the fallback is to start the worktree server on `:3000` after stopping the user's existing server (`kill <PID>`).

The backend on `:8001` is shared (one FastAPI process serves all worktrees via the same DB) — leave it running.

---

## File Structure

### To create

| Path | Responsibility |
|---|---|
| `frontend/e2e/features/analysis-no-field-length.feature` | One BDD scenario asserting the "Field Lengths" header is absent from the Analysis page. |
| `frontend/e2e/steps/analysis.steps.ts` | Adds the `Then("I do not see {string} on the page", ...)` step definition. Reuses existing `Given`/`When` steps from `common.steps.ts`. |

### To modify

| Path | Change | Lines (current) |
|---|---|---|
| `frontend/app/workbench/analysis/page.tsx` | Remove `FieldLengthsPanel` import and render. | Delete line 22 (`import { FieldLengthsPanel } ...`) and line 116 (`<FieldLengthsPanel aeroplaneId={aeroplaneId} />`). |

### To delete

| Path | Reason |
|---|---|
| `frontend/components/workbench/FieldLengthsPanel.tsx` | Redundant — inputs and visualization moved to Mission Objectives (#548–#552). |
| `frontend/hooks/useFieldLengths.ts` | Orphan after `FieldLengthsPanel` is deleted (only consumer). Backend `/aeroplanes/{id}/field-lengths` endpoint is left in place — possible follow-up cleanup ticket. |

### Untouched (per spec — explicitly out of scope)

- `app/services/field_length.py`, `app/schemas/field_length.py`, `app/api/v2/field_lengths.py`, `app/tests/test_field_length_endpoint.py` — backend stays.
- `frontend/components/workbench/MissionObjectivesPanel.tsx`, `MissionRadarChart.tsx`, `AssumptionsPanel.tsx`, `MassSweepPanel.tsx`.
- `frontend/hooks/useMissionObjectives.ts` and related mission hooks.

---

## Task 1: RED — Add failing BDD scenario for absent "Field Lengths" section

**Goal:** Prove that the assertion is wired correctly by writing a Playwright BDD scenario that currently FAILS because `FieldLengthsPanel` is still mounted on the Analysis page.

**Files:**
- Create: `frontend/e2e/features/analysis-no-field-length.feature`
- Create: `frontend/e2e/steps/analysis.steps.ts`

- [ ] **Step 1.1: Write the feature file**

Create `frontend/e2e/features/analysis-no-field-length.feature`:

```gherkin
Feature: Analysis view does not expose Field Length controls

  Field Length inputs and compliance moved to the Mission Objectives view
  (#548–#552). The Analysis/Assumption view must not duplicate them.

  Scenario: FieldLengthsPanel is not rendered on the Analysis page
    Given I am on the workbench with an aeroplane
    When I click the "Analysis" step pill
    Then I do not see "Field Lengths" on the page
```

- [ ] **Step 1.2: Write the new step definition**

Create `frontend/e2e/steps/analysis.steps.ts`:

```ts
import { createBdd } from "playwright-bdd";
import { expect } from "@playwright/test";

const { Then } = createBdd();

Then(
  "I do not see {string} on the page",
  async ({ page }, text: string) => {
    // Playwright auto-waits up to default timeout for the locator condition.
    // Using exact: false so "Field Lengths" matches the panel header without
    // being thrown off by extra whitespace.
    await expect(page.getByText(text)).toHaveCount(0);
  },
);
```

The existing `Given("I am on the workbench with an aeroplane", ...)` and `When("I click the {string} step pill", ...)` come from `frontend/e2e/steps/common.steps.ts` — reused as-is.

- [ ] **Step 1.3: Confirm the backend is reachable**

The workbench-setup step posts to `${API_URL}/aeroplanes` to ensure at least one aeroplane exists. Run:

```bash
curl -sf http://localhost:8001/aeroplanes >/dev/null && echo "backend OK" || echo "backend NOT running — start it first"
```

Expected: `backend OK`. If not, start the backend before running tests:

```bash
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

- [ ] **Step 1.4: Run the BDD scenario and confirm it FAILS**

```bash
cd frontend
PLAYWRIGHT_BASE_URL=http://localhost:3001 npm run test:e2e -- analysis-no-field-length
```

Expected failure: `Then I do not see "Field Lengths" on the page` fails because `toHaveCount(0)` finds 1 occurrence (the panel header rendered inside the Analysis page).

If the scenario PASSES at this point: stop. Either the panel was already removed (re-check git status), the step definition does not run (Gherkin/step mismatch — check `npm run test:e2e -- --list`), or the workbench-setup step bailed silently. Investigate before continuing.

- [ ] **Step 1.5: Commit the RED state**

```bash
git add frontend/e2e/features/analysis-no-field-length.feature \
        frontend/e2e/steps/analysis.steps.ts
git commit -m "$(cat <<'EOF'
test(gh-562): add failing BDD scenario for FieldLengthsPanel removal

The scenario asserts no "Field Lengths" text appears on the Analysis
page. It currently fails because FieldLengthsPanel is still mounted
in app/workbench/analysis/page.tsx — fixed in the next commit.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: VERIFY — Confirm zero unexpected consumers

**Goal:** Before deleting any production source file, confirm that `useFieldLengths` and `FieldLengthsPanel` have no consumers outside the three known files. This protects against silently breaking a downstream component.

**Files:** Read-only verification, no changes.

- [ ] **Step 2.1: Grep for any reference**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-562-remove-field-length-from-analysis
grep -rn 'useFieldLengths\|FieldLengthsPanel' frontend/
```

**Expected output (exactly these lines, in some order):**

```
frontend/app/workbench/analysis/page.tsx:22:import { FieldLengthsPanel } from "@/components/workbench/FieldLengthsPanel";
frontend/app/workbench/analysis/page.tsx:116:                <FieldLengthsPanel aeroplaneId={aeroplaneId} />
frontend/components/workbench/FieldLengthsPanel.tsx:5:import { useFieldLengths, type TakeoffMode, type LandingMode } from "@/hooks/useFieldLengths";
frontend/components/workbench/FieldLengthsPanel.tsx:43:export function FieldLengthsPanel({ aeroplaneId }: Props) {
frontend/components/workbench/FieldLengthsPanel.tsx:47:  const { data, isLoading, error } = useFieldLengths(aeroplaneId, {
frontend/hooks/useFieldLengths.ts:29:interface UseFieldLengthsOptions {
frontend/hooks/useFieldLengths.ts:38:export function useFieldLengths(
frontend/hooks/useFieldLengths.ts:47:  }: UseFieldLengthsOptions = {}
```

Line numbers may shift slightly if other commits have landed in between; the file paths must match exactly.

- [ ] **Step 2.2: If anything else appears — STOP**

Any additional hit (e.g., a Mission Radar Chart import, a test file, a snapshot) means a non-obvious consumer exists. Do **not** proceed with deletion. Surface the unexpected consumer in a comment on GH Issue #562 and pause for re-scope.

If only the expected lines appear, continue to Task 3.

---

## Task 3: GREEN — Delete the panel, the hook, and the call sites

**Goal:** Make the BDD scenario from Task 1 pass by removing the panel and its hook.

**Files:**
- Modify: `frontend/app/workbench/analysis/page.tsx` (lines 22 and 116)
- Delete: `frontend/components/workbench/FieldLengthsPanel.tsx`
- Delete: `frontend/hooks/useFieldLengths.ts`

- [ ] **Step 3.1: Remove the import from the Analysis page**

Edit `frontend/app/workbench/analysis/page.tsx`. Delete line 22:

```ts
import { FieldLengthsPanel } from "@/components/workbench/FieldLengthsPanel";
```

After this edit, the imports block ends with `MassSweepPanel` (line 21 in the current file).

- [ ] **Step 3.2: Remove the render from the assumptionsSlot**

In the same file, find the `assumptionsSlot` prop on `<AnalysisViewerPanel>`. Current shape:

```tsx
assumptionsSlot={
  <>
    <AssumptionsPanel aeroplaneId={aeroplaneId} />
    <FieldLengthsPanel aeroplaneId={aeroplaneId} />
    <div className="mt-6">
      <MassSweepPanel
        data={massSweep.data}
        isComputing={massSweep.isComputing}
        error={massSweep.error}
        onCompute={massSweep.compute}
        currentMassKg={currentMassKg}
      />
    </div>
  </>
}
```

Delete the `<FieldLengthsPanel aeroplaneId={aeroplaneId} />` line. After the edit:

```tsx
assumptionsSlot={
  <>
    <AssumptionsPanel aeroplaneId={aeroplaneId} />
    <div className="mt-6">
      <MassSweepPanel
        data={massSweep.data}
        isComputing={massSweep.isComputing}
        error={massSweep.error}
        onCompute={massSweep.compute}
        currentMassKg={currentMassKg}
      />
    </div>
  </>
}
```

`AssumptionsPanel` already supplies its own bottom margin and `MassSweepPanel` is wrapped in `mt-6`, so removing `FieldLengthsPanel` does not leave a visible gap. The remaining children stack cleanly inside the fragment.

- [ ] **Step 3.3: Delete the panel component**

```bash
git rm frontend/components/workbench/FieldLengthsPanel.tsx
```

- [ ] **Step 3.4: Delete the hook**

```bash
git rm frontend/hooks/useFieldLengths.ts
```

- [ ] **Step 3.5: Confirm zero references remain in production source**

```bash
grep -rn 'useFieldLengths\|FieldLengthsPanel' frontend/
```

Expected output: empty (no hits). If any hit remains, fix it before continuing — most likely a missed import in `analysis/page.tsx`.

- [ ] **Step 3.6: Run the BDD scenario and confirm it PASSES**

```bash
cd frontend
PLAYWRIGHT_BASE_URL=http://localhost:3001 npm run test:e2e -- analysis-no-field-length
```

Expected: 1 scenario passed, 0 failed.

- [ ] **Step 3.7: Commit the GREEN state**

```bash
git add frontend/app/workbench/analysis/page.tsx
git commit -m "$(cat <<'EOF'
refactor(gh-562): remove FieldLengthsPanel and useFieldLengths hook

Field length inputs (takeoff_mode, available_runway_m, runway_type,
t_static_N) and compliance visualization now live in the Mission
Objectives view (#548–#552) and Mission Radar Chart (#550). The
Analysis/Assumption view no longer duplicates them.

- Delete frontend/components/workbench/FieldLengthsPanel.tsx
- Delete frontend/hooks/useFieldLengths.ts (only consumer was the panel)
- Remove import + render in frontend/app/workbench/analysis/page.tsx

Backend /field-lengths endpoint is untouched in this PR; a possible
follow-up will revisit it if it stays unused.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: REFACTOR — Run full check suite

**Goal:** Confirm the deletion did not break anything else in the frontend toolchain.

**Files:** No code changes; this task is a guard.

- [ ] **Step 4.1: TypeScript check**

```bash
cd frontend
npm run typecheck
```

Expected: exit code 0, no errors.

Common breakage: a lingering import of `FieldLengthsPanel` or `useFieldLengths` outside `frontend/`. Fix the import (or remove it) and re-run.

- [ ] **Step 4.2: Dependency-cruiser**

```bash
cd frontend
npm run deps:check
```

Expected: no architecture violations. If `useFieldLengths` was referenced in a dependency rule, update the rule.

- [ ] **Step 4.3: Vitest unit suite**

```bash
cd frontend
npm run test:unit
```

Expected: all tests pass. Spec verified during brainstorming that `AssumptionsPanel.test.tsx`, `MissionObjectivesPanel.test.tsx`, and `missionHooks.test.tsx` do not reference the deleted symbols. If any test now fails, it indicates the spec inventory missed a consumer — investigate and either fix or re-scope.

- [ ] **Step 4.4: Full Playwright BDD suite**

```bash
cd frontend
PLAYWRIGHT_BASE_URL=http://localhost:3001 npm run test:e2e
```

Expected: all scenarios pass, including the new `analysis-no-field-length` scenario and the pre-existing `analysis-status`, `operating-points`, `ehawk-construction`, `component-types`, `navigation`, `ted-role-ui`, and `trim-interpretation` features.

- [ ] **Step 4.5: If any checks needed fixes, commit them**

If Step 4.1–4.4 produced corrective edits, commit them in a single follow-up:

```bash
git status   # confirm only the intended fix files are staged
git add <fixed-files>
git commit -m "fix(gh-562): clean up stale references after FieldLengthsPanel removal"
```

If no fixes were needed, skip the commit and move on.

---

## Task 5: Manual browser verification

**Goal:** Confirm the visible Analysis and Mission pages look correct in a real browser. CLAUDE.md mandates: "For UI or frontend changes, start the dev server and use the feature in a browser before reporting the task as complete."

**Files:** No code changes.

- [ ] **Step 5.1: Start dev server on port 3001 (if not already running)**

```bash
cd frontend
PORT=3001 npm run dev
```

A user-owned dev server is already running on `:3000` from the main repo — DO NOT stop it. The worktree's dev server runs on `:3001`. The Playwright `webServer` config sets `reuseExistingServer: true`, so a server left over from the BDD run is fine.

- [ ] **Step 5.2: Visit the Analysis page and inspect**

Open `http://localhost:3001/workbench` (worktree dev server — NOT the user's `:3000` main-repo server), pick an aeroplane, click the Analysis step pill.

Expected:
- No "Field Lengths" header anywhere.
- No empty gap between `AssumptionsPanel` and `MassSweepPanel` (they sit directly next to each other with the existing `mt-6` on `MassSweepPanel`).
- No console errors (open DevTools → Console — must be empty for this page).

- [ ] **Step 5.3: Visit the Mission page and confirm parity**

Open `http://localhost:3001/workbench`, click the Mission step pill.

Expected:
- `MissionObjectivesPanel` "Field Performance" section still works: `Available Runway`, `Runway Type`, `Static Thrust`, `Takeoff Mode` are editable and update on debounce.
- `MissionRadarChart` still renders the compliance polygon.
- No console errors.

- [ ] **Step 5.4: Capture a screenshot for the PR description**

Take a screenshot of the Analysis page (after removal) at full resolution. Save as `analysis-after-removal.png` in the worktree root (NOT inside `frontend/` — keep it out of the bundle). It will be attached to the PR description in Task 6.

```bash
# from the worktree root:
ls analysis-after-removal.png
```

If the manual check reveals a layout issue (gap, broken styling, console error), STOP and fix it before continuing. Common fix: collapse the wrapping `<>` fragment in `assumptionsSlot` if only one child remains — not applicable here because `AssumptionsPanel` + the wrapped `MassSweepPanel` are still two children.

---

## Task 6: Push branch and open PR

**Goal:** Get the change in front of `/supercycle-review`.

**Files:** No code changes.

- [ ] **Step 6.1: Push to remote**

```bash
git push github feat/gh-562-remove-field-length-from-analysis
```

The branch is already tracking `github/feat/gh-562-...` from the spec push, so a plain `git push` works too. The explicit form above is safer in case the upstream was unset.

- [ ] **Step 6.2: Open the PR**

```bash
gh pr create --repo szymansk/da3Dalus \
  --title "feat(gh-562): remove duplicate Field Length controls from Analysis view" \
  --body "$(cat <<'EOF'
Closes #562.

## Summary

- Deletes `frontend/components/workbench/FieldLengthsPanel.tsx` (~160 LOC) and its only consumer hook `frontend/hooks/useFieldLengths.ts` (~65 LOC). Inputs and compliance now live in the Mission Objectives view + Mission Radar Chart (#548–#552, #550).
- Removes the panel's import and render from `frontend/app/workbench/analysis/page.tsx`.
- Adds a Playwright BDD regression scenario `frontend/e2e/features/analysis-no-field-length.feature` that asserts the section does not reappear.

## Out of scope

- Backend `/field-lengths` endpoint cleanup (`app/services/field_length.py`, `app/schemas/field_length.py`, `app/api/v2/field_lengths.py`, related tests) — left untouched here; possible follow-up ticket.
- Any changes to MissionObjectivesPanel, MissionRadarChart, AssumptionsPanel, MassSweepPanel.

## Test plan

- [x] `npm run test:e2e` — new scenario passes, all pre-existing scenarios pass.
- [x] `npm run test:unit` — no regressions.
- [x] `npm run typecheck` — clean.
- [x] `npm run deps:check` — clean.
- [x] Manual browser verification:
  - Analysis page renders without layout gap or console errors.
  - Mission page (`MissionObjectivesPanel` + `MissionRadarChart`) unchanged.

## Spec + plan

- Spec: `docs/superpowers/specs/2026-05-16-remove-field-length-from-analysis-view-design.md`
- Plan: `docs/superpowers/plans/2026-05-16-remove-field-length-from-analysis-view-plan.md`

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 6.3: Capture the PR URL**

The `gh pr create` command prints the PR URL on stdout. Save it for the `has-pr` step comment that the supercycle orchestrator will post on Issue #562.

---

## Self-Review

Done against the spec:

1. **Spec coverage** — every acceptance-criteria checkbox in the spec maps to a step here:
   - "`FieldLengthsPanel.tsx` deleted" → Task 3.3
   - "`useFieldLengths.ts` deleted" → Task 3.4
   - "Analysis page no longer imports or renders the panel" → Task 3.1 + 3.2
   - "grep returns zero hits" → Task 3.5
   - "`analysis-no-field-length.feature` exists and passes" → Task 1 (creates + fails) + Task 3.6 (passes after deletion)
   - "`npm run test:unit` passes" → Task 4.3
   - "`npm run test:e2e` passes" → Task 4.4
   - "`npm run deps:check` passes" → Task 4.2
   - "`npm run typecheck` passes" → Task 4.1
   - "Manual browser check" → Task 5

2. **Placeholder scan** — no `TBD`, no `TODO`, no "add appropriate error handling", no "implement later". Every code block contains actual code.

3. **Type consistency** — the step definition uses `Then("I do not see {string} on the page", ...)`. The feature file uses the same phrase. The backend types referenced by `useFieldLengths` are not surfaced here because the hook is being deleted.

4. **Out of scope is enforced** — Backend files are listed under "Untouched" up top and never appear in any task. The deletion of `useFieldLengths.ts` is bounded by the Task 2 grep guard.

The plan is ready.
