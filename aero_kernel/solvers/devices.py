"""The refusal of a configuration with deflected control devices (ARCHITECTURE ch. 8.8)."""

from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry

__all__ = ["refuse_deflected_devices"]


def refuse_deflected_devices(airplane: AirplaneGeometry, consumer: str) -> None:
    """Refuse an airplane with a control device off its rest position.

    The consumer (AeroBuildup, AVL) is not given the devices yet, so a deflected airplane would
    silently be evaluated as the clean one. Both state fields the conversions drop are checked: the device's ``deflection_deg`` and the
    aerodynamic view's ``control_surface.deflection``.

    Args:
        airplane: The geometry with its devices as they are to be evaluated.
        consumer: The tool named in the message.

    Raises:
        FormulaError: ``unsupported_configuration`` naming the first deflected device and its role.
    """
    for key, wing in (airplane.wings or {}).items():
        for index, section in enumerate(wing.x_secs):
            device, surface = section.trailing_edge_device, section.control_surface
            if device is not None and device.deflection_deg:
                label, role, angle = (
                    device.name or f"device {index}",
                    device.role,
                    device.deflection_deg,
                )
            elif surface is not None and surface.deflection:
                label, role, angle = surface.name, "control_surface", surface.deflection
            else:
                continue
            raise FormulaError(
                ErrorCategory.UNSUPPORTED_CONFIGURATION,
                "unsupported_configuration",
                f"deflected control surfaces are not yet passed to {consumer}: {label!r} "
                f"(role {role}) of the wing {key!r} is at {angle} deg",
                "no value is computed for a deflected configuration rather than the clean one",
                detail={"wing": key, "device": label, "role": role},
                parameter="airplane",
            )
