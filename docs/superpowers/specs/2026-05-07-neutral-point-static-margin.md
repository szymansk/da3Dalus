# Spec: Neutral Point & Static Margin Calculation (#421)

## Problem

Stability analysis results are computed on-the-fly via
`POST /v2/aeroplanes/{id}/stability_summary/{tool}` but never persisted.
This means:

- Every query re-runs the full aero solver (expensive).
- No way to detect stale results after geometry changes.
- No CG range (forward/aft limits) derived from neutral point.
- No stability classification (stable/neutral/unstable).
- No MCP tools for AI-agent workflows.
- No auto-population of cd0 from parasitic drag analysis.

## Solution

Add a **`stability_results` table** that caches the last stability
computation per aeroplane+solver, with staleness tracking and derived
CG range. Expose via a new `GET` endpoint and MCP tools.

## Existing Infrastructure (reuse, don't rebuild)

| Component | File | Status |
|-----------|------|--------|
| `stability_service.get_stability_summary()` | `app/services/stability_service.py` | Computes NP, SM, derivatives — **extend** |
| `StabilitySummaryResponse` | `app/schemas/stability.py` | Response schema — **extend** |
| `POST .../stability_summary/{tool}` | `app/api/v2/endpoints/aeroanalysis.py:142` | Compute endpoint — **extend to persist** |
| `DesignAssumptionModel` | `app/models/aeroplanemodel.py:630` | Has `cg_x`, `target_static_margin`, `cd0` — **read** |
| `mass_cg_service.compute_recommended_cg()` | `app/services/mass_cg_service.py:38` | Pure fn — **reuse** |
| `avl_geometry_events.py` | `app/models/avl_geometry_events.py` | Dirty-flag pattern — **replicate** |

## Deliverables

### D1: StabilityResultModel (SQLAlchemy)

New table `stability_results`:

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `aeroplane_id` | FK → aeroplanes | Cascade delete |
| `solver` | String | `avl` / `aerobuildup` / `vlm` |
| `neutral_point_x` | Float | NP x-coordinate (m) |
| `mac` | Float | Mean aerodynamic chord (m) |
| `cg_x_used` | Float | CG x used for computation (m) |
| `static_margin_pct` | Float | SM as percentage of MAC |
| `stability_class` | String | `stable` / `neutral` / `unstable` |
| `cg_range_forward` | Float | Forward CG limit (m) |
| `cg_range_aft` | Float | Aft CG limit (m) |
| `Cma` | Float, nullable | dCm/dalpha |
| `Cnb` | Float, nullable | dCn/dbeta |
| `Clb` | Float, nullable | dCl/dbeta |
| `trim_alpha_deg` | Float, nullable | Alpha at operating point |
| `trim_elevator_deg` | Float, nullable | Elevator deflection |
| `is_statically_stable` | Boolean | Cma < 0 |
| `is_directionally_stable` | Boolean | Cnb > 0 |
| `is_laterally_stable` | Boolean | Clb < 0 |
| `computed_at` | DateTime(tz) | When last computed |
| `status` | String | `CURRENT` / `DIRTY` |
| `geometry_hash` | String, nullable | Hash of wing geometry for staleness |

**Unique constraint:** `(aeroplane_id, solver)` — one result per solver.

### D2: Alembic Migration

Down-revision: `b3c4d5e6f7a8`. Creates `stability_results` table.

### D3: StabilityResultSchema (Pydantic)

**`StabilityResultRead`**: Full read model with all DB fields.

**Extend `StabilitySummaryResponse`** with:
- `static_margin_pct: float | None` — SM × 100
- `stability_class: str | None` — `stable` / `neutral` / `unstable`
- `cg_range_forward: float | None` — Forward CG limit (m)
- `cg_range_aft: float | None` — Aft CG limit (m)
- `mac: float | None` — Mean aerodynamic chord (m)
- `status: str | None` — `CURRENT` / `DIRTY` (only on cached results)

### D4: Stability Service Enhancements

1. **`classify_stability(static_margin_pct)`** → `stable` / `neutral` / `unstable`
   - `> 5%` → stable
   - `0–5%` → neutral
   - `< 0%` → unstable

2. **`compute_cg_range(np_x, mac, min_margin, max_margin)`** → `(forward, aft)`
   - Forward = `NP_x − (max_margin / 100) × MAC`
   - Aft = `NP_x − (min_margin / 100) × MAC`
   - Defaults: min=5%, max=25% (from `design_assumptions` if available)

3. **`persist_stability_result(db, aeroplane_id, solver, result)`**
   - Upsert into `stability_results` (by aeroplane_id + solver)
   - Set status = `CURRENT`

4. **`get_cached_stability(db, aeroplane_id)`** → latest result or None
   - Returns most recent across solvers, preferring CURRENT over DIRTY

5. **`mark_stability_dirty(db, aeroplane_id)`**
   - Set all results for this aeroplane to `DIRTY`

6. **`compute_geometry_hash(plane_schema)`** → string
   - Hash wing span, chord, twist, sweep, dihedral, xsec count, fuselage length
   - Used to detect if geometry actually changed vs. just a re-save

7. **Auto-populate cd0**: After AeroBuildup analysis, update
   `design_assumptions.cd0.calculated_value` from parasitic drag.

### D5: API Endpoints

1. **Extend `POST .../stability_summary/{tool}`**:
   - After computing, persist result to `stability_results`
   - Return extended `StabilitySummaryResponse` with CG range, class, mac

2. **`GET /v2/aeroplanes/{id}/stability`** (new):
   - Returns last cached `StabilityResultRead` without triggering computation
   - 404 if no cached result exists
   - Used by frontend overlay and LLM advisor

### D6: Geometry Change Events

Add SQLAlchemy event listeners (following `avl_geometry_events.py` pattern):
- On wing/fuselage insert/update/delete → `mark_stability_dirty()`
- This marks all `stability_results` for that aeroplane as `DIRTY`

### D7: MCP Tools

1. **`get_stability(aeroplane_id)`** — Returns cached stability result
2. **`compute_stability(aeroplane_id, solver)`** — Triggers fresh computation

### D8: AeroplaneModel Relationship

Add `stability_results` relationship to `AeroplaneModel` with cascade delete.

## Acceptance Criteria

- [ ] `stability_results` table created via Alembic migration
- [ ] `POST .../stability_summary/{tool}` persists result and returns CG range + class
- [ ] `GET .../stability` returns cached result without re-computation
- [ ] 404 on `GET .../stability` when no cached result exists
- [ ] Stability class correctly classifies stable/neutral/unstable
- [ ] CG range uses min/max static margin from design_assumptions (with defaults)
- [ ] Geometry changes mark stability results as DIRTY
- [ ] MCP tools `get_stability` and `compute_stability` work
- [ ] cd0 auto-populated after AeroBuildup analysis
- [ ] All existing stability tests continue to pass
- [ ] New unit tests for: classification, CG range, persistence, dirty marking, GET endpoint
- [ ] >80% test coverage on new code

## Out of Scope

- Frontend visualization (that's #423)
- Operating point auto-generation (that's #422)
- What-if simulation (that's #420)
