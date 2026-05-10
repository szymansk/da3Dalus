"""Tests for seed_defaults seeding AircraftComputationConfigModel rows."""

from app.models.computation_config import (
    AircraftComputationConfigModel,
    COMPUTATION_CONFIG_DEFAULTS,
)
from app.services.design_assumptions_service import seed_defaults
from app.tests.conftest import make_aeroplane


def test_seed_defaults_creates_computation_config(client_and_db):
    """seed_defaults seeds a per-aircraft computation config row."""
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        seed_defaults(db, str(aeroplane.uuid))
        db.commit()
        aeroplane_id = aeroplane.id

    with SessionLocal() as db:
        config = (
            db.query(AircraftComputationConfigModel)
            .filter(AircraftComputationConfigModel.aeroplane_id == aeroplane_id)
            .first()
        )
        assert config is not None
        assert config.coarse_alpha_step_deg == COMPUTATION_CONFIG_DEFAULTS["coarse_alpha_step_deg"]
        assert config.fine_velocity_count == COMPUTATION_CONFIG_DEFAULTS["fine_velocity_count"]


def test_seed_defaults_idempotent_for_config(client_and_db):
    """Calling seed_defaults twice does not create a second config row."""
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        seed_defaults(db, str(aeroplane.uuid))
        seed_defaults(db, str(aeroplane.uuid))
        db.commit()
        aeroplane_id = aeroplane.id

    with SessionLocal() as db:
        configs = (
            db.query(AircraftComputationConfigModel)
            .filter(AircraftComputationConfigModel.aeroplane_id == aeroplane_id)
            .all()
        )
        assert len(configs) == 1
