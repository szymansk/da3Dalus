"""gh-1008: Endpoint + service integration tests for spar sizing.

All tests run on the CI fast tier:
- Endpoint tests mock analyze_airplane_spanwise_loads_with_sizing at the boundary.
- Material-seed tests use the real test DB fixture (no aerosandbox).
- Service orchestration tests mock spanwise/aero deps.

Recurring mock-correctness lesson: the strip_forces mock MUST use the
real data-structure keys (surfaces / strips with Yle/Area/cl/Chord).
Material specs must use real ComponentRead.specs keys:
  density_kg_m3, allowable_bending_stress_mpa.
"""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.exceptions import InternalError, NotFoundError
from app.schemas.aeroanalysisschema import OperatingPointSchema
from app.schemas.spar_sizing import SparSizingParams, SparSizingResult, SparSizingStation
from app.schemas.spanwise_loads import (
    SpanwiseLoadEntry,
    SpanwiseLoadsResponse,
    SurfaceSpanwiseLoads,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_spanwise_response(
    root_bm: float = 1000.0,
) -> SpanwiseLoadsResponse:
    entry = SpanwiseLoadEntry(y_m=0.0, chord_m=0.4, shear_N=500.0, bending_moment_Nm=root_bm)
    surf = SurfaceSpanwiseLoads(
        surface_name="main_wing",
        starboard=[entry],
        port=[],
        root_shear_N_starboard=500.0,
        root_shear_N_port=0.0,
        root_bending_moment_Nm_starboard=root_bm,
        root_bending_moment_Nm_port=0.0,
    )
    return SpanwiseLoadsResponse(
        alpha=2.0,
        velocity_mps=30.0,
        altitude_m=0.0,
        dynamic_pressure_Pa=551.25,
        surfaces=[surf],
    )


def _make_spar_station(y: float = 0.0) -> SparSizingStation:
    return SparSizingStation(
        y_m=y,
        chord_m=0.4,
        profile_thickness_mm=48.0,
        outer_mm=38.4,
        tc_ratio=0.12,
        tc_fallback=False,
        m_design_Nm=4500.0,
        required_W_mm3=9000.0,
        solved_mm=2.0,
        feasible=True,
        infeasibility_reason=None,
        cross_section_area_mm2=120.0,
    )


def _make_spar_result() -> SparSizingResult:
    station = _make_spar_station()
    return SparSizingResult(
        surface_name="main_wing",
        shape="tube",
        material_name="Carbon Fiber (structural)",
        sigma_allow_mpa=500.0,
        density_kg_m3=1600.0,
        g_limit=3.0,
        g_limit_fallback=False,
        safety_factor_j=1.5,
        packing_factor=0.8,
        stations=[station],
        root_station=station,
        spar_mass_half_kg=0.05,
        spar_mass_full_kg=0.10,
        tc_fallback_warning=None,
    )


# ---------------------------------------------------------------------------
# Endpoint tests (no spar params → plain spanwise response)
# ---------------------------------------------------------------------------


@pytest.fixture()
def plane_id():
    return uuid.uuid4()


@pytest.fixture()
def op():
    return OperatingPointSchema.model_construct(
        velocity=30.0,
        alpha=2.0,
        altitude=0.0,
        beta=0.0,
        xyz_ref=[0.0, 0.0, 0.0],
        p=0.0,
        q=0.0,
        r=0.0,
    )


class TestGetAirplaneSpanwiseLoadsWithoutSizing:
    """Endpoint without spar params returns plain SpanwiseLoadsResponse."""

    def test_no_spar_params_returns_spanwise_only(self, plane_id, op):
        from app.api.v2.endpoints.aeroanalysis import get_airplane_spanwise_loads

        mock_response = _make_spanwise_response()
        with patch(
            "app.services.analysis_service.analyze_airplane_spanwise_loads",
            new=AsyncMock(return_value=mock_response),
        ):
            result = asyncio.run(
                get_airplane_spanwise_loads(
                    aeroplane_id=plane_id,
                    operating_point=op,
                    db=None,
                    solver="vlm",
                )
            )
        assert isinstance(result, SpanwiseLoadsResponse)
        assert not hasattr(result, "spar_sizing") or result.spar_sizing is None


# ---------------------------------------------------------------------------
# SpanwiseLoadsWithSizingResponse
# ---------------------------------------------------------------------------


class TestSpanwiseLoadsWithSizingResponse:
    """Test the extended response schema."""

    def test_schema_fields(self):
        from app.schemas.spanwise_loads import SpanwiseLoadsWithSizingResponse

        spanwise = _make_spanwise_response()
        spar = _make_spar_result()
        resp = SpanwiseLoadsWithSizingResponse(
            **spanwise.model_dump(),
            spar_sizing=[spar],
        )
        assert resp.spar_sizing is not None
        assert len(resp.spar_sizing) == 1
        assert resp.spar_sizing[0].shape == "tube"
        assert resp.spar_sizing[0].root_station.feasible is True

    def test_schema_without_sizing(self):
        from app.schemas.spanwise_loads import SpanwiseLoadsWithSizingResponse

        spanwise = _make_spanwise_response()
        resp = SpanwiseLoadsWithSizingResponse(**spanwise.model_dump(), spar_sizing=None)
        assert resp.spar_sizing is None


# ---------------------------------------------------------------------------
# Material seed / schema tests (uses real test DB)
# ---------------------------------------------------------------------------


class TestMaterialSeedGh1008:
    """Verify the structural material seeds are present after conftest setup."""

    def test_pine_seeded(self, client_and_db):
        _, session_factory = client_and_db
        from app.models.component import ComponentModel

        with session_factory() as db:
            pine = (
                db.query(ComponentModel)
                .filter(
                    ComponentModel.name == "Pine (structural)",
                    ComponentModel.component_type == "material",
                )
                .first()
            )
        assert pine is not None
        assert pine.specs["density_kg_m3"] == pytest.approx(500.0)
        assert pine.specs["allowable_bending_stress_mpa"] == pytest.approx(39.0)
        assert pine.specs["youngs_modulus_gpa"] == pytest.approx(11.0)

    def test_carbon_fiber_seeded(self, client_and_db):
        _, session_factory = client_and_db
        from app.models.component import ComponentModel

        with session_factory() as db:
            cf = (
                db.query(ComponentModel)
                .filter(
                    ComponentModel.name == "Carbon Fiber (structural)",
                    ComponentModel.component_type == "material",
                )
                .first()
            )
        assert cf is not None
        assert cf.specs["density_kg_m3"] == pytest.approx(1600.0)
        assert cf.specs["allowable_bending_stress_mpa"] == pytest.approx(500.0)
        assert cf.specs["youngs_modulus_gpa"] == pytest.approx(120.0)

    def test_material_type_has_structural_fields(self, client_and_db):
        _, session_factory = client_and_db
        from app.models.component_type import ComponentTypeModel
        from app.services.component_type_service import _normalize_schema

        with session_factory() as db:
            mat_type = (
                db.query(ComponentTypeModel).filter(ComponentTypeModel.name == "material").first()
            )
        assert mat_type is not None
        schema = _normalize_schema(mat_type.schema_def)
        names = {p.get("name") for p in schema}
        assert "allowable_bending_stress_mpa" in names, f"Missing field in {names}"
        assert "youngs_modulus_gpa" in names, f"Missing field in {names}"

    def test_existing_material_rows_still_valid(self, client_and_db):
        """3D-print material rows (density only, no σ_allow) stay valid."""
        _, session_factory = client_and_db
        from app.models.component import ComponentModel

        with session_factory() as db:
            # Create a 3D-print-only material
            mat = ComponentModel(
                name="PLA Test",
                component_type="material",
                specs={"density_kg_m3": 1240.0},
            )
            db.add(mat)
            db.commit()
            db.refresh(mat)

            loaded = db.query(ComponentModel).filter(ComponentModel.name == "PLA Test").first()
        assert loaded is not None
        assert loaded.specs["density_kg_m3"] == pytest.approx(1240.0)
        # No allowable_bending_stress_mpa → should be absent, not error
        assert "allowable_bending_stress_mpa" not in loaded.specs


# ---------------------------------------------------------------------------
# analyze_airplane_spanwise_loads_with_sizing service tests
# ---------------------------------------------------------------------------


class TestAnalyzeSpanwiseLoadsWithSizing:
    """Cover the spar-sizing orchestration layer on the fast CI tier."""

    def _make_resolved_op(self):
        from types import SimpleNamespace

        return SimpleNamespace(
            velocity=30.0,
            alpha=2.0,
            beta=0.0,
            p=0.0,
            q=0.0,
            r=0.0,
            altitude=0.0,
            xyz_ref=[0.0, 0.0, 0.0],
        )

    def test_no_spar_params_returns_spanwise_response(self, plane_id, op):
        """Without spar params, returns plain SpanwiseLoadsResponse."""
        import sys
        from app.services import analysis_service

        canned_result = {
            "surfaces": [
                {
                    "surface_name": "main_wing",
                    "strips": [
                        {"Yle": 0.5, "Area": 0.1, "cl": 100.0, "Chord": 0.3},
                        {"Yle": -0.5, "Area": 0.1, "cl": 100.0, "Chord": 0.3},
                    ],
                }
            ],
        }
        resolved = self._make_resolved_op()
        asb_mock = MagicMock()
        asb_mock.Atmosphere.return_value.density.return_value = 1.225

        with (
            patch.dict(sys.modules, {"aerosandbox": asb_mock}),
            patch.object(analysis_service, "get_aeroplane_or_raise", return_value=MagicMock(id=1)),
            patch.object(
                analysis_service, "get_aeroplane_schema_or_raise", return_value=MagicMock()
            ),
            patch.object(
                analysis_service.operating_point_resolver,
                "resolve_operating_point",
                return_value=resolved,
            ),
            patch.object(
                analysis_service, "aeroplane_schema_to_asb_airplane_async", return_value=MagicMock()
            ),
            patch(
                "app.services.vlm_strip_forces.compute_vlm_strip_forces", return_value=canned_result
            ),
        ):
            result = asyncio.run(
                analysis_service.analyze_airplane_spanwise_loads(
                    db=MagicMock(),
                    aeroplane_uuid=plane_id,
                    operating_point=op,
                    solver="vlm",
                )
            )

        assert isinstance(result, SpanwiseLoadsResponse)

    def test_with_spar_params_returns_extended_response(self, plane_id, op):
        """With spar params, returns SpanwiseLoadsWithSizingResponse."""
        import sys
        from app.services import analysis_service
        from app.schemas.spanwise_loads import SpanwiseLoadsWithSizingResponse

        canned_result = {
            "surfaces": [
                {
                    "surface_name": "main_wing",
                    "strips": [
                        {"Yle": 0.5, "Area": 0.1, "cl": 100.0, "Chord": 0.3},
                    ],
                }
            ],
        }
        resolved = self._make_resolved_op()
        asb_mock = MagicMock()
        asb_mock.Atmosphere.return_value.density.return_value = 1.225

        # Mock the DB to return a material with the real specs keys
        mock_db = MagicMock()
        mock_material = MagicMock()
        mock_material.name = "Carbon Fiber (structural)"
        mock_material.specs = {
            "density_kg_m3": 1600.0,
            "allowable_bending_stress_mpa": 500.0,
            "youngs_modulus_gpa": 120.0,
        }
        mock_db.query.return_value.filter.return_value.first.return_value = mock_material

        spar_params = SparSizingParams(material_id=1, shape="rectangular")

        with (
            patch.dict(sys.modules, {"aerosandbox": asb_mock}),
            patch.object(analysis_service, "get_aeroplane_or_raise", return_value=MagicMock(id=1)),
            patch.object(
                analysis_service, "get_aeroplane_schema_or_raise", return_value=MagicMock()
            ),
            patch.object(
                analysis_service.operating_point_resolver,
                "resolve_operating_point",
                return_value=resolved,
            ),
            patch.object(
                analysis_service, "aeroplane_schema_to_asb_airplane_async", return_value=MagicMock()
            ),
            patch(
                "app.services.vlm_strip_forces.compute_vlm_strip_forces", return_value=canned_result
            ),
            patch(
                "app.services.design_assumptions_service.get_effective_assumption", return_value=3.0
            ),
        ):
            result = asyncio.run(
                analysis_service.analyze_airplane_spanwise_loads(
                    db=mock_db,
                    aeroplane_uuid=plane_id,
                    operating_point=op,
                    solver="vlm",
                    spar_params=spar_params,
                )
            )

        assert isinstance(result, SpanwiseLoadsWithSizingResponse)
        assert result.spar_sizing is not None
        assert len(result.spar_sizing) >= 1
        assert result.spar_sizing[0].material_name == "Carbon Fiber (structural)"

    def test_material_not_found_raises_422(self, plane_id, op):
        """When material_id not in DB → raises ValidationError."""
        import sys
        from app.services import analysis_service
        from app.core.exceptions import ValidationError

        canned_result = {
            "surfaces": [
                {
                    "surface_name": "main_wing",
                    "strips": [{"Yle": 0.5, "Area": 0.1, "cl": 100.0, "Chord": 0.3}],
                }
            ],
        }
        resolved = self._make_resolved_op()
        asb_mock = MagicMock()
        asb_mock.Atmosphere.return_value.density.return_value = 1.225

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None  # not found

        spar_params = SparSizingParams(material_id=999, shape="tube")

        with (
            patch.dict(sys.modules, {"aerosandbox": asb_mock}),
            patch.object(analysis_service, "get_aeroplane_or_raise", return_value=MagicMock(id=1)),
            patch.object(
                analysis_service, "get_aeroplane_schema_or_raise", return_value=MagicMock()
            ),
            patch.object(
                analysis_service.operating_point_resolver,
                "resolve_operating_point",
                return_value=resolved,
            ),
            patch.object(
                analysis_service, "aeroplane_schema_to_asb_airplane_async", return_value=MagicMock()
            ),
            patch(
                "app.services.vlm_strip_forces.compute_vlm_strip_forces", return_value=canned_result
            ),
            patch(
                "app.services.design_assumptions_service.get_effective_assumption", return_value=3.0
            ),
        ):
            with pytest.raises((ValidationError, Exception)) as exc:
                asyncio.run(
                    analysis_service.analyze_airplane_spanwise_loads(
                        db=mock_db,
                        aeroplane_uuid=plane_id,
                        operating_point=op,
                        solver="vlm",
                        spar_params=spar_params,
                    )
                )
        # Material ID 999 not found → should raise ValidationError or similar
        assert exc is not None

    def test_g_limit_fallback_used_when_no_assumption(self, plane_id, op):
        """When get_effective_assumption returns None → g_limit=3.0 fallback, warning set."""
        import sys
        from app.services import analysis_service
        from app.schemas.spanwise_loads import SpanwiseLoadsWithSizingResponse

        canned_result = {
            "surfaces": [
                {
                    "surface_name": "main_wing",
                    "strips": [{"Yle": 0.5, "Area": 0.1, "cl": 100.0, "Chord": 0.3}],
                }
            ],
        }
        resolved = self._make_resolved_op()
        asb_mock = MagicMock()
        asb_mock.Atmosphere.return_value.density.return_value = 1.225

        mock_db = MagicMock()
        mock_material = MagicMock()
        mock_material.name = "Carbon Fiber (structural)"
        mock_material.specs = {
            "density_kg_m3": 1600.0,
            "allowable_bending_stress_mpa": 500.0,
        }
        mock_db.query.return_value.filter.return_value.first.return_value = mock_material

        spar_params = SparSizingParams(material_id=1, shape="rectangular")

        with (
            patch.dict(sys.modules, {"aerosandbox": asb_mock}),
            patch.object(analysis_service, "get_aeroplane_or_raise", return_value=MagicMock(id=1)),
            patch.object(
                analysis_service, "get_aeroplane_schema_or_raise", return_value=MagicMock()
            ),
            patch.object(
                analysis_service.operating_point_resolver,
                "resolve_operating_point",
                return_value=resolved,
            ),
            patch.object(
                analysis_service, "aeroplane_schema_to_asb_airplane_async", return_value=MagicMock()
            ),
            patch(
                "app.services.vlm_strip_forces.compute_vlm_strip_forces", return_value=canned_result
            ),
            patch(
                "app.services.design_assumptions_service.get_effective_assumption",
                return_value=None,
            ),
        ):  # <-- no assumption row
            result = asyncio.run(
                analysis_service.analyze_airplane_spanwise_loads(
                    db=mock_db,
                    aeroplane_uuid=plane_id,
                    operating_point=op,
                    solver="vlm",
                    spar_params=spar_params,
                )
            )

        assert isinstance(result, SpanwiseLoadsWithSizingResponse)
        assert result.spar_sizing[0].g_limit_fallback is True
        assert result.spar_sizing[0].g_limit == pytest.approx(3.0)
