"""Tests for the backfill CLI script (Task 10, gh-821).

Asserts idempotency (skip already-computed), progress logging, no silent truncation.
Mocks the actual NeuralFoil compute.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Realistic 25-point coordinate array (SD7037-like) reused across fixtures.
# The backfill coord guard requires >= 10 points; 2/3-point triangles are
# correctly rejected as degenerate and must not appear in tests that assert
# compute is called.
_SD7037_COORDS = [
    [1.000, 0.000],
    [0.950, 0.012],
    [0.900, 0.022],
    [0.800, 0.038],
    [0.700, 0.051],
    [0.600, 0.060],
    [0.500, 0.066],
    [0.400, 0.068],
    [0.300, 0.065],
    [0.200, 0.055],
    [0.100, 0.035],
    [0.050, 0.020],
    [0.000, 0.000],
    [0.050, -0.010],
    [0.100, -0.014],
    [0.200, -0.016],
    [0.300, -0.014],
    [0.400, -0.010],
    [0.500, -0.006],
    [0.600, -0.003],
    [0.700, -0.001],
    [0.800, 0.001],
    [0.900, 0.001],
    [0.950, 0.001],
    [1.000, 0.000],
]


@pytest.fixture()
def backfill_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from app.db.base import Base
    import app.models  # noqa: F401
    from app.models.airfoil_low_re import AirfoilGeometryModel, AirfoilLowRePolarModel  # noqa: F401

    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    yield SessionLocal
    Base.metadata.drop_all(bind=engine)


def test_backfill_skips_already_computed_airfoils(backfill_db):
    """Idempotency: airfoils with current computed_at + model_size are skipped."""
    from app.models.airfoil import AirfoilModel
    from app.models.airfoil_low_re import AirfoilLowRePolarModel
    from app.settings import Settings

    settings = Settings()
    model_size = settings.low_re_neuralfoil_model_size

    with backfill_db() as session:
        af = AirfoilModel(name="sd7037_backfill_test", coordinates=_SD7037_COORDS)
        session.add(af)
        session.flush()
        # Pre-compute a polar with current model size
        for re in settings.low_re_grid:
            session.add(
                AirfoilLowRePolarModel(
                    airfoil_name="sd7037_backfill_test",
                    reynolds=float(re),
                    ld_max=40.0,
                    cl_max=1.2,
                    alpha_attached_lo=-3.0,
                    alpha_attached_hi=12.0,
                    drag_bucket_width=0.5,
                    cd_min=0.01,
                    stall_gentleness=-0.05,
                    cd0=0.012,
                    k=0.04,
                    cl0=0.3,
                    cl_valid_lo=0.0,
                    cl_valid_hi=1.2,
                    min_analysis_confidence=0.95,
                    neuralfoil_model_size=model_size,
                    n_crit=settings.low_re_n_crit,
                    computed_at=datetime.now(timezone.utc),
                )
            )
        session.commit()

    # Mock compute to detect if it's called
    with patch(
        "app.services.airfoil_low_re_service.compute_airfoil_low_re", return_value=[]
    ) as mock_compute:
        from scripts.backfill_airfoil_low_re import run_backfill

        with backfill_db() as session:
            run_backfill(session=session, force=False)
        # Should NOT have been called for already-computed airfoil
        for call_args in mock_compute.call_args_list:
            assert call_args[0][0] != "sd7037_backfill_test", (
                "Already-computed airfoil should not be recomputed"
            )


def test_backfill_processes_uncovered_airfoils(backfill_db):
    """Airfoils without any polars must be processed."""
    from app.models.airfoil import AirfoilModel

    with backfill_db() as session:
        af = AirfoilModel(
            name="new_airfoil_for_backfill",
            coordinates=_SD7037_COORDS,
        )
        session.add(af)
        session.commit()

    fake_polar = {
        "reynolds": 100_000.0,
        "ld_max": 30.0,
        "cl_max": 1.1,
        "alpha_attached_lo": -2.0,
        "alpha_attached_hi": 10.0,
        "drag_bucket_width": 0.4,
        "cd_min": 0.015,
        "stall_gentleness": -0.1,
        "cd0": 0.016,
        "k": 0.05,
        "cl0": 0.2,
        "cl_valid_lo": 0.0,
        "cl_valid_hi": 1.0,
        "min_analysis_confidence": 0.92,
        "neuralfoil_model_size": "xxxlarge",
        "n_crit": 9.0,
        "computed_at": datetime.now(timezone.utc),
    }

    with patch(
        "app.services.airfoil_low_re_service.compute_airfoil_low_re", return_value=[fake_polar]
    ) as mock_compute:
        from scripts.backfill_airfoil_low_re import run_backfill

        with backfill_db() as session:
            run_backfill(session=session, force=False)
        processed = [c.args[0] for c in mock_compute.call_args_list]
        assert "new_airfoil_for_backfill" in processed


def test_backfill_force_flag_recomputes_all(backfill_db):
    """With force=True, all airfoils are recomputed regardless of computed_at."""
    from app.models.airfoil import AirfoilModel
    from app.models.airfoil_low_re import AirfoilLowRePolarModel
    from app.settings import Settings

    settings = Settings()

    with backfill_db() as session:
        af = AirfoilModel(name="force_recompute_af", coordinates=_SD7037_COORDS)
        session.add(af)
        session.flush()
        session.add(
            AirfoilLowRePolarModel(
                airfoil_name="force_recompute_af",
                reynolds=100_000.0,
                ld_max=30.0,
                cl_max=1.0,
                alpha_attached_lo=-2.0,
                alpha_attached_hi=10.0,
                drag_bucket_width=0.3,
                cd_min=0.018,
                stall_gentleness=-0.2,
                cd0=0.020,
                k=0.05,
                cl0=0.2,
                cl_valid_lo=0.0,
                cl_valid_hi=0.9,
                min_analysis_confidence=0.93,
                neuralfoil_model_size=settings.low_re_neuralfoil_model_size,
                n_crit=settings.low_re_n_crit,
                computed_at=datetime.now(timezone.utc),
            )
        )
        session.commit()

    with patch(
        "app.services.airfoil_low_re_service.compute_airfoil_low_re", return_value=[]
    ) as mock_compute:
        from scripts.backfill_airfoil_low_re import run_backfill

        with backfill_db() as session:
            run_backfill(session=session, force=True)
        processed = [c.args[0] for c in mock_compute.call_args_list]
        assert "force_recompute_af" in processed


def test_backfill_logs_progress(backfill_db, caplog):
    """Backfill must log progress (not silently truncate)."""
    from app.models.airfoil import AirfoilModel

    with backfill_db() as session:
        af = AirfoilModel(name="logged_af", coordinates=_SD7037_COORDS)
        session.add(af)
        session.commit()

    with patch("app.services.airfoil_low_re_service.compute_airfoil_low_re", return_value=[]):
        from scripts.backfill_airfoil_low_re import run_backfill

        with caplog.at_level(logging.INFO):
            with backfill_db() as session:
                run_backfill(session=session, force=False)
    # Something should have been logged
    assert len(caplog.records) > 0
