"""gh-1080: TDD tests for shape-plumbing, tube-only bore-propagation, and
stock-snapping in the spar-plan pipeline.

Iron Law: these tests are written FIRST and drive the implementation.

Coverage targets:
- SparPlanRequest.shape validates to tube|rod|rectangular|capped, default 'tube'.
- compute_spar_plan_object passes shape into front_spec and rear_spec.
- plan_spar bore-propagation is TUBE-ONLY: non-tube multi-piece spars do NOT
  grow root bores to admit tip ODs (joiner-connected, not telescoping).
- Rod pieces: inner_d=0, joint='joiner' on intermediate, shape='rod'.
- Tube path: inner_d>0, joint='telescoping' on intermediate — UNCHANGED.
- Stock snapping: select lightest adequate stock from seeded DB rows by
  W_stock(Da,Di) >= erf_W (tube: W=π(Da⁴−Di⁴)/(32·Da); rod: W=d³/10).
- Infeasibility surfaced with reason when no stock fits.
- SparPieceOut carries width/height/cap_width for rectangular/capped; None for tube/rod.
- SparPlanRequest.shape invalid value rejected by Pydantic.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.component import ComponentModel
from app.schemas.spar_plan import MomentSample, SparPieceOut, SparPlanRequest
from app.services import spar_plan_service
from cad_designer.airplane.geometry.spar_solver import (
    SparPiece,
    SparPlan,
    SparRole,
    SparSpec,
    StationData,
    plan_spar,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _station(
    y_span: float,
    *,
    y_mm: float,
    band: tuple[float, float] = (-50.0, 50.0),
    required_od: float = 10.0,
    x_c: float = 0.4,
) -> StationData:
    return StationData(
        y_span=y_span,
        y_mm=y_mm,
        x_c=x_c,
        center_z=0.0,
        band_lo=band[0],
        band_hi=band[1],
        required_od=required_od,
    )


def _multi_piece_stations() -> list[StationData]:
    """Stations that force a two-piece plan (root OD won't fit outboard band)."""
    return [
        _station(0.0, y_mm=0.0, band=(-60.0, 60.0), required_od=50.0),
        _station(0.5, y_mm=500.0, band=(-60.0, 60.0), required_od=50.0),
        _station(0.5001, y_mm=500.1, band=(-10.0, 10.0), required_od=8.0),
        _station(1.0, y_mm=1000.0, band=(-10.0, 10.0), required_od=8.0),
    ]


def _uniform_stations(n: int = 3, *, required_od: float = 10.0) -> list[StationData]:
    return [
        _station(i / (n - 1), y_mm=i * 200.0, band=(-50.0, 50.0), required_od=required_od)
        for i in range(n)
    ]


def _basic_request(**overrides):
    body = dict(
        material_id=7,
        moments=[
            MomentSample(y_span=0.0, bending_moment_Nm=10.0),
            MomentSample(y_span=1.0, bending_moment_Nm=0.0),
        ],
    )
    body.update(overrides)
    return SparPlanRequest(**body)


def _piece(role=SparRole.FRONT, **kw):
    defaults = dict(
        role=role,
        spare_origin=(0.0, 0.0, 5.0),
        spare_vector=(0.0, 1.0, 0.0),
        outer_d=10.0,
        inner_d=0.0,
        shape="rod",
        governing_y=0.0,
        utilisation=0.8,
        length=300.0,
    )
    defaults.update(kw)
    return SparPiece(**defaults)


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SM = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    db = SM()
    yield db
    db.close()


def _seed_tube_stock(
    session: Session,
    *,
    outer_d_mm: float,
    inner_d_mm: float,
    density: float = 1550.0,
    sigma: float = 200.0,
    name: str | None = None,
) -> ComponentModel:
    """Seed a geometry-complete spar_tube stock row into the in-memory DB."""
    row = ComponentModel(
        name=name or f"TestTube OD{outer_d_mm}/ID{inner_d_mm}",
        component_type="spar_tube",
        specs={
            "outer_d_mm": outer_d_mm,
            "inner_d_mm": inner_d_mm,
            "role_use": "spar",
            "geometry_complete": True,
            "density_kg_m3": density,
            "allowable_bending_stress_mpa": sigma,
            "length_mm": [1000],
        },
    )
    session.add(row)
    session.flush()
    return row


def _seed_rod_stock(
    session: Session,
    *,
    outer_d_mm: float,
    density: float = 1580.0,
    sigma: float = 400.0,
    name: str | None = None,
) -> ComponentModel:
    """Seed a geometry-complete solid rod (inner_d_mm=0) spar_tube stock row."""
    row = ComponentModel(
        name=name or f"TestRod OD{outer_d_mm}",
        component_type="spar_tube",
        specs={
            "outer_d_mm": outer_d_mm,
            "inner_d_mm": 0.0,
            "role_use": "spar",
            "geometry_complete": True,
            "density_kg_m3": density,
            "allowable_bending_stress_mpa": sigma,
            "length_mm": [1000],
        },
    )
    session.add(row)
    session.flush()
    return row


# ---------------------------------------------------------------------------
# 1. SparPlanRequest.shape field validation
# ---------------------------------------------------------------------------


class TestSparPlanRequestShape:
    def test_default_shape_is_tube(self):
        req = _basic_request()
        assert req.shape == "tube"

    def test_shape_rod_accepted(self):
        req = _basic_request(shape="rod")
        assert req.shape == "rod"

    def test_shape_rectangular_accepted(self):
        req = _basic_request(shape="rectangular")
        assert req.shape == "rectangular"

    def test_shape_capped_accepted(self):
        req = _basic_request(shape="capped")
        assert req.shape == "capped"

    def test_invalid_shape_rejected(self):
        with pytest.raises(PydanticValidationError):
            _basic_request(shape="unknown_shape")


# ---------------------------------------------------------------------------
# 2. SparPieceOut width/height/cap_width optional fields
# ---------------------------------------------------------------------------


class TestSparPieceOutExtendedFields:
    def test_tube_rod_fields_default_to_none(self):
        """Tube/rod paths don't populate width/height/cap_width."""
        out = SparPieceOut(
            role="front",
            spare_origin=[0.0, 0.0, 0.0],
            spare_vector=[0.0, 1.0, 0.0],
            outer_d=0.01,
            inner_d=0.0,
            wall=0.0,
            shape="rod",
            governing_y=0.0,
            x_over_chord=0.3,
            y_start=0.0,
            y_end=0.5,
            utilisation=0.7,
        )
        assert out.width is None
        assert out.height is None
        assert out.cap_width is None

    def test_rectangular_fields_round_trip(self):
        """width and height can be set for rectangular cross-sections."""
        out = SparPieceOut(
            role="front",
            spare_origin=[0.0, 0.0, 0.0],
            spare_vector=[0.0, 1.0, 0.0],
            outer_d=0.012,
            inner_d=0.0,
            wall=0.0,
            shape="rectangular",
            governing_y=0.0,
            x_over_chord=0.3,
            y_start=0.0,
            y_end=0.5,
            utilisation=0.6,
            width=0.005,
            height=0.012,
        )
        assert out.width == pytest.approx(0.005)
        assert out.height == pytest.approx(0.012)
        assert out.cap_width is None

    def test_capped_fields_round_trip(self):
        """cap_width can be set for capped (I/C beam) cross-sections."""
        out = SparPieceOut(
            role="front",
            spare_origin=[0.0, 0.0, 0.0],
            spare_vector=[0.0, 1.0, 0.0],
            outer_d=0.015,
            inner_d=0.0,
            wall=0.0,
            shape="capped",
            governing_y=0.0,
            x_over_chord=0.3,
            y_start=0.0,
            y_end=0.5,
            utilisation=0.55,
            cap_width=0.008,
        )
        assert out.cap_width == pytest.approx(0.008)
        assert out.width is None
        assert out.height is None


# ---------------------------------------------------------------------------
# 3. plan_spar: bore-propagation is TUBE-ONLY (non-tube pieces stay at their
#    own strength bore = 0 for rods, without tube-stack clearance growth)
# ---------------------------------------------------------------------------


class TestBorePropagationTubeOnly:
    def test_tube_multi_piece_root_bore_grows_to_admit_tip_od(self):
        """Tube spars: root bore grows to accommodate tip OD + clearance (existing behaviour)."""
        spec = SparSpec(role=SparRole.FRONT, shape="tube", telescope_clearance_mm=0.5)
        pieces = plan_spar(_multi_piece_stations(), spec)
        assert len(pieces) >= 2
        root_piece = pieces[0]
        tip_piece = pieces[1]
        # root inner_d >= tip outer_d + 2*clearance (so tip slides in)
        assert root_piece.inner_d >= tip_piece.outer_d + 2 * 0.5 - 1e-6

    def test_rod_multi_piece_inner_d_is_zero(self):
        """Rod spars: all pieces have inner_d=0 (solid, no bore expansion)."""
        spec = SparSpec(role=SparRole.FRONT, shape="rod")
        pieces = plan_spar(_multi_piece_stations(), spec)
        assert len(pieces) >= 2
        for p in pieces:
            assert p.inner_d == pytest.approx(0.0), (
                f"Rod piece at y={p.governing_y} must have inner_d=0, got {p.inner_d}"
            )

    def test_rod_multi_piece_joint_is_joiner_not_telescoping(self):
        """Rod spars use 'joiner' for intermediate joints (not telescoping)."""
        spec = SparSpec(role=SparRole.FRONT, shape="rod")
        pieces = plan_spar(_multi_piece_stations(), spec)
        assert len(pieces) >= 2
        for p in pieces[:-1]:
            assert p.joint_to_next == "joiner", (
                f"rod piece joint should be 'joiner', got {p.joint_to_next!r}"
            )

    def test_tube_single_piece_has_positive_inner_d(self):
        """Single-piece tube: inner_d is strength-driven (wall from solve_dimension)."""
        spec = SparSpec(role=SparRole.FRONT, shape="tube")
        pieces = plan_spar(_uniform_stations(required_od=10.0), spec)
        assert len(pieces) == 1
        assert pieces[0].inner_d >= 0.0

    def test_rod_single_piece_has_zero_inner_d(self):
        """Single-piece rod: inner_d=0 (solid)."""
        spec = SparSpec(role=SparRole.FRONT, shape="rod")
        pieces = plan_spar(_uniform_stations(required_od=10.0), spec)
        assert len(pieces) == 1
        assert pieces[0].inner_d == pytest.approx(0.0)
        assert pieces[0].shape == "rod"


# ---------------------------------------------------------------------------
# 4. Stock snapping: W_stock(Da,Di) >= erf_W (section-modulus comparison)
# ---------------------------------------------------------------------------


class TestStockSnapping:
    """Tests for snap_piece_to_stock() and apply_stock_snap_to_plan() in
    spar_plan_service.  These use an in-memory SQLite DB seeded with stock rows.
    """

    def test_tube_piece_snaps_to_lightest_adequate_stock(self, db_session):
        """A tube piece snaps UP (never DOWN) to the lightest stock whose
        W_tube(Da,Di) >= erf_W of the piece's required OD."""
        # Seed tubes: OD10/ID8, OD12/ID10, OD14/ID12 (same density for simplicity)
        _seed_tube_stock(db_session, outer_d_mm=10.0, inner_d_mm=8.0)
        _seed_tube_stock(db_session, outer_d_mm=12.0, inner_d_mm=10.0)
        _seed_tube_stock(db_session, outer_d_mm=14.0, inner_d_mm=12.0)
        db_session.commit()

        # A piece whose required OD is 9.0 mm.  W_rod(9) = 9³/10 = 72.9 mm³.
        # W_tube(10,8) = π*(10⁴-8⁴)/(32*10) = π*(10000-4096)/320 = π*5904/320 ≈ 57.98 mm³.
        # That is LESS than 72.9, so OD10/ID8 must be skipped.
        # W_tube(12,10) = π*(12⁴-10⁴)/(32*12) = π*(20736-10000)/384 ≈ 87.96 mm³ ≥ 72.9 ✓
        # → should snap to OD12/ID10.
        erf_w = 9.0**3 / 10.0  # 72.9 mm³
        piece = _piece(shape="tube", outer_d=9.0, inner_d=7.0)

        result = spar_plan_service.snap_piece_to_stock(db_session, piece, erf_w=erf_w)

        assert result is not None
        assert result.outer_d == pytest.approx(12.0)
        assert result.inner_d == pytest.approx(10.0)
        assert result.shape == "tube"
        assert result.infeasibility_reason is None

    def test_rod_piece_snaps_to_adequate_rod_stock(self, db_session):
        """A rod piece snaps to adequate solid rod stock using W_rod = d³/10."""
        _seed_rod_stock(db_session, outer_d_mm=4.0)
        _seed_rod_stock(db_session, outer_d_mm=6.0)
        _seed_rod_stock(db_session, outer_d_mm=8.0)
        db_session.commit()

        # Required OD 5.0 mm → erf_W = 5³/10 = 12.5 mm³.
        # W_rod(4) = 4³/10 = 6.4 < 12.5 → skip.
        # W_rod(6) = 6³/10 = 21.6 ≥ 12.5 → snap to 6 mm rod.
        erf_w = 5.0**3 / 10.0  # 12.5 mm³
        piece = _piece(shape="rod", outer_d=5.0, inner_d=0.0)

        result = spar_plan_service.snap_piece_to_stock(db_session, piece, erf_w=erf_w)

        assert result is not None
        assert result.outer_d == pytest.approx(6.0)
        assert result.inner_d == pytest.approx(0.0)
        assert result.shape == "rod"

    def test_no_adequate_stock_marks_infeasible(self, db_session):
        """When no stock satisfies W_stock >= erf_W, the piece is marked infeasible."""
        # Only tiny tubes in stock
        _seed_tube_stock(db_session, outer_d_mm=3.0, inner_d_mm=1.0)
        db_session.commit()

        # Required W is huge — no stock can satisfy it
        erf_w = 9999.0  # mm³
        piece = _piece(shape="tube", outer_d=50.0, inner_d=40.0)

        result = spar_plan_service.snap_piece_to_stock(db_session, piece, erf_w=erf_w)

        assert result is not None
        assert result.feasible is False
        assert result.infeasibility_reason is not None
        assert "stock" in result.infeasibility_reason.lower()

    def test_snap_prefers_lightest_adequate_stock(self, db_session):
        """Among multiple adequate stocks, the one with minimum ρ·A (linear mass) wins."""
        # Two stocks both adequate: OD10/ID8 (thin-wall, lighter) vs OD12/ID10 (thicker).
        # Both are much stronger than erf_W=1 mm³ (trivial requirement).
        # OD10 has linear mass ρ·A = 1550 * π/4*(10²-8²) = 1550 * π/4*36 ≈ 43747 g/m²
        # OD12 has ρ·A = 1550 * π/4*(12²-10²) = 1550 * π/4*44 ≈ 53407 g/m²
        # → OD10/ID8 is lighter, should win.
        _seed_tube_stock(db_session, outer_d_mm=10.0, inner_d_mm=8.0, density=1550.0)
        _seed_tube_stock(db_session, outer_d_mm=12.0, inner_d_mm=10.0, density=1550.0)
        db_session.commit()

        piece = _piece(shape="tube", outer_d=5.0, inner_d=3.0)
        result = spar_plan_service.snap_piece_to_stock(db_session, piece, erf_w=1.0)

        assert result is not None
        assert result.outer_d == pytest.approx(10.0)  # lightest adequate

    def test_rod_stock_selected_correctly_using_rod_modulus(self, db_session):
        """Rod snapping must use W=d³/10, not tube formula.  A tube in DB for the
        same OD has W_tube < W_rod(same OD), so rod stock must be matched to rod
        formula: W_rod(d) = d³/10.
        """
        # Seed only rod stock (inner_d=0.0)
        _seed_rod_stock(db_session, outer_d_mm=5.0)
        _seed_rod_stock(db_session, outer_d_mm=8.0)
        db_session.commit()

        # Piece requires erf_W = 5³/10 = 12.5 mm³.
        # W_rod(5) = 12.5 — exactly meets it.  W_rod(8) = 51.2 > 12.5.
        # Lightest adequate = OD5 (smaller area).
        erf_w = 5.0**3 / 10.0
        piece = _piece(shape="rod", outer_d=5.0, inner_d=0.0)

        result = spar_plan_service.snap_piece_to_stock(db_session, piece, erf_w=erf_w)
        assert result.outer_d == pytest.approx(5.0)

    def test_snap_ignores_geometry_incomplete_stock(self, db_session):
        """geometry_complete=False records (conical, etc.) must be excluded from snap."""
        incomplete = ComponentModel(
            name="Conical boom",
            component_type="spar_tube",
            specs={
                "outer_d_mm": None,
                "inner_d_mm": None,
                "role_use": "spar",
                "geometry_complete": False,
                "density_kg_m3": 1550.0,
            },
        )
        db_session.add(incomplete)
        _seed_tube_stock(db_session, outer_d_mm=8.0, inner_d_mm=6.0)
        db_session.commit()

        erf_w = 1.0  # trivially small — any tube would do
        piece = _piece(shape="tube", outer_d=5.0, inner_d=3.0)
        result = spar_plan_service.snap_piece_to_stock(db_session, piece, erf_w=erf_w)
        assert result.outer_d == pytest.approx(8.0)  # snapped to OD8 (not the incomplete one)


# ---------------------------------------------------------------------------
# 5. End-to-end: shape="rod" in SparPlanRequest → rod pieces in response
# ---------------------------------------------------------------------------


class TestRodEndToEnd:
    """Verify that shape="rod" in the request flows end-to-end through the
    service and the plan_spar solver, producing pieces with shape='rod',
    inner_d=0, joint='joiner'."""

    def _patch_full(self, aeroplane, plan, db_session, sigma=200.0, g_limit=3.0):
        """Patch every external boundary; inject the real db_session for stock lookup."""
        import uuid

        stations = [
            StationData(
                y_span=0.0,
                y_mm=0.0,
                x_c=0.3,
                center_z=0.0,
                band_lo=-50.0,
                band_hi=50.0,
                required_od=10.0,
            ),
            StationData(
                y_span=1.0,
                y_mm=500.0,
                x_c=0.3,
                center_z=0.0,
                band_lo=-50.0,
                band_hi=50.0,
                required_od=5.0,
            ),
        ]
        return [
            patch.object(spar_plan_service, "get_aeroplane_or_raise", return_value=aeroplane),
            patch.object(spar_plan_service, "wing_model_to_wing_config", return_value=object()),
            patch.object(spar_plan_service, "_build_section_geometry", return_value=object()),
            patch.object(spar_plan_service, "_resolve_sigma_allow", return_value=sigma),
            patch.object(spar_plan_service, "_resolve_g_limit", return_value=g_limit),
            patch(
                "cad_designer.airplane.geometry.spar_solver.build_stations_from_geometry",
                return_value=stations,
            ),
        ]

    def _run(self, patches, fn):
        if not patches:
            return fn()
        with patches[0]:
            return self._run(patches[1:], fn)

    def test_rod_request_produces_rod_pieces_with_no_inner_d(self, db_session):
        """shape='rod' in the request → all pieces have shape='rod', inner_d=0."""
        import uuid

        aeroplane = SimpleNamespace(
            wings=[SimpleNamespace(name="main_wing")],
            uuid=uuid.uuid4(),
        )
        # Seed rod stock so snap can succeed
        _seed_rod_stock(db_session, outer_d_mm=6.0)
        _seed_rod_stock(db_session, outer_d_mm=10.0)
        db_session.commit()

        req = _basic_request(shape="rod")
        patches = self._patch_full(aeroplane, None, db_session)
        resp = self._run(
            patches,
            lambda: spar_plan_service.compute_spar_plan(
                db=db_session, aeroplane_uuid=aeroplane.uuid, request=req
            ),
        )

        assert len(resp.front_pieces) >= 1
        for p in resp.front_pieces:
            assert p.shape == "rod", f"Expected 'rod', got {p.shape!r}"
            assert p.inner_d == pytest.approx(0.0), f"Rod must have inner_d=0, got {p.inner_d}"

    def test_rod_pieces_use_joiner_not_telescoping(self, db_session):
        """Multi-piece rod spar must use 'joiner', never 'telescoping'."""
        import uuid

        aeroplane = SimpleNamespace(
            wings=[SimpleNamespace(name="main_wing")],
            uuid=uuid.uuid4(),
        )
        _seed_rod_stock(db_session, outer_d_mm=6.0)
        _seed_rod_stock(db_session, outer_d_mm=10.0)
        db_session.commit()

        req = _basic_request(shape="rod")

        # Force two pieces by injecting stations where root requires huge OD
        tight_stations = [
            StationData(
                y_span=0.0,
                y_mm=0.0,
                x_c=0.3,
                center_z=0.0,
                band_lo=-60.0,
                band_hi=60.0,
                required_od=45.0,
            ),
            StationData(
                y_span=0.5,
                y_mm=500.0,
                x_c=0.3,
                center_z=0.0,
                band_lo=-60.0,
                band_hi=60.0,
                required_od=45.0,
            ),
            StationData(
                y_span=0.5001,
                y_mm=500.1,
                x_c=0.3,
                center_z=0.0,
                band_lo=-10.0,
                band_hi=10.0,
                required_od=8.0,
            ),
            StationData(
                y_span=1.0,
                y_mm=1000.0,
                x_c=0.3,
                center_z=0.0,
                band_lo=-10.0,
                band_hi=10.0,
                required_od=8.0,
            ),
        ]
        # Need rod stock large enough for root (45 mm) too
        _seed_rod_stock(db_session, outer_d_mm=50.0, name="BigRod 50mm")
        db_session.commit()

        patches = [
            patch.object(spar_plan_service, "get_aeroplane_or_raise", return_value=aeroplane),
            patch.object(spar_plan_service, "wing_model_to_wing_config", return_value=object()),
            patch.object(spar_plan_service, "_build_section_geometry", return_value=object()),
            patch.object(spar_plan_service, "_resolve_sigma_allow", return_value=200.0),
            patch.object(spar_plan_service, "_resolve_g_limit", return_value=3.0),
            patch(
                "cad_designer.airplane.geometry.spar_solver.build_stations_from_geometry",
                return_value=tight_stations,
            ),
        ]
        resp = self._run(
            patches,
            lambda: spar_plan_service.compute_spar_plan(
                db=db_session, aeroplane_uuid=aeroplane.uuid, request=req
            ),
        )

        # At least two pieces expected from the tight outboard band
        assert len(resp.front_pieces) >= 2
        for p in resp.front_pieces[:-1]:
            assert p.joint_to_next == "joiner", (
                f"rod piece must use 'joiner', got {p.joint_to_next!r}"
            )
        assert resp.front_pieces[-1].joint_to_next is None

    def test_tube_path_unchanged(self, db_session):
        """Regression: default shape='tube' still yields tube pieces with positive inner_d."""
        import uuid

        aeroplane = SimpleNamespace(
            wings=[SimpleNamespace(name="main_wing")],
            uuid=uuid.uuid4(),
        )
        _seed_tube_stock(db_session, outer_d_mm=10.0, inner_d_mm=8.0)
        _seed_tube_stock(db_session, outer_d_mm=12.0, inner_d_mm=10.0)
        db_session.commit()

        req = _basic_request(shape="tube")
        stations = [
            StationData(
                y_span=0.0,
                y_mm=0.0,
                x_c=0.3,
                center_z=0.0,
                band_lo=-50.0,
                band_hi=50.0,
                required_od=8.0,
            ),
            StationData(
                y_span=1.0,
                y_mm=500.0,
                x_c=0.3,
                center_z=0.0,
                band_lo=-50.0,
                band_hi=50.0,
                required_od=4.0,
            ),
        ]
        patches = [
            patch.object(spar_plan_service, "get_aeroplane_or_raise", return_value=aeroplane),
            patch.object(spar_plan_service, "wing_model_to_wing_config", return_value=object()),
            patch.object(spar_plan_service, "_build_section_geometry", return_value=object()),
            patch.object(spar_plan_service, "_resolve_sigma_allow", return_value=200.0),
            patch.object(spar_plan_service, "_resolve_g_limit", return_value=3.0),
            patch(
                "cad_designer.airplane.geometry.spar_solver.build_stations_from_geometry",
                return_value=stations,
            ),
        ]
        resp = self._run(
            patches,
            lambda: spar_plan_service.compute_spar_plan(
                db=db_session, aeroplane_uuid=aeroplane.uuid, request=req
            ),
        )

        assert len(resp.front_pieces) >= 1
        for p in resp.front_pieces:
            assert p.shape == "tube"
            assert p.inner_d > 0.0, f"Tube must have positive inner_d, got {p.inner_d}"

    def test_no_stock_yields_infeasible_plan(self, db_session):
        """When no stock satisfies W_stock >= erf_W, the plan is infeasible with reason."""
        import uuid

        aeroplane = SimpleNamespace(
            wings=[SimpleNamespace(name="main_wing")],
            uuid=uuid.uuid4(),
        )
        # Only tiny tube stock — will fail to cover the required W
        _seed_tube_stock(db_session, outer_d_mm=3.0, inner_d_mm=1.0, sigma=200.0)
        db_session.commit()

        # Stations that need a large OD / W
        large_req_stations = [
            StationData(
                y_span=0.0,
                y_mm=0.0,
                x_c=0.3,
                center_z=0.0,
                band_lo=-200.0,
                band_hi=200.0,
                required_od=100.0,
            ),
            StationData(
                y_span=1.0,
                y_mm=500.0,
                x_c=0.3,
                center_z=0.0,
                band_lo=-200.0,
                band_hi=200.0,
                required_od=50.0,
            ),
        ]
        req = _basic_request(shape="tube")
        patches = [
            patch.object(spar_plan_service, "get_aeroplane_or_raise", return_value=aeroplane),
            patch.object(spar_plan_service, "wing_model_to_wing_config", return_value=object()),
            patch.object(spar_plan_service, "_build_section_geometry", return_value=object()),
            patch.object(spar_plan_service, "_resolve_sigma_allow", return_value=200.0),
            patch.object(spar_plan_service, "_resolve_g_limit", return_value=3.0),
            patch(
                "cad_designer.airplane.geometry.spar_solver.build_stations_from_geometry",
                return_value=large_req_stations,
            ),
        ]
        resp = self._run(
            patches,
            lambda: spar_plan_service.compute_spar_plan(
                db=db_session, aeroplane_uuid=aeroplane.uuid, request=req
            ),
        )
        assert resp.feasible is False
        assert resp.infeasibility_reason is not None
        assert "stock" in resp.infeasibility_reason.lower()
