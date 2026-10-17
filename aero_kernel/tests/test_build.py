"""Tests of the ``Build`` and its loaders (ARCHITECTURE ch. 8.4)."""

import logging
import subprocess
import sys
from pathlib import Path

import pytest
from aero_kernel import build as build_module
from aero_kernel.build import Build, load_build, shipped_build
from aero_kernel.canon.load import CanonLoadError
from aero_kernel.canon.model import CanonModel
from aero_kernel.errors import ErrorCategory
from aero_kernel.graph import CanonGraph, GraphModelError
from aero_kernel.registry import Registry

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "flight_canon.json"


@pytest.fixture(autouse=True)
def fresh_memo() -> None:
    shipped_build.cache_clear()


def test_a_build_holds_model_graph_digest_registry_and_report() -> None:
    registry = Registry()
    build = load_build(FIXTURE, registry)
    assert isinstance(build, Build)
    assert isinstance(build.model, CanonModel)
    assert isinstance(build.graph, CanonGraph)
    assert build.registry is registry
    assert build.digest.startswith("sha256:")
    assert build.report.ok
    assert "flight_canon" not in build.digest


def test_the_build_is_frozen() -> None:
    build = load_build(FIXTURE, Registry())
    with pytest.raises(AttributeError):
        build.digest = "x"  # type: ignore[misc]  # proves the dataclass is frozen


def test_formulas_without_implementation_are_no_load_failure() -> None:
    build = load_build(FIXTURE, Registry())
    assert "calc:stall-speed" in build.report.not_implemented


def test_a_missing_model_file_is_a_load_failure(tmp_path: Path) -> None:
    with pytest.raises(CanonLoadError) as caught:
        load_build(tmp_path / "absent.json", Registry())
    assert caught.value.error.category is ErrorCategory.INTERNAL
    assert caught.value.error.escalate is True


def test_a_traceability_finding_is_a_load_failure(caplog: pytest.LogCaptureFixture) -> None:
    registry = Registry()

    async def ghost(x: object, ctx: object) -> dict[str, object]:
        return {}

    registry.formula("no-such-formula")(ghost)
    with (
        caplog.at_level(logging.DEBUG, logger="aero_kernel"),
        pytest.raises(CanonLoadError) as caught,
    ):
        load_build(FIXTURE, registry)
    error = caught.value.error
    assert error.category is ErrorCategory.INTERNAL
    assert "no-such-formula" in str(error.detail)
    assert str(FIXTURE) not in f"{error.message} {error.hint} {error.detail}"
    logged = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert len(logged) == 1


def test_a_graph_defect_is_a_load_failure(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def broken(model: CanonModel) -> CanonGraph:
        msg = "cycle: a -> b -> a"
        raise GraphModelError(msg)

    monkeypatch.setattr(build_module, "CanonGraph", broken)
    with (
        caplog.at_level(logging.DEBUG, logger="aero_kernel"),
        pytest.raises(CanonLoadError) as caught,
    ):
        load_build(FIXTURE, Registry())
    assert "cycle" not in caught.value.error.message
    logged = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert len(logged) == 1
    assert logged[0].exc_info is not None


def test_the_default_registry_is_used_when_none_is_given(monkeypatch: pytest.MonkeyPatch) -> None:
    from aero_kernel.registry import DEFAULT_REGISTRY

    assert load_build(FIXTURE).registry is DEFAULT_REGISTRY


def test_the_shipped_build_loads_once(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    original = build_module.load_build

    def counting() -> Build:
        calls.append(1)
        return original(FIXTURE, Registry())

    monkeypatch.setattr(build_module, "load_build", counting)
    first = shipped_build()
    assert shipped_build() is first
    assert len(calls) == 1


def test_a_failed_shipped_load_is_not_memoised(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from aero_kernel.canon import load as load_module

    monkeypatch.setattr(load_module, "default_model_path", lambda: tmp_path / "absent.json")
    with pytest.raises(CanonLoadError):
        shipped_build()
    with pytest.raises(CanonLoadError):
        shipped_build()
    monkeypatch.setattr(load_module, "default_model_path", lambda: FIXTURE)
    assert shipped_build().model.content_hash.startswith("sha256:")


def test_importing_the_package_reads_no_model_file() -> None:
    script = (
        "import builtins, os\n"
        "opened = []\n"
        "real_open, real_os_open = builtins.open, os.open\n"
        "builtins.open = lambda f, *a, **k: (opened.append(str(f)), real_open(f, *a, **k))[1]\n"
        "os.open = lambda f, *a, **k: (opened.append(str(f)), real_os_open(f, *a, **k))[1]\n"
        "import aero_kernel, aero_kernel.api\n"
        "from aero_kernel.build import shipped_build\n"
        "assert shipped_build.cache_info().currsize == 0\n"
        "assert not [p for p in opened if p.endswith('.json')], opened\n"
    )
    done = subprocess.run(  # fixed interpreter and inline script
        [sys.executable, "-c", script], capture_output=True, text=True, check=False
    )
    assert done.returncode == 0, done.stderr
