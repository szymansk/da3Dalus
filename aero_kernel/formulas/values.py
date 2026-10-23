"""Reading ``x`` inside a formula (ARCHITECTURE ch. 8.12)."""

from aero_kernel.context import Context, Inputs
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.schema import KernelWarning
from aero_kernel.solvers.air import AirState

__all__ = ["air_state", "airplane", "forward_warnings", "number"]


def number(x: Inputs, name: str) -> float:
    """Return the scalar bound to a parameter.

    The engine binds every non-optional parameter before it calls a formula, and the parameters
    of this slice are scalars; anything else is a defect of the engine or of the model.

    Args:
        x: The formula inputs.
        name: The parameter name.

    Returns:
        The value as a float.

    Raises:
        TypeError: If the parameter is ``None`` (an absent optional) or not a number.
        KeyError: If the formula has no such parameter.
    """
    value = x[name]
    if not isinstance(value, float):
        msg = f"parameter {name!r} must be a number, got {type(value).__name__}"
        raise TypeError(msg)
    return value


def airplane(x: Inputs) -> AirplaneGeometry:
    """Return the geometry bound to the parameter ``airplane``.

    Raises:
        TypeError: If it is not the geometry document.
    """
    value = x["airplane"]
    if not isinstance(value, AirplaneGeometry):
        msg = f"parameter 'airplane' must be the geometry, got {type(value).__name__}"
        raise TypeError(msg)
    return value


def air_state(x: Inputs) -> AirState:
    """The ISA air state of the bound ``rho`` (kg/m^3), ``mu`` (Pa s) and ``a`` (m/s)."""
    return AirState(
        density=number(x, "rho"),
        dynamic_viscosity=number(x, "mu"),
        speed_of_sound=number(x, "a"),
    )


def forward_warnings(ctx: Context, warnings: tuple[KernelWarning, ...]) -> None:
    """Report the caveats an adapter returned (without origin) as the formula's own warnings."""
    for warning in warnings:
        ctx.warn(warning.code, warning.message, warning.detail)
