# Remove duplicate Field Length controls from Analysis view

**Status:** Design (Brainstorming complete, awaiting user review)
**Author:** Claude Opus 4.7 with user (marc.szymanski)
**Created:** 2026-05-16
**GitHub Issue:** [#562](https://github.com/szymansk/da3Dalus/issues/562)
**Depends on (already merged):** #548, #549, #550, #551, #552

## 1. Goal

Delete the `FieldLengthsPanel` from the Analysis/Assumption view. Its inputs (`takeoff_mode`, `available_runway_m`, `runway_type`, `t_static_N`) now live in the Mission Objectives form (`MissionObjectivesPanel`, added in #548–#552), and its computed compliance is visualised by the Mission Radar Chart (#550). The panel is fully redundant.

## 2. Scope

### In scope

- Delete `frontend/components/workbench/FieldLengthsPanel.tsx` (~160 LOC).
- Delete `frontend/hooks/useFieldLengths.ts` (~65 LOC).
- Remove the import (line ~19) and the JSX render (lines ~58–59) in `frontend/app/workbench/analysis/page.tsx`.
- Add a Playwright BDD regression scenario at `frontend/e2e/features/analysis-no-field-length.feature` that asserts the section is not on the Analysis page.

### Out of scope

- Backend `/field-lengths` endpoint, `app/services/field_length.py`, `app/schemas/field_length.py`, and `app/tests/test_field_length_endpoint.py` — left untouched in this PR. If they become orphan after this lands, a follow-up cleanup ticket handles them.
- Any visual/UX changes to `MissionObjectivesPanel`, `MissionRadarChart`, `AssumptionsPanel`, or `MassSweepPanel`.
- Layout rework of the Analysis page beyond removing the now-deleted slot child.

### Non-goals

- Renaming or moving any of the migrated Mission Objective fields.
- Adding any new mission/analysis features.

## 3. Background

The `FieldLengthsPanel` in the Analysis view exposes two controls — a `takeoff_mode` selector (runway / hand_launch / bungee / catapult) and a `landing_mode` selector (runway / belly_land) — and renders the read-only output of the backend `/field-lengths` compute endpoint: V_LOF, V_app, ground-roll distances, 50-ft obstacle distances.

The recent Mission Objectives work (#548–#552) introduced `MissionObjectivesPanel` with a "Field Performance" section that now owns the canonical inputs: `available_runway_m`, `runway_type` (grass / asphalt / belly), `t_static_N`, and `takeoff_mode`. The Mission Radar Chart added in #550 already visualises field-length compliance against `target_field_length_m`.

Code-base inventory (recorded during brainstorming) confirms:

- `useFieldLengths` is only consumed by `FieldLengthsPanel` (single importer).
- The frontend `DesignAssumption` schema and the backend `DesignAssumption` model have **never** contained a field-length field. The Analysis-side panel was always a UI mirror around the read-only `/field-lengths` compute endpoint.
- No existing vitest or Playwright BDD test asserts the panel's contents.

This makes the cleanup purely a frontend deletion with one regression scenario added on the way out.

## 4. Approach

Pure frontend deletion in TDD order:

1. **RED.** Add `frontend/e2e/features/analysis-no-field-length.feature` with a single scenario:
   > Given I open the Analysis page for an aeroplane
   > When the page has finished loading
   > Then I do not see a "Field Lengths" section
   Run the BDD suite. Scenario must fail (because the panel is still mounted) — this proves the assertion is wired correctly.
2. **VERIFY.** Run `grep -rn 'useFieldLengths\|FieldLengthsPanel' frontend/` and confirm exactly two source-file hits: the hook definition and the panel. Any additional consumer halts the deletion and forces a re-scope.
3. **GREEN.** Delete `FieldLengthsPanel.tsx`, delete `useFieldLengths.ts`, remove the import and JSX render in `analysis/page.tsx`. Re-run the BDD scenario — must pass.
4. **REFACTOR.** Run `npm run typecheck`, `npm run deps:check`, `npm run test:unit`, `npm run test:e2e`. Fix any stale imports or dependency-graph violations surfaced by these checks.

The PR is a single feature branch with a small, easy-to-review diff: two deletions, one small edit, one new test file.

## 5. Acceptance criteria

- [ ] `frontend/components/workbench/FieldLengthsPanel.tsx` deleted.
- [ ] `frontend/hooks/useFieldLengths.ts` deleted.
- [ ] `frontend/app/workbench/analysis/page.tsx` no longer imports or renders the panel.
- [ ] `grep -rn 'useFieldLengths\|FieldLengthsPanel' frontend/` returns zero hits.
- [ ] `frontend/e2e/features/analysis-no-field-length.feature` exists and passes.
- [ ] `npm run test:unit` passes (no regressions in `AssumptionsPanel`, `MissionObjectivesPanel`, or mission hook tests).
- [ ] `npm run test:e2e` passes (including the new feature and all pre-existing scenarios).
- [ ] `npm run deps:check` passes (no orphan dependency violations).
- [ ] `npm run typecheck` passes.
- [ ] Manual browser check: navigate Analysis → Mission → Analysis. Both views render without console errors. No empty layout gap on the Analysis page where the panel used to sit.

## 6. Risks and mitigations

| Risk | Mitigation |
|---|---|
| `useFieldLengths` has a non-obvious second consumer (e.g., picked up by the Mission Radar Chart). | Step 2 grep verification — gates deletion of the hook on zero additional hits. |
| Deleting the panel leaves a visible layout gap in the Analysis page (extra `mt-6` wrapper, fragment children, flex spacing). | Caught by the manual browser check listed in acceptance criteria. Trivial fix (remove wrapping fragment). |
| The backend `/field-lengths` endpoint is now orphan. | Explicitly out of scope. Tracked as a possible follow-up ticket. The endpoint stays callable and tested in this PR. |
| BDD scenario uses a selector that flakes on slow page hydration. | Use `expect(page.locator(...)).toHaveCount(0)` with the default Playwright auto-wait; do not poll. |

## 7. Test strategy

- **Removal-side regression test (new):** Playwright BDD scenario that asserts the "Field Lengths" heading does not exist on the Analysis page. This guards against accidental re-introduction of the panel by future work.
- **Unaffected tests stay green:** `AssumptionsPanel.test.tsx`, `MissionObjectivesPanel.test.tsx`, `missionHooks.test.tsx` — none of these reference `FieldLengthsPanel` or `useFieldLengths`, so they must continue to pass unchanged.
- **No new unit tests needed.** The deleted code had no `.test.tsx` of its own and is being removed, not refactored.
- **Backend tests untouched.** `app/tests/test_field_length_endpoint.py` continues to cover the read-only endpoint that this PR does not modify.

## 8. Rollout

Single PR, merged via the supercycle flow:

1. Worktree + branch `feat/gh-562-remove-field-length-from-analysis` created from `main`.
2. TDD implementation (RED → VERIFY → GREEN → REFACTOR).
3. Comprehensive review (`/supercycle-review`).
4. Fix findings if any (`/supercycle-fix`).
5. Merge (`/supercycle-merge`).
6. Issue #562 auto-closes via `Closes #562` in the PR body.

No feature flags, no migration, no coordination with backend. The change is reversible by reverting the merge commit.
