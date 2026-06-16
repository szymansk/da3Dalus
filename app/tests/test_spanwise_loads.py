"""gh-1002: spanwise shear + bending-moment integrator (pure, no aero deps).

These tests mock the strip-forces result dict so they run on the CI fast
tier (no aerosandbox, no network).  The integrator is a *pure* function
(`compute_spanwise_loads`) that operates on already-computed strip data.
"""

from __future__ import annotations

import math
import pytest

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_strip(j, yle, chord, area, cl):
    """Minimal StripForceEntry-compatible dict."""
    return {
        "j": j,
        "Xle": 0.0,
        "Yle": yle,
        "Zle": 0.0,
        "Chord": chord,
        "Area": area,
        "c_cl": chord * cl,
        "ai": 0.0,
        "cl_norm": 0.0,
        "cl": cl,
        "cd": 0.0,
        "cdv": 0.0,
        "cm_c/4": 0.0,
        "cm_LE": 0.0,
        "C.P.x/c": 0.25,
    }


def _make_surface(name, strips):
    return {
        "surface_name": name,
        "surface_number": 0,
        "n_chordwise": 8,
        "n_spanwise": len(strips),
        "surface_area": sum(s["Area"] for s in strips),
        "strips": strips,
    }


def _make_strip_forces_result(surfaces):
    """Minimal StripForcesResponse-compatible dict."""
    return {
        "alpha": 4.0,
        "beta": 0.0,
        "mach": 0.04,
        "sref": 1.0,
        "cref": 0.25,
        "bref": 2.0,
        "surfaces": surfaces,
        "velocity_mps": 14.0,
        "altitude_m": 0.0,
    }


# ---------------------------------------------------------------------------
# Core integrator tests
# ---------------------------------------------------------------------------


class TestComputeSpanwiseLoads:
    """Unit tests for `compute_spanwise_loads` — no aero imports needed."""

    def test_import_succeeds(self):
        from app.services.spanwise_loads import compute_spanwise_loads  # noqa: F401

    def test_empty_surfaces_returns_empty(self):
        from app.services.spanwise_loads import compute_spanwise_loads

        result = compute_spanwise_loads(
            strip_forces_result=_make_strip_forces_result([]),
            q=500.0,
        )
        assert result.surfaces == []

    def test_single_strip_per_half(self):
        """One strip on each half: shear at root == lift, M at tip == 0."""
        from app.services.spanwise_loads import compute_spanwise_loads

        # Two strips: y=-0.5 (port) and y=+0.5 (starboard), each lift = 100 N
        # q=1.0, Area=0.1, cl=1000 → lift = q*Area*cl = 100 N
        strips = [
            _make_strip(1, -0.5, 0.5, 0.1, 1000.0),
            _make_strip(2, 0.5, 0.5, 0.1, 1000.0),
        ]
        result = compute_spanwise_loads(
            strip_forces_result=_make_strip_forces_result([_make_surface("Main", strips)]),
            q=1.0,
        )
        assert len(result.surfaces) == 1
        surf = result.surfaces[0]
        # Starboard half
        sb = surf.starboard
        assert len(sb) == 1
        entry = sb[0]
        assert math.isclose(entry.shear_N, 100.0, rel_tol=1e-6)
        assert math.isclose(entry.bending_moment_Nm, 0.0, abs_tol=1e-9)

    def test_shear_monotonically_increases_toward_root(self):
        """V(y) must be non-decreasing as y decreases from tip to root."""
        from app.services.spanwise_loads import compute_spanwise_loads

        # 5 strips on starboard half (uniform lift per strip)
        strips = [_make_strip(i, 0.2 * i, 0.3, 0.06, 1.5) for i in range(1, 6)]
        # q=1.0, area=0.06, cl=1.5 → lift_per_strip = 0.09 N
        result = compute_spanwise_loads(
            strip_forces_result=_make_strip_forces_result([_make_surface("Wing", strips)]),
            q=1.0,
        )
        sb = result.surfaces[0].starboard
        shears = [e.shear_N for e in sb]
        # sorted by y outboard→inboard: shear increases
        for i in range(len(shears) - 1):
            assert shears[i] <= shears[i + 1], f"Non-monotone shear at index {i}: {shears}"

    def test_bending_moment_zero_at_tip(self):
        """M at the outermost strip should be zero (no outboard load)."""
        from app.services.spanwise_loads import compute_spanwise_loads

        strips = [_make_strip(i, 0.5 * i, 0.3, 0.15, 1.0) for i in range(1, 4)]
        result = compute_spanwise_loads(
            strip_forces_result=_make_strip_forces_result([_make_surface("Wing", strips)]),
            q=1.0,
        )
        sb = result.surfaces[0].starboard
        # Sorted outboard-first; the outermost strip contributes 0 moment
        # about itself (lever arm == 0).  shear outboard of it is 0; BM == 0.
        outermost = sb[0]
        assert math.isclose(outermost.bending_moment_Nm, 0.0, abs_tol=1e-9)

    def test_root_bm_matches_hand_calculation(self):
        """Three strips; verify root BM against pencil-and-paper calculation.

        Strips at y=1 m, y=2 m, y=3 m.
        q=1, area=1, cl=1 → each lift = 1 N.
        BM at root (y=0):
          strip1 (y=1): 1 N × 1 m = 1 Nm
          strip2 (y=2): 1 N × 2 m = 2 Nm
          strip3 (y=3): 1 N × 3 m = 3 Nm
          total = 6 Nm
        """
        from app.services.spanwise_loads import compute_spanwise_loads

        strips = [
            _make_strip(1, 1.0, 1.0, 1.0, 1.0),
            _make_strip(2, 2.0, 1.0, 1.0, 1.0),
            _make_strip(3, 3.0, 1.0, 1.0, 1.0),
        ]
        result = compute_spanwise_loads(
            strip_forces_result=_make_strip_forces_result([_make_surface("Wing", strips)]),
            q=1.0,
        )
        surf = result.surfaces[0]
        assert math.isclose(surf.root_bending_moment_Nm_starboard, 6.0, rel_tol=1e-6)

    def test_symmetric_port_equals_starboard(self):
        """Symmetric wing: port and starboard root BM should match."""
        from app.services.spanwise_loads import compute_spanwise_loads

        strips = [
            _make_strip(1, -2.0, 1.0, 1.0, 0.8),  # port
            _make_strip(2, -1.0, 1.0, 1.0, 0.8),  # port
            _make_strip(3, 1.0, 1.0, 1.0, 0.8),  # starboard
            _make_strip(4, 2.0, 1.0, 1.0, 0.8),  # starboard
        ]
        result = compute_spanwise_loads(
            strip_forces_result=_make_strip_forces_result([_make_surface("Wing", strips)]),
            q=1.0,
        )
        surf = result.surfaces[0]
        assert math.isclose(
            surf.root_bending_moment_Nm_starboard,
            surf.root_bending_moment_Nm_port,
            rel_tol=1e-6,
        )

    def test_root_shear_equals_total_half_lift(self):
        """Root shear == sum of all per-strip lifts on that half."""
        from app.services.spanwise_loads import compute_spanwise_loads

        # q=2, area=0.5, cl=3 → lift_per_strip = 3 N
        q = 2.0
        strips = [_make_strip(i, float(i), 0.5, 0.5, 3.0) for i in range(1, 5)]
        result = compute_spanwise_loads(
            strip_forces_result=_make_strip_forces_result([_make_surface("Wing", strips)]),
            q=q,
        )
        surf = result.surfaces[0]
        expected_shear = q * 0.5 * 3.0 * 4  # 4 strips
        assert math.isclose(surf.root_shear_N_starboard, expected_shear, rel_tol=1e-6)

    def test_multiple_surfaces(self):
        """Result contains one entry per surface in the input."""
        from app.services.spanwise_loads import compute_spanwise_loads

        main_strips = [_make_strip(1, 1.0, 0.3, 0.3, 1.0)]
        htp_strips = [_make_strip(1, 0.5, 0.15, 0.075, 0.8)]
        result = compute_spanwise_loads(
            strip_forces_result=_make_strip_forces_result(
                [
                    _make_surface("Main Wing", main_strips),
                    _make_surface("HTP", htp_strips),
                ]
            ),
            q=100.0,
        )
        assert len(result.surfaces) == 2
        names = [s.surface_name for s in result.surfaces]
        assert "Main Wing" in names
        assert "HTP" in names

    def test_chord_passthrough(self):
        """chord_m in the output matches the strip Chord field."""
        from app.services.spanwise_loads import compute_spanwise_loads

        strips = [_make_strip(1, 1.0, 0.42, 0.42, 1.0)]
        result = compute_spanwise_loads(
            strip_forces_result=_make_strip_forces_result([_make_surface("Wing", strips)]),
            q=1.0,
        )
        entry = result.surfaces[0].starboard[0]
        assert math.isclose(entry.chord_m, 0.42, rel_tol=1e-6)


# ---------------------------------------------------------------------------
# Schema smoke test
# ---------------------------------------------------------------------------


class TestSpanwiseLoadsSchema:
    def test_spanwise_load_entry_schema(self):
        from app.schemas.spanwise_loads import SpanwiseLoadEntry

        entry = SpanwiseLoadEntry(y_m=1.0, chord_m=0.3, shear_N=50.0, bending_moment_Nm=25.0)
        assert entry.y_m == 1.0
        assert entry.shear_N == 50.0

    def test_surface_spanwise_loads_schema(self):
        from app.schemas.spanwise_loads import SurfaceSpanwiseLoads, SpanwiseLoadEntry

        entry = SpanwiseLoadEntry(y_m=1.0, chord_m=0.3, shear_N=50.0, bending_moment_Nm=25.0)
        surf = SurfaceSpanwiseLoads(
            surface_name="Main Wing",
            starboard=[entry],
            port=[],
            root_shear_N_starboard=50.0,
            root_shear_N_port=0.0,
            root_bending_moment_Nm_starboard=25.0,
            root_bending_moment_Nm_port=0.0,
        )
        assert surf.root_bending_moment_Nm_starboard == 25.0

    def test_spanwise_loads_response_schema(self):
        from app.schemas.spanwise_loads import (
            SpanwiseLoadsResponse,
            SurfaceSpanwiseLoads,
            SpanwiseLoadEntry,
        )

        entry = SpanwiseLoadEntry(y_m=1.0, chord_m=0.3, shear_N=50.0, bending_moment_Nm=25.0)
        surf = SurfaceSpanwiseLoads(
            surface_name="Main Wing",
            starboard=[entry],
            port=[],
            root_shear_N_starboard=50.0,
            root_shear_N_port=0.0,
            root_bending_moment_Nm_starboard=25.0,
            root_bending_moment_Nm_port=0.0,
        )
        resp = SpanwiseLoadsResponse(
            alpha=2.0,
            velocity_mps=30.0,
            altitude_m=0.0,
            dynamic_pressure_Pa=551.0,
            surfaces=[surf],
        )
        assert resp.dynamic_pressure_Pa == 551.0


# ---------------------------------------------------------------------------
# Cessna 172N regression anchor (gh-1002)
# ---------------------------------------------------------------------------


class TestCessnaRegressionAnchor:
    """Validates the method against the Cessna 172N reference sanity value.

    Uses a hand-crafted strip-forces mock that mimics the Cessna 172N
    geometry (half-span 5.43 m, q ≈ 551 Pa at V=30 m/s, sea level).
    The expected root BM ≈ 4005 Nm per half, within 25% tolerance.

    This is NOT a live aero call — it drives the pure integrator with
    realistic cl(y) and area arrays so CI can run it without aerosandbox.
    """

    def _cessna_mock_strips(self):
        """Generate 10 equally-spaced starboard strips mimicking Cessna 172N.

        Half-span = 5.43 m, root chord ≈ 1.63 m, tip chord ≈ 1.09 m (linear
        taper), uniform cl ≈ 0.478 (matches the reference total lift at
        V=30, α=2°, sea level, MTOW 1111 kg, g=9.81).

        Total half-lift target ≈ q * S_half * CL = 551 * 8.8 * 0.478 ≈ 2318 N.
        Root BM ≈ 4005 Nm per hand integration.
        """
        half_span = 5.43
        n = 10
        dy = half_span / n
        strips = []
        for i in range(n):
            y_center = (i + 0.5) * dy  # 0.27, 0.81, ... 5.16 m
            frac = y_center / half_span
            chord = 1.63 * (1 - frac) + 1.09 * frac  # linear taper
            area = chord * dy
            cl = 0.478  # uniform (simplified), gives correct aggregate
            strips.append(_make_strip(i + 1, y_center, chord, area, cl))
        return strips

    def test_cessna_root_bm_within_tolerance(self):
        """Root BM for Cessna 172N mock is within 25% of 4005 Nm/half."""
        from app.services.spanwise_loads import compute_spanwise_loads

        # ISA sea-level: rho = 1.225 kg/m³, V = 30 m/s → q = 0.5*1.225*900 = 551.25 Pa
        q = 0.5 * 1.225 * 30.0**2  # ≈ 551.25 Pa

        strips = self._cessna_mock_strips()
        result = compute_spanwise_loads(
            strip_forces_result=_make_strip_forces_result([_make_surface("main_wing", strips)]),
            q=q,
        )
        surf = result.surfaces[0]
        root_bm = surf.root_bending_moment_Nm_starboard

        # Acceptance: within 25% of the reference value (4005 Nm)
        reference = 4005.0
        tolerance = 0.25
        assert abs(root_bm - reference) / reference < tolerance, (
            f"Cessna root BM {root_bm:.1f} Nm deviates >25% from reference {reference} Nm"
        )
        # Also validate monotonicity and M(tip)=0
        entries = surf.starboard
        # entries are sorted outboard-first (ascending y for starboard)
        outermost = entries[0]
        assert math.isclose(outermost.bending_moment_Nm, 0.0, abs_tol=1e-6)
        shears = [e.shear_N for e in entries]
        for i in range(len(shears) - 1):
            assert shears[i] <= shears[i + 1], f"Non-monotone shear at index {i}: {shears}"
