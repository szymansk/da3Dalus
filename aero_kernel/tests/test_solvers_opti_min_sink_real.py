"""Minimum sink against real IPOPT: a parabolic polar with known answers (aero tier)."""

import math
import sys
from types import SimpleNamespace
from typing import Any

import pytest
from aero_kernel.schema import Polar
from aero_kernel.solvers import opti as opti_module
from aero_kernel.solvers.asb_airplane import load_aerosandbox
from aero_kernel.solvers.opti import StallRequest
from aero_kernel.tests.solver_builders import airplane
from aero_kernel.tests.test_solvers_opti_real import GRAVITY, MASS_KG, sea_level

pytestmark = [pytest.mark.aero, pytest.mark.asyncio]

# CL = a x - b x^3 (x in rad): a peak at 14 deg, C_L,max = 0.896. CD0 is chosen so that
# CL_mp = sqrt(3 CD0 / k) = 0.775 lies below the peak: the minimum-sink point of a parabolic polar
# sits close to C_L,max.
CD0, K, LIFT_SLOPE, CUBIC = 0.01, 0.05, 5.5, 30.7
S_REF = 0.28


def cl_of(alpha_deg: Any) -> Any:  # a float or a CasADi expression
    x = alpha_deg * math.pi / 180.0
    return LIFT_SLOPE * x - CUBIC * x**3


def install_parabolic(monkeypatch: pytest.MonkeyPatch) -> None:
    """AeroBuildup replaced by CD = CD0 + k CL^2; the optimiser stays the real IPOPT."""
    real = load_aerosandbox()

    class Parabolic:
        def __init__(self, _airplane: object, op_point: Any, **_: object) -> None:
            self.op = op_point

        def run(self) -> dict[str, Any]:
            q = 0.5 * 1.2249991558877122 * self.op.velocity**2 * S_REF
            cl = cl_of(self.op.alpha)
            return {"L": q * cl, "D": q * (CD0 + K * cl**2), "CL": cl}

    def operating_point(**kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(**kwargs)

    def sweep(_airplane: object, _air: object, _v: float, alphas: list[float], _size: str) -> Polar:
        cl = tuple(float(cl_of(a)) for a in alphas)
        return Polar(alpha_deg=tuple(alphas), cl=cl, cd=(CD0,) * len(cl), cm=(0.0,) * len(cl))

    fake = SimpleNamespace(Opti=real.Opti, OperatingPoint=operating_point, AeroBuildup=Parabolic)
    monkeypatch.setattr(opti_module, "load_aerosandbox", lambda: fake)
    monkeypatch.setattr(opti_module, "sweep_polar", sweep)

    def convert(_airplane: object) -> SimpleNamespace:
        return SimpleNamespace(s_ref=S_REF)

    monkeypatch.setattr(opti_module, "to_asb_airplane", convert)


async def test_a_parabolic_polar_gives_the_closed_form_answers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hand values, W = 1.5 kg * 9.81, rho = 1.225, S = 0.28 m^2, CD0 = 0.01, k = 0.05:

    CL_mp = sqrt(3 CD0 / k) = 0.7746;
    V_mp = sqrt(2 W / (rho S)) (k / (3 CD0))^(1/4) = 9.2663 * 1.1362 = 10.529 m/s,
    and V_mp = V_md / 3^(1/4) (Sadraey 4.3.5.2), checked against the best-glide worker.
    """
    install_parabolic(monkeypatch)
    air = sea_level()
    request = StallRequest(
        airplane=airplane(), mass_kg=MASS_KG, gravity=GRAVITY, n_load=1.0, air=air
    )
    solution = opti_module.min_sink_worker(request).value
    glide = opti_module.best_glide_worker(request).value
    weight = MASS_KG * GRAVITY
    assert math.isclose(
        solution.v_mp,
        math.sqrt(2 * weight / (air.density * S_REF)) * (K / (3 * CD0)) ** 0.25,
        rel_tol=1e-6,
    )
    assert math.isclose(solution.cl_mp, math.sqrt(3 * CD0 / K), rel_tol=1e-6)
    assert math.isclose(cl_of(solution.alpha_mp), solution.cl_mp, rel_tol=1e-6)
    assert math.isclose(solution.v_mp, glide.v_md / 3**0.25, rel_tol=1e-6)


async def test_a_heavier_airplane_flies_the_minimum_sink_faster_by_the_square_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_parabolic(monkeypatch)
    air = sea_level()
    light, heavy = (
        opti_module.min_sink_worker(
            StallRequest(airplane=airplane(), mass_kg=m, gravity=GRAVITY, n_load=1.0, air=air)
        ).value
        for m in (1.0, 4.0)
    )
    assert math.isclose(heavy.v_mp / light.v_mp, 2.0, rel_tol=1e-5)
    assert math.isclose(heavy.cl_mp, light.cl_mp, rel_tol=1e-6)


async def test_a_minimum_beyond_the_lift_peak_is_returned_at_the_peak_flagged_stall_limited(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With CD0 = 0.03 the parabolic minimum-sink lift coefficient (1.34) exceeds C_L,max (0.896):
    the sink power is still falling at the lift peak, so the value is the stall boundary, flagged
    (#1268, maintainer 2026-10-25): the alpha and C_L of the first peak, no margin."""
    install_parabolic(monkeypatch)
    monkeypatch.setattr(sys.modules[__name__], "CD0", 0.03)
    request = StallRequest(
        airplane=airplane(), mass_kg=MASS_KG, gravity=GRAVITY, n_load=1.0, air=sea_level()
    )
    solution = opti_module.min_sink_worker(request).value
    assert solution.stall_limited is True
    peak_alpha = math.degrees(math.sqrt(LIFT_SLOPE / (3 * CUBIC)))
    assert math.isclose(solution.alpha_mp, peak_alpha, abs_tol=0.3)
    assert math.isclose(solution.cl_mp, cl_of(solution.alpha_mp), rel_tol=1e-6)


async def test_an_interior_minimum_is_not_flagged(monkeypatch: pytest.MonkeyPatch) -> None:
    install_parabolic(monkeypatch)
    request = StallRequest(
        airplane=airplane(), mass_kg=MASS_KG, gravity=GRAVITY, n_load=1.0, air=sea_level()
    )
    assert opti_module.min_sink_worker(request).value.stall_limited is False
