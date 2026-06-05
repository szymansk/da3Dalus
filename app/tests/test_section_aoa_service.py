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
        """alpha_eff = degrees(cl / (2*pi)) + alpha_L0  (CL-based, tip-singularity-safe).

        With mock airfoils alpha_L0 falls back to 0° (NeuralFoil mock raises →
        exception handler returns 0).

        Panel parameters:
          gamma = 0.3 m²/s,  V = [10, 0, 1] m/s  →  Vmag = sqrt(101),
          chord = 0.2 m
          cl = 2 * 0.3 / (sqrt(101) * 0.2)
          alpha_eff = degrees(cl / (2*pi))   (alpha_L0 = 0 from mock fallback)
        """
        import numpy as np

        gamma = 0.3
        v = [10.0, 0.0, 1.0]
        chord = 0.2
        vmag = math.sqrt(101.0)
        cl_expected = 2.0 * gamma / (vmag * chord)
        a0 = 2.0 * math.pi
        expected_alpha_eff = math.degrees(cl_expected / a0)  # alpha_L0 = 0

        entries = self._run(
            y_positions=[0.25],
            gammas=[gamma],
            chords=[chord],
            velocities=[v],
            fwds=[[-1.0, 0.0, 0.0]],  # still needed for vmag computation
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


# ---------------------------------------------------------------------------
# Tests: SectionAoaEntry.to_dict()
# ---------------------------------------------------------------------------


class TestSectionAoaEntryToDict:
    """SectionAoaEntry.to_dict() must return all fields."""

    def test_to_dict_all_fields(self):
        from app.services.section_aoa_service import SectionAoaEntry

        e = SectionAoaEntry(
            y_m=0.25,
            chord_m=0.18,
            cl=0.72,
            alpha_geometric_deg=5.5,
            alpha_effective_deg=3.1,
            induced_angle_deg=2.4,
        )
        d = e.to_dict()
        assert d["y_m"] == 0.25
        assert d["chord_m"] == 0.18
        assert d["cl"] == 0.72
        assert d["alpha_geometric_deg"] == 5.5
        assert d["alpha_effective_deg"] == 3.1
        assert d["induced_angle_deg"] == 2.4


# ---------------------------------------------------------------------------
# Tests: _compute_alpha_l0_per_section error paths
# ---------------------------------------------------------------------------


class TestComputeAlphaL0PerSection:
    """Unit tests for the _compute_alpha_l0_per_section helper.

    All NeuralFoil / airfoil access is mocked to exercise the exception
    fallback paths without importing real aerosandbox.
    """

    def _run_helper(self, xsec_mocks, op_velocity=15.0):
        """Call _compute_alpha_l0_per_section with fake wing + op objects."""
        mock_wing = MagicMock()
        mock_wing.xsecs = xsec_mocks

        mock_op = MagicMock()
        mock_op.velocity = op_velocity

        from app.services import section_aoa_service as svc

        return svc._compute_alpha_l0_per_section(mock_wing, mock_op)

    def test_chord_exception_falls_back_to_default(self):
        """When xs.chord raises on float(), chord defaults to 0.20 m."""
        xs = MagicMock()
        xs.xyz_le = [0.0, 0.0, 0.0]
        chord_mock = MagicMock()
        chord_mock.__float__ = MagicMock(side_effect=ValueError("bad chord"))
        xs.chord = chord_mock
        airfoil_mock = MagicMock()
        airfoil_mock.name = "naca0012"
        airfoil_mock.get_aero_from_neuralfoil = MagicMock(side_effect=RuntimeError("no nf"))
        xs.airfoil = airfoil_mock

        y_arr, alpha_l0_arr = self._run_helper([xs])
        assert y_arr.shape == (1,)
        assert alpha_l0_arr[0] == pytest.approx(0.0)

    def test_airfoil_access_exception_falls_back_to_zero(self):
        """When xs.airfoil raises, alpha_L0 falls back to 0°."""
        xs = MagicMock()
        xs.xyz_le = [0.0, 0.0, 0.0]
        xs.chord = 0.20

        def _bad_airfoil():
            raise AttributeError("no airfoil")

        type(xs).airfoil = property(lambda self: _bad_airfoil())

        y_arr, alpha_l0_arr = self._run_helper([xs])
        assert alpha_l0_arr[0] == pytest.approx(0.0)

    def test_neuralfoil_exception_falls_back_to_zero(self):
        """When get_aero_from_neuralfoil raises, alpha_L0 falls back to 0°."""
        xs = MagicMock()
        xs.xyz_le = [0.0, 0.25, 0.0]
        xs.chord = 0.20
        airfoil_mock = MagicMock()
        airfoil_mock.name = "naca2412"
        airfoil_mock.get_aero_from_neuralfoil = MagicMock(side_effect=RuntimeError("NF unavail"))
        xs.airfoil = airfoil_mock

        y_arr, alpha_l0_arr = self._run_helper([xs])
        assert alpha_l0_arr[0] == pytest.approx(0.0)

    def test_two_xsecs_same_airfoil_different_chord_both_computed(self):
        """Two xsecs with same airfoil name but different chords → different Re, both computed."""
        import numpy as np

        xs_root = MagicMock()
        xs_root.xyz_le = [0.0, 0.0, 0.0]
        xs_root.chord = 0.20
        airfoil_root = MagicMock()
        airfoil_root.name = "naca0012"
        airfoil_root.get_aero_from_neuralfoil = MagicMock(return_value={"CL": np.zeros(40)})
        xs_root.airfoil = airfoil_root

        xs_tip = MagicMock()
        xs_tip.xyz_le = [0.0, 0.5, 0.0]
        xs_tip.chord = 0.12
        airfoil_tip = MagicMock()
        airfoil_tip.name = "naca0012"
        airfoil_tip.get_aero_from_neuralfoil = MagicMock(return_value={"CL": np.zeros(40)})
        xs_tip.airfoil = airfoil_tip

        y_arr, alpha_l0_arr = self._run_helper([xs_root, xs_tip])
        assert y_arr.shape == (2,)
        assert alpha_l0_arr.shape == (2,)

    def test_velocity_fallback_when_op_velocity_none(self):
        """When op.velocity is None, helper falls back to 15.0 m/s default."""
        xs = MagicMock()
        xs.xyz_le = [0.0, 0.0, 0.0]
        xs.chord = 0.20
        airfoil_mock = MagicMock()
        airfoil_mock.name = "naca0012"
        airfoil_mock.get_aero_from_neuralfoil = MagicMock(side_effect=RuntimeError("no nf"))
        xs.airfoil = airfoil_mock

        # velocity=None → np.atleast_1d(None)[0] raises TypeError → safe default 15.0
        y_arr, alpha_l0_arr = self._run_helper([xs], op_velocity=None)
        assert y_arr.shape == (1,)


# ---------------------------------------------------------------------------
# Tests: compute_section_aoa — empty xsecs branch
# ---------------------------------------------------------------------------


class TestComputeSectionAoaEdgeCases:
    """Edge-case branches in compute_section_aoa."""

    def test_wing_no_xsecs_raises_validation_error(self):
        """Wing with 0 xsecs raises ValidationDomainError (line 318 guard).

        _compute_alpha_l0_per_section is mocked to return a non-empty array so
        the code reaches the len(xsecs) < 1 guard at line 317-318 rather than
        failing earlier in np.interp with empty data.
        """
        import numpy as np
        from app.core.exceptions import ValidationDomainError
        import importlib
        import app.services.section_aoa_service as svc

        # Wing with empty xsecs list
        wing = MagicMock()
        wing.name = "empty_wing"
        wing.xsecs = []

        airplane = MagicMock()
        airplane.wings = [wing]
        airplane.xyz_ref = [0.1, 0.0, 0.0]

        # LiftingLine returns 1 panel (so we get past the LL call)
        ll = MagicMock()
        ll.run = MagicMock()
        ll.vortex_centers = [[0.0, 0.25, 0.0]]
        ll.vortex_strengths = [0.3]
        ll.chords = [0.2]
        ll.get_velocity_at_points = MagicMock(return_value=np.array([[10.0, 0.0, 0.0]]))
        ll.local_forward_direction = [[-1.0, 0.0, 0.0]]
        ll.normal_directions = [[0.0, 0.0, 1.0]]

        mock_asb = MagicMock()
        mock_asb.Airplane = MagicMock(return_value=airplane)
        mock_asb.LiftingLine = MagicMock(return_value=ll)

        op = MagicMock()
        op.alpha = 4.0
        op.velocity = 15.0

        # Reload inside patch.dict so the module picks up the mocked asb,
        # then patch _compute_alpha_l0_per_section on the freshly reloaded module
        # so the len(xsecs) guard at line 317-318 is reached.
        with patch.dict("sys.modules", {"aerosandbox": mock_asb}):
            importlib.reload(svc)
            with patch.object(
                svc,
                "_compute_alpha_l0_per_section",
                return_value=(np.array([0.0, 0.5]), np.array([0.0, 0.0])),
            ):
                with pytest.raises(ValidationDomainError):
                    svc.compute_section_aoa(airplane, op, wing_name="empty_wing")


# ---------------------------------------------------------------------------
# Tests: get_section_aoa — TRIMMED OP from DB + fallback + control_deflections
# ---------------------------------------------------------------------------


class TestGetSectionAoaOPPaths:
    """Tests for OP-resolution branches not covered by TestGetSectionAoaService."""

    def _make_op_schema(self, has_deflections: bool = False):
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
            control_deflections={"elevator": 2.0} if has_deflections else None,
        )

    def test_trimmed_op_found_in_db_no_explicit_id(self):
        """When no explicit op id given but TRIMMED OP exists in DB, it is used."""
        import asyncio

        from app.services.section_aoa_service import get_section_aoa

        mock_plane_schema = MagicMock()
        mock_plane_schema.id = 1
        mock_plane_schema.total_mass_kg = 1.5

        op_schema = self._make_op_schema()
        mock_op_model = MagicMock()

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
            patch(
                "app.services.operating_point_resolver.operating_point_model_to_schema",
                return_value=op_schema,
            ),
            patch(
                "app.services.section_aoa_service.compute_section_aoa",
                mock_compute,
            ),
            patch.dict("sys.modules", {"aerosandbox": mock_asb}),
        ):
            mock_db = MagicMock()
            mock_aircraft_model = MagicMock()
            mock_aircraft_model.id = 7
            # First .first() → AeroplaneModel lookup; second .first() → TRIMMED OP found
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_aircraft_model,
                mock_op_model,
            ]

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

    def test_control_deflections_applied(self):
        """When op_schema has control_deflections, with_control_deflections is called."""
        import asyncio

        from app.services.section_aoa_service import get_section_aoa

        mock_plane_schema = MagicMock()
        mock_plane_schema.id = 1
        mock_plane_schema.total_mass_kg = 1.5

        op_schema_with_deflections = self._make_op_schema(has_deflections=True)

        mock_asb = MagicMock()
        mock_asb.Atmosphere = MagicMock(return_value=MagicMock())
        mock_asb.OperatingPoint = MagicMock(return_value=MagicMock())

        mock_compute = MagicMock(return_value=[])
        mock_airplane = _make_mock_airplane()

        with (
            patch(
                "app.services.section_aoa_service.get_aeroplane_schema_or_raise",
                return_value=mock_plane_schema,
            ),
            patch(
                "app.services.section_aoa_service.aeroplane_schema_to_asb_airplane_async",
                return_value=mock_airplane,
            ),
            patch(
                "app.services.section_aoa_service._resolve_level_flight_op",
                return_value=op_schema_with_deflections,
            ),
            patch(
                "app.services.section_aoa_service.compute_section_aoa",
                mock_compute,
            ),
            patch.dict("sys.modules", {"aerosandbox": mock_asb}),
        ):
            mock_db = MagicMock()
            mock_aircraft_model = MagicMock()
            mock_aircraft_model.id = 8
            # AeroplaneModel found, but no TRIMMED OP → falls back to _resolve_level_flight_op
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_aircraft_model,
                None,
            ]

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
        mock_airplane.with_control_deflections.assert_called_once_with({"elevator": 2.0})


# ---------------------------------------------------------------------------
# Tests: _resolve_level_flight_op
# ---------------------------------------------------------------------------


class TestResolveLevelFlightOp:
    """Tests for the AeroBuildup-based level-flight fallback."""

    def test_returns_op_schema_with_sensible_alpha(self):
        """_resolve_level_flight_op returns an OperatingPointSchema with valid alpha."""
        import numpy as np
        from app.schemas.aeroanalysisschema import OperatingPointSchema

        mock_plane_schema = MagicMock()
        mock_plane_schema.total_mass_kg = 1.5

        mock_wing = MagicMock()
        mock_wing.symmetric = True
        mock_wing.area = MagicMock(return_value=0.3)
        mock_airplane = MagicMock()
        mock_airplane.wings = [mock_wing]
        mock_airplane.xyz_ref = [0.1, 0.0, 0.0]

        mock_asb = MagicMock()
        mock_asb.Atmosphere = MagicMock(return_value=MagicMock())
        mock_asb.OperatingPoint = MagicMock(return_value=MagicMock())

        call_num = [0]

        def mock_run():
            call_num[0] += 1
            # Return increasing CL so brentq finds a crossing
            cl_val = -0.3 + call_num[0] * 0.1
            return {"CL": np.array([cl_val])}

        mock_abu_instance = MagicMock()
        mock_abu_instance.run = MagicMock(side_effect=mock_run)
        mock_asb.AeroBuildup = MagicMock(return_value=mock_abu_instance)

        with patch.dict("sys.modules", {"aerosandbox": mock_asb}):
            import importlib
            import app.services.section_aoa_service as svc

            importlib.reload(svc)
            result = svc._resolve_level_flight_op(mock_plane_schema, mock_airplane)

        assert isinstance(result, OperatingPointSchema)
        assert result.velocity == pytest.approx(15.0)
        assert -10.0 <= result.alpha <= 20.0

    def test_brentq_failure_uses_default_alpha(self):
        """When brentq cannot bracket a solution, alpha defaults to 4.0."""
        import numpy as np
        from app.schemas.aeroanalysisschema import OperatingPointSchema

        mock_plane_schema = MagicMock()
        mock_plane_schema.total_mass_kg = None  # triggers 1.5 default

        mock_wing = MagicMock()
        mock_wing.symmetric = False  # no symmetric wing → s_ref defaults to 0.3
        mock_airplane = MagicMock()
        mock_airplane.wings = [mock_wing]
        mock_airplane.xyz_ref = [0.1, 0.0, 0.0]

        mock_asb = MagicMock()
        mock_asb.Atmosphere = MagicMock(return_value=MagicMock())
        mock_asb.OperatingPoint = MagicMock(return_value=MagicMock())

        mock_abu_instance = MagicMock()
        mock_abu_instance.run = MagicMock(side_effect=RuntimeError("ASB failed"))
        mock_asb.AeroBuildup = MagicMock(return_value=mock_abu_instance)

        with patch.dict("sys.modules", {"aerosandbox": mock_asb}):
            import importlib
            import app.services.section_aoa_service as svc

            importlib.reload(svc)
            result = svc._resolve_level_flight_op(mock_plane_schema, mock_airplane)

        assert isinstance(result, OperatingPointSchema)
        assert result.alpha == pytest.approx(4.0)

    def test_no_symmetric_wing_uses_default_s_ref(self):
        """When no symmetric wing found, s_ref defaults to 0.3 and function completes."""
        import numpy as np
        from app.schemas.aeroanalysisschema import OperatingPointSchema

        mock_plane_schema = MagicMock()
        mock_plane_schema.total_mass_kg = 1.0

        mock_wing = MagicMock()
        mock_wing.symmetric = False
        mock_airplane = MagicMock()
        mock_airplane.wings = [mock_wing]
        mock_airplane.xyz_ref = [0.0, 0.0, 0.0]

        mock_asb = MagicMock()
        mock_asb.Atmosphere = MagicMock(return_value=MagicMock())
        mock_asb.OperatingPoint = MagicMock(return_value=MagicMock())
        mock_abu_instance = MagicMock()
        mock_abu_instance.run = MagicMock(side_effect=RuntimeError("no ASB"))
        mock_asb.AeroBuildup = MagicMock(return_value=mock_abu_instance)

        with patch.dict("sys.modules", {"aerosandbox": mock_asb}):
            import importlib
            import app.services.section_aoa_service as svc

            importlib.reload(svc)
            result = svc._resolve_level_flight_op(mock_plane_schema, mock_airplane)

        assert isinstance(result, OperatingPointSchema)


# ---------------------------------------------------------------------------
# Tests: endpoint — _raise_http and get_wing_section_aoa
# ---------------------------------------------------------------------------


class TestSectionAoaEndpoint:
    """Tests for the FastAPI endpoint module."""

    def test_raise_http_not_found(self):
        """_raise_http converts NotFoundError to HTTP 404."""
        from fastapi import HTTPException
        from app.api.v2.endpoints.section_aoa import _raise_http
        from app.core.exceptions import NotFoundError

        with pytest.raises(HTTPException) as exc_info:
            _raise_http(NotFoundError(message="plane not found"))
        assert exc_info.value.status_code == 404

    def test_raise_http_validation_domain_error(self):
        """_raise_http converts ValidationDomainError to HTTP 422."""
        from fastapi import HTTPException
        from app.api.v2.endpoints.section_aoa import _raise_http
        from app.core.exceptions import ValidationDomainError

        with pytest.raises(HTTPException) as exc_info:
            _raise_http(ValidationDomainError(message="wing not found"))
        assert exc_info.value.status_code == 422

    def test_raise_http_generic_service_exception(self):
        """_raise_http converts other ServiceException to HTTP 500."""
        from fastapi import HTTPException
        from app.api.v2.endpoints.section_aoa import _raise_http
        from app.core.exceptions import ServiceException

        class _OtherError(ServiceException):
            pass

        with pytest.raises(HTTPException) as exc_info:
            _raise_http(_OtherError(message="something broke"))
        assert exc_info.value.status_code == 500

    def test_endpoint_success_via_test_client(self, client_and_db):
        """GET /aeroplanes/{uuid}/wings/{name}/section-aoa returns 200 on success."""
        from app.tests.conftest import make_aeroplane
        from app.services.section_aoa_service import SectionAoaEntry

        client, SessionLocal = client_and_db

        db = SessionLocal()
        try:
            aeroplane = make_aeroplane(db, name="test-endpoint-plane")
            aeroplane_uuid = str(aeroplane.uuid)
        finally:
            db.close()

        mock_entries = [
            SectionAoaEntry(
                y_m=0.25,
                chord_m=0.18,
                cl=0.72,
                alpha_geometric_deg=5.5,
                alpha_effective_deg=3.1,
                induced_angle_deg=2.4,
            )
        ]

        # get_section_aoa is a local import inside the endpoint function body,
        # so we patch it at the source module where the function actually lives.
        with patch(
            "app.services.section_aoa_service.get_section_aoa",
            return_value=mock_entries,
        ):
            resp = client.get(f"/aeroplanes/{aeroplane_uuid}/wings/main_wing/section-aoa")

        assert resp.status_code == 200
        data = resp.json()
        assert data["wing_name"] == "main_wing"
        assert len(data["sections"]) == 1
        assert data["sections"][0]["cl"] == pytest.approx(0.72)

    def test_endpoint_not_found_returns_404(self, client_and_db):
        """GET section-aoa returns 404 when the service raises NotFoundError."""
        from app.core.exceptions import NotFoundError
        import uuid as uuid_mod

        client, _SessionLocal = client_and_db
        fake_uuid = str(uuid_mod.uuid4())

        with patch(
            "app.services.section_aoa_service.get_section_aoa",
            side_effect=NotFoundError(message="aeroplane not found"),
        ):
            resp = client.get(f"/aeroplanes/{fake_uuid}/wings/main_wing/section-aoa")

        assert resp.status_code == 404

    def test_endpoint_validation_error_returns_422(self, client_and_db):
        """GET section-aoa returns 422 when service raises ValidationDomainError."""
        from app.core.exceptions import ValidationDomainError
        import uuid as uuid_mod

        client, _SessionLocal = client_and_db
        fake_uuid = str(uuid_mod.uuid4())

        with patch(
            "app.services.section_aoa_service.get_section_aoa",
            side_effect=ValidationDomainError(message="wing not found"),
        ):
            resp = client.get(f"/aeroplanes/{fake_uuid}/wings/main_wing/section-aoa")

        assert resp.status_code == 422

    def test_endpoint_unexpected_exception_returns_500(self, client_and_db):
        """GET section-aoa returns 500 when service raises an unexpected exception."""
        import uuid as uuid_mod

        client, _SessionLocal = client_and_db
        fake_uuid = str(uuid_mod.uuid4())

        with patch(
            "app.services.section_aoa_service.get_section_aoa",
            side_effect=RuntimeError("unexpected failure"),
        ):
            resp = client.get(f"/aeroplanes/{fake_uuid}/wings/main_wing/section-aoa")

        assert resp.status_code == 500
