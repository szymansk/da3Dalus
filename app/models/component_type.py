"""Component Type — defines the specs-schema for Components (gh#83).

Each row holds a JSON ``schema`` list of PropertyDefinition objects. The
service layer validates component specs against that schema on create /
update (tolerant mode: unknown keys are kept, known keys are checked).

Seeded types (the 9 original hardcoded ones) are inserted by the Alembic
migration with ``deletable=False`` so the user cannot remove them.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, JSON, String, func

from app.db.base import Base


class ComponentTypeModel(Base):
    __tablename__ = "component_types"

    name = Column(String, nullable=False, unique=True, index=True)
    label = Column(String, nullable=False)
    description = Column(String, nullable=True)
    # List of PropertyDefinition objects (see app.schemas.component_type).
    # Stored as JSON for schema flexibility; validated in the service layer.
    schema_def = Column("schema", JSON, nullable=False, default=list)
    # False for seeded types (prevents DELETE). User-created types get True.
    deletable = Column(Boolean, nullable=False, default=True, server_default="1")

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
