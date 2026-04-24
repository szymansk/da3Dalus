"""Extended integration tests for fuselage and fuselage cross-section endpoints.

Covers paths not exercised by the existing unit-mock tests in
test_aeroplane_fuselage_endpoints.py and
test_aeroplane_fuselage_cross_section_endpoints.py.

Uses the shared ``client_and_db`` fixture so requests flow through the
full FastAPI stack (routing, validation, DB) rather than calling
endpoint functions directly with mock objects.
"""

from __future__ import annotations

import uuid

import pytest

from app.tests.conftest import make_aeroplane, make_fuselage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _xsec(xyz=None, a=0.5, b=0.4, n=2.0):
    """Return a valid FuselageXSecSuperEllipseSchema dict."""
    return {"xyz": xyz or [0.0, 0.0, 0.0], "a": a, "b": b, "n": n}


def _fuselage_body(name="fus", x_secs=None):
    """Return a valid FuselageSchema dict (min 2 cross-sections)."""
    if x_secs is None:
        x_secs = [
            _xsec([0.0, 0.0, 0.0]),
            _xsec([0.0, 1.0, 0.0]),
        ]
    return {"name": name, "x_secs": x_secs}


# ---------------------------------------------------------------------------
# GET /aeroplanes/{id}/fuselages  (list fuselage names)
# ---------------------------------------------------------------------------

class TestGetAeroplaneFuselages:
    """Cover get_aeroplane_fuselages endpoint."""

    def test_list_fuselages_empty(self, client_and_db):
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        resp = client.get(f"/aeroplanes/{ap_uuid}/fuselages")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_fuselages_returns_names(self, client_and_db):
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)
            make_fuselage(s, aeroplane_id=ap.id, name="fus_a")
            make_fuselage(s, aeroplane_id=ap.id, name="fus_b")

        resp = client.get(f"/aeroplanes/{ap_uuid}/fuselages")
        assert resp.status_code == 200
        names = resp.json()
        assert set(names) == {"fus_a", "fus_b"}

    def test_list_fuselages_aeroplane_not_found(self, client_and_db):
        client, _ = client_and_db
        resp = client.get(f"/aeroplanes/{uuid.uuid4()}/fuselages")
        assert resp.status_code == 404

    def test_list_fuselages_invalid_uuid(self, client_and_db):
        client, _ = client_and_db
        resp = client.get("/aeroplanes/not-a-uuid/fuselages")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PUT /aeroplanes/{id}/fuselages/{name}  (create)
# ---------------------------------------------------------------------------

class TestCreateFuselage:
    """Cover create_aeroplane_fuselage endpoint."""

    def test_create_fuselage_success(self, client_and_db):
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        body = _fuselage_body("new_fus")
        resp = client.put(f"/aeroplanes/{ap_uuid}/fuselages/new_fus", json=body)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "created"
        assert data["operation"] == "create_aeroplane_fuselage"

        # Verify it shows up in the list
        list_resp = client.get(f"/aeroplanes/{ap_uuid}/fuselages")
        assert "new_fus" in list_resp.json()

    def test_create_fuselage_aeroplane_not_found(self, client_and_db):
        client, _ = client_and_db
        body = _fuselage_body("fus")
        resp = client.put(f"/aeroplanes/{uuid.uuid4()}/fuselages/fus", json=body)
        assert resp.status_code == 404

    def test_create_fuselage_duplicate_name_conflict(self, client_and_db):
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        body = _fuselage_body("dup")
        resp1 = client.put(f"/aeroplanes/{ap_uuid}/fuselages/dup", json=body)
        assert resp1.status_code == 201

        # Second create with same name -> 409
        resp2 = client.put(f"/aeroplanes/{ap_uuid}/fuselages/dup", json=body)
        assert resp2.status_code == 409

    def test_create_fuselage_invalid_body(self, client_and_db):
        """Missing required x_secs field -> 422."""
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        resp = client.put(f"/aeroplanes/{ap_uuid}/fuselages/fus", json={"name": "fus"})
        assert resp.status_code == 422

    def test_create_fuselage_too_few_xsecs(self, client_and_db):
        """x_secs has min_length=2, sending 1 should fail validation."""
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        body = _fuselage_body("fus", x_secs=[_xsec()])
        resp = client.put(f"/aeroplanes/{ap_uuid}/fuselages/fus", json=body)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /aeroplanes/{id}/fuselages/{name}  (update)
# ---------------------------------------------------------------------------

class TestUpdateFuselage:
    """Cover update_aeroplane_fuselage endpoint."""

    def test_update_fuselage_success(self, client_and_db):
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        body = _fuselage_body("upd")
        client.put(f"/aeroplanes/{ap_uuid}/fuselages/upd", json=body)

        updated_body = _fuselage_body("upd", x_secs=[
            _xsec([0, 0, 0], a=1.0),
            _xsec([0, 2, 0], a=1.5),
        ])
        resp = client.post(f"/aeroplanes/{ap_uuid}/fuselages/upd", json=updated_body)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["operation"] == "update_aeroplane_fuselage"

    def test_update_fuselage_aeroplane_not_found(self, client_and_db):
        client, _ = client_and_db
        body = _fuselage_body("fus")
        resp = client.post(f"/aeroplanes/{uuid.uuid4()}/fuselages/fus", json=body)
        assert resp.status_code == 404

    def test_update_fuselage_fuselage_not_found(self, client_and_db):
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        body = _fuselage_body("ghost")
        resp = client.post(f"/aeroplanes/{ap_uuid}/fuselages/ghost", json=body)
        assert resp.status_code == 404

    def test_update_fuselage_invalid_body(self, client_and_db):
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        resp = client.post(f"/aeroplanes/{ap_uuid}/fuselages/x", json={})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /aeroplanes/{id}/fuselages/{name}  (get single)
# ---------------------------------------------------------------------------

class TestGetFuselage:
    """Cover get_aeroplane_fuselage endpoint."""

    def test_get_fuselage_success(self, client_and_db):
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        body = _fuselage_body("read_me")
        client.put(f"/aeroplanes/{ap_uuid}/fuselages/read_me", json=body)

        resp = client.get(f"/aeroplanes/{ap_uuid}/fuselages/read_me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "read_me"
        assert len(data["x_secs"]) == 2

    def test_get_fuselage_aeroplane_not_found(self, client_and_db):
        client, _ = client_and_db
        resp = client.get(f"/aeroplanes/{uuid.uuid4()}/fuselages/any")
        assert resp.status_code == 404

    def test_get_fuselage_fuselage_not_found(self, client_and_db):
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        resp = client.get(f"/aeroplanes/{ap_uuid}/fuselages/nonexistent")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /aeroplanes/{id}/fuselages/{name}
# ---------------------------------------------------------------------------

class TestDeleteFuselage:
    """Cover delete_aeroplane_fuselage endpoint."""

    def test_delete_fuselage_success(self, client_and_db):
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        body = _fuselage_body("del_me")
        client.put(f"/aeroplanes/{ap_uuid}/fuselages/del_me", json=body)

        resp = client.delete(f"/aeroplanes/{ap_uuid}/fuselages/del_me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

        # Confirm it's gone
        list_resp = client.get(f"/aeroplanes/{ap_uuid}/fuselages")
        assert "del_me" not in list_resp.json()

    def test_delete_fuselage_aeroplane_not_found(self, client_and_db):
        client, _ = client_and_db
        resp = client.delete(f"/aeroplanes/{uuid.uuid4()}/fuselages/any")
        assert resp.status_code == 404

    def test_delete_fuselage_fuselage_not_found(self, client_and_db):
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        resp = client.delete(f"/aeroplanes/{ap_uuid}/fuselages/nonexistent")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /aeroplanes/{id}/fuselages/{name}/cross_sections  (list)
# ---------------------------------------------------------------------------

class TestGetFuselageCrossSections:
    """Cover get_aeroplane_fuselage_cross_sections via HTTP."""

    def test_list_cross_sections_success(self, client_and_db):
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        body = _fuselage_body("cs_list")
        client.put(f"/aeroplanes/{ap_uuid}/fuselages/cs_list", json=body)

        resp = client.get(f"/aeroplanes/{ap_uuid}/fuselages/cs_list/cross_sections")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert "a" in data[0]
        assert "b" in data[0]

    def test_list_cross_sections_aeroplane_not_found(self, client_and_db):
        client, _ = client_and_db
        resp = client.get(f"/aeroplanes/{uuid.uuid4()}/fuselages/x/cross_sections")
        assert resp.status_code == 404

    def test_list_cross_sections_fuselage_not_found(self, client_and_db):
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        resp = client.get(f"/aeroplanes/{ap_uuid}/fuselages/nope/cross_sections")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /aeroplanes/{id}/fuselages/{name}/cross_sections  (delete all)
# ---------------------------------------------------------------------------

class TestDeleteAllCrossSections:
    """Cover delete_aeroplane_fuselage_cross_sections via HTTP."""

    def test_delete_all_cross_sections_success(self, client_and_db):
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        body = _fuselage_body("cs_del_all")
        client.put(f"/aeroplanes/{ap_uuid}/fuselages/cs_del_all", json=body)

        resp = client.delete(f"/aeroplanes/{ap_uuid}/fuselages/cs_del_all/cross_sections")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        # Verify they're gone
        list_resp = client.get(f"/aeroplanes/{ap_uuid}/fuselages/cs_del_all/cross_sections")
        assert list_resp.status_code == 200
        assert list_resp.json() == []

    def test_delete_all_cross_sections_aeroplane_not_found(self, client_and_db):
        client, _ = client_and_db
        resp = client.delete(f"/aeroplanes/{uuid.uuid4()}/fuselages/x/cross_sections")
        assert resp.status_code == 404

    def test_delete_all_cross_sections_fuselage_not_found(self, client_and_db):
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        resp = client.delete(f"/aeroplanes/{ap_uuid}/fuselages/nope/cross_sections")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET .../cross_sections/{index}  (get single)
# ---------------------------------------------------------------------------

class TestGetSingleCrossSection:
    """Cover get_aeroplane_fuselage_cross_section via HTTP."""

    def test_get_cross_section_by_index(self, client_and_db):
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        body = _fuselage_body("cs_get", x_secs=[
            _xsec([0, 0, 0], a=0.1),
            _xsec([0, 1, 0], a=0.2),
        ])
        client.put(f"/aeroplanes/{ap_uuid}/fuselages/cs_get", json=body)

        resp = client.get(f"/aeroplanes/{ap_uuid}/fuselages/cs_get/cross_sections/0")
        assert resp.status_code == 200
        assert resp.json()["a"] == pytest.approx(0.1)

        resp1 = client.get(f"/aeroplanes/{ap_uuid}/fuselages/cs_get/cross_sections/1")
        assert resp1.status_code == 200
        assert resp1.json()["a"] == pytest.approx(0.2)

    def test_get_cross_section_index_out_of_range(self, client_and_db):
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        body = _fuselage_body("cs_oor")
        client.put(f"/aeroplanes/{ap_uuid}/fuselages/cs_oor", json=body)

        resp = client.get(f"/aeroplanes/{ap_uuid}/fuselages/cs_oor/cross_sections/99")
        assert resp.status_code == 404

    def test_get_cross_section_negative_index(self, client_and_db):
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        body = _fuselage_body("cs_neg")
        client.put(f"/aeroplanes/{ap_uuid}/fuselages/cs_neg", json=body)

        resp = client.get(f"/aeroplanes/{ap_uuid}/fuselages/cs_neg/cross_sections/-1")
        assert resp.status_code == 404

    def test_get_cross_section_aeroplane_not_found(self, client_and_db):
        client, _ = client_and_db
        resp = client.get(f"/aeroplanes/{uuid.uuid4()}/fuselages/x/cross_sections/0")
        assert resp.status_code == 404

    def test_get_cross_section_fuselage_not_found(self, client_and_db):
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        resp = client.get(f"/aeroplanes/{ap_uuid}/fuselages/nope/cross_sections/0")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST .../cross_sections/{index}  (create / splice)
# ---------------------------------------------------------------------------

class TestCreateCrossSection:
    """Cover create_aeroplane_fuselage_cross_section via HTTP."""

    def test_create_cross_section_append(self, client_and_db):
        """Index -1 appends to the end."""
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        body = _fuselage_body("cs_app")
        client.put(f"/aeroplanes/{ap_uuid}/fuselages/cs_app", json=body)

        new_xs = _xsec([0, 5, 0], a=0.9)
        resp = client.post(
            f"/aeroplanes/{ap_uuid}/fuselages/cs_app/cross_sections/-1",
            json=new_xs,
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "created"

        # Confirm 3 cross-sections now
        list_resp = client.get(f"/aeroplanes/{ap_uuid}/fuselages/cs_app/cross_sections")
        assert len(list_resp.json()) == 3

    def test_create_cross_section_insert_at_start(self, client_and_db):
        """Index 0 inserts at the beginning."""
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        body = _fuselage_body("cs_ins0")
        client.put(f"/aeroplanes/{ap_uuid}/fuselages/cs_ins0", json=body)

        new_xs = _xsec([0, -1, 0], a=0.01)
        resp = client.post(
            f"/aeroplanes/{ap_uuid}/fuselages/cs_ins0/cross_sections/0",
            json=new_xs,
        )
        assert resp.status_code == 201

        # The new xsec should be at index 0
        get_resp = client.get(f"/aeroplanes/{ap_uuid}/fuselages/cs_ins0/cross_sections/0")
        assert get_resp.status_code == 200
        assert get_resp.json()["a"] == pytest.approx(0.01)

    def test_create_cross_section_insert_at_middle(self, client_and_db):
        """Index 1 inserts between existing 0 and 1."""
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        body = _fuselage_body("cs_mid", x_secs=[
            _xsec([0, 0, 0], a=0.1),
            _xsec([0, 2, 0], a=0.3),
        ])
        client.put(f"/aeroplanes/{ap_uuid}/fuselages/cs_mid", json=body)

        new_xs = _xsec([0, 1, 0], a=0.2)
        resp = client.post(
            f"/aeroplanes/{ap_uuid}/fuselages/cs_mid/cross_sections/1",
            json=new_xs,
        )
        assert resp.status_code == 201

        # 3 xsecs total, middle one has a=0.2
        list_resp = client.get(f"/aeroplanes/{ap_uuid}/fuselages/cs_mid/cross_sections")
        xsecs = list_resp.json()
        assert len(xsecs) == 3
        assert xsecs[1]["a"] == pytest.approx(0.2)

    def test_create_cross_section_beyond_end(self, client_and_db):
        """Index >= len(existing) appends (same as -1)."""
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        body = _fuselage_body("cs_big")
        client.put(f"/aeroplanes/{ap_uuid}/fuselages/cs_big", json=body)

        new_xs = _xsec([0, 99, 0], a=9.9)
        resp = client.post(
            f"/aeroplanes/{ap_uuid}/fuselages/cs_big/cross_sections/999",
            json=new_xs,
        )
        assert resp.status_code == 201

        list_resp = client.get(f"/aeroplanes/{ap_uuid}/fuselages/cs_big/cross_sections")
        assert len(list_resp.json()) == 3

    def test_create_cross_section_aeroplane_not_found(self, client_and_db):
        client, _ = client_and_db
        resp = client.post(
            f"/aeroplanes/{uuid.uuid4()}/fuselages/x/cross_sections/0",
            json=_xsec(),
        )
        assert resp.status_code == 404

    def test_create_cross_section_fuselage_not_found(self, client_and_db):
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        resp = client.post(
            f"/aeroplanes/{ap_uuid}/fuselages/nope/cross_sections/0",
            json=_xsec(),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT .../cross_sections/{index}  (update single)
# ---------------------------------------------------------------------------

class TestUpdateCrossSection:
    """Cover update_aeroplane_fuselage_cross_section via HTTP."""

    def test_update_cross_section_success(self, client_and_db):
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        body = _fuselage_body("cs_upd")
        client.put(f"/aeroplanes/{ap_uuid}/fuselages/cs_upd", json=body)

        updated = _xsec([0, 0, 0], a=9.9, b=8.8, n=3.0)
        resp = client.put(
            f"/aeroplanes/{ap_uuid}/fuselages/cs_upd/cross_sections/0",
            json=updated,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        # Verify the update took effect
        get_resp = client.get(f"/aeroplanes/{ap_uuid}/fuselages/cs_upd/cross_sections/0")
        assert get_resp.json()["a"] == pytest.approx(9.9)

    def test_update_cross_section_index_out_of_range(self, client_and_db):
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        body = _fuselage_body("cs_upd_oor")
        client.put(f"/aeroplanes/{ap_uuid}/fuselages/cs_upd_oor", json=body)

        resp = client.put(
            f"/aeroplanes/{ap_uuid}/fuselages/cs_upd_oor/cross_sections/99",
            json=_xsec(),
        )
        assert resp.status_code == 404

    def test_update_cross_section_negative_index(self, client_and_db):
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        body = _fuselage_body("cs_upd_neg")
        client.put(f"/aeroplanes/{ap_uuid}/fuselages/cs_upd_neg", json=body)

        resp = client.put(
            f"/aeroplanes/{ap_uuid}/fuselages/cs_upd_neg/cross_sections/-1",
            json=_xsec(),
        )
        assert resp.status_code == 404

    def test_update_cross_section_aeroplane_not_found(self, client_and_db):
        client, _ = client_and_db
        resp = client.put(
            f"/aeroplanes/{uuid.uuid4()}/fuselages/x/cross_sections/0",
            json=_xsec(),
        )
        assert resp.status_code == 404

    def test_update_cross_section_fuselage_not_found(self, client_and_db):
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        resp = client.put(
            f"/aeroplanes/{ap_uuid}/fuselages/nope/cross_sections/0",
            json=_xsec(),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE .../cross_sections/{index}  (delete single)
# ---------------------------------------------------------------------------

class TestDeleteSingleCrossSection:
    """Cover delete_aeroplane_fuselage_cross_section via HTTP."""

    def test_delete_cross_section_success(self, client_and_db):
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        body = _fuselage_body("cs_del", x_secs=[
            _xsec([0, 0, 0], a=0.1),
            _xsec([0, 1, 0], a=0.2),
            _xsec([0, 2, 0], a=0.3),
        ])
        client.put(f"/aeroplanes/{ap_uuid}/fuselages/cs_del", json=body)

        # Delete the middle one (index 1)
        resp = client.delete(f"/aeroplanes/{ap_uuid}/fuselages/cs_del/cross_sections/1")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        # Verify 2 remain and sort_index is contiguous
        list_resp = client.get(f"/aeroplanes/{ap_uuid}/fuselages/cs_del/cross_sections")
        xsecs = list_resp.json()
        assert len(xsecs) == 2
        assert xsecs[0]["a"] == pytest.approx(0.1)
        assert xsecs[1]["a"] == pytest.approx(0.3)

    def test_delete_cross_section_first(self, client_and_db):
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        body = _fuselage_body("cs_del0", x_secs=[
            _xsec([0, 0, 0], a=0.1),
            _xsec([0, 1, 0], a=0.2),
            _xsec([0, 2, 0], a=0.3),
        ])
        client.put(f"/aeroplanes/{ap_uuid}/fuselages/cs_del0", json=body)

        resp = client.delete(f"/aeroplanes/{ap_uuid}/fuselages/cs_del0/cross_sections/0")
        assert resp.status_code == 200

        list_resp = client.get(f"/aeroplanes/{ap_uuid}/fuselages/cs_del0/cross_sections")
        xsecs = list_resp.json()
        assert len(xsecs) == 2
        assert xsecs[0]["a"] == pytest.approx(0.2)

    def test_delete_cross_section_last(self, client_and_db):
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        body = _fuselage_body("cs_del_last", x_secs=[
            _xsec([0, 0, 0], a=0.1),
            _xsec([0, 1, 0], a=0.2),
            _xsec([0, 2, 0], a=0.3),
        ])
        client.put(f"/aeroplanes/{ap_uuid}/fuselages/cs_del_last", json=body)

        resp = client.delete(f"/aeroplanes/{ap_uuid}/fuselages/cs_del_last/cross_sections/2")
        assert resp.status_code == 200

        list_resp = client.get(f"/aeroplanes/{ap_uuid}/fuselages/cs_del_last/cross_sections")
        xsecs = list_resp.json()
        assert len(xsecs) == 2
        assert xsecs[1]["a"] == pytest.approx(0.2)

    def test_delete_cross_section_index_out_of_range(self, client_and_db):
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        body = _fuselage_body("cs_del_oor")
        client.put(f"/aeroplanes/{ap_uuid}/fuselages/cs_del_oor", json=body)

        resp = client.delete(f"/aeroplanes/{ap_uuid}/fuselages/cs_del_oor/cross_sections/99")
        assert resp.status_code == 404

    def test_delete_cross_section_negative_index(self, client_and_db):
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        body = _fuselage_body("cs_del_neg")
        client.put(f"/aeroplanes/{ap_uuid}/fuselages/cs_del_neg", json=body)

        resp = client.delete(f"/aeroplanes/{ap_uuid}/fuselages/cs_del_neg/cross_sections/-1")
        assert resp.status_code == 404

    def test_delete_cross_section_aeroplane_not_found(self, client_and_db):
        client, _ = client_and_db
        resp = client.delete(f"/aeroplanes/{uuid.uuid4()}/fuselages/x/cross_sections/0")
        assert resp.status_code == 404

    def test_delete_cross_section_fuselage_not_found(self, client_and_db):
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        resp = client.delete(f"/aeroplanes/{ap_uuid}/fuselages/nope/cross_sections/0")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# End-to-end CRUD sequence
# ---------------------------------------------------------------------------

class TestFuselageCrudSequence:
    """Full CRUD lifecycle in a single test to verify state transitions."""

    def test_full_lifecycle(self, client_and_db):
        client, Session = client_and_db
        with Session() as s:
            ap = make_aeroplane(s)
            ap_uuid = str(ap.uuid)

        # 1. Create
        body = _fuselage_body("lifecycle", x_secs=[
            _xsec([0, 0, 0], a=0.5),
            _xsec([0, 1, 0], a=0.6),
        ])
        create_resp = client.put(f"/aeroplanes/{ap_uuid}/fuselages/lifecycle", json=body)
        assert create_resp.status_code == 201

        # 2. Read back
        get_resp = client.get(f"/aeroplanes/{ap_uuid}/fuselages/lifecycle")
        assert get_resp.status_code == 200
        assert get_resp.json()["name"] == "lifecycle"

        # 3. Update
        updated = _fuselage_body("lifecycle", x_secs=[
            _xsec([0, 0, 0], a=1.0),
            _xsec([0, 2, 0], a=1.5),
        ])
        update_resp = client.post(f"/aeroplanes/{ap_uuid}/fuselages/lifecycle", json=updated)
        assert update_resp.status_code == 200

        # 4. Verify update
        get2 = client.get(f"/aeroplanes/{ap_uuid}/fuselages/lifecycle")
        assert get2.json()["x_secs"][0]["a"] == pytest.approx(1.0)

        # 5. Add a cross-section
        add_resp = client.post(
            f"/aeroplanes/{ap_uuid}/fuselages/lifecycle/cross_sections/-1",
            json=_xsec([0, 3, 0], a=2.0),
        )
        assert add_resp.status_code == 201

        # 6. Delete a cross-section
        del_xs_resp = client.delete(
            f"/aeroplanes/{ap_uuid}/fuselages/lifecycle/cross_sections/0",
        )
        assert del_xs_resp.status_code == 200

        # 7. Delete the fuselage
        del_resp = client.delete(f"/aeroplanes/{ap_uuid}/fuselages/lifecycle")
        assert del_resp.status_code == 200

        # 8. Confirm it's gone
        gone_resp = client.get(f"/aeroplanes/{ap_uuid}/fuselages/lifecycle")
        assert gone_resp.status_code == 404
