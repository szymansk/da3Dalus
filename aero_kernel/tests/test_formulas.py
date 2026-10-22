"""The slice-1 formulas: each against a hand value, ``x`` built from the model (Q11)."""

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.air_density_isa import air_density_isa
from aero_kernel.formulas.dynamic_pressure import dynamic_pressure
from aero_kernel.formulas.values import number
from aero_kernel.formulas.weight_from_mass import weight_from_mass
from aero_kernel.registry import DEFAULT_REGISTRY
from aero_kernel.tests.formula_builders import (
    StubAtmosphere,
    close,
    context_with,
    inputs_from_model,
)

pytestmark = pytest.mark.asyncio

MODEL = shipped_build().model
IMPLEMENTED = {"calc:weight-from-mass", "calc:air-density-isa", "calc:dynamic-pressure"}


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
    with pytest.raises(FormulaError) as raised:
        await air_density_isa(x, context_with(Failing({})))
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
    assert len(build.report.not_implemented) == 56


async def test_number_rejects_an_absent_or_non_numeric_parameter() -> None:
    assert number({"a": 2.5}, "a") == 2.5
    with pytest.raises(TypeError, match="'a'"):
        number({"a": None}, "a")
