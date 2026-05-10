from __future__ import annotations

from sqlalchemy import Column, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base

COMPUTATION_CONFIG_DEFAULTS: dict[str, float | int] = {
    "coarse_alpha_min_deg": -5.0,
    "coarse_alpha_max_deg": 25.0,
    "coarse_alpha_step_deg": 1.0,
    "fine_alpha_margin_deg": 5.0,
    "fine_alpha_step_deg": 0.5,
    "fine_velocity_count": 8,
    "debounce_seconds": 2.0,
}


class AircraftComputationConfigModel(Base):
    """Per-aircraft sweep parameters for auto-compute of design assumptions.

    Stored in its own table (rather than as columns on AeroplaneModel) so
    the configuration surface can grow without churning the aeroplanes
    schema. Defaults live in code (COMPUTATION_CONFIG_DEFAULTS) and are
    seeded into rows by the service layer.
    """

    __tablename__ = "aircraft_computation_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    aeroplane_id = Column(
        Integer,
        ForeignKey("aeroplanes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    coarse_alpha_min_deg = Column(
        Float, nullable=False, default=COMPUTATION_CONFIG_DEFAULTS["coarse_alpha_min_deg"]
    )
    coarse_alpha_max_deg = Column(
        Float, nullable=False, default=COMPUTATION_CONFIG_DEFAULTS["coarse_alpha_max_deg"]
    )
    coarse_alpha_step_deg = Column(
        Float, nullable=False, default=COMPUTATION_CONFIG_DEFAULTS["coarse_alpha_step_deg"]
    )
    fine_alpha_margin_deg = Column(
        Float, nullable=False, default=COMPUTATION_CONFIG_DEFAULTS["fine_alpha_margin_deg"]
    )
    fine_alpha_step_deg = Column(
        Float, nullable=False, default=COMPUTATION_CONFIG_DEFAULTS["fine_alpha_step_deg"]
    )
    fine_velocity_count = Column(
        Integer, nullable=False, default=COMPUTATION_CONFIG_DEFAULTS["fine_velocity_count"]
    )
    debounce_seconds = Column(
        Float, nullable=False, default=COMPUTATION_CONFIG_DEFAULTS["debounce_seconds"]
    )

    aeroplane = relationship("AeroplaneModel", back_populates="computation_config")

    __table_args__ = (
        UniqueConstraint("aeroplane_id", name="uq_computation_config_aeroplane"),
    )
