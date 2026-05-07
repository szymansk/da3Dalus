"""SQLAlchemy model for persisted flight envelope results."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON
from sqlalchemy.orm import relationship

from app.db.base import Base


class FlightEnvelopeModel(Base):
    """Cached flight-envelope computation for an aeroplane.

    One envelope per aeroplane (unique constraint on aeroplane_id).
    Upserted on every recompute.
    """

    __tablename__ = "flight_envelopes"

    id = Column(Integer, primary_key=True)
    aeroplane_id = Column(
        Integer,
        ForeignKey("aeroplanes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    vn_curve_json = Column(JSON, nullable=False)
    kpis_json = Column(JSON, nullable=False)
    markers_json = Column(JSON, nullable=False)
    assumptions_snapshot = Column(JSON, nullable=False)
    computed_at = Column(DateTime(timezone=True), nullable=False)

    aeroplane = relationship("AeroplaneModel", backref="flight_envelope")
