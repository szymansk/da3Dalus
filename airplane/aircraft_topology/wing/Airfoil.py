class Airfoil:
    def __init__(self, airfoil: str = None, chord: float = None, dihedral: float = 0, incidence: float = 0, rotation_point_rel_chord: float = 0):
        self.airfoil: str = airfoil
        self.chord: float = chord
        self.dihedral: float = dihedral
        self.incidence: float = incidence
        self.rotation_point_rel_chord: float = rotation_point_rel_chord

    def __repr__(self):
        from pprint import pformat
        return pformat(vars(self), indent=4, width=1)
