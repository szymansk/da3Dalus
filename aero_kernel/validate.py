"""Physical admissibility of the input (ARCHITECTURE ch. 8.11, step 1 of a ``compute()`` call).

The input models carry types only; a well-typed but physically inadmissible value (NaN, a
negative chord) parses and is reported here as an ``invalid_input`` :class:`KernelError` with a
dotted ``input_path``, never raised. Regime (Re, Mach) is not validated (ch. 8.2) and the stops
of control devices are never read (ch. 8.11).
"""

import json
import logging
import math
from collections.abc import Mapping
from typing import cast

from aero_kernel.errors import ErrorCategory, KernelError
from aero_kernel.geometry import Wing
from aero_kernel.schema import AircraftInput
from pydantic import BaseModel

logger = logging.getLogger(__name__)

__all__ = ["validate_input"]


def _key_path(parent: str, key: str) -> str:
    """Extend a path by a dict key: ``parent["key"]`` with the key JSON-quoted."""
    return f"{parent}[{json.dumps(key)}]"


def _finding(path: str, message: str, hint: str) -> KernelError:
    """Build an ``invalid_input`` error at ``path``."""
    return KernelError(
        code=ErrorCategory.INVALID_INPUT.value,
        category=ErrorCategory.INVALID_INPUT,
        input_path=path,
        message=message,
        hint=hint,
    )


def _non_finite(node: object, path: str) -> list[KernelError]:
    """Find every NaN or infinite number below ``node`` (models, dicts, sequences)."""
    if isinstance(node, float):
        if math.isfinite(node):
            return []
        return [
            _finding(
                path, f"{path} is {node}, not a finite number.", f"Give {path} a finite value."
            )
        ]
    findings: list[KernelError] = []
    if isinstance(node, BaseModel):
        for name in type(node).model_fields:
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


def _not_positive(value: float, path: str, what: str) -> list[KernelError]:
    """Report ``value`` if it is finite and ``<= 0`` (a non-finite value is reported elsewhere)."""
    if not math.isfinite(value) or value > 0:
        return []
    return [
        _finding(
            path, f"{what} at {path} is {value}, but must be > 0.", f"Give {path} a value > 0."
        )
    ]


def _wing_findings(wings: Mapping[str, Wing]) -> list[KernelError]:
    """Check the wings: at least two sections and a positive chord on each."""
    findings: list[KernelError] = []
    for key, wing in wings.items():
        wing_path = _key_path("airplane.wings", key)
        if len(wing.x_secs) < 2:
            findings.append(
                _finding(
                    f"{wing_path}.x_secs",
                    f"Wing {key!r} has {len(wing.x_secs)} section(s); a wing needs at least 2.",
                    "Give the wing a root and a tip section.",
                )
            )
        for index, x_sec in enumerate(wing.x_secs):
            findings += _not_positive(x_sec.chord, f"{wing_path}.x_secs[{index}].chord", "Chord")
    return findings


def _value_findings(values: Mapping[str, float]) -> list[KernelError]:
    """Check the passed values: mass and density must be positive."""
    findings: list[KernelError] = []
    for slug, what in _POSITIVE_VALUES.items():
        if slug in values:
            findings += _not_positive(values[slug], f"values.{slug}", what)
    return findings


_POSITIVE_VALUES: Mapping[str, str] = {
    "aircraft-mass": "Mass",
    "sea-level-air-density": "Density",
}


def validate_input(aircraft: AircraftInput) -> tuple[KernelError, ...]:
    """Report every physically inadmissible value of an aircraft input.

    Pure; collects all findings instead of stopping at the first. An empty tuple means the input
    is admissible.

    Args:
        aircraft: The parsed input; geometry in metres and degrees, ``values`` in canon units.

    Returns:
        ``invalid_input`` errors (code ``unresolved_airfoil`` for an unresolvable airfoil), each
        with the dotted ``input_path`` of the offending value.
    """
    findings = _non_finite(aircraft.airplane, "airplane")
    for slug in sorted(aircraft.values):
        findings += _non_finite(aircraft.values[slug], f"values.{slug}")
    logger.debug("rule non_finite: %d findings", len(findings))
    wing_findings = _wing_findings(aircraft.airplane.wings or {})
    logger.debug("rule wings: %d findings", len(wing_findings))
    value_findings = _value_findings(aircraft.values)
    logger.debug("rule positive_values: %d findings", len(value_findings))
    return tuple(findings + wing_findings + value_findings)
