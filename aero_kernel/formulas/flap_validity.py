"""The verdict declarations of a flapped result: confidence and deflection (ADR 0020, rule ``flap-model-validity``)."""

from aero_kernel.context import Context
from aero_kernel.devices import flap_deflections
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.solvers.opti import DeflectionDiagnostics

__all__ = ["warn_flap_validity"]

RULE = "flap-model-validity"


def warn_flap_validity(
    ctx: Context, airplane: AirplaneGeometry, found: DeflectionDiagnostics | None
) -> None:
    """Declare a flapped result that lies outside the model's trusted range (``defect`` warnings).

    The value is computed and returned; the declaration carries the value and the threshold. Without
    a deflected flap nothing is read and nothing is declared.

    Args:
        ctx: The formula context.
        airplane: The configured airplane the result was computed on.
        found: NeuralFoil's confidence at the solution, or ``None`` where no recording run was made
            (the AVL world).
    """
    flaps = flap_deflections(airplane)
    if not flaps:
        return
    rules = ctx.solvers.rules
    limit = rules.value(RULE, "max_flap_deflection")
    beyond = [
        {"wing": wing, "device": device, "deflection_deg": angle}
        for wing, device, angle in flaps
        if abs(angle) > limit
    ]
    if beyond:
        ctx.warn(
            "flap_deflection_beyond_validity",
            f"A flap deflection is above {limit:g} deg: a plain flap separates above about 40 deg "
            "and earlier at low Reynolds number, which the model does not contain. The value is "
            "computed at the given angle.",
            {"limit_deg": limit, "flaps": beyond},  # pyright: ignore[reportArgumentType]
        )
    if found is None:
        return
    floor = rules.value(RULE, "min_confidence")
    if found.min_confidence < floor:
        ctx.warn(
            "flap_confidence_low",
            f"NeuralFoil's analysis confidence of a section at the solution is "
            f"{found.min_confidence:.3g}, below {floor:g}: the flapped contour lies outside what "
            "the net was trained on. The value is computed; validate it with another method.",
            {
                "min_confidence": found.min_confidence,
                "threshold": floor,
                "wing": found.min_confidence_wing,
            },
        )
