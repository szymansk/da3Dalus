# Trim Result Interpretation — Design Spec

Issue: GH#440 — feat: trim result interpretation — designer feedback per operating point  
Parent: GH#417 — Operating Point Simulation  
Dependencies: #439 (control surface roles — merged), #434 (OP table/drawer — merged)

## Scope Decision

Issue #440 describes three subsystems. This spec covers **only the first
and third** — trim enrichment and frontend feedback. The control surface
mixing & gains subsystem (AVL multi-CONTROL, SgnDup, differential throw,
flaperon decomposition) is deferred to a follow-up issue — it requires
AVL geometry file generation changes and AeroSandbox dual-variable
modeling that are independent of the enrichment work.

### In Scope

1. Backend: compute and persist trim enrichment data per operating point
2. Frontend: display enrichment in the OP detail drawer
3. Analysis goal annotations per OP type

### Out of Scope (follow-up issues)

- Control surface mixing & gains (AVL multi-CONTROL, SgnDup)
- Flaperon/elevon symmetric + differential decomposition
- AeroSandbox dual-role surface modeling
- Stability derivatives from AeroSandbox perturbation analysis
- Cross-OP comparison view
- CG limit analysis

## Problem

The trim solver produces raw equilibrium results (alpha, control
deflections, residual moments). Designers must manually interpret these
to answer their actual questions: "Is my elevator big enough?", "Am I
close to stall?", "What does this trim point mean for my design?"

The app should do this interpretation automatically and present it as
actionable feedback: authority bar charts, threshold warnings, and
plain-language analysis goals.

## Design

### 1. Enrichment Data Model

Add a single JSON column `trim_enrichment` to `OperatingPointModel`.
This follows the existing pattern of JSON columns (`controls`,
`warnings`, `control_deflections`) on the same table.

**Schema** (`TrimEnrichment` — Pydantic model, serialized to JSON):

```python
class DeflectionReserve(BaseModel):
    deflection_deg: float        # actual deflection at trim
    max_pos_deg: float           # mechanical limit (positive direction)
    max_neg_deg: float           # mechanical limit (negative direction)
    usage_fraction: float        # |deflection| / limit_in_direction, 0.0–1.0+

class DesignWarning(BaseModel):
    level: Literal["info", "warning", "critical"]
    category: str                # "authority", "trim_quality", "stall_proximity"
    surface: str | None          # control surface name, if applicable
    message: str                 # human-readable

class TrimEnrichment(BaseModel):
    analysis_goal: str           # e.g. "Can the aircraft trim near stall? ..."
    trim_method: str             # "opti", "grid_search", "avl", "aerobuildup"
    trim_score: float | None     # quality metric from solver (lower = better)
    trim_residuals: dict[str, float]  # {"cm": 0.001, "cy": 0.0}
    deflection_reserves: dict[str, DeflectionReserve]
    design_warnings: list[DesignWarning]
```

### 2. Analysis Goal Lookup

Static mapping from OP name → analysis goal description. Each
auto-generated OP name (cruise, stall_near_clean, takeoff_climb, etc.)
maps to a one-line designer question.

```python
_ANALYSIS_GOALS: dict[str, str] = {
    "stall_near_clean": "Can the aircraft trim near stall? How much elevator remains?",
    "takeoff_climb": "What flap + elevator setting gives safe climb at takeoff speed?",
    "cruise": "What is the drag-minimal trim at cruise speed?",
    "loiter_endurance": "What trim gives minimum sink for max loiter endurance?",
    "max_level_speed": "Can the aircraft trim at Vmax? Is the tail adequate?",
    "approach_landing": "What flap + elevator trim for safe approach speed?",
    "turn_n2": "How much aileron + rudder for coordinated turn at 2g?",
    "dutch_role_start": "How does the aircraft respond to sideslip? Is yaw damping adequate?",
    "best_angle_climb_vx": "What trim gives the steepest climb for obstacle clearance?",
    "best_rate_climb_vy": "What trim gives the fastest altitude gain?",
    "max_range": "What trim maximizes ground distance per unit energy?",
    "stall_with_flaps": "How does stall behavior change with flaps deployed?",
}
```

For user-created OPs (via `trim_operating_point_for_aircraft`), the
analysis goal defaults to "User-defined trim point".

### 3. Deflection Reserve Computation

After each trim solve, iterate over all control surfaces in the ASB
airplane and compute:

```
For each surface with a solved deflection:
  direction = sign(deflection)
  limit = max_pos_deg if direction >= 0 else max_neg_deg
  usage_fraction = |deflection| / limit   (clamped to 0 if limit == 0)
```

Mechanical limits come from the ASB airplane object. AeroSandbox
`ControlSurface` stores `deflection` as the current deflection angle,
but the limits are defined in the da3Dalus data model:
- `TrailingEdgeDeviceDetailSchema.positive_deflection_deg`
- `TrailingEdgeDeviceDetailSchema.negative_deflection_deg`

These need to be threaded through to the enrichment function. The
simplest approach: build a `limits` dict during the same airplane
traversal that `_detect_control_capabilities()` performs, mapping
`control_name → (max_pos_deg, max_neg_deg)`.

### 4. Design Warning Generation

Threshold-based, using deflection reserves and trim quality:

| Condition | Level | Category | Message |
|-----------|-------|----------|---------|
| usage_fraction > 0.8 | warning | authority | "{surface}: 80%+ authority used — surface may be undersized" |
| usage_fraction > 0.95 | critical | authority | "{surface}: near mechanical limit — redesign needed" |
| trim_score > 0.1 | warning | trim_quality | "Poor trim quality — equilibrium not fully achieved" |
| trim_score > 0.5 | critical | trim_quality | "Trim failed to converge — results unreliable" |
| status == LIMIT_REACHED | critical | authority | "Optimizer hit a constraint boundary — check all surfaces" |

### 5. Enrichment Integration Points

**`generate_default_set_for_aircraft()`:**
After each `_trim_or_estimate_point()` call, compute enrichment from the
`TrimmedPoint` + airplane + limits dict. Store in the `TrimmedPoint`
(add `trim_enrichment: TrimEnrichment | None` field). Persist to DB in
`_persist_point_set()`.

**`trim_operating_point_for_aircraft()`:**
Same enrichment after the single trim solve.

**API response:**
Extend `StoredOperatingPointRead` to include `trim_enrichment: dict | None`.
The JSON column is returned as-is (dict), matching existing patterns for
`controls` and `control_deflections`.

### 6. Database Migration

Single migration adding `trim_enrichment` (JSON, nullable, no default)
to the `operating_points` table. Existing rows get NULL — enrichment is
computed on next generate/trim.

### 7. Frontend: OP Detail Drawer Enhancement

Extend `OperatingPointsPanel.tsx` detail drawer with three new sections:

**a) Analysis Goal Banner**
At the top of the detail drawer, a highlighted banner:
> **Analysis Goal:** Can the aircraft trim near stall? How much elevator
> authority remains?

Only shown when `trim_enrichment?.analysis_goal` exists.

**b) Control Authority Section**
Horizontal bar chart per control surface:
```
Elevator  ████████░░░░░  62%
Aileron   ██░░░░░░░░░░░  15%
Rudder    █░░░░░░░░░░░░   8%
```

Color coding:
- Green (< 60%): healthy margin
- Yellow (60–80%): moderate usage
- Orange (80–95%): high usage — warning
- Red (> 95%): critical — near limit

Implemented as styled divs (no chart library needed for horizontal bars).

**c) Design Warnings**
List of warning badges below the authority chart:
- Info: blue badge
- Warning: yellow/amber badge  
- Critical: red badge

Each shows the message text. Warnings also appear as small icons in the
OP table row for at-a-glance scanning.

### 8. TypeScript Types

```typescript
interface DeflectionReserve {
  deflection_deg: number;
  max_pos_deg: number;
  max_neg_deg: number;
  usage_fraction: number;
}

interface DesignWarning {
  level: "info" | "warning" | "critical";
  category: string;
  surface: string | null;
  message: string;
}

interface TrimEnrichment {
  analysis_goal: string;
  trim_method: string;
  trim_score: number | null;
  trim_residuals: Record<string, number>;
  deflection_reserves: Record<string, DeflectionReserve>;
  design_warnings: DesignWarning[];
}
```

Extend `StoredOperatingPoint` to include
`trim_enrichment: TrimEnrichment | null`.

## Acceptance Criteria

1. **Enrichment computed for all generated OPs:**
   `generate_default_set_for_aircraft()` returns OPs with non-null
   `trim_enrichment` containing `analysis_goal`, `deflection_reserves`,
   and `design_warnings`.

2. **Enrichment computed for single-trim OPs:**
   `trim_operating_point_for_aircraft()` returns an OP with non-null
   `trim_enrichment`.

3. **Deflection reserves accurate:**
   For a trimmed OP with known deflection (e.g., elevator at -5° with
   limit ±25°), `usage_fraction` equals 0.2 (= 5/25).

4. **Warnings generated from thresholds:**
   An OP with > 80% elevator usage gets a "warning" level
   DesignWarning. An OP with > 95% gets "critical".

5. **Analysis goals mapped:**
   All 12 auto-generated OP names map to human-readable goal strings.
   User-created OPs get the default goal.

6. **DB migration applies cleanly:**
   `alembic upgrade head` adds `trim_enrichment` column without errors.
   Existing OPs have NULL enrichment.

7. **API returns enrichment:**
   `GET /operating_points/{id}` includes `trim_enrichment` in response
   when present.

8. **Frontend analysis goal banner:**
   OP detail drawer shows the analysis goal as a highlighted banner.

9. **Frontend authority bar chart:**
   Detail drawer shows horizontal bars per surface with color-coded
   usage fractions.

10. **Frontend warning badges:**
    Design warnings display as colored badges in the detail drawer.
    Warning/critical OPs show an indicator icon in the table row.

11. **Backward compatible:**
    OPs without enrichment (created before migration) display normally
    without errors.

12. **Tests:**
    - Backend unit tests for enrichment computation (deflection reserve
      math, warning thresholds, analysis goal lookup)
    - Backend integration test: generate OPs and verify enrichment is
      persisted
    - Frontend unit tests: enrichment display components render
      correctly with and without enrichment data
