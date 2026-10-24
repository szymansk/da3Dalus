"""Pure helpers of the steady-roll problem (canon ``roll-rate``, ARCHITECTURE ch. 8.8).

No AeroSandbox import: the angle functions are passed in, so the same code runs on CasADi
expressions in the optimiser and on floats in the fast tier.
"""

import math
from collections.abc import Sequence
from typing import Any, Protocol

__all__ = [
    "EFFECTIVENESS_EXPONENT",
    "AngleFunctions",
    "alpha_for_lift_coefficient",
    "body_rates",
    "control_effectiveness",
    "stability_rolling_moment",
]


class AngleFunctions(Protocol):
    """Sine and cosine of an angle in degrees (``aerosandbox.numpy`` provides them)."""

    def sind(self, x: Any) -> Any:  # noqa: ANN401  # CasADi expression or float
        """Sine of ``x`` in degrees."""
        ...

    def cosd(self, x: Any) -> Any:  # noqa: ANN401  # CasADi expression or float
        """Cosine of ``x`` in degrees."""
        ...


# The exponent of ASB's fit to an XFoil study, ``tau = 1 - h^n``
# (aerosandbox/geometry/airfoil/kulfan_airfoil.py:216-219, AeroSandbox 4.2.9). The one kernel copy;
# pinned against ASB by ``test_effective_alpha_shift_matches_asb``.
EFFECTIVENESS_EXPONENT = 2.751428551177291


def control_effectiveness(hinge: float) -> float:
    """The factor ``tau`` by which AeroBuildup turns a deflection into an angle-of-attack shift.

    Args:
        hinge: Hinge position as a fraction of chord.

    Returns:
        ``1 - h^2.7514``: the effective angle of attack added is ``tau * deflection``.
    """
    return 1.0 - max(0.0, hinge + 1e-16) ** EFFECTIVENESS_EXPONENT


# ``Any`` below: a CasADi expression in the optimiser, a float in the fast tier; AeroSandbox ships no
# type information.
def body_rates(
    p_stability: Any,  # noqa: ANN401  # CasADi expression or float
    alpha_deg: Any,  # noqa: ANN401  # CasADi expression or float
    trig: AngleFunctions,
) -> tuple[Any, Any]:
    """The body-axis roll and yaw rate of a rotation about the stability x axis.

    The stability x axis lies at the angle of attack in the body xz plane, so a rate ``p`` about it
    is ``p cos(alpha)`` about the body x axis and ``p sin(alpha)`` about the body z axis (Etkin;
    AVL's default rotation axes, ``avl.f:652``).

    Args:
        p_stability: The roll rate about the stability x axis (any unit).
        alpha_deg: The angle of attack in degrees.
        trig: Sine and cosine in degrees.

    Returns:
        ``(p_body, r_body)`` in the unit of ``p_stability``.
    """
    return (
        trig.cosd(alpha_deg) * p_stability,
        trig.sind(alpha_deg) * p_stability,
    )


def stability_rolling_moment(
    cl_body: Any,  # noqa: ANN401  # CasADi expression or float
    cn_body: Any,  # noqa: ANN401  # CasADi expression or float
    alpha_deg: Any,  # noqa: ANN401  # CasADi expression or float
    trig: AngleFunctions,
) -> Any:  # noqa: ANN401  # CasADi expression or float
    """The rolling-moment coefficient in stability axes, ``Cl cos(alpha) + Cn sin(alpha)``.

    The steady roll sets it to zero (AVL's ``RM`` constraint, ``aoper.f:1120``).

    Args:
        cl_body: The body-axis rolling-moment coefficient.
        cn_body: The body-axis yawing-moment coefficient.
        alpha_deg: The angle of attack in degrees.
        trig: Sine and cosine in degrees.

    Returns:
        The coefficient (same normalisation as the inputs).
    """
    return cl_body * trig.cosd(alpha_deg) + cn_body * trig.sind(alpha_deg)


def alpha_for_lift_coefficient(
    alphas_deg: Sequence[float], cl: Sequence[float], peak_index: int, wanted: float
) -> float | None:
    """The angle of attack on the pre-stall branch at which the sweep reaches a lift coefficient.

    Scans from the first C_L peak downwards in angle and interpolates linearly between the two
    samples that enclose ``wanted``, so the crossing nearest the peak is found even if the curve
    is not monotonic far below it.

    Args:
        alphas_deg: The sweep angles, rising.
        cl: The lift coefficient per sample.
        peak_index: Index of the first C_L peak.
        wanted: The lift coefficient to reach.

    Returns:
        The angle in degrees, or ``None`` if no sample pair up to the peak encloses ``wanted``.
    """
    for k in range(peak_index, 0, -1):
        if cl[k - 1] <= wanted <= cl[k]:
            span = cl[k] - cl[k - 1]
            fraction = (
                0.0 if math.isclose(span, 0.0, abs_tol=1e-15) else (wanted - cl[k - 1]) / span
            )
            return alphas_deg[k - 1] + fraction * (alphas_deg[k] - alphas_deg[k - 1])
    return None
