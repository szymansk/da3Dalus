class WingSegment:
    def __init__(self, root_airfoil: str,
                 length: float,
                 root_chord: float,
                 tip_chord: float,
                 sweep: float = 0,
                 root_dihedral: float = 0,
                 root_incidence: float = 0,
                 root_trailing_edge: float = 1,
                 tip_airfoil: str = None,
                 tip_dihedral: float = 0,
                 tip_incidence: float = 0,
                 tip_trailing_edge: float = 1):
        self.tip_trailing_edge = tip_trailing_edge
        self.root_trailing_edge = root_trailing_edge
        self.tip_airfoil = tip_airfoil
        self.root_airfoil = root_airfoil
        self.length = length
        self.root_chord = root_chord
        self.tip_chord = tip_chord
        self.sweep = sweep
        self.root_dihedral = root_dihedral
        self.root_incidence = root_incidence
        self.tip_dihedral = tip_dihedral
        self.tip_incidence = tip_incidence


class WingConfiguration:

    def __init__(self, root_airfoil: str,
                 nose_pnt: tuple[float, float, float],
                 length: float,
                 root_chord: float,
                 tip_chord: float,
                 sweep: float = 0,
                 root_dihedral: float = 0,
                 root_incidence: float = 0,
                 root_trailing_edge: float = 1,
                 tip_airfoil: str = None,
                 tip_dihedral: float = 0,
                 tip_incidence: float = 0,
                 tip_trailing_edge: float = 1):
        self.nose_pnt: tuple[float, float, float] = nose_pnt
        root_segment = WingSegment(root_airfoil, length, root_chord, tip_chord,
                                   sweep, root_dihedral, root_incidence, root_trailing_edge,
                                   tip_airfoil, tip_dihedral, tip_incidence, tip_trailing_edge)
        self.segments: list[WingSegment] = [root_segment]

    def add_segment(self,
                    length: float,
                    tip_chord: float,
                    sweep: float = 0,
                    tip_airfoil: str = None,
                    tip_dihedral: float = 0,
                    tip_incidence: float = 0,
                    root_trailing_edge: float = 1,
                    tip_trailing_edge: float = 1 ):
        airfoil = self.segments[-1].root_airfoil if self.segments[-1].tip_airfoil is None else self.segments[-1].tip_airfoil
        tip_airfoil = airfoil if tip_airfoil is None else tip_airfoil
        segment = WingSegment(airfoil, length, self.segments[-1].tip_chord, tip_chord,
                              sweep, 0, 0, root_trailing_edge, tip_airfoil, tip_dihedral, tip_incidence, tip_trailing_edge)
        self.segments.append(segment)