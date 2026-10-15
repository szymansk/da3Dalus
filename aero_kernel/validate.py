"""Physical admissibility of the input (ARCHITECTURE ch. 8.11, step 1 of a ``compute()`` call).

The input models carry types only; a well-typed but physically inadmissible value (NaN, a
negative chord) parses and is reported here as an ``invalid_input`` :class:`KernelError` with a
dotted ``input_path``, never raised. The facts of the input that are not errors (a mass that
differs from the geometry's, a geometry deflection the kernel ignores) come back as warnings.
Regime (Re, Mach) is not validated (ch. 8.2) and the stops of control devices are never read
(ch. 8.11).

A check exists only for a field the kernel reads: CAD-only fields (servo, spars, turbulator,
spacings, stops) are in :data:`UNREAD_FIELDS` and skipped.
"""

import json
import logging
import math
import re
from collections.abc import Mapping
from itertools import pairwise
from typing import cast

from aero_kernel import geometry
from aero_kernel.errors import ErrorCategory, KernelError
from aero_kernel.geometry import Wing
from aero_kernel.schema import WARNING_CATALOGUE, AircraftInput, KernelWarning
from pydantic import BaseModel, ConfigDict, JsonValue

logger = logging.getLogger(__name__)

__all__ = ["UNREAD_FIELDS", "Validation", "validate_aircraft"]


class Validation(BaseModel):
    """The outcome of validating an aircraft input (ch. 8.11).

    Attributes:
        errors: Every ``invalid_input`` finding, in document order and then by ``values`` slug.
        warnings: Facts of the input the caller should know; the engine attaches them to the
            quantities that depend on them.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    errors: tuple[KernelError, ...] = ()
    warnings: tuple[KernelWarning, ...] = ()


# Fields no kernel formula reads (ch. 8.11); a finding on them would be noise. A device's
# ``control_surface`` is read for its deflection only (to report an ignored one); the stops
# (``*_deflection_deg``) are never read.
UNREAD_FIELDS: Mapping[type[BaseModel], frozenset[str]] = {
    geometry.Servo: frozenset(geometry.Servo.model_fields),
    geometry.SpareDetail: frozenset(geometry.SpareDetail.model_fields),
    geometry.Turbulator: frozenset(geometry.Turbulator.model_fields),
    geometry.ControlSurface: frozenset(geometry.ControlSurface.model_fields) - {"deflection"},
    geometry.TrailingEdgeDevice: frozenset(
        {
            "servo",
            "hinge_spacing_m",
            "side_spacing_root_m",
            "side_spacing_tip_m",
            "positive_deflection_deg",
            "negative_deflection_deg",
            "trailing_edge_offset_factor",
        }
    ),
}

_SLUG_KEY = re.compile(r"[a-z][a-z0-9]*(-[a-z0-9]+)*")


def _key_path(parent: str, key: str) -> str:
    """Extend a path by a dict key: ``parent["key"]``, the key JSON-escaped, unicode kept."""
    return f"{parent}[{json.dumps(key, ensure_ascii=False)}]"


def _values_path(slug: str) -> str:
    """Path of a ``values`` entry: dotted for a canon slug, bracketed for any other key."""
    if _SLUG_KEY.fullmatch(slug):
        return f"values.{slug}"
    return _key_path("values", slug)


def _finding(code: str, path: str, message: str, hint: str) -> KernelError:
    """Build an ``invalid_input`` error at ``path``."""
    logger.debug("finding %s at %s", code, path)
    return KernelError(
        code=code,
        category=ErrorCategory.INVALID_INPUT,
        input_path=path,
        message=message,
        hint=hint,
    )


def _non_finite(node: object, path: str) -> list[KernelError]:
    """Find every NaN or infinite number below ``node`` that the kernel reads."""
    if isinstance(node, float):
        if math.isfinite(node):
            return []
        return [
            _finding(
                "non_finite_number",
                path,
                f"Value at {path} is {node}; it must be a finite number.",
                f"Give {path} a finite value.",
            )
        ]
    findings: list[KernelError] = []
    if isinstance(node, BaseModel):
        unread = UNREAD_FIELDS.get(type(node), frozenset())
        for name in type(node).model_fields:
            if name not in unread:
                findings += _non_finite(getattr(node, name), f"{path}.{name}")
    elif isinstance(node, dict):
        # isinstance narrows a generic dict to dict[Unknown, Unknown]; only its keys' text is used
        for key, item in cast("dict[object, object]", node).items():
            findings += _non_finite(item, _key_path(path, str(key)))
    elif isinstance(node, tuple):
        # same narrowing as for dict above
        for index, item in enumerate(cast("tuple[object, ...]", node)):
            findings += _non_finite(item, f"{path}[{index}]")
    return findings


def _not_positive(
    value: float, path: str, code: str, what: str, unit: str, hint: str
) -> list[KernelError]:
    """Report ``value`` if it is finite and ``<= 0`` (a non-finite value is reported elsewhere)."""
    if not math.isfinite(value) or value > 0:
        return []
    message = f"{what} at {path} is {value} {unit}; it must be > 0."
    return [_finding(code, path, message, hint)]


def _name_mismatch(kind: str, key: str, name: str, path: str) -> list[KernelError]:
    """Report a ``name`` that differs from the dict key it is stored under."""
    if name == key:
        return []
    message = f"The name {name!r} of {kind} {key!r} differs from its key; the key is the identity."
    return [_finding("name_mismatch", f"{path}.name", message, f"Rename it to {key!r}.")]


_NACA = re.compile(r"naca(?P<digits>\d{4,5})", re.IGNORECASE)


def _interpolate(curve: list[tuple[float, float]], x: float) -> float:
    """Linearly interpolate ``y`` at ``x`` on a curve sorted by x; constant outside its range."""
    if x <= curve[0][0]:
        return curve[0][1]
    for (x0, y0), (x1, y1) in pairwise(curve):
        if x <= x1:
            # x > x0 here: an earlier pair would have caught x <= x0, so x1 > x0
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return curve[-1][1]


def _contour_thickness(points: tuple[tuple[float, float], ...]) -> float:
    """Maximum thickness (upper minus lower, chord fractions) of a Selig-ordered contour.

    The contour runs trailing edge, upper surface, leading edge (smallest x), lower surface,
    trailing edge. The lower surface is interpolated at the stations of the upper one.
    """
    leading_edge = min(range(len(points)), key=lambda index: points[index][0])
    upper = sorted(points[: leading_edge + 1])
    lower = sorted(points[leading_edge:])
    return max(y - _interpolate(lower, x) for x, y in upper)


def _airfoil_findings(airfoil: geometry.Airfoil, path: str) -> list[KernelError]:
    """Check an airfoil: a resolvable designation or a closed contour with positive thickness."""
    if isinstance(airfoil, str):
        match = _NACA.fullmatch(airfoil)
        if match is None:
            return [
                _finding(
                    "unresolved_airfoil",
                    path,
                    f"Airfoil {airfoil!r} is not a NACA 4- or 5-digit designation and the "
                    "kernel loads no files.",
                    "Pass a designation such as 'naca2412', or inline coordinates.",
                )
            ]
        if int(match["digits"][-2:]) == 0:
            return [
                _finding(
                    "non_positive_thickness",
                    path,
                    f"Airfoil {airfoil!r} has a thickness of 0 chord fractions; it must be > 0.",
                    "Use a designation with a thickness above 00.",
                )
            ]
        return []
    points = airfoil.coordinates
    coordinates_path = f"{path}.coordinates"
    findings: list[KernelError] = []
    if len(points) < 3 or points[0] != points[-1]:
        findings.append(
            _finding(
                "open_airfoil_contour",
                coordinates_path,
                f"The airfoil contour at {coordinates_path} has {len(points)} point(s) and "
                "its first and last point differ; it must be closed with at least 3 points.",
                "End the contour on its first point (Selig order, trailing edge to trailing edge).",
            )
        )
    if len(points) >= 3 and all(math.isfinite(c) for point in points for c in point):
        thickness = _contour_thickness(points)
        if thickness <= 0:
            findings.append(
                _finding(
                    "non_positive_thickness",
                    coordinates_path,
                    f"The airfoil at {coordinates_path} has a maximum thickness of {thickness} "
                    "chord fractions; it must be > 0.",
                    "Give the upper surface (first half of the contour) above the lower one.",
                )
            )
    return findings


def _section_findings(x_sec: geometry.WingXSec, path: str, *, is_last: bool) -> list[KernelError]:
    """Check one rib: positive chord, no segment details on the last, no orphan control surface."""
    findings = _not_positive(
        x_sec.chord,
        f"{path}.chord",
        "non_positive_length",
        "Chord",
        "m",
        "Give the chord a length > 0.",
    )
    findings += _airfoil_findings(x_sec.airfoil, f"{path}.airfoil")
    if is_last:
        details = {
            "trailing_edge_device": x_sec.trailing_edge_device,
            "spare_list": x_sec.spare_list,
            "turbulator": x_sec.turbulator,
        }
        for field, detail in details.items():
            if detail is not None:
                findings.append(
                    _finding(
                        "segment_on_last_section",
                        f"{path}.{field}",
                        f"The last section carries {field}, but it ends the wing and has no "
                        "segment outboard of it.",
                        f"Move {field} to the section where its segment starts, or remove it.",
                    )
                )
    if x_sec.control_surface is not None and x_sec.trailing_edge_device is None:
        findings.append(
            _finding(
                "control_surface_without_device",
                f"{path}.control_surface",
                "A control surface is given on a section without a trailing-edge device; the "
                "kernel takes role and hinge from the device.",
                "Add a trailing_edge_device to the same section.",
            )
        )
    return findings


def _wing_findings(wings: Mapping[str, Wing]) -> list[KernelError]:
    """Check the wings: name, section count and each section."""
    findings: list[KernelError] = []
    for key, wing in wings.items():
        wing_path = _key_path("airplane.wings", key)
        findings += _name_mismatch("wing", key, wing.name, wing_path)
        if len(wing.x_secs) < 2:
            findings.append(
                _finding(
                    "too_few_sections",
                    f"{wing_path}.x_secs",
                    f"Wing {key!r} has {len(wing.x_secs)} section(s); a wing needs at least 2.",
                    "Give the wing a root and a tip section.",
                )
            )
        last = len(wing.x_secs) - 1
        for index, x_sec in enumerate(wing.x_secs):
            findings += _section_findings(
                x_sec, f"{wing_path}.x_secs[{index}]", is_last=index == last
            )
    return findings


def _fuselage_findings(fuselages: Mapping[str, geometry.Fuselage]) -> list[KernelError]:
    """Check the fuselages: name and positive semi-axes."""
    findings: list[KernelError] = []
    for key, fuselage in fuselages.items():
        path = _key_path("airplane.fuselages", key)
        findings += _name_mismatch("fuselage", key, fuselage.name, path)
        for index, x_sec in enumerate(fuselage.x_secs):
            for axis, size in (("a", x_sec.a), ("b", x_sec.b)):
                findings += _not_positive(
                    size,
                    f"{path}.x_secs[{index}].{axis}",
                    "non_positive_length",
                    "Semi-axis",
                    "m",
                    "Give the semi-axis a length > 0.",
                )
    return findings


# slug -> (code, quantity name, unit) of the values that must be positive (ch. 8.11)
_POSITIVE_VALUES: Mapping[str, tuple[str, str, str]] = {
    "aircraft-mass": ("non_positive_mass", "Mass", "kg"),
    "sea-level-air-density": ("non_positive_density", "Density", "kg/m^3"),
}


def _value_findings(values: Mapping[str, float]) -> list[KernelError]:
    """Check the passed values: mass and density must be positive."""
    findings: list[KernelError] = []
    for slug, (code, what, unit) in _POSITIVE_VALUES.items():
        if slug in values:
            findings += _not_positive(
                values[slug], _values_path(slug), code, what, unit, f"Give {slug} a value > 0."
            )
    return findings


def _warning(code: str, origin: str, message: str, detail: dict[str, JsonValue]) -> KernelWarning:
    """Build a practice warning from the catalogue (the severity follows from the code)."""
    logger.debug("warning %s at %s", code, origin)
    return KernelWarning(
        severity=WARNING_CATALOGUE[code], code=code, message=message, origin=origin, detail=detail
    )


def _mass_warnings(aircraft: AircraftInput) -> list[KernelWarning]:
    """Warn when the passed mass and the geometry's ``total_mass_kg`` differ (exact comparison).

    The passed mass wins (ch. 8.11). A non-finite mass is an error elsewhere, not a warning.
    """
    passed = aircraft.values.get("aircraft-mass")
    stored = aircraft.airplane.total_mass_kg
    if passed is None or stored is None or not (math.isfinite(passed) and math.isfinite(stored)):
        return []
    if passed == stored:
        return []
    message = (
        f"The passed aircraft-mass is {passed} kg but the geometry's total_mass_kg is "
        f"{stored} kg; the passed mass is used."
    )
    detail: dict[str, JsonValue] = {"aircraft_mass_kg": passed, "geometry_total_mass_kg": stored}
    return [_warning("conflicting_mass", "aircraft-mass", message, detail)]


def _deflection_warnings(wings: Mapping[str, Wing]) -> list[KernelWarning]:
    """Warn once per device whose geometry carries a non-zero deflection; the kernel ignores it."""
    warnings: list[KernelWarning] = []
    for key, wing in wings.items():
        for index, x_sec in enumerate(wing.x_secs):
            path = f"{_key_path('airplane.wings', key)}.x_secs[{index}]"
            candidates = (
                (f"{path}.trailing_edge_device", x_sec.trailing_edge_device, "deflection_deg"),
                (f"{path}.control_surface", x_sec.control_surface, "deflection"),
            )
            for device, model, field in candidates:
                # getattr is Any; both fields are `Num | None`/`Num` floats on their models
                angle = None if model is None else cast("float | None", getattr(model, field))
                if angle is not None and math.isfinite(angle) and angle != 0:
                    message = (
                        f"The geometry sets a deflection of {angle} deg at {device}; it is "
                        "ignored, deflections come from the values."
                    )
                    detail: dict[str, JsonValue] = {"device": device, "deflection_deg": angle}
                    warnings.append(
                        _warning("geometry_deflection_ignored", "airplane", message, detail)
                    )
                    break
    return warnings


def validate_aircraft(aircraft: AircraftInput) -> Validation:
    """Report every physically inadmissible value of an aircraft input, and the input's caveats.

    Pure and I/O free; collects all findings instead of stopping at the first. Empty ``errors``
    means the input is admissible.

    Args:
        aircraft: The parsed input; geometry in metres and degrees, ``values`` in canon units.

    Returns:
        The ``invalid_input`` errors (each with the dotted ``input_path`` of the offending
        value) and the warnings about the input.
    """
    errors = _non_finite(aircraft.airplane, "airplane")
    for slug in sorted(aircraft.values):
        errors += _non_finite(aircraft.values[slug], _values_path(slug))
    errors += _wing_findings(aircraft.airplane.wings or {})
    errors += _fuselage_findings(aircraft.airplane.fuselages or {})
    errors += _value_findings(aircraft.values)
    logger.debug("validation done: %d errors", len(errors))
    warnings = _mass_warnings(aircraft) + _deflection_warnings(aircraft.airplane.wings or {})
    return Validation(errors=tuple(errors), warnings=tuple(warnings))
