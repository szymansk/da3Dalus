"""Tests for the tessellation cache service."""

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
