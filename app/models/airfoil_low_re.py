"""SQLAlchemy models for low-Re airfoil precomputed data (gh-821).

This module stores:
  - AirfoilGeometryModel  — Re-independent geometry (1:1 per airfoil)
  - AirfoilLowRePolarModel — per-(airfoil, Re-grid-point) scalar metrics
                              + parabolic drag-polar fit

IMPORTANT DISTINCTION from polar_re_table_service (gh-493):
  - polar_re_table_service is *aircraft-level*: it re-bins aircraft fine-sweep
    data into speed-band (V-band) labels, where "Re" is a speed proxy for the
    main-wing MAC at the current flight condition.
  - This module is *2D per-airfoil*: polars are computed across an absolute Re
    grid (40k–750k) directly from NeuralFoil for each airfoil shape, independent
    of any aircraft context. The two Re concepts must NOT be confused.
"""

from __future__ import annotations

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)

from app.db.base import Base


class AirfoilGeometryModel(Base):
    """Re-independent geometry statistics for one airfoil (1:1 with airfoils).

    Derived from the raw coordinate data; recomputed whenever an airfoil is
    imported. The `family` field uses the frozen classifier labels:
    flat_bottom | semi_symmetric | symmetric | cambered | reflexed.
    """

    __tablename__ = "airfoil_geometry"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    # airfoil_name: unique, indexed, FK → airfoils.name (natural 1:1 key)
    airfoil_name = Column(
        String,
        ForeignKey("airfoils.name", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    max_thickness_pct = Column(Float, nullable=False)
    max_camber_pct = Column(Float, nullable=False)
    # Camber-line value at the trailing edge (x≈1). Positive → reflexed TE.
    camber_at_te = Column(Float, nullable=False)
    # Family label assigned by the heuristic classifier.
    family = Column(String, nullable=False)
    computed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class AirfoilLowRePolarModel(Base):
    """Scalar low-Re metrics + parabolic drag-polar fit for one (airfoil, Re).

    One row per (airfoil_name, reynolds) grid-point. Unique constraint
    enforces idempotent upserts during backfill.

    Parabolic fit: CD = cd0 + k·(CL − cl0)²
    Validity range [cl_valid_lo, cl_valid_hi] is the CL window where the
    parabolic fit is trusted (analysis_confidence ≥ gate over that range).
    """

    __tablename__ = "airfoil_low_re_polar"
    __table_args__ = (UniqueConstraint("airfoil_name", "reynolds", name="uq_airfoil_low_re_polar"),)

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    airfoil_name = Column(
        String,
        ForeignKey("airfoils.name", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reynolds = Column(Float, nullable=False, index=True)

    # Scalar performance metrics (gated at analysis_confidence ≥ 0.90)
    ld_max = Column(Float, nullable=True)  # (L/D)_max within trusted range
    cl_max = Column(Float, nullable=True)  # CL_max within trusted range
    alpha_attached_lo = Column(Float, nullable=True)  # deg, start of attached-flow window
    alpha_attached_hi = Column(Float, nullable=True)  # deg, end of attached-flow window
    drag_bucket_width = Column(Float, nullable=True)  # ΔCL where CD ≤ 1.15·CD_min
    cd_min = Column(Float, nullable=True)
    stall_gentleness = Column(Float, nullable=True)  # dCL/dα just past peak (≈0 gentle)

    # Parabolic drag-polar fit: CD = cd0 + k*(CL - cl0)^2
    cd0 = Column(Float, nullable=True)
    k = Column(Float, nullable=True)
    cl0 = Column(Float, nullable=True)
    cl_valid_lo = Column(Float, nullable=True)
    cl_valid_hi = Column(Float, nullable=True)

    # Trust badge: min over the swept α-range
    min_analysis_confidence = Column(Float, nullable=True)

    # Provenance — allows idempotent backfill to skip up-to-date rows
    neuralfoil_model_size = Column(String, nullable=False, default="xxxlarge")
    n_crit = Column(Float, nullable=False, default=9.0)
    computed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
