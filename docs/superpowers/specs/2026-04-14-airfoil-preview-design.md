# Airfoil Preview Screen — Design Spec

**GH Issue:** #50
**Date:** 2026-04-14
**Wireframe:** `da3Dalus.pen` → `screen-2b-airfoil-preview` (Node `ys5gm`)

## Problem

The construction workbench has AirfoilSelector dropdowns but no way to preview airfoil geometry or aerodynamic characteristics. The designer picks airfoils blind — only seeing the filename (e.g. "mh32"). All backend endpoints exist (datfile download, NeuralFoil analysis) but the frontend has no screen to use them.

## Design

### Navigation

- **Route:** `/workbench/airfoil-preview` (dedicated App Router page)
- **Entry:** Preview icon button next to each AirfoilSelector in PropertyForm → `router.push('/workbench/airfoil-preview')`
- **Exit:** Browser back, or click "Construction" step pill in Header
- **Header:** Step 2 (Construction) stays active; breadcrumb shows `{wing} / segment {N}`
- **Context:** Uses existing AeroplaneContext (selectedWing, selectedXsecIndex) — no URL params needed

### Layout (matching wireframe)

```
┌─ Header (breadcrumb: "main_wing / segment 0") ─────────────────┐
├─────────────────────────────┬───────────────────────────────────┤
│  Viewer Panel (flex-1)      │  Config Panel (480px fixed)       │
│                             │                                   │
│  ┌─ viewerHeader ─────────┐ │  ┌─ actionRow ─────────────────┐ │
│  │ "Airfoil Preview" mh32 │ │  │ [Run Analysis] [Clear]      │ │
│  │           Re: 200k Ma:0│ │  └─────────────────────────────┘ │
│  └────────────────────────┘ │  "segment 0 · Properties"        │
│                             │                                   │
│  ┌─ Geometry SVG ─────────┐ │  root_airfoil: [mh32      ▼]    │
│  │   ╭──────────╮         │ │    ┌─ Search airfoils... ──────┐ │
│  │  ╱            ╲        │ │    │ ✓ mh32       8.9%         │ │
│  │ ╱──────────────╲───TE  │ │    │   mh45       9.6%         │ │
│  │ LE  t/c=8.9% cam=2.4% │ │    │   rg15       8.9%         │ │
│  └────────────────────────┘ │    └───────────────────────────┘ │
│                             │                                   │
│  ┌─ CL vs α ──┬─ L/D vs α┐ │  tip_airfoil: [mh32      ▼]     │
│  │  chart     │  chart    │ │  ─────────────────────────        │
│  │  (from     │  (from    │ │  span: 200    sweep: 0.0         │
│  │  NeuralFoil│  NeuralFoil│ │  dihedral: 3  incidence: 0.0    │
│  └────────────┴───────────┘ │  (grayed out, read-only)         │
├─────────────────────────────┴───────────────────────────────────┤
│  CopilotBar                                                     │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Page** reads `selectedWing` + `selectedXsecIndex` from AeroplaneContext
2. **useWingConfig(aeroplaneId, selectedWing)** provides segment data (airfoil names, chord, sweep, etc.)
3. **useAirfoilGeometry(airfoilName)** — new hook, fetches `GET /airfoils/{name}/datfile`, parses Selig format to `{upper: [x,y][], lower: [x,y][]}`, computes t/c% and camber%
4. **useAirfoilAnalysis** — new hook, `POST /airfoils/{name}/neuralfoil/analysis` with Re/Ma. Triggered only by "Run Analysis" button click. Returns CL[], CD[], CL/CD[], alpha[], cl_max, alpha_at_cl_max
5. Airfoil change in selector → geometry updates immediately, charts show "Run Analysis to see polars"

### Quick Stats in Selector Dropdown

- Geometry-only: t/c% computed from .dat coordinates (max upper_y - lower_y across chord)
- Shown right-aligned per dropdown item: `"8.9%"` in muted JetBrains Mono
- L/D is NOT shown in dropdown — only visible after "Run Analysis" in viewer charts
- Backend: new `GET /airfoils/{name}/geometry-stats` endpoint, or compute client-side from datfile response

### Backend Changes

**New endpoint:** `GET /airfoils/{name}/geometry-stats`
- Response: `{ airfoil_name, max_thickness_pct, max_camber_pct }`
- Pure geometry computation from .dat coordinates, <10ms
- No NeuralFoil dependency

**Existing endpoints used as-is:**
- `GET /airfoils/{name}/datfile` — raw Selig coordinates
- `POST /airfoils/{name}/neuralfoil/analysis` — full polar analysis
- `GET /airfoils` — list for selector dropdown

### New Files

| File | Purpose |
|------|---------|
| `frontend/app/workbench/airfoil-preview/page.tsx` | Route page, orchestrates state |
| `frontend/hooks/useAirfoilGeometry.ts` | Fetch + parse .dat, compute t/c% + camber% |
| `frontend/hooks/useAirfoilAnalysis.ts` | NeuralFoil analysis hook |
| `frontend/components/workbench/AirfoilPreviewViewerPanel.tsx` | Left panel (geometry + charts) |
| `frontend/components/workbench/AirfoilPreviewConfigPanel.tsx` | Right panel (selectors + properties) |
| `app/api/v2/endpoints/airfoils.py` | Add geometry-stats endpoint |
| `app/schemas/airfoils.py` or inline | AirfoilGeometryStatsResponse schema |

### Modified Files

| File | Change |
|------|--------|
| `frontend/components/workbench/PropertyForm.tsx` | Add preview icon button next to AirfoilSelector |
| `frontend/components/workbench/Header.tsx` | isActive for `/workbench/airfoil-preview` → Step 2 |
| `frontend/components/workbench/AirfoilSelector.tsx` | Add `stats` prop for t/c% display per item |

### Geometry SVG Rendering

Parse Selig .dat format:
```
mh32
1.0000  0.0000
0.9900  0.0050
...        (upper surface, LE→TE)
0.0000  0.0000   (leading edge)
0.0100 -0.0030
...        (lower surface, LE→TE)
1.0000  0.0000
```

Render as SVG paths:
- Upper surface: orange stroke + light orange fill
- Lower surface: orange stroke + light orange fill
- Chord line: dashed gray
- Camber line: white, thin
- t/c annotation at max thickness location
- LE / TE labels

### Chart Rendering

Reuse the SVG LineChart pattern from AnalysisViewerPanel.tsx:
- CL vs α: orange line, show CL,max annotation
- CL/CD vs α: green line, show L/D,max annotation
- X-axis: alpha range from analysis
- Stall line (red vertical) at CL,max alpha

Charts show "Run Analysis to see polars" when no analysis data exists.

### Out of Scope

- Comparison mode (root vs tip overlay)
- Airfoil upload
- Batch NeuralFoil for dropdown L/D stats
- Custom alpha range input
