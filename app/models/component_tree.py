"""Component Tree — hierarchical assembly structure per aeroplane."""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, func
from datetime import datetime, timezone

from app.db.base import Base


class ComponentTreeNodeModel(Base):
    """A node in the component tree.

    Three node types:
    - "group": structural grouping (e.g. "main_wing", "electronics")
    - "cad_shape": reference to a CadQuery shape from the Creator pipeline
    - "cots": reference to a COTS component in the components catalog
    """
    __tablename__ = "component_tree"

    aeroplane_id = Column(String, nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("component_tree.id"), nullable=True)
    sort_index = Column(Integer, default=0)

    # Node identity
    node_type = Column(String, nullable=False)  # "group", "cad_shape", "cots"
    name = Column(String, nullable=False)

    # For node_type = "cad_shape"
    shape_key = Column(String, nullable=True)
    shape_hash = Column(String, nullable=True)
    volume_mm3 = Column(Float, nullable=True)
    area_mm2 = Column(Float, nullable=True)

    # For node_type = "cots"
    component_id = Column(Integer, ForeignKey("components.id"), nullable=True)
    quantity = Column(Integer, default=1)

    # For node_type = "cad_shape" with a manually uploaded source — references a
    # row in `construction_parts` (gh#57-g4h). When set, the service snapshots
    # volume_mm3 / area_mm2 / material_id from the referenced part on create.
    # Mutually compatible with `shape_key` (Creator-pipeline source); both fields
    # may exist on different nodes, but typically only one of them is set per node.
    construction_part_id = Column(
        Integer,
        ForeignKey("construction_parts.id"),
        nullable=True,
    )

    # Position / Orientation (6-DOF)
    pos_x = Column(Float, default=0)
    pos_y = Column(Float, default=0)
    pos_z = Column(Float, default=0)
    rot_x = Column(Float, default=0)
    rot_y = Column(Float, default=0)
    rot_z = Column(Float, default=0)

    # Weight
    material_id = Column(Integer, ForeignKey("components.id"), nullable=True)
    weight_override_g = Column(Float, nullable=True)
    print_type = Column(String, nullable=True)  # "volume" or "surface"
    scale_factor = Column(Float, default=1.0)

    # Sync protection
    synced_from = Column(String, nullable=True)  # e.g. "wing:main_wing" or "segment:main_wing:0"

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
