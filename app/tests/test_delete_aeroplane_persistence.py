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
