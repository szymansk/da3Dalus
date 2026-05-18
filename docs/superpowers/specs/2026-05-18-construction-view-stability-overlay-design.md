# Construction-View Stability Overlay — Design Spec

**Date:** 2026-05-18 (corrected — initial draft targeted the OCP CadViewer; the real target is the Plotly-based `WingOutlineViewer`).
**Epic:** #566 (move stability visualisation from Analysis tab to Construction view)
**Sibling sub-issue:** #567 (remove Stability tab)
**Related bug:** #568 (cg_agg_m not displayed in footer)
**Authoritative source:** Issue #569 body. This document is a synchronised local copy.

## Problem

NP, CG and Static Margin are configuration properties of the geometry (Sadraey §11.4) — they belong on the geometry, not in a separate 2D-schematic Analysis tab. Two CGs exist and must be reconciled in the user's view: **SOLL CG** (design target) and **IST CG** (component-aggregated). The footer renders these as text + colour; the Construction view should render them spatially.

## Architecture — Plotly trace overlay via composable registry

The Construction view's 3D preview is the **Plotly-based** `WingOutlineViewer.tsx` (Three.js / OCP `CadViewer` is a different surface and not the target here).

### Composition model

```
app/workbench/page.tsx
  ├── const { traces, register } = useOverlayRegistry()
  ├── <WingOutlineViewer ... extraTraces={traces} />
  └── <OverlayBar>
        ├── <StabilityOverlay aeroplaneId={...} register={register('stability')} />
        └── (future overlays slot in here — same pattern)
      </OverlayBar>
```

- `WingOutlineViewer` accepts one new optional prop `extraTraces?: PlotlyData[]`.
- `useOverlayRegistry()` is a tiny hook that maps `overlay-key → trace[]` and exposes a flat array.
- Each overlay component owns: its data hook, its enabled state, its traces, its toggle button.

### Markers (Plotly traces)

| Marker | Trace | Style | Hovertext |
|---|---|---|---|
| NP | `scatter3d` 1 pt | sphere, blue, 8 px | NP + MAC |
| CG SOLL | `scatter3d` 1 pt | sphere, `#FF8400`, 12 px | CG soll + target SM |
| CG IST | `scatter3d` 1 pt | sphere, ~6 px, semi-transparent, colour via `cgDivergenceColor(soll,ist,mac)` | CG ist + resulting SM + Δ |
| SM band | `scatter3d` 2 pts, `mode: "lines"` | solid yellow-green | target SM |
| SOLL↔IST link | `scatter3d` 2 pts, `mode: "lines"`, dashed | colour from IST marker; only when both present and `|Δ|/MAC > 1 %` | (none) |

### Coordinate handling

Backend NP/CG in metres; `WingOutlineViewer` renders wings in mm with `aspectmode: "data"`. Apply `× 1000` to NP/CG values before placing in Plotly traces. Longitudinal axis is X.

### Tooltips

Plotly native `hovertext` + `hovertemplate`. No HTML overlay, no projection math, no raycasting.

### Update behaviour

`useMemo` rebuilds traces on changes to ctx + enabled state. Register call triggers `WingOutlineViewer` replot. Camera preservation already implemented in `WingOutlineViewer.tsx:882-892`.

### Toggle

Button in `WingOutlineViewer`'s existing bottom-right overlay bar (sibling to `¼ Chord`). State persisted in `localStorage`. Default on. Disabled state → empty trace array → no perf cost.

### Graceful degradation

| Data state | Markers shown |
|---|---|
| All values present | NP + SOLL + IST + SM band + (delta link if `|Δ|/MAC > 1 %`) |
| `cg_agg_m == null` | NP + SOLL + SM band |
| `x_np_m == null` | nothing; toggle hidden |
| `target_static_margin == null` | NP + IST; toggle hint *"No design target set"* |

## Acceptance Criteria

See issue #569 — keep in sync.

## Out of scope

Backend changes; CadViewer changes; airfoil-preview-page mounting; future overlays; #567; #568.

## Open implementation risks

1. `extraTraces` interaction with `WingOutlineViewer.tsx:870-877` empty-scene placeholder — plan handles it.
2. Camera preservation across overlay-only updates — plan verifies via test.
3. Trace-count scaling for future overlays — non-issue at 5 traces.
