"""Expert View backend (gh-1282, ADR 0030): the canon service with the kernel boundary stubbed."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

import pytest
from aero_kernel.schema import (
    AircraftInput,
    ComputeRequest,
    ComputeResult,
    KernelError,
    Provenance,
    QuantityResult,
    QuantityStatus,
    Reason,
    ReasonCode,
    TimeBounds,
    Timing,
)

from app.core.exceptions import NotFoundError, ValidationError
from app.schemas.canon import CanonAircraftRef, CanonComputeRequest
from app.services import canon_service
from aero_kernel import CachedKernel

PROVENANCE = Provenance(build_digest="test")


def ok(slug: str, value: float) -> QuantityResult:
    return QuantityResult(
        slug=slug, unit="m/s", status=QuantityStatus.OK, value=value, tool="APP", application="a"
    )


def skipped_long_run(slug: str) -> QuantityResult:
    return QuantityResult(
        slug=slug,
        status=QuantityStatus.SKIPPED,
        reason=Reason(code=ReasonCode.LONG_RUN_NOT_INCLUDED, message="needs minutes"),
    )


class StubKernel:
    """Replaces ``aero_kernel.compute``: records the call and answers with a prepared result."""

    def __init__(self, *quantities: QuantityResult) -> None:
        self.quantities = quantities
        self.calls: list[tuple[AircraftInput, ComputeRequest]] = []

    async def __call__(self, aircraft: AircraftInput, request: ComputeRequest) -> ComputeResult:
        self.calls.append((aircraft, request))
        logging.getLogger("aero_kernel.engine").debug(
            "node started", extra={"formula": "stall-speed", "quantity": "stall-speed"}
        )
        return ComputeResult(quantities=self.quantities, provenance=PROVENANCE)


class Facade:
    """Replaces the shared ``CachedKernel``: its ``compute`` is the given stub."""

    def __init__(
        self, stub: Callable[[AircraftInput, ComputeRequest], Awaitable[ComputeResult]]
    ) -> None:
        self.compute = stub


def use_kernel(
    monkeypatch: pytest.MonkeyPatch,
    stub: Callable[[AircraftInput, ComputeRequest], Awaitable[ComputeResult]],
) -> None:
    """Answer the cached path (the default) with ``stub``; the stateless one must not be used."""

    async def not_fresh(aircraft: AircraftInput, request: ComputeRequest) -> ComputeResult:
        raise AssertionError("the stateless compute ran although fresh was not requested")

    monkeypatch.setattr(canon_service, "KERNEL", Facade(stub))
    monkeypatch.setattr(canon_service, "compute", not_fresh)


def request_of(
    *quantities: str,
    fleet: str = "bryan",
    values: dict[str, float] | None = None,
    include_long_runs: bool = False,
    fresh: bool = False,
) -> CanonComputeRequest:
    return CanonComputeRequest(
        aircraft=CanonAircraftRef(fleet=fleet),
        quantities=list(quantities),
        values=values or {},
        include_long_runs=include_long_runs,
        fresh=fresh,
    )


@pytest.fixture
def kernel(monkeypatch: pytest.MonkeyPatch) -> StubKernel:
    stub = StubKernel(ok("stall-speed", 7.5))
    use_kernel(monkeypatch, stub)
    return stub


def test_the_fleet_lists_every_reference_aircraft_with_its_values() -> None:
    fleet = {entry.id: entry for entry in canon_service.list_fleet()}
    assert set(fleet) == {"bryan", "jaguar", "rv-7", "chekker", "wiesel", "belemnitos"}
    assert fleet["bryan"].name == "BRYAN"
    assert fleet["bryan"].mass_kg == pytest.approx(0.151)
    assert fleet["bryan"].flap_deflections == {}
    assert fleet["rv-7"].name == "RV-7"
    assert fleet["rv-7"].flap_deflections == {
        "flap-deflection-takeoff": 15.0,
        "flap-deflection-landing": 30.0,
    }


@pytest.mark.asyncio
async def test_the_kernel_gets_the_fleet_aircraft_with_the_callers_values(
    kernel: StubKernel,
) -> None:
    await canon_service.compute_canon(
        request_of(
            "stall-speed", fleet="rv-7", values={"aircraft-mass": 0.7}, include_long_runs=True
        )
    )
    ((aircraft, request),) = kernel.calls
    assert aircraft.values["aircraft-mass"] == pytest.approx(0.7)
    assert aircraft.values["flap-deflection-landing"] == pytest.approx(30.0)
    assert request.quantities == ("stall-speed",)
    assert request.include_long_runs is True


@pytest.mark.asyncio
async def test_the_response_carries_the_results_and_the_provenance(kernel: StubKernel) -> None:
    response = await canon_service.compute_canon(request_of("stall-speed"))
    assert [q.slug for q in response.quantities] == ["stall-speed"]
    assert response.quantities[0].value == pytest.approx(7.5)
    assert response.provenance.build_digest == "test"
    assert response.input_errors == []


@pytest.mark.asyncio
async def test_the_measured_run_time_of_each_quantity_is_passed_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timing = Timing.of(
        own=TimeBounds(lower=0.5, upper=1.5), before=TimeBounds(lower=2.0, upper=3.0)
    )
    timed = ok("stall-speed", 7.5).model_copy(update={"timing": timing})
    use_kernel(monkeypatch, StubKernel(timed))
    response = await canon_service.compute_canon(request_of("stall-speed"))
    assert response.quantities[0].timing == timing


@pytest.mark.asyncio
async def test_an_unknown_aircraft_is_not_found(kernel: StubKernel) -> None:
    request = request_of("stall-speed", fleet="nonexistent")
    with pytest.raises(NotFoundError):
        await canon_service.compute_canon(request)
    assert kernel.calls == []


@pytest.mark.asyncio
async def test_a_quantity_requested_twice_is_a_validation_error(kernel: StubKernel) -> None:
    request = request_of("stall-speed", "stall-speed")
    with pytest.raises(ValidationError):
        await canon_service.compute_canon(request)


@pytest.mark.asyncio
async def test_input_errors_of_the_kernel_are_passed_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = KernelError(
        code="not_an_input", category="invalid_input", message="m", hint="h", input_path="values"
    )

    async def refuse(aircraft: AircraftInput, request: ComputeRequest) -> ComputeResult:
        return ComputeResult(input_errors=(error,), provenance=PROVENANCE)

    use_kernel(monkeypatch, refuse)
    response = await canon_service.compute_canon(request_of("stall-speed"))
    assert [e.code for e in response.input_errors] == ["not_an_input"]
    assert response.quantities == []


@pytest.mark.asyncio
async def test_a_skipped_long_run_asks_for_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    use_kernel(monkeypatch, StubKernel(skipped_long_run("neutral-point"), ok("a", 1.0)))
    response = await canon_service.compute_canon(request_of("neutral-point", "a"))
    assert response.needs_confirmation == ["neutral-point"]


@pytest.mark.asyncio
async def test_the_kernel_logs_of_the_request_are_returned(kernel: StubKernel) -> None:
    response = await canon_service.compute_canon(request_of("stall-speed"))
    started = [r for r in response.logs if r.message == "node started"]
    assert len(started) == 1
    assert started[0].level == "DEBUG"
    assert started[0].logger == "aero_kernel.engine"
    assert started[0].formula == "stall-speed"
    assert started[0].quantity == "stall-speed"
    assert started[0].time.endswith("Z")


@pytest.mark.asyncio
async def test_logs_of_other_loggers_are_not_returned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def noisy(aircraft: AircraftInput, request: ComputeRequest) -> ComputeResult:
        logging.getLogger("app.something").warning("not the kernel")
        logging.getLogger("aero_kernel.engine").warning("the kernel")
        return ComputeResult(quantities=(ok("stall-speed", 1.0),), provenance=PROVENANCE)

    use_kernel(monkeypatch, noisy)
    response = await canon_service.compute_canon(request_of("stall-speed"))
    assert [r.message for r in response.logs] == ["the kernel"]


@pytest.mark.asyncio
async def test_file_paths_are_not_part_of_a_log_message(monkeypatch: pytest.MonkeyPatch) -> None:
    async def leaky(aircraft: AircraftInput, request: ComputeRequest) -> ComputeResult:
        logging.getLogger("aero_kernel.solvers.process").warning(
            "temp directory not removed: %s, speed 7.5 m/s",
            "/private/var/folders/xy/T/avl_abc",
        )
        return ComputeResult(quantities=(ok("stall-speed", 1.0),), provenance=PROVENANCE)

    use_kernel(monkeypatch, leaky)
    (record,) = (await canon_service.compute_canon(request_of("stall-speed"))).logs
    assert "/private" not in record.message
    assert record.message == "temp directory not removed: <path>, speed 7.5 m/s"


@pytest.mark.asyncio
async def test_concurrent_requests_keep_their_own_logs(monkeypatch: pytest.MonkeyPatch) -> None:
    async def answer(aircraft: AircraftInput, request: ComputeRequest) -> ComputeResult:
        slug = request.quantities[0]
        logging.getLogger("aero_kernel.engine").warning("start %s", slug)
        await asyncio.sleep(0.05)
        logging.getLogger("aero_kernel.engine").warning("end %s", slug)
        return ComputeResult(quantities=(ok(slug, 1.0),), provenance=PROVENANCE)

    use_kernel(monkeypatch, answer)
    first, second = await asyncio.gather(
        canon_service.compute_canon(request_of("a")),
        canon_service.compute_canon(request_of("b")),
    )
    assert [r.message for r in first.logs] == ["start a", "end a"]
    assert [r.message for r in second.logs] == ["start b", "end b"]


@pytest.mark.asyncio
async def test_the_kernel_logger_level_is_restored(kernel: StubKernel) -> None:
    kernel_logger = logging.getLogger("aero_kernel")
    before = kernel_logger.level
    kernel_logger.setLevel(logging.WARNING)
    try:
        response = await canon_service.compute_canon(request_of("stall-speed"))
        assert any(r.message == "node started" for r in response.logs)  # DEBUG was captured
        assert kernel_logger.level == logging.WARNING
    finally:
        kernel_logger.setLevel(before)


@pytest.mark.asyncio
async def test_verdicts_cover_the_requested_quantities_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_kernel(monkeypatch, StubKernel(ok("horizontal-tail-volume", 0.5)))
    response = await canon_service.compute_canon(request_of("horizontal-tail-volume"))
    assert response.verdicts
    assert {v.quantity for v in response.verdicts} == {"horizontal-tail-volume"}
    assert response.verdicts[0].value == pytest.approx(0.5)
    assert response.verdicts[0].text


@pytest.mark.asyncio
async def test_a_fresh_request_recomputes_with_the_stateless_compute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stateless, cached = StubKernel(ok("stall-speed", 7.5)), StubKernel(ok("stall-speed", 1.0))
    monkeypatch.setattr(canon_service, "KERNEL", Facade(cached))
    monkeypatch.setattr(canon_service, "compute", stateless)
    response = await canon_service.compute_canon(request_of("stall-speed", fresh=True))
    assert (len(stateless.calls), len(cached.calls)) == (1, 0)
    assert response.quantities[0].value == pytest.approx(7.5)


@pytest.mark.asyncio
async def test_a_request_uses_the_shared_cached_kernel_by_default(kernel: StubKernel) -> None:
    await canon_service.compute_canon(request_of("stall-speed"))
    await canon_service.compute_canon(request_of("stall-speed"))
    assert len(kernel.calls) == 2  # both through the one facade


def test_the_shared_kernel_is_one_cached_kernel_of_the_named_size() -> None:
    assert isinstance(canon_service.KERNEL, CachedKernel)
    assert canon_service.KERNEL_CACHE_ENTRIES == 4096


@pytest.mark.asyncio
async def test_the_shared_kernel_runs_on_one_loop_that_is_not_the_callers() -> None:
    loops: list[asyncio.AbstractEventLoop] = []

    async def where() -> ComputeResult:
        loops.append(asyncio.get_running_loop())
        return ComputeResult(provenance=PROVENANCE)

    await canon_service._KERNEL_LOOP.run(where())
    await canon_service._KERNEL_LOOP.run(where())
    assert loops[0] is loops[1]
    assert loops[0] is not asyncio.get_running_loop()


@pytest.mark.asyncio
async def test_a_failure_on_the_kernel_loop_reaches_the_caller() -> None:
    async def broken() -> ComputeResult:
        raise LookupError("kernel defect")

    running = canon_service._KERNEL_LOOP.run(broken())
    with pytest.raises(LookupError, match="kernel defect"):
        await running


@pytest.mark.asyncio
async def test_a_caller_that_leaves_does_not_break_the_kernel_loop() -> None:

    async def slow() -> ComputeResult:
        await asyncio.sleep(0.05)
        return ComputeResult(provenance=PROVENANCE)

    waiting = asyncio.create_task(canon_service._KERNEL_LOOP.run(slow()))
    await asyncio.sleep(0)
    waiting.cancel()
    await asyncio.gather(waiting, return_exceptions=True)
    await asyncio.sleep(0.1)  # the kernel task finishes after its caller left
    assert (await canon_service._KERNEL_LOOP.run(slow())).quantities == ()
