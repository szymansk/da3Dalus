"""Defaults and the inheritance of input warnings (ARCHITECTURE ch. 8.2, 8.11, 8.14; Q28, Q31)."""

import logging
from collections.abc import Mapping
from typing import Any

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
    two_deflected_wing,
)

pytestmark = pytest.mark.asyncio

DENSITY = DefaultUsed(
    slug="air-density", value=1.225, unit="kg/m^3", source="us standard atmosphere"
)
MARGIN = DefaultUsed(slug="margin-target", value=1.3, unit="1", source="test margin")


async def go(
    *slugs: str,
    values: Mapping[str, float] | None = None,
    long_runs: bool = False,
    overrides: Mapping[str, Impl] | None = None,
    geometry_mass_kg: float | None = None,
    wings: dict[str, Any] | None = None,
) -> ComputeResult:
    return await evaluate(
        make_build(registry_with(overrides)),
        aircraft(values, wings, geometry_mass_kg),
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
    assert line.getMessage() == "default used: air-density = 1.225 kg/m^3 (us standard atmosphere)"
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


async def test_a_call_with_two_defaults_has_two_default_lines_then_the_summary(
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


@pytest.mark.parametrize(
    ("slug", "drop", "row"),
    [
        ("density-when-q", (), "row 1: the condition is unmet"),
        ("density-after-roll-q", (), "row 2: a predecessor is not applicable"),
        ("density-q", ("density-user",), "row 3: no implementation"),
        ("density-pending-q", (), "row 3: a pending term"),
    ],
)
async def test_a_node_that_stops_at_rows_1_to_3_takes_no_default(
    slug: str, drop: tuple[str, ...], row: str, caplog: pytest.LogCaptureFixture
) -> None:
    registry = registry_with(drop=drop)
    with caplog.at_level(logging.INFO, logger="aero_kernel"):
        result = await evaluate(make_build(registry), aircraft(), request(slug))
    assert result.quantities[0].status is not QuantityStatus.OK, row
    assert result.provenance.defaults_used == (), row
    assert default_lines(caplog) == [], row


async def test_a_node_that_stops_at_a_missing_input_takes_no_default(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="aero_kernel"):
        result = await go("density-needs-t-q")
    assert result.quantities[0].error is not None
    assert result.quantities[0].error.code == "missing_input"
    assert result.provenance.defaults_used == ()
    assert default_lines(caplog) == []


async def test_a_node_that_stops_at_a_skipped_predecessor_takes_no_default(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="aero_kernel"):
        result = await go("density-after-long-q")
    assert result.quantities[0].reason is not None
    assert result.quantities[0].reason.code.value == "depends_on_skipped"
    assert result.provenance.defaults_used == ()
    assert default_lines(caplog) == []


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


# --- more pins (b, amendment 1) -----------------------------------------------------------------


async def test_a_target_default_bound_by_two_running_nodes_warns_and_logs_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="aero_kernel"):
        result = await go("margin-and-after-q")
    quantity = result.quantities[0]
    assert [w.code for w in quantity.warnings] == ["default_target_used"]
    assert len(default_lines(caplog)) == 1
    assert result.provenance.defaults_used == (MARGIN,)


async def test_the_info_line_of_a_target_default_has_its_exact_text_and_role(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="aero_kernel"):
        await go("margin-q")
    (line,) = default_lines(caplog)
    assert line.getMessage() == "default used: margin-target = 1.3 1 (test margin)"
    assert line.role == "target"  # type: ignore[attr-defined]  # logging extra


async def test_the_provenance_is_sorted_by_slug_not_by_when_or_by_source() -> None:
    """margin-target is taken a layer earlier, and its source sorts before density's."""
    result = await go("density-after-margin-q")
    assert result.provenance.defaults_used == (DENSITY, MARGIN)
    assert MARGIN.source < DENSITY.source


async def test_the_default_warning_comes_before_the_formulas_own_warnings() -> None:
    async def warn(x: Inputs, ctx: Context) -> Mapping[str, object]:
        ctx.warn("precondition_unchecked", "not checked")
        return {"r": 1.0}

    result = await go("margin-q", overrides={"margin-user": warn})
    assert [w.code for w in result.quantities[0].warnings] == [
        "default_target_used",
        "precondition_unchecked",
    ]


async def test_every_input_warning_is_inherited_in_validation_order() -> None:
    result = await go("mass-airplane-q", geometry_mass_kg=3.0, wings=two_deflected_wing())
    warnings = result.quantities[0].warnings
    assert [(w.code, w.origin) for w in warnings] == [
        ("conflicting_mass", "aircraft-mass"),
        ("geometry_deflection_ignored", "airplane"),
        ("geometry_deflection_ignored", "airplane"),
    ]
    assert [w.detail.get("device") for w in warnings[1:]] == [
        'airplane.wings["Main"].x_secs[0].trailing_edge_device',
        'airplane.wings["Main"].x_secs[1].trailing_edge_device',
    ]


async def test_a_not_applicable_and_a_skipped_result_carry_no_input_warning() -> None:
    result = await go("roll-q", "long-q", geometry_mass_kg=3.0)
    assert [q.status for q in result.quantities] == [
        QuantityStatus.NOT_APPLICABLE,
        QuantityStatus.SKIPPED,
    ]
    assert [q.warnings for q in result.quantities] == [(), ()]


async def test_node_warnings_follow_the_subtree_in_topological_order() -> None:
    async def weight(x: Inputs, ctx: Context) -> Mapping[str, object]:
        ctx.warn("precondition_unchecked", "from weight")
        return {"w": 1.0}

    async def double(x: Inputs, ctx: Context) -> Mapping[str, object]:
        ctx.warn("postcondition_unchecked", "from double")
        return {"d": 2.0}

    result = await go("double-weight", overrides={"weight": weight, "double": double})
    assert [(w.origin, w.message) for w in result.quantities[0].warnings] == [
        ("weight", "from weight"),
        ("double-weight", "from double"),
    ]


async def test_the_default_lines_of_one_node_follow_its_parameter_order(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="aero_kernel"):
        await go("both-q")
    assert [r.getMessage() for r in default_lines(caplog)] == [
        "default used: air-density = 1.225 kg/m^3 (us standard atmosphere)",
        "default used: margin-target = 1.3 1 (test margin)",
    ]
