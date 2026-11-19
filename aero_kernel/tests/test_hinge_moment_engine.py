"""hinge-moment through the engine on the shipped canon, with a stub AVL (ch. 8.3, 8.5, 8.13)."""

import math
from typing import cast

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.cache import DedupedCache, MemoryCache
from aero_kernel.engine import evaluate
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.graph import Subtree
from aero_kernel.schema import (
    AircraftInput,
    ComputeRequest,
    ComputeResult,
    QuantityResult,
    QuantityStatus,
    ReasonCode,
    WarningSeverity,
)
from aero_kernel.tests.asb_fakes import stand_in_main_wing_properties
from aero_kernel.tests.formula_builders import StubAtmosphere, near, solvers_with
from aero_kernel.tests.hinge_builders import conventional, device, v_tail_plane
from aero_kernel.tests.np_builders import StubAvl

pytestmark = pytest.mark.asyncio

RHO, MASS, GRAVITY = 1.225, 0.5, 9.80665
GIVEN = {
    "aircraft-mass": MASS,
    "altitude": 0.0,
    "flight-speed": 20.0,
    "aileron-deflection": 10.0,
    "elevator-deflection-up": -10.0,
    "elevator-deflection-down": 8.0,
    "rudder-deflection": 5.0,
}


async def run(
    airplane: AirplaneGeometry | None = None,
    avl: StubAvl | None = None,
    values: dict[str, float] | None = None,
) -> ComputeResult:
    given = {**GIVEN, **(values or {})}
    aircraft = AircraftInput.model_validate(
        {"airplane": airplane or conventional(), "values": given}
    )
    solvers = solvers_with(atmosphere=StubAtmosphere({0.0: RHO}), avl=avl or StubAvl())
    return await evaluate(
        shipped_build(),
        aircraft,
        ComputeRequest(quantities=("hinge-moment",)),
        solvers=solvers,
    )


def assert_surfaces(
    actual: dict[str, dict[str, float]] | None, expected: dict[str, dict[str, float]]
) -> None:
    """Compare per-surface values entry by entry to a tolerance."""
    assert actual is not None
    assert actual.keys() == expected.keys()
    for key, by_application in expected.items():
        assert actual[key].keys() == by_application.keys(), key
        for application, value in by_application.items():
            assert near(actual[key][application], value), (key, application)


def only(result: ComputeResult) -> QuantityResult:
    (quantity,) = result.quantities
    return quantity


async def test_every_applicable_role_contributes_its_entries_to_one_quantity() -> None:
    quantity = only(await run())
    assert quantity.status is QuantityStatus.OK
    assert quantity.unit == "N*m"
    assert quantity.tool == "AVL"
    assert quantity.value is None
    assert quantity.surfaces is not None
    # the stub answers 1e-3 N*m per degree, signed by the side: aileron right -, left +
    assert_surfaces(
        quantity.surfaces,
        {
            "Main wing.aileron_right": {"aileron": -0.01},
            "Main wing.aileron_left": {"aileron": 0.01},
            "Tail.elevator_right": {"elevator_up": -0.01, "elevator_down": 0.008},
            "Tail.elevator_left": {"elevator_up": -0.01, "elevator_down": 0.008},
            "Fin.rudder": {"rudder": 0.005},
        },
    )


async def test_the_application_field_names_the_applications_that_produced_the_value() -> None:
    quantity = only(await run())
    assert quantity.application == "aileron, elevator_up, elevator_down, rudder"


async def test_each_role_is_one_adapter_call_at_the_lift_of_the_operating_point() -> None:
    avl = StubAvl()
    plane = conventional()
    await run(plane, avl, {"load-factor": 2.0})
    calls = {(c["role"], c["delta"]): c for c in avl.hinge_calls}
    assert set(calls) == {
        ("aileron", 10.0),
        ("elevator", -10.0),
        ("elevator", 8.0),
        ("rudder", 5.0),
    }
    s_ref = stand_in_main_wing_properties(plane).s_ref
    expected = 2.0 * MASS * GRAVITY / (0.5 * RHO * 20.0**2 * s_ref)
    assert all(math.isclose(c["cl"], expected, rel_tol=1e-12) for c in avl.hinge_calls)
    assert all(c["speed"] == 20.0 for c in avl.hinge_calls)


async def test_the_airplane_is_handed_to_avl_with_its_devices_at_rest() -> None:
    avl = StubAvl()
    moved = conventional(main={1: device("aileron", "aileron", 0.75, deflection_deg=15.0)})
    await run(moved, avl)
    handed = [cast("AirplaneGeometry", call["airplane"]) for call in avl.hinge_calls]
    assert handed
    for airplane in handed:
        for wing in (airplane.wings or {}).values():
            for section in wing.x_secs:
                device_ = section.trailing_edge_device
                assert device_ is None or not device_.deflection_deg


async def test_a_dual_role_surface_has_an_entry_per_role() -> None:
    plane = v_tail_plane()
    quantity = only(await run(plane, values={"elevator-deflection-up": -4.0}))
    assert_surfaces(
        quantity.surfaces,
        {
            "V-tail.ruddervator_right": {
                "elevator_up": -0.004,
                "elevator_down": 0.008,
                "rudder": 0.005,
            },
            "V-tail.ruddervator_left": {
                "elevator_up": -0.004,
                "elevator_down": 0.008,
                "rudder": -0.005,
            },
        },
    )


async def test_flap_applications_apply_when_a_device_acts_as_flap() -> None:
    plane = conventional(
        main={0: device("flap", "flap", 0.7), 1: device("aileron", "aileron", 0.75)}
    )
    quantity = await run(
        plane, values={"flap-deflection-takeoff": 15.0, "flap-deflection-landing": 30.0}
    )
    surfaces = only(quantity).surfaces
    assert_surfaces(
        {k: v for k, v in (surfaces or {}).items() if "flap" in k},
        {
            "Main wing.flap_right": {"flap_takeoff": 0.015, "flap_landing": 0.03},
            "Main wing.flap_left": {"flap_takeoff": 0.015, "flap_landing": 0.03},
        },
    )


async def test_no_device_acting_in_any_role_makes_the_quantity_not_applicable() -> None:
    quantity = only(await run(conventional(main={}, tail={}, fin={})))
    assert quantity.status is QuantityStatus.NOT_APPLICABLE
    assert quantity.reason is not None
    assert quantity.reason.code is ReasonCode.CONDITION_NOT_MET
    assert quantity.surfaces is None


async def test_the_declared_limits_travel_with_the_value() -> None:
    quantity = only(await run(avl=StubAvl()))
    declared = {w.code: w.severity for w in quantity.warnings}
    assert declared["hinge_moment_inviscid_estimate"] is WarningSeverity.NOTICE
    assert declared["hinge_moment_pitch_untrimmed"] is WarningSeverity.NOTICE


async def test_an_applicable_role_without_its_deflection_is_an_error_not_a_partial_value() -> None:
    aircraft = AircraftInput.model_validate(
        {
            "airplane": conventional(),
            "values": {k: v for k, v in GIVEN.items() if k != "rudder-deflection"},
        }
    )
    result = await evaluate(
        shipped_build(),
        aircraft,
        ComputeRequest(quantities=("hinge-moment",)),
        solvers=solvers_with(atmosphere=StubAtmosphere({0.0: RHO}), avl=StubAvl()),
    )
    quantity = only(result)
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.error is not None
    assert quantity.error.category is ErrorCategory.INVALID_INPUT
    assert quantity.surfaces is None


async def test_a_failing_role_makes_the_quantity_an_error() -> None:
    avl = StubAvl()
    avl.hinge_failure = FormulaError(
        ErrorCategory.UNSUPPORTED_CONFIGURATION, "avl_array_limit", "too fine", "coarser"
    )
    quantity = only(await run(avl=avl))
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.error is not None
    assert quantity.error.code == "avl_array_limit"
    assert quantity.error.quantity == "hinge-moment"


async def test_an_adapter_answer_that_is_not_a_value_per_surface_is_an_internal_error() -> None:
    avl = StubAvl()
    avl.hinge_answer = {}
    quantity = only(await run(avl=avl))
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.error is not None
    assert quantity.error.category is ErrorCategory.INTERNAL


async def test_a_device_on_the_last_rib_is_refused_by_the_validation_before_any_run() -> None:
    """has_rudder looks at every rib, but a device on the last rib is an input error (it spans no
    segment), so the mesh never meets a role the conditions allow but no segment carries."""
    result = await run(conventional(fin={1: device("rudder", "rudder", 0.6)}))
    assert result.quantities == ()
    assert [e.code for e in result.input_errors] == ["segment_on_last_section"]


async def test_the_node_cache_serves_the_second_call_with_the_same_surfaces() -> None:
    avl = StubAvl()
    cache = DedupedCache(MemoryCache(max_entries=64))
    aircraft = AircraftInput.model_validate({"airplane": conventional(), "values": GIVEN})
    request = ComputeRequest(quantities=("hinge-moment",))
    solvers = solvers_with(atmosphere=StubAtmosphere({0.0: RHO}), avl=avl)
    first = only(await evaluate(shipped_build(), aircraft, request, solvers=solvers, cache=cache))
    second = only(await evaluate(shipped_build(), aircraft, request, solvers=solvers, cache=cache))
    assert first.from_cache is False
    assert second.from_cache is True
    assert second.surfaces == first.surfaces
    assert len(avl.hinge_calls) == 4


async def test_the_shipped_hinge_moment_has_no_method_worlds_upstream() -> None:
    """The union assumes plain-value inputs; this pins the assumption on the shipped canon."""
    subtree = shipped_build().graph.subtree(["hinge-moment"])
    assert subtree.world_assignments("hinge-moment") == ({},)


async def test_a_per_surface_quantity_with_worlds_upstream_is_refused_not_asserted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If an uncertain formula ever lies upstream, the quantity says so instead of failing an assert."""

    def with_worlds(_self: Subtree, _slug: str) -> tuple[dict[str, str], ...]:
        return ({"neutral-point": "avl"},)

    monkeypatch.setattr(Subtree, "world_assignments", with_worlds)
    quantity = only(await run())
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.error is not None
    assert quantity.error.code == "non_scalar_result"
