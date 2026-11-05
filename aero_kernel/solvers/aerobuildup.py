"""The numeric AeroBuildup runs in a fixed air state and the kernel's drag (ARCHITECTURE ch. 8.8).

Called from the OPT adapter's workers, in a pool process: the alpha sweeps (the published polars and
the bracketing lift curves) and the evaluation of one operating point (canon
``aerobuildup-evaluation``). The OPT adapter owns every AeroBuildup call of the kernel (ADR 0022); the
IPOPT problems see AeroBuildup through the model function of ``aero_model`` instead.

**The kernel's drag (#1346).** AeroBuildup's induced drag uses the Nita-Scholz Oswald factor, which
multiplies the inviscid factor by the full-scale viscous factor k_e,D0
(``aerosandbox/library/aerodynamics/inviscid.py:67-74, 81``); NeuralFoil's section polars already
contain the lift-dependent profile drag that factor stands for. Every drag the kernel takes from
AeroBuildup is :func:`kernel_drag`, ``D_profile + k_e,D0 * D_induced``, with k_e,D0 the parameter of
the canon rule ``aerobuildup-induced-drag``: one function, numeric and symbolic alike, so there is no
second producer of drag. AeroSandbox is not patched.
"""

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
from aero_kernel.schema import FlowConditions, Polar
from aero_kernel.solvers.air import AirState, FixedAtmosphere
from aero_kernel.solvers.asb_airplane import load_aerosandbox
from pydantic import BaseModel, ConfigDict

__all__ = [
    "INDUCED_DRAG_RULE",
    "VISCOUS_FACTOR_PARAMETER",
    "LiftCurve",
    "evaluate_forces",
    "kernel_drag",
    "scalar",
    "sweep_lift",
    "sweep_polar",
]

# The canon rule (``rules.yaml``) whose parameter is AeroBuildup's viscous factor k_e,D0, and the
# parameter's name (#1346, maintainer 2026-11-03).
INDUCED_DRAG_RULE = "aerobuildup-induced-drag"
VISCOUS_FACTOR_PARAMETER = "k_e_d0"


def kernel_drag(result: Mapping[str, Any], viscous_factor: float) -> Any:  # noqa: ANN401  # numbers, arrays or CasADi expressions alike
    """The kernel's drag from an AeroBuildup result: the viscous factor taken out of the induced part.

    ``D = D_profile + k_e,D0 * D_induced`` (canon ``aerobuildup-evaluation``, rule
    ``aerobuildup-induced-drag``, #1346). AeroBuildup's induced drag is ``L^2 / (q pi b_eff^2)`` with
    ``b_eff^2`` a scale-free softmax of the components' ``b^2 e`` (``aero_buildup.py:279-290``), which
    is homogeneous of degree 1, so this equals AeroBuildup run with ``k_e,D0 = 1`` while the wings
    dominate that softmax: every wing's ``e`` carries ``k_e,D0``, a fuselage's own ``e = 0.95``
    (``aero_buildup.py:1221``) does not, so where the fuselage term counts the equality is not exact
    (the aero tier compares both on BRYAN and BELEMNITOS). AeroBuildup's own total ``D`` is never read.

    Args:
        result: An AeroBuildup result, or the model function's outputs: ``D_profile`` and
            ``D_induced`` in N (numbers, arrays or CasADi expressions).
        viscous_factor: k_e,D0, the factor inside AeroBuildup's Oswald factor (dimensionless).

    Returns:
        The drag in N, of the type of the result's entries.
    """
    return result["D_profile"] + viscous_factor * result["D_induced"]


class LiftCurve(BaseModel):
    """The lift coefficient over the angle of attack at one speed: what a bracketing sweep needs.

    Attributes:
        alpha_deg: Angles of attack in degrees, strictly rising.
        cl: The lift coefficient at each angle, as AeroBuildup computes it.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    alpha_deg: tuple[float, ...]
    cl: tuple[float, ...]


def _sweep(
    asb_airplane: object,
    air: AirState,
    velocity_ms: float,
    alphas_deg: Sequence[float],
    model_size: str,
) -> tuple[Mapping[str, Any], Any]:
    """One vectorised AeroBuildup run over the angles; the result and its operating point."""
    asb = load_aerosandbox()
    alphas = np.asarray(alphas_deg, dtype=float)
    point = asb.OperatingPoint(
        atmosphere=FixedAtmosphere(air),
        velocity=np.full_like(alphas, velocity_ms),
        alpha=alphas,
    )
    return asb.AeroBuildup(asb_airplane, point, model_size=model_size).run(), point


def sweep_lift(
    asb_airplane: object,
    air: AirState,
    velocity_ms: float,
    alphas_deg: Sequence[float],
    model_size: str,
) -> LiftCurve:
    """Run AeroBuildup over the angles of attack and read the lift coefficient only.

    The bracketing sweeps of the IPOPT problems and of the roll window locate the
    first C_L extremum; they read no drag. Runs in a pool worker.

    Args:
        asb_airplane: The ``asb.Airplane`` (from ``to_asb_airplane``).
        air: The air state.
        velocity_ms: True airspeed in m/s.
        alphas_deg: Angles of attack in degrees, strictly rising.
        model_size: The NeuralFoil model size AeroBuildup evaluates its sections with.

    Returns:
        The lift curve.
    """
    result, _point = _sweep(asb_airplane, air, velocity_ms, alphas_deg, model_size)
    return LiftCurve(
        alpha_deg=tuple(float(a) for a in alphas_deg),
        cl=tuple(float(v) for v in result["CL"]),
    )


def sweep_polar(
    asb_airplane: object,
    air: AirState,
    velocity_ms: float,
    alphas_deg: Sequence[float],
    model_size: str,
    viscous_factor: float,
) -> Polar:
    """Run AeroBuildup over the angles of attack on an already converted airplane: the polar.

    The one place that evaluates a polar of AeroBuildup in a fixed air state (ADR 0022). ``C_D`` is the
    kernel's drag (:func:`kernel_drag`) over ``q S_ref``, with ``q`` from AeroSandbox's operating point
    and ``S_ref`` the airplane's, as AeroBuildup forms its own ``C_D`` (``aero_buildup.py:327, 334``).
    Runs in a pool worker.

    Args:
        asb_airplane: The ``asb.Airplane`` (from ``to_asb_airplane``).
        air: The air state.
        velocity_ms: True airspeed in m/s.
        alphas_deg: Angles of attack in degrees, strictly rising.
        model_size: The NeuralFoil model size AeroBuildup evaluates its sections with.
        viscous_factor: k_e,D0 (rule ``aerobuildup-induced-drag``).

    Returns:
        The polar (C_L as AeroBuildup computes it, C_D the kernel's).
    """
    result, point = _sweep(asb_airplane, air, velocity_ms, alphas_deg, model_size)
    airplane: Any = asb_airplane  # the untyped asb.Airplane: its reference area
    reference = np.asarray(point.dynamic_pressure(), dtype=float) * float(airplane.s_ref)
    cd = np.asarray(kernel_drag(result, viscous_factor), dtype=float) / reference
    return Polar(
        alpha_deg=tuple(float(a) for a in alphas_deg),
        cl=tuple(float(v) for v in result["CL"]),
        cd=tuple(float(v) for v in np.broadcast_to(cd, (len(alphas_deg),))),
        conditions=FlowConditions(
            v_ms=velocity_ms,
            density=air.density,
            dynamic_viscosity=air.dynamic_viscosity,
            speed_of_sound=air.speed_of_sound,
        ),
    )


def scalar(value: object) -> float:
    """One number out of an AeroBuildup result, which may be a one-element array."""
    return float(np.asarray(value, dtype=float).reshape(-1).item())


def evaluate_forces(
    asb_airplane: object,
    air: AirState,
    velocity_ms: float,
    alpha_deg: float,
    model_size: str,
    viscous_factor: float,
) -> tuple[float, float]:
    """Run AeroBuildup once at one operating point and read lift and drag (canon ``aerobuildup-evaluation``).

    AeroBuildup forms the Reynolds number per section from ``V``, the local chord and the given air,
    and the Mach number as ``V / a``. Runs in a pool worker.

    Args:
        asb_airplane: The ``asb.Airplane`` (from ``to_asb_airplane``).
        air: The air state.
        velocity_ms: True airspeed in m/s.
        alpha_deg: Angle of attack in degrees.
        model_size: The NeuralFoil model size AeroBuildup evaluates its sections with.
        viscous_factor: k_e,D0 (rule ``aerobuildup-induced-drag``).

    Returns:
        Lift in N as AeroBuildup returns it (``L``), and the kernel's drag in N (:func:`kernel_drag`).
    """
    asb = load_aerosandbox()
    result = asb.AeroBuildup(
        asb_airplane,
        asb.OperatingPoint(atmosphere=FixedAtmosphere(air), velocity=velocity_ms, alpha=alpha_deg),
        model_size=model_size,
    ).run()
    return scalar(result["L"]), scalar(kernel_drag(result, viscous_factor))
