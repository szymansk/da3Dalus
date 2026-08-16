"""gh-1096: the rear-spar hinge-clearance guard must run in PRODUCTION.

`rear_spar_x_c_with_clearance` and its `build_stations_from_geometry` seam have
existed since gh-1059 and are covered by `cad_designer/tests/`. They were never
reached: `spar_plan_service` calls the station builder without
`control_surface_hinge_x_c`, so the parameter defaults to `None` and the guard
returns the request unchanged. A solver-placed rear spar could therefore land
inside a control surface on every production path.

These are fast-tier tests: the station builder is patched, so what is asserted is
the *wiring* — which arguments the service passes — not the geometry, which
`cad_designer/tests/test_spar_clearance_and_secondary.py` already covers.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.schemas.spar_plan import MomentSample, SparPlanRequest
from app.services import spar_plan_service


@dataclass
class _StubStation:
    y_mm: float


def _xsec(hinge_x_c: float | None):
    """A wing cross-section, optionally carrying a control surface.

    `rel_chord_root` is the hinge x/c — it is populated from AeroSandbox's
    `hinge_point` (`app/models/aeroplanemodel.py:320-324`).
    """
    ted = None if hinge_x_c is None else SimpleNamespace(rel_chord_root=hinge_x_c)
    return SimpleNamespace(detail=SimpleNamespace(trailing_edge_device=ted))


def _wing(*hinges: float | None):
    return SimpleNamespace(name="w", x_secs=[_xsec(h) for h in hinges])


def _request(**overrides):
    body: dict = dict(
        material_id=7,
        moments=[
            MomentSample(y_span=0.0, bending_moment_Nm=100.0),
            MomentSample(y_span=1.0, bending_moment_Nm=0.0),
        ],
    )
    body.update(overrides)
    return SparPlanRequest(**body)


def _run_plan(wing, request, captured):
    """Run compute_spar_plan with the solver seam patched, recording kwargs."""
    aeroplane = SimpleNamespace(wings=[wing], uuid=uuid.uuid4())

    def fake_build(geometry, *, x_c=None, moment_fn=None, **kw):
        captured.append({"x_c": x_c, **kw})
        return [_StubStation(0.0), _StubStation(500.0)]

    from cad_designer.airplane.geometry.spar_solver import SparPlan

    patches = [
        patch.object(spar_plan_service, "get_aeroplane_or_raise", return_value=aeroplane),
        patch.object(spar_plan_service, "_resolve_wing", return_value=wing),
        patch.object(spar_plan_service, "wing_model_to_wing_config", return_value=object()),
        patch.object(spar_plan_service, "_build_section_geometry", return_value=object()),
        patch.object(spar_plan_service, "_resolve_sigma_allow", return_value=200.0),
        patch.object(spar_plan_service, "_resolve_g_limit", return_value=3.0),
        patch(
            "cad_designer.airplane.geometry.spar_solver.build_stations_from_geometry",
            side_effect=fake_build,
        ),
        patch(
            "cad_designer.airplane.geometry.spar_solver.solve_spar_plan",
            return_value=SparPlan(),
        ),
    ]

    def _nest(rest):
        if not rest:
            return spar_plan_service.compute_spar_plan(
                db=None, aeroplane_uuid=aeroplane.uuid, request=request
            )
        with rest[0]:
            return _nest(rest[1:])

    return _nest(patches)


class TestHingeReachesTheSolver:
    """The production call path must carry the control-surface hinge."""

    def test_rear_call_site_receives_the_hinge(self):
        """THE defect: today the rear spar is solved with hinge=None."""
        captured: list[dict] = []
        _run_plan(
            _wing(0.60),
            _request(front_x_over_chord=0.25, rear_x_over_chord=0.70),
            captured,
        )
        rear = next(c for c in captured if c["x_c"] == pytest.approx(0.70))
        assert rear.get("control_surface_hinge_x_c") == pytest.approx(0.60), (
            "the rear spar was solved without the control-surface hinge, so the "
            "gh-1059 clearance guard never ran"
        )

    def test_most_forward_hinge_constrains_the_wing(self):
        """A wing carries several control surfaces; the rear spar clears them all.

        The binding one is therefore the most FORWARD hinge, not the first found.
        """
        captured: list[dict] = []
        _run_plan(
            _wing(0.75, 0.55, 0.68),
            _request(rear_x_over_chord=0.70),
            captured,
        )
        rear = next(c for c in captured if c["x_c"] == pytest.approx(0.70))
        assert rear.get("control_surface_hinge_x_c") == pytest.approx(0.55)

    def test_wing_without_control_surfaces_passes_none(self):
        captured: list[dict] = []
        _run_plan(_wing(None, None), _request(rear_x_over_chord=0.70), captured)
        rear = next(c for c in captured if c["x_c"] == pytest.approx(0.70))
        assert rear.get("control_surface_hinge_x_c") is None

    def test_front_spar_is_not_constrained_by_the_hinge(self):
        """Intent, not incident: the guard exists for the REAR/torsion spar.

        The front spar sits far forward of any hinge; constraining it would move
        a spar that has no reason to move.
        """
        captured: list[dict] = []
        _run_plan(
            _wing(0.60),
            _request(front_x_over_chord=0.25, rear_x_over_chord=0.70),
            captured,
        )
        front = next(c for c in captured if c["x_c"] == pytest.approx(0.25))
        assert front.get("control_surface_hinge_x_c") is None


class TestInfeasibilityIsReported:
    """RF-SP-20: an impossible layout is reported, never clamped."""

    def test_geometry_infeasibility_becomes_a_422(self):
        """The solver's refusal must reach the caller as ValidationError.

        The geometry-level behaviour (when the guard refuses) is covered in
        `cad_designer/tests/test_spar_clearance_and_secondary.py`. What is
        asserted here is the *translation*: an untranslated ValueError would
        surface as an opaque 500 and lose the builder-readable message.
        """
        from cad_designer.airplane.geometry.spar_solver import (
            RearSparClearanceInfeasible,
            SparPlan,
        )

        from app.core.exceptions import ValidationError

        wing = _wing(0.06)
        aeroplane = SimpleNamespace(wings=[wing], uuid=uuid.uuid4())
        boom = RearSparClearanceInfeasible(
            "hinge x/c 0.060, clearance 0.030, leaves 0.030 forward of 0.050"
        )

        def fake_build(geometry, *, x_c=None, moment_fn=None, **kw):
            if kw.get("control_surface_hinge_x_c") is not None:
                raise boom
            return [_StubStation(0.0), _StubStation(500.0)]

        patches = [
            patch.object(spar_plan_service, "get_aeroplane_or_raise", return_value=aeroplane),
            patch.object(spar_plan_service, "_resolve_wing", return_value=wing),
            patch.object(spar_plan_service, "wing_model_to_wing_config", return_value=object()),
            patch.object(spar_plan_service, "_build_section_geometry", return_value=object()),
            patch.object(spar_plan_service, "_resolve_sigma_allow", return_value=200.0),
            patch.object(spar_plan_service, "_resolve_g_limit", return_value=3.0),
            patch(
                "cad_designer.airplane.geometry.spar_solver.build_stations_from_geometry",
                side_effect=fake_build,
            ),
            patch(
                "cad_designer.airplane.geometry.spar_solver.solve_spar_plan",
                return_value=SparPlan(),
            ),
        ]

        def _nest(rest):
            if not rest:
                return spar_plan_service.compute_spar_plan(
                    db=None, aeroplane_uuid=aeroplane.uuid, request=_request()
                )
            with rest[0]:
                return _nest(rest[1:])

        with pytest.raises(ValidationError) as exc:
            _nest(patches)
        assert "0.060" in str(exc.value), "the governing numbers must survive translation"
