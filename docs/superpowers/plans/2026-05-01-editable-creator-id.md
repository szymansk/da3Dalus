# Editable CreatorId Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to manually edit the CreatorId in the EditParamsModal, with a dirty flag that locks the value and prevents auto-derivation, plus a reset button to revert.

**Architecture:** Add `_creatorIdDirty` boolean to `PlanStepNode`. In `EditParamsModal`, render an editable text input for `creator_id` between the header and shapes section. When the user types into it, set `_creatorIdDirty = true` on the node, stopping auto-derivation from parameter changes. A reset button clears the flag and re-derives the ID. `toBackendTree()` strips `_creatorIdDirty` before serialization; `fromBackendTree()` preserves it via spread.

**Tech Stack:** React 19, TypeScript, Vitest, Tailwind CSS, lucide-react icons

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/components/workbench/PlanTree.tsx:16-21` | Modify | Add `_creatorIdDirty?: boolean` to `PlanStepNode` interface |
| `frontend/lib/planTreeUtils.ts:179-216` | Modify | Strip `_creatorIdDirty` in `toBackendTree()` |
| `frontend/components/workbench/construction-plans/EditParamsModal.tsx` | Modify | Add CreatorId text input with dirty tracking, reset button, auto-derivation on param change |
| `frontend/components/workbench/construction-plans/PlanTreeSection.tsx:30-35` | Modify | Skip placeholder re-derivation when `_creatorIdDirty` is truthy |
| `frontend/app/workbench/construction-plans/page.tsx:322-347` | Modify | Pass `creatorInfo` to `EditParamsModal` for `suggested_id` access (already passed), ensure `creator_id` + `_creatorIdDirty` flow through `handleEditSave` |
| `frontend/__tests__/planTreeUtils.test.ts` | Modify | Add tests for dirty flag stripping and preservation |

---

### Task 1: Add `_creatorIdDirty` to PlanStepNode and test `toBackendTree` stripping

**Files:**
- Modify: `frontend/components/workbench/PlanTree.tsx:16-21`
- Modify: `frontend/lib/planTreeUtils.ts:179-216`
- Test: `frontend/__tests__/planTreeUtils.test.ts`

- [ ] **Step 1: Write the failing test for `toBackendTree` stripping `_creatorIdDirty`**

Add to `frontend/__tests__/planTreeUtils.test.ts` inside the `describe("toBackendTree", ...)` block:

```typescript
it("strips _creatorIdDirty from nodes before serialization", () => {
  const frontend: PlanStepNode = {
    $TYPE: "ConstructionRootNode",
    creator_id: "root",
    successors: [
      {
        $TYPE: "WingLoftCreator",
        creator_id: "custom_wing",
        _creatorIdDirty: true,
        offset: 0,
        successors: [],
      },
    ],
  };
  const backend = toBackendTree(frontend);
  const step = (backend.successors as Record<string, Record<string, unknown>>)["custom_wing"];
  const creator = step.creator as Record<string, unknown>;
  expect(creator._creatorIdDirty).toBeUndefined();
  expect(step._creatorIdDirty).toBeUndefined();
  expect(backend._creatorIdDirty).toBeUndefined();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run __tests__/planTreeUtils.test.ts -t "strips _creatorIdDirty"`
Expected: FAIL — `_creatorIdDirty` will appear in `creator` because it's spread into `creatorParams`.

- [ ] **Step 3: Add `_creatorIdDirty` to the `PlanStepNode` interface**

In `frontend/components/workbench/PlanTree.tsx`, change the interface:

```typescript
export interface PlanStepNode {
  $TYPE: string;
  creator_id: string;
  _creatorIdDirty?: boolean;
  [key: string]: unknown;
  successors?: PlanStepNode[];
}
```

- [ ] **Step 4: Strip `_creatorIdDirty` in `toBackendTree()`**

In `frontend/lib/planTreeUtils.ts`, in the `toBackendTree` function, update the destructuring on line 186 to also extract `_creatorIdDirty`:

```typescript
const { $TYPE, creator_id, successors: childSuccessors, _creatorIdDirty, ...creatorParams } = child;
```

The variable `_creatorIdDirty` is destructured but intentionally unused — it's discarded. Also strip it from the root:

Change line 208 from:
```typescript
const { successors: _s, ...rootFields } = node as Record<string, unknown>;
```
to:
```typescript
const { successors: _s, _creatorIdDirty: _d, ...rootFields } = node as Record<string, unknown>;
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd frontend && npx vitest run __tests__/planTreeUtils.test.ts -t "strips _creatorIdDirty"`
Expected: PASS

- [ ] **Step 6: Write test for `fromBackendTree` preserving `_creatorIdDirty`**

Add to `frontend/__tests__/planTreeUtils.test.ts` inside the `describe("fromBackendTree", ...)` block:

```typescript
it("preserves _creatorIdDirty when present in frontend-format tree", () => {
  const frontend: PlanStepNode = {
    $TYPE: "ConstructionRootNode",
    creator_id: "root",
    successors: [
      {
        $TYPE: "WingLoftCreator",
        creator_id: "custom_wing",
        _creatorIdDirty: true,
        successors: [],
      },
    ],
  };
  const result = fromBackendTree(frontend);
  expect(result.successors![0]._creatorIdDirty).toBe(true);
});

it("works fine with old trees that lack _creatorIdDirty", () => {
  const frontend: PlanStepNode = {
    $TYPE: "ConstructionRootNode",
    creator_id: "root",
    successors: [
      { $TYPE: "WingLoftCreator", creator_id: "w1", successors: [] },
    ],
  };
  const result = fromBackendTree(frontend);
  expect(result.successors![0]._creatorIdDirty).toBeUndefined();
});
```

- [ ] **Step 7: Run the new `fromBackendTree` tests**

Run: `cd frontend && npx vitest run __tests__/planTreeUtils.test.ts -t "preserves _creatorIdDirty"`
Expected: PASS — `fromBackendTree` already spreads all fields via `...params`, so `_creatorIdDirty` passes through naturally.

- [ ] **Step 8: Write round-trip test with dirty flag**

Add to `frontend/__tests__/planTreeUtils.test.ts` inside the `describe("round-trip conversion", ...)` block:

```typescript
it("round-trip strips _creatorIdDirty (frontend → backend → frontend)", () => {
  const original: PlanStepNode = {
    $TYPE: "ConstructionRootNode",
    creator_id: "root",
    successors: [
      {
        $TYPE: "WingLoftCreator",
        creator_id: "custom_wing",
        _creatorIdDirty: true,
        offset: 0,
        successors: [],
      },
    ],
  };
  const roundTripped = fromBackendTree(toBackendTree(original));
  expect(roundTripped.successors![0].creator_id).toBe("custom_wing");
  expect(roundTripped.successors![0]._creatorIdDirty).toBeUndefined();
  expect(roundTripped.successors![0].offset).toBe(0);
});
```

- [ ] **Step 9: Run all planTreeUtils tests**

Run: `cd frontend && npx vitest run __tests__/planTreeUtils.test.ts`
Expected: All tests PASS

- [ ] **Step 10: Commit**

```bash
git add frontend/components/workbench/PlanTree.tsx frontend/lib/planTreeUtils.ts frontend/__tests__/planTreeUtils.test.ts
git commit -m "feat(gh-356): add _creatorIdDirty to PlanStepNode, strip in toBackendTree"
```

---

### Task 2: Add editable CreatorId input to EditParamsModal

**Files:**
- Modify: `frontend/components/workbench/construction-plans/EditParamsModal.tsx`

- [ ] **Step 1: Add the CreatorId text input with dirty tracking and reset button**

In `frontend/components/workbench/construction-plans/EditParamsModal.tsx`:

1. Add `RotateCcw` to the lucide-react import:
```typescript
import { ArrowRight, ArrowLeft, X, RotateCcw } from "lucide-react";
```

2. Add `resolveIdTemplate` to the planTreeUtils import:
```typescript
import { resolveNodeShapes, resolveIdTemplate } from "@/lib/planTreeUtils";
```

3. Add local state for `creatorId` and `creatorIdDirty` inside the component, right after the `lastNodePath` state block (after line 55). When the modal opens for a new node, initialise from the node:

```typescript
const [creatorId, setCreatorId] = useState(node?.creator_id ?? "");
const [creatorIdDirty, setCreatorIdDirty] = useState<boolean>(
  !!(node as Record<string, unknown>)?._creatorIdDirty,
);

// Sync creatorId/dirty state when a different node opens
if (open && node && nodePath !== lastNodePath) {
  // (this block already exists — add these two lines inside it, after setValues)
}
```

Actually, integrate into the existing reset block. Replace the current block at lines 48-55:

```typescript
const [lastNodePath, setLastNodePath] = useState<string | null>(null);
const [creatorId, setCreatorId] = useState("");
const [creatorIdDirty, setCreatorIdDirty] = useState(false);

if (open && node && nodePath !== lastNodePath) {
  setLastNodePath(nodePath);
  setValues(creatorInfo ? extractValues(node, creatorInfo) : {});
  setCreatorId(node.creator_id);
  setCreatorIdDirty(!!(node as Record<string, unknown>)._creatorIdDirty);
}
if (!open && lastNodePath !== null) {
  setLastNodePath(null);
}
```

4. Add auto-derivation: when a parameter changes and the ID is NOT dirty, re-derive `creatorId` from `suggested_id`. Replace the `onChange` callback in `CreatorParameterForm` (line 136):

```typescript
onChange={(key, value) => {
  const next = { ...values, [key]: value };
  setValues(next);
  if (!creatorIdDirty && creatorInfo?.suggested_id) {
    setCreatorId(resolveIdTemplate(creatorInfo.suggested_id, next));
  }
}}
```

5. Update `handleSave` to include `creator_id` and `_creatorIdDirty` in the saved params. Change line 64 from:
```typescript
await onSave(nodePath, values);
```
to:
```typescript
await onSave(nodePath, { ...values, creator_id: creatorId, _creatorIdDirty: creatorIdDirty || undefined });
```

The `|| undefined` ensures falsy values don't get serialised as `false` — the field is omitted entirely when not dirty.

6. Add the CreatorId input UI between the header (`</div>` at line 94) and the body (`<div className="flex flex-1 flex-col...">` at line 97). Insert this block:

```tsx
{/* CreatorId field */}
<div className="flex items-center gap-2 border-b border-border px-6 py-3">
  <label
    htmlFor="creator-id-input"
    className="shrink-0 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground"
  >
    ID
  </label>
  <input
    id="creator-id-input"
    type="text"
    value={creatorId}
    onChange={(e) => {
      setCreatorId(e.target.value);
      setCreatorIdDirty(true);
    }}
    className="flex-1 rounded-lg border border-border bg-card-muted/30 px-2 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground outline-none focus:border-primary"
  />
  {creatorIdDirty && (
    <button
      type="button"
      onClick={() => {
        setCreatorIdDirty(false);
        if (creatorInfo?.suggested_id) {
          setCreatorId(resolveIdTemplate(creatorInfo.suggested_id, values));
        }
      }}
      title="Reset to auto-derived ID"
      className="flex size-6 shrink-0 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
    >
      <RotateCcw size={12} />
    </button>
  )}
</div>
```

- [ ] **Step 2: Verify the full test suite still passes**

Run: `cd frontend && npx vitest run`
Expected: All tests PASS (no runtime errors from the component changes)

- [ ] **Step 3: Commit**

```bash
git add frontend/components/workbench/construction-plans/EditParamsModal.tsx
git commit -m "feat(gh-356): add editable CreatorId input with dirty flag and reset button"
```

---

### Task 3: Update PlanTreeSection display for dirty nodes

**Files:**
- Modify: `frontend/components/workbench/construction-plans/PlanTreeSection.tsx:30-35`

- [ ] **Step 1: Skip placeholder re-derivation when `_creatorIdDirty` is true**

In `frontend/components/workbench/construction-plans/PlanTreeSection.tsx`, replace lines 30-35:

```typescript
// Resolve {placeholder} in creator_id for display (e.g. "{wing_index}.vase_wing" → "0.vase_wing")
const nodeRecord = node as Record<string, unknown>;
const displayLabel = node.creator_id.replace(/\{(\w+)\}/g, (_match, param) => {
  const val = nodeRecord[param];
  return typeof val === "string" ? val : typeof val === "number" ? String(val) : `{${param}}`;
});
```

with:

```typescript
const nodeRecord = node as Record<string, unknown>;
const displayLabel = nodeRecord._creatorIdDirty
  ? node.creator_id
  : node.creator_id.replace(/\{(\w+)\}/g, (_match, param) => {
      const val = nodeRecord[param];
      return typeof val === "string" ? val : typeof val === "number" ? String(val) : `{${param}}`;
    });
```

When `_creatorIdDirty` is true, the user typed this ID manually — show it as-is without attempting placeholder resolution.

- [ ] **Step 2: Run the frontend test suite**

Run: `cd frontend && npx vitest run`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add frontend/components/workbench/construction-plans/PlanTreeSection.tsx
git commit -m "feat(gh-356): skip placeholder re-derivation for dirty creator IDs in tree display"
```

---

### Task 4: Ensure `handleEditSave` flows `creator_id` and `_creatorIdDirty` through

**Files:**
- Modify: `frontend/app/workbench/construction-plans/page.tsx:322-347`

- [ ] **Step 1: Verify the current shallow merge already handles this**

Look at `handleEditSave` in `page.tsx` line 334:

```typescript
const updatedNode = { ...editingNode, ...params } as PlanStepNode;
```

Since Task 2 already includes `creator_id` and `_creatorIdDirty` in the `params` passed from `EditParamsModal.handleSave`, the shallow merge will correctly update both fields on the node. **No code change is needed here** — the existing merge already handles it.

However, the `onSave` type signature `(path: string, updatedParams: Record<string, unknown>) => Promise<void>` already accepts any key-value pairs, so `creator_id` and `_creatorIdDirty` flow through naturally.

- [ ] **Step 2: Verify no changes needed — run full test suite**

Run: `cd frontend && npx vitest run`
Expected: All tests PASS

---

### Task 5: Visual verification in browser

- [ ] **Step 1: Start the frontend dev server**

Run: `cd frontend && npm run dev`

- [ ] **Step 2: Test the golden path**

1. Navigate to Construction Plans workbench
2. Open an existing plan or create a new one with a step
3. Click Edit on a step → verify the CreatorId field appears between header and shapes
4. Verify the CreatorId shows the current auto-derived value
5. Change a parameter that appears in the `suggested_id` template → verify the CreatorId auto-updates
6. Manually type a custom ID → verify the reset button appears
7. Change a parameter → verify the CreatorId does NOT auto-update (dirty lock)
8. Click the reset button → verify ID reverts to auto-derived value, reset button disappears
9. Save → verify the custom ID persists in the tree display
10. Re-open the edit modal → verify the custom ID and dirty state are preserved

- [ ] **Step 3: Test edge cases**

1. Enter an empty string as CreatorId → save → verify backend rejects (non-empty required)
2. Enter a CreatorId that already exists in the plan → save → verify the duplicate warning appears in console
3. Edit a node from a plan loaded from backend (old format without `_creatorIdDirty`) → verify it defaults to non-dirty (auto-derivation works)

- [ ] **Step 4: Final commit if any visual fixes were needed**

```bash
git add -A
git commit -m "fix(gh-356): visual adjustments from browser testing"
```

---

### Task 6: Run full test suite and verify

- [ ] **Step 1: Run all frontend unit tests**

Run: `cd frontend && npx vitest run`
Expected: All tests PASS

- [ ] **Step 2: Run dependency check**

Run: `cd frontend && npm run deps:check`
Expected: No circular dependency violations

- [ ] **Step 3: Final commit if needed**

All work complete. The branch is ready for PR creation.
