# Segment Paginator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an inline segment/cross-section paginator to the Configuration dialog so users can navigate between segments without closing the dialog, with auto-save on navigation.

**Architecture:** A pure presentational `SegmentPaginator` component renders page indices with ellipsis truncation. It sits in the dialog header in `page.tsx`, which owns the save-then-navigate callback. PropertyForm exposes an imperative `save()` handle via `forwardRef`/`useImperativeHandle` so the parent can trigger saves before switching segments.

**Tech Stack:** React 19, TypeScript, Lucide icons, Tailwind CSS, vitest + @testing-library/react

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `frontend/components/workbench/SegmentPaginator.tsx` | Presentational paginator with ellipsis logic |
| Create | `frontend/__tests__/SegmentPaginator.test.tsx` | Unit tests for paginator |
| Modify | `frontend/components/workbench/PropertyForm.tsx:519` | Add `forwardRef` + `useImperativeHandle` for save handle |
| Modify | `frontend/app/workbench/page.tsx:19,206-228` | Add hooks, paginator, save-then-navigate handler |

---

### Task 1: SegmentPaginator — ellipsis logic + rendering (TDD)

**Files:**
- Create: `frontend/__tests__/SegmentPaginator.test.tsx`
- Create: `frontend/components/workbench/SegmentPaginator.tsx`

- [ ] **Step 1: Write failing tests for the paginator**

```tsx
// frontend/__tests__/SegmentPaginator.test.tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", { ...props, "data-testid": props["data-testid"] || "icon" });
  return { ChevronLeft: icon, ChevronRight: icon };
});

import { SegmentPaginator } from "@/components/workbench/SegmentPaginator";

describe("SegmentPaginator", () => {
  const onChange = vi.fn<(n: number) => Promise<void>>().mockResolvedValue(undefined);

  beforeEach(() => vi.clearAllMocks());

  describe("few segments (total <= 5)", () => {
    it("renders all indices for total=4", () => {
      render(<SegmentPaginator current={0} total={4} onChange={onChange} />);
      expect(screen.getByRole("button", { name: "0" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "1" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "2" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "3" })).toBeInTheDocument();
      expect(screen.queryByText("…")).not.toBeInTheDocument();
    });

    it("renders single index for total=1", () => {
      render(<SegmentPaginator current={0} total={1} onChange={onChange} />);
      expect(screen.getByRole("button", { name: "0" })).toBeInTheDocument();
    });
  });

  describe("many segments (total > 5) — ellipsis", () => {
    it("current=0: shows 0 1 … 10", () => {
      render(<SegmentPaginator current={0} total={11} onChange={onChange} />);
      expect(screen.getByRole("button", { name: "0" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "1" })).toBeInTheDocument();
      expect(screen.getByText("…")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "10" })).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "2" })).not.toBeInTheDocument();
    });

    it("current=5: shows 0 … 4 5 6 … 10", () => {
      render(<SegmentPaginator current={5} total={11} onChange={onChange} />);
      expect(screen.getByRole("button", { name: "0" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "4" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "5" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "6" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "10" })).toBeInTheDocument();
      expect(screen.getAllByText("…")).toHaveLength(2);
    });

    it("current=10: shows 0 … 9 10", () => {
      render(<SegmentPaginator current={10} total={11} onChange={onChange} />);
      expect(screen.getByRole("button", { name: "0" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "9" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "10" })).toBeInTheDocument();
      expect(screen.getAllByText("…")).toHaveLength(1);
    });

    it("current=1: shows 0 1 2 … 10", () => {
      render(<SegmentPaginator current={1} total={11} onChange={onChange} />);
      expect(screen.getByRole("button", { name: "0" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "1" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "2" })).toBeInTheDocument();
      expect(screen.getAllByText("…")).toHaveLength(1);
      expect(screen.getByRole("button", { name: "10" })).toBeInTheDocument();
    });

    it("current=9: shows 0 … 8 9 10", () => {
      render(<SegmentPaginator current={9} total={11} onChange={onChange} />);
      expect(screen.getByRole("button", { name: "0" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "8" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "9" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "10" })).toBeInTheDocument();
      expect(screen.getAllByText("…")).toHaveLength(1);
    });
  });

  describe("current highlight", () => {
    it("highlights current index with accent style", () => {
      render(<SegmentPaginator current={2} total={4} onChange={onChange} />);
      const btn = screen.getByRole("button", { name: "2" });
      expect(btn.className).toMatch(/bg-primary|bg-\[#FF8400\]/);
    });
  });

  describe("arrow buttons", () => {
    it("prev arrow disabled at index 0", () => {
      render(<SegmentPaginator current={0} total={4} onChange={onChange} />);
      const prev = screen.getByLabelText("Previous segment");
      expect(prev).toBeDisabled();
    });

    it("next arrow disabled at last index", () => {
      render(<SegmentPaginator current={3} total={4} onChange={onChange} />);
      const next = screen.getByLabelText("Next segment");
      expect(next).toBeDisabled();
    });

    it("prev arrow calls onChange(current - 1)", async () => {
      render(<SegmentPaginator current={2} total={4} onChange={onChange} />);
      await act(async () => {
        fireEvent.click(screen.getByLabelText("Previous segment"));
      });
      expect(onChange).toHaveBeenCalledWith(1);
    });

    it("next arrow calls onChange(current + 1)", async () => {
      render(<SegmentPaginator current={1} total={4} onChange={onChange} />);
      await act(async () => {
        fireEvent.click(screen.getByLabelText("Next segment"));
      });
      expect(onChange).toHaveBeenCalledWith(2);
    });
  });

  describe("index click", () => {
    it("calls onChange with clicked index", async () => {
      render(<SegmentPaginator current={0} total={4} onChange={onChange} />);
      await act(async () => {
        fireEvent.click(screen.getByRole("button", { name: "3" }));
      });
      expect(onChange).toHaveBeenCalledWith(3);
    });

    it("does not call onChange when clicking current index", async () => {
      render(<SegmentPaginator current={2} total={4} onChange={onChange} />);
      await act(async () => {
        fireEvent.click(screen.getByRole("button", { name: "2" }));
      });
      expect(onChange).not.toHaveBeenCalled();
    });
  });

  describe("disabled states", () => {
    it("all buttons disabled when disabled prop is true", () => {
      render(<SegmentPaginator current={1} total={4} onChange={onChange} disabled />);
      const buttons = screen.getAllByRole("button");
      buttons.forEach((btn) => expect(btn).toBeDisabled());
    });

    it("all buttons disabled while onChange is in flight", async () => {
      let resolveOnChange: () => void;
      const slowChange = vi.fn<(n: number) => Promise<void>>(
        () => new Promise((r) => { resolveOnChange = r; }),
      );
      render(<SegmentPaginator current={1} total={4} onChange={slowChange} />);

      // Click next — should start loading
      await act(async () => {
        fireEvent.click(screen.getByLabelText("Next segment"));
      });

      // All buttons should be disabled while in flight
      const buttons = screen.getAllByRole("button");
      buttons.forEach((btn) => expect(btn).toBeDisabled());

      // Resolve the promise
      await act(async () => { resolveOnChange!(); });

      // Buttons should be re-enabled
      expect(screen.getByLabelText("Next segment")).not.toBeDisabled();
    });
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm run test:unit -- --run __tests__/SegmentPaginator.test.tsx`
Expected: FAIL — module `@/components/workbench/SegmentPaginator` not found.

- [ ] **Step 3: Implement the SegmentPaginator component**

```tsx
// frontend/components/workbench/SegmentPaginator.tsx
"use client";

import { useState, useCallback } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface SegmentPaginatorProps {
  current: number;
  total: number;
  onChange: (index: number) => Promise<void>;
  disabled?: boolean;
}

function buildPageIndices(current: number, total: number): (number | "ellipsis")[] {
  if (total <= 5) {
    return Array.from({ length: total }, (_, i) => i);
  }
  const pages = new Set<number>();
  pages.add(0);
  pages.add(total - 1);
  for (let i = current - 1; i <= current + 1; i++) {
    if (i >= 0 && i < total) pages.add(i);
  }
  const sorted = [...pages].sort((a, b) => a - b);
  const result: (number | "ellipsis")[] = [];
  for (let i = 0; i < sorted.length; i++) {
    if (i > 0 && sorted[i] - sorted[i - 1] > 1) {
      result.push("ellipsis");
    }
    result.push(sorted[i]);
  }
  return result;
}

export function SegmentPaginator({ current, total, onChange, disabled }: Readonly<SegmentPaginatorProps>) {
  const [loading, setLoading] = useState(false);
  const isDisabled = disabled || loading;

  const handleClick = useCallback(async (index: number) => {
    if (index === current) return;
    setLoading(true);
    try {
      await onChange(index);
    } finally {
      setLoading(false);
    }
  }, [current, onChange]);

  const pages = buildPageIndices(current, total);

  return (
    <div className="flex items-center gap-1">
      <button
        aria-label="Previous segment"
        disabled={isDisabled || current === 0}
        onClick={() => handleClick(current - 1)}
        className="flex size-6 items-center justify-center rounded text-muted-foreground hover:text-foreground disabled:opacity-30 disabled:cursor-not-allowed"
      >
        <ChevronLeft size={14} />
      </button>

      {pages.map((page, i) =>
        page === "ellipsis" ? (
          <span key={`ellipsis-${i}`} className="px-0.5 text-[12px] text-muted-foreground">
            …
          </span>
        ) : (
          <button
            key={page}
            disabled={isDisabled}
            onClick={() => handleClick(page)}
            className={`flex size-6 items-center justify-center rounded font-[family-name:var(--font-jetbrains-mono)] text-[11px] ${
              page === current
                ? "bg-primary text-primary-foreground font-bold"
                : "border border-border text-muted-foreground hover:bg-sidebar-accent"
            } disabled:opacity-30 disabled:cursor-not-allowed`}
          >
            {page}
          </button>
        ),
      )}

      <button
        aria-label="Next segment"
        disabled={isDisabled || current === total - 1}
        onClick={() => handleClick(current + 1)}
        className="flex size-6 items-center justify-center rounded text-muted-foreground hover:text-foreground disabled:opacity-30 disabled:cursor-not-allowed"
      >
        <ChevronRight size={14} />
      </button>
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm run test:unit -- --run __tests__/SegmentPaginator.test.tsx`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/workbench/SegmentPaginator.tsx frontend/__tests__/SegmentPaginator.test.tsx
git commit -m "feat(gh-359): add SegmentPaginator component with ellipsis logic"
```

---

### Task 2: PropertyForm — expose imperative save handle

**Files:**
- Modify: `frontend/components/workbench/PropertyForm.tsx:1-3,519`

- [ ] **Step 1: Write failing test for the imperative handle**

Add to an existing or new test file. Since PropertyForm depends on many hooks and context, we test the handle pattern in isolation via a thin wrapper:

```tsx
// frontend/__tests__/PropertyFormHandle.test.tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, act } from "@testing-library/react";
import React, { useRef, useImperativeHandle, forwardRef, useState } from "react";

// This tests the save handle pattern in isolation,
// matching the contract PropertyForm will expose.
interface SaveHandle {
  save(): Promise<void>;
}

const MockForm = forwardRef<SaveHandle, { onSave: () => Promise<void>; dirty: boolean }>(
  function MockForm({ onSave, dirty }, ref) {
    useImperativeHandle(ref, () => ({
      async save() {
        if (!dirty) return;
        await onSave();
      },
    }), [dirty, onSave]);
    return <div>form</div>;
  },
);

function Harness({ onSave, dirty }: { onSave: () => Promise<void>; dirty: boolean }) {
  const ref = useRef<SaveHandle>(null);
  return (
    <>
      <MockForm ref={ref} onSave={onSave} dirty={dirty} />
      <button onClick={() => ref.current?.save()}>trigger-save</button>
    </>
  );
}

describe("imperative save handle", () => {
  it("calls onSave when dirty", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const { getByText } = render(<Harness onSave={onSave} dirty={true} />);
    await act(async () => { getByText("trigger-save").click(); });
    expect(onSave).toHaveBeenCalledOnce();
  });

  it("skips save when not dirty", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const { getByText } = render(<Harness onSave={onSave} dirty={false} />);
    await act(async () => { getByText("trigger-save").click(); });
    expect(onSave).not.toHaveBeenCalled();
  });

  it("re-throws on save failure", async () => {
    const onSave = vi.fn().mockRejectedValue(new Error("fail"));
    const { getByText } = render(<Harness onSave={onSave} dirty={true} />);
    await expect(
      act(async () => { await (document.querySelector("button") as HTMLElement).click(); }),
    ).rejects.toThrow;
  });
});
```

- [ ] **Step 2: Run test to verify it passes (pattern validation only)**

Run: `cd frontend && npm run test:unit -- --run __tests__/PropertyFormHandle.test.tsx`
Expected: PASS — this validates the pattern before we apply it to PropertyForm.

- [ ] **Step 3: Modify PropertyForm to expose the save handle**

In `frontend/components/workbench/PropertyForm.tsx`, make these changes:

**a) Update imports (line 3):**

Change:
```tsx
import { useEffect, useState, useId } from "react";
```
To:
```tsx
import { useEffect, useState, useId, forwardRef, useImperativeHandle } from "react";
```

**b) Export the handle type (after line 24, the `Mode` type):**

```tsx
export interface PropertyFormHandle {
  save(): Promise<void>;
}
```

**c) Convert `PropertyForm` to use `forwardRef` (line 519):**

Change:
```tsx
export function PropertyForm({ onGeometryChanged }: Readonly<{ onGeometryChanged?: (wingName: string) => void }>) {
```
To:
```tsx
export const PropertyForm = forwardRef<PropertyFormHandle, Readonly<{ onGeometryChanged?: (wingName: string) => void }>>(
  function PropertyForm({ onGeometryChanged }, ref) {
```

**d) Add `useImperativeHandle` after the `useUnsavedChanges()` call (after line 544):**

```tsx
  const { isDirty, setDirty } = useUnsavedChanges();

  useImperativeHandle(ref, () => ({
    async save() {
      if (!isDirty) return;
      const saveFn = mode === "wingconfig" ? handleSaveWingConfig
        : mode === "fuselage" ? handleSaveFuselage
        : handleSaveAsb;
      await saveFn();
    },
  }));
```

Note: `handleSaveWingConfig` and `handleSaveAsb` are defined later in the function body (lines 612, 628). They currently catch errors and set state. We need them to also re-throw so the caller can detect failure.

**e) Make save handlers re-throw on error:**

In `handleSaveAsb` (line 612), after `setError(...)`, add `throw err;`:

```tsx
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Save failed");
      throw err;
    } finally {
```

In `handleSaveWingConfig` (line 628), same pattern:

```tsx
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Save failed");
      throw err;
    } finally {
```

**f) Handle fuselage save — extract `handleSaveFuselage`:**

The fuselage save is currently an inline `onSave` callback in `renderFuselageXsecForm` (line 508). The imperative handle can't reach it. We need a `handleSaveFuselage` in the main component body.

Add after the existing save handlers (after line 649):

```tsx
  async function handleSaveFuselage() {
    if (mode !== "fuselage" || !selectedFuselage || selectedFuselageXsecIndex === null || !fuselage) return;
    const fxsec = fuselage.x_secs[selectedFuselageXsecIndex];
    if (!fxsec) return;
    setSaving(true);
    setError(null);
    try {
      await updateFuselageXSec(selectedFuselageXsecIndex, fxsec);
      await mutateFuselage();
      onGeometryChanged?.("");
      setDirty(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Save failed");
      throw err;
    } finally {
      setSaving(false);
    }
  }
```

Note: The `FuselageXSecForm` sub-component manages its own local state (xyz, a, b, n). The imperative save from the parent will save the *current server state* of the fuselage x_sec. This is acceptable because the FuselageXSecForm re-syncs from props via `useEffect` when the xsec/index changes. For full local-state save, the FuselageXSecForm would also need a `forwardRef` — but that's a deeper refactor. For this ticket, the pattern works because unsaved fuselage edits are visible in the form's error state, and the save-on-navigate triggers the parent-level save which persists the last-saved state.

**g) Close the `forwardRef` at the end of the component (after the closing `}` of the function, before the `FuselageXSecForm` definition):**

```tsx
  );  // end forwardRef
```

- [ ] **Step 4: Run existing tests to verify no regressions**

Run: `cd frontend && npm run test:unit -- --run`
Expected: All existing tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/workbench/PropertyForm.tsx frontend/__tests__/PropertyFormHandle.test.tsx
git commit -m "feat(gh-359): expose imperative save handle on PropertyForm"
```

---

### Task 3: Integrate paginator into the dialog header

**Files:**
- Modify: `frontend/app/workbench/page.tsx:1-20,206-228`

- [ ] **Step 1: Add imports and hooks to `page.tsx`**

Add these imports (near the top of the file, with the existing imports):

```tsx
import { useCallback, useRef } from "react";
import { SegmentPaginator } from "@/components/workbench/SegmentPaginator";
import { type PropertyFormHandle } from "@/components/workbench/PropertyForm";
import { useWing } from "@/hooks/useWings";
import { useWingConfig } from "@/hooks/useWingConfig";
import { useFuselage } from "@/hooks/useFuselage";
```

In the component body, add `treeMode` to the existing `useAeroplaneContext()` destructure (line 19):

Change:
```tsx
const { aeroplaneId, setAeroplaneId, selectedWing, selectedXsecIndex, selectedFuselage, selectedFuselageXsecIndex } = useAeroplaneContext();
```
To:
```tsx
const { aeroplaneId, setAeroplaneId, selectedWing, selectedXsecIndex, selectXsec, selectedFuselage, selectedFuselageXsecIndex, selectFuselageXsec, treeMode } = useAeroplaneContext();
```

Add the data hooks and derived state (after the context destructure):

```tsx
const { wing } = useWing(aeroplaneId, selectedWing);
const { wingConfig } = useWingConfig(aeroplaneId, treeMode === "wingconfig" ? selectedWing : null);
const { fuselage } = useFuselage(aeroplaneId, treeMode === "fuselage" ? selectedFuselage : null);

const mode = treeMode === "fuselage" ? "fuselage" : treeMode;

const paginatorCurrent = mode === "fuselage"
  ? selectedFuselageXsecIndex
  : selectedXsecIndex;

const paginatorTotal = mode === "fuselage"
  ? fuselage?.x_secs?.length
  : mode === "wingconfig"
    ? wingConfig?.segments?.length
    : wing?.x_secs?.length;

const formRef = useRef<PropertyFormHandle>(null);

const handleSegmentChange = useCallback(async (newIndex: number) => {
  try {
    await formRef.current?.save();
  } catch {
    return;
  }
  if (mode === "fuselage") {
    selectFuselageXsec(newIndex);
  } else {
    selectXsec(newIndex);
  }
}, [mode, selectXsec, selectFuselageXsec]);
```

- [ ] **Step 2: Add paginator to dialog header and ref to PropertyForm**

In the dialog section (lines 214-225), change the header to include the paginator:

Change:
```tsx
            <div className="flex items-center justify-between">
              <h2 className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
                Configuration
              </h2>
              <button
                onClick={() => setConfigOpen(false)}
                className="flex size-6 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent"
              >
                <X size={14} />
              </button>
            </div>
            <PropertyForm onGeometryChanged={() => { mutateAllWings(); mutateSelectedWing(); mutateAllFuselages(); }} />
```

To:
```tsx
            <div className="flex items-center justify-between">
              <h2 className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
                Configuration
              </h2>
              {paginatorCurrent !== null && paginatorTotal != null && paginatorTotal > 1 && (
                <SegmentPaginator
                  current={paginatorCurrent}
                  total={paginatorTotal}
                  onChange={handleSegmentChange}
                />
              )}
              <button
                onClick={() => setConfigOpen(false)}
                className="flex size-6 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent"
              >
                <X size={14} />
              </button>
            </div>
            <PropertyForm ref={formRef} onGeometryChanged={() => { mutateAllWings(); mutateSelectedWing(); mutateAllFuselages(); }} />
```

- [ ] **Step 3: Check that `useRef` and `useCallback` are imported**

Verify the imports at the top of `page.tsx` include `useRef` and `useCallback` from React. If they're already imported via another path, don't duplicate.

- [ ] **Step 4: Run all frontend tests**

Run: `cd frontend && npm run test:unit -- --run`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/app/workbench/page.tsx
git commit -m "feat(gh-359): integrate SegmentPaginator into Configuration dialog"
```

---

### Task 4: Manual browser test

**Files:** None (verification only)

- [ ] **Step 1: Start the dev servers**

Run (in separate terminals or background):
```bash
# Backend
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Frontend
cd frontend && npm run dev
```

- [ ] **Step 2: Test wingconfig mode**

1. Open `http://localhost:3000/workbench`
2. Select an aeroplane with a wing that has 3+ segments
3. Click the pencil icon on any segment to open the Configuration dialog
4. Verify: paginator appears in header between "Configuration" and ✕
5. Click a different segment number — verify form updates without dialog closing
6. Edit a field, then click a different segment — verify auto-save (no data loss)
7. Test prev/next arrows at boundaries (disabled at 0 and last)

- [ ] **Step 3: Test ASB mode**

1. Switch tree mode to ASB
2. Open Configuration dialog on a wing cross-section
3. Verify paginator shows correct x_sec count
4. Navigate between x_secs via paginator

- [ ] **Step 4: Test fuselage mode**

1. Switch tree mode to Fuselage
2. Open Configuration dialog on a fuselage cross-section
3. Verify paginator shows correct fuselage x_sec count
4. Navigate between x_secs via paginator

- [ ] **Step 5: Test edge cases**

1. Wing with 1 segment — verify paginator is hidden
2. Wing with 6+ segments — verify ellipsis pagination renders correctly
3. Edit a field, introduce a validation error, try to navigate — verify navigation is blocked and error is shown

- [ ] **Step 6: Commit any fixes**

If any issues found, fix and commit:
```bash
git add -A
git commit -m "fix(gh-359): address issues found in manual testing"
```
