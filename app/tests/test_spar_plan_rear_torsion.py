"""gh-1038: the rear spar is sized from TORSION, not the primary bending moment.

The merged #1029 solver built BOTH the front and rear stations from the same
bending-moment distribution, so the rear spar came out a near-twin of the front.
The rear spar's real job is to react the torsion couple (front+rear form the
couple against wing twist) reacted over the front–rear spar spacing, plus any
genuine secondary bending.

These are fast-tier tests (no cadquery): they exercise the service's rear
moment-driver construction (``_make_rear_moment_fn``) and verify that the
``build_stations_from_geometry`` seam is called with a DIFFERENT moment_fn for
the rear spar than for the front. The torsion source and the spacing reaction
are pure functions, so every branch is covered without a real lofted solid.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.schemas.spar_plan import MomentSample, SparPlanRequest, TorsionSample
from app.services import spar_plan_service


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


# ---------------------------------------------------------------------------
# The torsion driver itself (pure)
# ---------------------------------------------------------------------------


class TestMakeRearMomentFn:
    def test_explicit_torsion_reacted_over_spar_spacing(self):
        """With an explicit T(y), the rear sizing-moment is T(y)/spacing.

        spacing = rear_x_over_chord - front_x_over_chord (chord fraction).
        front=0.25, rear=0.65 -> spacing 0.40 -> rear M = T / 0.40.
        """
        req = _basic_request(
            front_x_over_chord=0.25,
            rear_x_over_chord=0.65,
            torsion_moments=[
                TorsionSample(y_span=0.0, torsion_moment_Nm=20.0),
                TorsionSample(y_span=1.0, torsion_moment_Nm=0.0),
            ],
            rear_secondary_bending_fraction=0.0,
        )
        fn = spar_plan_service._make_rear_moment_fn(req)
        # root: T=20 reacted over spacing 0.40 -> 50 N·m
        assert fn(0.0) == pytest.approx(50.0)
        # tip: zero torsion -> zero
        assert fn(1.0) == pytest.approx(0.0)

    def test_rear_differs_from_front_bending(self):
        """On a wing with real pitching moment the rear driver != front driver."""
        req = _basic_request(
            front_x_over_chord=0.25,
            rear_x_over_chord=0.65,
            torsion_moments=[
                TorsionSample(y_span=0.0, torsion_moment_Nm=20.0),
                TorsionSample(y_span=1.0, torsion_moment_Nm=0.0),
            ],
        )
        front = spar_plan_service._make_moment_fn(req)
        rear = spar_plan_service._make_rear_moment_fn(req)
        assert rear(0.0) != pytest.approx(front(0.0))

    def test_secondary_bending_adds_to_torsion(self):
        """Genuine secondary bending is added on top of the torsion reaction."""
        req = _basic_request(
            front_x_over_chord=0.25,
            rear_x_over_chord=0.65,
            torsion_moments=[
                TorsionSample(y_span=0.0, torsion_moment_Nm=20.0),
                TorsionSample(y_span=1.0, torsion_moment_Nm=0.0),
            ],
            rear_secondary_bending_fraction=0.1,  # 10% of bending
        )
        fn = spar_plan_service._make_rear_moment_fn(req)
        # torsion part 50 + secondary 0.1*100 = 10 -> 60
        assert fn(0.0) == pytest.approx(60.0)

    def test_zero_torsion_falls_back_to_secondary_only(self):
        """Zero torsion -> rear sized by secondary bending only (minimal)."""
        req = _basic_request(
            front_x_over_chord=0.25,
            rear_x_over_chord=0.65,
            torsion_moments=[
                TorsionSample(y_span=0.0, torsion_moment_Nm=0.0),
                TorsionSample(y_span=1.0, torsion_moment_Nm=0.0),
            ],
            rear_secondary_bending_fraction=0.05,
        )
        fn = spar_plan_service._make_rear_moment_fn(req)
        assert fn(0.0) == pytest.approx(5.0)  # 0.05 * 100
        assert fn(1.0) == pytest.approx(0.0)

    def test_no_torsion_supplied_uses_documented_proxy(self):
        """When no T(y) is supplied, derive a defensible proxy from bending.

        T(y) ≈ pitching_moment_proxy_ratio · M(y); the rear driver is then that
        proxy reacted over the spar spacing. The proxy must be SMALLER than the
        front bending moment (the couple is a fraction of the primary load), so
        front≠rear still holds.
        """
        req = _basic_request(
            front_x_over_chord=0.25,
            rear_x_over_chord=0.65,
            pitching_moment_proxy_ratio=0.10,
        )
        front = spar_plan_service._make_moment_fn(req)
        rear = spar_plan_service._make_rear_moment_fn(req)
        # proxy T(0)=0.10*100=10; reacted over 0.40 -> 25 N·m
        assert rear(0.0) == pytest.approx(25.0)
        assert rear(0.0) != pytest.approx(front(0.0))

    def test_front_unset_uses_default_front_fraction_for_spacing(self):
        """When front_x_over_chord is None the spacing uses a default front x/c.

        The front spar then sits at the section max-thickness location, whose x/c
        is unknown a-priori; the spacing falls back to a sane default so the
        torsion reaction is still well-defined.
        """
        req = _basic_request(
            front_x_over_chord=None,
            rear_x_over_chord=0.65,
            torsion_moments=[
                TorsionSample(y_span=0.0, torsion_moment_Nm=20.0),
                TorsionSample(y_span=1.0, torsion_moment_Nm=0.0),
            ],
        )
        fn = spar_plan_service._make_rear_moment_fn(req)
        # default front x/c (DEFAULT_FRONT_X_C) -> spacing = 0.65 - default
        spacing = 0.65 - spar_plan_service._DEFAULT_FRONT_X_C
        assert fn(0.0) == pytest.approx(20.0 / spacing)


# ---------------------------------------------------------------------------
# Integration into compute_spar_plan: rear uses a DIFFERENT driver
# ---------------------------------------------------------------------------


class TestRearSparUsesTorsionDriver:
    def _patches(self, captured):
        aeroplane = SimpleNamespace(wings=[SimpleNamespace(name="w")], uuid=uuid.uuid4())

        def fake_build(geometry, *, x_c=None, moment_fn=None, **kw):
            # Record which moment_fn was used per x_c so we can compare drivers.
            captured.setdefault("calls", []).append((x_c, moment_fn(0.0)))
            return [_StubStation(0.0), _StubStation(500.0)]

        from cad_designer.airplane.geometry.spar_solver import SparPlan

        return aeroplane, [
            patch.object(spar_plan_service, "get_aeroplane_or_raise", return_value=aeroplane),
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

    @staticmethod
    def _run(patches, fn):
        if not patches:
            return fn()
        with patches[0]:
            return TestRearSparUsesTorsionDriver._run(patches[1:], fn)

    def test_front_and_rear_receive_different_moment_fns(self):
        captured: dict = {}
        aeroplane, patches = self._patches(captured)
        req = _basic_request(
            front_x_over_chord=0.25,
            rear_x_over_chord=0.65,
            torsion_moments=[
                TorsionSample(y_span=0.0, torsion_moment_Nm=20.0),
                TorsionSample(y_span=1.0, torsion_moment_Nm=0.0),
            ],
        )
        self._run(
            patches,
            lambda: spar_plan_service.compute_spar_plan(
                db=None, aeroplane_uuid=aeroplane.uuid, request=req
            ),
        )
        calls = dict(captured["calls"])
        front_val = calls[0.25]
        rear_val = calls[0.65]
        # front sees the bending moment (100); rear sees the torsion reaction.
        assert front_val == pytest.approx(100.0)
        assert rear_val == pytest.approx(50.0)
        assert front_val != pytest.approx(rear_val)
