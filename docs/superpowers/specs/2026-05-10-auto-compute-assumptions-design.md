# Auto-Compute Design Assumptions (CL_max, CD0, CG)

**Issue:** #465
**Date:** 2026-05-10
**Status:** Approved

## Problem

Design assumptions `cl_max`, `cd0`, and `cg_x` are manual inputs that most users cannot estimate. They should be auto-computed from aircraft geometry using AeroSandbox whenever the geometry changes.

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Aero solver | AeroSandbox only, never AVL | ASB is the foundation of the app — designed for speed and optimizer loops |
| CL_max method | Two-phase AeroBuildup sweep: coarse alpha-only to find stall region, then fine alpha × velocity sweep around stall | ASB handles AR, taper, sweep, Re internally; velocity sweep captures Re effects across flight envelope |
| CG semantics | CG_aero (from NP + static margin) is the design target; CG_agg (from weight items) is shown for comparison only | Standard aircraft design process — ballast trims CG_agg to match CG_aero |
| CG_agg storage | Not in Assumption system; queried live from weight items | CG_agg is a verification metric, not a design input |
| Trigger | GeometryChanged → job tracker (debounced, configurable) → async recompute | Non-blocking, uses existing infrastructure, values ready for retrim chain |
| Auto-switch source | On first computed value: auto-switch to CALCULATED; after that, respect user choice | Hobbyists get good defaults; pros keep manual control |
| UI changes | Minimal — use existing badge/divergence system; dynamic Info Chip Row | No structural AssumptionsPanel changes needed |
| Analysis tab gating | Computation tabs show empty state without wings; Assumptions tab always accessible | Design choices belong to early design phase |

## Architecture

### Computation Pipeline

```
GeometryChanged event (any wing/fuselage change)
  → invalidation_service: schedule_recompute_assumptions(aeroplane_id)
    → job_tracker debounce (config.debounce_seconds, default 2s)
      → assumption_compute_service.recompute_assumptions(db, aeroplane_uuid)
         1. Load aircraft → convert to ASB Airplane
         2. Load flight profile (or default) → cruise_speed, V_max (max_level_speed_mps)
         3. Compute MAC from ASB geometry
         4. Load aircraft_computation_config (or seed defaults)
         5. Two-phase AeroBuildup sweep:
            Phase 1 — coarse alpha sweep at cruise speed (config: alpha_min to alpha_max, coarse_step):
              - Find approximate stall alpha (alpha where CL peaks)
              - CD0 = CD at the alpha where CL is closest to 0
              - x_np from run_with_stability_derivatives()
            Phase 2 — fine alpha × velocity sweep around stall region:
              - Alpha: stall_alpha ± config.fine_alpha_margin, config.fine_step
              - Velocity: from ~1.0× stall speed to V_max from flight profile
                (config.fine_velocity_count evenly spaced speeds)
              - CL_max = max(CL) across all (alpha, velocity) combinations
              - This captures Re-dependent stall behavior at RC/UAV scales
         6. Load target_static_margin from assumptions (effective value)
         7. cg_x = x_np - target_static_margin × MAC
         8. update_calculated_value("cl_max", CL_max, "aerobuildup", auto_switch=True)
            update_calculated_value("cd0", CD0, "aerobuildup", auto_switch=True)
            update_calculated_value("cg_x", cg_x, "aerobuildup", auto_switch=True)
         9. Cache computation context on aeroplane model
        10. If cg_x changed: publish AssumptionChanged event directly from recompute service
            (update_calculated_value does NOT publish events by design — the recompute
            service takes responsibility for triggering the retrim chain)
```

### Event Chain

```
GeometryChanged
  → recompute_assumptions (debounced, config.debounce_seconds)
    → update_calculated_value × 3
    → AssumptionChanged (for cg_x, if changed)
      → schedule_retrim (existing)
        → OPs recomputed with new CG
```

### Data Model

**No schema changes required for assumptions.** The existing `DesignAssumptionModel` already supports:
- `calculated_value` / `calculated_source` — populated with ASB results
- `active_source` — auto-switch logic added in service
- `divergence_pct` / `divergence_level` — computed automatically

**New table: `aircraft_computation_config`** — per-aircraft configuration for sweep parameters and other computation settings. No magic numbers in code — all sweep resolutions come from this table with sensible defaults.

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| id | int PK | | |
| aeroplane_id | int FK | | unique, cascade delete |
| coarse_alpha_min_deg | float | -5.0 | Coarse sweep start |
| coarse_alpha_max_deg | float | 25.0 | Coarse sweep end |
| coarse_alpha_step_deg | float | 1.0 | Coarse sweep resolution |
| fine_alpha_margin_deg | float | 5.0 | Margin around stall alpha for fine sweep |
| fine_alpha_step_deg | float | 0.5 | Fine sweep resolution |
| fine_velocity_count | int | 8 | Number of velocity steps in fine sweep |
| debounce_seconds | float | 2.0 | Debounce delay after GeometryChanged |

Seeded with defaults when assumptions are seeded. Later exposed via the gear icon in the Analysis tab header (out of scope for this feature — just the data model and API).

**New field on AeroplaneModel:** `assumption_computation_context: JSON | None` — caches the intermediate values from the last recompute for the Info Chip Row.

Structure:
```json
{
  "v_cruise_mps": 18.0,
  "reynolds": 230000,
  "mac_m": 0.21,
  "x_np_m": 0.085,
  "target_static_margin": 0.12,
  "cg_agg_m": 0.092,
  "computed_at": "2026-05-10T14:30:00Z"
}
```

Requires an Alembic migration to add the column.

## Backend Changes

### New Files

**`app/services/assumption_compute_service.py`**

Single public function:
- `recompute_assumptions(db: Session, aeroplane_uuid: str) -> None`
  - Orchestrates the full pipeline (load → ASB → compute → store → event)
  - Handles missing wings gracefully (skips computation, logs warning)
  - Handles missing flight profile (uses default: 18 m/s cruise)

### Modified Files

**`app/services/invalidation_service.py`**
- Add `_on_geometry_changed_recompute_assumptions` handler
- Register via `register_handlers()`
- Uses `job_tracker.schedule_recompute_assumptions(aeroplane_id)` (debounced)

**`app/services/design_assumptions_service.py`**
- Modify `update_calculated_value()`: add `auto_switch_source` parameter (default False)
  - When True and current `calculated_value` is None and `active_source` is "ESTIMATE": switch to "CALCULATED"
  - Respects `DESIGN_CHOICE_PARAMS` — never auto-switches those
  - `update_calculated_value()` remains event-silent by design — the calling service (recompute) publishes events when needed

**`app/models/aeroplanemodel.py`**
- Add `assumption_computation_context: Column(JSON, nullable=True)` to `AeroplaneModel`
- Add `AircraftComputationConfigModel` (new table `aircraft_computation_config`)

**`app/schemas/computation_config.py`** (new)
- `ComputationConfigRead` / `ComputationConfigWrite` — Pydantic schemas for the config table

**`alembic/versions/`**
- New migration: add `assumption_computation_context` column + `aircraft_computation_config` table

**`app/services/design_assumptions_service.py`** (seed_defaults)
- Extend `seed_defaults()` to also seed `aircraft_computation_config` with defaults (idempotent)

**`app/api/v2/endpoints/aeroplane/design_assumptions.py`**
- New endpoint: `GET /aeroplanes/{id}/assumptions/computation-context`
  - Returns the cached computation context JSON
  - 200 with data or 200 with null (never computed yet)
- New endpoint: `GET /aeroplanes/{id}/computation-config`
  - Returns current computation config (or defaults if not yet seeded)
- New endpoint: `PUT /aeroplanes/{id}/computation-config`
  - Updates computation config (for future gear icon UI)

### Existing CD0 Auto-Population

`stability_service._auto_populate_cd0()` already writes CD0 after AeroBuildup runs. This remains — if a user manually runs a stability analysis, that CD0 also feeds into `calculated_value`. The `recompute_assumptions` pipeline does the same but triggered by geometry changes. Last writer wins, both use source `"aerobuildup"`.

## Frontend Changes

### Info Chip Row (`AnalysisViewerPanel.tsx`)

Replace hardcoded chips with dynamic values from computation context:

| Chip | Source | Example |
|------|--------|---------|
| V_cruise | `v_cruise_mps` | `V = 18.0 m/s` |
| Re | `reynolds` | `Re ≈ 2.3e5` |
| MAC | `mac_m` | `MAC = 0.21 m` |
| NP | `x_np_m` | `NP = 0.085 m` |
| SM | `target_static_margin` | `SM = 12%` |
| CG | `cg_x` + `cg_agg_m` in parentheses | `CG = 0.073 m (0.092)` |

**CG chip detail:** The main value is CG_aero (cg_x from assumptions). CG_agg is shown in parentheses with color coding:
- Green: CG_agg is close to CG_aero (delta < 5% MAC) — well balanced
- Orange: moderate offset (5–15% MAC) — needs ballast adjustment
- Red: large offset (> 15% MAC) — significantly nose- or tail-heavy

The direction (nose-heavy vs tail-heavy) is implicit: CG_agg > CG_aero = nose-heavy, CG_agg < CG_aero = tail-heavy (assuming x-axis points aft).

New hook: `useComputationContext(aeroplaneId)` → `GET /aeroplanes/{id}/assumptions/computation-context`. When no context exists, chips show "–".

### AssumptionsPanel

Minimal change: for `cg_x`, show CG_agg comparison value from the computation context (small inline chip below the assumption row). No structural changes.

### Analysis Tab Wing Gate

In `AnalysisViewerPanel.tsx`, for each computation tab (Polar, Trefftz, Streamlines, Stability, Envelope, Operating Points): if `wings.length === 0`, render empty state "Add a wing to enable aerodynamic analysis" instead of tab content. Assumptions tab always renders normally.

Check via existing `wingXSecs` prop (already passed) or a new `hasWings: boolean` prop.

### No Polling Needed

SWR revalidates on focus/navigation. The recompute takes ~2s and runs in the background. By the time the user navigates to Assumptions, values are ready.

## Testing

### Backend

| Test | Type | What |
|------|------|------|
| `test_recompute_assumptions_basic` | unit | Mock ASB, verify all 3 values written + context cached |
| `test_recompute_assumptions_no_wings` | unit | Graceful skip when no wings exist |
| `test_recompute_assumptions_auto_switch` | unit | First compute auto-switches to CALCULATED |
| `test_recompute_assumptions_respects_user_choice` | unit | After user switches to ESTIMATE, recompute doesn't override |
| `test_geometry_changed_triggers_recompute` | integration | Event → job scheduled → assumptions updated |
| `test_cg_change_triggers_retrim` | integration | cg_x update → AssumptionChanged → OPs dirty |
| `test_computation_context_endpoint` | unit | GET returns cached context |

### Frontend

| Test | Type | What |
|------|------|------|
| Info Chip Row renders context values | vitest | Chips show dynamic values from hook |
| Info Chip Row handles null context | vitest | Chips show "–" when no context |
| Tabs show wing gate | vitest | Empty state when no wings |
| Assumptions tab accessible without wings | vitest | Always renders |

## Out of Scope

- WebSocket/polling for real-time updates (SWR revalidation is enough)
- AssumptionsPanel structural redesign (existing badge system works)
- AVL-based computation (ASB only, per project philosophy)
- Gear icon UI for editing computation config (data model and API only in this feature)
