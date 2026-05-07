"""SQLAlchemy model for persisted stability analysis results."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.db.base import Base

_FK_AEROPLANES_ID = "aeroplanes.id"


class StabilityResultModel(Base):
    __tablename__ = "stability_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    aeroplane_id = Column(
        Integer,
        ForeignKey(_FK_AEROPLANES_ID, ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    solver = Column(String, nullable=False)
    neutral_point_x = Column(Float, nullable=True)
    mac = Column(Float, nullable=True)
    cg_x_used = Column(Float, nullable=True)
    static_margin_pct = Column(Float, nullable=True)
    stability_class = Column(String, nullable=True)
    cg_range_forward = Column(Float, nullable=True)
    cg_range_aft = Column(Float, nullable=True)
    Cma = Column(Float, nullable=True)
    Cnb = Column(Float, nullable=True)
    Clb = Column(Float, nullable=True)
    trim_alpha_deg = Column(Float, nullable=True)
    trim_elevator_deg = Column(Float, nullable=True)
    is_statically_stable = Column(Boolean, nullable=False, default=False)
    is_directionally_stable = Column(Boolean, nullable=False, default=False)
    is_laterally_stable = Column(Boolean, nullable=False, default=False)
    computed_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    status = Column(String, nullable=False, default="CURRENT")
    geometry_hash = Column(String, nullable=True)

    aeroplane = relationship("AeroplaneModel", back_populates="stability_results")

    __table_args__ = (
        UniqueConstraint("aeroplane_id", "solver", name="uq_stability_aeroplane_solver"),
    )
