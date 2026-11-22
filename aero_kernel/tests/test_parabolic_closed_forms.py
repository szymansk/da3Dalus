"""The closed forms of the parabolic polar (#1401): each against a hand value, ``x`` built from the model."""

import math

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.context import Context
from aero_kernel.errors import ErrorCategory
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
from aero_kernel.formulas.sink_rate import (
    drag_coefficient_positive,
    lift_coefficient_positive,
    sink_rate,
)
from aero_kernel.schema import ComputeResult, KernelWarning, QuantityResult, QuantityStatus
from aero_kernel.tests.formula_builders import (
    StubAtmosphere,
    close,
    context_with,
    inputs_from_model,
)
from aero_kernel.tests.stall_stubs import CD0, K, StubOpti
from aero_kernel.tests.test_parabolic_polar_fit import polar_of
from aero_kernel.tests.test_roll_rate_engine import GRAVITY, MASS, RHO, run

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


@pytest.mark.parametrize(
    ("e_osw", "ar"),
    [
        (0.0, 8.0),
        (-0.3, 8.0),
        (0.8, 0.0),
        (0.8, -1.0),
        (math.nan, 8.0),
        (0.8, math.nan),
    ],
)
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
    ("e_osw", "ar", "cd0"),
    [
        (0.8, 8.0, 0.0),
        (0.8, 8.0, -0.01),
        (0.0, 8.0, 0.03),
        (0.8, 0.0, 0.03),
        (0.8, -8.0, 0.03),
        (-0.3, 8.0, 0.03),
        (math.nan, 8.0, 0.03),
        (0.8, math.nan, 0.03),
        (0.8, 8.0, math.nan),
    ],
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


@pytest.mark.parametrize(("e_osw", "ar", "cd0"), [(0.8, 8.0, 0.03), (1e-12, 1e-12, 1e-12)])
async def test_max_lift_to_drag_precondition_holds_for_every_positive_parabola(
    e_osw: float, ar: float, cd0: float
) -> None:
    """Each of e, AR and C_D0 is greater than zero: held, also just above the boundary."""
    x = inputs_from_model(
        MODEL,
        "max-lift-to-drag-parabolic",
        {"oswald-efficiency": e_osw, "aspect-ratio": ar, "zero-lift-drag-coefficient": cd0},
    )
    assert max_ld_parabola_defined(x).state == "held"


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
        (30.0, 1.225, 0.03, 0.0),
        (-30.0, 1.225, 0.03, 0.05),
        (30.0, -1.225, 0.03, 0.05),
        (30.0, 1.225, -0.03, 0.05),
        (math.nan, 1.225, 0.03, 0.05),
        (30.0, math.nan, 0.03, 0.05),
        (30.0, 1.225, math.nan, 0.05),
        (30.0, 1.225, 0.03, math.nan),
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


@pytest.mark.parametrize(
    ("w_s", "rho", "cd0", "k"), [(30.0, 1.225, 0.03, 0.05), (1e-12, 1e-12, 1e-12, 1e-12)]
)
async def test_minimum_drag_speed_precondition_holds_for_every_positive_parabola(
    w_s: float, rho: float, cd0: float, k: float
) -> None:
    """All four quantities greater than zero: held, also just above the boundary."""
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
    assert v_md_parabola_defined(x).state == "held"


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


@pytest.mark.parametrize("cl", [0.0, -0.2, -math.inf, math.nan])
async def test_sink_rate_precondition_refuses_a_lift_coefficient_at_or_below_zero(
    cl: float,
) -> None:
    x = inputs_from_model(
        MODEL,
        "sink-rate",
        {"flight-speed": 10.0, "lift-coefficient": cl, "drag-coefficient-parabolic": 0.05},
    )
    assert lift_coefficient_positive(x).state == "violated"


@pytest.mark.parametrize("cl", [0.5, 1e-12])
async def test_sink_rate_precondition_holds_for_a_positive_lift_coefficient(cl: float) -> None:
    """Greater than zero is held, also 1e-12 just above the boundary."""
    x = inputs_from_model(
        MODEL,
        "sink-rate",
        {"flight-speed": 10.0, "lift-coefficient": cl, "drag-coefficient-parabolic": 0.05},
    )
    assert lift_coefficient_positive(x).state == "held"


@pytest.mark.parametrize("cd", [0.0, -0.01, -math.inf, math.nan])
async def test_sink_rate_precondition_refuses_a_drag_coefficient_at_or_below_zero(
    cd: float,
) -> None:
    x = inputs_from_model(
        MODEL,
        "sink-rate",
        {"flight-speed": 10.0, "lift-coefficient": 0.5, "drag-coefficient-parabolic": cd},
    )
    assert drag_coefficient_positive(x).state == "violated"


async def test_sink_rate_precondition_holds_for_a_positive_drag_coefficient() -> None:
    x = inputs_from_model(
        MODEL,
        "sink-rate",
        {"flight-speed": 10.0, "lift-coefficient": 0.5, "drag-coefficient-parabolic": 0.05},
    )
    assert drag_coefficient_positive(x).state == "held"


S_REF_STUB = 0.16  # plane() of test_roll_rate_engine: 0.4 m half span, chord 0.2 m, two wings


def only(result: ComputeResult, slug: str) -> QuantityResult:
    """The result of one requested quantity."""
    (found,) = [q for q in result.quantities if q.slug == slug]
    return found


async def test_the_sink_rate_through_the_engine_is_speed_times_the_stub_parabola_over_cl() -> None:
    """V = 10 m/s, m = 0.15 kg, rho = 1.225, S_ref = 0.16 m^2, parabola C_D0 0.03, k 0.05.

    q S = 0.5 * 1.225 * 100 * 0.16 = 9.8 N, W = 0.15 * 9.80665 = 1.4709975 N,
    C_L = 1.4709975 / 9.8 = 0.150101786, C_D = 0.03 + 0.05 C_L^2 = 0.031126527,
    w = 10 * C_D / C_L = 2.0736947 m/s.
    """
    result = await run(
        "sink-rate",
        "lift-coefficient",
        "drag-coefficient-parabolic",
        delta=None,
        extra={"flight-speed": 10.0},
    )
    assert all(q.status is QuantityStatus.OK for q in result.quantities), result.quantities
    sink = only(result, "sink-rate")
    assert sink.unit == "m/s"
    cl = MASS * GRAVITY / (0.5 * RHO * 10.0**2 * S_REF_STUB)
    assert close(only(result, "lift-coefficient").value, cl, 1e-9)
    assert close(sink.value, 10.0 * (0.03 + 0.05 * cl**2) / cl, 1e-9)
    assert close(sink.value, 2.0736947, 1e-7)


async def test_a_negative_load_factor_refuses_the_sink_rate_through_the_engine() -> None:
    """n = -1 gives C_L = -0.150101786: no steady glide, error and no value."""
    result = await run("sink-rate", delta=None, extra={"flight-speed": 10.0, "load-factor": -1.0})
    sink = only(result, "sink-rate")
    assert sink.status is QuantityStatus.ERROR
    assert sink.value is None
    assert sink.error is not None
    assert sink.error.code == "precondition_violated"
    assert sink.error.detail["precondition"] == "lift_coefficient_positive"


async def test_the_minimum_drag_speed_probe_through_the_engine_follows_the_stub_parabola() -> None:
    """W/S = 0.15 * 9.80665 / 0.16 = 9.19373 N/m^2; C_L,md = sqrt(0.03 / 0.05) = 0.774597;
    V = sqrt(2 * 9.19373 / (1.225 * 0.774597)) = 4.40205 m/s."""
    result = await run("minimum-drag-speed-probe", delta=None)
    probe = only(result, "minimum-drag-speed-probe")
    assert probe.status is QuantityStatus.OK
    assert probe.unit == "m/s"
    w_s = MASS * GRAVITY / S_REF_STUB
    assert close(probe.value, math.sqrt(2.0 * w_s / (RHO * math.sqrt(CD0 / K))), 1e-9)
    assert close(probe.value, 4.40205, 1e-5)


async def test_a_falling_polar_gives_no_minimum_drag_speed_probe() -> None:
    """k < 0 stops the chain at the induced-drag factor: the probe is upstream_failed, no value."""
    opti = StubOpti()
    opti.level_answer = lambda levels: polar_of(lambda cl: 0.05 - 0.02 * cl * cl, tuple(levels))
    result = await run("minimum-drag-speed-probe", opti=opti, delta=None)
    probe = only(result, "minimum-drag-speed-probe")
    assert probe.status is QuantityStatus.ERROR
    assert probe.value is None
    assert probe.error is not None
    assert probe.error.category is ErrorCategory.UPSTREAM_FAILED
    assert probe.error.code == "upstream_failed"
