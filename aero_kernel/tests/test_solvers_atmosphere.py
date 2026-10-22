"""The ATM adapter: exact ISA density behind the solver boundary (ARCHITECTURE ch. 8.8, K30)."""

import importlib
import importlib.machinery
import math
import sys
import threading
import types

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.runtime import SolverRuntime
from aero_kernel.solvers import atmosphere as atmosphere_module
from aero_kernel.solvers.atmosphere import AtmosphereAdapter


class FakeAtmosphere:
    """Stands in for ``asb.Atmosphere``: records its arguments, density = 1 + altitude / 1000."""

    calls: list[tuple[float, str]] = []  # noqa: RUF012  # test spy, reset by the fixture

    def __init__(self, altitude: float, method: str = "differentiable") -> None:
        self.altitude = altitude
        self.method = method
        self._valid_altitude_range = (0.0, 80000.0)
        FakeAtmosphere.calls.append((altitude, method))

    def density(self) -> float:
        return 1.0 + self.altitude / 1000.0

    def dynamic_viscosity(self) -> float:
        return 1.0e-5 + self.altitude * 1.0e-9

    def speed_of_sound(self) -> float:
        return 300.0 + self.altitude / 1000.0


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
async def test_state_asks_the_exact_isa_for_the_altitude(fake_aerosandbox: None) -> None:
    air = await AtmosphereAdapter(SolverRuntime()).state(1500.0)
    assert (air.density, air.speed_of_sound) == (2.5, 301.5)
    assert math.isclose(air.dynamic_viscosity, 1.15e-05, rel_tol=1e-12)
    assert FakeAtmosphere.calls == [(1500.0, "isa")]


@pytest.mark.asyncio
@pytest.mark.parametrize("altitude", [-0.5, 80000.5])
async def test_an_altitude_outside_the_isa_range_is_invalid_input(
    fake_aerosandbox: None, altitude: float
) -> None:
    adapter = AtmosphereAdapter(SolverRuntime())
    with pytest.raises(FormulaError) as raised:
        await adapter.state(altitude)
    assert raised.value.category is ErrorCategory.INVALID_INPUT
    assert raised.value.parameter == "h"
    assert raised.value.detail is not None
    assert raised.value.detail["valid_range_m"] == [0.0, 80000.0]


@pytest.mark.asyncio
@pytest.mark.parametrize("altitude", [0.0, 80000.0])
async def test_the_range_limits_belong_to_the_range(
    fake_aerosandbox: None, altitude: float
) -> None:
    assert (
        await AtmosphereAdapter(SolverRuntime()).state(altitude)
    ).density == 1.0 + altitude / 1000.0


@pytest.mark.asyncio
async def test_a_missing_aerosandbox_is_tool_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(AtmosphereAdapter, "requirements", {"no-such-distribution": "no_such_xyz"})
    adapter = AtmosphereAdapter(SolverRuntime())
    with pytest.raises(FormulaError) as raised:
        await adapter.state(100.0)
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
    air = await AtmosphereAdapter(SolverRuntime()).state(altitude)
    assert math.isclose(air.density, hand, rel_tol=5e-4)
    # Sutherland's law and the speed of sound of an ideal gas, with the same temperature:
    # mu = 1.458e-6 T^1.5 / (T + 110.4) Pa s; a = sqrt(1.4 R T), R = 287.05 J/(kg K).
    assert math.isclose(
        air.dynamic_viscosity, 1.458e-6 * temperature**1.5 / (temperature + 110.4), rel_tol=1e-4
    )
    assert math.isclose(air.speed_of_sound, math.sqrt(1.4 * 287.05 * temperature), rel_tol=1e-4)


@pytest.mark.asyncio
async def test_the_import_runs_off_the_event_loop_thread(
    fake_aerosandbox: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The first import of aerosandbox takes about 0.8 s and must not stall the loop (ch. 8.10)."""
    imported_on: list[tuple[str, int]] = []
    real_import = importlib.import_module

    def recording(name: str, package: str | None = None) -> types.ModuleType:
        imported_on.append((name, threading.get_ident()))
        return real_import(name, package)

    monkeypatch.setattr(atmosphere_module.importlib, "import_module", recording)
    await AtmosphereAdapter(SolverRuntime()).state(100.0)
    assert [name for name, _ in imported_on] == ["aerosandbox"]
    assert imported_on[0][1] != threading.get_ident()
