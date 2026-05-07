# Flight Envelope Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add flight envelope computation (V-n curves, performance KPIs) with REST API, MCP tools, and an Envelope tab in the analysis workbench.

**Architecture:** New service `flight_envelope_service.py` computes V-n diagram boundaries and KPIs from design assumptions (mass, cl_max, g_limit) and wing geometry. Results cached in a new `flight_envelopes` DB table. Two endpoints (GET cached, POST compute) exposed via REST and MCP. Frontend adds an "Envelope" tab with KPI cards and a Plotly V-n chart.

**Tech Stack:** Python/FastAPI, SQLAlchemy/Alembic, Pydantic v2, AeroSandbox, React 19/Next.js 16, Plotly, SWR-style hooks.

---

## File Structure

### Backend (create)
- `app/schemas/flight_envelope.py` — Pydantic schemas (VnPoint, VnCurve, PerformanceKPI, VnMarker, FlightEnvelopeRead, ComputeEnvelopeRequest)
- `app/models/flight_envelope_model.py` — SQLAlchemy model (FlightEnvelopeModel)
- `app/services/flight_envelope_service.py` — Business logic (compute_flight_envelope, get_flight_envelope)
- `app/api/v2/endpoints/aeroplane/flight_envelope.py` — REST endpoints
- `alembic/versions/*_add_flight_envelopes_table.py` — DB migration
- `app/tests/test_flight_envelope_service.py` — Service unit tests
- `app/tests/test_flight_envelope_endpoints.py` — Endpoint tests

### Backend (modify)
- `app/api/v2/endpoints/aeroplane/__init__.py` — Register flight_envelope router
- `app/mcp_server.py` — Register MCP tools

### Frontend (create)
- `frontend/hooks/useFlightEnvelope.ts` — SWR-style hook
- `frontend/components/workbench/EnvelopePanel.tsx` — Container with view toggle
- `frontend/components/workbench/PerformanceOverview.tsx` — KPI cards grid
- `frontend/components/workbench/VnDiagram.tsx` — Plotly V-n chart
- `frontend/__tests__/useFlightEnvelope.test.ts` — Hook tests
- `frontend/__tests__/EnvelopePanel.test.tsx` — Component tests

### Frontend (modify)
- `frontend/components/workbench/AnalysisViewerPanel.tsx` — Add "Envelope" to TABS
- `frontend/app/workbench/analysis/page.tsx` — Wire envelope data to AnalysisViewerPanel

---

## Task 1: Flight Envelope Schemas

**Files:**
- Create: `app/schemas/flight_envelope.py`
- Test: `app/tests/test_flight_envelope_service.py` (schema validation tests)

- [ ] **Step 1: Write failing tests for schema validation**

```python
"""Tests for flight envelope schemas and service."""

from __future__ import annotations

import pytest

from app.schemas.flight_envelope import (
    VnPoint,
    VnCurve,
    PerformanceKPI,
    VnMarker,
    FlightEnvelopeRead,
    ComputeEnvelopeRequest,
)


class TestVnPointSchema:
    def test_valid_point(self):
        p = VnPoint(velocity_mps=20.0, load_factor=1.0)
        assert p.velocity_mps == 20.0
        assert p.load_factor == 1.0

    def test_negative_velocity_rejected(self):
        with pytest.raises(ValueError):
            VnPoint(velocity_mps=-1.0, load_factor=1.0)


class TestVnCurveSchema:
    def test_valid_curve(self):
        curve = VnCurve(
            positive=[VnPoint(velocity_mps=10.0, load_factor=1.0)],
            negative=[VnPoint(velocity_mps=10.0, load_factor=-0.5)],
            dive_speed_mps=40.0,
            stall_speed_mps=8.0,
        )
        assert curve.dive_speed_mps == 40.0
        assert curve.stall_speed_mps == 8.0
        assert len(curve.positive) == 1


class TestPerformanceKPISchema:
    def test_valid_kpi(self):
        kpi = PerformanceKPI(
            label="stall_speed",
            display_name="Stall Speed",
            value=8.5,
            unit="m/s",
            source_op_id=None,
            confidence="estimated",
        )
        assert kpi.label == "stall_speed"
        assert kpi.confidence == "estimated"


class TestComputeEnvelopeRequestSchema:
    def test_defaults(self):
        req = ComputeEnvelopeRequest()
        assert req.force_recompute is False
```

- [ ] **Step 2: Run tests — expect ImportError**

Run: `poetry run pytest app/tests/test_flight_envelope_service.py::TestVnPointSchema -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.schemas.flight_envelope'`

- [ ] **Step 3: Implement schemas**

```python
"""Flight envelope schemas — V-n diagram and performance KPIs."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class VnPoint(BaseModel):
    velocity_mps: float = Field(..., description="Velocity in m/s")
    load_factor: float = Field(..., description="Load factor in g")

    @field_validator("velocity_mps")
    @classmethod
    def velocity_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError("velocity must be non-negative")
        return v


class VnCurve(BaseModel):
    positive: list[VnPoint] = Field(..., description="Positive-g V-n boundary")
    negative: list[VnPoint] = Field(..., description="Negative-g V-n boundary")
    dive_speed_mps: float = Field(..., description="Dive speed V_d in m/s")
    stall_speed_mps: float = Field(..., description="1-g stall speed in m/s")


class PerformanceKPI(BaseModel):
    label: str = Field(..., description="Machine key, e.g. stall_speed")
    display_name: str = Field(..., description="Human label, e.g. Stall Speed")
    value: float
    unit: str = Field("", description="Display unit, e.g. m/s")
    source_op_id: int | None = Field(None, description="Linked operating point id")
    confidence: Literal["trimmed", "estimated", "limit"] = Field(
        "estimated", description="How the value was derived"
    )


class VnMarker(BaseModel):
    op_id: int
    name: str
    velocity_mps: float
    load_factor: float
    status: str = Field(..., description="TRIMMED / NOT_TRIMMED / LIMIT_REACHED")
    label: str = Field("", description="Semantic label, e.g. cruise, stall")


class FlightEnvelopeRead(BaseModel):
    id: int
    aeroplane_id: int
    vn_curve: VnCurve
    kpis: list[PerformanceKPI]
    operating_points: list[VnMarker]
    assumptions_snapshot: dict = Field(
        ..., description="Design assumption values used for computation"
    )
    computed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComputeEnvelopeRequest(BaseModel):
    force_recompute: bool = Field(
        False, description="Recompute even if a cached result exists"
    )
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `poetry run pytest app/tests/test_flight_envelope_service.py -v -k "Schema"`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/schemas/flight_envelope.py app/tests/test_flight_envelope_service.py
git commit -m "feat(gh-422): add flight envelope schemas with tests"
```

---

## Task 2: DB Model + Alembic Migration

**Files:**
- Create: `app/models/flight_envelope_model.py`
- Create: `alembic/versions/*_add_flight_envelopes_table.py` (auto-generated)
- Modify: `app/tests/test_flight_envelope_service.py` (add model tests)

- [ ] **Step 1: Write failing test for model creation**

Append to `app/tests/test_flight_envelope_service.py`:

```python
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base_class import Base
from app.models.flight_envelope_model import FlightEnvelopeModel
from app.tests.conftest import make_aeroplane


class TestFlightEnvelopeModel:
    def _make_session(self) -> Session:
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(bind=engine)
        return sessionmaker(bind=engine)()

    def test_create_and_read(self):
        session = self._make_session()
        aeroplane = make_aeroplane(session)
        envelope = FlightEnvelopeModel(
            aeroplane_id=aeroplane.id,
            vn_curve_json={"positive": [], "negative": [], "dive_speed_mps": 40.0, "stall_speed_mps": 8.0},
            kpis_json=[{"label": "stall_speed", "display_name": "Stall Speed", "value": 8.5, "unit": "m/s"}],
            markers_json=[],
            assumptions_snapshot={"mass": 1.5, "cl_max": 1.4, "g_limit": 3.0},
            computed_at=datetime.now(timezone.utc),
        )
        session.add(envelope)
        session.commit()
        session.refresh(envelope)

        assert envelope.id is not None
        assert envelope.aeroplane_id == aeroplane.id
        assert envelope.vn_curve_json["dive_speed_mps"] == 40.0

    def test_unique_per_aeroplane(self):
        session = self._make_session()
        aeroplane = make_aeroplane(session)
        now = datetime.now(timezone.utc)
        base = dict(
            aeroplane_id=aeroplane.id,
            vn_curve_json={},
            kpis_json=[],
            markers_json=[],
            assumptions_snapshot={},
            computed_at=now,
        )
        session.add(FlightEnvelopeModel(**base))
        session.commit()
        session.add(FlightEnvelopeModel(**base))
        with pytest.raises(Exception):
            session.commit()
```

- [ ] **Step 2: Run tests — expect ImportError**

Run: `poetry run pytest app/tests/test_flight_envelope_service.py::TestFlightEnvelopeModel -v`
Expected: FAIL — cannot import `FlightEnvelopeModel`

- [ ] **Step 3: Implement DB model**

```python
"""Flight envelope DB model — caches computed envelope per aeroplane."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, JSON, ForeignKey, func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class FlightEnvelopeModel(Base):
    __tablename__ = "flight_envelopes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    aeroplane_id = Column(
        Integer,
        ForeignKey("aeroplanes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    vn_curve_json = Column(JSON, nullable=False)
    kpis_json = Column(JSON, nullable=False, default=list)
    markers_json = Column(JSON, nullable=False, default=list)
    assumptions_snapshot = Column(JSON, nullable=False, default=dict)
    computed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    aeroplane = relationship("AeroplaneModel", backref="flight_envelope")
```

- [ ] **Step 4: Run model tests — expect PASS**

Run: `poetry run pytest app/tests/test_flight_envelope_service.py::TestFlightEnvelopeModel -v`
Expected: PASS

- [ ] **Step 5: Generate Alembic migration**

```bash
poetry run alembic revision --autogenerate -m "add flight_envelopes table"
```

Review the generated migration: verify it creates `flight_envelopes` table with the correct columns, FK, and unique constraint.

- [ ] **Step 6: Run migration to verify it applies cleanly**

```bash
poetry run alembic upgrade head
```

- [ ] **Step 7: Commit**

```bash
git add app/models/flight_envelope_model.py alembic/versions/*flight_envelopes* app/tests/test_flight_envelope_service.py
git commit -m "feat(gh-422): add FlightEnvelopeModel with Alembic migration"
```

---

## Task 3: Flight Envelope Computation Service

**Files:**
- Create: `app/services/flight_envelope_service.py`
- Modify: `app/tests/test_flight_envelope_service.py` (add computation tests)

- [ ] **Step 1: Write failing tests for V-n curve computation**

Append to `app/tests/test_flight_envelope_service.py`:

```python
import math

from app.services.flight_envelope_service import (
    compute_vn_curve,
    derive_performance_kpis,
)


class TestComputeVnCurve:
    """Test V-n curve math with known inputs."""

    def test_stall_speed(self):
        """V_stall = sqrt(2*m*g / (rho*S*cl_max))"""
        mass_kg = 1.5
        cl_max = 1.4
        g_limit = 3.0
        wing_area_m2 = 0.5
        rho = 1.225
        v_max_mps = 30.0

        curve = compute_vn_curve(
            mass_kg=mass_kg,
            cl_max=cl_max,
            g_limit=g_limit,
            wing_area_m2=wing_area_m2,
            rho=rho,
            v_max_mps=v_max_mps,
        )

        expected_stall = math.sqrt(2 * mass_kg * 9.81 / (rho * wing_area_m2 * cl_max))
        assert abs(curve.stall_speed_mps - expected_stall) < 0.01

    def test_dive_speed(self):
        curve = compute_vn_curve(
            mass_kg=1.5, cl_max=1.4, g_limit=3.0,
            wing_area_m2=0.5, rho=1.225, v_max_mps=30.0,
        )
        assert abs(curve.dive_speed_mps - 42.0) < 0.01  # 1.4 * 30

    def test_positive_boundary_capped_at_g_limit(self):
        curve = compute_vn_curve(
            mass_kg=1.5, cl_max=1.4, g_limit=3.0,
            wing_area_m2=0.5, rho=1.225, v_max_mps=30.0,
        )
        for pt in curve.positive:
            assert pt.load_factor <= 3.0 + 0.001

    def test_negative_boundary_capped(self):
        curve = compute_vn_curve(
            mass_kg=1.5, cl_max=1.4, g_limit=3.0,
            wing_area_m2=0.5, rho=1.225, v_max_mps=30.0,
        )
        for pt in curve.negative:
            assert pt.load_factor >= -1.2 - 0.001  # -0.4 * g_limit

    def test_positive_boundary_starts_at_stall(self):
        curve = compute_vn_curve(
            mass_kg=1.5, cl_max=1.4, g_limit=3.0,
            wing_area_m2=0.5, rho=1.225, v_max_mps=30.0,
        )
        assert curve.positive[0].load_factor == pytest.approx(1.0, abs=0.05)

    def test_curve_has_reasonable_number_of_points(self):
        curve = compute_vn_curve(
            mass_kg=1.5, cl_max=1.4, g_limit=3.0,
            wing_area_m2=0.5, rho=1.225, v_max_mps=30.0,
        )
        assert len(curve.positive) >= 10
        assert len(curve.negative) >= 10
```

- [ ] **Step 2: Run tests — expect ImportError**

Run: `poetry run pytest app/tests/test_flight_envelope_service.py::TestComputeVnCurve -v`
Expected: FAIL — cannot import `compute_vn_curve`

- [ ] **Step 3: Implement V-n curve computation**

```python
"""Flight envelope computation — V-n curves and performance KPIs."""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone

from app.schemas.flight_envelope import PerformanceKPI, VnCurve, VnPoint

logger = logging.getLogger(__name__)

GRAVITY = 9.81
SEA_LEVEL_RHO = 1.225
CL_MIN_FACTOR = -0.8
NEGATIVE_G_FACTOR = -0.4
DIVE_SPEED_FACTOR = 1.4
VN_NUM_POINTS = 50


def compute_vn_curve(
    *,
    mass_kg: float,
    cl_max: float,
    g_limit: float,
    wing_area_m2: float,
    rho: float = SEA_LEVEL_RHO,
    v_max_mps: float,
) -> VnCurve:
    """Compute V-n diagram boundaries."""
    v_stall = math.sqrt(2 * mass_kg * GRAVITY / (rho * wing_area_m2 * cl_max))
    v_dive = DIVE_SPEED_FACTOR * v_max_mps
    cl_min = CL_MIN_FACTOR * cl_max
    neg_g_cap = NEGATIVE_G_FACTOR * g_limit

    positive: list[VnPoint] = []
    negative: list[VnPoint] = []

    for i in range(VN_NUM_POINTS + 1):
        v = v_stall + (v_dive - v_stall) * i / VN_NUM_POINTS

        n_pos = 0.5 * rho * v**2 * wing_area_m2 * cl_max / (mass_kg * GRAVITY)
        n_pos = min(n_pos, g_limit)
        positive.append(VnPoint(velocity_mps=round(v, 4), load_factor=round(n_pos, 4)))

        n_neg = 0.5 * rho * v**2 * wing_area_m2 * cl_min / (mass_kg * GRAVITY)
        n_neg = max(n_neg, neg_g_cap)
        negative.append(VnPoint(velocity_mps=round(v, 4), load_factor=round(n_neg, 4)))

    return VnCurve(
        positive=positive,
        negative=negative,
        dive_speed_mps=round(v_dive, 4),
        stall_speed_mps=round(v_stall, 4),
    )
```

- [ ] **Step 4: Run V-n tests — expect PASS**

Run: `poetry run pytest app/tests/test_flight_envelope_service.py::TestComputeVnCurve -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Write failing tests for KPI derivation**

Append to `app/tests/test_flight_envelope_service.py`:

```python
from app.schemas.flight_envelope import VnMarker


class TestDerivePerformanceKpis:
    def test_stall_speed_kpi(self):
        kpis = derive_performance_kpis(
            stall_speed_mps=8.5,
            v_max_mps=30.0,
            g_limit=3.0,
            markers=[],
        )
        stall = next(k for k in kpis if k.label == "stall_speed")
        assert stall.value == pytest.approx(8.5, abs=0.01)
        assert stall.unit == "m/s"

    def test_dive_speed_kpi(self):
        kpis = derive_performance_kpis(
            stall_speed_mps=8.5,
            v_max_mps=30.0,
            g_limit=3.0,
            markers=[],
        )
        dive = next(k for k in kpis if k.label == "dive_speed")
        assert dive.value == pytest.approx(42.0, abs=0.01)

    def test_best_ld_from_markers(self):
        markers = [
            VnMarker(op_id=1, name="cruise", velocity_mps=18.0, load_factor=1.0,
                      status="TRIMMED", label="cruise"),
            VnMarker(op_id=2, name="best_ld", velocity_mps=15.0, load_factor=1.0,
                      status="TRIMMED", label="best_ld"),
        ]
        kpis = derive_performance_kpis(
            stall_speed_mps=8.5, v_max_mps=30.0, g_limit=3.0, markers=markers,
        )
        best_ld = next((k for k in kpis if k.label == "best_ld_speed"), None)
        assert best_ld is not None
        assert best_ld.value == pytest.approx(15.0)
        assert best_ld.confidence == "trimmed"

    def test_always_has_six_kpis(self):
        kpis = derive_performance_kpis(
            stall_speed_mps=8.5, v_max_mps=30.0, g_limit=3.0, markers=[],
        )
        assert len(kpis) == 6
```

- [ ] **Step 6: Run KPI tests — expect ImportError for derive_performance_kpis**

Run: `poetry run pytest app/tests/test_flight_envelope_service.py::TestDerivePerformanceKpis -v`
Expected: FAIL — cannot import `derive_performance_kpis`

- [ ] **Step 7: Implement KPI derivation**

Add to `app/services/flight_envelope_service.py`:

```python
def derive_performance_kpis(
    *,
    stall_speed_mps: float,
    v_max_mps: float,
    g_limit: float,
    markers: list[VnMarker],
) -> list[PerformanceKPI]:
    """Derive six performance KPIs from envelope data and operating point markers."""
    from app.schemas.flight_envelope import VnMarker

    def _find_marker(label: str) -> VnMarker | None:
        return next((m for m in markers if m.label == label), None)

    def _confidence(marker: VnMarker | None) -> str:
        if marker is None:
            return "estimated"
        return "trimmed" if marker.status == "TRIMMED" else "limit"

    best_ld = _find_marker("best_ld")
    min_sink = _find_marker("min_sink")
    max_turn = _find_marker("max_turn")

    return [
        PerformanceKPI(
            label="stall_speed",
            display_name="Stall Speed",
            value=round(stall_speed_mps, 2),
            unit="m/s",
            source_op_id=None,
            confidence="estimated",
        ),
        PerformanceKPI(
            label="best_ld_speed",
            display_name="Best L/D Speed",
            value=round(best_ld.velocity_mps if best_ld else stall_speed_mps * 1.4, 2),
            unit="m/s",
            source_op_id=best_ld.op_id if best_ld else None,
            confidence=_confidence(best_ld),
        ),
        PerformanceKPI(
            label="min_sink_speed",
            display_name="Min Sink Speed",
            value=round(min_sink.velocity_mps if min_sink else stall_speed_mps * 1.2, 2),
            unit="m/s",
            source_op_id=min_sink.op_id if min_sink else None,
            confidence=_confidence(min_sink),
        ),
        PerformanceKPI(
            label="max_speed",
            display_name="Max Speed",
            value=round(v_max_mps, 2),
            unit="m/s",
            source_op_id=None,
            confidence="estimated",
        ),
        PerformanceKPI(
            label="max_load_factor",
            display_name="Max Load Factor",
            value=round(max_turn.load_factor if max_turn else g_limit, 2),
            unit="g",
            source_op_id=max_turn.op_id if max_turn else None,
            confidence=_confidence(max_turn),
        ),
        PerformanceKPI(
            label="dive_speed",
            display_name="Dive Speed",
            value=round(DIVE_SPEED_FACTOR * v_max_mps, 2),
            unit="m/s",
            source_op_id=None,
            confidence="estimated",
        ),
    ]
```

- [ ] **Step 8: Run KPI tests — expect PASS**

Run: `poetry run pytest app/tests/test_flight_envelope_service.py::TestDerivePerformanceKpis -v`
Expected: All 4 tests PASS

- [ ] **Step 9: Commit**

```bash
git add app/services/flight_envelope_service.py app/tests/test_flight_envelope_service.py
git commit -m "feat(gh-422): add V-n curve computation and KPI derivation"
```

---

## Task 4: Full Envelope Service (DB Integration)

**Files:**
- Modify: `app/services/flight_envelope_service.py` (add compute_flight_envelope, get_flight_envelope)
- Modify: `app/tests/test_flight_envelope_service.py` (add integration tests)

- [ ] **Step 1: Write failing tests for the full service functions**

Append to `app/tests/test_flight_envelope_service.py`:

```python
from unittest.mock import patch, MagicMock

from app.services.flight_envelope_service import (
    compute_flight_envelope,
    get_flight_envelope,
)
from app.core.exceptions import NotFoundError


class TestComputeFlightEnvelope:
    """Test the orchestrating service function with mocked dependencies."""

    def _make_db_and_aeroplane(self):
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(bind=engine)
        session = sessionmaker(bind=engine)()
        aeroplane = make_aeroplane(session)
        return session, aeroplane

    @patch("app.services.flight_envelope_service._get_wing_area_m2")
    @patch("app.services.flight_envelope_service._load_assumptions")
    @patch("app.services.flight_envelope_service._load_operating_point_markers")
    @patch("app.services.flight_envelope_service._get_v_max")
    def test_compute_returns_envelope(
        self, mock_vmax, mock_markers, mock_assumptions, mock_area
    ):
        db, aeroplane = self._make_db_and_aeroplane()
        mock_assumptions.return_value = {"mass": 1.5, "cl_max": 1.4, "g_limit": 3.0}
        mock_area.return_value = 0.5
        mock_markers.return_value = []
        mock_vmax.return_value = 30.0

        result = compute_flight_envelope(db, aeroplane.uuid)

        assert result.aeroplane_id == aeroplane.id
        assert result.vn_curve.stall_speed_mps > 0
        assert len(result.kpis) == 6
        assert result.assumptions_snapshot["mass"] == 1.5

    @patch("app.services.flight_envelope_service._get_wing_area_m2")
    @patch("app.services.flight_envelope_service._load_assumptions")
    @patch("app.services.flight_envelope_service._load_operating_point_markers")
    @patch("app.services.flight_envelope_service._get_v_max")
    def test_compute_persists_to_db(
        self, mock_vmax, mock_markers, mock_assumptions, mock_area
    ):
        db, aeroplane = self._make_db_and_aeroplane()
        mock_assumptions.return_value = {"mass": 1.5, "cl_max": 1.4, "g_limit": 3.0}
        mock_area.return_value = 0.5
        mock_markers.return_value = []
        mock_vmax.return_value = 30.0

        compute_flight_envelope(db, aeroplane.uuid)
        cached = get_flight_envelope(db, aeroplane.uuid)

        assert cached is not None
        assert cached.aeroplane_id == aeroplane.id

    @patch("app.services.flight_envelope_service._get_wing_area_m2")
    @patch("app.services.flight_envelope_service._load_assumptions")
    @patch("app.services.flight_envelope_service._load_operating_point_markers")
    @patch("app.services.flight_envelope_service._get_v_max")
    def test_compute_upserts(
        self, mock_vmax, mock_markers, mock_assumptions, mock_area
    ):
        db, aeroplane = self._make_db_and_aeroplane()
        mock_assumptions.return_value = {"mass": 1.5, "cl_max": 1.4, "g_limit": 3.0}
        mock_area.return_value = 0.5
        mock_markers.return_value = []
        mock_vmax.return_value = 30.0

        compute_flight_envelope(db, aeroplane.uuid)
        mock_assumptions.return_value = {"mass": 2.0, "cl_max": 1.4, "g_limit": 3.0}
        result = compute_flight_envelope(db, aeroplane.uuid)

        assert result.assumptions_snapshot["mass"] == 2.0


class TestGetFlightEnvelope:
    def test_returns_none_when_no_envelope(self):
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(bind=engine)
        session = sessionmaker(bind=engine)()
        aeroplane = make_aeroplane(session)

        result = get_flight_envelope(session, aeroplane.uuid)
        assert result is None
```

- [ ] **Step 2: Run tests — expect ImportError**

Run: `poetry run pytest app/tests/test_flight_envelope_service.py::TestComputeFlightEnvelope -v`
Expected: FAIL — cannot import `compute_flight_envelope`

- [ ] **Step 3: Implement full service functions**

Add to `app/services/flight_envelope_service.py`:

```python
from sqlalchemy.orm import Session

from app.core.exceptions import InternalError, NotFoundError
from app.models.aeroplanemodel import AeroplaneModel
from app.models.flight_envelope_model import FlightEnvelopeModel
from app.schemas.flight_envelope import FlightEnvelopeRead, VnMarker


def _get_aeroplane(db: Session, aeroplane_uuid) -> AeroplaneModel:
    aeroplane = (
        db.query(AeroplaneModel).filter(AeroplaneModel.uuid == str(aeroplane_uuid)).first()
    )
    if aeroplane is None:
        raise NotFoundError(entity="Aeroplane", resource_id=str(aeroplane_uuid))
    return aeroplane


def _load_assumptions(db: Session, aeroplane_uuid) -> dict[str, float]:
    from app.services.mass_cg_service import get_effective_assumption_value

    params = {}
    for name in ("mass", "cl_max", "g_limit"):
        try:
            params[name] = get_effective_assumption_value(db, aeroplane_uuid, name)
        except NotFoundError:
            from app.schemas.design_assumption import PARAMETER_DEFAULTS

            params[name] = PARAMETER_DEFAULTS[name]
    return params


def _get_wing_area_m2(db: Session, aeroplane: AeroplaneModel) -> float:
    from app.converters.model_schema_converters import (
        aeroplane_model_to_aeroplane_schema_async,
        aeroplane_schema_to_asb_airplane_async,
    )

    schema = aeroplane_model_to_aeroplane_schema_async(aeroplane)
    asb_airplane = aeroplane_schema_to_asb_airplane_async(plane_schema=schema)
    s_ref = asb_airplane.s_ref
    if s_ref is None or s_ref <= 0:
        raise InternalError("Cannot determine wing reference area — no wings defined")
    return float(s_ref)


def _get_v_max(db: Session, aeroplane: AeroplaneModel) -> float:
    if aeroplane.flight_profile and aeroplane.flight_profile.goals:
        goals = aeroplane.flight_profile.goals
        if isinstance(goals, dict) and "max_level_speed_mps" in goals:
            return float(goals["max_level_speed_mps"])
    return 28.0  # sensible default for RC aircraft


def _load_operating_point_markers(
    db: Session, aeroplane: AeroplaneModel, mass_kg: float, wing_area_m2: float,
) -> list[VnMarker]:
    from app.models.analysismodels import OperatingPointModel

    ops = (
        db.query(OperatingPointModel)
        .filter(OperatingPointModel.aircraft_id == aeroplane.id)
        .all()
    )
    markers = []
    for op in ops:
        v = op.velocity
        if v <= 0 or mass_kg <= 0 or wing_area_m2 <= 0:
            continue
        n = 0.5 * SEA_LEVEL_RHO * v**2 * wing_area_m2 / (mass_kg * GRAVITY)
        markers.append(
            VnMarker(
                op_id=op.id,
                name=op.name,
                velocity_mps=round(v, 4),
                load_factor=round(min(n, 1.0) if op.status == "NOT_TRIMMED" else n, 4),
                status=op.status,
                label=op.name.lower().replace(" ", "_"),
            )
        )
    return markers


def compute_flight_envelope(db: Session, aeroplane_uuid) -> FlightEnvelopeRead:
    """Compute and persist flight envelope for an aeroplane."""
    aeroplane = _get_aeroplane(db, aeroplane_uuid)
    assumptions = _load_assumptions(db, aeroplane_uuid)
    wing_area = _get_wing_area_m2(db, aeroplane)
    v_max = _get_v_max(db, aeroplane)

    curve = compute_vn_curve(
        mass_kg=assumptions["mass"],
        cl_max=assumptions["cl_max"],
        g_limit=assumptions["g_limit"],
        wing_area_m2=wing_area,
        v_max_mps=v_max,
    )

    markers = _load_operating_point_markers(db, aeroplane, assumptions["mass"], wing_area)

    kpis = derive_performance_kpis(
        stall_speed_mps=curve.stall_speed_mps,
        v_max_mps=v_max,
        g_limit=assumptions["g_limit"],
        markers=markers,
    )

    now = datetime.now(timezone.utc)

    existing = (
        db.query(FlightEnvelopeModel)
        .filter(FlightEnvelopeModel.aeroplane_id == aeroplane.id)
        .first()
    )
    if existing:
        existing.vn_curve_json = curve.model_dump()
        existing.kpis_json = [k.model_dump() for k in kpis]
        existing.markers_json = [m.model_dump() for m in markers]
        existing.assumptions_snapshot = assumptions
        existing.computed_at = now
        envelope = existing
    else:
        envelope = FlightEnvelopeModel(
            aeroplane_id=aeroplane.id,
            vn_curve_json=curve.model_dump(),
            kpis_json=[k.model_dump() for k in kpis],
            markers_json=[m.model_dump() for m in markers],
            assumptions_snapshot=assumptions,
            computed_at=now,
        )
        db.add(envelope)

    db.flush()
    db.refresh(envelope)

    return FlightEnvelopeRead(
        id=envelope.id,
        aeroplane_id=envelope.aeroplane_id,
        vn_curve=VnCurve(**envelope.vn_curve_json),
        kpis=[PerformanceKPI(**k) for k in envelope.kpis_json],
        operating_points=[VnMarker(**m) for m in envelope.markers_json],
        assumptions_snapshot=envelope.assumptions_snapshot,
        computed_at=envelope.computed_at,
    )


def get_flight_envelope(db: Session, aeroplane_uuid) -> FlightEnvelopeRead | None:
    """Return cached flight envelope or None."""
    aeroplane = _get_aeroplane(db, aeroplane_uuid)
    envelope = (
        db.query(FlightEnvelopeModel)
        .filter(FlightEnvelopeModel.aeroplane_id == aeroplane.id)
        .first()
    )
    if envelope is None:
        return None

    return FlightEnvelopeRead(
        id=envelope.id,
        aeroplane_id=envelope.aeroplane_id,
        vn_curve=VnCurve(**envelope.vn_curve_json),
        kpis=[PerformanceKPI(**k) for k in envelope.kpis_json],
        operating_points=[VnMarker(**m) for m in envelope.markers_json],
        assumptions_snapshot=envelope.assumptions_snapshot,
        computed_at=envelope.computed_at,
    )
```

Note: The `_load_operating_point_markers` and `_get_wing_area_from_cache` functions use a module-level cache for wing area to avoid recomputing during the marker loop. The worker should clear `_wing_area_cache` between test runs if needed.

- [ ] **Step 4: Run full service tests — expect PASS**

Run: `poetry run pytest app/tests/test_flight_envelope_service.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/flight_envelope_service.py app/tests/test_flight_envelope_service.py
git commit -m "feat(gh-422): add full flight envelope service with DB persistence"
```

---

## Task 5: REST Endpoints

**Files:**
- Create: `app/api/v2/endpoints/aeroplane/flight_envelope.py`
- Modify: `app/api/v2/endpoints/aeroplane/__init__.py`
- Create: `app/tests/test_flight_envelope_endpoints.py`

- [ ] **Step 1: Write failing endpoint tests**

```python
"""Tests for flight envelope REST endpoints."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.core.platform import aerosandbox_available
from app.schemas.flight_envelope import FlightEnvelopeRead, VnCurve, VnPoint
from app.tests.conftest import make_aeroplane

pytestmark = pytest.mark.skipif(
    not aerosandbox_available(),
    reason="flight envelope endpoints require aerosandbox",
)


def _mock_envelope_read(aeroplane_id: int) -> FlightEnvelopeRead:
    from datetime import datetime, timezone

    return FlightEnvelopeRead(
        id=1,
        aeroplane_id=aeroplane_id,
        vn_curve=VnCurve(
            positive=[VnPoint(velocity_mps=10.0, load_factor=1.0)],
            negative=[VnPoint(velocity_mps=10.0, load_factor=-0.5)],
            dive_speed_mps=42.0,
            stall_speed_mps=8.5,
        ),
        kpis=[],
        operating_points=[],
        assumptions_snapshot={"mass": 1.5, "cl_max": 1.4, "g_limit": 3.0},
        computed_at=datetime.now(timezone.utc),
    )


class TestGetFlightEnvelope:
    def test_returns_cached(self, client_and_db):
        client, SessionLocal = client_and_db
        db = SessionLocal()
        aeroplane = make_aeroplane(db)
        db.close()

        with patch(
            "app.services.flight_envelope_service.get_flight_envelope"
        ) as mock_get:
            mock_get.return_value = _mock_envelope_read(aeroplane.id)
            resp = client.get(f"/aeroplanes/{aeroplane.uuid}/flight-envelope")
            assert resp.status_code == 200
            data = resp.json()
            assert data["vn_curve"]["stall_speed_mps"] == 8.5

    def test_returns_404_when_none(self, client_and_db):
        client, SessionLocal = client_and_db
        db = SessionLocal()
        aeroplane = make_aeroplane(db)
        db.close()

        with patch(
            "app.services.flight_envelope_service.get_flight_envelope"
        ) as mock_get:
            mock_get.return_value = None
            resp = client.get(f"/aeroplanes/{aeroplane.uuid}/flight-envelope")
            assert resp.status_code == 404


class TestComputeFlightEnvelope:
    def test_compute_returns_envelope(self, client_and_db):
        client, SessionLocal = client_and_db
        db = SessionLocal()
        aeroplane = make_aeroplane(db)
        db.close()

        with patch(
            "app.services.flight_envelope_service.compute_flight_envelope"
        ) as mock_compute:
            mock_compute.return_value = _mock_envelope_read(aeroplane.id)
            resp = client.post(f"/aeroplanes/{aeroplane.uuid}/flight-envelope/compute")
            assert resp.status_code == 200
            data = resp.json()
            assert "vn_curve" in data
            assert "kpis" in data
```

- [ ] **Step 2: Run tests — expect failure (router not registered)**

Run: `poetry run pytest app/tests/test_flight_envelope_endpoints.py -v`
Expected: FAIL — 404 (route not found)

- [ ] **Step 3: Implement endpoint file**

```python
"""Flight envelope REST endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import UUID4
from sqlalchemy.orm import Session

from app.core.exceptions import ServiceException, NotFoundError, InternalError
from app.db.session import get_db
from app.schemas.flight_envelope import ComputeEnvelopeRequest, FlightEnvelopeRead
from app.services import flight_envelope_service

router = APIRouter()


def _raise_http_from_domain(exc: ServiceException) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    if isinstance(exc, InternalError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
    ) from exc


@router.get(
    "/aeroplanes/{aeroplane_id}/flight-envelope",
    operation_id="get_flight_envelope",
)
async def get_flight_envelope(
    aeroplane_id: Annotated[UUID4, Path(..., description="Aeroplane UUID")],
    db: Annotated[Session, Depends(get_db)],
) -> FlightEnvelopeRead:
    try:
        result = flight_envelope_service.get_flight_envelope(db, aeroplane_id)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No flight envelope computed yet",
            )
        return result
    except ServiceException as exc:
        _raise_http_from_domain(exc)


@router.post(
    "/aeroplanes/{aeroplane_id}/flight-envelope/compute",
    operation_id="compute_flight_envelope",
)
async def compute_flight_envelope_endpoint(
    aeroplane_id: Annotated[UUID4, Path(..., description="Aeroplane UUID")],
    db: Annotated[Session, Depends(get_db)],
) -> FlightEnvelopeRead:
    try:
        return flight_envelope_service.compute_flight_envelope(db, aeroplane_id)
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Envelope computation failed: {exc}",
        ) from exc
```

- [ ] **Step 4: Register the router**

In `app/api/v2/endpoints/aeroplane/__init__.py`, add:

```python
from .flight_envelope import router as flight_envelope_router
# ... after existing includes
router.include_router(flight_envelope_router)
```

- [ ] **Step 5: Run endpoint tests — expect PASS**

Run: `poetry run pytest app/tests/test_flight_envelope_endpoints.py -v`
Expected: All tests PASS

- [ ] **Step 6: Run full test suite to check for regressions**

Run: `poetry run pytest -x -q --timeout=30 -m "not slow" 2>&1 | tail -10`
Expected: All existing + new tests pass

- [ ] **Step 7: Commit**

```bash
git add app/api/v2/endpoints/aeroplane/flight_envelope.py app/api/v2/endpoints/aeroplane/__init__.py app/tests/test_flight_envelope_endpoints.py
git commit -m "feat(gh-422): add flight envelope REST endpoints"
```

---

## Task 6: MCP Tools

**Files:**
- Modify: `app/mcp_server.py`

- [ ] **Step 1: Add MCP tools to mcp_server.py**

Locate the section where operating point tools are registered (near `generate_default_operating_point_set_tool`). Add nearby:

```python
@mcp_tool(
    name="get_flight_envelope",
    description="Get the cached flight envelope (V-n diagram, KPIs) for an aircraft. Returns 404 if not yet computed.",
)
async def get_flight_envelope_tool(aircraft_id: UUID4) -> Any:
    from app.api.v2.endpoints.aeroplane.flight_envelope import get_flight_envelope

    return await _call_endpoint(get_flight_envelope, aeroplane_id=aircraft_id)


@mcp_tool(
    name="compute_flight_envelope",
    description="Compute or recompute the flight envelope for an aircraft. Returns V-n curves, performance KPIs, and operating point markers.",
)
async def compute_flight_envelope_tool(aircraft_id: UUID4) -> Any:
    from app.api.v2.endpoints.aeroplane.flight_envelope import (
        compute_flight_envelope_endpoint,
    )

    return await _call_endpoint(compute_flight_envelope_endpoint, aeroplane_id=aircraft_id)
```

- [ ] **Step 2: Run existing MCP-related tests to check no regressions**

Run: `poetry run pytest app/tests/ -k "mcp" -v --timeout=30`
Expected: All existing MCP tests still pass

- [ ] **Step 3: Commit**

```bash
git add app/mcp_server.py
git commit -m "feat(gh-422): register flight envelope MCP tools"
```

---

## Task 7: Frontend Hook — useFlightEnvelope

**Files:**
- Create: `frontend/hooks/useFlightEnvelope.ts`
- Create: `frontend/__tests__/useFlightEnvelope.test.ts`

- [ ] **Step 1: Write failing hook test**

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useFlightEnvelope } from "@/hooks/useFlightEnvelope";

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe("useFlightEnvelope", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it("returns null when no aeroplaneId", () => {
    const { result } = renderHook(() => useFlightEnvelope(null));
    expect(result.current.data).toBeNull();
    expect(result.current.isLoading).toBe(false);
  });

  it("fetches envelope on mount", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        id: 1,
        vn_curve: { positive: [], negative: [], dive_speed_mps: 42, stall_speed_mps: 8.5 },
        kpis: [],
        operating_points: [],
        assumptions_snapshot: {},
        computed_at: "2026-05-07T00:00:00Z",
      }),
    });

    const { result } = renderHook(() => useFlightEnvelope("abc-123"));
    await waitFor(() => expect(result.current.data).not.toBeNull());
    expect(result.current.data?.vn_curve.stall_speed_mps).toBe(8.5);
  });

  it("compute triggers POST then refreshes", async () => {
    mockFetch
      .mockResolvedValueOnce({ ok: true, json: async () => null, status: 404 })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          id: 1,
          vn_curve: { positive: [], negative: [], dive_speed_mps: 42, stall_speed_mps: 9 },
          kpis: [],
          operating_points: [],
          assumptions_snapshot: {},
          computed_at: "2026-05-07T00:00:00Z",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          id: 1,
          vn_curve: { positive: [], negative: [], dive_speed_mps: 42, stall_speed_mps: 9 },
          kpis: [],
          operating_points: [],
          assumptions_snapshot: {},
          computed_at: "2026-05-07T00:00:00Z",
        }),
      });

    const { result } = renderHook(() => useFlightEnvelope("abc-123"));

    await act(async () => {
      await result.current.compute();
    });

    await waitFor(() => expect(result.current.data?.vn_curve.stall_speed_mps).toBe(9));
  });
});
```

- [ ] **Step 2: Run test — expect import failure**

Run: `cd frontend && npm run test:unit -- --reporter verbose useFlightEnvelope`
Expected: FAIL — module not found

- [ ] **Step 3: Implement hook**

```typescript
"use client";

import { useState, useCallback, useEffect } from "react";
import { API_BASE } from "@/lib/fetcher";

export interface VnPoint {
  velocity_mps: number;
  load_factor: number;
}

export interface VnCurve {
  positive: VnPoint[];
  negative: VnPoint[];
  dive_speed_mps: number;
  stall_speed_mps: number;
}

export interface PerformanceKPI {
  label: string;
  display_name: string;
  value: number;
  unit: string;
  source_op_id: number | null;
  confidence: "trimmed" | "estimated" | "limit";
}

export interface VnMarker {
  op_id: number;
  name: string;
  velocity_mps: number;
  load_factor: number;
  status: string;
  label: string;
}

export interface FlightEnvelopeData {
  id: number;
  aeroplane_id: number;
  vn_curve: VnCurve;
  kpis: PerformanceKPI[];
  operating_points: VnMarker[];
  assumptions_snapshot: Record<string, number>;
  computed_at: string;
}

export interface UseFlightEnvelopeReturn {
  data: FlightEnvelopeData | null;
  isLoading: boolean;
  isComputing: boolean;
  error: string | null;
  compute: () => Promise<void>;
  refresh: () => Promise<void>;
}

export function useFlightEnvelope(
  aeroplaneId: string | null,
): UseFlightEnvelopeReturn {
  const [data, setData] = useState<FlightEnvelopeData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isComputing, setIsComputing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchEnvelope = useCallback(async () => {
    if (!aeroplaneId) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/flight-envelope`,
      );
      if (res.status === 404) {
        setData(null);
        return;
      }
      if (!res.ok) throw new Error(`Failed to fetch envelope: ${res.status}`);
      setData(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setIsLoading(false);
    }
  }, [aeroplaneId]);

  const compute = useCallback(async () => {
    if (!aeroplaneId) return;
    setIsComputing(true);
    setError(null);
    try {
      const res = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/flight-envelope/compute`,
        { method: "POST" },
      );
      if (!res.ok) {
        const body = await res.text();
        throw new Error(`Compute failed: ${res.status} ${body}`);
      }
      setData(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setIsComputing(false);
    }
  }, [aeroplaneId]);

  useEffect(() => {
    fetchEnvelope();
  }, [fetchEnvelope]);

  return { data, isLoading, isComputing, error, compute, refresh: fetchEnvelope };
}
```

- [ ] **Step 4: Run hook tests — expect PASS**

Run: `cd frontend && npm run test:unit -- --reporter verbose useFlightEnvelope`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/hooks/useFlightEnvelope.ts frontend/__tests__/useFlightEnvelope.test.ts
git commit -m "feat(gh-422): add useFlightEnvelope hook with tests"
```

---

## Task 8: Frontend Components — EnvelopePanel, PerformanceOverview, VnDiagram

**Files:**
- Create: `frontend/components/workbench/EnvelopePanel.tsx`
- Create: `frontend/components/workbench/PerformanceOverview.tsx`
- Create: `frontend/components/workbench/VnDiagram.tsx`
- Modify: `frontend/components/workbench/AnalysisViewerPanel.tsx` (add Envelope tab)
- Modify: `frontend/app/workbench/analysis/page.tsx` (wire hook)

- [ ] **Step 1: Create PerformanceOverview component**

```tsx
"use client";

import type { PerformanceKPI } from "@/hooks/useFlightEnvelope";

const CONFIDENCE_COLORS: Record<string, string> = {
  trimmed: "text-green-400 bg-green-900/30",
  estimated: "text-yellow-400 bg-yellow-900/30",
  limit: "text-red-400 bg-red-900/30",
};

interface Props {
  readonly kpis: PerformanceKPI[];
}

export function PerformanceOverview({ kpis }: Props) {
  if (kpis.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-muted-foreground text-[13px]">
        No performance data available. Compute the envelope first.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 p-4">
      {kpis.map((kpi) => (
        <div
          key={kpi.label}
          className="rounded-lg border border-border bg-card p-4 flex flex-col gap-1"
        >
          <span className="text-[11px] uppercase tracking-wider text-muted-foreground">
            {kpi.display_name}
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-mono font-semibold text-foreground">
              {kpi.value.toFixed(1)}
            </span>
            <span className="text-[13px] text-muted-foreground">{kpi.unit}</span>
          </div>
          <span
            className={`text-[11px] px-1.5 py-0.5 rounded w-fit ${CONFIDENCE_COLORS[kpi.confidence] ?? ""}`}
          >
            {kpi.confidence}
          </span>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Create VnDiagram component**

```tsx
"use client";

import { useEffect, useRef } from "react";
import type { VnCurve, VnMarker } from "@/hooks/useFlightEnvelope";

const MARKER_SYMBOLS: Record<string, string> = {
  TRIMMED: "circle",
  NOT_TRIMMED: "circle-open",
  LIMIT_REACHED: "diamond",
};

interface Props {
  readonly curve: VnCurve;
  readonly markers: VnMarker[];
}

export function VnDiagram({ curve, markers }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    let cancelled = false;

    (async () => {
      const Plotly = await import("plotly.js-gl3d-dist-min");
      if (cancelled || !containerRef.current) return;

      const posV = curve.positive.map((p) => p.velocity_mps);
      const posN = curve.positive.map((p) => p.load_factor);
      const negV = curve.negative.map((p) => p.velocity_mps);
      const negN = curve.negative.map((p) => p.load_factor);

      const traces: Plotly.Data[] = [
        {
          x: posV,
          y: posN,
          mode: "lines",
          name: "Positive g",
          line: { color: "#FF8400", width: 2 },
        },
        {
          x: negV,
          y: negN,
          mode: "lines",
          name: "Negative g",
          line: { color: "#FF8400", width: 2, dash: "dash" },
        },
        {
          x: [curve.dive_speed_mps, curve.dive_speed_mps],
          y: [negN[negN.length - 1] ?? -1, posN[posN.length - 1] ?? 3],
          mode: "lines",
          name: "V_dive",
          line: { color: "#666", width: 1, dash: "dot" },
        },
      ];

      if (markers.length > 0) {
        traces.push({
          x: markers.map((m) => m.velocity_mps),
          y: markers.map((m) => m.load_factor),
          mode: "markers+text",
          name: "Operating Points",
          text: markers.map((m) => m.name),
          textposition: "top center",
          textfont: { size: 10, color: "#aaa" },
          marker: {
            size: 10,
            color: markers.map((m) =>
              m.status === "TRIMMED" ? "#4ade80" : m.status === "LIMIT_REACHED" ? "#f87171" : "#facc15",
            ),
            symbol: markers.map((m) => MARKER_SYMBOLS[m.status] ?? "circle"),
          },
        });
      }

      const layout: Partial<Plotly.Layout> = {
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        font: { color: "#ccc", family: "JetBrains Mono, monospace" },
        xaxis: {
          title: "Velocity (m/s)",
          gridcolor: "#333",
          zerolinecolor: "#555",
        },
        yaxis: {
          title: "Load Factor (g)",
          gridcolor: "#333",
          zerolinecolor: "#555",
        },
        margin: { t: 30, r: 20, b: 50, l: 60 },
        showlegend: true,
        legend: { x: 0.01, y: 0.99, bgcolor: "rgba(0,0,0,0.5)" },
      };

      Plotly.newPlot(containerRef.current, traces, layout, {
        responsive: true,
        displayModeBar: false,
      });
    })();

    return () => {
      cancelled = true;
      if (containerRef.current) {
        import("plotly.js-gl3d-dist-min").then((Plotly) => {
          if (containerRef.current) Plotly.purge(containerRef.current);
        });
      }
    };
  }, [curve, markers]);

  return <div ref={containerRef} className="w-full h-full min-h-[400px]" />;
}
```

- [ ] **Step 3: Create EnvelopePanel container**

```tsx
"use client";

import { useState } from "react";
import type { FlightEnvelopeData } from "@/hooks/useFlightEnvelope";
import { PerformanceOverview } from "./PerformanceOverview";
import { VnDiagram } from "./VnDiagram";

type View = "performance" | "vn-diagram";

interface Props {
  readonly envelope: FlightEnvelopeData | null;
  readonly isComputing: boolean;
  readonly error: string | null;
  readonly onCompute: () => void;
}

export function EnvelopePanel({ envelope, isComputing, error, onCompute }: Props) {
  const [view, setView] = useState<View>("performance");

  return (
    <div className="flex h-full flex-col">
      {/* Toolbar */}
      <div className="flex items-center gap-3 border-b border-border px-4 py-2">
        <div className="flex rounded-md border border-border overflow-hidden text-[12px]">
          <button
            onClick={() => setView("performance")}
            className={`px-3 py-1 ${view === "performance" ? "bg-[#FF8400] text-white" : "bg-card text-muted-foreground hover:bg-muted"}`}
          >
            Performance
          </button>
          <button
            onClick={() => setView("vn-diagram")}
            className={`px-3 py-1 ${view === "vn-diagram" ? "bg-[#FF8400] text-white" : "bg-card text-muted-foreground hover:bg-muted"}`}
          >
            V-n Diagram
          </button>
        </div>
        <button
          onClick={onCompute}
          disabled={isComputing}
          className="ml-auto rounded-md bg-[#FF8400] px-3 py-1 text-[12px] font-medium text-white hover:bg-[#e67600] disabled:opacity-50"
        >
          {isComputing ? "Computing..." : "Compute Envelope"}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="mx-4 mt-2 rounded border border-red-800 bg-red-900/20 px-3 py-2 text-[12px] text-red-400">
          {error}
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {!envelope ? (
          <div className="flex items-center justify-center h-full text-muted-foreground text-[13px]">
            No envelope data. Click &quot;Compute Envelope&quot; to generate.
          </div>
        ) : view === "performance" ? (
          <PerformanceOverview kpis={envelope.kpis} />
        ) : (
          <VnDiagram curve={envelope.vn_curve} markers={envelope.operating_points} />
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Add Envelope tab to AnalysisViewerPanel**

In `frontend/components/workbench/AnalysisViewerPanel.tsx`:

1. Add `"Envelope"` to the TABS array:
```typescript
const TABS = ["Assumptions", "Polar", "Trefftz Plane", "Streamlines", "Envelope"] as const;
```

2. Add props for envelope data:
```typescript
interface Props {
  // ... existing props
  readonly envelope: FlightEnvelopeData | null;
  readonly isComputingEnvelope: boolean;
  readonly envelopeError: string | null;
  readonly onComputeEnvelope: () => void;
}
```

3. Render `EnvelopePanel` when `activeTab === "Envelope"`:
```tsx
{activeTab === "Envelope" && (
  <EnvelopePanel
    envelope={envelope}
    isComputing={isComputingEnvelope}
    error={envelopeError}
    onCompute={onComputeEnvelope}
  />
)}
```

- [ ] **Step 5: Wire hook in analysis page**

In `frontend/app/workbench/analysis/page.tsx`:

1. Import the hook:
```typescript
import { useFlightEnvelope } from "@/hooks/useFlightEnvelope";
```

2. Call the hook:
```typescript
const envelope = useFlightEnvelope(aeroplaneId);
```

3. Pass envelope props to `AnalysisViewerPanel`:
```tsx
<AnalysisViewerPanel
  // ... existing props
  envelope={envelope.data}
  isComputingEnvelope={envelope.isComputing}
  envelopeError={envelope.error}
  onComputeEnvelope={envelope.compute}
/>
```

- [ ] **Step 6: Run frontend unit tests**

Run: `cd frontend && npm run test:unit`
Expected: All tests pass including the new hook test

- [ ] **Step 7: Run frontend lint + type check**

Run: `cd frontend && npm run lint`
Expected: No errors

- [ ] **Step 8: Commit**

```bash
git add frontend/components/workbench/EnvelopePanel.tsx frontend/components/workbench/PerformanceOverview.tsx frontend/components/workbench/VnDiagram.tsx frontend/components/workbench/AnalysisViewerPanel.tsx frontend/app/workbench/analysis/page.tsx
git commit -m "feat(gh-422): add Envelope tab with KPI cards and V-n diagram"
```

---

## Task 9: Full Backend Test Suite Verification

**Files:** None new — verification only

- [ ] **Step 1: Run full backend tests**

Run: `poetry run pytest -x -q --timeout=60 -m "not slow"`
Expected: All tests pass, no regressions

- [ ] **Step 2: Run ruff linting**

Run: `poetry run ruff check app/schemas/flight_envelope.py app/models/flight_envelope_model.py app/services/flight_envelope_service.py app/api/v2/endpoints/aeroplane/flight_envelope.py`
Expected: No lint errors

- [ ] **Step 3: Run ruff format**

Run: `poetry run ruff format app/schemas/flight_envelope.py app/models/flight_envelope_model.py app/services/flight_envelope_service.py app/api/v2/endpoints/aeroplane/flight_envelope.py`
Expected: Files formatted (if needed, commit formatting)

- [ ] **Step 4: Run frontend tests**

Run: `cd frontend && npm run test:unit`
Expected: All tests pass

- [ ] **Step 5: Final commit if formatting changed anything**

```bash
git add -u
git commit -m "chore(gh-422): lint and format flight envelope code"
```
