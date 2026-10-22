"""The slice-1 formulas: each against a hand value, ``x`` built from the model (Q11)."""

from typing import Any

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.air_density_isa import air_density_isa
from aero_kernel.formulas.airplane_configuration import airplane_configuration
from aero_kernel.formulas.airplane_geometry import airplane_geometry
from aero_kernel.formulas.aspect_ratio import aspect_ratio
from aero_kernel.formulas.dynamic_pressure import dynamic_pressure
from aero_kernel.formulas.mean_geometric_chord import mean_geometric_chord
from aero_kernel.formulas.values import number
from aero_kernel.formulas.weight_from_mass import weight_from_mass
from aero_kernel.formulas.wing_loading import wing_loading
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.registry import DEFAULT_REGISTRY
from aero_kernel.tests.formula_builders import (
    IMPLEMENTED,
    StubAtmosphere,
    close,
    context_with,
    inputs_from_model,
)

pytestmark = pytest.mark.asyncio

MODEL = shipped_build().model


async def test_weight_from_mass_is_mass_times_gravity() -> None:
    """Hand value: W = m g = 0.151 kg * 9.80665 m/s^2 = 1.48080415 N (BRYAN)."""
    x = inputs_from_model(MODEL, "weight-from-mass", {"aircraft-mass": 0.151, "gravity": 9.80665})
    result = await weight_from_mass(x, context_with(StubAtmosphere({})))
    assert set(result) == {"w"}
    assert close(result["w"], 1.48080415, 1e-12)


async def test_dynamic_pressure_is_half_density_times_speed_squared() -> None:
    """Hand value: q = 1/2 rho V^2 = 0.5 * 1.2 kg/m^3 * (10 m/s)^2 = 60 Pa."""
    x = inputs_from_model(MODEL, "dynamic-pressure", {"air-density": 1.2, "flight-speed": 10.0})
    result = await dynamic_pressure(x, context_with(StubAtmosphere({})))
    assert result == {"q": 60.0}


async def test_air_density_isa_asks_the_atmosphere_adapter_for_the_altitude() -> None:
    """The formula returns exactly what the adapter says for its altitude, nothing substituted."""
    atmosphere = StubAtmosphere({1000.0: 1.1116})
    x = inputs_from_model(MODEL, "air-density-isa", {"altitude": 1000.0})
    result = await air_density_isa(x, context_with(atmosphere))
    assert result == {"rho": 1.1116}
    assert atmosphere.asked == [1000.0]


async def test_air_density_isa_passes_an_adapter_failure_on_unchanged() -> None:
    class Failing(StubAtmosphere):
        async def density(self, altitude_m: float) -> float:
            raise FormulaError(ErrorCategory.TOOL_UNAVAILABLE, "tool_unavailable", "m", "h")

    x = inputs_from_model(MODEL, "air-density-isa", {"altitude": 0.0})
    context = context_with(Failing({}))
    with pytest.raises(FormulaError) as raised:
        await air_density_isa(x, context)
    assert raised.value.category is ErrorCategory.TOOL_UNAVAILABLE


async def test_the_default_registry_holds_exactly_these_three_and_is_frozen() -> None:
    assert DEFAULT_REGISTRY.slugs() == IMPLEMENTED
    assert DEFAULT_REGISTRY.frozen


async def test_the_traceability_report_is_ok_on_the_shipped_model() -> None:
    build = shipped_build()
    assert build.report.ok
    declared = {
        f"{namespace}:{slug}"
        for namespace, content in build.model.namespaces.items()
        for slug in content.formulas
    }
    assert set(build.report.not_implemented) == declared - IMPLEMENTED
    assert len(build.report.not_implemented) == 59 - len(IMPLEMENTED)


async def test_number_rejects_an_absent_or_non_numeric_parameter() -> None:
    assert number({"a": 2.5}, "a") == 2.5
    with pytest.raises(TypeError, match="'a'"):
        number({"a": None}, "a")


async def test_mean_geometric_chord_is_area_over_span() -> None:
    """Hand value: c_bar = S / b = 0.06 m^2 / 0.4 m = 0.15 m."""
    x = inputs_from_model(
        MODEL, "mean-geometric-chord", {"wing-reference-area": 0.06, "wing-span": 0.4}
    )
    result = await mean_geometric_chord(x, context_with(StubAtmosphere({})))
    assert set(result) == {"c_bar"}
    assert close(result["c_bar"], 0.15, 1e-12)


async def test_aspect_ratio_is_span_squared_over_area() -> None:
    """Hand value: AR = b^2 / S = (0.4 m)^2 / 0.06 m^2 = 8/3 = 2.6667."""
    x = inputs_from_model(MODEL, "aspect-ratio", {"wing-reference-area": 0.06, "wing-span": 0.4})
    result = await aspect_ratio(x, context_with(StubAtmosphere({})))
    assert set(result) == {"ar"}
    assert close(result["ar"], 8.0 / 3.0, 1e-12)


async def test_wing_loading_is_weight_over_area() -> None:
    """Hand value: W/S = m g / S = 0.151 kg * 9.80665 m/s^2 / 0.06 m^2 = 24.68007 N/m^2."""
    x = inputs_from_model(
        MODEL,
        "wing-loading",
        {"aircraft-mass": 0.151, "gravity": 9.80665, "wing-reference-area": 0.06},
    )
    result = await wing_loading(x, context_with(StubAtmosphere({})))
    assert set(result) == {"w_s"}
    assert close(result["w_s"], 1.48080415 / 0.06, 1e-12)


async def test_airplane_geometry_returns_the_projected_reference_values_of_the_main_wing() -> None:
    """Hand values: half panel y 0..0.4 m, chord 0.2 -> 0.1 m, mirrored: S 0.12, b 0.8, c_MAC 0.155556."""
    sections = [
        {"xyz_le": [0.0, y, 0.0], "chord": c, "twist": 0.0, "airfoil": "naca2412"}
        for y, c in ((0.0, 0.2), (0.4, 0.1))
    ]
    wing = {"name": "Main", "surface_type": "main_wing", "x_secs": sections}
    airplane = AirplaneGeometry.model_validate({"name": "t", "wings": {"Main": wing}})
    x = inputs_from_model(MODEL, "airplane-geometry", {"airplane": airplane})
    result = await airplane_geometry(x, context_with(StubAtmosphere({})))
    assert set(result) == {"s_ref", "b_ref", "c_mac"}
    assert close(result["s_ref"], 0.12, 1e-12)
    assert close(result["b_ref"], 0.8, 1e-12)
    assert close(result["c_mac"], 2 / 0.12 * 0.4 * 0.07 / 3, 1e-12)


async def test_airplane_geometry_rejects_a_value_that_is_not_the_geometry() -> None:
    context = context_with(StubAtmosphere({}))
    with pytest.raises(TypeError, match="airplane"):
        await airplane_geometry({"airplane": 1.0}, context)


def main_wing_document(root_y: float) -> AirplaneGeometry:
    sections = [
        {"xyz_le": [0.0, y, 0.0], "chord": c, "twist": 0.0, "airfoil": "naca2412"}
        for y, c in ((root_y, 0.3), (0.45, 0.2))
    ]
    wing = {"name": "Main", "surface_type": "main_wing", "x_secs": sections}
    return AirplaneGeometry.model_validate({"name": "t", "wings": {"Main": wing}})


async def test_airplane_geometry_warns_when_the_root_is_extended_to_the_centreline() -> None:
    x = inputs_from_model(MODEL, "airplane-geometry", {"airplane": main_wing_document(0.05)})
    context = context_with(StubAtmosphere({}), origin="wing-reference-area")
    await airplane_geometry(x, context)
    (warning,) = context.warnings
    assert warning.code == "reference_wing_at_centreline"
    assert warning.severity.value == "practice"
    assert warning.origin == "wing-reference-area"
    assert warning.detail == {"wing": "Main", "extended_m": 0.05}
    assert "extended" in warning.message
    assert "centreline" in warning.message


async def test_airplane_geometry_warns_when_the_stored_side_is_clipped_at_the_centreline() -> None:
    x = inputs_from_model(MODEL, "airplane-geometry", {"airplane": main_wing_document(-0.1)})
    context = context_with(StubAtmosphere({}))
    await airplane_geometry(x, context)
    (warning,) = context.warnings
    assert warning.code == "reference_wing_at_centreline"
    assert warning.detail == {"wing": "Main", "clipped_m": 0.1}
    assert "clipped" in warning.message


async def test_airplane_geometry_does_not_warn_when_the_root_lies_on_the_centreline() -> None:
    x = inputs_from_model(MODEL, "airplane-geometry", {"airplane": main_wing_document(0.0)})
    context = context_with(StubAtmosphere({}))
    await airplane_geometry(x, context)
    assert context.warnings == ()


def configuration_x(deflection: float | None, *roles: str) -> dict[str, Any]:
    """``x`` of airplane-configuration from the model: an airplane with devices of the given roles."""
    sections = [
        {
            "xyz_le": [0.0, 0.2 * index, 0.0],
            "chord": 0.2,
            "twist": 0.0,
            "airfoil": "naca2412",
            **({"trailing_edge_device": {"role": role}} if role else {}),
        }
        for index, role in enumerate((*roles, ""))
    ]
    wing = {"name": "Main", "surface_type": "main_wing", "x_secs": sections}
    airplane = AirplaneGeometry.model_validate({"name": "t", "wings": {"Main": wing}})
    x: dict[str, Any] = {"airplane": airplane, "flap_deflection": deflection}
    assert set(x) == set(MODEL.formula("airplane-configuration").inputs)  # type: ignore[union-attr]  # formula exists
    return x


def deflections_of(airplane: AirplaneGeometry) -> list[float | None]:
    return [
        None if s.trailing_edge_device is None else s.trailing_edge_device.deflection_deg
        for s in (airplane.wings or {})["Main"].x_secs
    ]


async def test_configuration_with_flaps_and_a_deflection_sets_the_flaps_exactly() -> None:
    x = configuration_x(55.0, "flap", "aileron")
    context = context_with(StubAtmosphere({}))
    result = await airplane_configuration(x, context)
    assert set(result) == {"airplane_cfg"}
    assert deflections_of(result["airplane_cfg"]) == [55.0, 0.0, None]
    assert context.warnings == ()


async def test_configuration_without_flaps_and_without_a_deflection_is_the_airplane_itself() -> (
    None
):
    x = configuration_x(None, "aileron")
    context = context_with(StubAtmosphere({}))
    result = await airplane_configuration(x, context)
    assert result["airplane_cfg"] == x["airplane"]
    assert context.warnings == ()


async def test_configuration_without_flaps_ignores_a_deflection_and_warns() -> None:
    x = configuration_x(20.0, "aileron")
    context = context_with(StubAtmosphere({}), origin="airplane-landing")
    result = await airplane_configuration(x, context)
    assert result["airplane_cfg"] == x["airplane"]
    (warning,) = context.warnings
    assert warning.code == "deflection_without_flap"
    assert warning.origin == "airplane-landing"
    assert warning.detail == {"flap_deflection_deg": 20.0}


async def test_configuration_with_flaps_but_no_deflection_is_a_missing_input() -> None:
    x = configuration_x(None, "flap")
    context = context_with(StubAtmosphere({}))
    with pytest.raises(FormulaError) as raised:
        await airplane_configuration(x, context)
    assert raised.value.category is ErrorCategory.INVALID_INPUT
    assert raised.value.code == "missing_input"
    assert raised.value.parameter == "flap_deflection"
