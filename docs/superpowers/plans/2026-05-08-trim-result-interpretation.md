# Trim Result Interpretation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich every trimmed operating point with analysis goals, deflection reserves, and design warnings, then display them in the frontend OP detail drawer.

**Architecture:** Add `TrimEnrichment` Pydantic model stored as a JSON column on `OperatingPointModel`. Enrichment is computed in the OP generator service after each trim solve. Frontend reads the new field and renders an analysis goal banner, control authority bars, and warning badges in the existing detail drawer.

**Tech Stack:** Python/Pydantic/SQLAlchemy/Alembic (backend), React/TypeScript/Tailwind (frontend)

---

### Task 1: Enrichment Schemas — `TrimEnrichment`, `DeflectionReserve`, `DesignWarning`

**Files:**
- Modify: `app/schemas/aeroanalysisschema.py`
- Test: `app/tests/test_trim_enrichment.py`

- [ ] **Step 1: Write failing tests for the new Pydantic models**

```python
# app/tests/test_trim_enrichment.py
import pytest
from pydantic import ValidationError

from app.schemas.aeroanalysisschema import (
    DeflectionReserve,
    DesignWarning,
    TrimEnrichment,
)


class TestDeflectionReserve:
    def test_basic_reserve(self):
        r = DeflectionReserve(
            deflection_deg=-5.0,
            max_pos_deg=25.0,
            max_neg_deg=25.0,
            usage_fraction=0.2,
        )
        assert r.deflection_deg == -5.0
        assert r.usage_fraction == 0.2

    def test_zero_deflection(self):
        r = DeflectionReserve(
            deflection_deg=0.0,
            max_pos_deg=25.0,
            max_neg_deg=25.0,
            usage_fraction=0.0,
        )
        assert r.usage_fraction == 0.0


class TestDesignWarning:
    def test_authority_warning(self):
        w = DesignWarning(
            level="warning",
            category="authority",
            surface="[elevator]Elevator",
            message="80%+ authority used",
        )
        assert w.level == "warning"
        assert w.surface == "[elevator]Elevator"

    def test_trim_quality_warning_no_surface(self):
        w = DesignWarning(
            level="critical",
            category="trim_quality",
            surface=None,
            message="Trim failed to converge",
        )
        assert w.surface is None

    def test_invalid_level_rejected(self):
        with pytest.raises(ValidationError):
            DesignWarning(
                level="panic",
                category="authority",
                surface=None,
                message="test",
            )


class TestTrimEnrichment:
    def test_full_enrichment(self):
        e = TrimEnrichment(
            analysis_goal="Can the aircraft trim near stall?",
            trim_method="opti",
            trim_score=0.02,
            trim_residuals={"cm": 0.001, "cy": 0.0},
            deflection_reserves={
                "[elevator]Elevator": DeflectionReserve(
                    deflection_deg=-5.0,
                    max_pos_deg=25.0,
                    max_neg_deg=25.0,
                    usage_fraction=0.2,
                ),
            },
            design_warnings=[],
        )
        assert e.trim_method == "opti"
        assert "[elevator]Elevator" in e.deflection_reserves

    def test_minimal_enrichment(self):
        e = TrimEnrichment(
            analysis_goal="User-defined trim point",
            trim_method="opti",
            trim_score=None,
            trim_residuals={},
            deflection_reserves={},
            design_warnings=[],
        )
        assert e.trim_score is None

    def test_serialization_roundtrip(self):
        e = TrimEnrichment(
            analysis_goal="Test goal",
            trim_method="grid_search",
            trim_score=0.5,
            trim_residuals={"cm": 0.1},
            deflection_reserves={},
            design_warnings=[
                DesignWarning(
                    level="warning",
                    category="authority",
                    surface="elev",
                    message="test",
                ),
            ],
        )
        data = e.model_dump()
        e2 = TrimEnrichment.model_validate(data)
        assert e2 == e
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-440-trim-interpretation && poetry run pytest app/tests/test_trim_enrichment.py -v`
Expected: ImportError — `DeflectionReserve`, `DesignWarning`, `TrimEnrichment` do not exist yet.

- [ ] **Step 3: Implement the Pydantic models**

Add to the end of `app/schemas/aeroanalysisschema.py` (before the last class `AnalysisStatusResponse`):

```python
class DeflectionReserve(BaseModel):
    """Per-surface deflection usage at a trim point."""

    deflection_deg: float = Field(..., description="Actual deflection at trim (degrees)")
    max_pos_deg: float = Field(..., description="Mechanical limit in positive direction (degrees)")
    max_neg_deg: float = Field(..., description="Mechanical limit in negative direction (degrees)")
    usage_fraction: float = Field(
        ..., description="Fraction of available authority used (|defl| / limit), 0.0–1.0+"
    )


class DesignWarning(BaseModel):
    """A threshold-based design warning generated from trim results."""

    level: str = Field(
        ..., description="Severity: 'info', 'warning', or 'critical'", pattern="^(info|warning|critical)$"
    )
    category: str = Field(..., description="Warning category: 'authority', 'trim_quality', etc.")
    surface: Optional[str] = Field(None, description="Control surface name, if applicable")
    message: str = Field(..., description="Human-readable warning message")


class TrimEnrichment(BaseModel):
    """Enrichment data computed after a trim solve — stored as JSON on OperatingPointModel."""

    analysis_goal: str = Field(..., description="Human-readable design question this OP answers")
    trim_method: str = Field(..., description="Solver used: 'opti', 'grid_search', 'avl', 'aerobuildup'")
    trim_score: Optional[float] = Field(None, description="Trim quality score (lower = better)")
    trim_residuals: dict[str, float] = Field(
        default_factory=dict, description="Residual coefficients at trim (cm, cy, cl)"
    )
    deflection_reserves: dict[str, DeflectionReserve] = Field(
        default_factory=dict, description="Per-surface deflection reserve"
    )
    design_warnings: list[DesignWarning] = Field(
        default_factory=list, description="Threshold-based design warnings"
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-440-trim-interpretation && poetry run pytest app/tests/test_trim_enrichment.py -v`
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-440-trim-interpretation
git add app/schemas/aeroanalysisschema.py app/tests/test_trim_enrichment.py
git commit -m "feat(gh-440): add TrimEnrichment, DeflectionReserve, DesignWarning schemas"
```

---

### Task 2: DB Migration — `trim_enrichment` Column on `OperatingPointModel`

**Files:**
- Modify: `app/models/analysismodels.py`
- Create: `alembic/versions/<hash>_add_trim_enrichment_to_op.py`
- Test: `app/tests/test_trim_enrichment.py` (extend)

- [ ] **Step 1: Write failing test that the column exists**

Append to `app/tests/test_trim_enrichment.py`:

```python
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.aeroplanemodel import AeroplaneModel
from app.models.analysismodels import OperatingPointModel


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


class TestTrimEnrichmentPersistence:
    def test_op_model_stores_trim_enrichment(self, db_session):
        aircraft = AeroplaneModel(name="test-plane", uuid=uuid.uuid4())
        db_session.add(aircraft)
        db_session.commit()

        enrichment_data = {
            "analysis_goal": "Can trim near stall?",
            "trim_method": "opti",
            "trim_score": 0.02,
            "trim_residuals": {"cm": 0.001},
            "deflection_reserves": {},
            "design_warnings": [],
        }

        op = OperatingPointModel(
            name="test_op",
            description="test",
            aircraft_id=aircraft.id,
            config="clean",
            status="TRIMMED",
            warnings=[],
            controls={},
            velocity=15.0,
            alpha=0.05,
            beta=0.0,
            p=0.0, q=0.0, r=0.0,
            xyz_ref=[0, 0, 0],
            altitude=0.0,
            trim_enrichment=enrichment_data,
        )
        db_session.add(op)
        db_session.commit()
        db_session.refresh(op)

        assert op.trim_enrichment is not None
        assert op.trim_enrichment["analysis_goal"] == "Can trim near stall?"

    def test_op_model_trim_enrichment_null_by_default(self, db_session):
        aircraft = AeroplaneModel(name="test-plane-2", uuid=uuid.uuid4())
        db_session.add(aircraft)
        db_session.commit()

        op = OperatingPointModel(
            name="test_op_null",
            description="test",
            aircraft_id=aircraft.id,
            config="clean",
            status="NOT_TRIMMED",
            warnings=[],
            controls={},
            velocity=15.0,
            alpha=0.0,
            beta=0.0,
            p=0.0, q=0.0, r=0.0,
            xyz_ref=[0, 0, 0],
            altitude=0.0,
        )
        db_session.add(op)
        db_session.commit()
        db_session.refresh(op)

        assert op.trim_enrichment is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-440-trim-interpretation && poetry run pytest app/tests/test_trim_enrichment.py::TestTrimEnrichmentPersistence -v`
Expected: FAIL — `OperatingPointModel` has no `trim_enrichment` column.

- [ ] **Step 3: Add column to model**

In `app/models/analysismodels.py`, add to `OperatingPointModel` after the `control_deflections` column:

```python
    trim_enrichment = Column(JSON, nullable=True)
```

- [ ] **Step 4: Generate and review Alembic migration**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-440-trim-interpretation
poetry run alembic revision --autogenerate -m "add trim_enrichment to operating_points"
```

Review the generated migration — it should add one nullable JSON column. No data backfill needed (existing rows get NULL).

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-440-trim-interpretation && poetry run pytest app/tests/test_trim_enrichment.py -v`
Expected: All pass.

- [ ] **Step 6: Commit**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-440-trim-interpretation
git add app/models/analysismodels.py alembic/versions/ app/tests/test_trim_enrichment.py
git commit -m "feat(gh-440): add trim_enrichment JSON column to operating_points"
```

---

### Task 3: API Layer — Add `trim_enrichment` to Stored OP Schemas

**Files:**
- Modify: `app/schemas/aeroanalysisschema.py` — `StoredOperatingPointCreate`, `StoredOperatingPointRead`
- Test: `app/tests/test_trim_enrichment.py` (extend)

- [ ] **Step 1: Write failing test for schema field**

Append to `app/tests/test_trim_enrichment.py`:

```python
from app.schemas.aeroanalysisschema import StoredOperatingPointCreate, StoredOperatingPointRead


class TestStoredOPSchemaEnrichment:
    def test_create_schema_accepts_trim_enrichment(self):
        enrichment = {
            "analysis_goal": "Test goal",
            "trim_method": "opti",
            "trim_score": 0.05,
            "trim_residuals": {"cm": 0.001},
            "deflection_reserves": {},
            "design_warnings": [],
        }
        op = StoredOperatingPointCreate(
            name="test",
            description="test",
            velocity=15.0,
            alpha=0.05,
            beta=0.0,
            p=0.0, q=0.0, r=0.0,
            altitude=0.0,
            trim_enrichment=enrichment,
        )
        assert op.trim_enrichment is not None
        assert op.trim_enrichment["trim_method"] == "opti"

    def test_create_schema_defaults_to_none(self):
        op = StoredOperatingPointCreate(
            name="test",
            description="test",
            velocity=15.0,
            alpha=0.05,
            beta=0.0,
            p=0.0, q=0.0, r=0.0,
            altitude=0.0,
        )
        assert op.trim_enrichment is None

    def test_read_schema_includes_trim_enrichment(self):
        op = StoredOperatingPointRead(
            id=1,
            name="test",
            description="test",
            velocity=15.0,
            alpha=0.05,
            beta=0.0,
            p=0.0, q=0.0, r=0.0,
            altitude=0.0,
            trim_enrichment={"analysis_goal": "Goal", "trim_method": "opti",
                             "trim_score": None, "trim_residuals": {},
                             "deflection_reserves": {}, "design_warnings": []},
        )
        assert op.trim_enrichment["analysis_goal"] == "Goal"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-440-trim-interpretation && poetry run pytest app/tests/test_trim_enrichment.py::TestStoredOPSchemaEnrichment -v`
Expected: FAIL — `StoredOperatingPointCreate` does not accept `trim_enrichment`.

- [ ] **Step 3: Add field to schemas**

In `app/schemas/aeroanalysisschema.py`, add to `StoredOperatingPointCreate` after `control_deflections`:

```python
    trim_enrichment: Optional[dict] = Field(
        default=None,
        description="Enrichment data: analysis goal, deflection reserves, design warnings. "
        "Computed after trim solve.",
    )
```

`StoredOperatingPointRead` inherits from `StoredOperatingPointCreate`, so it gets the field automatically.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-440-trim-interpretation && poetry run pytest app/tests/test_trim_enrichment.py -v`
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-440-trim-interpretation
git add app/schemas/aeroanalysisschema.py app/tests/test_trim_enrichment.py
git commit -m "feat(gh-440): add trim_enrichment field to StoredOperatingPoint schemas"
```

---

### Task 4: Enrichment Engine — Compute Deflection Reserves, Warnings, and Analysis Goals

**Files:**
- Modify: `app/services/operating_point_generator_service.py`
- Test: `app/tests/test_trim_enrichment.py` (extend)

This is the core business logic. Three functions:
1. `_build_deflection_limits()` — extract mechanical limits from ASB airplane
2. `_compute_enrichment()` — compute enrichment from TrimmedPoint + limits
3. `_ANALYSIS_GOALS` — static lookup dict

- [ ] **Step 1: Write failing tests for enrichment computation**

Append to `app/tests/test_trim_enrichment.py`:

```python
from unittest.mock import MagicMock
from app.services.operating_point_generator_service import (
    _build_deflection_limits,
    _compute_enrichment,
    ANALYSIS_GOALS,
    TrimmedPoint,
)
from app.schemas.aeroanalysisschema import OperatingPointStatus


def _mock_airplane_with_limits(surfaces: list[dict]) -> MagicMock:
    """Create a mock ASB airplane with control surfaces that have deflection limits."""
    airplane = MagicMock()
    xsec = MagicMock()
    controls = []
    for s in surfaces:
        cs = MagicMock()
        cs.name = s["name"]
        cs.deflection = s.get("deflection", 0.0)
        controls.append(cs)
    xsec.control_surfaces = controls
    wing = MagicMock()
    wing.xsecs = [xsec]
    airplane.wings = [wing]
    return airplane


class TestAnalysisGoals:
    def test_all_auto_generated_ops_have_goals(self):
        expected_names = {
            "stall_near_clean", "takeoff_climb", "cruise", "loiter_endurance",
            "max_level_speed", "approach_landing", "turn_n2", "dutch_role_start",
            "best_angle_climb_vx", "best_rate_climb_vy", "max_range", "stall_with_flaps",
        }
        assert expected_names <= set(ANALYSIS_GOALS.keys())

    def test_unknown_name_not_in_goals(self):
        assert "custom_op_xyz" not in ANALYSIS_GOALS


class TestBuildDeflectionLimits:
    def test_extracts_limits_from_airplane(self):
        airplane = _mock_airplane_with_limits([
            {"name": "[elevator]Elevator"},
            {"name": "[aileron]Left Aileron"},
        ])
        limits = _build_deflection_limits(airplane, default_limit_deg=25.0)
        assert "[elevator]Elevator" in limits
        assert limits["[elevator]Elevator"] == (25.0, 25.0)

    def test_default_limit_applied(self):
        airplane = _mock_airplane_with_limits([{"name": "rudder"}])
        limits = _build_deflection_limits(airplane, default_limit_deg=30.0)
        assert limits["rudder"] == (30.0, 30.0)


class TestComputeEnrichment:
    def test_basic_enrichment(self):
        point = TrimmedPoint(
            name="cruise", description="", config="clean",
            velocity=18.0, altitude=0.0,
            alpha_rad=0.05, beta_rad=0.0,
            p=0.0, q=0.0, r=0.0,
            status=OperatingPointStatus.TRIMMED,
            warnings=[], controls={"[elevator]Elevator": -5.0},
        )
        limits = {"[elevator]Elevator": (25.0, 25.0)}
        enrichment = _compute_enrichment(
            point=point, limits=limits,
            trim_method="opti", trim_score=0.02,
            trim_residuals={"cm": 0.001, "cy": 0.0},
        )
        assert enrichment.analysis_goal == ANALYSIS_GOALS["cruise"]
        assert enrichment.trim_method == "opti"
        assert enrichment.trim_score == 0.02
        reserve = enrichment.deflection_reserves["[elevator]Elevator"]
        assert reserve.deflection_deg == -5.0
        assert reserve.usage_fraction == pytest.approx(0.2)

    def test_user_defined_op_gets_default_goal(self):
        point = TrimmedPoint(
            name="my_custom_point", description="", config="clean",
            velocity=20.0, altitude=100.0,
            alpha_rad=0.03, beta_rad=0.0,
            p=0.0, q=0.0, r=0.0,
            status=OperatingPointStatus.TRIMMED,
            warnings=[], controls={},
        )
        enrichment = _compute_enrichment(
            point=point, limits={},
            trim_method="opti", trim_score=0.01,
            trim_residuals={},
        )
        assert enrichment.analysis_goal == "User-defined trim point"

    def test_high_authority_generates_warning(self):
        point = TrimmedPoint(
            name="stall_near_clean", description="", config="clean",
            velocity=10.0, altitude=0.0,
            alpha_rad=0.2, beta_rad=0.0,
            p=0.0, q=0.0, r=0.0,
            status=OperatingPointStatus.TRIMMED,
            warnings=[], controls={"[elevator]Elevator": -22.0},
        )
        limits = {"[elevator]Elevator": (25.0, 25.0)}
        enrichment = _compute_enrichment(
            point=point, limits=limits,
            trim_method="opti", trim_score=0.03,
            trim_residuals={"cm": 0.002},
        )
        reserve = enrichment.deflection_reserves["[elevator]Elevator"]
        assert reserve.usage_fraction == pytest.approx(22.0 / 25.0)
        warning_levels = [w.level for w in enrichment.design_warnings]
        assert "warning" in warning_levels

    def test_critical_authority_generates_critical_warning(self):
        point = TrimmedPoint(
            name="stall_near_clean", description="", config="clean",
            velocity=10.0, altitude=0.0,
            alpha_rad=0.2, beta_rad=0.0,
            p=0.0, q=0.0, r=0.0,
            status=OperatingPointStatus.TRIMMED,
            warnings=[], controls={"[elevator]Elevator": -24.5},
        )
        limits = {"[elevator]Elevator": (25.0, 25.0)}
        enrichment = _compute_enrichment(
            point=point, limits=limits,
            trim_method="opti", trim_score=0.03,
            trim_residuals={},
        )
        warning_levels = [w.level for w in enrichment.design_warnings]
        assert "critical" in warning_levels

    def test_poor_trim_quality_generates_warning(self):
        point = TrimmedPoint(
            name="cruise", description="", config="clean",
            velocity=18.0, altitude=0.0,
            alpha_rad=0.05, beta_rad=0.0,
            p=0.0, q=0.0, r=0.0,
            status=OperatingPointStatus.NOT_TRIMMED,
            warnings=[], controls={},
        )
        enrichment = _compute_enrichment(
            point=point, limits={},
            trim_method="opti", trim_score=0.6,
            trim_residuals={"cm": 0.3},
        )
        categories = [w.category for w in enrichment.design_warnings]
        assert "trim_quality" in categories
        assert any(w.level == "critical" for w in enrichment.design_warnings)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-440-trim-interpretation && poetry run pytest app/tests/test_trim_enrichment.py::TestAnalysisGoals app/tests/test_trim_enrichment.py::TestBuildDeflectionLimits app/tests/test_trim_enrichment.py::TestComputeEnrichment -v`
Expected: ImportError — `_build_deflection_limits`, `_compute_enrichment`, `ANALYSIS_GOALS` don't exist yet.

- [ ] **Step 3: Implement the enrichment engine**

Add to `app/services/operating_point_generator_service.py`, after the existing imports and before `_default_profile()`:

```python
from app.schemas.aeroanalysisschema import (
    DeflectionReserve,
    DesignWarning,
    TrimEnrichment,
)

ANALYSIS_GOALS: dict[str, str] = {
    "stall_near_clean": "Can the aircraft trim near stall? How much elevator authority remains?",
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

_DEFAULT_ANALYSIS_GOAL = "User-defined trim point"


def _build_deflection_limits(
    asb_airplane: asb.Airplane,
    default_limit_deg: float = 25.0,
) -> dict[str, tuple[float, float]]:
    """Extract per-surface mechanical limits (max_pos_deg, max_neg_deg) from ASB airplane."""
    limits: dict[str, tuple[float, float]] = {}
    for wing in getattr(asb_airplane, "wings", []) or []:
        for xsec in getattr(wing, "xsecs", []) or []:
            for cs in getattr(xsec, "control_surfaces", []) or []:
                name = str(getattr(cs, "name", "")).strip()
                if not name:
                    continue
                limits[name] = (default_limit_deg, default_limit_deg)
    return limits


def _compute_enrichment(
    point: "TrimmedPoint",
    limits: dict[str, tuple[float, float]],
    trim_method: str,
    trim_score: float | None,
    trim_residuals: dict[str, float],
) -> TrimEnrichment:
    """Compute enrichment data from a trimmed point and its mechanical limits."""
    analysis_goal = ANALYSIS_GOALS.get(point.name, _DEFAULT_ANALYSIS_GOAL)

    deflection_reserves: dict[str, DeflectionReserve] = {}
    for surface_name, deflection_deg in point.controls.items():
        max_pos, max_neg = limits.get(surface_name, (25.0, 25.0))
        if deflection_deg >= 0:
            limit = max_pos
        else:
            limit = max_neg
        usage = abs(deflection_deg) / limit if limit > 0 else 0.0
        deflection_reserves[surface_name] = DeflectionReserve(
            deflection_deg=deflection_deg,
            max_pos_deg=max_pos,
            max_neg_deg=max_neg,
            usage_fraction=usage,
        )

    warnings: list[DesignWarning] = []
    for surface_name, reserve in deflection_reserves.items():
        if reserve.usage_fraction > 0.95:
            warnings.append(DesignWarning(
                level="critical",
                category="authority",
                surface=surface_name,
                message=f"{surface_name}: near mechanical limit ({reserve.usage_fraction:.0%} used) — redesign needed",
            ))
        elif reserve.usage_fraction > 0.80:
            warnings.append(DesignWarning(
                level="warning",
                category="authority",
                surface=surface_name,
                message=f"{surface_name}: {reserve.usage_fraction:.0%} authority used — surface may be undersized",
            ))

    if trim_score is not None:
        if trim_score > 0.5:
            warnings.append(DesignWarning(
                level="critical",
                category="trim_quality",
                surface=None,
                message="Trim failed to converge — results unreliable",
            ))
        elif trim_score > 0.1:
            warnings.append(DesignWarning(
                level="warning",
                category="trim_quality",
                surface=None,
                message="Poor trim quality — equilibrium not fully achieved",
            ))

    if point.status == OperatingPointStatus.LIMIT_REACHED:
        warnings.append(DesignWarning(
            level="critical",
            category="authority",
            surface=None,
            message="Optimizer hit a constraint boundary — check all surfaces",
        ))

    return TrimEnrichment(
        analysis_goal=analysis_goal,
        trim_method=trim_method,
        trim_score=trim_score,
        trim_residuals=trim_residuals,
        deflection_reserves=deflection_reserves,
        design_warnings=warnings,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-440-trim-interpretation && poetry run pytest app/tests/test_trim_enrichment.py -v`
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-440-trim-interpretation
git add app/services/operating_point_generator_service.py app/tests/test_trim_enrichment.py
git commit -m "feat(gh-440): implement enrichment engine — deflection reserves, warnings, goals"
```

---

### Task 5: Wire Enrichment into OP Generator and Trim Service

**Files:**
- Modify: `app/services/operating_point_generator_service.py`
- Modify: `app/tests/test_operating_point_generator_service.py`
- Modify: `app/tests/test_trim_enrichment.py`

This task connects the enrichment engine to both `generate_default_set_for_aircraft()` and `trim_operating_point_for_aircraft()`.

Changes:
1. Add `trim_enrichment: TrimEnrichment | None = None` field to `TrimmedPoint` dataclass
2. Compute enrichment in `_trim_or_estimate_point()` after the trim solve
3. Pass `_build_deflection_limits()` result into the function
4. Persist `trim_enrichment.model_dump()` in `_persist_point_set()`
5. Include `trim_enrichment` in `StoredOperatingPointCreate` payload for single-trim endpoint

- [ ] **Step 1: Write failing integration tests**

Append to `app/tests/test_trim_enrichment.py`:

```python
from types import SimpleNamespace
from unittest.mock import patch


def _fake_trim(*_, target, **__):
    return TrimmedPoint(
        name=target["name"],
        description=f"mocked {target['name']}",
        config=target["config"],
        velocity=float(target["velocity"]),
        altitude=float(target["altitude"]),
        alpha_rad=0.05,
        beta_rad=0.0,
        p=0.0, q=0.0, r=0.0,
        status=OperatingPointStatus.TRIMMED,
        warnings=[],
        controls={"[elevator]Elevator": -3.0},
    )


def _mock_airplane_with_controls(*control_names: str) -> SimpleNamespace:
    control_surfaces = [SimpleNamespace(name=name) for name in control_names]
    return SimpleNamespace(
        xyz_ref=[0, 0, 0],
        s_ref=1.0,
        wings=[SimpleNamespace(xsecs=[SimpleNamespace(control_surfaces=control_surfaces)])],
    )


class TestEnrichmentIntegration:
    def test_generated_ops_have_trim_enrichment(self, db_session):
        from app.services.operating_point_generator_service import generate_default_set_for_aircraft
        aircraft_uuid = uuid.uuid4()
        aircraft = AeroplaneModel(name="enrich-test", uuid=aircraft_uuid)
        db_session.add(aircraft)
        db_session.commit()

        with (
            patch("app.services.operating_point_generator_service.aeroplane_model_to_aeroplane_schema_async", return_value=SimpleNamespace()),
            patch("app.services.operating_point_generator_service.aeroplane_schema_to_asb_airplane_async", return_value=_mock_airplane_with_controls("[elevator]Elevator", "[rudder]Rudder")),
            patch("app.services.operating_point_generator_service._trim_or_estimate_point", side_effect=_fake_trim),
        ):
            result = generate_default_set_for_aircraft(db_session, aircraft_uuid)

        for op in result.operating_points:
            assert op.trim_enrichment is not None, f"OP {op.name} missing enrichment"
            assert "analysis_goal" in op.trim_enrichment
            assert "deflection_reserves" in op.trim_enrichment

    def test_generated_ops_enrichment_persisted_to_db(self, db_session):
        from app.services.operating_point_generator_service import generate_default_set_for_aircraft
        aircraft_uuid = uuid.uuid4()
        aircraft = AeroplaneModel(name="enrich-persist", uuid=aircraft_uuid)
        db_session.add(aircraft)
        db_session.commit()

        with (
            patch("app.services.operating_point_generator_service.aeroplane_model_to_aeroplane_schema_async", return_value=SimpleNamespace()),
            patch("app.services.operating_point_generator_service.aeroplane_schema_to_asb_airplane_async", return_value=_mock_airplane_with_controls("[elevator]Elevator", "[rudder]Rudder")),
            patch("app.services.operating_point_generator_service._trim_or_estimate_point", side_effect=_fake_trim),
        ):
            generate_default_set_for_aircraft(db_session, aircraft_uuid)

        persisted = db_session.query(OperatingPointModel).filter(
            OperatingPointModel.aircraft_id == aircraft.id
        ).all()
        for op_model in persisted:
            assert op_model.trim_enrichment is not None

    def test_single_trim_has_enrichment(self, db_session):
        from app.services.operating_point_generator_service import trim_operating_point_for_aircraft
        from app.schemas.aeroanalysisschema import TrimOperatingPointRequest

        aircraft_uuid = uuid.uuid4()
        aircraft = AeroplaneModel(name="enrich-single", uuid=aircraft_uuid)
        db_session.add(aircraft)
        db_session.commit()

        request = TrimOperatingPointRequest(
            name="custom_test",
            config="clean",
            velocity=20.0,
            altitude=100.0,
        )

        with (
            patch("app.services.operating_point_generator_service.aeroplane_model_to_aeroplane_schema_async", return_value=SimpleNamespace()),
            patch("app.services.operating_point_generator_service.aeroplane_schema_to_asb_airplane_async", return_value=_mock_airplane_with_controls("[elevator]Elevator")),
            patch("app.services.operating_point_generator_service._trim_or_estimate_point", side_effect=_fake_trim),
        ):
            result = trim_operating_point_for_aircraft(db_session, aircraft_uuid, request)

        assert result.point.trim_enrichment is not None
        assert result.point.trim_enrichment["analysis_goal"] == "User-defined trim point"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-440-trim-interpretation && poetry run pytest app/tests/test_trim_enrichment.py::TestEnrichmentIntegration -v`
Expected: FAIL — enrichment not yet wired in.

- [ ] **Step 3: Add `trim_enrichment` to `TrimmedPoint` dataclass**

In `app/services/operating_point_generator_service.py`, modify the `TrimmedPoint` dataclass to add:

```python
    trim_enrichment: Optional[dict] = None
```

(Use `dict` not `TrimEnrichment` to keep it JSON-serializable for DB storage.)

- [ ] **Step 4: Wire enrichment into `generate_default_set_for_aircraft()`**

In `generate_default_set_for_aircraft()`:
1. After `capabilities = _detect_control_capabilities(asb_airplane)`, add:
   ```python
   deflection_limits = _build_deflection_limits(asb_airplane)
   ```
2. After each `_trim_or_estimate_point()` call in the for-loop, before `points.append(point)`, add:
   ```python
   enrichment = _compute_enrichment(
       point=point,
       limits=deflection_limits,
       trim_method="opti",
       trim_score=None,
       trim_residuals={},
   )
   point.trim_enrichment = enrichment.model_dump()
   ```

In `_persist_point_set()`, add to the `OperatingPointModel(...)` constructor:
```python
    trim_enrichment=point.trim_enrichment,
```

In `StoredOperatingPointRead.model_validate(point, from_attributes=True)` — this works automatically since the model column is now present and `from_attributes=True` reads it.

- [ ] **Step 5: Wire enrichment into `trim_operating_point_for_aircraft()`**

After `point = _trim_or_estimate_point(...)`, add:
```python
deflection_limits = _build_deflection_limits(asb_airplane)
enrichment = _compute_enrichment(
    point=point,
    limits=deflection_limits,
    trim_method="opti",
    trim_score=None,
    trim_residuals={},
)
```

In the `StoredOperatingPointCreate(...)` constructor, add:
```python
    trim_enrichment=enrichment.model_dump(),
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-440-trim-interpretation && poetry run pytest app/tests/test_trim_enrichment.py -v`
Expected: All pass.

- [ ] **Step 7: Run full test suite to verify no regressions**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-440-trim-interpretation && poetry run pytest -x -q --tb=short --ignore=app/tests/test_avl_strip_forces_integration.py`
Expected: All pass (except pre-existing AVL binary test).

- [ ] **Step 8: Commit**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-440-trim-interpretation
git add app/services/operating_point_generator_service.py app/tests/test_trim_enrichment.py
git commit -m "feat(gh-440): wire enrichment into OP generator and trim service"
```

---

### Task 6: Frontend Types — Add `TrimEnrichment` TypeScript Interfaces

**Files:**
- Modify: `frontend/hooks/useOperatingPoints.ts`
- Test: `frontend/__tests__/trim-enrichment-types.test.ts`

- [ ] **Step 1: Write failing test for the new types**

```typescript
// frontend/__tests__/trim-enrichment-types.test.ts
import { describe, it, expect } from "vitest";
import type {
  TrimEnrichment,
  DeflectionReserve,
  DesignWarning,
} from "@/hooks/useOperatingPoints";

describe("TrimEnrichment types", () => {
  it("TrimEnrichment satisfies the shape", () => {
    const enrichment: TrimEnrichment = {
      analysis_goal: "Can the aircraft trim near stall?",
      trim_method: "opti",
      trim_score: 0.02,
      trim_residuals: { cm: 0.001, cy: 0.0 },
      deflection_reserves: {
        "[elevator]Elevator": {
          deflection_deg: -5.0,
          max_pos_deg: 25.0,
          max_neg_deg: 25.0,
          usage_fraction: 0.2,
        },
      },
      design_warnings: [],
    };
    expect(enrichment.analysis_goal).toBe("Can the aircraft trim near stall?");
    expect(enrichment.deflection_reserves["[elevator]Elevator"].usage_fraction).toBe(0.2);
  });

  it("StoredOperatingPoint has trim_enrichment field", () => {
    // This verifies the type exists on the StoredOperatingPoint interface.
    // If the field is missing, TypeScript will error at compile time.
    const op = {
      id: 1, name: "cruise", description: "", aircraft_id: 1,
      config: "clean", status: "TRIMMED" as const,
      warnings: [], controls: {},
      velocity: 18, alpha: 0.05, beta: 0, p: 0, q: 0, r: 0,
      xyz_ref: [0, 0, 0], altitude: 0,
      control_deflections: null,
      trim_enrichment: {
        analysis_goal: "Test",
        trim_method: "opti",
        trim_score: null,
        trim_residuals: {},
        deflection_reserves: {},
        design_warnings: [],
      },
    } satisfies import("@/hooks/useOperatingPoints").StoredOperatingPoint;
    expect(op.trim_enrichment).not.toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-440-trim-interpretation/frontend && npx vitest run __tests__/trim-enrichment-types.test.ts`
Expected: FAIL — `TrimEnrichment` and related types not exported from `useOperatingPoints`.

- [ ] **Step 3: Add TypeScript interfaces to `useOperatingPoints.ts`**

At the top of `frontend/hooks/useOperatingPoints.ts`, add the type exports:

```typescript
export interface DeflectionReserve {
  deflection_deg: number;
  max_pos_deg: number;
  max_neg_deg: number;
  usage_fraction: number;
}

export interface DesignWarning {
  level: "info" | "warning" | "critical";
  category: string;
  surface: string | null;
  message: string;
}

export interface TrimEnrichment {
  analysis_goal: string;
  trim_method: string;
  trim_score: number | null;
  trim_residuals: Record<string, number>;
  deflection_reserves: Record<string, DeflectionReserve>;
  design_warnings: DesignWarning[];
}
```

And add `trim_enrichment: TrimEnrichment | null` to the existing `StoredOperatingPoint` interface.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-440-trim-interpretation/frontend && npx vitest run __tests__/trim-enrichment-types.test.ts`
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-440-trim-interpretation
git add frontend/hooks/useOperatingPoints.ts frontend/__tests__/trim-enrichment-types.test.ts
git commit -m "feat(gh-440): add TrimEnrichment TypeScript types to useOperatingPoints"
```

---

### Task 7: Frontend — Analysis Goal Banner + Control Authority Bars + Warning Badges

**Files:**
- Modify: `frontend/components/workbench/OperatingPointsPanel.tsx`
- Test: `frontend/__tests__/operating-points-enrichment.test.tsx`

- [ ] **Step 1: Write failing tests for enrichment display components**

```typescript
// frontend/__tests__/operating-points-enrichment.test.tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AnalysisGoalBanner, ControlAuthorityChart, DesignWarningBadges } from "@/components/workbench/OperatingPointsPanel";
import type { TrimEnrichment } from "@/hooks/useOperatingPoints";

const MOCK_ENRICHMENT: TrimEnrichment = {
  analysis_goal: "Can the aircraft trim near stall?",
  trim_method: "opti",
  trim_score: 0.02,
  trim_residuals: { cm: 0.001 },
  deflection_reserves: {
    "[elevator]Elevator": {
      deflection_deg: -5.0,
      max_pos_deg: 25.0,
      max_neg_deg: 25.0,
      usage_fraction: 0.2,
    },
    "[aileron]Left Aileron": {
      deflection_deg: 3.0,
      max_pos_deg: 20.0,
      max_neg_deg: 20.0,
      usage_fraction: 0.15,
    },
  },
  design_warnings: [
    {
      level: "warning",
      category: "authority",
      surface: "[elevator]Elevator",
      message: "85% authority used — surface may be undersized",
    },
  ],
};

describe("AnalysisGoalBanner", () => {
  it("renders analysis goal text", () => {
    render(<AnalysisGoalBanner enrichment={MOCK_ENRICHMENT} />);
    expect(screen.getByText("Can the aircraft trim near stall?")).toBeTruthy();
  });

  it("renders nothing when enrichment is null", () => {
    const { container } = render(<AnalysisGoalBanner enrichment={null} />);
    expect(container.firstChild).toBeNull();
  });
});

describe("ControlAuthorityChart", () => {
  it("renders a bar for each surface", () => {
    render(<ControlAuthorityChart enrichment={MOCK_ENRICHMENT} />);
    expect(screen.getByText(/Elevator/)).toBeTruthy();
    expect(screen.getByText(/Left Aileron/)).toBeTruthy();
  });

  it("shows percentage for each surface", () => {
    render(<ControlAuthorityChart enrichment={MOCK_ENRICHMENT} />);
    expect(screen.getByText("20%")).toBeTruthy();
    expect(screen.getByText("15%")).toBeTruthy();
  });

  it("renders nothing when enrichment is null", () => {
    const { container } = render(<ControlAuthorityChart enrichment={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when no deflection reserves", () => {
    const empty: TrimEnrichment = { ...MOCK_ENRICHMENT, deflection_reserves: {} };
    const { container } = render(<ControlAuthorityChart enrichment={empty} />);
    expect(container.firstChild).toBeNull();
  });
});

describe("DesignWarningBadges", () => {
  it("renders warning badges", () => {
    render(<DesignWarningBadges enrichment={MOCK_ENRICHMENT} />);
    expect(screen.getByText(/85% authority used/)).toBeTruthy();
  });

  it("renders nothing when no warnings", () => {
    const noWarn: TrimEnrichment = { ...MOCK_ENRICHMENT, design_warnings: [] };
    const { container } = render(<DesignWarningBadges enrichment={noWarn} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when enrichment is null", () => {
    const { container } = render(<DesignWarningBadges enrichment={null} />);
    expect(container.firstChild).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-440-trim-interpretation/frontend && npx vitest run __tests__/operating-points-enrichment.test.tsx`
Expected: FAIL — exported components don't exist yet.

- [ ] **Step 3: Implement the three enrichment display components**

Add to `frontend/components/workbench/OperatingPointsPanel.tsx`:

**AnalysisGoalBanner** — renders a highlighted banner showing the analysis goal:
```tsx
export function AnalysisGoalBanner({ enrichment }: Readonly<{ enrichment: TrimEnrichment | null }>) {
  if (!enrichment) return null;
  return (
    <div className="rounded-lg border border-[#FF8400]/30 bg-[#FF8400]/10 px-4 py-3">
      <span className="font-[family-name:var(--font-geist-sans)] text-[11px] font-medium uppercase tracking-wider text-[#FF8400]">
        Analysis Goal
      </span>
      <p className="mt-1 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground">
        {enrichment.analysis_goal}
      </p>
    </div>
  );
}
```

**ControlAuthorityChart** — horizontal bars per surface:
```tsx
function authorityColor(fraction: number): string {
  if (fraction > 0.95) return "bg-red-500";
  if (fraction > 0.80) return "bg-orange-500";
  if (fraction > 0.60) return "bg-yellow-500";
  return "bg-emerald-500";
}

function displaySurfaceName(encoded: string): string {
  const match = encoded.match(/^\[(\w+)\](.+)$/);
  return match ? match[2] : encoded;
}

export function ControlAuthorityChart({ enrichment }: Readonly<{ enrichment: TrimEnrichment | null }>) {
  if (!enrichment) return null;
  const entries = Object.entries(enrichment.deflection_reserves);
  if (entries.length === 0) return null;
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-card-muted p-4">
      <span className="font-[family-name:var(--font-geist-sans)] text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
        Control Authority
      </span>
      <div className="flex flex-col gap-2">
        {entries.map(([name, reserve]) => {
          const pct = Math.round(reserve.usage_fraction * 100);
          const barWidth = Math.min(pct, 100);
          return (
            <div key={name} className="flex flex-col gap-1">
              <div className="flex items-baseline justify-between">
                <span className="font-[family-name:var(--font-geist-sans)] text-[12px] text-muted-foreground">
                  {displaySurfaceName(name)}
                </span>
                <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground">
                  {pct}%
                </span>
              </div>
              <div className="h-2 w-full rounded-full bg-sidebar-accent">
                <div
                  className={`h-full rounded-full transition-all ${authorityColor(reserve.usage_fraction)}`}
                  style={{ width: `${barWidth}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

**DesignWarningBadges** — renders warning badges:
```tsx
const WARNING_STYLES = {
  info: "border-blue-500/30 bg-blue-500/10 text-blue-400",
  warning: "border-yellow-500/30 bg-yellow-500/10 text-yellow-400",
  critical: "border-red-500/30 bg-red-500/10 text-red-400",
} as const;

export function DesignWarningBadges({ enrichment }: Readonly<{ enrichment: TrimEnrichment | null }>) {
  if (!enrichment || enrichment.design_warnings.length === 0) return null;
  return (
    <div className="flex flex-col gap-1.5">
      {enrichment.design_warnings.map((w, i) => (
        <div
          key={i}
          className={`rounded-lg border px-3 py-2 ${WARNING_STYLES[w.level] ?? WARNING_STYLES.info}`}
        >
          <span className="font-[family-name:var(--font-geist-sans)] text-[12px]">
            {w.message}
          </span>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Add `TrimEnrichment` import to the component file**

Add at the top of `OperatingPointsPanel.tsx`:
```typescript
import type { TrimEnrichment } from "@/hooks/useOperatingPoints";
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-440-trim-interpretation/frontend && npx vitest run __tests__/operating-points-enrichment.test.tsx`
Expected: All pass.

- [ ] **Step 6: Commit**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-440-trim-interpretation
git add frontend/components/workbench/OperatingPointsPanel.tsx frontend/__tests__/operating-points-enrichment.test.tsx
git commit -m "feat(gh-440): add analysis goal banner, authority chart, and warning badges"
```

---

### Task 8: Frontend — Integrate Enrichment Components into OP Detail Drawer + Table Warning Icons

**Files:**
- Modify: `frontend/components/workbench/OperatingPointsPanel.tsx`
- Test: visual verification via dev server

- [ ] **Step 1: Add enrichment sections to the detail drawer**

In `OperatingPointsPanel.tsx`, inside the detail drawer `<div className="flex flex-col gap-5 p-6">`, insert the three new components after the description paragraph and before the "Flight Conditions" section:

```tsx
<AnalysisGoalBanner enrichment={selectedPoint.trim_enrichment ?? null} />
<ControlAuthorityChart enrichment={selectedPoint.trim_enrichment ?? null} />
<DesignWarningBadges enrichment={selectedPoint.trim_enrichment ?? null} />
```

- [ ] **Step 2: Add warning indicator to table rows**

In the table row for each OP, after the status badge cell, check `pt.trim_enrichment?.design_warnings`:

In the status `<td>`, after the status badge `<span>`, add:

```tsx
{pt.trim_enrichment?.design_warnings?.some(
  (w: { level: string }) => w.level === "warning" || w.level === "critical",
) && (
  <span
    className="ml-1.5 inline-block size-2 rounded-full bg-yellow-500"
    title="Has design warnings"
  />
)}
```

- [ ] **Step 3: Run full frontend test suite**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-440-trim-interpretation/frontend && npm run test:unit -- --run`
Expected: All tests pass (no regressions).

- [ ] **Step 4: Commit**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-440-trim-interpretation
git add frontend/components/workbench/OperatingPointsPanel.tsx
git commit -m "feat(gh-440): integrate enrichment display into OP detail drawer and table"
```

- [ ] **Step 5: Start dev server and verify in browser**

Run both backend and frontend:
```bash
# Terminal 1 (backend)
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-440-trim-interpretation
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Terminal 2 (frontend)
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-440-trim-interpretation/frontend
npm run dev
```

Test:
1. Open workbench, select an aircraft
2. Go to Analysis → Operating Points
3. Click "Generate Default OPs"
4. Verify OPs appear in the table
5. Click an OP row to open the detail drawer
6. Verify: Analysis Goal banner appears with orange accent
7. Verify: Control Authority section with horizontal bars
8. Verify: Warning badges appear for high-authority OPs
9. Verify: Warning indicator dots appear on table rows
10. Verify: OPs without enrichment (if any) render without errors
