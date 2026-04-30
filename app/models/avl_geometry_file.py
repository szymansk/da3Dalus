"""SQLAlchemy model for persisting user-edited AVL geometry files.

One record per aeroplane (enforced by the unique constraint on aeroplane_id).
The is_dirty flag signals that the stored content no longer matches what
would be auto-generated from the current aeroplane state.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import backref, relationship

from app.db.base import Base


class AvlGeometryFileModel(Base):
    __tablename__ = "avl_geometry_files"
    __table_args__ = (
        UniqueConstraint("aeroplane_id", name="uq_avl_geometry_files_aeroplane_id"),
    )

    aeroplane_id = Column(
        Integer,
        ForeignKey("aeroplanes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content = Column(Text, nullable=False)
    is_dirty = Column(Boolean, default=False, nullable=False)
    is_user_edited = Column(Boolean, default=False, nullable=False)
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

    aeroplane = relationship(
        "AeroplaneModel",
        backref=backref("avl_geometry_file", cascade="all, delete-orphan"),
    )
