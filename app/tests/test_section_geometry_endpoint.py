"""gh-1021: Fast-tier tests for the section-geometry endpoint + service.

These run on the CI fast tier (no cadquery). We mock the SectionGeometry
boundary so the real lofted-solid build never runs. Endpoint functions are
called directly (same pattern as test_spanwise_loads_endpoint.py) to avoid the
router-registration guard in main.py.

Coverage targets: default sampling, mm->m unit conversion, per_segment flag,
explicit wing selection, and error paths (no wings, wing not found, aeroplane
not found, cadquery-unavailable -> clean 422).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.api.v2.endpoints.aeroanalysis import get_airplane_section_geometry
from app.core.exceptions import NotFoundError, ValidationError
from app.schemas.section_geometry import SectionGeometryRequest
from app.services import section_geometry_service


@dataclass(frozen=True)
class _StubPoint:
    """Mimics cad_designer SectionPoint (millimetres)."""

    y_span: float
    x_c: float
    thickness: float
    top_z: float
    bottom_z: float
    center_z: float


class _StubGeometry:
    """Records sample/per_segment calls and returns synthetic mm points."""

    def __init__(self):
        self.sample_calls: list[tuple[list[float], list[float]]] = []
        self.per_segment_calls: list[tuple[int, int]] = []

    def sample(self, y_spans, x_cs):
        self.sample_calls.append((list(y_spans), list(x_cs)))
        return [
            _StubPoint(
                y_span=y,
                x_c=x,
                thickness=120.0,
                top_z=60.0,
                bottom_z=-60.0,
                center_z=0.0,
            )
            for y in y_spans
            for x in x_cs
        ]

    def per_segment(self, n_span, n_chord):
        self.per_segment_calls.append((n_span, n_chord))
        return {
            0: [
                _StubPoint(
                    y_span=0.1,
                    x_c=0.3,
                    thickness=100.0,
                    top_z=50.0,
                    bottom_z=-50.0,
                    center_z=0.0,
                )
            ]
        }


@pytest.fixture()
def plane_id():
    return uuid.uuid4()


def _aeroplane_with_wings(wing_names):
    wings = [SimpleNamespace(name=n) for n in wing_names]
    return SimpleNamespace(wings=wings, uuid=uuid.uuid4())


def _patch_resolution(aeroplane, geometry):
    """Patch the service's aeroplane resolution + SectionGeometry build."""
    return (
        patch.object(
            section_geometry_service,
            "get_aeroplane_or_raise",
            return_value=aeroplane,
        ),
        patch.object(
            section_geometry_service,
            "wing_model_to_wing_config",
            return_value=object(),
        ),
        patch.object(
            section_geometry_service,
            "_build_section_geometry",
            return_value=geometry,
        ),
    )


# --------------------------------------------------------------------------
# Service-level tests
# --------------------------------------------------------------------------


class TestComputeSectionGeometryService:
    def test_default_sampling_uses_even_grid(self, plane_id):
        aeroplane = _aeroplane_with_wings(["main_wing"])
        geom = _StubGeometry()
        p_get, p_conv, p_build = _patch_resolution(aeroplane, geom)
        with p_get, p_conv, p_build:
            resp = section_geometry_service.compute_section_geometry(
                db=None,
                aeroplane_uuid=plane_id,
                request=SectionGeometryRequest(),
            )

        # 11 x 11 default grid -> 121 surface points.
        assert len(resp.surface) == 121
        y_spans, x_cs = geom.sample_calls[0]
        assert len(y_spans) == 11
        assert len(x_cs) == 11
        # Interior grid: never the exact endpoints.
        assert all(0.0 < y < 1.0 for y in y_spans)
        assert all(0.0 < x < 1.0 for x in x_cs)

    def test_mm_to_m_conversion(self, plane_id):
        aeroplane = _aeroplane_with_wings(["main_wing"])
        geom = _StubGeometry()
        p_get, p_conv, p_build = _patch_resolution(aeroplane, geom)
        with p_get, p_conv, p_build:
            resp = section_geometry_service.compute_section_geometry(
                db=None,
                aeroplane_uuid=plane_id,
                request=SectionGeometryRequest(y_over_span=[0.5], x_over_chord=[0.3]),
            )

        pt = resp.surface[0]
        # 120 mm thickness -> 0.120 m, 60 mm -> 0.060 m.
        assert pt.thickness == pytest.approx(0.120)
        assert pt.top_z == pytest.approx(0.060)
        assert pt.bottom_z == pytest.approx(-0.060)
        assert pt.center_z == pytest.approx(0.0)

    def test_explicit_arrays_passed_through(self, plane_id):
        aeroplane = _aeroplane_with_wings(["main_wing"])
        geom = _StubGeometry()
        p_get, p_conv, p_build = _patch_resolution(aeroplane, geom)
        with p_get, p_conv, p_build:
            section_geometry_service.compute_section_geometry(
                db=None,
                aeroplane_uuid=plane_id,
                request=SectionGeometryRequest(y_over_span=[0.2, 0.8], x_over_chord=[0.25]),
            )

        assert geom.sample_calls[0] == ([0.2, 0.8], [0.25])

    def test_per_segment_flag_returns_segments(self, plane_id):
        aeroplane = _aeroplane_with_wings(["main_wing"])
        geom = _StubGeometry()
        p_get, p_conv, p_build = _patch_resolution(aeroplane, geom)
        with p_get, p_conv, p_build:
            resp = section_geometry_service.compute_section_geometry(
                db=None,
                aeroplane_uuid=plane_id,
                request=SectionGeometryRequest(per_segment=True),
            )

        assert resp.segments is not None
        assert 0 in resp.segments
        assert resp.segments[0][0].thickness == pytest.approx(0.100)
        assert len(geom.per_segment_calls) == 1

    def test_per_segment_omitted_by_default(self, plane_id):
        aeroplane = _aeroplane_with_wings(["main_wing"])
        geom = _StubGeometry()
        p_get, p_conv, p_build = _patch_resolution(aeroplane, geom)
        with p_get, p_conv, p_build:
            resp = section_geometry_service.compute_section_geometry(
                db=None,
                aeroplane_uuid=plane_id,
                request=SectionGeometryRequest(),
            )

        assert resp.segments is None
        assert geom.per_segment_calls == []

    def test_request_mode_forwarded_to_build(self, plane_id):
        """gh-1046: the request's mode reaches the build seam (analytic default)."""
        aeroplane = _aeroplane_with_wings(["main_wing"])
        geom = _StubGeometry()
        seen = {}

        def _capture_build(wing_config, mode="analytic"):
            seen["mode"] = mode
            return geom

        with (
            patch.object(
                section_geometry_service, "get_aeroplane_or_raise", return_value=aeroplane
            ),
            patch.object(
                section_geometry_service, "wing_model_to_wing_config", return_value=object()
            ),
            patch.object(section_geometry_service, "_build_section_geometry", _capture_build),
        ):
            section_geometry_service.compute_section_geometry(
                db=None, aeroplane_uuid=plane_id, request=SectionGeometryRequest()
            )
            assert seen["mode"] == "analytic"
            section_geometry_service.compute_section_geometry(
                db=None,
                aeroplane_uuid=plane_id,
                request=SectionGeometryRequest(mode="solid"),
            )
            assert seen["mode"] == "solid"

    def test_named_wing_is_selected(self, plane_id):
        aeroplane = _aeroplane_with_wings(["main_wing", "h_tail"])
        geom = _StubGeometry()
        with (
            patch.object(
                section_geometry_service, "get_aeroplane_or_raise", return_value=aeroplane
            ),
            patch.object(section_geometry_service, "get_wing_or_raise") as mock_get_wing,
            patch.object(
                section_geometry_service, "wing_model_to_wing_config", return_value=object()
            ),
            patch.object(section_geometry_service, "_build_section_geometry", return_value=geom),
        ):
            mock_get_wing.return_value = aeroplane.wings[1]
            section_geometry_service.compute_section_geometry(
                db=None,
                aeroplane_uuid=plane_id,
                request=SectionGeometryRequest(wing_name="h_tail"),
            )
            mock_get_wing.assert_called_once_with(aeroplane, "h_tail")

    def test_no_wings_raises_not_found(self, plane_id):
        aeroplane = _aeroplane_with_wings([])
        with patch.object(
            section_geometry_service, "get_aeroplane_or_raise", return_value=aeroplane
        ):
            with pytest.raises(NotFoundError):
                section_geometry_service.compute_section_geometry(
                    db=None,
                    aeroplane_uuid=plane_id,
                    request=SectionGeometryRequest(),
                )

    def test_aeroplane_not_found_propagates(self, plane_id):
        with patch.object(
            section_geometry_service,
            "get_aeroplane_or_raise",
            side_effect=NotFoundError(message="Aeroplane not found"),
        ):
            with pytest.raises(NotFoundError):
                section_geometry_service.compute_section_geometry(
                    db=None,
                    aeroplane_uuid=plane_id,
                    request=SectionGeometryRequest(),
                )

    def test_cadquery_unavailable_raises_validation_error(self, plane_id):
        aeroplane = _aeroplane_with_wings(["main_wing"])
        with (
            patch.object(
                section_geometry_service, "get_aeroplane_or_raise", return_value=aeroplane
            ),
            patch.object(
                section_geometry_service, "wing_model_to_wing_config", return_value=object()
            ),
            patch.object(
                section_geometry_service,
                "_build_section_geometry",
                side_effect=ValidationError(message="Section geometry is unavailable"),
            ),
        ):
            with pytest.raises(ValidationError):
                section_geometry_service.compute_section_geometry(
                    db=None,
                    aeroplane_uuid=plane_id,
                    request=SectionGeometryRequest(),
                )


class TestBuildSectionGeometryBoundary:
    """Cover the _build_section_geometry seam that translates the platform guard."""

    def test_translates_unavailable_to_validation_error(self):
        import cad_designer.airplane.geometry.section_geometry as sg

        class _Boom:
            def __init__(self, *a, **k):
                raise sg.SectionGeometryUnavailableError("no cadquery")

        with patch.object(sg, "SectionGeometry", _Boom):
            with pytest.raises(ValidationError):
                section_geometry_service._build_section_geometry(object())

    def test_returns_constructed_instance(self):
        import cad_designer.airplane.geometry.section_geometry as sg

        sentinel = object()

        with patch.object(sg, "SectionGeometry", lambda *a, **k: sentinel):
            result = section_geometry_service._build_section_geometry(object())
        assert result is sentinel

    def test_passes_mode_to_section_geometry(self):
        """gh-1046: the seam forwards the requested mode (analytic default)."""
        import cad_designer.airplane.geometry.section_geometry as sg

        seen = {}

        def _capture(wing_config, mode="analytic"):
            seen["mode"] = mode
            return object()

        with patch.object(sg, "SectionGeometry", _capture):
            section_geometry_service._build_section_geometry(object())
        assert seen["mode"] == "analytic"

        with patch.object(sg, "SectionGeometry", _capture):
            section_geometry_service._build_section_geometry(object(), mode="solid")
        assert seen["mode"] == "solid"


# --------------------------------------------------------------------------
# Endpoint-level tests
# --------------------------------------------------------------------------


class TestSectionGeometryEndpoint:
    def test_returns_response_on_success(self, plane_id):
        aeroplane = _aeroplane_with_wings(["main_wing"])
        geom = _StubGeometry()
        p_get, p_conv, p_build = _patch_resolution(aeroplane, geom)
        with p_get, p_conv, p_build:
            result = get_airplane_section_geometry(
                aeroplane_id=plane_id,
                request=SectionGeometryRequest(y_over_span=[0.5], x_over_chord=[0.3]),
                db=None,
            )
        assert len(result.surface) == 1
        assert result.surface[0].thickness == pytest.approx(0.120)

    def test_raises_http_404_on_not_found(self, plane_id):
        with patch.object(
            section_geometry_service,
            "compute_section_geometry",
            side_effect=NotFoundError(message="Aeroplane not found"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                get_airplane_section_geometry(
                    aeroplane_id=plane_id,
                    request=SectionGeometryRequest(),
                    db=None,
                )
        assert exc_info.value.status_code == 404

    def test_raises_http_422_when_cadquery_unavailable(self, plane_id):
        with patch.object(
            section_geometry_service,
            "compute_section_geometry",
            side_effect=ValidationError(message="unavailable"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                get_airplane_section_geometry(
                    aeroplane_id=plane_id,
                    request=SectionGeometryRequest(),
                    db=None,
                )
        assert exc_info.value.status_code == 422
