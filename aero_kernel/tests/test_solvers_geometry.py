"""The GEO adapter: the AeroSandbox airplane of a geometry document (ARCHITECTURE ch. 8.8)."""

import importlib
import math
import threading
import types
from typing import Any

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry
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


def two_wing_airplane() -> AirplaneGeometry:
    """A tail listed first and the main wing second, so the choice cannot be 'the first wing'."""

    def sections(chords: tuple[float, float], half_span: float) -> list[dict[str, Any]]:
        return [
            {"xyz_le": [0.0, y, 0.0], "chord": c, "twist": 0.0, "airfoil": "naca2412"}
            for y, c in zip((0.0, half_span), chords, strict=True)
        ]

    return AirplaneGeometry.model_validate(
        {
            "name": "t",
            "wings": {
                "Tail": {
                    "name": "Tail",
                    "surface_type": "horizontal_tail",
                    "x_secs": sections((0.1, 0.05), 0.2),
                },
                "Main": {
                    "name": "Main",
                    "surface_type": "main_wing",
                    "x_secs": sections((0.2, 0.1), 0.4),
                },
            },
        }
    )


async def test_the_main_wing_properties_are_those_of_the_main_wing_not_the_first_wing() -> None:
    """Tail: half panel 0.2 m, chords 0.1 -> 0.05; Main: 0.4 m, 0.2 -> 0.1 (S 0.12, b 0.8)."""
    properties = await GeometryAdapter(SolverRuntime()).main_wing_properties(two_wing_airplane())
    assert math.isclose(properties.s_ref, 0.12, rel_tol=1e-12)
    assert math.isclose(properties.b_ref, 0.8, rel_tol=1e-12)
    assert math.isclose(properties.c_mac, 0.07 * 0.4 / 3 / 0.06, rel_tol=1e-12)


async def test_the_main_wing_properties_need_no_aerosandbox(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The reference values are integrated from the sections, not asked from AeroSandbox."""
    monkeypatch.setattr(GeometryAdapter, "requirements", {"no-such-distribution": "no_such_xyz"})
    properties = await GeometryAdapter(SolverRuntime()).main_wing_properties(two_wing_airplane())
    assert math.isclose(properties.b_ref, 0.8, rel_tol=1e-12)


@pytest.mark.parametrize("wings", [{}, {"A": "main_wing", "B": "main_wing"}])
async def test_other_than_one_main_wing_is_invalid_input(
    wings: dict[str, str],
) -> None:
    document = two_wing_airplane().model_dump(mode="json", by_alias=True)
    base = document["wings"]["Main"]
    document["wings"] = {k: {**base, "name": k, "surface_type": v} for k, v in wings.items()}
    airplane = AirplaneGeometry.model_validate(document)
    adapter = GeometryAdapter(SolverRuntime())
    with pytest.raises(FormulaError) as raised:
        await adapter.main_wing_properties(airplane)
    assert (raised.value.category, raised.value.code) == (
        ErrorCategory.INVALID_INPUT,
        "main_wing_count",
    )
