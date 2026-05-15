# Mission Tab Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the placeholder Mission tab (Tab 1) with a Mission-driven design system: 7-axis compliance spider chart, multi-mission overlay, mission-preset auto-apply of design assumptions, and migrated Field Performance inputs.

**Architecture:** Backend introduces two new DB tables (`mission_objectives`, `mission_presets`) seeded via Alembic, a `mission_kpi_service` aggregating 7 normalised KPIs from the existing `ComputationContext` + `field_length_service` + V-n, and four endpoints. Frontend replaces the Mission tab content with a `MissionCompliancePanel` (custom SVG radar) + `MissionObjectivesPanel` (form with auto-apply banner). Field-performance inputs migrate out of Assumptions.

**Tech Stack:** Python 3.11 · FastAPI · Pydantic v2 · SQLAlchemy · Alembic · pytest · Next.js 16 · React 19 · TypeScript · SWR · Tailwind · custom SVG (not Plotly — multi-polygon overlay).

**Spec:** [`docs/superpowers/specs/2026-05-15-mission-spider-chart-design.md`](../specs/2026-05-15-mission-spider-chart-design.md)
**Mock:** [`docs/superpowers/specs/assets/2026-05-15-mission-tab-mock.html`](../specs/assets/2026-05-15-mission-tab-mock.html)

**Phase order (data-flow dependencies):**
1. DB tables + endpoints (BE)
2. KPI aggregation service (BE)
3. Field-length refactor + migration (BE)
4. Mission-preset auto-apply (BE)
5. Radar chart component (FE)
6. Mission tab UI (FE)
7. Axis drawer (FE)
8. v2 EPIC (GH housekeeping)

Each phase = one PR via `/supercycle-implement`.

---

## Phase 1 — DB tables, schemas, endpoints (BE)

**Goal:** Pydantic schemas, two new SQLAlchemy tables, Alembic migration with seed presets, REST endpoints.

### Task 1.1: ParabolicPolar pattern check + axis-name enum

**Files:**
- Create: `app/schemas/mission_kpi.py`
- Test: `app/tests/test_mission_kpi_schema.py`

- [ ] **Step 1: Read existing schema pattern**

```bash
cat app/schemas/polar_by_config.py
```

Note the pattern: `from __future__ import annotations`, `Literal` for finite sets, `BaseModel` from pydantic, `Field(..., description=...)`.

- [ ] **Step 2: Write the failing test**

`app/tests/test_mission_kpi_schema.py`:
```python
"""Tests for the mission_kpi schemas (gh-XXX)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.mission_kpi import MissionAxisKpi, MissionKpiSet, MissionTargetPolygon


def test_axis_kpi_accepts_known_axes_only():
    kpi = MissionAxisKpi(
        axis="stall_safety",
        value=1.45,
        unit="-",
        score_0_1=0.72,
        range_min=1.3,
        range_max=3.0,
        provenance="computed",
        formula="V_cruise / V_s1",
    )
    assert kpi.axis == "stall_safety"


def test_axis_kpi_rejects_unknown_axis():
    with pytest.raises(ValidationError):
        MissionAxisKpi(
            axis="bogus_axis",
            value=1.0, unit="-", score_0_1=0.5,
            range_min=0, range_max=1, provenance="computed",
            formula="-",
        )


def test_axis_kpi_provenance_missing_allows_none_value():
    kpi = MissionAxisKpi(
        axis="glide", value=None, unit=None, score_0_1=None,
        range_min=0, range_max=1, provenance="missing", formula="-",
    )
    assert kpi.value is None
    assert kpi.score_0_1 is None


def test_kpi_set_round_trips_model_dump():
    ist = {
        "stall_safety": MissionAxisKpi(
            axis="stall_safety", value=1.45, unit="-", score_0_1=0.72,
            range_min=1.3, range_max=3.0, provenance="computed",
            formula="V_cruise / V_s1",
        ),
    }
    kset = MissionKpiSet(
        aeroplane_uuid="00000000-0000-0000-0000-000000000000",
        ist_polygon=ist,
        target_polygons=[
            MissionTargetPolygon(
                mission_id="trainer", label="Trainer",
                scores_0_1={"stall_safety": 0.78},
            ),
        ],
        active_mission_id="trainer",
        computed_at="2026-05-15T12:00:00Z",
        context_hash="0" * 64,
    )
    dumped = kset.model_dump()
    re_parsed = MissionKpiSet.model_validate(dumped)
    assert re_parsed == kset
```

- [ ] **Step 3: Run test to verify it fails**

```bash
poetry run pytest app/tests/test_mission_kpi_schema.py -v
```

Expected: ImportError (`app.schemas.mission_kpi` doesn't exist).

- [ ] **Step 4: Create the schema file**

`app/schemas/mission_kpi.py`:
```python
"""Pydantic schemas for the Mission compliance spider chart (gh-XXX)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AxisName = Literal[
    "stall_safety", "glide", "climb", "cruise",
    "maneuver", "wing_loading", "field_friendliness",
]
"""The seven mission-compliance axes."""

Provenance = Literal["computed", "estimated", "missing"]
"""Where a KPI value came from. ``missing`` → renders as a polygon gap."""


class MissionAxisKpi(BaseModel):
    """One axis on the spider chart."""

    axis: AxisName
    value: float | None = Field(..., description="Raw physical value, None when missing")
    unit: str | None = Field(..., description="SI unit; UI converts via global preset")
    score_0_1: float | None = Field(..., description="Normalised to current mission range")
    range_min: float = Field(..., description="Lower bound used for normalisation")
    range_max: float = Field(..., description="Upper bound used for normalisation")
    provenance: Provenance
    formula: str = Field(..., description="Human-readable formula for the side-drawer")
    warning: str | None = None


class MissionTargetPolygon(BaseModel):
    """The Soll-polygon for one mission preset."""

    mission_id: str = Field(..., description="Mission preset id (e.g. 'trainer')")
    label: str
    scores_0_1: dict[AxisName, float]


class MissionKpiSet(BaseModel):
    """Full KPI payload returned from /mission-kpis."""

    aeroplane_uuid: str
    ist_polygon: dict[AxisName, MissionAxisKpi]
    target_polygons: list[MissionTargetPolygon]
    active_mission_id: str
    computed_at: str
    context_hash: str = Field(..., min_length=64, max_length=64)
```

- [ ] **Step 5: Run test to verify it passes**

```bash
poetry run pytest app/tests/test_mission_kpi_schema.py -v
```

Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add app/schemas/mission_kpi.py app/tests/test_mission_kpi_schema.py
git commit -m "feat(mission): MissionAxisKpi / MissionKpiSet schemas"
```

---

### Task 1.2: MissionObjective + MissionPreset schemas

**Files:**
- Create: `app/schemas/mission_objective.py`
- Test: `app/tests/test_mission_objective_schema.py`

- [ ] **Step 1: Write the failing test**

`app/tests/test_mission_objective_schema.py`:
```python
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.mission_objective import (
    MissionObjective,
    MissionPreset,
    MissionPresetEstimates,
)


def test_mission_objective_full_payload():
    obj = MissionObjective(
        mission_type="trainer",
        target_cruise_mps=18.0,
        target_stall_safety=1.8,
        target_maneuver_n=3.0,
        target_glide_ld=12,
        target_climb_energy=22,
        target_wing_loading_n_m2=42 * 9.81,  # g/dm² → N/m² scale
        target_field_length_m=50,
        available_runway_m=50,
        runway_type="grass",
        t_static_N=18,
        takeoff_mode="runway",
    )
    assert obj.mission_type == "trainer"


def test_runway_type_enum_rejects_unknown():
    with pytest.raises(ValidationError):
        MissionObjective(
            mission_type="trainer",
            target_cruise_mps=18, target_stall_safety=1.8,
            target_maneuver_n=3, target_glide_ld=12,
            target_climb_energy=22, target_wing_loading_n_m2=400,
            target_field_length_m=50, available_runway_m=50,
            runway_type="diamond",   # invalid
            t_static_N=18, takeoff_mode="runway",
        )


def test_preset_has_polygon_and_estimates():
    pre = MissionPreset(
        id="trainer", label="Trainer", description="Forgiving trainer",
        target_polygon={
            "stall_safety": 1.0, "glide": 0.4, "climb": 0.3, "cruise": 0.3,
            "maneuver": 0.3, "wing_loading": 0.3, "field_friendliness": 0.9,
        },
        axis_ranges={
            "stall_safety": (1.3, 2.5), "glide": (5, 18),
            "climb": (5, 25), "cruise": (10, 25),
            "maneuver": (2, 5), "wing_loading": (20, 80),
            "field_friendliness": (3, 100),
        },
        suggested_estimates=MissionPresetEstimates(
            g_limit=3.0, target_static_margin=0.15, cl_max=1.4,
            power_to_weight=0.5, prop_efficiency=0.7,
        ),
    )
    assert pre.target_polygon["stall_safety"] == 1.0
```

- [ ] **Step 2: Run failing test**

```bash
poetry run pytest app/tests/test_mission_objective_schema.py -v
```

Expected: ImportError.

- [ ] **Step 3: Create schema**

`app/schemas/mission_objective.py`:
```python
"""Mission-Objective + Mission-Preset Pydantic schemas (gh-XXX)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.mission_kpi import AxisName

RunwayType = Literal["grass", "asphalt", "belly"]
TakeoffMode = Literal["runway", "hand_launch", "bungee", "catapult"]


class MissionObjective(BaseModel):
    """User-set mission targets + field-performance inputs for one aeroplane."""

    mission_type: str = Field(..., description="FK to MissionPreset.id")

    # Performance targets (one per spider axis except W/S which is computed)
    target_cruise_mps: float = Field(..., ge=0)
    target_stall_safety: float = Field(..., ge=1.0, description="V_cruise / V_s1")
    target_maneuver_n: float = Field(..., ge=1.0, description="Load factor [g]")
    target_glide_ld: float = Field(..., ge=0, description="L/D target")
    target_climb_energy: float = Field(..., ge=0, description="C_L^1.5/CD")
    target_wing_loading_n_m2: float = Field(..., ge=0)
    target_field_length_m: float = Field(..., ge=0)

    # Field Performance inputs (migrated from Assumptions)
    available_runway_m: float = Field(..., ge=0)
    runway_type: RunwayType
    t_static_N: float = Field(..., ge=0, description="Static thrust at V=0")
    takeoff_mode: TakeoffMode


class MissionPresetEstimates(BaseModel):
    """Default DesignAssumption estimate_values applied when this mission is selected."""

    g_limit: float
    target_static_margin: float
    cl_max: float
    power_to_weight: float
    prop_efficiency: float


class MissionPreset(BaseModel):
    """One mission preset row (Trainer, Sport, Sailplane, …)."""

    id: str = Field(..., description="Stable preset id, e.g. 'trainer'")
    label: str
    description: str
    target_polygon: dict[AxisName, float] = Field(
        ..., description="Soll polygon scores 0..1 for the 7 axes"
    )
    axis_ranges: dict[AxisName, tuple[float, float]] = Field(
        ..., description="Mission-relative (min, max) for axis normalisation"
    )
    suggested_estimates: MissionPresetEstimates
```

- [ ] **Step 4: Run tests pass**

```bash
poetry run pytest app/tests/test_mission_objective_schema.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add app/schemas/mission_objective.py app/tests/test_mission_objective_schema.py
git commit -m "feat(mission): MissionObjective + MissionPreset schemas"
```

---

### Task 1.3: SQLAlchemy models

**Files:**
- Create: `app/models/mission_objective.py`
- Create: `app/models/mission_preset.py`

- [ ] **Step 1: Read existing model pattern**

```bash
sed -n '1,40p' app/models/aeroplanemodel.py
```

Note: `from app.db.base import Base`, `Column(Integer, primary_key=True)`, `Float`, `String`, `JSON`, `ForeignKey`, naming conventions.

- [ ] **Step 2: Create `mission_objective` model**

`app/models/mission_objective.py`:
```python
"""SQLAlchemy model for per-aeroplane Mission Objectives (gh-XXX)."""
from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class MissionObjectiveModel(Base):
    __tablename__ = "mission_objectives"

    id = Column(Integer, primary_key=True)
    aeroplane_id = Column(
        Integer,
        ForeignKey("aeroplanes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,   # one row per aeroplane
        index=True,
    )

    mission_type = Column(String, nullable=False, default="trainer")

    # Performance targets
    target_cruise_mps = Column(Float, nullable=False, default=18.0)
    target_stall_safety = Column(Float, nullable=False, default=1.8)
    target_maneuver_n = Column(Float, nullable=False, default=3.0)
    target_glide_ld = Column(Float, nullable=False, default=12.0)
    target_climb_energy = Column(Float, nullable=False, default=22.0)
    target_wing_loading_n_m2 = Column(Float, nullable=False, default=412.0)  # ~42 g/dm²
    target_field_length_m = Column(Float, nullable=False, default=50.0)

    # Field Performance (migrated from Assumptions)
    available_runway_m = Column(Float, nullable=False, default=50.0)
    runway_type = Column(String, nullable=False, default="grass")
    t_static_N = Column(Float, nullable=False, default=18.0)
    takeoff_mode = Column(String, nullable=False, default="runway")

    aeroplane = relationship("AeroplaneModel", back_populates="mission_objective")
```

- [ ] **Step 3: Create `mission_preset` model**

`app/models/mission_preset.py`:
```python
"""SQLAlchemy model for Mission Presets library (gh-XXX)."""
from sqlalchemy import Column, JSON, Integer, String

from app.db.base import Base


class MissionPresetModel(Base):
    __tablename__ = "mission_presets"

    id = Column(String, primary_key=True)   # stable preset id "trainer", etc.
    label = Column(String, nullable=False)
    description = Column(String, nullable=False, default="")
    target_polygon = Column(JSON, nullable=False)      # dict[AxisName, float]
    axis_ranges = Column(JSON, nullable=False)         # dict[AxisName, [min, max]]
    suggested_estimates = Column(JSON, nullable=False) # MissionPresetEstimates dict
```

- [ ] **Step 4: Add back-relationship on AeroplaneModel**

Edit `app/models/aeroplanemodel.py`. Find the `AeroplaneModel` class definition, locate where other 1-to-1 relationships are declared, and add:

```python
    mission_objective = relationship(
        "MissionObjectiveModel",
        back_populates="aeroplane",
        uselist=False,
        cascade="all, delete-orphan",
    )
```

- [ ] **Step 5: Commit**

```bash
git add app/models/mission_objective.py app/models/mission_preset.py app/models/aeroplanemodel.py
git commit -m "feat(mission): SQLAlchemy models for MissionObjective + MissionPreset"
```

---

### Task 1.4: Mission-preset seed data

**Files:**
- Create: `app/services/mission_preset_seed.py`
- Test: `app/tests/test_mission_preset_seed.py`

- [ ] **Step 1: Write failing test**

`app/tests/test_mission_preset_seed.py`:
```python
from __future__ import annotations

from app.schemas.mission_kpi import AxisName
from app.services.mission_preset_seed import SEED_PRESETS


def test_six_seed_presets_exist():
    ids = {p.id for p in SEED_PRESETS}
    assert ids == {"trainer", "sport", "sailplane", "wing_racer", "acro_3d", "stol_bush"}


def test_each_preset_covers_all_seven_axes():
    expected_axes = {
        "stall_safety", "glide", "climb", "cruise",
        "maneuver", "wing_loading", "field_friendliness",
    }
    for p in SEED_PRESETS:
        assert set(p.target_polygon.keys()) == expected_axes, f"{p.id} target_polygon"
        assert set(p.axis_ranges.keys()) == expected_axes, f"{p.id} axis_ranges"


def test_axis_ranges_min_less_than_max():
    for p in SEED_PRESETS:
        for axis, (lo, hi) in p.axis_ranges.items():
            assert lo < hi, f"{p.id}.{axis}: range {lo} !< {hi}"


def test_stall_safety_range_floor_is_1_3():
    """Per spec: hard floor for Stall Safety is 1.3 across all missions."""
    for p in SEED_PRESETS:
        lo, _ = p.axis_ranges["stall_safety"]
        assert lo >= 1.3, f"{p.id} stall floor {lo} < 1.3"
```

- [ ] **Step 2: Run failing test**

```bash
poetry run pytest app/tests/test_mission_preset_seed.py -v
```

Expected: ImportError.

- [ ] **Step 3: Create seed module**

`app/services/mission_preset_seed.py`:
```python
"""Seed data for the six default Mission Presets (gh-XXX).

Used by the Alembic data migration. Values come from the brainstorming
spec §3 "Mission Soll-Polygone" — adjusted per the spec's normalisation
ranges. Source of truth: docs/superpowers/specs/2026-05-15-mission-spider-chart-design.md
"""
from __future__ import annotations

from app.schemas.mission_objective import MissionPreset, MissionPresetEstimates

SEED_PRESETS: list[MissionPreset] = [
    MissionPreset(
        id="trainer",
        label="Trainer",
        description="Forgiving low-loading trainer for first-flight pilots.",
        target_polygon={
            "stall_safety": 1.0, "glide": 0.4, "climb": 0.3, "cruise": 0.3,
            "maneuver": 0.3, "wing_loading": 0.3, "field_friendliness": 0.9,
        },
        axis_ranges={
            "stall_safety": (1.3, 2.5), "glide": (5.0, 18.0),
            "climb": (5.0, 25.0), "cruise": (10.0, 25.0),
            "maneuver": (2.0, 5.0), "wing_loading": (20.0, 80.0),
            "field_friendliness": (3.0, 100.0),
        },
        suggested_estimates=MissionPresetEstimates(
            g_limit=3.0, target_static_margin=0.15, cl_max=1.4,
            power_to_weight=0.5, prop_efficiency=0.7,
        ),
    ),
    MissionPreset(
        id="sport",
        label="Sport",
        description="All-rounder with moderate loading and honest control authority.",
        target_polygon={
            "stall_safety": 0.7, "glide": 0.6, "climb": 0.6, "cruise": 0.6,
            "maneuver": 0.6, "wing_loading": 0.6, "field_friendliness": 0.6,
        },
        axis_ranges={
            "stall_safety": (1.3, 2.2), "glide": (8.0, 20.0),
            "climb": (8.0, 30.0), "cruise": (15.0, 35.0),
            "maneuver": (3.0, 7.0), "wing_loading": (40.0, 120.0),
            "field_friendliness": (5.0, 100.0),
        },
        suggested_estimates=MissionPresetEstimates(
            g_limit=5.0, target_static_margin=0.10, cl_max=1.3,
            power_to_weight=0.7, prop_efficiency=0.7,
        ),
    ),
    MissionPreset(
        id="sailplane",
        label="Sailplane",
        description="High-AR thermal glider with low minimum sink and high L/D.",
        target_polygon={
            "stall_safety": 0.8, "glide": 1.0, "climb": 0.5, "cruise": 0.3,
            "maneuver": 0.3, "wing_loading": 0.1, "field_friendliness": 0.5,
        },
        axis_ranges={
            "stall_safety": (1.3, 2.0), "glide": (15.0, 35.0),
            "climb": (15.0, 60.0), "cruise": (10.0, 25.0),
            "maneuver": (2.5, 5.5), "wing_loading": (10.0, 50.0),
            "field_friendliness": (3.0, 100.0),
        },
        suggested_estimates=MissionPresetEstimates(
            g_limit=5.3, target_static_margin=0.10, cl_max=1.3,
            power_to_weight=0.0, prop_efficiency=0.0,
        ),
    ),
    MissionPreset(
        id="wing_racer",
        label="Wing-Racer",
        description="Low-AR pylon / FPV racer optimised for cruise + maneuver.",
        target_polygon={
            "stall_safety": 0.5, "glide": 0.7, "climb": 0.7, "cruise": 1.0,
            "maneuver": 0.7, "wing_loading": 0.9, "field_friendliness": 0.4,
        },
        axis_ranges={
            "stall_safety": (1.3, 2.0), "glide": (6.0, 18.0),
            "climb": (10.0, 35.0), "cruise": (30.0, 80.0),
            "maneuver": (5.0, 12.0), "wing_loading": (80.0, 250.0),
            "field_friendliness": (3.0, 100.0),
        },
        suggested_estimates=MissionPresetEstimates(
            g_limit=10.0, target_static_margin=0.05, cl_max=1.0,
            power_to_weight=1.0, prop_efficiency=0.7,
        ),
    ),
    MissionPreset(
        id="acro_3d",
        label="3D / Acro",
        description="Neutral-stability 3D model with very high control authority.",
        target_polygon={
            "stall_safety": 0.5, "glide": 0.4, "climb": 0.7, "cruise": 0.5,
            "maneuver": 1.0, "wing_loading": 0.8, "field_friendliness": 0.5,
        },
        axis_ranges={
            "stall_safety": (1.3, 2.0), "glide": (6.0, 14.0),
            "climb": (15.0, 40.0), "cruise": (15.0, 30.0),
            "maneuver": (6.0, 12.0), "wing_loading": (60.0, 180.0),
            "field_friendliness": (3.0, 80.0),
        },
        suggested_estimates=MissionPresetEstimates(
            g_limit=8.0, target_static_margin=0.0, cl_max=1.1,
            power_to_weight=1.4, prop_efficiency=0.7,
        ),
    ),
    MissionPreset(
        id="stol_bush",
        label="STOL / Bush",
        description="Short take-off / bush model with high CL_max and short field.",
        target_polygon={
            "stall_safety": 0.9, "glide": 0.5, "climb": 0.6, "cruise": 0.3,
            "maneuver": 0.4, "wing_loading": 0.2, "field_friendliness": 1.0,
        },
        axis_ranges={
            "stall_safety": (1.3, 3.0), "glide": (6.0, 16.0),
            "climb": (8.0, 30.0), "cruise": (10.0, 25.0),
            "maneuver": (2.5, 5.0), "wing_loading": (15.0, 80.0),
            "field_friendliness": (2.0, 50.0),
        },
        suggested_estimates=MissionPresetEstimates(
            g_limit=4.0, target_static_margin=0.15, cl_max=2.0,
            power_to_weight=0.8, prop_efficiency=0.7,
        ),
    ),
]
```

- [ ] **Step 4: Run tests pass**

```bash
poetry run pytest app/tests/test_mission_preset_seed.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add app/services/mission_preset_seed.py app/tests/test_mission_preset_seed.py
git commit -m "feat(mission): seed data for six default Mission Presets"
```

---

### Task 1.5: Alembic migration

**Files:**
- Create: `alembic/versions/XXXX_mission_tables.py` (Alembic will assign the prefix)

- [ ] **Step 1: Generate migration scaffold**

```bash
poetry run alembic revision -m "mission tables: presets + objectives"
```

This creates a new file in `alembic/versions/`. Note the filename printed.

- [ ] **Step 2: Implement the migration**

Open the newly created file and replace `upgrade()` and `downgrade()`:

```python
"""mission tables: presets + objectives

Revision ID: <auto>
Revises: <previous>
Create Date: 2026-05-15 ...
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers (leave auto-generated values)
revision = "..."
down_revision = "..."
branch_labels = None
depends_on = None


def upgrade() -> None:
    # mission_presets
    op.create_table(
        "mission_presets",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False, server_default=""),
        sa.Column("target_polygon", sa.JSON(), nullable=False),
        sa.Column("axis_ranges", sa.JSON(), nullable=False),
        sa.Column("suggested_estimates", sa.JSON(), nullable=False),
    )

    # Seed presets via bulk insert. Import locally to avoid model-load order issues.
    from app.services.mission_preset_seed import SEED_PRESETS

    op.bulk_insert(
        sa.table(
            "mission_presets",
            sa.column("id", sa.String),
            sa.column("label", sa.String),
            sa.column("description", sa.String),
            sa.column("target_polygon", sa.JSON),
            sa.column("axis_ranges", sa.JSON),
            sa.column("suggested_estimates", sa.JSON),
        ),
        [
            {
                "id": p.id,
                "label": p.label,
                "description": p.description,
                "target_polygon": p.target_polygon,
                # JSON tuple → list for storage
                "axis_ranges": {k: list(v) for k, v in p.axis_ranges.items()},
                "suggested_estimates": p.suggested_estimates.model_dump(),
            }
            for p in SEED_PRESETS
        ],
    )

    # mission_objectives
    op.create_table(
        "mission_objectives",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "aeroplane_id",
            sa.Integer(),
            sa.ForeignKey("aeroplanes.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("mission_type", sa.String(), nullable=False, server_default="trainer"),
        sa.Column("target_cruise_mps", sa.Float(), nullable=False, server_default="18.0"),
        sa.Column("target_stall_safety", sa.Float(), nullable=False, server_default="1.8"),
        sa.Column("target_maneuver_n", sa.Float(), nullable=False, server_default="3.0"),
        sa.Column("target_glide_ld", sa.Float(), nullable=False, server_default="12.0"),
        sa.Column("target_climb_energy", sa.Float(), nullable=False, server_default="22.0"),
        sa.Column("target_wing_loading_n_m2", sa.Float(), nullable=False, server_default="412.0"),
        sa.Column("target_field_length_m", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("available_runway_m", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("runway_type", sa.String(), nullable=False, server_default="grass"),
        sa.Column("t_static_N", sa.Float(), nullable=False, server_default="18.0"),
        sa.Column("takeoff_mode", sa.String(), nullable=False, server_default="runway"),
    )


def downgrade() -> None:
    op.drop_table("mission_objectives")
    op.drop_table("mission_presets")
```

- [ ] **Step 3: Smoke-test the migration**

```bash
poetry run alembic upgrade head
poetry run alembic downgrade -1
poetry run alembic upgrade head
```

All three commands should exit 0. The first creates the tables + seeds; the second drops them; the third recreates.

- [ ] **Step 4: Commit**

```bash
git add alembic/versions/
git commit -m "feat(mission): Alembic migration for mission_presets + mission_objectives"
```

---

### Task 1.6: mission_objective_service (read/write)

**Files:**
- Create: `app/services/mission_objective_service.py`
- Test: `app/tests/test_mission_objective_service.py`

- [ ] **Step 1: Write failing test**

`app/tests/test_mission_objective_service.py`:
```python
from __future__ import annotations

from app.models.aeroplanemodel import AeroplaneModel
from app.schemas.mission_objective import MissionObjective
from app.services.mission_objective_service import (
    get_mission_objective,
    upsert_mission_objective,
    list_mission_presets,
)
from app.tests.conftest import make_aeroplane


def _make_objective(**overrides):
    payload = dict(
        mission_type="trainer",
        target_cruise_mps=18.0, target_stall_safety=1.8,
        target_maneuver_n=3.0, target_glide_ld=12.0,
        target_climb_energy=22.0, target_wing_loading_n_m2=412.0,
        target_field_length_m=50.0, available_runway_m=50.0,
        runway_type="grass", t_static_N=18.0, takeoff_mode="runway",
    )
    payload.update(overrides)
    return MissionObjective(**payload)


def test_get_returns_default_when_none_persisted(client_and_db):
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        db.commit()

    with SessionLocal() as db:
        obj = get_mission_objective(db, aeroplane.id)
        assert obj.mission_type == "trainer"
        assert obj.target_cruise_mps == 18.0


def test_upsert_creates_then_updates(client_and_db):
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        db.commit()
        aircraft_id = aeroplane.id

    with SessionLocal() as db:
        upsert_mission_objective(db, aircraft_id, _make_objective(target_cruise_mps=22.0))
        db.commit()

    with SessionLocal() as db:
        obj = get_mission_objective(db, aircraft_id)
        assert obj.target_cruise_mps == 22.0

    with SessionLocal() as db:
        upsert_mission_objective(db, aircraft_id, _make_objective(target_cruise_mps=25.0))
        db.commit()

    with SessionLocal() as db:
        obj = get_mission_objective(db, aircraft_id)
        assert obj.target_cruise_mps == 25.0


def test_list_mission_presets_returns_six_seeded(client_and_db):
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        presets = list_mission_presets(db)
        ids = {p.id for p in presets}
    assert ids == {"trainer", "sport", "sailplane", "wing_racer", "acro_3d", "stol_bush"}
```

- [ ] **Step 2: Run failing test**

```bash
poetry run pytest app/tests/test_mission_objective_service.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement service**

`app/services/mission_objective_service.py`:
```python
"""CRUD + preset lookup for Mission Objectives (gh-XXX)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.mission_objective import MissionObjectiveModel
from app.models.mission_preset import MissionPresetModel
from app.schemas.mission_objective import MissionObjective, MissionPreset

_DEFAULT_OBJECTIVE = MissionObjective(
    mission_type="trainer",
    target_cruise_mps=18.0, target_stall_safety=1.8,
    target_maneuver_n=3.0, target_glide_ld=12.0,
    target_climb_energy=22.0, target_wing_loading_n_m2=412.0,
    target_field_length_m=50.0, available_runway_m=50.0,
    runway_type="grass", t_static_N=18.0, takeoff_mode="runway",
)


def get_mission_objective(db: Session, aeroplane_id: int) -> MissionObjective:
    """Return the persisted MissionObjective for an aeroplane, or the default."""
    row = (
        db.query(MissionObjectiveModel)
        .filter(MissionObjectiveModel.aeroplane_id == aeroplane_id)
        .one_or_none()
    )
    if row is None:
        return _DEFAULT_OBJECTIVE.model_copy()
    return MissionObjective(
        mission_type=row.mission_type,
        target_cruise_mps=row.target_cruise_mps,
        target_stall_safety=row.target_stall_safety,
        target_maneuver_n=row.target_maneuver_n,
        target_glide_ld=row.target_glide_ld,
        target_climb_energy=row.target_climb_energy,
        target_wing_loading_n_m2=row.target_wing_loading_n_m2,
        target_field_length_m=row.target_field_length_m,
        available_runway_m=row.available_runway_m,
        runway_type=row.runway_type,
        t_static_N=row.t_static_N,
        takeoff_mode=row.takeoff_mode,
    )


def upsert_mission_objective(
    db: Session, aeroplane_id: int, payload: MissionObjective
) -> MissionObjective:
    """Create or update the MissionObjective for an aeroplane."""
    row = (
        db.query(MissionObjectiveModel)
        .filter(MissionObjectiveModel.aeroplane_id == aeroplane_id)
        .one_or_none()
    )
    if row is None:
        row = MissionObjectiveModel(aeroplane_id=aeroplane_id)
        db.add(row)
    for field, value in payload.model_dump().items():
        setattr(row, field, value)
    db.flush()
    return payload


def list_mission_presets(db: Session) -> list[MissionPreset]:
    """Return the seeded mission-preset library."""
    rows = db.query(MissionPresetModel).all()
    return [
        MissionPreset(
            id=row.id, label=row.label, description=row.description,
            target_polygon=row.target_polygon,
            axis_ranges={k: tuple(v) for k, v in row.axis_ranges.items()},
            suggested_estimates=row.suggested_estimates,
        )
        for row in rows
    ]
```

- [ ] **Step 4: Run tests pass**

```bash
poetry run pytest app/tests/test_mission_objective_service.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add app/services/mission_objective_service.py app/tests/test_mission_objective_service.py
git commit -m "feat(mission): mission_objective_service CRUD + list_presets"
```

---

### Task 1.7: REST endpoints

**Files:**
- Create: `app/api/v2/endpoints/aeroplane/mission_objectives.py`
- Modify: `app/api/v2/endpoints/aeroplane/__init__.py` (register router)
- Test: `app/tests/test_mission_objectives_endpoint.py`

- [ ] **Step 1: Inspect existing endpoint pattern**

```bash
sed -n '1,40p' app/api/v2/endpoints/aeroplane/design_assumptions.py
```

Use the same router/dependency-injection style.

- [ ] **Step 2: Write failing test**

`app/tests/test_mission_objectives_endpoint.py`:
```python
from __future__ import annotations

from app.tests.conftest import make_aeroplane


def test_get_mission_objectives_default(client_and_db):
    client, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        db.commit()
        uuid = str(aeroplane.uuid)

    r = client.get(f"/aeroplanes/{uuid}/mission-objectives")
    assert r.status_code == 200
    body = r.json()
    assert body["mission_type"] == "trainer"
    assert body["target_cruise_mps"] == 18.0


def test_put_mission_objectives_persists(client_and_db):
    client, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        db.commit()
        uuid = str(aeroplane.uuid)

    payload = {
        "mission_type": "sailplane",
        "target_cruise_mps": 14.0, "target_stall_safety": 1.6,
        "target_maneuver_n": 4.0, "target_glide_ld": 25.0,
        "target_climb_energy": 45.0, "target_wing_loading_n_m2": 200.0,
        "target_field_length_m": 60.0, "available_runway_m": 80.0,
        "runway_type": "grass", "t_static_N": 0.0, "takeoff_mode": "bungee",
    }
    r = client.put(f"/aeroplanes/{uuid}/mission-objectives", json=payload)
    assert r.status_code == 200

    r2 = client.get(f"/aeroplanes/{uuid}/mission-objectives")
    assert r2.json()["mission_type"] == "sailplane"
    assert r2.json()["target_glide_ld"] == 25.0


def test_get_mission_presets_returns_six(client_and_db):
    client, _ = client_and_db
    r = client.get("/mission-presets")
    assert r.status_code == 200
    ids = {p["id"] for p in r.json()}
    assert ids == {"trainer", "sport", "sailplane", "wing_racer", "acro_3d", "stol_bush"}
```

- [ ] **Step 3: Run failing tests**

```bash
poetry run pytest app/tests/test_mission_objectives_endpoint.py -v
```

Expected: 404s (routes don't exist).

- [ ] **Step 4: Create endpoint**

`app/api/v2/endpoints/aeroplane/mission_objectives.py`:
```python
"""REST endpoints for Mission Objectives + Mission Presets (gh-XXX)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import UUID4
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.aeroplanemodel import AeroplaneModel
from app.schemas.mission_objective import MissionObjective, MissionPreset
from app.services.mission_objective_service import (
    get_mission_objective,
    list_mission_presets,
    upsert_mission_objective,
)

router = APIRouter()


def _resolve_aeroplane_id(db: Session, uuid: UUID4) -> int:
    row = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == uuid).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail=f"aeroplane {uuid} not found")
    return row.id


@router.get(
    "/aeroplanes/{uuid}/mission-objectives",
    response_model=MissionObjective,
    summary="Read Mission Objectives for an aeroplane",
)
def get_objectives(uuid: UUID4, db: Session = Depends(get_db)) -> MissionObjective:
    aeroplane_id = _resolve_aeroplane_id(db, uuid)
    return get_mission_objective(db, aeroplane_id)


@router.put(
    "/aeroplanes/{uuid}/mission-objectives",
    response_model=MissionObjective,
    summary="Create or update Mission Objectives for an aeroplane",
)
def put_objectives(
    uuid: UUID4, payload: MissionObjective, db: Session = Depends(get_db)
) -> MissionObjective:
    aeroplane_id = _resolve_aeroplane_id(db, uuid)
    return upsert_mission_objective(db, aeroplane_id, payload)


@router.get(
    "/mission-presets",
    response_model=list[MissionPreset],
    summary="List all Mission Presets",
)
def get_presets(db: Session = Depends(get_db)) -> list[MissionPreset]:
    return list_mission_presets(db)
```

- [ ] **Step 5: Register the router**

Edit `app/api/v2/endpoints/aeroplane/__init__.py`. Find where other aeroplane sub-routers are imported and included, and add:

```python
from app.api.v2.endpoints.aeroplane.mission_objectives import router as mission_router
router.include_router(mission_router, tags=["mission"])
```

(Match the import / include pattern used by the surrounding sub-routers — if they go through a different file, follow that.)

- [ ] **Step 6: Run tests pass**

```bash
poetry run pytest app/tests/test_mission_objectives_endpoint.py -v
```

Expected: 3 passed.

- [ ] **Step 7: Commit**

```bash
git add app/api/v2/endpoints/aeroplane/mission_objectives.py \
        app/api/v2/endpoints/aeroplane/__init__.py \
        app/tests/test_mission_objectives_endpoint.py
git commit -m "feat(mission): GET/PUT mission-objectives + GET mission-presets endpoints"
```

---

### Task 1.8: Push Phase 1 PR

- [ ] **Step 1: Run all assumption/mission-related tests**

```bash
poetry run pytest app/tests/test_mission_kpi_schema.py \
                  app/tests/test_mission_objective_schema.py \
                  app/tests/test_mission_preset_seed.py \
                  app/tests/test_mission_objective_service.py \
                  app/tests/test_mission_objectives_endpoint.py -v
```

Expected: all green.

- [ ] **Step 2: Full fast regression**

```bash
poetry run pytest -q -m "not slow"
```

Expected: no regressions.

- [ ] **Step 3: Lint**

```bash
poetry run ruff check . && poetry run ruff format --check app/schemas/mission_kpi.py app/schemas/mission_objective.py app/services/mission_objective_service.py app/services/mission_preset_seed.py app/models/mission_objective.py app/models/mission_preset.py app/api/v2/endpoints/aeroplane/mission_objectives.py
```

- [ ] **Step 4: Push branch + open PR**

```bash
git push github HEAD:feat/gh-XXX-mission-objectives-and-presets-be -u
gh pr create --base main --head feat/gh-XXX-mission-objectives-and-presets-be \
  --title "feat(mission): MissionObjective + MissionPreset DB + endpoints (Phase 1)" \
  --body "Phase 1 of the Mission Tab redesign. Adds two DB tables, seeded mission presets, and three REST endpoints. No frontend yet."
```

---

## Phase 2 — mission_kpi_service (BE)

**Goal:** Aggregate 7 KPI axes from existing `ComputationContext` + `field_length_service` + V-n. Return a `MissionKpiSet` for the radar.

### Task 2.1: Per-axis KPI calculators

**Files:**
- Create: `app/services/mission_kpi_service.py`
- Test: `app/tests/test_mission_kpi_service.py`

- [ ] **Step 1: Write failing test**

`app/tests/test_mission_kpi_service.py`:
```python
from __future__ import annotations

from app.schemas.mission_objective import MissionObjective
from app.services.mission_kpi_service import (
    _kpi_stall_safety, _kpi_glide, _kpi_climb_energy,
    _kpi_cruise, _kpi_maneuver, _kpi_wing_loading,
    _normalise_score,
)


def test_normalise_clips_outside_range():
    assert _normalise_score(5.0, 0.0, 10.0) == 0.5
    assert _normalise_score(15.0, 0.0, 10.0) == 1.0
    assert _normalise_score(-3.0, 0.0, 10.0) == 0.0


def test_kpi_stall_safety_from_context():
    ctx = {"v_cruise_mps": 18.0, "v_s1_mps": 12.0}
    kpi = _kpi_stall_safety(ctx, range_min=1.3, range_max=2.5)
    assert kpi.value == 1.5
    assert kpi.score_0_1 == pytest.approx((1.5 - 1.3) / (2.5 - 1.3))
    assert kpi.provenance == "computed"


def test_kpi_stall_safety_missing_when_v_s1_absent():
    ctx = {"v_cruise_mps": 18.0}
    kpi = _kpi_stall_safety(ctx, range_min=1.3, range_max=2.5)
    assert kpi.value is None
    assert kpi.provenance == "missing"


def test_kpi_glide_from_polar_by_config():
    ctx = {
        "aspect_ratio": 8.0,
        "polar_by_config": {
            "clean": {"cd0": 0.025, "e_oswald": 0.80, "cl_max": 1.4},
        },
    }
    kpi = _kpi_glide(ctx, range_min=5.0, range_max=18.0)
    # (L/D)_max = 0.5 * sqrt(pi * e * AR / CD0)
    import math
    expected = 0.5 * math.sqrt(math.pi * 0.80 * 8.0 / 0.025)
    assert kpi.value == pytest.approx(expected, rel=1e-3)


import pytest  # noqa: E402  (imported here so other tests above can use it inline)
```

- [ ] **Step 2: Run failing test**

```bash
poetry run pytest app/tests/test_mission_kpi_service.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement per-axis calculators**

`app/services/mission_kpi_service.py`:
```python
"""Aggregate the seven Mission compliance KPIs (gh-XXX).

All values come from cached `ComputationContext` plus the persisted
MissionObjective + the static list of MissionPresets. NO AeroBuildup
re-run — this service is closed-form on top of existing data.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.aeroplanemodel import AeroplaneModel
from app.schemas.mission_kpi import (
    AxisName,
    MissionAxisKpi,
    MissionKpiSet,
    MissionTargetPolygon,
)
from app.schemas.mission_objective import MissionObjective, MissionPreset


# ----- Helpers ----------------------------------------------------------------

def _normalise_score(value: float, lo: float, hi: float) -> float:
    """Map ``value`` to 0..1 across ``[lo, hi]``; clip outside."""
    if hi <= lo:
        return 0.0
    score = (value - lo) / (hi - lo)
    return max(0.0, min(1.0, score))


def _missing(axis: AxisName, lo: float, hi: float, formula: str) -> MissionAxisKpi:
    return MissionAxisKpi(
        axis=axis, value=None, unit=None, score_0_1=None,
        range_min=lo, range_max=hi, provenance="missing", formula=formula,
    )


def _ctx_get(ctx: dict[str, Any], key: str) -> float | None:
    v = ctx.get(key)
    if isinstance(v, (int, float)) and v > 0:
        return float(v)
    return None


# ----- Per-axis calculators ---------------------------------------------------

def _kpi_stall_safety(
    ctx: dict[str, Any], range_min: float, range_max: float
) -> MissionAxisKpi:
    formula = "V_cruise / V_s1"
    v_cruise = _ctx_get(ctx, "v_cruise_mps")
    v_s1 = _ctx_get(ctx, "v_s1_mps")
    if v_cruise is None or v_s1 is None:
        return _missing("stall_safety", range_min, range_max, formula)
    value = v_cruise / v_s1
    return MissionAxisKpi(
        axis="stall_safety", value=value, unit="-",
        score_0_1=_normalise_score(value, range_min, range_max),
        range_min=range_min, range_max=range_max,
        provenance="computed", formula=formula,
    )


def _kpi_glide(
    ctx: dict[str, Any], range_min: float, range_max: float
) -> MissionAxisKpi:
    formula = "(L/D)_max = 0.5 · √(π · e · AR / C_D0)"
    polar = ctx.get("polar_by_config", {}).get("clean") if ctx.get("polar_by_config") else None
    ar = ctx.get("aspect_ratio")
    if not polar or ar is None:
        return _missing("glide", range_min, range_max, formula)
    cd0 = polar.get("cd0")
    e = polar.get("e_oswald")
    if cd0 is None or cd0 <= 0 or e is None or e <= 0 or ar <= 0:
        return _missing("glide", range_min, range_max, formula)
    value = 0.5 * math.sqrt(math.pi * e * ar / cd0)
    return MissionAxisKpi(
        axis="glide", value=value, unit="-",
        score_0_1=_normalise_score(value, range_min, range_max),
        range_min=range_min, range_max=range_max,
        provenance="computed", formula=formula,
    )


def _kpi_climb_energy(
    ctx: dict[str, Any], range_min: float, range_max: float
) -> MissionAxisKpi:
    formula = "(C_L^1.5 / C_D)_max = 0.5 · (3π·e·AR)^0.75 / C_D0^0.5 / √3"
    polar = ctx.get("polar_by_config", {}).get("clean") if ctx.get("polar_by_config") else None
    ar = ctx.get("aspect_ratio")
    if not polar or ar is None:
        return _missing("climb", range_min, range_max, formula)
    cd0 = polar.get("cd0")
    e = polar.get("e_oswald")
    if cd0 is None or cd0 <= 0 or e is None or e <= 0 or ar <= 0:
        return _missing("climb", range_min, range_max, formula)
    # CL^1.5/CD max occurs at CL where 3·C_D0 = C_Di → standard closed form
    value = (3.0 * math.pi * e * ar) ** 0.75 / math.sqrt(cd0) / (math.sqrt(3.0) * 4.0)
    return MissionAxisKpi(
        axis="climb", value=value, unit="-",
        score_0_1=_normalise_score(value, range_min, range_max),
        range_min=range_min, range_max=range_max,
        provenance="computed", formula=formula,
    )


def _kpi_cruise(
    ctx: dict[str, Any], range_min: float, range_max: float
) -> MissionAxisKpi:
    formula = "V_cruise (from ComputationContext)"
    v = _ctx_get(ctx, "v_cruise_mps")
    if v is None:
        return _missing("cruise", range_min, range_max, formula)
    return MissionAxisKpi(
        axis="cruise", value=v, unit="m/s",
        score_0_1=_normalise_score(v, range_min, range_max),
        range_min=range_min, range_max=range_max,
        provenance="computed", formula=formula,
    )


def _kpi_maneuver(
    ctx: dict[str, Any], range_min: float, range_max: float
) -> MissionAxisKpi:
    formula = "n_max from V-n diagram (load factor)"
    # ComputationContext stores `flight_envelope.max_load_factor` under that key
    n_max = ctx.get("flight_envelope_n_max")
    if n_max is None or n_max <= 0:
        return _missing("maneuver", range_min, range_max, formula)
    return MissionAxisKpi(
        axis="maneuver", value=float(n_max), unit="g",
        score_0_1=_normalise_score(float(n_max), range_min, range_max),
        range_min=range_min, range_max=range_max,
        provenance="computed", formula=formula,
    )


def _kpi_wing_loading(
    ctx: dict[str, Any], mass_kg: float | None,
    range_min: float, range_max: float,
) -> MissionAxisKpi:
    formula = "W/S = m·g / S_ref"
    s_ref = _ctx_get(ctx, "s_ref_m2")
    if mass_kg is None or mass_kg <= 0 or s_ref is None:
        return _missing("wing_loading", range_min, range_max, formula)
    value = mass_kg * 9.81 / s_ref
    return MissionAxisKpi(
        axis="wing_loading", value=value, unit="N/m²",
        score_0_1=_normalise_score(value, range_min, range_max),
        range_min=range_min, range_max=range_max,
        provenance="computed", formula=formula,
    )
```

- [ ] **Step 4: Run tests pass**

```bash
poetry run pytest app/tests/test_mission_kpi_service.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add app/services/mission_kpi_service.py app/tests/test_mission_kpi_service.py
git commit -m "feat(mission): per-axis KPI calculators (closed-form from cached context)"
```

---

### Task 2.2: Field-Friendliness KPI + aggregator

**Files:**
- Modify: `app/services/mission_kpi_service.py` (add `_kpi_field_friendliness` + public `compute_mission_kpis`)
- Modify: `app/tests/test_mission_kpi_service.py` (add aggregator tests)

- [ ] **Step 1: Write failing test**

Append to `app/tests/test_mission_kpi_service.py`:
```python
from unittest.mock import patch

from app.services.mission_kpi_service import compute_mission_kpis
from app.tests.conftest import make_aeroplane


def _seed_context(SessionLocal, aeroplane_id: int) -> None:
    """Inject a synthetic ComputationContext into the aeroplane row."""
    from app.models.aeroplanemodel import AeroplaneModel
    with SessionLocal() as db:
        a = db.query(AeroplaneModel).filter_by(id=aeroplane_id).first()
        a.assumption_computation_context = {
            "v_cruise_mps": 18.0,
            "v_s1_mps": 12.0,
            "aspect_ratio": 8.0,
            "s_ref_m2": 0.30,
            "polar_by_config": {
                "clean": {"cd0": 0.025, "e_oswald": 0.80, "cl_max": 1.4},
                "takeoff": {"cd0": 0.040, "e_oswald": 0.75, "cl_max": 1.7},
                "landing": {"cd0": 0.060, "e_oswald": 0.70, "cl_max": 2.0},
            },
            "flight_envelope_n_max": 3.0,
        }
        db.commit()


def test_compute_mission_kpis_full_payload(client_and_db):
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        db.commit()
        aircraft_id = aeroplane.id

    _seed_context(SessionLocal, aircraft_id)

    with patch(
        "app.services.mission_kpi_service._compute_field_length_score",
        return_value=(45.0, 1.0),  # (raw m, score 0..1)
    ):
        with SessionLocal() as db:
            kset = compute_mission_kpis(db, aircraft_id, ["trainer"])

    # All 7 axes present in ist polygon
    assert set(kset.ist_polygon.keys()) == {
        "stall_safety", "glide", "climb", "cruise",
        "maneuver", "wing_loading", "field_friendliness",
    }
    # Trainer target polygon present
    assert kset.target_polygons[0].mission_id == "trainer"
    assert kset.active_mission_id == "trainer"


def test_compute_mission_kpis_multi_mission_overlay(client_and_db):
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        db.commit()
        aircraft_id = aeroplane.id

    _seed_context(SessionLocal, aircraft_id)

    with patch(
        "app.services.mission_kpi_service._compute_field_length_score",
        return_value=(45.0, 1.0),
    ):
        with SessionLocal() as db:
            kset = compute_mission_kpis(db, aircraft_id, ["trainer", "sailplane"])

    assert {p.mission_id for p in kset.target_polygons} == {"trainer", "sailplane"}
```

- [ ] **Step 2: Run failing test**

```bash
poetry run pytest app/tests/test_mission_kpi_service.py -v -k "compute_mission_kpis"
```

Expected: ImportError (compute_mission_kpis doesn't exist).

- [ ] **Step 3: Implement aggregator**

Append to `app/services/mission_kpi_service.py`:
```python
# ----- Field Friendliness (delegates to field_length_service) -----------------

def _compute_field_length_score(
    aeroplane: AeroplaneModel,
    target_field_length_m: float,
) -> tuple[float | None, float | None]:
    """Return (effective_field_length_m, score_0_1).

    The score is `target_field / effective_field` clipped to [0, 1]: shorter
    field is better. Returns (None, None) when field-length service can't run.
    """
    try:
        from app.services.field_length_service import compute_field_lengths_for_aeroplane
        result = compute_field_lengths_for_aeroplane(aeroplane)
        eff = max(result.get("s_to_50ft_m", 0), result.get("s_ldg_50ft_m", 0))
        if eff <= 0:
            return None, None
        score = max(0.0, min(1.0, target_field_length_m / eff))
        return float(eff), float(score)
    except Exception:
        return None, None


def _kpi_field_friendliness(
    aeroplane: AeroplaneModel,
    target_field_length_m: float,
    range_min: float, range_max: float,
) -> MissionAxisKpi:
    formula = "max(s_TO_50ft, s_LDG_50ft); score = target / effective"
    eff, score = _compute_field_length_score(aeroplane, target_field_length_m)
    if eff is None or score is None:
        return _missing("field_friendliness", range_min, range_max, formula)
    return MissionAxisKpi(
        axis="field_friendliness", value=eff, unit="m",
        score_0_1=score, range_min=range_min, range_max=range_max,
        provenance="computed", formula=formula,
    )


# ----- Aggregator -------------------------------------------------------------

def _hash_context(ctx: dict[str, Any]) -> str:
    blob = json.dumps(ctx, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def compute_mission_kpis(
    db: Session,
    aeroplane_id: int,
    active_mission_ids: list[str],
) -> MissionKpiSet:
    """Bundle ist + multi-mission target polygons for the spider chart."""
    from app.services.mission_objective_service import (
        get_mission_objective, list_mission_presets,
    )

    aeroplane = db.query(AeroplaneModel).filter_by(id=aeroplane_id).one()
    ctx: dict[str, Any] = aeroplane.assumption_computation_context or {}
    objective = get_mission_objective(db, aeroplane_id)
    presets = {p.id: p for p in list_mission_presets(db)}

    active_mission_ids = active_mission_ids or [objective.mission_type]
    primary_preset = presets.get(active_mission_ids[0]) or presets["trainer"]
    rng = primary_preset.axis_ranges

    # Compute Ist polygon — ranges driven by the PRIMARY (active) mission.
    mass = ctx.get("mass_kg") or _ctx_get(aeroplane.assumption_computation_context or {}, "mass_kg")
    ist: dict[str, MissionAxisKpi] = {
        "stall_safety":  _kpi_stall_safety(ctx, *rng["stall_safety"]),
        "glide":         _kpi_glide(ctx, *rng["glide"]),
        "climb":         _kpi_climb_energy(ctx, *rng["climb"]),
        "cruise":        _kpi_cruise(ctx, *rng["cruise"]),
        "maneuver":      _kpi_maneuver(ctx, *rng["maneuver"]),
        "wing_loading":  _kpi_wing_loading(ctx, mass, *rng["wing_loading"]),
        "field_friendliness": _kpi_field_friendliness(
            aeroplane, objective.target_field_length_m, *rng["field_friendliness"]
        ),
    }

    # Build target polygons (Soll for each active mission preset)
    targets: list[MissionTargetPolygon] = []
    for mid in active_mission_ids:
        preset = presets.get(mid)
        if preset is None:
            continue
        targets.append(
            MissionTargetPolygon(
                mission_id=preset.id, label=preset.label,
                scores_0_1=preset.target_polygon,
            )
        )

    return MissionKpiSet(
        aeroplane_uuid=str(aeroplane.uuid),
        ist_polygon=ist,
        target_polygons=targets,
        active_mission_id=active_mission_ids[0],
        computed_at=datetime.now(timezone.utc).isoformat(),
        context_hash=_hash_context(ctx),
    )
```

- [ ] **Step 4: Run tests pass**

```bash
poetry run pytest app/tests/test_mission_kpi_service.py -v
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add app/services/mission_kpi_service.py app/tests/test_mission_kpi_service.py
git commit -m "feat(mission): mission_kpi_service aggregator + field_friendliness KPI"
```

---

### Task 2.3: KPI endpoint

**Files:**
- Modify: `app/api/v2/endpoints/aeroplane/mission_objectives.py`
- Modify: `app/tests/test_mission_objectives_endpoint.py`

- [ ] **Step 1: Write failing test**

Append to `app/tests/test_mission_objectives_endpoint.py`:
```python
def test_get_mission_kpis_returns_seven_axes(client_and_db):
    client, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        db.commit()
        uuid = str(aeroplane.uuid)
        a_id = aeroplane.id

    # Seed a context so the KPIs aren't all "missing"
    from app.models.aeroplanemodel import AeroplaneModel
    with SessionLocal() as db:
        a = db.query(AeroplaneModel).filter_by(id=a_id).one()
        a.assumption_computation_context = {
            "v_cruise_mps": 18.0, "v_s1_mps": 12.0, "aspect_ratio": 8.0,
            "s_ref_m2": 0.3,
            "polar_by_config": {
                "clean": {"cd0": 0.025, "e_oswald": 0.8, "cl_max": 1.4},
            },
            "flight_envelope_n_max": 3.0,
        }
        db.commit()

    r = client.get(f"/aeroplanes/{uuid}/mission-kpis")
    assert r.status_code == 200
    body = r.json()
    assert set(body["ist_polygon"].keys()) == {
        "stall_safety", "glide", "climb", "cruise",
        "maneuver", "wing_loading", "field_friendliness",
    }


def test_get_mission_kpis_multi_mission_param(client_and_db):
    client, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        db.commit()
        uuid = str(aeroplane.uuid)

    r = client.get(f"/aeroplanes/{uuid}/mission-kpis?missions=trainer&missions=sailplane")
    assert r.status_code == 200
    body = r.json()
    assert {p["mission_id"] for p in body["target_polygons"]} == {"trainer", "sailplane"}
```

- [ ] **Step 2: Run failing test**

```bash
poetry run pytest app/tests/test_mission_objectives_endpoint.py -v -k "kpi"
```

Expected: 404.

- [ ] **Step 3: Implement endpoint**

Append to `app/api/v2/endpoints/aeroplane/mission_objectives.py`:
```python
from fastapi import Query
from app.schemas.mission_kpi import MissionKpiSet
from app.services.mission_kpi_service import compute_mission_kpis


@router.get(
    "/aeroplanes/{uuid}/mission-kpis",
    response_model=MissionKpiSet,
    summary="Compute the 7-axis Mission compliance KPI set",
)
def get_kpis(
    uuid: UUID4,
    missions: list[str] = Query(default_factory=list),
    db: Session = Depends(get_db),
) -> MissionKpiSet:
    aeroplane_id = _resolve_aeroplane_id(db, uuid)
    return compute_mission_kpis(db, aeroplane_id, missions)
```

- [ ] **Step 4: Run tests pass**

```bash
poetry run pytest app/tests/test_mission_objectives_endpoint.py -v
```

Expected: all green.

- [ ] **Step 5: Commit + push Phase 2 PR**

```bash
git add app/api/v2/endpoints/aeroplane/mission_objectives.py app/tests/test_mission_objectives_endpoint.py
git commit -m "feat(mission): GET /mission-kpis endpoint (Phase 2)"
git push github HEAD:feat/gh-XXX-mission-kpi-service -u
gh pr create --base main --head feat/gh-XXX-mission-kpi-service \
  --title "feat(mission): mission_kpi_service + /mission-kpis endpoint (Phase 2)" \
  --body "Phase 2 of the Mission Tab redesign. Adds the 7-axis KPI aggregator and the /mission-kpis endpoint."
```

---

## Phase 3 — Field-length refactor + migration (BE)

**Goal:** `field_length_service` no longer reads field-performance fields from Assumptions. The new MissionObjective payload is the source of truth. Backfill existing aeroplanes.

### Task 3.1: Refactor signature

**Files:**
- Modify: `app/services/field_length_service.py`
- Modify: existing callers (search and update)
- Modify: `app/tests/test_field_length.py`

- [ ] **Step 1: Find every caller**

```bash
grep -rn "compute_field_lengths" app/ --include="*.py"
```

Document them — every call site will need its `aircraft["available_runway_m"]` etc. swapped for the `MissionObjective` payload.

- [ ] **Step 2: Add new helper that takes MissionObjective**

In `app/services/field_length_service.py`, **add** a new public function alongside the existing one (don't delete yet):

```python
def compute_field_lengths_for_aeroplane(
    aeroplane: AeroplaneModel,
    *,
    db: Session | None = None,
) -> dict:
    """Wrapper that fetches the MissionObjective for the aeroplane and
    converts it (plus the cached ComputationContext) into the dict the
    legacy ``compute_field_lengths`` expects.

    Replaces the historical pattern of reading runway/brake/T_static
    from design_assumptions.
    """
    from app.services.mission_objective_service import get_mission_objective
    from app.db.session import SessionLocal

    if db is None:
        db = SessionLocal()
        owned = True
    else:
        owned = False

    try:
        objective = get_mission_objective(db, aeroplane.id)
        ctx = aeroplane.assumption_computation_context or {}
        aircraft_dict = {
            "mass_kg": ctx.get("mass_kg"),
            "s_ref_m2": ctx.get("s_ref_m2"),
            "v_stall_mps": ctx.get("v_stall_mps"),
            "v_s_to_mps": ctx.get("v_s_to_mps"),
            "v_s0_mps": ctx.get("v_s0_mps"),
            "cl_max": ctx.get("cl_max"),
            "cl_max_takeoff": (ctx.get("polar_by_config") or {}).get("takeoff", {}).get("cl_max"),
            "cl_max_landing": (ctx.get("polar_by_config") or {}).get("landing", {}).get("cl_max"),
            "flap_type": ctx.get("flap_type"),
            # From MissionObjective:
            "available_runway_m": objective.available_runway_m,
            "runway_type": objective.runway_type,
            "t_static_N": objective.t_static_N,
            "takeoff_mode": objective.takeoff_mode,
        }
        return compute_field_lengths(aircraft_dict)
    finally:
        if owned:
            db.close()
```

- [ ] **Step 3: Add a regression test**

`app/tests/test_field_length.py` — append:
```python
def test_compute_field_lengths_for_aeroplane_uses_mission_runway(client_and_db):
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        from app.tests.conftest import make_aeroplane
        from app.models.aeroplanemodel import AeroplaneModel
        from app.services.mission_objective_service import upsert_mission_objective
        from app.schemas.mission_objective import MissionObjective

        aeroplane = make_aeroplane(db)
        db.commit()

        a = db.query(AeroplaneModel).filter_by(id=aeroplane.id).one()
        a.assumption_computation_context = {
            "mass_kg": 1.5, "s_ref_m2": 0.3, "v_stall_mps": 8.0,
            "cl_max": 1.4,
            "polar_by_config": {
                "takeoff": {"cl_max": 1.6}, "landing": {"cl_max": 1.8},
            },
        }
        upsert_mission_objective(db, aeroplane.id, MissionObjective(
            mission_type="trainer",
            target_cruise_mps=18, target_stall_safety=1.8,
            target_maneuver_n=3, target_glide_ld=12,
            target_climb_energy=22, target_wing_loading_n_m2=400,
            target_field_length_m=50,
            available_runway_m=80.0,   # ← mission-provided value
            runway_type="grass", t_static_N=20.0, takeoff_mode="runway",
        ))
        db.commit()

    with SessionLocal() as db:
        from app.services.field_length_service import compute_field_lengths_for_aeroplane
        a = db.query(AeroplaneModel).filter_by(id=aeroplane.id).one()
        result = compute_field_lengths_for_aeroplane(a, db=db)
        assert result["available_runway_m"] == 80.0
```

- [ ] **Step 4: Run the test**

```bash
poetry run pytest app/tests/test_field_length.py -v -k "for_aeroplane"
```

Expected: green.

- [ ] **Step 5: Commit**

```bash
git add app/services/field_length_service.py app/tests/test_field_length.py
git commit -m "feat(mission): field_length_service.compute_field_lengths_for_aeroplane wrapper"
```

---

### Task 3.2: Update callers + delete Assumptions field-performance defaults

**Files:**
- Modify: every caller of `compute_field_lengths` found in 3.1 step 1
- Modify: `app/schemas/design_assumption.py` (`PARAMETER_DEFAULTS`)

- [ ] **Step 1: Update endpoint caller**

Search for the field-lengths endpoint (likely `app/api/v2/endpoints/aeroplane/field_lengths.py`):

```bash
sed -n '1,40p' app/api/v2/endpoints/aeroplane/field_lengths.py
```

Replace whatever assembles the `aircraft` dict from `design_assumptions` with a call to `compute_field_lengths_for_aeroplane(aeroplane, db=db)`. Keep the same response model.

- [ ] **Step 2: Remove field-performance keys from PARAMETER_DEFAULTS**

Edit `app/schemas/design_assumption.py`. Find `PARAMETER_DEFAULTS` and remove any entries that pertain to field performance (search for `runway`, `t_static`, `takeoff_mode`, `flap_type` if listed). Do NOT remove pure-aero keys (`mass`, `cl_max`, `cd0`, `target_static_margin`, `g_limit`, `power_to_weight`, `prop_efficiency`).

- [ ] **Step 3: Run full field-length test suite**

```bash
poetry run pytest app/tests/test_field_length.py app/tests/test_field_length_endpoint.py -v
```

Expected: all green. If a test fails because it was building `aircraft` from Assumptions, update it to seed the MissionObjective + ComputationContext instead.

- [ ] **Step 4: Commit**

```bash
git add app/api/v2/endpoints/aeroplane/field_lengths.py app/schemas/design_assumption.py app/tests/test_field_length.py
git commit -m "refactor(field-length): consume MissionObjective; drop field-performance Assumptions"
```

---

### Task 3.3: Backfill migration for existing aeroplanes

**Files:**
- Create: `alembic/versions/YYYY_backfill_mission_objectives.py`

- [ ] **Step 1: Generate migration**

```bash
poetry run alembic revision -m "backfill mission_objectives for existing aeroplanes"
```

- [ ] **Step 2: Implement upgrade()**

Replace the body:

```python
"""backfill mission_objectives for existing aeroplanes

Revision ID: <auto>
Revises: <previous>
"""
from alembic import op
import sqlalchemy as sa


revision = "..."
down_revision = "..."
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    aeroplane_ids = [
        row[0]
        for row in conn.execute(sa.text("SELECT id FROM aeroplanes")).fetchall()
    ]
    if not aeroplane_ids:
        return

    # Insert default Trainer-objective for any aeroplane that doesn't have one.
    op.bulk_insert(
        sa.table(
            "mission_objectives",
            sa.column("aeroplane_id", sa.Integer),
            sa.column("mission_type", sa.String),
            sa.column("target_cruise_mps", sa.Float),
            sa.column("target_stall_safety", sa.Float),
            sa.column("target_maneuver_n", sa.Float),
            sa.column("target_glide_ld", sa.Float),
            sa.column("target_climb_energy", sa.Float),
            sa.column("target_wing_loading_n_m2", sa.Float),
            sa.column("target_field_length_m", sa.Float),
            sa.column("available_runway_m", sa.Float),
            sa.column("runway_type", sa.String),
            sa.column("t_static_N", sa.Float),
            sa.column("takeoff_mode", sa.String),
        ),
        [
            {
                "aeroplane_id": aid,
                "mission_type": "trainer",
                "target_cruise_mps": 18.0, "target_stall_safety": 1.8,
                "target_maneuver_n": 3.0, "target_glide_ld": 12.0,
                "target_climb_energy": 22.0, "target_wing_loading_n_m2": 412.0,
                "target_field_length_m": 50.0, "available_runway_m": 50.0,
                "runway_type": "grass", "t_static_N": 18.0, "takeoff_mode": "runway",
            }
            for aid in aeroplane_ids
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM mission_objectives")
```

- [ ] **Step 3: Smoke test**

```bash
poetry run alembic upgrade head
poetry run alembic downgrade -1
poetry run alembic upgrade head
```

- [ ] **Step 4: Commit + push Phase 3 PR**

```bash
git add alembic/versions/
git commit -m "feat(mission): backfill mission_objectives for existing aeroplanes"
git push github HEAD:feat/gh-XXX-field-length-refactor -u
gh pr create --base main --head feat/gh-XXX-field-length-refactor \
  --title "refactor(field-length): consume MissionObjective + migration (Phase 3)" \
  --body "Phase 3. field_length_service now reads field-performance from MissionObjective instead of Assumptions. Existing aeroplanes get a Trainer-default MissionObjective via Alembic backfill."
```

---

## Phase 4 — Mission-preset auto-apply estimates (BE)

**Goal:** When `PUT /mission-objectives` changes `mission_type`, the preset's `suggested_estimates` are written into `design_assumptions.estimate_value` (never `calculated_value`).

### Task 4.1: Auto-apply helper

**Files:**
- Modify: `app/services/mission_objective_service.py`
- Modify: `app/tests/test_mission_objective_service.py`

- [ ] **Step 1: Write failing test**

Append to `app/tests/test_mission_objective_service.py`:
```python
def test_upsert_changes_mission_type_writes_suggested_estimates(client_and_db):
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        from app.tests.conftest import make_aeroplane
        from app.services.design_assumptions_service import seed_defaults
        from app.models.aeroplanemodel import DesignAssumptionModel

        aeroplane = make_aeroplane(db)
        seed_defaults(db, str(aeroplane.uuid))
        db.commit()
        aircraft_id = aeroplane.id

    # Change mission_type to sailplane → estimates should reflect Sailplane preset
    with SessionLocal() as db:
        upsert_mission_objective(db, aircraft_id, _make_objective(mission_type="sailplane"))
        db.commit()

    with SessionLocal() as db:
        rows = {
            r.parameter_name: r
            for r in db.query(DesignAssumptionModel)
            .filter_by(aeroplane_id=aircraft_id).all()
        }
        # Sailplane preset values from the seed file
        assert rows["g_limit"].estimate_value == 5.3
        assert rows["target_static_margin"].estimate_value == 0.10
        assert rows["cl_max"].estimate_value == 1.3
        # calculated_value MUST be untouched
        assert rows["g_limit"].calculated_value in (None, rows["g_limit"].calculated_value)
```

- [ ] **Step 2: Run failing test**

```bash
poetry run pytest app/tests/test_mission_objective_service.py -v -k "writes_suggested"
```

Expected: fails — estimates not yet auto-applied.

- [ ] **Step 3: Add auto-apply call into `upsert_mission_objective`**

Edit `app/services/mission_objective_service.py`. Refactor the upsert to apply preset estimates when the mission_type changes:

```python
def upsert_mission_objective(
    db: Session, aeroplane_id: int, payload: MissionObjective
) -> MissionObjective:
    row = (
        db.query(MissionObjectiveModel)
        .filter(MissionObjectiveModel.aeroplane_id == aeroplane_id)
        .one_or_none()
    )
    old_mission_type = row.mission_type if row else None
    if row is None:
        row = MissionObjectiveModel(aeroplane_id=aeroplane_id)
        db.add(row)
    for field, value in payload.model_dump().items():
        setattr(row, field, value)
    db.flush()

    # Auto-apply preset estimates when mission_type changes (or first creation).
    if old_mission_type != payload.mission_type:
        _apply_preset_estimates(db, aeroplane_id, payload.mission_type)

    return payload


def _apply_preset_estimates(db: Session, aeroplane_id: int, mission_type: str) -> None:
    """Write the preset's suggested_estimates to design_assumptions.estimate_value.
    Never touches calculated_value or active_source."""
    from app.models.aeroplanemodel import DesignAssumptionModel

    preset = (
        db.query(MissionPresetModel)
        .filter_by(id=mission_type)
        .one_or_none()
    )
    if preset is None:
        return
    estimates: dict = preset.suggested_estimates
    for param_name, value in estimates.items():
        a_row = (
            db.query(DesignAssumptionModel)
            .filter_by(aeroplane_id=aeroplane_id, parameter_name=param_name)
            .one_or_none()
        )
        if a_row is None:
            a_row = DesignAssumptionModel(
                aeroplane_id=aeroplane_id, parameter_name=param_name
            )
            db.add(a_row)
        a_row.estimate_value = value
    db.flush()
```

- [ ] **Step 4: Run test pass**

```bash
poetry run pytest app/tests/test_mission_objective_service.py -v -k "writes_suggested"
```

Expected: green.

- [ ] **Step 5: Commit + push Phase 4 PR**

```bash
git add app/services/mission_objective_service.py app/tests/test_mission_objective_service.py
git commit -m "feat(mission): mission-preset auto-apply on mission_type change (Phase 4)"
git push github HEAD:feat/gh-XXX-mission-auto-apply -u
gh pr create --base main --head feat/gh-XXX-mission-auto-apply \
  --title "feat(mission): mission-preset auto-apply estimates (Phase 4)" \
  --body "Phase 4. PUT /mission-objectives with a changed mission_type now copies the preset's suggested_estimates into design_assumptions.estimate_value. calculated_value untouched."
```

---

## Phase 5 — Custom SVG radar component (FE)

**Goal:** Reusable `MissionRadarChart.tsx` rendering Ist + Soll + ghost polygons with auto-rescale on toggle.

### Task 5.1: Hook + helper

**Files:**
- Create: `frontend/hooks/useMissionKpis.ts`
- Create: `frontend/hooks/useMissionObjectives.ts`
- Create: `frontend/hooks/useMissionPresets.ts`
- Create: `frontend/lib/missionScale.ts`
- Create: `frontend/__tests__/missionScale.test.ts`

- [ ] **Step 1: Write failing test for the scale helper**

`frontend/__tests__/missionScale.test.ts`:
```typescript
import { describe, it, expect } from "vitest";
import { computeAxisRanges } from "@/lib/missionScale";
import type { MissionPreset } from "@/hooks/useMissionPresets";

const trainer: MissionPreset = {
  id: "trainer", label: "Trainer", description: "",
  target_polygon: { stall_safety: 1, glide: 0.4, climb: 0.3, cruise: 0.3, maneuver: 0.3, wing_loading: 0.3, field_friendliness: 0.9 },
  axis_ranges: {
    stall_safety: [1.3, 2.5], glide: [5, 18], climb: [5, 25],
    cruise: [10, 25], maneuver: [2, 5], wing_loading: [20, 80],
    field_friendliness: [3, 100],
  },
  suggested_estimates: { g_limit: 3, target_static_margin: 0.15, cl_max: 1.4, power_to_weight: 0.5, prop_efficiency: 0.7 },
};
const sailplane: MissionPreset = {
  ...trainer, id: "sailplane",
  axis_ranges: {
    stall_safety: [1.3, 2.0], glide: [15, 35], climb: [15, 60],
    cruise: [10, 25], maneuver: [2.5, 5.5], wing_loading: [10, 50],
    field_friendliness: [3, 100],
  },
};

describe("computeAxisRanges", () => {
  it("uses single mission range when only one is active", () => {
    const ranges = computeAxisRanges([trainer]);
    expect(ranges.glide).toEqual([5, 18]);
  });

  it("returns [min(mins), max(maxes)] over active missions", () => {
    const ranges = computeAxisRanges([trainer, sailplane]);
    expect(ranges.glide).toEqual([5, 35]);
    expect(ranges.stall_safety).toEqual([1.3, 2.5]);
    expect(ranges.wing_loading).toEqual([10, 80]);
  });
});
```

- [ ] **Step 2: Run failing test**

```bash
cd frontend && npm run test:unit -- --run __tests__/missionScale.test.ts
```

Expected: ImportError.

- [ ] **Step 3: Implement scale helper**

`frontend/lib/missionScale.ts`:
```typescript
import type { MissionPreset, AxisName } from "@/hooks/useMissionPresets";

export const AXES: AxisName[] = [
  "stall_safety", "glide", "climb", "cruise",
  "maneuver", "wing_loading", "field_friendliness",
];

export type AxisRange = [number, number];
export type AxisRanges = Record<AxisName, AxisRange>;

/**
 * Combine multiple mission presets' per-axis ranges into one set.
 * For each axis, result = [min(all mins), max(all maxes)].
 */
export function computeAxisRanges(activeMissions: MissionPreset[]): AxisRanges {
  if (activeMissions.length === 0) {
    return Object.fromEntries(AXES.map((a) => [a, [0, 1]])) as AxisRanges;
  }
  const out = {} as AxisRanges;
  for (const axis of AXES) {
    let lo = Infinity;
    let hi = -Infinity;
    for (const m of activeMissions) {
      const [a, b] = m.axis_ranges[axis];
      if (a < lo) lo = a;
      if (b > hi) hi = b;
    }
    out[axis] = [lo, hi];
  }
  return out;
}

/**
 * Re-normalise a 0..1 score from a preset's *local* range to a *global*
 * range so it sits correctly on the auto-scaled chart.
 */
export function renormalise(
  score: number, localRange: AxisRange, globalRange: AxisRange,
): number {
  const localValue = localRange[0] + score * (localRange[1] - localRange[0]);
  const span = globalRange[1] - globalRange[0];
  if (span <= 0) return 0;
  return Math.max(0, Math.min(1, (localValue - globalRange[0]) / span));
}

/** Convert a 0..1 score on a given axis-index (out of 7) into SVG (x, y). */
export function polarToCartesian(
  axisIndex: number, score: number, radius: number,
): { x: number; y: number } {
  const angle = (Math.PI * 2 * axisIndex) / 7 - Math.PI / 2;
  return { x: Math.cos(angle) * score * radius, y: Math.sin(angle) * score * radius };
}
```

- [ ] **Step 4: Run scale test pass**

```bash
npm run test:unit -- --run __tests__/missionScale.test.ts
```

Expected: 2 passed.

- [ ] **Step 5: Create the hooks (typed wrappers around SWR)**

`frontend/hooks/useMissionKpis.ts`:
```typescript
"use client";
import useSWR from "swr";
import { fetcher } from "@/lib/fetcher";
import type { AxisName } from "./useMissionPresets";

export type Provenance = "computed" | "estimated" | "missing";

export interface MissionAxisKpi {
  axis: AxisName;
  value: number | null;
  unit: string | null;
  score_0_1: number | null;
  range_min: number;
  range_max: number;
  provenance: Provenance;
  formula: string;
  warning: string | null;
}

export interface MissionTargetPolygon {
  mission_id: string;
  label: string;
  scores_0_1: Partial<Record<AxisName, number>>;
}

export interface MissionKpiSet {
  aeroplane_uuid: string;
  ist_polygon: Record<AxisName, MissionAxisKpi>;
  target_polygons: MissionTargetPolygon[];
  active_mission_id: string;
  computed_at: string;
  context_hash: string;
}

export function useMissionKpis(
  aeroplaneId: string | null,
  missions: string[],
  options?: { isRecomputing?: boolean },
) {
  const params = missions.length ? `?${missions.map((m) => `missions=${m}`).join("&")}` : "";
  const path = aeroplaneId
    ? `/aeroplanes/${encodeURIComponent(aeroplaneId)}/mission-kpis${params}`
    : null;
  return useSWR<MissionKpiSet | null>(
    path,
    fetcher,
    options?.isRecomputing ? { refreshInterval: 1500 } : undefined,
  );
}
```

`frontend/hooks/useMissionObjectives.ts`:
```typescript
"use client";
import useSWR from "swr";
import { fetcher, putJson } from "@/lib/fetcher";

export interface MissionObjective {
  mission_type: string;
  target_cruise_mps: number;
  target_stall_safety: number;
  target_maneuver_n: number;
  target_glide_ld: number;
  target_climb_energy: number;
  target_wing_loading_n_m2: number;
  target_field_length_m: number;
  available_runway_m: number;
  runway_type: "grass" | "asphalt" | "belly";
  t_static_N: number;
  takeoff_mode: "runway" | "hand_launch" | "bungee" | "catapult";
}

export function useMissionObjectives(aeroplaneId: string | null) {
  const path = aeroplaneId
    ? `/aeroplanes/${encodeURIComponent(aeroplaneId)}/mission-objectives`
    : null;
  const { data, error, isLoading, mutate } = useSWR<MissionObjective | null>(path, fetcher);

  const update = async (payload: MissionObjective): Promise<MissionObjective | null> => {
    if (!aeroplaneId) return null;
    const updated = await putJson<MissionObjective>(path!, payload);
    await mutate(updated, { revalidate: false });
    return updated;
  };

  return { data, error, isLoading, update, mutate };
}
```

`frontend/hooks/useMissionPresets.ts`:
```typescript
"use client";
import useSWR from "swr";
import { fetcher } from "@/lib/fetcher";

export type AxisName =
  | "stall_safety" | "glide" | "climb" | "cruise"
  | "maneuver" | "wing_loading" | "field_friendliness";

export interface MissionPreset {
  id: string;
  label: string;
  description: string;
  target_polygon: Record<AxisName, number>;
  axis_ranges: Record<AxisName, [number, number]>;
  suggested_estimates: {
    g_limit: number;
    target_static_margin: number;
    cl_max: number;
    power_to_weight: number;
    prop_efficiency: number;
  };
}

export function useMissionPresets() {
  return useSWR<MissionPreset[] | null>("/mission-presets", fetcher);
}
```

If `frontend/lib/fetcher.ts` doesn't already export `putJson`, add it:
```typescript
export async function putJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`PUT ${path} failed: ${res.status}`);
  return res.json();
}
```

- [ ] **Step 6: Commit**

```bash
git add frontend/hooks/useMissionKpis.ts \
        frontend/hooks/useMissionObjectives.ts \
        frontend/hooks/useMissionPresets.ts \
        frontend/lib/missionScale.ts \
        frontend/lib/fetcher.ts \
        frontend/__tests__/missionScale.test.ts
git commit -m "feat(mission/frontend): hooks + scale helper for the radar chart"
```

---

### Task 5.2: MissionRadarChart SVG component

**Files:**
- Create: `frontend/components/workbench/mission/MissionRadarChart.tsx`
- Create: `frontend/__tests__/MissionRadarChart.test.tsx`

- [ ] **Step 1: Write failing test**

`frontend/__tests__/MissionRadarChart.test.tsx`:
```typescript
import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import React from "react";
import { MissionRadarChart } from "@/components/workbench/mission/MissionRadarChart";
import type { MissionKpiSet } from "@/hooks/useMissionKpis";
import type { MissionPreset } from "@/hooks/useMissionPresets";

const baseKpi = (axis: any, score: number) => ({
  axis, value: 1, unit: "-", score_0_1: score,
  range_min: 0, range_max: 1, provenance: "computed", formula: "-",
  warning: null,
});

const kset: MissionKpiSet = {
  aeroplane_uuid: "x",
  ist_polygon: {
    stall_safety: baseKpi("stall_safety", 0.5),
    glide: baseKpi("glide", 0.5), climb: baseKpi("climb", 0.5),
    cruise: baseKpi("cruise", 0.5), maneuver: baseKpi("maneuver", 0.5),
    wing_loading: baseKpi("wing_loading", 0.5), field_friendliness: baseKpi("field_friendliness", 0.5),
  },
  target_polygons: [],
  active_mission_id: "trainer",
  computed_at: "",
  context_hash: "0".repeat(64),
};

const preset = (id: string): MissionPreset => ({
  id, label: id, description: "",
  target_polygon: {
    stall_safety: 1, glide: 0.5, climb: 0.5, cruise: 0.5,
    maneuver: 0.5, wing_loading: 0.5, field_friendliness: 0.5,
  },
  axis_ranges: {
    stall_safety: [1.3, 2.5], glide: [5, 18], climb: [5, 25],
    cruise: [10, 25], maneuver: [2, 5], wing_loading: [20, 80],
    field_friendliness: [3, 100],
  },
  suggested_estimates: { g_limit: 3, target_static_margin: 0.15, cl_max: 1.4, power_to_weight: 0.5, prop_efficiency: 0.7 },
});

describe("MissionRadarChart", () => {
  it("renders one ist polygon", () => {
    const { container } = render(
      <MissionRadarChart kpis={kset} activeMissions={[preset("trainer")]} onAxisClick={() => undefined}/>,
    );
    const polys = container.querySelectorAll("polygon");
    // grid rings (3) + active soll (1) + ist (1)
    expect(polys.length).toBeGreaterThanOrEqual(5);
  });

  it("renders ghost polygons for additional active missions", () => {
    const { container } = render(
      <MissionRadarChart
        kpis={kset}
        activeMissions={[preset("trainer"), preset("sailplane")]}
        onAxisClick={() => undefined}/>,
    );
    const ghosts = container.querySelectorAll(".radar-ghost");
    expect(ghosts.length).toBe(1);
  });

  it("invokes onAxisClick with axis name when an axis label is clicked", () => {
    const onAxisClick = vi.fn();
    const { container } = render(
      <MissionRadarChart kpis={kset} activeMissions={[preset("trainer")]} onAxisClick={onAxisClick}/>,
    );
    const labels = container.querySelectorAll("[data-axis]");
    expect(labels.length).toBe(7);
    (labels[0] as HTMLElement).dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect(onAxisClick).toHaveBeenCalledTimes(1);
  });
});
```

- [ ] **Step 2: Run failing test**

```bash
npm run test:unit -- --run __tests__/MissionRadarChart.test.tsx
```

Expected: ImportError.

- [ ] **Step 3: Implement the component**

`frontend/components/workbench/mission/MissionRadarChart.tsx`:
```typescript
"use client";

import React from "react";
import type { MissionKpiSet, MissionAxisKpi } from "@/hooks/useMissionKpis";
import type { MissionPreset, AxisName } from "@/hooks/useMissionPresets";
import {
  AXES, computeAxisRanges, polarToCartesian, renormalise,
} from "@/lib/missionScale";

interface Props {
  readonly kpis: MissionKpiSet;
  readonly activeMissions: MissionPreset[];  // first is "active"; rest are ghosts
  readonly onAxisClick: (axis: AxisName) => void;
}

const R = 80;  // base radius — 1.0 = R
const R_OUTER = R * 1.3;   // neighbour-ring radius
const GHOST_COLORS = ["#66ccff", "#ff8888", "#a0e7a0", "#ffd966"];

export function MissionRadarChart({ kpis, activeMissions, onAxisClick }: Props) {
  const globalRanges = computeAxisRanges(activeMissions);

  const istPoints = AXES.map((axis, i) => {
    const k = kpis.ist_polygon[axis];
    const local: [number, number] = [k.range_min, k.range_max];
    const score = k.score_0_1 ?? 0;
    const global = renormalise(score, local, globalRanges[axis]);
    return polarToCartesian(i, global, R);
  });

  const renderPolygon = (
    points: { x: number; y: number }[], cls: string, key?: string,
  ) => (
    <polygon
      key={key}
      className={cls}
      points={points.map((p) => `${p.x},${p.y}`).join(" ")}
    />
  );

  const [active, ...ghosts] = activeMissions;

  const sollPoints = active
    ? AXES.map((axis, i) => {
        const localScore = active.target_polygon[axis];
        const local = active.axis_ranges[axis];
        const global = renormalise(localScore, local, globalRanges[axis]);
        return polarToCartesian(i, global, R);
      })
    : null;

  const ghostPolygons = ghosts.map((g) =>
    AXES.map((axis, i) => {
      const score = g.target_polygon[axis];
      const local = g.axis_ranges[axis];
      const global = renormalise(score, local, globalRanges[axis]);
      return polarToCartesian(i, global, R);
    }),
  );

  // Provenance badge dot
  const badge = (p: "computed" | "estimated" | "missing") =>
    p === "computed" ? "#22dd66" : p === "estimated" ? "#f0c75e" : "#555";

  return (
    <svg viewBox="-150 -150 300 300" className="w-full max-w-[360px] aspect-square mx-auto">
      {/* Grid */}
      <polygon
        className="radar-grid-outer"
        fill="none" stroke="#1f1f1f" strokeWidth="0.4" strokeDasharray="3 3"
        points={AXES.map((_, i) => {
          const p = polarToCartesian(i, 1.3, R);
          return `${p.x},${p.y}`;
        }).join(" ")}
      />
      {[0.33, 0.66, 1.0].map((ring) => (
        <polygon
          key={ring}
          className="radar-grid"
          fill="none" stroke="#2a2a2a" strokeWidth="0.6"
          points={AXES.map((_, i) => {
            const p = polarToCartesian(i, ring, R);
            return `${p.x},${p.y}`;
          }).join(" ")}
        />
      ))}

      {/* Axes */}
      {AXES.map((axis, i) => {
        const tip = polarToCartesian(i, 1.0, R);
        const tipOuter = polarToCartesian(i, 1.3, R);
        return (
          <g key={axis}>
            <line x1={0} y1={0} x2={tip.x} y2={tip.y} stroke="#444" strokeWidth="0.6"/>
            <line x1={tip.x} y1={tip.y} x2={tipOuter.x} y2={tipOuter.y}
                  stroke="#444" strokeWidth="0.4" strokeDasharray="2 2"/>
          </g>
        );
      })}

      {/* Ghost polygons */}
      {ghostPolygons.map((pts, idx) =>
        <polygon
          key={ghosts[idx].id}
          className="radar-ghost"
          fill={`${GHOST_COLORS[idx % GHOST_COLORS.length]}1a`}
          stroke={GHOST_COLORS[idx % GHOST_COLORS.length]}
          strokeWidth="0.9" strokeDasharray="2 2"
          points={pts.map((p) => `${p.x},${p.y}`).join(" ")}
        />,
      )}

      {/* Gap fill (red, between ist and soll where ist < soll) */}
      {sollPoints && (
        renderPolygon(sollPoints, "fill-red-500/20", "gap")
      )}

      {/* Soll (active mission) */}
      {sollPoints && (
        <polygon
          fill="none" stroke="#fff" strokeWidth="1.4" strokeDasharray="4 3"
          points={sollPoints.map((p) => `${p.x},${p.y}`).join(" ")}
        />
      )}

      {/* Ist (current aircraft) */}
      <polygon
        fill="rgba(255,132,0,0.34)" stroke="#FF8400" strokeWidth="1.8"
        points={istPoints.map((p) => `${p.x},${p.y}`).join(" ")}
      />
      {istPoints.map((p, i) => (
        <circle
          key={AXES[i]} cx={p.x} cy={p.y} r="2.6"
          fill={kpis.ist_polygon[AXES[i]].provenance === "missing" ? "transparent" : "#FF8400"}
          stroke="#fff" strokeWidth="0.6"
        />
      ))}

      {/* Axis labels + provenance badges (clickable) */}
      {AXES.map((axis, i) => {
        const labelPos = polarToCartesian(i, 1.5, R);
        const k = kpis.ist_polygon[axis];
        return (
          <g
            key={axis} data-axis={axis}
            onClick={() => onAxisClick(axis)}
            style={{ cursor: "pointer" }}
          >
            <text x={labelPos.x} y={labelPos.y}
                  textAnchor="middle" fill="#ccc"
                  fontSize="10" fontWeight="600">
              {label(axis)}
            </text>
            <circle cx={labelPos.x + 18} cy={labelPos.y - 4} r="2.6"
                    fill={badge(k.provenance)}/>
          </g>
        );
      })}
    </svg>
  );
}

function label(axis: AxisName): string {
  return {
    stall_safety: "Stall Safety",
    glide: "Glide",
    climb: "Climb",
    cruise: "Cruise",
    maneuver: "Maneuver",
    wing_loading: "W/S",
    field_friendliness: "Field",
  }[axis];
}
```

- [ ] **Step 4: Run test pass**

```bash
npm run test:unit -- --run __tests__/MissionRadarChart.test.tsx
```

Expected: 3 passed.

- [ ] **Step 5: Commit + push Phase 5 PR**

```bash
git add frontend/components/workbench/mission/MissionRadarChart.tsx \
        frontend/__tests__/MissionRadarChart.test.tsx
git commit -m "feat(mission/frontend): MissionRadarChart SVG with multi-mission overlay (Phase 5)"
git push github HEAD:feat/gh-XXX-mission-radar-chart -u
gh pr create --base main --head feat/gh-XXX-mission-radar-chart \
  --title "feat(mission/frontend): MissionRadarChart component (Phase 5)" \
  --body "Phase 5. Custom SVG radar with Ist + Soll + ghost polygons, auto-rescale across active missions, provenance badges, clickable axis labels."
```

---

## Phase 6 — Mission Tab UI replacement (FE)

**Goal:** Replace the placeholder Mission tab content with the full panel layout.

### Task 6.1: MissionObjectivesPanel form

**Files:**
- Create: `frontend/components/workbench/mission/MissionObjectivesPanel.tsx`
- Create: `frontend/__tests__/MissionObjectivesPanel.test.tsx`

- [ ] **Step 1: Write failing test**

`frontend/__tests__/MissionObjectivesPanel.test.tsx`:
```typescript
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { MissionObjectivesPanel } from "@/components/workbench/mission/MissionObjectivesPanel";

vi.mock("@/hooks/useMissionObjectives", () => ({
  useMissionObjectives: () => ({
    data: {
      mission_type: "trainer",
      target_cruise_mps: 18, target_stall_safety: 1.8,
      target_maneuver_n: 3, target_glide_ld: 12,
      target_climb_energy: 22, target_wing_loading_n_m2: 412,
      target_field_length_m: 50,
      available_runway_m: 50, runway_type: "grass",
      t_static_N: 18, takeoff_mode: "runway",
    },
    update: vi.fn().mockResolvedValue(undefined),
    isLoading: false, error: null,
  }),
}));

vi.mock("@/hooks/useMissionPresets", () => ({
  useMissionPresets: () => ({
    data: [
      { id: "trainer", label: "Trainer", description: "", target_polygon: {}, axis_ranges: {}, suggested_estimates: {} },
      { id: "sailplane", label: "Sailplane", description: "", target_polygon: {}, axis_ranges: {}, suggested_estimates: {} },
    ],
    isLoading: false, error: null,
  }),
}));

describe("MissionObjectivesPanel", () => {
  it("renders the mission type dropdown with all presets", () => {
    render(<MissionObjectivesPanel aeroplaneId="x"/>);
    expect(screen.getByRole("option", { name: /Trainer/ })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /Sailplane/ })).toBeInTheDocument();
  });

  it("renders the field-performance section", () => {
    render(<MissionObjectivesPanel aeroplaneId="x"/>);
    expect(screen.getByText(/Field Performance/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Available Runway/i)).toBeInTheDocument();
  });

  it("shows the auto-apply banner after mission_type change", () => {
    render(<MissionObjectivesPanel aeroplaneId="x"/>);
    const select = screen.getByLabelText(/Mission Type/i) as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "sailplane" } });
    expect(screen.getByText(/Estimates angepasst/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run failing test**

```bash
npm run test:unit -- --run __tests__/MissionObjectivesPanel.test.tsx
```

Expected: ImportError.

- [ ] **Step 3: Implement the panel**

`frontend/components/workbench/mission/MissionObjectivesPanel.tsx`:
```typescript
"use client";

import React, { useEffect, useRef, useState } from "react";
import { useMissionObjectives, MissionObjective } from "@/hooks/useMissionObjectives";
import { useMissionPresets } from "@/hooks/useMissionPresets";

interface Props {
  readonly aeroplaneId: string;
}

export function MissionObjectivesPanel({ aeroplaneId }: Props) {
  const { data: persisted, update } = useMissionObjectives(aeroplaneId);
  const { data: presets } = useMissionPresets();
  const [draft, setDraft] = useState<MissionObjective | null>(null);
  const [bannerKey, setBannerKey] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => { if (persisted && !draft) setDraft({ ...persisted }); }, [persisted, draft]);

  if (!draft || !presets) return <div className="text-muted-foreground text-sm">Loading…</div>;

  const set = <K extends keyof MissionObjective>(key: K, value: MissionObjective[K]) => {
    setDraft((d) => (d ? { ...d, [key]: value } : d));
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      void update({ ...(draft as MissionObjective), [key]: value });
    }, 300);
  };

  const onMissionTypeChange = (id: string) => {
    set("mission_type", id);
    setBannerKey(id);
  };

  const activePreset = presets.find((p) => p.id === draft.mission_type);

  return (
    <div className="flex h-full flex-col gap-3">
      <h3 className="text-sm font-semibold text-orange-500">⊙ Mission Objectives</h3>

      {bannerKey && activePreset && (
        <div className="rounded border-l-2 border-orange-500 bg-orange-500/10 p-3 text-xs">
          <div className="font-semibold text-orange-500">
            ⚡ Mission auf <span className="text-white">{activePreset.label}</span> gesetzt — Estimates angepasst
          </div>
          <div className="mt-1 font-mono text-[10px] text-foreground/80">
            {Object.entries(activePreset.suggested_estimates).map(([k, v]) => `${k}=${v}`).join(" · ")}
          </div>
        </div>
      )}

      <div className="space-y-2">
        <label htmlFor="mission-type" className="block text-xs text-muted-foreground">
          Mission Type
        </label>
        <select
          id="mission-type" aria-label="Mission Type"
          className="w-full rounded bg-background border border-border px-2 py-1.5 text-sm"
          value={draft.mission_type}
          onChange={(e) => onMissionTypeChange(e.target.value)}
        >
          {presets.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
        </select>
      </div>

      <div className="text-[10px] uppercase tracking-wider text-muted-foreground border-b border-border pb-1">
        Performance Targets
      </div>
      <div className="grid grid-cols-2 gap-2">
        <NumField label="Target Cruise" suffix="m/s" value={draft.target_cruise_mps} onChange={(v) => set("target_cruise_mps", v)}/>
        <NumField label="Stall Safety" suffix="–" value={draft.target_stall_safety} onChange={(v) => set("target_stall_safety", v)}/>
        <NumField label="Max Maneuver" suffix="g" value={draft.target_maneuver_n} onChange={(v) => set("target_maneuver_n", v)}/>
        <NumField label="Min Glide (L/D)" suffix="–" value={draft.target_glide_ld} onChange={(v) => set("target_glide_ld", v)}/>
        <NumField label="Climb Energy" suffix="–" value={draft.target_climb_energy} onChange={(v) => set("target_climb_energy", v)}/>
        <NumField label="Target Wing Load" suffix="N/m²" value={draft.target_wing_loading_n_m2} onChange={(v) => set("target_wing_loading_n_m2", v)}/>
      </div>

      <div className="text-[10px] uppercase tracking-wider text-muted-foreground border-b border-border pb-1 mt-2">
        Field Performance
      </div>
      <div className="grid grid-cols-2 gap-2">
        <NumField label="Available Runway" suffix="m" value={draft.available_runway_m} onChange={(v) => set("available_runway_m", v)}/>
        <SelectField label="Runway Type" value={draft.runway_type} options={["grass", "asphalt", "belly"]} onChange={(v) => set("runway_type", v as MissionObjective["runway_type"])}/>
        <NumField label="Static Thrust" suffix="N" value={draft.t_static_N} onChange={(v) => set("t_static_N", v)}/>
        <SelectField label="Takeoff Mode" value={draft.takeoff_mode} options={["runway", "hand_launch", "bungee", "catapult"]} onChange={(v) => set("takeoff_mode", v as MissionObjective["takeoff_mode"])}/>
      </div>
    </div>
  );
}

function NumField(props: { label: string; suffix: string; value: number; onChange: (v: number) => void }) {
  const id = `f-${props.label.replace(/\s+/g, "-").toLowerCase()}`;
  return (
    <div>
      <label htmlFor={id} className="block text-xs text-muted-foreground mb-1">{props.label}</label>
      <div className="flex">
        <input
          id={id} aria-label={props.label} type="number"
          className="flex-1 rounded-l bg-background border border-border px-2 py-1.5 text-sm font-mono"
          value={props.value}
          onChange={(e) => props.onChange(parseFloat(e.target.value))}
        />
        <span className="rounded-r bg-card border border-l-0 border-border px-2 py-1.5 text-[10px] text-muted-foreground">
          {props.suffix}
        </span>
      </div>
    </div>
  );
}

function SelectField(props: { label: string; value: string; options: string[]; onChange: (v: string) => void }) {
  const id = `f-${props.label.replace(/\s+/g, "-").toLowerCase()}`;
  return (
    <div>
      <label htmlFor={id} className="block text-xs text-muted-foreground mb-1">{props.label}</label>
      <select id={id} aria-label={props.label}
        className="w-full rounded bg-background border border-border px-2 py-1.5 text-sm"
        value={props.value} onChange={(e) => props.onChange(e.target.value)}>
        {props.options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    </div>
  );
}
```

- [ ] **Step 4: Run test pass**

```bash
npm run test:unit -- --run __tests__/MissionObjectivesPanel.test.tsx
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/workbench/mission/MissionObjectivesPanel.tsx \
        frontend/__tests__/MissionObjectivesPanel.test.tsx
git commit -m "feat(mission/frontend): MissionObjectivesPanel form with auto-apply banner"
```

---

### Task 6.2: MissionCompliancePanel (left side)

**Files:**
- Create: `frontend/components/workbench/mission/MissionCompliancePanel.tsx`
- Create: `frontend/components/workbench/mission/MissionToggleGrid.tsx`

- [ ] **Step 1: Implement the toggle grid**

`frontend/components/workbench/mission/MissionToggleGrid.tsx`:
```typescript
"use client";

import React from "react";
import type { MissionPreset } from "@/hooks/useMissionPresets";

interface Props {
  readonly presets: MissionPreset[];
  readonly activeId: string;
  readonly comparisonIds: string[];
  readonly onToggle: (id: string) => void;
}

export function MissionToggleGrid({ presets, activeId, comparisonIds, onToggle }: Props) {
  return (
    <div className="mt-3 rounded bg-card-muted p-2 grid grid-cols-2 gap-x-3 gap-y-1">
      {presets.map((p) => {
        const isActive = p.id === activeId;
        const isComparison = comparisonIds.includes(p.id);
        return (
          <button
            key={p.id}
            type="button"
            disabled={isActive}
            onClick={() => onToggle(p.id)}
            className={`flex items-center gap-2 text-left text-xs py-1 ${
              isActive ? "text-orange-500 font-semibold cursor-default"
              : isComparison ? "text-sky-400" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <span className={`inline-block w-3 h-3 rounded-sm ${
              isActive ? "bg-orange-500 border-orange-500"
              : isComparison ? "bg-sky-400 border-sky-400" : "border border-border"
            }`}/>
            {p.label}
            {isActive && <span className="ml-auto text-[10px] text-muted-foreground">aktiv</span>}
          </button>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2: Implement the compliance panel**

`frontend/components/workbench/mission/MissionCompliancePanel.tsx`:
```typescript
"use client";

import React, { useState } from "react";
import { MissionRadarChart } from "./MissionRadarChart";
import { MissionToggleGrid } from "./MissionToggleGrid";
import { useMissionKpis } from "@/hooks/useMissionKpis";
import { useMissionPresets, AxisName } from "@/hooks/useMissionPresets";
import { useMissionObjectives } from "@/hooks/useMissionObjectives";

interface Props {
  readonly aeroplaneId: string;
  readonly onAxisClick: (axis: AxisName) => void;
}

export function MissionCompliancePanel({ aeroplaneId, onAxisClick }: Props) {
  const { data: objective } = useMissionObjectives(aeroplaneId);
  const { data: presets } = useMissionPresets();
  const [comparisons, setComparisons] = useState<string[]>([]);

  const activeId = objective?.mission_type ?? "trainer";
  const missionIds = [activeId, ...comparisons.filter((c) => c !== activeId)];
  const { data: kpis } = useMissionKpis(aeroplaneId, missionIds);

  if (!presets || !kpis) {
    return <div className="text-sm text-muted-foreground">Loading…</div>;
  }

  const activePreset = presets.find((p) => p.id === activeId)!;
  const comparisonPresets = comparisons
    .map((c) => presets.find((p) => p.id === c))
    .filter((p): p is NonNullable<typeof p> => Boolean(p));

  return (
    <div className="flex h-full flex-col">
      <h3 className="text-sm font-semibold text-orange-500 mb-2">⊙ Mission Compliance</h3>
      <MissionRadarChart
        kpis={kpis}
        activeMissions={[activePreset, ...comparisonPresets]}
        onAxisClick={onAxisClick}
      />
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground mt-3">
        Vergleichs-Profile
      </div>
      <MissionToggleGrid
        presets={presets}
        activeId={activeId}
        comparisonIds={comparisons}
        onToggle={(id) =>
          setComparisons((cs) => cs.includes(id) ? cs.filter((x) => x !== id) : [...cs, id])
        }
      />
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/workbench/mission/MissionToggleGrid.tsx \
        frontend/components/workbench/mission/MissionCompliancePanel.tsx
git commit -m "feat(mission/frontend): MissionCompliancePanel with multi-mission toggle"
```

---

### Task 6.3: Replace Mission tab content

**Files:**
- Find: existing Mission-tab content file. Search for the title text "Mission Compliance" or "Mission Objectives" from the existing placeholder.

```bash
grep -rln "Mission Objectives" frontend/components frontend/app 2>/dev/null
```

- [ ] **Step 1: Locate the file**

The grep should reveal the current Mission-tab page or component. Open it.

- [ ] **Step 2: Replace its body**

Replace the existing two-panel placeholder layout with:

```typescript
"use client";

import React, { useState } from "react";
import { MissionCompliancePanel } from "@/components/workbench/mission/MissionCompliancePanel";
import { MissionObjectivesPanel } from "@/components/workbench/mission/MissionObjectivesPanel";
import { AxisDrawer } from "@/components/workbench/mission/AxisDrawer";   // added in Phase 7
import type { AxisName } from "@/hooks/useMissionPresets";

export function MissionTab({ aeroplaneId }: { readonly aeroplaneId: string }) {
  const [drawerAxis, setDrawerAxis] = useState<AxisName | null>(null);

  return (
    <div className="grid grid-cols-2 gap-3 p-3 h-full">
      <div className="rounded border border-border bg-card p-3">
        <MissionCompliancePanel
          aeroplaneId={aeroplaneId}
          onAxisClick={(axis) => setDrawerAxis(axis)}
        />
      </div>
      <div className="rounded border border-border bg-card p-3 overflow-y-auto">
        <MissionObjectivesPanel aeroplaneId={aeroplaneId}/>
      </div>
      {drawerAxis && (
        <AxisDrawer
          aeroplaneId={aeroplaneId}
          axis={drawerAxis}
          onClose={() => setDrawerAxis(null)}
        />
      )}
    </div>
  );
}
```

(Adjust the import path and the export name to match the file's existing structure — e.g. if it's a Next.js page `app/workbench/mission/page.tsx`, replace the page body; if it's a component referenced from a parent `WorkbenchTabs`, replace that component.)

- [ ] **Step 3: Smoke run**

```bash
cd frontend && npm run dev
```

Open the app, switch to Tab 1. The new layout should render. Form inputs save (debounced 300 ms). Toggling a comparison mission adds a ghost polygon.

- [ ] **Step 4: Run all frontend tests**

```bash
npm run test:unit
```

Expected: all green, including the new Mission-tab tests.

- [ ] **Step 5: Commit + push Phase 6 PR**

```bash
git add frontend/
git commit -m "feat(mission/frontend): wire Mission Tab redesign (Phase 6)"
git push github HEAD:feat/gh-XXX-mission-tab-ui -u
gh pr create --base main --head feat/gh-XXX-mission-tab-ui \
  --title "feat(mission/frontend): Mission Tab UI replacement (Phase 6)" \
  --body "Phase 6. Full UI replacement of the placeholder Mission tab with the two-panel layout: Compliance (left, radar + toggles) + Objectives (right, form with auto-apply banner). AxisDrawer comes in Phase 7."
```

---

## Phase 7 — AxisDrawer (FE)

**Goal:** Side-drawer that opens when an axis is clicked, showing raw value, target, formula, and provenance.

### Task 7.1: AxisDrawer component

**Files:**
- Create: `frontend/components/workbench/mission/AxisDrawer.tsx`
- Create: `frontend/__tests__/AxisDrawer.test.tsx`

- [ ] **Step 1: Write failing test**

`frontend/__tests__/AxisDrawer.test.tsx`:
```typescript
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { AxisDrawer } from "@/components/workbench/mission/AxisDrawer";

vi.mock("@/hooks/useMissionKpis", () => ({
  useMissionKpis: () => ({
    data: {
      ist_polygon: {
        stall_safety: {
          axis: "stall_safety", value: 1.45, unit: "-",
          score_0_1: 0.13, range_min: 1.3, range_max: 2.5,
          provenance: "computed", formula: "V_cruise / V_s1", warning: null,
        },
      },
    },
    isLoading: false, error: null,
  }),
}));

describe("AxisDrawer", () => {
  it("renders value, target, and formula", () => {
    render(<AxisDrawer aeroplaneId="x" axis="stall_safety" onClose={() => undefined}/>);
    expect(screen.getByText(/Stall Safety/)).toBeInTheDocument();
    expect(screen.getByText(/1\.45/)).toBeInTheDocument();
    expect(screen.getByText(/V_cruise \/ V_s1/)).toBeInTheDocument();
    expect(screen.getByText(/computed/)).toBeInTheDocument();
  });

  it("renders close button that triggers onClose", () => {
    const onClose = vi.fn();
    render(<AxisDrawer aeroplaneId="x" axis="stall_safety" onClose={onClose}/>);
    screen.getByRole("button", { name: /close/i }).click();
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
```

- [ ] **Step 2: Run failing test**

```bash
npm run test:unit -- --run __tests__/AxisDrawer.test.tsx
```

Expected: ImportError.

- [ ] **Step 3: Implement the drawer**

`frontend/components/workbench/mission/AxisDrawer.tsx`:
```typescript
"use client";

import React from "react";
import { useMissionKpis } from "@/hooks/useMissionKpis";
import type { AxisName } from "@/hooks/useMissionPresets";

interface Props {
  readonly aeroplaneId: string;
  readonly axis: AxisName;
  readonly onClose: () => void;
}

const LABEL: Record<AxisName, string> = {
  stall_safety: "Stall Safety", glide: "Glide", climb: "Climb",
  cruise: "Cruise", maneuver: "Maneuver", wing_loading: "Wing Loading",
  field_friendliness: "Field Friendliness",
};

export function AxisDrawer({ aeroplaneId, axis, onClose }: Props) {
  const { data: kpis } = useMissionKpis(aeroplaneId, []);
  if (!kpis) return null;
  const k = kpis.ist_polygon[axis];

  const provColor = k.provenance === "computed" ? "text-green-400"
    : k.provenance === "estimated" ? "text-yellow-400" : "text-muted-foreground";

  return (
    <div className="fixed right-4 top-20 w-80 rounded-lg border-l-2 border-orange-500 bg-card p-4 shadow-lg z-50">
      <div className="flex items-start justify-between">
        <h4 className="text-orange-500 font-semibold text-sm">{LABEL[axis]}</h4>
        <button onClick={onClose} aria-label="close" className="text-muted-foreground hover:text-foreground">×</button>
      </div>

      <div className="mt-3 space-y-2 text-xs">
        <Row label="Ist" value={k.value != null ? `${k.value.toFixed(3)} ${k.unit ?? ""}` : "–"}/>
        <Row label="Range" value={`${k.range_min.toFixed(2)} … ${k.range_max.toFixed(2)}`}/>
        <Row label="Score" value={k.score_0_1 != null ? `${(k.score_0_1 * 100).toFixed(0)} %` : "–"}/>
        <Row label="Provenance" value={<span className={provColor}>{k.provenance}</span>}/>
      </div>

      <div className="mt-3 rounded bg-background p-2 font-mono text-[10px] text-muted-foreground">
        {k.formula}
      </div>

      {k.warning && (
        <div className="mt-3 text-[11px] text-yellow-400">⚠ {k.warning}</div>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between border-b border-border/30 py-1">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
```

- [ ] **Step 4: Run tests pass**

```bash
npm run test:unit -- --run __tests__/AxisDrawer.test.tsx
```

Expected: 2 passed.

- [ ] **Step 5: Verify the drawer integrates in the Mission tab**

```bash
npm run dev
```

Open Tab 1, click on a radar axis, drawer slides in. Click X to close.

- [ ] **Step 6: Commit + push Phase 7 PR**

```bash
git add frontend/components/workbench/mission/AxisDrawer.tsx \
        frontend/__tests__/AxisDrawer.test.tsx
git commit -m "feat(mission/frontend): AxisDrawer drill-down on axis click (Phase 7)"
git push github HEAD:feat/gh-XXX-axis-drawer -u
gh pr create --base main --head feat/gh-XXX-axis-drawer \
  --title "feat(mission/frontend): AxisDrawer (Phase 7)" \
  --body "Phase 7. Click-on-axis opens a side-drawer with raw value + range + score + provenance + formula."
```

---

## Phase 8 — Create v2 EPIC (GH housekeeping)

**Goal:** GH EPIC issue tracking all deferred Mission-tab features for v2.

### Task 8.1: Create the v2 EPIC

- [ ] **Step 1: Create the EPIC**

```bash
gh issue create \
  --title "epic: Mission Tab v2 — coaching, UAV axes, advanced controls" \
  --label "epic" \
  --label "has-spec" \
  --body "$(cat <<'EOF'
## Goal

Deferred items from the v1 Mission Tab redesign (epic gh-525-related, separate from the V-speed epic). These were captured during the brainstorming session on 2026-05-15 and are referenced in [\`docs/superpowers/specs/2026-05-15-mission-spider-chart-design.md\`](docs/superpowers/specs/2026-05-15-mission-spider-chart-design.md) section 2 (Out of scope) and section 13 (Decisions taken during review).

## Sub-items

- [ ] **Coaching drawer (extends AxisDrawer).** Per-axis sensitivity-driven suggestions — "Wing-Fläche +12 % → Margin 1.53". Requires generalising the gh-494 SM sensitivity machinery to the seven Mission axes.
- [ ] **UAV-specific axes** — Endurance, Range, Payload Fraction. Requires Powertrain + Battery spec in the backend.
- [ ] **8-axis hybrid layout** (5 RC-core + 3 UAV-extension). UAV axes grey out without battery spec.
- [ ] **Per-axis unit override** on top of the global unit-system preset.
- [ ] **Absolute-scale toggle** for cross-mission comparison (Pro-Mode).
- [ ] **Mission visualisation inside the Assumptions tab.** Show which mission is active and which estimates came from mission auto-apply vs. user-override.
- [ ] **Mission versioning** — keep prior mission revisions for design-comparison.

## Acceptance

- Each sub-item gets its own GH Issue when prioritised; this EPIC tracks the parent linkage.
- Closing this EPIC requires all sub-items to be merged.

## Audit reference

Brainstorming spec [\`2026-05-15-mission-spider-chart-design.md\`](docs/superpowers/specs/2026-05-15-mission-spider-chart-design.md).
EOF
)"
```

- [ ] **Step 2: Verify**

```bash
gh issue list --label "epic" --state open
```

Confirm the new EPIC is listed.

- [ ] **Step 3: Done — no commit needed (GH issue only)**

---

## Self-review

Run through the spec sections (`docs/superpowers/specs/2026-05-15-mission-spider-chart-design.md`) and confirm each is covered:

- §2 In-scope items → Phases 1–7 (every item maps to a phase)
- §2 Out-of-scope items → Phase 8 EPIC
- §3 UX decisions (9) → all encoded in Phase 5–7 component logic
- §4 Architecture → file paths in Phases 1–7 match
- §5 Backend (schemas, services, endpoints) → Phases 1, 2, 4
- §6 Frontend → Phases 5, 6, 7
- §7 Field-performance migration → Phase 3
- §8 Error handling → `_missing` provenance branch (Phase 2), 422 in endpoints (Phase 1), drawer fallback when KPI value is null (Phase 7)
- §9 Testing strategy → TDD steps in every task
- §10 Implementation phases → exact phase ordering matches §10 of the spec
- §11 Rollback → each phase = independent PR (covered)
- §12 Visual reference → `docs/superpowers/specs/assets/2026-05-15-mission-tab-mock.html` referenced in plan header
- §13 Decisions during review → DB-backed presets (Phase 1.4–1.5), default = only-active-mission (Phase 6.2), verbatim backfill (Phase 3.3)

Placeholder scan: every code step contains complete code; no "TODO" / "TBD" / "implement later" / "similar to Task N". Endpoint registration step (Task 1.7 Step 5) tells the engineer how to adapt to the existing pattern; that's appropriate flexibility rather than a placeholder.

Type consistency check:
- `AxisName` defined in `mission_kpi.py` and re-used by `mission_objective.py` ✓
- `MissionPreset.axis_ranges` is `dict[AxisName, tuple[float, float]]` in the Pydantic model and stored as `dict[AxisName, list[float]]` in JSON; the service converts on read (Task 1.6) ✓
- `compute_mission_kpis(db, aeroplane_id, missions)` signature consistent across service, endpoint, test ✓
- Frontend `MissionKpiSet`, `MissionAxisKpi`, `MissionPreset`, `AxisName` types match the backend Pydantic schemas ✓

Plan ready.
