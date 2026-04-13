"""Tests for the tessellation cache service and endpoint."""

import pytest

from app.services import tessellation_cache_service as cache_svc


@pytest.fixture()
def db_session(client_and_db):
    """Provide a DB session for direct service tests."""
    _, SessionLocal = client_and_db
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture()
def aeroplane_id(client_and_db):
    """Create a test aeroplane and return its internal DB id."""
    client, SessionLocal = client_and_db
    resp = client.post("/aeroplanes", params={"name": "cache_test"})
    assert resp.status_code == 201
    aeroplane_uuid = resp.json()["id"]
    # Resolve UUID to internal integer id
    from app.models.aeroplanemodel import AeroplaneModel
    session = SessionLocal()
    aeroplane = session.query(AeroplaneModel).filter(
        AeroplaneModel.uuid == aeroplane_uuid
    ).first()
    yield aeroplane.id
    session.close()


@pytest.fixture()
def aeroplane_uuid_and_id(client_and_db):
    """Create a test aeroplane and return (uuid, internal_id)."""
    client, SessionLocal = client_and_db
    resp = client.post("/aeroplanes", params={"name": "tess_endpoint_test"})
    assert resp.status_code == 201
    aeroplane_uuid = resp.json()["id"]
    from app.models.aeroplanemodel import AeroplaneModel
    session = SessionLocal()
    aeroplane = session.query(AeroplaneModel).filter(
        AeroplaneModel.uuid == aeroplane_uuid
    ).first()
    result = (aeroplane_uuid, aeroplane.id)
    session.close()
    return result


class TestGeometryHash:
    def test_hash_is_deterministic(self):
        data = {"x_secs": [{"chord": 0.15, "airfoil": "mh32"}]}
        h1 = cache_svc.compute_geometry_hash(data)
        h2 = cache_svc.compute_geometry_hash(data)
        assert h1 == h2

    def test_hash_changes_on_data_change(self):
        data_a = {"x_secs": [{"chord": 0.15}]}
        data_b = {"x_secs": [{"chord": 0.20}]}
        assert cache_svc.compute_geometry_hash(data_a) != cache_svc.compute_geometry_hash(data_b)

    def test_hash_is_16_chars(self):
        h = cache_svc.compute_geometry_hash({"test": True})
        assert len(h) == 16


class TestCacheCRUD:
    def test_cache_and_retrieve(self, db_session, aeroplane_id):
        cache_svc.cache_tessellation(
            db_session, aeroplane_id,
            component_type="wing",
            component_name="main_wing",
            geometry_hash="abc123",
            tessellation_json={"shapes": {"version": 3}},
        )
        cached = cache_svc.get_cached(db_session, aeroplane_id, "wing", "main_wing")
        assert cached is not None
        assert cached.geometry_hash == "abc123"
        assert cached.tessellation_json["shapes"]["version"] == 3
        assert cached.is_stale is False

    def test_cache_update_overwrites(self, db_session, aeroplane_id):
        cache_svc.cache_tessellation(
            db_session, aeroplane_id, "wing", "main_wing", "hash1", {"v": 1},
        )
        cache_svc.cache_tessellation(
            db_session, aeroplane_id, "wing", "main_wing", "hash2", {"v": 2},
        )
        cached = cache_svc.get_cached(db_session, aeroplane_id, "wing", "main_wing")
        assert cached.geometry_hash == "hash2"
        assert cached.tessellation_json == {"v": 2}

    def test_get_all_cached(self, db_session, aeroplane_id):
        cache_svc.cache_tessellation(db_session, aeroplane_id, "wing", "w1", "h1", {})
        cache_svc.cache_tessellation(db_session, aeroplane_id, "wing", "w2", "h2", {})
        cache_svc.cache_tessellation(db_session, aeroplane_id, "fuselage", "f1", "h3", {})
        all_cached = cache_svc.get_all_cached(db_session, aeroplane_id)
        assert len(all_cached) == 3

    def test_get_cached_returns_none_when_missing(self, db_session, aeroplane_id):
        assert cache_svc.get_cached(db_session, aeroplane_id, "wing", "nope") is None


class TestInvalidation:
    def test_invalidate_marks_stale(self, db_session, aeroplane_id):
        cache_svc.cache_tessellation(db_session, aeroplane_id, "wing", "w1", "h", {})
        count = cache_svc.invalidate(db_session, aeroplane_id)
        assert count == 1
        cached = cache_svc.get_cached(db_session, aeroplane_id, "wing", "w1")
        assert cached.is_stale is True

    def test_invalidate_specific_component(self, db_session, aeroplane_id):
        cache_svc.cache_tessellation(db_session, aeroplane_id, "wing", "w1", "h1", {})
        cache_svc.cache_tessellation(db_session, aeroplane_id, "wing", "w2", "h2", {})
        count = cache_svc.invalidate(
            db_session, aeroplane_id, component_type="wing", component_name="w1",
        )
        assert count == 1
        assert cache_svc.get_cached(db_session, aeroplane_id, "wing", "w1").is_stale is True
        assert cache_svc.get_cached(db_session, aeroplane_id, "wing", "w2").is_stale is False

    def test_invalidate_idempotent(self, db_session, aeroplane_id):
        cache_svc.cache_tessellation(db_session, aeroplane_id, "wing", "w1", "h", {})
        cache_svc.invalidate(db_session, aeroplane_id)
        count = cache_svc.invalidate(db_session, aeroplane_id)
        assert count == 0  # already stale


class TestHashCurrent:
    def test_hash_current_when_matching(self, db_session, aeroplane_id):
        cache_svc.cache_tessellation(db_session, aeroplane_id, "wing", "w1", "hash_a", {})
        assert cache_svc.is_hash_current(db_session, aeroplane_id, "wing", "w1", "hash_a") is True

    def test_hash_not_current_when_changed(self, db_session, aeroplane_id):
        cache_svc.cache_tessellation(db_session, aeroplane_id, "wing", "w1", "hash_a", {})
        assert cache_svc.is_hash_current(db_session, aeroplane_id, "wing", "w1", "hash_b") is False

    def test_hash_current_when_no_cache(self, db_session, aeroplane_id):
        assert cache_svc.is_hash_current(db_session, aeroplane_id, "wing", "w1", "any") is True


class TestAeroplaneTessellationEndpoint:
    """Tests for GET /aeroplanes/{id}/tessellation."""

    def test_returns_404_when_no_cache(self, client_and_db):
        """GET tessellation with no cached entries returns 404."""
        client, SessionLocal = client_and_db
        resp = client.post("/aeroplanes", params={"name": "no_cache_plane"})
        assert resp.status_code == 201
        aeroplane_uuid = resp.json()["id"]

        resp = client.get(f"/aeroplanes/{aeroplane_uuid}/tessellation")
        assert resp.status_code == 404
        assert "No cached tessellations" in resp.json()["detail"]

    def test_returns_assembled_scene(self, client_and_db, aeroplane_uuid_and_id):
        """GET tessellation assembles cached entries into a three-cad-viewer scene."""
        client, SessionLocal = client_and_db
        aeroplane_uuid, aeroplane_internal_id = aeroplane_uuid_and_id

        session = SessionLocal()
        # Cache two wing tessellations
        wing_tess = {
            "data": {
                "shapes": {
                    "version": 3,
                    "name": "main_wing",
                    "id": "/main_wing",
                    "parts": [],
                    "loc": [[0, 0, 0], [0, 0, 0, 1]],
                    "bb": {"min": [-1, -2, -3], "max": [1, 2, 3]},
                },
                "instances": [{"id": "/main_wing", "shape": "/main_wing"}],
            },
            "type": "data",
            "count": 42,
        }
        cache_svc.cache_tessellation(
            session, aeroplane_internal_id,
            "wing", "main_wing", "hash_mw", wing_tess,
        )

        tail_tess = {
            "data": {
                "shapes": {
                    "version": 3,
                    "name": "tail",
                    "id": "/tail",
                    "parts": [],
                    "loc": [[0, 0, 0], [0, 0, 0, 1]],
                    "bb": {"min": [5, -1, 0], "max": [7, 1, 1]},
                },
                "instances": [{"id": "/tail", "shape": "/tail"}],
            },
            "type": "data",
            "count": 18,
        }
        cache_svc.cache_tessellation(
            session, aeroplane_internal_id,
            "wing", "tail", "hash_tail", tail_tess,
        )
        session.close()

        resp = client.get(f"/aeroplanes/{aeroplane_uuid}/tessellation")
        assert resp.status_code == 200

        body = resp.json()
        assert body["type"] == "data"
        assert body["count"] == 60  # 42 + 18
        assert body["is_stale"] is False
        assert body["config"] == {"theme": "dark"}

        shapes = body["data"]["shapes"]
        assert shapes["version"] == 3
        assert shapes["name"] == "tess_endpoint_test"
        assert len(shapes["parts"]) == 2

        # Combined bounding box
        bb = shapes["bb"]
        assert bb["min"] == [-1, -2, -3]
        assert bb["max"] == [7, 2, 3]

        # Combined instances
        assert len(body["data"]["instances"]) == 2

    def test_is_stale_flag_propagates(self, client_and_db, aeroplane_uuid_and_id):
        """is_stale is True when any cached entry is stale."""
        client, SessionLocal = client_and_db
        aeroplane_uuid, aeroplane_internal_id = aeroplane_uuid_and_id

        session = SessionLocal()
        tess = {
            "data": {
                "shapes": {"version": 3, "bb": {"min": [0, 0, 0], "max": [1, 1, 1]}},
                "instances": [],
            },
            "type": "data",
            "count": 5,
        }
        cache_svc.cache_tessellation(
            session, aeroplane_internal_id, "wing", "w1", "h1", tess,
        )
        cache_svc.cache_tessellation(
            session, aeroplane_internal_id, "wing", "w2", "h2", tess,
        )
        # Mark one stale
        cache_svc.invalidate(
            session, aeroplane_internal_id,
            component_type="wing", component_name="w1",
        )
        session.close()

        resp = client.get(f"/aeroplanes/{aeroplane_uuid}/tessellation")
        assert resp.status_code == 200
        assert resp.json()["is_stale"] is True
