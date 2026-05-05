# Spec: GH-405 — Apply Global UI Patterns to Construction Tab Toggle

## Problem

The "Segments / X-Secs" toggle in the Construction tab (`AeroplaneTree.tsx`)
uses a smaller, inconsistent style compared to the "Library / Construction
Parts" toggle in the Components tab. The heading says "Aeroplane Tree"
instead of "Configuration".

## Solution

Restyle the existing toggle and heading in `AeroplaneTree.tsx` to match
the Components tab pattern exactly.

## Changes

### 1. Heading (line 819-821)

**Before:** `Aeroplane Tree` (plain text, muted)
**After:** `Plane` icon (size 14, text-primary) + `Configuration` (text-foreground, text-[13px])

### 2. Toggle Container (line 823)

**Before:** `rounded-full border border-primary/60 bg-card-muted p-0.5`
**After:** `rounded-full border border-border bg-card p-1`

### 3. Toggle Buttons (lines 824-843)

**Before:** `px-3.5 py-0.5 text-[10px]` (text only, no icons)
**After:** `flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[12px]` with icons:
- Segments: `GalleryHorizontal` (size 12)
- X-Secs: `GalleryHorizontalEnd` (size 12)

### 4. Imports

Add: `Plane`, `GalleryHorizontal`, `GalleryHorizontalEnd` from `lucide-react`

## Acceptance Criteria

- [ ] Toggle visually matches the Components tab pattern (same sizing, colors, rounded pill)
- [ ] Segments button has gallery-horizontal icon
- [ ] X-Secs button has gallery-horizontal-end icon
- [ ] Heading reads "Configuration" with plane icon
- [ ] No functional/logic changes — toggle still switches between wingconfig/asb modes
- [ ] Dark theme renders correctly

## Out of Scope

- Moving the toggle to a different position in the DOM
- Changing toggle behavior or state management
- Other UI pattern alignment tasks
