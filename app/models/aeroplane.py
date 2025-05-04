from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Table, JSON
from sqlalchemy.orm import relationship
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import TypeDecorator, CHAR
from datetime import datetime, timezone
from sqlalchemy import DateTime, func

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


class ControlSurface(Base):
    __tablename__ = "control_surfaces"
    name = Column(String, nullable=False)
    hinge_point = Column(Float, default=0.8)
    symmetric = Column(Boolean, default=True)
    deflection = Column(Float, default=0.0)

    # Relationship with WingXSec
    wing_xsec_id = Column(Integer, ForeignKey("wing_xsecs.id", ondelete="CASCADE"))
    wing_xsec = relationship("WingXSec", back_populates="control_surface")

class WingXSec(Base):
    __tablename__ = "wing_xsecs"
    xyz_le = Column(JSON, nullable=False)  # Store as JSON array
    chord = Column(Float, nullable=False)
    twist = Column(Float, nullable=False)
    airfoil = Column(String, nullable=False)  # Store path or URL as string

    # Relationship with Wing
    wing_id = Column(Integer, ForeignKey("wings.id", ondelete="CASCADE"))
    wing = relationship("Wing", back_populates="x_secs")

    # Relationship with ControlSurface
    control_surface = relationship("ControlSurface", back_populates="wing_xsec", uselist=False)
    # index to maintain ordering of cross-sections within a wing
    sort_index = Column(Integer, default=0, nullable=False)

class Wing(Base):
    __tablename__ = "wings"
    name = Column(String, nullable=False)
    symmetric = Column(Boolean, default=True)

    # One-to-many to WingXSec, ordered by sort_index
    x_secs = relationship(
        "WingXSec",
        back_populates="wing",
        cascade="all, delete-orphan",
        order_by="WingXSec.sort_index"
    )

    # ForeignKey to Aeroplane
    aeroplane_id = Column(Integer, ForeignKey("aeroplanes.id", ondelete="CASCADE"))
    aeroplane = relationship("Aeroplane", back_populates="wings")

    @classmethod
    def from_dict(cls, name, data):
        xsec_dicts = data.pop("x_secs", [])
        data.pop("name", None)
        wing = cls(name=name, **data)
        for xd in xsec_dicts:
            wing.x_secs.append(WingXSec(**xd))
        return wing

class FuselageXSecSuperEllipse(Base):
    __tablename__ = "fuselage_xsecs"
    xyz = Column(JSON, nullable=False)  # Store as JSON array
    a = Column(Float, nullable=False)
    b = Column(Float, nullable=False)
    n = Column(Float, nullable=False)

    # Relationship with Fuselage
    fuselage_id = Column(Integer, ForeignKey("fuselages.id", ondelete="CASCADE"))
    fuselage = relationship("Fuselage", back_populates="x_secs")

class Fuselage(Base):
    __tablename__ = "fuselages"
    name = Column(String, nullable=False)

    # Relationship with FuselageXSecSuperEllipse
    x_secs = relationship(
        "FuselageXSecSuperEllipse",
        back_populates="fuselage",
        cascade="all, delete-orphan")

    # ForeignKey to Aeroplane
    aeroplane_id = Column(Integer, ForeignKey("aeroplanes.id", ondelete="CASCADE"))
    aeroplane = relationship("Aeroplane", back_populates="fuselages")

class Aeroplane(Base):
    __tablename__ = "aeroplanes"
    uuid = Column(GUID, default=lambda: uuid.uuid4(), unique=True, nullable=False)
    name = Column(String, nullable=False)
    xyz_ref = Column(JSON, default=[0, 0, 0])  # Store as JSON array
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        server_onupdate=func.now(),
        nullable=False
    )

    # Relationships
    wings = relationship(
        "Wing",
        back_populates="aeroplane",
        cascade="all, delete-orphan")
    fuselages = relationship(
        "Fuselage",
        back_populates="aeroplane",
        cascade="all, delete-orphan")
