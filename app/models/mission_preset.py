"""SQLAlchemy model for Mission Presets library (gh-546)."""

from sqlalchemy import JSON, Column, Integer, String

from app.db.base import Base


class MissionPresetModel(Base):
    __tablename__ = "mission_presets"

    id = Column(String, primary_key=True)  # stable preset id "trainer", etc.
    label = Column(String, nullable=False)
    description = Column(String, nullable=False, default="")
    target_polygon = Column(JSON, nullable=False)  # dict[AxisName, float]
    axis_ranges = Column(JSON, nullable=False)  # dict[AxisName, [min, max]]
    suggested_estimates = Column(JSON, nullable=False)  # MissionPresetEstimates dict
