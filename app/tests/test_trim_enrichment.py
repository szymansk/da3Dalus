import uuid

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.aeroplanemodel import AeroplaneModel
from app.models.analysismodels import OperatingPointModel
from app.schemas.aeroanalysisschema import (
    DeflectionReserve,
    DesignWarning,
    OperatingPointStatus,
    StoredOperatingPointCreate,
    StoredOperatingPointRead,
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
            p=0.0,
            q=0.0,
            r=0.0,
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
            p=0.0,
            q=0.0,
            r=0.0,
            xyz_ref=[0, 0, 0],
            altitude=0.0,
        )
        db_session.add(op)
        db_session.commit()
        db_session.refresh(op)

        assert op.trim_enrichment is None


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
            p=0.0,
            q=0.0,
            r=0.0,
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
            p=0.0,
            q=0.0,
            r=0.0,
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
            p=0.0,
            q=0.0,
            r=0.0,
            altitude=0.0,
            trim_enrichment={
                "analysis_goal": "Goal",
                "trim_method": "opti",
                "trim_score": None,
                "trim_residuals": {},
                "deflection_reserves": {},
                "design_warnings": [],
            },
        )
        assert op.trim_enrichment["analysis_goal"] == "Goal"


# ---------------------------------------------------------------------------
# Enrichment engine tests (Task 4)
# ---------------------------------------------------------------------------

from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from app.services.operating_point_generator_service import (
    _build_deflection_limits,
    _compute_enrichment,
    ANALYSIS_GOALS,
    TrimmedPoint,
)


def _mock_airplane_with_limits(surfaces: list[dict]) -> MagicMock:
    """Create a mock ASB airplane with control surfaces that have deflection limits."""
    airplane = MagicMock()
    xsec = MagicMock()
    controls = []
    for s in surfaces:
        cs = MagicMock()
        cs.name = s["name"]
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


# ---------------------------------------------------------------------------
# Integration tests: enrichment wired into service entry points (Task 5)
# ---------------------------------------------------------------------------


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


def _mock_airplane_for_integration(*control_names: str) -> SimpleNamespace:
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
            patch("app.services.operating_point_generator_service.aeroplane_schema_to_asb_airplane_async", return_value=_mock_airplane_for_integration("[elevator]Elevator", "[rudder]Rudder")),
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
            patch("app.services.operating_point_generator_service.aeroplane_schema_to_asb_airplane_async", return_value=_mock_airplane_for_integration("[elevator]Elevator", "[rudder]Rudder")),
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
            patch("app.services.operating_point_generator_service.aeroplane_schema_to_asb_airplane_async", return_value=_mock_airplane_for_integration("[elevator]Elevator")),
            patch("app.services.operating_point_generator_service._trim_or_estimate_point", side_effect=_fake_trim),
        ):
            result = trim_operating_point_for_aircraft(db_session, aircraft_uuid, request)

        assert result.point.trim_enrichment is not None
        assert result.point.trim_enrichment["analysis_goal"] == "User-defined trim point"

    def test_trim_score_flows_through_to_enrichment(self, db_session):
        from app.services.operating_point_generator_service import generate_default_set_for_aircraft

        def _fake_trim_with_score(*_, target, **__):
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
                trim_score=0.15,
                trim_residuals={"cm": 0.08, "cy": 0.01},
            )

        aircraft_uuid = uuid.uuid4()
        aircraft = AeroplaneModel(name="score-flow", uuid=aircraft_uuid)
        db_session.add(aircraft)
        db_session.commit()

        with (
            patch("app.services.operating_point_generator_service.aeroplane_model_to_aeroplane_schema_async", return_value=SimpleNamespace()),
            patch("app.services.operating_point_generator_service.aeroplane_schema_to_asb_airplane_async", return_value=_mock_airplane_for_integration("[elevator]Elevator", "[rudder]Rudder")),
            patch("app.services.operating_point_generator_service._trim_or_estimate_point", side_effect=_fake_trim_with_score),
        ):
            result = generate_default_set_for_aircraft(db_session, aircraft_uuid)

        first_op = result.operating_points[0]
        assert first_op.trim_enrichment is not None
        assert first_op.trim_enrichment["trim_score"] == pytest.approx(0.15)
        assert first_op.trim_enrichment["trim_residuals"]["cm"] == pytest.approx(0.08)
        warning_categories = [w["category"] for w in first_op.trim_enrichment["design_warnings"]]
        assert "trim_quality" in warning_categories
