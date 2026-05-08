# Stability Overlay Design Spec

**Issue:** #423 — Display NP, static margin range, and proposed CG on design configuration preview
**Date:** 2026-05-08
**Prerequisites:** #421 (NP + static margin — merged), #420 (CG assumptions — merged)

## Summary

Add a "Stability" tab to the Analysis page that shows a 2D side-view
schematic with longitudinal stability markers: neutral point (NP),
center of gravity (CG), reference point (x_ref), CG range band, and
mean aerodynamic chord (MAC). Clicking a marker shows detail info.

## Backend

**No backend changes required.** All data is already available:

- `GET /v2/aeroplanes/{id}/stability` returns `StabilityResultRead`
  with: `neutral_point_x`, `cg_x_used`, `mac`, `static_margin_pct`,
  `stability_class`, `cg_range_forward`, `cg_range_aft`, `status`,
  `Cma`, `Cnb`, `Clb`, `is_statically_stable`, etc.
- `GET /v2/aeroplanes/{id}/assumptions` returns CG assumption with
  `estimate_value`, `calculated_value`, `active_source`.
- `POST /v2/aeroplanes/{id}/stability_summary/{tool}` triggers fresh
  stability computation (already exists).

## Frontend

### New Files

| File | Purpose |
|------|---------|
| `frontend/hooks/useStability.ts` | SWR/fetch hook for cached stability data |
| `frontend/components/workbench/StabilityPanel.tsx` | Container panel with toolbar and sub-views |
| `frontend/components/workbench/StabilitySideView.tsx` | Plotly 2D schematic with markers |
| `frontend/components/workbench/MarkerDetailBox.tsx` | Detail popup on marker click |

### Modified Files

| File | Change |
|------|--------|
| `frontend/components/workbench/AnalysisViewerPanel.tsx` | Add "Stability" to TABS, render StabilityPanel |
| `frontend/app/workbench/analysis/page.tsx` | Wire useStability hook, pass data to AnalysisViewerPanel |

### useStability Hook

Follows the `useFlightEnvelope` pattern:

```typescript
interface StabilityData {
  neutral_point_x: number | null;
  cg_x_used: number | null;
  mac: number | null;
  static_margin_pct: number | null;
  stability_class: "stable" | "neutral" | "unstable" | null;
  cg_range_forward: number | null;
  cg_range_aft: number | null;
  Cma: number | null;
  Cnb: number | null;
  Clb: number | null;
  is_statically_stable: boolean;
  is_directionally_stable: boolean;
  is_laterally_stable: boolean;
  status: "CURRENT" | "DIRTY";
  computed_at: string;
  solver: string;
}

interface UseStabilityReturn {
  data: StabilityData | null;
  isLoading: boolean;
  isComputing: boolean;
  error: string | null;
  compute: (tool?: string) => Promise<void>;
  refresh: () => Promise<void>;
}
```

- `refresh()` calls `GET /v2/aeroplanes/{id}/stability`
- `compute()` calls `POST /v2/aeroplanes/{id}/stability_summary/avl`
  with a default operating point, then refreshes cached data
- Auto-fetches on mount when `aeroplaneId` is set

### StabilityPanel

Container component following the `EnvelopePanel` pattern:

- **Toolbar:** "Compute Stability" button (calls `compute()`)
- **Empty state:** "No stability data. Click Compute Stability."
- **Loading/computing state:** spinner
- **Error state:** red banner
- **Content:** Renders `StabilitySideView` when data exists
- **DIRTY indicator:** When `status === "DIRTY"`, show amber banner
  "Stability data may be outdated — geometry changed since last analysis"

### StabilitySideView (Plotly 2D)

A horizontal number-line schematic showing positions along the
aircraft's longitudinal axis (x-axis in meters).

**Layout:**
- X-axis: longitudinal position in meters (nose-left, tail-right)
- Y-axis: hidden (decorative only)
- Dark theme: `paper_bgcolor: "transparent"`, `plot_bgcolor: "transparent"`

**Elements (all plotted as Plotly traces):**

1. **MAC bar** — horizontal grey bar at y=0 showing the mean
   aerodynamic chord extent. X-span: `[np_x - mac, np_x]` (approximate;
   MAC LE is near `np_x - mac`). Label: "MAC" with length annotation.

2. **CG range band** — semi-transparent green rectangle between
   `cg_range_forward` and `cg_range_aft` x-positions.
   Color: green for stable, amber for neutral, red for unstable
   (keyed on `stability_class`).

3. **NP marker** — blue diamond at `neutral_point_x` position.
   Label: "NP".

4. **CG marker** — orange circle at `cg_x_used` position.
   Label: "CG".

5. **Static margin annotation** — text label showing
   "SM: {static_margin_pct}% MAC" positioned between CG and NP.

**Interactivity:**
- `plotly_click` event handler: when a marker is clicked, show
  `MarkerDetailBox` with details for that marker.
- Hover tooltips on each marker with basic info.

### MarkerDetailBox

A small overlay card (not a modal) positioned near the clicked marker.
Dismissed by clicking elsewhere or pressing Escape.

**NP selected:**
- Position: `{neutral_point_x}` m
- Cm_alpha: `{Cma}`
- Stability: `{stability_class}`
- Solver: `{solver}`

**CG selected:**
- Position: `{cg_x_used}` m
- Source: estimate / calculated
- Static margin: `{static_margin_pct}%` MAC

**CG range selected:**
- Forward limit: `{cg_range_forward}` m
- Aft limit: `{cg_range_aft}` m
- Range width: `{cg_range_aft - cg_range_forward}` m

### Tab Integration

Add "Stability" to the `TABS` array in `AnalysisViewerPanel.tsx`
after "Envelope":

```typescript
const TABS = ["Assumptions", "Polar", "Trefftz Plane", "Streamlines",
              "Envelope", "Stability"] as const;
```

The stability tab renders `StabilityPanel` with props from the
`useStability` hook.

## Acceptance Criteria

1. "Stability" tab appears in the Analysis page tab bar
2. Clicking "Compute Stability" triggers a stability analysis and
   displays the side-view schematic
3. NP (blue diamond), CG (orange circle), and CG range (green band)
   are visible on the schematic
4. Static margin percentage is displayed as a text annotation
5. Clicking NP or CG marker shows a detail popup with relevant values
6. When stability data is DIRTY, an amber banner indicates outdated data
7. Empty state shows when no stability data exists
8. Error state displays when computation fails
9. Component follows existing dark-theme styling conventions
10. All new components have unit tests

## Out of Scope

- CG dragging (deferred to future iteration)
- x_ref marker display (minor, can be added later)
- Auto-refresh polling when DIRTY (future enhancement)
- Stability tab in AnalysisConfigPanel modal (stability uses a direct
  compute button like Envelope, not the Configure & Run modal)
