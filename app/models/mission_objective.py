"""SQLAlchemy model for per-aeroplane Mission Objectives (gh-546)."""

from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class MissionObjectiveModel(Base):
    __tablename__ = "mission_objectives"

    id = Column(Integer, primary_key=True)
    aeroplane_id = Column(
        Integer,
        ForeignKey("aeroplanes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # one row per aeroplane
        index=True,
    )

    mission_type = Column(String, nullable=False, default="trainer")

    # Performance targets
    target_cruise_mps = Column(Float, nullable=False, default=18.0)
    target_stall_safety = Column(Float, nullable=False, default=1.8)
    target_maneuver_n = Column(Float, nullable=False, default=3.0)
    target_glide_ld = Column(Float, nullable=False, default=12.0)
    target_climb_energy = Column(Float, nullable=False, default=22.0)
    target_wing_loading_n_m2 = Column(Float, nullable=False, default=412.0)  # ~42 g/dm²
    target_field_length_m = Column(Float, nullable=False, default=50.0)

    # Field Performance (migrated from Assumptions)
    available_runway_m = Column(Float, nullable=False, default=50.0)
    runway_type = Column(String, nullable=False, default="grass")
    t_static_N = Column(Float, nullable=False, default=18.0)
    takeoff_mode = Column(String, nullable=False, default="runway")

    aeroplane = relationship("AeroplaneModel", back_populates="mission_objective")
