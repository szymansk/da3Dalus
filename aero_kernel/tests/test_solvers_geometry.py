"""The GEO adapter: AeroSandbox's reference values of the main wing behind the solver boundary."""

import sys

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.runtime import SolverRuntime
from aero_kernel.solvers import geometry as geometry_module
from aero_kernel.solvers.asb_airplane import (
    fin_area,
    main_wing_properties,
    quarter_chord_mac_x,
    surface_properties,
)
from aero_kernel.solvers.geometry import GeometryAdapter
from aero_kernel.tests.asb_fakes import (
    FAKE_AC_X,
    FAKE_CENTRELINE_AREA,
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
        area + FAKE_CENTRELINE_AREA,
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
    assert (found.area, found.span, found.c_mac) == (
        area + FAKE_CENTRELINE_AREA,
        span + FAKE_CENTRELINE_GAP,
        chord,
    )
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


@pytest.mark.asyncio
async def test_the_quarter_chord_position_is_asbs_aerodynamic_centre(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_aerosandbox(monkeypatch)
    monkeypatch.setattr(geometry_module, "quarter_chord_mac_x", quarter_chord_mac_x)
    x = await GeometryAdapter(SolverRuntime()).quarter_chord_mac_x(airplane(), "Main")
    assert x == FAKE_AC_X["Main"]


def test_the_quarter_chord_is_asked_with_an_explicit_chord_fraction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The flag is set in code, never left to ASB's default (maintainer, gh-1262)."""
    module = install_fake_aerosandbox(monkeypatch)
    asked: list[dict[str, float]] = []
    original = module.Wing.aerodynamic_center  # pyright: ignore[reportAttributeAccessIssue]

    def recording(self: object, **options: float) -> list[float]:
        asked.append(options)
        return original(self, **options)

    monkeypatch.setattr(module.Wing, "aerodynamic_center", recording)  # pyright: ignore[reportAttributeAccessIssue]
    quarter_chord_mac_x(airplane(), "Main")
    assert asked == [{"chord_fraction": 0.25}]


def _nan_centre(*_args: object, **_options: object) -> list[float]:
    return [float("nan"), 0.0, 0.0]


def test_a_wing_without_a_finite_aerodynamic_centre_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = install_fake_aerosandbox(monkeypatch)
    monkeypatch.setattr(
        module.Wing,  # pyright: ignore[reportAttributeAccessIssue]
        "aerodynamic_center",
        _nan_centre,
    )
    plane = airplane()
    with pytest.raises(FormulaError) as raised:
        quarter_chord_mac_x(plane, "Main")
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION


@pytest.mark.asyncio
async def test_without_aerosandbox_the_quarter_chord_position_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "aerosandbox", None)
    adapter = GeometryAdapter(SolverRuntime())
    document = airplane()
    with pytest.raises(FormulaError) as raised:
        await adapter.quarter_chord_mac_x(document, "Main")
    assert raised.value.category is ErrorCategory.TOOL_UNAVAILABLE


@pytest.mark.asyncio
async def test_the_fin_area_is_what_asb_reports(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_aerosandbox(monkeypatch)
    monkeypatch.setattr(geometry_module, "fin_area", fin_area)
    found = await GeometryAdapter(SolverRuntime()).fin_area(airplane(), "Main")
    assert (
        found == FAKE_REFERENCE["Main"][0]
    )  # the fake adds its centreline area only when asked to


@pytest.mark.asyncio
async def test_without_aerosandbox_the_fin_area_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "aerosandbox", None)
    adapter = GeometryAdapter(SolverRuntime())
    document = airplane()
    with pytest.raises(FormulaError) as raised:
        await adapter.fin_area(document, "Main")
    assert raised.value.category is ErrorCategory.TOOL_UNAVAILABLE
