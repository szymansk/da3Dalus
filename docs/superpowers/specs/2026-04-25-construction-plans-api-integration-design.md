# Construction Plans — Real API Integration Design

**Issues:** #325 (Plan mode), #326 (Template mode), #328 (Input/output shapes)
**Epic:** #320
**Branch base:** `feat/gh-323-click-dummy-construction-plans`

## Goal

Replace mock data in the click-dummy construction plans page with real backend
API integration. After this work, the page fetches real plans/templates from the
database, displays input/output shapes from the Creator catalog, and all plan-level
actions (execute, save-as-template, rename, add step, parameter editing) are functional.

## Architecture

The click-dummy split (#324) produced 6 files under
`frontend/components/workbench/construction-plans/`. This integration evolves those
components from mock types (`MockCreatorNode`, `MockPlan`, etc.) to real API types
(`PlanStepNode`, `PlanSummary`, `PlanRead`, `CreatorInfo`).

**Data flow:**
```
useAeroplaneContext() → aeroplaneId
  ├─ useAeroplanePlans(aeroplaneId) → PlanSummary[] (plan list)
  ├─ useConstructionPlans("template") → PlanSummary[] (template list)
  ├─ useConstructionPlan(planId) → PlanRead (full tree_json)
  └─ useCreators() → CreatorInfo[] (shape metadata)
```

**Existing infrastructure (no changes needed):**
- Backend endpoints: `construction_plans.py`, `construction_templates.py`, `aeroplane_construction_plans.py`
- Backend service: `construction_plan_service.py`
- Frontend hooks: `useConstructionPlans.ts`, `useCreators.ts`
- Frontend utilities: `planTreeUtils.ts` (tree manipulation, shape key resolution, format conversion)
- Context: `useAeroplaneContext()` provides `aeroplaneId` from the workbench layout

## Components

### 1. types.ts — Delete and replace

**Delete** `frontend/components/workbench/construction-plans/types.ts` entirely.
All mock types (`MockShape`, `MockCreatorNode`, `MockPlan`, `MockTemplate`) and
mock data constants (`MOCK_PLANS`, `MOCK_TEMPLATES`) are removed.

Components import real types from existing modules:
- `PlanStepNode` from `@/lib/planTreeUtils`
- `PlanSummary`, `PlanRead` from `@/hooks/useConstructionPlans`
- `CreatorInfo`, `CreatorOutput` from `@/hooks/useCreators`

### 2. Shape resolution utility

Create a helper function (in `planTreeUtils.ts` or a new file) for resolving
a tree node's input/output shapes from the Creator catalog:

```typescript
interface ResolvedShapes {
  inputs: string[];   // parameter names where is_shape_ref === true
  outputs: string[];  // from CreatorInfo.outputs (can be multiple)
}

function resolveNodeShapes(
  node: PlanStepNode,
  creators: CreatorInfo[],
): ResolvedShapes
```

**Implementation:**
1. Find the `CreatorInfo` matching `node.$TYPE`
2. Inputs: `creator.parameters.filter(p => p.is_shape_ref).map(p => p.name)`
3. Outputs: `creator.outputs.map(o => o.name)` — note that a Creator can produce
   multiple output shapes (e.g., a creator that generates both a shell and a lid)

This function is used by `PlanTreeSection`'s recursive renderer to display
shape rows under each creator node.

### 3. page.tsx — Real data coordinator

**Remove:**
- All imports from `./types` (mock data)
- `INITIAL_EXPANDED_CREATORS` constant
- `countCreators` utility

**Add:**
- `useAeroplaneContext()` for `aeroplaneId`
- `useAeroplanePlans(aeroplaneId)` for plan list
- `useConstructionPlans("template")` for template list
- `useCreators()` for creator catalog (already imported for CreatorGallery)
- `selectedPlanId: number | null` state — set when expanding a plan to fetch
  its full `tree_json` via `useConstructionPlan(selectedPlanId)`

**State changes:**
- `expandedPlans` initialized from first plan in list (not hardcoded IDs)
- `expandedCreators` starts as empty Set (no pre-expanded nodes)
- Total step count derived from `plans.reduce((sum, p) => sum + p.step_count, 0)`
  using `PlanSummary.step_count` (already computed by backend)

**Plan-level action callbacks:**
- `handleExecutePlan(planId)` → call `executePlan(aeroplaneId, planId)`,
  display result in 3D viewer (tessellation data) or error toast
- `handleSaveAsTemplate(planId)` → call `toTemplate(aeroplaneId, planId)`,
  mutate template list, show success feedback
- `handleRenamePlan(planId, newName)` → call `updatePlan(planId, { name: newName })`,
  mutate plan list
- `handleAddStep(planId, parentPath)` → open creator picker, then:
  1. Build new `PlanStepNode` from selected `CreatorInfo`
  2. Call `appendChildAtPath(tree, parentPath, newNode)` from `planTreeUtils`
  3. Convert via `toBackendTree()` and call `updatePlan(planId, { tree_json })`
  4. Mutate plan detail

**No-aeroplane guard:** When `aeroplaneId` is null (no aeroplane selected),
show a centered message: "Select an aeroplane to view its construction plans."
This matches the pattern used by other workbench pages.

### 4. PlanTreeSection — Real tree rendering

**Props change:**
```typescript
interface PlanTreeSectionProps {
  plan: PlanSummary;
  treeJson: PlanStepNode | null;  // null while loading
  creators: CreatorInfo[];
  aeroplaneId: string;
  expanded: boolean;
  onToggle: () => void;
  expandedCreators: Set<string>;
  onToggleCreator: (key: string) => void;
  onEditCreator: (planId: number, node: PlanStepNode, path: string) => void;
  onExecute: (planId: number) => void;
  onSaveAsTemplate: (planId: number) => void;
  onRename: (planId: number, newName: string) => void;
  onAddStep: (planId: number, parentPath?: string) => void;
  hidePlanActions?: boolean;
}
```

**renderCreatorTree changes:**
- Operates on `PlanStepNode` instead of `MockCreatorNode`
- `node.$TYPE` → chip label (strip "Creator" suffix, same as before)
- `node.creator_id` → row label
- Shape rows resolved via `resolveNodeShapes(node, creators)` — shows all
  inputs (blue arrow down) and all outputs (green arrow up)
- `node.successors` → recursive children
- `path` parameter added for tree mutation callbacks (e.g., "root.0.2")

**Plan header action buttons become functional:**
- Play → calls `onExecute(plan.id)`
- Save as Template → calls `onSaveAsTemplate(plan.id)`
- Rename → inline edit mode (contentEditable or input), then `onRename(plan.id, newName)`
- Add Step → calls `onAddStep(plan.id)`

### 5. TemplateModePanel — Real template data

**Data fetching:**
- Template list from `useConstructionPlans("template")` (passed as prop from page)
- Selected template detail from `useConstructionPlan(selectedTemplateId)` (passed as prop)

**Props change:**
```typescript
interface TemplateModePanelProps {
  templates: PlanSummary[];
  selectedTemplateId: number | null;
  selectedTemplateTree: PlanStepNode | null;
  creators: CreatorInfo[];
  onSelectTemplate: (id: number) => void;
  // ... expand/toggle/edit callbacks
  onExecuteTemplate: (templateId: number) => void;  // opens aeroplane picker
  onInstantiateTemplate: (templateId: number) => void;
  treeWide: boolean;
  onToggleWide: () => void;
}
```

**Template Play button:** Opens an aeroplane selection dialog (simple dropdown
using `useAeroplanes()`) before executing. This is a small modal, not a full page.

**TemplateSelector:** Stays largely the same but uses `PlanSummary` instead of
`MockTemplate`. The `step_count` field is already on `PlanSummary`.

### 6. EditParamsModal — Real parameter editing

**Props change:**
```typescript
interface EditParamsModalProps {
  open: boolean;
  node: PlanStepNode | null;     // the real tree node
  nodePath: string | null;       // path in tree (for mutation)
  creatorInfo: CreatorInfo | null;
  availableShapeKeys: string[];  // from collectAvailableShapeKeys()
  onClose: () => void;
  onSave: (path: string, updatedParams: Record<string, unknown>) => void;
}
```

**Changes from click-dummy:**
- Values initialized from the node's actual parameters (`node[paramName]`)
- `availableShapeKeys` populated via `collectAvailableShapeKeys(tree, creators, nodePath)`
  from `planTreeUtils.ts` — provides shape keys available at this point in the tree
- Save calls `onSave(path, updatedParams)` which the page handles by:
  1. `updateNodeAtPath(tree, path, mergedNode)`
  2. `toBackendTree(updatedTree)`
  3. `updatePlan(planId, { tree_json })`
  4. Mutate SWR cache

### 7. Execution result handling

When `executePlan()` returns an `ExecutionResult`:
- **Success:** Open the existing 3D viewer modal with `result.tessellation` data.
  The tessellation format is already compatible with `three-cad-viewer`.
- **Error:** Show an error toast/banner with `result.error` message.
- **Loading state:** Disable the Play button and show a spinner while executing.

The 3D viewer modal pattern already exists in the project (used by the wing
editor). Reuse that pattern.

### 8. Tree persistence pattern

All tree mutations follow the same pattern:
1. Modify the in-memory tree using `planTreeUtils` functions
2. Convert to backend format via `toBackendTree()`
3. Persist via `updatePlan(planId, { tree_json: backendTree })`
4. Mutate SWR cache for immediate UI update

This applies to: add step, delete step, reorder, rename node, edit parameters.

## What stays unchanged

- Visual layout, styling, TreeCard/SimpleTreeRow usage
- Mode toggle (Plans/Templates pill buttons)
- Panel expand/collapse (PanelLeftOpen/PanelLeftClose)
- CreatorGallery on the right (already uses real `useCreators()`)
- `useDialog` hook pattern for modals
- Branch stays `feat/gh-323-click-dummy-construction-plans`

## Out of scope

- Drag-and-drop (#327) — separate issue, uses `@dnd-kit` integration
- Artifact browser (#331) — depends on backend artifact directory (#330)
- Validation before execution (#332) — separate issue
- Undo/Redo — future enhancement
- Backend changes — all endpoints already exist
