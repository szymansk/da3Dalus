"""Canon formula ``airplane-configuration``: the airplane with its flaps set (ARCHITECTURE ch. 8.5)."""

from aero_kernel.context import Context, Inputs
from aero_kernel.devices import has_flap, with_flaps_at
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.values import airplane_of
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.registry import formula

__all__ = ["airplane_configuration"]


@formula("airplane-configuration")
async def airplane_configuration(x: Inputs, ctx: Context) -> dict[str, AirplaneGeometry]:
    """The airplane in its take-off or landing configuration.

    Four cases (canon table): without flaps and without a deflection the airplane itself, no
    warning (the canon's own definition, not a fallback); without flaps but with a deflection the
    airplane itself and the ``deflection_without_flap`` warning (a supplied value is not used);
    with flaps and a deflection every flap device set to it exactly, also beyond the stop; with
    flaps and no deflection no value.

    Args:
        x: ``airplane`` the geometry (devices at rest), ``flap_deflection`` in degrees or ``None``.
        ctx: The formula context.

    Returns:
        ``airplane_cfg`` the configured geometry (canon quantity ``airplane-takeoff`` or
        ``airplane-landing``).

    Raises:
        TypeError: If ``airplane`` is not the geometry or ``flap_deflection`` not a number.
        FormulaError: ``invalid_input`` (``missing_input``) for an airplane with flaps and no
            deflection.
    """
    airplane = airplane_of(x)
    deflection = x["flap_deflection"]
    if deflection is not None and not isinstance(deflection, float):
        msg = f"parameter 'flap_deflection' must be a number, got {type(deflection).__name__}"
        raise TypeError(msg)
    if not has_flap(airplane):
        if deflection is not None:
            ctx.warn(
                "deflection_without_flap",
                f"The airplane has no flap, so the supplied flap deflection of {deflection} deg is not used.",
                {"flap_deflection_deg": deflection},
            )
        return {"airplane_cfg": airplane}
    if deflection is None:
        raise FormulaError(
            ErrorCategory.INVALID_INPUT,
            "missing_input",
            "the airplane has flaps but no flap deflection was given for this configuration",
            "supply the flap deflection of the configuration in deg",
            parameter="flap_deflection",
        )
    return {"airplane_cfg": with_flaps_at(airplane, deflection)}
