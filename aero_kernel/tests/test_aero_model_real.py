"""The model function cache never changes a value, and it saves the build (aero tier, #1336).

A problem solved through a function reused from the worker's cache gives exactly the numbers of
the same problem solved through a function built for it (ch. 8.4: the cache never changes a
value). Through a ``CachedKernel`` a second Opti call on the same geometry reuses the function its
first call built in the same worker.
"""

import logging
import time
from collections.abc import Callable
from typing import Any

import pytest
from aero_kernel import CachedKernel
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.runtime import SolverRuntime, WorkerOutcome
from aero_kernel.schema import AircraftInput, QuantityStatus
from aero_kernel.solvers import aero_model as aero_model_module
from aero_kernel.solvers.aero_model import install_model_cache, installed_model_cache, model_key
from aero_kernel.solvers.opti import (
    NEURALFOIL_MODEL_SIZE,
    OptiAdapter,
    RollRequest,
    StallRequest,
    best_glide_worker,
    min_sink_worker,
    stall_worker,
    steady_roll_worker,
)
from aero_kernel.tests.engine_builders import request
from aero_kernel.tests.reference_fleet import FleetMember, flap_values, reference_document
from aero_kernel.tests.solver_builders import K_E_D0
from aero_kernel.tests.test_roll_rate_fleet import V_APP
from aero_kernel.tests.test_stall_speed_fleet import sea_level_air

pytestmark = [pytest.mark.aero, pytest.mark.asyncio]

MEMBERS = (FleetMember.BRYAN, FleetMember.JAGUAR)
GRAVITY = 9.80665
AILERON_DEG = 20.0


@pytest.fixture
def worker_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install a model cache in this process as the runtime does in a worker; removed afterwards."""
    monkeypatch.setattr(aero_model_module._INSTALLED, "cache", None)  # pyright: ignore[reportPrivateUsage]  # the process-local holder under test
    install_model_cache(2)


def geometry(member: FleetMember) -> AirplaneGeometry:
    return AirplaneGeometry.model_validate(reference_document(member))


def key(airplane: AirplaneGeometry, roll_deg: float) -> str:
    return model_key(
        airplane,
        roll_deg=roll_deg,
        model_size=NEURALFOIL_MODEL_SIZE,
        tool_versions=OptiAdapter(SolverRuntime()).tool_versions(),
    )


def stall_request(member: FleetMember, cached: bool) -> StallRequest:
    airplane = geometry(member)
    return StallRequest(
        airplane=airplane,
        mass_kg=member.mass_kg,
        gravity=GRAVITY,
        n_load=1.0,
        air=sea_level_air(),
        k_e_d0=K_E_D0,
        model_key=key(airplane, 0.0) if cached else None,
    )


def roll_request(member: FleetMember, cached: bool) -> RollRequest:
    airplane = geometry(member)
    return RollRequest(
        airplane=airplane,
        mass_kg=member.mass_kg,
        gravity=GRAVITY,
        air=sea_level_air(),
        v_ms=V_APP[member],
        delta_deg=AILERON_DEG,
        model_key=key(airplane, AILERON_DEG) if cached else None,
    )


def notes(outcome: WorkerOutcome[Any]) -> str:
    return "; ".join(outcome.diagnostics.notes)


@pytest.mark.parametrize("member", MEMBERS)
@pytest.mark.usefixtures("worker_cache")
async def test_a_reused_function_gives_exactly_the_values_of_one_built_for_the_call(
    member: FleetMember,
) -> None:
    """Stall speed, best glide, minimum sink and roll: bit for bit equal, built vs reused."""
    stall_problems: list[Callable[[StallRequest], WorkerOutcome[Any]]] = [
        stall_worker,
        best_glide_worker,
        min_sink_worker,
    ]
    for worker in stall_problems:
        built = worker(stall_request(member, cached=False))
        assert "built" in notes(built)
        reused = worker(stall_request(member, cached=True))
        if worker is stall_worker:  # the first keyed call builds and keeps the function
            assert "built" in notes(reused)
            reused = worker(stall_request(member, cached=True))
        assert "reused" in notes(reused), worker
        assert reused.value == built.value, worker
    roll_built = steady_roll_worker(roll_request(member, cached=False))
    first_keyed = steady_roll_worker(roll_request(member, cached=True))
    roll_reused = steady_roll_worker(roll_request(member, cached=True))
    assert "built" in notes(first_keyed)
    assert "reused" in notes(roll_reused)
    assert roll_reused.value == roll_built.value == first_keyed.value
    cache = installed_model_cache()
    assert cache is not None
    assert len(cache.keys()) == 2  # the clean and the rolled airplane


async def test_a_second_opti_call_on_the_same_geometry_reuses_the_function_and_is_faster(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Two stall-speed calls on BRYAN through one ``CachedKernel``, the second at another mass (so
    the node cache does not serve it): the same worker reuses the model function."""
    member = FleetMember.BRYAN
    durations: list[float] = []

    def aircraft(mass_kg: float) -> AircraftInput:
        values = {"aircraft-mass": mass_kg, "altitude": 0.0, **flap_values(member)}
        return AircraftInput.model_validate(
            {"airplane": reference_document(member), "values": values}
        )

    with caplog.at_level(logging.DEBUG, logger="aero_kernel.runtime"):
        async with CachedKernel(max_entries=64, max_workers=1) as kernel:
            for mass in (member.mass_kg, member.mass_kg * 1.01):
                started = time.perf_counter()
                result = await kernel.compute(aircraft(mass), request("stall-speed"))
                durations.append(time.perf_counter() - started)
                (quantity,) = result.quantities
                assert quantity.status is QuantityStatus.OK
                assert not quantity.from_cache
    finished = [r.getMessage() for r in caplog.records if "fn=stall_worker" in r.getMessage()]
    assert len(finished) == 2
    assert "aero model built" in finished[0]
    assert "aero model reused" in finished[1]
    first, second = durations
    assert second < first - 2.0, durations  # the build alone is about 3 s
