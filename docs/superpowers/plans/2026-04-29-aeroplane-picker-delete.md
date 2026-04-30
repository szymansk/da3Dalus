# Aeroplane Picker & Delete Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify aeroplane selection into a single modal dialog across all workbench tabs, and add delete capability to it.

**Architecture:** Add `pickerOpen` / `openPicker` / `closePicker` state to `AeroplaneContext` so that Header and all tab pages share a single modal trigger. Enhance `AeroplanePickerDialog` with delete buttons (+ confirmation) and a create button. Render the dialog once in `layout.tsx` rather than per-page. Each tab page's no-aeroplane guard calls `openPicker()` via an effect. Remove the inline `AeroplaneSelector` from the Construction page.

**Tech Stack:** React 19, Next.js App Router, Tailwind CSS, lucide-react, SWR

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `frontend/components/workbench/AeroplaneContext.tsx` | Modify | Add `pickerOpen`, `openPicker`, `closePicker` to context |
| `frontend/components/workbench/construction-plans/AeroplanePickerDialog.tsx` | Modify | Add delete button per row, confirmation dialog, create button, `onDelete`/`onCreate` props |
| `frontend/app/workbench/layout.tsx` | Modify | Render `AeroplanePickerDialog` once, wired to context |
| `frontend/components/workbench/Header.tsx` | Modify | Call `openPicker()` instead of `setAeroplaneId(null)` |
| `frontend/app/workbench/page.tsx` | Modify | Remove `AeroplaneSelector`, add `useEffect` to open picker when no aeroplane |
| `frontend/app/workbench/analysis/page.tsx` | Modify | Add `useEffect` to open picker when no aeroplane |
| `frontend/app/workbench/construction-plans/page.tsx` | Modify | Replace text placeholder with `useEffect` to open picker |

---

### Task 1: Add picker state to AeroplaneContext

**Files:**
- Modify: `frontend/components/workbench/AeroplaneContext.tsx`

- [ ] **Step 1: Add `pickerOpen`, `openPicker`, `closePicker` to the context interface and provider**

Add three new fields to `AeroplaneContextValue`:

```typescript
pickerOpen: boolean;
openPicker: () => void;
closePicker: () => void;
```

In `AeroplaneProvider`, add state and callbacks:

```typescript
const [pickerOpen, setPickerOpen] = useState(false);
const openPicker = useCallback(() => setPickerOpen(true), []);
const closePicker = useCallback(() => setPickerOpen(false), []);
```

Add `pickerOpen`, `openPicker`, `closePicker` to both the `ctxValue` memo object and its dependency array.

- [ ] **Step 2: Verify the app still compiles**

Run: `cd frontend && npx next build 2>&1 | head -30`
Expected: No type errors related to AeroplaneContext (existing consumers don't use the new fields yet).

- [ ] **Step 3: Commit**

```bash
git add frontend/components/workbench/AeroplaneContext.tsx
git commit -m "feat(gh-370): add picker state to AeroplaneContext"
```

---

### Task 2: Enhance AeroplanePickerDialog with delete and create

**Files:**
- Modify: `frontend/components/workbench/construction-plans/AeroplanePickerDialog.tsx`

- [ ] **Step 1: Add `onDelete`, `onCreate`, and `selectedAeroplaneId` props**

Update the props interface:

```typescript
interface AeroplanePickerDialogProps {
  open: boolean;
  aeroplanes: Aeroplane[];
  title: string;
  selectedAeroplaneId?: string | null;
  onClose: () => void;
  onSelect: (aeroplaneId: string) => Promise<void> | void;
  onDelete?: (aeroplaneId: string) => Promise<void>;
  onCreate?: (name: string) => Promise<void>;
}
```

- [ ] **Step 2: Add confirmation state and delete handler**

Inside the component, add state for the delete confirmation:

```typescript
const [confirmDelete, setConfirmDelete] = useState<Aeroplane | null>(null);
```

Add a handler:

```typescript
async function handleDelete() {
  if (!confirmDelete || !onDelete) return;
  setSubmitting(true);
  try {
    await onDelete(confirmDelete.id);
    setConfirmDelete(null);
  } catch (err) {
    alert(`Failed to delete: ${err instanceof Error ? err.message : String(err)}`);
  } finally {
    setSubmitting(false);
  }
}
```

- [ ] **Step 3: Add delete icon button to each aeroplane row**

Import `Trash2` from lucide-react. Replace the existing row button with a `div` containing the name button and a delete icon:

```tsx
filtered.map((a) => (
  <div
    key={a.id}
    className="group flex items-center gap-1 rounded-lg hover:bg-sidebar-accent"
  >
    <button
      type="button"
      disabled={submitting}
      onClick={() => handlePick(a.id)}
      className="flex flex-1 items-center px-3 py-2 text-left text-[13px] text-foreground disabled:opacity-50"
    >
      <span className="font-[family-name:var(--font-jetbrains-mono)]">
        {a.name}
      </span>
    </button>
    {onDelete && (
      <button
        type="button"
        disabled={submitting}
        onClick={(e) => { e.stopPropagation(); setConfirmDelete(a); }}
        className="mr-2 flex size-6 items-center justify-center rounded-md text-muted-foreground opacity-0 transition-opacity hover:bg-red-500/20 hover:text-red-400 group-hover:opacity-100 disabled:opacity-50"
        title={`Delete ${a.name}`}
      >
        <Trash2 size={14} />
      </button>
    )}
  </div>
))
```

- [ ] **Step 4: Add confirmation dialog overlay**

After the aeroplane list `div`, before the closing `</div>` of the body section, add the confirmation overlay. It renders inside the same dialog card when `confirmDelete` is set:

```tsx
{confirmDelete && (
  <div className="flex flex-col gap-3 rounded-xl border border-red-500/30 bg-red-500/10 p-4">
    <p className="text-[13px] text-foreground">
      Delete <strong>{confirmDelete.name}</strong>? This action cannot be undone.
    </p>
    <div className="flex gap-2">
      <button
        type="button"
        disabled={submitting}
        onClick={() => setConfirmDelete(null)}
        className="flex-1 rounded-lg border border-border px-3 py-2 text-[13px] text-foreground hover:bg-sidebar-accent disabled:opacity-50"
      >
        Cancel
      </button>
      <button
        type="button"
        disabled={submitting}
        onClick={handleDelete}
        className="flex-1 rounded-lg bg-red-600 px-3 py-2 text-[13px] text-white hover:bg-red-700 disabled:opacity-50"
      >
        Delete
      </button>
    </div>
  </div>
)}
```

- [ ] **Step 5: Add "+ Create New" button**

After the confirmation section (or after the list if no confirmation), add a create button in the footer area. Add a `handleCreate` function:

```typescript
async function handleCreate() {
  if (!onCreate) return;
  const name = window.prompt("Aeroplane name?");
  if (!name) return;
  setSubmitting(true);
  try {
    await onCreate(name);
  } catch (err) {
    alert(`Failed to create: ${err instanceof Error ? err.message : String(err)}`);
  } finally {
    setSubmitting(false);
  }
}
```

Add a footer section after the body div, before the closing card div:

```tsx
{onCreate && (
  <div className="border-t border-border px-6 py-4">
    <button
      type="button"
      disabled={submitting}
      onClick={handleCreate}
      className="w-full rounded-full bg-primary px-4 py-2.5 text-[13px] text-primary-foreground hover:opacity-90 disabled:opacity-50"
    >
      + Create New
    </button>
  </div>
)}
```

- [ ] **Step 6: Verify the component compiles**

Run: `cd frontend && npx next build 2>&1 | head -30`
Expected: No errors (new props are optional, existing callers unchanged).

- [ ] **Step 7: Commit**

```bash
git add frontend/components/workbench/construction-plans/AeroplanePickerDialog.tsx
git commit -m "feat(gh-370): add delete and create to AeroplanePickerDialog"
```

---

### Task 3: Render picker dialog in layout and wire to context

**Files:**
- Modify: `frontend/app/workbench/layout.tsx`

- [ ] **Step 1: Import dependencies and render AeroplanePickerDialog in layout**

The layout needs to be a client component to access context. However, layout.tsx currently doesn't use `"use client"`. Since `AeroplaneProvider` is already a client component, we need a small wrapper.

Create a client component `WorkbenchPickerHost` inline in `layout.tsx` — or better, since layout.tsx already imports client components and wraps everything in `AeroplaneProvider`, add a new child component.

Actually, looking at the layout: it renders `Header` (a client component) and `children` inside the `AeroplaneProvider`. The layout itself is a server component. The simplest approach: create a small client component that renders the dialog.

Add a new file `frontend/components/workbench/AeroplanePickerHost.tsx`:

```tsx
"use client";

import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { useAeroplanes } from "@/hooks/useAeroplanes";
import { AeroplanePickerDialog } from "@/components/workbench/construction-plans/AeroplanePickerDialog";

export function AeroplanePickerHost() {
  const { aeroplaneId, setAeroplaneId, pickerOpen, closePicker } = useAeroplaneContext();
  const { aeroplanes, createAeroplane, deleteAeroplane } = useAeroplanes();

  return (
    <AeroplanePickerDialog
      open={pickerOpen}
      aeroplanes={aeroplanes}
      title="Select Aeroplane"
      selectedAeroplaneId={aeroplaneId}
      onClose={closePicker}
      onSelect={async (id) => {
        setAeroplaneId(id);
        closePicker();
      }}
      onDelete={async (id) => {
        await deleteAeroplane(id);
        if (id === aeroplaneId) {
          setAeroplaneId(null);
        }
      }}
      onCreate={async (name) => {
        const created = await createAeroplane(name);
        setAeroplaneId(created.id);
        closePicker();
      }}
    />
  );
}
```

- [ ] **Step 2: Add AeroplanePickerHost to layout.tsx**

In `layout.tsx`, import and render the host inside the `AeroplaneProvider`, after `UnsavedChangesModal`:

```tsx
import { AeroplanePickerHost } from "@/components/workbench/AeroplanePickerHost";
```

Add `<AeroplanePickerHost />` after `<UnsavedChangesModal />` inside the `UnsavedChangesProvider`.

- [ ] **Step 3: Verify the app compiles**

Run: `cd frontend && npx next build 2>&1 | head -30`
Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/workbench/AeroplanePickerHost.tsx frontend/app/workbench/layout.tsx
git commit -m "feat(gh-370): render AeroplanePickerDialog in workbench layout"
```

---

### Task 4: Header opens picker instead of clearing selection

**Files:**
- Modify: `frontend/components/workbench/Header.tsx`

- [ ] **Step 1: Update Header to use `openPicker`**

In `Header.tsx`, destructure `openPicker` from `useAeroplaneContext()` instead of (or in addition to) `setAeroplaneId`:

Change the destructuring on line 34 from:
```typescript
const { aeroplaneId, selectedWing, selectedXsecIndex, setAeroplaneId } = useAeroplaneContext();
```
to:
```typescript
const { aeroplaneId, selectedWing, selectedXsecIndex, openPicker } = useAeroplaneContext();
```

Change the button's `onClick` on line 43 from:
```typescript
onClick={() => setAeroplaneId(null)}
```
to:
```typescript
onClick={openPicker}
```

- [ ] **Step 2: Verify the app compiles**

Run: `cd frontend && npx next build 2>&1 | head -30`
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/workbench/Header.tsx
git commit -m "feat(gh-370): Header opens picker modal instead of clearing selection"
```

---

### Task 5: Construction page — replace inline AeroplaneSelector with picker effect

**Files:**
- Modify: `frontend/app/workbench/page.tsx`

- [ ] **Step 1: Remove the `AeroplaneSelector` component and its usage**

Delete the entire `AeroplaneSelector` function (lines 315–373).

Replace the no-aeroplane guard block (lines 149–158) with an effect that opens the picker. Add `useEffect` to the imports and `openPicker` to the context destructuring:

Add to the destructuring at the top of `WorkbenchPage`:
```typescript
const {
  aeroplaneId, setAeroplaneId,
  selectedWing, selectedXsecIndex, selectXsec,
  selectedFuselage, selectedFuselageXsecIndex, selectFuselageXsec,
  treeMode,
  openPicker,
} = useAeroplaneContext();
```

Add `useEffect` to the React import. Then add this effect after the hooks section (after `mutateAllFuselages` line):

```typescript
useEffect(() => {
  if (!aeroplaneId) openPicker();
}, [aeroplaneId, openPicker]);
```

Replace the guard block:
```typescript
if (!aeroplaneId) {
  return <AeroplaneSelector ... />;
}
```
with:
```typescript
if (!aeroplaneId) {
  return (
    <div className="flex flex-1 items-center justify-center">
      <span className="text-[13px] text-muted-foreground">No aeroplane selected</span>
    </div>
  );
}
```

Remove `createAeroplane` from the `useAeroplanes()` destructuring since it's no longer used on this page (only `aeroplanes` and `isLoading` remain — check if they're still used; `aeroplanes` is used for `aeroplaneName` lookup, `isLoading` is not used anymore). Clean up unused imports.

- [ ] **Step 2: Verify the app compiles**

Run: `cd frontend && npx next build 2>&1 | head -30`
Expected: No errors, no reference to `AeroplaneSelector`.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/workbench/page.tsx
git commit -m "feat(gh-370): Construction page uses modal picker, remove AeroplaneSelector"
```

---

### Task 6: Analysis page — add no-aeroplane guard with picker

**Files:**
- Modify: `frontend/app/workbench/analysis/page.tsx`

- [ ] **Step 1: Add effect to open picker when no aeroplane selected**

Add `useEffect` to the React import. Destructure `openPicker` from context:

```typescript
const { aeroplaneId, selectedWing, openPicker } = useAeroplaneContext();
```

Add the effect after hooks:

```typescript
useEffect(() => {
  if (!aeroplaneId) openPicker();
}, [aeroplaneId, openPicker]);
```

Add an early return guard before the main JSX return:

```typescript
if (!aeroplaneId) {
  return (
    <div className="flex flex-1 items-center justify-center">
      <span className="text-[13px] text-muted-foreground">No aeroplane selected</span>
    </div>
  );
}
```

- [ ] **Step 2: Verify the app compiles**

Run: `cd frontend && npx next build 2>&1 | head -30`
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/workbench/analysis/page.tsx
git commit -m "feat(gh-370): Analysis page opens picker when no aeroplane selected"
```

---

### Task 7: Plans page — replace text placeholder with picker

**Files:**
- Modify: `frontend/app/workbench/construction-plans/page.tsx`

- [ ] **Step 1: Add effect to open picker when no aeroplane selected**

Add `useEffect` to the React import at the top of the file. Import `openPicker` from context — find where `useAeroplaneContext` is destructured and add `openPicker`:

```typescript
const { aeroplaneId, openPicker } = useAeroplaneContext();
```

Add the effect (place it near other effects in the file):

```typescript
useEffect(() => {
  if (!aeroplaneId) openPicker();
}, [aeroplaneId, openPicker]);
```

Replace the existing no-aeroplane guard (lines 465–472):
```typescript
if (!aeroplaneId) {
  return (
    <div className="flex flex-1 items-center justify-center">
      <p className="text-[13px] text-muted-foreground">
        Select an aeroplane to view its construction plans.
      </p>
    </div>
  );
}
```
with:
```typescript
if (!aeroplaneId) {
  return (
    <div className="flex flex-1 items-center justify-center">
      <span className="text-[13px] text-muted-foreground">No aeroplane selected</span>
    </div>
  );
}
```

- [ ] **Step 2: Check if Plans page has its own `AeroplanePickerDialog` usage to remove**

The Plans page uses `AeroplanePickerDialog` for template execution (picking which aeroplane to apply a template to). This is a *different* use case — keep it. It has its own `open` state and `onSelect` handler for templates, not for the global aeroplane selection.

- [ ] **Step 3: Verify the app compiles**

Run: `cd frontend && npx next build 2>&1 | head -30`
Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/workbench/construction-plans/page.tsx
git commit -m "feat(gh-370): Plans page opens picker when no aeroplane selected"
```

---

### Task 8: Manual browser verification

- [ ] **Step 1: Start the dev server**

Run: `cd frontend && npm run dev`

- [ ] **Step 2: Verify golden path**

1. Navigate to `/workbench` with no aeroplane selected → modal picker opens automatically
2. Create a new aeroplane via "+ Create New" → modal closes, aeroplane is selected
3. Click the aeroplane name button in the Header → modal opens (aeroplane remains selected until you pick another)
4. Navigate to Analysis tab → if no aeroplane selected, modal opens
5. Navigate to Plans tab → if no aeroplane selected, modal opens
6. In the picker, hover over an aeroplane row → trash icon appears
7. Click trash → confirmation panel shows with "Cancel" and "Delete" buttons
8. Click "Cancel" → confirmation disappears
9. Click trash again, then "Delete" → aeroplane is deleted, row disappears
10. Delete the currently-selected aeroplane → selection clears, picker stays open

- [ ] **Step 3: Verify edge cases**

1. Search filter in picker still works
2. Deleting the last aeroplane → list shows "No aeroplanes found", "+ Create New" still visible
3. Clicking backdrop closes the picker (unless no aeroplane selected — user must pick one)
4. Plans page template picker still works independently
