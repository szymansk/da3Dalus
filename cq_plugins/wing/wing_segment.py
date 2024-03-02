import logging

import math
from typing import Literal

import cadquery as cq
from cadquery import Workplane

from cq_plugins.wing.wing_root_segment import wing_root_segment
from cadquery.occ_impl.shapes import Wire, Solid, Location

def wing_segment(self: cq.Workplane, tip_airfoil: str, tip_chord: float, length: float,
                 sweep: float = 0, sweep_mode: Literal["distance", "angle"] = "distance",
                 tip_incidence: float = 0, tip_dihedral: float = 0, offset: float = 0):
    airfoil_root: Workplane = self
    airfoil_root_wires: Wire = airfoil_root.vals()[-2]
    airfoil_root.ctx.pendingWires = [airfoil_root_wires]
    root_plane = airfoil_root.plane
    tip_origin = root_plane.origin
    if sweep_mode == "distance":
        tip_origin.x = tip_origin.x + sweep
    else:
        e = length
        b = e / math.cos(math.radians(sweep))
        sweep_by_ang = math.sqrt(b * b - e * e)
        tip_origin.x = tip_origin.x + sweep_by_ang

    tip_plane = (cq.Workplane().copyWorkplane(airfoil_root).workplane(offset=-length, origin=tip_origin)
                 .plane.rotated((tip_dihedral, 0, -tip_incidence)))
    airfoil_tip = (cq.Workplane().copyWorkplane(cq.Workplane(tip_plane)).add(airfoil_root_wires).toPending()
                   .airfoil(tip_airfoil, tip_chord, offset=offset))
    pending = airfoil_tip.ctx.pendingWires
    try:
        _wing = airfoil_tip.loft()#.union(airfoil_root_solid)  # ruled=True --> airfoils must have same number of points
        return _wing.newObject([tip_plane, airfoil_tip.val(), _wing.val()])
    except:
        loft = cq.Solid.makeLoft(pending)
        _wing = cq.Workplane(obj=loft).copyWorkplane(
            airfoil_tip)  # ruled=True --> airfoils must have same number of points0
        return _wing.newObject([tip_plane, airfoil_tip.val(), self.findSolid(), _wing.findSolid()])


if __name__ == "__main__":
    _airfoil = "../components/airfoils/naca23013.5.dat"
    wing: Workplane = (cq.Workplane('XZ').wing_root_segment(root_airfoil=_airfoil,
                                                            root_chord=200,
                                                            root_dihedral=0,
                                                            root_incidence=0,
                                                            length=200,
                                                            sweep=5,
                                                            sweep_mode="angle",
                                                            tip_chord=100,
                                                            tip_dihedral=4,
                                                            tip_incidence=-2))

    wing.display(name="naca23013.5", severity=logging.WARN)

    wing = wing.wing_segment(tip_airfoil=_airfoil, tip_chord=40, length=100, tip_dihedral=0, sweep_mode="angle",
                             sweep=5)
    wing.display(name="naca23013.5_middle", severity=logging.WARN)

    wing = wing.wing_segment(tip_airfoil=_airfoil, tip_chord=20, length=20, tip_dihedral=0, sweep_mode="angle", sweep=5)
    wing.display(name="naca23013.5_tip", severity=logging.WARN)

    off_wing: Workplane = (cq.Workplane('XZ').wing_root_segment(root_airfoil=_airfoil,
                                                                root_chord=200,
                                                                root_dihedral=0,
                                                                root_incidence=0,
                                                                length=200,
                                                                sweep=5,
                                                                sweep_mode="angle",
                                                                tip_chord=100,
                                                                tip_dihedral=4,
                                                                tip_incidence=-2,
                                                                offset=-0.8))
    off_wing.display(name="off_wing.5", severity=logging.WARN)

    off_wing = off_wing.wing_segment(tip_airfoil=_airfoil, tip_chord=40, length=100, tip_dihedral=0, sweep_mode="angle",
                                     sweep=5, offset=-0.8)
    off_wing.display(name="off_wing.5_middle", severity=logging.WARN)

    off_wing = off_wing.wing_segment(tip_airfoil=_airfoil, tip_chord=20, length=20, tip_dihedral=0, sweep_mode="angle",
                                     sweep=5, offset=-0.8)
    off_wing.display(name="off_wing.5_tip", severity=logging.WARN)
    pass


