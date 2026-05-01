# GH-387: EditParamsModal Reset Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the reset button state desync when `suggested_id` is null, remove an unnecessary type cast, and add component tests for EditParamsModal.

**Architecture:** Three small, independent changes to `EditParamsModal.tsx` (visibility guard, cast removal) plus a new test file. Tests written first (TDD), then production fixes.

**Tech Stack:** React 19, TypeScript, vitest, @testing-library/react

---

### Task 1: Add component test — reset button visibility

**Files:**
- Create: `frontend/__tests__/EditParamsModal.test.tsx`

- [ ] **Step 1: Create test file with mocks and helpers**

The modal uses `useDialog` (which calls `showModal()`/`close()` on the `<dialog>` element), `CreatorParameterForm`, and `resolveNodeShapes`/`resolveIdTemplate` from `planTreeUtils`. Mock the first two; import the real `resolveIdTemplate` since it's pure logic.

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import React from "react";
import type { PlanStepNode } from "@/components/workbench/PlanTree";
import type { CreatorInfo } from "@/hooks/useCreators";

// Mock lucide-react icons used by EditParamsModal
vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return { ArrowRight: icon, ArrowLeft: icon, X: icon, RotateCcw: icon };
});

// Mock useDialog — jsdom doesn't support <dialog>.showModal()
vi.mock("@/hooks/useDialog", () => ({
  useDialog: (_open: boolean, onClose: () => void) => ({
    dialogRef: { current: null },
    handleClose: onClose,
  }),
}));

// Mock CreatorParameterForm — render a stub that exposes onChange
let capturedOnChange: ((key: string, value: unknown) => void) | null = null;
vi.mock("@/components/workbench/CreatorParameterForm", () => ({
  CreatorParameterForm: (props: { onChange: (key: string, value: unknown) => void }) => {
    capturedOnChange = props.onChange;
    return React.createElement("div", { "data-testid": "param-form" });
  },
}));

// Mock resolveNodeShapes — not relevant for these tests
vi.mock("@/lib/planTreeUtils", async (importOriginal) => {
  const orig = await importOriginal<typeof import("@/lib/planTreeUtils")>();
  return {
    ...orig,
    resolveNodeShapes: () => ({ inputs: [], outputs: [] }),
  };
});

import { EditParamsModal } from "@/components/workbench/construction-plans/EditParamsModal";

function makeNode(overrides: Partial<PlanStepNode> = {}): PlanStepNode {
  return {
    $TYPE: "SomeCreator",
    creator_id: "original-id",
    ...overrides,
  } as PlanStepNode;
}

function makeCreatorInfo(overrides: Partial<CreatorInfo> = {}): CreatorInfo {
  return {
    class_name: "SomeCreator",
    category: "wing",
    description: null,
    parameters: [{ name: "span", type: "number", default: 1000, required: true, description: null, options: null }],
    outputs: [],
    suggested_id: "wing_{span}",
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  capturedOnChange = null;
});
```

- [ ] **Step 2: Write test — reset button hidden when suggested_id is null**

```tsx
describe("EditParamsModal — reset button", () => {
  it("does not show reset button when dirty but suggested_id is null", () => {
    const node = makeNode({ _creatorIdDirty: true });
    const creator = makeCreatorInfo({ suggested_id: null });

    render(
      <EditParamsModal
        open={true}
        node={node}
        nodePath="/0"
        creatorInfo={creator}
        availableShapeKeys={[]}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />,
    );

    expect(screen.queryByTitle("Reset to auto-derived ID")).toBeNull();
  });

  it("shows reset button when dirty and suggested_id exists", () => {
    const node = makeNode({ _creatorIdDirty: true });
    const creator = makeCreatorInfo({ suggested_id: "wing_{span}" });

    render(
      <EditParamsModal
        open={true}
        node={node}
        nodePath="/0"
        creatorInfo={creator}
        availableShapeKeys={[]}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />,
    );

    expect(screen.queryByTitle("Reset to auto-derived ID")).not.toBeNull();
  });

  it("does not show reset button when not dirty", () => {
    const node = makeNode();
    const creator = makeCreatorInfo({ suggested_id: "wing_{span}" });

    render(
      <EditParamsModal
        open={true}
        node={node}
        nodePath="/0"
        creatorInfo={creator}
        availableShapeKeys={[]}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />,
    );

    expect(screen.queryByTitle("Reset to auto-derived ID")).toBeNull();
  });
});
```

- [ ] **Step 3: Run tests to verify the first test FAILS**

Run: `cd frontend && npx vitest run __tests__/EditParamsModal.test.tsx`

Expected: First test FAILS — reset button IS rendered when `suggested_id` is null (because the current guard only checks `creatorIdDirty`).

---

### Task 2: Fix reset button visibility guard

**Files:**
- Modify: `frontend/components/workbench/construction-plans/EditParamsModal.tsx:119`

- [ ] **Step 1: Update the reset button condition**

Change line 119 from:
```tsx
{creatorIdDirty && (
```
to:
```tsx
{creatorIdDirty && creatorInfo?.suggested_id && (
```

- [ ] **Step 2: Run tests to verify all three pass**

Run: `cd frontend && npx vitest run __tests__/EditParamsModal.test.tsx`

Expected: All 3 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/__tests__/EditParamsModal.test.tsx frontend/components/workbench/construction-plans/EditParamsModal.tsx
git commit -m "fix(gh-387): hide reset button when suggested_id is null"
```

---

### Task 3: Add test — dirty state on typing into ID field

**Files:**
- Modify: `frontend/__tests__/EditParamsModal.test.tsx`

- [ ] **Step 1: Write test — typing into ID field sets dirty and stops auto-derivation**

```tsx
describe("EditParamsModal — dirty state transitions", () => {
  it("typing into ID field sets dirty and blocks auto-derivation on param change", () => {
    const node = makeNode();
    const creator = makeCreatorInfo({ suggested_id: "wing_{span}" });

    render(
      <EditParamsModal
        open={true}
        node={node}
        nodePath="/0"
        creatorInfo={creator}
        availableShapeKeys={[]}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />,
    );

    const idInput = screen.getByLabelText("ID") as HTMLInputElement;

    // Type into the ID field — should become dirty
    fireEvent.change(idInput, { target: { value: "my-custom-id" } });
    expect(idInput.value).toBe("my-custom-id");

    // Now change a param — ID should NOT auto-derive because dirty
    act(() => { capturedOnChange?.("span", 2000); });
    expect(idInput.value).toBe("my-custom-id");
  });
});
```

- [ ] **Step 2: Run test to verify it passes**

Run: `cd frontend && npx vitest run __tests__/EditParamsModal.test.tsx`

Expected: PASS (this tests existing correct behavior).

- [ ] **Step 3: Commit**

```bash
git add frontend/__tests__/EditParamsModal.test.tsx
git commit -m "test(gh-387): add dirty state transition test for EditParamsModal"
```

---

### Task 4: Add test — reset click clears dirty and re-derives ID

**Files:**
- Modify: `frontend/__tests__/EditParamsModal.test.tsx`

- [ ] **Step 1: Write test — clicking reset clears dirty and re-derives from template**

```tsx
describe("EditParamsModal — reset behavior", () => {
  it("clicking reset clears dirty and re-derives ID from template", () => {
    const node = makeNode({ _creatorIdDirty: true });
    const creator = makeCreatorInfo({ suggested_id: "wing_{span}" });

    render(
      <EditParamsModal
        open={true}
        node={node}
        nodePath="/0"
        creatorInfo={creator}
        availableShapeKeys={[]}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />,
    );

    const idInput = screen.getByLabelText("ID") as HTMLInputElement;
    // Type custom value
    fireEvent.change(idInput, { target: { value: "custom-id" } });
    expect(idInput.value).toBe("custom-id");

    // Click reset
    const resetBtn = screen.getByTitle("Reset to auto-derived ID");
    fireEvent.click(resetBtn);

    // ID should be resolved from template with current param values
    // Default span=1000, so template "wing_{span}" → "wing_1000"
    expect(idInput.value).toBe("wing_1000");

    // Reset button should disappear (dirty=false)
    expect(screen.queryByTitle("Reset to auto-derived ID")).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it passes**

Run: `cd frontend && npx vitest run __tests__/EditParamsModal.test.tsx`

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/__tests__/EditParamsModal.test.tsx
git commit -m "test(gh-387): add reset behavior test for EditParamsModal"
```

---

### Task 5: Add test — save payload contract

**Files:**
- Modify: `frontend/__tests__/EditParamsModal.test.tsx`

- [ ] **Step 1: Write test — onSave receives correct payload based on dirty state**

```tsx
describe("EditParamsModal — save payload", () => {
  it("sends _creatorIdDirty: true when ID was manually edited", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const node = makeNode();
    const creator = makeCreatorInfo({ suggested_id: "wing_{span}" });

    render(
      <EditParamsModal
        open={true}
        node={node}
        nodePath="/0"
        creatorInfo={creator}
        availableShapeKeys={[]}
        onClose={vi.fn()}
        onSave={onSave}
      />,
    );

    // Type into ID field to set dirty
    fireEvent.change(screen.getByLabelText("ID"), { target: { value: "my-id" } });

    // Click save
    fireEvent.click(screen.getByText("Save"));
    await vi.waitFor(() => expect(onSave).toHaveBeenCalled());

    const [path, params] = onSave.mock.calls[0];
    expect(path).toBe("/0");
    expect(params.creator_id).toBe("my-id");
    expect(params._creatorIdDirty).toBe(true);
  });

  it("omits _creatorIdDirty when ID was not manually edited", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const node = makeNode();
    const creator = makeCreatorInfo({ suggested_id: "wing_{span}" });

    render(
      <EditParamsModal
        open={true}
        node={node}
        nodePath="/0"
        creatorInfo={creator}
        availableShapeKeys={[]}
        onClose={vi.fn()}
        onSave={onSave}
      />,
    );

    // Save without editing ID
    fireEvent.click(screen.getByText("Save"));
    await vi.waitFor(() => expect(onSave).toHaveBeenCalled());

    const [, params] = onSave.mock.calls[0];
    expect(params._creatorIdDirty).toBeUndefined();
  });
});
```

- [ ] **Step 2: Run test to verify it passes**

Run: `cd frontend && npx vitest run __tests__/EditParamsModal.test.tsx`

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/__tests__/EditParamsModal.test.tsx
git commit -m "test(gh-387): add save payload contract tests for EditParamsModal"
```

---

### Task 6: Remove unnecessary Record cast

**Files:**
- Modify: `frontend/components/workbench/construction-plans/EditParamsModal.tsx:56`

- [ ] **Step 1: Simplify the cast**

Change line 56 from:
```tsx
setCreatorIdDirty(!!(node as Record<string, unknown>)._creatorIdDirty);
```
to:
```tsx
setCreatorIdDirty(!!node._creatorIdDirty);
```

- [ ] **Step 2: Run all tests to verify no regressions**

Run: `cd frontend && npx vitest run __tests__/EditParamsModal.test.tsx`

Expected: All tests PASS.

- [ ] **Step 3: Run TypeScript check**

Run: `cd frontend && npx tsc --noEmit`

Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/workbench/construction-plans/EditParamsModal.tsx
git commit -m "refactor(gh-387): remove unnecessary Record cast for _creatorIdDirty"
```

---

### Task 7: Full test suite verification

- [ ] **Step 1: Run entire frontend test suite**

Run: `cd frontend && npm run test:unit -- --run`

Expected: All tests pass, including the new EditParamsModal tests.

- [ ] **Step 2: Run dependency check**

Run: `cd frontend && npm run deps:check`

Expected: No dependency violations.
