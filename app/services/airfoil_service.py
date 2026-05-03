"""Service layer for airfoil profile management."""
from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import InternalError, NotFoundError
from app.models.airfoil import AirfoilModel
from app.schemas.airfoil import AirfoilImportResult, AirfoilRead, AirfoilSummary

logger = logging.getLogger(__name__)


def list_airfoils(db: Session) -> list[AirfoilSummary]:
    """List all airfoil names."""
    try:
        airfoils = db.query(AirfoilModel).order_by(AirfoilModel.name).all()
        return [AirfoilSummary.model_validate(a) for a in airfoils]
    except SQLAlchemyError as e:
        logger.error("DB error listing airfoils: %s", e)
        raise InternalError(message=f"Database error: {e}") from e


def get_airfoil(db: Session, name: str) -> AirfoilRead:
    """Get airfoil by name (case-insensitive)."""
    try:
        airfoil = (
            db.query(AirfoilModel)
            .filter(func.lower(AirfoilModel.name) == name.lower())
            .first()
        )
        if airfoil is None:
            raise NotFoundError(entity="Airfoil", resource_id=name)
        return AirfoilRead.model_validate(airfoil)
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        logger.error("DB error getting airfoil '%s': %s", name, e)
        raise InternalError(message=f"Database error: {e}") from e


def get_airfoil_coordinates(db: Session, name: str) -> list[tuple[float, float]] | None:
    """Get airfoil coordinates as list of (x, y) tuples.

    Used by the CadQuery airfoil plugin as a DB-backed alternative
    to reading .dat files from the filesystem.
    """
    airfoil = (
        db.query(AirfoilModel)
        .filter(func.lower(AirfoilModel.name) == name.lower())
        .first()
    )
    if airfoil is None:
        return None
    return [(p[0], p[1]) for p in airfoil.coordinates]


def _parse_dat_file(path: Path) -> tuple[str, list[list[float]]]:
    """Parse a Selig-format .dat file.

    Returns (airfoil_name, [[x, y], ...]).
    Raises ValueError if the file cannot be parsed.
    """
    lines = path.read_text(encoding="utf-8", errors="replace").strip().splitlines()
    if len(lines) < 3:
        raise ValueError(f"Too few lines ({len(lines)})")

    # Use the filename stem as the canonical name (e.g. "rg15" from "rg15.dat").
    # This matches how the CQ plugin looks up airfoils (by file stem, not Selig header).
    airfoil_name = path.stem

    # Parse coordinate lines
    coords = []
    for line in lines[1:]:
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            x = float(parts[0])
            y = float(parts[1])
            coords.append([x, y])
        except ValueError:
            continue

    if len(coords) < 3:
        raise ValueError(f"Too few valid coordinates ({len(coords)})")

    return airfoil_name, coords


def import_directory(db: Session, directory: str) -> AirfoilImportResult:
    """Recursively scan a directory for .dat files and import new airfoils.

    - Case-insensitive dedup: if an airfoil with the same name (ignoring case)
      already exists, it is skipped.
    - Malformed files are skipped with a warning.
    """
    dir_path = Path(directory).resolve()
    # Security: restrict import to the project's components directory
    project_root = Path(__file__).resolve().parent.parent.parent
    allowed_base = project_root / "components"
    try:
        dir_path.relative_to(allowed_base)
    except ValueError:
        from app.core.exceptions import ValidationError as VE
        raise VE(message=f"Import directory must be within {allowed_base}")
    if not dir_path.is_dir():
        raise NotFoundError(entity="Directory", resource_id=directory)

    # Load existing names for dedup (lowercase)
    try:
        existing_names = {
            name.lower()
            for (name,) in db.query(AirfoilModel.name).all()
        }
    except SQLAlchemyError as e:
        raise InternalError(message=f"Database error: {e}") from e

    result = AirfoilImportResult()

    for dat_file in sorted(dir_path.rglob("*.dat")):
        try:
            airfoil_name, coords = _parse_dat_file(dat_file)
        except Exception as exc:
            logger.warning("Skipping malformed airfoil file %s: %s", dat_file.name, exc)
            result.errors += 1
            result.error_files.append(dat_file.name)
            continue

        if airfoil_name.lower() in existing_names:
            result.skipped += 1
            continue

        try:
            model = AirfoilModel(
                name=airfoil_name,
                coordinates=coords,
                source_file=dat_file.name,
            )
            db.add(model)
            db.flush()
            existing_names.add(airfoil_name.lower())
            result.imported += 1
        except SQLAlchemyError as exc:
            logger.warning("Failed to import airfoil '%s': %s", airfoil_name, exc)
            result.errors += 1
            result.error_files.append(dat_file.name)

    logger.info(
        "Airfoil import: %d imported, %d skipped, %d errors",
        result.imported, result.skipped, result.errors,
    )
    return result
