"""Compare WingConfiguration code output against hand-computed H-matrix theory.

For each test configuration from test_wingconfig_roundtrip.py, we:
1. Build the WingConfiguration from the schema (the code path)
2. Compute expected LE positions + twists from the H-matrix formulas
   documented in docs/WingConfiguration.adoc
3. Compare the two — any mismatch means the code diverges from the theory

This pinpoints exactly where the roundtrip breaks:
- If forward (WingConfig → ASB) matches theory: the bug is in from_asb()
- If forward already diverges: the bug is in asb_wing() or get_wing_workplane()

Relates to GH #158.
"""

import math

import numpy as np
import pytest

asb_mod = pytest.importorskip("aerosandbox")
pytest.importorskip("cadquery")

from app.schemas.wing import Wing, Segment, Airfoil  # noqa: E402
from app.services.create_wing_configuration import create_wing_configuration  # noqa: E402
from app.converters.model_schema_converters import (  # noqa: E402
    wing_config_to_asb_wing_schema,
    asb_wing_schema_to_wing_config,
)

AIRFOIL = "naca0015"


# ═══════════════════════════════════════════════════════════════════
# H-matrix theory (from docs/WingConfiguration.adoc)
# ═══════════════════════════════════════════════════════════════════

def _T(x, y, z):
    return np.array([[1,0,0,x],[0,1,0,y],[0,0,1,z],[0,0,0,1]], dtype=float)

def _Rx(deg):
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return np.array([[1,0,0,0],[0,c,-s,0],[0,s,c,0],[0,0,0,1]], dtype=float)

def _Ry(deg):
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return np.array([[c,0,s,0],[0,1,0,0],[-s,0,c,0],[0,0,0,1]], dtype=float)


def compute_expected_xsecs(segments_params):
    """Compute expected LE positions and cumulative twists from decoupled H-matrix theory.

    Decoupled frame computation (GH #162):
        Position chain uses only R_x(cumulative_dihedral) to rotate
        [sweep, length, 0]. Twist (R_y) is accumulated separately
        and applied only as a local rotation at the end, NOT propagated
        into positions.

        xyz_le[0] = [0, 0, 0]  (origin)
        xyz_le[k] = sum_{i<k} R_x(gamma_accum_i) . [sweep_i, length_i, 0]

        where gamma_accum_i is the cumulative dihedral up to segment i's
        root airfoil.

    Each x_sec corresponds to one airfoil station:
        x_sec[0] = root airfoil of segment 0
        x_sec[i] = tip airfoil of segment i-1 = root airfoil of segment i

    Returns list of dicts: [{xyz_le: [x,y,z], twist: float, chord: float}, ...]
    """
    xsecs = []

    # x_sec 0: root airfoil of segment 0, always at origin
    seg0 = segments_params[0]
    gamma_accum = seg0["root_dihedral"]
    theta_accum = seg0["root_incidence"]

    xsecs.append({
        "xyz_le": np.array([0.0, 0.0, 0.0]),
        "twist": theta_accum,
        "chord": seg0["root_chord"],
    })

    xyz_le = np.zeros(3)

    for seg in segments_params:
        # Position offset: R_x(gamma_accum) . [sweep, length, 0]
        R_x_mat = np.array(_Rx(gamma_accum))[:3, :3]
        offset = R_x_mat @ np.array([seg["sweep"], seg["length"], 0.0])
        xyz_le = xyz_le + offset

        # Accumulate angles from tip airfoil
        gamma_accum += seg.get("tip_dihedral", 0)
        theta_accum += seg.get("tip_incidence", 0)

        xsecs.append({
            "xyz_le": xyz_le.copy(),
            "twist": theta_accum,
            "chord": seg["tip_chord"],
        })

    return xsecs


# ═══════════════════════════════════════════════════════════════════
# Helper: build Wing schema and extract code-computed ASB values
# ═══════════════════════════════════════════════════════════════════

def _seg_schema(
    root_airfoil=AIRFOIL, root_chord=200, root_incidence=0, root_dihedral=0,
    tip_airfoil=AIRFOIL, tip_chord=180, tip_incidence=0, tip_dihedral=0,
    length=100, sweep=0, interpolation_pts=101,
):
    return Segment(
        root_airfoil=Airfoil(
            airfoil=root_airfoil, chord=root_chord,
            dihedral_as_rotation_in_degrees=root_dihedral,
            incidence=root_incidence,
        ),
        tip_airfoil=Airfoil(
            airfoil=tip_airfoil, chord=tip_chord,
            dihedral_as_rotation_in_degrees=tip_dihedral,
            incidence=tip_incidence,
        ),
        length=length, sweep=sweep,
        number_interpolation_points=interpolation_pts,
    )


def _seg_params(
    root_chord=200, root_incidence=0, root_dihedral=0,
    tip_chord=180, tip_incidence=0, tip_dihedral=0,
    length=100, sweep=0, dihedral_translation=0,
):
    """Parameters dict for the H-matrix computation."""
    return {
        "root_chord": root_chord, "root_incidence": root_incidence,
        "root_dihedral": root_dihedral,
        "tip_chord": tip_chord, "tip_incidence": tip_incidence,
        "tip_dihedral": tip_dihedral,
        "length": length, "sweep": sweep,
        "dihedral_translation": dihedral_translation,
    }


def _build_and_compare(segments_schemas, segments_params, scale=0.001, tol_pos=0.05, tol_twist=0.01):
    """Build WingConfig from schema, compute ASB, compare against H-matrix theory.

    Returns (matches, details) where details is a list of per-xsec comparison results.
    """
    wing_data = Wing(nose_pnt=[0, 0, 0], symmetric=True, segments=segments_schemas)
    wc = create_wing_configuration(wing_data)
    asb_schema = wing_config_to_asb_wing_schema(wc, "test", scale=scale)

    expected = compute_expected_xsecs(segments_params)

    details = []
    all_match = True

    for i, (exp, actual_xs) in enumerate(zip(expected, asb_schema.x_secs, strict=False)):
        actual_le = actual_xs.xyz_le
        actual_twist = actual_xs.twist
        actual_chord = actual_xs.chord

        # Expected LE is in mm, actual is in meters (scaled by 0.001)
        exp_le_scaled = exp["xyz_le"] * scale

        le_match = np.allclose(exp_le_scaled, actual_le, atol=tol_pos * scale)
        twist_match = abs(exp["twist"] - actual_twist) < tol_twist
        chord_match = abs(exp["chord"] * scale - actual_chord) < tol_pos * scale

        detail = {
            "xsec": i,
            "expected_le_mm": exp["xyz_le"].tolist(),
            "actual_le_m": list(actual_le),
            "expected_twist": exp["twist"],
            "actual_twist": actual_twist,
            "expected_chord_mm": exp["chord"],
            "actual_chord_m": actual_chord,
            "le_match": le_match,
            "twist_match": twist_match,
            "chord_match": chord_match,
        }
        details.append(detail)

        if not (le_match and twist_match and chord_match):
            all_match = False

    return all_match, details


# ═══════════════════════════════════════════════════════════════════
# Tests: same configurations as test_wingconfig_roundtrip.py
# ═══════════════════════════════════════════════════════════════════


class TestForwardConversionVsTheory:
    """Compare WingConfig → ASB output against H-matrix theory.

    If these fail: the bug is in asb_wing() or get_wing_workplane().
    If these pass: the bug is in from_asb() (reverse direction).
    """

    def _run(self, schemas, params, label=""):
        ok, details = _build_and_compare(schemas, params)
        if not ok:
            lines = [f"\n{'='*60}", f"MISMATCH in forward conversion: {label}", f"{'='*60}"]
            for d in details:
                status = "OK" if (d["le_match"] and d["twist_match"] and d["chord_match"]) else "FAIL"
                lines.append(
                    f"  x_sec {d['xsec']}: {status}"
                    f"  LE expected(mm)={d['expected_le_mm']} actual(m)={d['actual_le_m']}"
                    f"  twist expected={d['expected_twist']:.3f} actual={d['actual_twist']:.3f}"
                )
            print("\n".join(lines))
        assert ok, f"Forward conversion mismatch for {label}"

    # ── Basic (from TestBasicRoundtrip) ──

    def test_single_segment_flat(self):
        self._run(
            [_seg_schema()],
            [_seg_params()],
            "single_segment_flat",
        )

    def test_two_segments_flat(self):
        self._run(
            [_seg_schema(root_chord=200, tip_chord=180, length=100),
             _seg_schema(root_chord=180, tip_chord=160, length=200)],
            [_seg_params(root_chord=200, tip_chord=180, length=100),
             _seg_params(root_chord=180, tip_chord=160, length=200)],
            "two_segments_flat",
        )

    def test_four_segments_flat(self):
        self._run(
            [_seg_schema(root_chord=200, tip_chord=180, length=50, sweep=3),
             _seg_schema(root_chord=180, tip_chord=160, length=200, sweep=5),
             _seg_schema(root_chord=160, tip_chord=120, length=200, sweep=8),
             _seg_schema(root_chord=120, tip_chord=60, length=100, sweep=12)],
            [_seg_params(root_chord=200, tip_chord=180, length=50, sweep=3),
             _seg_params(root_chord=180, tip_chord=160, length=200, sweep=5),
             _seg_params(root_chord=160, tip_chord=120, length=200, sweep=8),
             _seg_params(root_chord=120, tip_chord=60, length=100, sweep=12)],
            "four_segments_flat",
        )

    # ── Incidence (from TestIncidenceRoundtrip) ──

    def test_constant_incidence(self):
        self._run(
            [_seg_schema(root_incidence=2, tip_incidence=2, length=100),
             _seg_schema(root_incidence=2, tip_incidence=2, length=200)],
            [_seg_params(root_incidence=2, tip_incidence=2, length=100),
             _seg_params(root_incidence=2, tip_incidence=2, length=200)],
            "constant_incidence",
        )

    def test_washout_classic(self):
        self._run(
            [_seg_schema(root_incidence=3, tip_incidence=1, length=200),
             _seg_schema(root_incidence=1, tip_incidence=-1, length=200)],
            [_seg_params(root_incidence=3, tip_incidence=1, length=200),
             _seg_params(root_incidence=1, tip_incidence=-1, length=200)],
            "washout_classic",
        )

    def test_washin(self):
        self._run(
            [_seg_schema(root_incidence=-1.5, tip_incidence=0, length=100),
             _seg_schema(root_incidence=0, tip_incidence=1.5, length=200)],
            [_seg_params(root_incidence=-1.5, tip_incidence=0, length=100),
             _seg_params(root_incidence=0, tip_incidence=1.5, length=200)],
            "washin",
        )

    def test_root_incidence_tip_zero(self):
        self._run(
            [_seg_schema(root_incidence=-1.5, tip_incidence=0, length=50),
             _seg_schema(root_incidence=0, tip_incidence=0, length=200)],
            [_seg_params(root_incidence=-1.5, tip_incidence=0, length=50),
             _seg_params(root_incidence=0, tip_incidence=0, length=200)],
            "root_incidence_tip_zero",
        )

    def test_large_twist_range(self):
        self._run(
            [_seg_schema(root_incidence=8, tip_incidence=4, length=100),
             _seg_schema(root_incidence=4, tip_incidence=0, length=200),
             _seg_schema(root_incidence=0, tip_incidence=-5, length=200)],
            [_seg_params(root_incidence=8, tip_incidence=4, length=100),
             _seg_params(root_incidence=4, tip_incidence=0, length=200),
             _seg_params(root_incidence=0, tip_incidence=-5, length=200)],
            "large_twist_range",
        )

    def test_nonmonotone_twist(self):
        self._run(
            [_seg_schema(root_incidence=0, tip_incidence=2, length=100),
             _seg_schema(root_incidence=2, tip_incidence=4, length=200),
             _seg_schema(root_incidence=4, tip_incidence=1, length=200)],
            [_seg_params(root_incidence=0, tip_incidence=2, length=100),
             _seg_params(root_incidence=2, tip_incidence=4, length=200),
             _seg_params(root_incidence=4, tip_incidence=1, length=200)],
            "nonmonotone_twist",
        )

    def test_all_segments_different_incidence(self):
        self._run(
            [_seg_schema(root_incidence=3, tip_incidence=2, length=50),
             _seg_schema(root_incidence=2, tip_incidence=0, length=200),
             _seg_schema(root_incidence=0, tip_incidence=-2, length=200),
             _seg_schema(root_incidence=-2, tip_incidence=-4, length=100)],
            [_seg_params(root_incidence=3, tip_incidence=2, length=50),
             _seg_params(root_incidence=2, tip_incidence=0, length=200),
             _seg_params(root_incidence=0, tip_incidence=-2, length=200),
             _seg_params(root_incidence=-2, tip_incidence=-4, length=100)],
            "all_segments_different_incidence",
        )

    # ── Dihedral (from TestDihedralRoundtrip) ──

    def test_constant_dihedral(self):
        self._run(
            [_seg_schema(root_dihedral=3, tip_dihedral=3, length=200),
             _seg_schema(root_dihedral=3, tip_dihedral=3, length=200)],
            [_seg_params(root_dihedral=3, tip_dihedral=3, length=200),
             _seg_params(root_dihedral=3, tip_dihedral=3, length=200)],
            "constant_dihedral",
        )

    def test_dihedral_only_root_segment(self):
        self._run(
            [_seg_schema(root_dihedral=2, length=50),
             _seg_schema(length=200),
             _seg_schema(length=200)],
            [_seg_params(root_dihedral=2, length=50),
             _seg_params(length=200),
             _seg_params(length=200)],
            "dihedral_only_root_segment",
        )

    # ── Combined (from TestCombinedRoundtrip) ──

    def test_washin_with_dihedral_and_sweep(self):
        self._run(
            [_seg_schema(root_incidence=-1.5, tip_incidence=1, root_dihedral=3,
                         length=50, sweep=5, root_chord=200, tip_chord=180),
             _seg_schema(root_incidence=1, tip_incidence=0,
                         length=200, sweep=8, root_chord=180, tip_chord=140),
             _seg_schema(root_incidence=0, tip_incidence=-1,
                         length=200, sweep=12, root_chord=140, tip_chord=80)],
            [_seg_params(root_incidence=-1.5, tip_incidence=1, root_dihedral=3,
                         length=50, sweep=5, root_chord=200, tip_chord=180),
             _seg_params(root_incidence=1, tip_incidence=0,
                         length=200, sweep=8, root_chord=180, tip_chord=140),
             _seg_params(root_incidence=0, tip_incidence=-1,
                         length=200, sweep=12, root_chord=140, tip_chord=80)],
            "washin_with_dihedral_and_sweep",
        )

    def test_trapez_wing_full(self):
        self._run(
            [_seg_schema(root_airfoil="naca2424", root_chord=200, root_incidence=2,
                         tip_airfoil="naca2424", tip_chord=180, tip_incidence=1.5,
                         root_dihedral=2, length=50, sweep=3),
             _seg_schema(root_airfoil="naca2424", root_chord=180, root_incidence=1.5,
                         tip_airfoil="naca2424", tip_chord=160, tip_incidence=1,
                         length=200, sweep=5),
             _seg_schema(root_airfoil="naca2424", root_chord=160, root_incidence=1,
                         tip_airfoil="naca2424", tip_chord=120, tip_incidence=0,
                         length=200, sweep=8),
             _seg_schema(root_airfoil="naca2424", root_chord=120, root_incidence=0,
                         tip_airfoil="naca2424", tip_chord=60, tip_incidence=-1,
                         length=100, sweep=12)],
            [_seg_params(root_chord=200, root_incidence=2, tip_chord=180, tip_incidence=1.5,
                         root_dihedral=2, length=50, sweep=3),
             _seg_params(root_chord=180, root_incidence=1.5, tip_chord=160, tip_incidence=1,
                         length=200, sweep=5),
             _seg_params(root_chord=160, root_incidence=1, tip_chord=120, tip_incidence=0,
                         length=200, sweep=8),
             _seg_params(root_chord=120, root_incidence=0, tip_chord=60, tip_incidence=-1,
                         length=100, sweep=12)],
            "trapez_wing_full",
        )

    # ── Drift test: 6-segment wing ──

    def test_drift_6_segment_wing(self):
        schemas = [
            _seg_schema(root_chord=250, tip_chord=230, root_incidence=4, tip_incidence=3,
                        root_dihedral=3, length=80, sweep=5),
            _seg_schema(root_chord=230, tip_chord=200, root_incidence=3, tip_incidence=2,
                        length=400, sweep=10),
            _seg_schema(root_chord=200, tip_chord=170, root_incidence=2, tip_incidence=1,
                        length=500, sweep=15),
            _seg_schema(root_chord=170, tip_chord=130, root_incidence=1, tip_incidence=0,
                        length=500, sweep=20),
            _seg_schema(root_chord=130, tip_chord=90, root_incidence=0, tip_incidence=-1,
                        length=400, sweep=15),
            _seg_schema(root_chord=90, tip_chord=50, root_incidence=-1, tip_incidence=-3,
                        length=200, sweep=10),
        ]
        params = [
            _seg_params(root_chord=250, tip_chord=230, root_incidence=4, tip_incidence=3,
                        root_dihedral=3, length=80, sweep=5),
            _seg_params(root_chord=230, tip_chord=200, root_incidence=3, tip_incidence=2,
                        length=400, sweep=10),
            _seg_params(root_chord=200, tip_chord=170, root_incidence=2, tip_incidence=1,
                        length=500, sweep=15),
            _seg_params(root_chord=170, tip_chord=130, root_incidence=1, tip_incidence=0,
                        length=500, sweep=20),
            _seg_params(root_chord=130, tip_chord=90, root_incidence=0, tip_incidence=-1,
                        length=400, sweep=15),
            _seg_params(root_chord=90, tip_chord=50, root_incidence=-1, tip_incidence=-3,
                        length=200, sweep=10),
        ]
        self._run(schemas, params, "drift_6_segment_wing")

    # ── Drift test: 4-segment asymmetric ──

    def test_drift_asymmetric_4_segments(self):
        schemas = [
            _seg_schema(root_chord=300, tip_chord=260, root_incidence=-2, tip_incidence=3,
                        root_dihedral=5, length=150, sweep=8),
            _seg_schema(root_chord=260, tip_chord=200, root_incidence=3, tip_incidence=-1,
                        length=600, sweep=12),
            _seg_schema(root_chord=200, tip_chord=140, root_incidence=-1, tip_incidence=4,
                        length=600, sweep=18),
            _seg_schema(root_chord=140, tip_chord=60, root_incidence=4, tip_incidence=-3,
                        length=300, sweep=25),
        ]
        params = [
            _seg_params(root_chord=300, tip_chord=260, root_incidence=-2, tip_incidence=3,
                        root_dihedral=5, length=150, sweep=8),
            _seg_params(root_chord=260, tip_chord=200, root_incidence=3, tip_incidence=-1,
                        length=600, sweep=12),
            _seg_params(root_chord=200, tip_chord=140, root_incidence=-1, tip_incidence=4,
                        length=600, sweep=18),
            _seg_params(root_chord=140, tip_chord=60, root_incidence=4, tip_incidence=-3,
                        length=300, sweep=25),
        ]
        self._run(schemas, params, "drift_asymmetric_4_segments")
