"""Extended tests for app/services/wing_service.py — targets uncovered lines.

Complements the existing endpoint-level tests by exercising service functions
directly against an in-memory SQLite DB (via the ``client_and_db`` fixture).
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from app.core.exceptions import NotFoundError, ValidationError, InternalError
from app.models.aeroplanemodel import (
    AeroplaneModel,
    WingModel,
    WingXSecModel,
    WingXSecDetailModel,
    WingXSecSpareModel,
    WingXSecTrailingEdgeDeviceModel,
    WingXSecTedServoModel,
)
from app.services import wing_service
from app.tests.conftest import make_aeroplane, make_wing
from app import schemas
from app.schemas.Servo import Servo as ServoSchema

airfoil_path = str(
    (Path(__file__).resolve().parents[2] / "components" / "airfoils" / "mh32.dat").resolve()
)


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture()
def db(client_and_db):
    """Provide a raw SQLAlchemy session from the client_and_db fixture."""
    _, SessionLocal = client_and_db
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(client_and_db):
    c, _ = client_and_db
    yield c


def _make_plane_with_wing(db, *, wing_name: str = "main", xsec_count: int = 2, ):
    """Create an aeroplane with a wing that has xsec_count cross-sections.

    Returns (aeroplane, wing) ORM instances.
    The first N-1 xsecs get a detail row; the last (terminal) does not.
    """
    plane = make_aeroplane(db, name=f"test-{uuid.uuid4().hex[:8]}")
    wing = WingModel(name=wing_name, symmetric=True, aeroplane_id=plane.id)
    for i in range(xsec_count):
        xsec = WingXSecModel(
            sort_index=i,
            xyz_le=[0.0, float(i) * 0.5, 0.0],
            chord=0.15 - i * 0.02,
            twist=0.0,
            airfoil="naca0012",
        )
        if i < xsec_count - 1:
            xsec.detail = WingXSecDetailModel()
        wing.x_secs.append(xsec)
    db.add(wing)
    db.commit()
    db.refresh(plane)
    return plane, wing



# ── get_aeroplane_or_raise ────────────────────────────────────────────


class TestGetAeroplaneOrRaise:
    def test_returns_aeroplane_when_exists(self, db):
        plane = make_aeroplane(db)
        result = wing_service.get_aeroplane_or_raise(db, plane.uuid)
        assert result.id == plane.id

    def test_raises_not_found_for_unknown_uuid(self, db):
        with pytest.raises(NotFoundError, match="Aeroplane not found"):
            wing_service.get_aeroplane_or_raise(db, uuid.uuid4())


# ── get_wing_or_raise ─────────────────────────────────────────────────


class TestGetWingOrRaise:
    def test_returns_wing_when_exists(self, db):
        plane, wing = _make_plane_with_wing(db)
        result = wing_service.get_wing_or_raise(plane, "main")
        assert result.name == "main"

    def test_raises_not_found_for_missing_wing(self, db):
        plane = make_aeroplane(db)
        with pytest.raises(NotFoundError, match="Wing not found"):
            wing_service.get_wing_or_raise(plane, "nonexistent")


# ── _get_xsec_or_raise ───────────────────────────────────────────────


class TestGetXsecOrRaise:
    def test_returns_xsec_for_valid_index(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=3)
        result = wing_service._get_xsec_or_raise(wing, 1)
        assert result.sort_index == 1

    def test_raises_for_negative_index(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        with pytest.raises(NotFoundError, match="Cross-section not found"):
            wing_service._get_xsec_or_raise(wing, -1)

    def test_raises_for_out_of_bounds_index(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        with pytest.raises(NotFoundError, match="Cross-section not found"):
            wing_service._get_xsec_or_raise(wing, 5)


# ── _assert_non_terminal_xsec_or_raise ───────────────────────────────


class TestAssertNonTerminalXsec:
    def test_passes_for_non_terminal(self):
        wing_service._assert_non_terminal_xsec_or_raise(0, 3)

    def test_raises_for_terminal(self):
        with pytest.raises(ValidationError, match="terminal cross-section"):
            wing_service._assert_non_terminal_xsec_or_raise(2, 3)


# ── list_wing_names ───────────────────────────────────────────────────


class TestListWingNames:
    def test_returns_empty_list_when_no_wings(self, db):
        plane = make_aeroplane(db)
        result = wing_service.list_wing_names(db, plane.uuid)
        assert result == []

    def test_returns_wing_names(self, db):
        plane, _ = _make_plane_with_wing(db, wing_name="alpha")
        wing2 = WingModel(name="beta", symmetric=False, aeroplane_id=plane.id)
        db.add(wing2)
        db.commit()
        result = wing_service.list_wing_names(db, plane.uuid)
        assert sorted(result) == ["alpha", "beta"]

    def test_raises_for_unknown_aeroplane(self, db):
        with pytest.raises(NotFoundError):
            wing_service.list_wing_names(db, uuid.uuid4())


# ── create_wing ───────────────────────────────────────────────────────


class TestCreateWing:
    def test_creates_wing_successfully(self, db):
        plane = make_aeroplane(db)
        write_schema = schemas.AsbWingGeometryWriteSchema.model_construct(
            name="new_wing",
            x_secs=[],
        )
        wing_service.create_wing(db, plane.uuid, "new_wing", write_schema)
        db.refresh(plane)
        assert any(w.name == "new_wing" for w in plane.wings)
        created = next(w for w in plane.wings if w.name == "new_wing")
        assert created.design_model == "asb"

    def test_rejects_duplicate_wing_name(self, db):
        plane, _ = _make_plane_with_wing(db, wing_name="dup")
        write_schema = schemas.AsbWingGeometryWriteSchema.model_construct(
            name="dup",
            x_secs=[],
        )
        with pytest.raises(ValidationError, match="unique"):
            wing_service.create_wing(db, plane.uuid, "dup", write_schema)

    def test_raises_not_found_for_bad_plane(self, db):
        write_schema = schemas.AsbWingGeometryWriteSchema.model_construct(
            name="w", x_secs=[]
        )
        with pytest.raises(NotFoundError):
            wing_service.create_wing(db, uuid.uuid4(), "w", write_schema)


# ── update_wing ───────────────────────────────────────────────────────


class TestUpdateWing:
    def test_replaces_wing_data(self, db):
        plane, wing = _make_plane_with_wing(db, wing_name="upd")
        write_schema = schemas.AsbWingGeometryWriteSchema.model_construct(
            name="upd",
            x_secs=[],
        )
        wing_service.update_wing(db, plane.uuid, "upd", write_schema)
        db.refresh(plane)
        updated = next(w for w in plane.wings if w.name == "upd")
        assert updated.design_model == "asb"

    def test_raises_not_found_for_missing_wing(self, db):
        plane = make_aeroplane(db)
        write_schema = schemas.AsbWingGeometryWriteSchema.model_construct(
            name="nope", x_secs=[]
        )
        with pytest.raises(NotFoundError):
            wing_service.update_wing(db, plane.uuid, "nope", write_schema)


# ── get_wing ──────────────────────────────────────────────────────────


class TestGetWing:
    def test_returns_wing_schema(self, db):
        plane, wing = _make_plane_with_wing(db, wing_name="gw")
        result = wing_service.get_wing(db, plane.uuid, "gw")
        assert isinstance(result, schemas.AsbWingReadSchema)
        assert result.name == "gw"

    def test_raises_for_missing_wing(self, db):
        plane = make_aeroplane(db)
        with pytest.raises(NotFoundError):
            wing_service.get_wing(db, plane.uuid, "nope")


# ── delete_wing ───────────────────────────────────────────────────────


class TestDeleteWing:
    def test_deletes_existing_wing(self, db):
        plane, _ = _make_plane_with_wing(db, wing_name="del")
        wing_service.delete_wing(db, plane.uuid, "del")
        db.refresh(plane)
        assert not any(w.name == "del" for w in plane.wings)

    def test_raises_for_missing_wing(self, db):
        plane = make_aeroplane(db)
        with pytest.raises(NotFoundError):
            wing_service.delete_wing(db, plane.uuid, "nope")


# ── get_wing_design_model ────────────────────────────────────────────


class TestGetWingDesignModel:
    def test_returns_none_for_missing_wing(self, db):
        plane = make_aeroplane(db)
        result = wing_service.get_wing_design_model(db, plane.uuid, "nonexistent")
        assert result is None

    def test_returns_design_model_for_existing_wing(self, db):
        plane, wing = _make_plane_with_wing(db, wing_name="dm")
        wing.design_model = "wc"
        db.commit()
        result = wing_service.get_wing_design_model(db, plane.uuid, "dm")
        assert result == "wc"

    def test_raises_not_found_for_bad_aeroplane(self, db):
        with pytest.raises(NotFoundError, match="Aeroplane not found"):
            wing_service.get_wing_design_model(db, uuid.uuid4(), "any")


# ── Cross-section operations ─────────────────────────────────────────


class TestGetWingCrossSections:
    def test_returns_all_cross_sections(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=3)
        result = wing_service.get_wing_cross_sections(db, plane.uuid, "main")
        assert len(result) == 3

    def test_raises_for_missing_wing(self, db):
        plane = make_aeroplane(db)
        with pytest.raises(NotFoundError):
            wing_service.get_wing_cross_sections(db, plane.uuid, "nope")


class TestDeleteAllCrossSections:
    def test_deletes_all_cross_sections(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=3)
        wing_service.delete_all_cross_sections(db, plane.uuid, "main")
        db.refresh(wing)
        assert len(wing.x_secs) == 0


class TestGetCrossSection:
    def test_returns_single_cross_section(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        result = wing_service.get_cross_section(db, plane.uuid, "main", 0)
        assert isinstance(result, schemas.WingXSecReadSchema)

    def test_raises_for_out_of_bounds(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        with pytest.raises(NotFoundError):
            wing_service.get_cross_section(db, plane.uuid, "main", 10)


class TestCreateCrossSection:
    def test_appends_at_end(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        xsec_data = schemas.WingXSecGeometryWriteSchema.model_construct(
            xyz_le=[0.0, 1.5, 0.0],
            chord=0.08,
            twist=0.0,
            airfoil="naca0012",
        )
        wing_service.create_cross_section(db, plane.uuid, "main", -1, xsec_data)
        db.refresh(wing)
        assert len(wing.x_secs) == 3

    def test_inserts_at_index(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        xsec_data = schemas.WingXSecGeometryWriteSchema.model_construct(
            xyz_le=[0.0, 0.25, 0.0],
            chord=0.12,
            twist=0.0,
            airfoil="naca0012",
        )
        wing_service.create_cross_section(db, plane.uuid, "main", 1, xsec_data)
        db.refresh(wing)
        assert len(wing.x_secs) == 3

    def test_with_segment_metadata(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        xsec_data = schemas.WingXSecGeometryWriteSchema.model_construct(
            xyz_le=[0.0, 0.25, 0.0],
            chord=0.12,
            twist=0.0,
            airfoil="naca0012",
            x_sec_type="segment",
            tip_type="round",
            number_interpolation_points=50,
        )
        wing_service.create_cross_section(db, plane.uuid, "main", 0, xsec_data)
        db.refresh(wing)
        assert len(wing.x_secs) == 3
        inserted = wing.x_secs[0]
        assert inserted.detail is not None
        assert inserted.detail.tip_type == "round"


class TestUpdateCrossSection:
    def test_updates_geometry_fields(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        xsec_data = schemas.WingXSecGeometryWriteSchema.model_construct(
            xyz_le=[0.1, 0.0, 0.0],
            chord=0.20,
            twist=2.5,
            airfoil="naca2412",
        )
        wing_service.update_cross_section(db, plane.uuid, "main", 0, xsec_data)
        db.refresh(wing)
        xsec = wing.x_secs[0]
        assert xsec.chord == 0.20
        assert xsec.airfoil == "naca2412"

    def test_updates_segment_metadata_on_non_terminal(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=3)
        xsec_data = schemas.WingXSecGeometryWriteSchema.model_construct(
            xyz_le=[0.0, 0.0, 0.0],
            chord=0.15,
            twist=0.0,
            airfoil="naca0012",
            x_sec_type="root",
            tip_type="flat",
            number_interpolation_points=80,
        )
        wing_service.update_cross_section(db, plane.uuid, "main", 0, xsec_data)
        db.refresh(wing)
        assert wing.x_secs[0].detail.tip_type == "flat"
        assert wing.x_secs[0].detail.number_interpolation_points == 80

    def test_rejects_metadata_on_terminal(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        xsec_data = schemas.WingXSecGeometryWriteSchema.model_construct(
            xyz_le=[0.0, 0.5, 0.0],
            chord=0.10,
            twist=0.0,
            airfoil="naca0012",
            tip_type="round",
        )
        with pytest.raises(ValidationError, match="last cross-section"):
            wing_service.update_cross_section(db, plane.uuid, "main", 1, xsec_data)

    def test_raises_for_out_of_bounds(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        xsec_data = schemas.WingXSecGeometryWriteSchema.model_construct(
            xyz_le=[0, 0, 0], chord=0.1, twist=0, airfoil="naca0012"
        )
        with pytest.raises(NotFoundError):
            wing_service.update_cross_section(db, plane.uuid, "main", 99, xsec_data)


class TestDeleteCrossSection:
    def test_deletes_by_index(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=3)
        wing_service.delete_cross_section(db, plane.uuid, "main", 1)
        db.refresh(wing)
        assert len(wing.x_secs) == 2

    def test_raises_for_out_of_bounds(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        with pytest.raises(NotFoundError):
            wing_service.delete_cross_section(db, plane.uuid, "main", 10)


# ── Spar operations ──────────────────────────────────────────────────


class TestSparService:
    def _add_spar(self, db, wing, xsec_index=0, position_factor=0.25):
        """Add a spar to a wing's cross-section detail."""
        xsec = wing.x_secs[xsec_index]
        if xsec.detail is None:
            xsec.detail = WingXSecDetailModel()
        spar = WingXSecSpareModel(
            sort_index=len(xsec.detail.spares),
            spare_support_dimension_width=5.0,
            spare_support_dimension_height=5.0,
            spare_position_factor=position_factor,
            spare_start=0.0,
            spare_mode="standard",
        )
        xsec.detail.spares.append(spar)
        db.add(spar)
        db.commit()
        return spar

    def test_get_spares_returns_empty_when_none(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        result = wing_service.get_spares(db, plane.uuid, "main", 0)
        assert result == []

    def test_get_spares_returns_existing(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        self._add_spar(db, wing, 0, position_factor=0.3)
        result = wing_service.get_spares(db, plane.uuid, "main", 0)
        assert len(result) == 1
        assert result[0].spare_position_factor == pytest.approx(0.3)

    def test_create_spare_on_non_terminal(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=3)
        spare_data = schemas.SpareDetailSchema.model_construct(
            spare_support_dimension_width=4.0,
            spare_support_dimension_height=4.0,
            spare_position_factor=0.5,
            spare_start=0.0,
            spare_mode="standard",
        )
        wing_service.create_spare(db, plane.uuid, "main", 0, spare_data)
        db.refresh(wing)
        assert len(wing.x_secs[0].detail.spares) == 1

    def test_create_spare_on_terminal_raises(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        spare_data = schemas.SpareDetailSchema.model_construct(
            spare_support_dimension_width=4.0,
            spare_support_dimension_height=4.0,
            spare_position_factor=0.5,
            spare_start=0.0,
            spare_mode="standard",
        )
        with pytest.raises(ValidationError, match="terminal"):
            wing_service.create_spare(db, plane.uuid, "main", 1, spare_data)

    def test_update_spare(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        self._add_spar(db, wing, 0, position_factor=0.25)
        updated = schemas.SpareDetailSchema.model_construct(
            spare_support_dimension_width=8.0,
            spare_support_dimension_height=8.0,
            spare_position_factor=0.6,
            spare_start=0.0,
            spare_mode="follow",
        )
        wing_service.update_spare(db, plane.uuid, "main", 0, 0, updated)
        db.refresh(wing)
        spar = wing.x_secs[0].detail.spares[0]
        assert spar.spare_position_factor == pytest.approx(0.6)
        assert spar.spare_mode == "follow"

    def test_update_spare_invalid_index_raises(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        self._add_spar(db, wing, 0)
        updated = schemas.SpareDetailSchema.model_construct(
            spare_support_dimension_width=5.0,
            spare_support_dimension_height=5.0,
            spare_position_factor=0.25,
            spare_start=0.0,
            spare_mode="standard",
        )
        with pytest.raises(NotFoundError, match="Spar index"):
            wing_service.update_spare(db, plane.uuid, "main", 0, 99, updated)

    def test_delete_spare(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        self._add_spar(db, wing, 0)
        wing_service.delete_spare(db, plane.uuid, "main", 0, 0)
        db.refresh(wing)
        assert len(wing.x_secs[0].detail.spares) == 0

    def test_delete_spare_invalid_index_raises(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        with pytest.raises(NotFoundError, match="Spar index"):
            wing_service.delete_spare(db, plane.uuid, "main", 0, 99)


# ── Control Surface (via TED) ────────────────────────────────────────


class TestControlSurfaceService:
    def _add_ted(self, db, wing, xsec_index=0, *, name="aileron", hinge=0.8):
        xsec = wing.x_secs[xsec_index]
        if xsec.detail is None:
            xsec.detail = WingXSecDetailModel()
        ted = WingXSecTrailingEdgeDeviceModel(
            name=name,
            rel_chord_root=hinge,
            symmetric=False,
            deflection_deg=3.0,
        )
        xsec.detail.trailing_edge_device = ted
        db.add(ted)
        db.commit()
        return ted

    def test_get_control_surface(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        self._add_ted(db, wing, 0, name="flap")
        result = wing_service.get_control_surface(db, plane.uuid, "main", 0)
        assert isinstance(result, schemas.ControlSurfaceSchema)
        assert result.name == "flap"

    def test_get_control_surface_missing_raises(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        with pytest.raises(NotFoundError, match="Control surface not found"):
            wing_service.get_control_surface(db, plane.uuid, "main", 0)

    def test_get_control_surface_terminal_raises(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        with pytest.raises(ValidationError, match="terminal"):
            wing_service.get_control_surface(db, plane.uuid, "main", 1)

    def test_patch_control_surface_creates_ted(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        patch = schemas.ControlSurfacePatchSchema(
            name="elevator",
            hinge_point=0.7,
        )
        result = wing_service.patch_control_surface(db, plane.uuid, "main", 0, patch)
        assert result.name == "elevator"
        assert result.hinge_point == pytest.approx(0.7)

    def test_patch_control_surface_updates_existing(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        self._add_ted(db, wing, 0, name="ail")
        patch = schemas.ControlSurfacePatchSchema(symmetric=True)
        result = wing_service.patch_control_surface(db, plane.uuid, "main", 0, patch)
        assert result.symmetric is True

    def test_patch_control_surface_deflection(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        self._add_ted(db, wing, 0)
        patch = schemas.ControlSurfacePatchSchema(deflection=5.0)
        result = wing_service.patch_control_surface(db, plane.uuid, "main", 0, patch)
        assert result.deflection == pytest.approx(5.0)

    def test_delete_control_surface(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        self._add_ted(db, wing, 0)
        wing_service.delete_control_surface(db, plane.uuid, "main", 0)
        db.refresh(wing)
        assert wing.x_secs[0].detail.trailing_edge_device is None

    def test_delete_control_surface_missing_raises(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        with pytest.raises(NotFoundError, match="Control surface not found"):
            wing_service.delete_control_surface(db, plane.uuid, "main", 0)


# ── Control Surface CAD Details ───────────────────────────────────────


class TestControlSurfaceCadDetailsService:
    def _add_ted_with_cad(self, db, wing, xsec_index=0):
        xsec = wing.x_secs[xsec_index]
        if xsec.detail is None:
            xsec.detail = WingXSecDetailModel()
        ted = WingXSecTrailingEdgeDeviceModel(
            name="ail",
            rel_chord_root=0.8,
            rel_chord_tip=0.75,
            hinge_spacing=2.0,
            side_spacing_root=1.5,
            side_spacing_tip=1.5,
            servo_placement="top",
        )
        xsec.detail.trailing_edge_device = ted
        db.add(ted)
        db.commit()
        return ted

    def test_get_cad_details(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        self._add_ted_with_cad(db, wing, 0)
        result = wing_service.get_control_surface_cad_details(
            db, plane.uuid, "main", 0
        )
        assert isinstance(result, schemas.ControlSurfaceCadDetailsSchema)
        assert result.rel_chord_tip == pytest.approx(0.75)
        assert result.hinge_spacing == pytest.approx(2.0)

    def test_get_cad_details_no_ted_raises(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        with pytest.raises(ValidationError, match="Control surface must exist"):
            wing_service.get_control_surface_cad_details(
                db, plane.uuid, "main", 0
            )

    def test_patch_cad_details(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        self._add_ted_with_cad(db, wing, 0)
        patch = schemas.ControlSurfaceCadDetailsPatchSchema.model_construct(
            rel_chord_tip=0.82,
            hinge_type="top_simple",
        )
        result = wing_service.patch_control_surface_cad_details(
            db, plane.uuid, "main", 0, patch
        )
        assert result.rel_chord_tip == pytest.approx(0.82)
        assert result.hinge_type == "top_simple"

    def test_delete_cad_details_resets_to_minimal(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        self._add_ted_with_cad(db, wing, 0)
        wing_service.delete_control_surface_cad_details(
            db, plane.uuid, "main", 0
        )
        db.refresh(wing)
        ted = wing.x_secs[0].detail.trailing_edge_device
        # TED still exists but CAD-specific fields are cleared
        assert ted is not None
        assert ted.hinge_spacing is None
        assert ted.hinge_type is None
        assert ted.servo_data is None


# ── Control Surface CAD Servo Details ─────────────────────────────────


class TestControlSurfaceCadServoDetailsService:
    def _add_ted_with_servo(self, db, wing, xsec_index=0):
        xsec = wing.x_secs[xsec_index]
        if xsec.detail is None:
            xsec.detail = WingXSecDetailModel()
        servo = WingXSecTedServoModel(
            length=23, width=12.5, height=31.5,
            leading_length=6, latch_z=14.5, latch_x=7.25,
            latch_thickness=2.6, latch_length=6, cable_z=26,
            screw_hole_lx=0, screw_hole_d=0,
        )
        ted = WingXSecTrailingEdgeDeviceModel(
            name="ail",
            rel_chord_root=0.8,
            servo_data=servo,
        )
        xsec.detail.trailing_edge_device = ted
        db.add(ted)
        db.commit()
        return ted

    def _add_ted_with_servo_index(self, db, wing, xsec_index=0):
        xsec = wing.x_secs[xsec_index]
        if xsec.detail is None:
            xsec.detail = WingXSecDetailModel()
        ted = WingXSecTrailingEdgeDeviceModel(
            name="ail",
            rel_chord_root=0.8,
            servo_index=42,
        )
        xsec.detail.trailing_edge_device = ted
        db.add(ted)
        db.commit()
        return ted

    def test_get_servo_details_with_servo_data(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        self._add_ted_with_servo(db, wing, 0)
        result = wing_service.get_control_surface_cad_details_servo_details(
            db, plane.uuid, "main", 0
        )
        assert isinstance(result, schemas.ControlSurfaceServoDetailsSchema)

    def test_get_servo_details_with_servo_index(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        self._add_ted_with_servo_index(db, wing, 0)
        result = wing_service.get_control_surface_cad_details_servo_details(
            db, plane.uuid, "main", 0
        )
        assert result.servo == 42

    def test_get_servo_details_no_servo_raises(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        xsec = wing.x_secs[0]
        if xsec.detail is None:
            xsec.detail = WingXSecDetailModel()
        ted = WingXSecTrailingEdgeDeviceModel(name="ail", rel_chord_root=0.8)
        xsec.detail.trailing_edge_device = ted
        db.add(ted)
        db.commit()
        with pytest.raises(NotFoundError, match="No servo configured"):
            wing_service.get_control_surface_cad_details_servo_details(
                db, plane.uuid, "main", 0
            )

    def test_patch_servo_details_with_int(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        self._add_ted_with_servo(db, wing, 0)
        patch = schemas.ControlSurfaceServoDetailsPatchSchema(servo=7)
        result = wing_service.patch_control_surface_cad_details_servo_details(
            db, plane.uuid, "main", 0, patch
        )
        assert result.servo == 7

    def test_patch_servo_details_with_servo_obj(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        self._add_ted_with_servo(db, wing, 0)
        servo = ServoSchema(
            length=20, width=10, height=25,
            leading_length=5, latch_z=10, latch_x=5,
            latch_thickness=2, latch_length=5, cable_z=20,
            screw_hole_lx=0, screw_hole_d=0,
        )
        patch = schemas.ControlSurfaceServoDetailsPatchSchema(servo=servo)
        result = wing_service.patch_control_surface_cad_details_servo_details(
            db, plane.uuid, "main", 0, patch
        )
        assert isinstance(result, schemas.ControlSurfaceServoDetailsSchema)

    def test_delete_servo_details(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        self._add_ted_with_servo(db, wing, 0)
        wing_service.delete_control_surface_cad_details_servo_details(
            db, plane.uuid, "main", 0
        )
        db.refresh(wing)
        ted = wing.x_secs[0].detail.trailing_edge_device
        assert ted.servo_data is None
        assert ted.servo_index is None

    def test_delete_servo_details_no_servo_raises(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        xsec = wing.x_secs[0]
        if xsec.detail is None:
            xsec.detail = WingXSecDetailModel()
        ted = WingXSecTrailingEdgeDeviceModel(name="ail", rel_chord_root=0.8)
        xsec.detail.trailing_edge_device = ted
        db.add(ted)
        db.commit()
        with pytest.raises(NotFoundError, match="No servo configured"):
            wing_service.delete_control_surface_cad_details_servo_details(
                db, plane.uuid, "main", 0
            )


# ── Trailing Edge Device (direct TED access) ─────────────────────────


class TestTrailingEdgeDeviceService:
    def _add_ted(self, db, wing, xsec_index=0):
        xsec = wing.x_secs[xsec_index]
        if xsec.detail is None:
            xsec.detail = WingXSecDetailModel()
        ted = WingXSecTrailingEdgeDeviceModel(
            name="flap",
            rel_chord_root=0.75,
            symmetric=True,
        )
        xsec.detail.trailing_edge_device = ted
        db.add(ted)
        db.commit()
        return ted

    def test_get_trailing_edge_device(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        self._add_ted(db, wing, 0)
        result = wing_service.get_trailing_edge_device(db, plane.uuid, "main", 0)
        assert isinstance(result, schemas.TrailingEdgeDeviceDetailSchema)
        assert result.name == "flap"

    def test_get_trailing_edge_device_missing_raises(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        with pytest.raises(NotFoundError, match="Trailing-edge device not found"):
            wing_service.get_trailing_edge_device(db, plane.uuid, "main", 0)

    def test_get_trailing_edge_device_terminal_raises(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        with pytest.raises(ValidationError, match="terminal"):
            wing_service.get_trailing_edge_device(db, plane.uuid, "main", 1)

    def test_patch_trailing_edge_device_creates(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        patch = schemas.TrailingEdgeDevicePatchSchema.model_construct(
            name="rudder",
            rel_chord_root=0.7,
        )
        result = wing_service.patch_trailing_edge_device(db, plane.uuid, "main", 0, patch)
        assert isinstance(result, schemas.TrailingEdgeDeviceDetailSchema)
        assert result.name == "rudder"

    def test_patch_trailing_edge_device_updates_existing(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        self._add_ted(db, wing, 0)
        patch = schemas.TrailingEdgeDevicePatchSchema.model_construct(
            hinge_spacing=3.0,
            hinge_type="top_simple",
        )
        result = wing_service.patch_trailing_edge_device(db, plane.uuid, "main", 0, patch)
        assert result.hinge_spacing == pytest.approx(3.0)

    def test_delete_trailing_edge_device(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        self._add_ted(db, wing, 0)
        wing_service.delete_trailing_edge_device(db, plane.uuid, "main", 0)
        db.refresh(wing)
        assert wing.x_secs[0].detail.trailing_edge_device is None

    def test_delete_trailing_edge_device_missing_raises(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        with pytest.raises(NotFoundError, match="Trailing-edge device not found"):
            wing_service.delete_trailing_edge_device(db, plane.uuid, "main", 0)


# ── Trailing Edge Servo ───────────────────────────────────────────────


class TestTrailingEdgeServoService:
    def _add_ted_with_servo(self, db, wing, xsec_index=0):
        xsec = wing.x_secs[xsec_index]
        if xsec.detail is None:
            xsec.detail = WingXSecDetailModel()
        servo = WingXSecTedServoModel(
            length=20, width=10, height=25,
            leading_length=5, latch_z=10, latch_x=5,
            latch_thickness=2, latch_length=5, cable_z=20,
            screw_hole_lx=0, screw_hole_d=0,
        )
        ted = WingXSecTrailingEdgeDeviceModel(
            name="ail",
            rel_chord_root=0.8,
            servo_data=servo,
        )
        xsec.detail.trailing_edge_device = ted
        db.add(ted)
        db.commit()
        return ted

    def _add_ted_no_servo(self, db, wing, xsec_index=0):
        xsec = wing.x_secs[xsec_index]
        if xsec.detail is None:
            xsec.detail = WingXSecDetailModel()
        ted = WingXSecTrailingEdgeDeviceModel(
            name="ail", rel_chord_root=0.8,
        )
        xsec.detail.trailing_edge_device = ted
        db.add(ted)
        db.commit()
        return ted

    def test_get_trailing_edge_servo(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        self._add_ted_with_servo(db, wing, 0)
        result = wing_service.get_trailing_edge_servo(db, plane.uuid, "main", 0)
        assert isinstance(result, schemas.TrailingEdgeServoSchema)

    def test_get_trailing_edge_servo_no_ted_raises(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        with pytest.raises(NotFoundError, match="Trailing-edge device not found"):
            wing_service.get_trailing_edge_servo(db, plane.uuid, "main", 0)

    def test_get_trailing_edge_servo_no_servo_raises(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        self._add_ted_no_servo(db, wing, 0)
        with pytest.raises(NotFoundError, match="No servo configured"):
            wing_service.get_trailing_edge_servo(db, plane.uuid, "main", 0)

    def test_get_trailing_edge_servo_terminal_raises(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        with pytest.raises(ValidationError, match="terminal"):
            wing_service.get_trailing_edge_servo(db, plane.uuid, "main", 1)

    def test_patch_trailing_edge_servo_with_int(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        self._add_ted_no_servo(db, wing, 0)
        patch = schemas.TrailingEdgeServoPatchSchema(servo=5)
        result = wing_service.patch_trailing_edge_servo(db, plane.uuid, "main", 0, patch)
        assert result.servo == 5

    def test_patch_trailing_edge_servo_with_object(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        self._add_ted_no_servo(db, wing, 0)
        servo = ServoSchema(
            length=23, width=12.5, height=31.5,
            leading_length=6, latch_z=14.5, latch_x=7.25,
            latch_thickness=2.6, latch_length=6, cable_z=26,
            screw_hole_lx=0, screw_hole_d=0,
        )
        patch = schemas.TrailingEdgeServoPatchSchema(servo=servo)
        result = wing_service.patch_trailing_edge_servo(db, plane.uuid, "main", 0, patch)
        assert isinstance(result, schemas.TrailingEdgeServoSchema)

    def test_patch_trailing_edge_servo_updates_existing(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        self._add_ted_with_servo(db, wing, 0)
        servo = ServoSchema(
            length=30, width=15, height=35,
            leading_length=8, latch_z=16, latch_x=8,
            latch_thickness=3, latch_length=7, cable_z=28,
            screw_hole_lx=1, screw_hole_d=2,
        )
        patch = schemas.TrailingEdgeServoPatchSchema(servo=servo)
        result = wing_service.patch_trailing_edge_servo(db, plane.uuid, "main", 0, patch)
        assert isinstance(result, schemas.TrailingEdgeServoSchema)

    def test_patch_trailing_edge_servo_no_ted_raises(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        patch = schemas.TrailingEdgeServoPatchSchema(servo=5)
        with pytest.raises(ValidationError, match="Trailing-edge device must exist"):
            wing_service.patch_trailing_edge_servo(db, plane.uuid, "main", 0, patch)

    def test_delete_trailing_edge_servo(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        self._add_ted_with_servo(db, wing, 0)
        wing_service.delete_trailing_edge_servo(db, plane.uuid, "main", 0)
        db.refresh(wing)
        ted = wing.x_secs[0].detail.trailing_edge_device
        assert ted.servo_data is None
        assert ted.servo_index is None

    def test_delete_trailing_edge_servo_no_ted_raises(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        with pytest.raises(NotFoundError, match="Trailing-edge device not found"):
            wing_service.delete_trailing_edge_servo(db, plane.uuid, "main", 0)

    def test_delete_trailing_edge_servo_no_servo_raises(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        self._add_ted_no_servo(db, wing, 0)
        with pytest.raises(NotFoundError, match="No servo configured"):
            wing_service.delete_trailing_edge_servo(db, plane.uuid, "main", 0)


# ── _ensure_segment_detail_or_raise ───────────────────────────────────


class TestEnsureSegmentDetailOrRaise:
    def test_creates_detail_when_missing(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=3)
        xsec = wing.x_secs[0]
        # Remove detail to test creation
        xsec.detail = None
        db.commit()
        result = wing_service._ensure_segment_detail_or_raise(xsec, 0, 3)
        assert isinstance(result, WingXSecDetailModel)

    def test_returns_existing_detail(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=3)
        xsec = wing.x_secs[0]
        existing = xsec.detail
        result = wing_service._ensure_segment_detail_or_raise(xsec, 0, 3)
        assert result is existing


# ── _servo_schema_from_ted / _control_surface_servo_details_schema_from_ted ──


class TestServoSchemaFromTed:
    def test_with_servo_data(self, db):
        ted = WingXSecTrailingEdgeDeviceModel(
            name="ail", rel_chord_root=0.8,
        )
        ted.servo_data = WingXSecTedServoModel(
            length=20, width=10, height=25,
            leading_length=5, latch_z=10, latch_x=5,
            latch_thickness=2, latch_length=5, cable_z=20,
            screw_hole_lx=0, screw_hole_d=0,
        )
        result = wing_service._servo_schema_from_ted(ted)
        assert isinstance(result, schemas.TrailingEdgeServoSchema)

    def test_with_servo_index(self):
        ted = WingXSecTrailingEdgeDeviceModel(
            name="ail", rel_chord_root=0.8, servo_index=3,
        )
        result = wing_service._servo_schema_from_ted(ted)
        assert result.servo == 3

    def test_no_servo_raises(self):
        ted = WingXSecTrailingEdgeDeviceModel(
            name="ail", rel_chord_root=0.8,
        )
        with pytest.raises(NotFoundError, match="No servo configured"):
            wing_service._servo_schema_from_ted(ted)

    def test_control_surface_variant_with_data(self, db):
        ted = WingXSecTrailingEdgeDeviceModel(
            name="ail", rel_chord_root=0.8,
        )
        ted.servo_data = WingXSecTedServoModel(
            length=20, width=10, height=25,
            leading_length=5, latch_z=10, latch_x=5,
            latch_thickness=2, latch_length=5, cable_z=20,
            screw_hole_lx=0, screw_hole_d=0,
        )
        result = wing_service._control_surface_servo_details_schema_from_ted(ted)
        assert isinstance(result, schemas.ControlSurfaceServoDetailsSchema)

    def test_control_surface_variant_no_servo_raises(self):
        ted = WingXSecTrailingEdgeDeviceModel(
            name="ail", rel_chord_root=0.8,
        )
        with pytest.raises(NotFoundError, match="No servo configured"):
            wing_service._control_surface_servo_details_schema_from_ted(ted)


# ── WingConfig roundtrip (via REST, integration) ──────────────────────


class TestWingConfigRoundtrip:
    def test_create_and_get_wingconfig(self, client):
        """Create a wing via wingconfig, then read it back."""
        resp = client.post("/aeroplanes", params={"name": "wc-rt"})
        assert resp.status_code == 201
        aid = resp.json()["id"]

        wc = {
            "segments": [
                {
                    "root_airfoil": {"airfoil": airfoil_path, "chord": 150.0, "incidence": 0},
                    "tip_airfoil": {"airfoil": airfoil_path, "chord": 120.0, "incidence": 0},
                    "length": 500.0,
                    "sweep": 10.0,
                    "number_interpolation_points": 101,
                }
            ],
            "nose_pnt": [0, 0, 0],
        }
        resp = client.post(f"/aeroplanes/{aid}/wings/wrt/from-wingconfig", json=wc)
        assert resp.status_code == 201, resp.text

        resp = client.get(f"/aeroplanes/{aid}/wings/wrt/wingconfig")
        assert resp.status_code == 200
        data = resp.json()
        assert "segments" in data
        assert len(data["segments"]) == 1

    def test_put_wingconfig_replaces(self, client):
        """PUT wingconfig replaces an existing wing."""
        resp = client.post("/aeroplanes", params={"name": "wc-put"})
        aid = resp.json()["id"]

        wc = {
            "segments": [
                {
                    "root_airfoil": {"airfoil": airfoil_path, "chord": 150.0, "incidence": 0},
                    "tip_airfoil": {"airfoil": airfoil_path, "chord": 120.0, "incidence": 0},
                    "length": 500.0,
                    "sweep": 10.0,
                    "number_interpolation_points": 101,
                }
            ],
            "nose_pnt": [0, 0, 0],
        }
        resp = client.post(f"/aeroplanes/{aid}/wings/wput/from-wingconfig", json=wc)
        assert resp.status_code == 201

        wc2 = {
            "segments": [
                {
                    "root_airfoil": {"airfoil": airfoil_path, "chord": 200.0, "incidence": 0},
                    "tip_airfoil": {"airfoil": airfoil_path, "chord": 160.0, "incidence": 0},
                    "length": 600.0,
                    "sweep": 15.0,
                    "number_interpolation_points": 50,
                }
            ],
            "nose_pnt": [10, 0, 0],
        }
        resp = client.put(f"/aeroplanes/{aid}/wings/wput/wingconfig", json=wc2)
        assert resp.status_code == 200, resp.text

    def test_put_wingconfig_creates_if_new(self, client):
        """PUT wingconfig creates the wing if it does not exist."""
        resp = client.post("/aeroplanes", params={"name": "wc-putnew"})
        aid = resp.json()["id"]

        wc = {
            "segments": [
                {
                    "root_airfoil": {"airfoil": airfoil_path, "chord": 150.0, "incidence": 0},
                    "tip_airfoil": {"airfoil": airfoil_path, "chord": 120.0, "incidence": 0},
                    "length": 500.0,
                    "sweep": 10.0,
                    "number_interpolation_points": 101,
                }
            ],
            "nose_pnt": [0, 0, 0],
        }
        resp = client.put(f"/aeroplanes/{aid}/wings/wnew/wingconfig", json=wc)
        assert resp.status_code == 200

    def test_create_wingconfig_duplicate_raises_422(self, client):
        """POST wingconfig with existing name should fail."""
        resp = client.post("/aeroplanes", params={"name": "wc-dup"})
        aid = resp.json()["id"]

        wc = {
            "segments": [
                {
                    "root_airfoil": {"airfoil": airfoil_path, "chord": 150.0, "incidence": 0},
                    "tip_airfoil": {"airfoil": airfoil_path, "chord": 120.0, "incidence": 0},
                    "length": 500.0,
                    "sweep": 10.0,
                    "number_interpolation_points": 101,
                }
            ],
            "nose_pnt": [0, 0, 0],
        }
        resp = client.post(f"/aeroplanes/{aid}/wings/wdup/from-wingconfig", json=wc)
        assert resp.status_code == 201

        resp = client.post(f"/aeroplanes/{aid}/wings/wdup/from-wingconfig", json=wc)
        assert resp.status_code == 422

    @pytest.mark.xfail(reason="wrong endpoint route (gh-299)", strict=False)
    def test_wingconfig_with_spars_and_ted(self, client):
        """Create wingconfig with spars and TED, then read back."""
        resp = client.post("/aeroplanes", params={"name": "wc-full"})
        aid = resp.json()["id"]

        wc = {
            "segments": [
                {
                    "root_airfoil": {"airfoil": airfoil_path, "chord": 150.0, "incidence": 0},
                    "tip_airfoil": {"airfoil": airfoil_path, "chord": 120.0, "incidence": 0},
                    "length": 500.0,
                    "sweep": 10.0,
                    "number_interpolation_points": 101,
                    "spare_list": [
                        {
                            "spare_support_dimension_width": 5.0,
                            "spare_support_dimension_height": 5.0,
                            "spare_position_factor": 0.25,
                            "spare_start": 0.0,
                            "spare_mode": "standard",
                        }
                    ],
                    "trailing_edge_device": {
                        "name": "aileron",
                        "rel_chord_root": 0.8,
                        "rel_chord_tip": 0.8,
                        "symmetric": False,
                    },
                }
            ],
            "nose_pnt": [0, 0, 0],
        }
        resp = client.post(f"/aeroplanes/{aid}/wings/wfull/from-wingconfig", json=wc)
        assert resp.status_code == 201, resp.text

        resp = client.get(f"/aeroplanes/{aid}/wings/wfull/wingconfig")
        assert resp.status_code == 200
        data = resp.json()
        seg = data["segments"][0]
        assert "spare_list" in seg
        assert len(seg["spare_list"]) >= 1
        assert "trailing_edge_device" in seg


# ── _build_cross_section_model ────────────────────────────────────────


class TestBuildCrossSectionModel:
    def test_terminal_xsec_drops_metadata(self):
        data = schemas.WingXSecGeometryWriteSchema.model_construct(
            xyz_le=[0, 0, 0],
            chord=0.1,
            twist=0,
            airfoil="naca0012",
            x_sec_type="tip",
            tip_type="round",
            number_interpolation_points=50,
        )
        result = wing_service._build_cross_section_model(data, sort_index=2, is_terminal_xsec=True)
        assert result.detail is None

    def test_non_terminal_with_metadata(self):
        data = schemas.WingXSecGeometryWriteSchema.model_construct(
            xyz_le=[0, 0, 0],
            chord=0.15,
            twist=0,
            airfoil="naca0012",
            x_sec_type="root",
            tip_type="flat",
            number_interpolation_points=80,
        )
        result = wing_service._build_cross_section_model(data, sort_index=0, is_terminal_xsec=False)
        assert result.detail is not None
        assert result.detail.tip_type == "flat"

    def test_non_terminal_without_metadata(self):
        data = schemas.WingXSecGeometryWriteSchema.model_construct(
            xyz_le=[0, 0, 0],
            chord=0.15,
            twist=0,
            airfoil="naca0012",
        )
        result = wing_service._build_cross_section_model(data, sort_index=0, is_terminal_xsec=False)
        # No metadata provided => no detail row
        assert result.detail is None


# ── _existing_ted_for_control_surface_or_raise ────────────────────────


class TestExistingTedForControlSurface:
    def test_returns_ted_when_present(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        xsec = wing.x_secs[0]
        if xsec.detail is None:
            xsec.detail = WingXSecDetailModel()
        ted = WingXSecTrailingEdgeDeviceModel(name="ail", rel_chord_root=0.8)
        xsec.detail.trailing_edge_device = ted
        db.commit()
        result = wing_service._existing_ted_for_control_surface_or_raise(
            wing, xsec, 0, "main"
        )
        assert result is ted

    def test_raises_when_no_ted(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        xsec = wing.x_secs[0]
        with pytest.raises(ValidationError, match="Control surface must exist"):
            wing_service._existing_ted_for_control_surface_or_raise(
                wing, xsec, 0, "main"
            )

    def test_raises_for_terminal(self, db):
        plane, wing = _make_plane_with_wing(db, xsec_count=2)
        xsec = wing.x_secs[1]
        with pytest.raises(ValidationError, match="terminal"):
            wing_service._existing_ted_for_control_surface_or_raise(
                wing, xsec, 1, "main"
            )
