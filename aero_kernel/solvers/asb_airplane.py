"""The one conversion of the geometry format to an AeroSandbox airplane (ARCHITECTURE ch. 8.8).

Every adapter that needs an AeroSandbox airplane (the GEO properties, later AeroBuildup) calls
:func:`to_asb_airplane`; there is no second conversion (ADR 0022).
"""

import importlib
import logging
from typing import Any

import numpy as np
from aero_kernel.geometry import Airfoil, AirplaneGeometry, InlineAirfoil, Wing, WingXSec

logger = logging.getLogger(__name__)

__all__ = ["to_asb_airplane"]

# ``Any`` is the boundary to AeroSandbox, which ships no type information.


def _airfoil(asb: Any, airfoil: Airfoil) -> Any:  # noqa: ANN401  # untyped aerosandbox boundary
    """Convert a NACA designation or inline coordinates (Selig order, chord 1)."""
    if isinstance(airfoil, InlineAirfoil):
        return asb.Airfoil(name="inline", coordinates=np.array(airfoil.coordinates, dtype=float))
    return asb.Airfoil(name=airfoil)


def _section(asb: Any, section: WingXSec) -> Any:  # noqa: ANN401  # untyped aerosandbox boundary
    """Convert one rib.

    Control devices and the ``dihedral`` field are not passed: the airplane is built with every
    device at 0 deg (ch. 8.11), and ``xyz_le`` already carries the dihedral.
    """
    return asb.WingXSec(
        xyz_le=list(section.xyz_le),
        chord=section.chord,
        twist=section.twist,
        airfoil=_airfoil(asb, section.airfoil),
    )


def _wing(asb: Any, wing: Wing) -> Any:  # noqa: ANN401  # untyped aerosandbox boundary
    """Convert one lifting surface."""
    return asb.Wing(
        name=wing.name,
        xsecs=[_section(asb, section) for section in wing.x_secs],
        symmetric=wing.symmetric,
    )


def to_asb_airplane(airplane: AirplaneGeometry) -> Any:  # noqa: ANN401  # untyped aerosandbox boundary
    """Convert the wings of a geometry document to an ``asb.Airplane``.

    Metres and degrees as parsed (ch. 8.11). Fuselages are added with the first formula that
    needs them (ADR 0021). AeroSandbox is imported here; callers import it off the event loop
    first (ch. 8.10), so this import is a lookup.

    Args:
        airplane: The parsed geometry document.

    Returns:
        The ``asb.Airplane``, wings in document order.
    """
    asb = importlib.import_module("aerosandbox")
    wings = [_wing(asb, wing) for wing in (airplane.wings or {}).values()]
    logger.debug("converted airplane %s: %d wings", airplane.name, len(wings))
    return asb.Airplane(name=airplane.name, xyz_ref=list(airplane.xyz_ref), wings=wings)
