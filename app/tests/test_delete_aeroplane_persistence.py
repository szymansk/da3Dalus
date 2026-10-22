"""gh-1151: DELETE /aeroplanes/{id} must really delete, not just answer 200.

The commit runs in ``get_db`` after the response is built, so a constraint
violation there is invisible to the client. These tests use a real SQLite
schema and check the rows, not just the status code.
"""

import uuid
from datetime import datetime, timezone

from app.models.aeroplanemodel import AeroplaneModel, BranchModel
from app.models.flight_envelope_model import FlightEnvelopeModel
from app.models.tessellation_cache import TessellationCacheModel


def _create(client) -> dict:
    resp = client.post("/aeroplanes", params={"name": "delete-me"})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _uuid_of(created: dict) -> str:
    return str(created.get("id") or created["uuid"])


def _row(session_factory, aeroplane_uuid: str) -> AeroplaneModel | None:
    with session_factory() as s:
        return s.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_uuid).first()


def test_delete_removes_aeroplane_and_its_versioning_branch(client_and_db):
    client, session_factory = client_and_db
    aeroplane_uuid = _uuid_of(_create(client))

    resp = client.delete(f"/aeroplanes/{aeroplane_uuid}")

    assert resp.status_code == 200, resp.text
    with session_factory() as s:
        assert s.query(AeroplaneModel).count() == 0
        assert s.query(BranchModel).count() == 0


def test_delete_removes_flight_envelope_and_tessellation_cache(client_and_db):
    client, session_factory = client_and_db
    aeroplane_uuid = _uuid_of(_create(client))
    with session_factory() as s:
        aeroplane_id = (
            s.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_uuid).one().id
        )
        s.add(
            FlightEnvelopeModel(
                aeroplane_id=aeroplane_id,
                vn_curve_json={},
                kpis_json={},
                markers_json={},
                assumptions_snapshot={},
                computed_at=datetime.now(timezone.utc),
            )
        )
        s.add(
            TessellationCacheModel(
                aeroplane_id=aeroplane_id,
                component_type="wing",
                component_name="w",
                geometry_hash="h",
                tessellation_json={},
            )
        )
        s.commit()

    resp = client.delete(f"/aeroplanes/{aeroplane_uuid}")

    assert resp.status_code == 200, resp.text
    with session_factory() as s:
        assert s.query(AeroplaneModel).count() == 0
        assert s.query(FlightEnvelopeModel).count() == 0
        assert s.query(TessellationCacheModel).count() == 0


def test_delete_unknown_aeroplane_is_404(client_and_db):
    client, _ = client_and_db
    resp = client.delete(f"/aeroplanes/{uuid.uuid4()}")
    assert resp.status_code == 404


def _id_of(session_factory, aeroplane_uuid: str) -> int:
    with session_factory() as s:
        return s.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_uuid).one().id


def test_delete_removes_operating_points_so_a_new_aeroplane_does_not_inherit_them(
    client_and_db,
):
    from app.models.analysismodels import OperatingPointModel, OperatingPointSetModel

    client, session_factory = client_and_db
    a_uuid = _uuid_of(_create(client))
    a_id = _id_of(session_factory, a_uuid)
    with session_factory() as s:
        s.add(
            OperatingPointModel(
                name="op",
                description="d",
                aircraft_id=a_id,
                velocity=20.0,
                alpha=0.0,
                beta=0.0,
                p=0.0,
                q=0.0,
                r=0.0,
                xyz_ref=[0, 0, 0],
                altitude=0.0,
            )
        )
        s.add(
            OperatingPointSetModel(
                name="set", description="d", aircraft_id=a_id, operating_points=[]
            )
        )
        s.commit()

    assert client.delete(f"/aeroplanes/{a_uuid}").status_code == 200

    b_uuid = _uuid_of(_create(client))
    b_id = _id_of(session_factory, b_uuid)
    assert b_id == a_id, "SQLite reuses the freed integer id; the test relies on it"
    with session_factory() as s:
        assert s.query(OperatingPointModel).filter_by(aircraft_id=b_id).count() == 0
        assert s.query(OperatingPointSetModel).filter_by(aircraft_id=b_id).count() == 0


def test_delete_removes_component_tree_and_construction_parts(client_and_db):
    from app.models.component_tree import ComponentTreeNodeModel
    from app.models.construction_part import ConstructionPartModel

    client, session_factory = client_and_db
    a_uuid = _uuid_of(_create(client))
    other_uuid = str(uuid.uuid4())
    with session_factory() as s:
        part = ConstructionPartModel(aeroplane_id=a_uuid, name="p")
        keep_part = ConstructionPartModel(aeroplane_id=other_uuid, name="keep")
        s.add_all([part, keep_part])
        s.flush()
        root = ComponentTreeNodeModel(aeroplane_id=a_uuid, node_type="group", name="root")
        s.add(root)
        s.flush()
        s.add(
            ComponentTreeNodeModel(
                aeroplane_id=a_uuid,
                node_type="cad_shape",
                name="child",
                parent_id=root.id,
                construction_part_id=part.id,
            )
        )
        s.add(ComponentTreeNodeModel(aeroplane_id=other_uuid, node_type="group", name="keep"))
        s.commit()

    assert client.delete(f"/aeroplanes/{a_uuid}").status_code == 200

    with session_factory() as s:
        assert s.query(ComponentTreeNodeModel).filter_by(aeroplane_id=a_uuid).count() == 0
        assert s.query(ConstructionPartModel).filter_by(aeroplane_id=a_uuid).count() == 0
        # Other aeroplanes' rows are untouched.
        assert s.query(ComponentTreeNodeModel).filter_by(aeroplane_id=other_uuid).count() == 1
        assert s.query(ConstructionPartModel).filter_by(aeroplane_id=other_uuid).count() == 1
