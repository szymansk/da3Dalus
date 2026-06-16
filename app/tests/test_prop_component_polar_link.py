"""Component↔polar resolution + picker filter for seeded propellers (gh-1012).

Verifies that a seeded propeller ``ComponentModel`` resolves to its
``PropellerPolarModel`` via the shared ``model_ref`` and that the
component response exposes ``has_polar`` / ``polar_id`` so the performance
layer (powertrain_performance) can bridge component → polar.
"""

from __future__ import annotations

from app.models.component import ComponentModel
from app.models.prop_polar import PropellerPolarModel
from app.services import prop_component_seed


def _seed_polar_and_component(SessionLocal) -> None:
    db = SessionLocal()
    try:
        db.add(
            PropellerPolarModel(
                manufacturer="APC",
                name="APC 9x6",
                model_ref="apc/9x6",
                diameter_in=9.0,
                pitch_in=6.0,
                variant="",
                blades=2,
            )
        )
        db.flush()
        prop_component_seed.seed_propeller_components(db)
        db.commit()
    finally:
        db.close()


class TestPickerFilter:
    def test_propeller_components_listed(self, client_and_db):
        client, SessionLocal = client_and_db
        _seed_polar_and_component(SessionLocal)
        res = client.get("/components", params={"type": "propeller"})
        assert res.status_code == 200
        items = res.json()["items"]
        names = {c["name"] for c in items}
        assert "APC 9x6" in names


class TestPolarLink:
    def test_response_exposes_has_polar_and_polar_id(self, client_and_db):
        client, SessionLocal = client_and_db
        _seed_polar_and_component(SessionLocal)
        # Find the polar id for cross-check.
        db = SessionLocal()
        try:
            polar = db.query(PropellerPolarModel).filter_by(model_ref="apc/9x6").one()
            polar_id = polar.id
            comp = db.query(ComponentModel).filter_by(model_ref="apc/9x6").one()
            comp_id = comp.id
        finally:
            db.close()

        res = client.get(f"/components/{comp_id}")
        assert res.status_code == 200
        body = res.json()
        assert body["has_polar"] is True
        assert body["polar_id"] == polar_id

    def test_component_without_polar_has_no_link(self, client_and_db):
        client, _ = client_and_db
        res = client.post(
            "/components",
            json={
                "name": "Generic widget",
                "component_type": "generic",
                "specs": {},
            },
        )
        assert res.status_code == 201
        body = res.json()
        assert body["has_polar"] is False
        assert body["polar_id"] is None


class TestMassUnknown:
    def test_seeded_prop_mass_is_null(self, client_and_db):
        client, SessionLocal = client_and_db
        _seed_polar_and_component(SessionLocal)
        res = client.get("/components", params={"type": "propeller"})
        prop = next(c for c in res.json()["items"] if c["name"] == "APC 9x6")
        assert prop["mass_g"] is None
