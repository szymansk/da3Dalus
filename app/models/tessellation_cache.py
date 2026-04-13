from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON
from sqlalchemy import DateTime, func
from datetime import datetime, timezone

from app.db.base import Base


class TessellationCacheModel(Base):
    """Caches tessellated 3D geometry for wings and fuselages.

    Each entry stores the three-cad-viewer JSON for one component
    (wing or fuselage). A geometry_hash detects changes — when the
    underlying ASB schema changes, the cache is marked stale and
    a background re-tessellation is triggered.
    """
    __tablename__ = "tessellation_cache"

    aeroplane_id = Column(
        Integer, ForeignKey("aeroplanes.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    component_type = Column(String, nullable=False)  # "wing" | "fuselage"
    component_name = Column(String, nullable=False)
    geometry_hash = Column(String, nullable=False)
    tessellation_json = Column(JSON, nullable=False)
    is_stale = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        server_onupdate=func.now(),
        nullable=False,
    )
