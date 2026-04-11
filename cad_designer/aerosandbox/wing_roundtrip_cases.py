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
    ("single_segment_with_dihedral", single_segment_with_dihedral),
    ("single_segment_with_twist", single_segment_with_twist),
    ("configurator_wing", configurator_wing),
    ("ehawk_main_wing", ehawk_main_wing),
]


def get_factory(case_id: str) -> Callable[[], WingConfiguration]:
    """Look up a factory by case id. Raises ``KeyError`` on unknown ids."""
    for cid, factory in CASE_FACTORIES:
        if cid == case_id:
            return factory
    raise KeyError(case_id)
