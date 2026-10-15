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
from typing import cast

from aero_kernel import geometry
from aero_kernel.errors import ErrorCategory, KernelError
from aero_kernel.geometry import Wing
from aero_kernel.schema import AircraftInput, KernelWarning
from pydantic import BaseModel, ConfigDict

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


def _wing_findings(wings: Mapping[str, Wing]) -> list[KernelError]:
    """Check the wings: at least two sections and a positive chord on each."""
    findings: list[KernelError] = []
    for key, wing in wings.items():
        wing_path = _key_path("airplane.wings", key)
        if len(wing.x_secs) < 2:
            findings.append(
                _finding(
                    "too_few_sections",
                    f"{wing_path}.x_secs",
                    f"Wing {key!r} has {len(wing.x_secs)} section(s); a wing needs at least 2.",
                    "Give the wing a root and a tip section.",
                )
            )
        for index, x_sec in enumerate(wing.x_secs):
            path = f"{wing_path}.x_secs[{index}].chord"
            findings += _not_positive(
                x_sec.chord,
                path,
                "non_positive_length",
                "Chord",
                "m",
                "Give the chord a length > 0.",
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
    errors += _value_findings(aircraft.values)
    logger.debug("validation done: %d errors", len(errors))
    return Validation(errors=tuple(errors))
