"""Tests of the public ``compute`` (ARCHITECTURE ch. 6, 8.1, 8.4)."""

import asyncio
import logging
import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import aero_kernel
import pytest
from aero_kernel import api as api_module
from aero_kernel import build as build_module
from aero_kernel.api import compute
from aero_kernel.build import Build, shipped_build
from aero_kernel.cache import build_digest
from aero_kernel.canon import load as load_module
from aero_kernel.canon.load import load_canon_model
from aero_kernel.errors import ErrorCategory
from aero_kernel.registry import Registry
from aero_kernel.schema import QuantityStatus
from aero_kernel.tests.engine_builders import aircraft, request

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "flight_canon.json"


pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def fresh_memo() -> Iterator[None]:
    shipped_build.cache_clear()
    yield
    shipped_build.cache_clear()


def use_model(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    """Point the shipped build at a fixture model and an empty registry (no formulas yet)."""
    monkeypatch.setattr(load_module, "default_model_path", lambda: path)
    monkeypatch.setattr(build_module, "DEFAULT_REGISTRY", Registry())


async def test_compute_is_exported_and_no_build_is() -> None:
    assert aero_kernel.compute is compute
    assert "Build" not in aero_kernel.__all__
    assert not hasattr(aero_kernel, "Build")
    assert not hasattr(aero_kernel, "load_build")


async def test_compute_runs_on_the_shipped_build(monkeypatch: pytest.MonkeyPatch) -> None:
    use_model(monkeypatch, FIXTURE)
    result = await compute(aircraft({"air-density": 1.225}), request("stall-speed"))
    quantity = result.quantities[0]
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.error is not None
    assert quantity.error.category is ErrorCategory.NOT_IMPLEMENTED  # no formulas yet, Q1
    fixture = load_canon_model(FIXTURE)
    assert result.provenance.canon_model_hash == fixture.content_hash


async def test_no_packaged_model_makes_every_quantity_internal_and_never_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    use_model(monkeypatch, tmp_path / "absent.json")
    with caplog.at_level(logging.DEBUG, logger="aero_kernel"):
        result = await compute(aircraft(), request("stall-speed", "calc:nonsense"))
    assert result.input_errors == ()
    assert [q.slug for q in result.quantities] == ["stall-speed", "calc:nonsense"]
    for quantity in result.quantities:
        assert quantity.status is QuantityStatus.ERROR
        assert quantity.unit is None
        assert quantity.error is not None
        assert quantity.error.category is ErrorCategory.INTERNAL
        assert quantity.error.escalate is True
        assert quantity.error.quantity == quantity.slug
        assert str(tmp_path) not in f"{quantity.error.message} {quantity.error.hint}"
    assert result.provenance.canon_model_hash is None
    assert result.provenance.build_digest.startswith("sha256:")
    logged = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert len(logged) == 1
    assert logged[0].exc_info is not None
    assert isinstance(getattr(logged[0], "call_id", None), str)
    assert "python -m aero_kernel.importer" in logged[0].getMessage()
    assert "importer" not in str([q.error for q in result.quantities if q.error is not None])
    assert str(tmp_path) not in logged[0].getMessage()


async def test_the_failing_path_logs_one_info_line_with_a_call_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    use_model(monkeypatch, tmp_path / "absent.json")
    with caplog.at_level(logging.INFO, logger="aero_kernel"):
        await compute(aircraft({"air-density": 1.225}), request("stall-speed"))
    info = [r for r in caplog.records if r.levelno == logging.INFO]
    assert len(info) == 1
    assert isinstance(getattr(info[0], "call_id", None), str)


async def test_the_memo_loads_once_across_two_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    use_model(monkeypatch, FIXTURE)
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    original = build_module.load_build

    def counting(*args: Any, **kwargs: Any) -> Build:
        calls.append((args, kwargs))
        return original(*args, **kwargs)

    monkeypatch.setattr(build_module, "load_build", counting)
    await compute(aircraft({"air-density": 1.225}), request("stall-speed"))
    await compute(aircraft({"air-density": 1.225}), request("stall-speed"))
    assert calls == [((), {})]


async def test_a_failed_load_recovers_without_a_restart(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    use_model(monkeypatch, tmp_path / "absent.json")
    failed = await compute(aircraft({"air-density": 1.225}), request("stall-speed"))
    assert failed.quantities[0].error is not None
    assert failed.quantities[0].error.category is ErrorCategory.INTERNAL
    use_model(monkeypatch, FIXTURE)
    fixed = await compute(aircraft({"air-density": 1.225}), request("stall-speed"))
    assert fixed.quantities[0].error is not None
    assert fixed.quantities[0].error.category is ErrorCategory.NOT_IMPLEMENTED


async def test_a_failed_build_reports_the_exact_load_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    use_model(monkeypatch, tmp_path / "absent.json")
    result = await compute(aircraft(), request("stall-speed"))
    error = result.quantities[0].error
    assert error is not None
    assert (
        error.message
        == "The canon model could not be loaded: the file cannot be read (FileNotFoundError)."
    )
    assert error.hint == "Report it; attach input and provenance."
    assert (error.code, error.quantity, error.formula, error.application) == (
        "internal",
        "stall-speed",
        None,
        None,
    )
    assert error.retryable is False
    assert error.escalate is True


async def test_the_digest_of_a_failed_build_is_the_package_digest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    use_model(monkeypatch, tmp_path / "absent.json")
    result = await compute(aircraft(), request("stall-speed"))
    assert result.provenance.build_digest == build_digest()


async def test_two_failing_calls_log_two_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    use_model(monkeypatch, tmp_path / "absent.json")
    with caplog.at_level(logging.DEBUG, logger="aero_kernel"):
        await compute(aircraft(), request("stall-speed"))
        await compute(aircraft(), request("stall-speed"))
    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert len(errors) == 2
    assert errors[0].call_id != errors[1].call_id  # type: ignore[attr-defined]  # logging extra


async def test_the_failing_call_logs_its_request_in_the_info_line(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    use_model(monkeypatch, tmp_path / "absent.json")
    with caplog.at_level(logging.INFO, logger="aero_kernel"):
        await compute(aircraft(), request("stall-speed", "nonsense", long_runs=True))
    (info,) = [r for r in caplog.records if r.levelno == logging.INFO]
    assert info.getMessage().startswith(
        "compute: [stall-speed, nonsense] include_long_runs=True, 2 quantities (error=2), "
        "0 input errors, "
    )
    assert info.getMessage().endswith("; the shipped canon model is not loaded")


async def test_compute_hands_the_identical_objects_to_the_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_model(monkeypatch, FIXTURE)
    seen: list[tuple[object, object, object]] = []
    original = api_module.evaluate

    async def spy(build: Build, aircraft_: object, request_: object) -> object:
        seen.append((build, aircraft_, request_))
        return await original(build, aircraft_, request_)  # type: ignore[arg-type]  # pass-through spy

    monkeypatch.setattr(api_module, "evaluate", spy)
    the_aircraft, the_request = aircraft({"air-density": 1.225}), request("stall-speed")
    await compute(the_aircraft, the_request)
    ((build, got_aircraft, got_request),) = seen
    assert got_aircraft is the_aircraft
    assert got_request is the_request
    assert build is shipped_build()


async def test_the_formulas_package_is_not_imported_by_a_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_model(monkeypatch, FIXTURE)
    await compute(aircraft({"air-density": 1.225}), request("stall-speed"))
    assert "aero_kernel.formulas" not in sys.modules


async def test_the_first_compute_emits_exactly_one_info_record(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    use_model(monkeypatch, FIXTURE)
    with caplog.at_level(logging.DEBUG, logger="aero_kernel"):
        await compute(aircraft({"air-density": 1.225}), request("stall-speed"))
    infos = [r for r in caplog.records if r.levelno == logging.INFO]
    assert len(infos) == 1
    assert infos[0].name == "aero_kernel.engine"


async def test_a_failure_while_assembling_the_build_never_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_model(monkeypatch, FIXTURE)

    def broken(root: object = None) -> str:
        msg = "disk gone"
        raise OSError(msg)

    monkeypatch.setattr(build_module, "build_digest", broken)
    result = await compute(aircraft(), request("stall-speed"))
    error = result.quantities[0].error
    assert error is not None
    assert error.category is ErrorCategory.INTERNAL
    assert error.escalate is True
    assert "disk gone" not in error.message


async def test_the_failing_build_line_ends_with_the_timing_then_the_reason(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    use_model(monkeypatch, tmp_path / "absent.json")
    with caplog.at_level(logging.INFO, logger="aero_kernel"):
        await compute(aircraft(), request("stall-speed"))
    (info,) = [r for r in caplog.records if r.levelno == logging.INFO]
    found = re.fullmatch(
        r"compute: \[stall-speed\] include_long_runs=False, 1 quantities \(error=1\), "
        r"0 input errors, (\d+\.\d) ms; the shipped canon model is not loaded",
        info.getMessage(),
    )
    assert found is not None
    assert float(found.group(1)) < 60_000


@pytest.mark.parametrize(
    "failure", [RuntimeError("x"), ValueError("x"), KeyError("x")], ids=lambda e: type(e).__name__
)
async def test_every_exception_of_the_assembly_gives_internal_for_every_quantity(
    monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    use_model(monkeypatch, FIXTURE)

    def broken(*args: object, **kwargs: object) -> Any:
        raise failure

    monkeypatch.setattr(build_module, "build_digest", broken)
    result = await compute(aircraft(), request("stall-speed", "calc:nonsense"))
    assert [q.slug for q in result.quantities] == ["stall-speed", "calc:nonsense"]
    for quantity in result.quantities:
        assert quantity.error is not None
        assert quantity.error.category is ErrorCategory.INTERNAL
        assert quantity.error.escalate is True


async def test_cancellation_passes_through_compute(monkeypatch: pytest.MonkeyPatch) -> None:
    use_model(monkeypatch, FIXTURE)

    def cancelled(*args: object, **kwargs: object) -> Any:
        raise asyncio.CancelledError

    monkeypatch.setattr(build_module, "build_digest", cancelled)
    with pytest.raises(asyncio.CancelledError):
        await compute(aircraft(), request("stall-speed"))
