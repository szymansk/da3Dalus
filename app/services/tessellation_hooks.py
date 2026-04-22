"""Tessellation hooks — called after geometry-changing operations.

These hooks bridge wing/fuselage mutation endpoints to the tessellation
cache, ensuring that stale entries are invalidated promptly and (in a
future iteration) background re-tessellation is triggered automatically.
"""

import logging

from sqlalchemy.orm import Session

from app.models.aeroplanemodel import AeroplaneModel

logger = logging.getLogger(__name__)


def on_wing_changed(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
) -> None:
    """Invalidate the tessellation cache after a wing geometry change.

    Called from wing endpoints after any successful create / update /
    delete operation that modifies wing geometry.

    Args:
        db: Active SQLAlchemy session (the same one used by the endpoint).
        aeroplane_uuid: UUID of the aeroplane (as passed to the endpoint).
        wing_name: Name of the wing that changed.
    """
    from app.services import tessellation_cache_service as cache_svc

    aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == str(aeroplane_uuid)).first()
    if aeroplane is None:
        logger.warning(
            "Cannot invalidate tessellation cache — aeroplane %s not found",
            aeroplane_uuid,
        )
        return

    count = cache_svc.invalidate(db, aeroplane.id, "wing", wing_name)
    if count:
        safe_wing_name = wing_name.replace("\n", "").replace("\r", "")
        logger.info(
            "Invalidated %d tessellation cache entries for aeroplane=%s wing=%s",
            count,
            aeroplane.id,
            safe_wing_name,
        )

    # See GH #202: Trigger background re-tessellation.
    # This requires re-loading the wing schema from the DB, pickling it,
    # and calling tessellation_service.trigger_background_tessellation().
    # Deferred because it needs a separate DB session factory and careful
    # wiring into the wing service to obtain the wing schema pickle.
