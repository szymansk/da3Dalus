# GH-387: EditParamsModal Reset Edge Case + Component Tests

## Problem

Three issues in `frontend/components/workbench/construction-plans/EditParamsModal.tsx`
introduced by #356 (editable CreatorId):

1. **Reset button state desync** — When `creatorInfo?.suggested_id` is null
   (valid state for creators without a suggested ID template), clicking reset
   clears `creatorIdDirty` to false but does not update `creatorId`. The button
   disappears while the manually-entered ID persists, silently treated as
   auto-derived.

2. **No component tests** — The dirty state transitions, auto-derivation gating,
   and save payload contract have zero component-level coverage.

3. **Unnecessary cast** — Line 56 uses `(node as Record<string, unknown>)._creatorIdDirty`
   but `_creatorIdDirty` is declared on the `PlanStepNode` interface.

## Design

### Fix 1: Reset Button Visibility

Show the reset button only when both conditions are true:
- `creatorIdDirty` is true (user manually edited the ID)
- `creatorInfo?.suggested_id` is truthy (a template exists to reset to)

Change line 119 from:
```tsx
{creatorIdDirty && (
```
to:
```tsx
{creatorIdDirty && creatorInfo?.suggested_id && (
```

This is consistent with the `onChange` auto-derivation guard (line 179)
which already checks `!creatorIdDirty && creatorInfo?.suggested_id`.

### Fix 2: Cast Cleanup

Change line 56 from:
```tsx
setCreatorIdDirty(!!(node as Record<string, unknown>)._creatorIdDirty);
```
to:
```tsx
setCreatorIdDirty(!!node._creatorIdDirty);
```

### Fix 3: Component Tests

New file: `frontend/__tests__/EditParamsModal.test.tsx`

Test cases:
- Typing into ID field sets dirty=true and stops auto-derivation on param change
- Clicking reset sets dirty=false and re-derives from template
- Reset button only renders when dirty=true AND suggested_id exists
- Reset button does NOT render when dirty=true but suggested_id is null
- `onSave` receives `creator_id` + `_creatorIdDirty: true` when dirty
- `onSave` receives `creator_id` without `_creatorIdDirty` when not dirty

## Acceptance Criteria

- [ ] Reset button hidden when `suggested_id` is null
- [ ] Component test file covers dirty state transitions
- [ ] Tests cover: dirty on type, reset clears dirty, reset button visibility, save payload
- [ ] Unnecessary Record cast removed
