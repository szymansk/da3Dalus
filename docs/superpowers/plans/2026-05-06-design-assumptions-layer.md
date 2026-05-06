# Implementation Plan: Design Assumptions Layer (#424)

Epic: #417 — Operating Point Simulation
Spec: `docs/superpowers/specs/2026-05-06-operating-point-simulation-design.md`

## Overview

Add a `design_assumptions` table and full-stack CRUD (model → schema →
service → API → MCP → frontend) for 6 core design parameters that
drive simulation during iterative aircraft design. Each assumption
tracks an estimate, an optional calculated value, active source, and
divergence percentage.

## Task Breakdown

### Task 1: Backend Model + Alembic Migration

**Files:**
- `app/models/aeroplanemodel.py` — add `DesignAssumptionModel`
- `alembic/versions/<hash>_add_design_assumptions_table.py` — new migration

**Model (follows WeightItemModel pattern):**
```
DesignAssumptionModel(Base):
  __tablename__ = "design_assumptions"
  id               — Integer, PK, autoincrement
  aeroplane_id     — Integer, FK aeroplanes.id, CASCADE, NOT NULL, indexed
  parameter_name   — String, NOT NULL (mass, cg_x, target_static_margin, cd0, cl_max, g_limit)
  estimate_value   — Float, NOT NULL
  calculated_value — Float, nullable
  calculated_source— String, nullable (component_tree, aero_analysis, etc.)
  active_source    — String, NOT NULL, default "ESTIMATE" (enum: ESTIMATE | CALCULATED)
  divergence_pct   — Float, nullable
  updated_at       — DateTime(tz), server_default now(), onupdate now()

  UniqueConstraint(aeroplane_id, parameter_name)
  relationship → AeroplaneModel.design_assumptions (cascade all, delete-orphan)
```

**AeroplaneModel extension:**
- Add `design_assumptions` relationship

**TDD:** Write model-level test (instantiation, unique constraint) → create model → migration.

---

### Task 2: Backend Pydantic Schemas

**Files:**
- `app/schemas/design_assumption.py` — new file

**Schemas:**
```python
VALID_PARAMETERS = Literal["mass", "cg_x", "target_static_margin", "cd0", "cl_max", "g_limit"]
ACTIVE_SOURCE = Literal["ESTIMATE", "CALCULATED"]
DIVERGENCE_LEVEL = Literal["none", "info", "warning", "alert"]

class AssumptionWrite(BaseModel):
    estimate_value: float

class AssumptionSourceSwitch(BaseModel):
    active_source: ACTIVE_SOURCE

class AssumptionRead(BaseModel):
    id: int
    parameter_name: VALID_PARAMETERS
    estimate_value: float
    calculated_value: float | None
    calculated_source: str | None
    active_source: ACTIVE_SOURCE
    effective_value: float  # computed: calc if CALCULATED else estimate
    divergence_pct: float | None
    divergence_level: DIVERGENCE_LEVEL  # computed from pct thresholds
    updated_at: datetime

class AssumptionsSummary(BaseModel):
    assumptions: list[AssumptionRead]
    warnings_count: int  # count of divergence_level >= warning
```

**TDD:** Write schema validation tests (valid/invalid params, divergence level computation) → create schemas.

---

### Task 3: Backend Service

**Files:**
- `app/services/design_assumptions_service.py` — new file

**Functions (follow weight_items_service pattern):**
```
seed_defaults(db, aeroplane_uuid) → AssumptionsSummary
    Creates all 6 assumptions with standard defaults if they don't exist.
    Defaults: mass=1.5, cg_x=0.15, target_static_margin=0.12,
              cd0=0.03, cl_max=1.4, g_limit=3.0

list_assumptions(db, aeroplane_uuid) → AssumptionsSummary
    Returns all assumptions with computed effective_value and divergence_level.

update_assumption(db, aeroplane_uuid, param_name, data: AssumptionWrite) → AssumptionRead
    Updates estimate_value, recomputes divergence. Validates param_name.

switch_source(db, aeroplane_uuid, param_name, data: AssumptionSourceSwitch) → AssumptionRead
    Toggles active_source. Validates: CALCULATED only allowed when
    calculated_value is not None. target_static_margin and g_limit
    reject CALCULATED (always design choices).

get_effective_value(db, aeroplane_uuid, param_name) → float
    Returns the value used for simulations.
```

**Internal helpers:**
```
_compute_divergence(estimate, calculated) → float | None
_divergence_level(pct: float | None) → str
_assumption_to_schema(model) → AssumptionRead
```

**TDD:** Write service tests with mocked DB → implement service.

---

### Task 4: Backend API Endpoints

**Files:**
- `app/api/v2/endpoints/aeroplane/design_assumptions.py` — new file
- `app/api/v2/endpoints/aeroplane/__init__.py` — register router

**Endpoints (follow weight_items.py pattern):**
```
POST   /aeroplanes/{aeroplane_id}/assumptions
    → seed_defaults → 201 AssumptionsSummary
GET    /aeroplanes/{aeroplane_id}/assumptions
    → list_assumptions → 200 AssumptionsSummary
PUT    /aeroplanes/{aeroplane_id}/assumptions/{param_name}
    → update_assumption → 200 AssumptionRead
PATCH  /aeroplanes/{aeroplane_id}/assumptions/{param_name}/source
    → switch_source → 200 AssumptionRead
```

Tags: `["design-assumptions"]`

**TDD:** Write endpoint tests → implement endpoints → register in __init__.py.

---

### Task 5: MCP Tools

**Files:**
- `app/mcp_server.py` — add 3 tools

**Tools:**
```
set_design_assumption(aeroplane_id, param, value) → calls PUT endpoint
get_design_assumptions(aeroplane_id) → calls GET endpoint
switch_assumption_source(aeroplane_id, param, source) → calls PATCH endpoint
```

Follow existing `@mcp_tool` + `_call_endpoint` pattern.

**TDD:** Write MCP tool registration tests → implement tools.

---

### Task 6: Frontend — useDesignAssumptions Hook

**Files:**
- `frontend/hooks/useDesignAssumptions.ts` — new file

**Interface:**
```typescript
interface Assumption {
  id: number;
  parameter_name: string;
  estimate_value: number;
  calculated_value: number | null;
  calculated_source: string | null;
  active_source: "ESTIMATE" | "CALCULATED";
  effective_value: number;
  divergence_pct: number | null;
  divergence_level: "none" | "info" | "warning" | "alert";
  updated_at: string;
}

interface AssumptionsSummary {
  assumptions: Assumption[];
  warnings_count: number;
}

useDesignAssumptions(aeroplaneId: string | null) → {
  data: AssumptionsSummary | null;
  isLoading: boolean;
  error: Error | null;
  seedDefaults: () => Promise<void>;
  updateEstimate: (param: string, value: number) => Promise<void>;
  switchSource: (param: string, source: string) => Promise<void>;
  mutate: () => void;
}
```

Uses SWR for GET, fetch for mutations with `mutate()` revalidation.

**TDD:** Write hook unit tests (vitest) → implement hook.

---

### Task 7: Frontend — AssumptionsPanel Component

**Files:**
- `frontend/components/workbench/AssumptionsPanel.tsx` — new file
- `frontend/components/workbench/AssumptionRow.tsx` — new file

**AssumptionsPanel:** Table of assumptions with seed button if empty.
Each row shows: parameter name (human-readable), effective value with
unit, badge (estimate/calculated/design-choice), divergence indicator.

**AssumptionRow:** Single row with inline edit for estimate, toggle for
active source, divergence bar/badge.

**Badge types:**
- estimate (orange) — only manual, or conscious override
- calculated (green) — calculated value active
- design choice (grey) — target_static_margin, g_limit

**Divergence thresholds:** <5% none | 5-15% info (blue) | >15% warning (orange) | >30% alert (red)

**TDD:** Write component tests (vitest + @testing-library/react) → implement.

---

### Task 8: Frontend — Analysis Page Tab Integration

**Files:**
- `frontend/app/workbench/analysis/page.tsx` — add Assumptions tab

**Changes:**
- Add "Assumptions" as a tab option alongside Polar, Trefftz Plane, Streamlines
- When Assumptions tab is active, render AssumptionsPanel instead of
  AnalysisViewerPanel
- Use URL query param `?tab=assumptions` (from spec) — but for MVP,
  local state tab switching is acceptable since the other tabs don't
  use query params yet

**TDD:** Write page-level test for tab switching → implement integration.

---

## Execution Order

Tasks 1-5 (backend) are sequential — each depends on the previous.
Tasks 6-8 (frontend) depend on Task 4 (API) but are independent of
each other and can run in parallel.

```
Task 1 (model) → Task 2 (schemas) → Task 3 (service) → Task 4 (API) → Task 5 (MCP)
                                                           ↓
                                                    Tasks 6, 7, 8 (frontend, parallel)
```

## Acceptance Criteria (from spec)

- [ ] `design_assumptions` table with 6 core parameters per aeroplane
- [ ] POST seeds defaults, GET returns all with divergence, PUT updates estimate, PATCH toggles source
- [ ] Divergence auto-computed: |estimate - calculated| / |calculated| × 100
- [ ] target_static_margin and g_limit reject CALCULATED source (design choices)
- [ ] MCP tools: set_design_assumption, get_design_assumptions, switch_assumption_source
- [ ] Frontend Assumptions tab in Analysis page with badge types and divergence indicators
- [ ] >80% test coverage on new code
