"""TDD tests for Turbulator persistence — gh-934 Slice 1.

Covers:
- WingXSecTurbulatorModel DB persistence (one-to-one with WingXSecDetailModel)
- Converter round-trip: schema → topology → DB → topology → schema
- WingModel.from_dict builds turbulator detail when segment carries one
- Backward compat: segments without turbulator still load fine
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.aeroplanemodel import (
    AeroplaneModel,
    WingModel,
    WingXSecDetailModel,
    WingXSecModel,
    WingXSecTurbulatorModel,
)


# ---------------------------------------------------------------------------
# In-memory SQLite fixture (no FastAPI overhead)
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_session():
    """Fresh in-memory SQLite + all tables for each test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    Base.metadata.drop_all(bind=engine)


# ---------------------------------------------------------------------------
# Helper: minimal aeroplane + wing payload
# ---------------------------------------------------------------------------

AIRFOIL = "./components/airfoils/rg15.dat"


def _wing_dict_with_turbulator(
    form="zigzag",
    height_mm=0.3,
    position_root=0.1,
    position_tip=0.15,
    enabled=True,
) -> dict:
    """Return a WingModel.from_dict-compatible dict with one segment carrying a turbulator."""
    return {
        "symmetric": True,
        "x_secs": [
            {
                "xyz_le": [0.0, 0.0, 0.0],
                "chord": 0.2,
                "twist": 0.0,
                "airfoil": AIRFOIL,
                "x_sec_type": "root",
                "turbulator": {
                    "form": form,
                    "height_mm": height_mm,
                    "position_root": position_root,
                    "position_tip": position_tip,
                    "enabled": enabled,
                },
            },
            {
                "xyz_le": [0.0, 0.5, 0.0],
                "chord": 0.16,
                "twist": 0.0,
                "airfoil": AIRFOIL,
                # terminal x-sec — no turbulator
            },
        ],
    }


def _wing_dict_without_turbulator() -> dict:
    """Return a WingModel.from_dict-compatible dict with NO turbulator (backward compat)."""
    return {
        "symmetric": True,
        "x_secs": [
            {
                "xyz_le": [0.0, 0.0, 0.0],
                "chord": 0.2,
                "twist": 0.0,
                "airfoil": AIRFOIL,
                "x_sec_type": "root",
                # No "turbulator" key — old format
            },
            {
                "xyz_le": [0.0, 0.5, 0.0],
                "chord": 0.16,
                "twist": 0.0,
                "airfoil": AIRFOIL,
            },
        ],
    }


# ---------------------------------------------------------------------------
# WingXSecTurbulatorModel basic persistence
# ---------------------------------------------------------------------------


class TestWingXSecTurbulatorModel:
    def test_turbulator_model_exists(self):
        """WingXSecTurbulatorModel is importable and has expected columns."""
        t = WingXSecTurbulatorModel()
        assert hasattr(t, "form")
        assert hasattr(t, "height_mm")
        assert hasattr(t, "position_root")
        assert hasattr(t, "position_tip")
        assert hasattr(t, "enabled")

    def test_persist_and_reload(self, db_session):
        """Turbulator row survives a flush + reload from DB."""
        aeroplane = AeroplaneModel(name="test_plane", uuid="a" * 32)
        db_session.add(aeroplane)
        db_session.flush()

        wing = WingModel(name="main", symmetric=True, aeroplane_id=aeroplane.id)
        db_session.add(wing)
        db_session.flush()

        xsec = WingXSecModel(
            xyz_le=[0.0, 0.0, 0.0],
            chord=0.2,
            twist=0.0,
            airfoil=AIRFOIL,
            sort_index=0,
            wing_id=wing.id,
        )
        db_session.add(xsec)
        db_session.flush()

        detail = WingXSecDetailModel(
            wing_xsec_id=xsec.id,
            x_sec_type="root",
        )
        db_session.add(detail)
        db_session.flush()

        turb = WingXSecTurbulatorModel(
            wing_xsec_detail_id=detail.id,
            form="dots",
            height_mm=0.4,
            position_root=0.08,
            position_tip=0.12,
            enabled=True,
        )
        db_session.add(turb)
        db_session.commit()

        # Reload
        db_session.expire_all()
        reloaded_detail = db_session.get(WingXSecDetailModel, detail.id)
        assert reloaded_detail.turbulator is not None
        t = reloaded_detail.turbulator
        assert t.form == "dots"
        assert t.height_mm == pytest.approx(0.4)
        assert t.position_root == pytest.approx(0.08)
        assert t.position_tip == pytest.approx(0.12)
        assert t.enabled is True

    def test_cascade_delete(self, db_session):
        """Deleting detail cascades to turbulator row."""
        aeroplane = AeroplaneModel(name="cascade_plane", uuid="b" * 32)
        db_session.add(aeroplane)
        db_session.flush()

        wing = WingModel(name="cascade_wing", symmetric=True, aeroplane_id=aeroplane.id)
        db_session.add(wing)
        db_session.flush()

        xsec = WingXSecModel(
            xyz_le=[0.0, 0.0, 0.0],
            chord=0.2,
            twist=0.0,
            airfoil=AIRFOIL,
            sort_index=0,
            wing_id=wing.id,
        )
        db_session.add(xsec)
        db_session.flush()

        detail = WingXSecDetailModel(wing_xsec_id=xsec.id, x_sec_type="root")
        db_session.add(detail)
        db_session.flush()

        turb = WingXSecTurbulatorModel(
            wing_xsec_detail_id=detail.id,
            form="zigzag",
            height_mm=0.3,
            position_root=0.1,
            position_tip=0.1,
            enabled=True,
        )
        db_session.add(turb)
        db_session.commit()
        turb_id = turb.id

        db_session.delete(detail)
        db_session.commit()

        assert db_session.get(WingXSecTurbulatorModel, turb_id) is None


# ---------------------------------------------------------------------------
# WingModel.from_dict builds turbulator
# ---------------------------------------------------------------------------


class TestWingModelFromDictWithTurbulator:
    def test_from_dict_builds_turbulator(self, db_session):
        data = _wing_dict_with_turbulator(
            form="thread", height_mm=0.5, position_root=0.07, position_tip=0.09
        )
        wing = WingModel.from_dict(name="w", data=data)
        db_session.add(wing)
        db_session.commit()

        db_session.expire_all()
        reloaded = db_session.get(WingModel, wing.id)
        # First xsec has a detail with turbulator
        xsec0 = reloaded.x_secs[0]
        assert xsec0.turbulator is not None
        t = xsec0.turbulator
        assert t.form == "thread"
        assert t.height_mm == pytest.approx(0.5)
        assert t.position_root == pytest.approx(0.07)
        assert t.position_tip == pytest.approx(0.09)
        assert t.enabled is True

    def test_from_dict_no_turbulator_backward_compat(self, db_session):
        """Old wing dicts without turbulator field should load without error."""
        data = _wing_dict_without_turbulator()
        wing = WingModel.from_dict(name="w_old", data=data)
        db_session.add(wing)
        db_session.commit()

        db_session.expire_all()
        reloaded = db_session.get(WingModel, wing.id)
        xsec0 = reloaded.x_secs[0]
        # Should have no turbulator (may have no detail at all, or detail.turbulator is None)
        assert xsec0.turbulator is None

    def test_terminal_xsec_has_no_turbulator(self, db_session):
        """The last x-sec should never carry a turbulator (it's just a boundary)."""
        data = _wing_dict_with_turbulator()
        wing = WingModel.from_dict(name="w_term", data=data)
        db_session.add(wing)
        db_session.commit()

        db_session.expire_all()
        reloaded = db_session.get(WingModel, wing.id)
        last_xsec = reloaded.x_secs[-1]
        assert last_xsec.turbulator is None


# ---------------------------------------------------------------------------
# Converter round-trip: topology → DB → topology
# ---------------------------------------------------------------------------


class TestConverterRoundTrip:
    def test_turbulator_survives_schema_db_roundtrip(self, db_session):
        """schema turbulator → WingModel → reload → WingXSecSchema turbulator matches."""
        from app.converters.model_schema_converters import wing_model_to_asb_wing_schema
        import app.schemas as schemas

        data = _wing_dict_with_turbulator(
            form="zigzag",
            height_mm=0.3,
            position_root=0.1,
            position_tip=0.15,
            enabled=True,
        )
        wing = WingModel.from_dict(name="rt_wing", data=data)
        db_session.add(wing)
        db_session.commit()

        db_session.expire_all()
        reloaded = db_session.get(WingModel, wing.id)

        # Convert model → schema
        asb_schema = wing_model_to_asb_wing_schema(reloaded)
        # First xsec carries the turbulator
        xsec0_schema = asb_schema.x_secs[0]
        assert xsec0_schema.turbulator is not None
        t_schema = xsec0_schema.turbulator
        assert t_schema.form == "zigzag"
        assert t_schema.height_mm == pytest.approx(0.3)
        assert t_schema.position_root == pytest.approx(0.1)
        assert t_schema.position_tip == pytest.approx(0.15)
        assert t_schema.enabled is True

    def test_turbulator_survives_topology_to_db(self, db_session):
        """Pydantic Turbulator schema → WingSegment topology → WingModel DB → WingXSecSchema."""
        from app.converters.model_schema_converters import wing_model_to_asb_wing_schema
        from app.schemas.wing import Turbulator as TurbulatorSchema, Segment, Wing, Airfoil
        from app.services.create_wing_configuration import create_wing_configuration
        from app.converters.model_schema_converters import wing_config_to_wing_model

        turb = TurbulatorSchema(
            form="dots",
            height_mm=0.25,
            position_root=0.09,
            position_tip=0.11,
            enabled=False,
        )
        segment = Segment(
            root_airfoil=Airfoil(airfoil=AIRFOIL, chord=200.0),
            tip_airfoil=Airfoil(airfoil=AIRFOIL, chord=160.0),
            length=500.0,
            sweep=0.0,
            turbulator=turb,
        )
        wing_schema = Wing(nose_pnt=[0.0, 0.0, 0.0], symmetric=True, segments=[segment])

        # topology
        wc = create_wing_configuration(wing_schema)
        assert wc.segments[0].turbulator is not None
        assert wc.segments[0].turbulator.form == "dots"

        # to DB model
        wing_model = wing_config_to_wing_model(wc, "dots_wing", scale=0.001)
        db_session.add(wing_model)
        db_session.commit()

        db_session.expire_all()
        reloaded = db_session.get(WingModel, wing_model.id)

        asb_schema = wing_model_to_asb_wing_schema(reloaded)
        xsec0 = asb_schema.x_secs[0]
        assert xsec0.turbulator is not None
        assert xsec0.turbulator.form == "dots"
        assert xsec0.turbulator.height_mm == pytest.approx(0.25)
        assert xsec0.turbulator.position_root == pytest.approx(0.09)
        assert xsec0.turbulator.position_tip == pytest.approx(0.11)
        assert xsec0.turbulator.enabled is False
