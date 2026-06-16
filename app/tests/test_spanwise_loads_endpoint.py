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
