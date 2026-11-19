"""An independent computation of the drive-train balance for the powertrain tests (plain Python).

Written separately from the kernel's code on purpose: a piecewise-linear interpolation of the
published APC 13x8E table (J inside a block, then rpm between blocks) and bisection of the two balances
with the T-Motor AT2814 KV900 values (K_v 900 rpm/V, R_m 0.082 ohm, I_0 1.2 A) on a 14.8 V pack.
"""

import math
from dataclasses import dataclass
from typing import Any

from aero_kernel.tests.components_builders import apc_13x8e_table

RHO = 1.225
D_PROP = 13 * 0.0254
U_BAT = 14.8
KV, I0, RM = 900.0, 1.2, 0.082
KV_RAD = 2 * math.pi * KV / 60
ITERATIONS = 200


@dataclass(frozen=True)
class Point:
    """A balance point: the propeller speed in rpm, the motor current, torque and the thrust."""

    rpm: float
    current: float
    torque: float
    thrust: float


def lerp(x: float, xs: list[float], ys: list[float]) -> float:
    """Piecewise-linear interpolation of ``ys`` over the ascending ``xs`` (x inside the range)."""
    for k in range(1, len(xs)):
        if x <= xs[k]:
            return ys[k - 1] + (x - xs[k - 1]) / (xs[k] - xs[k - 1]) * (ys[k] - ys[k - 1])
    raise ValueError(f"{x} is above the table")


def coefficients(rpm: float, j: float) -> tuple[float, float]:
    """``C_T`` and ``C_P`` at the speed and the advance ratio."""
    blocks: list[dict[str, Any]] = apc_13x8e_table()["blocks"]
    rpms = [float(b["rpm"]) for b in blocks]
    c_t = lerp(rpm, rpms, [lerp(j, b["j"], b["ct"]) for b in blocks])
    c_p = lerp(rpm, rpms, [lerp(j, b["j"], b["cp"]) for b in blocks])
    return c_t, c_p


def full_throttle(v: float) -> Point:
    """The torque balance at the airspeed (bisection on rpm between 1000 and the free-run speed)."""
    low, high = 1000.0, KV * U_BAT
    rpm = 0.5 * (low + high)
    for _ in range(ITERATIONS):
        rpm = 0.5 * (low + high)
        n = rpm / 60
        _, c_p = coefficients(rpm, v / (n * D_PROP))
        q_p = c_p * RHO * n**2 * D_PROP**5 / (2 * math.pi)
        q_m = ((U_BAT - 2 * math.pi * n / KV_RAD) / RM - I0) / KV_RAD
        if q_m - q_p > 0:
            low = rpm
        else:
            high = rpm
    n = rpm / 60
    c_t, c_p = coefficients(rpm, v / (n * D_PROP))
    q_p = c_p * RHO * n**2 * D_PROP**5 / (2 * math.pi)
    current = (U_BAT - 2 * math.pi * n / KV_RAD) / RM
    return Point(rpm, current, q_p, c_t * RHO * n**2 * D_PROP**4)


@dataclass(frozen=True)
class PartLoad:
    """The part-load point: speed in 1/s, battery current and power, and the demand ratio."""

    n_pl: float
    i_bat: float
    p_bat: float
    r_t: float


def part_load(v: float, drag: float) -> PartLoad:
    """The speed where the table's thrust equals the drag, and the battery side of route B."""
    low, high = 3000.0, 18000.0
    rpm = 0.5 * (low + high)
    for _ in range(ITERATIONS):
        rpm = 0.5 * (low + high)
        n = rpm / 60
        c_t, _ = coefficients(rpm, v / (n * D_PROP))
        if c_t * RHO * n**2 * D_PROP**4 < drag:
            low = rpm
        else:
            high = rpm
    n = rpm / 60
    _, c_p = coefficients(rpm, v / (n * D_PROP))
    torque = c_p * RHO * n**2 * D_PROP**5 / (2 * math.pi)
    current = I0 + torque * KV_RAD
    power = (current * RM + 2 * math.pi * n / KV_RAD) * current
    return PartLoad(n, power / U_BAT, power, drag / full_throttle(v).thrust)
