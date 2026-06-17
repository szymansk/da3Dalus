"""gh-1031: Fast-tier tests for the spar-plan endpoint + service.

These run on the CI fast tier (no cadquery). We mock the SectionGeometry build
and the solver seam (build_stations_from_geometry / solve_spar_plan) so the real
lofted-solid build never runs. Endpoint functions are called directly (same
pattern as test_section_geometry_endpoint.py) to avoid the router-registration
guard in main.py.

Coverage targets: material/sigma resolution, g_limit fallback, moment_fn
interpolation, mm->m unit conversion, default wing selection, named-wing
selection, the cadquery-unavailable seam, and error paths (no wings, wing not
found, aeroplane not found, material not found, no allowable stress).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.api.v2.endpoints.aeroanalysis import get_airplane_spar_plan
from app.core.exceptions import NotFoundError, ValidationError
from app.schemas.spar_plan import MomentSample, SparPlanRequest
from app.services import spar_plan_service
from cad_designer.airplane.geometry.spar_solver import (
    SparPiece,
    SparPlan,
    SparRole,
)


# --------------------------------------------------------------------------
# Stubs
# --------------------------------------------------------------------------


def _piece(role=SparRole.FRONT, **kw):
    defaults = dict(
        role=role,
        spare_origin=(0.0, 100.0, 10.0),
        spare_vector=(0.0, 1.0, 0.0),
        outer_d=20.0,
        inner_d=12.0,
        shape="tube",
        governing_y=100.0,
        utilisation=0.9,
    )
    defaults.update(kw)
    return SparPiece(**defaults)


def _stub_plan(with_reinforcement=False):
    plan = SparPlan(
        front_pieces=[_piece(role=SparRole.FRONT)],
        rear_pieces=[_piece(role=SparRole.REAR, outer_d=10.0, inner_d=6.0)],
        front_joint="continuous",
        rear_joint="continuous",
    )
    if with_reinforcement:
        plan.front_joint = "reinforcement+joiner"
        plan.reinforcement = _piece(
            role=SparRole.FRONT, spare_origin=(0.0, -50.0, 5.0), governing_y=0.0
        )
    return plan


@dataclass
class _StubStation:
    y_mm: float


def _basic_request(**overrides):
    body = dict(
        material_id=7,
        moments=[
            MomentSample(y_span=0.0, bending_moment_Nm=100.0),
            MomentSample(y_span=1.0, bending_moment_Nm=0.0),
        ],
    )
    body.update(overrides)
    return SparPlanRequest(**body)


def _aeroplane_with_wings(wing_names):
    wings = [SimpleNamespace(name=n) for n in wing_names]
    return SimpleNamespace(wings=wings, uuid=uuid.uuid4())


@pytest.fixture()
def plane_id():
    return uuid.uuid4()


def _patch_full(aeroplane, plan, stations=None, sigma=200.0, g_limit=4.0):
    """Patch every external boundary the service touches."""
    stations = stations if stations is not None else [_StubStation(0.0), _StubStation(500.0)]
    return [
        patch.object(spar_plan_service, "get_aeroplane_or_raise", return_value=aeroplane),
        patch.object(spar_plan_service, "wing_model_to_wing_config", return_value=object()),
        patch.object(spar_plan_service, "_build_section_geometry", return_value=object()),
        patch.object(spar_plan_service, "_resolve_sigma_allow", return_value=sigma),
        patch.object(spar_plan_service, "_resolve_g_limit", return_value=g_limit),
        patch(
            "cad_designer.airplane.geometry.spar_solver.build_stations_from_geometry",
            return_value=stations,
        ),
        patch(
            "cad_designer.airplane.geometry.spar_solver.solve_spar_plan",
            return_value=plan,
        ),
    ]


def _run(patches, fn):
    if not patches:
        return fn()
    with patches[0]:
        return _run(patches[1:], fn)


# --------------------------------------------------------------------------
# Service: happy path + conversion
# --------------------------------------------------------------------------


class TestComputeSparPlanService:
    def test_returns_converted_plan(self, plane_id):
        aeroplane = _aeroplane_with_wings(["main_wing"])
        resp = _run(
            _patch_full(aeroplane, _stub_plan()),
            lambda: spar_plan_service.compute_spar_plan(
                db=None, aeroplane_uuid=plane_id, request=_basic_request()
            ),
        )
        assert len(resp.front_pieces) == 1
        assert len(resp.rear_pieces) == 1
        assert resp.front_joint == "continuous"
        assert resp.rear_joint == "continuous"
        assert resp.reinforcement is None
        # gh-1037: a feasible plan reports feasible truthfully.
        assert resp.feasible is True
        assert resp.infeasibility_reason is None
        assert resp.front_pieces[0].feasible is True

    def test_infeasible_plan_propagates_to_response(self, plane_id):
        # gh-1037: when the solver marks a piece/plan infeasible, the API must
        # report it (not return a fake feasible plan).
        aeroplane = _aeroplane_with_wings(["main_wing"])
        plan = _stub_plan()
        plan.front_pieces[0].feasible = False
        plan.front_pieces[0].infeasibility_reason = "required OD 96.5 mm exceeds section depth"
        plan.front_pieces[0].utilisation = 2.6
        plan.feasible = False
        plan.infeasibility_reason = plan.front_pieces[0].infeasibility_reason
        resp = _run(
            _patch_full(aeroplane, plan),
            lambda: spar_plan_service.compute_spar_plan(
                db=None, aeroplane_uuid=plane_id, request=_basic_request()
            ),
        )
        assert resp.feasible is False
        assert "exceeds section depth" in resp.infeasibility_reason
        assert resp.front_pieces[0].feasible is False
        assert resp.front_pieces[0].utilisation == pytest.approx(2.6)

    def test_mm_to_m_conversion(self, plane_id):
        aeroplane = _aeroplane_with_wings(["main_wing"])
        resp = _run(
            _patch_full(aeroplane, _stub_plan()),
            lambda: spar_plan_service.compute_spar_plan(
                db=None, aeroplane_uuid=plane_id, request=_basic_request()
            ),
        )
        fp = resp.front_pieces[0]
        # 20 mm OD -> 0.020 m, 12 mm ID -> 0.012 m, wall (20-12)/2=4 mm -> 0.004 m.
        assert fp.outer_d == pytest.approx(0.020)
        assert fp.inner_d == pytest.approx(0.012)
        assert fp.wall == pytest.approx(0.004)
        # origin (0,100,10) mm -> (0,0.1,0.01) m
        assert fp.spare_origin == pytest.approx([0.0, 0.1, 0.01])
        # governing_y 100 mm -> 0.1 m
        assert fp.governing_y == pytest.approx(0.1)
        # direction vector is dimensionless (unchanged)
        assert fp.spare_vector == [0.0, 1.0, 0.0]
        assert fp.role == "front"

    def test_reinforcement_converted_when_present(self, plane_id):
        aeroplane = _aeroplane_with_wings(["main_wing"])
        resp = _run(
            _patch_full(aeroplane, _stub_plan(with_reinforcement=True)),
            lambda: spar_plan_service.compute_spar_plan(
                db=None, aeroplane_uuid=plane_id, request=_basic_request()
            ),
        )
        assert resp.front_joint == "reinforcement+joiner"
        assert resp.reinforcement is not None
        assert resp.reinforcement.spare_origin == pytest.approx([0.0, -0.05, 0.005])

    def test_named_wing_selected(self, plane_id):
        aeroplane = _aeroplane_with_wings(["main_wing", "h_tail"])
        with patch.object(
            spar_plan_service, "get_wing_or_raise", return_value=aeroplane.wings[1]
        ) as mock_get_wing:
            _run(
                _patch_full(aeroplane, _stub_plan()),
                lambda: spar_plan_service.compute_spar_plan(
                    db=None,
                    aeroplane_uuid=plane_id,
                    request=_basic_request(wing_name="h_tail"),
                ),
            )
            mock_get_wing.assert_called_once_with(aeroplane, "h_tail")

    def test_solver_receives_mirrored_left_halves(self, plane_id):
        """The left-half stations must be the y-negated mirror of the right half."""
        aeroplane = _aeroplane_with_wings(["main_wing"])
        captured = {}

        def fake_solve(front_left, front_right, rear_left, rear_right, **kw):
            captured["front_left"] = front_left
            captured["front_right"] = front_right
            return _stub_plan()

        stations = [_StubStation(0.0), _StubStation(500.0)]
        patches = [
            patch.object(spar_plan_service, "get_aeroplane_or_raise", return_value=aeroplane),
            patch.object(spar_plan_service, "wing_model_to_wing_config", return_value=object()),
            patch.object(spar_plan_service, "_build_section_geometry", return_value=object()),
            patch.object(spar_plan_service, "_resolve_sigma_allow", return_value=200.0),
            patch.object(spar_plan_service, "_resolve_g_limit", return_value=4.0),
            patch(
                "cad_designer.airplane.geometry.spar_solver.build_stations_from_geometry",
                return_value=stations,
            ),
            patch(
                "cad_designer.airplane.geometry.spar_solver.solve_spar_plan",
                side_effect=fake_solve,
            ),
        ]
        _run(
            patches,
            lambda: spar_plan_service.compute_spar_plan(
                db=None, aeroplane_uuid=plane_id, request=_basic_request()
            ),
        )
        assert [s.y_mm for s in captured["front_right"]] == [0.0, 500.0]
        assert [s.y_mm for s in captured["front_left"]] == [0.0, -500.0]


# --------------------------------------------------------------------------
# Service: resolution helpers
# --------------------------------------------------------------------------


class TestResolveWing:
    def test_no_wings_raises_not_found(self, plane_id):
        aeroplane = _aeroplane_with_wings([])
        with pytest.raises(NotFoundError):
            spar_plan_service._resolve_wing(aeroplane, _basic_request())

    def test_aeroplane_not_found_propagates(self, plane_id):
        with patch.object(
            spar_plan_service,
            "get_aeroplane_or_raise",
            side_effect=NotFoundError(message="Aeroplane not found"),
        ):
            with pytest.raises(NotFoundError):
                spar_plan_service.compute_spar_plan(
                    db=None, aeroplane_uuid=plane_id, request=_basic_request()
                )


class TestResolveSigmaAllow:
    def test_override_wins(self):
        req = _basic_request(sigma_allow_mpa_override=333.0)
        assert spar_plan_service._resolve_sigma_allow(db=None, request=req) == 333.0

    def test_material_value_used(self):
        material = SimpleNamespace(name="CFRP", specs={"allowable_bending_stress_mpa": 250.0})
        db = SimpleNamespace(
            query=lambda *a: SimpleNamespace(
                filter=lambda *a, **k: SimpleNamespace(first=lambda: material)
            )
        )
        assert spar_plan_service._resolve_sigma_allow(db=db, request=_basic_request()) == 250.0

    def test_material_not_found_raises_validation(self):
        db = SimpleNamespace(
            query=lambda *a: SimpleNamespace(
                filter=lambda *a, **k: SimpleNamespace(first=lambda: None)
            )
        )
        with pytest.raises(ValidationError):
            spar_plan_service._resolve_sigma_allow(db=db, request=_basic_request())

    def test_non_positive_sigma_raises_validation(self):
        material = SimpleNamespace(name="foam", specs={"allowable_bending_stress_mpa": 0.0})
        db = SimpleNamespace(
            query=lambda *a: SimpleNamespace(
                filter=lambda *a, **k: SimpleNamespace(first=lambda: material)
            )
        )
        with pytest.raises(ValidationError):
            spar_plan_service._resolve_sigma_allow(db=db, request=_basic_request())

    def test_missing_specs_raises_validation(self):
        material = SimpleNamespace(name="unknown", specs=None)
        db = SimpleNamespace(
            query=lambda *a: SimpleNamespace(
                filter=lambda *a, **k: SimpleNamespace(first=lambda: material)
            )
        )
        with pytest.raises(ValidationError):
            spar_plan_service._resolve_sigma_allow(db=db, request=_basic_request())


class TestResolveGLimit:
    def test_uses_assumption_when_present(self, plane_id):
        with patch(
            "app.services.design_assumptions_service.get_effective_assumption",
            return_value=5.0,
        ):
            assert spar_plan_service._resolve_g_limit(db=None, aeroplane_uuid=plane_id) == 5.0

    def test_falls_back_to_default(self, plane_id):
        with patch(
            "app.services.design_assumptions_service.get_effective_assumption",
            return_value=None,
        ):
            assert (
                spar_plan_service._resolve_g_limit(db=None, aeroplane_uuid=plane_id)
                == spar_plan_service._G_LIMIT_DEFAULT
            )


class TestMomentFn:
    def test_interpolates_and_clamps(self):
        req = _basic_request(
            moments=[
                MomentSample(y_span=0.0, bending_moment_Nm=100.0),
                MomentSample(y_span=0.5, bending_moment_Nm=40.0),
                MomentSample(y_span=1.0, bending_moment_Nm=0.0),
            ]
        )
        fn = spar_plan_service._make_moment_fn(req)
        assert fn(0.0) == pytest.approx(100.0)
        assert fn(0.25) == pytest.approx(70.0)  # midpoint of 100..40
        assert fn(0.5) == pytest.approx(40.0)
        assert fn(1.0) == pytest.approx(0.0)
        # clamp below / above the sampled range
        assert fn(-1.0) == pytest.approx(100.0)
        assert fn(2.0) == pytest.approx(0.0)

    def test_uses_absolute_moment(self):
        req = _basic_request(
            moments=[
                MomentSample(y_span=0.0, bending_moment_Nm=-80.0),
                MomentSample(y_span=1.0, bending_moment_Nm=-20.0),
            ]
        )
        fn = spar_plan_service._make_moment_fn(req)
        assert fn(0.0) == pytest.approx(80.0)
        assert fn(1.0) == pytest.approx(20.0)

    def test_unsorted_input_is_sorted(self):
        req = _basic_request(
            moments=[
                MomentSample(y_span=1.0, bending_moment_Nm=0.0),
                MomentSample(y_span=0.0, bending_moment_Nm=100.0),
            ]
        )
        fn = spar_plan_service._make_moment_fn(req)
        assert fn(0.0) == pytest.approx(100.0)
        assert fn(1.0) == pytest.approx(0.0)

    def test_duplicate_y_resolves_to_first_match(self):
        req = _basic_request(
            moments=[
                MomentSample(y_span=0.0, bending_moment_Nm=100.0),
                MomentSample(y_span=0.5, bending_moment_Nm=60.0),
                MomentSample(y_span=0.5, bending_moment_Nm=30.0),
                MomentSample(y_span=1.0, bending_moment_Nm=0.0),
            ]
        )
        fn = spar_plan_service._make_moment_fn(req)
        # querying exactly the duplicated y resolves via the first matching pair
        assert fn(0.5) == pytest.approx(60.0)
        # interior of the second (post-duplicate) segment still interpolates
        assert fn(0.75) == pytest.approx(15.0)


class TestBuildSectionGeometryBoundary:
    def test_translates_unavailable_to_validation_error(self):
        import cad_designer.airplane.geometry.section_geometry as sg

        class _Boom:
            def __init__(self, *a, **k):
                raise sg.SectionGeometryUnavailableError("no cadquery")

        with patch.object(sg, "SectionGeometry", _Boom):
            with pytest.raises(ValidationError):
                spar_plan_service._build_section_geometry(object())

    def test_returns_constructed_instance(self):
        import cad_designer.airplane.geometry.section_geometry as sg

        sentinel = object()
        with patch.object(sg, "SectionGeometry", lambda *a, **k: sentinel):
            assert spar_plan_service._build_section_geometry(object()) is sentinel

    def test_cadquery_unavailable_surfaces_as_validation(self, plane_id):
        aeroplane = _aeroplane_with_wings(["main_wing"])
        with (
            patch.object(spar_plan_service, "get_aeroplane_or_raise", return_value=aeroplane),
            patch.object(spar_plan_service, "wing_model_to_wing_config", return_value=object()),
            patch.object(spar_plan_service, "_resolve_sigma_allow", return_value=200.0),
            patch.object(spar_plan_service, "_resolve_g_limit", return_value=3.0),
            patch.object(
                spar_plan_service,
                "_build_section_geometry",
                side_effect=ValidationError(message="unavailable"),
            ),
        ):
            with pytest.raises(ValidationError):
                spar_plan_service.compute_spar_plan(
                    db=None, aeroplane_uuid=plane_id, request=_basic_request()
                )


# --------------------------------------------------------------------------
# Endpoint
# --------------------------------------------------------------------------


class TestSparPlanEndpoint:
    def test_returns_response_on_success(self, plane_id):
        with patch.object(
            spar_plan_service, "compute_spar_plan", return_value="RESULT"
        ) as mock_compute:
            result = get_airplane_spar_plan(
                aeroplane_id=plane_id, request=_basic_request(), db=None
            )
        assert result == "RESULT"
        mock_compute.assert_called_once()

    def test_raises_http_404_on_not_found(self, plane_id):
        with patch.object(
            spar_plan_service,
            "compute_spar_plan",
            side_effect=NotFoundError(message="Aeroplane not found"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                get_airplane_spar_plan(aeroplane_id=plane_id, request=_basic_request(), db=None)
        assert exc_info.value.status_code == 404

    def test_raises_http_422_on_validation_error(self, plane_id):
        with patch.object(
            spar_plan_service,
            "compute_spar_plan",
            side_effect=ValidationError(message="unavailable"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                get_airplane_spar_plan(aeroplane_id=plane_id, request=_basic_request(), db=None)
        assert exc_info.value.status_code == 422
