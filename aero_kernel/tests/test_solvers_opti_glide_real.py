"""Best glide against real IPOPT: a parabolic polar with known answers, and the real AeroBuildup."""

import math
from types import SimpleNamespace
from typing import Any

import pytest
from aero_kernel.runtime import SolverRuntime
from aero_kernel.schema import Polar
from aero_kernel.solvers import opti as opti_module
from aero_kernel.solvers.asb_airplane import load_aerosandbox
from aero_kernel.solvers.opti import OptiAdapter, StallRequest
from aero_kernel.tests.solver_builders import airplane
from aero_kernel.tests.test_solvers_opti_real import GRAVITY, MASS_KG, sea_level, trainer

pytestmark = [pytest.mark.aero, pytest.mark.asyncio]

CD0, K, LIFT_SLOPE, CUBIC = 0.03, 0.05, 5.5, 30.7  # CL = a x - b x^3 (x in rad): a peak at 14 deg
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
    """Hand values, W = 1.5 kg * 9.81, rho = 1.225, S = 0.28 m^2, CD0 = 0.03, k = 0.05:

    V_md = sqrt(2 W / (rho S)) (k / CD0)^(1/4) = 9.2663 * 1.1362 = 10.529 m/s;
    CL_md = sqrt(CD0 / k) = 0.7746; (L/D)max = 1 / (2 sqrt(CD0 k)) = 12.910.
    The first CL peak of the cubic lies at 14 deg, so CL_md (alpha = 5.7 deg) is pre-stall.
    """
    install_parabolic(monkeypatch)
    air = sea_level()
    request = StallRequest(
        airplane=airplane(), mass_kg=MASS_KG, gravity=GRAVITY, n_load=1.0, air=air
    )
    solution = opti_module.best_glide_worker(request).value
    weight = MASS_KG * GRAVITY
    assert math.isclose(
        solution.v_md,
        math.sqrt(2 * weight / (air.density * S_REF)) * (K / CD0) ** 0.25,
        rel_tol=1e-6,
    )
    assert math.isclose(solution.cl_md, math.sqrt(CD0 / K), rel_tol=1e-6)
    assert math.isclose(solution.e_max, 1 / (2 * math.sqrt(CD0 * K)), rel_tol=1e-6)
    assert math.isclose(cl_of(solution.alpha_md), solution.cl_md, rel_tol=1e-6)


async def test_a_heavier_airplane_flies_the_best_glide_faster_by_the_square_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_parabolic(monkeypatch)
    air = sea_level()
    light, heavy = (
        opti_module.best_glide_worker(
            StallRequest(airplane=airplane(), mass_kg=m, gravity=GRAVITY, n_load=1.0, air=air)
        ).value
        for m in (1.0, 4.0)
    )
    assert math.isclose(heavy.v_md / light.v_md, 2.0, rel_tol=1e-5)
    assert math.isclose(heavy.e_max, light.e_max, rel_tol=1e-6)  # E_max does not depend on weight


async def test_the_real_trainer_best_glide_against_a_dense_sweep() -> None:
    """The canon entry's dense-sweep cross-check (agreement 1-2 %): for each speed the alpha with
    L = W is found by interpolation on a dense alpha sweep; the minimum drag over the speeds."""
    import numpy as np
    from aero_kernel.solvers.aerobuildup import sweep_polar
    from aero_kernel.solvers.asb_airplane import to_asb_airplane

    air = sea_level()
    async with SolverRuntime(max_workers=1) as runtime:
        glide = await OptiAdapter(runtime).best_glide(trainer(), MASS_KG, GRAVITY, 1.0, air)
    converted = to_asb_airplane(trainer())
    area = float(converted.s_ref)
    weight = MASS_KG * GRAVITY
    alphas = [-5.0 + 0.05 * k for k in range(0, 360)]  # -5 .. 13 deg, below the first peak
    best: tuple[float, float] | None = None
    for v in np.arange(9.0, 25.0, 0.25):
        polar = sweep_polar(converted, air, float(v), alphas, opti_module.NEURALFOIL_MODEL_SIZE)
        lift = [0.5 * air.density * v**2 * area * cl for cl in polar.cl]
        index = next(k for k in range(len(lift) - 1) if lift[k] <= weight < lift[k + 1])
        fraction = (weight - lift[index]) / (lift[index + 1] - lift[index])
        cd = polar.cd[index] + fraction * (polar.cd[index + 1] - polar.cd[index])
        drag = 0.5 * air.density * v**2 * area * cd
        if best is None or drag < best[1]:
            best = (float(v), drag)
    assert best is not None
    assert math.isclose(glide.solution.v_md, best[0], rel_tol=0.03)  # the dense grid's step is 0.25
    assert math.isclose(glide.solution.e_max, weight / best[1], rel_tol=0.02)
