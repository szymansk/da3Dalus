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
