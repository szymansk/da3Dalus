"""The AVL input text and the reading of its output (ARCHITECTURE ch. 8.8).

The one writer of ``.avl`` text in the kernel. A BODY appears only for a run that is given bodies
(:mod:`aero_kernel.solvers.avl_body`): the neutral point and the steady roll model no fuselage. A
CONTROL appears only on the stations of a mesh that drives the roll devices (the clean file has none).
Airfoil contours are separate files named ``af<i>.dat`` that the
caller puts beside the geometry file (nothing here touches the disk).
"""

import re
from collections.abc import Sequence

from aero_kernel.config import config
from aero_kernel.solvers.avl_body import MeshBody
from aero_kernel.solvers.avl_mesh import (
    FLAP_CONTROL,
    ROLL_CONTROL,
    ROLL_SGN_DUP,
    MeshSurface,
)
from pydantic import BaseModel, ConfigDict

__all__ = [
    "AvlOutput",
    "LateralOutput",
    "RollOutput",
    "airfoil_file",
    "airfoil_file_name",
    "avl_commands",
    "avl_geometry",
    "avl_lateral_commands",
    "avl_roll_commands",
    "body_file_name",
    "control_order",
    "parse_avl_output",
    "parse_flap_echo",
    "parse_lateral_output",
    "parse_roll_output",
]

# Chordwise vortex spacing: cosine (AVL's default, 1).
CHORD_SPACING = 1
# One strip per neighbouring section pair; the spacing is moot for a single strip.
_STRIP = "1   1"
GEOMETRY_FILE = "airplane.avl"
# Source and doublet nodes along a body axis, and their spacing: cosine (1.0), as for the strips. The
# primer's own example uses 15 nodes (avl_doc.txt:947-949); a fuselage of 20-60 sections is resolved
# by 20 cosine-spaced nodes, the line being smooth between the sections.
BODY_NODES = 20
BODY_SPACING = 1.0
# The roll control: one name for every device acting as aileron, driven as an AVL control variable.
# SgnDup -1 makes the mirrored half deflect the other way (avl_doc.txt:755-757, an aileron on a
# YDUPLICATE surface); the hinge vector 0 0 0 puts the hinge along the hinge line (avl_doc.txt:737-757).
# The flap control (:data:`FLAP_CONTROL`) is symmetric: SgnDup +1, written after the roll control.
CONTROL_NAME = ROLL_CONTROL
SGN_DUP = ROLL_SGN_DUP

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
        cl_p: ``Clp``, the stability-axis rolling-moment derivative with respect to ``p'b/2V``, at
            the airplane's state without roll and without deflection and the same ``C_L``.
        cl_delta: ``Cld01``, the rolling-moment derivative with respect to the aileron in
            degrees, at that state.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    p_hat: float
    cl: float
    cl_stability: float
    control: float
    cl_p: float
    cl_delta: float


class LateralOutput(BaseModel):
    """What the kernel reads from an AVL run for the lateral-directional derivatives.

    The six derivatives are AVL's stability-axis values, ``C_l,beta`` and ``C_n,beta`` per radian of
    sideslip, the rate derivatives per ``p'b/2V`` and ``r'b/2V``.

    Attributes:
        cl: The total lift coefficient AVL trimmed to.
        c_l_beta: ``Clb``.
        c_n_beta: ``Cnb``.
        c_l_p: ``Clp``.
        c_n_p: ``Cnp``.
        c_l_r: ``Clr``.
        c_n_r: ``Cnr``.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    cl: float
    c_l_beta: float
    c_n_beta: float
    c_l_p: float
    c_n_p: float
    c_l_r: float
    c_n_r: float


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


def body_file_name(index: int) -> str:
    """The file name of the outline of body ``index``."""
    return f"body{index}.dat"


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
    margin = config().avl_contour_margin.value
    for x, _ in coordinates:
        if not -margin <= x <= 1.0 + margin:
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
    bodies: Sequence[MeshBody] = (),
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
        bodies: The fuselages as round bodies, each read from its own file
            (:func:`body_file_name`, :func:`aero_kernel.solvers.avl_body.body_file_text`).

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
            f"{surface.n_chord or n_chord}   {CHORD_SPACING}",
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
            for control in section.controls():
                lines += [
                    "CONTROL",
                    f"{control.name} {control.gain!r} {control.x_hinge!r} "
                    f"0.0 0.0 0.0 {control.sgn_dup}",
                ]
    for index, body in enumerate(bodies):
        lines += [
            "#" + "=" * 60,
            "BODY",
            body.name,
            "#Nbody  Bspace",
            f"{BODY_NODES}   {BODY_SPACING}",
            "TRANSLATE",
            f"{body.origin[0]!r} {body.origin[1]!r} {body.origin[2]!r}",
            "BFIL",
            body_file_name(index),
        ]
    return "\n".join(lines) + "\n"


def avl_commands(cl: float, core_ratio: float) -> str:
    """The OPER dialogue: vortex core ratio, ``C_L`` constraint, run, stability derivatives."""
    return f"oper\no\nc\n{core_ratio}\n\na c {cl!r}\nx\nst\n\n\nquit\n"


def avl_lateral_commands(
    cl: float, core_ratio: float, *, order: Sequence[str] = (), flap_deg: float = 0.0
) -> str:
    """The OPER dialogue of the lateral derivatives: ``C_L`` constraint, held flap, run, derivatives.

    The only control a lateral run holds is the symmetric flap of the configuration, at its
    deflection; a file without controls gives the plain dialogue of :func:`avl_commands`.

    Args:
        cl: The lift coefficient.
        core_ratio: The vortex core ratio.
        order: The control names in AVL's numbering (:func:`control_order`), flap only.
        flap_deg: The flap deflection in degrees.

    Returns:
        The command text.
    """
    held = "".join(f"d{index} d{index} {flap_deg!r}\n" for index, _ in enumerate(order, start=1))
    return f"oper\no\nc\n{core_ratio}\n\na c {cl!r}\n{held}x\nst\n\n\nquit\n"


def control_order(surfaces: Sequence[MeshSurface]) -> tuple[str, ...]:
    """The control variables of the file in AVL's numbering: the order of first appearance.

    AVL numbers its controls ``d1``, ``d2``, ... by the first CONTROL line that names them, scanning
    the surfaces and sections in file order, so the commands are built from the same scan that
    :func:`avl_geometry` writes.

    Args:
        surfaces: The mesh as written.

    Returns:
        The distinct control names, ``d1`` first.
    """
    names: list[str] = []
    for surface in surfaces:
        for section in surface.sections:
            for control in section.controls():
                if control.name not in names:
                    names.append(control.name)
    return tuple(names)


def avl_roll_commands(
    cl: float,
    core_ratio: float,
    delta_deg: float,
    *,
    order: Sequence[str] = (ROLL_CONTROL,),
    flap_deg: float = 0.0,
) -> str:
    """The OPER dialogue of a steady roll.

    Constrains ``C_L``, the stability-axis rolling moment to zero (``r rm 0``), the roll control to
    the command and a flap control to the flap deflection of the configuration, and runs: the roll
    rate is the result, in AVL's default stability axes (``avl.f:652``). Then it holds the roll rate
    (``r r 0``) and the roll control at zero with the flap unchanged, runs again and prints the
    stability derivatives of that state, from which the adapter forms the linearised roll rate
    ``-Cld0k * delta / Clp`` as a consistency check of the first result.

    Args:
        cl: The lift coefficient.
        core_ratio: The vortex core ratio.
        delta_deg: The roll command in degrees.
        order: The control names in AVL's numbering (:func:`control_order`).
        flap_deg: The flap deflection in degrees, for the flap control if the file has one.
    """

    def constraints(roll: str) -> str:
        values = {ROLL_CONTROL: roll, FLAP_CONTROL: f"{flap_deg!r}"}
        return "".join(
            f"d{index} d{index} {values[name]}\n" for index, name in enumerate(order, start=1)
        )

    return (
        f"oper\no\nc\n{core_ratio}\n\na c {cl!r}\nr rm 0\n{constraints(f'{delta_deg!r}')}x\n"
        f"r r 0\n{constraints('0')}x\nst\n\n\nquit\n"
    )


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


def parse_lateral_output(text: str) -> LateralOutput | None:
    """Read ``CLtot`` and the six lateral stability-axis derivatives from the output.

    Returns:
        The values, or ``None`` if one is missing (the run did not complete).
    """
    values = {key: _first(text, key) for key in ("CLtot", "Clb", "Cnb", "Clp", "Cnp", "Clr", "Cnr")}
    if any(value is None for value in values.values()):
        return None
    return LateralOutput.model_validate(
        {
            "cl": values["CLtot"],
            "c_l_beta": values["Clb"],
            "c_n_beta": values["Cnb"],
            "c_l_p": values["Clp"],
            "c_n_p": values["Cnp"],
            "c_l_r": values["Clr"],
            "c_n_r": values["Cnr"],
        }
    )


def parse_flap_echo(text: str) -> float | None:
    """The flap control deflection AVL echoes in degrees, or ``None`` if the output has none."""
    echo = re.search(rf"^\s*{re.escape(FLAP_CONTROL)}\s*=\s*{_NUMBER}", text, re.MULTILINE)
    return None if echo is None else float(echo.group(1))


def parse_roll_output(text: str, roll_index: int = 1) -> RollOutput | None:
    """Read ``p'b/2V``, ``CLtot``, ``Cl'tot`` and the control echo from a steady-roll run.

    The first hit of each key is taken: AVL also prints ``pb/2V`` (body axes) before ``p'b/2V``.

    Args:
        text: The output.
        roll_index: The roll control's number in AVL's numbering, which names its derivative
            ``Cld0<k>``.

    Returns:
        The values, or ``None`` if one is missing (the run did not complete).
    """
    p_hat, cl = _first(text, "p'b/2V"), _first(text, "CLtot")
    cl_stability = _first(text, "Cl'tot")
    echo = re.search(rf"^\s*{re.escape(CONTROL_NAME)}\s*=\s*{_NUMBER}", text, re.MULTILINE)
    cl_p, cl_delta = _first(text, "Clp"), _first(text, f"Cld{roll_index:02d}")
    if (
        p_hat is None
        or cl is None
        or cl_stability is None
        or echo is None
        or cl_p is None
        or cl_delta is None
    ):
        return None
    return RollOutput(
        p_hat=p_hat,
        cl=cl,
        cl_stability=cl_stability,
        control=float(echo.group(1)),
        cl_p=cl_p,
        cl_delta=cl_delta,
    )
