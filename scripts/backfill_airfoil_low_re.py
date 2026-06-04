"""Backfill CLI for low-Re airfoil suitability scoring (gh-821).

Idempotent: skips airfoils whose polars are already computed with the current
model_size. Imports legacy .dat files from components/airfoils/ first, then
computes polars for all airfoils in the DB.

Usage
-----
    poetry run python scripts/backfill_airfoil_low_re.py [--force]
    # OR import run_backfill for programmatic use in tests

Important: do NOT modify existing airfoil coordinates. This script is purely
additive (inserts/updates airfoil_geometry and airfoil_low_re_polar rows).
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# Add repo root to sys.path when run as a script
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def run_backfill(
    session=None,
    force: bool = False,
    model_size: Optional[str] = None,
    n_crit: Optional[float] = None,
) -> None:
    """Run the low-Re airfoil backfill.

    Parameters
    ----------
    session : SQLAlchemy Session
        Database session to use. If None, a session is created from the
        default engine.
    force : bool
        If True, recompute all airfoils regardless of existing computed_at.
    model_size : str, optional
        Override the NeuralFoil model size from settings.
    n_crit : float, optional
        Override the n_crit from settings.
    """
    from app.models.airfoil import AirfoilModel
    from app.models.airfoil_low_re import AirfoilGeometryModel, AirfoilLowRePolarModel
    from app.services.airfoil_low_re_service import (
        classify_family,
        compute_airfoil_low_re,
    )
    from app.settings import Settings

    settings = Settings()
    _model_size = model_size or settings.low_re_neuralfoil_model_size
    _n_crit = n_crit if n_crit is not None else settings.low_re_n_crit
    re_grid = settings.low_re_grid

    # Determine which session to use
    _own_session = False
    if session is None:
        from app.db.session import SessionLocal

        session = SessionLocal()
        _own_session = True

    try:
        # Load all airfoils from DB
        airfoils = session.query(AirfoilModel).all()
        total = len(airfoils)
        logger.info("Backfill: found %d airfoil(s) in DB", total)

        skipped = 0
        computed = 0

        for idx, af in enumerate(airfoils):
            name = af.name
            logger.info("[%d/%d] Processing '%s'", idx + 1, total, name)

            # Check idempotency: skip if all Re-grid points are already computed
            # with the current model_size (unless force=True)
            if not force:
                existing_polars = (
                    session.query(AirfoilLowRePolarModel)
                    .filter(
                        AirfoilLowRePolarModel.airfoil_name == name,
                        AirfoilLowRePolarModel.neuralfoil_model_size == _model_size,
                    )
                    .all()
                )
                existing_re = {float(p.reynolds) for p in existing_polars}
                grid_set = {float(r) for r in re_grid}
                if grid_set.issubset(existing_re):
                    logger.info("  Skipping '%s' — already fully computed", name)
                    skipped += 1
                    continue

            # Get coordinates
            coords = af.coordinates
            if not coords or len(coords) < 2:
                logger.warning("  Skipping '%s' — no coordinates", name)
                continue

            coords_arr = np.asarray(coords, dtype=float)

            # Compute geometry (classify family)
            try:
                family = classify_family(coords_arr)
                # Compute geometry stats
                max_thickness_pct, max_camber_pct, camber_at_te = _compute_geometry_stats(
                    coords_arr
                )

                # Upsert geometry
                geo = (
                    session.query(AirfoilGeometryModel)
                    .filter(AirfoilGeometryModel.airfoil_name == name)
                    .first()
                )
                if geo is None:
                    geo = AirfoilGeometryModel(airfoil_name=name)
                    session.add(geo)
                geo.max_thickness_pct = max_thickness_pct
                geo.max_camber_pct = max_camber_pct
                geo.camber_at_te = camber_at_te
                geo.family = family
                geo.computed_at = datetime.now(timezone.utc)
            except Exception as e:
                logger.warning("  Geometry failed for '%s': %s", name, e)

            # Compute polars (mocked in tests via monkeypatch on compute_airfoil_low_re)
            try:
                polar_results = compute_airfoil_low_re(
                    name,
                    coords_arr,
                    re_grid,
                    model_size=_model_size,
                    n_crit=_n_crit,
                    confidence_gate=settings.low_re_confidence_gate,
                )
            except Exception as e:
                logger.error("  Compute failed for '%s': %s", name, e)
                polar_results = []

            # Upsert polars
            for row in polar_results:
                re_val = float(row["reynolds"])
                polar_row = (
                    session.query(AirfoilLowRePolarModel)
                    .filter(
                        AirfoilLowRePolarModel.airfoil_name == name,
                        AirfoilLowRePolarModel.reynolds == re_val,
                    )
                    .first()
                )
                if polar_row is None:
                    polar_row = AirfoilLowRePolarModel(
                        airfoil_name=name,
                        reynolds=re_val,
                    )
                    session.add(polar_row)

                # Update all fields
                for field_name, value in row.items():
                    if field_name != "reynolds" and hasattr(polar_row, field_name):
                        setattr(polar_row, field_name, value)

            computed += 1
            logger.info("  '%s' done (%d polar points)", name, len(polar_results))

        session.commit()
        logger.info(
            "Backfill complete: %d computed, %d skipped, %d total",
            computed,
            skipped,
            total,
        )

    except Exception as exc:
        logger.error("Backfill failed: %s", exc)
        session.rollback()
        raise
    finally:
        if _own_session:
            session.close()


def _compute_geometry_stats(coords: np.ndarray) -> tuple[float, float, float]:
    """Extract max_thickness_pct, max_camber_pct, camber_at_te from coordinates."""
    coords = np.asarray(coords, dtype=float)
    le_idx = int(np.argmin(coords[:, 0]))
    seg_a = coords[: le_idx + 1]
    seg_b = coords[le_idx:]

    if len(seg_a) > 1 and seg_a[0, 0] > seg_a[-1, 0]:
        seg_a = seg_a[::-1]
    if len(seg_b) > 1 and seg_b[0, 0] > seg_b[-1, 0]:
        seg_b = seg_b[::-1]

    x_ref = 0.3
    y_a = float(np.interp(x_ref, np.sort(seg_a[:, 0]), seg_a[np.argsort(seg_a[:, 0]), 1]))
    y_b = float(np.interp(x_ref, np.sort(seg_b[:, 0]), seg_b[np.argsort(seg_b[:, 0]), 1]))

    if y_a >= y_b:
        upper, lower = seg_a, seg_b
    else:
        upper, lower = seg_b, seg_a

    upper_s = upper[np.argsort(upper[:, 0])]
    lower_s = lower[np.argsort(lower[:, 0])]
    x_min = max(upper_s[0, 0], lower_s[0, 0])
    x_max = min(upper_s[-1, 0], lower_s[-1, 0])
    x_eval = np.linspace(x_min, x_max, 200)

    y_upper = np.interp(x_eval, upper_s[:, 0], upper_s[:, 1])
    y_lower = np.interp(x_eval, lower_s[:, 0], lower_s[:, 1])
    thickness = y_upper - y_lower
    camber = (y_upper + y_lower) / 2.0

    max_thickness_pct = float(np.max(thickness)) * 100.0
    max_camber_pct = float(np.max(np.abs(camber))) * 100.0
    camber_at_te = float(camber[-1])

    return max_thickness_pct, max_camber_pct, camber_at_te


def main() -> None:
    """CLI entry point."""
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Backfill low-Re airfoil suitability polars (gh-821)."
    )
    parser.add_argument(
        "--force", action="store_true", help="Recompute all airfoils even if already computed."
    )
    parser.add_argument(
        "--model-size",
        default=None,
        help="Override NeuralFoil model size (default from settings: xxxlarge).",
    )
    parser.add_argument(
        "--import-dir",
        default="components/airfoils",
        help="Path to legacy .dat files directory (imported into DB first).",
    )
    args = parser.parse_args()

    # Optionally import legacy .dat files first
    import_dir = Path(args.import_dir)
    if import_dir.exists():
        logger.info("Importing legacy .dat files from %s", import_dir)
        try:
            from app.db.session import SessionLocal
            from app.services.airfoil_service import import_directory

            with SessionLocal() as session:
                result = import_directory(session, str(import_dir))
                session.commit()
                logger.info(
                    "Import: %d new, %d skipped, %d errors",
                    result.imported,
                    result.skipped,
                    result.errors,
                )
        except Exception as e:
            logger.warning("Import of .dat files failed: %s", e)

    run_backfill(force=args.force, model_size=args.model_size)


if __name__ == "__main__":
    main()
