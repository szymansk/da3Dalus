# Segment Paginator — Design Spec

**Issue:** GH#359  
**Status:** Design approved  
**Scope:** All Configuration dialogs in the Construction view (wingconfig, ASB, fuselage)

## Problem

When editing segment/cross-section properties in the Configuration dialog, users must close the dialog, select a different segment in the component tree, and reopen the dialog. With many segments this is tedious and breaks the editing flow.

## Solution

Add a `SegmentPaginator` component to the Configuration dialog header that lets users navigate between segments/cross-sections inline, with auto-save on navigation.

## Component: `SegmentPaginator`

**File:** `frontend/components/workbench/SegmentPaginator.tsx`

### Interface

```tsx
interface SegmentPaginatorProps {
  current: number;
  total: number;
  onChange: (index: number) => Promise<void>;
  disabled?: boolean;
}
```

### Presentation

- Pure, stateless presentation component (plus internal loading state for async onChange).
- `current` highlighted with orange accent (`#FF8400`), inactive indices use `border-border` + `text-muted-foreground`.
- Prev/next arrows: Lucide `ChevronLeft`/`ChevronRight`.
- Prev disabled at index 0; next disabled at last index.
- All buttons disabled while `onChange` promise is in flight (dimmed appearance).
- Uses JetBrains Mono font, consistent with dialog header.

### Ellipsis algorithm

- `total <= 5`: show all indices `0..total-1`.
- `total > 5`: always show first (0) and last (total-1), plus a ±1 window around `current`, with `…` filling gaps.

Examples for `total=11`:
- `current=0` → `0 1 … 10`
- `current=1` → `0 1 2 … 10`
- `current=5` → `0 … 4 5 6 … 10`
- `current=9` → `0 … 8 9 10`
- `current=10` → `0 … 9 10`

## Integration in `page.tsx`

### Placement

Between the `<h2>Configuration</h2>` title and the close `<button>` in the dialog header flex row (line 214). The header is `flex items-center justify-between` in a 480px dialog.

### Mode-aware props

`page.tsx` currently destructures `selectedXsecIndex`, `selectedFuselageXsecIndex` from `useAeroplaneContext()` but does not import `treeMode` or the data hooks. The implementation must:

1. Add `treeMode` to the `useAeroplaneContext()` destructure in `page.tsx`.
2. Add `useWing`, `useWingConfig`, and `useFuselage` hook calls (same pattern as PropertyForm) to derive `total`. These hooks are already imported/used by PropertyForm, so the data is already fetched by SWR — no extra network calls.

```tsx
const { treeMode } = useAeroplaneContext();
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
```

Paginator renders only when `paginatorCurrent !== null && paginatorTotal != null && paginatorTotal > 1`.

### Save-then-navigate handler

```tsx
const handleSegmentChange = useCallback(async (newIndex: number) => {
  try {
    await formRef.current.save();
  } catch {
    return; // save failed → stay on current segment
  }
  if (mode === "fuselage") {
    selectFuselageXsec(newIndex);
  } else {
    selectXsec(newIndex);
  }
}, [mode, selectXsec, selectFuselageXsec]);
```

## PropertyForm: imperative save handle

**Pattern:** `forwardRef` + `useImperativeHandle` to expose `save(): Promise<void>`.

```tsx
export interface PropertyFormHandle {
  save(): Promise<void>;
}
```

- `save()` reuses the existing save handlers (`handleSaveWingConfig`, `handleSaveAsb`, fuselage save).
- If the form is not dirty, `save()` resolves immediately (no network call).
- On failure, `save()` sets the existing `error` state AND re-throws so the caller knows navigation should be blocked.
- The dialog creates a `formRef = useRef<PropertyFormHandle>(null)` and passes it to PropertyForm.

## Auto-save flow

1. User clicks paginator index `N` (or arrow).
2. Paginator sets internal `loading = true`, disables all buttons.
3. Paginator calls `await onChange(N)`.
4. Parent calls `await formRef.current.save()`.
   - **Not dirty:** resolves immediately.
   - **Success:** proceeds to step 5.
   - **Failure:** throws → parent returns without navigating → PropertyForm shows error → paginator re-enables.
5. Parent calls `selectXsec(N)` or `selectFuselageXsec(N)`.
6. PropertyForm re-renders with new segment data.
7. Paginator `finally` sets `loading = false`.

## Codebase references

| File | Lines | Role |
|------|-------|------|
| `frontend/app/workbench/page.tsx` | 206–228 | Dialog container; header at 214–224 |
| `frontend/app/workbench/page.tsx` | 139 | Dialog open trigger (`onNodeEdit`) |
| `frontend/components/workbench/PropertyForm.tsx` | 519–711 | Form component; save handlers |
| `frontend/components/workbench/PropertyForm.tsx` | 651 | Mode-based save dispatch |
| `frontend/components/workbench/AeroplaneContext.tsx` | 16–29 | Context type: `selectXsec`, `selectFuselageXsec` |
| `frontend/hooks/useWingConfig.ts` | 6–66 | `wingConfig.segments[]` |

## Test plan

### Unit: `SegmentPaginator.test.tsx`

- Renders all indices for total ≤ 5
- Renders ellipsis format for total > 5
- Highlights current index (orange accent)
- Prev disabled at 0, next disabled at last
- Calls `onChange` with correct index on click
- Window slides correctly at edges (0, 1, total-2, total-1)
- All buttons disabled when `disabled={true}`
- All buttons disabled while `onChange` promise in flight

### Integration

- Paginator appears in wingconfig mode with correct segment count
- Paginator appears in ASB mode with correct x_sec count
- Paginator appears in fuselage mode with correct x_sec count
- Paginator hidden when only 1 segment/x_sec
- Auto-save triggered before navigation
- Navigation blocked on save failure, error displayed
- Clean navigation (not dirty) skips save call

## Scope — out of scope

- Keyboard navigation (arrow keys) — future enhancement
- Drag-to-reorder segments — unrelated feature
- Segment add/delete from paginator — navigation-only
- Unsaved changes warning dialog — replaced by auto-save

## Changes vs GH#359

- **Extended to all three modes** (wingconfig, ASB, fuselage) — original spec was wing-only.
- **Added auto-save on navigation** — original spec deferred this.
- **Added imperative save handle** on PropertyForm — required for auto-save integration.
