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

import os
from pathlib import Path
from typing import Callable

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
from cad_designer.airplane.aircraft_topology.wing.Airfoil import Airfoil  # noqa: E402
from cad_designer.airplane.aircraft_topology.wing.WingConfiguration import (  # noqa: E402
    WingConfiguration,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
AIRFOIL_PATH = str(REPO_ROOT / "components" / "airfoils" / "naca0010.dat")


# --------------------------------------------------------------------------- #
# Test-case factories
#
# Each factory returns a freshly-built, *relative*-mode WingConfiguration.
# Factories are invoked twice per test: once to produce the "expected"
# baseline and once to produce the input to the roundtrip (so the
# baseline is never mutated by asb_wing() caching).
# --------------------------------------------------------------------------- #


def _single_segment_flat() -> WingConfiguration:
    """One segment, zero twist / sweep / dihedral. The trivial sanity case."""
    return WingConfiguration(
        nose_pnt=(0.0, 0.0, 0.0),
        root_airfoil=Airfoil(
            airfoil=AIRFOIL_PATH,
            chord=200.0,
            dihedral_as_rotation_in_degrees=0,
            incidence=0,
            rotation_point_rel_chord=0.25,
        ),
        length=500.0,
        sweep=0,
        sweep_is_angle=False,
        tip_airfoil=Airfoil(
            chord=200.0,
            dihedral_as_rotation_in_degrees=0,
            incidence=0,
            rotation_point_rel_chord=0.25,
        ),
        symmetric=True,
        parameters="relative",
    )


def _single_segment_with_dihedral() -> WingConfiguration:
    """One segment, +5° dihedral rotation. Isolates the dihedral sign bug."""
    return WingConfiguration(
        nose_pnt=(0.0, 0.0, 0.0),
        root_airfoil=Airfoil(
            airfoil=AIRFOIL_PATH,
            chord=200.0,
            dihedral_as_rotation_in_degrees=5,
            incidence=0,
            rotation_point_rel_chord=0.25,
        ),
        length=500.0,
        sweep=0,
        sweep_is_angle=False,
        tip_airfoil=Airfoil(
            chord=200.0,
            dihedral_as_rotation_in_degrees=5,
            incidence=0,
            rotation_point_rel_chord=0.25,
        ),
        symmetric=True,
        parameters="relative",
    )


def _single_segment_with_twist() -> WingConfiguration:
    """One segment, -10° tip incidence. Isolates twist recovery."""
    return WingConfiguration(
        nose_pnt=(0.0, 0.0, 0.0),
        root_airfoil=Airfoil(
            airfoil=AIRFOIL_PATH,
            chord=200.0,
            dihedral_as_rotation_in_degrees=0,
            incidence=0,
            rotation_point_rel_chord=0.25,
        ),
        length=500.0,
        sweep=0,
        sweep_is_angle=False,
        tip_airfoil=Airfoil(
            chord=200.0,
            dihedral_as_rotation_in_degrees=0,
            incidence=-10,
            rotation_point_rel_chord=0.25,
        ),
        symmetric=True,
        parameters="relative",
    )


def _configurator_wing() -> WingConfiguration:
    """The 3-segment wing from ``test/Test_Configurator_wing.py``.

    Copied 1:1 (including the non-trivial nose_pnt=(25,50,100) and
    the alternating positive/negative sweep + dihedral pattern) so that
    a green result here proves the primary user-visible case.
    """
    wc = WingConfiguration(
        nose_pnt=(25, 50, 100),
        symmetric=True,
        parameters="relative",
        root_airfoil=Airfoil(
            airfoil=AIRFOIL_PATH,
            chord=200.0,
            dihedral_as_rotation_in_degrees=4,
            incidence=0,
            rotation_point_rel_chord=0.25,
        ),
        length=500.0,
        sweep=50,
        sweep_is_angle=False,
        tip_airfoil=Airfoil(
            chord=200.0,
            dihedral_as_rotation_in_degrees=-4,
            incidence=-10,
            rotation_point_rel_chord=0.25,
        ),
    )
    wc.add_segment(
        length=500,
        sweep=-50,
        sweep_is_angle=False,
        tip_airfoil=Airfoil(
            chord=150,
            dihedral_as_rotation_in_degrees=-4,
            incidence=-5,
            rotation_point_rel_chord=0.25,
        ),
    )
    wc.add_segment(
        length=500,
        sweep=50,
        sweep_is_angle=False,
        tip_airfoil=Airfoil(
            chord=100,
            dihedral_as_rotation_in_degrees=0,
            incidence=0,
            rotation_point_rel_chord=0.25,
        ),
    )
    return wc


def _ehawk_main_wing() -> WingConfiguration:
    """Real-world eHawk main wing from ``test/ehawk_workflow_helpers``.

    Imported lazily because ``test/`` is not a pytest package and its
    import side-effects (logging setup etc.) we want to pay only when
    this case actually runs.
    """
    # Delayed import — ehawk_workflow_helpers pulls in CAD modules that
    # we don't want to load when the rest of the suite is collected.
    from test.ehawk_workflow_helpers import _build_main_wing  # type: ignore

    return _build_main_wing(AIRFOIL_PATH)


# --------------------------------------------------------------------------- #
# Parametrized fixture wiring
# --------------------------------------------------------------------------- #


# Each entry is (case_id, factory, parameter_tol, origin_tol). Tolerances
# default to float-noise levels — see the baseline notes in beads issue
# cad-modelling-service-7kq for calibration rationale.
CASES: list[tuple[str, Callable[[], WingConfiguration], float, float]] = [
    ("single_segment_flat", _single_segment_flat, 1e-9, 1e-6),
    ("single_segment_with_dihedral", _single_segment_with_dihedral, 1e-9, 1e-6),
    ("single_segment_with_twist", _single_segment_with_twist, 1e-9, 1e-6),
    ("configurator_wing", _configurator_wing, 1e-9, 1e-6),
    ("ehawk_main_wing", _ehawk_main_wing, 1e-9, 1e-6),
]


@pytest.fixture(
    params=CASES,
    ids=[c[0] for c in CASES],
)
def roundtrip_case(request):
    """Yields (case_id, expected_wc, actual_wc, param_tol, origin_tol).

    ``expected_wc`` is freshly built from the factory and never touched
    by ``asb_wing()``. ``actual_wc`` is the result of
    ``from_asb(expected.asb_wing().xsecs)`` — i.e. the roundtripped
    configuration we want to compare against the baseline.
    """
    case_id, factory, param_tol, origin_tol = request.param

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
SHAPE_TOL = {
    "single_segment_flat": dict(vol_rel=1e-3, surf_rel=1e-3, centroid_mm=1e-2),
    "single_segment_with_dihedral": dict(vol_rel=5e-2, surf_rel=5e-2, centroid_mm=5.0),
    "single_segment_with_twist": dict(vol_rel=5e-2, surf_rel=5e-2, centroid_mm=5.0),
    "configurator_wing": dict(vol_rel=2e-1, surf_rel=2e-1, centroid_mm=20.0),
    "ehawk_main_wing": dict(vol_rel=2e-1, surf_rel=2e-1, centroid_mm=20.0),
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
    expected_for_render = _factory_for_case(case_id)

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


def _factory_for_case(case_id: str) -> WingConfiguration:
    for c_id, factory, _, _ in CASES:
        if c_id == case_id:
            return factory()
    raise KeyError(case_id)
