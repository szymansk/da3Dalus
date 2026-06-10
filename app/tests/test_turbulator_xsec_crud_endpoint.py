"""TDD tests for turbulator cross-section CRUD endpoints (gh-936 Part 0).

Coverage:
- GET /aeroplanes/{id}/wings/{name}/cross_sections/{idx}/turbulator
  → 200 when present; 404 when absent or terminal xsec
- PUT …/turbulator → create (201/200) + read-back; validate x/c range; upsert
- DELETE …/turbulator → 200; 404 when absent
- PUT triggers on_wing_changed (recompute side-effect)
- DELETE triggers on_wing_changed
- Validation: position_root / position_tip must be in [0,1]
"""

from __future__ import annotations

import uuid

import pytest

AIRFOIL = "./components/airfoils/rg15.dat"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_two_xsec_wing(session, aeroplane_id: int, *, with_turbulator: bool = False):
    """Create a wing with two x-secs (root + tip). Optionally add a turbulator to root."""
    from app.models.aeroplanemodel import (
        WingModel,
        WingXSecDetailModel,
        WingXSecModel,
        WingXSecTurbulatorModel,
    )

    wing = WingModel(name="test_wing", symmetric=True, aeroplane_id=aeroplane_id)
    session.add(wing)
    session.flush()

    # root xsec (index 0) — non-terminal, may carry turbulator
    root = WingXSecModel(
        wing_id=wing.id,
        xyz_le=[0.0, 0.0, 0.0],
        chord=0.2,
        twist=0.0,
        airfoil=AIRFOIL,
        sort_index=0,
    )
    session.add(root)
    session.flush()

    detail = WingXSecDetailModel(wing_xsec_id=root.id, x_sec_type="segment")
    session.add(detail)
    session.flush()

    if with_turbulator:
        turb = WingXSecTurbulatorModel(
            wing_xsec_detail_id=detail.id,
            form="zigzag",
            height_mm=0.3,
            position_root=0.1,
            position_tip=0.15,
            enabled=True,
        )
        session.add(turb)
        session.flush()

    # tip xsec (index 1) — terminal, must never have a turbulator
    tip = WingXSecModel(
        wing_id=wing.id,
        xyz_le=[0.0, 0.5, 0.0],
        chord=0.15,
        twist=0.0,
        airfoil=AIRFOIL,
        sort_index=1,
    )
    session.add(tip)
    session.flush()

    session.commit()
    session.refresh(wing)
    return wing


# ---------------------------------------------------------------------------
# GET
# ---------------------------------------------------------------------------


class TestGetTurbulator:
    def test_get_returns_404_when_absent(self, client_and_db):
        """GET returns 404 when the xsec has no turbulator."""
        from app.tests.conftest import make_aeroplane

        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)
            wing = _make_two_xsec_wing(db, plane.id, with_turbulator=False)

        resp = client.get(
            f"/aeroplanes/{plane.uuid}/wings/{wing.name}/cross_sections/0/turbulator"
        )
        assert resp.status_code == 404

    def test_get_returns_200_when_present(self, client_and_db):
        """GET returns 200 with correct fields when turbulator exists."""
        from app.tests.conftest import make_aeroplane

        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)
            wing = _make_two_xsec_wing(db, plane.id, with_turbulator=True)

        resp = client.get(
            f"/aeroplanes/{plane.uuid}/wings/{wing.name}/cross_sections/0/turbulator"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["form"] == "zigzag"
        assert body["position_root"] == pytest.approx(0.1)
        assert body["position_tip"] == pytest.approx(0.15)
        assert body["height_mm"] == pytest.approx(0.3)
        assert body["enabled"] is True

    def test_get_returns_404_for_unknown_aeroplane(self, client_and_db):
        """GET with unknown UUID returns 404."""
        client, _ = client_and_db
        resp = client.get(
            f"/aeroplanes/{uuid.uuid4()}/wings/test_wing/cross_sections/0/turbulator"
        )
        assert resp.status_code == 404

    def test_get_terminal_xsec_returns_422(self, client_and_db):
        """GET on the terminal x-sec returns 422 (terminal validation error before turbulator lookup)."""
        from app.tests.conftest import make_aeroplane

        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)
            wing = _make_two_xsec_wing(db, plane.id, with_turbulator=False)

        # index 1 is terminal — raises ValidationError → 422
        resp = client.get(
            f"/aeroplanes/{plane.uuid}/wings/{wing.name}/cross_sections/1/turbulator"
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PUT (upsert)
# ---------------------------------------------------------------------------


class TestPutTurbulator:
    def test_put_creates_turbulator(self, client_and_db):
        """PUT creates a new turbulator and returns it."""
        from app.tests.conftest import make_aeroplane

        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)
            wing = _make_two_xsec_wing(db, plane.id, with_turbulator=False)

        payload = {
            "form": "dots",
            "height_mm": 0.4,
            "position_root": 0.08,
            "position_tip": 0.12,
            "enabled": True,
        }
        resp = client.put(
            f"/aeroplanes/{plane.uuid}/wings/{wing.name}/cross_sections/0/turbulator",
            json=payload,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["form"] == "dots"
        assert body["position_root"] == pytest.approx(0.08)
        assert body["position_tip"] == pytest.approx(0.12)
        assert body["height_mm"] == pytest.approx(0.4)
        assert body["enabled"] is True

    def test_put_updates_existing_turbulator(self, client_and_db):
        """PUT on an xsec that already has a turbulator updates in place."""
        from app.tests.conftest import make_aeroplane

        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)
            wing = _make_two_xsec_wing(db, plane.id, with_turbulator=True)

        updated_payload = {
            "form": "thread",
            "height_mm": 0.5,
            "position_root": 0.2,
            "position_tip": None,
            "enabled": False,
        }
        resp = client.put(
            f"/aeroplanes/{plane.uuid}/wings/{wing.name}/cross_sections/0/turbulator",
            json=updated_payload,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["form"] == "thread"
        assert body["position_root"] == pytest.approx(0.2)
        assert body["enabled"] is False

    def test_put_round_trip_get_after_put(self, client_and_db):
        """GET after PUT returns the values just written."""
        from app.tests.conftest import make_aeroplane

        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)
            wing = _make_two_xsec_wing(db, plane.id, with_turbulator=False)

        payload = {
            "form": "zigzag",
            "height_mm": 0.3,
            "position_root": 0.09,
            "position_tip": 0.11,
            "enabled": True,
        }
        put_resp = client.put(
            f"/aeroplanes/{plane.uuid}/wings/{wing.name}/cross_sections/0/turbulator",
            json=payload,
        )
        assert put_resp.status_code == 200

        get_resp = client.get(
            f"/aeroplanes/{plane.uuid}/wings/{wing.name}/cross_sections/0/turbulator"
        )
        assert get_resp.status_code == 200
        body = get_resp.json()
        assert body["position_root"] == pytest.approx(0.09)
        assert body["position_tip"] == pytest.approx(0.11)

    def test_put_validation_position_root_out_of_range(self, client_and_db):
        """PUT rejects position_root > 1.0 with 422."""
        from app.tests.conftest import make_aeroplane

        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)
            wing = _make_two_xsec_wing(db, plane.id, with_turbulator=False)

        resp = client.put(
            f"/aeroplanes/{plane.uuid}/wings/{wing.name}/cross_sections/0/turbulator",
            json={"form": "zigzag", "height_mm": 0.3, "position_root": 1.5, "enabled": True},
        )
        assert resp.status_code == 422

    def test_put_validation_position_tip_out_of_range(self, client_and_db):
        """PUT rejects position_tip < 0.0 with 422."""
        from app.tests.conftest import make_aeroplane

        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)
            wing = _make_two_xsec_wing(db, plane.id, with_turbulator=False)

        resp = client.put(
            f"/aeroplanes/{plane.uuid}/wings/{wing.name}/cross_sections/0/turbulator",
            json={
                "form": "zigzag",
                "height_mm": 0.3,
                "position_root": 0.1,
                "position_tip": -0.1,
                "enabled": True,
            },
        )
        assert resp.status_code == 422

    def test_put_validation_height_negative(self, client_and_db):
        """PUT rejects height_mm < 0 with 422."""
        from app.tests.conftest import make_aeroplane

        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)
            wing = _make_two_xsec_wing(db, plane.id, with_turbulator=False)

        resp = client.put(
            f"/aeroplanes/{plane.uuid}/wings/{wing.name}/cross_sections/0/turbulator",
            json={"form": "zigzag", "height_mm": -1.0, "position_root": 0.1, "enabled": True},
        )
        assert resp.status_code == 422

    def test_put_triggers_on_wing_changed(self, client_and_db, monkeypatch):
        """PUT calls on_wing_changed so geometry/Cd0 recompute fires."""
        from app.tests.conftest import make_aeroplane

        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)
            wing = _make_two_xsec_wing(db, plane.id, with_turbulator=False)

        calls = []
        monkeypatch.setattr(
            "app.api.v2.endpoints.aeroplane.wings.on_wing_changed",
            lambda db, aid, wname: calls.append((str(aid), wname)),
        )

        client.put(
            f"/aeroplanes/{plane.uuid}/wings/{wing.name}/cross_sections/0/turbulator",
            json={"form": "zigzag", "height_mm": 0.3, "position_root": 0.1, "enabled": True},
        )
        assert len(calls) == 1
        assert calls[0][1] == wing.name

    def test_put_unknown_aeroplane_returns_404(self, client_and_db):
        """PUT with unknown aeroplane UUID returns 404."""
        client, _ = client_and_db
        resp = client.put(
            f"/aeroplanes/{uuid.uuid4()}/wings/test_wing/cross_sections/0/turbulator",
            json={"form": "zigzag", "height_mm": 0.3, "position_root": 0.1, "enabled": True},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------


class TestDeleteTurbulator:
    def test_delete_removes_turbulator(self, client_and_db):
        """DELETE removes the turbulator; subsequent GET returns 404."""
        from app.tests.conftest import make_aeroplane

        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)
            wing = _make_two_xsec_wing(db, plane.id, with_turbulator=True)

        del_resp = client.delete(
            f"/aeroplanes/{plane.uuid}/wings/{wing.name}/cross_sections/0/turbulator"
        )
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "deleted"

        get_resp = client.get(
            f"/aeroplanes/{plane.uuid}/wings/{wing.name}/cross_sections/0/turbulator"
        )
        assert get_resp.status_code == 404

    def test_delete_returns_404_when_absent(self, client_and_db):
        """DELETE on an xsec with no turbulator returns 404."""
        from app.tests.conftest import make_aeroplane

        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)
            wing = _make_two_xsec_wing(db, plane.id, with_turbulator=False)

        resp = client.delete(
            f"/aeroplanes/{plane.uuid}/wings/{wing.name}/cross_sections/0/turbulator"
        )
        assert resp.status_code == 404

    def test_delete_triggers_on_wing_changed(self, client_and_db, monkeypatch):
        """DELETE calls on_wing_changed so geometry/Cd0 recompute fires."""
        from app.tests.conftest import make_aeroplane

        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)
            wing = _make_two_xsec_wing(db, plane.id, with_turbulator=True)

        calls = []
        monkeypatch.setattr(
            "app.api.v2.endpoints.aeroplane.wings.on_wing_changed",
            lambda db, aid, wname: calls.append((str(aid), wname)),
        )

        client.delete(
            f"/aeroplanes/{plane.uuid}/wings/{wing.name}/cross_sections/0/turbulator"
        )
        assert len(calls) == 1
        assert calls[0][1] == wing.name
