"""gh-1063: slow/requires_cadquery round-trip for the persisted segment split.

Builds a real single-segment wing via ``/from-wingconfig``, drives the
spar-insert service with a synthetic *telescoping* front-spar plan (so the split
is deterministic and not dependent on the solver's diameter choices), and asserts
END-TO-END through the REAL converters + CAD:

* the persisted wing gains new cross-section rows (the split is materialised),
  with contiguous ``sort_index``;
* the front (main) spar is ``sort_index = 0`` in EVERY sub-segment;
* the rebuilt loft equals the pre-split loft (geometrically transparent — reusing
  the same analytic SectionGeometry check the gh-1064 helper proof uses);
* the secondary (rear) spar is persisted at index >= 1 (Option-B partial span);
* a dry-run writes nothing.
"""

from __future__ import annotations

import json
import uuid as uuid_mod
from pathlib import Path

import pytest

from app.schemas.spar_insert import SparInsertRequest
from app.schemas.spar_plan import MomentSample
from app.services import spar_insert_service
from cad_designer.airplane.aircraft_topology.wing.Airfoil import Airfoil
from cad_designer.airplane.aircraft_topology.wing.TrailingEdgeDevice import (
    TrailingEdgeDevice,
)
from cad_designer.airplane.aircraft_topology.wing.WingConfiguration import (
    WingConfiguration,
)
from cad_designer.airplane.geometry.spar_solver import SparPiece, SparPlan, SparRole

_SAMPLE_Y = [0.1, 0.3, 0.5, 0.7, 0.9]
_SAMPLE_X = [0.2, 0.4, 0.6]


def _airfoil_path() -> str:
    repo_root = Path(__file__).resolve().parents[2]
    return str((repo_root / "components" / "airfoils" / "mh32.dat").resolve())


def _single_segment_wingconfig() -> WingConfiguration:
    """A 600 mm single tapered segment with an aileron — the host to be split."""
    af = _airfoil_path()
    return WingConfiguration(
        nose_pnt=(0.0, 0.0, 0.0),
        root_airfoil=Airfoil(airfoil=af, chord=200.0, dihedral_as_rotation_in_degrees=4.0),
        length=600.0,
        sweep=20.0,
        sweep_is_angle=False,
        tip_airfoil=Airfoil(airfoil=af, chord=120.0),
        number_interpolation_points=101,
        trailing_edge_device=TrailingEdgeDevice(
            name="[aileron]Aileron", rel_chord_root=0.75, rel_chord_tip=0.75
        ),
        symmetric=True,
    )


def _wingconfig_payload(wing_config: WingConfiguration) -> dict:
    state = wing_config.__getstate__()

    class _Enc(json.JSONEncoder):
        def default(self, obj):
            if hasattr(obj, "toTuple"):
                return list(obj.toTuple())
            if hasattr(obj, "x") and hasattr(obj, "y") and hasattr(obj, "z"):
                return [float(obj.x), float(obj.y), float(obj.z)]
            try:
                return float(obj)
            except Exception:
                return str(obj)

    return json.loads(json.dumps(state, cls=_Enc))


def _telescoping_plan() -> SparPlan:
    """Front spar telescoping into two pieces with a joint at y = 300 mm."""

    def piece(role, y, od, idd, length, joint=None, gov=None):
        return SparPiece(
            role=role,
            spare_origin=(0.0, y, 0.0),
            spare_vector=(0.0, 1.0, 0.0),
            outer_d=od,
            inner_d=idd,
            shape="tube",
            governing_y=gov if gov is not None else y,
            utilisation=0.9,
            length=length,
            joint_to_next=joint,
        )

    return SparPlan(
        front_pieces=[
            piece(SparRole.FRONT, 0.0, 18.0, 12.0, 300.0, joint="telescoping"),
            piece(SparRole.FRONT, 300.0, 14.0, 9.0, 300.0),
        ],
        rear_pieces=[piece(SparRole.REAR, 0.0, 8.0, 5.0, 600.0)],
        front_joint="continuous",
        rear_joint="continuous",
    )


def _reload_wing(session_local, plane_uuid: str):
    """Return (db, wing) for the persisted wing — caller closes db."""
    from app.services.wing_service import get_aeroplane_or_raise, get_wing_or_raise

    db = session_local()
    plane = get_aeroplane_or_raise(db, uuid_mod.UUID(plane_uuid))
    return db, get_wing_or_raise(plane, "main_wing")


def _max_section_diff(before: WingConfiguration, after: WingConfiguration) -> float:
    from cad_designer.airplane.geometry.section_geometry import SectionGeometry

    sg_b = SectionGeometry(before, mode="analytic")
    sg_a = SectionGeometry(after, mode="analytic")
    worst = 0.0
    for y in _SAMPLE_Y:
        for x in _SAMPLE_X:
            pb = sg_b.at(y, x)
            pa = sg_a.at(y, x)
            worst = max(
                worst,
                abs(pa.thickness - pb.thickness),
                abs(pa.top_z - pb.top_z),
                abs(pa.bottom_z - pb.bottom_z),
                abs(pa.center_z - pb.center_z),
            )
    return worst


@pytest.fixture()
def aeroplane_with_wing(client_and_db):
    test_client, session_local = client_and_db
    create_plane = test_client.post("/aeroplanes", params={"name": "split RT"})
    assert create_plane.status_code == 201, create_plane.text
    plane_uuid = create_plane.json()["id"]  # the create endpoint returns the UUID
    create_wing = test_client.post(
        f"/aeroplanes/{plane_uuid}/wings/main_wing/from-wingconfig",
        json=_wingconfig_payload(_single_segment_wingconfig()),
    )
    assert create_wing.status_code == 201, create_wing.text
    return test_client, session_local, plane_uuid


def _insert_request(material_id: int, *, dry_run: bool) -> SparInsertRequest:
    return SparInsertRequest(
        material_id=material_id,
        wing_name="main_wing",
        dry_run=dry_run,
        moments=[
            MomentSample(y_span=0.0, bending_moment_Nm=4.0),
            MomentSample(y_span=1.0, bending_moment_Nm=0.0),
        ],
    )


def _first_material_id(session_local) -> int:
    from app.models.component import ComponentModel

    db = session_local()
    try:
        m = db.query(ComponentModel).filter(ComponentModel.component_type == "material").first()
        assert m is not None
        return m.id
    finally:
        db.close()


@pytest.mark.slow
@pytest.mark.requires_cadquery
def test_persisted_split_roundtrip_loft_unchanged_main_index_zero(aeroplane_with_wing):
    from unittest.mock import patch

    from app.converters.model_schema_converters import wing_model_to_wing_config

    test_client, session_local, plane_uuid = aeroplane_with_wing
    material_id = _first_material_id(session_local)
    plan = _telescoping_plan()

    # Pre-split loft (mm WingConfiguration straight from the persisted wing).
    db0, wing0 = _reload_wing(session_local, plane_uuid)
    try:
        before_config = wing_model_to_wing_config(wing0, scale=1000.0)
        n_xsecs_before = len(wing0.x_secs)
    finally:
        db0.close()
    assert n_xsecs_before == 2  # one segment -> root + tip rib

    # Commit through the REAL converters/CAD; only the solver is synthetic.
    db = session_local()
    try:
        with (
            patch.object(spar_insert_service, "compute_spar_plan_object", return_value=plan),
            patch.object(spar_insert_service, "aeroplane_version_service") as mock_ver,
        ):
            mock_ver.snapshot.return_value = type("N", (), {"id": 1})()
            resp = spar_insert_service.insert_spar_plan(
                db=db,
                aeroplane_uuid=uuid_mod.UUID(plane_uuid),
                request=_insert_request(material_id, dry_run=False),
            )
        db.commit()
    finally:
        db.close()

    assert resp.committed is True
    assert resp.planned_segment_lengths is not None
    assert len(resp.planned_segment_lengths) == 2

    # Reload the persisted, split wing.
    db2, wing2 = _reload_wing(session_local, plane_uuid)
    try:
        x_secs = list(wing2.x_secs)
        # one segment split into two -> 3 ribs.
        assert len(x_secs) == 3
        # sort_index contiguous 0..n-1
        assert [x.sort_index for x in x_secs] == [0, 1, 2]
        # the main (front) spar is sort_index 0 in EVERY sub-segment (first two
        # ribs are segment roots; the terminal rib carries no detail).
        for seg_idx in range(2):
            spares = list(x_secs[seg_idx].detail.spares)
            assert spares, f"segment {seg_idx} carries no spar"
            main = spares[0]
            assert main.sort_index == 0
            # front piece OD (mm) -> width in mm stored in DB.
            # seg0 front piece OD = 18 mm, seg1 = 14 mm.
            expected_od = 18.0 if seg_idx == 0 else 14.0
            assert main.spare_support_dimension_width == pytest.approx(expected_od, abs=1e-3)
        # rear (secondary) spar persisted at index >= 1 in the first sub-segment.
        seg0_spares = list(x_secs[0].detail.spares)
        rear = [s for s in seg0_spares if s.spare_support_dimension_width == pytest.approx(8.0)]
        assert rear, "rear (Option-B) spar not persisted"
        assert all(s.sort_index >= 1 for s in rear)

        after_config = wing_model_to_wing_config(wing2, scale=1000.0)
    finally:
        db2.close()

    # The rebuilt loft equals the pre-split loft (geometrically transparent).
    assert _max_section_diff(before_config, after_config) < 1.5


@pytest.mark.slow
@pytest.mark.requires_cadquery
def test_persisted_split_dry_run_writes_nothing(aeroplane_with_wing):
    from unittest.mock import patch

    test_client, session_local, plane_uuid = aeroplane_with_wing
    material_id = _first_material_id(session_local)
    plan = _telescoping_plan()

    db = session_local()
    try:
        with patch.object(spar_insert_service, "compute_spar_plan_object", return_value=plan):
            resp = spar_insert_service.insert_spar_plan(
                db=db,
                aeroplane_uuid=uuid_mod.UUID(plane_uuid),
                request=_insert_request(material_id, dry_run=True),
            )
        db.commit()
    finally:
        db.close()

    assert resp.committed is False
    assert resp.snapshot_id is None
    assert resp.planned_segment_lengths is not None and len(resp.planned_segment_lengths) == 2

    db2, wing2 = _reload_wing(session_local, plane_uuid)
    try:
        # still a single segment (root + tip rib) — nothing was materialised.
        assert len(wing2.x_secs) == 2
    finally:
        db2.close()
