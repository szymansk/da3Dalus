from sqlalchemy import Column, String, JSON, DateTime, func

from app.db.base import Base


class AirfoilModel(Base):
    """Airfoil profile stored as coordinate pairs."""

    __tablename__ = "airfoils"

    name = Column(String, nullable=False, unique=True, index=True)
    coordinates = Column(JSON, nullable=False)
    source_file = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
