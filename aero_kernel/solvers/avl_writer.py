"""The AVL input text and the reading of its output (ARCHITECTURE ch. 8.8).

The one writer of ``.avl`` text in the kernel. It emits no BODY: the fuselage is not modelled. A
CONTROL appears only on the stations of a mesh that drives the roll devices (the clean file has none).
Airfoil contours are separate files named ``af<i>.dat`` that the
caller puts beside the geometry file (nothing here touches the disk).
"""

import re
from collections.abc import Sequence

from aero_kernel.solvers.avl_mesh import MeshSurface
from pydantic import BaseModel, ConfigDict

__all__ = [
    "AvlOutput",
    "RollOutput",
    "airfoil_file",
    "airfoil_file_name",
    "avl_commands",
    "avl_geometry",
    "avl_roll_commands",
    "parse_avl_output",
    "parse_roll_output",
]

# Chordwise vortex spacing: cosine (AVL's default, 1).
_CHORD_SPACING = 1
# One strip per neighbouring section pair; the spacing is moot for a single strip.
_STRIP = "1   1"
GEOMETRY_FILE = "airplane.avl"
# The roll control: one name for every device acting as aileron, driven as AVL's control variable d1.
# SgnDup -1 makes the mirrored half deflect the other way (avl_doc.txt:755-757, an aileron on a
# YDUPLICATE surface); the hinge vector 0 0 0 puts the hinge along the hinge line (avl_doc.txt:737-757).
CONTROL_NAME = "aileron"
SGN_DUP = -1

_NUMBER = r"(-?\d+\.\d*(?:[EeDd][-+]?\d+)?)"


class RollOutput(BaseModel):
    """What the kernel reads from a steady-roll AVL run.

    Attributes:
        p_hat: ``p'b/2V``, the roll rate in stability axes (what the constraint ``rm`` holds to
            zero moment), positive to the right.
        cl: The total lift coefficient AVL trimmed to.
        cl_stability: ``Cl'tot``, the rolling moment in stability axes (zero when the run is a
            steady roll).
        control: The control deflection AVL echoes in degrees.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    p_hat: float
    cl: float
    cl_stability: float
    control: float


class AvlOutput(BaseModel):
    """What the kernel reads from an AVL run.

    Attributes:
        x_np: x of the neutral point in m.
        cl: The total lift coefficient AVL trimmed to.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    x_np: float
    cl: float


def airfoil_file_name(index: int) -> str:
    """The file name of the contour of airfoil ``index``."""
    return f"af{index}.dat"


def airfoil_file(name: str, coordinates: Sequence[tuple[float, float]]) -> str:
    """The contour file text: Selig order, chord 1.

    Args:
        name: Label on the first line.
        coordinates: Points (x, y) with x in [0, 1].

    Returns:
        The file text.

    Raises:
        ValueError: If a point lies outside the unit chord (AVL then returns nonsense).
    """
    for x, _ in coordinates:
        if not -1e-9 <= x <= 1.0 + 1e-9:
            msg = f"airfoil point x = {x} lies outside the unit chord"
            raise ValueError(msg)
    body = "\n".join(f"{x:.8f} {y:.8f}" for x, y in coordinates)
    return f"{name}\n{body}\n"


def avl_geometry(
    surfaces: Sequence[MeshSurface],
    claf: Sequence[float],
    *,
    n_chord: int,
    s_ref: float,
    c_ref: float,
    b_ref: float,
    xyz_ref: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> str:
    """The ``.avl`` text of an airplane at Mach 0.

    Args:
        surfaces: The aligned mesh.
        claf: ``CLAF`` per airfoil index.
        n_chord: Chordwise vortices.
        s_ref: Reference area in m^2.
        c_ref: Reference chord in m.
        b_ref: Reference span in m.
        xyz_ref: The moment and rotation reference point in m (the origin for the neutral point,
            which does not depend on it; the airplane's own for a roll, which does).

    Returns:
        The file text.
    """
    lines = [
        "airplane",
        "#Mach",
        "0.0",
        "#IYsym   IZsym   Zsym",
        "0   0   0.0",
        "#Sref    Cref    Bref",
        f"{s_ref!r} {c_ref!r} {b_ref!r}",
        "#Xref    Yref    Zref",
        f"{xyz_ref[0]!r} {xyz_ref[1]!r} {xyz_ref[2]!r}",
        "# CDp",
        "0.0",
    ]
    for surface in surfaces:
        lines += [
            "#" + "=" * 60,
            "SURFACE",
            surface.name,
            "#Nchordwise  Cspace",
            f"{surface.n_chord or n_chord}   {_CHORD_SPACING}",
        ]
        if surface.component is not None:
            lines += ["COMPONENT", f"{surface.component}"]
        if surface.symmetric:
            lines += ["YDUPLICATE", "0.0"]
        for section in surface.sections:
            lines += [
                "SECTION",
                "#Xle    Yle    Zle     Chord   Ainc  Nspanwise  Sspace",
                f"{section.x!r} {section.y!r} {section.z!r} {section.chord!r} {section.twist!r}   {_STRIP}",
                "AFIL"
                if section.chord_range is None
                else "AFIL {} {}".format(*section.chord_range),
                airfoil_file_name(section.airfoil),
                "CLAF",
                f"{claf[section.airfoil]!r}",
            ]
            if section.control is not None:
                lines += [
                    "CONTROL",
                    f"{CONTROL_NAME} {section.control.gain!r} {section.control.x_hinge!r} "
                    f"0.0 0.0 0.0 {SGN_DUP}",
                ]
    return "\n".join(lines) + "\n"


def avl_commands(cl: float, core_ratio: float) -> str:
    """The OPER dialogue: vortex core ratio, ``C_L`` constraint, run, stability derivatives."""
    return f"oper\no\nc\n{core_ratio}\n\na c {cl!r}\nx\nst\n\n\nquit\n"


def avl_roll_commands(cl: float, core_ratio: float, delta_deg: float) -> str:
    """The OPER dialogue of a steady roll.

    Constrains ``C_L``, the stability-axis rolling moment to zero (``r rm 0``) and the aileron
    control ``d1`` to the command; runs, asks for no derivatives. The roll rate is the result, in
    AVL's default stability axes (``avl.f:652``); the result is linear in ``d1``
    (``amake.f:1184-1187``).
    """
    return f"oper\no\nc\n{core_ratio}\n\na c {cl!r}\nr rm 0\nd1 d1 {delta_deg!r}\nx\n\nquit\n"


def _first(text: str, key: str) -> float | None:
    """The first ``key = number`` in the output (AVL also prints derived ratios later)."""
    found = re.search(rf"\b{re.escape(key)}\s*=\s*{_NUMBER}", text)
    return float(found.group(1).replace("D", "E").replace("d", "e")) if found else None


def parse_avl_output(text: str) -> AvlOutput | None:
    """Read ``Xnp`` and ``CLtot`` from the output.

    Returns:
        The values, or ``None`` if one is missing (the run did not complete).
    """
    x_np, cl = _first(text, "Xnp"), _first(text, "CLtot")
    if x_np is None or cl is None:
        return None
    return AvlOutput(x_np=x_np, cl=cl)


def parse_roll_output(text: str) -> RollOutput | None:
    """Read ``p'b/2V``, ``CLtot``, ``Cl'tot`` and the control echo from a steady-roll run.

    The first hit of each key is taken: AVL also prints ``pb/2V`` (body axes) before ``p'b/2V``.

    Returns:
        The values, or ``None`` if one is missing (the run did not complete).
    """
    p_hat, cl = _first(text, "p'b/2V"), _first(text, "CLtot")
    cl_stability = _first(text, "Cl'tot")
    echo = re.search(rf"^\s*{re.escape(CONTROL_NAME)}\s*=\s*{_NUMBER}", text, re.MULTILINE)
    if p_hat is None or cl is None or cl_stability is None or echo is None:
        return None
    return RollOutput(p_hat=p_hat, cl=cl, cl_stability=cl_stability, control=float(echo.group(1)))
