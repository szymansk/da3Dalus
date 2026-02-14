from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class RCFlightProfileModel(Base):
    """Persistent RC flight intent profile used to derive operating points."""

    __tablename__ = "rc_flight_profiles"

    # Unique profile name shown in UI, e.g. "rc_trainer_balanced".
    name = Column(String, nullable=False, unique=True, index=True)
    # Category used to filter profiles and apply defaults.
    type = Column(String, nullable=False) 
    # Environmental assumptions in SI units.
    environment = Column(JSON, nullable=False)
    # Performance targets (speeds, margins, load factor, loiter goal).
    goals = Column(JSON, nullable=False)
    # Desired handling qualities for pilot feel.
    handling = Column(JSON, nullable=False)
    # Hard limits that generated points must respect.
    constraints = Column(JSON, nullable=False)

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

    aircraft = relationship("AeroplaneModel", back_populates="flight_profile")
