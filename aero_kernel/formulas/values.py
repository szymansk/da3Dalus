"""Reading ``x`` inside a formula (ARCHITECTURE ch. 8.12)."""

from aero_kernel.context import Inputs

__all__ = ["number"]


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
