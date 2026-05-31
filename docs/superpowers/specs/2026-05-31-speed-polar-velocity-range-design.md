# Geschwindigkeitspolare — velocity range anchored to computed V_stall / V_dive

**Issue:** #799
**Date:** 2026-05-31
**Status:** Design approved (brainstorming), pending implementation plan

## Problem

The speed polar (`SpeedPolar`, merged in #785) plots sink rate `w` over forward
speed `V`. The velocity range currently falls out of the fixed alpha sweep
(`α ∈ [-15°, 20°]`, 36 points): the high-CL end gives the lowest `V` (≈ stall),
the lowest positive CL gives an arbitrarily high `V` (the `CL → 0⁺` tail). The
displayed range is therefore not tied to the aircraft's real operating envelope.

**Goal:** anchor the *displayed* velocity range to the aircraft's **computed**
flight-envelope speeds — from `0.7·V_stall` to `1.3·V_dive`.

## Requirements

1. **Low end is a display margin, not curve data.** A steady glide speed polar
   exists only for `V ≥ V_stall` (at `V_stall`, `C_L = C_L,max`; slower would
   need `C_L > C_L,max` → no equilibrium). So the curve **data** still starts at
   `V_stall`; only the **X-axis lower limit** is set to `0.7·V_stall` for visual
   margin.
2. **Anchor = envelope over all plotted masses.** With multiple mass curves on
   one plot, a single X-axis range is needed:
   - `v_axis_min = 0.7 × min(V_stall over all curves)` → the **lightest** mass
     (since `V_stall ∝ √m`).
   - `v_axis_max = 1.3 × V_dive`.
3. **V_dive is mass-independent.** `V_dive` is a fixed design/structural airspeed;
   unlike `V_stall` it does **not** scale with mass. A single `V_dive` sets the
   right edge for all curves; only the left edge varies with mass.
4. **Glider fallback.** When `V_dive` is not computable (glider with no `V_max`
   goal → `v_dive_mps is None`), set `v_axis_max = max V across all curves`
   (the lowest-positive-`C_L` point the sweep produced). Always available.

## Approach (A — backend owns the bounds)

The backend computes the recommended axis bounds and returns them in the
`SpeedPolar` schema; the frontend applies them to the Plotly X-axis. Physics
stays in the backend (unit-testable), the frontend stays thin, and the curve
data is unchanged (non-destructive — no clipping).

Rejected alternatives:
- **B (frontend-only):** couples the speed-polar chart to a separate
  flight-envelope KPI fetch and pushes physics into TS (harder to unit-test).
- **C (clip curve data to the band):** invasive, discards data outside the band,
  and conflicts with requirement 1 (curve should begin physically at `V_stall`,
  not be hard-clipped).

## Design

### Data source

- `v_dive_mps` is read from the cached `aircraft.assumption_computation_context`
  dict (`assumption_compute_service.py` persists it at line ~1759). No recompute:
  the speed-polar path already has `db` + `aeroplane_uuid`. If the context is
  absent/`None` or has no `v_dive_mps`, the glider fallback (req. 4) applies.
- Per-curve `V_stall` is already computed in `_compute_speed_polar`
  (`sqrt(2·m·g / (ρ·S·C_L,max))`, from the sweep's max CL).

### Schema — `app/schemas/aeroanalysisschema.py`, `SpeedPolar`

Add two optional fields (display bounds, m/s):

```python
v_axis_min: Optional[float] = Field(
    None, description="Recommended X-axis lower limit [m/s] = 0.7 × min V_stall over curves"
)
v_axis_max: Optional[float] = Field(
    None, description="Recommended X-axis upper limit [m/s] = 1.3 × V_dive, "
    "or max sweep V when V_dive is unavailable"
)
```

Optional (annotation): `v_dive: Optional[float]` for a labelled marker. Per-curve
`v_stall` stays as-is.

### Backend — `app/services/analysis_service.py`

- `_compute_speed_polar` **stays pure**: add an optional `v_dive: float | None =
  None` parameter and compute the two bounds from the curves it already builds:
  - `v_stall_values = [c.v_stall for c in curves if c.v_stall is not None]`
  - `v_axis_min = 0.7 × min(v_stall_values)` if any, else `None`.
  - if `v_dive` is not None and `> 0`: `v_axis_max = 1.3 × v_dive`
    else: `v_axis_max = max(max(c.V) for c in curves if c.V)` (fallback).
  - guard: if both bounds set and `v_axis_min >= v_axis_max`, drop to autorange
    (`v_axis_min = v_axis_max = None`) — defensive, should not happen.
  - return them on the `SpeedPolar`.
- `_build_speed_polar` resolves `v_dive`: load the aeroplane model, read
  `(getattr(aeroplane, "assumption_computation_context", None) or {}).get("v_dive_mps")`,
  pass it into `_compute_speed_polar`. Best-effort (wrapped in the existing
  try/except — a missing context must not break the sweep).

### Frontend — `frontend/components/workbench/AnalysisViewerPanel.tsx`

- `SpeedPolarChart`: when `speedPolar.v_axis_min`/`v_axis_max` are present and
  finite, set Plotly `xaxis.range = [v_axis_min, v_axis_max]`; otherwise leave
  autorange. Curve traces unchanged. (Optional: a vertical `V_dive` annotation.)
- `useAnalysis.ts`: extend the `SpeedPolar` TS interface with the two fields.

## Edge cases

- No assumptions context / `v_dive_mps` missing → fallback to max sweep V.
- All `v_stall` None (degenerate sweep) → `v_axis_min = None` → autorange.
- Single mass → `min` over one curve.
- `v_axis_min >= v_axis_max` → autorange (defensive).

## Testing (TDD)

**Backend** (`app/tests/test_speed_polar.py`):
- bounds with `v_dive` given: `v_axis_min == 0.7 × min(v_stall)`,
  `v_axis_max == 1.3 × v_dive`.
- fallback: `v_dive=None` → `v_axis_max == max(V)` over curves.
- envelope: multi-mass → `v_axis_min` uses the lightest mass's `v_stall`.
- `v_dive` mass-independence: right edge identical regardless of which masses are
  added.
- defensive: degenerate inputs → bounds `None` (autorange), no exception.

**Frontend** (`frontend/__tests__/`):
- chart applies `xaxis.range` when bounds present; autorange when absent.

## Out of scope

- Recomputing `V_dive`/`V_max` per comparison mass (treated mass-independent).
- Changing the alpha sweep range or re-running AeroBuildup (the sweep already
  covers the band; this is a display-bounds feature).
- Flutter-based `V_dive` (still the `1.4·V_max` heuristic from gh-476).
