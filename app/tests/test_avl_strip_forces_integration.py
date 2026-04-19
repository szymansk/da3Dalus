"""Integration test for AVL strip-force extraction.

Requires the AVL binary at exports/avl and CadQuery.
"""
import pytest
from pathlib import Path

AVL_BINARY = Path(__file__).resolve().parents[2] / "exports" / "avl"
pytestmark = pytest.mark.slow


@pytest.fixture
def simple_airplane():
    import aerosandbox as asb
    return asb.Airplane(
        name="test_plane",
        wings=[
            asb.Wing(
                name="Main Wing",
                symmetric=True,
                xsecs=[
                    asb.WingXSec(xyz_le=[0, 0, 0], chord=0.3, airfoil=asb.Airfoil("naca0012")),
                    asb.WingXSec(xyz_le=[0.02, 0.5, 0], chord=0.2, airfoil=asb.Airfoil("naca0012")),
                ],
            )
        ],
    )


@pytest.fixture
def op_point():
    import aerosandbox as asb
    return asb.OperatingPoint(velocity=20, alpha=5)


class TestAVLWithStripForcesIntegration:
    def test_run_returns_strip_forces(self, simple_airplane, op_point):
        from app.services.avl_strip_forces import AVLWithStripForces

        avl = AVLWithStripForces(
            airplane=simple_airplane,
            op_point=op_point,
            avl_command=str(AVL_BINARY),
            timeout=15,
        )
        result = avl.run()

        # Standard AVL results still present
        assert "CL" in result
        assert "CD" in result
        assert result["CL"] > 0

        # Strip forces present
        assert "strip_forces" in result
        surfaces = result["strip_forces"]
        assert len(surfaces) >= 1

        # Check first surface
        surface = surfaces[0]
        assert surface["surface_name"] == "Main Wing"
        assert len(surface["strips"]) > 0

        # Check strip data is physically plausible
        for strip in surface["strips"]:
            assert strip["Chord"] > 0
            assert strip["cl"] > 0  # positive alpha -> positive lift
            assert -1 < strip["Yle"] < 1  # within wingspan

    def test_standard_results_match_parent(self, simple_airplane, op_point):
        """AVLWithStripForces must return the same base results as asb.AVL."""
        import aerosandbox as asb
        from app.services.avl_strip_forces import AVLWithStripForces

        parent_avl = asb.AVL(
            airplane=simple_airplane,
            op_point=op_point,
            avl_command=str(AVL_BINARY),
            timeout=15,
        )
        parent_result = parent_avl.run()

        child_avl = AVLWithStripForces(
            airplane=simple_airplane,
            op_point=op_point,
            avl_command=str(AVL_BINARY),
            timeout=15,
        )
        child_result = child_avl.run()

        # Key aerodynamic coefficients must match
        for key in ["CL", "CD", "Cm", "CLa", "Cma"]:
            assert child_result[key] == pytest.approx(parent_result[key], rel=1e-4), \
                f"{key}: {child_result[key]} != {parent_result[key]}"
