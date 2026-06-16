"""Tests for app.services.prop_component_seed (gh-1012).

Seeds every propeller polar as a COTS ``ComponentModel`` so propellers
become selectable in the component picker / BoM. All tests run against
in-memory SQLite — no network, no aero deps.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.db.base import Base
from app.models.component import ComponentModel
from app.models.prop_polar import PropellerPolarModel
from app.services.prop_component_seed import SeedResult, seed_propeller_components


@pytest.fixture()
def session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SM = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    db = SM()
    yield db
    db.close()


def _add_polar(
    db: Session,
    *,
    name: str,
    model_ref: str,
    diameter_in: float = 9.0,
    pitch_in: float = 6.0,
    variant: str = "",
    blades: int = 2,
) -> PropellerPolarModel:
    p = PropellerPolarModel(
        manufacturer="APC",
        name=name,
        model_ref=model_ref,
        diameter_in=diameter_in,
        pitch_in=pitch_in,
        variant=variant,
        blades=blades,
    )
    db.add(p)
    db.flush()
    return p


# ──────────────────────────────────────────────────────────────────────────────
# Fresh seed
# ──────────────────────────────────────────────────────────────────────────────


class TestSeedFresh:
    def test_creates_one_component_per_polar(self, session: Session):
        _add_polar(session, name="APC 9x6", model_ref="apc/9x6")
        _add_polar(session, name="APC 10x5", model_ref="apc/10x5")
        result = seed_propeller_components(session)
        session.flush()
        assert isinstance(result, SeedResult)
        assert result.created == 2
        assert result.updated == 0
        comps = session.query(ComponentModel).filter_by(component_type="propeller").all()
        assert len(comps) == 2

    def test_component_fields(self, session: Session):
        _add_polar(
            session,
            name="APC 28x20-4",
            model_ref="apc/28x20-4",
            diameter_in=28.0,
            pitch_in=20.0,
            variant="-4",
            blades=4,
        )
        seed_propeller_components(session)
        session.flush()
        comp = session.query(ComponentModel).filter_by(model_ref="apc/28x20-4").one()
        assert comp.component_type == "propeller"
        assert comp.name == "APC 28x20-4"
        assert comp.manufacturer == "APC"
        assert comp.model_ref == "apc/28x20-4"
        assert comp.specs["diameter_in"] == 28.0
        assert comp.specs["pitch_in"] == 20.0
        assert comp.specs["blades"] == 4
        assert comp.specs["variant"] == "-4"

    def test_mass_is_null_no_silent_zero(self, session: Session):
        """mass_g must stay NULL — no silent 0-fallback (real masses from #1000)."""
        _add_polar(session, name="APC 9x6", model_ref="apc/9x6")
        seed_propeller_components(session)
        session.flush()
        comp = session.query(ComponentModel).filter_by(model_ref="apc/9x6").one()
        assert comp.mass_g is None


# ──────────────────────────────────────────────────────────────────────────────
# Idempotency
# ──────────────────────────────────────────────────────────────────────────────


class TestSeedIdempotent:
    def test_rerun_creates_no_duplicates(self, session: Session):
        _add_polar(session, name="APC 9x6", model_ref="apc/9x6")
        seed_propeller_components(session)
        session.flush()
        result2 = seed_propeller_components(session)
        session.flush()
        assert result2.created == 0
        comps = session.query(ComponentModel).filter_by(model_ref="apc/9x6").all()
        assert len(comps) == 1

    def test_rerun_updates_changed_specs(self, session: Session):
        polar = _add_polar(session, name="APC 9x6", model_ref="apc/9x6", blades=2)
        seed_propeller_components(session)
        session.flush()
        # Polar blade count corrected (e.g. after #1004) — reseed should update.
        polar.blades = 3
        session.flush()
        result = seed_propeller_components(session)
        session.flush()
        assert result.updated == 1
        comp = session.query(ComponentModel).filter_by(model_ref="apc/9x6").one()
        assert comp.specs["blades"] == 3

    def test_does_not_clobber_user_set_mass(self, session: Session):
        """A user-entered mass must survive a reseed (only null masses stay null)."""
        _add_polar(session, name="APC 9x6", model_ref="apc/9x6")
        seed_propeller_components(session)
        session.flush()
        comp = session.query(ComponentModel).filter_by(model_ref="apc/9x6").one()
        comp.mass_g = 42.0
        session.flush()
        seed_propeller_components(session)
        session.flush()
        comp = session.query(ComponentModel).filter_by(model_ref="apc/9x6").one()
        assert comp.mass_g == 42.0


# ──────────────────────────────────────────────────────────────────────────────
# Guards
# ──────────────────────────────────────────────────────────────────────────────


class TestSeedGuards:
    def test_skips_polar_without_model_ref(self, session: Session):
        p = PropellerPolarModel(manufacturer="APC", name="APC mystery", model_ref=None)
        session.add(p)
        session.flush()
        result = seed_propeller_components(session)
        session.flush()
        assert result.created == 0
        assert result.skipped == 1
