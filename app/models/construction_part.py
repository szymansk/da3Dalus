"""Construction Part — per-aeroplane CAD bauteil (typically 3D-printed).

Complements the global COTS Component Library (``components`` table).
The MVP tracks only metadata and the ``locked`` flag that protects the
part from being overwritten by a future regeneration pipeline (gh#57-qim).
Actual STEP/STL file storage and full CRUD arrive in a follow-up ticket
(gh#57-9uk).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, func

from app.db.base import Base


class ConstructionPartModel(Base):
    """A CAD part that belongs to a specific aeroplane."""

    __tablename__ = "construction_parts"

    aeroplane_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)

    # Geometry metadata (populated when the file is uploaded; nullable until then)
    volume_mm3 = Column(Float, nullable=True)
    area_mm2 = Column(Float, nullable=True)
    bbox_x_mm = Column(Float, nullable=True)
    bbox_y_mm = Column(Float, nullable=True)
    bbox_z_mm = Column(Float, nullable=True)

    # Reference to a material entry in the generic component library
    # (components.component_type == 'material'). The service layer does not
    # enforce the type — the frontend filters the dropdown.
    material_component_id = Column(
        Integer,
        ForeignKey("components.id"),
        nullable=True,
    )

    # Lock protects the stored part from being overwritten by a regeneration
    # pipeline. Tree operations (move, add, remove) are not affected.
    locked = Column(Boolean, nullable=False, default=False, server_default="0")

    thumbnail_url = Column(String, nullable=True)

    # Local storage path for the uploaded CAD file (relative to cwd) and the
    # source format. Populated by the upload endpoint (gh#57-9uk). NULL until
    # a file has been uploaded.
    file_path = Column(String, nullable=True)
    file_format = Column(String, nullable=True)  # "step" or "stl"

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
