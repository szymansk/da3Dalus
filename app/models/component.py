from sqlalchemy import Column, Integer, String, Float, JSON
from sqlalchemy import DateTime, func
from datetime import datetime, timezone

from app.db.base import Base


class ComponentModel(Base):
    """Generic hardware component for the component library.

    Uses a JSON `specs` column for type-specific fields (mass_g, kv, capacity_mah, etc.)
    so every component type shares one table. The `component_type` discriminator
    enables filtering and validation at the schema/service layer.
    """
    __tablename__ = "components"

    name = Column(String, nullable=False)
    component_type = Column(String, nullable=False, index=True)
    manufacturer = Column(String, nullable=True)
    description = Column(String, nullable=True)
    mass_g = Column(Float, nullable=True)
    bbox_x_mm = Column(Float, nullable=True)
    bbox_y_mm = Column(Float, nullable=True)
    bbox_z_mm = Column(Float, nullable=True)
    model_ref = Column(String, nullable=True)
    specs = Column(JSON, nullable=False, default=dict)
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
