"""
Shared test-case factories for the ``WingConfiguration`` roundtrip
harness.

These factories are consumed both by ``app/tests/test_wing_config_roundtrip.py``
(the pytest entry point) and by the ``__main__`` CLI in
``cad_designer/aerosandbox/wing_roundtrip.py`` (the STEP exporter that
the developer uses for manual visual comparison in a CAD tool).

Each factory returns a fresh, *relative*-mode ``WingConfiguration``.
They are plain functions — not fixtures — so either entry point can
call them without pulling in pytest machinery.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Tuple

from cad_designer.airplane.aircraft_topology.wing.Airfoil import Airfoil
from cad_designer.airplane.aircraft_topology.wing.WingConfiguration import (
    WingConfiguration,
)

# Repo root is four levels up from this file:
# cad_designer/aerosandbox/wing_roundtrip_cases.py -> repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
AIRFOIL_PATH = str(REPO_ROOT / "components" / "airfoils" / "naca0010.dat")


def single_segment_flat() -> WingConfiguration:
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


def single_segment_with_dihedral() -> WingConfiguration:
    """One segment with a ~5° dihedral, expressed via ``dihedral_as_translation``.

    ``dihedral_as_rotation_in_degrees`` is *not* used here because that
    parameter has no clean round-trip through asb: Wing applies an
    explicit ``R_x`` rotation in its H matrix, while asb derives
    dihedral from ``yg_local`` (the LE-to-LE span direction). The two
    representations only agree when dihedral is expressed as a span
    translation (which reshapes the LE positions), not as an
    independent airfoil bank. See cad-modelling-service-121.
    """
    import math

    length = 500.0
    dihedral_deg = 5.0
    return WingConfiguration(
        nose_pnt=(0.0, 0.0, 0.0),
        root_airfoil=Airfoil(
            airfoil=AIRFOIL_PATH,
            chord=200.0,
            dihedral_as_rotation_in_degrees=0,
            dihedral_as_translation=length * math.sin(math.radians(dihedral_deg)),
            incidence=0,
            rotation_point_rel_chord=0.25,
        ),
        length=length * math.cos(math.radians(dihedral_deg)),
        sweep=0,
        sweep_is_angle=False,
        tip_airfoil=Airfoil(
            chord=200.0,
            dihedral_as_rotation_in_degrees=0,
            dihedral_as_translation=0,
            incidence=0,
            rotation_point_rel_chord=0.25,
        ),
        symmetric=True,
        parameters="relative",
    )


def single_segment_with_nose_pnt() -> WingConfiguration:
    """One segment at non-zero ``nose_pnt``. Guards against regression
    of the ``_get_relative_segment_coordinate_system`` inverted-``if``
    bug (cad-modelling-service-tda): a 1-segment wing is the simplest
    topology that still surfaces the nose_pnt double-counting, and
    avoids the other parameter-drift noise that multi-segment cases
    add on top of it.
    """
    return WingConfiguration(
        nose_pnt=(25.0, 50.0, 100.0),
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


def single_segment_with_rc_0_5() -> WingConfiguration:
    """One segment with ``rotation_point_rel_chord = 0.5`` on both
    airfoils. Locks in the Phase-3 (cad-modelling-service-121)
    guarantee that the from_asb projection works for any rc, not
    just 0.25. Before Phase 3, ``asb_wing()`` rejected non-0.25 rc
    outright — so this case only becomes runnable once the guards
    are lifted.
    """
    return WingConfiguration(
        nose_pnt=(0.0, 0.0, 0.0),
        root_airfoil=Airfoil(
            airfoil=AIRFOIL_PATH,
            chord=200.0,
            dihedral_as_rotation_in_degrees=0,
            incidence=0,
            rotation_point_rel_chord=0.5,
        ),
        length=500.0,
        sweep=0,
        sweep_is_angle=False,
        tip_airfoil=Airfoil(
            chord=200.0,
            dihedral_as_rotation_in_degrees=0,
            incidence=-10,
            rotation_point_rel_chord=0.5,
        ),
        symmetric=True,
        parameters="relative",
    )


def single_segment_with_twist() -> WingConfiguration:
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


def configurator_wing() -> WingConfiguration:
    """The 3-segment wing from ``test/Test_Configurator_wing.py``,
    re-expressed with ``dihedral_as_translation`` instead of
    ``dihedral_as_rotation_in_degrees``.

    The original test/ file alternates +4°/-4° dihedral using the
    rotation form on per-segment airfoils. That parameterisation is
    not asb-roundtrippable (see
    ``single_segment_with_dihedral`` and
    cad-modelling-service-121). Here we encode the *equivalent* LE
    positions via per-segment ``dihedral_as_translation`` +
    corrected ``length``, preserving the overall wing shape while
    keeping the roundtrip exact.

    The nose_pnt, sweep, twist and 3-segment topology are kept 1:1
    from the original so Level 2 / Level 3 still exercise the
    multi-segment matrix stack with a non-trivial nose.
    """
    import math

    # Per-segment dihedral angles from the original configurator_wing:
    # seg 0 tip was -4°, seg 1 tip was -4°, seg 2 tip was 0°. The
    # equivalent translation form uses the *trigonometric* decomposition
    # of each segment's length L into (L*cos(d), L*sin(d)) so the LE
    # position at the segment tip is preserved.
    length_seg0 = 500.0
    length_seg1 = 500.0
    length_seg2 = 500.0
    dihedral_0 = -4.0  # seg 0 tip
    dihedral_1 = -4.0  # seg 1 tip
    dihedral_2 = 0.0   # seg 2 tip

    wc = WingConfiguration(
        nose_pnt=(25, 50, 100),
        symmetric=True,
        parameters="relative",
        root_airfoil=Airfoil(
            airfoil=AIRFOIL_PATH,
            chord=200.0,
            dihedral_as_rotation_in_degrees=0,
            dihedral_as_translation=length_seg0 * math.sin(math.radians(dihedral_0)),
            incidence=0,
            rotation_point_rel_chord=0.25,
        ),
        length=length_seg0 * math.cos(math.radians(dihedral_0)),
        sweep=50,
        sweep_is_angle=False,
        tip_airfoil=Airfoil(
            chord=200.0,
            dihedral_as_rotation_in_degrees=0,
            dihedral_as_translation=length_seg1 * math.sin(math.radians(dihedral_1)),
            incidence=-10,
            rotation_point_rel_chord=0.25,
        ),
    )
    wc.add_segment(
        length=length_seg1 * math.cos(math.radians(dihedral_1)),
        sweep=-50,
        sweep_is_angle=False,
        tip_airfoil=Airfoil(
            chord=150,
            dihedral_as_rotation_in_degrees=0,
            dihedral_as_translation=length_seg2 * math.sin(math.radians(dihedral_2)),
            incidence=-5,
            rotation_point_rel_chord=0.25,
        ),
    )
    wc.add_segment(
        length=length_seg2 * math.cos(math.radians(dihedral_2)),
        sweep=50,
        sweep_is_angle=False,
        tip_airfoil=Airfoil(
            chord=100,
            dihedral_as_rotation_in_degrees=0,
            dihedral_as_translation=0,
            incidence=0,
            rotation_point_rel_chord=0.25,
        ),
    )
    return wc


def ehawk_main_wing() -> WingConfiguration:
    """Real-world eHawk main wing from ``test/ehawk_workflow_helpers``."""
    # Delayed import — ehawk_workflow_helpers pulls in CAD modules that
    # we don't want to load when the rest of the suite is collected.
    from test.ehawk_workflow_helpers import _build_main_wing  # type: ignore

    return _build_main_wing(AIRFOIL_PATH)


# Ordered list of (case_id, factory) used by both the pytest harness
# and the CLI exporter. Tests add their own tolerance columns on top.
CASE_FACTORIES: List[Tuple[str, Callable[[], WingConfiguration]]] = [
    ("single_segment_flat", single_segment_flat),
    ("single_segment_with_nose_pnt", single_segment_with_nose_pnt),
    ("single_segment_with_dihedral", single_segment_with_dihedral),
    ("single_segment_with_twist", single_segment_with_twist),
    ("single_segment_with_rc_0_5", single_segment_with_rc_0_5),
    ("configurator_wing", configurator_wing),
    ("ehawk_main_wing", ehawk_main_wing),
]


def get_factory(case_id: str) -> Callable[[], WingConfiguration]:
    """Look up a factory by case id. Raises ``KeyError`` on unknown ids."""
    for cid, factory in CASE_FACTORIES:
        if cid == case_id:
            return factory
    raise KeyError(case_id)
