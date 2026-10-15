"""Physical admissibility of the input (ARCHITECTURE ch. 8.11, step 1 of a ``compute()`` call).

The input models carry types only; a well-typed but physically inadmissible value (NaN, a
negative chord) parses and is reported here as an ``invalid_input`` :class:`KernelError` with a
dotted ``input_path``, never raised. Regime (Re, Mach) is not validated (ch. 8.2) and the stops
of control devices are never read (ch. 8.11).
"""

import json
import logging
import math
from typing import cast

from aero_kernel.errors import ErrorCategory, KernelError
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
    return tuple(findings)
