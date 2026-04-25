# ShapeId Type for Creator Parameters

**Goal:** Replace the fragile regex-based `is_shape_ref` detection with a
self-documenting `ShapeId` type alias. Make `list[ShapeId]` parameters
visible in the frontend as multi-shape selectors.

## Changes

### 1. New type in cad_designer

Create `cad_designer/airplane/types.py`:
```python
from typing import NewType
ShapeId = NewType("ShapeId", str)
```

### 2. Update Creator constructors

Change type annotations from `str` → `ShapeId` and `list[str]` → `list[ShapeId]`
for all parameters that reference upstream shape keys. No behavioral changes —
`NewType` is assignment-compatible with `str`.

Affected Creators (all in `cad_designer/airplane/creator/`):
- `cad_operations/Cut2ShapesCreator.py` — `minuend: ShapeId`, `subtrahend: ShapeId`
- `cad_operations/Fuse2ShapesCreator.py` — `shape_a: ShapeId`, `shape_b: ShapeId`
- `cad_operations/Intersect2ShapesCreator.py` — `shape_a: ShapeId`, `shape_b: ShapeId`
- `cad_operations/AddMultipleShapesCreator.py` — `shapes: list[ShapeId]`
- `cad_operations/FuseMultipleShapesCreator.py` — `shapes: list[ShapeId]`
- `cad_operations/CutMultipleShapesCreator.py` — `subtrahends: list[ShapeId]`, `minuend: ShapeId`
- `cad_operations/SimpleOffsetShapeCreator.py` — `source_shape: ShapeId` (if applicable)
- `cad_operations/ScaleRotateTranslateCreator.py` — `source_shape: ShapeId` (if applicable)
- `cad_operations/RepairFacesShapeCreator.py` — `source_shape: ShapeId` (if applicable)
- Any other Creator whose params are passed to `shapes_of_interest_keys`

### 3. Backend introspection — replace regex with annotation check

In `app/services/construction_plan_service.py`:
- Delete `_get_shape_ref_params()` function (regex-based, ~30 lines)
- In `_collect_creators()`, determine shape-ref status from the type annotation
  string: if it contains `"ShapeId"`, the param is a shape ref
- Report `type: "ShapeId"` or `type: "list[ShapeId]"` in `CreatorParam`

### 4. Remove `is_shape_ref` from schema

In `app/schemas/construction_plan.py`:
- Remove `is_shape_ref` field from `CreatorParam`

In `frontend/hooks/useCreators.ts`:
- Remove `is_shape_ref` field from `CreatorParam` interface

### 5. Frontend — detect shape refs from type field

In `frontend/lib/planTreeUtils.ts`:
- `resolveNodeShapes`: check `param.type === "ShapeId" || param.type === "list[ShapeId]"`
  instead of `param.is_shape_ref`
- For `list[ShapeId]` params, read the value as `string[]` (or split comma-separated)

In `frontend/lib/planValidation.ts`:
- Same type check for validation

In `frontend/components/workbench/CreatorParameterForm.tsx`:
- Render shape selector for `type === "ShapeId"` (single)
- Render multi-shape selector for `type === "list[ShapeId]"` (list — tag input or
  multi-select from available shape keys)

## What gets deleted

- `_get_shape_ref_params()` in `construction_plan_service.py`
- `is_shape_ref` field in `CreatorParam` (backend + frontend)
- All `is_shape_ref` checks in frontend code

## Out of scope

- Changing Creator runtime behavior (only annotations change)
- Modifying `AbstractShapeCreator` base class
- Modifying `GeneralJSONEncoder/Decoder`
