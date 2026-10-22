"""AeroBuildup over angle of attack, the one place that evaluates it (ARCHITECTURE ch. 8.8).

Called from the stall worker, in a pool process. The adapter class (``aerobuildup.sweep``) arrives
with ``aerobuildup-evaluation``, the first formula that calls AeroBuildup itself (ADR 0021).
"""

from collections.abc import Sequence

import numpy as np
from aero_kernel.schema import Polar
from aero_kernel.solvers.air import AirState, FixedAtmosphere
from aero_kernel.solvers.asb_airplane import load_aerosandbox

__all__ = ["sweep_polar"]


def sweep_polar(
    asb_airplane: object, air: AirState, velocity_ms: float, alphas_deg: Sequence[float]
) -> Polar:
    """Run AeroBuildup over the angles of attack on an already converted airplane.

    The one place that evaluates AeroBuildup in a fixed air state, used by the stall worker
    (ADR 0022). Runs in a pool worker.

    Args:
        asb_airplane: The ``asb.Airplane`` (from ``to_asb_airplane``).
        air: The air state.
        velocity_ms: True airspeed in m/s.
        alphas_deg: Angles of attack in degrees, strictly rising.

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
    ).run()
    return Polar(
        alpha_deg=tuple(float(a) for a in alphas_deg),
        cl=tuple(float(v) for v in result["CL"]),
        cd=tuple(float(v) for v in result["CD"]),
        cm=tuple(float(v) for v in result["Cm"]),
    )
