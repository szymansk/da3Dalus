"""The numeric AeroBuildup runs in a fixed air state (ARCHITECTURE ch. 8.8).

Called from the OPT adapter's workers, in a pool process: the alpha sweep (the published polars) and
the evaluation of one operating point (canon ``aerobuildup-evaluation``). The OPT adapter owns every
AeroBuildup call of the kernel (ADR 0022); the IPOPT problems see AeroBuildup through the model
function of ``aero_model`` instead.
"""

from collections.abc import Sequence

import numpy as np
from aero_kernel.schema import FlowConditions, Polar
from aero_kernel.solvers.air import AirState, FixedAtmosphere
from aero_kernel.solvers.asb_airplane import load_aerosandbox

__all__ = ["evaluate_forces", "scalar", "sweep_polar"]


def sweep_polar(
    asb_airplane: object,
    air: AirState,
    velocity_ms: float,
    alphas_deg: Sequence[float],
    model_size: str,
) -> Polar:
    """Run AeroBuildup over the angles of attack on an already converted airplane.

    The one place that evaluates AeroBuildup in a fixed air state, used by the stall worker
    (ADR 0022). Runs in a pool worker.

    Args:
        asb_airplane: The ``asb.Airplane`` (from ``to_asb_airplane``).
        air: The air state.
        velocity_ms: True airspeed in m/s.
        alphas_deg: Angles of attack in degrees, strictly rising.
        model_size: The NeuralFoil model size AeroBuildup evaluates its sections with.

    Returns:
        The polar (CL, CD, Cm as AeroBuildup computes them).
    """
    asb = load_aerosandbox()
    alphas = np.asarray(alphas_deg, dtype=float)
    result = asb.AeroBuildup(
        asb_airplane,
        asb.OperatingPoint(
            atmosphere=FixedAtmosphere(air),
            velocity=np.full_like(alphas, velocity_ms),
            alpha=alphas,
        ),
        model_size=model_size,
    ).run()
    return Polar(
        alpha_deg=tuple(float(a) for a in alphas_deg),
        cl=tuple(float(v) for v in result["CL"]),
        cd=tuple(float(v) for v in result["CD"]),
        cm=tuple(float(v) for v in result["Cm"]),
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
) -> tuple[float, float]:
    """Run AeroBuildup once at one operating point and read its lift and drag (canon ``aerobuildup-evaluation``).

    AeroBuildup forms the Reynolds number per section from ``V``, the local chord and the given air,
    and the Mach number as ``V / a``. Runs in a pool worker.

    Args:
        asb_airplane: The ``asb.Airplane`` (from ``to_asb_airplane``).
        air: The air state.
        velocity_ms: True airspeed in m/s.
        alpha_deg: Angle of attack in degrees.
        model_size: The NeuralFoil model size AeroBuildup evaluates its sections with.

    Returns:
        Lift and drag in N, as AeroBuildup returns them (``L``, ``D``).
    """
    asb = load_aerosandbox()
    result = asb.AeroBuildup(
        asb_airplane,
        asb.OperatingPoint(atmosphere=FixedAtmosphere(air), velocity=velocity_ms, alpha=alpha_deg),
        model_size=model_size,
    ).run()
    return scalar(result["L"]), scalar(result["D"])
