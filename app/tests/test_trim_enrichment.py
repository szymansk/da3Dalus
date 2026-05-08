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
