"""Tests for spar PUT/DELETE (#96) and TED direct-access endpoints (#97).

Uses the wingconfig API to seed a wing with one segment + one spar + one TED,
then exercises the new CRUD endpoints.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

airfoil_path = str(
    (Path(__file__).resolve().parents[2] / "components" / "airfoils" / "mh32.dat").resolve()
)


@pytest.fixture()
def client(client_and_db):
    c, _ = client_and_db
    yield c


@pytest.fixture()
def db(client_and_db):
    _, SessionLocal = client_and_db
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _seed_wing(client: TestClient, name: str = "crud_test", *, db=None) -> str:
    """Create an aeroplane with a wing that has 1 spar + 1 TED on xsec 0.

    The wing is created via wingconfig (design_model='wc') and then
    flipped to 'asb' so that the ASB spar/TED CRUD endpoints can
    operate on it.
    """
    from app.models.aeroplanemodel import AeroplaneModel, WingModel

    resp = client.post("/aeroplanes", params={"name": name})
    assert resp.status_code == 201
    aeroplane_id = resp.json()["id"]

    wc = {
        "segments": [
            {
                "root_airfoil": {"airfoil": airfoil_path, "chord": 150.0, "incidence": 0},
                "tip_airfoil": {"airfoil": airfoil_path, "chord": 120.0, "incidence": 0},
                "length": 500.0,
                "sweep": 10.0,
                "number_interpolation_points": 101,
                "spare_list": [
                    {
                        "spare_support_dimension_width": 5.0,
                        "spare_support_dimension_height": 5.0,
                        "spare_position_factor": 0.25,
                        "spare_start": 0.0,
                        "spare_mode": "standard",
                        "spare_vector": [0, 1, 0],
                        "spare_origin": [0, 0, 0],
                    }
                ],
                "trailing_edge_device": {
                    "name": "aileron",
                    "rel_chord_root": 0.8,
                    "rel_chord_tip": 0.8,
                    "positive_deflection_deg": 25,
                    "negative_deflection_deg": 25,
                    "symmetric": False,
                },
            }
        ],
        "nose_pnt": [0, 0, 0],
    }
    resp = client.post(f"/aeroplanes/{aeroplane_id}/wings/w/from-wingconfig", json=wc)
    assert resp.status_code == 201, resp.text

    # Flip design_model to 'asb' so ASB CRUD endpoints accept the wing
    if db is not None:
        plane = db.query(AeroplaneModel).filter(
            AeroplaneModel.uuid == aeroplane_id
        ).first()
        wing = next(w for w in plane.wings if w.name == "w")
        wing.design_model = "asb"
        db.commit()

    return aeroplane_id


# ── Spar CRUD (#96) ────────────────────────────────────────────────


class TestSparCrud:
    def test_get_spars_returns_seeded_spar(self, client, db):
        aid = _seed_wing(client, "spar_get", db=db)
        resp = client.get(f"/aeroplanes/{aid}/wings/w/cross_sections/0/spars")
        assert resp.status_code == 200
        spars = resp.json()
        assert len(spars) == 1
        assert spars[0]["spare_position_factor"] == pytest.approx(0.25)

    def test_put_spar_updates_existing(self, client, db):
        aid = _seed_wing(client, "spar_put", db=db)
        updated = {
            "spare_support_dimension_width": 8.0,
            "spare_support_dimension_height": 8.0,
            "spare_position_factor": 0.50,
            "spare_start": 0.0,
            "spare_mode": "follow",
            "spare_vector": [0, 1, 0],
            "spare_origin": [0, 0, 0],
        }
        resp = client.put(f"/aeroplanes/{aid}/wings/w/cross_sections/0/spars/0", json=updated)
        assert resp.status_code == 200, resp.text

        # Verify update took effect
        resp = client.get(f"/aeroplanes/{aid}/wings/w/cross_sections/0/spars")
        spars = resp.json()
        assert len(spars) == 1
        assert spars[0]["spare_position_factor"] == pytest.approx(0.50)
        assert spars[0]["spare_support_dimension_width"] == pytest.approx(8.0)
        assert spars[0]["spare_mode"] == "follow"

    def test_put_spar_invalid_index_returns_404(self, client, db):
        aid = _seed_wing(client, "spar_put_404", db=db)
        updated = {
            "spare_support_dimension_width": 5.0,
            "spare_support_dimension_height": 5.0,
            "spare_position_factor": 0.25,
            "spare_start": 0.0,
            "spare_mode": "standard",
            "spare_vector": [0, 1, 0],
            "spare_origin": [0, 0, 0],
        }
        resp = client.put(f"/aeroplanes/{aid}/wings/w/cross_sections/0/spars/99", json=updated)
        assert resp.status_code == 404

    def test_delete_spar_removes_it(self, client, db):
        aid = _seed_wing(client, "spar_del", db=db)
        resp = client.delete(f"/aeroplanes/{aid}/wings/w/cross_sections/0/spars/0")
        assert resp.status_code == 200

        # Verify spar is gone
        resp = client.get(f"/aeroplanes/{aid}/wings/w/cross_sections/0/spars")
        assert len(resp.json()) == 0

    def test_delete_spar_invalid_index_returns_404(self, client, db):
        aid = _seed_wing(client, "spar_del_404", db=db)
        resp = client.delete(f"/aeroplanes/{aid}/wings/w/cross_sections/0/spars/99")
        assert resp.status_code == 404

    def test_append_then_delete_first_preserves_second(self, client, db):
        aid = _seed_wing(client, "spar_order", db=db)
        # Append a second spar
        second = {
            "spare_support_dimension_width": 3.0,
            "spare_support_dimension_height": 3.0,
            "spare_position_factor": 0.75,
            "spare_mode": "standard",
        }
        resp = client.post(f"/aeroplanes/{aid}/wings/w/cross_sections/0/spars", json=second)
        assert resp.status_code == 201

        # Delete the first (index 0)
        resp = client.delete(f"/aeroplanes/{aid}/wings/w/cross_sections/0/spars/0")
        assert resp.status_code == 200

        # Only the second spar remains
        resp = client.get(f"/aeroplanes/{aid}/wings/w/cross_sections/0/spars")
        spars = resp.json()
        assert len(spars) == 1
        assert spars[0]["spare_position_factor"] == pytest.approx(0.75)


# ── TED direct-access endpoints (#97) ──────────────────────────────


class TestTedDirectAccess:
    def test_get_trailing_edge_device_returns_full_schema(self, client, db):
        aid = _seed_wing(client, "ted_get", db=db)
        resp = client.get(f"/aeroplanes/{aid}/wings/w/cross_sections/0/trailing_edge_device")
        assert resp.status_code == 200
        ted = resp.json()
        assert ted["name"] == "aileron"
        assert ted["symmetric"] is False

    def test_patch_trailing_edge_device_updates_fields(self, client, db):
        aid = _seed_wing(client, "ted_patch", db=db)
        patch = {
            "hinge_spacing": 0.5,
            "side_spacing_root": 2.0,
            "side_spacing_tip": 2.0,
            "hinge_type": "top_simple",
        }
        resp = client.patch(
            f"/aeroplanes/{aid}/wings/w/cross_sections/0/trailing_edge_device",
            json=patch,
        )
        assert resp.status_code == 200, resp.text
        ted = resp.json()
        assert ted["hinge_spacing"] == pytest.approx(0.5)
        assert ted["hinge_type"] == "top_simple"

    def test_delete_trailing_edge_device(self, client, db):
        aid = _seed_wing(client, "ted_del", db=db)
        resp = client.delete(f"/aeroplanes/{aid}/wings/w/cross_sections/0/trailing_edge_device")
        assert resp.status_code == 200

        # Verify it's gone
        resp = client.get(f"/aeroplanes/{aid}/wings/w/cross_sections/0/trailing_edge_device")
        assert resp.status_code == 404

    def test_patch_servo_on_ted(self, client, db):
        aid = _seed_wing(client, "servo_patch", db=db)
        servo_payload = {
            "servo": {
                "length": 23, "width": 12.5, "height": 31.5,
                "leading_length": 6, "latch_z": 14.5, "latch_x": 7.25,
                "latch_thickness": 2.6, "latch_length": 6, "cable_z": 26,
                "screw_hole_lx": 0, "screw_hole_d": 0,
            }
        }
        resp = client.patch(
            f"/aeroplanes/{aid}/wings/w/cross_sections/0/trailing_edge_device/servo",
            json=servo_payload,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["servo"]["length"] == pytest.approx(23)

    def test_get_servo_after_patch(self, client, db):
        aid = _seed_wing(client, "servo_get", db=db)
        servo_payload = {
            "servo": {
                "length": 20, "width": 10, "height": 25,
                "leading_length": 5, "latch_z": 10, "latch_x": 5,
                "latch_thickness": 2, "latch_length": 5, "cable_z": 20,
                "screw_hole_lx": 0, "screw_hole_d": 0,
            }
        }
        client.patch(
            f"/aeroplanes/{aid}/wings/w/cross_sections/0/trailing_edge_device/servo",
            json=servo_payload,
        )
        resp = client.get(
            f"/aeroplanes/{aid}/wings/w/cross_sections/0/trailing_edge_device/servo",
        )
        assert resp.status_code == 200
        assert resp.json()["servo"]["width"] == pytest.approx(10)

    def test_delete_servo(self, client, db):
        aid = _seed_wing(client, "servo_del", db=db)
        # First assign a servo
        servo_payload = {
            "servo": {
                "length": 20, "width": 10, "height": 25,
                "leading_length": 5, "latch_z": 10, "latch_x": 5,
                "latch_thickness": 2, "latch_length": 5, "cable_z": 20,
                "screw_hole_lx": 0, "screw_hole_d": 0,
            }
        }
        client.patch(
            f"/aeroplanes/{aid}/wings/w/cross_sections/0/trailing_edge_device/servo",
            json=servo_payload,
        )
        # Delete it
        resp = client.delete(
            f"/aeroplanes/{aid}/wings/w/cross_sections/0/trailing_edge_device/servo",
        )
        assert resp.status_code == 200

        # Verify it's gone
        resp = client.get(
            f"/aeroplanes/{aid}/wings/w/cross_sections/0/trailing_edge_device/servo",
        )
        assert resp.status_code == 404
