"""gh-1368 — setting an aeroplane's mass writes both places.

An aeroplane's mass lives in ``aeroplanes.total_mass_kg`` and in the
``mass`` design assumption (estimate / calculated / active_source). The
app's computations read the effective assumption, so every writer of the
mass must write both: ``total_mass_kg`` and the ``mass`` estimate.
``active_source`` is never changed by setting the mass.

Maintainer decision (2026-11-07): ``total_mass_kg`` always holds the mass the
app computes with — the effective value of the ``mass`` assumption. While the
calculated value is active, ``total_mass_kg`` follows it; writing the mass then
changes only the estimate.
"""

from __future__ import annotations

from app.converters.openvsp_importer import ImportResult
from app.models.aeroplanemodel import AeroplaneModel, DesignAssumptionModel
from app.schemas.aeroplaneschema import AeroplaneSchema
from app.schemas.design_assumption import AssumptionSourceSwitch, AssumptionWrite
from app.services import aeroplane_service
from app.services import design_assumptions_service as da_svc
from app.services.openvsp_import_service import _persist_aeroplane
from app.tests.conftest import make_aeroplane


def _mass_row(db, aeroplane_id: int) -> DesignAssumptionModel | None:
    return (
        db.query(DesignAssumptionModel)
        .filter(
            DesignAssumptionModel.aeroplane_id == aeroplane_id,
            DesignAssumptionModel.parameter_name == "mass",
        )
        .first()
    )


class TestSetAeroplaneMassWritesBoth:
    def test_without_assumption_rows_creates_mass_estimate(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            created = aeroplane_service.set_aeroplane_mass(db, aeroplane.uuid, 2.35)
            db.commit()

            assert created is True
            db.refresh(aeroplane)
            assert aeroplane.total_mass_kg == 2.35
            row = _mass_row(db, aeroplane.id)
            assert row is not None
            assert row.estimate_value == 2.35
            assert row.active_source == "ESTIMATE"
            assert da_svc.get_effective_assumption(db, aeroplane.id, "mass") == 2.35

    def test_existing_seeded_row_is_updated(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db, total_mass_kg=0.625)
            da_svc.seed_defaults(db, aeroplane.uuid)
            db.commit()

            created = aeroplane_service.set_aeroplane_mass(db, aeroplane.uuid, 0.7)
            db.commit()

            assert created is False
            db.refresh(aeroplane)
            assert aeroplane.total_mass_kg == 0.7
            assert _mass_row(db, aeroplane.id).estimate_value == 0.7

    def test_calculated_active_source_is_kept(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            da_svc.seed_defaults(db, aeroplane.uuid)
            da_svc.update_calculated_value(
                db, aeroplane.uuid, "mass", 1.9, "weight_items", auto_switch_source=True
            )
            db.commit()

            aeroplane_service.set_aeroplane_mass(db, aeroplane.uuid, 2.1)
            db.commit()

            row = _mass_row(db, aeroplane.id)
            assert row.estimate_value == 2.1
            assert row.active_source == "CALCULATED"
            assert row.calculated_value == 1.9
            db.refresh(aeroplane)
            assert aeroplane.total_mass_kg == 1.9


class TestMassEndpointWritesBoth:
    """The REST endpoint (and the MCP tool ``set_aeroplane_total_mass``,
    which delegates to it) writes both places."""

    def test_post_total_mass_sets_assumption(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            uuid_str = str(aeroplane.uuid)
            aeroplane_id = aeroplane.id

        resp = client.post(f"/aeroplanes/{uuid_str}/total_mass_kg", json={"total_mass_kg": 3.2})
        assert resp.status_code in (200, 201), resp.text

        with SessionLocal() as db:
            plane = db.query(AeroplaneModel).filter(AeroplaneModel.id == aeroplane_id).one()
            assert plane.total_mass_kg == 3.2
            assert _mass_row(db, aeroplane_id).estimate_value == 3.2


class TestMassAssumptionEditWritesBoth:
    def test_update_mass_estimate_writes_total_mass(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db, total_mass_kg=0.07)
            da_svc.seed_defaults(db, aeroplane.uuid)
            da_svc.update_assumption(
                db, aeroplane.uuid, "mass", AssumptionWrite(estimate_value=0.4)
            )
            db.commit()

            db.refresh(aeroplane)
            assert aeroplane.total_mass_kg == 0.4
            assert _mass_row(db, aeroplane.id).estimate_value == 0.4

    def test_update_other_parameter_leaves_total_mass(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db, total_mass_kg=1.1)
            da_svc.seed_defaults(db, aeroplane.uuid)
            da_svc.update_assumption(
                db, aeroplane.uuid, "cl_max", AssumptionWrite(estimate_value=1.2)
            )
            db.commit()

            db.refresh(aeroplane)
            assert aeroplane.total_mass_kg == 1.1


class TestOpenVspImportWritesBoth:
    def test_declared_total_mass_is_persisted_in_both_places(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            result = ImportResult(aeroplane=AeroplaneSchema(name="vsp", total_mass_kg=4.2))
            uuid_str, _ = _persist_aeroplane(db, result, name="vsp-mass")
            db.commit()

            plane = db.query(AeroplaneModel).filter(AeroplaneModel.name == "vsp-mass").one()
            assert str(plane.uuid) == uuid_str
            assert plane.total_mass_kg == 4.2
            row = _mass_row(db, plane.id)
            assert row is not None
            assert row.estimate_value == 4.2
            assert row.active_source == "ESTIMATE"

    def test_no_declared_mass_writes_neither(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            result = ImportResult(aeroplane=AeroplaneSchema(name="vsp"))
            _persist_aeroplane(db, result, name="vsp-nomass")
            db.commit()

            plane = db.query(AeroplaneModel).filter(AeroplaneModel.name == "vsp-nomass").one()
            assert plane.total_mass_kg is None
            assert _mass_row(db, plane.id) is None


class TestTotalMassFollowsEffectiveMass:
    """``total_mass_kg`` is the effective mass (maintainer 2026-11-07)."""

    def test_auto_switch_to_calculated_updates_total_mass(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db, total_mass_kg=2.0)
            da_svc.seed_defaults(db, aeroplane.uuid)
            da_svc.update_calculated_value(
                db, aeroplane.uuid, "mass", 1.9, "weight_items", auto_switch_source=True
            )
            db.commit()

            db.refresh(aeroplane)
            assert aeroplane.total_mass_kg == 1.9

    def test_calculated_value_without_switch_leaves_total_mass(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db, total_mass_kg=2.0)
            da_svc.seed_defaults(db, aeroplane.uuid)
            da_svc.update_calculated_value(db, aeroplane.uuid, "mass", 1.9, "weight_items")
            db.commit()

            db.refresh(aeroplane)
            assert aeroplane.total_mass_kg == 2.0

    def test_new_calculated_value_while_active_updates_total_mass(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db, total_mass_kg=2.0)
            da_svc.seed_defaults(db, aeroplane.uuid)
            da_svc.update_calculated_value(
                db, aeroplane.uuid, "mass", 1.9, "weight_items", auto_switch_source=True
            )
            da_svc.update_calculated_value(db, aeroplane.uuid, "mass", 2.3, "weight_items")
            db.commit()

            db.refresh(aeroplane)
            assert aeroplane.total_mass_kg == 2.3

    def test_switch_source_moves_total_mass(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db, total_mass_kg=2.0)
            da_svc.seed_defaults(db, aeroplane.uuid)
            da_svc.update_calculated_value(db, aeroplane.uuid, "mass", 1.9, "weight_items")

            da_svc.switch_source(
                db, aeroplane.uuid, "mass", AssumptionSourceSwitch(active_source="CALCULATED")
            )
            db.refresh(aeroplane)
            assert aeroplane.total_mass_kg == 1.9

            da_svc.switch_source(
                db, aeroplane.uuid, "mass", AssumptionSourceSwitch(active_source="ESTIMATE")
            )
            db.refresh(aeroplane)
            assert aeroplane.total_mass_kg == 2.0

    def test_seeding_takes_the_stored_total_mass_as_estimate(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db, total_mass_kg=0.625)
            da_svc.seed_defaults(db, aeroplane.uuid)
            db.commit()

            assert _mass_row(db, aeroplane.id).estimate_value == 0.625
            db.refresh(aeroplane)
            assert aeroplane.total_mass_kg == 0.625
