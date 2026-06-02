"""JSON-safety helpers for non-finite floats.

Starlette's :class:`~starlette.responses.JSONResponse` renders with
``json.dumps(..., allow_nan=False)``, so any NaN / +/-Inf in a response payload
raises ``ValueError: Out of range float values are not JSON compliant`` and
surfaces as an unhandled HTTP 500.

Numeric solvers (AeroSandbox AeroBuildup in particular) can legitimately emit
non-finite values for degenerate inputs — a zero-volume fuselage gives
``length**3 / volume`` -> NaN, a zero Reynolds number gives ``log10(0)`` ->
-inf. The JSON API must stay robust to those: we represent a non-finite float as
JSON ``null`` — an honest "no value", never a fabricated fallback number that
would hide the underlying design problem. The substitution is *logged* so the
degenerate result still leaves a server-side trace rather than vanishing.
"""

from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np
from starlette.responses import JSONResponse

__all__ = ["replace_nonfinite", "NonFiniteSafeJSONResponse"]

logger = logging.getLogger(__name__)


def _sanitize(obj: Any) -> tuple[Any, int]:
    """Recurse over *obj*, returning ``(clean, num_replaced)``.

    Non-finite floats (NaN, +/-Inf) — Python or ``numpy`` scalars — become
    ``None``; ``num_replaced`` counts how many were substituted. Tuples are
    normalized to lists (JSON has no tuple type). Booleans, ints and every other
    value pass through unchanged.
    """
    if isinstance(obj, bool):
        return obj, 0
    if isinstance(obj, float):
        return (obj, 0) if math.isfinite(obj) else (None, 1)
    # np.float32 (and friends) are NOT float subclasses, so match numpy floats
    # explicitly; finite ones become native floats the JSON encoder can handle.
    if isinstance(obj, np.floating):
        return (float(obj), 0) if math.isfinite(obj) else (None, 1)
    if isinstance(obj, dict):
        clean: dict[Any, Any] = {}
        replaced = 0
        for key, value in obj.items():
            clean[key], count = _sanitize(value)
            replaced += count
        return clean, replaced
    if isinstance(obj, (list, tuple)):
        items: list[Any] = []
        replaced = 0
        for item in obj:
            clean_item, count = _sanitize(item)
            items.append(clean_item)
            replaced += count
        return items, replaced
    return obj, 0


def replace_nonfinite(obj: Any) -> Any:
    """Recursively replace non-finite floats (NaN, +/-Inf) with ``None``.

    Walks dicts, lists and tuples (tuples are normalized to lists). Python and
    ``numpy`` float scalars are both handled. Booleans, ints and every other
    value pass through unchanged.
    """
    return _sanitize(obj)[0]


class NonFiniteSafeJSONResponse(JSONResponse):
    """JSONResponse that emits non-finite floats as ``null`` instead of crashing.

    Set as the ``default_response_class`` of routers whose responses carry solver
    output that may contain NaN / +/-Inf. When a substitution occurs it is logged
    at WARNING level so the degenerate result is traceable server-side.
    """

    def render(self, content: Any) -> bytes:
        sanitized, replaced = _sanitize(content)
        if replaced:
            logger.warning(
                "Replaced %d non-finite float value(s) (NaN/Inf) with null in a "
                "JSON response — likely degenerate geometry or a zero Reynolds "
                "number upstream.",
                replaced,
            )
        return super().render(sanitized)
