"""Control-device state of a geometry document (ARCHITECTURE ch. 8.5, 8.11).

The kernel's aircraft has every device at 0 deg (the geometry's own deflections are an editor's
state, not a design input); a configuration sets the flaps it needs. Stops are never read.
"""

from collections.abc import Callable

from aero_kernel.geometry import AirplaneGeometry, Wing, WingXSec

__all__ = ["FLAP_ROLES", "devices_at_rest", "flap_deflections", "has_flap", "with_flaps_at"]

# Every control surface that acts as a flap (maintainer, 2026-10-14): flaperons too.
FLAP_ROLES = frozenset({"flap", "flaperon"})


def _converted(
    airplane: AirplaneGeometry, convert: Callable[[WingXSec], WingXSec]
) -> AirplaneGeometry:
    """The airplane with ``convert`` applied to every section of every wing."""
    if not airplane.wings:
        return airplane
    wings: dict[str, Wing] = {
        key: wing.model_copy(update={"x_secs": tuple(convert(s) for s in wing.x_secs)})
        for key, wing in airplane.wings.items()
    }
    return airplane.model_copy(update={"wings": wings})


def devices_at_rest(airplane: AirplaneGeometry) -> AirplaneGeometry:
    """Return the airplane with every device at 0 deg.

    Both state fields, ``trailing_edge_device.deflection_deg`` and ``control_surface.deflection``,
    are zeroed; stops and everything else are kept (ch. 8.11).

    Args:
        airplane: The supplied geometry.

    Returns:
        A copy with the devices at rest (the same object if it has no wings).
    """

    def at_rest(section: WingXSec) -> WingXSec:
        update: dict[str, object] = {}
        if section.trailing_edge_device is not None:
            update["trailing_edge_device"] = section.trailing_edge_device.model_copy(
                update={"deflection_deg": 0.0}
            )
        if section.control_surface is not None:
            update["control_surface"] = section.control_surface.model_copy(
                update={"deflection": 0.0}
            )
        return section.model_copy(update=update)

    return _converted(airplane, at_rest)


def has_flap(airplane: AirplaneGeometry) -> bool:
    """Whether some device acts as a flap (role ``flap`` or ``flaperon``)."""
    return any(
        section.trailing_edge_device is not None and section.trailing_edge_device.role in FLAP_ROLES
        for wing in (airplane.wings or {}).values()
        for section in wing.x_secs
    )


def with_flaps_at(airplane: AirplaneGeometry, deflection_deg: float) -> AirplaneGeometry:
    """Return the airplane with every flap device at ``deflection_deg``, exactly.

    Also beyond the device's stop (the stop is never read, ch. 8.11). Other devices keep their
    state.

    Args:
        airplane: The geometry, devices at rest.
        deflection_deg: The flap deflection in degrees, in the geometry's sign convention.

    Returns:
        A copy with the flaps set; the same object if there is no flap.
    """

    def flapped(section: WingXSec) -> WingXSec:
        device = section.trailing_edge_device
        if device is None or device.role not in FLAP_ROLES:
            return section
        return section.model_copy(
            update={
                "trailing_edge_device": device.model_copy(update={"deflection_deg": deflection_deg})
            }
        )

    return _converted(airplane, flapped) if has_flap(airplane) else airplane


def flap_deflections(airplane: AirplaneGeometry) -> list[tuple[str, str, float]]:
    """The flaps off their rest position as ``(wing key, device label, deflection in deg)``.

    Args:
        airplane: The geometry with its devices as they are to be evaluated.

    Returns:
        One entry per flap segment in document order; empty for an airplane at rest.
    """
    return [
        (key, device.name or f"device {index}", device.deflection_deg)
        for key, wing in (airplane.wings or {}).items()
        for index, section in enumerate(wing.x_secs)
        if (device := section.trailing_edge_device) is not None
        and device.role in FLAP_ROLES
        and device.deflection_deg
    ]
