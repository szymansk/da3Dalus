"""Tests for the flight envelope feature — schemas, model, computation, service."""

from __future__ import annotations

import math
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError as PydanticValidationError


# ────────────────────────────────────────────────────────────────────────────
# Task 1: Schema tests
# ────────────────────────────────────────────────────────────────────────────


class TestVnPoint:
    """VnPoint schema validation."""

    def test_valid_point(self):
        from app.schemas.flight_envelope import VnPoint

        p = VnPoint(velocity_mps=25.0, load_factor=2.5)
        assert p.velocity_mps == 25.0
        assert p.load_factor == 2.5

    def test_zero_velocity_accepted(self):
        from app.schemas.flight_envelope import VnPoint

        p = VnPoint(velocity_mps=0.0, load_factor=1.0)
        assert p.velocity_mps == 0.0

    def test_negative_velocity_rejected(self):
        from app.schemas.flight_envelope import VnPoint

        with pytest.raises(PydanticValidationError, match="velocity"):
            VnPoint(velocity_mps=-1.0, load_factor=1.0)


class TestVnCurve:
    """VnCurve schema validation."""

    def test_valid_curve(self):
        from app.schemas.flight_envelope import VnCurve, VnPoint

        pos = [VnPoint(velocity_mps=10.0, load_factor=1.0)]
        neg = [VnPoint(velocity_mps=10.0, load_factor=-0.5)]
        curve = VnCurve(
            positive=pos,
            negative=neg,
            dive_speed_mps=40.0,
            stall_speed_mps=8.0,
        )
        assert curve.dive_speed_mps == 40.0
        assert len(curve.positive) == 1


class TestPerformanceKPI:
    """PerformanceKPI schema validation."""

    def test_valid_kpi(self):
        from app.schemas.flight_envelope import PerformanceKPI

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

    def test_invalid_confidence_rejected(self):
        from app.schemas.flight_envelope import PerformanceKPI

        with pytest.raises(PydanticValidationError):
            PerformanceKPI(
                label="stall_speed",
                display_name="Stall Speed",
                value=8.5,
                unit="m/s",
                source_op_id=None,
                confidence="guess",
            )


class TestVnMarker:
    """VnMarker schema validation."""

    def test_valid_marker(self):
        from app.schemas.flight_envelope import VnMarker

        m = VnMarker(
            op_id=1,
            name="cruise",
            velocity_mps=20.0,
            load_factor=1.0,
            status="TRIMMED",
            label="cruise",
        )
        assert m.op_id == 1
        assert m.name == "cruise"


class TestFlightEnvelopeRead:
    """FlightEnvelopeRead schema validation."""

    def test_valid_read(self):
        from app.schemas.flight_envelope import (
            FlightEnvelopeRead,
            PerformanceKPI,
            VnCurve,
            VnMarker,
            VnPoint,
        )

        now = datetime.now(timezone.utc)
        curve = VnCurve(
            positive=[VnPoint(velocity_mps=10.0, load_factor=1.0)],
            negative=[VnPoint(velocity_mps=10.0, load_factor=-0.5)],
            dive_speed_mps=40.0,
            stall_speed_mps=8.0,
        )
        kpi = PerformanceKPI(
            label="stall_speed",
            display_name="Stall Speed",
            value=8.5,
            unit="m/s",
            source_op_id=None,
            confidence="estimated",
        )
        marker = VnMarker(
            op_id=1,
            name="cruise",
            velocity_mps=20.0,
            load_factor=1.0,
            status="TRIMMED",
            label="cruise",
        )
        envelope = FlightEnvelopeRead(
            id=1,
            aeroplane_id=42,
            vn_curve=curve,
            kpis=[kpi],
            operating_points=[marker],
            assumptions_snapshot={"mass": 1.5},
            computed_at=now,
        )
        assert envelope.aeroplane_id == 42
        assert len(envelope.kpis) == 1
        assert len(envelope.operating_points) == 1


class TestComputeEnvelopeRequest:
    """ComputeEnvelopeRequest schema validation."""

    def test_default_force_recompute(self):
        from app.schemas.flight_envelope import ComputeEnvelopeRequest

        req = ComputeEnvelopeRequest()
        assert req.force_recompute is False

    def test_force_recompute_true(self):
        from app.schemas.flight_envelope import ComputeEnvelopeRequest

        req = ComputeEnvelopeRequest(force_recompute=True)
        assert req.force_recompute is True


# ────────────────────────────────────────────────────────────────────────────
# Task 2: DB model tests
# ────────────────────────────────────────────────────────────────────────────


class TestFlightEnvelopeModel:
    """FlightEnvelopeModel ORM tests using in-memory SQLite."""

    @pytest.fixture(autouse=True)
    def _setup_db(self):
        """Create a fresh in-memory SQLite database for each test."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session, sessionmaker
        from sqlalchemy.pool import StaticPool

        from app.db.base import Base

        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        self.SessionLocal = sessionmaker(bind=engine, class_=Session)
        self.engine = engine
        yield
        Base.metadata.drop_all(bind=engine)

    def _make_aeroplane(self, session) -> int:
        """Create a minimal aeroplane and return its id."""
        import uuid as _uuid

        from app.models.aeroplanemodel import AeroplaneModel

        plane = AeroplaneModel(name="test-plane", uuid=_uuid.uuid4())
        session.add(plane)
        session.flush()
        return plane.id

    def test_create_and_read(self):
        from datetime import datetime, timezone

        from app.models.flight_envelope_model import FlightEnvelopeModel

        with self.SessionLocal() as session:
            aeroplane_id = self._make_aeroplane(session)
            now = datetime.now(timezone.utc)
            envelope = FlightEnvelopeModel(
                aeroplane_id=aeroplane_id,
                vn_curve_json={"positive": [], "negative": []},
                kpis_json=[],
                markers_json=[],
                assumptions_snapshot={"mass": 1.5},
                computed_at=now,
            )
            session.add(envelope)
            session.flush()
            session.refresh(envelope)

            assert envelope.id is not None
            assert envelope.aeroplane_id == aeroplane_id
            assert envelope.vn_curve_json == {"positive": [], "negative": []}
            # SQLite strips timezone info; compare naive timestamps
            assert envelope.computed_at.replace(tzinfo=None) == now.replace(tzinfo=None)

    def test_unique_constraint_per_aeroplane(self):
        from datetime import datetime, timezone

        from sqlalchemy.exc import IntegrityError

        from app.models.flight_envelope_model import FlightEnvelopeModel

        with self.SessionLocal() as session:
            aeroplane_id = self._make_aeroplane(session)
            now = datetime.now(timezone.utc)
            e1 = FlightEnvelopeModel(
                aeroplane_id=aeroplane_id,
                vn_curve_json={},
                kpis_json=[],
                markers_json=[],
                assumptions_snapshot={},
                computed_at=now,
            )
            session.add(e1)
            session.flush()

            e2 = FlightEnvelopeModel(
                aeroplane_id=aeroplane_id,
                vn_curve_json={},
                kpis_json=[],
                markers_json=[],
                assumptions_snapshot={},
                computed_at=now,
            )
            session.add(e2)
            with pytest.raises(IntegrityError):
                session.flush()


# ────────────────────────────────────────────────────────────────────────────
# Task 3: V-n curve computation + KPI derivation tests
# ────────────────────────────────────────────────────────────────────────────


class TestComputeVnCurve:
    """Pure computation: V-n curve generation."""

    # Reference values for a 1.5 kg aircraft, Cl_max=1.4, g_limit=3.0,
    # S=0.25 m^2, rho=1.225, v_max=28 m/s.
    MASS = 1.5
    CL_MAX = 1.4
    G_LIMIT = 3.0
    S = 0.25
    RHO = 1.225
    V_MAX = 28.0

    @property
    def expected_stall(self) -> float:
        return math.sqrt(2 * self.MASS * 9.81 / (self.RHO * self.S * self.CL_MAX))

    @property
    def expected_dive(self) -> float:
        return 1.4 * self.V_MAX

    def test_stall_speed_math(self):
        from app.services.flight_envelope_service import compute_vn_curve

        curve = compute_vn_curve(
            mass_kg=self.MASS,
            cl_max=self.CL_MAX,
            g_limit=self.G_LIMIT,
            wing_area_m2=self.S,
            rho=self.RHO,
            v_max_mps=self.V_MAX,
        )
        assert abs(curve.stall_speed_mps - self.expected_stall) < 0.01

    def test_dive_speed(self):
        from app.services.flight_envelope_service import compute_vn_curve

        curve = compute_vn_curve(
            mass_kg=self.MASS,
            cl_max=self.CL_MAX,
            g_limit=self.G_LIMIT,
            wing_area_m2=self.S,
            rho=self.RHO,
            v_max_mps=self.V_MAX,
        )
        assert abs(curve.dive_speed_mps - self.expected_dive) < 0.01

    def test_positive_boundary_capped_at_g_limit(self):
        from app.services.flight_envelope_service import compute_vn_curve

        curve = compute_vn_curve(
            mass_kg=self.MASS,
            cl_max=self.CL_MAX,
            g_limit=self.G_LIMIT,
            wing_area_m2=self.S,
            rho=self.RHO,
            v_max_mps=self.V_MAX,
        )
        for pt in curve.positive:
            assert pt.load_factor <= self.G_LIMIT + 1e-9

    def test_negative_boundary_capped(self):
        from app.services.flight_envelope_service import compute_vn_curve

        curve = compute_vn_curve(
            mass_kg=self.MASS,
            cl_max=self.CL_MAX,
            g_limit=self.G_LIMIT,
            wing_area_m2=self.S,
            rho=self.RHO,
            v_max_mps=self.V_MAX,
        )
        neg_limit = -0.4 * self.G_LIMIT
        for pt in curve.negative:
            assert pt.load_factor >= neg_limit - 1e-9

    def test_at_least_50_positive_points(self):
        from app.services.flight_envelope_service import compute_vn_curve

        curve = compute_vn_curve(
            mass_kg=self.MASS,
            cl_max=self.CL_MAX,
            g_limit=self.G_LIMIT,
            wing_area_m2=self.S,
            rho=self.RHO,
            v_max_mps=self.V_MAX,
        )
        assert len(curve.positive) >= 50

    def test_rejects_non_positive_mass(self):
        from app.services.flight_envelope_service import compute_vn_curve

        with pytest.raises(ValueError, match="positive"):
            compute_vn_curve(
                mass_kg=0, cl_max=self.CL_MAX, g_limit=self.G_LIMIT,
                wing_area_m2=self.S, v_max_mps=self.V_MAX,
            )

    def test_rejects_non_positive_wing_area(self):
        from app.services.flight_envelope_service import compute_vn_curve

        with pytest.raises(ValueError, match="positive"):
            compute_vn_curve(
                mass_kg=self.MASS, cl_max=self.CL_MAX, g_limit=self.G_LIMIT,
                wing_area_m2=-1.0, v_max_mps=self.V_MAX,
            )


class TestDerivePerformanceKPIs:
    """Pure computation: KPI derivation."""

    def test_always_returns_6_kpis(self):
        from app.services.flight_envelope_service import derive_performance_kpis

        kpis = derive_performance_kpis(
            stall_speed_mps=8.0,
            v_max_mps=28.0,
            g_limit=3.0,
            markers=[],
        )
        assert len(kpis) == 6

    def test_kpi_labels_present(self):
        from app.services.flight_envelope_service import derive_performance_kpis

        kpis = derive_performance_kpis(
            stall_speed_mps=8.0,
            v_max_mps=28.0,
            g_limit=3.0,
            markers=[],
        )
        labels = {k.label for k in kpis}
        assert labels == {
            "stall_speed",
            "best_ld_speed",
            "min_sink_speed",
            "max_speed",
            "max_load_factor",
            "dive_speed",
        }

    def test_dive_speed_kpi_value(self):
        from app.services.flight_envelope_service import derive_performance_kpis

        kpis = derive_performance_kpis(
            stall_speed_mps=8.0,
            v_max_mps=28.0,
            g_limit=3.0,
            markers=[],
        )
        dive_kpi = next(k for k in kpis if k.label == "dive_speed")
        assert abs(dive_kpi.value - 1.4 * 28.0) < 0.01

    def test_best_ld_from_marker(self):
        from app.schemas.flight_envelope import VnMarker
        from app.services.flight_envelope_service import derive_performance_kpis

        marker = VnMarker(
            op_id=10,
            name="best_ld_point",
            velocity_mps=15.0,
            load_factor=1.0,
            status="TRIMMED",
            label="best_ld",
        )
        kpis = derive_performance_kpis(
            stall_speed_mps=8.0,
            v_max_mps=28.0,
            g_limit=3.0,
            markers=[marker],
        )
        best_ld = next(k for k in kpis if k.label == "best_ld_speed")
        assert abs(best_ld.value - 15.0) < 0.01
        assert best_ld.source_op_id == 10
        assert best_ld.confidence == "trimmed"

    def test_fallback_best_ld_without_marker(self):
        from app.services.flight_envelope_service import derive_performance_kpis

        kpis = derive_performance_kpis(
            stall_speed_mps=8.0,
            v_max_mps=28.0,
            g_limit=3.0,
            markers=[],
        )
        best_ld = next(k for k in kpis if k.label == "best_ld_speed")
        assert abs(best_ld.value - 1.4 * 8.0) < 0.01
        assert best_ld.confidence == "estimated"


# ────────────────────────────────────────────────────────────────────────────
# Task 4: Full envelope service (DB integration) tests
# ────────────────────────────────────────────────────────────────────────────


class TestFullEnvelopeService:
    """Integration tests for compute_flight_envelope / get_flight_envelope.

    Heavy external dependencies (_load_assumptions, _get_wing_area_m2,
    _get_v_max, _load_operating_point_markers) are mocked so the tests
    exercise orchestration and DB upsert logic without needing real
    ASB converters or design-assumption rows.
    """

    @pytest.fixture(autouse=True)
    def _setup_db(self):
        """Fresh in-memory SQLite with all tables."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session, sessionmaker
        from sqlalchemy.pool import StaticPool

        from app.db.base import Base

        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        self.SessionLocal = sessionmaker(bind=engine, class_=Session)
        self.engine = engine
        yield
        Base.metadata.drop_all(bind=engine)

    def _make_aeroplane(self, session):
        """Create a minimal aeroplane and return the model instance."""
        import uuid as _uuid

        from app.models.aeroplanemodel import AeroplaneModel

        plane = AeroplaneModel(name="test-plane", uuid=_uuid.uuid4())
        session.add(plane)
        session.flush()
        return plane

    def _mock_patches(self):
        """Return a dict of patch targets and their return values."""
        return {
            "app.services.flight_envelope_service._load_assumptions": {
                "mass": 1.5,
                "cl_max": 1.4,
                "g_limit": 3.0,
            },
            "app.services.flight_envelope_service._get_wing_area_m2": 0.25,
            "app.services.flight_envelope_service._get_v_max": 28.0,
            "app.services.flight_envelope_service._load_operating_point_markers": [],
        }

    def test_compute_returns_envelope(self):
        from unittest.mock import patch

        from app.services.flight_envelope_service import compute_flight_envelope

        patches = self._mock_patches()
        with self.SessionLocal() as session:
            plane = self._make_aeroplane(session)
            with (
                patch(
                    "app.services.flight_envelope_service._load_assumptions",
                    return_value=patches["app.services.flight_envelope_service._load_assumptions"],
                ),
                patch(
                    "app.services.flight_envelope_service._get_wing_area_m2",
                    return_value=patches["app.services.flight_envelope_service._get_wing_area_m2"],
                ),
                patch(
                    "app.services.flight_envelope_service._get_v_max",
                    return_value=patches["app.services.flight_envelope_service._get_v_max"],
                ),
                patch(
                    "app.services.flight_envelope_service._load_operating_point_markers",
                    return_value=patches[
                        "app.services.flight_envelope_service._load_operating_point_markers"
                    ],
                ),
            ):
                result = compute_flight_envelope(session, plane.uuid)

            assert result.aeroplane_id == plane.id
            assert len(result.kpis) == 6
            assert len(result.vn_curve.positive) >= 50
            assert result.assumptions_snapshot == {"mass": 1.5, "cl_max": 1.4, "g_limit": 3.0}

    def test_compute_persists_to_db(self):
        from unittest.mock import patch

        from app.models.flight_envelope_model import FlightEnvelopeModel
        from app.services.flight_envelope_service import compute_flight_envelope

        patches = self._mock_patches()
        with self.SessionLocal() as session:
            plane = self._make_aeroplane(session)
            with (
                patch(
                    "app.services.flight_envelope_service._load_assumptions",
                    return_value=patches["app.services.flight_envelope_service._load_assumptions"],
                ),
                patch(
                    "app.services.flight_envelope_service._get_wing_area_m2",
                    return_value=patches["app.services.flight_envelope_service._get_wing_area_m2"],
                ),
                patch(
                    "app.services.flight_envelope_service._get_v_max",
                    return_value=patches["app.services.flight_envelope_service._get_v_max"],
                ),
                patch(
                    "app.services.flight_envelope_service._load_operating_point_markers",
                    return_value=patches[
                        "app.services.flight_envelope_service._load_operating_point_markers"
                    ],
                ),
            ):
                compute_flight_envelope(session, plane.uuid)

            row = (
                session.query(FlightEnvelopeModel)
                .filter(FlightEnvelopeModel.aeroplane_id == plane.id)
                .first()
            )
            assert row is not None
            assert row.aeroplane_id == plane.id

    def test_upsert_on_recompute(self):
        from unittest.mock import patch

        from app.models.flight_envelope_model import FlightEnvelopeModel
        from app.services.flight_envelope_service import compute_flight_envelope

        patches = self._mock_patches()
        with self.SessionLocal() as session:
            plane = self._make_aeroplane(session)
            with (
                patch(
                    "app.services.flight_envelope_service._load_assumptions",
                    return_value=patches["app.services.flight_envelope_service._load_assumptions"],
                ),
                patch(
                    "app.services.flight_envelope_service._get_wing_area_m2",
                    return_value=patches["app.services.flight_envelope_service._get_wing_area_m2"],
                ),
                patch(
                    "app.services.flight_envelope_service._get_v_max",
                    return_value=patches["app.services.flight_envelope_service._get_v_max"],
                ),
                patch(
                    "app.services.flight_envelope_service._load_operating_point_markers",
                    return_value=patches[
                        "app.services.flight_envelope_service._load_operating_point_markers"
                    ],
                ),
            ):
                first = compute_flight_envelope(session, plane.uuid)
                second = compute_flight_envelope(session, plane.uuid)

            # Same DB row reused (upsert, not duplicate)
            assert first.id == second.id
            count = (
                session.query(FlightEnvelopeModel)
                .filter(FlightEnvelopeModel.aeroplane_id == plane.id)
                .count()
            )
            assert count == 1

    def test_get_returns_cached(self):
        from unittest.mock import patch

        from app.services.flight_envelope_service import (
            compute_flight_envelope,
            get_flight_envelope,
        )

        patches = self._mock_patches()
        with self.SessionLocal() as session:
            plane = self._make_aeroplane(session)
            with (
                patch(
                    "app.services.flight_envelope_service._load_assumptions",
                    return_value=patches["app.services.flight_envelope_service._load_assumptions"],
                ),
                patch(
                    "app.services.flight_envelope_service._get_wing_area_m2",
                    return_value=patches["app.services.flight_envelope_service._get_wing_area_m2"],
                ),
                patch(
                    "app.services.flight_envelope_service._get_v_max",
                    return_value=patches["app.services.flight_envelope_service._get_v_max"],
                ),
                patch(
                    "app.services.flight_envelope_service._load_operating_point_markers",
                    return_value=patches[
                        "app.services.flight_envelope_service._load_operating_point_markers"
                    ],
                ),
            ):
                compute_flight_envelope(session, plane.uuid)

            cached = get_flight_envelope(session, plane.uuid)
            assert cached is not None
            assert cached.aeroplane_id == plane.id

    def test_get_returns_none_when_missing(self):
        import uuid as _uuid

        from app.services.flight_envelope_service import get_flight_envelope

        with self.SessionLocal() as session:
            plane = self._make_aeroplane(session)
            result = get_flight_envelope(session, plane.uuid)
            assert result is None
