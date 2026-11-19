"""Canon formula ``airplane-components``: the properties of the fitted motor, battery and propeller.

A plain read of ``AircraftInput.components`` (tool ``KAT``, ARCHITECTURE ch. 8.8, 8.11) with the unit
conversions and the three derivations of the canonical form. The kernel holds no catalogue: the caller
pushes the parts, and a value a part does not carry is a failure of this formula, never a substitute
(gh-1397: no fallback, no default, no estimate).
"""

from typing import TypeVar

from aero_kernel.components import Components
from aero_kernel.context import Context, Inputs
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.registry import formula
from pydantic import JsonValue

__all__ = ["airplane_components"]

_T = TypeVar("_T")

# Unit conversions of the read (canon entry): the catalogue's grams, inches and percent to the
# canon's kg, m and 1. The inch is exactly 25.4 mm (international yard and pound agreement, 1959).
_G_PER_KG = 1000.0
_M_PER_INCH = 0.0254
_PERCENT = 100.0
_MAH_PER_AH = 1000.0

# The optional catalogue fields the formula needs, in the order a failure names them: (part, field).
# The four fields the contract requires (kv_rpm_per_volt, capacity_mah, cells, diameter_in) cannot be
# absent and are not listed.
_NEEDED_OPTIONAL = (
    ("motor", "rm_ohm"),
    ("motor", "io_no_load_a"),
    ("motor", "efficiency_pct"),
    ("motor", "max_power_w"),
    ("battery", "mass_g"),
    ("battery", "c_rate"),
    ("battery", "cell_voltage_v"),
)


def _components_of(x: Inputs) -> Components:
    """The pushed components bound to the parameter ``components``."""
    value = x["components"]
    if not isinstance(value, Components):
        msg = f"parameter 'components' must be the components, got {type(value).__name__}"
        raise TypeError(msg)
    return value


def held(value: _T | None, path: str) -> _T:
    """The value of a field ``_absent_fields`` found present.

    Raises:
        TypeError: If it is absent after all: a defect of ``_absent_fields``, never a user error.
    """
    if value is None:
        msg = f"{path} is absent although _absent_fields found it present"
        raise TypeError(msg)
    return value


def _absent_fields(components: Components) -> list[str]:
    """The parts and optional catalogue fields the formula needs that are absent, as paths."""
    parts = {
        "motor": components.motor,
        "battery": components.battery,
        "propeller": components.propeller,
    }
    absent = [f"components.{part}" for part, body in parts.items() if body is None]
    for part, name in _NEEDED_OPTIONAL:
        body = parts[part]
        if body is not None and getattr(body, name) is None:
            absent.append(f"components.{part}.{name}")
    return absent


@formula("airplane-components")
async def airplane_components(x: Inputs, ctx: Context) -> dict[str, float]:
    """Read the fitted components in the canon's units.

    ``m_bat = mass_g / 1000``, ``D_prop = diameter_in * 0.0254``, ``eta_mot = efficiency_pct / 100``,
    ``U_bat = cells * U_cell``, ``E_bat = Q_bat / 1000 * U_bat``, ``I_bat,max = C_rate * Q_bat / 1000``.

    Args:
        x: ``components``, the pushed fitted parts.
        ctx: The formula context (no warning is raised here: nothing is substituted).

    Returns:
        ``m_bat`` in kg, ``q_bat`` in mAh, ``e_bat`` in Wh, ``c_rate`` in 1/h, ``i_bat_max`` in A,
        ``u_cell`` and ``u_bat`` in V, ``k_v`` in rpm/V, ``i_0`` in A, ``r_m`` in ohm, ``eta_mot``
        as a fraction, ``p_mot_max`` in W and ``d_prop`` in m.

    Raises:
        TypeError: If ``components`` is not the components document.
        FormulaError: ``missing_input`` if a part or a field the formula reads is absent; the
            message and ``detail.inputs`` name every absent catalogue field.
    """
    del ctx  # no warning: the entry substitutes nothing in this slice
    components = _components_of(x)
    absent = _absent_fields(components)
    if absent:
        names = ", ".join(f"`{path}`" for path in absent)
        raise FormulaError(
            ErrorCategory.INVALID_INPUT,
            "missing_input",
            f"airplane-components needs {names}, which the pushed components do not carry.",
            "Push the catalogue values with the components; the kernel does not estimate them.",
            detail={"inputs": list[JsonValue](absent)},
            parameter="components",
        )
    # _absent_fields is empty: every part and every field read below is present
    motor = held(components.motor, "components.motor")
    battery = held(components.battery, "components.battery")
    propeller = held(components.propeller, "components.propeller")
    mass_g = held(battery.mass_g, "components.battery.mass_g")
    c_rate = held(battery.c_rate, "components.battery.c_rate")
    u_cell = held(battery.cell_voltage_v, "components.battery.cell_voltage_v")
    u_bat = battery.cells * u_cell
    return {
        "m_bat": mass_g / _G_PER_KG,
        "q_bat": battery.capacity_mah,
        "e_bat": battery.capacity_mah / _MAH_PER_AH * u_bat,
        "c_rate": c_rate,
        "i_bat_max": c_rate * battery.capacity_mah / _MAH_PER_AH,
        "u_cell": u_cell,
        "k_v": motor.kv_rpm_per_volt,
        "i_0": held(motor.io_no_load_a, "components.motor.io_no_load_a"),
        "r_m": held(motor.rm_ohm, "components.motor.rm_ohm"),
        "eta_mot": held(motor.efficiency_pct, "components.motor.efficiency_pct") / _PERCENT,
        "u_bat": u_bat,
        "p_mot_max": held(motor.max_power_w, "components.motor.max_power_w"),
        "d_prop": propeller.diameter_in * _M_PER_INCH,
    }
