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
would hide the underlying design problem.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from starlette.responses import JSONResponse

__all__ = ["replace_nonfinite", "NonFiniteSafeJSONResponse"]


def replace_nonfinite(obj: Any) -> Any:
    """Recursively replace non-finite floats (NaN, +/-Inf) with ``None``.

    Walks dicts, lists and tuples. Python and ``numpy`` float scalars are both
    handled — note ``np.float32`` is *not* a :class:`float` subclass, so numpy
    floats are matched explicitly and finite ones are returned as native floats
    (which the JSON encoder can serialize). Booleans, ints and every other value
    pass through unchanged.
    """
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, np.floating):
        return float(obj) if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {key: replace_nonfinite(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [replace_nonfinite(item) for item in obj]
    return obj


class NonFiniteSafeJSONResponse(JSONResponse):
    """JSONResponse that emits non-finite floats as ``null`` instead of crashing.

    Set as the ``default_response_class`` of routers whose responses carry solver
    output that may contain NaN / +/-Inf.
    """

    def render(self, content: Any) -> bytes:
        return super().render(replace_nonfinite(content))
