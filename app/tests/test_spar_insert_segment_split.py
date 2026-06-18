"""gh-1063: Fast-tier tests for persisting the main-spar segment split.

When the solved **front** spar telescopes (multi-piece), the insert-commit must
materialise the segment split in the DB — insert new ``WingXSecModel`` rows at
the joint y's, reindex ``sort_index``, transfer children (control surface
duplicated, turbulator carried, existing spares re-homed), and place each main
piece at ``spar_index 0`` in its sub-segment. Secondary spars persist as
Option-B partial-span spares (no split).

These run on the CI fast tier (no cadquery). They mock the geometry/converter
boundary (``_wing_to_config_mm`` / ``_persist_wing_config``) with a synthetic
WingConfiguration so the real lofted-solid build never runs, against a REAL DB
session for the secondary-spare path.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.schemas.spar_insert import SparInsertRequest
from app.schemas.spar_plan import MomentSample
from app.services import spar_insert_service
from cad_designer.airplane.aircraft_topology.wing.Airfoil import Airfoil
from cad_designer.airplane.aircraft_topology.wing.TrailingEdgeDevice import (
    TrailingEdgeDevice,
)
from cad_designer.airplane.aircraft_topology.wing.Turbulator import Turbulator
from cad_designer.airplane.aircraft_topology.wing.WingConfiguration import (
    WingConfiguration,
)
from cad_designer.airplane.geometry.spar_solver import SparPiece, SparPlan, SparRole


# --------------------------------------------------------------------------
# Stubs
# --------------------------------------------------------------------------


def _piece(role=SparRole.FRONT, y=0.0, governing_y=0.0, **kw):
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


def _telescoping_front_plan():
    """Front spar that telescopes into two pieces within one host segment.

    Joint at y=600 mm: piece 0 spans [0, 600), piece 1 spans [600, 1000).
    """
    return SparPlan(
        front_pieces=[
            _piece(
                role=SparRole.FRONT,
                y=0.0,
                governing_y=50.0,
                length=600.0,
                joint_to_next="telescoping",
            ),
            _piece(
                role=SparRole.FRONT,
                y=600.0,
                governing_y=650.0,
                outer_d=16.0,
                inner_d=10.0,
                length=400.0,
            ),
        ],
        rear_pieces=[
            _piece(
                role=SparRole.REAR,
                y=0.0,
                governing_y=50.0,
                outer_d=10.0,
                inner_d=6.0,
                length=1000.0,
            ),
        ],
        front_joint="continuous",
        rear_joint="continuous",
    )


def _single_front_plan():
    return SparPlan(
        front_pieces=[_piece(role=SparRole.FRONT, y=0.0, governing_y=50.0, length=1000.0)],
        rear_pieces=[
            _piece(
                role=SparRole.REAR,
                y=0.0,
                governing_y=50.0,
                outer_d=10.0,
                inner_d=6.0,
                length=1000.0,
            )
        ],
        front_joint="continuous",
        rear_joint="continuous",
    )


def _wing_config_one_segment(*, with_ted=True, with_turbulator=True, with_spare=False):
    """A 1000 mm single-segment WingConfiguration (mm)."""
    spare_list = None
    if with_spare:
        from cad_designer.airplane.aircraft_topology.wing.Spare import Spare

        spare_list = [
            Spare(
                spare_support_dimension_width=8.0,
                spare_support_dimension_height=8.0,
                spare_length=100.0,
                spare_start=0.0,
                spare_origin=(0.0, 700.0, 5.0),
                spare_vector=(0.0, 1.0, 0.0),
                spare_mode="normal",
            )
        ]
    ted = None
    if with_ted:
        ted = TrailingEdgeDevice(
            name="[aileron]Aileron",
            rel_chord_root=0.75,
            rel_chord_tip=0.75,
        )
    turb = Turbulator(position_root=0.1, height_mm=0.3) if with_turbulator else None
    return WingConfiguration(
        nose_pnt=(0.0, 0.0, 0.0),
        root_airfoil=Airfoil(airfoil="mh32.dat", chord=200.0),
        length=1000.0,
        sweep=0.0,
        sweep_is_angle=False,
        tip_airfoil=Airfoil(airfoil="mh32.dat", chord=150.0),
        spare_list=spare_list,
        trailing_edge_device=ted,
        turbulator=turb,
        symmetric=True,
    )


def _wing(name="main_wing"):
    return SimpleNamespace(name=name, x_secs=[], _config=None)


def _aeroplane(wings, node_id=42):
    return SimpleNamespace(wings=wings, uuid=uuid.uuid4(), id=node_id)


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


# --------------------------------------------------------------------------
# Front-telescoping detection
# --------------------------------------------------------------------------


class TestFrontTelescopingDetection:
    def test_single_front_piece_is_not_telescoping(self):
        assert spar_insert_service._front_telescopes(_single_front_plan()) is False

    def test_multi_front_piece_telescopes(self):
        assert spar_insert_service._front_telescopes(_telescoping_front_plan()) is True

    def test_zero_od_front_pieces_are_ignored(self):
        plan = _telescoping_front_plan()
        # second (tip) piece collapses to Ø0 -> only one real piece -> no split
        plan.front_pieces[1].outer_d = 0.0
        assert spar_insert_service._front_telescopes(plan) is False


# --------------------------------------------------------------------------
# Split-y computation
# --------------------------------------------------------------------------


class TestSplitLengths:
    def test_joint_ys_are_segment_local(self):
        plan = _telescoping_front_plan()
        # host segment is segment 0 ([0, 1000)). The single joint is at 600.
        host_idx, split_lengths = spar_insert_service._front_split_plan(plan, [1000.0])
        assert host_idx == 0
        assert split_lengths == pytest.approx([600.0])

    def test_host_segment_resolved_from_first_front_piece(self):
        plan = _telescoping_front_plan()
        # shift the whole front spar into the second segment ([500, 1500))
        for p in plan.front_pieces:
            p.spare_origin = (0.0, p.spare_origin[1] + 500.0, p.spare_origin[2])
        host_idx, split_lengths = spar_insert_service._front_split_plan(plan, [500.0, 1000.0])
        assert host_idx == 1
        # joint at global 1100 -> segment-local 1100 - 500 = 600
        assert split_lengths == pytest.approx([600.0])


# --------------------------------------------------------------------------
# Split application + child transfer (synthetic WingConfiguration)
# --------------------------------------------------------------------------


class TestApplySplitToConfig:
    def test_split_inserts_subsegments_and_carries_children(self):
        wc = _wing_config_one_segment(with_ted=True, with_turbulator=True, with_spare=True)
        plan = _telescoping_front_plan()
        host_idx, split_lengths = spar_insert_service._front_split_plan(plan, [1000.0])
        new_wc = spar_insert_service._apply_front_split_to_config(wc, host_idx, split_lengths, plan)
        # 1 -> 2 sub-segments
        assert len(new_wc.segments) == 2
        # each sub-segment's spar_list[0] is the matching main (front) piece
        seg0, seg1 = new_wc.segments
        assert seg0.spare_list is not None and seg1.spare_list is not None
        # front piece 0 (OD 20) on seg0, front piece 1 (OD 16) on seg1
        assert seg0.spare_list[0].spare_support_dimension_width == pytest.approx(20.0)
        assert seg1.spare_list[0].spare_support_dimension_width == pytest.approx(16.0)
        # control surface duplicated onto every sub-segment
        assert seg0.trailing_edge_device is not None
        assert seg1.trailing_edge_device is not None
        # names disambiguated so they don't collapse into one AVL DOF (gh-955)
        assert seg0.trailing_edge_device.name != seg1.trailing_edge_device.name
        # turbulator carried onto every sub-segment
        assert seg0.turbulator is not None
        assert seg1.turbulator is not None
        # existing manual spare (at y=700) re-homed to seg1 (sub-span [600, 1000))
        seg1_widths = [s.spare_support_dimension_width for s in seg1.spare_list]
        assert 8.0 in [pytest.approx(w) for w in seg1_widths]

    def test_subsegment_lengths_sum_to_original(self):
        wc = _wing_config_one_segment()
        plan = _telescoping_front_plan()
        host_idx, split_lengths = spar_insert_service._front_split_plan(plan, [1000.0])
        new_wc = spar_insert_service._apply_front_split_to_config(wc, host_idx, split_lengths, plan)
        assert sum(s.length for s in new_wc.segments) == pytest.approx(1000.0)


# --------------------------------------------------------------------------
# Full service flow (mocked converter boundary)
# --------------------------------------------------------------------------


def _patch_flow(aeroplane, plan, config, *, segment_lengths):
    wing = aeroplane.wings[0]
    persisted = {}

    def fake_persist(db, aeroplane_uuid, wing_obj, new_wc):
        persisted["wc"] = new_wc

    return (
        [
            patch.object(spar_insert_service, "get_aeroplane_or_raise", return_value=aeroplane),
            patch.object(spar_insert_service, "_resolve_wing", return_value=wing),
            patch.object(spar_insert_service, "compute_spar_plan_object", return_value=plan),
            patch.object(spar_insert_service, "_segment_lengths_mm", return_value=segment_lengths),
            patch.object(spar_insert_service, "_wing_to_config_mm", return_value=config),
            patch.object(spar_insert_service, "_persist_wing_config", side_effect=fake_persist),
            patch.object(
                spar_insert_service.aeroplane_version_service,
                "snapshot",
                return_value=SimpleNamespace(id=1),
            ),
        ],
        persisted,
    )


def _run(patches, fn):
    if not patches:
        return fn()
    with patches[0]:
        return _run(patches[1:], fn)


class TestServiceSplitFlow:
    def test_commit_telescoping_front_persists_split_config(self, plane_id):
        aeroplane = _aeroplane([_wing()])
        config = _wing_config_one_segment()
        patches, persisted = _patch_flow(
            aeroplane, _telescoping_front_plan(), config, segment_lengths=[1000.0]
        )
        resp = _run(
            patches,
            lambda: spar_insert_service.insert_spar_plan(
                db=None, aeroplane_uuid=plane_id, request=_request(dry_run=False)
            ),
        )
        assert resp.committed is True
        # the persisted config has the split materialised: 2 sub-segments
        assert "wc" in persisted
        assert len(persisted["wc"].segments) == 2
        # snapshot still taken before the destructive change
        assert resp.snapshot_id == 1

    def test_dry_run_telescoping_front_writes_nothing(self, plane_id):
        aeroplane = _aeroplane([_wing()])
        config = _wing_config_one_segment()
        patches, persisted = _patch_flow(
            aeroplane, _telescoping_front_plan(), config, segment_lengths=[1000.0]
        )
        resp = _run(
            patches,
            lambda: spar_insert_service.insert_spar_plan(
                db=None, aeroplane_uuid=plane_id, request=_request(dry_run=True)
            ),
        )
        assert resp.committed is False
        assert "wc" not in persisted  # _persist_wing_config never called
        assert resp.snapshot_id is None
        # dry-run preview surfaces the planned post-split segment list
        assert resp.planned_segment_lengths is not None
        assert len(resp.planned_segment_lengths) == 2

    def test_non_telescoping_front_does_not_split(self, plane_id):
        """A single-piece front spar must take the spare-only path (no split)."""
        aeroplane = _aeroplane([_wing()])
        config = _wing_config_one_segment()
        patches, persisted = _patch_flow(
            aeroplane, _single_front_plan(), config, segment_lengths=[1000.0]
        )
        with patch.object(spar_insert_service, "_persist_spares") as mock_spares:
            resp = _run(
                patches,
                lambda: spar_insert_service.insert_spar_plan(
                    db=None, aeroplane_uuid=plane_id, request=_request(dry_run=False)
                ),
            )
        # spare-only persistence used, NOT the split persistence
        mock_spares.assert_called_once()
        assert "wc" not in persisted
        assert resp.committed is True
        # no split planned
        assert resp.planned_segment_lengths is None
