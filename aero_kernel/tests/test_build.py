"""Tests of the ``Build`` and its loaders (ARCHITECTURE ch. 8.4)."""

import asyncio
import json
import logging
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from aero_kernel import build as build_module
from aero_kernel.build import Build, load_build, shipped_build
from aero_kernel.cache import build_digest
from aero_kernel.canon import load as load_module
from aero_kernel.canon.load import CanonLoadError, load_canon_model
from aero_kernel.canon.model import CanonModel
from aero_kernel.errors import ErrorCategory
from aero_kernel.graph import CanonGraph, GraphModelError
from aero_kernel.registry import Registry
from aero_kernel.tests.canon_builders import with_hash
from aero_kernel.tests.formula_builders import IMPLEMENTED
from aero_kernel.tests.graph_builders import formula, quantity

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "flight_canon.json"


@pytest.fixture(autouse=True)
def fresh_memo() -> Iterator[None]:
    shipped_build.cache_clear()
    yield
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
    assert error.hint == "Report it; attach input and provenance."
    assert error.message == (
        "The canon model could not be loaded: the implementations do not match the model."
    )
    assert error.detail["finding_count"] == 1
    assert error.detail["findings"] == [
        {"kind": "unknown_formula", "slug": "no-such-formula", "check_id": None}
    ]
    assert str(FIXTURE) not in f"{error.message} {error.hint} {error.detail}"
    assert [r for r in caplog.records if r.levelno >= logging.WARNING] == []


def test_a_cyclic_model_is_a_load_failure(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    namespaces = {
        "calc": {
            "quantities": {"a": quantity("derived"), "b": quantity("derived")},
            "formulas": {
                "f-a": formula({"x": "b"}, {"y": "a"}),
                "f-b": formula({"x": "a"}, {"y": "b"}),
            },
        }
    }
    path = tmp_path / "cyclic.json"
    path.write_text(json.dumps(with_hash(namespaces)), encoding="utf-8")
    with (
        caplog.at_level(logging.DEBUG, logger="aero_kernel"),
        pytest.raises(CanonLoadError) as caught,
    ):
        load_build(path, Registry())
    assert "cycle" not in caught.value.error.message
    assert caught.value.error.hint == "Report it; attach input and provenance."
    assert [r for r in caplog.records if r.levelno >= logging.WARNING] == []


def test_a_model_with_an_unproduced_computed_quantity_is_a_load_failure(tmp_path: Path) -> None:
    namespaces = {"calc": {"quantities": {"a": quantity("output")}, "formulas": {}}}
    path = tmp_path / "unproduced.json"
    path.write_text(json.dumps(with_hash(namespaces)), encoding="utf-8")
    with pytest.raises(CanonLoadError):
        load_build(path, Registry())


def test_the_shipped_build_loads_once(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    original = build_module.load_build

    def counting(*args: Any, **kwargs: Any) -> Build:
        calls.append((args, kwargs))
        return original(FIXTURE, Registry())

    monkeypatch.setattr(build_module, "load_build", counting)
    first = shipped_build()
    assert shipped_build() is first
    assert calls == [((), {})]


def test_a_failed_shipped_load_is_not_memoised(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(load_module, "default_model_path", lambda: tmp_path / "absent.json")
    with pytest.raises(CanonLoadError):
        shipped_build()
    with pytest.raises(CanonLoadError):
        shipped_build()
    monkeypatch.setattr(load_module, "default_model_path", lambda: FIXTURE)
    monkeypatch.setattr(build_module, "DEFAULT_REGISTRY", Registry())  # the fixture has no formulas
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


def test_the_digest_is_the_package_digest_and_the_hash_the_models() -> None:
    build = load_build(FIXTURE, Registry())
    assert build.digest == build_digest()
    assert build.model.content_hash == load_canon_model(FIXTURE).content_hash
    assert build.report == Registry().check_traceability(build.model)


def test_a_given_registry_is_used_even_when_it_is_empty() -> None:
    empty = Registry()
    assert load_build(FIXTURE, empty).registry is empty


def test_a_graph_defect_keeps_its_cause_and_says_so(tmp_path: Path) -> None:
    namespaces = {
        "calc": {
            "quantities": {"a": quantity("derived"), "b": quantity("derived")},
            "formulas": {
                "f-a": formula({"x": "b"}, {"y": "a"}),
                "f-b": formula({"x": "a"}, {"y": "b"}),
            },
        }
    }
    path = tmp_path / "cyclic.json"
    path.write_text(json.dumps(with_hash(namespaces)), encoding="utf-8")
    with pytest.raises(CanonLoadError) as caught:
        load_build(path, Registry())
    assert isinstance(caught.value.__cause__, GraphModelError)
    assert caught.value.error.message == (
        "The canon model could not be loaded: the model is not a well-formed graph."
    )


def test_a_successful_load_logs_one_debug_line_and_nothing_louder(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG, logger="aero_kernel"):
        build = load_build(FIXTURE, Registry())
    assert [r for r in caplog.records if r.levelno >= logging.INFO] == []
    ready = [r for r in caplog.records if r.getMessage().startswith("build ready")]
    formulas = sum(len(c.formulas) for c in build.model.namespaces.values())
    assert [r.getMessage() for r in ready] == [
        f"build ready: {formulas} formulas, {len(build.report.not_implemented)} without implementation"
    ]
    assert all(r.levelno == logging.DEBUG for r in ready)


class SilentRegistry(Registry):
    """A registry that is falsy, as a container with nothing in it would be."""

    def __len__(self) -> int:
        return 0


def test_a_falsy_registry_is_used_as_given() -> None:
    registry = SilentRegistry()
    assert not registry
    assert load_build(FIXTURE, registry).registry is registry


def test_any_exception_while_assembling_is_a_load_failure_with_its_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken(root: object = None) -> str:
        msg = "disk gone"
        raise OSError(msg)

    monkeypatch.setattr(build_module, "build_digest", broken)
    with pytest.raises(CanonLoadError) as caught:
        load_build(FIXTURE, Registry())
    assert isinstance(caught.value.__cause__, OSError)
    assert caught.value.error.category is ErrorCategory.INTERNAL
    assert caught.value.error.escalate is True
    assert "disk gone" not in caught.value.error.message


def test_the_default_registry_is_traced_by_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    fresh = Registry()
    monkeypatch.setattr(build_module, "DEFAULT_REGISTRY", fresh)
    assert load_build(FIXTURE).registry is fresh


@pytest.mark.parametrize(
    "failure", [RuntimeError("x"), ValueError("x"), OSError("x")], ids=lambda e: type(e).__name__
)
def test_every_exception_of_the_digest_is_wrapped_with_its_cause(
    monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    def broken(*args: object, **kwargs: object) -> str:
        raise failure

    monkeypatch.setattr(build_module, "build_digest", broken)
    with pytest.raises(CanonLoadError) as caught:
        load_build(FIXTURE, Registry())
    assert caught.value.__cause__ is failure
    assert caught.value.error.message == (
        "The canon model could not be loaded: the build could not be assembled."
    )


def test_an_exception_of_the_traceability_check_is_wrapped_with_its_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failure = KeyError("slug")

    def broken(self: Registry, model: CanonModel) -> object:
        raise failure

    monkeypatch.setattr(Registry, "check_traceability", broken)
    with pytest.raises(CanonLoadError) as caught:
        load_build(FIXTURE, Registry())
    assert caught.value.__cause__ is failure


def test_cancellation_is_not_a_load_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def cancelled(*args: object, **kwargs: object) -> str:
        raise asyncio.CancelledError

    monkeypatch.setattr(build_module, "build_digest", cancelled)
    with pytest.raises(asyncio.CancelledError):
        load_build(FIXTURE, Registry())


def test_every_formula_but_the_built_ones_is_not_implemented_at_build_time() -> None:
    """Only the formulas of IMPLEMENTED have an implementation; the others are declared only."""
    from aero_kernel.build import shipped_build

    build = shipped_build()
    declared = {
        f"{namespace}:{slug}"
        for namespace, content in build.model.namespaces.items()
        for slug in content.formulas
    }
    implemented = IMPLEMENTED
    assert set(build.report.not_implemented) == declared - implemented
    assert len(build.report.not_implemented) == 59 - len(IMPLEMENTED)
