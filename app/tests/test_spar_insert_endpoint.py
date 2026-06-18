"""gh-1049: Fast-tier tests for the spar-plan → wing insert endpoint + service.

These run on the CI fast tier (no cadquery). We mock the solver/geometry
boundary (``compute_spar_plan_object`` returns a synthetic :class:`SparPlan`) so
the real lofted-solid build never runs, and assert:

- segment resolution from a piece's spanwise span (governing_y → segment),
- the HARD spar_index invariant (front=0 in every segment, same logical spar
  same index across segments, rear=1, reinforcement next),
- dry_run vs commit (commit calls create_spare with the correct sort_index and
  metre dimensions),
- infeasible plan → 422 refusal,
- missing aeroplane / wing → 404,
- unit conversion (mm plan → metre response),
- the already-has-index-0 replace behaviour.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.api.v2.endpoints.aeroanalysis import insert_airplane_spar_plan
from app.core.exceptions import NotFoundError, ValidationError
from app.schemas.spar_insert import SparInsertRequest
from app.schemas.spar_plan import MomentSample
from app.services import spar_insert_service
from cad_designer.airplane.geometry.spar_solver import SparPiece, SparPlan, SparRole


# --------------------------------------------------------------------------
# Stubs
# --------------------------------------------------------------------------


def _piece(role=SparRole.FRONT, y=100.0, governing_y=100.0, **kw):
    defaults = dict(
        role=role,
        spare_origin=(0.0, y, 10.0),
        spare_vector=(0.0, 1.0, 0.0),
        outer_d=20.0,
        inner_d=12.0,
        shape="tube",
        governing_y=governing_y,
        utilisation=0.9,
        length=400.0,
    )
    defaults.update(kw)
    return SparPiece(**defaults)


def _two_segment_plan():
    """A plan whose front spar telescopes across two segments (root + outboard)."""
    return SparPlan(
        front_pieces=[
            _piece(role=SparRole.FRONT, y=0.0, governing_y=50.0, joint_to_next="telescoping"),
            _piece(role=SparRole.FRONT, y=600.0, governing_y=650.0, outer_d=16.0, inner_d=10.0),
        ],
        rear_pieces=[
            _piece(role=SparRole.REAR, y=0.0, governing_y=50.0, outer_d=10.0, inner_d=6.0),
        ],
        front_joint="continuous",
        rear_joint="continuous",
    )


def _single_segment_plan(with_reinforcement=False):
    plan = SparPlan(
        front_pieces=[_piece(role=SparRole.FRONT, y=0.0, governing_y=50.0)],
        rear_pieces=[
            _piece(role=SparRole.REAR, y=0.0, governing_y=50.0, outer_d=10.0, inner_d=6.0)
        ],
        front_joint="continuous",
        rear_joint="continuous",
    )
    if with_reinforcement:
        plan.front_joint = "reinforcement+joiner"
        plan.reinforcement = _piece(
            role=SparRole.FRONT, y=-50.0, governing_y=0.0, outer_d=22.0, inner_d=14.0
        )
    return plan


def _wing(name="main_wing", segment_lengths_mm=(500.0,)):
    """A stub wing whose config exposes segments with mm lengths."""
    segments = [SimpleNamespace(length=length) for length in segment_lengths_mm]
    # x_secs: one per segment + the terminal one.
    x_secs = [SimpleNamespace(sort_index=i) for i in range(len(segment_lengths_mm) + 1)]
    return SimpleNamespace(name=name, x_secs=x_secs, _segments=segments)


def _aeroplane(wings):
    return SimpleNamespace(wings=wings, uuid=uuid.uuid4())


def _request(**overrides):
    body = dict(
        material_id=7,
        moments=[
            MomentSample(y_span=0.0, bending_moment_Nm=100.0),
            MomentSample(y_span=1.0, bending_moment_Nm=0.0),
        ],
    )
    body.update(overrides)
    return SparInsertRequest(**body)


@pytest.fixture()
def plane_id():
    return uuid.uuid4()


def _patch_service(aeroplane, plan, wing=None):
    """Patch the boundaries: aeroplane lookup, wing resolution, plan compute,
    and the wing_config segment provider."""
    wing = wing if wing is not None else aeroplane.wings[0]
    return [
        patch.object(spar_insert_service, "get_aeroplane_or_raise", return_value=aeroplane),
        patch.object(spar_insert_service, "_resolve_wing", return_value=wing),
        patch.object(spar_insert_service, "compute_spar_plan_object", return_value=plan),
        patch.object(
            spar_insert_service,
            "_segment_lengths_mm",
            return_value=[s.length for s in wing._segments],
        ),
    ]


def _run(patches, fn):
    if not patches:
        return fn()
    with patches[0]:
        return _run(patches[1:], fn)


# --------------------------------------------------------------------------
# Segment resolution
# --------------------------------------------------------------------------


class TestSegmentResolution:
    def test_resolves_governing_y_to_segment_index(self):
        # boundaries: seg0 = [0, 500), seg1 = [500, 1100)
        lengths = [500.0, 600.0]
        assert spar_insert_service._segment_for_y(50.0, lengths) == 0
        assert spar_insert_service._segment_for_y(499.0, lengths) == 0
        assert spar_insert_service._segment_for_y(500.0, lengths) == 1
        assert spar_insert_service._segment_for_y(650.0, lengths) == 1
        # beyond the last boundary clamps to the last segment
        assert spar_insert_service._segment_for_y(5000.0, lengths) == 1
        # negative (mirror) clamps to the root segment
        assert spar_insert_service._segment_for_y(-10.0, lengths) == 0


# --------------------------------------------------------------------------
# HARD spar_index invariant
# --------------------------------------------------------------------------


class TestSparIndexInvariant:
    def test_front_is_index_zero_in_every_segment(self, plane_id):
        aeroplane = _aeroplane([_wing(segment_lengths_mm=(500.0, 600.0))])
        resp = _run(
            _patch_service(aeroplane, _two_segment_plan()),
            lambda: spar_insert_service.insert_spar_plan(
                db=None, aeroplane_uuid=plane_id, request=_request(dry_run=True)
            ),
        )
        front = [p for p in resp.planned_spares if p.role == "front"]
        # front spar spans two segments (one piece each), index 0 in both
        segs = {p.segment_index for p in front}
        assert segs == {0, 1}
        for p in front:
            assert p.spar_index == 0

    def test_rear_is_index_one(self, plane_id):
        aeroplane = _aeroplane([_wing(segment_lengths_mm=(500.0, 600.0))])
        resp = _run(
            _patch_service(aeroplane, _two_segment_plan()),
            lambda: spar_insert_service.insert_spar_plan(
                db=None, aeroplane_uuid=plane_id, request=_request(dry_run=True)
            ),
        )
        rear = [p for p in resp.planned_spares if p.role == "rear"]
        assert rear
        for p in rear:
            assert p.spar_index == 1

    def test_reinforcement_gets_next_index(self, plane_id):
        aeroplane = _aeroplane([_wing(segment_lengths_mm=(500.0,))])
        resp = _run(
            _patch_service(aeroplane, _single_segment_plan(with_reinforcement=True)),
            lambda: spar_insert_service.insert_spar_plan(
                db=None, aeroplane_uuid=plane_id, request=_request(dry_run=True)
            ),
        )
        # front=0, rear=1, reinforcement=2 (next), all in the root segment
        by_role = {(p.role, p.spar_index) for p in resp.planned_spares}
        assert ("front", 0) in by_role
        assert ("rear", 1) in by_role
        reinforcements = [p for p in resp.planned_spares if p.spar_index == 2]
        assert len(reinforcements) == 1
        assert reinforcements[0].role == "front"


# --------------------------------------------------------------------------
# dry_run vs commit
# --------------------------------------------------------------------------


class TestDryRunVsCommit:
    def test_dry_run_does_not_persist(self, plane_id):
        aeroplane = _aeroplane([_wing(segment_lengths_mm=(500.0,))])
        with patch.object(spar_insert_service, "_persist_spares") as mock_persist:
            resp = _run(
                _patch_service(aeroplane, _single_segment_plan()),
                lambda: spar_insert_service.insert_spar_plan(
                    db=None, aeroplane_uuid=plane_id, request=_request(dry_run=True)
                ),
            )
        mock_persist.assert_not_called()
        assert resp.committed is False
        assert resp.dry_run is True
        assert len(resp.planned_spares) == 2

    def test_commit_calls_create_spare_with_sort_index_and_metres(self, plane_id):
        aeroplane = _aeroplane([_wing(segment_lengths_mm=(500.0,))])
        captured = []

        def fake_create_spare(db, aeroplane_uuid, wing_name, xsec_index, spare_data):
            captured.append((xsec_index, spare_data))

        with (
            patch.object(spar_insert_service, "create_spare", side_effect=fake_create_spare),
            patch.object(spar_insert_service, "_clear_plan_spares") as mock_clear,
        ):
            resp = _run(
                _patch_service(aeroplane, _single_segment_plan()),
                lambda: spar_insert_service.insert_spar_plan(
                    db=None, aeroplane_uuid=plane_id, request=_request(dry_run=False)
                ),
            )
        assert resp.committed is True
        # both pieces persisted into segment 0
        assert {c[0] for c in captured} == {0}
        assert len(captured) == 2
        # front piece: 20 mm OD -> 0.020 m metre dimensions handed to create_spare
        front_spare = captured[0][1]
        assert front_spare.spare_support_dimension_width == pytest.approx(0.020)
        assert front_spare.spare_support_dimension_height == pytest.approx(0.020)
        assert front_spare.spare_length == pytest.approx(0.400)
        # spare_vector dimensionless, unchanged
        assert front_spare.spare_vector == [0.0, 1.0, 0.0]
        # mode 'normal' so the solved origin/vector are honoured verbatim
        assert front_spare.spare_mode == "normal"
        # existing plan spares cleared before insert (replace behaviour)
        mock_clear.assert_called_once()


# --------------------------------------------------------------------------
# already-has-index-0 replace behaviour
# --------------------------------------------------------------------------


class TestReplaceExistingSpares:
    def test_clear_called_for_each_target_segment_on_commit(self, plane_id):
        aeroplane = _aeroplane([_wing(segment_lengths_mm=(500.0, 600.0))])
        cleared_segments = []

        with (
            patch.object(spar_insert_service, "create_spare"),
            patch.object(
                spar_insert_service,
                "_clear_plan_spares",
                side_effect=lambda db, wing, seg_idx: cleared_segments.append(seg_idx),
            ),
        ):
            _run(
                _patch_service(aeroplane, _two_segment_plan()),
                lambda: spar_insert_service.insert_spar_plan(
                    db=None, aeroplane_uuid=plane_id, request=_request(dry_run=False)
                ),
            )
        # both target segments cleared exactly once (no double-corruption)
        assert sorted(set(cleared_segments)) == [0, 1]


# --------------------------------------------------------------------------
# Infeasible refusal + not-found
# --------------------------------------------------------------------------


class TestInfeasibleAndNotFound:
    def test_infeasible_plan_raises_validation_error(self, plane_id):
        aeroplane = _aeroplane([_wing(segment_lengths_mm=(500.0,))])
        plan = _single_segment_plan()
        plan.feasible = False
        plan.infeasibility_reason = "required OD 96.5 mm exceeds section depth"
        plan.front_pieces[0].feasible = False
        with pytest.raises(ValidationError) as exc:
            _run(
                _patch_service(aeroplane, plan),
                lambda: spar_insert_service.insert_spar_plan(
                    db=None, aeroplane_uuid=plane_id, request=_request(dry_run=False)
                ),
            )
        assert "exceeds section depth" in str(exc.value.message)

    def test_infeasible_refused_even_for_dry_run(self, plane_id):
        aeroplane = _aeroplane([_wing(segment_lengths_mm=(500.0,))])
        plan = _single_segment_plan()
        plan.feasible = False
        plan.infeasibility_reason = "no tube fits"
        with pytest.raises(ValidationError):
            _run(
                _patch_service(aeroplane, plan),
                lambda: spar_insert_service.insert_spar_plan(
                    db=None, aeroplane_uuid=plane_id, request=_request(dry_run=True)
                ),
            )

    def test_aeroplane_not_found_propagates(self, plane_id):
        with patch.object(
            spar_insert_service,
            "get_aeroplane_or_raise",
            side_effect=NotFoundError(message="Aeroplane not found"),
        ):
            with pytest.raises(NotFoundError):
                spar_insert_service.insert_spar_plan(
                    db=None, aeroplane_uuid=plane_id, request=_request()
                )

    def test_wing_not_found_propagates(self, plane_id):
        aeroplane = _aeroplane([_wing()])
        with (
            patch.object(spar_insert_service, "get_aeroplane_or_raise", return_value=aeroplane),
            patch.object(
                spar_insert_service,
                "_resolve_wing",
                side_effect=NotFoundError(message="Wing not found"),
            ),
        ):
            with pytest.raises(NotFoundError):
                spar_insert_service.insert_spar_plan(
                    db=None, aeroplane_uuid=plane_id, request=_request()
                )


# --------------------------------------------------------------------------
# Unit conversion (dry-run response is in metres)
# --------------------------------------------------------------------------


class TestUnitConversion:
    def test_dry_run_dimensions_in_metres(self, plane_id):
        aeroplane = _aeroplane([_wing(segment_lengths_mm=(500.0,))])
        resp = _run(
            _patch_service(aeroplane, _single_segment_plan()),
            lambda: spar_insert_service.insert_spar_plan(
                db=None, aeroplane_uuid=plane_id, request=_request(dry_run=True)
            ),
        )
        front = next(p for p in resp.planned_spares if p.role == "front")
        assert front.outer_d == pytest.approx(0.020)
        assert front.inner_d == pytest.approx(0.012)
        assert front.spare_length == pytest.approx(0.400)
        assert front.spare_origin == pytest.approx([0.0, 0.0, 0.01])
        assert front.spare_vector == [0.0, 1.0, 0.0]


# --------------------------------------------------------------------------
# Endpoint
# --------------------------------------------------------------------------


class TestInsertEndpoint:
    def test_returns_response_on_success(self, plane_id):
        with patch.object(
            spar_insert_service, "insert_spar_plan", return_value="RESULT"
        ) as mock_insert:
            result = insert_airplane_spar_plan(aeroplane_id=plane_id, request=_request(), db=None)
        assert result == "RESULT"
        mock_insert.assert_called_once()

    def test_raises_http_404_on_not_found(self, plane_id):
        with patch.object(
            spar_insert_service,
            "insert_spar_plan",
            side_effect=NotFoundError(message="Aeroplane not found"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                insert_airplane_spar_plan(aeroplane_id=plane_id, request=_request(), db=None)
        assert exc_info.value.status_code == 404

    def test_raises_http_422_on_infeasible(self, plane_id):
        with patch.object(
            spar_insert_service,
            "insert_spar_plan",
            side_effect=ValidationError(message="plan infeasible"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                insert_airplane_spar_plan(aeroplane_id=plane_id, request=_request(), db=None)
        assert exc_info.value.status_code == 422
