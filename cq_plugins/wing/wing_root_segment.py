import math
from typing import Literal

import cadquery as cq
import cq_plugins.wing.airfoil

def wing_root_segment(self: cq.Workplane, root_airfoil: str,
                      root_chord: float, tip_chord: float, length: float,
                      sweep: float = 0, sweep_mode: Literal["distance", "angle"] = "distance",
                      root_incidence: float = 0, tip_incidence: float = 0,
                      root_dihedral: float = 0, tip_dihedral: float = 0,
                      tip_airfoil: str = None,
                      offset: float = 0):
    tip_airfoil = tip_airfoil if tip_airfoil is not None else root_airfoil
    if sweep_mode == "angle":
        e = length
        b = e / math.cos(math.radians(sweep))
        sweep = math.sqrt(b * b - e * e)

    root_plane = self.plane.rotated((root_dihedral, 0, -root_incidence))
    airfoil_root = (cq.Workplane(root_plane).airfoil(root_airfoil, root_chord, offset=offset))
    tip_plane = (airfoil_root.workplane(offset=-length, origin=(sweep, 0, 0))
                 .plane.rotated((tip_dihedral, 0, -tip_incidence)))
    airfoil_tip = (airfoil_root.copyWorkplane(cq.Workplane(tip_plane))
                   .airfoil(tip_airfoil, tip_chord, offset=offset))
    wing = airfoil_tip.loft(combine='a')  # ruled=True --> airfoils must have same number of points

    return wing.newObject([tip_plane.location, airfoil_tip.val(), wing.val()])

