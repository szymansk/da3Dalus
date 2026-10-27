"""The one conversion of the geometry format to an AeroSandbox airplane (ARCHITECTURE ch. 8.8).

Every adapter that needs an AeroSandbox airplane (the GEO properties, later AeroBuildup) calls
:func:`to_asb_airplane`; there is no second conversion (ADR 0022). The reference values of the
main wing are AeroSandbox's own, read from the wing this conversion builds (:func:`main_wing_properties`).
"""

import importlib
import logging
import math
from typing import Any

import numpy as np
from aero_kernel.config import config
from aero_kernel.devices import FLAP_ROLES
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import (
    Airfoil,
    AirplaneGeometry,
    Fuselage,
    FuselageXSecSuperEllipse,
    InlineAirfoil,
    Wing,
)
from aero_kernel.geometry_properties import MainWingProperties, SurfaceProperties
from aero_kernel.graph import AILERON_ROLES
from aero_kernel.solvers.devices import flap_segments, roll_deflection, roll_segments
from aero_kernel.superellipse import equivalent_exponent
from aero_kernel.surface_chain import ChainPoint, oriented_chain

logger = logging.getLogger(__name__)

# The flags of every ASB area and span call: set here, never left to ASB's defaults (gh-1262).
# ``area`` measures the lofted planform and ``span`` the y-z extent, both carried to the centreline
# plane: a root off y = 0 is extruded to it with the wing's geometric chord, as the reference wing
# runs through the fuselage (Scholz, Wing Design 7.1).
AREA_TYPE = "planform"
SPAN_TYPE = "yz"
INCLUDE_CENTRELINE = True

# The aerodynamic centre of a surface lies at a quarter of its mean aerodynamic chord.
AC_FRACTION = 0.25

__all__ = [
    "AC_FRACTION",
    "load_aerosandbox",
    "main_wing_properties",
    "quarter_chord_mac_x",
    "surface_properties",
    "to_asb_airplane",
]

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


def _flap_state(point: ChainPoint, drive_flaps: bool) -> tuple[float, float] | None:
    """The deflection and the mean hinge of the flap on the strip that starts at ``point``, if any."""
    device = point.device
    if not (drive_flaps and device is not None and device.role in FLAP_ROLES):
        return None
    if not device.deflection_deg:
        return None
    if device.hinge_start is None or device.hinge_end is None:
        msg = "a driven device without a hinge: flap_segments must have refused it"
        raise ValueError(msg)
    return device.deflection_deg, (device.hinge_start + device.hinge_end) / 2.0


def _deflected(
    asb: Any,  # noqa: ANN401  # untyped aerosandbox boundary
    airfoil: Any,  # noqa: ANN401  # untyped aerosandbox boundary
    flap: tuple[float, float],
) -> Any:  # noqa: ANN401  # untyped aerosandbox boundary
    """The airfoil with its trailing edge rotated about the hinge: the geometry of a plain flap.

    ``Airfoil.add_control_surface`` rotates the contour behind the hinge (trailing edge down
    positive). The result is rebuilt as a plain airfoil from those coordinates, so that
    AeroBuildup's NeuralFoil call normalises the deflected contour to its leading-edge to
    trailing-edge chord and corrects the angle of attack by the rotation (a deflected contour is no
    control surface: its ``ControlSurface.deflection`` stays 0, so the Hoerner drag factor is 1 and
    nothing is counted twice).
    """
    deflection, hinge = flap
    shaped = airfoil.add_control_surface(deflection=deflection, hinge_point_x=hinge)
    return asb.Airfoil(name=f"{airfoil.name} flap {deflection:g}", coordinates=shaped.coordinates)


def _xsec(
    asb: Any,  # noqa: ANN401  # untyped aerosandbox boundary
    point: ChainPoint,
    flap: tuple[float, float] | None,
    *,
    starts_strip: bool,
    roll_deg: float,
    label: str,
) -> Any:  # noqa: ANN401  # untyped aerosandbox boundary
    """Convert one rib of an oriented chain.

    The geometry's ``dihedral`` field and the aerodynamic view's deflection are not passed:
    ``xyz_le`` already carries the dihedral. A deflected flap (``flap``) is the airfoil's geometry
    (:func:`_deflected`), not a control surface. The roll command makes the only control surface: on
    the rib that starts a roll segment, one antisymmetric surface at the mean of the segment's hinge
    positions, ASB's convention for the strip a -> a+1 (``tau * delta``). A flaperon has both: the
    flap deflection is the geometric symmetric bias and the roll command comes on top. A mirrored
    surface is written on the positive side, root first, as the AVL writer writes it, so the sign of
    the deflection is that of side +1 in both tools.
    """
    airfoil = _airfoil(asb, point.airfoil)
    if flap is not None:
        airfoil = _deflected(asb, airfoil, flap)
    kwargs: dict[str, Any] = {
        "xyz_le": [point.x, point.y, point.z],
        "chord": point.chord,
        "twist": point.twist,
        "airfoil": airfoil,
    }
    device = point.device
    if starts_strip and roll_deg and device is not None and device.role in AILERON_ROLES:
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


def _xsecs(
    asb: Any,  # noqa: ANN401  # untyped aerosandbox boundary
    key: str,
    chain: list[ChainPoint],
    roll_deg: float,
    drive_flaps: bool,
) -> list[Any]:
    """The cross-sections of a chain; a rib between two strips of different flap state is two.

    AeroBuildup blends the airfoil of the two bounding sections linearly over a strip and takes a
    section's control surfaces for the strip that starts there. A deflected airfoil must therefore
    sit on both sections of its strip and on no section of the next one: the rib where the flap
    state changes is written twice at the same place, first as the end of the strip before and then
    as the start of the strip after (a strip of zero width between them).
    """
    last = len(chain) - 1
    xsecs: list[Any] = []
    for index, point in enumerate(chain):
        label = f"{key} device {index}"
        starting = _flap_state(point, drive_flaps) if index < last else None
        ending = _flap_state(chain[index - 1], drive_flaps) if index else None
        if 0 < index < last and starting != ending:
            xsecs.append(
                _xsec(asb, point, ending, starts_strip=False, roll_deg=roll_deg, label=label)
            )
            later = point.model_copy(update={"y": point.y + config().opt_flap_rib_gap.value})
            xsecs.append(
                _xsec(asb, later, starting, starts_strip=True, roll_deg=roll_deg, label=label)
            )
        else:
            xsecs.append(
                _xsec(
                    asb,
                    point,
                    starting if index < last else ending,
                    starts_strip=index < last,
                    roll_deg=roll_deg,
                    label=label,
                )
            )
    return xsecs


def _wing(
    asb: Any,  # noqa: ANN401  # untyped aerosandbox boundary
    key: str,
    wing: Wing,
    roll_deg: float,
    drive_flaps: bool = False,
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
        xsecs=_xsecs(asb, key, chain, roll_deg, drive_flaps),
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


def _fuselage_section(asb: Any, section: FuselageXSecSuperEllipse) -> Any:  # noqa: ANN401  # untyped aerosandbox boundary
    """Convert one super-ellipse section: width ``2a``, height ``2b``, one shape exponent.

    A section with two exponents becomes the symmetric section of the same width, height and centre
    whose exponent keeps the cross-section area (:func:`equivalent_exponent`, gh-1307); input
    validation declares the substitution (``fuselage_section_equivalent``).
    """
    shape = section.n
    if section.n_lower is not None:
        shape = equivalent_exponent(section.n, section.n_lower)
    return asb.FuselageXSec(
        xyz_c=list(section.xyz),
        width=2.0 * section.a,
        height=2.0 * section.b,
        shape=shape,
    )


def _fuselage(asb: Any, fuselage: Fuselage) -> Any:  # noqa: ANN401  # untyped aerosandbox boundary
    """Convert one fuselage: super-ellipse sections, ``a`` and ``b`` as half width and height.

    ASB takes the full width and height, one shape exponent per section and no mirrored body, so a
    ``symmetric`` body is refused rather than approximated; a section with ``n_lower`` different
    from ``n`` is mapped to its equivalent symmetric section (:func:`_fuselage_section`).
    A section of size 0 (the nose or tail point of a lofted body) is accepted by ASB.
    """
    if fuselage.symmetric:
        raise _unsupported(
            f"the fuselage {fuselage.name!r} is mirrored; AeroSandbox has no mirrored body",
            "give both halves as separate fuselages, or one body on the centreline",
            fuselage.name,
        )
    sections = [_fuselage_section(asb, section) for section in fuselage.x_secs]
    return asb.Fuselage(name=fuselage.name, xsecs=sections)


def _main_wing_key(airplane: AirplaneGeometry) -> str:
    """Key of the one wing with ``surface_type`` ``main_wing``, never the first wing in the list.

    Raises:
        ValueError: If the document does not have exactly one main wing (a defect: validation
            reports ``main_wing_count`` as the user-facing error).
    """
    keys = [k for k, w in (airplane.wings or {}).items() if w.surface_type == "main_wing"]
    if len(keys) != 1:
        msg = f"validated input has exactly one main wing, got {len(keys)}"
        raise ValueError(msg)
    return keys[0]


def _surface(wing: Any, aerodynamic_center_x: float) -> SurfaceProperties:  # noqa: ANN401  # untyped aerosandbox boundary
    """AeroSandbox's planform values of a wing, as ``asb.Airplane`` takes them for its reference.

    Area and span both include the centreline gap, with ``type`` and ``include_centerline_distance``
    passed explicitly (gh-1262). This holds for every surface that goes through here, the main wing
    and the tail alike: a mirrored surface is a reference surface carried through the fuselage to
    the centreline, and for a root on y = 0 the flag changes nothing. The aspect ratio is
    ``span^2 / area`` of those two, and the leading edge of the MAC is the aerodynamic centre less
    a quarter of the MAC (the same MAC definition, gh-1253); ``mean_aerodynamic_chord()`` and
    ``aerodynamic_center()`` take no flag.

    Raises:
        FormulaError: ``unsupported_configuration`` if area, span or MAC is not a positive finite
            number (a wing with no planform, e.g. all its sections at one y).
    """
    area = float(wing.area(type=AREA_TYPE, include_centerline_distance=INCLUDE_CENTRELINE))
    span = float(wing.span(type=SPAN_TYPE, include_centerline_distance=INCLUDE_CENTRELINE))
    c_mac = float(wing.mean_aerodynamic_chord())
    if not all(math.isfinite(v) and v > 0.0 for v in (area, span, c_mac)):
        raise FormulaError(
            ErrorCategory.UNSUPPORTED_CONFIGURATION,
            "unsupported_configuration",
            f"the wing {wing.name!r} has no planform: AeroSandbox gives area {area}, span {span}, "
            f"mean aerodynamic chord {c_mac}",
            "a wing needs sections at different y; a vertical surface has no planform",
            detail={"wing": str(wing.name)},
            parameter="airplane",
        )
    return SurfaceProperties(
        area=area,
        span=span,
        aspect_ratio=span**2 / area,
        c_mac=c_mac,
        x_le_mac=aerodynamic_center_x - AC_FRACTION * c_mac,
    )


def _reference(wing: Any) -> MainWingProperties:  # noqa: ANN401  # untyped aerosandbox boundary
    """AeroSandbox's reference values of a wing: what ``asb.Airplane`` infers from its first wing."""
    surface = _surface(wing, 0.0)
    return MainWingProperties(s_ref=surface.area, b_ref=surface.span, c_mac=surface.c_mac)


def surface_properties(airplane: AirplaneGeometry, key: str) -> SurfaceProperties:
    """Return AeroSandbox's planform values of the wing stored under ``key``.

    The wing is converted like in :func:`to_asb_airplane`; ``x_le_MAC`` is
    ``Wing.aerodynamic_center()[0] - 0.25 c_MAC`` (gh-1253).

    Args:
        airplane: The validated geometry document.
        key: The key of the wing in ``airplane.wings``.

    Returns:
        Area, span, aspect ratio, MAC and the MAC's leading edge, in m^2, m, 1, m, m.

    Raises:
        FormulaError: As :func:`_wing` and :func:`_surface`.
    """
    wing = _wing(load_aerosandbox(), key, (airplane.wings or {})[key], 0.0)
    return _surface(wing, float(wing.aerodynamic_center()[0]))


def quarter_chord_mac_x(airplane: AirplaneGeometry, key: str) -> float:
    """Return x of the quarter-chord MAC of the wing stored under ``key``, as AeroSandbox measures it.

    ``Wing.aerodynamic_center(chord_fraction=0.25)[0]`` of the wing converted like in
    :func:`to_asb_airplane` (gh-1272). Unlike :func:`surface_properties` it asks for no area or
    span, so it also serves a vertical surface, whose projected planform is empty.

    Args:
        airplane: The validated geometry document.
        key: The key of the wing in ``airplane.wings``.

    Returns:
        x in m, in the geometry frame, aft positive.

    Raises:
        FormulaError: As :func:`_wing`; ``unsupported_configuration`` if ASB gives no finite x.
    """
    wing = _wing(load_aerosandbox(), key, (airplane.wings or {})[key], 0.0)
    x = float(wing.aerodynamic_center(chord_fraction=AC_FRACTION)[0])
    if not math.isfinite(x):
        raise FormulaError(
            ErrorCategory.UNSUPPORTED_CONFIGURATION,
            "unsupported_configuration",
            f"the wing {wing.name!r} has no aerodynamic centre: AeroSandbox gives x = {x}",
            "a wing needs sections with a non-zero area; check its chords and positions",
            detail={"wing": str(wing.name)},
            parameter="airplane",
        )
    return x


def main_wing_properties(airplane: AirplaneGeometry) -> MainWingProperties:
    """Return AeroSandbox's ``S_ref``, ``b_ref`` and ``c_MAC`` of the one wing of type ``main_wing``.

    The wing is converted like in :func:`to_asb_airplane` and measured with
    ``Wing.area(type="planform", include_centerline_distance=True)``,
    ``Wing.span(type="yz", include_centerline_distance=True)`` and ``Wing.mean_aerodynamic_chord()``
    (maintainer, 2026-10-25, gh-1262).

    Args:
        airplane: The validated geometry document, which has exactly one main wing.

    Returns:
        The three reference values in m^2, m and m.

    Raises:
        ValueError: If the document does not have exactly one main wing.
        FormulaError: As :func:`_wing` and :func:`_surface`.
    """
    asb = load_aerosandbox()
    key = _main_wing_key(airplane)
    return _reference(_wing(asb, key, (airplane.wings or {})[key], 0.0))


def to_asb_airplane(airplane: AirplaneGeometry, roll_deg: float = 0.0) -> Any:  # noqa: ANN401  # untyped aerosandbox boundary
    """Convert a geometry document to an ``asb.Airplane``.

    Metres and degrees as parsed (ch. 8.11). The reference area, span and chord of the airplane
    are AeroSandbox's own values of the main wing (:func:`main_wing_properties`), chosen by
    ``surface_type`` and not by list position as ASB's default would, so ASB normalises its
    coefficients by the one reference area the canon names (ADR 0022). AeroSandbox is imported here; callers import it off the event
    loop first (ch. 8.10), so this import is a lookup.

    Args:
        airplane: The validated geometry document (exactly one main wing).
        roll_deg: The aileron command in degrees, positive = roll to the right (ch. 8.8). Zero
            adds no roll surface; otherwise every segment with a roll device gets one
            antisymmetric control surface (:func:`roll_segments`). The airplane's deflected flaps
            (:func:`flap_segments`) are always built in, as the deflected contour of the flapped
            strip's airfoils (:func:`_xsecs`); an airplane with every device at rest and no command
            is the clean airplane, bit for bit.

    Returns:
        The ``asb.Airplane``, wings and fuselages in document order.

    Raises:
        ValueError: If the document does not have exactly one main wing.
        FormulaError: ``unsupported_configuration`` for a fuselage ASB cannot represent, a roll
            device or a deflected flap on an unmirrored wing, or a mirrored wing whose sections fold
            back along y (the oriented chain refuses it); ``invalid_input`` for a roll device or a
            deflected flap without a hinge.
    """
    asb = load_aerosandbox()
    main_key = _main_wing_key(airplane)
    if roll_deg:
        roll_segments(airplane)  # the shared rules: mirrored surface, hinge given
    flaps = flap_segments(airplane)  # the same rules for a deflected flap
    built = {
        key: _wing(asb, key, wing, roll_deg, drive_flaps=True)
        for key, wing in (airplane.wings or {}).items()
    }
    # the reference is the planform of the wing without the extra ribs of a flap
    reference = _reference(
        _wing(asb, main_key, (airplane.wings or {})[main_key], 0.0) if flaps else built[main_key]
    )
    wings = list(built.values())
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
