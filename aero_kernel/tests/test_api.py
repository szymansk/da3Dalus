"""Tests of the public ``compute`` (ARCHITECTURE ch. 6, 8.1, 8.4)."""

import logging
from collections.abc import Iterator
from pathlib import Path

import aero_kernel
import pytest
from aero_kernel import build as build_module
from aero_kernel.api import compute
from aero_kernel.build import Build, shipped_build
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
    assert result.provenance.canon_source_commit == fixture.source_commit


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
    assert result.provenance.canon_source_commit is None
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
    with caplog.at_level(logging.INFO, logger="aero_kernel.api"):
        await compute(aircraft({"air-density": 1.225}), request("stall-speed"))
    info = [r for r in caplog.records if r.levelno == logging.INFO]
    assert len(info) == 1
    assert isinstance(getattr(info[0], "call_id", None), str)


async def test_the_memo_loads_once_across_two_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    use_model(monkeypatch, FIXTURE)
    calls: list[int] = []
    original = build_module.load_build

    def counting() -> Build:
        calls.append(1)
        return original()

    monkeypatch.setattr(build_module, "load_build", counting)
    await compute(aircraft({"air-density": 1.225}), request("stall-speed"))
    await compute(aircraft({"air-density": 1.225}), request("stall-speed"))
    assert len(calls) == 1


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
