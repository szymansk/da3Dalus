# Template Execution — Design Spec

**Date:** 2026-04-26
**Status:** Approved (brainstorming complete)
**Related:** Construction Plans (gh#101), Templates (gh#126), Artifact Browser (gh#320)

## Problem

Construction Templates currently cannot be executed. The execute endpoint
in `construction_plan_service.py` raises a `ValidationError` with the
message *"Templates cannot be executed. Instantiate as a plan first."*
This guard exists in both `execute_plan()` (lines 603–606) and
`execute_plan_streaming()` (lines 716–718).

Consequence: templates cannot be tested without first instantiating
them as a concrete plan against an aeroplane — adding friction and
polluting the production artifact tree with throwaway test runs.

The frontend is already prepared for template execution
(`TemplateModePanel` Play button, `AeroplanePickerDialog` flow,
`executePlan(aeroplane_id, template_id)` call). Only the backend
guard blocks the existing wiring.

## Goal

Allow template executions for testing purposes, with generated files
treated as **ephemeral**: downloadable individually or as zip from the
result dialog, automatically replaced on the next template run.

Production plan executions are unchanged.

## Architecture

### Path scheme

| Type     | Path                                                          | Lifecycle                          |
|----------|---------------------------------------------------------------|------------------------------------|
| Plan     | `<ARTIFACTS_BASE_DIR>/<aero_id>/<plan_id>/<exec_id>/`         | persistent, manually managed       |
| Template | `<ARTIFACTS_BASE_DIR>/_template_runs/<template_id>/<exec_id>/` | replace-on-next-run                |

The `_template_runs/` underscore prefix isolates template runs from
the per-aeroplane artifact tree. `list_executions()` for regular plans
iterates aeroplane subdirectories; `_template_runs` is never
mistaken for an aeroplane.

### Replace-on-next-run

Before creating a new template execution directory, any existing
`<base>/_template_runs/<template_id>/` is wiped (`shutil.rmtree`).
At most one template execution exists on disk per template at any
time. No TTL sweeper, no explicit cleanup endpoint, no client-side
delete call.

### Frontend

`AeroplanePickerDialog` flow remains unchanged — the user picks an
aeroplane to execute the template against. The aeroplane provides
runtime configuration (wing_config, printer_settings) only; the
artifact location is independent of the chosen aeroplane.

`ExecutionResultDialog` is extended with a **Generated files**
section, applicable to both plan and template executions. The
section lists files via the existing `list_artifact_files` endpoint
and offers individual download links plus a *Download all (zip)*
button.

## Components

### Backend

**`app/services/artifact_service.py`**
- New `create_template_execution_dir(template_id) -> tuple[str, Path]`:
  - Wipe `<base>/_template_runs/<template_id>/` if it exists
  - Create `<base>/_template_runs/<template_id>/<exec_id>/`
  - Reuse `_ensure_within_base` for traversal protection
- Modify `_resolve_execution_dir(plan_id, execution_id)`:
  - First search `<base>/<aero_id>/<plan_id>/<execution_id>` (current behaviour)
  - Fall back to `<base>/_template_runs/<plan_id>/<execution_id>`
  - First match wins; both paths go through `_ensure_within_base`
- New `zip_execution(plan_id, execution_id) -> Path`:
  - Resolve execution dir (works for both plan and template)
  - Build zip in memory or to a temp file (decision in implementation plan)
  - Return path / streaming response (decision in implementation plan)

**`app/services/construction_plan_service.py`**
- `execute_plan()` — replace lines 603–606:
  - Remove the `ValidationError` guard
  - Branch on `plan.plan_type`:
    - `"template"` → `execution_id, artifact_dir = create_template_execution_dir(plan_id)`
    - else → `create_execution_dir(effective_aeroplane_id, plan_id)` (current path)
  - Require `request.aeroplane_id` for template executions, raise `ValidationError("aeroplane_id required for template execution")` otherwise
- `execute_plan_streaming()` — same change at lines 716–718

**`app/api/v2/endpoints/construction_plans.py`**
- New endpoint:
  ```python
  @router.get("/construction-plans/{plan_id}/artifacts/{execution_id}/zip")
  async def download_execution_zip(plan_id: int, execution_id: str): ...
  ```
  Returns `StreamingResponse` with `media_type="application/zip"`,
  filename `<plan_name>-<exec_id>.zip`. Empty execution → empty zip
  (200, not 404).

### Frontend

**`frontend/hooks/usePlanArtifacts.ts`** (or new `useExecutionZipUrl`)
- Helper that returns the zip download URL for a given
  `(planId, executionId)` pair.

**`frontend/components/workbench/construction-plans/ExecutionResultDialog.tsx`**
- New "Generated files" section, shown after a successful execution.
- Loads files via existing `list_artifact_files` SWR hook on mount.
- Header: *Download all (zip)* button → triggers zip URL.
- File list: each row shows filename + size + individual download link.
- Empty state: *"No files generated."*

## Data Flow

```
1. User clicks Play on a template in TemplateModePanel
2. AeroplanePickerDialog opens → user picks Aeroplane X
3. Frontend POST /construction-plans/{template_id}/execute
   { aeroplane_id: "X" }
4. Backend execute_plan():
   ├─ Load plan (plan_type=="template")
   ├─ effective_aeroplane_id = X (from request)
   ├─ create_template_execution_dir(template_id):
   │     ├─ shutil.rmtree(<base>/_template_runs/<template_id>/)
   │     └─ mkdir <base>/_template_runs/<template_id>/<exec_id>/
   ├─ _rewrite_export_paths(tree_json, artifact_dir)
   ├─ decode tree + create_shape()
   └─ return ExecutionResult(execution_id, artifact_dir, tessellation, ...)
5. Frontend ExecutionResultDialog opens
   ├─ Shows: status, duration, shape_keys, 3D preview
   └─ Loads GET /construction-plans/{template_id}/artifacts/{exec_id}
6. User clicks file → GET .../artifacts/{exec_id}/{filename}
   OR clicks "Download zip" → GET .../artifacts/{exec_id}/zip
7. User closes modal → no client-side cleanup
8. Next template run → step 4 wipes the previous execution
```

Plan execution flow is unchanged. The only frontend change visible to
plan users is the new files section in the result dialog.

## Error Handling

### Backend

| Scenario                                                            | Behaviour                                                           |
|---------------------------------------------------------------------|---------------------------------------------------------------------|
| Template execute without `aeroplane_id` in request                  | `ValidationError("aeroplane_id required for template execution")` → 422 |
| `aeroplane_id` does not exist                                       | `NotFoundError` from `get_aeroplane_or_raise` → 404                 |
| `_template_runs/<id>/` wipe fails (e.g. file lock)                  | `InternalError("Cannot reset template run directory")` → 500        |
| Decode/execute failure                                              | Existing `ExecutionResult(status="error", artifact_dir=..., execution_id=...)` with 200 |
| Zip endpoint: execution does not exist                              | `NotFoundError` → 404                                                |
| Zip endpoint: empty execution dir                                   | Empty zip, 200                                                       |
| Path-traversal attempt in `_template_runs`                          | Existing `_ensure_within_base` check rejects                         |

### Frontend

| Scenario                                                            | Behaviour                                                           |
|---------------------------------------------------------------------|---------------------------------------------------------------------|
| Files endpoint 404 after successful execution (race)                | "No files generated" hint, no crash                                 |
| Zip download network error                                          | Toast/alert, modal stays open, user can retry                       |
| User closes modal during zip download                               | Browser aborts download — no state to clean up                      |
| Template validation fails (existing `validatePlan`)                 | Existing flow — modal does not open, user sees issue list           |

### Edge case

Plan and template IDs share the same global sequence
(`construction_plans` table) — collisions are impossible, the
resolver can unambiguously locate either kind of execution.

## Testing

### Backend (pytest, fast tier)

`app/tests/test_construction_templates.py` (extend):
- `test_execute_template_returns_success`
- `test_execute_template_without_aeroplane_id_returns_422`
- `test_template_execution_replaces_previous_run`
- `test_template_artifacts_are_listable_via_plan_endpoints`
- `test_zip_download_returns_all_files`

`app/tests/test_artifact_service.py` (new or extend):
- `test_create_template_execution_dir_wipes_previous`
- `test_resolver_finds_template_execution`

`app/tests/test_construction_plans.py` (regression):
- `test_plan_execution_path_unchanged`

Tests use `tmp_path` as `ARTIFACTS_BASE_DIR` and mock `create_shape()`
to stay in the fast tier. One optional `slow` test exercises a real
Creator end-to-end.

### Frontend (vitest)

`frontend/__tests__/ExecutionResultDialog.test.tsx` (extend):
- Renders file list when files endpoint returns data
- Renders "no files" when empty
- Download-zip button triggers correct URL
- Each file row has individual download link

### E2E

Out of scope for this story. A playwright-bdd scenario
*"Template ausführen → Files herunterladen"* may be added once the
flow is stable.

### Coverage target

New backend functions ≥ 80% (consistent with the project-wide 70–80%
target in CLAUDE.md).

## Out of Scope

- Persistent template-run history (replaced on every run by design)
- Auth/permissions on template runs (template executions are
  observable via the same artifact endpoints — same trust boundary
  as plans)
- Background TTL sweeper (replace-on-next-run makes it unnecessary)
- E2E coverage for the new flow
