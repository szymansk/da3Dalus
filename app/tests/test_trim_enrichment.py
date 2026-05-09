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
    AeroBuildupTrimResult,
    AVLTrimResult,
    ControlEffectiveness,
    DeflectionReserve,
    DesignWarning,
    MixerValues,
    OperatingPointStatus,
    StabilityClassification,
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

    def test_new_fields_have_defaults(self):
        """New enrichment fields (effectiveness, stability_classification, etc.)
        must default so existing persisted JSON does not break on load."""
        e = TrimEnrichment(
            analysis_goal="Test backward compat",
            trim_method="opti",
        )
        assert e.effectiveness == {}
        assert e.stability_classification is None
        assert e.mixer_values == {}
        assert e.result_summary == ""

    def test_full_enrichment_with_all_new_fields(self):
        e = TrimEnrichment(
            analysis_goal="cruise",
            trim_method="avl",
            trim_score=0.01,
            trim_residuals={"cm": 0.0},
            deflection_reserves={},
            design_warnings=[],
            effectiveness={
                "[elevator]Elev": ControlEffectiveness(
                    derivative=-0.012, coefficient="Cm", surface="[elevator]Elev"
                )
            },
            stability_classification=StabilityClassification(
                is_statically_stable=True,
                is_directionally_stable=True,
                is_laterally_stable=True,
                static_margin=0.15,
                overall_class="stable",
            ),
            mixer_values={
                "elevon_mixer": MixerValues(
                    symmetric_offset=3.0, differential_throw=2.0, role="elevon"
                )
            },
            result_summary="Drag-minimal trim at alpha=2.9deg",
        )
        assert e.effectiveness["[elevator]Elev"].coefficient == "Cm"
        assert e.stability_classification.is_statically_stable is True
        assert e.mixer_values["elevon_mixer"].role == "elevon"
        assert "alpha" in e.result_summary


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(
        bind=engine, autocommit=False, autoflush=False, class_=Session
    )
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
# Enrichment engine tests
# ---------------------------------------------------------------------------

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.trim_enrichment_service import (
    ANALYSIS_GOALS,
    build_deflection_limits_from_schema,
    classify_stability,
    compute_control_effectiveness,
    compute_enrichment,
    decompose_dual_role,
    generate_result_summary,
)
from app.services.operating_point_generator_service import TrimmedPoint


class TestAnalysisGoals:
    def test_all_auto_generated_ops_have_goals(self):
        expected_names = {
            "stall_near_clean",
            "takeoff_climb",
            "cruise",
            "loiter_endurance",
            "max_level_speed",
            "approach_landing",
            "turn_n2",
            "dutch_role_start",
            "best_angle_climb_vx",
            "best_rate_climb_vy",
            "max_range",
            "stall_with_flaps",
        }
        assert expected_names <= set(ANALYSIS_GOALS.keys())

    def test_unknown_name_not_in_goals(self):
        assert "custom_op_xyz" not in ANALYSIS_GOALS


class TestBuildDeflectionLimitsFromSchema:
    """Tests for the schema-based deflection limits extraction."""

    def test_extracts_ted_limits(self):
        """Extracts positive/negative deflection from TED schema."""
        ted = SimpleNamespace(
            name="[elevator]Elevator",
            positive_deflection_deg=30.0,
            negative_deflection_deg=20.0,
        )
        xsec = SimpleNamespace(trailing_edge_device=ted)
        wing = SimpleNamespace(x_secs=[xsec, SimpleNamespace(trailing_edge_device=None)])
        schema = SimpleNamespace(wings={"main": wing})

        limits = build_deflection_limits_from_schema(schema)
        assert "[elevator]Elevator" in limits
        assert limits["[elevator]Elevator"] == (30.0, 20.0)

    def test_fallback_to_defaults(self):
        """Falls back to 25.0 when TED does not specify limits."""
        ted = SimpleNamespace(
            name="[aileron]Aileron",
            positive_deflection_deg=None,
            negative_deflection_deg=None,
        )
        xsec = SimpleNamespace(trailing_edge_device=ted)
        wing = SimpleNamespace(x_secs=[xsec, SimpleNamespace(trailing_edge_device=None)])
        schema = SimpleNamespace(wings={"main": wing})

        limits = build_deflection_limits_from_schema(schema)
        assert limits["[aileron]Aileron"] == (25.0, 25.0)

    def test_empty_schema(self):
        """Returns empty dict for schema with no wings."""
        schema = SimpleNamespace(wings=None)
        assert build_deflection_limits_from_schema(schema) == {}

    def test_none_schema(self):
        assert build_deflection_limits_from_schema(None) == {}

    def test_dict_wings(self):
        """Handles OrderedDict wings from AeroplaneSchema."""
        ted1 = SimpleNamespace(
            name="[elevator]Elev", positive_deflection_deg=25.0, negative_deflection_deg=25.0
        )
        ted2 = SimpleNamespace(
            name="[rudder]Rudder", positive_deflection_deg=30.0, negative_deflection_deg=30.0
        )
        wing1 = SimpleNamespace(
            x_secs=[
                SimpleNamespace(trailing_edge_device=ted1),
                SimpleNamespace(trailing_edge_device=None),
            ]
        )
        wing2 = SimpleNamespace(
            x_secs=[
                SimpleNamespace(trailing_edge_device=ted2),
                SimpleNamespace(trailing_edge_device=None),
            ]
        )
        schema = SimpleNamespace(wings={"main": wing1, "vtail": wing2})

        limits = build_deflection_limits_from_schema(schema)
        assert len(limits) == 2
        assert "[elevator]Elev" in limits
        assert "[rudder]Rudder" in limits


class TestComputeEnrichment:
    def test_basic_enrichment(self):
        controls = {"[elevator]Elevator": -5.0}
        limits = {"[elevator]Elevator": (25.0, 25.0)}
        enrichment = compute_enrichment(
            controls=controls,
            limits=limits,
            trim_method="opti",
            trim_score=0.02,
            trim_residuals={"cm": 0.001, "cy": 0.0},
            op_name="cruise",
            alpha_deg=2.86,
        )
        assert enrichment.analysis_goal == ANALYSIS_GOALS["cruise"]
        assert enrichment.trim_method == "opti"
        assert enrichment.trim_score == 0.02
        reserve = enrichment.deflection_reserves["[elevator]Elevator"]
        assert reserve.deflection_deg == -5.0
        assert reserve.usage_fraction == pytest.approx(0.2)

    def test_user_defined_op_gets_default_goal(self):
        enrichment = compute_enrichment(
            controls={},
            limits={},
            trim_method="opti",
            trim_score=0.01,
            trim_residuals={},
            op_name="my_custom_point",
            alpha_deg=1.72,
        )
        assert enrichment.analysis_goal == "User-defined trim point"

    def test_high_authority_generates_warning(self):
        controls = {"[elevator]Elevator": -22.0}
        limits = {"[elevator]Elevator": (25.0, 25.0)}
        enrichment = compute_enrichment(
            controls=controls,
            limits=limits,
            trim_method="opti",
            trim_score=0.03,
            trim_residuals={"cm": 0.002},
            op_name="stall_near_clean",
            alpha_deg=11.5,
        )
        reserve = enrichment.deflection_reserves["[elevator]Elevator"]
        assert reserve.usage_fraction == pytest.approx(22.0 / 25.0)
        warning_levels = [w.level for w in enrichment.design_warnings]
        assert "warning" in warning_levels

    def test_critical_authority_generates_critical_warning(self):
        controls = {"[elevator]Elevator": -24.5}
        limits = {"[elevator]Elevator": (25.0, 25.0)}
        enrichment = compute_enrichment(
            controls=controls,
            limits=limits,
            trim_method="opti",
            trim_score=0.03,
            trim_residuals={},
            op_name="stall_near_clean",
            alpha_deg=11.5,
        )
        warning_levels = [w.level for w in enrichment.design_warnings]
        assert "critical" in warning_levels

    def test_poor_trim_quality_generates_warning(self):
        enrichment = compute_enrichment(
            controls={},
            limits={},
            trim_method="opti",
            trim_score=0.6,
            trim_residuals={"cm": 0.3},
            op_name="cruise",
            alpha_deg=2.86,
        )
        categories = [w.category for w in enrichment.design_warnings]
        assert "trim_quality" in categories
        assert any(w.level == "critical" for w in enrichment.design_warnings)

    def test_enrichment_backward_compatible(self):
        """Enrichment without stability_derivatives does not crash."""
        enrichment = compute_enrichment(
            controls={"[elevator]Elev": -3.0},
            limits={"[elevator]Elev": (25.0, 25.0)},
            trim_method="opti",
            trim_score=0.01,
            trim_residuals={},
            op_name="cruise",
            alpha_deg=3.0,
        )
        assert enrichment.stability_classification is None
        assert enrichment.effectiveness == {}
        assert enrichment.mixer_values == {}
        assert enrichment.result_summary != ""

    def test_full_enrichment_with_all_fields(self):
        controls = {"[elevator]Elev": -5.0, "[aileron]Left Ail": 3.0}
        limits = {"[elevator]Elev": (25.0, 25.0), "[aileron]Left Ail": (20.0, 20.0)}
        derivs = {"Cm_a": -0.5, "CL_a": 4.0, "Cn_b": 0.02, "Cl_b": -0.01}
        aero = {"CL": 0.45, "CD": 0.025}
        enrichment = compute_enrichment(
            controls=controls,
            limits=limits,
            trim_method="avl",
            trim_score=None,
            trim_residuals={},
            op_name="cruise",
            alpha_deg=3.0,
            stability_derivatives=derivs,
            aero_coefficients=aero,
        )
        assert enrichment.stability_classification is not None
        assert enrichment.stability_classification.overall_class == "stable"
        assert "[elevator]Elev" in enrichment.effectiveness
        assert "CL=0.450" in enrichment.result_summary


# ---------------------------------------------------------------------------
# Stability classification tests
# ---------------------------------------------------------------------------


class TestStabilityClassification:
    def test_stable_aircraft(self):
        sc = classify_stability({"Cm_a": -0.5, "Cn_b": 0.02, "Cl_b": -0.01, "CL_a": 4.0})
        assert sc.is_statically_stable is True
        assert sc.is_directionally_stable is True
        assert sc.is_laterally_stable is True
        assert sc.overall_class == "stable"

    def test_unstable_aircraft(self):
        sc = classify_stability({"Cm_a": 0.3, "Cn_b": 0.02, "Cl_b": -0.01, "CL_a": 4.0})
        assert sc.is_statically_stable is False
        assert sc.overall_class == "unstable"

    def test_neutral_aircraft(self):
        """Cm_a < 0, Cn_b > 0, but Cl_b > 0 (laterally unstable) -> neutral."""
        sc = classify_stability({"Cm_a": -0.5, "Cn_b": 0.02, "Cl_b": 0.01, "CL_a": 4.0})
        assert sc.is_statically_stable is True
        assert sc.is_directionally_stable is True
        assert sc.is_laterally_stable is False
        assert sc.overall_class == "neutral"

    def test_static_margin_computed(self):
        sc = classify_stability({"Cm_a": -2.0, "CL_a": 4.0, "Cn_b": 0.01, "Cl_b": -0.01})
        assert sc.static_margin is not None
        assert sc.static_margin == pytest.approx(0.5)

    def test_zero_cl_a_no_margin(self):
        sc = classify_stability({"Cm_a": -0.5, "CL_a": 0.0, "Cn_b": 0.01, "Cl_b": -0.01})
        assert sc.static_margin is None


# ---------------------------------------------------------------------------
# Control effectiveness tests
# ---------------------------------------------------------------------------


class TestControlEffectiveness:
    def test_elevator_effectiveness(self):
        derivs = {"Cm_a": -0.5, "CL_a": 4.0}
        controls = {"[elevator]Elev": -3.0}
        eff = compute_control_effectiveness(derivs, controls)
        assert "[elevator]Elev" in eff
        assert eff["[elevator]Elev"].coefficient == "Cm"
        assert eff["[elevator]Elev"].derivative == pytest.approx(-0.5)

    def test_unknown_role_skipped(self):
        derivs = {"Cm_a": -0.5}
        controls = {"[spoiler]Spoiler": 5.0}
        eff = compute_control_effectiveness(derivs, controls)
        assert len(eff) == 0

    def test_no_derivatives_empty_result(self):
        eff = compute_control_effectiveness({}, {"[elevator]Elev": -3.0})
        assert len(eff) == 0


# ---------------------------------------------------------------------------
# Dual-role decomposition tests
# ---------------------------------------------------------------------------


class TestDualRoleDecomposition:
    def test_paired_elevons(self):
        controls = {
            "[elevon]Left Elevon": 5.0,
            "[elevon]Right Elevon": 3.0,
        }
        mixer = decompose_dual_role(controls)
        assert "elevon_mixer" in mixer
        assert mixer["elevon_mixer"].symmetric_offset == pytest.approx(4.0)
        assert mixer["elevon_mixer"].differential_throw == pytest.approx(1.0)
        assert mixer["elevon_mixer"].role == "elevon"

    def test_single_dual_role(self):
        controls = {"[elevon]Single Elevon": 7.0}
        mixer = decompose_dual_role(controls)
        assert "[elevon]Single Elevon" in mixer
        assert mixer["[elevon]Single Elevon"].symmetric_offset == pytest.approx(7.0)
        assert mixer["[elevon]Single Elevon"].differential_throw == pytest.approx(0.0)

    def test_no_dual_role_empty(self):
        controls = {
            "[elevator]Elev": -3.0,
            "[aileron]Ail": 5.0,
            "[rudder]Rud": 2.0,
        }
        mixer = decompose_dual_role(controls)
        assert len(mixer) == 0


# ---------------------------------------------------------------------------
# Result summary tests
# ---------------------------------------------------------------------------


class TestResultSummary:
    def test_cruise_summary_includes_alpha(self):
        summary = generate_result_summary(
            op_name="cruise",
            alpha_deg=3.5,
            controls={},
            deflection_reserves={},
            stability_class=None,
        )
        assert "alpha=3.5deg" in summary

    def test_unknown_op_gets_generic_summary(self):
        summary = generate_result_summary(
            op_name="custom_xyz",
            alpha_deg=5.0,
            controls={},
            deflection_reserves={},
            stability_class=None,
        )
        assert "Trimmed at" in summary
        assert "alpha=5.0deg" in summary

    def test_summary_includes_reserve(self):
        reserves = {
            "[elevator]Elev": DeflectionReserve(
                deflection_deg=-5.0,
                max_pos_deg=25.0,
                max_neg_deg=25.0,
                usage_fraction=0.2,
            )
        }
        summary = generate_result_summary(
            op_name="cruise",
            alpha_deg=3.0,
            controls={"[elevator]Elev": -5.0},
            deflection_reserves=reserves,
            stability_class=None,
        )
        assert "elevator reserve" in summary


# ---------------------------------------------------------------------------
# Static margin warning tests
# ---------------------------------------------------------------------------


class TestStaticMarginWarnings:
    def test_low_margin_warning(self):
        enrichment = compute_enrichment(
            controls={"[elevator]Elev": -3.0},
            limits={"[elevator]Elev": (25.0, 25.0)},
            trim_method="avl",
            trim_score=None,
            trim_residuals={},
            op_name="cruise",
            alpha_deg=3.0,
            stability_derivatives={"Cm_a": -0.12, "CL_a": 4.0, "Cn_b": 0.01, "Cl_b": -0.01},
        )
        # sm = 0.12/4.0 = 0.03 < 0.05
        stability_warnings = [w for w in enrichment.design_warnings if w.category == "stability"]
        assert len(stability_warnings) == 1
        assert "Marginal" in stability_warnings[0].message

    def test_high_margin_warning(self):
        enrichment = compute_enrichment(
            controls={"[elevator]Elev": -3.0},
            limits={"[elevator]Elev": (25.0, 25.0)},
            trim_method="avl",
            trim_score=None,
            trim_residuals={},
            op_name="cruise",
            alpha_deg=3.0,
            stability_derivatives={"Cm_a": -1.4, "CL_a": 4.0, "Cn_b": 0.01, "Cl_b": -0.01},
        )
        # sm = 1.4/4.0 = 0.35 > 0.30
        stability_warnings = [w for w in enrichment.design_warnings if w.category == "stability"]
        assert len(stability_warnings) == 1
        assert "nose-heavy" in stability_warnings[0].message

    def test_negative_margin_critical(self):
        enrichment = compute_enrichment(
            controls={"[elevator]Elev": -3.0},
            limits={"[elevator]Elev": (25.0, 25.0)},
            trim_method="avl",
            trim_score=None,
            trim_residuals={},
            op_name="cruise",
            alpha_deg=3.0,
            stability_derivatives={"Cm_a": 0.08, "CL_a": 4.0, "Cn_b": 0.01, "Cl_b": -0.01},
        )
        # sm = -0.08/4.0 = -0.02 < 0 -> critical
        stability_warnings = [w for w in enrichment.design_warnings if w.category == "stability"]
        assert len(stability_warnings) == 1
        assert stability_warnings[0].level == "critical"
        assert "Negative" in stability_warnings[0].message

    def test_normal_margin_no_warning(self):
        enrichment = compute_enrichment(
            controls={"[elevator]Elev": -3.0},
            limits={"[elevator]Elev": (25.0, 25.0)},
            trim_method="avl",
            trim_score=None,
            trim_residuals={},
            op_name="cruise",
            alpha_deg=3.0,
            stability_derivatives={"Cm_a": -0.6, "CL_a": 4.0, "Cn_b": 0.01, "Cl_b": -0.01},
        )
        # sm = 0.6/4.0 = 0.15
        stability_warnings = [w for w in enrichment.design_warnings if w.category == "stability"]
        assert len(stability_warnings) == 0


# ---------------------------------------------------------------------------
# AVL/AeroBuildup trim_enrichment field tests
# ---------------------------------------------------------------------------


class TestAVLTrimEnrichmentField:
    def test_avl_result_has_trim_enrichment_field(self):
        result = AVLTrimResult(
            converged=True,
            trimmed_deflections={"[elevator]Elev": -3.0},
            aero_coefficients={"CL": 0.5},
            stability_derivatives={"Cm_a": -0.5},
            trim_enrichment={"analysis_goal": "test", "trim_method": "avl"},
        )
        assert result.trim_enrichment is not None
        assert result.trim_enrichment["trim_method"] == "avl"

    def test_avl_result_defaults_to_none(self):
        result = AVLTrimResult(converged=False)
        assert result.trim_enrichment is None


class TestAeroBuildupTrimEnrichmentField:
    def test_aerobuildup_result_has_trim_enrichment_field(self):
        result = AeroBuildupTrimResult(
            converged=True,
            trim_variable="[elevator]Elev",
            trimmed_deflection=-3.5,
            target_coefficient="Cm",
            achieved_value=0.0001,
            trim_enrichment={"analysis_goal": "test", "trim_method": "aerobuildup"},
        )
        assert result.trim_enrichment is not None
        assert result.trim_enrichment["trim_method"] == "aerobuildup"

    def test_aerobuildup_result_defaults_to_none(self):
        result = AeroBuildupTrimResult(
            converged=False,
            trim_variable="elev",
            trimmed_deflection=0.0,
            target_coefficient="Cm",
            achieved_value=None,
        )
        assert result.trim_enrichment is None


# ---------------------------------------------------------------------------
# Integration tests: enrichment wired into service entry points
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
        p=0.0,
        q=0.0,
        r=0.0,
        status=OperatingPointStatus.TRIMMED,
        warnings=[],
        controls={"[elevator]Elevator": -3.0},
    )


def _mock_plane_schema_with_teds(*ted_names: str) -> SimpleNamespace:
    """Build a mock plane schema with trailing-edge devices for limit extraction."""
    xsecs = []
    for name in ted_names:
        ted = SimpleNamespace(name=name, positive_deflection_deg=25.0, negative_deflection_deg=25.0)
        xsecs.append(SimpleNamespace(trailing_edge_device=ted))
    # Add terminal xsec with no TED
    xsecs.append(SimpleNamespace(trailing_edge_device=None))
    wing = SimpleNamespace(x_secs=xsecs)
    return SimpleNamespace(wings={"main": wing})


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
            patch(
                "app.services.operating_point_generator_service.aeroplane_model_to_aeroplane_schema_async",
                return_value=_mock_plane_schema_with_teds("[elevator]Elevator", "[rudder]Rudder"),
            ),
            patch(
                "app.services.operating_point_generator_service.aeroplane_schema_to_asb_airplane_async",
                return_value=_mock_airplane_for_integration("[elevator]Elevator", "[rudder]Rudder"),
            ),
            patch(
                "app.services.operating_point_generator_service._trim_or_estimate_point",
                side_effect=_fake_trim,
            ),
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
            patch(
                "app.services.operating_point_generator_service.aeroplane_model_to_aeroplane_schema_async",
                return_value=_mock_plane_schema_with_teds("[elevator]Elevator", "[rudder]Rudder"),
            ),
            patch(
                "app.services.operating_point_generator_service.aeroplane_schema_to_asb_airplane_async",
                return_value=_mock_airplane_for_integration("[elevator]Elevator", "[rudder]Rudder"),
            ),
            patch(
                "app.services.operating_point_generator_service._trim_or_estimate_point",
                side_effect=_fake_trim,
            ),
        ):
            generate_default_set_for_aircraft(db_session, aircraft_uuid)

        persisted = (
            db_session.query(OperatingPointModel)
            .filter(OperatingPointModel.aircraft_id == aircraft.id)
            .all()
        )
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
            patch(
                "app.services.operating_point_generator_service.aeroplane_model_to_aeroplane_schema_async",
                return_value=_mock_plane_schema_with_teds("[elevator]Elevator"),
            ),
            patch(
                "app.services.operating_point_generator_service.aeroplane_schema_to_asb_airplane_async",
                return_value=_mock_airplane_for_integration("[elevator]Elevator"),
            ),
            patch(
                "app.services.operating_point_generator_service._trim_or_estimate_point",
                side_effect=_fake_trim,
            ),
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
                p=0.0,
                q=0.0,
                r=0.0,
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
            patch(
                "app.services.operating_point_generator_service.aeroplane_model_to_aeroplane_schema_async",
                return_value=_mock_plane_schema_with_teds("[elevator]Elevator", "[rudder]Rudder"),
            ),
            patch(
                "app.services.operating_point_generator_service.aeroplane_schema_to_asb_airplane_async",
                return_value=_mock_airplane_for_integration("[elevator]Elevator", "[rudder]Rudder"),
            ),
            patch(
                "app.services.operating_point_generator_service._trim_or_estimate_point",
                side_effect=_fake_trim_with_score,
            ),
        ):
            result = generate_default_set_for_aircraft(db_session, aircraft_uuid)

        first_op = result.operating_points[0]
        assert first_op.trim_enrichment is not None
        assert first_op.trim_enrichment["trim_score"] == pytest.approx(0.15)
        assert first_op.trim_enrichment["trim_residuals"]["cm"] == pytest.approx(0.08)
        warning_categories = [w["category"] for w in first_op.trim_enrichment["design_warnings"]]
        assert "trim_quality" in warning_categories
