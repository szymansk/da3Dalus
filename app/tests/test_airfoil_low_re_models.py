"""Tests for AirfoilGeometryModel + AirfoilLowRePolarModel (Task 1, gh-821)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def engine_and_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from app.db.base import Base

    # Import models so they register with Base
    import app.models  # noqa: F401
    from app.models.airfoil import AirfoilModel
    from app.models.airfoil_low_re import AirfoilGeometryModel, AirfoilLowRePolarModel  # noqa: F401

    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    yield engine, SessionLocal
    Base.metadata.drop_all(bind=engine)


def test_airfoil_geometry_model_table_exists(engine_and_session):
    engine, _ = engine_and_session
    inspector = inspect(engine)
    assert "airfoil_geometry" in inspector.get_table_names()


def test_airfoil_low_re_polar_table_exists(engine_and_session):
    engine, _ = engine_and_session
    inspector = inspect(engine)
    assert "airfoil_low_re_polar" in inspector.get_table_names()


def test_airfoil_geometry_columns(engine_and_session):
    engine, _ = engine_and_session
    inspector = inspect(engine)
    col_names = {c["name"] for c in inspector.get_columns("airfoil_geometry")}
    for col in (
        "airfoil_name",
        "max_thickness_pct",
        "max_camber_pct",
        "camber_at_te",
        "family",
        "computed_at",
    ):
        assert col in col_names, f"missing column: {col}"


def test_airfoil_geometry_unique_constraint(engine_and_session):
    engine, SessionLocal = engine_and_session
    from app.models.airfoil import AirfoilModel
    from app.models.airfoil_low_re import AirfoilGeometryModel

    with SessionLocal() as session:
        # Need a parent airfoil first (FK)
        af = AirfoilModel(name="naca2412", coordinates=[[0, 0], [1, 0]])
        session.add(af)
        session.flush()

        g1 = AirfoilGeometryModel(
            airfoil_name="naca2412",
            max_thickness_pct=12.0,
            max_camber_pct=2.0,
            camber_at_te=0.01,
            family="cambered",
            computed_at=datetime.now(timezone.utc),
        )
        session.add(g1)
        session.commit()

        # Duplicate should fail
        from sqlalchemy.exc import IntegrityError

        g2 = AirfoilGeometryModel(
            airfoil_name="naca2412",
            max_thickness_pct=12.0,
            max_camber_pct=2.0,
            camber_at_te=0.01,
            family="cambered",
            computed_at=datetime.now(timezone.utc),
        )
        session.add(g2)
        with pytest.raises(IntegrityError):
            session.commit()


def test_airfoil_low_re_polar_columns(engine_and_session):
    engine, _ = engine_and_session
    inspector = inspect(engine)
    col_names = {c["name"] for c in inspector.get_columns("airfoil_low_re_polar")}
    required = {
        "airfoil_name",
        "reynolds",
        "ld_max",
        "cl_max",
        "alpha_attached_lo",
        "alpha_attached_hi",
        "drag_bucket_width",
        "cd_min",
        "stall_gentleness",
        "cd0",
        "k",
        "cl0",
        "cl_valid_lo",
        "cl_valid_hi",
        "min_analysis_confidence",
        "neuralfoil_model_size",
        "n_crit",
        "computed_at",
    }
    for col in required:
        assert col in col_names, f"missing column: {col}"


def test_airfoil_low_re_polar_unique_constraint(engine_and_session):
    engine, SessionLocal = engine_and_session
    from app.models.airfoil import AirfoilModel
    from app.models.airfoil_low_re import AirfoilLowRePolarModel
    from sqlalchemy.exc import IntegrityError

    with SessionLocal() as session:
        af = AirfoilModel(name="sd7037", coordinates=[[0, 0], [1, 0]])
        session.add(af)
        session.flush()

        def _make_polar():
            return AirfoilLowRePolarModel(
                airfoil_name="sd7037",
                reynolds=100_000.0,
                ld_max=40.0,
                cl_max=1.2,
                alpha_attached_lo=-3.0,
                alpha_attached_hi=12.0,
                drag_bucket_width=0.5,
                cd_min=0.01,
                stall_gentleness=-0.1,
                cd0=0.012,
                k=0.04,
                cl0=0.2,
                cl_valid_lo=0.0,
                cl_valid_hi=1.0,
                min_analysis_confidence=0.95,
                neuralfoil_model_size="xxxlarge",
                n_crit=9.0,
                computed_at=datetime.now(timezone.utc),
            )

        session.add(_make_polar())
        session.commit()

        session.add(_make_polar())
        with pytest.raises(IntegrityError):
            session.commit()


def test_airfoil_geometry_fk_to_airfoils(engine_and_session):
    """airfoil_geometry.airfoil_name must FK → airfoils.name."""
    engine, _ = engine_and_session
    inspector = inspect(engine)
    fks = inspector.get_foreign_keys("airfoil_geometry")
    referred = {fk["referred_table"] for fk in fks}
    assert "airfoils" in referred


def test_airfoil_low_re_polar_fk_to_airfoils(engine_and_session):
    engine, _ = engine_and_session
    inspector = inspect(engine)
    fks = inspector.get_foreign_keys("airfoil_low_re_polar")
    referred = {fk["referred_table"] for fk in fks}
    assert "airfoils" in referred
