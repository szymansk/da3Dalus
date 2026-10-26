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
from bisect import bisect_left
from collections.abc import Mapping
from itertools import pairwise
from typing import cast

from aero_kernel import geometry
from aero_kernel.canon.model import CanonModel
from aero_kernel.errors import ErrorCategory, KernelError, is_slug
from aero_kernel.geometry import Wing
from aero_kernel.rules import Rules
from aero_kernel.schema import AircraftInput, ComputeRequest, KernelWarning
from pydantic import BaseModel, ConfigDict, JsonValue

logger = logging.getLogger(__name__)

__all__ = ["Validation", "validate_aircraft", "validate_request", "validate_values"]


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


# What the kernel reads of a trailing-edge device (ch. 8.11), an allowlist so a field cannot be
# missed: its role, the hinge line, the symmetry, the AVL mixing gains of dual roles, and the
# deflection (only to report it as ignored). Its span is the segment it sits on.
_TED_READ = frozenset(
    {
        "role",
        "rel_chord_root",
        "rel_chord_tip",
        "symmetric",
        "mix_gain_primary",
        "mix_gain_secondary",
        "deflection_deg",
    }
)

# Fields no kernel formula reads. This is the policy "a check exists only for a field the kernel
# reads" (ch. 8.11): a finding on them would be noise. When a later formula starts reading one
# (turbulator, spars), that unit removes it from this table. A device's
# ``control_surface`` is read for its deflection only (to report an ignored one); the stops
# (``*_deflection_deg``) are never read.
UNREAD_FIELDS: Mapping[type[BaseModel], frozenset[str]] = {
    geometry.Servo: frozenset(geometry.Servo.model_fields),
    geometry.SpareDetail: frozenset(geometry.SpareDetail.model_fields),
    geometry.Turbulator: frozenset(geometry.Turbulator.model_fields),
    geometry.ControlSurface: frozenset(geometry.ControlSurface.model_fields) - {"deflection"},
    geometry.TrailingEdgeDevice: frozenset(geometry.TrailingEdgeDevice.model_fields) - _TED_READ,
}


WINGS_PATH = "airplane.wings"


def _key_path(parent: str, key: str) -> str:
    """Extend a path by a dict key: ``parent["key"]``, the key JSON-escaped, unicode kept."""
    return f"{parent}[{json.dumps(key, ensure_ascii=False)}]"


def _values_path(slug: str) -> str:
    """Path of a ``values`` entry: dotted for a canon slug, bracketed for any other key."""
    if is_slug(slug):
        return f"values.{slug}"
    return _key_path("values", slug)


def _number(value: float) -> JsonValue:
    """Encode a number for a free JSON field: a float, or ``"nan"`` / ``"inf"`` / ``"-inf"``."""
    return value if math.isfinite(value) else str(value)


def _finding(
    code: str, path: str, message: str, hint: str, value: float | None = None
) -> KernelError:
    """Build an ``invalid_input`` error at ``path``; ``value`` goes to ``detail`` if given."""
    logger.debug("finding %s at %s", code, path)
    detail: dict[str, JsonValue] = {} if value is None else {"value": _number(value)}
    return KernelError(
        code=code,
        category=ErrorCategory.INVALID_INPUT,
        input_path=path,
        message=message,
        hint=hint,
        detail=detail,
    )


def _non_finite(node: object, path: str, skip: frozenset[str] = frozenset()) -> list[KernelError]:
    """Find every NaN or infinite number below ``node`` (models and tuples) that the kernel reads.

    ``skip`` names fields of ``node`` itself that the caller checks separately.
    """
    if isinstance(node, float):
        if math.isfinite(node):
            return []
        return [
            _finding(
                "non_finite_number",
                path,
                f"Value at {path} is {node}; it must be a finite number.",
                f"Give {path} a finite value.",
                node,
            )
        ]
    findings: list[KernelError] = []
    if isinstance(node, BaseModel):
        unread = UNREAD_FIELDS.get(type(node), frozenset()) | skip
        for name in type(node).model_fields:
            if name not in unread:
                findings += _non_finite(getattr(node, name), f"{path}.{name}")
    elif isinstance(node, tuple):
        # isinstance narrows a generic tuple to tuple[Unknown, ...]
        for index, item in enumerate(cast("tuple[object, ...]", node)):
            findings += _non_finite(item, f"{path}[{index}]")
    return findings


def _not_positive(
    value: float,
    path: str,
    code: str,
    what: str,
    unit: str,
    hint: str,
    *,
    allow_zero: bool = False,
) -> list[KernelError]:
    """Report ``value`` if it is finite and ``<= 0`` (``< 0`` with ``allow_zero``).

    A non-finite value is reported elsewhere.
    """
    if not math.isfinite(value) or value > 0 or (allow_zero and value == 0):
        return []
    bound = ">= 0" if allow_zero else "> 0"
    message = f"{what} at {path} is {f'{value} {unit}'.rstrip()}; it must be {bound}."
    return [_finding(code, path, message, hint, value)]


def _above_maximum(
    value: float, maximum: float, path: str, slug: str, unit: str
) -> list[KernelError]:
    """Report ``value`` if it is finite and above the canon's ``at_most`` of the quantity."""
    if not math.isfinite(value) or value <= maximum:
        return []
    message = f"Value of {slug} at {path} is {f'{value} {unit}'.rstrip()}; it must be <= {maximum}."
    return [
        _finding("value_above_maximum", path, message, f"Give {slug} a value <= {maximum}.", value)
    ]


_NACA = re.compile(r"naca(?P<digits>[0-9]{4})", re.IGNORECASE)


def _interpolate(curve: list[tuple[float, float]], x: float) -> float:
    """Linearly interpolate ``y`` at ``x`` on a curve sorted by x.

    ``x`` must lie within the curve's x range; the caller guarantees it through the end-point
    rule (the lower surface spans the leading edge to the largest x). No extrapolation.
    """
    xs = [point[0] for point in curve]
    index = bisect_left(xs, x)
    if index == 0:
        return curve[0][1]
    # xs[index - 1] < x <= xs[index], so the interval has a positive width
    (x0, y0), (x1, y1) = curve[index - 1], curve[index]
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def _contour_thickness(points: tuple[tuple[float, float], ...]) -> float:
    """Maximum thickness (upper minus lower, chord fractions) of a Selig-ordered contour.

    The contour runs trailing edge, upper surface, leading edge (smallest x), lower surface,
    trailing edge. The lower surface is interpolated at the stations of the upper one.
    """
    leading_edge = min(range(len(points)), key=lambda index: points[index][0])
    # the maximum over the upper points is independent of their order, so they are not sorted;
    # the lower surface is sorted by x (stable: at an equal x the first point along it wins, y
    # never decides) because it is interpolated
    upper = points[: leading_edge + 1]
    lower = sorted(points[leading_edge:], key=lambda point: point[0])
    return max(y - _interpolate(lower, x) for x, y in upper)


def _airfoil_findings(airfoil: geometry.Airfoil, path: str, rules: Rules) -> list[KernelError]:
    """Check an airfoil: a NACA 4-digit designation or a valid contour with positive thickness."""
    if isinstance(airfoil, str):
        match = _NACA.fullmatch(airfoil)
        if match is None:
            return [
                _finding(
                    "unresolved_airfoil",
                    path,
                    f"Airfoil {airfoil!r} is not a NACA 4-digit designation and the kernel "
                    "loads no files.",
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
                    0.0,
                )
            ]
        return []
    points = airfoil.coordinates
    minimum_points = int(rules.value("airfoil-resolvable", "min_contour_points"))
    coordinates_path = f"{path}.coordinates"
    findings: list[KernelError] = []
    finite = all(math.isfinite(c) for point in points for c in point)
    # the point count is its own cause and is judged whatever the values; the end-point rule and
    # the thickness need finite coordinates and are skipped otherwise (the walk reports those)
    trailing_edge = (
        finite
        and len(points) >= minimum_points
        and points[0][0] == points[-1][0] == max(x for x, _ in points)
    )
    if len(points) < minimum_points or (finite and not trailing_edge):
        findings.append(
            _finding(
                "invalid_airfoil_contour",
                coordinates_path,
                f"The airfoil contour at {coordinates_path} has {len(points)} point(s); it "
                f"needs at least {minimum_points}, and its first and last point must lie at the largest x.",
                "Start and end the contour at the trailing edge (Selig order).",
            )
        )
    # the thickness of a contour that fails the rule is meaningless: one code for one cause
    if trailing_edge:
        thickness = _contour_thickness(points)
        if thickness <= 0:
            findings.append(
                _finding(
                    "non_positive_thickness",
                    coordinates_path,
                    f"The airfoil at {coordinates_path} has a maximum thickness of {thickness} "
                    "chord fractions: thickness <= 0; inline coordinates must be in Selig order "
                    "(upper surface from the trailing edge to the leading edge, then the lower "
                    "surface).",
                    "List the upper surface from the trailing edge to the leading edge, then the lower "
                    "surface.",
                    thickness,
                )
            )
    return findings


def _section_findings(
    x_sec: geometry.WingXSec, path: str, rules: Rules, *, is_last: bool
) -> list[KernelError]:
    """Check one rib: finiteness, chord, airfoil, segment details on the last, control surface."""
    findings = _non_finite(x_sec, path)
    findings += _not_positive(
        x_sec.chord,
        f"{path}.chord",
        "non_positive_length",
        "Chord",
        "m",
        "Give the chord a length > 0.",
    )
    findings += _airfoil_findings(x_sec.airfoil, f"{path}.airfoil", rules)
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


def _too_few_sections(
    kind: str, key: str, count: int, path: str, rules: Rules
) -> list[KernelError]:
    """Report a wing or fuselage with fewer sections than the canon requires."""
    minimum = int(rules.value("minimum-sections", "min_sections"))
    if count >= minimum:
        return []
    return [
        _finding(
            "too_few_sections",
            f"{path}.x_secs",
            f"{kind} {key!r} has {count} section(s); it needs at least {minimum}.",
            f"Give it at least {minimum} sections.",
            float(count),
        )
    ]


def _span_findings(wing: Wing, path: str) -> list[KernelError]:
    """Report a wing whose ``xyz_le`` chain has length 0 (needs finite points and 2+ sections)."""
    points = [x_sec.xyz_le for x_sec in wing.x_secs]
    if len(points) < 2 or not all(math.isfinite(c) for point in points for c in point):
        return []
    span = sum(math.dist(start, end) for start, end in pairwise(points))
    if span > 0:
        return []
    return [
        _finding(
            "non_positive_length",
            f"{path}.x_secs",
            f"The span of the wing at {path} is {span} m; it must be > 0.",
            "Give the sections different leading-edge points.",
            span,
        )
    ]


def _wing_findings(wings: Mapping[str, Wing], rules: Rules) -> list[KernelError]:
    """Check the wings: section count, span and each section."""
    findings: list[KernelError] = []
    for key, wing in wings.items():
        path = _key_path(WINGS_PATH, key)
        findings += _too_few_sections("Wing", key, len(wing.x_secs), path, rules)
        findings += _span_findings(wing, path)
        last = len(wing.x_secs) - 1
        for index, x_sec in enumerate(wing.x_secs):
            findings += _section_findings(
                x_sec, f"{path}.x_secs[{index}]", rules, is_last=index == last
            )
        findings += _missing_surface_type(wing, key, path)
    return findings + _main_wing_count(wings, rules) + _main_wing_inclination(wings, rules)


def _missing_surface_type(wing: Wing, key: str, path: str) -> list[KernelError]:
    """Report a wing without its ``surface_type`` (D9: required, never inferred)."""
    if wing.surface_type is not None:
        return []
    return [
        _finding(
            "missing_surface_type",
            path,
            f"The wing {key!r} has no surface_type.",
            "Set surface_type to the function of the wing, e.g. main_wing or horizontal_tail.",
        )
    ]


def _main_wing_count(wings: Mapping[str, Wing], rules: Rules) -> list[KernelError]:
    """Report an airplane that does not have the required number of ``main_wing`` wings."""
    required = int(rules.value("one-main-wing", "required_main_wings"))
    count = sum(1 for wing in wings.values() if wing.surface_type == "main_wing")
    if count == required:
        return []
    logger.debug("finding main_wing_count at airplane.wings: %d", count)
    return [
        KernelError(
            code="main_wing_count",
            category=ErrorCategory.INVALID_INPUT,
            input_path=WINGS_PATH,
            message=f"The airplane has {count} wings with surface_type main_wing; it needs exactly {required}.",
            hint="Mark exactly one wing as main_wing; its area, span and chord are the reference values.",
            detail={"count": count},
        )
    ]


def _main_wing_inclination(wings: Mapping[str, Wing], rules: Rules) -> list[KernelError]:
    """Report a ``main_wing`` that is inclined from the horizontal by ``max_inclination`` or more.

    The inclination is that of the whole stored wing, ``atan2(z-extent, y-extent)``; a wing with no
    y-extent is vertical (canon rule ``main-wing-spanwise-extent``, adopted 2026-10-25, #1253).
    """
    limit = rules.value("main-wing-spanwise-extent", "max_inclination")
    findings: list[KernelError] = []
    for key, wing in wings.items():
        if wing.surface_type != "main_wing":
            continue
        ys = [x_sec.xyz_le[1] for x_sec in wing.x_secs]
        zs = [x_sec.xyz_le[2] for x_sec in wing.x_secs]
        if not ys or not all(math.isfinite(c) for c in (*ys, *zs)):
            continue  # no sections or a non-finite one: other findings
        y_extent, z_extent = max(ys) - min(ys), max(zs) - min(zs)
        inclination = math.degrees(math.atan2(z_extent, y_extent))
        if inclination < limit:
            continue
        findings.append(
            KernelError(
                code="main_wing_without_spanwise_extent",
                category=ErrorCategory.INVALID_INPUT,
                input_path=_key_path(WINGS_PATH, key),
                message=(
                    f"The main wing {key!r} extends {y_extent:.4g} m in y and {z_extent:.4g} m in z: "
                    f"it is inclined by {inclination:.3g} deg, at least the {limit:g} deg a main wing "
                    "may have, so it is a vertical surface."
                ),
                hint=(
                    "Check the surface type of the wing: a fin or a V-tail is not a main wing. "
                    "An expert may raise the rule parameter main-wing-spanwise-extent.max_inclination."
                ),
                detail={
                    "y_extent_m": y_extent,
                    "z_extent_m": z_extent,
                    "max_inclination_deg": limit,
                },
            )
        )
    return findings


def _fuselage_findings(
    fuselages: Mapping[str, geometry.Fuselage], rules: Rules
) -> list[KernelError]:
    """Check the fuselages: section count, semi-axes (0 allowed at the ends) and exponents."""
    findings: list[KernelError] = []
    for key, fuselage in fuselages.items():
        path = _key_path("airplane.fuselages", key)
        findings += _too_few_sections("Fuselage", key, len(fuselage.x_secs), path, rules)
        last = len(fuselage.x_secs) - 1
        for index, x_sec in enumerate(fuselage.x_secs):
            section = f"{path}.x_secs[{index}]"
            findings += _non_finite(x_sec, section)
            # A lofted fuselage closes to a point or a line at its ends (team-lead 2026-10-22).
            at_end = index in (0, last)
            for axis, size in (("a", x_sec.a), ("b", x_sec.b)):
                findings += _not_positive(
                    size,
                    f"{section}.{axis}",
                    "non_positive_length",
                    "Semi-axis",
                    "m",
                    "Give the semi-axis a length >= 0 at an end section, > 0 elsewhere.",
                    allow_zero=at_end,
                )
            for name, exponent in (("n", x_sec.n), ("n_lower", x_sec.n_lower)):
                if exponent is not None:
                    findings += _not_positive(
                        exponent,
                        f"{section}.{name}",
                        "non_positive_exponent",
                        "Exponent",
                        "",
                        "Give the super-ellipse exponent a value > 0.",
                    )
    return findings


def _warning(code: str, origin: str, message: str, detail: dict[str, JsonValue]) -> KernelWarning:
    """Build a practice warning from the catalogue (the severity follows from the code)."""
    logger.debug("warning %s at %s", code, origin)
    return KernelWarning.of(code, message, origin=origin, detail=detail)


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


def validate_aircraft(aircraft: AircraftInput, rules: Rules | None = None) -> Validation:
    """Report every physically inadmissible value of an aircraft input, and the input's caveats.

    Pure and I/O free; collects all findings instead of stopping at the first. Empty ``errors``
    means the input is admissible. Findings follow the document, then ``values`` by slug.
    ``values`` are checked for finiteness only: their admissibility comes from the canon model.

    The thresholds of the rules come from the canon (``rules.yaml``) through ``rules``, with the
    caller's ``rule_overrides``; the geometry rules run here, once, on every path.

    Args:
        aircraft: The parsed input; geometry in metres and degrees, ``values`` in canon units.
        rules: The thresholds of the call; the shipped canon's with the aircraft's overrides if
            omitted.

    Returns:
        The ``invalid_input`` errors (each with the dotted ``input_path`` of the offending
        value) and the warnings about the input.
    """
    if rules is None:
        from aero_kernel.build import shipped_build  # build imports this module

        rules = Rules(shipped_build().model, aircraft.rule_overrides)
    airplane = aircraft.airplane
    errors = _non_finite(airplane, "airplane", skip=frozenset({"wings", "fuselages"}))
    errors += _wing_findings(airplane.wings or {}, rules)
    errors += _fuselage_findings(airplane.fuselages or {}, rules)
    for slug in sorted(aircraft.values):
        errors += _non_finite(aircraft.values[slug], _values_path(slug))
    warnings = _mass_warnings(aircraft) + _deflection_warnings(airplane.wings or {})
    logger.debug("validation done: %d errors, %d warnings", len(errors), len(warnings))
    return Validation(errors=tuple(errors), warnings=tuple(warnings))


def validate_request(request: ComputeRequest) -> tuple[KernelError, ...]:
    """Report an inadmissible time budget of the request (ch. 8.10).

    Args:
        request: The parsed request.

    Returns:
        ``non_finite_number`` or ``non_positive_value`` at ``request.time_budget_s``; empty if the
        budget is absent or a positive finite number.
    """
    budget = request.time_budget_s
    path = "request.time_budget_s"
    errors: list[KernelError] = []
    if budget is None:
        return tuple(errors)
    if not math.isfinite(budget):
        errors.append(
            _finding(
                "non_finite_number",
                path,
                f"Value at {path} is {budget}; it must be a finite number.",
                "Give a finite budget in seconds, or leave it out for none.",
                budget,
            )
        )
    elif budget <= 0:
        errors.append(
            _finding(
                "non_positive_value",
                path,
                f"Value at {path} is {budget} s; it must be > 0.",
                "Give a positive budget in seconds, or leave it out for none.",
                budget,
            )
        )
    return tuple(errors)


def validate_values(values: Mapping[str, float], model: CanonModel) -> tuple[KernelError, ...]:
    """Check the supplied ``values`` against the canon model (ch. 8.11).

    A slug must name a quantity of the model (``unknown_quantity``) that the caller supplies: a
    scalar of role ``input`` or ``target`` (``not_an_input``), and a quantity the canon declares
    ``positive`` must be > 0 (``non_positive_value``) and a quantity with ``at_most`` must not
    exceed it (``value_above_maximum``). Non-finite numbers are
    :func:`validate_aircraft`'s finding and not reported twice. The admissibility comes from the
    model; no slug is named here.

    Args:
        values: Value per canon slug (a bare slug means ``calc:``), in the canon's unit.
        model: The canon model.

    Returns:
        The ``invalid_input`` errors, by slug, each with ``input_path`` ``values.<slug>``.
    """
    errors: list[KernelError] = []
    for slug in sorted(values):
        path = _values_path(slug)
        quantity = model.quantity(slug)
        if quantity is None:
            errors.append(
                _finding(
                    "unknown_quantity",
                    path,
                    f"{slug} is not a quantity of the canon.",
                    "Use the slug of a canon input or target quantity.",
                )
            )
        elif quantity.role not in ("input", "target"):
            errors.append(
                _finding(
                    "not_an_input",
                    path,
                    f"`{slug}` is computed by the kernel; values cannot override it.",
                    f"Remove `{slug}` from the values; request it as a quantity instead.",
                )
            )
        elif quantity.type == "airplane":
            errors.append(
                _finding(
                    "not_an_input",
                    path,
                    f"`{slug}` is given as AircraftInput.airplane, not in values.",
                    f"Remove `{slug}` from the values and pass the geometry as the airplane.",
                )
            )
        elif quantity.type != "scalar":
            errors.append(
                _finding(
                    "not_an_input",
                    path,
                    f"`{slug}` is a {quantity.type}, not a number; values hold numbers only.",
                    f"Remove `{slug}` from the values.",
                )
            )
        elif quantity.positive:
            errors += _not_positive(
                values[slug],
                path,
                "non_positive_value",
                f"Value of {slug}",
                quantity.unit,
                f"Give {slug} a value > 0.",
            )
        if quantity is not None and quantity.at_most is not None:
            errors += _above_maximum(values[slug], quantity.at_most, path, slug, quantity.unit)
    return tuple(errors)
