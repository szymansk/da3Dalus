"""AVL geometry dataclass hierarchy.

Each class implements ``__repr__`` to emit its AVL format block.
``repr(AvlGeometryFile(...))`` produces a complete ``.avl`` file string.

Reference: AVL User Primer (Drela & Youngren) and the project spec at
docs/superpowers/specs/2026-04-30-avl-cdcl-neuralfoil-design.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union


# ---------------------------------------------------------------------------
# Task 1 — Core Types
# ---------------------------------------------------------------------------


@dataclass
class AvlCdcl:
    """CDCL drag polar definition (3-point polar in AVL format).

    AVL expects six values on one line after the CDCL keyword:
        CL1 CD1  CL2 CD2  CL3 CD3
    where (CL1,CD1) is the negative-stall point, (CL2,CD2) the drag
    bucket minimum, and (CL3,CD3) the positive-stall point.
    """

    cl_min: float  # CL1 — negative stall boundary
    cd_min: float  # CD1
    cl_0: float  # CL2 — drag minimum CL
    cd_0: float  # CD2 — minimum drag coefficient
    cl_max: float  # CL3 — positive stall boundary
    cd_max: float  # CD3

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------

    @classmethod
    def zeros(cls) -> "AvlCdcl":
        """Return an all-zero CDCL (AVL default — no profile drag)."""
        return cls(cl_min=0.0, cd_min=0.0, cl_0=0.0, cd_0=0.0, cl_max=0.0, cd_max=0.0)

    def is_zero(self) -> bool:
        """Return True when all six values are zero."""
        return (
            self.cl_min == 0.0
            and self.cd_min == 0.0
            and self.cl_0 == 0.0
            and self.cd_0 == 0.0
            and self.cl_max == 0.0
            and self.cd_max == 0.0
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        vals = f"{self.cl_min} {self.cd_min}  {self.cl_0} {self.cd_0}  {self.cl_max} {self.cd_max}"
        return f"CDCL\n{vals}\n"


@dataclass
class AvlControl:
    """CONTROL surface definition (one per deflectable surface panel).

    AVL format::

        CONTROL
        name  gain  Xhinge  Xhvec Yhvec Zhvec  SgnDup
    """

    name: str
    gain: float
    xhinge: float
    xyz_hvec: tuple[float, float, float]
    sgn_dup: float

    def __repr__(self) -> str:
        hx, hy, hz = self.xyz_hvec
        return f"CONTROL\n{self.name}  {self.gain}  {self.xhinge}  {hx} {hy} {hz}  {self.sgn_dup}\n"


@dataclass
class AvlNaca:
    """NACA 4/5-digit airfoil keyword.

    AVL format::

        NACA
        2412
    """

    digits: str

    def __repr__(self) -> str:
        return f"NACA\n{self.digits}\n"


@dataclass
class AvlAfile:
    """AFIL — airfoil coordinates from an external file.

    AVL format::

        AFIL
        /path/to/airfoil.dat
    """

    filepath: str

    def __repr__(self) -> str:
        return f"AFIL\n{self.filepath}\n"


@dataclass
class AvlAirfoilInline:
    """AIRFOIL — airfoil coordinates embedded inline.

    AVL format::

        AIRFOIL
        ! name (optional comment line)
        x1 y1
        x2 y2
        ...
    """

    name: str
    coordinates: str  # multi-line string of "x y" pairs

    def __repr__(self) -> str:
        return f"AIRFOIL\n! {self.name}\n{self.coordinates}\n"


# Type alias used by AvlSection
AvlAirfoil = Union[AvlNaca, AvlAirfoilInline, AvlAfile]


# ---------------------------------------------------------------------------
# Task 2 — Section and Surface
# ---------------------------------------------------------------------------


@dataclass
class AvlDesign:
    """DESIGN variable definition (perturbation parameter).

    AVL format::

        DESIGN
        name  weight
    """

    name: str
    weight: float

    def __repr__(self) -> str:
        return f"DESIGN\n{self.name}  {self.weight}\n"


@dataclass
class AvlSection:
    """SECTION block — one spanwise cross-section of a surface.

    Mandatory fields: xyz_le, chord.
    Optional: ainc (default 0), n_span, s_space, airfoil, claf, cdcl,
    controls, designs.

    AVL format::

        SECTION
        !  Xle  Yle  Zle  Chord  Ainc  [Nspan  Sspace]
           0.0  0.0  0.0  0.200  2.0   [8      1.0   ]
        [NACA | AFIL | AIRFOIL block]
        [CLAF
         1.05]
        [CDCL block]
        [CONTROL block(s)]
        [DESIGN block(s)]
    """

    xyz_le: tuple[float, float, float]
    chord: float
    ainc: float = 0.0
    n_span: int | None = None
    s_space: float | None = None
    airfoil: AvlAirfoil | None = None
    claf: float | None = None
    cdcl: AvlCdcl | None = None
    controls: list[AvlControl] = field(default_factory=list)
    designs: list[AvlDesign] = field(default_factory=list)

    def __repr__(self) -> str:
        lines: list[str] = []
        lines.append("SECTION")
        lines.append("!  Xle    Yle    Zle    Chord  Ainc   Nspan  Sspace")

        xle, yle, zle = self.xyz_le
        geo = f"   {xle}  {yle}  {zle}  {self.chord}  {self.ainc}"
        if self.n_span is not None and self.s_space is not None:
            geo += f"  {self.n_span}  {self.s_space}"
        lines.append(geo)

        if self.airfoil is not None:
            lines.append(repr(self.airfoil).rstrip("\n"))

        if self.claf is not None:
            lines.append(f"CLAF\n   {self.claf}")

        if self.cdcl is not None:
            lines.append(repr(self.cdcl).rstrip("\n"))

        for ctrl in self.controls:
            lines.append(repr(ctrl).rstrip("\n"))

        for design in self.designs:
            lines.append(repr(design).rstrip("\n"))

        return "\n".join(lines) + "\n"


@dataclass
class AvlSurface:
    """SURFACE block — one lifting/control surface.

    AVL format::

        SURFACE
        name
        !  Nchord  Cspace  [Nspan  Sspace]
           12      1.0     [20     1.0   ]
        [COMPONENT n]
        [YDUPLICATE  y]
        [SCALE  Xscale Yscale Zscale]
        [TRANSLATE  dX dY dZ]
        [ANGLE  angle]
        [NOWAKE]
        [NOALBE]
        [NOLOAD]
        [CDCL block]
        SECTION block(s)
    """

    name: str
    n_chord: int
    c_space: float
    sections: list[AvlSection] = field(default_factory=list)
    n_span: int | None = None
    s_space: float | None = None
    yduplicate: float | None = None
    component: int | None = None
    scale: tuple[float, float, float] | None = None
    translate: tuple[float, float, float] | None = None
    angle: float | None = None
    nowake: bool = False
    noalbe: bool = False
    noload: bool = False
    cdcl: AvlCdcl | None = None

    def __repr__(self) -> str:
        lines: list[str] = []
        lines.append("SURFACE")
        lines.append(self.name)

        # Chord panelling line
        lines.append("!  Nchord  Cspace  Nspan  Sspace")
        panel_line = f"   {self.n_chord}  {self.c_space}"
        if self.n_span is not None and self.s_space is not None:
            panel_line += f"  {self.n_span}  {self.s_space}"
        lines.append(panel_line)

        if self.component is not None:
            lines.append(f"COMPONENT\n   {self.component}")

        if self.yduplicate is not None:
            lines.append(f"YDUPLICATE\n   {self.yduplicate}")

        if self.scale is not None:
            sx, sy, sz = self.scale
            lines.append(f"SCALE\n   {sx}  {sy}  {sz}")

        if self.translate is not None:
            tx, ty, tz = self.translate
            lines.append(f"TRANSLATE\n   {tx}  {ty}  {tz}")

        if self.angle is not None:
            lines.append(f"ANGLE\n   {self.angle}")

        if self.nowake:
            lines.append("NOWAKE")

        if self.noalbe:
            lines.append("NOALBE")

        if self.noload:
            lines.append("NOLOAD")

        if self.cdcl is not None:
            lines.append(repr(self.cdcl).rstrip("\n"))

        for section in self.sections:
            lines.append(repr(section).rstrip("\n"))

        return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Task 3 — Top-Level File
# ---------------------------------------------------------------------------


@dataclass
class AvlSymmetry:
    """Symmetry specification.

    AVL format (after Mach line)::

        Iysym  Izsym  Zsym
        0      0      0.0

    Iysym: 0=none, 1=reflect about y=0, -1=anti-symmetric
    Izsym: 0=none, 1=reflect about z=Zsym, -1=anti-symmetric
    Zsym: z-plane of symmetry (used when Izsym != 0)
    """

    iy_sym: int = 0
    iz_sym: int = 0
    z_sym: float = 0.0

    def __repr__(self) -> str:
        return f"!  Iysym  Izsym  Zsym\n   {self.iy_sym}      {self.iz_sym}      {self.z_sym}\n"


@dataclass
class AvlReference:
    """Reference quantities for non-dimensionalisation.

    AVL format::

        Sref  Cref  Bref
        Xref  Yref  Zref
    """

    s_ref: float
    c_ref: float
    b_ref: float
    xyz_ref: tuple[float, float, float]

    def __repr__(self) -> str:
        xr, yr, zr = self.xyz_ref
        return (
            f"!  Sref    Cref    Bref\n"
            f"   {self.s_ref}  {self.c_ref}  {self.b_ref}\n"
            f"!  Xref    Yref    Zref\n"
            f"   {xr}  {yr}  {zr}\n"
        )


@dataclass
class AvlBody:
    """BODY block — a fuselage or nacelle body shape.

    AVL format::

        BODY
        name
        !  Nbody  Bspace
           12     1.0
        [YDUPLICATE  y]
        [SCALE  Xs Ys Zs]
        [TRANSLATE  dX dY dZ]
        BFIL
        /path/to/body.bfile
    """

    name: str
    n_body: int
    b_space: float
    bfile: str
    yduplicate: float | None = None
    scale: tuple[float, float, float] | None = None
    translate: tuple[float, float, float] | None = None

    def __repr__(self) -> str:
        lines: list[str] = []
        lines.append("BODY")
        lines.append(self.name)
        lines.append("!  Nbody  Bspace")
        lines.append(f"   {self.n_body}  {self.b_space}")

        if self.yduplicate is not None:
            lines.append(f"YDUPLICATE\n   {self.yduplicate}")

        if self.scale is not None:
            sx, sy, sz = self.scale
            lines.append(f"SCALE\n   {sx}  {sy}  {sz}")

        if self.translate is not None:
            tx, ty, tz = self.translate
            lines.append(f"TRANSLATE\n   {tx}  {ty}  {tz}")

        lines.append(f"BFIL\n{self.bfile}")

        return "\n".join(lines) + "\n"


@dataclass
class AvlGeometryFile:
    """Top-level AVL geometry file.

    ``repr(avl_file)`` produces the complete ``.avl`` file content.

    AVL format::

        title
        !  Mach
           0.0
        !  Iysym  Izsym  Zsym
           0      0      0.0
        !  Sref    Cref    Bref
           ...
        !  Xref    Yref    Zref
           ...
        [!  CDp
            0.0]

        SURFACE
        ...

        BODY
        ...
    """

    title: str
    mach: float
    symmetry: AvlSymmetry
    reference: AvlReference
    surfaces: list[AvlSurface] = field(default_factory=list)
    bodies: list[AvlBody] = field(default_factory=list)
    cdp: float = 0.0

    def __repr__(self) -> str:
        sections: list[str] = []

        # Header
        sections.append(self.title)
        sections.append(f"!  Mach\n   {self.mach}")
        sections.append(repr(self.symmetry).rstrip("\n"))
        sections.append(repr(self.reference).rstrip("\n"))

        if self.cdp != 0.0:
            sections.append(f"!  CDp\n   {self.cdp}")

        # Surfaces
        for surface in self.surfaces:
            sections.append("")
            sections.append(repr(surface).rstrip("\n"))

        # Bodies
        for body in self.bodies:
            sections.append("")
            sections.append(repr(body).rstrip("\n"))

        return "\n".join(sections) + "\n"
