# Plan: GH-358 — Add Insert/Add/Delete Controls to X-Secs Tree View

## Summary

Mirror the Segments view's insert/add/delete UI into `buildXsecNodes()`.
Frontend-only change, all handlers and callbacks already exist.

## Tasks

### Task 1: Write failing tests for X-Secs CRUD controls (RED)

**File:** `frontend/__tests__/XsecTreeCrud.test.tsx`

Tests to write:
1. Insert-point nodes appear between consecutive x-secs (not before first)
2. Clicking insert point calls `handleInsertXsec(wingName, i)`
3. `+ x_sec` node appears after the last x-sec
4. Clicking `+ x_sec` calls `handleAddSegment(wingName)`
5. Wing-level node has delete that calls `onDeleteXsec(wingName, -1)` after confirm
6. Segments view is unchanged (no regressions)

**Pattern:** Follow `FuselageTree.test.tsx` for rendering `<AeroplaneTree>` with mock data.

### Task 2: Add wing-level delete to X-Secs view (GREEN)

**File:** `frontend/components/workbench/AeroplaneTree.tsx`
**Location:** `buildXsecNodes()` line 303-310

Add `onDelete` to wing node:
```tsx
onDelete: () => {
  if (confirm(`Delete wing "${wingName}"?`)) {
    callbacks.onDeleteXsec(wingName, -1);
  }
},
```

### Task 3: Add insert points between x-secs (GREEN)

**File:** `frontend/components/workbench/AeroplaneTree.tsx`
**Location:** Inside `wing.x_secs.forEach()` at line 318, before each x-sec node

Add insert-point node when `i > 0 && callbacks.onInsertXsec`:
```tsx
if (i > 0 && callbacks.onInsertXsec) {
  nodes.push({
    id: `${wingName}-xsec-ins-${i}`,
    label: "insert",
    level: 2,
    isInsertPoint: true,
    onInsert: () => callbacks.onInsertXsec!(wingName, i),
  });
}
```

### Task 4: Add `+ x_sec` button after x-sec list (GREEN)

**File:** `frontend/components/workbench/AeroplaneTree.tsx`
**Location:** After the `forEach` loop (line 367), before `return nodes`

Add append button:
```tsx
if (callbacks.onAddSegment) {
  nodes.push({
    id: `${wingName}-xsec-add`,
    label: "+ x_sec",
    level: 2, leaf: true, muted: true,
    onClick: () => callbacks.onAddSegment!(wingName),
  });
}
```

### Task 5: Verify all tests pass (REFACTOR)

Run `npm run test:unit` — confirm:
- New tests pass (insert, add, delete)
- Existing tests pass (no regressions in FuselageTree, etc.)

## Dependencies

- Tasks 2-4 are independent of each other but all depend on Task 1
- Task 5 depends on Tasks 2-4

## Risk Assessment

**Low risk** — copying established patterns, no interface/handler changes,
no backend changes, no new dependencies.
