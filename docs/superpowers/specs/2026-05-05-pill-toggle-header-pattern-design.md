# GH-405: Apply Global UI Pattern — Toggle Button in Header Row

## Problem

The "2 - Construction" tab uses a different layout for its
Segments/X-Secs toggle than the established pattern in the
"4 - Components" tab. The toggle is buried inside the AeroplaneTree
component header, styled differently, and positioned on the right
side of the tree header. There is no "Configuration" heading above
the preview area.

The goal is to enforce a consistent UI pattern across all workbench
tabs: **toggle on the left in the header row, heading on the right
above the content area.**

## Approach

Extract the inline toggle pattern into a shared `PillToggle`
component, apply it to the Construction tab with the correct layout,
and retrofit the Components and Construction Plans tabs to use the
same shared component.

## Design

### 1. PillToggle Component

**File:** `frontend/components/ui/PillToggle.tsx`

A generic, reusable pill-shaped toggle group.

**API:**

```tsx
interface PillToggleOption<T extends string> {
  value: T;
  label: string;
  icon: LucideIcon;
}

interface PillToggleProps<T extends string> {
  options: PillToggleOption<T>[];
  value: T;
  onChange: (value: T) => void;
  isActive?: (optionValue: T, currentValue: T) => boolean;
}
```

**Styling (matches existing Components tab inline pattern):**

- Container: `rounded-full border border-border bg-card p-1`,
  with `gap-1` between buttons
- Button: `rounded-full px-3 py-1.5 text-[12px]`, with `gap-1.5`
  between icon and label, JetBrains Mono font
- Active: `bg-primary text-primary-foreground`
- Inactive: `text-muted-foreground hover:text-foreground`
- Icon size: 12px
- Transition: `transition-colors`

### 2. Construction Tab Layout Changes

**File:** `frontend/app/workbench/page.tsx`

Add a header row above the existing two-panel layout:

- **Left side:** `<PillToggle>` with two options:
  - Segments — `GalleryHorizontal` icon, value `"wingconfig"`
  - X-Secs — `GalleryHorizontalEnd` icon, value `"asb"`
  - Wired to `treeMode`/`setTreeMode` from `AeroplaneContext`
- **Right side:** Heading "Configuration" with `Plane` icon
  - Icon: `size-5 text-primary`
  - Text: `text-[20px]` JetBrains Mono, `text-foreground`
  - Same styling as "Component Library" heading in Components tab

The X-Secs option maps to the `"asb"` tree mode. When `treeMode`
is `"fuselage"` (set by clicking a fuselage in the tree), the
X-Secs button should appear active (matching current behavior where
`treeMode === "asb" || treeMode === "fuselage"` triggers the active
state). This is handled via the optional `isActive` prop on
`PillToggle` — default behavior is `optionValue === currentValue`,
but the Construction tab passes a custom comparator:
`(opt, cur) => opt === cur || (opt === "asb" && cur === "fuselage")`.

**File:** `frontend/components/workbench/AeroplaneTree.tsx`

Remove the Segments/X-Secs toggle from the tree component header
(the `<div>` containing the two toggle buttons). The tree header
retains its collapse button and "Aeroplane Tree" label.

### 3. Retrofit Existing Tabs

**Components tab** (`frontend/app/workbench/components/page.tsx`):

Replace the inline toggle JSX with `<PillToggle>`:
- Library — `Package` icon, value `"library"`
- Construction Parts — `Box` icon, value `"construction"`

No other changes to this file.

**Construction Plans tab**
(`frontend/app/workbench/construction-plans/page.tsx`):

Replace the local `ModeButton` component and its usage with
`<PillToggle>`:
- Plans — `Hammer` icon, value `"plans"`
- Templates — `BookTemplate` icon, value `"templates"`

Delete the `ModeButton` function.

### 4. Testing

**New test:** `frontend/__tests__/PillToggle.test.tsx`

- Renders all options with correct labels
- Active option has `bg-primary` class
- Clicking inactive option calls `onChange` with correct value
- Clicking active option still calls `onChange`

**Existing tests:** No changes expected — the refactor preserves
identical visual output and behavior. If any tests reference
inline toggle markup, they will be updated to match the new
component structure.

**E2E:** No changes — toggle buttons keep the same visible text
labels for Playwright selectors.

## Acceptance Criteria

1. The Segments/X-Secs toggle in the Construction tab is positioned
   in the header row (left side), matching the Components tab layout
2. Toggle buttons have icons: `GalleryHorizontal` for Segments,
   `GalleryHorizontalEnd` for X-Secs
3. "Configuration" heading with `Plane` icon appears above the
   preview area (right side of header row)
4. A shared `PillToggle` component is used by all three tabs
5. All existing unit and E2E tests pass
6. New unit tests cover the `PillToggle` component

## Files Changed

| File | Change |
|------|--------|
| `frontend/components/ui/PillToggle.tsx` | New shared component |
| `frontend/__tests__/PillToggle.test.tsx` | New unit tests |
| `frontend/app/workbench/page.tsx` | Add header row with toggle + heading |
| `frontend/components/workbench/AeroplaneTree.tsx` | Remove toggle from tree header |
| `frontend/app/workbench/components/page.tsx` | Replace inline toggle with PillToggle |
| `frontend/app/workbench/construction-plans/page.tsx` | Replace ModeButton with PillToggle |
