"""``tail-efficiency`` (eta_h): a defined value of the textbook neutral-point world (#1205).

Hand values: K = eta (1 - 4/(AR_w + 2)) [AR_h/(AR_h + 2)] / [AR_w/(AR_w + 2)] = eta * (5/9) * (6/7)
= eta * 10/21 for the fixture planform; x_NP = (S_w x_w + K S_h x_h) / (S_w + K S_h).
"""

import importlib.util
import logging
from pathlib import Path
from types import ModuleType

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.errors import ErrorCategory
from aero_kernel.schema import QuantityResult, QuantityStatus
from aero_kernel.tests.formula_builders import close
from aero_kernel.tests.test_neutral_point import (
    S_H,
    S_W,
    X_AC_H,
    X_AC_W,
    only,
    run,
)

pytestmark = pytest.mark.asyncio

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "build_canon_navigator.py"


def textbook_x_np(eta: float) -> float:
    """The textbook-world neutral point of the fixture for the tail efficiency ``eta``."""
    weight = eta * 10 / 21
    return (S_W * X_AC_W + weight * S_H * X_AC_H) / (S_W + weight * S_H)


def textbook(quantity: QuantityResult) -> float:
    assert quantity.interval is not None
    return quantity.interval.worlds["neutral-point=textbook"]


async def test_the_default_is_065_taken_declared_and_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="aero_kernel"):
        result, _ = await run("neutral-point")
    (default,) = [d for d in result.provenance.defaults_used if d.slug == "tail-efficiency"]
    assert close(default.value, 0.65, 1e-12)
    assert default.unit == "1"
    assert "Lennon" in default.source
    lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith("default used")]
    assert any(line.startswith("default used: tail-efficiency = 0.65 ") for line in lines)
    assert close(textbook(only(result)), textbook_x_np(0.65), 1e-12)


@pytest.mark.parametrize("eta", [0.9, 0.5])
async def test_a_supplied_eta_is_used_and_is_no_default(eta: float) -> None:
    """Hand values: eta 0.9 gives K = 3/7, eta 0.5 gives K = 5/21."""
    result, _ = await run("neutral-point", eta=eta)
    assert "tail-efficiency" not in [d.slug for d in result.provenance.defaults_used]
    assert close(textbook(only(result)), textbook_x_np(eta), 1e-12)


async def test_eta_09_reproduces_the_former_constant() -> None:
    """Regression continuity: the value before #1205, 0.0387142857 / 0.2971428571, with eta given."""
    result, _ = await run("neutral-point", eta=0.9)
    assert close(textbook(only(result)), 0.0387142857 / 0.2971428571, 1e-9)


async def test_eta_moves_only_the_textbook_world() -> None:
    low, _ = await run("neutral-point", eta=0.4)
    high, _ = await run("neutral-point", eta=1.0)
    assert (low_interval := only(low).interval) is not None
    assert (high_interval := only(high).interval) is not None
    assert (
        low_interval.worlds["neutral-point=pappas"] == high_interval.worlds["neutral-point=pappas"]
    )
    assert low_interval.worlds["neutral-point=avl"] == high_interval.worlds["neutral-point=avl"]
    assert textbook(only(low)) < textbook(only(high))


async def test_the_default_moves_the_textbook_world_forward_of_the_former_constant() -> None:
    result, _ = await run("neutral-point")
    assert textbook(only(result)) < textbook_x_np(0.9)


@pytest.mark.parametrize(
    ("eta", "code"),
    [(0.0, "non_positive_value"), (-0.2, "non_positive_value"), (1.01, "value_above_maximum")],
)
async def test_an_inadmissible_eta_is_rejected_with_its_path(eta: float, code: str) -> None:
    result, _ = await run("neutral-point", eta=eta)
    (error,) = result.input_errors
    assert error.code == code
    assert error.category is ErrorCategory.INVALID_INPUT
    assert error.input_path == "values.tail-efficiency"
    assert error.hint


async def test_eta_of_one_is_admissible() -> None:
    result, _ = await run("neutral-point", eta=1.0)
    assert result.input_errors == ()
    assert only(result).status is QuantityStatus.OK


async def test_the_quantity_has_a_sourced_default() -> None:
    namespace = shipped_build().model.namespaces["calc"]
    quantity = namespace.quantities["tail-efficiency"]
    assert (quantity.symbol, quantity.unit, quantity.role) == ("eta_h", "1", "input")
    assert quantity.positive is True
    assert close(quantity.at_most, 1.0, 1e-12)
    assert (
        namespace.defaults["tail-efficiency"].basis == "sourced"
    )  # Lennon Ch. 7/8, maintainer 2026-10-25


def load_navigator_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("build_canon_navigator", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def test_the_navigator_no_longer_marks_the_neutral_point_as_resting_on_a_convention() -> None:
    _, data = load_navigator_script().build()
    assert "tail-efficiency" not in data["conventions"]
    for slug in ("neutral-point", "static-margin", "cg-for-target-margin"):
        assert "tail-efficiency" not in data["conv"].get(slug, []), slug
