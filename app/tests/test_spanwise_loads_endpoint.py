"""gh-1002: Endpoint tests for POST /aeroplanes/{id}/spanwise_loads.

All tests run on the CI fast tier (no aerosandbox) by patching
``analysis_service.analyze_airplane_spanwise_loads`` at the call boundary.
Tests call endpoint functions directly (same pattern as test_aeroanalysis_endpoint_extended.py)
to avoid the `aerosandbox_available()` router-registration guard in main.py.
"""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.api.v2.endpoints.aeroanalysis import get_airplane_spanwise_loads
from app.core.exceptions import InternalError, NotFoundError
from app.schemas.aeroanalysisschema import OperatingPointSchema
from app.schemas.spanwise_loads import (
    SpanwiseLoadEntry,
    SpanwiseLoadsResponse,
    SurfaceSpanwiseLoads,
)


def _make_response() -> SpanwiseLoadsResponse:
    entry = SpanwiseLoadEntry(y_m=1.0, chord_m=0.3, shear_N=100.0, bending_moment_Nm=50.0)
    surf = SurfaceSpanwiseLoads(
        surface_name="main_wing",
        starboard=[entry],
        port=[],
        root_shear_N_starboard=100.0,
        root_shear_N_port=0.0,
        root_bending_moment_Nm_starboard=50.0,
        root_bending_moment_Nm_port=0.0,
    )
    return SpanwiseLoadsResponse(
        alpha=2.0,
        velocity_mps=30.0,
        altitude_m=0.0,
        dynamic_pressure_Pa=551.25,
        surfaces=[surf],
    )


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


class TestGetAirplaneSpanwiseLoadsEndpoint:
    """Direct endpoint-function tests — no router needed, runs without aero deps."""

    def test_returns_response_when_service_succeeds(self, plane_id, op):
        mock_response = _make_response()

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

        assert result is mock_response
        assert result.dynamic_pressure_Pa == pytest.approx(551.25)
        assert result.surfaces[0].root_bending_moment_Nm_starboard == pytest.approx(50.0)

    def test_raises_http_404_on_not_found(self, plane_id, op):
        with patch(
            "app.services.analysis_service.analyze_airplane_spanwise_loads",
            new=AsyncMock(side_effect=NotFoundError(message="Aeroplane not found")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(
                    get_airplane_spanwise_loads(
                        aeroplane_id=plane_id,
                        operating_point=op,
                        db=None,
                        solver="vlm",
                    )
                )
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    def test_raises_http_500_on_internal_error(self, plane_id, op):
        with patch(
            "app.services.analysis_service.analyze_airplane_spanwise_loads",
            new=AsyncMock(side_effect=InternalError(message="Solver failed")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(
                    get_airplane_spanwise_loads(
                        aeroplane_id=plane_id,
                        operating_point=op,
                        db=None,
                        solver="vlm",
                    )
                )
        assert exc_info.value.status_code == 500

    def test_solver_param_forwarded_to_service(self, plane_id, op):
        mock_response = _make_response()
        captured = {}

        async def capture(db, aeroplane_uuid, operating_point, solver="vlm"):
            captured["solver"] = solver
            return mock_response

        with patch(
            "app.services.analysis_service.analyze_airplane_spanwise_loads",
            side_effect=capture,
        ):
            asyncio.run(
                get_airplane_spanwise_loads(
                    aeroplane_id=plane_id,
                    operating_point=op,
                    db=None,
                    solver="avl",
                )
            )

        assert captured["solver"] == "avl"


class TestAnalyzeAirplaneSpanwiseLoadsService:
    """Cover the aero wrapper on the CI fast tier (no aerosandbox) by stubbing the
    solver boundary: aerosandbox itself, the schema/aeroplane resolution, and the
    VLM strip-forces computation. Only the integration glue runs for real."""

    def test_integrates_strip_forces_into_loads(self, plane_id, op):
        import sys
        from types import SimpleNamespace
        from unittest.mock import MagicMock

        from app.services import analysis_service

        # Two strips (one per half), q·Area·cl = 551.25·0.1·1000 = 55125 N lift each;
        # root BM per half = lift · |y| = 55125 · 0.5 = 27562.5 N·m.
        canned_result = {
            "surfaces": [
                {
                    "surface_name": "main_wing",
                    "strips": [
                        {"Yle": 0.5, "Area": 0.1, "cl": 1000.0, "Chord": 0.2},
                        {"Yle": -0.5, "Area": 0.1, "cl": 1000.0, "Chord": 0.2},
                    ],
                }
            ],
        }
        resolved = SimpleNamespace(
            velocity=30.0, alpha=2.0, beta=0.0, p=0.0, q=0.0, r=0.0,
            altitude=0.0, xyz_ref=[0.0, 0.0, 0.0],
        )
        asb_mock = MagicMock()
        asb_mock.Atmosphere.return_value.density.return_value = 1.225

        with patch.dict(sys.modules, {"aerosandbox": asb_mock}), patch.object(
            analysis_service, "get_aeroplane_or_raise", return_value=MagicMock(id=1)
        ), patch.object(
            analysis_service, "get_aeroplane_schema_or_raise", return_value=MagicMock()
        ), patch.object(
            analysis_service.operating_point_resolver,
            "resolve_operating_point",
            return_value=resolved,
        ), patch.object(
            analysis_service, "aeroplane_schema_to_asb_airplane_async", return_value=MagicMock()
        ), patch(
            "app.services.vlm_strip_forces.compute_vlm_strip_forces",
            return_value=canned_result,
        ):
            result = asyncio.run(
                analysis_service.analyze_airplane_spanwise_loads(
                    db=MagicMock(), aeroplane_uuid=plane_id, operating_point=op, solver="vlm"
                )
            )

        assert isinstance(result, SpanwiseLoadsResponse)
        assert result.dynamic_pressure_Pa == pytest.approx(0.5 * 1.225 * 30.0**2)  # 551.25
        surf = result.surfaces[0]
        assert surf.surface_name == "main_wing"
        assert surf.root_bending_moment_Nm_starboard == pytest.approx(27562.5, rel=1e-3)
        assert surf.root_bending_moment_Nm_port == pytest.approx(27562.5, rel=1e-3)

    def test_not_found_propagates(self, plane_id, op):
        import sys
        from unittest.mock import MagicMock

        from app.services import analysis_service

        with patch.dict(sys.modules, {"aerosandbox": MagicMock()}), patch.object(
            analysis_service,
            "get_aeroplane_or_raise",
            side_effect=NotFoundError(message="Aeroplane not found"),
        ):
            with pytest.raises(NotFoundError):
                asyncio.run(
                    analysis_service.analyze_airplane_spanwise_loads(
                        db=MagicMock(), aeroplane_uuid=plane_id, operating_point=op, solver="vlm"
                    )
                )

    def _patches(self, analysis_service, resolved):
        import sys
        from unittest.mock import MagicMock

        asb_mock = MagicMock()
        asb_mock.Atmosphere.return_value.density.return_value = 1.225
        return [
            patch.dict(sys.modules, {"aerosandbox": asb_mock}),
            patch.object(analysis_service, "get_aeroplane_or_raise", return_value=MagicMock(id=1)),
            patch.object(analysis_service, "get_aeroplane_schema_or_raise", return_value=MagicMock()),
            patch.object(
                analysis_service.operating_point_resolver,
                "resolve_operating_point",
                return_value=resolved,
            ),
            patch.object(
                analysis_service, "aeroplane_schema_to_asb_airplane_async", return_value=MagicMock()
            ),
        ]

    def test_avl_solver_branch(self, plane_id, op):
        import contextlib
        from types import SimpleNamespace
        from unittest.mock import MagicMock

        from app.services import analysis_service

        canned = {
            "surfaces": [
                {"surface_name": "w", "strips": [{"Yle": 0.5, "Area": 0.1, "cl": 1000.0, "Chord": 0.2}]}
            ]
        }
        resolved = SimpleNamespace(
            velocity=30.0, alpha=2.0, beta=0.0, p=0.0, q=0.0, r=0.0,
            altitude=0.0, xyz_ref=[0.0, 0.0, 0.0],
        )
        with contextlib.ExitStack() as stack:
            for p in self._patches(analysis_service, resolved):
                stack.enter_context(p)
            stack.enter_context(
                patch.object(analysis_service, "_run_avl_strip_forces", return_value=canned)
            )
            result = asyncio.run(
                analysis_service.analyze_airplane_spanwise_loads(
                    db=MagicMock(), aeroplane_uuid=plane_id, operating_point=op, solver="avl"
                )
            )
        assert result.surfaces[0].root_bending_moment_Nm_starboard == pytest.approx(27562.5, rel=1e-3)

    def test_generic_error_wrapped_as_internal(self, plane_id, op):
        import contextlib
        from types import SimpleNamespace
        from unittest.mock import MagicMock

        from app.services import analysis_service

        resolved = SimpleNamespace(
            velocity=30.0, alpha=2.0, beta=0.0, p=0.0, q=0.0, r=0.0,
            altitude=0.0, xyz_ref=[0.0, 0.0, 0.0],
        )
        with contextlib.ExitStack() as stack:
            for p in self._patches(analysis_service, resolved):
                stack.enter_context(p)
            stack.enter_context(
                patch(
                    "app.services.vlm_strip_forces.compute_vlm_strip_forces",
                    side_effect=ValueError("boom"),
                )
            )
            with pytest.raises(InternalError):
                asyncio.run(
                    analysis_service.analyze_airplane_spanwise_loads(
                        db=MagicMock(), aeroplane_uuid=plane_id, operating_point=op, solver="vlm"
                    )
                )
