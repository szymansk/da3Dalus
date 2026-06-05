"""Fast unit tests for section_aoa_service (gh-840).

Strategy
--------
The aerosandbox boundary is fully mocked.  Tests verify:
 - cl extraction formula: cl = 2·Γ / (Vmag · c)
 - alpha_eff = atan2(V·n, V·f)
 - alpha_geom = op_alpha + twist(y)   via linear interpolation
 - induced_angle = alpha_geom - alpha_eff
 - correct sorting by ascending y
 - unknown-wing error path
 - operating-point fallback logic in get_section_aoa

These tests never import aerosandbox; they patch it at the call sites.
"""

from __future__ import annotations

import asyncio
import math
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers — shared across tests (no copy-paste)
# ---------------------------------------------------------------------------


def _make_mock_ll(
    *,
    y_positions: list[float],
    gammas: list[float],
    chords: list[float],
    velocities: list[list[float]],
    fwds: list[list[float]],
    norms: list[list[float]],
):
    """Build a deterministic mock asb.LiftingLine result."""
    import numpy as np

    ll = MagicMock()
    ll.run = MagicMock()

    # vortex_centers: only y-column matters for y extraction
    n = len(y_positions)
    centers = [[0.0, y, 0.0] for y in y_positions]
    ll.vortex_centers = centers
    ll.vortex_strengths = gammas
    ll.chords = chords
    ll.local_forward_direction = fwds
    ll.normal_directions = norms

    # get_velocity_at_points must return an array
    ll.get_velocity_at_points = MagicMock(return_value=np.array(velocities))
    return ll


def _make_mock_airplane(
    wing_name: str = "main_wing",
    xsec_specs: list[tuple[float, float]] | None = None,
    symmetric: bool = True,
) -> MagicMock:
    """Build a mock asb.Airplane with one named wing."""
    if xsec_specs is None:
        # Two xsecs: root (y=0, twist=2°) and tip (y=0.5, twist=0°)
        xsec_specs = [(0.0, 2.0), (0.5, 0.0)]

    xsecs = []
    for y, twist in xsec_specs:
        xs = MagicMock()
        xs.xyz_le = [0.0, y, 0.0]
        xs.twist = twist
        xs.control_surfaces = []
        xsecs.append(xs)

    wing = MagicMock()
    wing.name = wing_name
    wing.symmetric = symmetric
    wing.xsecs = xsecs

    airplane = MagicMock()
    airplane.wings = [wing]
    airplane.xyz_ref = [0.1, 0.0, 0.0]
    airplane.with_control_deflections = MagicMock(return_value=airplane)
    return airplane


def _make_mock_asb_op(alpha_deg: float = 4.0) -> MagicMock:
    op = MagicMock()
    op.alpha = alpha_deg
    return op


# ---------------------------------------------------------------------------
# Tests: compute_section_aoa (pure function)
# ---------------------------------------------------------------------------


class TestComputeSectionAoa:
    """Tests for the pure compute_section_aoa function."""

    def _run(
        self,
        *,
        y_positions,
        gammas,
        chords,
        velocities,
        fwds,
        norms,
        op_alpha=4.0,
        xsec_specs=None,
        wing_name="main_wing",
    ):
        """Helper: patch LiftingLine and call compute_section_aoa."""
        import numpy as np
        from app.services.section_aoa_service import compute_section_aoa

        mock_ll = _make_mock_ll(
            y_positions=y_positions,
            gammas=gammas,
            chords=chords,
            velocities=velocities,
            fwds=fwds,
            norms=norms,
        )
        mock_airplane = _make_mock_airplane(
            wing_name=wing_name,
            xsec_specs=xsec_specs,
        )
        mock_op = _make_mock_asb_op(alpha_deg=op_alpha)

        mock_asb = MagicMock()
        mock_asb.Airplane = MagicMock(return_value=mock_airplane)
        mock_asb.LiftingLine = MagicMock(return_value=mock_ll)

        with patch.dict("sys.modules", {"aerosandbox": mock_asb}):
            # Re-import to pick up the patched module
            import importlib
            import app.services.section_aoa_service as svc

            importlib.reload(svc)
            entries = svc.compute_section_aoa(mock_airplane, mock_op, wing_name=wing_name)
        return entries

    def test_cl_formula(self):
        """cl = 2·Γ / (Vmag · chord) matches hand-computed value."""
        import numpy as np

        # Simple 1-panel case
        gamma = 0.5  # m²/s
        v = [10.0, 0.0, 0.0]
        chord = 0.2  # m
        vmag = 10.0
        expected_cl = 2.0 * gamma / (vmag * chord)  # = 0.5

        entries = self._run(
            y_positions=[0.25],
            gammas=[gamma],
            chords=[chord],
            velocities=[v],
            fwds=[[-1.0, 0.0, 0.0]],  # TE→LE (ASB convention)
            norms=[[0.0, 0.0, 1.0]],
            op_alpha=4.0,
            xsec_specs=[(0.0, 2.0), (0.5, 0.0)],
        )
        assert len(entries) == 1
        assert abs(entries[0].cl - expected_cl) < 1e-4

    def test_alpha_eff_formula(self):
        """alpha_eff = atan2(V·n, -V·f) [deg] (ASB convention: fwd is TE→LE).

        V = [10, 0, 1], fwd (TE→LE) = [-1, 0, 0], norm = [0, 0, 1]
        V·fwd = -10, V·norm = 1
        alpha_eff = atan2(1, -(-10)) = atan2(1, 10) [deg]
        """
        v = [10.0, 0.0, 1.0]
        # fwd is TE→LE in ASB convention (negative x for a standard wing)
        expected_alpha_eff = math.degrees(math.atan2(1.0, 10.0))

        entries = self._run(
            y_positions=[0.25],
            gammas=[0.3],
            chords=[0.2],
            velocities=[v],
            fwds=[[-1.0, 0.0, 0.0]],  # TE→LE (ASB convention)
            norms=[[0.0, 0.0, 1.0]],
            op_alpha=4.0,
            xsec_specs=[(0.0, 2.0), (0.5, 0.0)],
        )
        assert abs(entries[0].alpha_effective_deg - expected_alpha_eff) < 0.01

    def test_alpha_geom_includes_twist(self):
        """alpha_geom = op_alpha + twist(y) via linear interpolation."""
        # xsecs: root y=0 twist=2°, tip y=0.5 twist=0°
        # panel at y=0.25 → twist = 1° → alpha_geom = 4+1 = 5°
        entries = self._run(
            y_positions=[0.25],
            gammas=[0.3],
            chords=[0.2],
            velocities=[[10.0, 0.0, 0.0]],
            fwds=[[-1.0, 0.0, 0.0]],  # TE→LE (ASB convention)
            norms=[[0.0, 0.0, 1.0]],
            op_alpha=4.0,
            xsec_specs=[(0.0, 2.0), (0.5, 0.0)],
        )
        assert abs(entries[0].alpha_geometric_deg - 5.0) < 0.05

    def test_induced_angle_decomposition(self):
        """induced_angle = alpha_geom - alpha_eff."""
        entries = self._run(
            y_positions=[0.25],
            gammas=[0.3],
            chords=[0.2],
            velocities=[[10.0, 0.0, 0.5]],
            fwds=[[-1.0, 0.0, 0.0]],  # TE→LE (ASB convention)
            norms=[[0.0, 0.0, 1.0]],
            op_alpha=4.0,
            xsec_specs=[(0.0, 2.0), (0.5, 0.0)],
        )
        e = entries[0]
        assert abs(e.induced_angle_deg - (e.alpha_geometric_deg - e.alpha_effective_deg)) < 1e-6

    def test_sorted_by_ascending_y(self):
        """Output is sorted by ascending y_m."""
        entries = self._run(
            y_positions=[0.4, 0.1, 0.25],
            gammas=[0.3, 0.5, 0.4],
            chords=[0.2, 0.2, 0.2],
            velocities=[[10.0, 0.0, 0.0]] * 3,
            fwds=[[-1.0, 0.0, 0.0]] * 3,  # TE→LE (ASB convention)
            norms=[[0.0, 0.0, 1.0]] * 3,
            op_alpha=4.0,
            xsec_specs=[(0.0, 2.0), (0.5, 0.0)],
        )
        ys = [e.y_m for e in entries]
        assert ys == sorted(ys)

    def test_unknown_wing_raises(self):
        """ValidationDomainError raised when wing_name not found."""
        from app.services.section_aoa_service import compute_section_aoa
        from app.core.exceptions import ValidationDomainError

        mock_airplane = _make_mock_airplane(wing_name="main_wing")
        mock_op = _make_mock_asb_op()

        mock_asb = MagicMock()
        mock_asb.Airplane = MagicMock(return_value=mock_airplane)

        with patch.dict("sys.modules", {"aerosandbox": mock_asb}):
            import importlib
            import app.services.section_aoa_service as svc

            importlib.reload(svc)
            with pytest.raises(ValidationDomainError, match="not found"):
                svc.compute_section_aoa(mock_airplane, mock_op, wing_name="nonexistent_wing")


# ---------------------------------------------------------------------------
# Tests: endpoint schema (no aero, just Pydantic)
# ---------------------------------------------------------------------------


class TestSectionAoaSchema:
    """Validate the response schema serialises correctly."""

    def test_section_aoa_response_serialises(self):
        from app.api.v2.endpoints.section_aoa import SectionAoaResponse, SectionAoaPoint

        point = SectionAoaPoint(
            y_m=0.25,
            chord_m=0.18,
            cl=0.72,
            alpha_geometric_deg=5.5,
            alpha_effective_deg=3.1,
            induced_angle_deg=2.4,
        )
        resp = SectionAoaResponse(
            aeroplane_id="abc-123",
            wing_name="main_wing",
            operating_point_id=42,
            sections=[point],
        )
        d = resp.model_dump()
        assert d["sections"][0]["cl"] == 0.72
        assert d["wing_name"] == "main_wing"

    def test_section_aoa_response_no_op(self):
        from app.api.v2.endpoints.section_aoa import SectionAoaResponse

        resp = SectionAoaResponse(
            aeroplane_id="abc-123",
            wing_name="main_wing",
            operating_point_id=None,
            sections=[],
        )
        assert resp.operating_point_id is None
        assert resp.sections == []


# ---------------------------------------------------------------------------
# Tests: get_section_aoa (DB-aware async, mocked)
# ---------------------------------------------------------------------------


class TestGetSectionAoaService:
    """Tests for the DB-aware get_section_aoa async entry point.

    We test the OP-lookup logic by patching the operating_point_model_to_schema
    resolver (which has its own test suite) and testing the two critical paths:
      1. NotFoundError when the requested OP is not found.
      2. compute_section_aoa is called once on success.
    """

    def _make_op_schema(self):
        """Build a valid OperatingPointSchema for mocking."""
        from app.schemas.aeroanalysisschema import OperatingPointSchema

        return OperatingPointSchema(
            name="cruise",
            velocity=15.0,
            alpha=4.0,
            beta=0.0,
            p=0.0,
            q=0.0,
            r=0.0,
            xyz_ref=[0.1, 0.0, 0.0],
            altitude=0.0,
            control_deflections=None,
        )

    def test_op_lookup_not_found_raises(self):
        """NotFoundError when requested OP does not belong to this aircraft.

        Patch ``operating_point_model_to_schema`` at the resolver level to
        avoid fighting SQLAlchemy mock-chain complexity; the critical path is
        that ``get_section_aoa`` raises NotFoundError when the DB returns None.
        """
        from app.core.exceptions import NotFoundError
        from app.services.section_aoa_service import get_section_aoa

        mock_plane_schema = MagicMock()
        mock_plane_schema.id = 1
        mock_plane_schema.total_mass_kg = 1.5

        # All DB queries return None (no OP found)
        mock_query = MagicMock()
        mock_query.first.return_value = None
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.filter.return_value = mock_query
        # Also handle the single-filter path (TRIMMED OP fallback)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        mock_asb = MagicMock()
        mock_asb.Atmosphere = MagicMock(return_value=MagicMock())
        mock_asb.OperatingPoint = MagicMock(return_value=MagicMock())

        with (
            patch(
                "app.services.section_aoa_service.get_aeroplane_schema_or_raise",
                return_value=mock_plane_schema,
            ),
            patch(
                "app.services.section_aoa_service.aeroplane_schema_to_asb_airplane_async",
                return_value=_make_mock_airplane(),
            ),
            # Patch fallback so it doesn't call scipy/asb
            patch(
                "app.services.section_aoa_service._resolve_level_flight_op",
                side_effect=Exception("fallback called"),
            ),
        ):
            with pytest.raises(NotFoundError):
                asyncio.run(
                    get_section_aoa(
                        mock_db,
                        "some-uuid",
                        "main_wing",
                        operating_point_id=999,
                    )
                )

    def test_entry_point_calls_compute_on_success(self):
        """compute_section_aoa is called once when OP is resolved successfully."""
        from app.services.section_aoa_service import get_section_aoa

        mock_plane_schema = MagicMock()
        mock_plane_schema.id = 1
        mock_plane_schema.total_mass_kg = 1.5

        op_schema = self._make_op_schema()

        mock_asb = MagicMock()
        mock_asb.Atmosphere = MagicMock(return_value=MagicMock())
        mock_asb.OperatingPoint = MagicMock(return_value=MagicMock())

        mock_compute = MagicMock(return_value=[])
        with (
            patch(
                "app.services.section_aoa_service.get_aeroplane_schema_or_raise",
                return_value=mock_plane_schema,
            ),
            patch(
                "app.services.section_aoa_service.aeroplane_schema_to_asb_airplane_async",
                return_value=_make_mock_airplane(),
            ),
            # Patch both the DB-based OP lookup and the fallback to return a ready schema
            patch(
                "app.services.section_aoa_service._resolve_level_flight_op", return_value=op_schema
            ),
            patch(
                "app.services.operating_point_resolver.operating_point_model_to_schema",
                return_value=op_schema,
            ),
            patch("app.services.section_aoa_service.compute_section_aoa", mock_compute),
            patch.dict("sys.modules", {"aerosandbox": mock_asb}),
        ):
            # No operating_point_id → first tries DB query, then falls to fallback
            mock_db = MagicMock()
            # DB returns None → no TRIMMED OP stored → uses fallback
            mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = None
            result = asyncio.run(
                get_section_aoa(
                    mock_db,
                    "some-uuid",
                    "main_wing",
                    operating_point_id=None,
                )
            )

        assert isinstance(result, list)
        mock_compute.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: get_section_aoa — real DB, mocked ASB (gh-840 regression)
# ---------------------------------------------------------------------------


class TestGetSectionAoaDbPath:
    """Exercises the DB OP-resolution path of get_section_aoa using a real
    in-memory SQLite session (client_and_db fixture).

    These tests catch the AttributeError that fired because get_section_aoa
    used ``plane_schema.id`` (AeroplaneSchema has no .id field) instead of
    loading the DB integer PK from AeroplaneModel.

    AeroSandbox is fully mocked — this runs in the 'not slow' tier.
    """

    def test_resolves_trimmed_op_by_aircraft_id(self, client_and_db):
        """get_section_aoa() finds the TRIMMED OP for the aircraft and calls
        compute_section_aoa without raising AttributeError.

        Setup: create a real AeroplaneModel + TRIMMED OperatingPointModel in
        the in-memory DB, then call get_section_aoa with no operating_point_id.
        The service must resolve aircraft_db_id via AeroplaneModel.uuid and
        then find the matching OP.
        """
        import asyncio
        from unittest.mock import MagicMock, patch

        from app.tests.conftest import make_aeroplane, make_operating_point

        _client, SessionLocal = client_and_db
        db = SessionLocal()

        try:
            # Arrange: real DB rows
            aeroplane = make_aeroplane(db, name="test-section-aoa-plane")
            make_operating_point(
                db,
                aircraft_id=aeroplane.id,
                name="trimmed_op",
                velocity=15.0,
                alpha=0.07,  # radians — converted to degrees by resolver
                beta=0.0,
                xyz_ref=[0.1, 0.0, 0.0],
                altitude=0.0,
                status="TRIMMED",
            )

            # Mock ASB at the module boundary so no real LiftingLine runs
            mock_asb = MagicMock()
            mock_asb.Atmosphere = MagicMock(return_value=MagicMock())
            mock_asb.OperatingPoint = MagicMock(return_value=MagicMock())

            mock_compute = MagicMock(return_value=[])

            with (
                patch(
                    "app.services.section_aoa_service.aeroplane_schema_to_asb_airplane_async",
                    return_value=_make_mock_airplane(),
                ),
                patch(
                    "app.services.section_aoa_service.compute_section_aoa",
                    mock_compute,
                ),
                patch.dict("sys.modules", {"aerosandbox": mock_asb}),
            ):
                result = asyncio.run(
                    __import__(
                        "app.services.section_aoa_service", fromlist=["get_section_aoa"]
                    ).get_section_aoa(
                        db,
                        aeroplane.uuid,
                        "main_wing",
                        operating_point_id=None,
                    )
                )

            # Assert: no AttributeError, compute_section_aoa was reached
            assert isinstance(result, list)
            mock_compute.assert_called_once()

        finally:
            db.close()

    def test_explicit_op_id_resolves_by_aircraft_id(self, client_and_db):
        """get_section_aoa() with an explicit operating_point_id resolves the
        OP correctly when it belongs to the aircraft.

        This covers the explicit-OP branch that also used plane_schema.id.
        """
        import asyncio
        from unittest.mock import MagicMock, patch

        from app.tests.conftest import make_aeroplane, make_operating_point

        _client, SessionLocal = client_and_db
        db = SessionLocal()

        try:
            aeroplane = make_aeroplane(db, name="test-explicit-op-plane")
            op_model = make_operating_point(
                db,
                aircraft_id=aeroplane.id,
                name="explicit_op",
                velocity=20.0,
                alpha=0.05,
                beta=0.0,
                xyz_ref=[0.1, 0.0, 0.0],
                altitude=0.0,
                status="TRIMMED",
            )

            mock_asb = MagicMock()
            mock_asb.Atmosphere = MagicMock(return_value=MagicMock())
            mock_asb.OperatingPoint = MagicMock(return_value=MagicMock())

            mock_compute = MagicMock(return_value=[])

            with (
                patch(
                    "app.services.section_aoa_service.aeroplane_schema_to_asb_airplane_async",
                    return_value=_make_mock_airplane(),
                ),
                patch(
                    "app.services.section_aoa_service.compute_section_aoa",
                    mock_compute,
                ),
                patch.dict("sys.modules", {"aerosandbox": mock_asb}),
            ):
                result = asyncio.run(
                    __import__(
                        "app.services.section_aoa_service", fromlist=["get_section_aoa"]
                    ).get_section_aoa(
                        db,
                        aeroplane.uuid,
                        "main_wing",
                        operating_point_id=op_model.id,
                    )
                )

            assert isinstance(result, list)
            mock_compute.assert_called_once()

        finally:
            db.close()
