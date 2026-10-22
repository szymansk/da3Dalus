"""The GEO adapter: the AeroSandbox airplane of a geometry document (ARCHITECTURE ch. 8.8)."""

import importlib
import threading
import types

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.runtime import SolverRuntime
from aero_kernel.solvers import geometry as geometry_module
from aero_kernel.solvers.geometry import GeometryAdapter
from aero_kernel.tests.asb_fakes import FakeAirplane, install_fake_aerosandbox
from aero_kernel.tests.test_solvers_asb_airplane import geometry

pytestmark = pytest.mark.asyncio


async def test_the_adapter_declares_its_tool_and_requirement() -> None:
    assert GeometryAdapter.tool == "GEO"
    assert GeometryAdapter.requirements == {"aerosandbox": "aerosandbox"}


async def test_the_adapter_hands_out_the_one_conversion(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_aerosandbox(monkeypatch)
    airplane = await GeometryAdapter(SolverRuntime()).asb_airplane(geometry())
    assert isinstance(airplane, FakeAirplane)
    assert [w.kwargs["name"] for w in airplane.kwargs["wings"]] == ["Main", "Fin"]


async def test_the_import_runs_off_the_event_loop_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_aerosandbox(monkeypatch)
    imported_on: list[int] = []
    real_import = importlib.import_module

    def recording(name: str, package: str | None = None) -> types.ModuleType:
        imported_on.append(threading.get_ident())
        return real_import(name, package)

    monkeypatch.setattr(geometry_module.importlib, "import_module", recording)
    await GeometryAdapter(SolverRuntime()).asb_airplane(geometry())
    assert imported_on[0] != threading.get_ident()


async def test_a_missing_aerosandbox_is_tool_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(GeometryAdapter, "requirements", {"no-such-distribution": "no_such_xyz"})
    adapter = GeometryAdapter(SolverRuntime())
    document = geometry()
    with pytest.raises(FormulaError) as raised:
        await adapter.asb_airplane(document)
    assert raised.value.category is ErrorCategory.TOOL_UNAVAILABLE
