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
    """Declare a flapped result that lies outside the model's trusted range (``warning`` severity).

    The value is computed and returned; the declaration carries the value and the threshold. Without
    a deflected flap nothing is read and nothing is declared. The confidence is judged per deflected
    device (each deflected flap, and a driven aileron of the roll): the area-weighted mean of
    NeuralFoil's ``analysis_confidence`` over the sections the device spans, against the rule's
    ``min_confidence`` (#1342); one warning per device below it, with where and how much.

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
    for device in found.devices:
        mean = device.mean_confidence()
        if mean >= floor:
            continue
        lowest = device.lowest()
        share = device.span_share_below(floor)
        ctx.warn(
            "flap_confidence_low",
            f"NeuralFoil's analysis confidence over the span of the device {device.device!r} of "
            f"the wing {device.wing!r} is {mean:.3g} (area-weighted), below {floor:g}: "
            f"{share:.0%} of its span lies below, the lowest section {lowest.confidence:.3g}. The "
            "deflected contour lies outside what the net was trained on. The value is computed; "
            "validate it with another method.",
            {
                "wing": device.wing,
                "device": device.device,
                "mean_confidence": mean,
                "threshold": floor,
                "span_share_below_threshold": share,
                "min_confidence": lowest.confidence,
                "min_confidence_at_m": list(lowest.at_m),
            },
        )
