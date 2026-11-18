"""The closed forms of the parabolic polar (#1401): each against a hand value, ``x`` built from the model."""

import math

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.context import Context
from aero_kernel.formulas.drag_polar import drag_polar
from aero_kernel.formulas.induced_drag_factor import induced_drag_factor, oswald_factor_positive
from aero_kernel.formulas.max_lift_to_drag_parabolic import (
    max_lift_to_drag_parabolic,
)
from aero_kernel.formulas.max_lift_to_drag_parabolic import (
    parabola_defined as max_ld_parabola_defined,
)
from aero_kernel.formulas.minimum_drag_speed_closed_form import (
    minimum_drag_speed_closed_form,
)
from aero_kernel.formulas.minimum_drag_speed_closed_form import (
    parabola_defined as v_md_parabola_defined,
)
from aero_kernel.formulas.sink_rate import lift_coefficient_positive, sink_rate
from aero_kernel.schema import KernelWarning
from aero_kernel.tests.formula_builders import (
    StubAtmosphere,
    close,
    context_with,
    inputs_from_model,
)

pytestmark = pytest.mark.asyncio

MODEL = shipped_build().model


def detail_of(warning: KernelWarning, key: str) -> float:
    """A number of a warning's detail."""
    value = warning.detail[key]
    assert isinstance(value, float)
    return value


def context() -> Context:
    """A context without a solver."""
    return context_with(StubAtmosphere({}))


async def test_induced_drag_factor_is_one_over_pi_e_ar() -> None:
    """Hand value: k = 1 / (pi * 0.8 * 8) = 1 / 20.1061929829747 = 0.0497359197162173."""
    x = inputs_from_model(
        MODEL, "induced-drag-factor", {"oswald-efficiency": 0.8, "aspect-ratio": 8.0}
    )
    result = await induced_drag_factor(x, context())
    assert set(result) == {"k"}
    assert close(result["k"], 0.0497359197162173, 1e-12)


@pytest.mark.parametrize(("e_osw", "ar"), [(0.0, 8.0), (-0.3, 8.0), (0.8, 0.0), (0.8, -1.0)])
async def test_induced_drag_factor_precondition_refuses_what_has_no_finite_positive_k(
    e_osw: float, ar: float
) -> None:
    x = inputs_from_model(
        MODEL, "induced-drag-factor", {"oswald-efficiency": e_osw, "aspect-ratio": ar}
    )
    assert oswald_factor_positive(x).state == "violated"


async def test_induced_drag_factor_precondition_holds_for_a_physical_factor() -> None:
    x = inputs_from_model(
        MODEL, "induced-drag-factor", {"oswald-efficiency": 0.8, "aspect-ratio": 8.0}
    )
    assert oswald_factor_positive(x).state == "held"


async def test_drag_polar_is_cd0_plus_k_cl_squared() -> None:
    """Hand value: 0.03 + 0.05 * 0.6^2 = 0.03 + 0.018 = 0.048."""
    x = inputs_from_model(
        MODEL,
        "drag-polar",
        {"zero-lift-drag-coefficient": 0.03, "induced-drag-factor": 0.05, "lift-coefficient": 0.6},
    )
    result = await drag_polar(x, context())
    assert set(result) == {"cd_par"}
    assert close(result["cd_par"], 0.048, 1e-12)


async def test_max_lift_to_drag_probe_is_half_sqrt_pi_e_ar_over_cd0() -> None:
    """Hand value: 0.5 * sqrt(pi * 0.8 * 8 / 0.03) = 0.5 * sqrt(670.2064327658225) = 12.9448...

    Cross-check from the polar itself: at the optimum C_L = sqrt(C_D0 / k) and C_D = 2 C_D0.
    """
    x = inputs_from_model(
        MODEL,
        "max-lift-to-drag-parabolic",
        {"oswald-efficiency": 0.8, "aspect-ratio": 8.0, "zero-lift-drag-coefficient": 0.03},
    )
    result = await max_lift_to_drag_parabolic(x, context())
    assert set(result) == {"e_max_probe"}
    assert close(result["e_max_probe"], 0.5 * math.sqrt(670.2064327658225), 1e-12)
    k = 1.0 / (math.pi * 0.8 * 8.0)
    assert close(result["e_max_probe"], math.sqrt(0.03 / k) / (2 * 0.03), 1e-12)


@pytest.mark.parametrize(
    ("e_osw", "ar", "cd0"), [(0.8, 8.0, 0.0), (0.8, 8.0, -0.01), (0.0, 8.0, 0.03)]
)
async def test_max_lift_to_drag_precondition_refuses_an_undefined_parabola(
    e_osw: float, ar: float, cd0: float
) -> None:
    x = inputs_from_model(
        MODEL,
        "max-lift-to-drag-parabolic",
        {"oswald-efficiency": e_osw, "aspect-ratio": ar, "zero-lift-drag-coefficient": cd0},
    )
    assert max_ld_parabola_defined(x).state == "violated"


async def test_minimum_drag_speed_probe_follows_the_parabola() -> None:
    """Hand value: C_L,md = sqrt(0.03 / 0.05) = 0.774597; V = sqrt(2 * 30 / (1.225 * 0.774597)) = 7.9520...

    Cross-check: at that speed the lift balance W/S = q C_L,md holds.
    """
    x = inputs_from_model(
        MODEL,
        "minimum-drag-speed-closed-form",
        {
            "wing-loading": 30.0,
            "air-density": 1.225,
            "zero-lift-drag-coefficient": 0.03,
            "induced-drag-factor": 0.05,
        },
    )
    result = await minimum_drag_speed_closed_form(x, context())
    assert set(result) == {"v_md_probe"}
    cl_md = math.sqrt(0.03 / 0.05)
    assert close(result["v_md_probe"], math.sqrt(2.0 * 30.0 / (1.225 * cl_md)), 1e-12)
    assert close(0.5 * 1.225 * result["v_md_probe"] ** 2 * cl_md, 30.0, 1e-12)


@pytest.mark.parametrize(
    ("w_s", "rho", "cd0", "k"),
    [
        (0.0, 1.225, 0.03, 0.05),
        (30.0, 0.0, 0.03, 0.05),
        (30.0, 1.225, 0.0, 0.05),
        (30.0, 1.225, 0.03, -0.05),
    ],
)
async def test_minimum_drag_speed_precondition_refuses_an_undefined_parabola(
    w_s: float, rho: float, cd0: float, k: float
) -> None:
    x = inputs_from_model(
        MODEL,
        "minimum-drag-speed-closed-form",
        {
            "wing-loading": w_s,
            "air-density": rho,
            "zero-lift-drag-coefficient": cd0,
            "induced-drag-factor": k,
        },
    )
    assert v_md_parabola_defined(x).state == "violated"


async def test_sink_rate_is_speed_times_cd_over_cl() -> None:
    """Hand value: 10 m/s * 0.05 / 0.5 = 1.0 m/s; the glide ratio 10 is above the floor, no warning."""
    x = inputs_from_model(
        MODEL,
        "sink-rate",
        {"flight-speed": 10.0, "lift-coefficient": 0.5, "drag-coefficient-parabolic": 0.05},
    )
    ctx = context()
    result = await sink_rate(x, ctx)
    assert set(result) == {"w_sink"}
    assert close(result["w_sink"], 1.0, 1e-12)
    assert ctx.warnings == ()


async def test_sink_rate_below_the_glide_ratio_floor_is_declared_and_still_returned() -> None:
    """E = 0.5 / 0.2 = 2.5: gamma = atan(0.4) = 21.8 deg; the dropped factors are exact."""
    x = inputs_from_model(
        MODEL,
        "sink-rate",
        {"flight-speed": 10.0, "lift-coefficient": 0.5, "drag-coefficient-parabolic": 0.2},
    )
    ctx = context()
    result = await sink_rate(x, ctx)
    assert close(result["w_sink"], 4.0, 1e-12)
    (warning,) = ctx.warnings
    assert warning.code == "small_glide_angle"
    gamma = math.atan(0.4)
    assert close(detail_of(warning, "glide_ratio"), 2.5, 1e-12)
    assert close(detail_of(warning, "glide_angle_deg"), math.degrees(gamma), 1e-12)
    assert close(detail_of(warning, "from_tan_for_sin"), 1.0 / math.cos(gamma) - 1.0, 1e-12)
    exact_lift = 1.0 / math.sqrt(math.cos(gamma)) - 1.0
    assert close(detail_of(warning, "from_lift_equals_weight"), exact_lift, 1e-12)
    assert close(detail_of(warning, "floor"), 5.0, 1e-12)


async def test_sink_rate_at_the_floor_is_not_declared() -> None:
    """The floor itself is inside (a violation is strictly below it), as for the AVL range."""
    x = inputs_from_model(
        MODEL,
        "sink-rate",
        {"flight-speed": 10.0, "lift-coefficient": 0.5, "drag-coefficient-parabolic": 0.1},
    )
    ctx = context()
    await sink_rate(x, ctx)
    assert ctx.warnings == ()


@pytest.mark.parametrize("cl", [0.0, -0.2])
async def test_sink_rate_precondition_refuses_a_lift_coefficient_at_or_below_zero(
    cl: float,
) -> None:
    x = inputs_from_model(
        MODEL,
        "sink-rate",
        {"flight-speed": 10.0, "lift-coefficient": cl, "drag-coefficient-parabolic": 0.05},
    )
    assert lift_coefficient_positive(x).state == "violated"
