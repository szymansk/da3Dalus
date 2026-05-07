"""Integration test for AVL strip-force extraction via AVLRunner.

Requires the AVL binary at exports/avl.
"""

import pytest
from pathlib import Path

AVL_BINARY = Path(__file__).resolve().parents[2] / "exports" / "avl"
pytestmark = pytest.mark.slow


def _build_avl_geometry_content(airplane) -> str:
    """Build AVL geometry file content from an asb.Airplane.

    Uses asb.AVL.write_avl() purely for geometry generation in integration
    tests. Production code uses our own builder (build_avl_geometry_file).
    """
    import tempfile
    import aerosandbox as asb

    op = asb.OperatingPoint(velocity=20, alpha=5)
    with tempfile.TemporaryDirectory() as tmpdir:
        avl = asb.AVL(airplane=airplane, op_point=op)
        avl_path = Path(tmpdir) / "airplane.avl"
        avl.write_avl(avl_path)
        return avl_path.read_text()


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


class TestAVLRunnerStripForcesIntegration:
    def test_run_returns_strip_forces(self, simple_airplane, op_point):
        from app.services.avl_runner import AVLRunner

        avl_content = _build_avl_geometry_content(simple_airplane)
        runner = AVLRunner(
            airplane=simple_airplane,
            op_point=op_point,
            xyz_ref=[0, 0, 0],
            avl_command=str(AVL_BINARY),
            timeout=15,
        )
        result = runner.run(
            avl_file_content=avl_content,
            include_strip_forces=True,
        )

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
        """AVLRunner must return equivalent base results to asb.AVL."""
        import aerosandbox as asb
        from app.services.avl_runner import AVLRunner

        parent_avl = asb.AVL(
            airplane=simple_airplane,
            op_point=op_point,
            avl_command=str(AVL_BINARY),
            timeout=15,
        )
        parent_result = parent_avl.run()

        avl_content = _build_avl_geometry_content(simple_airplane)
        runner = AVLRunner(
            airplane=simple_airplane,
            op_point=op_point,
            xyz_ref=[0, 0, 0],
            avl_command=str(AVL_BINARY),
            timeout=15,
        )
        runner_result = runner.run(avl_file_content=avl_content)

        # Key aerodynamic coefficients must match
        for key in ["CL", "CD", "Cm"]:
            assert runner_result[key] == pytest.approx(parent_result[key], rel=1e-4), (
                f"{key}: {runner_result[key]} != {parent_result[key]}"
            )

    def test_symmetric_airplane_produces_symmetric_strip_forces(self, op_point):
        """For a symmetric multi-wing airplane at beta=0, YDUP strip forces must match exactly."""
        import aerosandbox as asb
        from app.services.avl_runner import AVLRunner

        airplane = asb.Airplane(
            name="symmetric_test",
            wings=[
                asb.Wing(
                    name="main_wing",
                    symmetric=True,
                    xsecs=[
                        asb.WingXSec(xyz_le=[0, 0, 0], chord=0.3, airfoil=asb.Airfoil("naca2412")),
                        asb.WingXSec(
                            xyz_le=[0.02, 0.5, 0], chord=0.2, airfoil=asb.Airfoil("naca2412")
                        ),
                    ],
                ),
                asb.Wing(
                    name="v-tail",
                    symmetric=True,
                    xsecs=[
                        asb.WingXSec(
                            xyz_le=[0.4, 0, 0], chord=0.15, airfoil=asb.Airfoil("naca0012")
                        ),
                        asb.WingXSec(
                            xyz_le=[0.42, 0.15, 0.1], chord=0.1, airfoil=asb.Airfoil("naca0012")
                        ),
                    ],
                ),
            ],
        )

        avl_content = _build_avl_geometry_content(airplane)
        runner = AVLRunner(
            airplane=airplane,
            op_point=op_point,
            xyz_ref=[0, 0, 0],
            avl_command=str(AVL_BINARY),
            timeout=15,
        )
        surfaces = runner.run(
            avl_file_content=avl_content,
            include_strip_forces=True,
        )["strip_forces"]

        paired = {}
        for s in surfaces:
            base = s["surface_name"].replace(" (YDUP)", "")
            paired.setdefault(base, {})["ydup" if "(YDUP)" in s["surface_name"] else "orig"] = s

        for name, pair in paired.items():
            assert "orig" in pair and "ydup" in pair, f"{name}: missing YDUP pair"
            orig_strips = sorted(pair["orig"]["strips"], key=lambda s: s["Yle"])
            ydup_strips = sorted(pair["ydup"]["strips"], key=lambda s: abs(s["Yle"]))

            assert len(orig_strips) == len(ydup_strips), f"{name}: strip count mismatch"
            for o, y in zip(orig_strips, ydup_strips, strict=True):
                assert o["cl"] == pytest.approx(y["cl"], rel=1e-6), (
                    f"{name}: Cl asymmetry at y={o['Yle']}: {o['cl']} vs {y['cl']}"
                )

    def test_nonzero_beta_causes_asymmetry(self, simple_airplane):
        """Non-zero beta legitimately produces asymmetric strip forces."""
        import aerosandbox as asb
        from app.services.avl_runner import AVLRunner

        op_beta = asb.OperatingPoint(velocity=20, alpha=5, beta=2)
        avl_content = _build_avl_geometry_content(simple_airplane)

        runner = AVLRunner(
            airplane=simple_airplane,
            op_point=op_beta,
            xyz_ref=[0, 0, 0],
            avl_command=str(AVL_BINARY),
            timeout=15,
        )
        surfaces = runner.run(
            avl_file_content=avl_content,
            include_strip_forces=True,
        )["strip_forces"]

        orig = next(s for s in surfaces if "(YDUP)" not in s["surface_name"])
        ydup = next(s for s in surfaces if "(YDUP)" in s["surface_name"])
        orig_strips = sorted(orig["strips"], key=lambda s: s["Yle"])
        ydup_strips = sorted(ydup["strips"], key=lambda s: abs(s["Yle"]))

        max_cl_diff = max(
            abs(o["cl"] - y["cl"]) for o, y in zip(orig_strips, ydup_strips, strict=True)
        )
        assert max_cl_diff > 0.001, f"Expected asymmetry from beta=2, got max diff={max_cl_diff}"
