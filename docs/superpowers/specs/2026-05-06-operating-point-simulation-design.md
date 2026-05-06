# Operating Point Simulation — Epic Design

Epic: GH#417 — Operating Point Simulation: deflections, trim, stability

## Problem

da3Dalus supports single-point aerodynamic analysis (alpha sweeps, strip
forces, streamlines), but results are ephemeral and disconnected from the
iterative aircraft design cycle. Designers need to:

- Set estimates for unknown parameters early on and refine them through
  simulation
- Run trimmed operating points with per-point control surface deflections
- See stability metrics (neutral point, static margin) spatially on the
  aircraft
- Get an automatic flight envelope summary without manually configuring
  every condition
- Iterate: change geometry or estimates → see how results shift → refine

The app serves both hobby RC builders and professional UAV designers.
Every feature must be accessible to non-experts (visual defaults, plain
language) while exposing full technical depth for professionals.

## Architecture Principles

### API-first, Frontend-thin

Every action a designer can perform is a REST API endpoint. The frontend
collects input and renders state — it never makes decisions. A future
LLM-based advisor, MCP client, or CLI can achieve identical results
through the same API.

**Consequences:**

- No business logic in the frontend (no dirty-checking, no comparisons,
  no calculations)
- Backend delivers all derived information (deltas, dirty status,
  divergence warnings)
- Every state transition has exactly one API endpoint
- Domain events are backend-internal — consumers (frontend, LLM, MCP)
  only see resulting state

### Event-driven Invalidation

Geometry and assumption changes emit domain events. Listeners invalidate
dependent data (operating points, stability, envelope) and schedule
background re-computation with debouncing.

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   Frontend   │   │  LLM Advisor │   │  MCP Client  │
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       └──────────────────┼──────────────────┘
                          ▼
                   ┌─────────────┐
                   │  REST API   │
                   └──────┬──────┘
                          ▼
                   ┌─────────────┐
                   │  Services   │──→ Domain Events
                   └──────┬──────┘
                          ▼
                   ┌─────────────┐
                   │  Listeners  │
                   │  • invalidate OPs
                   │  • enqueue re-trim
                   │  • store previous_results
                   └──────┬──────┘
                          ▼
                   ┌─────────────┐
                   │  Background │
                   │  Workers    │
                   │  (asyncio)  │
                   └─────────────┘
```

## Data Model

### DesignAssumption (new table)

```
design_assumptions
  ├─ id (PK)
  ├─ aeroplane_id (FK → aeroplanes)
  ├─ parameter_name (str: mass, cg_x, cd0, cl_max, g_limit, target_static_margin)
  ├─ estimate_value (float) — set by designer
  ├─ calculated_value (float, nullable) — from analysis or components
  ├─ calculated_source (str, nullable) — e.g. "component_tree", "stability_analysis"
  ├─ active_source (enum: ESTIMATE | CALCULATED)
  ├─ divergence_pct (float, nullable) — auto: |est - calc| / calc × 100
  ├─ updated_at (datetime)
```

### OperatingPointModel (extended)

```
operating_points (extensions)
  ├─ status (enum: TRIMMED | NOT_TRIMMED | LIMIT_REACHED | DIRTY | COMPUTING)
  ├─ control_deflections (JSON) — per-OP deflection overrides
  ├─ computed_results (JSON) — CL, CD, Cm, L/D, etc.
  ├─ previous_results (JSON, nullable) — snapshot before last re-trim (for deltas)
  ├─ computed_at (datetime, nullable)
  ├─ geometry_hash (str) — SHA-256 of (wing_configs + fuselage_configs + active_assumption_values)
```

The `geometry_hash` is computed from a deterministic JSON serialization
of all wing geometries (span, chord, twist, airfoil, control surfaces),
fuselage geometries, and the effective assumption values at computation
time. This serves as a fallback consistency check: even if an event is
missed, the API can detect `op.geometry_hash != current_hash` on read.

### StabilityResult (new table)

```
stability_results
  ├─ id (PK)
  ├─ aeroplane_id (FK)
  ├─ solver (str: avl | aerobuildup | vlm)
  ├─ neutral_point_x (float, m)
  ├─ mac (float, m)
  ├─ cg_x_used (float, m)
  ├─ static_margin_pct (float)
  ├─ stability_class (str: stable | neutral | unstable)
  ├─ cg_range_forward (float, m)
  ├─ cg_range_aft (float, m)
  ├─ derivatives (JSON)
  ├─ computed_at (datetime)
  ├─ geometry_hash (str)
  ├─ status (enum: CURRENT | DIRTY)
```

### AeroplaneModel (extended)

```
aeroplanes (extension)
  ├─ geometry_version (int, default=0) — incremented on relevant change
```

## Design Assumptions Layer (#424)

### The 6 Core Assumptions (MVP)

| Parameter | Unit | Typical Start | Calculated Source |
|---|---|---|---|
| mass | kg | Manual estimate | component_tree (sum of component masses) |
| cg_x | m from LE | Manual estimate | component_tree (weighted centroid) |
| target_static_margin | % MAC | 10–15% | Never auto — always a design decision |
| cd0 | dimensionless | 0.02–0.04 | aero_analysis (parasitic drag from AeroBuildup) |
| cl_max | dimensionless | 1.2–1.6 | aero_analysis (alpha sweep to stall) |
| g_limit | g | 3.0–4.0 | Never auto — always a structural/regulatory decision |

`target_static_margin` and `g_limit` never have a `calculated_source`.
The UI shows no "Use calculated" toggle for these — only the input field
with a `[design choice]` badge.

### Assumption Lifecycle

```python
def get_effective_value(assumption):
    """Value used for all simulations."""
    if assumption.active_source == CALCULATED and assumption.calculated_value is not None:
        return assumption.calculated_value
    return assumption.estimate_value
```

### Auto-Population

| Trigger | Updates |
|---|---|
| Component tree changed | mass.calculated_value, cg_x.calculated_value |
| Stability analysis runs | cd0.calculated_value (if AeroBuildup) |
| Alpha sweep to stall | cl_max.calculated_value |

Auto-population writes via the same `update_assumption(..., source=CALCULATED)`
path, triggering the same events and dirty-flagging.

### Divergence Thresholds

| Range | Level | UI |
|---|---|---|
| < 5% | None | No indicator |
| 5–15% | Info | Blue hint |
| > 15% | Warning | Orange, "review recommended" |
| > 30% | Alert | Red, "significant divergence" |

### Badge Types

- `⚠ estimate` (orange) — only manual value, or conscious override
- `✓ calculated` (green) — calculated value active
- `design choice` (grey) — parameter never has a calculated value

### API

```
POST   /v2/aeroplanes/{id}/assumptions              — Bulk-create defaults
GET    /v2/aeroplanes/{id}/assumptions              — All with divergence info
PUT    /v2/aeroplanes/{id}/assumptions/{param}      — Update value
PATCH  /v2/aeroplanes/{id}/assumptions/{param}/source — Toggle ESTIMATE ↔ CALCULATED
```

## Operating Points & Deflection Overrides (#416)

### Status Lifecycle

```
         create/generate → DIRTY
                              │ trim job starts
                              ▼
                          COMPUTING
                         ┌────┴────┐
                         ▼         ▼
                     TRIMMED   NOT_TRIMMED   LIMIT_REACHED
                         │         │              │
                         └─────────┴──────────────┘
                              │ geometry_changed
                              ▼
                            DIRTY
```

### Control Surface Deflection Overrides (#416)

Per-OP overrides merged with geometry defaults:

```
Effective deflection for an OP =
  1. OP.control_deflections["elevator"]   (if set)
  2. else: geometry deflection from Wing/TED
```

**Key distinction:**

- Geometry change → all OPs dirty → auto-re-trim
- Deflection override on one OP → recompute this OP only (no trim —
  user-set deflection is a deliberate what-if). The recompute runs the
  solver at the OP's existing trimmed alpha/beta with the new deflections
  and updates `computed_results`. Status stays TRIMMED (the OP was
  trimmed; the user is now exploring a variant).

### Trim Architecture (#418, #419)

Two solver paths, one API:

| Solver | Method | When |
|---|---|---|
| AVL (#418) | Native indirect constraints (`D1 PM 0`) | More accurate, AVL-compatible configs |
| AeroBuildup (#419) | `scipy.optimize.brentq` on Cm=0 | Universal, faster, viscous effects |

Default solver for trim: AeroBuildup (faster). AVL when explicitly chosen.

### Background Auto-Trim

Every geometry or assumption change triggers automatic re-trim:

1. Event emitted → all OPs marked DIRTY (immediate)
2. Debounce 2000ms after last change
3. Background worker trims each OP sequentially
4. Each OP: `previous_results` saved → status COMPUTING → trim → TRIMMED/FAILED
5. After all OPs: envelope and stability re-computed

### Debouncing

```python
RETRIM_DEBOUNCE_MS = 2000

async def on_geometry_changed(aeroplane_id):
    mark_all_ops_dirty(aeroplane_id)        # immediate → UI shows dirty
    await cancel_pending_retrim(aeroplane_id)
    await schedule_retrim(aeroplane_id, delay_ms=RETRIM_DEBOUNCE_MS)
```

### API

```
POST   /v2/aeroplanes/{id}/operating-points                       — Create new OP
GET    /v2/aeroplanes/{id}/operating-points                       — All with status, results, deltas
GET    /v2/aeroplanes/{id}/operating-points/{op_id}               — Single OP detail
PUT    /v2/aeroplanes/{id}/operating-points/{op_id}               — Update (incl. deflections)
DELETE /v2/aeroplanes/{id}/operating-points/{op_id}               — Delete
POST   /v2/aeroplanes/{id}/operating-pointsets/generate-default   — existing
POST   /v2/aeroplanes/{id}/operating-points/trim-all              — Re-trim all dirty OPs
POST   /v2/aeroplanes/{id}/operating-points/{op_id}/trim          — Re-trim single OP
POST   /v2/aeroplanes/{id}/operating-points/{op_id}/compute       — Aero-run without trim (what-if)
```

## Stability (#421, #423)

### Calculation

```
NP_x = x_ref − (Cm_alpha / CL_alpha) × MAC
Static Margin = (NP_x − CG_x) / MAC × 100%

CG Range:
  Forward Limit = NP_x − (max_margin / 100) × MAC
  Aft Limit     = NP_x − (min_margin / 100) × MAC
  Defaults: min = 5%, max = 25%
  Stored as: design_assumptions "min_static_margin" and "max_static_margin"
  (added to assumptions table, type = design choice, not in MVP 6 core)
```

All three solvers provide the required derivatives (Cm_alpha, CL_alpha).
The existing `stability_summary` endpoint is extended with NP, static
margin, CG range, and stability classification.

### API

```
POST /v2/aeroplanes/{id}/stability_summary/{tool}   — existing, extended with NP/SM/CG range
GET  /v2/aeroplanes/{id}/stability                   — cached last result from DB
```

### Frontend: Stability Side-View Overlay (#423)

Plotly 2D schematic side view of the aircraft with overlay markers:

- **CG** (orange marker) — position from assumptions, draggable for what-if
- **NP** (blue marker) — from stability analysis
- **x_ref** (grey marker) — reference point
- **CG range bar** — forward/aft limits as shaded region

Clicking a marker shows a detail box with position, source, and
related values (e.g. Cm_alpha, CL_alpha for NP). Dragging the CG
marker issues `PUT /assumptions/cg_x` — same API path as manual edit.

## Flight Envelope (#422)

### Envelope Computation

Derived from operating points and assumptions:

```
V-n positive: n_max(V) = 0.5 × ρ × V² × S × CL_max / (mass × g)
              capped at g_limit
V-n negative: n_min(V) = 0.5 × ρ × V² × S × CL_min / (mass × g)
              capped at −0.4 × g_limit
Dive speed:   V_d = 1.4 × V_max
```

All values from assumptions (mass, g_limit, cl_max) and geometry (S, ρ).

### Performance KPIs

| KPI | Source |
|---|---|
| Stall speed | Lowest V with TRIMMED status |
| Best L/D | V at max L/D from operating points |
| Min sink speed | V at min sink rate |
| Max speed | From flight profile or assumption |
| Max turn load | Highest n with converged trim |
| Endurance | Derived from best L/D + mass (estimate-based) |

### Dual-View Frontend

**Default: Performance Overview** (hobbyist-friendly)

KPI cards with deltas + radar chart (Speed, Turn, Endurance, Range axes).

**Toggle: V-n Diagram** (professional)

Classical velocity vs. load factor diagram with operating points as
clickable markers. Click jumps to OP detail in Operating Points tab.

### API

```
GET  /v2/aeroplanes/{id}/flight-envelope           — cached envelope
POST /v2/aeroplanes/{id}/flight-envelope/compute    — trigger recomputation
```

## Event System

### Domain Events

In-process dispatcher, no external framework. Events are fire-and-forget
within the same Python process — they do not survive server restarts.
This is acceptable because all state is persisted in the database; a
restart simply means pending re-trims won't fire, and the next read
will detect stale `geometry_hash` and re-trigger.

```python
EventType = Literal[
    "geometry_changed",
    "assumptions_updated",
    "operating_point_updated",
    "trim_completed",
    "all_trims_completed",
    "stability_computed",
]
```

### Event → Reaction Mapping

```
geometry_changed
  ├─→ mark all OPs dirty
  ├─→ mark stability_result dirty
  ├─→ mark flight_envelope dirty
  └─→ schedule retrim (debounced 2s)

assumptions_updated
  ├─→ mark all OPs dirty (if mass/cg/cd0/cl_max affected)
  ├─→ mark flight_envelope dirty (if mass/g_limit/cl_max affected)
  └─→ schedule retrim (debounced 2s)

operating_point_updated (single OP deflection override)
  └─→ recompute this OP only (no trim, aero-run only)

all_trims_completed
  ├─→ recompute flight_envelope
  └─→ recompute stability (if dirty)

stability_computed
  ├─→ auto-populate assumptions (cd0, cl_max if available)
  └─→ update stability_result in DB
```

### Dirty Triggers

Triggers dirty flag on all operating points, stability, and envelope:

- Wing geometry (span, chord, twist, airfoil, sweep, dihedral)
- Control surface add/remove/modify
- Fuselage geometry
- Design assumptions (mass, CG, Cd0, CL_max, g_limit)
- Flight profile change

Does NOT trigger dirty:

- Aeroplane name/description
- Component library changes
- Construction plan edits

### Background Job Management

FastAPI background tasks with asyncio. No Celery/Redis.

- Per aeroplane: max 1 active retrim job
- New trigger cancels pending job
- Each OP committed individually → frontend sees incremental updates
- After all OPs: envelope + stability recomputed

### Invalidation Service

Central module for dirty-marking, called by event handlers:

```python
async def invalidate_operating_points(aeroplane_id):
    ops = get_operating_points(aeroplane_id)
    for op in ops:
        if op.status not in ("DIRTY", "COMPUTING"):
            op.previous_results = op.computed_results
            op.status = "DIRTY"

async def invalidate_stability(aeroplane_id): ...
async def invalidate_envelope(aeroplane_id): ...
```

### Existing Services: Changes Required

Each service emits one event after its write:

```python
# wing_service.py
async def update_wing(db, aeroplane_id, wing_name, data):
    # ... existing logic ...
    await emit("geometry_changed", aeroplane_id=aeroplane_id)
```

Affected: wing_service (update_wing, update_xsec, add/remove_spar,
add/remove_ted), fuselage_service (update_fuselage, update_xsec),
assumptions_service (update, switch_source), operating_point_service
(update_deflections).

## Frontend Architecture

### Navigation

Analysis step expanded with sub-tabs via URL query parameter:

```
/workbench/analysis?tab=assumptions
/workbench/analysis?tab=operating
/workbench/analysis?tab=polar
/workbench/analysis?tab=stability
/workbench/analysis?tab=envelope
```

### Tab Badges

Backend-driven via single endpoint:

```
GET /v2/aeroplanes/{id}/analysis-status
→ {
    "assumptions_warnings": 2,
    "operating_points_dirty": 3,
    "operating_points_computing": 1,
    "operating_points_total": 11,
    "stability_dirty": true,
    "envelope_dirty": true
  }
```

### SWR Polling Strategy

| Hook | Endpoint | Polls when |
|---|---|---|
| useAssumptions(id) | GET /assumptions | Never (stable) |
| useOperatingPoints(id) | GET /operating-points | 2s if any dirty/computing |
| useStabilityResult(id) | GET /stability | 2s if dirty |
| useFlightEnvelope(id) | GET /flight-envelope | 3s if dirty |
| useAnalysisStatus(id) | GET /analysis-status | 2s if anything dirty |

Polling activates only when needed and stops automatically when all
states resolve.

### Polar Tab Extension

Existing polar/sweep tab gains OP integration:

- "From Operating Point" selector pre-fills config from a stored OP
- "Save to Operating Point" writes sweep results as calculated values
  into assumptions (CL_max from max CL, Cd0 from zero-lift drag)

### New Components

```
components/workbench/
  ├─ AnalysisTabBar.tsx                  — PillToggle with badges
  ├─ AssumptionsPanel.tsx                — Assumptions tab content
  │   └─ AssumptionRow.tsx               — Single assumption with badge + toggle
  ├─ OperatingPointsPanel.tsx            — Table + drawer layout
  │   ├─ OperatingPointTable.tsx         — Left table
  │   └─ OperatingPointDrawer.tsx        — Right detail drawer
  │       └─ DeflectionOverrideRow.tsx   — Deflection input per control surface
  ├─ StabilityPanel.tsx                  — Side view + markers
  │   ├─ StabilitySideView.tsx           — Plotly 2D schematic with overlay
  │   └─ MarkerDetailBox.tsx             — Detail popup on marker selection
  ├─ EnvelopePanel.tsx                   — Tab wrapper for Performance/V-n
  │   ├─ PerformanceOverview.tsx         — KPI cards + radar chart
  │   └─ VnDiagram.tsx                   — V-n Plotly chart with OP markers
  ├─ AnalysisConfigPanel.tsx             — existing, extended with OP source
  └─ AnalysisViewerPanel.tsx             — existing
```

## MCP Tools (for LLM Advisor)

Each API endpoint exposed as an MCP tool:

```
── Design Assumptions ──
set_design_assumption(aeroplane_id, param, value)
get_design_assumptions(aeroplane_id)
switch_assumption_source(aeroplane_id, param, source)

── Operating Points ──
create_operating_point(aeroplane_id, name, velocity, alpha, ...)
list_operating_points(aeroplane_id)
get_operating_point(aeroplane_id, op_id)
update_operating_point(aeroplane_id, op_id, ...)
set_control_deflections(aeroplane_id, op_id, deflections)
delete_operating_point(aeroplane_id, op_id)
generate_default_operating_points(aeroplane_id)
trim_all(aeroplane_id)
trim_operating_point(aeroplane_id, op_id)

── Stability ──
get_stability(aeroplane_id)
compute_stability(aeroplane_id, solver)

── Flight Envelope ──
get_flight_envelope(aeroplane_id)
compute_flight_envelope(aeroplane_id)

── Jobs & Status ──
get_analysis_status(aeroplane_id)
wait_for_jobs(aeroplane_id, timeout_s)
```

`wait_for_jobs` is essential for the LLM workflow: after a geometry
change, the advisor waits for results before interpreting them.

## Sequencing

```
Phase 1: Foundation
  #424 — Design Assumptions Layer (model + service + API + frontend tab)
  #416 — OperatingPoint Deflection Overrides (schema + API)

Phase 2: Core Engine
  #415 — AVL Runner Refactor (prerequisite for clean trim)
  Event System + Invalidation Service + Background Jobs (cross-cutting)

Phase 3: Trim
  #418 — AVL Trim via indirect constraints
  #419 — AeroBuildup Trim via optimization loop

Phase 4: Stability & Envelope
  #421 — NP + Static Margin calculation + API
  #423 — Stability Side-View Overlay (frontend)
  #420 — Mass/CG as design parameters with what-if sweeps
  #422 — Flight Envelope auto-generation + frontend

Phase 5: Polish
  Inline deltas on all panels
  Tab badges with analysis-status endpoint
  Dirty banners + re-compute flows
  MCP tool registration
```

## Out of Scope

- **Snapshot/Versioning** — separate issue; inline deltas bridge the gap
- **LLM Advisor chat component** — separate epic; uses MCP tools defined here
- **Propulsion integration** (#197, #199) — parallel; feeds into assumptions later
- **Multi-user / concurrent editing** — single maintainer, no locking needed
