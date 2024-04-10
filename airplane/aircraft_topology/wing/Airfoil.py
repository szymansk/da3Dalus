class Airfoil:
    def __init__(self, airfoil: str|None = None, chord: float|None = None, dihedral: float = 0, incidence: float = 0):
        self.airfoil = airfoil
        self.chord = chord
        self.dihedral = dihedral
        self.incidence = incidence

    def __repr__(self):
        from pprint import pformat
        return pformat(vars(self), indent=4, width=1)
