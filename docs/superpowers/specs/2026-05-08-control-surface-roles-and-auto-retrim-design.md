# Control Surface Roles & Auto-Retrim Pipeline

**Date:** 2026-05-08
**Tickets:** #439 (Role Dropdown), #438 (Auto-Retrim Pipeline)
**Epic:** #417 — Operating Point Simulation

---

## Overview

Two complementary changes to close the iterative design loop:

1. **#439** — Replace free-text control surface names with a standardized
   `role` enum. Fixes brittle substring matching in the OP generator,
   enables flap deployment in takeoff/landing OPs, and simplifies the
   TED edit dialog.

2. **#438** — Domain event system, invalidation service, and background
   job tracker that automatically re-trims operating points when geometry
   or design assumptions change.

---

## #439 — Control Surface Role Dropdown

### ControlSurfaceRole Enum

Eight roles — every role is supported by the trim solver:

```python
class ControlSurfaceRole(str, Enum):
    ELEVATOR    = "elevator"
    STABILATOR  = "stabilator"
    RUDDER      = "rudder"
    AILERON     = "aileron"
    ELEVON      = "elevon"
    FLAP        = "flap"
    FLAPERON    = "flaperon"
    RUDDERVATOR = "ruddervator"
```

No `other` or `spoiler` — if it's not in the trim solver, it's not in
the enum.

### Role Properties (static lookup, no DB column)

```python
ROLE_PROPERTIES: dict[ControlSurfaceRole, dict] = {
    "elevator":    {"symmetric": True,  "pitch": True,  "roll": False, "yaw": False, "high_lift": False},
    "stabilator":  {"symmetric": True,  "pitch": True,  "roll": False, "yaw": False, "high_lift": False},
    "rudder":      {"symmetric": True,  "pitch": False, "roll": False, "yaw": True,  "high_lift": False},
    "aileron":     {"symmetric": False, "pitch": False, "roll": True,  "yaw": False, "high_lift": False},
    "elevon":      {"symmetric": False, "pitch": True,  "roll": True,  "yaw": False, "high_lift": False},
    "flap":        {"symmetric": True,  "pitch": False, "roll": False, "yaw": False, "high_lift": True},
    "flaperon":    {"symmetric": False, "pitch": False, "roll": True,  "yaw": False, "high_lift": True},
    "ruddervator": {"symmetric": False, "pitch": True,  "roll": False, "yaw": True,  "high_lift": False},
}
```

`symmetric` is derived from role — not stored in DB, not editable by user.

### Schema Changes

**`TrailingEdgeDeviceDetailSchema`:**

```python
role: ControlSurfaceRole              # required, dropdown in UI
label: str | None = None              # optional, freetext ("Left Aileron")
```

`name` becomes a computed property: `label or role.value` (backwards compat).
`symmetric` is removed from the writable schema — derived from
`ROLE_PROPERTIES[role]["symmetric"]`.

**`ControlSurfaceSchema`** (ASB bridge):

```python
role: ControlSurfaceRole
name: str                             # = label or role.value
hinge_point: float = 0.8
symmetric: bool                       # from ROLE_PROPERTIES
deflection: float = 0.0
```

### Database Migration

```sql
ALTER TABLE wing_xsec_trailing_edge_devices
  ADD COLUMN role VARCHAR NOT NULL DEFAULT 'elevator';
ALTER TABLE wing_xsec_trailing_edge_devices
  ADD COLUMN label VARCHAR;
```

- Data migration infers `role` from existing `name` via substring matching
  (same tokens the OP generator uses today: "elevator", "aileron", etc.).
  Matched TEDs get the correct role. Unmatched TEDs keep `role='elevator'`
  (the NOT NULL default) — this is intentionally wrong to force manual
  correction. The API returns a warning for any aeroplane that has TEDs
  whose `label` is NULL and `role` doesn't match the old `name` pattern.
- `symmetric` column stays in DB but is ignored by code — `ROLE_PROPERTIES`
  is the source of truth. Column is not dropped to avoid destructive
  migration on a test database.

### OP Generator Refactoring

**`_detect_control_capabilities()` rewrite — role-based:**

```python
def _detect_control_capabilities(asb_airplane):
    roles = set()
    controls = []
    for wing in asb_airplane.wings:
        for xsec in wing.xsecs:
            for cs in xsec.control_surfaces:
                roles.add(cs.role)
                controls.append({"name": cs.name, "role": cs.role})

    props = ROLE_PROPERTIES
    return {
        "has_pitch_control": any(props[r]["pitch"] for r in roles),
        "has_roll_control":  any(props[r]["roll"] for r in roles),
        "has_yaw_control":   any(props[r]["yaw"] for r in roles),
        "has_high_lift":     any(props[r]["high_lift"] for r in roles),
        "controls": controls,
    }
```

**`_pick_control_name()` rewrite:**

```python
def _pick_control_name(controls, roles):
    for c in controls:
        if c["role"] in roles:
            return c["name"]
    return None
```

**Trim variable assignment per OP:**

| OP | Pitch roles | Roll roles | Yaw roles | High-lift roles |
|----|-------------|------------|-----------|-----------------|
| cruise, stall, climb, loiter, max_range, max_level_speed | elevator, stabilator, elevon, ruddervator | — | — | — |
| turn_n2 | same | aileron, elevon, flaperon | rudder, ruddervator | — |
| dutch_role_start | — | — | rudder, ruddervator | — |
| takeoff_climb | pitch roles | — | — | flap, flaperon |
| approach_landing | pitch roles | — | — | flap, flaperon |

**Flap deployment** — fixed deflections (not Opti variables):

- `takeoff_climb`: high-lift surface set to 15° (hardcoded MVP default)
- `approach_landing`: high-lift surface set to 30° (hardcoded MVP default)
- Long-term: values come from Flight Profile or Design Assumptions

### ASB ControlSurface — passing `role` through

The converter sets `role` as a custom attribute on the ASB object:

```python
cs = asb.ControlSurface(name=name, symmetric=symmetric, ...)
cs.role = role
```

ASB doesn't know about `role` — `_detect_control_capabilities` reads it.

### Frontend: TedEditDialog

**Fields:**

1. **Role** — dropdown (required, first field). Options: 8 enum values
   with readable labels.
2. **Label** — text input (optional). Placeholder: "Optional — e.g. Left
   Aileron, Inboard Flap".
3. **Symmetric checkbox removed** — replaced by read-only badge
   ("symmetric" / "differential") derived from selected role.

**Tree display:** `TED: {label or role}` — chip stays `TED`.

**API call change:**

```typescript
// before
{ name: "Elevator", rel_chord_root: 0.8, symmetric: true }

// after
{ role: "elevator", label: "Left Elevator", rel_chord_root: 0.8 }
```

---

## #438 — Event-Driven Auto-Retrim Pipeline

### Domain Event System (`app/core/events.py`)

Synchronous in-process pub/sub bus:

```python
class DomainEvent:
    aeroplane_id: int
    timestamp: datetime

class GeometryChanged(DomainEvent):
    source_model: str   # "WingModel", "WingXSecModel", "FuselageModel"

class AssumptionChanged(DomainEvent):
    parameter_name: str  # "mass", "cg_x", "cl_max", etc.

class EventBus:
    _subscribers: dict[type[DomainEvent], list[Callable]]
    def subscribe(self, event_type, handler): ...
    def publish(self, event): ...
```

**Publishers:**
- SQLAlchemy listeners (`avl_geometry_events.py`, `stability_events.py`)
  publish `GeometryChanged` after dirty-flagging.
- `design_assumptions_service.py` publishes `AssumptionChanged` after
  `update_assumption()` and `switch_source()`.

**Subscribers:** Invalidation Service (sole subscriber in MVP).

**Lifecycle:** Module-level singleton, wired in `app/main.py` at startup.

### Invalidation Service (`app/services/invalidation_service.py`)

Subscribes to events, marks dependent data as DIRTY, delegates to
job tracker.

**Invalidation rules:**

```
GeometryChanged →
    all OPs for aeroplane     → status = DIRTY
    StabilityResult            → status = DIRTY   (as today)
    AvlGeometryFile            → is_dirty = True   (as today)
    FlightEnvelope             → status = DIRTY

AssumptionChanged →
    parameter ∈ {mass, cg_x, cl_max, g_limit}
        → FlightEnvelope → status = DIRTY
    parameter ∈ {mass, cg_x}
        → all OPs → status = DIRTY (CL_target changes)
    parameter ∈ {cd0, target_static_margin}
        → no OP invalidation
```

**Consolidation:** After this refactoring, the existing SQLAlchemy
listeners only publish events. All dirty-flagging logic moves into the
Invalidation Service — single source of truth, testable in isolation.

### New OP Statuses

```python
class OperatingPointStatus(str, Enum):
    TRIMMED       = "TRIMMED"
    NOT_TRIMMED   = "NOT_TRIMMED"
    LIMIT_REACHED = "LIMIT_REACHED"
    DIRTY         = "DIRTY"
    COMPUTING     = "COMPUTING"
```

### Background Job Tracker (`app/core/background_jobs.py`)

In-memory job management per aeroplane with debounce:

```python
class RetrimJob:
    aeroplane_id: int
    status: Literal["DEBOUNCING", "QUEUED", "COMPUTING", "DONE", "FAILED"]
    dirty_op_ids: list[int]
    completed_op_ids: list[int]
    failed_op_ids: list[int]
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None

class JobTracker:
    _jobs: dict[int, RetrimJob]
    _debounce_tasks: dict[int, asyncio.Task]
    DEBOUNCE_SECONDS: float = 2.0
```

**Flow:**

```
invalidation_service calls job_tracker.schedule_retrim(aeroplane_id)
  │
  ├── Debounce timer running for this aeroplane?
  │     └── Yes → cancel timer, start new (reset to 2s)
  │
  └── After 2s silence:
        ├── Load all DIRTY OPs from DB
        ├── Job status → COMPUTING
        ├── For each OP sequentially:
        │     ├── OP status → COMPUTING
        │     ├── call _trim_or_estimate_point() (AeroSandbox Opti)
        │     ├── persist result to DB
        │     └── OP status → TRIMMED / NOT_TRIMMED / LIMIT_REACHED
        └── Job status → DONE (or FAILED on exception)
```

**Solver:** Always AeroSandbox Opti (fast, ~seconds for 11 OPs).
AVL/AeroBuildup trim remains on-demand only.

**New changes during retrim:** Current run is not aborted. After
completion, tracker checks for new DIRTY OPs → new debounce cycle.

**Concurrency:** Max 1 retrim job per aeroplane. Different aeroplanes
can run in parallel.

**Shutdown:** On app shutdown, cancel running tasks, reset COMPUTING OPs
back to DIRTY.

### Analysis Status Endpoint

`GET /v2/aeroplanes/{aeroplane_id}/analysis-status`

```python
class AnalysisStatusResponse(BaseModel):
    op_counts: dict[OperatingPointStatus, int]
    total_ops: int
    retrim_active: bool
    retrim_debouncing: bool
    last_computation: datetime | None
```

No new service — endpoint queries OP table (grouped by status) and
JobTracker directly.

### Frontend Integration

**Hook:** `useAnalysisStatus(aeroplaneId)`
- Polls only when `retrim_active || retrim_debouncing || dirty_count > 0`
- Poll interval: 2s while active, stops when all TRIMMED

**Status indicator** in Analysis workbench header:
- All TRIMMED → green dot + "All trimmed"
- DIRTY present → orange dot + "3 points outdated"
- COMPUTING → spinner + "Re-trimming 2/11..."
- DEBOUNCING → gray dot + "Waiting for changes..."

Compact indicator next to the tab title. Click navigates to OP table
(#434) once available.

---

## Out of Scope

These are explicitly deferred to other tickets:

- **Control surface mixing & gains** (#440) — AVL gain vectors, SgnDup
  overrides, dual-role symmetric+differential decomposition
- **Trim result interpretation & designer feedback** (#440) — deflection
  reserve, control authority charts, stability derivatives at trim point
- **OP table & trim controls UI** (#434) — table component, trim buttons
- **Deflection override UI** (#435) — per-OP deflection editing
- **Mass sweep chart** (#436) — visualization
- **CG comparison warning** (#437) — assumptions panel banner
- **WebSocket/SSE** — future alternative to SWR polling for status updates
