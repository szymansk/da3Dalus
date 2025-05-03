from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Table, JSON
from sqlalchemy.orm import relationship
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy import text

from app.db.base import Base

# Custom UUID type for SQLite compatibility
class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses
    CHAR(32), storing as stringified hex values.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return "%.32x" % uuid.UUID(value).int
            else:
                # hexstring
                return "%.32x" % value.int

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                value = uuid.UUID(value)
            return value

# Association tables for many-to-many relationships
wing_association = Table(
    'wing_association',
    Base.metadata,
    Column('aeroplane_id', Integer, ForeignKey('aeroplanes.id')),
    Column('wing_id', Integer, ForeignKey('wings.id'))
)

fuselage_association = Table(
    'fuselage_association',
    Base.metadata,
    Column('aeroplane_id', Integer, ForeignKey('aeroplanes.id')),
    Column('fuselage_id', Integer, ForeignKey('fuselages.id'))
)

class ControlSurface(Base):
    __tablename__ = "control_surfaces"
    name = Column(String, nullable=False)
    hinge_point = Column(Float, default=0.8)
    symmetric = Column(Boolean, default=True)
    deflection = Column(Float, default=0.0)

    # Relationship with WingXSec
    wing_xsec_id = Column(Integer, ForeignKey("wing_xsecs.id"))
    wing_xsec = relationship("WingXSec", back_populates="control_surface")

class WingXSec(Base):
    __tablename__ = "wing_xsecs"
    xyz_le = Column(JSON, nullable=False)  # Store as JSON array
    chord = Column(Float, nullable=False)
    twist = Column(Float, nullable=False)
    airfoil = Column(String, nullable=False)  # Store path or URL as string

    # Relationship with Wing
    wing_id = Column(Integer, ForeignKey("wings.id"))
    wing = relationship("Wing", back_populates="x_secs")

    # Relationship with ControlSurface
    control_surface = relationship("ControlSurface", back_populates="wing_xsec", uselist=False)

class Wing(Base):
    __tablename__ = "wings"
    name = Column(String, nullable=False)
    symmetric = Column(Boolean, default=True)

    # Relationship with WingXSec
    x_secs = relationship("WingXSec", back_populates="wing", cascade="all, delete-orphan")

    # Relationship with Aeroplane
    aeroplanes = relationship("Aeroplane", secondary=wing_association, back_populates="wings")

class FuselageXSecSuperEllipse(Base):
    __tablename__ = "fuselage_xsecs"
    xyz = Column(JSON, nullable=False)  # Store as JSON array
    a = Column(Float, nullable=False)
    b = Column(Float, nullable=False)
    n = Column(Float, nullable=False)

    # Relationship with Fuselage
    fuselage_id = Column(Integer, ForeignKey("fuselages.id"))
    fuselage = relationship("Fuselage", back_populates="x_secs")

class Fuselage(Base):
    __tablename__ = "fuselages"
    name = Column(String, nullable=False)

    # Relationship with FuselageXSecSuperEllipse
    x_secs = relationship("FuselageXSecSuperEllipse", back_populates="fuselage", cascade="all, delete-orphan")

    # Relationship with Aeroplane
    aeroplanes = relationship("Aeroplane", secondary=fuselage_association, back_populates="fuselages")

class Aeroplane(Base):
    __tablename__ = "aeroplanes"
    uuid = Column(GUID, default=lambda: uuid.uuid4(), unique=True, nullable=False)
    name = Column(String, nullable=False)
    xyz_ref = Column(JSON, default=[0, 0, 0])  # Store as JSON array

    # Relationships
    wings = relationship("Wing", secondary=wing_association, back_populates="aeroplanes")
    fuselages = relationship("Fuselage", secondary=fuselage_association, back_populates="aeroplanes")
