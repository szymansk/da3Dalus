from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import TypeDecorator, CHAR
from datetime import datetime, timezone
from sqlalchemy import DateTime, func
from typing import Any, Optional

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
        if dialect.name == "postgresql":
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == "postgresql":
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


# --- Shared SQLAlchemy relationship / FK constants (S1192) ---
_CASCADE_ALL_DELETE_ORPHAN = "all, delete-orphan"
_FK_AEROPLANES_ID = "aeroplanes.id"


class ProjectedControlSurface:
    """ASB-compatible control-surface view projected from a TED."""

    def __init__(
        self,
        name: str,
        hinge_point: float,
        symmetric: bool,
        deflection: float,
    ) -> None:
        self.name = name
        self.hinge_point = hinge_point
        self.symmetric = symmetric
        self.deflection = deflection


class WingXSecDetailModel(Base):
    __tablename__ = "wing_xsec_details"
    wing_xsec_id = Column(
        Integer, ForeignKey("wing_xsecs.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    x_sec_type = Column(String, nullable=True)
    tip_type = Column(String, nullable=True)
    number_interpolation_points = Column(Integer, nullable=True)

    wing_xsec = relationship("WingXSecModel", back_populates="detail")
    spares = relationship(
        "WingXSecSpareModel",
        back_populates="detail",
        cascade=_CASCADE_ALL_DELETE_ORPHAN,
        order_by="WingXSecSpareModel.sort_index",
    )
    trailing_edge_device = relationship(
        "WingXSecTrailingEdgeDeviceModel",
        back_populates="detail",
        uselist=False,
        cascade=_CASCADE_ALL_DELETE_ORPHAN,
    )


class WingXSecSpareModel(Base):
    __tablename__ = "wing_xsec_spares"
    wing_xsec_detail_id = Column(
        Integer, ForeignKey("wing_xsec_details.id", ondelete="CASCADE"), nullable=False
    )
    sort_index = Column(Integer, default=0, nullable=False)
    spare_support_dimension_width = Column(Float, nullable=False)
    spare_support_dimension_height = Column(Float, nullable=False)
    spare_position_factor = Column(Float, nullable=True)
    spare_length = Column(Float, nullable=True)
    spare_start = Column(Float, nullable=True)
    spare_mode = Column(String, nullable=True)
    spare_vector = Column(JSON, nullable=True)
    spare_origin = Column(JSON, nullable=True)

    detail = relationship("WingXSecDetailModel", back_populates="spares")


class WingXSecTrailingEdgeDeviceModel(Base):
    __tablename__ = "wing_xsec_trailing_edge_devices"
    wing_xsec_detail_id = Column(
        Integer, ForeignKey("wing_xsec_details.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    name = Column(String, nullable=True)
    role = Column(String, nullable=False, default="other", server_default="other")
    label = Column(String, nullable=True)
    rel_chord_root = Column(Float, nullable=True)
    rel_chord_tip = Column(Float, nullable=True)
    hinge_spacing = Column(Float, nullable=True)
    side_spacing_root = Column(Float, nullable=True)
    side_spacing_tip = Column(Float, nullable=True)
    servo_placement = Column(String, nullable=True)
    rel_chord_servo_position = Column(Float, nullable=True)
    rel_length_servo_position = Column(Float, nullable=True)
    positive_deflection_deg = Column(Float, nullable=True)
    negative_deflection_deg = Column(Float, nullable=True)
    deflection_deg = Column(Float, nullable=True)
    trailing_edge_offset_factor = Column(Float, nullable=True)
    hinge_type = Column(String, nullable=True)
    symmetric = Column(Boolean, nullable=True)
    servo_index = Column(Integer, nullable=True)

    detail = relationship("WingXSecDetailModel", back_populates="trailing_edge_device")
    servo_data = relationship(
        "WingXSecTedServoModel",
        back_populates="ted",
        uselist=False,
        cascade=_CASCADE_ALL_DELETE_ORPHAN,
    )

    @property
    def servo(self):
        if self.servo_data is not None:
            return self.servo_data
        return self.servo_index


class WingXSecTedServoModel(Base):
    __tablename__ = "wing_xsec_ted_servos"
    ted_id = Column(
        Integer,
        ForeignKey("wing_xsec_trailing_edge_devices.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    component_id = Column(Integer, ForeignKey("components.id"), nullable=True)
    length = Column(Float, nullable=True)
    width = Column(Float, nullable=True)
    height = Column(Float, nullable=True)
    leading_length = Column(Float, nullable=True)
    latch_z = Column(Float, nullable=True)
    latch_x = Column(Float, nullable=True)
    latch_thickness = Column(Float, nullable=True)
    latch_length = Column(Float, nullable=True)
    cable_z = Column(Float, nullable=True)
    screw_hole_lx = Column(Float, nullable=True)
    screw_hole_d = Column(Float, nullable=True)

    ted = relationship("WingXSecTrailingEdgeDeviceModel", back_populates="servo_data")


class WingXSecModel(Base):
    __tablename__ = "wing_xsecs"
    xyz_le = Column(JSON, nullable=False)  # Store as JSON array
    chord = Column(Float, nullable=False)
    twist = Column(Float, nullable=False)
    airfoil = Column(String, nullable=False)  # Store path or URL as string

    # Relationship with Wing
    wing_id = Column(Integer, ForeignKey("wings.id", ondelete="CASCADE"))
    wing = relationship("WingModel", back_populates="x_secs")

    detail = relationship(
        "WingXSecDetailModel",
        back_populates="wing_xsec",
        uselist=False,
        cascade=_CASCADE_ALL_DELETE_ORPHAN,
    )
    # index to maintain ordering of cross-sections within a wing
    sort_index = Column(Integer, default=0, nullable=False)

    @property
    def x_sec_type(self):
        return self.detail.x_sec_type if self.detail else None

    @property
    def tip_type(self):
        return self.detail.tip_type if self.detail else None

    @property
    def number_interpolation_points(self):
        return self.detail.number_interpolation_points if self.detail else None

    @property
    def spare_list(self):
        return self.detail.spares if self.detail else None

    @property
    def trailing_edge_device(self):
        return self.detail.trailing_edge_device if self.detail else None

    @property
    def control_surface(self):
        ted = self.trailing_edge_device
        if ted is None:
            return None
        projected = WingModel._control_surface_from_ted(ted)
        return ProjectedControlSurface(
            name=projected["name"],
            hinge_point=projected["hinge_point"],
            symmetric=projected["symmetric"],
            deflection=projected["deflection"],
        )


class WingModel(Base):
    __tablename__ = "wings"
    name = Column(String, nullable=False)
    symmetric = Column(Boolean, default=True)
    design_model = Column(String, nullable=True, default=None)

    # One-to-many to WingXSec, ordered by sort_index
    x_secs = relationship(
        "WingXSecModel",
        back_populates="wing",
        cascade=_CASCADE_ALL_DELETE_ORPHAN,
        order_by="WingXSecModel.sort_index",
    )

    # ForeignKey to Aeroplane
    aeroplane_id = Column(Integer, ForeignKey(_FK_AEROPLANES_ID, ondelete="CASCADE"))
    aeroplane = relationship("AeroplaneModel", back_populates="wings")

    @property
    def units(self):
        return {
            "geometry_length": "m",
            "detail_length": "m",
            "angle": "deg",
        }

    @staticmethod
    def _as_payload(value: Any):
        if value is None:
            return None
        if hasattr(value, "model_dump"):
            return value.model_dump()
        if isinstance(value, dict):
            return value
        if hasattr(value, "__dict__"):
            return {k: v for k, v in value.__dict__.items() if not k.startswith("_")}
        return value

    @classmethod
    def _minimal_ted_from_control_surface(cls, control_surface: Any) -> dict:
        cs = cls._as_payload(control_surface) or {}
        hinge_point = cs.get("hinge_point")
        return {
            "name": cs.get("name"),
            "rel_chord_root": hinge_point,
            "rel_chord_tip": hinge_point,
            "symmetric": cs.get("symmetric"),
            "deflection_deg": float(cs.get("deflection", 0.0) or 0.0),
        }

    @classmethod
    def _merge_ted_with_control_surface(
        cls,
        trailing_edge_device: Any = None,
        control_surface: Any = None,
    ) -> Optional[dict]:
        ted = cls._as_payload(trailing_edge_device)
        cs = cls._as_payload(control_surface)

        if ted is None and cs is None:
            return None
        if ted is None:
            return cls._minimal_ted_from_control_surface(cs)
        if cs is None:
            return ted

        ted = ted.copy()
        ted.setdefault("name", cs.get("name"))
        if ted.get("rel_chord_root") is None:
            ted["rel_chord_root"] = cs.get("hinge_point")
        if ted.get("rel_chord_tip") is None and cs.get("hinge_point") is not None:
            ted["rel_chord_tip"] = cs.get("hinge_point")
        if ted.get("symmetric") is None:
            ted["symmetric"] = cs.get("symmetric")
        if ted.get("deflection_deg") is None:
            ted["deflection_deg"] = float(cs.get("deflection", 0.0) or 0.0)
        return ted

    @classmethod
    def _control_surface_from_ted(cls, trailing_edge_device: Any, fallback: Any = None) -> dict:
        ted = cls._as_payload(trailing_edge_device) or {}
        fallback_cs = cls._as_payload(fallback) or {}
        return {
            "name": ted.get("name") or fallback_cs.get("name") or "Control Surface",
            "hinge_point": ted.get("rel_chord_root")
            if ted.get("rel_chord_root") is not None
            else fallback_cs.get("hinge_point", 0.8),
            "symmetric": ted.get("symmetric")
            if ted.get("symmetric") is not None
            else fallback_cs.get("symmetric", True),
            "deflection": ted.get("deflection_deg")
            if ted.get("deflection_deg") is not None
            else fallback_cs.get("deflection", 0.0),
        }

    @classmethod
    def _build_ted_model(cls, trailing_edge_device: Any):
        ted_payload = cls._as_payload(trailing_edge_device)
        if not ted_payload:
            return None

        ted_payload = ted_payload.copy()
        ted_payload.pop("id", None)
        ted_payload.pop("wing_xsec_detail_id", None)
        ted_payload.pop("detail", None)
        ted_payload.pop("servo_data", None)
        servo_payload = cls._as_payload(ted_payload.pop("servo", None))
        ted = WingXSecTrailingEdgeDeviceModel(**ted_payload)

        if isinstance(servo_payload, int):
            ted.servo_index = servo_payload
        elif isinstance(servo_payload, dict):
            servo_payload = servo_payload.copy()
            servo_payload.pop("id", None)
            servo_payload.pop("ted_id", None)
            servo_payload.pop("ted", None)
            ted.servo_data = WingXSecTedServoModel(**servo_payload)

        return ted

    @classmethod
    def _extract_xsec_segment_fields(cls, xsec_payload: dict):
        """Pop segment-specific fields from xsec_payload; return them as a tuple."""
        control_surface = cls._as_payload(xsec_payload.pop("control_surface", None))
        trailing_edge_device = cls._merge_ted_with_control_surface(
            trailing_edge_device=xsec_payload.pop("trailing_edge_device", None),
            control_surface=control_surface,
        )
        return (
            trailing_edge_device,
            xsec_payload.pop("spare_list", None),
            xsec_payload.pop("x_sec_type", None),
            xsec_payload.pop("tip_type", None),
            xsec_payload.pop("number_interpolation_points", None),
        )

    @classmethod
    def _build_xsec_detail(
        cls, x_sec_type, tip_type, number_interpolation_points, trailing_edge_device, spare_list
    ):
        """Build a WingXSecDetailModel if any segment field is non-None, else return None."""
        has_detail = any(
            v is not None
            for v in [
                x_sec_type,
                tip_type,
                number_interpolation_points,
                trailing_edge_device,
                spare_list,
            ]
        )
        if not has_detail:
            return None

        detail = WingXSecDetailModel(
            x_sec_type=x_sec_type,
            tip_type=tip_type,
            number_interpolation_points=number_interpolation_points,
        )
        for spare_index, spare in enumerate(spare_list or []):
            spare_payload = cls._as_payload(spare)
            if spare_payload is not None:
                detail.spares.append(WingXSecSpareModel(sort_index=spare_index, **spare_payload))

        ted_model = cls._build_ted_model(trailing_edge_device)
        if ted_model is not None:
            detail.trailing_edge_device = ted_model

        return detail

    @classmethod
    def from_dict(cls, name, data):
        payload = data.copy()
        xsec_dicts = payload.pop("x_secs", [])
        payload.pop("name", None)
        payload.pop("units", None)
        wing = cls(name=name, **payload)

        for index, raw_xsec in enumerate(xsec_dicts):
            xsec_payload = (cls._as_payload(raw_xsec) or {}).copy()
            is_terminal = index == len(xsec_dicts) - 1

            ted, spare_list, x_sec_type, tip_type, n_interp = cls._extract_xsec_segment_fields(
                xsec_payload
            )
            if is_terminal:
                ted = spare_list = x_sec_type = tip_type = n_interp = None

            if "airfoil" in xsec_payload:
                from app.converters.model_schema_converters import (
                    _normalize_airfoil_reference_for_schema,
                )

                xsec_payload["airfoil"] = _normalize_airfoil_reference_for_schema(
                    xsec_payload["airfoil"]
                )

            if "sort_index" not in xsec_payload:
                xsec_payload["sort_index"] = index
            xsec = WingXSecModel(**xsec_payload)
            xsec.detail = cls._build_xsec_detail(x_sec_type, tip_type, n_interp, ted, spare_list)

            wing.x_secs.append(xsec)
        return wing


class FuselageXSecSuperEllipseModel(Base):
    __tablename__ = "fuselage_xsecs"
    xyz = Column(JSON, nullable=False)  # Store as JSON array
    a = Column(Float, nullable=False)
    b = Column(Float, nullable=False)
    n = Column(Float, nullable=False)
    # index to maintain ordering of cross-sections within a fuselage
    sort_index = Column(Integer, default=0, nullable=False)

    # Relationship with Fuselage
    fuselage_id = Column(Integer, ForeignKey("fuselages.id", ondelete="CASCADE"))
    fuselage = relationship("FuselageModel", back_populates="x_secs")


class FuselageModel(Base):
    __tablename__ = "fuselages"
    name = Column(String, nullable=False)

    # Relationship with FuselageXSecSuperEllipse
    x_secs = relationship(
        "FuselageXSecSuperEllipseModel",
        back_populates="fuselage",
        cascade=_CASCADE_ALL_DELETE_ORPHAN,
        order_by="FuselageXSecSuperEllipseModel.sort_index",
    )

    # ForeignKey to Aeroplane
    aeroplane_id = Column(Integer, ForeignKey(_FK_AEROPLANES_ID, ondelete="CASCADE"))
    aeroplane = relationship("AeroplaneModel", back_populates="fuselages")

    @classmethod
    def from_dict(cls, name, data):
        xsec_dicts = data.pop("x_secs", [])
        data.pop("name", None)
        fuselage = cls(name=name, **data)
        for i, xd in enumerate(xsec_dicts):
            fuselage.x_secs.append(FuselageXSecSuperEllipseModel(sort_index=i, **xd))
        return fuselage


class LoadingScenarioModel(Base):
    """Loading scenario — a named CG loadout for CG envelope computation (gh-488).

    Each scenario describes a combination of component overrides and adhoc items
    (pilot, payload, ballast, etc.) that determines a CG position.  The min/max
    across all scenarios for an aeroplane defines the Loading-Envelope.
    """

    __tablename__ = "loading_scenarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    aeroplane_id = Column(
        Integer,
        ForeignKey(_FK_AEROPLANES_ID, ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String, nullable=False)
    aircraft_class = Column(String, nullable=False, default="rc_trainer", server_default="rc_trainer")
    component_overrides = Column(JSON, nullable=False, default=dict, server_default="{}")
    is_default = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    aeroplane = relationship("AeroplaneModel", back_populates="loading_scenarios")


class AeroplaneModel(Base):
    __tablename__ = "aeroplanes"
    uuid = Column(GUID, default=lambda: uuid.uuid4(), unique=True, nullable=False)
    name = Column(String, nullable=False)
    total_mass_kg = Column(Float, nullable=True)
    # Optional assigned flight-intent profile used for target operating-point generation.
    flight_profile_id = Column(
        Integer, ForeignKey("rc_flight_profiles.id"), nullable=True, index=True
    )
    xyz_ref = Column(JSON, default=[0, 0, 0])  # Store as JSON array
    assumption_computation_context = Column(JSON, nullable=True)
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

    # Relationships
    wings = relationship(
        "WingModel", back_populates="aeroplane", cascade=_CASCADE_ALL_DELETE_ORPHAN
    )
    fuselages = relationship(
        "FuselageModel", back_populates="aeroplane", cascade=_CASCADE_ALL_DELETE_ORPHAN
    )
    flight_profile = relationship("RCFlightProfileModel", back_populates="aircraft")
    mission_objective = relationship(
        "MissionObjectiveModel",
        back_populates="aeroplane",
        uselist=False,
        cascade="all, delete-orphan",
    )
    weight_items = relationship(
        "WeightItemModel",
        back_populates="aeroplane",
        cascade=_CASCADE_ALL_DELETE_ORPHAN,
        order_by="WeightItemModel.id",
    )
    copilot_messages = relationship(
        "CopilotMessageModel",
        back_populates="aeroplane",
        cascade=_CASCADE_ALL_DELETE_ORPHAN,
        order_by="CopilotMessageModel.sort_index",
    )
    design_versions = relationship(
        "DesignVersionModel",
        back_populates="aeroplane",
        cascade=_CASCADE_ALL_DELETE_ORPHAN,
        order_by="DesignVersionModel.id.desc()",
    )
    design_assumptions = relationship(
        "DesignAssumptionModel",
        back_populates="aeroplane",
        cascade=_CASCADE_ALL_DELETE_ORPHAN,
    )
    computation_config = relationship(
        "AircraftComputationConfigModel",
        back_populates="aeroplane",
        uselist=False,
        cascade=_CASCADE_ALL_DELETE_ORPHAN,
    )
    stability_results = relationship(
        "StabilityResultModel",
        back_populates="aeroplane",
        cascade=_CASCADE_ALL_DELETE_ORPHAN,
    )
    loading_scenarios = relationship(
        "LoadingScenarioModel",
        back_populates="aeroplane",
        cascade=_CASCADE_ALL_DELETE_ORPHAN,
        order_by="LoadingScenarioModel.id",
    )


class WeightItemModel(Base):
    __tablename__ = "weight_items"

    aeroplane_id = Column(
        Integer,
        ForeignKey(_FK_AEROPLANES_ID, ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String, nullable=False)
    mass_kg = Column(Float, nullable=False)
    x_m = Column(Float, nullable=False, default=0.0)
    y_m = Column(Float, nullable=False, default=0.0)
    z_m = Column(Float, nullable=False, default=0.0)
    description = Column(String, nullable=True)
    category = Column(String, nullable=False, default="other")

    aeroplane = relationship("AeroplaneModel", back_populates="weight_items")


class CopilotMessageModel(Base):
    __tablename__ = "copilot_messages"

    aeroplane_id = Column(
        Integer,
        ForeignKey(_FK_AEROPLANES_ID, ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sort_index = Column(Integer, nullable=False, default=0)
    role = Column(String, nullable=False)  # user | assistant | tool
    content = Column(String, nullable=False, default="")
    tool_calls = Column(JSON, nullable=True)
    tool_results = Column(JSON, nullable=True)
    parent_id = Column(Integer, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    aeroplane = relationship("AeroplaneModel", back_populates="copilot_messages")


class DesignVersionModel(Base):
    __tablename__ = "design_versions"

    aeroplane_id = Column(
        Integer,
        ForeignKey(_FK_AEROPLANES_ID, ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label = Column(String, nullable=False)
    description = Column(String, nullable=True)
    parent_version_id = Column(Integer, nullable=True)
    snapshot = Column(JSON, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    aeroplane = relationship("AeroplaneModel", back_populates="design_versions")


class DesignAssumptionModel(Base):
    __tablename__ = "design_assumptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    aeroplane_id = Column(
        Integer,
        ForeignKey(_FK_AEROPLANES_ID, ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parameter_name = Column(String, nullable=False)
    estimate_value = Column(Float, nullable=False)
    calculated_value = Column(Float, nullable=True)
    calculated_source = Column(String, nullable=True)
    active_source = Column(String, nullable=False, default="ESTIMATE")
    divergence_pct = Column(Float, nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    aeroplane = relationship("AeroplaneModel", back_populates="design_assumptions")

    __table_args__ = (
        UniqueConstraint("aeroplane_id", "parameter_name", name="uq_assumption_aeroplane_param"),
    )
