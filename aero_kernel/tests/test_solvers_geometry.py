"""The GEO adapter: AeroSandbox's reference values of the main wing behind the solver boundary."""

import sys

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.runtime import SolverRuntime
from aero_kernel.solvers import geometry as geometry_module
from aero_kernel.solvers.asb_airplane import main_wing_properties, surface_properties
from aero_kernel.solvers.geometry import GeometryAdapter
from aero_kernel.tests.asb_fakes import (
    FAKE_AC_X,
    FAKE_CENTRELINE_GAP,
    FAKE_REFERENCE,
    install_fake_aerosandbox,
)
from aero_kernel.tests.wing_builders import airplane_document


def airplane() -> AirplaneGeometry:
    return AirplaneGeometry.model_validate(airplane_document())


def test_the_adapter_declares_its_tool_and_requirement() -> None:
    assert GeometryAdapter.tool == "GEO"
    assert GeometryAdapter.requirements == {"aerosandbox": "aerosandbox"}


@pytest.mark.asyncio
async def test_the_main_wing_reference_is_what_asb_reports(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_aerosandbox(monkeypatch)
    monkeypatch.setattr(geometry_module, "main_wing_properties", main_wing_properties)
    area, span, chord = FAKE_REFERENCE["Main"]
    reference = await GeometryAdapter(SolverRuntime()).main_wing_reference(airplane())
    assert (reference.s_ref, reference.b_ref, reference.c_mac) == (
        area,
        span + FAKE_CENTRELINE_GAP,
        chord,
    )


@pytest.mark.asyncio
async def test_without_aerosandbox_the_tool_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "aerosandbox", None)
    adapter = GeometryAdapter(SolverRuntime())
    assert not adapter.available()
    assert adapter.tool_versions() == {}
    document = airplane()
    with pytest.raises(FormulaError) as raised:
        await adapter.main_wing_reference(document)
    assert raised.value.category is ErrorCategory.TOOL_UNAVAILABLE


@pytest.mark.asyncio
async def test_the_surface_reference_is_what_asb_reports(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_aerosandbox(monkeypatch)
    monkeypatch.setattr(geometry_module, "surface_properties", surface_properties)
    area, span, chord = FAKE_REFERENCE["Main"]
    found = await GeometryAdapter(SolverRuntime()).surface_reference(airplane(), "Main")
    assert (found.area, found.span, found.c_mac) == (area, span + FAKE_CENTRELINE_GAP, chord)
    assert found.x_le_mac == FAKE_AC_X["Main"] - 0.25 * chord


@pytest.mark.asyncio
async def test_without_aerosandbox_the_surface_reference_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "aerosandbox", None)
    adapter = GeometryAdapter(SolverRuntime())
    document = airplane()
    with pytest.raises(FormulaError) as raised:
        await adapter.surface_reference(document, "Main")
    assert raised.value.category is ErrorCategory.TOOL_UNAVAILABLE
