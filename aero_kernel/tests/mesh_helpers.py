"""``mesh_surfaces`` for the tests, with the join tolerance of the shipped canon (rule ``hinge-line-continuity``)."""

from collections.abc import Callable

from aero_kernel.build import shipped_build
from aero_kernel.geometry import Airfoil, AirplaneGeometry
from aero_kernel.rules import Rules
from aero_kernel.solvers.avl_mesh import MeshSurface
from aero_kernel.solvers.avl_mesh import mesh_surfaces as _mesh_surfaces

__all__ = ["mesh_surfaces"]


def mesh_surfaces(
    airplane: AirplaneGeometry,
    n_wing: int,
    airfoil_index: Callable[[Airfoil], int],
    *,
    drive_roll: bool = False,
    drive_flaps: bool = False,
) -> tuple[MeshSurface, ...]:
    """The aligned mesh with the canon's join tolerance."""
    join = Rules(shipped_build().model).value("hinge-line-continuity", "join_tolerance")
    return _mesh_surfaces(
        airplane,
        n_wing,
        airfoil_index,
        join_tolerance_m=join,
        drive_roll=drive_roll,
        drive_flaps=drive_flaps,
    )
