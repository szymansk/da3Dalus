"""The ATM adapter: exact ISA density behind the solver boundary (ARCHITECTURE ch. 8.8, K30)."""

import importlib.machinery
import math
import sys
import types

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.runtime import SolverRuntime
from aero_kernel.solvers.atmosphere import AtmosphereAdapter


class FakeAtmosphere:
    """Stands in for ``asb.Atmosphere``: records its arguments, density = 2 * altitude / 1000."""

    calls: list[tuple[float, str]] = []  # noqa: RUF012  # test spy, reset by the fixture

    def __init__(self, altitude: float, method: str = "differentiable") -> None:
        self.altitude = altitude
        self.method = method
        self._valid_altitude_range = (0.0, 80000.0)
        FakeAtmosphere.calls.append((altitude, method))

    def density(self) -> float:
        return 2.0 * self.altitude / 1000.0


@pytest.fixture
def fake_aerosandbox(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install a fake ``aerosandbox`` that ``find_spec`` can see."""
    FakeAtmosphere.calls = []
    module = types.ModuleType("aerosandbox")
    module.__spec__ = importlib.machinery.ModuleSpec("aerosandbox", None)
    module.Atmosphere = FakeAtmosphere  # pyright: ignore[reportAttributeAccessIssue]  # fake module
    monkeypatch.setitem(sys.modules, "aerosandbox", module)


def test_the_adapter_declares_its_tool_and_requirement() -> None:
    assert AtmosphereAdapter.tool == "ATM"
    assert AtmosphereAdapter.requirements == {"aerosandbox": "aerosandbox"}


@pytest.mark.asyncio
async def test_density_asks_the_exact_isa_for_the_altitude(fake_aerosandbox: None) -> None:
    density = await AtmosphereAdapter(SolverRuntime()).density(1500.0)
    assert density == 3.0
    assert FakeAtmosphere.calls == [(1500.0, "isa")]


@pytest.mark.asyncio
@pytest.mark.parametrize("altitude", [-0.5, 80000.5])
async def test_an_altitude_outside_the_isa_range_is_invalid_input(
    fake_aerosandbox: None, altitude: float
) -> None:
    with pytest.raises(FormulaError) as raised:
        await AtmosphereAdapter(SolverRuntime()).density(altitude)
    assert raised.value.category is ErrorCategory.INVALID_INPUT
    assert raised.value.parameter == "h"
    assert raised.value.detail is not None
    assert raised.value.detail["valid_range_m"] == [0.0, 80000.0]


@pytest.mark.asyncio
@pytest.mark.parametrize("altitude", [0.0, 80000.0])
async def test_the_range_limits_belong_to_the_range(
    fake_aerosandbox: None, altitude: float
) -> None:
    assert await AtmosphereAdapter(SolverRuntime()).density(altitude) == 2.0 * altitude / 1000.0


@pytest.mark.asyncio
async def test_a_missing_aerosandbox_is_tool_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(AtmosphereAdapter, "requirements", {"no-such-distribution": "no_such_xyz"})
    with pytest.raises(FormulaError) as raised:
        await AtmosphereAdapter(SolverRuntime()).density(100.0)
    assert raised.value.category is ErrorCategory.TOOL_UNAVAILABLE


@pytest.mark.asyncio
@pytest.mark.aero
@pytest.mark.parametrize("altitude", [0.0, 1000.0, 5000.0])
async def test_the_real_isa_matches_the_hand_computed_troposphere(altitude: float) -> None:
    """Hand computation of the ISA troposphere (ISO 2533 / U.S. Standard Atmosphere 1976).

    T = 288.15 K - 0.0065 K/m * h; p = 101325 Pa * (T / 288.15 K)^(g / (R * 0.0065));
    rho = p / (R * T) with R = 287.053 J/(kg K), g = 9.80665 m/s^2. That gives
    1.22500 (0 m), 1.11164 (1000 m) and 0.73612 kg/m^3 (5000 m). AeroSandbox documents a mean
    error of 0.02 % against the ISA for its tabulated model, so 0.05 % is the tolerance.
    """
    gas_constant, gravity, lapse = 287.053, 9.80665, 0.0065
    temperature = 288.15 - lapse * altitude
    pressure = 101325.0 * (temperature / 288.15) ** (gravity / (gas_constant * lapse))
    hand: float = pressure / (gas_constant * temperature)
    density = await AtmosphereAdapter(SolverRuntime()).density(altitude)
    assert math.isclose(density, hand, rel_tol=5e-4)
