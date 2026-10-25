"""cg-for-target-margin: x_cg,design = x_NP - SM_target c_MAC, as a law and per method world (A10, A11)."""

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.cg_for_target_margin import cg_for_target_margin
from aero_kernel.schema import QuantityStatus, WarningSeverity
from aero_kernel.tests.formula_builders import (
    StubAtmosphere,
    close,
    context_with,
    inputs_from_model,
)
from aero_kernel.tests.np_builders import StubAvl
from aero_kernel.tests.test_neutral_point import (
    C_MAC,
    X_NP_AVL,
    X_NP_PAPPAS,
    X_NP_TEXTBOOK,
    only,
    run,
)

pytestmark = pytest.mark.asyncio

MODEL = shipped_build().model
SM_TARGET = 0.08


async def test_the_law_is_the_neutral_point_minus_the_margin_in_chords() -> None:
    """Hand value: 0.30 m - 0.10 * 0.20 m = 0.28 m."""
    x = inputs_from_model(
        MODEL,
        "cg-for-target-margin",
        {"neutral-point": 0.30, "static-margin-target": 0.10, "mean-aerodynamic-chord": 0.20},
    )
    result = await cg_for_target_margin(x, context_with(StubAtmosphere({})))
    assert close(result["x_cg_sm"], 0.28, 1e-12)


async def test_the_cg_is_an_interval_per_world() -> None:
    quantity = only((await run("centre-of-gravity-design", target=SM_TARGET))[0])
    assert quantity.status is QuantityStatus.OK
    assert quantity.interval is not None
    assert quantity.unit == "m"
    expected = {
        "neutral-point=textbook": X_NP_TEXTBOOK - SM_TARGET * C_MAC,
        "neutral-point=pappas": X_NP_PAPPAS - SM_TARGET * C_MAC,
        "neutral-point=avl": X_NP_AVL - SM_TARGET * C_MAC,
    }
    assert set(quantity.interval.worlds) == set(expected)
    for key, value in expected.items():
        assert close(quantity.interval.worlds[key], value, 1e-12), key


async def test_the_static_margin_of_that_cg_is_the_target_in_every_world() -> None:
    cg = only((await run("centre-of-gravity-design", target=SM_TARGET))[0])
    assert cg.interval is not None
    for key, value in cg.interval.worlds.items():
        margin = only((await run("static-margin-measured", cg=value))[0])
        assert margin.interval is not None
        assert close(margin.interval.worlds[key], SM_TARGET, 1e-9), key


async def test_a_missing_target_takes_the_starting_value_and_declares_it() -> None:
    result = (await run("centre-of-gravity-design"))[0]
    quantity = only(result)
    assert quantity.status is QuantityStatus.OK
    assert quantity.interval is not None
    assert close(quantity.interval.worlds["neutral-point=avl"], X_NP_AVL - 0.10 * C_MAC, 1e-12)
    used = {d.slug: d for d in result.provenance.defaults_used}
    assert used["static-margin-target"].value == 0.10


async def test_the_missing_fuselage_is_inherited_in_every_world() -> None:
    quantity = only((await run("centre-of-gravity-design", target=SM_TARGET))[0])
    fuselage = [w for w in quantity.warnings if w.code == "fuselage_not_modelled"]
    assert sorted(str(w.world) for w in fuselage) == [
        "neutral-point=avl",
        "neutral-point=pappas",
        "neutral-point=textbook",
    ]
    assert all(w.severity is WarningSeverity.PRACTICE for w in fuselage)


async def test_a_failing_avl_world_is_an_error_with_the_worlds_that_computed() -> None:
    """Pins the existing merge behaviour (ARCH 8.13) for this formula; it passes without new code."""
    avl = StubAvl(X_NP_AVL)
    avl.failure = FormulaError(ErrorCategory.NOT_CONVERGED, "not_converged", "avl failed", "retry")
    quantity = only((await run("centre-of-gravity-design", target=SM_TARGET, avl=avl))[0])
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.interval is None
    assert quantity.error is not None
    worlds_ok = quantity.error.detail["worlds_ok"]
    assert isinstance(worlds_ok, dict)
    assert set(worlds_ok) == {"neutral-point=textbook", "neutral-point=pappas"}
