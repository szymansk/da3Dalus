import math
from typing import Literal

import cadquery as cq
from cadquery import Workplane, Plane

import cq_plugins.wing.airfoil

def wing_root_segment(self: cq.Workplane, root_airfoil: str,
                      root_chord: float, tip_chord: float, length: float,
                      sweep: float = 0, sweep_mode: Literal["distance", "angle"] = "distance",
                      root_incidence: float = 0, tip_incidence: float = 0,
                      root_dihedral: float = 0, tip_dihedral: float = 0,
                      tip_airfoil: str = None,
                      offset: float = 0,
                      number_interpolation_points: int = None):
    tip_airfoil = tip_airfoil if tip_airfoil is not None else root_airfoil
    if sweep_mode == "angle":
        e = length
        b = e / math.cos(math.radians(sweep))
        sweep = math.sqrt(b * b - e * e)

    root_plane: Plane = self.plane.rotated((root_dihedral, 0, -root_incidence))
    airfoil_root: Workplane = (cq.Workplane(root_plane).airfoil(root_airfoil, root_chord, offset=offset, number_interpolation_points=number_interpolation_points).toPending())
    tip_plane: Plane = (airfoil_root.workplane(offset=-length, origin=(sweep, 0, 0))
                 .plane.rotated((tip_dihedral, 0, -tip_incidence)))
    airfoil_tip: Workplane = (airfoil_root.copyWorkplane(cq.Workplane(tip_plane))
                              .airfoil(tip_airfoil, tip_chord, offset=offset, number_interpolation_points=number_interpolation_points).toPending())
    wing: Workplane = airfoil_tip.loft(combine='a')  # ruled=True --> airfoils must have same number of points

    # add a connection part
    center_plane: Plane = self.plane.rotated((0, 0, -root_incidence))
    base_root: Workplane = (cq.Workplane(root_plane).airfoil(root_airfoil, root_chord, offset=offset, number_interpolation_points=number_interpolation_points).toPending())
    center_root: Workplane = (cq.Workplane(center_plane).workplane(offset=length))
    center: Workplane = (base_root.copyWorkplane(center_root)
                         .airfoil(root_airfoil, root_chord, offset=offset, number_interpolation_points=number_interpolation_points).toPending())
    center_wing = center.loft(combine='a')

    final_wing = wing.union(toUnion=center_wing).copyWorkplane(self).split(keepBottom=True)

    return wing.newObject([tip_plane, airfoil_tip.val(), final_wing.val()])

