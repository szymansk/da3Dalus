"""Tessellation Cache Service — persist and retrieve 3D viewer geometry.

Stores tessellated shapes in the DB keyed by (aeroplane_id, component_type,
component_name, geometry_hash). The hash detects geometry changes — when
the underlying wing/fuselage schema changes, the cache entry is marked
stale and a background re-tessellation is enqueued.
"""

import hashlib
import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.aeroplanemodel import AeroplaneModel
from app.models.tessellation_cache import TessellationCacheModel

logger = logging.getLogger(__name__)


def compute_geometry_hash(wing_or_fuselage_data: dict) -> str:
    """Compute a deterministic SHA256 hash of the geometry data.

    The hash changes whenever the wing/fuselage ASB schema changes,
    which tells us the cached tessellation is stale.
    """
    canonical = json.dumps(wing_or_fuselage_data, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def get_cached(
    db: Session,
    aeroplane_id: int,
    component_type: str,
    component_name: str,
) -> Optional[TessellationCacheModel]:
    """Get cached tessellation for a specific component."""
    return (
        db.query(TessellationCacheModel)
        .filter(
            TessellationCacheModel.aeroplane_id == aeroplane_id,
            TessellationCacheModel.component_type == component_type,
            TessellationCacheModel.component_name == component_name,
        )
        .first()
    )


def get_all_cached(
    db: Session,
    aeroplane_id: int,
) -> list[TessellationCacheModel]:
    """Get all cached tessellations for an aeroplane."""
    return (
        db.query(TessellationCacheModel)
        .filter(TessellationCacheModel.aeroplane_id == aeroplane_id)
        .all()
    )


def cache_tessellation(
    db: Session,
    aeroplane_id: int,
    component_type: str,
    component_name: str,
    geometry_hash: str,
    tessellation_json: dict,
) -> TessellationCacheModel:
    """Store or update tessellation cache for a component."""
    existing = get_cached(db, aeroplane_id, component_type, component_name)

    if existing:
        existing.geometry_hash = geometry_hash
        existing.tessellation_json = tessellation_json
        existing.is_stale = False
        db.commit()
        db.refresh(existing)
        return existing

    entry = TessellationCacheModel(
        aeroplane_id=aeroplane_id,
        component_type=component_type,
        component_name=component_name,
        geometry_hash=geometry_hash,
        tessellation_json=tessellation_json,
        is_stale=False,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def invalidate(
    db: Session,
    aeroplane_id: int,
    component_type: Optional[str] = None,
    component_name: Optional[str] = None,
) -> int:
    """Mark cache entries as stale. Returns count of invalidated entries.

    If component_type/name are provided, invalidates only that component.
    Otherwise invalidates all entries for the aeroplane.
    """
    query = db.query(TessellationCacheModel).filter(
        TessellationCacheModel.aeroplane_id == aeroplane_id,
        TessellationCacheModel.is_stale == False,  # noqa: E712
    )
    if component_type:
        query = query.filter(TessellationCacheModel.component_type == component_type)
    if component_name:
        query = query.filter(TessellationCacheModel.component_name == component_name)

    count = query.update({"is_stale": True})
    db.commit()
    return count


def is_hash_current(
    db: Session,
    aeroplane_id: int,
    component_type: str,
    component_name: str,
    geometry_hash: str,
) -> bool:
    """Check if the geometry hash matches the current cache entry.

    Used by the background worker to discard stale results — if the
    hash changed while tessellation was running, the result is outdated.
    """
    existing = get_cached(db, aeroplane_id, component_type, component_name)
    if not existing:
        return True  # No cache yet, any hash is "current"
    return existing.geometry_hash == geometry_hash
