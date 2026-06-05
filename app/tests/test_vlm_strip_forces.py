"""gh-674: in-process VLM strip-force producer (AVL parity).

`compute_vlm_strip_forces` reconstructs AVL-equivalent per-strip force
distributions from an AeroSandbox VortexLatticeMethod solve, so the
Trefftz-Plane chart keeps working without an AVL subprocess.

Pure ASB (no AVL binary), so these run in the requires_aerosandbox tier
but need no external solver. Reconstruction is validated against the VLM's
own aggregate CL/CD.
"""

from __future__ import annotations

import pytest

asb = pytest.importorskip("aerosandbox", reason="aerosandbox not installed")

from app.schemas.strip_forces import StripForceEntry  # noqa: E402


def _airplane():
    main = asb.Wing(
        name="Main",
        symmetric=True,
        xsecs=[
            asb.WingXSec(xyz_le=[0, 0, 0], chord=0.25, airfoil=asb.Airfoil("naca2412")),
            asb.WingXSec(xyz_le=[0.05, 1.0, 0], chord=0.18, airfoil=asb.Airfoil("naca2412")),
        ],
    )
    htp = asb.Wing(
        name="HTP",
        symmetric=True,
        xsecs=[
            asb.WingXSec(xyz_le=[1.0, 0, 0], chord=0.12, airfoil=asb.Airfoil("naca0010")),
            asb.WingXSec(xyz_le=[1.05, 0.35, 0], chord=0.09, airfoil=asb.Airfoil("naca0010")),
        ],
    )
    return asb.Airplane(name="t", wings=[main, htp])


def _op():
    return asb.OperatingPoint(velocity=14.0, alpha=4.0)


@pytest.mark.requires_aerosandbox
class TestComputeVlmStripForces:
    def test_result_has_avl_compatible_shape(self):
        from app.services.vlm_strip_forces import compute_vlm_strip_forces

        result = compute_vlm_strip_forces(
            _airplane(), _op(), spanwise_resolution=8, chordwise_resolution=6
        )
        for key in ("Sref", "Cref", "Bref", "alpha", "beta", "mach", "strip_forces"):
            assert key in result, key
        assert result["alpha"] == pytest.approx(4.0)
        assert result["Sref"] > 0 and result["Cref"] > 0 and result["Bref"] > 0

    def test_one_surface_per_wing_named_after_the_wing(self):
        from app.services.vlm_strip_forces import compute_vlm_strip_forces

        result = compute_vlm_strip_forces(
            _airplane(), _op(), spanwise_resolution=8, chordwise_resolution=6
        )
        names = [s["surface_name"] for s in result["strip_forces"]]
        assert names == ["Main", "HTP"]
        for s in result["strip_forces"]:
            assert s["n_spanwise"] == len(s["strips"])
            assert s["n_chordwise"] == 6
            assert s["surface_area"] > 0

    def test_strips_validate_into_schema(self):
        from app.services.vlm_strip_forces import compute_vlm_strip_forces

        result = compute_vlm_strip_forces(
            _airplane(), _op(), spanwise_resolution=8, chordwise_resolution=6
        )
        for surface in result["strip_forces"]:
            for raw in surface["strips"]:
                entry = StripForceEntry.model_validate(raw)
                assert entry.chord > 0
                assert entry.area > 0
                # inviscid VLM → no viscous drag component
                assert entry.cdv == 0.0
                # induced angle and derived products are finite
                assert entry.ai == entry.ai  # not NaN
                assert entry.c_cl == pytest.approx(entry.chord * entry.cl, rel=1e-6)

    def test_reconstruction_matches_aggregate_cl(self):
        """Σ(cl·area)/Sref over strips must equal the VLM's own CL."""
        from app.services.vlm_strip_forces import compute_vlm_strip_forces

        result = compute_vlm_strip_forces(
            _airplane(), _op(), spanwise_resolution=10, chordwise_resolution=6
        )
        sref = result["Sref"]
        lift_area = sum(
            s["cl"] * s["Area"] for surf in result["strip_forces"] for s in surf["strips"]
        )
        cl_reconstructed = lift_area / sref
        assert cl_reconstructed == pytest.approx(result["CL"], abs=1e-3)
        # a cambered wing at +4° → clearly positive lift
        assert cl_reconstructed > 0.2
