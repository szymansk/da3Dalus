# Mission Tab Redesign — Mission-driven Design with 7-axis Compliance Spider

**Status:** Design (Brainstorming complete, awaiting user review)
**Author:** Claude Opus 4.7 with user (marc.szymanski)
**Created:** 2026-05-15
**Supersedes:** the current "Coming soon" placeholder in Tab 1 (`MissionObjectives` form + 5-axis pentagon)

## 1. Goal

Replace the placeholder Mission tab with a Mission-driven design system in which the user picks a mission profile, the app proposes physical defaults for the design assumptions, and the resulting design is scored against the mission on a 7-axis compliance spider chart. The user can overlay neighbouring mission profiles to see *where on the design-space* the current aircraft sits — turning the chart from a static dashboard into a design-conversation tool.

The Mission becomes the **first design driver** in the workflow, justifying Tab 1's position. Estimates that historically lived as static `PARAMETER_DEFAULTS` (g_limit, target_static_margin, cl_max, power_to_weight) become Mission-dependent.

## 2. Scope

### In scope (v1)

- New 7-axis radar chart replacing the existing 5-axis pentagon. Axes:
  Stall Safety · Glide · Climb · Cruise · Maneuver · Wing Loading · Field Friendliness.
- Ist + Soll polygon overlay with red "gap" fill showing design-deficit area.
- Multi-mission overlay: user toggles other profiles on/off; chart auto-rescales so all visible polygons fit.
- Mission-relative axis scaling with mission-specific min/max per axis.
- Provenance badge (`●` computed / `○` estimated / `▽` missing) at each axis label.
- Click-on-axis side-drawer with raw value, target, formula, and dependent context values (Provenance B).
- Mission Type dropdown with presets: Trainer · Sport · Sailplane · Wing-Racer · 3D / Acro · STOL / Bush.
- Mission preset auto-applies design-assumption estimates (`estimate_value` only; `calculated_value` from AeroBuildup still wins when active). Visible banner shows the diff and links to the Assumptions tab.
- Migrate field-performance inputs (`runway_length_m`, `runway_type`, `t_static_N`, `takeoff_mode`) from the Assumptions area into a "Field Performance" section of the Mission Objectives form.
- Global unit-system preset (RC-Metric / SI / Imperial). Default: RC-Metric (mm + g/dm² + km/h + g).
- Debounced update (300 ms) on Mission Objectives form input.
- New backend service `mission_kpi_service` aggregating the 7 KPIs from `ComputationContext` + `field_length_service` + V-n data.
- New backend service / table for `MissionObjective` storage per aeroplane, with mission-preset library in code.

### Out of scope (v2 — captured in EPIC)

The following are explicitly deferred to a v2 epic, to be created after this design lands on `main`:

1. **Coaching drawer.** Click-on-axis drawer extended with concrete tuning suggestions ("Wing-Fläche +12 % → Margin 1.53"). Requires per-axis sensitivity analysis (gh-494 pattern generalised).
2. **UAV-specific axes** — Endurance, Range, Payload Fraction. Requires Powertrain + Battery spec in the backend.
3. **8-axis hybrid layout** (5 RC-core + 3 UAV-extension axes that grey out without battery spec).
4. **Per-axis unit override** on top of the global unit-system preset.
5. **Absolute-scale toggle** for cross-mission comparison ("Pro-Mode").
6. **Mission visualisation inside the Assumptions tab** (which mission is active, which estimates came from mission auto-apply, which were user-overridden).
7. **Mission Save with versioning** — keep prior mission revisions for design-comparison.

### Non-goals

- Endurance, Range, Service Ceiling computations (need Powertrain). Tracked in v2.
- Roll-rate KPI (needs AVL roll sweep). Tracked in v2.
- AeroBuildup re-runs caused by mission change (the existing recompute pipeline is unchanged; mission only changes targets and estimate values).

## 3. UX decisions (brainstorming outcomes)

| Question | Decision | Rationale |
|---|---|---|
| Ist + Soll overlay? | Both, always | Red "gap" between Ist and Soll is the pedagogical hook. |
| Where does the chart live? | Existing Tab 1 (Mission) | Already in the right place; full redesign of content. |
| Axes | New 7 axes (no UAV-specific axes in v1) | All computable from existing backend; no ghost axes at launch. |
| Update frequency | Debounced 300 ms | Standard designer-tool pattern; no flicker. |
| Scale type | Mission-relative + multi-mission toggle with auto-rescale | Mission-first app demands mission-first scale. |
| Provenance viz | Mini-badge at axis label | Subtle; polygon shape remains the primary read. |
| Units | Global preset, RC-Metric default | Consistent across all chips, charts, and forms. |
| Click action | Side-drawer with value + formula + provenance | Lehrmoment without overengineering. Coaching deferred to v2. |
| Mission ↔ Assumptions | Auto-apply estimates with banner | `calculated_value` from AeroBuildup overrides estimates anyway, so auto-apply is safe; banner makes the change visible. |

## 4. Architecture

### High-level component map

```
Frontend · Mission Tab
├── MissionCompliancePanel     (left, ~50 % width)
│   ├── MissionRadarChart       (custom SVG, 7 axes)
│   ├── MissionToggleGrid       (mission overlay checkboxes)
│   ├── MissionLegend
│   └── AxisDrawer              (right-sliding panel on axis click)
└── MissionObjectivesPanel     (right, ~50 % width)
    ├── MissionTypeDropdown     (with auto-apply banner on change)
    ├── PerformanceTargetsForm  (6 numeric inputs)
    ├── FieldPerformanceForm    (4 inputs migrated from Assumptions)
    └── CancelSaveButtons

           │ REST                                  │ REST
           ▼                                       ▼
GET /v2/aeroplanes/{uuid}/mission-kpis    GET/PUT /v2/aeroplanes/{uuid}/mission-objectives
                                          GET     /v2/mission-presets

           │                                       │
           ▼                                       ▼
mission_kpi_service                  mission_objective_service
  reads:                                reads/writes:
  - ComputationContext                  - mission_objectives (new table)
  - field_length_service                writes (side-effect on PUT):
  - flight_envelope V-n                 - design_assumptions.estimate_value
                                          (when mission preset auto-applies)
```

### Data flow

1. User opens Mission tab → frontend issues `GET /v2/aeroplanes/{uuid}/mission-objectives` and `GET /v2/aeroplanes/{uuid}/mission-kpis` and `GET /v2/mission-presets`.
2. `mission_kpi_service` reads `aeroplane.assumption_computation_context` + the persisted `mission_objectives` row, computes 7 normalised scores per axis (Ist) and per active mission preset (Soll), bundles them into a `MissionKpiSet`.
3. User edits a field in the objectives form. Frontend debounces 300 ms, then issues `PUT /v2/aeroplanes/{uuid}/mission-objectives` (idempotent). Backend persists. Frontend re-fetches the KPI set; radar redraws.
4. User changes Mission Type. Backend persists the new mission_type and, in the same transaction, writes mission-preset `suggested_estimates` to `design_assumptions.estimate_value` (without touching `calculated_value` or `active_source`). Frontend banner shows the diff and links to the Assumptions tab.
5. User toggles a comparison mission. Frontend issues a re-fetch with `?missions=trainer,sailplane`. Backend returns multiple Soll polygons; frontend recomputes axis ranges and redraws all polygons.

## 5. Backend components

### 5.1 New schemas

`app/schemas/mission_kpi.py`

```python
from typing import Literal
from pydantic import BaseModel, Field

AxisName = Literal[
    "stall_safety", "glide", "climb", "cruise",
    "maneuver", "wing_loading", "field_friendliness",
]
Provenance = Literal["computed", "estimated", "missing"]

class MissionAxisKpi(BaseModel):
    axis: AxisName
    value: float | None       # raw physical value (None when missing)
    unit: str | None          # SI unit; UI converts via global preset
    score_0_1: float | None   # normalised to current mission range
    range_min: float          # range used for normalisation (Soll mission)
    range_max: float
    provenance: Provenance
    formula: str              # human-readable, for the side-drawer
    warning: str | None = None

class MissionTargetPolygon(BaseModel):
    mission_id: str           # "trainer", "sailplane", ...
    label: str                # "Trainer", "Sailplane", ...
    scores_0_1: dict[AxisName, float]

class MissionKpiSet(BaseModel):
    aeroplane_uuid: str
    ist_polygon: dict[AxisName, MissionAxisKpi]
    target_polygons: list[MissionTargetPolygon]     # one per active mission
    active_mission_id: str
    computed_at: str
    context_hash: str         # for stale-detection in FE
```

`app/schemas/mission_objective.py`

```python
class MissionObjective(BaseModel):
    mission_type: str                # FK to mission preset id
    target_cruise_mps: float
    target_stall_safety: float       # V_cruise / V_s1
    target_maneuver_n: float         # g
    target_glide_ld: float
    target_climb_energy: float       # (CL^1.5 / CD)
    target_wing_loading_n_m2: float
    target_field_length_m: float
    # Field-performance inputs (migrated from Assumptions)
    available_runway_m: float
    runway_type: Literal["grass", "asphalt", "belly"]
    t_static_N: float
    takeoff_mode: Literal["runway", "hand_launch", "bungee", "catapult"]

class MissionPresetEstimates(BaseModel):
    """Suggested DesignAssumption estimate_values per mission preset."""
    g_limit: float
    target_static_margin: float
    cl_max: float
    power_to_weight: float
    prop_efficiency: float

class MissionPreset(BaseModel):
    id: str                           # "trainer", "sport", "sailplane", ...
    label: str
    description: str
    target_polygon: dict[AxisName, float]   # score-0-1 polygon
    axis_ranges: dict[AxisName, tuple[float, float]]   # mission-relative scale
    suggested_estimates: MissionPresetEstimates
```

### 5.2 New service

`app/services/mission_kpi_service.py`

```python
def compute_mission_kpis(
    db: Session,
    aeroplane_uuid: str,
    active_mission_ids: list[str],  # ["trainer"] by default; multi for overlay
) -> MissionKpiSet:
    """Aggregate 7 normalised KPI axes from cached context + field length + V-n.

    Reads ComputationContext (V-speeds, polar_by_config, AR, MAC, S_ref) once;
    no AeroBuildup re-run. All KPIs are closed-form from cached data.
    """
```

### 5.3 New models + migration

Two new SQLAlchemy tables:

- `app/models/mission_objective.py` — `mission_objectives` table, one row per aeroplane (FK to `aeroplanes`). Mirrors the Pydantic `MissionObjective`.
- `app/models/mission_preset.py` — `mission_presets` table, one row per preset (Trainer, Sport, Sailplane, …). Mirrors the Pydantic `MissionPreset`.

Storing presets in the DB (rather than as a Python dict) enables future user-extensible presets without code changes, supports versioning, and lets admin tooling edit values without redeploying.

Alembic migration:

1. Create `mission_presets` table.
2. Seed initial presets via a data migration step using a `op.bulk_insert` of the six default presets (Trainer, Sport, Sailplane, Wing-Racer, 3D / Acro, STOL / Bush). Seeded values live in a single `app/services/mission_preset_seed.py` so they're version-controlled and re-applyable.
3. Create `mission_objectives` table.
4. Drop field-performance columns from `design_assumptions` if they exist (`runway_length_m`, `runway_type`, `t_static_N`, `takeoff_mode`). If they only exist in code as `PARAMETER_DEFAULTS` keys without DB persistence, just remove from the assumption-parameter list.
5. Backfill — for existing aeroplanes, create a default `mission_objectives` row preserving the aeroplane's existing field-performance values verbatim (if present in the legacy Assumption data); use Trainer defaults only for fields that were never set.

### 5.4 New endpoints

```
GET    /v2/aeroplanes/{uuid}/mission-objectives    → MissionObjective
PUT    /v2/aeroplanes/{uuid}/mission-objectives    → MissionObjective  (full update; idempotent)
GET    /v2/aeroplanes/{uuid}/mission-kpis?missions=trainer,sailplane → MissionKpiSet
GET    /v2/mission-presets                         → list[MissionPreset]
```

`field_length_service.compute_field_lengths` signature changes from reading `aircraft["available_runway_m"]` (assumption dict) to receiving the `MissionObjective` payload as input. Callers updated to fetch from the new service.

## 6. Frontend components

```
frontend/components/workbench/mission/
├── MissionTab.tsx                    (page-level, holds layout)
├── MissionCompliancePanel.tsx        (left card)
│   ├── MissionRadarChart.tsx          (custom SVG; multi-polygon overlay + auto-rescale)
│   ├── MissionToggleGrid.tsx
│   ├── MissionLegend.tsx
│   └── AxisDrawer.tsx                 (slide-out from right edge)
└── MissionObjectivesPanel.tsx        (right card)
    ├── MissionTypeDropdown.tsx
    ├── MissionAutoApplyBanner.tsx
    ├── PerformanceTargetsForm.tsx
    ├── FieldPerformanceForm.tsx
    └── ObjectiveSaveBar.tsx

frontend/hooks/
├── useMissionKpis.ts        (SWR, refetches on isRecomputing + mission toggle)
├── useMissionObjectives.ts  (SWR + debounced PUT)
└── useMissionPresets.ts     (SWR, mostly static)
```

`MissionRadarChart.tsx` is a custom SVG component (Plotly polar doesn't support multi-polygon overlay with per-mission ghost styling cleanly). The chart computes axis range = `[min_active_missions, max_active_missions]` per axis dynamically, then renders Soll + Ist + ghost polygons. Provenance badges are rendered as small circles next to each axis label.

## 7. Migration: field-performance inputs

Today's path: `app/services/field_length_service.compute_field_lengths(aircraft: dict)` reads `aircraft["available_runway_m"]`, `aircraft["t_static_N"]`, etc. The `aircraft` dict is built from `design_assumptions` + the aeroplane row.

Post-migration path:

```python
def compute_field_lengths(
    aircraft_geometry: AircraftGeometry,
    mission: MissionObjective,
) -> FieldLengthResult: ...
```

The service no longer reads field-performance parameters from Assumptions. Callers (`/v2/aeroplanes/{uuid}/field-lengths` endpoint and the migration calls inside `assumption_compute_service`) fetch the MissionObjective explicitly and pass it in.

This change is breaking but small in scope — the assumption-parameter list shrinks; the new MissionObjective covers the same data.

## 8. Error handling

- `mission_kpi_service` returns `MissionAxisKpi(provenance="missing", value=None, score_0_1=None)` when a required input is absent (e.g. mass not yet computed). Frontend renders the vertex as a gap in the polygon.
- `PUT /mission-objectives` validates numeric ranges via Pydantic; out-of-range values return 422 with the field name in the error payload.
- Mission-type change triggering auto-apply runs in a single transaction. If writing to `design_assumptions` fails, the entire request is rolled back; the user sees the error in the banner instead of "Mission updated".
- Frontend SWR `useMissionKpis` returns `stale: true` when `isRecomputing` is true (consistent with `useComputationContext` pattern); chart values render in muted red until the recompute settles.

## 9. Testing strategy

### Backend

- **Unit:** `mission_kpi_service` per-axis tests — each axis computed against a known fixture (Cessna-172-class, RC-trainer-class, ASW-27-class). Assert numeric value, score, range, provenance.
- **Unit:** Mission-preset auto-apply: pick "Sailplane" → assert `g_limit = 5.3` etc. is written to `estimate_value` only, not `calculated_value`.
- **Integration:** `GET /mission-kpis?missions=trainer,sailplane` returns both target polygons; ranges merge correctly.
- **Migration test:** Alembic upgrade + downgrade round-trip. `mission_objectives` row backfilled with Trainer defaults for existing aeroplanes.
- **Field-length regression:** all existing `test_field_length.py` tests pass; service now consumes `MissionObjective` instead of the assumption dict.

### Frontend

- **Unit (vitest):** `MissionRadarChart` snapshot tests for 1, 2, 3 active missions. Auto-rescale math (axis range = global min/max over active missions).
- **Unit:** `MissionAutoApplyBanner` shows on mission type change; respects existing user-overridden estimates (banner says "X already overridden, won't be touched").
- **E2E (playwright-bdd):** Open Mission tab → change Mission Type → see banner → click "Save" → assert Assumptions tab shows new estimate values.

## 10. Implementation phases / proposed tickets

Phase ordering reflects data-flow dependencies:

1. **`feat(mission): MissionObjective + MissionPreset DB tables + endpoints`** — two new DB tables, Pydantic schemas, seed data migration for the six initial presets, GET/PUT/GET endpoints. No frontend yet.
2. **`feat(mission): mission_kpi_service computing 7 axes`** — pure aggregation from existing services + the new MissionObjective.
3. **`refactor(field-length): consume MissionObjective instead of Assumptions dict`** — service signature change + Alembic migration moving field-performance fields out of Assumptions.
4. **`feat(mission): Mission-preset auto-apply estimates`** — atomic write of suggested_estimates to design_assumptions.estimate_value on mission_type change.
5. **`feat(frontend): MissionRadarChart with multi-polygon overlay`** — custom SVG component, auto-rescale, provenance badges.
6. **`feat(frontend): MissionTab redesign — Compliance + Objectives panels`** — full UI replacement of the placeholder.
7. **`feat(frontend): AxisDrawer for click-on-axis detail`** — side-drawer with raw value + formula + provenance.
8. **`chore: create v2 EPIC for deferred items`** — separate GH EPIC tracking coaching drawer, UAV axes, per-axis units, absolute-scale toggle, Mission-in-Assumptions visualisation, mission versioning.

Tickets are sized for individual implementation cycles (`/supercycle-implement`). All but #8 produce observable user-visible progress on the Mission tab.

## 11. Rollback

Each phase ticket is independently revertable:

- Phases 1–4 are backend-only; Alembic migration in #3 has a `downgrade()` path that restores the field-performance columns to design_assumptions.
- Phases 5–7 are frontend-only; the placeholder Mission tab UI remains available behind a feature flag (`mission.tab.v2.enabled`) until phase 6 lands.
- The v2 EPIC (#8) is meta — its existence is independent of the v1 code.

## 12. Visual reference

A full interactive HTML mockup of the target Mission tab lives at
[`assets/2026-05-15-mission-tab-mock.html`](./assets/2026-05-15-mission-tab-mock.html).
Open it in any browser to inspect spacing, typography, and the
provenance-badge / multi-mission-toggle / banner patterns in their
intended rendered form.

### Layout wireframe

```
┌──────────────────────────────────────────────────────────────────────┐
│ RV-7 / —    [1·Mission ●]  [2·Construction] [3·Analysis] [4·Comp.]   │
│                                                       [↻] [v3 ▾] [⚙] │
├───────────────────────────────────┬──────────────────────────────────┤
│                                   │                                  │
│  ⊙ Mission Compliance             │  ⊙ Mission Objectives            │
│  ─────────────────────            │  ─────────────────────           │
│                                   │  ┌───────────────────────────┐   │
│           ▲ Glide                 │  │ ⚡ Mission = Trainer       │   │
│       Stall●─┼─●Climb             │  │   g_limit:3.0 · SM:0.15… │   │
│       ●         ●                 │  │   [In Assumptions →]      │   │
│     Maneuver  Cruise              │  └───────────────────────────┘   │
│        ●     ●                    │                                  │
│         W/S Field                 │  Mission Type    ┌───────────┐   │
│            ●                      │                  │ Trainer ▾ │   │
│      (orange Ist + white Soll     │                  └───────────┘   │
│       + red gap-fill +            │                                  │
│       blue Sailplane ghost)       │  ── PERFORMANCE TARGETS ───      │
│                                   │  Cruise [18.0 m/s]  Stall [1.80] │
│  ── VERGLEICHS-PROFILE ───        │  Maneuver [3.0 g]   Glide [12]   │
│  ☑ Trainer (aktiv)  ☐ Sport       │  Climb [22]         W/S [42]     │
│  ☑ Sailplane (blue) ☐ Wing-Racer  │                                  │
│  ☐ 3D / Acro        ☐ STOL        │  ── FIELD PERFORMANCE ───        │
│                                   │  Runway [50 m]      Type [grass▾]│
│  ▬ Ist  ┄ Soll  ▒ Gap             │  T_static [18 N]    Mode [run.▾] │
│                                   │                                  │
│                                   │            [Cancel] [Save]       │
├───────────────────────────────────┴──────────────────────────────────┤
│ V_stall 23 · V_md 48 · V_cruise 65 · V_max 95 · Re 1.2e5 · MAC 210 … │
├──────────────────────────────────────────────────────────────────────┤
│ 💬 Ask the copilot…                                                  │
└──────────────────────────────────────────────────────────────────────┘
```

### Key visual details (from the rendered mock)

- **Radar** sits centred in the left panel, ~360 px max, with three solid
  grid rings (0.33 / 0.66 / 1.0) and one dashed outer ring (~1.3) showing
  where neighbour-mission markers can land when the chart auto-rescales.
- **Provenance badges** are 2.6-px circles in `#22dd66` (computed),
  `#f0c75e` (estimated), `#555` (missing) placed next to each axis label.
- **Ist polygon** uses `rgba(255, 132, 0, 0.34)` fill with `#FF8400`
  stroke. **Soll** is dashed white. **Gap** is `rgba(239, 68, 68, 0.14)`.
  **Ghost missions** use 10 % alpha fill with a coloured dashed stroke
  (sky-blue for Sailplane, red for Wing-Racer, etc.).
- **Toggle grid** for comparison profiles renders below the radar in a
  two-column layout. The active profile is highlighted in orange; ghost
  profiles inherit their polygon colour.
- **Auto-apply banner** in the right panel uses a left-bar accent
  (`#FF8400` 3 px) with a gradient background, mono-spaced diff line, and
  a single secondary action linking to the Assumptions tab.
- **Form inputs** use suffix chips for units (`m/s`, `g`, `g/dm²`,
  `m`, `N`). Numeric inputs are monospaced.
- **Field Performance section** is visually marked "aus Assumptions
  migriert" as a one-time orientation cue for users coming from the old
  layout. The label is removed after v1 stabilises (drop in v2 cleanup).

## 13. Decisions taken during review

The following details were resolved after the initial spec write-up:

- **Mission-preset library** lives in a DB table (`mission_presets`), seeded via Alembic data migration. See §5.3.
- **Multi-mission overlay** defaults to "only the active mission". Comparison missions are opt-in via the toggle grid.
- **Field-Performance migration** preserves existing aeroplane values verbatim. Trainer defaults are only used for fields that were never set in the legacy Assumption data.
