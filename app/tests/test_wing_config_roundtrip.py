"""
Roundtrip harness for ``WingConfiguration -> asb.Wing -> from_asb`` fidelity.

Builds a ``WingConfiguration`` in *relative* mode, transforms it to an
``asb.Wing`` via ``WingConfiguration.asb_wing()``, and then rebuilds a
``WingConfiguration`` from the resulting ``xsecs`` via
``WingConfiguration.from_asb()``. The three comparison helpers in
``cad_designer/aerosandbox/wing_roundtrip.py`` then quantify the drift
on three levels:

1. Per-field parameter equality (strict)
2. Per-segment workplane-origin equality in global space (strict)
3. Rendered-shape volume / surface / centroid equality (tolerant)

The user has specified that levels 1 and 2 must be *exact* for
``nose_pnt``, ``incidence``, ``sweep``, ``dihedral_as_rotation_in_degrees``
and ``dihedral_as_translation``. Airfoil-thickness drift from chord
rotation is tolerated at level 3 and will be addressed separately via
an ``Airfoil.chord_stretch_factor`` in Phase 4.

This test is intentionally **marked slow** and only runs on CI when the
slow workflow is dispatched. The comparison helpers are platform-
guarded: the module skips if cadquery or aerosandbox are unavailable
(e.g. on linux/aarch64 where both are excluded).
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.slow,
    pytest.mark.requires_cadquery,
    pytest.mark.requires_aerosandbox,
]

# Hard skip at collection time if the platform-excluded deps are missing.
# (The `requires_*` markers filter at select time, but we also need the
# imports below to succeed during collection.)
cq = pytest.importorskip("cadquery")
asb = pytest.importorskip("aerosandbox")

from cad_designer.aerosandbox.wing_roundtrip import (  # noqa: E402
    compare_segment_origins,
    compare_wing_configs,
    compare_wing_shapes,
    render_wing_loft_to_step,
)
from cad_designer.aerosandbox.wing_roundtrip_cases import (  # noqa: E402
    CASE_FACTORIES,
    get_factory,
)
from cad_designer.airplane.aircraft_topology.wing.WingConfiguration import (  # noqa: E402
    WingConfiguration,
)


# --------------------------------------------------------------------------- #
# Parametrized fixture wiring
# --------------------------------------------------------------------------- #


# Parameter- and origin-tolerance per case. The factories themselves live
# in ``cad_designer/aerosandbox/wing_roundtrip_cases.py`` so that the CLI
# STEP exporter (``python -m cad_designer.aerosandbox.wing_roundtrip``)
# and this pytest harness consume the same inputs.
#
# tol defaults to float-noise levels — see the baseline notes in beads
# issue cad-modelling-service-7kq for calibration rationale.
PARAM_TOL: dict[str, tuple[float, float]] = {
    case_id: (1e-9, 1e-6) for case_id, _ in CASE_FACTORIES
}


@pytest.fixture(
    params=CASE_FACTORIES,
    ids=[c[0] for c in CASE_FACTORIES],
)
def roundtrip_case(request):
    """Yields (case_id, expected_wc, actual_wc, param_tol, origin_tol).

    ``expected_wc`` is freshly built from the factory and never touched
    by ``asb_wing()``. ``actual_wc`` is the result of
    ``from_asb(expected.asb_wing().xsecs)`` — i.e. the roundtripped
    configuration we want to compare against the baseline.
    """
    case_id, factory = request.param
    param_tol, origin_tol = PARAM_TOL[case_id]

    # Build twice so asb_wing() caching on the baseline never leaks
    # the reconstructed xsecs back into the "expected" side.
    expected_wc = factory()
    source_wc = factory()

    asb_wing = source_wc.asb_wing()
    actual_wc = WingConfiguration.from_asb(
        asb_wing.xsecs,
        symmetric=expected_wc.symmetric,
    )

    yield case_id, expected_wc, actual_wc, param_tol, origin_tol


# --------------------------------------------------------------------------- #
# Level 1: parameter-strict
# --------------------------------------------------------------------------- #


def test_parameters_strict(roundtrip_case):
    """All user-declared "must match exactly" parameters survive the roundtrip.

    Drives bugs 1-4 in ``WingConfiguration.from_asb`` (rotation_point,
    dihedral sign, parameter-mode, and dihedral case-split). Expected
    to fail pre-fix on every non-trivial case; that failure *is* the
    baseline signal we need for Phase 2.
    """
    case_id, expected, actual, param_tol, _ = roundtrip_case
    result = compare_wing_configs(expected, actual, tol=param_tol)
    assert result.ok, f"[{case_id}] parameter drift:\n{result}"


# --------------------------------------------------------------------------- #
# Level 2: segment-origin-strict
# --------------------------------------------------------------------------- #


def test_segment_origins_strict(roundtrip_case):
    """Per-segment workplane origins match exactly in global space.

    This is the "nose point der Segmente" requirement from the user.
    Because it chains the accumulated homogeneous transforms, a clean
    Level-1 pass is not sufficient — bugs in the transformation matrix
    or in get_wing_workplane() show up here.
    """
    case_id, expected, actual, _, origin_tol = roundtrip_case
    result = compare_segment_origins(expected, actual, tol=origin_tol)
    assert result.ok, (
        f"[{case_id}] segment origin drift, max_distance={result.max_distance}:\n"
        + "\n".join(
            f"  segment[{d.segment_index}] expected={d.expected} "
            f"actual={d.actual} dist={d.distance}"
            for d in result.diffs
        )
    )


# --------------------------------------------------------------------------- #
# Level 3: shape-tolerant (rendered CAD comparison)
# --------------------------------------------------------------------------- #


# Toleranzen werden nach der Baseline-Messung in Phase 2 kalibriert.
# Initial sehr grosszuegig, damit wir die *gemessenen* Werte sehen statt
# in eine fixe Zahl zu rennen. Volumen und Oberflaeche in Prozent; Centroid
# in mm (wing_config units).
# Strict (1e-3) Toleranz für alle Cases, die den asb-kompatiblen
# Parameter-Subraum verwenden (rc beliebig, dihedral_as_translation
# statt dihedral_as_rotation_in_degrees). Der ehawk_main_wing Case
# kommt aus ``test/ehawk_workflow_helpers._build_main_wing`` und setzt
# ``dihedral_as_rotation_in_degrees=1`` auf dem Root-Airfoil — eine
# Bank-Rotation, die aerosandbox nicht darstellen kann (asb leitet
# dihedral ausschließlich aus der yg_local-Richtung zwischen LE-
# Positionen ab). Das Residuum von ~2% volume / 1% surface ist die
# heutige Obergrenze für "real-world Wing mit latentem
# dihedral_as_rotation_in_degrees". Ein vollständiger Fix bräuchte
# cumulative-rotation tracking in ``from_asb`` + koordinierte R_x-
# Rotationen pro Segment — siehe Follow-up Issue auf
# cad-modelling-service-121.
SHAPE_TOL = {
    "single_segment_flat": dict(vol_rel=1e-3, surf_rel=1e-3, centroid_mm=1e-2),
    "single_segment_with_nose_pnt": dict(vol_rel=1e-3, surf_rel=1e-3, centroid_mm=1e-2),
    "single_segment_with_dihedral": dict(vol_rel=1e-3, surf_rel=1e-3, centroid_mm=1e-2),
    "single_segment_with_twist": dict(vol_rel=1e-3, surf_rel=1e-3, centroid_mm=1e-2),
    "single_segment_with_rc_0_5": dict(vol_rel=1e-3, surf_rel=1e-3, centroid_mm=1e-2),
    "configurator_wing": dict(vol_rel=1e-3, surf_rel=1e-3, centroid_mm=1e-2),
    "ehawk_main_wing": dict(vol_rel=3e-2, surf_rel=2e-2, centroid_mm=5e-1),
}


def test_shape_tolerant(roundtrip_case, tmp_path):
    """Render both variants via WingLoftCreator and compare the CAD solids.

    Phase 2 will relax or tighten the ``SHAPE_TOL`` entries based on the
    measured baseline. The metric is intentionally plural (volume,
    surface, centroid) so that a single failing dimension does not
    obscure the others in the report.
    """
    case_id, expected, actual, _, _ = roundtrip_case

    # Rebuild fresh (we already consumed the source_wc inside the
    # fixture when we called asb_wing()).
    expected_for_render = get_factory(case_id)()

    step_a = tmp_path / f"{case_id}_expected.step"
    step_b = tmp_path / f"{case_id}_actual.step"

    render_wing_loft_to_step(
        expected_for_render,
        step_a,
        wing_name="main_wing",
        wing_side="RIGHT",  # mirroring doubles cost and obscures per-segment drift
        connected=False,
    )
    render_wing_loft_to_step(
        actual,
        step_b,
        wing_name="main_wing",
        wing_side="RIGHT",
        connected=False,
    )

    result = compare_wing_shapes(step_a, step_b)

    tol = SHAPE_TOL[case_id]
    assert result.volume_rel_delta <= tol["vol_rel"], (
        f"[{case_id}] volume drift {result.volume_rel_delta:.4%} "
        f"> tol {tol['vol_rel']:.4%}; {result.summary()}"
    )
    assert result.surface_rel_delta <= tol["surf_rel"], (
        f"[{case_id}] surface drift {result.surface_rel_delta:.4%} "
        f"> tol {tol['surf_rel']:.4%}; {result.summary()}"
    )
    assert result.centroid_distance <= tol["centroid_mm"], (
        f"[{case_id}] centroid drift {result.centroid_distance:.4f}mm "
        f"> tol {tol['centroid_mm']:.4f}mm; {result.summary()}"
    )
