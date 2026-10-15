"""Base of the solver adapters (ARCHITECTURE ch. 8.8).

Adapters know no canon names. They return warnings without ``origin``; the engine sets it.
"""

import logging
from collections.abc import Sequence

from aero_kernel.schema import KernelWarning, WarningSeverity
from pydantic import JsonValue

logger = logging.getLogger(__name__)

__all__ = ["regime"]

# The RC/UAV regime of ADR 0028, defined by flow physics.
_RE_BAND_MIN = 3.0e4
_RE_BUBBLE_MAX = 7.0e4
_RE_BAND_MAX = 1.0e6
_MACH_LIMIT = 0.3
_MACH_VALIDITY = 0.6


def _require_positive(name: str, value: float) -> None:
    """Raise ``ValueError`` unless ``value`` is greater than zero."""
    if not value > 0.0:
        msg = f"{name} must be > 0, got {value}"
        raise ValueError(msg)


def regime(
    chords_m: Sequence[float],
    v_ms: float,
    speed_of_sound_ms: float,
    kinematic_viscosity_m2s: float,
) -> list[KernelWarning]:
    """Check chord Reynolds number and Mach number against the RC/UAV regime (ADR 0028).

    Re = V c / nu per chord, Mach = V / a. One warning per code and call; the Reynolds warnings
    carry the extreme Reynolds numbers over all chords. Raised where Re and Mach become known,
    in the adapters (ch. 8.2).

    Args:
        chords_m: Section chords in metres (not empty, all > 0).
        v_ms: Evaluated airspeed in m/s (>= 0).
        speed_of_sound_ms: Speed of sound at the altitude in m/s (> 0).
        kinematic_viscosity_m2s: Kinematic viscosity at the altitude in m^2/s (> 0).

    Returns:
        ``reynolds_outside_band`` (Re < 3e4 or > 1e6), ``reynolds_bubble_sensitive``
        (3e4 <= Re < 7e4), ``mach_above_limit`` (0.3 < M <= 0.6), ``mach_beyond_validity``
        (M > 0.6), as applicable.

    Raises:
        ValueError: If an argument is not physical.
    """
    if not chords_m:
        msg = "chords_m must be non-empty"
        raise ValueError(msg)
    for chord in chords_m:
        _require_positive("chord", chord)
    if v_ms < 0.0:
        msg = f"v_ms must be >= 0, got {v_ms}"
        raise ValueError(msg)
    _require_positive("speed_of_sound_ms", speed_of_sound_ms)
    _require_positive("kinematic_viscosity_m2s", kinematic_viscosity_m2s)

    reynolds = [v_ms * chord / kinematic_viscosity_m2s for chord in chords_m]
    re_min, re_max = min(reynolds), max(reynolds)
    mach = v_ms / speed_of_sound_ms
    warnings: list[KernelWarning] = []
    detail: dict[str, JsonValue] = {"re_min": re_min, "re_max": re_max, "mach": mach}
    if re_min < _RE_BAND_MIN or re_max > _RE_BAND_MAX:
        warnings.append(
            KernelWarning(
                severity=WarningSeverity.DEFECT,
                code="reynolds_outside_band",
                message=(
                    f"chord Reynolds number {re_min:.0f}..{re_max:.0f} leaves the validated "
                    f"band {_RE_BAND_MIN:.0f}..{_RE_BAND_MAX:.0f}"
                ),
                detail=detail,
            )
        )
    if any(_RE_BAND_MIN <= re < _RE_BUBBLE_MAX for re in reynolds):
        warnings.append(
            KernelWarning(
                severity=WarningSeverity.PRACTICE,
                code="reynolds_bubble_sensitive",
                message=(
                    f"chord Reynolds number below {_RE_BUBBLE_MAX:.0f}: laminar separation "
                    "bubbles dominate and the result is sensitive"
                ),
                detail=detail,
            )
        )
    if mach > _MACH_VALIDITY:
        warnings.append(
            KernelWarning(
                severity=WarningSeverity.DEFECT,
                code="mach_beyond_validity",
                message=f"Mach {mach:.2f} is beyond {_MACH_VALIDITY}: compressibility not modelled",
                detail=detail,
            )
        )
    elif mach > _MACH_LIMIT:
        warnings.append(
            KernelWarning(
                severity=WarningSeverity.PRACTICE,
                code="mach_above_limit",
                message=f"Mach {mach:.2f} is above {_MACH_LIMIT}: compressibility is neglected",
                detail=detail,
            )
        )
    return warnings
