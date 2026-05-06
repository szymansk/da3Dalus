"""Tests for app.services.design_assumptions_service — design assumption CRUD."""

from __future__ import annotations

import uuid

import pytest

from app.core.exceptions import NotFoundError, ValidationError
from app.schemas.design_assumption import (
    PARAMETER_DEFAULTS,
    AssumptionSourceSwitch,
    AssumptionWrite,
)
from app.services import design_assumptions_service as svc
from app.tests.conftest import make_aeroplane


# ---------------------------------------------------------------------------
# seed_defaults
# ---------------------------------------------------------------------------


class TestSeedDefaults:
    def test_creates_six_assumptions(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            summary = svc.seed_defaults(db, aeroplane.uuid)
            assert len(summary.assumptions) == 6

    def test_default_values_match(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            summary = svc.seed_defaults(db, aeroplane.uuid)
            by_name = {a.parameter_name: a for a in summary.assumptions}
            for name, default in PARAMETER_DEFAULTS.items():
                assert by_name[name].estimate_value == default

    def test_idempotent(self, client_and_db):
        """Calling seed_defaults twice does not duplicate rows."""
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            svc.seed_defaults(db, aeroplane.uuid)
            summary = svc.seed_defaults(db, aeroplane.uuid)
            assert len(summary.assumptions) == 6

    def test_all_defaults_use_estimate_source(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            summary = svc.seed_defaults(db, aeroplane.uuid)
            for a in summary.assumptions:
                assert a.active_source == "ESTIMATE"

    def test_raises_not_found_for_missing_aeroplane(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            with pytest.raises(NotFoundError):
                svc.seed_defaults(db, uuid.uuid4())


# ---------------------------------------------------------------------------
# list_assumptions
# ---------------------------------------------------------------------------


class TestListAssumptions:
    def test_returns_seeded_assumptions(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            svc.seed_defaults(db, aeroplane.uuid)
            summary = svc.list_assumptions(db, aeroplane.uuid)
            assert len(summary.assumptions) == 6

    def test_empty_before_seed(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            summary = svc.list_assumptions(db, aeroplane.uuid)
            assert len(summary.assumptions) == 0
            assert summary.warnings_count == 0

    def test_computed_fields(self, client_and_db):
        """Verify effective_value, divergence_level, unit, is_design_choice."""
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            svc.seed_defaults(db, aeroplane.uuid)
            summary = svc.list_assumptions(db, aeroplane.uuid)
            by_name = {a.parameter_name: a for a in summary.assumptions}

            mass = by_name["mass"]
            assert mass.effective_value == mass.estimate_value
            assert mass.unit == "kg"
            assert mass.is_design_choice is False
            assert mass.divergence_level == "none"

            sm = by_name["target_static_margin"]
            assert sm.is_design_choice is True
            assert sm.unit == "% MAC"

    def test_warnings_count_zero_for_fresh_defaults(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            svc.seed_defaults(db, aeroplane.uuid)
            summary = svc.list_assumptions(db, aeroplane.uuid)
            assert summary.warnings_count == 0

    def test_raises_not_found_for_missing_aeroplane(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            with pytest.raises(NotFoundError):
                svc.list_assumptions(db, uuid.uuid4())


# ---------------------------------------------------------------------------
# update_assumption
# ---------------------------------------------------------------------------


class TestUpdateAssumption:
    def test_updates_estimate_value(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            svc.seed_defaults(db, aeroplane.uuid)
            result = svc.update_assumption(
                db, aeroplane.uuid, "mass", AssumptionWrite(estimate_value=2.0)
            )
            assert result.estimate_value == 2.0

    def test_recomputes_divergence(self, client_and_db):
        """When calculated_value exists, divergence_pct is recomputed on update."""
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            svc.seed_defaults(db, aeroplane.uuid)

            # Manually set a calculated value on the model
            from app.models.aeroplanemodel import DesignAssumptionModel

            row = (
                db.query(DesignAssumptionModel)
                .filter(
                    DesignAssumptionModel.aeroplane_id == aeroplane.id,
                    DesignAssumptionModel.parameter_name == "mass",
                )
                .first()
            )
            row.calculated_value = 2.0
            row.calculated_source = "weight_items"
            db.flush()

            # Now update estimate and verify divergence is recomputed
            result = svc.update_assumption(
                db, aeroplane.uuid, "mass", AssumptionWrite(estimate_value=1.5)
            )
            # |1.5 - 2.0| / |2.0| * 100 = 25.0
            assert result.divergence_pct == 25.0

    def test_raises_not_found_for_bad_param(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            svc.seed_defaults(db, aeroplane.uuid)
            with pytest.raises(NotFoundError):
                svc.update_assumption(
                    db, aeroplane.uuid, "nonexistent", AssumptionWrite(estimate_value=1.0)
                )

    def test_raises_not_found_before_seed(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            with pytest.raises(NotFoundError):
                svc.update_assumption(
                    db, aeroplane.uuid, "mass", AssumptionWrite(estimate_value=1.0)
                )

    def test_raises_not_found_for_missing_aeroplane(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            with pytest.raises(NotFoundError):
                svc.update_assumption(db, uuid.uuid4(), "mass", AssumptionWrite(estimate_value=1.0))


# ---------------------------------------------------------------------------
# switch_source
# ---------------------------------------------------------------------------


class TestSwitchSource:
    def test_switch_to_calculated(self, client_and_db):
        """Switching to CALCULATED works when calculated_value is present."""
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            svc.seed_defaults(db, aeroplane.uuid)

            # Set calculated value on mass
            from app.models.aeroplanemodel import DesignAssumptionModel

            row = (
                db.query(DesignAssumptionModel)
                .filter(
                    DesignAssumptionModel.aeroplane_id == aeroplane.id,
                    DesignAssumptionModel.parameter_name == "mass",
                )
                .first()
            )
            row.calculated_value = 1.8
            row.calculated_source = "weight_items"
            db.flush()

            result = svc.switch_source(
                db,
                aeroplane.uuid,
                "mass",
                AssumptionSourceSwitch(active_source="CALCULATED"),
            )
            assert result.active_source == "CALCULATED"
            assert result.effective_value == 1.8

    def test_switch_back_to_estimate(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            svc.seed_defaults(db, aeroplane.uuid)

            result = svc.switch_source(
                db,
                aeroplane.uuid,
                "mass",
                AssumptionSourceSwitch(active_source="ESTIMATE"),
            )
            assert result.active_source == "ESTIMATE"
            assert result.effective_value == PARAMETER_DEFAULTS["mass"]

    def test_rejects_calculated_for_design_choice(self, client_and_db):
        """target_static_margin and g_limit cannot be switched to CALCULATED."""
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            svc.seed_defaults(db, aeroplane.uuid)

            with pytest.raises(ValidationError):
                svc.switch_source(
                    db,
                    aeroplane.uuid,
                    "target_static_margin",
                    AssumptionSourceSwitch(active_source="CALCULATED"),
                )

    def test_rejects_calculated_when_no_value(self, client_and_db):
        """Cannot switch to CALCULATED when calculated_value is None."""
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            svc.seed_defaults(db, aeroplane.uuid)

            with pytest.raises(ValidationError):
                svc.switch_source(
                    db,
                    aeroplane.uuid,
                    "mass",
                    AssumptionSourceSwitch(active_source="CALCULATED"),
                )

    def test_raises_not_found_for_bad_param(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            svc.seed_defaults(db, aeroplane.uuid)
            with pytest.raises(NotFoundError):
                svc.switch_source(
                    db,
                    aeroplane.uuid,
                    "nonexistent",
                    AssumptionSourceSwitch(active_source="ESTIMATE"),
                )

    def test_raises_not_found_for_missing_aeroplane(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            with pytest.raises(NotFoundError):
                svc.switch_source(
                    db,
                    uuid.uuid4(),
                    "mass",
                    AssumptionSourceSwitch(active_source="ESTIMATE"),
                )
