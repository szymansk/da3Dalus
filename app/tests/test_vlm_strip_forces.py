"""gh-674: in-process VLM strip-force producer (AVL parity).

`compute_vlm_strip_forces` reconstructs AVL-equivalent per-strip force
distributions from an AeroSandbox VortexLatticeMethod solve, so the
Trefftz-Plane chart keeps working without an AVL subprocess.

Pure ASB (no AVL binary), so these run in the requires_aerosandbox tier
but need no external solver. Reconstruction is validated against the VLM's
own aggregate CL/CD.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.schemas.strip_forces import StripForceEntry
from app.services.vlm_strip_forces import (
    _panels_per_segment,
    _strip_index_ranges,
    _wing_strip_counts,
    compute_vlm_strip_forces,
)

asb = pytest.importorskip("aerosandbox", reason="aerosandbox not installed")


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
            _airplane(), _op(), spanwise_panels=12, chordwise_resolution=6
        )
        for key in ("Sref", "Cref", "Bref", "alpha", "beta", "mach", "strip_forces"):
            assert key in result, key
        assert result["alpha"] == pytest.approx(4.0)
        assert result["Sref"] > 0 and result["Cref"] > 0 and result["Bref"] > 0

    def test_one_surface_per_wing_named_after_the_wing(self):
        from app.services.vlm_strip_forces import compute_vlm_strip_forces

        result = compute_vlm_strip_forces(
            _airplane(), _op(), spanwise_panels=12, chordwise_resolution=6
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
            _airplane(), _op(), spanwise_panels=12, chordwise_resolution=6
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
            _airplane(), _op(), spanwise_panels=14, chordwise_resolution=6
        )
        sref = result["Sref"]
        lift_area = sum(
            s["cl"] * s["Area"] for surf in result["strip_forces"] for s in surf["strips"]
        )
        cl_reconstructed = lift_area / sref
        assert cl_reconstructed == pytest.approx(result["CL"], abs=1e-3)
        # a cambered wing at +4° → clearly positive lift
        assert cl_reconstructed > 0.2

    def test_span_proportional_distribution_no_tiny_segment_overresolution(self):
        """gh-855: a tiny 5 cm segment must NOT get as many strips as a 95 cm one.

        Pre-fix the per-segment spanwise_resolution gave both segments equal
        panels (~19x density mismatch). After the remesh, strip widths are
        roughly uniform.
        """
        wing = asb.Wing(
            name="Main",
            symmetric=True,
            xsecs=[
                asb.WingXSec(xyz_le=[0, 0, 0], chord=0.25, airfoil=asb.Airfoil("naca2412")),
                asb.WingXSec(xyz_le=[0, 0.05, 0], chord=0.24, airfoil=asb.Airfoil("naca2412")),
                asb.WingXSec(xyz_le=[0.05, 1.0, 0], chord=0.16, airfoil=asb.Airfoil("naca2412")),
            ],
        )
        ap = asb.Airplane(name="t", wings=[wing])
        result = compute_vlm_strip_forces(ap, _op(), spanwise_panels=40)

        strips = result["strip_forces"][0]["strips"]
        right = sorted(s["Yle"] for s in strips if s["Yle"] > 0)
        tiny = [y for y in right if y < 0.05]
        big = [y for y in right if y >= 0.05]
        # the big segment (95 cm) gets many more strips than the tiny (5 cm) one
        assert len(big) > len(tiny) * 3
        # strip widths on the right half are roughly uniform (no 19x spikes)
        widths = np.diff([0.0, *right])
        assert widths.max() / widths.min() < 4.0


# ---------------------------------------------------------------------------
# Fast tier (no real solver): pure helpers + a mocked VLM solve so the module
# is covered by the PR-fast / SonarCloud new_coverage run (gh-674).
# ---------------------------------------------------------------------------


class TestStripIndexRanges:
    def test_splits_on_trailing_edge(self):
        te = np.array([0, 0, 1, 0, 1], dtype=bool)
        assert _strip_index_ranges(te) == [(0, 3), (3, 5)]

    def test_empty(self):
        assert _strip_index_ranges(np.array([], dtype=bool)) == []


class TestWingStripCounts:
    def _wing(self, n_xsecs: int, symmetric: bool):
        w = MagicMock()
        w.xsecs = [object()] * n_xsecs
        w.symmetric = symmetric
        return w

    def test_symmetric_doubles(self):
        ap = MagicMock()
        ap.wings = [self._wing(2, True), self._wing(3, False)]
        # 1 segment * 4 * 2 = 8 ; 2 segments * 4 * 1 = 8
        assert _wing_strip_counts(ap, spanwise_resolution=4) == [8, 8]


def _mock_xsec(y: float, chord: float, airfoil_name: str):
    xs = MagicMock()
    xs.xyz_le = np.array([0.0, y, 0.0])
    xs.chord = chord
    xs.twist = 0.0
    af = MagicMock()
    af.name = airfoil_name
    af.blend_with_another_airfoil.return_value = MagicMock()
    xs.airfoil = af
    xs.control_surfaces = []
    return xs


class TestRemeshMocked:
    """gh-855: exercise the remesh chain (_segment_spans → _panels_per_segment →
    _blend_xsec → remesh_uniform_density → _remesh_airplane) in the fast tier by
    patching the asb constructors, so the new code is covered without aerosandbox.
    """

    def test_remesh_airplane_builds_span_proportional_sections(self):
        from app.services.vlm_strip_forces import _remesh_airplane

        # tiny 5 cm segment (same airfoil → blend early-return branch) + big 95 cm
        # segment (different airfoil → blend call branch)
        xsecs = [
            _mock_xsec(0.0, 0.25, "A"),
            _mock_xsec(0.05, 0.24, "A"),
            _mock_xsec(1.0, 0.16, "B"),
        ]
        wing = MagicMock()
        wing.xsecs = xsecs
        wing.symmetric = True
        wing.name = "Main"
        ap = MagicMock()
        ap.wings = [wing]
        ap.name = "t"
        ap.xyz_ref = [0.0, 0.0, 0.0]
        ap.s_ref = 1.0
        ap.b_ref = 2.0
        ap.c_ref = 0.2
        ap.fuselages = []

        with (
            patch("aerosandbox.WingXSec", side_effect=lambda **kw: ("xsec", kw)) as m_xsec,
            patch("aerosandbox.Wing", side_effect=lambda **kw: ("wing", kw)) as m_wing,
            patch("aerosandbox.Airplane", side_effect=lambda **kw: ("airplane", kw)) as m_ap,
        ):
            out = _remesh_airplane(ap, budget=40, min_per_segment=2)

        # budget 40 over spans [0.05, 0.95] → 2 + 38 inserted sections
        assert m_xsec.call_count == 40
        assert m_wing.call_count == 1
        assert m_ap.call_count == 1
        assert out[0] == "airplane"
        # the different-airfoil (big) segment triggered real blending
        assert xsecs[1].airfoil.blend_with_another_airfoil.called


class TestPanelsPerSegment:
    """gh-855: spanwise panels are distributed ∝ segment span, ≥ min each."""

    def test_proportional_to_span(self):
        # tiny 0.05 m segment + big 0.95 m segment, budget 40 → 2 vs 38
        counts = _panels_per_segment([0.05, 0.95], budget=40, min_per_segment=2)
        assert counts == [2, 38]
        assert sum(counts) == 40

    def test_min_floor_protects_tiny_segments(self):
        # a 1 mm sliver next to a 1 m segment still gets the floor, not 0
        counts = _panels_per_segment([0.001, 1.0], budget=20, min_per_segment=2)
        assert counts[0] == 2
        assert counts[1] >= 2

    def test_equal_segments_split_evenly(self):
        assert _panels_per_segment([0.5, 0.5], budget=20, min_per_segment=1) == [10, 10]

    def test_empty_and_degenerate(self):
        assert _panels_per_segment([], budget=10, min_per_segment=2) == []
        # zero total span → every segment gets the floor
        assert _panels_per_segment([0.0, 0.0], budget=10, min_per_segment=2) == [2, 2]


def _fake_vlm():
    vlm = MagicMock()
    vlm.is_trailing_edge = np.array([0, 1, 0, 1], dtype=bool)
    vlm.areas = np.array([0.1, 0.1, 0.1, 0.1])
    vlm.forces_geometry = np.array([[0.0, 0.0, 1.0]] * 4)
    vlm.steady_freestream_direction = np.array([1.0, 0.0, 0.0])
    # only LE-of-strip (first panel) and TE-of-strip (last panel) vertices are read
    vlm.front_left_vertices = np.array(
        [[0, 0, 0], [0, 0, 0], [0, 0.5, 0], [0, 0.5, 0]], dtype=float
    )
    vlm.front_right_vertices = np.array(
        [[0, 0.5, 0], [0, 0.5, 0], [0, 1.0, 0], [0, 1.0, 0]], dtype=float
    )
    vlm.back_left_vertices = np.array(
        [[0.2, 0, 0], [0.2, 0, 0], [0.2, 0.5, 0], [0.2, 0.5, 0]], dtype=float
    )
    vlm.back_right_vertices = np.array(
        [[0.2, 0.5, 0], [0.2, 0.5, 0], [0.2, 1.0, 0], [0.2, 1.0, 0]], dtype=float
    )
    vlm.run.return_value = {"CL": 0.04, "CD": 0.0}
    return vlm


def _fake_airplane(wing_name="Main", n_xsecs=2, symmetric=False, ap_name="t"):
    wing = MagicMock()
    wing.xsecs = [object()] * n_xsecs
    wing.symmetric = symmetric
    wing.name = wing_name
    ap = MagicMock()
    ap.wings = [wing]
    ap.s_ref = 1.0
    ap.c_ref = 0.2
    ap.b_ref = 1.0
    ap.name = ap_name
    return ap


def _fake_op():
    op = MagicMock()
    op.dynamic_pressure.return_value = 100.0
    op.alpha = 0.0
    op.beta = 0.0
    op.mach.return_value = 0.0
    return op


class TestComputeVlmStripForcesMocked:
    """Exercises compute_vlm_strip_forces without a real solve (fast tier).

    The span-proportional remesh (gh-855) needs real asb geometry, so it is
    patched out here; the strip-walk + surface attribution is what we cover.
    """

    def test_builds_surface_and_strips(self):
        # 3 xsecs → 2 segments → spanwise_resolution=1 → 2 strips, matching the mock.
        fake = _fake_airplane(n_xsecs=3, symmetric=False)
        with (
            patch("aerosandbox.VortexLatticeMethod", return_value=_fake_vlm()),
            patch("app.services.vlm_strip_forces._remesh_airplane", return_value=fake),
        ):
            result = compute_vlm_strip_forces(fake, _fake_op(), chordwise_resolution=2)
        assert result["CL"] == 0.04
        assert result["alpha"] == 0.0
        assert len(result["strip_forces"]) == 1
        surface = result["strip_forces"][0]
        assert surface["surface_name"] == "Main"
        assert surface["n_spanwise"] == 2
        assert surface["n_chordwise"] == 2
        for raw in surface["strips"]:
            entry = StripForceEntry.model_validate(raw)
            assert entry.chord == pytest.approx(0.2)
            assert entry.cl == pytest.approx(0.1)  # lift 2 / (q 100 · area 0.2)
            assert entry.cdv == 0.0
            assert entry.ai == pytest.approx(0.0)

    def test_count_mismatch_falls_back_to_single_surface(self):
        # 2 xsecs → 1 segment → expected 1 strip, but the mock yields 2 →
        # the guard collapses everything into one aggregate surface.
        fake = _fake_airplane(n_xsecs=2, symmetric=False, ap_name="Romulus")
        with (
            patch("aerosandbox.VortexLatticeMethod", return_value=_fake_vlm()),
            patch("app.services.vlm_strip_forces._remesh_airplane", return_value=fake),
        ):
            result = compute_vlm_strip_forces(fake, _fake_op(), chordwise_resolution=2)
        assert len(result["strip_forces"]) == 1
        assert result["strip_forces"][0]["surface_name"] == "Romulus"
        assert result["strip_forces"][0]["n_spanwise"] == 2


class TestAnalyzeAirplaneStripForcesVlmDefault:
    """The service defaults to the VLM path (gh-674); mock the solve + DB so
    the default branch + 'ASB' provenance are covered in the fast tier."""

    def test_default_solver_uses_vlm_and_tags_asb(self):
        import asyncio
        from contextlib import ExitStack

        from app.schemas.aeroanalysisschema import OperatingPointSchema
        from app.services import analysis_service

        vlm_result = {
            "Sref": 1.0,
            "Cref": 0.2,
            "Bref": 2.0,
            "alpha": 3.0,
            "beta": 0.0,
            "mach": 0.0,
            "CL": 0.4,
            "CD": 0.01,
            "strip_forces": [
                {
                    "surface_name": "Main",
                    "surface_number": 0,
                    "n_chordwise": 8,
                    "n_spanwise": 1,
                    "surface_area": 0.5,
                    "strips": [
                        {
                            "j": 1,
                            "Xle": 0.0,
                            "Yle": 0.1,
                            "Zle": 0.0,
                            "Chord": 0.2,
                            "Area": 0.5,
                            "c_cl": 0.08,
                            "ai": 1.2,
                            "cl_norm": 0.4,
                            "cl": 0.4,
                            "cd": 0.01,
                            "cdv": 0.0,
                            "cm_c/4": 0.0,
                            "cm_LE": 0.0,
                            "C.P.x/c": 0.25,
                        }
                    ],
                }
            ],
        }
        resolved = OperatingPointSchema(alpha=3.0, velocity=14.0, altitude=0.0, xyz_ref=[0.1, 0, 0])
        aircraft = MagicMock(id=3)
        aircraft.name = "Falcon"

        with ExitStack() as stack:
            stack.enter_context(
                patch.object(analysis_service, "get_aeroplane_or_raise", return_value=aircraft)
            )
            stack.enter_context(
                patch.object(
                    analysis_service, "get_aeroplane_schema_or_raise", return_value=MagicMock()
                )
            )
            stack.enter_context(
                patch.object(
                    analysis_service,
                    "aeroplane_schema_to_asb_airplane_async",
                    return_value=MagicMock(),
                )
            )
            stack.enter_context(
                patch.object(
                    analysis_service.operating_point_resolver,
                    "resolve_operating_point",
                    return_value=resolved,
                )
            )
            mock_vlm = stack.enter_context(
                patch(
                    "app.services.vlm_strip_forces.compute_vlm_strip_forces",
                    return_value=vlm_result,
                )
            )
            response = asyncio.run(
                analysis_service.analyze_airplane_strip_forces(
                    MagicMock(), aeroplane_uuid="0" * 36, operating_point=OperatingPointSchema()
                )
            )

        mock_vlm.assert_called_once()
        assert response.aero_model == "ASB"
        assert response.wing_name == "Falcon"
        assert len(response.surfaces) == 1
        assert response.surfaces[0].strips[0].cl == pytest.approx(0.4)
