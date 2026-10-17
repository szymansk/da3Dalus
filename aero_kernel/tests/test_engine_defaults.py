"""Defaults and the inheritance of input warnings (ARCHITECTURE ch. 8.2, 8.11, 8.14; Q28, Q31)."""

import logging
from collections.abc import Mapping

import pytest
from aero_kernel.context import Context, Inputs
from aero_kernel.engine import evaluate
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.schema import ComputeResult, DefaultUsed, QuantityStatus, WarningSeverity
from aero_kernel.tests.engine_builders import (
    Impl,
    aileron_wing,
    aircraft,
    deflected_wing,
    make_build,
    registry_with,
    request,
)

pytestmark = pytest.mark.asyncio

DENSITY = DefaultUsed(slug="air-density", value=1.225, unit="kg/m^3", source="ISA sea level")
MARGIN = DefaultUsed(slug="margin-target", value=1.3, unit="1", source="test margin")


async def go(
    *slugs: str,
    values: Mapping[str, float] | None = None,
    long_runs: bool = False,
    overrides: Mapping[str, Impl] | None = None,
    geometry_mass_kg: float | None = None,
    wings: dict[str, object] | None = None,
) -> ComputeResult:
    return await evaluate(
        make_build(registry_with(overrides)),
        aircraft(values, wings, geometry_mass_kg),  # type: ignore[arg-type]  # test wings
        request(*slugs, long_runs=long_runs),
    )


def default_lines(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.getMessage().startswith("default used")]


# --- an input default (a physical constant) ----------------------------------------------------


async def test_an_input_default_is_taken_declared_in_provenance_and_the_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="aero_kernel"):
        result = await go("density-q")
    quantity = result.quantities[0]
    assert (quantity.status, quantity.warnings) == (QuantityStatus.OK, ())
    assert result.provenance.defaults_used == (DENSITY,)
    (line,) = default_lines(caplog)
    assert line.levelno == logging.INFO
    assert line.getMessage() == "default used: air-density = 1.225 kg/m^3 (ISA sea level)"
    assert (line.quantity, line.role) == ("air-density", "input")  # type: ignore[attr-defined]  # logging extra
    assert isinstance(getattr(line, "call_id", None), str)


async def test_the_default_value_reaches_the_formula() -> None:
    seen: list[object] = []

    async def spy(x: Inputs, ctx: Context) -> Mapping[str, object]:
        seen.append(x["rho"])
        return {"r": 1.0}

    await go("density-q", overrides={"density-user": spy})
    assert seen == [1.225]


async def test_a_supplied_value_wins_and_no_default_is_taken(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="aero_kernel"):
        result = await go("density-q", values={"air-density": 1.0})
    assert result.provenance.defaults_used == ()
    assert default_lines(caplog) == []


async def test_a_call_with_one_default_has_the_default_line_and_the_summary(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="aero_kernel"):
        await go("density-q", "margin-q")
    infos = [r.getMessage() for r in caplog.records if r.levelno == logging.INFO]
    assert len(infos) == 3
    assert infos[0].startswith("default used: ")
    assert infos[1].startswith("default used: ")
    assert infos[2].startswith("compute: ")


async def test_a_call_without_defaults_keeps_exactly_one_info_line(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="aero_kernel"):
        await go("weight")
    assert len([r for r in caplog.records if r.levelno == logging.INFO]) == 1


async def test_one_default_read_by_two_running_nodes_is_taken_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="aero_kernel"):
        result = await go("density-q", "density-again-q")
    assert [q.status for q in result.quantities] == [QuantityStatus.OK] * 2
    assert len(default_lines(caplog)) == 1
    assert result.provenance.defaults_used == (DENSITY,)


async def test_the_provenance_is_sorted_by_display_slug_whatever_the_request_order() -> None:
    forward = await go("both-q")
    reverse = await go("margin-q", "density-q")
    assert forward.provenance.defaults_used == (DENSITY, MARGIN)
    assert reverse.provenance.defaults_used == (DENSITY, MARGIN)


async def test_an_absent_optional_input_with_a_default_takes_the_default() -> None:
    seen: list[object] = []

    async def spy(x: Inputs, ctx: Context) -> Mapping[str, object]:
        seen.append(x["rho"])
        return {"r": 1.0}

    result = await go("optional-density-q", overrides={"optional-density": spy})
    assert seen == [1.225]
    assert result.provenance.defaults_used == (DENSITY,)


async def test_a_value_without_a_default_is_still_missing() -> None:
    result = await go("weight", values={"gravity": 9.81}, geometry_mass_kg=None)
    assert result.quantities[0].status is QuantityStatus.OK
    nothing = await evaluate(
        make_build(),
        aircraft().model_copy(update={"values": {}}),
        request("weight"),
    )
    assert nothing.quantities[0].error is not None
    assert nothing.quantities[0].error.code == "missing_input"
    assert nothing.provenance.defaults_used == ()


# --- when a default counts as taken -------------------------------------------------------------


async def test_a_default_read_by_a_skipped_long_run_is_not_taken(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="aero_kernel"):
        result = await go("long-density-q")
    assert result.quantities[0].status is QuantityStatus.SKIPPED
    assert result.provenance.defaults_used == ()
    assert default_lines(caplog) == []
    included = await go("long-density-q", long_runs=True)
    assert included.provenance.defaults_used == (DENSITY,)


async def test_a_default_read_only_by_a_node_that_fails_upstream_is_not_taken(
    caplog: pytest.LogCaptureFixture,
) -> None:
    error = FormulaError(ErrorCategory.NOT_CONVERGED, "not_converged", "No solution.", "Retry.")

    async def failing(x: Inputs, ctx: Context) -> Mapping[str, object]:
        raise error

    with caplog.at_level(logging.INFO, logger="aero_kernel"):
        result = await go("fail-density-q", overrides={"weight": failing})
    assert result.quantities[0].error is not None
    assert result.quantities[0].error.category is ErrorCategory.UPSTREAM_FAILED
    assert result.provenance.defaults_used == ()
    assert default_lines(caplog) == []


async def test_a_default_read_by_a_not_applicable_node_is_not_taken() -> None:
    result = await go("tail-q")  # not implemented: row 3, never calls anything
    assert result.provenance.defaults_used == ()


async def test_a_default_is_taken_when_the_formula_is_called_even_if_it_then_fails() -> None:
    error = FormulaError(ErrorCategory.NOT_CONVERGED, "not_converged", "No solution.", "Retry.")

    async def failing(x: Inputs, ctx: Context) -> Mapping[str, object]:
        raise error

    result = await go("density-q", overrides={"density-user": failing})
    assert result.quantities[0].status is QuantityStatus.ERROR
    assert result.provenance.defaults_used == (DENSITY,)


# --- a target default is a substitution and says so --------------------------------------------


async def test_a_target_default_warns_and_the_warning_is_inherited() -> None:
    result = await go("margin-q", "after-margin-q", "independent-q")
    margin, after, independent = result.quantities
    for quantity in (margin, after):
        (warning,) = quantity.warnings
        assert warning.severity is WarningSeverity.PRACTICE
        assert warning.code == "default_target_used"
        assert warning.origin == "margin-target"
        assert warning.message == (
            "`margin-target` was not set; the canon default 1.3 1 is used (test margin)."
        )
        assert warning.detail == {"value": 1.3, "unit": "1", "source": "test margin"}
    assert independent.warnings == ()
    assert result.provenance.defaults_used == (MARGIN,)


async def test_an_input_default_gives_no_warning_and_a_supplied_target_neither() -> None:
    result = await go("density-q", "margin-q", values={"margin-target": 2.0})
    assert [q.warnings for q in result.quantities] == [(), ()]


# --- warning inheritance (Q28) ------------------------------------------------------------------


async def test_q28_conflicting_mass_is_on_mass_dependent_quantities_only() -> None:
    result = await go(
        "weight", "double-weight", "independent-q", "gravity-only-q", geometry_mass_kg=3.0
    )
    weight, double, independent, gravity_only = result.quantities
    for quantity in (weight, double, independent):
        (warning,) = quantity.warnings
        assert (warning.code, warning.origin) == ("conflicting_mass", "aircraft-mass")
        assert warning.severity is WarningSeverity.PRACTICE
        assert warning.detail == {"aircraft_mass_kg": 2.0, "geometry_total_mass_kg": 3.0}
    assert gravity_only.warnings == ()


async def test_no_conflicting_mass_warning_without_a_conflict() -> None:
    result = await go("weight", geometry_mass_kg=2.0)
    assert result.quantities[0].warnings == ()


async def test_geometry_deflection_ignored_is_on_quantities_reading_the_airplane_only() -> None:
    result = await go("span-q", "cfg-span-q", "weight", wings=deflected_wing())
    span, cfg_span, weight = result.quantities
    for quantity in (span, cfg_span):
        (warning,) = quantity.warnings
        assert (warning.code, warning.origin) == ("geometry_deflection_ignored", "airplane")
        assert warning.detail == {
            "device": 'airplane.wings["Main"].x_secs[0].trailing_edge_device',
            "deflection_deg": 5.0,
        }
    assert weight.warnings == ()


async def test_node_warnings_and_input_warnings_collect_without_repeats() -> None:
    async def warn(x: Inputs, ctx: Context) -> Mapping[str, object]:
        ctx.warn("precondition_unchecked", "not checked")
        return {"w": 1.0}

    result = await go(
        "double-weight",
        overrides={"weight": warn},
        geometry_mass_kg=3.0,
        wings=aileron_wing(),
    )
    assert [w.code for w in result.quantities[0].warnings] == [
        "precondition_unchecked",
        "conflicting_mass",
    ]


async def test_a_failed_quantity_carries_no_input_warning() -> None:
    error = FormulaError(ErrorCategory.NOT_CONVERGED, "not_converged", "No solution.", "Retry.")

    async def failing(x: Inputs, ctx: Context) -> Mapping[str, object]:
        raise error

    result = await go("weight", overrides={"weight": failing}, geometry_mass_kg=3.0)
    assert result.quantities[0].status is QuantityStatus.ERROR
    assert result.quantities[0].warnings == ()
