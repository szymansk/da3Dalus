"""Control-device state of a geometry document (ARCHITECTURE ch. 8.5, 8.11).

The kernel's aircraft has every device at 0 deg (the geometry's own deflections are an editor's
state, not a design input); a configuration sets the flaps it needs. Stops are never read.
"""

from collections.abc import Callable

from aero_kernel.geometry import AirplaneGeometry, Wing, WingXSec

__all__ = [
    "CROW_AILERON_ROLES",
    "CROW_FLAP_ROLES",
    "FLAP_ROLES",
    "crow_configuration",
    "devices_at_rest",
    "flap_deflections",
    "has_flap",
    "with_flaps_at",
]

# Every control surface that acts as a flap (maintainer, 2026-10-14): flaperons too.
FLAP_ROLES = frozenset({"flap", "flaperon"})
# The devices of a butterfly layout (D10): a flap and a distinct aileron or elevon; a flaperon is
# neither, so it never counts towards crow.
CROW_FLAP_ROLES = frozenset({"flap"})
CROW_AILERON_ROLES = frozenset({"aileron", "elevon"})


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


def crow_configuration(
    airplane: AirplaneGeometry,
    mix: float,
    flap_landing_deg: float,
    flap_crow_deg: float,
    aileron_crow_up_deg: float,
) -> AirplaneGeometry:
    """Return the airplane at the crow mix ``mix`` (canon ``butterfly-approach``).

    The devices of role ``flap`` run from ``flap_landing_deg`` (mix 0) to ``flap_crow_deg`` (mix 1),
    trailing edge down. The devices of role ``aileron`` or ``elevon`` rise from 0 to
    ``aileron_crow_up_deg`` (mix 1) on both halves. A raised aileron is evaluated as the plain-flap
    contour it becomes in crow: the copy returned here carries it with the role ``flap`` and the
    negative angle, because the tools map a symmetric trailing-edge deflection of that role only.
    The copy is for evaluation, never for display. Flaperons and every other device keep their
    state (a flaperon never counts towards the butterfly layout, D10).

    Args:
        airplane: The landing configuration (flaps at the landing angle, other devices at rest).
        mix: The crow mix in [0, 1].
        flap_landing_deg: The flap angle of the landing configuration (mix 0), degrees.
        flap_crow_deg: The flap angle of full crow, degrees, trailing edge down positive.
        aileron_crow_up_deg: The aileron angle of full crow, degrees, positive for trailing edge up.

    Returns:
        A copy with the flaps and ailerons set; the same object if there is no wing.
    """
    flap = flap_landing_deg + mix * (flap_crow_deg - flap_landing_deg)
    aileron = -mix * aileron_crow_up_deg

    def at_mix(section: WingXSec) -> WingXSec:
        device = section.trailing_edge_device
        if device is None:
            return section
        if device.role in CROW_FLAP_ROLES:
            return section.model_copy(
                update={"trailing_edge_device": device.model_copy(update={"deflection_deg": flap})}
            )
        if device.role in CROW_AILERON_ROLES:
            raised = device.model_copy(update={"role": "flap", "deflection_deg": aileron})
            return section.model_copy(update={"trailing_edge_device": raised})
        return section

    return _converted(airplane, at_mix)


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
