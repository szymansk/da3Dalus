# Flight Envelope Analysis — Design Spec

**Issue:** #422  
**Epic:** #417 (Operating Point Simulation)  
**Date:** 2026-05-07  
**Dependencies:** #420 (mass/CG — merged), #424 (design assumptions — merged)

---

## 1. Goal

Add a flight envelope analysis feature that computes V-n diagram curves
and performance KPIs from existing operating points and design
assumptions, then displays them in a new "Envelope" tab in the analysis
workbench.

Users get a complete performance picture — stall speed, best L/D,
max load factor, dive speed — without manually interpreting raw
operating point data.

---

## 2. Scope

### In scope

- **Backend**: Flight envelope computation service, schemas, DB cache
  model, two REST endpoints (GET cached / POST compute), two MCP tools
- **Frontend**: New "Envelope" tab with Performance Overview (KPI cards)
  and V-n Diagram (Plotly chart) sub-views
- All computation uses existing infrastructure: design assumptions
  (mass, cl_max, g_limit), operating points (trimmed results), and
  wing geometry (reference area S)

### Out of scope

- Auto-recompute on trim completion (event integration — future PR)
- Propulsion-dependent points (requires #197/#199)
- Radar chart in Performance Overview (can add later; KPI cards suffice)
- Flight profile editing from the envelope tab

---

## 3. Backend Design

### 3.1 Schemas (`app/schemas/flight_envelope.py`)

```python
class VnPoint(BaseModel):
    velocity_mps: float
    load_factor: float

class VnCurve(BaseModel):
    positive: list[VnPoint]    # positive g boundary
    negative: list[VnPoint]    # negative g boundary
    dive_speed_mps: float      # V_d = 1.4 * V_max_level

class PerformanceKPI(BaseModel):
    label: str                 # e.g. "stall_speed"
    display_name: str          # e.g. "Stall Speed"
    value: float
    unit: str                  # e.g. "m/s"
    source_op_id: int | None   # link to the operating point
    confidence: str            # "trimmed" | "estimated" | "limit"

class FlightEnvelopeRead(BaseModel):
    id: int
    aeroplane_id: str
    vn_curve: VnCurve
    kpis: list[PerformanceKPI]
    operating_points: list[VnMarker]
    assumptions_snapshot: dict  # mass, cl_max, g_limit used
    computed_at: datetime

class VnMarker(BaseModel):
    op_id: int
    name: str
    velocity_mps: float
    load_factor: float
    status: str                # TRIMMED / NOT_TRIMMED / LIMIT_REACHED
    label: str                 # e.g. "cruise", "stall", "best_ld"

class ComputeEnvelopeRequest(BaseModel):
    force_recompute: bool = False
```

### 3.2 DB Model (`app/models/flight_envelope_model.py`)

Single table `flight_envelopes` with:
- `id` (PK), `aeroplane_id` (FK, unique — one envelope per aeroplane)
- `vn_curve_json` (JSON), `kpis_json` (JSON), `markers_json` (JSON)
- `assumptions_snapshot` (JSON — records which assumption values were used)
- `computed_at` (timestamp)
- `is_stale` (boolean — set true when assumptions or OPs change)

One-to-one with AeroplaneModel. Alembic migration required.

### 3.3 Service (`app/services/flight_envelope_service.py`)

**`compute_flight_envelope(db, aeroplane_id)`**

1. Load design assumptions via `get_effective_assumption_value()`:
   mass_kg, cl_max, g_limit (from `app/services/mass_cg_service.py`)
2. Load wing reference area S (m^2) from ASB airplane projected
   planform area (via existing aeroplane → ASB converter)
3. Load atmosphere density rho at profile altitude (default sea level)
4. Compute V-n curves:
   ```
   V_stall = sqrt(2 * mass * g / (rho * S * cl_max))
   n_pos(V) = min(0.5 * rho * V^2 * S * cl_max / (mass * g), g_limit)
   n_neg(V) = max(0.5 * rho * V^2 * S * cl_min / (mass * g), -0.4 * g_limit)
   V_d = 1.4 * V_max_level  (from flight profile or assumption)
   ```
5. Load existing operating points for the aeroplane
6. Map each OP to a (V, n) marker on the V-n diagram
7. Derive performance KPIs:

| KPI | How derived |
|-----|-------------|
| `stall_speed` | V_stall from cl_max + mass, or lowest V with TRIMMED status |
| `best_ld_speed` | V at max L/D from operating points (if available) |
| `min_sink_speed` | V at max CL^1.5/CD (if available) |
| `max_speed` | From flight profile `max_level_speed_mps` or highest trimmed V |
| `max_load_factor` | Highest n with converged trim |
| `dive_speed` | 1.4 * max_speed |

8. Persist to `flight_envelopes` table (upsert)
9. Return `FlightEnvelopeRead`

**`get_flight_envelope(db, aeroplane_id)`**
- Return cached result from DB, or 404 if never computed

**Helper: `get_wing_reference_area(db, aeroplane_id) -> float`**
- Sum projected area of all wing panels
- Uses existing converter: aeroplane → ASB airplane → sum wing areas

**Helper: `_compute_cl_min(cl_max) -> float`**
- Approximation: cl_min = -0.8 * cl_max (inverted flight coefficient)
- Sufficient for V-n negative boundary

### 3.4 Endpoints (`app/api/v2/endpoints/aeroplane/flight_envelope.py`)

```
GET  /v2/aeroplanes/{aeroplane_id}/flight-envelope
POST /v2/aeroplanes/{aeroplane_id}/flight-envelope/compute
```

Both return `FlightEnvelopeRead`. GET returns cached (404 if none).
POST computes fresh and returns result.

Thin endpoints — delegate to service layer.

### 3.5 MCP Tools

```python
@mcp.tool()
def get_flight_envelope(aeroplane_id: str) -> FlightEnvelopeRead: ...

@mcp.tool()
def compute_flight_envelope(aeroplane_id: str) -> FlightEnvelopeRead: ...
```

Follow existing MCP registration pattern in `app/mcp_server.py`.

---

## 4. Frontend Design

### 4.1 New "Envelope" Tab

Add to the existing `AnalysisViewerPanel.tsx` TABS array. Tab key:
`"Envelope"`. When active, renders `EnvelopePanel`.

### 4.2 Component Structure

```
EnvelopePanel.tsx
  ├─ PerformanceOverview.tsx   — KPI cards grid
  └─ VnDiagram.tsx             — Plotly V-n chart with OP markers
```

**Toggle:** A segmented control at the top switches between
"Performance" and "V-n Diagram" views.

### 4.3 PerformanceOverview

Grid of KPI cards (3 columns on desktop, 2 on tablet, 1 on mobile):
- Each card shows: icon, label, value + unit, confidence badge
- Confidence: green (trimmed), yellow (estimated), red (limit)
- Cards are clickable — could link to the source operating point
  (stretch goal, not required for v1)

KPIs displayed: Stall Speed, Best L/D Speed, Min Sink Speed,
Max Speed, Max Load Factor, Dive Speed.

### 4.4 VnDiagram

Plotly chart with:
- X-axis: Velocity (m/s)
- Y-axis: Load factor (g)
- Filled area between positive and negative V-n curves
- Operating points as scatter markers:
  - Filled circle (TRIMMED), half circle (NOT_TRIMMED),
    open circle (LIMIT_REACHED)
- Hover shows OP name, V, n, status
- Dark theme styling matching existing Plotly charts

### 4.5 Hook: `useFlightEnvelope(aeroplaneId)`

SWR hook pattern matching existing hooks:
- `data: FlightEnvelopeRead | null`
- `isLoading: boolean`
- `compute(): Promise<void>` — triggers POST, then mutates SWR cache
- `isComputing: boolean`

### 4.6 Config Panel

When "Envelope" tab is active, the config modal shows:
- Current assumptions summary (mass, cl_max, g_limit) — read-only
- Link to full Assumptions panel for editing
- "Compute Envelope" button (triggers POST)

---

## 5. Data Flow

```
User clicks "Compute Envelope"
  → POST /v2/aeroplanes/{id}/flight-envelope/compute
    → flight_envelope_service.compute_flight_envelope()
      → Load design assumptions (mass, cl_max, g_limit)
      → Load wing geometry → compute S
      → Compute V-n curves (pure math)
      → Load stored operating points
      → Map OPs to V-n markers
      → Derive performance KPIs
      → Upsert to flight_envelopes table
    ← Return FlightEnvelopeRead
  ← SWR cache updated
  → UI re-renders with KPIs + V-n diagram
```

---

## 6. Acceptance Criteria

### Backend
- [ ] `FlightEnvelopeModel` DB table with Alembic migration
- [ ] `flight_envelope.py` schema with VnCurve, KPIs, markers
- [ ] `flight_envelope_service.py` with compute + get functions
- [ ] V-n curve computation is correct: positive/negative boundaries,
      dive speed, stall speed
- [ ] KPIs derived from operating points + assumptions
- [ ] GET endpoint returns cached envelope (404 if none)
- [ ] POST endpoint computes and returns fresh envelope
- [ ] MCP tools registered and functional
- [ ] Unit tests: V-n curve math, KPI derivation, endpoint responses
- [ ] Integration tests: compute with real aeroplane fixture

### Frontend
- [ ] "Envelope" tab appears in AnalysisViewerPanel
- [ ] PerformanceOverview displays KPI cards with correct values
- [ ] VnDiagram renders V-n curves with operating point markers
- [ ] Toggle between Performance and V-n views works
- [ ] Compute button triggers fresh computation
- [ ] Loading and empty states handled
- [ ] Dark theme consistent with existing charts
- [ ] Unit tests for EnvelopePanel, PerformanceOverview, VnDiagram

---

## 7. Unit Considerations

- Wing reference area (S): computed from ASB airplane in m^2
- Velocities: m/s throughout
- Mass: kg from design assumptions
- Load factor: dimensionless (g units)
- Angles: radians in stored OPs, degrees in display
- All computation in SI; frontend formats for display
