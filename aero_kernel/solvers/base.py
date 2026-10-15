"""Base of the solver adapters (ARCHITECTURE ch. 8.8).

Adapters know no canon names. They return warnings without ``origin``; the engine sets it.
"""

import importlib.metadata
import importlib.util
import logging
import math
from collections.abc import Mapping, Sequence
from typing import ClassVar

from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.runtime import SolverRuntime
from aero_kernel.schema import KernelWarning, WarningSeverity
from pydantic import JsonValue

logger = logging.getLogger(__name__)

__all__ = ["SolverAdapter", "regime"]

# The RC/UAV regime of ADR 0028, defined by flow physics.
_RE_BAND_MIN = 3.0e4
_RE_BUBBLE_MAX = 7.0e4
_RE_BAND_MAX = 1.0e6
_MACH_LIMIT = 0.3
_MACH_VALIDITY = 0.6


class SolverAdapter:
    """Base of every solver adapter (ch. 8.8): capability check, tool versions, the runtime.

    A subclass names its tool and the distributions it needs, each with the module that proves
    it is importable. Nothing is imported here: capability is found with ``find_spec`` and the
    versions with ``importlib.metadata``, so a missing tool is ``tool_unavailable`` and never an
    ``ImportError`` (Q10). Adapters know no canon names. Every public method of a subclass calls
    :meth:`require_available` first, and returns warnings without ``origin`` (the engine sets it).

    Attributes:
        tool: Name of the tool, e.g. ``aerobuildup``.
        requirements: Distribution name -> importable module name, for every distribution the
            adapter relies on (e.g. ``{"aerosandbox": "aerosandbox"}``).
        runtime: The runtime that runs the adapter's CPU work and subprocesses.
    """

    tool: ClassVar[str]
    requirements: ClassVar[Mapping[str, str]]

    def __init__(self, runtime: SolverRuntime) -> None:
        """Create the adapter.

        Args:
            runtime: The runtime of the owning ``compute()`` call or ``CachedKernel``.
        """
        self.runtime = runtime
        self._versions: dict[str, str] | None = None

    @staticmethod
    def _importable(module: str) -> bool:
        """Tell whether ``module`` can be found, without importing it."""
        try:
            return importlib.util.find_spec(module) is not None
        except ModuleNotFoundError:  # a parent package of a dotted name is missing
            return False

    def _missing(self) -> list[str]:
        """Return the required distributions whose module cannot be found."""
        return [
            distribution
            for distribution, module in self.requirements.items()
            if not self._importable(module)
        ]

    def available(self) -> bool:
        """Tell whether every required module can be found (nothing is imported)."""
        return not self._missing()

    def require_available(self) -> None:
        """Raise ``tool_unavailable`` unless :meth:`available`; logs a ``WARNING`` (ch. 8.14).

        Raises:
            FormulaError: Category ``tool_unavailable`` naming the missing distributions.
        """
        missing = self._missing()
        if not missing:
            return
        logger.warning("tool %s is unavailable, missing: %s", self.tool, ", ".join(missing))
        raise FormulaError(
            ErrorCategory.TOOL_UNAVAILABLE,
            "tool_unavailable",
            f"the tool {self.tool} is not available in this installation",
            f"install: {', '.join(missing)}",
            detail={"tool": self.tool, "missing": list(missing)},
        )

    def tool_versions(self) -> dict[str, str]:
        """Return the installed version per required distribution (provenance, cache key).

        A distribution that is not installed is omitted. The result is read once and then kept;
        treat it as read-only.

        Returns:
            Distribution name -> version, e.g. ``{"aerosandbox": "4.2.8"}``.
        """
        if self._versions is None:
            versions: dict[str, str] = {}
            for distribution in self.requirements:
                try:
                    versions[distribution] = importlib.metadata.version(distribution)
                except importlib.metadata.PackageNotFoundError:
                    continue
            self._versions = versions
        return self._versions


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
        ValueError: If an argument is not finite or not physical.
    """
    if not chords_m:
        msg = "chords_m must be non-empty"
        raise ValueError(msg)
    for name, value in (
        *(("chord", chord) for chord in chords_m),
        ("v_ms", v_ms),
        ("speed_of_sound_ms", speed_of_sound_ms),
        ("kinematic_viscosity_m2s", kinematic_viscosity_m2s),
    ):
        if not math.isfinite(value):
            msg = f"{name} must be finite, got {value}"
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
