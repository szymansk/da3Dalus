"""gh-1008: Unit tests for the pure spar-sizing service.

All tests run on the CI fast tier (no aerosandbox, no DB).
The spar-sizing service is pure — it operates only on floats.

Reference values are hand-computed from the kirch W-formula scan:
  - Rectangular:  W = b·h²/6  → b = 6·W/h²
  - Capped:       W = b(H³-h³)/(6H)  → h = (H³ - 6·H·W/b)^(1/3)
  - Rod:          W = d³/10  → d = (10·W)^(1/3)
  - Tube:         W = π(Da⁴-Di⁴)/(32·Da)  → Di = (Da⁴ - 32·W·Da/π)^(1/4)

Units: all mm for dimensions, mm³ for W.
"""

from __future__ import annotations

import math
from typing import Any

import pytest


# ---------------------------------------------------------------------------
# Section-modulus helpers
# ---------------------------------------------------------------------------


class TestSectionModulus:
    """section_modulus_* helpers — known inputs → known W (mm³)."""

    def test_rectangular_known_value(self):
        """b=20, h=40 → W = 20·40²/6 = 5333.33 mm³."""
        from app.services.spar_sizing import section_modulus_rectangular

        w = section_modulus_rectangular(b=20.0, h=40.0)
        assert w == pytest.approx(20.0 * 40.0**2 / 6.0, rel=1e-6)

    def test_capped_known_value(self):
        """b=20, H=40, h=35 → W = 20·(40³-35³)/(6·40)."""
        from app.services.spar_sizing import section_modulus_capped

        b, H, h = 20.0, 40.0, 35.0
        expected = b * (H**3 - h**3) / (6.0 * H)
        assert section_modulus_capped(b=b, H=H, h=h) == pytest.approx(expected, rel=1e-6)

    def test_rod_known_value(self):
        """d=30 → W = 30³/10 = 2700 mm³."""
        from app.services.spar_sizing import section_modulus_rod

        assert section_modulus_rod(d=30.0) == pytest.approx(30.0**3 / 10.0, rel=1e-6)

    def test_tube_known_value(self):
        """Da=30, Di=24 → W = π(30⁴-24⁴)/(32·30)."""
        from app.services.spar_sizing import section_modulus_tube

        Da, Di = 30.0, 24.0
        expected = math.pi * (Da**4 - Di**4) / (32.0 * Da)
        assert section_modulus_tube(Da=Da, Di=Di) == pytest.approx(expected, rel=1e-6)

    def test_tube_solid_limit(self):
        """Di=0 (solid rod) → W = π·Da³/32."""
        from app.services.spar_sizing import section_modulus_tube

        Da = 30.0
        # Solid: W = π·Da⁴/(32·Da) = π·Da³/32
        expected = math.pi * Da**3 / 32.0
        assert section_modulus_tube(Da=Da, Di=0.0) == pytest.approx(expected, rel=1e-6)


# ---------------------------------------------------------------------------
# required_section_modulus
# ---------------------------------------------------------------------------


class TestRequiredSectionModulus:
    """erf_W = M_design / sigma_allow, with proper unit conversion."""

    def test_basic(self):
        """M=1000 N·m, σ=100 MPa → erf_W = 1000·1000 / 100 = 10000 mm³."""
        from app.services.spar_sizing import required_section_modulus

        # M is in N·m → N·mm = *1000; σ_allow in N/mm² (MPa)
        # erf_W = M[N·m] * 1000 / σ[MPa] (mm³)
        w = required_section_modulus(m_design_Nm=1000.0, sigma_allow_mpa=100.0)
        assert w == pytest.approx(10_000.0, rel=1e-6)

    def test_zero_moment(self):
        from app.services.spar_sizing import required_section_modulus

        assert required_section_modulus(m_design_Nm=0.0, sigma_allow_mpa=100.0) == pytest.approx(
            0.0
        )

    def test_pine_values(self):
        """M=100 N·m, σ=39 MPa (Pine) → erf_W = 100·1000/39 ≈ 2564.1 mm³."""
        from app.services.spar_sizing import required_section_modulus

        w = required_section_modulus(m_design_Nm=100.0, sigma_allow_mpa=39.0)
        assert w == pytest.approx(100.0 * 1000.0 / 39.0, rel=1e-5)


# ---------------------------------------------------------------------------
# solve_dimension — Rectangular
# ---------------------------------------------------------------------------


class TestSolveDimensionRectangular:
    """h = outer, solve b = 6·erf_W / h²."""

    def test_rectangular_feasible(self):
        """erf_W=5000 mm³, outer=40 mm → b = 6·5000/1600 = 18.75 mm."""
        from app.services.spar_sizing import solve_dimension

        result = solve_dimension(shape="rectangular", erf_w=5000.0, outer_mm=40.0)
        assert result["feasible"] is True
        assert result["solved_mm"] == pytest.approx(6.0 * 5000.0 / 40.0**2, rel=1e-5)
        assert "cross_section_area_mm2" in result

    def test_rectangular_zero_erf_w(self):
        """Zero required W → b ≈ 0, feasible (no moment → no stress)."""
        from app.services.spar_sizing import solve_dimension

        result = solve_dimension(shape="rectangular", erf_w=0.0, outer_mm=30.0)
        assert result["feasible"] is True
        assert result["solved_mm"] == pytest.approx(0.0, abs=1e-9)

    def test_rectangular_cross_section_area(self):
        """Cross-section area = b × h."""
        from app.services.spar_sizing import solve_dimension

        erf_w = 6000.0
        outer = 40.0
        result = solve_dimension(shape="rectangular", erf_w=erf_w, outer_mm=outer)
        b = result["solved_mm"]
        expected_area = b * outer  # b × h
        assert result["cross_section_area_mm2"] == pytest.approx(expected_area, rel=1e-5)


# ---------------------------------------------------------------------------
# solve_dimension — Rod
# ---------------------------------------------------------------------------


class TestSolveDimensionRod:
    """d = (10·erf_W)^(1/3); feasible if d ≤ outer."""

    def test_rod_feasible(self):
        """erf_W=1000 mm³, outer=50 mm → d = (10·1000)^(1/3) = 21.54 mm ≤ 50 → feasible."""
        from app.services.spar_sizing import solve_dimension

        result = solve_dimension(shape="rod", erf_w=1000.0, outer_mm=50.0)
        expected_d = (10.0 * 1000.0) ** (1.0 / 3.0)
        assert result["feasible"] is True
        assert result["solved_mm"] == pytest.approx(expected_d, rel=1e-5)

    def test_rod_too_big(self):
        """erf_W=100000 mm³, outer=20 mm → d ≫ 20 → infeasible."""
        from app.services.spar_sizing import solve_dimension

        result = solve_dimension(shape="rod", erf_w=100_000.0, outer_mm=20.0)
        assert result["feasible"] is False
        assert result["infeasibility_reason"] is not None
        assert (
            "too big" in result["infeasibility_reason"].lower()
            or "rod" in result["infeasibility_reason"].lower()
        )

    def test_rod_exactly_at_limit(self):
        """d exactly == outer → feasible (edge case)."""
        from app.services.spar_sizing import solve_dimension

        outer = 30.0
        # erf_W = d³/10 = 30³/10 = 2700
        erf_w = outer**3 / 10.0
        result = solve_dimension(shape="rod", erf_w=erf_w, outer_mm=outer)
        assert result["feasible"] is True
        assert result["solved_mm"] == pytest.approx(outer, rel=1e-5)

    def test_rod_cross_section_area_feasible(self):
        """Area = π·d²/4 when feasible."""
        from app.services.spar_sizing import solve_dimension

        result = solve_dimension(shape="rod", erf_w=1000.0, outer_mm=50.0)
        d = result["solved_mm"]
        assert result["cross_section_area_mm2"] == pytest.approx(math.pi * d**2 / 4.0, rel=1e-5)


# ---------------------------------------------------------------------------
# solve_dimension — Tube
# ---------------------------------------------------------------------------


class TestSolveDimensionTube:
    """Da = outer; Di = (Da⁴ - 32·erf_W·Da/π)^(1/4); wall = (Da-Di)/2."""

    def test_tube_feasible(self):
        """Da=30, erf_W=1000 → Di and wall computed correctly."""
        from app.services.spar_sizing import solve_dimension

        Da = 30.0
        erf_w = 1000.0
        under_radical = Da**4 - 32.0 * erf_w * Da / math.pi
        Di_expected = under_radical ** (1.0 / 4.0)
        wall_expected = (Da - Di_expected) / 2.0

        result = solve_dimension(shape="tube", erf_w=erf_w, outer_mm=Da)
        assert result["feasible"] is True
        assert result["solved_mm"] == pytest.approx(wall_expected, rel=1e-5)
        assert result.get("inner_mm") == pytest.approx(Di_expected, rel=1e-5)

    def test_tube_solid_needed(self):
        """When 32·erf_W·Da/π >= Da⁴ → Di imaginary → solid needed."""
        from app.services.spar_sizing import solve_dimension

        # Tiny Da, huge erf_W
        result = solve_dimension(shape="tube", erf_w=1_000_000.0, outer_mm=10.0)
        assert result["feasible"] is False
        assert "solid" in result["infeasibility_reason"].lower()

    def test_tube_area_is_annular(self):
        """Area = π(Da²-Di²)/4."""
        from app.services.spar_sizing import solve_dimension

        Da = 40.0
        result = solve_dimension(shape="tube", erf_w=2000.0, outer_mm=Da)
        if result["feasible"]:
            Di = result["inner_mm"]
            expected = math.pi * (Da**2 - Di**2) / 4.0
            assert result["cross_section_area_mm2"] == pytest.approx(expected, rel=1e-5)


# ---------------------------------------------------------------------------
# solve_dimension — Capped
# ---------------------------------------------------------------------------


class TestSolveDimensionCapped:
    """H = outer; h = (H³ - 6·H·erf_W/b)^(1/3); gurt = (H-h)/2."""

    def test_capped_feasible(self):
        """H=40, b=20, erf_W=2000 → h = (64000 - 6·40·2000/20)^(1/3)."""
        from app.services.spar_sizing import solve_dimension

        H, b, erf_w = 40.0, 20.0, 2000.0
        inner = H**3 - 6.0 * H * erf_w / b
        h_expected = inner ** (1.0 / 3.0)
        gurt_expected = (H - h_expected) / 2.0

        result = solve_dimension(shape="capped", erf_w=erf_w, outer_mm=H, cap_width_mm=b)
        assert result["feasible"] is True
        assert result["solved_mm"] == pytest.approx(gurt_expected, rel=1e-4)

    def test_capped_infeasible(self):
        """When H³ < 6·H·erf_W/b → infeasible."""
        from app.services.spar_sizing import solve_dimension

        # H=10, b=5, erf_W=1000000 → H³=1000, 6·10·1000000/5=12000000 → infeasible
        result = solve_dimension(shape="capped", erf_w=1_000_000.0, outer_mm=10.0, cap_width_mm=5.0)
        assert result["feasible"] is False
        assert result["infeasibility_reason"] is not None

    def test_capped_requires_cap_width(self):
        """ValueError when cap_width_mm is None for capped shape."""
        from app.services.spar_sizing import solve_dimension

        with pytest.raises((ValueError, TypeError)):
            solve_dimension(shape="capped", erf_w=1000.0, outer_mm=40.0, cap_width_mm=None)

    def test_capped_cross_section_area(self):
        """Cross-section = b(H-h) + b·h is full rectangle minus inner rectangle.
        Actually: area = b·H - b·h = b·(H-h) for flanges only model.
        Spec §4 is W for upper+lower flanges of width b each.
        We use: area ≈ 2·b·gurt (two flanges).
        """
        from app.services.spar_sizing import solve_dimension

        H, b, erf_w = 40.0, 20.0, 2000.0
        result = solve_dimension(shape="capped", erf_w=erf_w, outer_mm=H, cap_width_mm=b)
        if result["feasible"]:
            gurt = result["solved_mm"]
            expected = 2.0 * b * gurt  # two flanges
            assert result["cross_section_area_mm2"] == pytest.approx(expected, rel=1e-4)


# ---------------------------------------------------------------------------
# compute_spar_sizing — integration test (pure, no DB/aero)
# ---------------------------------------------------------------------------


def _make_material_specs(
    density_kg_m3: float = 1600.0,
    allowable_bending_stress_mpa: float = 500.0,
    youngs_modulus_gpa: float = 120.0,
) -> dict[str, Any]:
    """Build a material specs dict using the REAL ComponentRead.specs keys."""
    return {
        "density_kg_m3": density_kg_m3,
        "allowable_bending_stress_mpa": allowable_bending_stress_mpa,
        "youngs_modulus_gpa": youngs_modulus_gpa,
    }


def _make_component_read(
    id: int = 1,
    name: str = "Carbon Fiber",
    density_kg_m3: float = 1600.0,
    allowable_bending_stress_mpa: float = 500.0,
) -> dict[str, Any]:
    """Minimal ComponentRead-compatible dict (real schema keys from app/schemas/component.py)."""
    return {
        "id": id,
        "name": name,
        "component_type": "material",
        "manufacturer": None,
        "description": None,
        "mass_g": None,
        "bbox_x_mm": None,
        "bbox_y_mm": None,
        "bbox_z_mm": None,
        "model_ref": None,
        "specs": _make_material_specs(density_kg_m3, allowable_bending_stress_mpa),
        "created_at": "2025-01-01T00:00:00",
        "updated_at": "2025-01-01T00:00:00",
    }


class TestComputeSparSizing:
    """Integration test for compute_spar_sizing — pure, no aero/DB deps."""

    def _make_stations(self) -> list[dict[str, Any]]:
        """Three stations: tip, mid, root — simplified for testing."""
        return [
            # Outboard (tip, low M)
            {"y_m": 2.0, "chord_m": 0.2, "bending_moment_Nm": 100.0},
            # Mid
            {"y_m": 1.0, "chord_m": 0.3, "bending_moment_Nm": 500.0},
            # Root
            {"y_m": 0.0, "chord_m": 0.4, "bending_moment_Nm": 1000.0},
        ]

    def test_tube_sizing_feasible(self):
        """Tube spar sizing with parameters that produce a feasible tube at root.

        Large chord (0.5 m, t/c=0.15 → outer=60 mm) + low moment (100 N·m) + CF
        ensures the tube is feasible: Da⁴ > 32·erf_W·Da/π.
        """
        from app.services.spar_sizing import compute_spar_sizing
        from app.schemas.spar_sizing import SparSizingParams

        params = SparSizingParams(
            material_id=1,
            shape="tube",
            safety_factor_j=1.5,
            packing_factor=0.8,
        )
        # Stations where tube IS feasible: large chord, low moment, thick profile
        stations = [
            {"y_m": 1.0, "chord_m": 0.4, "bending_moment_Nm": 50.0},  # outer=48 mm
            {"y_m": 0.0, "chord_m": 0.5, "bending_moment_Nm": 100.0},  # outer=60 mm
        ]
        tc_by_y = {1.0: 0.15, 0.0: 0.15}
        material_specs = _make_material_specs()  # CF σ=500
        material_name = "Carbon Fiber"
        g_limit = 3.0
        g_limit_fallback = False

        result = compute_spar_sizing(
            stations=stations,
            tc_by_y=tc_by_y,
            material_specs=material_specs,
            material_name=material_name,
            params=params,
            g_limit=g_limit,
            g_limit_fallback=g_limit_fallback,
            surface_name="main_wing",
        )

        assert result.shape == "tube"
        assert result.material_name == "Carbon Fiber"
        assert result.g_limit == pytest.approx(3.0)
        assert result.g_limit_fallback is False
        assert len(result.stations) == 2
        assert result.root_station.y_m == pytest.approx(0.0)
        assert result.root_station.m_design_Nm == pytest.approx(100.0 * 3.0 * 1.5)
        # Root station must be feasible with these parameters
        assert result.root_station.feasible is True
        # Mass should be positive (at least root station has area)
        assert result.spar_mass_half_kg > 0
        assert result.spar_mass_full_kg == pytest.approx(result.spar_mass_half_kg * 2.0, rel=1e-6)

    def test_rectangular_root_station(self):
        """Root station must produce the right required_W."""
        from app.services.spar_sizing import compute_spar_sizing
        from app.schemas.spar_sizing import SparSizingParams

        params = SparSizingParams(
            material_id=1,
            shape="rectangular",
            safety_factor_j=1.5,
            packing_factor=0.8,
        )
        stations = [{"y_m": 0.0, "chord_m": 0.5, "bending_moment_Nm": 2000.0}]
        tc_by_y = {0.0: 0.15}
        material_specs = _make_material_specs(
            density_kg_m3=500.0, allowable_bending_stress_mpa=39.0
        )

        result = compute_spar_sizing(
            stations=stations,
            tc_by_y=tc_by_y,
            material_specs=material_specs,
            material_name="Pine",
            params=params,
            g_limit=3.0,
            g_limit_fallback=False,
            surface_name="main_wing",
        )

        # M_design = 2000 · 3.0 · 1.5 = 9000 N·m
        # erf_W = 9000·1000 / 39 = 230769.2 mm³
        assert result.root_station.m_design_Nm == pytest.approx(9000.0, rel=1e-5)
        assert result.root_station.required_W_mm3 == pytest.approx(9000.0 * 1000.0 / 39.0, rel=1e-4)
        # outer = chord · tc · packing = 500 · 0.15 · 0.8 = 60 mm
        assert result.root_station.outer_mm == pytest.approx(60.0, rel=1e-5)

    def test_tc_fallback_applied_with_warning(self):
        """When tc_by_y doesn't contain a station y, t/c=0.12 fallback fires."""
        from app.services.spar_sizing import compute_spar_sizing
        from app.schemas.spar_sizing import SparSizingParams

        params = SparSizingParams(material_id=1, shape="rod")
        stations = [{"y_m": 1.5, "chord_m": 0.3, "bending_moment_Nm": 100.0}]
        # tc_by_y is empty → fallback
        result = compute_spar_sizing(
            stations=stations,
            tc_by_y={},
            material_specs=_make_material_specs(),
            material_name="CF",
            params=params,
            g_limit=4.0,
            g_limit_fallback=False,
            surface_name="main_wing",
        )

        assert result.stations[0].tc_fallback is True
        assert result.stations[0].tc_ratio == pytest.approx(0.12)
        assert result.tc_fallback_warning is not None
        assert (
            "1.5" in result.tc_fallback_warning or "fallback" in result.tc_fallback_warning.lower()
        )

    def test_g_limit_fallback_propagated(self):
        from app.services.spar_sizing import compute_spar_sizing
        from app.schemas.spar_sizing import SparSizingParams

        params = SparSizingParams(material_id=1, shape="rectangular")
        stations = [{"y_m": 0.0, "chord_m": 0.3, "bending_moment_Nm": 500.0}]
        result = compute_spar_sizing(
            stations=stations,
            tc_by_y={0.0: 0.12},
            material_specs=_make_material_specs(),
            material_name="CF",
            params=params,
            g_limit=3.0,
            g_limit_fallback=True,  # <-- fallback
            surface_name="main_wing",
        )
        assert result.g_limit_fallback is True

    def test_sigma_override_used_over_material(self):
        """When sigma_allow_mpa_override is set, it overrides material's value."""
        from app.services.spar_sizing import compute_spar_sizing
        from app.schemas.spar_sizing import SparSizingParams

        # Material has σ=500, but override is 200
        params = SparSizingParams(
            material_id=1,
            shape="rectangular",
            sigma_allow_mpa_override=200.0,
        )
        stations = [{"y_m": 0.0, "chord_m": 0.3, "bending_moment_Nm": 500.0}]
        result = compute_spar_sizing(
            stations=stations,
            tc_by_y={0.0: 0.12},
            material_specs=_make_material_specs(allowable_bending_stress_mpa=500.0),
            material_name="CF",
            params=params,
            g_limit=3.0,
            g_limit_fallback=False,
            surface_name="main_wing",
        )
        assert result.sigma_allow_mpa == pytest.approx(200.0)
        # erf_W at root with override
        m_design = 500.0 * 3.0 * 1.5
        expected_erf_w = m_design * 1000.0 / 200.0
        assert result.root_station.required_W_mm3 == pytest.approx(expected_erf_w, rel=1e-4)

    def test_uses_max_abs_bending_moment(self):
        """The service should handle |M| (absolute value used for M_design)."""
        from app.services.spar_sizing import compute_spar_sizing
        from app.schemas.spar_sizing import SparSizingParams

        params = SparSizingParams(material_id=1, shape="rectangular")
        # bending_moment_Nm is negative (port side convention)
        stations = [{"y_m": 0.0, "chord_m": 0.3, "bending_moment_Nm": -800.0}]
        result = compute_spar_sizing(
            stations=stations,
            tc_by_y={0.0: 0.12},
            material_specs=_make_material_specs(),
            material_name="CF",
            params=params,
            g_limit=3.0,
            g_limit_fallback=False,
            surface_name="main_wing",
        )
        # M_design must use |M|
        assert result.root_station.m_design_Nm == pytest.approx(abs(-800.0) * 3.0 * 1.5, rel=1e-5)


# ---------------------------------------------------------------------------
# spar_mass estimation
# ---------------------------------------------------------------------------


class TestSparMass:
    """spar_mass trapezoidal integration."""

    def test_constant_section_mass(self):
        """Uniform cross-section along span → mass = density · area · span."""
        from app.services.spar_sizing import spar_mass_half_kg

        # 3 stations equally spaced at y=0,1,2 m, area=100 mm² each
        ys = [2.0, 1.0, 0.0]  # outboard first (tip to root order matches stations list)
        areas = [100.0, 100.0, 100.0]  # mm²
        density = 1600.0  # kg/m³

        # span = 2 m, area = 100 mm² = 100e-6 m²
        # mass = density · area · span = 1600 · 100e-6 · 2 = 0.32 kg
        mass = spar_mass_half_kg(ys_m=ys, areas_mm2=areas, density_kg_m3=density)
        assert mass == pytest.approx(0.32, rel=1e-4)

    def test_tapered_section(self):
        """Two stations: tip area=50, root area=200, span=1 m → trapezoidal."""
        from app.services.spar_sizing import spar_mass_half_kg

        ys = [1.0, 0.0]
        areas = [50.0, 200.0]
        density = 1000.0

        # avg area = (50+200)/2 = 125 mm², span = 1 m, area in m² = 125e-6
        # mass = 1000 · 125e-6 · 1 = 0.125 kg
        mass = spar_mass_half_kg(ys_m=ys, areas_mm2=areas, density_kg_m3=density)
        assert mass == pytest.approx(0.125, rel=1e-4)

    def test_zero_span(self):
        """Single station → no span → mass = 0."""
        from app.services.spar_sizing import spar_mass_half_kg

        mass = spar_mass_half_kg(ys_m=[0.0], areas_mm2=[100.0], density_kg_m3=1600.0)
        assert mass == pytest.approx(0.0)
