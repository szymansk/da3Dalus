from sqlalchemy import Column, Float, JSON, String, Integer

from app.db.base import Base

class OperatingPointSetModel(Base):
    __tablename__ = "operating_pointsets"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    operating_points = Column(JSON, nullable=False)  # Store as JSON array of OperatingPointModel IDs

class OperatingPointModel(Base):
    __tablename__ = "operating_points"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)

    # Operating point parameters
    velocity = Column(Float, nullable=False)
    alpha = Column(Float, nullable=False)
    beta = Column(Float, nullable=False)
    p = Column(Float, nullable=False)
    q = Column(Float, nullable=False)
    r = Column(Float, nullable=False)

    xyz_ref = Column(JSON, nullable=False)
    # Atmosphere parameters
    altitude = Column(Float, nullable=False)
