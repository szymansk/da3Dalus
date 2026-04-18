"""Construction Plan — JSON-defined build workflows (gh#101)."""

from datetime import datetime, timezone

from sqlalchemy import Column, ForeignKey, String, DateTime, func
from sqlalchemy.types import JSON

from app.db.base import Base


class ConstructionPlanModel(Base):
    """A reusable construction plan stored as a JSON tree.

    The tree_json column holds the serialised ConstructionRootNode /
    ConstructionStepNode hierarchy produced by GeneralJSONEncoder.
    Plans are not bound to a specific aeroplane — the aeroplane
    provides runtime configuration (wing_config, printer_settings)
    at execution time.
    """

    __tablename__ = "construction_plans"

    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    tree_json = Column(JSON, nullable=False)
    plan_type = Column(String, nullable=False, default="template")
    aeroplane_id = Column(String, ForeignKey("aeroplanes.id"), nullable=True)

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
