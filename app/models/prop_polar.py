"""Propeller performance polar models (gh-995).

Two tables:
  - propeller_polars: one row per propeller (APC 9x6 etc.) — metadata +
    source/version bookkeeping.
  - propeller_polar_samples: one row per (propeller, RPM, advance-ratio)
    measurement point — the actual Ct/Cp/Pe/Thrust/Power/Torque values.

Pattern mirrors airfoil_low_re.py: separate header + data-point tables so
the data can be queried efficiently by propeller or by RPM.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class PropellerPolarModel(Base):
    """Per-propeller metadata + source bookkeeping.

    Keyed by (manufacturer, name) for idempotent re-import.
    """

    __tablename__ = "propeller_polars"

    manufacturer = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    model_ref = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    source_version = Column(String, nullable=True)

    # Propeller geometry
    diameter_in = Column(Float, nullable=True)  # inches
    pitch_in = Column(Float, nullable=True)  # inches
    blades = Column(Integer, nullable=True, default=2)

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

    samples = relationship(
        "PropellerPolarSampleModel",
        back_populates="propeller",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )


class PropellerPolarSampleModel(Base):
    """One measurement point: (propeller, RPM, advance-ratio) → coefficients.

    Columns follow APC PER3 file definitions:
      J         = V / (n·D)          advance ratio (dimensionless)
      Ct        = T / (ρ·n²·D⁴)     thrust coefficient (dimensionless)
      Cp        = P / (ρ·n³·D⁵)     power coefficient (dimensionless)
      Pe        = Ct·J / Cp          propulsive efficiency (dimensionless)
      PWR_W                          shaft power in Watts
      Torque_Nm                      shaft torque in Newton-metres
      Thrust_N                       thrust force in Newtons
    """

    __tablename__ = "propeller_polar_samples"

    propeller_id = Column(Integer, ForeignKey("propeller_polars.id"), nullable=False, index=True)
    rpm = Column(Integer, nullable=False, index=True)

    # APC PER3 dimensionless coefficients
    J = Column(Float, nullable=False)
    Ct = Column(Float, nullable=False)
    Cp = Column(Float, nullable=False)
    Pe = Column(Float, nullable=True)  # 0 at static (J=0); nullable for safety

    # Dimensional quantities (SI)
    PWR_W = Column(Float, nullable=True)  # shaft power [W]
    Torque_Nm = Column(Float, nullable=True)  # shaft torque [N·m]
    Thrust_N = Column(Float, nullable=True)  # thrust [N]

    propeller = relationship(
        "PropellerPolarModel",
        back_populates="samples",
    )
