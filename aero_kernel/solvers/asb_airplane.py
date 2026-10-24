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
    WingXSec,
)
from aero_kernel.geometry_properties import main_wing_properties
from aero_kernel.solvers.devices import RollSegment, roll_deflection, roll_segments

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
    section: WingXSec,
    roll: RollSegment | None,
    roll_deg: float,
) -> Any:  # noqa: ANN401  # untyped aerosandbox boundary
    """Convert one rib.

    The geometry's own control-device state and the ``dihedral`` field are not passed: the airplane
    is built with every device at 0 deg (ch. 8.11), and ``xyz_le`` already carries the dihedral.
    Only the roll command makes a control surface: the rib that starts a roll segment gets one
    antisymmetric surface at the segment's hinge, ASB's convention for the strip a -> a+1.
    """
    kwargs: dict[str, Any] = {
        "xyz_le": list(section.xyz_le),
        "chord": section.chord,
        "twist": section.twist,
        "airfoil": _airfoil(asb, section.airfoil),
    }
    if roll is not None:
        kwargs["control_surfaces"] = [
            asb.ControlSurface(
                name=roll.device,
                symmetric=False,
                hinge_point=roll.hinge,
                deflection=roll_deflection(roll.side, roll_deg),
            )
        ]
    return asb.WingXSec(**kwargs)


def _wing(
    asb: Any,  # noqa: ANN401  # untyped aerosandbox boundary
    key: str,
    wing: Wing,
    rolls: dict[tuple[str, int], RollSegment],
    roll_deg: float,
) -> Any:  # noqa: ANN401  # untyped aerosandbox boundary
    """Convert one lifting surface."""
    return asb.Wing(
        name=wing.name,
        xsecs=[
            _section(asb, section, rolls.get((key, index)), roll_deg)
            for index, section in enumerate(wing.x_secs)
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
        FormulaError: ``unsupported_configuration`` for a fuselage ASB cannot represent or a roll
            device on an unmirrored wing; ``invalid_input`` for a roll device without a hinge.
    """
    asb = load_aerosandbox()
    reference = main_wing_properties(airplane)
    rolls = {(r.wing, r.index): r for r in roll_segments(airplane)} if roll_deg else {}
    wings = [_wing(asb, key, wing, rolls, roll_deg) for key, wing in (airplane.wings or {}).items()]
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
