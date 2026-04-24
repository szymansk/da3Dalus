"""Extended tests for app/api/v2/endpoints/aeroanalysis.py.

Covers error-handling branches, strip-force endpoints, stability summary,
and the _raise_http_from_domain helper that were not exercised by the
original test_aeroanalysis.py.
"""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, Request

from app.api.v2.endpoints.aeroanalysis import (
    _raise_http_from_domain,
    _resolve_base_url,
    analyze_airplane_post,
    analyze_wing_post,
    calculate_streamlines_json,
    get_airplane_strip_forces,
    get_stability_summary,
    get_wing_strip_forces,
    get_aeroplane_three_view_url,
    get_streamlines_three_view_url,
    analyze_airplane_alpha_sweep,
    analyze_airplane_simple_sweep,
)
from app.core.exceptions import (
    ConflictError,
    InternalError,
    NotFoundError,
    ServiceException,
    ValidationDomainError,
    ValidationError,
)
from app.schemas.AeroplaneRequest import (
    AlphaSweepRequest,
    AnalysisToolUrlType,
    SimpleSweepRequest,
)
from app.schemas.aeroanalysisschema import OperatingPointSchema


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def plane_id():
    return uuid.uuid4()


@pytest.fixture()
def operating_point():
    return OperatingPointSchema.model_construct(
        velocity=10.0,
        alpha=5.0,
        beta=0.0,
        p=0.0,
        q=0.0,
        r=0.0,
        xyz_ref=[0.0, 0.0, 0.0],
    )


@pytest.fixture()
def mock_db():
    return MagicMock()


@pytest.fixture()
def mock_request():
    req = MagicMock(spec=Request)
    req.base_url = "http://testserver/"
    return req


@pytest.fixture()
def mock_settings():
    s = MagicMock()
    s.base_url = "http://testserver"
    return s


# ---------------------------------------------------------------------------
# _raise_http_from_domain — all branches
# ---------------------------------------------------------------------------


class TestRaiseHttpFromDomain:
    """Cover every isinstance branch in _raise_http_from_domain."""

    def test_not_found_maps_to_404(self):
        with pytest.raises(HTTPException) as exc_info:
            _raise_http_from_domain(NotFoundError("gone"))
        assert exc_info.value.status_code == 404
        assert "gone" in exc_info.value.detail

    def test_validation_error_maps_to_422(self):
        with pytest.raises(HTTPException) as exc_info:
            _raise_http_from_domain(ValidationError("bad input"))
        assert exc_info.value.status_code == 422
        assert "bad input" in exc_info.value.detail

    def test_validation_domain_error_maps_to_422(self):
        with pytest.raises(HTTPException) as exc_info:
            _raise_http_from_domain(ValidationDomainError("domain issue"))
        assert exc_info.value.status_code == 422
        assert "domain issue" in exc_info.value.detail

    def test_conflict_error_maps_to_409(self):
        with pytest.raises(HTTPException) as exc_info:
            _raise_http_from_domain(ConflictError("already exists"))
        assert exc_info.value.status_code == 409
        assert "already exists" in exc_info.value.detail

    def test_internal_error_maps_to_500(self):
        with pytest.raises(HTTPException) as exc_info:
            _raise_http_from_domain(InternalError("boom"))
        assert exc_info.value.status_code == 500
        assert "boom" in exc_info.value.detail

    def test_generic_service_exception_maps_to_500(self):
        with pytest.raises(HTTPException) as exc_info:
            _raise_http_from_domain(ServiceException("unknown"))
        assert exc_info.value.status_code == 500
        assert "unknown" in exc_info.value.detail


# ---------------------------------------------------------------------------
# _resolve_base_url
# ---------------------------------------------------------------------------


class TestResolveBaseUrl:
    def test_returns_request_base_url_when_available(self, mock_request, mock_settings):
        result = _resolve_base_url(mock_request, mock_settings)
        assert result == "http://testserver"

    def test_falls_back_to_settings_when_no_request(self, mock_settings):
        result = _resolve_base_url(None, mock_settings)
        assert result == "http://testserver"

    def test_replaces_apiserver_sentinel_with_settings(self, mock_settings):
        req = MagicMock(spec=Request)
        req.base_url = "apiserver"
        mock_settings.base_url = "http://real-server"
        result = _resolve_base_url(req, mock_settings)
        assert result == "http://real-server"


# ---------------------------------------------------------------------------
# get_airplane_strip_forces
# ---------------------------------------------------------------------------


class TestGetAirplaneStripForces:
    def test_success(self, plane_id, operating_point, mock_db):
        expected = {"surfaces": []}
        with patch(
            "app.api.v2.endpoints.aeroanalysis.analysis_service.analyze_airplane_strip_forces",
            new=AsyncMock(return_value=expected),
        ) as mock_fn:
            result = asyncio.run(
                get_airplane_strip_forces(plane_id, operating_point, mock_db)
            )
        assert result == expected
        mock_fn.assert_awaited_once_with(mock_db, plane_id, operating_point)

    def test_not_found_maps_to_404(self, plane_id, operating_point, mock_db):
        with patch(
            "app.api.v2.endpoints.aeroanalysis.analysis_service.analyze_airplane_strip_forces",
            new=AsyncMock(side_effect=NotFoundError("no plane")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(
                    get_airplane_strip_forces(plane_id, operating_point, mock_db)
                )
        assert exc_info.value.status_code == 404

    def test_conflict_maps_to_409(self, plane_id, operating_point, mock_db):
        with patch(
            "app.api.v2.endpoints.aeroanalysis.analysis_service.analyze_airplane_strip_forces",
            new=AsyncMock(side_effect=ConflictError("locked")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(
                    get_airplane_strip_forces(plane_id, operating_point, mock_db)
                )
        assert exc_info.value.status_code == 409


# ---------------------------------------------------------------------------
# get_wing_strip_forces
# ---------------------------------------------------------------------------


class TestGetWingStripForces:
    def test_success(self, plane_id, operating_point, mock_db):
        expected = {"surfaces": [{"name": "main"}]}
        with patch(
            "app.api.v2.endpoints.aeroanalysis.analysis_service.analyze_wing_strip_forces",
            new=AsyncMock(return_value=expected),
        ) as mock_fn:
            result = asyncio.run(
                get_wing_strip_forces(plane_id, "main_wing", operating_point, mock_db)
            )
        assert result == expected
        mock_fn.assert_awaited_once_with(
            mock_db, plane_id, "main_wing", operating_point
        )

    def test_not_found_maps_to_404(self, plane_id, operating_point, mock_db):
        with patch(
            "app.api.v2.endpoints.aeroanalysis.analysis_service.analyze_wing_strip_forces",
            new=AsyncMock(side_effect=NotFoundError("wing gone")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(
                    get_wing_strip_forces(plane_id, "no_wing", operating_point, mock_db)
                )
        assert exc_info.value.status_code == 404

    def test_validation_error_maps_to_422(self, plane_id, operating_point, mock_db):
        with patch(
            "app.api.v2.endpoints.aeroanalysis.analysis_service.analyze_wing_strip_forces",
            new=AsyncMock(side_effect=ValidationError("bad wing config")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(
                    get_wing_strip_forces(plane_id, "bad_wing", operating_point, mock_db)
                )
        assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# get_stability_summary
# ---------------------------------------------------------------------------


class TestGetStabilitySummary:
    def test_success(self, plane_id, operating_point, mock_db):
        from app.schemas.stability import StabilitySummaryResponse

        expected = StabilitySummaryResponse(
            static_margin=0.15,
            neutral_point_x=0.3,
            cg_x=0.25,
            is_statically_stable=True,
        )
        with patch(
            "app.api.v2.endpoints.aeroanalysis.stability_service.get_stability_summary",
            new=AsyncMock(return_value=expected),
        ) as mock_fn:
            result = asyncio.run(
                get_stability_summary(
                    plane_id, operating_point, AnalysisToolUrlType.AVL, mock_db
                )
            )
        assert result == expected
        mock_fn.assert_awaited_once_with(
            mock_db, plane_id, operating_point, AnalysisToolUrlType.AVL
        )

    def test_not_found_maps_to_404(self, plane_id, operating_point, mock_db):
        with patch(
            "app.api.v2.endpoints.aeroanalysis.stability_service.get_stability_summary",
            new=AsyncMock(side_effect=NotFoundError("no aeroplane")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(
                    get_stability_summary(
                        plane_id, operating_point, AnalysisToolUrlType.AVL, mock_db
                    )
                )
        assert exc_info.value.status_code == 404

    def test_internal_error_maps_to_500(self, plane_id, operating_point, mock_db):
        with patch(
            "app.api.v2.endpoints.aeroanalysis.stability_service.get_stability_summary",
            new=AsyncMock(side_effect=InternalError("solver crashed")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(
                    get_stability_summary(
                        plane_id, operating_point, AnalysisToolUrlType.AVL, mock_db
                    )
                )
        assert exc_info.value.status_code == 500

    def test_unexpected_exception_maps_to_500(self, plane_id, operating_point, mock_db):
        with patch(
            "app.api.v2.endpoints.aeroanalysis.stability_service.get_stability_summary",
            new=AsyncMock(side_effect=RuntimeError("surprise")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(
                    get_stability_summary(
                        plane_id, operating_point, AnalysisToolUrlType.AVL, mock_db
                    )
                )
        assert exc_info.value.status_code == 500
        assert "surprise" in exc_info.value.detail


# ---------------------------------------------------------------------------
# calculate_streamlines_json — error path
# ---------------------------------------------------------------------------


class TestStreamlinesJsonErrors:
    def test_internal_error_maps_to_500(self, plane_id, operating_point, mock_db):
        with patch(
            "app.api.v2.endpoints.aeroanalysis.analysis_service.calculate_streamlines_json",
            new=AsyncMock(side_effect=InternalError("VLM diverged")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(
                    calculate_streamlines_json(plane_id, operating_point, mock_db)
                )
        assert exc_info.value.status_code == 500

    def test_unexpected_exception_maps_to_500(self, plane_id, operating_point, mock_db):
        with patch(
            "app.api.v2.endpoints.aeroanalysis.analysis_service.calculate_streamlines_json",
            new=AsyncMock(side_effect=RuntimeError("oops")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(
                    calculate_streamlines_json(plane_id, operating_point, mock_db)
                )
        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# analyze_wing_post — additional error types
# ---------------------------------------------------------------------------


class TestAnalyzeWingPostErrors:
    def test_validation_domain_error_maps_to_422(
        self, plane_id, operating_point, mock_db
    ):
        with patch(
            "app.api.v2.endpoints.aeroanalysis.analysis_service.analyze_wing",
            new=AsyncMock(side_effect=ValidationDomainError("chord <= 0")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(
                    analyze_wing_post(
                        plane_id,
                        "wing",
                        operating_point,
                        AnalysisToolUrlType.AEROBUILDUP,
                        mock_db,
                    )
                )
        assert exc_info.value.status_code == 422

    def test_internal_error_maps_to_500(self, plane_id, operating_point, mock_db):
        with patch(
            "app.api.v2.endpoints.aeroanalysis.analysis_service.analyze_wing",
            new=AsyncMock(side_effect=InternalError("solver failed")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(
                    analyze_wing_post(
                        plane_id,
                        "wing",
                        operating_point,
                        AnalysisToolUrlType.AEROBUILDUP,
                        mock_db,
                    )
                )
        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# analyze_airplane_post — additional error types
# ---------------------------------------------------------------------------


class TestAnalyzeAirplanePostErrors:
    def test_conflict_error_maps_to_409(self, plane_id, operating_point, mock_db):
        with patch(
            "app.api.v2.endpoints.aeroanalysis.analysis_service.analyze_airplane",
            new=AsyncMock(side_effect=ConflictError("analysis in progress")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(
                    analyze_airplane_post(
                        plane_id,
                        operating_point,
                        AnalysisToolUrlType.VORTEX_LATTICE,
                        mock_db,
                    )
                )
        assert exc_info.value.status_code == 409


# ---------------------------------------------------------------------------
# alpha_sweep — error path
# ---------------------------------------------------------------------------


class TestAlphaSweepErrors:
    @pytest.fixture()
    def sweep_request(self):
        return AlphaSweepRequest.model_construct(
            altitude=0.0,
            velocity=20.0,
            alpha_start=0.0,
            alpha_end=10.0,
            alpha_num=5,
            beta=0.0,
            p=0.0,
            q=0.0,
            r=0.0,
            xyz_ref=[0.0, 0.0, 0.0],
        )

    def test_not_found_maps_to_404(self, plane_id, sweep_request, mock_db):
        with patch(
            "app.api.v2.endpoints.aeroanalysis.analysis_service.analyze_alpha_sweep",
            new=AsyncMock(side_effect=NotFoundError("no plane")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(
                    analyze_airplane_alpha_sweep(plane_id, sweep_request, mock_db)
                )
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# simple_sweep — error path
# ---------------------------------------------------------------------------


class TestSimpleSweepErrors:
    @pytest.fixture()
    def sweep_request(self):
        return SimpleSweepRequest.model_construct(
            sweep_var="velocity",
            step_size=5.0,
            num=3,
            altitude=0.0,
            velocity=20.0,
            alpha=5.0,
            beta=0.0,
            p=0.0,
            q=0.0,
            r=0.0,
            xyz_ref=[0.0, 0.0, 0.0],
        )

    def test_not_found_maps_to_404(self, plane_id, sweep_request, mock_db):
        with patch(
            "app.api.v2.endpoints.aeroanalysis.analysis_service.analyze_simple_sweep",
            new=AsyncMock(side_effect=NotFoundError("no aeroplane")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(
                    analyze_airplane_simple_sweep(plane_id, sweep_request, mock_db)
                )
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# three_view and streamlines_three_view — error paths
# ---------------------------------------------------------------------------


class TestThreeViewErrors:
    def test_not_found_maps_to_404(self, plane_id, mock_db, mock_request, mock_settings):
        with patch(
            "app.api.v2.endpoints.aeroanalysis.analysis_service.get_three_view_image",
            new=AsyncMock(side_effect=NotFoundError("no aeroplane")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(
                    get_aeroplane_three_view_url(
                        plane_id, mock_db, mock_settings, mock_request
                    )
                )
        assert exc_info.value.status_code == 404

    def test_validation_error_maps_to_422(self, plane_id, mock_db, mock_request, mock_settings):
        with patch(
            "app.api.v2.endpoints.aeroanalysis.analysis_service.get_three_view_image",
            new=AsyncMock(side_effect=ValidationError("incomplete model")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(
                    get_aeroplane_three_view_url(
                        plane_id, mock_db, mock_settings, mock_request
                    )
                )
        assert exc_info.value.status_code == 422


class TestStreamlinesThreeViewErrors:
    def test_not_found_maps_to_404(
        self, plane_id, operating_point, mock_db, mock_request, mock_settings
    ):
        with patch(
            "app.api.v2.endpoints.aeroanalysis.analysis_service.get_streamlines_three_view_image",
            new=AsyncMock(side_effect=NotFoundError("not found")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(
                    get_streamlines_three_view_url(
                        plane_id, operating_point, mock_db, mock_settings, mock_request
                    )
                )
        assert exc_info.value.status_code == 404
