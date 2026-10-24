"""The one conversion of the geometry format to an AeroSandbox airplane (ARCHITECTURE ch. 8.8).

Every adapter that needs an AeroSandbox airplane (the GEO properties, later AeroBuildup) calls
:func:`to_asb_airplane`; there is no second conversion (ADR 0022).
"""

import importlib
import logging
from typing import Any

import numpy as np
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import (
    Airfoil,
    AirplaneGeometry,
    Fuselage,
    InlineAirfoil,
    Wing,
)
from aero_kernel.geometry_properties import main_wing_properties
from aero_kernel.graph import AILERON_ROLES
from aero_kernel.solvers.devices import roll_deflection, roll_segments
from aero_kernel.surface_chain import ChainPoint, oriented_chain

logger = logging.getLogger(__name__)

__all__ = ["load_aerosandbox", "to_asb_airplane"]

# ``Any`` is the boundary to AeroSandbox, which ships no type information.


def load_aerosandbox() -> Any:  # noqa: ANN401  # untyped aerosandbox boundary
    """Return the ``aerosandbox`` module, typed as the untyped boundary it is.

    Callers import it off the event loop first (ch. 8.10), or run in a pool worker, so this is a
    lookup.
    """
    return importlib.import_module("aerosandbox")


def _airfoil(asb: Any, airfoil: Airfoil) -> Any:  # noqa: ANN401  # untyped aerosandbox boundary
    """Convert a NACA designation or inline coordinates (Selig order, chord 1)."""
    if isinstance(airfoil, InlineAirfoil):
        return asb.Airfoil(name="inline", coordinates=np.array(airfoil.coordinates, dtype=float))
    return asb.Airfoil(name=airfoil)


def _section(
    asb: Any,  # noqa: ANN401  # untyped aerosandbox boundary
    point: ChainPoint,
    roll_deg: float,
    label: str,
) -> Any:  # noqa: ANN401  # untyped aerosandbox boundary
    """Convert one rib of an oriented chain.

    The geometry's own control-device state and the ``dihedral`` field are not passed: the airplane
    is built with every device at 0 deg (ch. 8.11), and ``xyz_le`` already carries the dihedral.
    Only the roll command makes a control surface: the rib that starts a roll segment gets one
    antisymmetric surface at the mean of the segment's hinge positions, ASB's convention for the
    strip a -> a+1. A mirrored surface is written on the positive side, root first, as the AVL
    writer writes it, so the sign of the deflection is that of side +1 in both tools.
    """
    kwargs: dict[str, Any] = {
        "xyz_le": [point.x, point.y, point.z],
        "chord": point.chord,
        "twist": point.twist,
        "airfoil": _airfoil(asb, point.airfoil),
    }
    device = point.device
    if roll_deg and device is not None and device.role in AILERON_ROLES:
        if device.hinge_start is None or device.hinge_end is None:
            msg = "a driven device without a hinge: roll_segments must have refused it"
            raise ValueError(msg)
        kwargs["control_surfaces"] = [
            asb.ControlSurface(
                name=device.name or label,
                symmetric=False,
                hinge_point=(device.hinge_start + device.hinge_end) / 2.0,
                deflection=roll_deflection(1, roll_deg),
            )
        ]
    return asb.WingXSec(**kwargs)


def _wing(
    asb: Any,  # noqa: ANN401  # untyped aerosandbox boundary
    key: str,
    wing: Wing,
    roll_deg: float,
) -> Any:  # noqa: ANN401  # untyped aerosandbox boundary
    """Convert one lifting surface.

    A mirrored surface is built from the oriented chain (root first, y >= 0), the one orientation
    rule of the kernel: ASB mirrors a surface stored on the other side or tip first into a
    different wing (BRYAN: C_D 0.246 against 0.070). An unmirrored surface keeps its stored order.
    """
    if wing.symmetric:
        chain = oriented_chain(wing, 1)
    else:
        chain = [
            ChainPoint(
                x=s.xyz_le[0],
                y=s.xyz_le[1],
                z=s.xyz_le[2],
                chord=s.chord,
                twist=s.twist,
                airfoil=s.airfoil,
            )
            for s in wing.x_secs
        ]
    return asb.Wing(
        name=wing.name,
        xsecs=[
            _section(asb, point, roll_deg, f"{key} device {index}")
            for index, point in enumerate(chain)
        ],
        symmetric=wing.symmetric,
    )


def _unsupported(message: str, hint: str, name: str) -> FormulaError:
    """The error of a fuselage ASB cannot represent without a silent substitution (ADR 0020)."""
    return FormulaError(
        ErrorCategory.UNSUPPORTED_CONFIGURATION,
        "unsupported_configuration",
        message,
        hint,
        detail={"fuselage": name},
        parameter="airplane",
    )


def _fuselage(asb: Any, fuselage: Fuselage) -> Any:  # noqa: ANN401  # untyped aerosandbox boundary
    """Convert one fuselage: super-ellipse sections, ``a`` and ``b`` as half width and height.

    ASB takes the full width and height, one shape exponent per section and no mirrored body, so
    ``n_lower`` different from ``n`` and ``symmetric`` bodies are refused rather than approximated.
    A section of size 0 (the nose or tail point of a lofted body) is accepted by ASB.
    """
    if fuselage.symmetric:
        raise _unsupported(
            f"the fuselage {fuselage.name!r} is mirrored; AeroSandbox has no mirrored body",
            "give both halves as separate fuselages, or one body on the centreline",
            fuselage.name,
        )
    sections: list[Any] = []
    for index, section in enumerate(fuselage.x_secs):
        if section.n_lower is not None and section.n_lower != section.n:
            raise _unsupported(
                f"section {index} of the fuselage {fuselage.name!r} has n_lower != n; "
                "AeroSandbox has one shape exponent per section",
                "use one exponent n for the whole section",
                fuselage.name,
            )
        sections.append(
            asb.FuselageXSec(
                xyz_c=list(section.xyz),
                width=2.0 * section.a,
                height=2.0 * section.b,
                shape=section.n,
            )
        )
    return asb.Fuselage(name=fuselage.name, xsecs=sections)


def to_asb_airplane(airplane: AirplaneGeometry, roll_deg: float = 0.0) -> Any:  # noqa: ANN401  # untyped aerosandbox boundary
    """Convert a geometry document to an ``asb.Airplane``.

    Metres and degrees as parsed (ch. 8.11). The reference area, span and chord of the airplane
    are the kernel's own (:func:`main_wing_properties`, projected onto the x-y plane), so ASB
    normalises its coefficients by the one reference area the canon names (ADR 0022); ASB's
    default is the planform area. AeroSandbox is imported here; callers import it off the event
    loop first (ch. 8.10), so this import is a lookup.

    Args:
        airplane: The validated geometry document (exactly one main wing).
        roll_deg: The aileron command in degrees, positive = roll to the right (ch. 8.8). Zero
            builds the clean airplane, bit for bit; otherwise every segment with a roll device
            gets one antisymmetric control surface (:func:`roll_segments`).

    Returns:
        The ``asb.Airplane``, wings and fuselages in document order.

    Raises:
        ValueError: If the document does not have exactly one main wing.
        FormulaError: ``unsupported_configuration`` for a fuselage ASB cannot represent, a roll
            device on an unmirrored wing, or a mirrored wing whose sections fold back along y
            (the oriented chain refuses it); ``invalid_input`` for a roll device without a hinge.
    """
    asb = load_aerosandbox()
    reference = main_wing_properties(airplane)
    if roll_deg:
        roll_segments(airplane)  # the shared rules: mirrored surface, hinge given
    wings = [_wing(asb, key, wing, roll_deg) for key, wing in (airplane.wings or {}).items()]
    fuselages = [_fuselage(asb, fuselage) for fuselage in (airplane.fuselages or {}).values()]
    logger.debug(
        "converted airplane %s: %d wings, %d fuselages", airplane.name, len(wings), len(fuselages)
    )
    return asb.Airplane(
        name=airplane.name,
        xyz_ref=list(airplane.xyz_ref),
        wings=wings,
        fuselages=fuselages,
        s_ref=reference.s_ref,
        b_ref=reference.b_ref,
        c_ref=reference.c_mac,
    )
