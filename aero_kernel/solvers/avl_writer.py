"""The AVL input text and the reading of its output (ARCHITECTURE ch. 8.8).

The one writer of ``.avl`` text in the kernel. It emits no BODY and no CONTROL: the fuselage is not
modelled and the devices are at rest. Airfoil contours are separate files named ``af<i>.dat`` that the
caller puts beside the geometry file (nothing here touches the disk).
"""

import re
from collections.abc import Sequence

from aero_kernel.solvers.avl_mesh import MeshSurface
from pydantic import BaseModel, ConfigDict

__all__ = [
    "AvlOutput",
    "airfoil_file",
    "airfoil_file_name",
    "avl_commands",
    "avl_geometry",
    "parse_avl_output",
]

# Chordwise vortex spacing: cosine (AVL's default, 1).
_CHORD_SPACING = 1
# One strip per neighbouring section pair; the spacing is moot for a single strip.
_STRIP = "1   1"
GEOMETRY_FILE = "airplane.avl"

_NUMBER = r"(-?\d+\.\d*(?:[EeDd][-+]?\d+)?)"


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
) -> str:
    """The ``.avl`` text of an airplane at Mach 0 with the reference point at the origin.

    Args:
        surfaces: The aligned mesh.
        claf: ``CLAF`` per airfoil index.
        n_chord: Chordwise vortices.
        s_ref: Reference area in m^2.
        c_ref: Reference chord in m.
        b_ref: Reference span in m.

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
        "0.0 0.0 0.0",
        "# CDp",
        "0.0",
    ]
    for surface in surfaces:
        lines += [
            "#" + "=" * 60,
            "SURFACE",
            surface.name,
            "#Nchordwise  Cspace",
            f"{n_chord}   {_CHORD_SPACING}",
        ]
        if surface.symmetric:
            lines += ["YDUPLICATE", "0.0"]
        for section in surface.sections:
            lines += [
                "SECTION",
                "#Xle    Yle    Zle     Chord   Ainc  Nspanwise  Sspace",
                f"{section.x!r} {section.y!r} {section.z!r} {section.chord!r} {section.twist!r}   {_STRIP}",
                "AFIL",
                airfoil_file_name(section.airfoil),
                "CLAF",
                f"{claf[section.airfoil]!r}",
            ]
    return "\n".join(lines) + "\n"


def avl_commands(cl: float, core_ratio: float) -> str:
    """The OPER dialogue: vortex core ratio, ``C_L`` constraint, run, stability derivatives."""
    return f"oper\no\nc\n{core_ratio}\n\na c {cl!r}\nx\nst\n\n\nquit\n"


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
