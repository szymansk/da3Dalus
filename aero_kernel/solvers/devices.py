"""The control-device rows of the tool mapping and the refusal of what is not mapped (ARCHITECTURE ch. 8.8).

Two kinds of device reach the tools. A device acting as aileron is driven by the roll command and
deflects antisymmetrically. A deflected flap (``flap``, ``flaperon``) is part of the airplane's
configuration and deflects symmetrically, trailing edge down positive in both tools; a flaperon
carries both: its flap deflection is the symmetric bias and the roll command is applied on top.
"""

from aero_kernel.devices import FLAP_ROLES
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry, TrailingEdgeDevice, Wing, WingXSec
from aero_kernel.graph import AILERON_ROLES
from aero_kernel.schema import KernelWarning
from pydantic import BaseModel, ConfigDict

__all__ = [
    "FlapSegment",
    "RollSegment",
    "flap_segments",
    "refuse_deflected_devices",
    "roll_deflection",
    "roll_hinge_warnings",
    "roll_segments",
    "segment_label",
]


def _unmapped_deflection(
    section: WingXSec, index: int, flaps_supported: bool
) -> tuple[str, str, float] | None:
    """The label, role and angle of a deflection on this section that the consumer is not given.

    Args:
        section: The section; its device and its aerodynamic view are checked.
        index: The index of the section, naming an unnamed device.
        flaps_supported: Whether the consumer maps a deflected flap device.
    """
    device, surface = section.trailing_edge_device, section.control_surface
    if device is not None and device.deflection_deg:
        if flaps_supported and device.role in FLAP_ROLES:
            return None
        return device.name or f"device {index}", device.role, device.deflection_deg
    if surface is not None and surface.deflection:
        return surface.name, "control_surface", surface.deflection
    return None


def refuse_deflected_devices(
    airplane: AirplaneGeometry, consumer: str, *, flaps_supported: bool
) -> None:
    """Refuse an airplane with a control device off its rest position that the consumer is not given.

    A deflected flap is mapped to the tool (:func:`flap_segments`) where ``flaps_supported``; every
    other deflected device, and the aerodynamic view's ``control_surface.deflection``, is not, so
    the airplane would silently be evaluated without it. Both state fields are checked: the
    device's ``deflection_deg`` and the view's ``control_surface.deflection``.

    Args:
        airplane: The geometry with its devices as they are to be evaluated.
        consumer: The tool named in the message.
        flaps_supported: Whether the consumer maps a deflected flap device.

    Raises:
        FormulaError: ``unsupported_configuration`` naming the first deflected device and its role.
    """
    for key, wing in (airplane.wings or {}).items():
        for index, section in enumerate(wing.x_secs):
            found = _unmapped_deflection(section, index, flaps_supported)
            if found is None:
                continue
            label, role, angle = found
            raise FormulaError(
                ErrorCategory.UNSUPPORTED_CONFIGURATION,
                "unsupported_configuration",
                f"deflected control surfaces are not yet passed to {consumer}: {label!r} "
                f"(role {role}) of the wing {key!r} is at {angle} deg",
                "no value is computed for a deflected configuration rather than the clean one",
                detail={"wing": key, "device": label, "role": role},
                parameter="airplane",
            )


def segment_label(device: TrailingEdgeDevice, index: int) -> str:
    """The label of a device in messages: its name, else the index of the rib it starts on."""
    return device.name or f"device {index}"


def roll_deflection(written_side: int, delta_deg: float) -> float:
    """The deflection a tool receives for the roll command ``delta_deg`` (ch. 8.8).

    A positive command is a roll to the right: the right trailing edge goes up. The sign of the
    tool's deflection follows the side the segment is written on **to that tool**, because ASB and
    AVL both count a trailing edge down as positive (``wing.py:1619``; ``avl_doc.txt:752-753``).

    Args:
        written_side: +1 for a segment written on the positive y side, -1 for the negative one.
        delta_deg: The aileron deflection command in degrees (positive = right roll).

    Returns:
        The deflection in degrees to hand to the tool for that segment.
    """
    return -written_side * delta_deg


class RollSegment(BaseModel):
    """One segment of a stored wing that carries a roll device (ch. 8.8).

    Attributes:
        wing: Key of the wing in the document.
        index: Index of the rib the segment starts on, in stored order.
        device: Label of the device.
        role: Its role.
        hinge_root: Hinge position at the segment start as a fraction of chord.
        hinge_tip: Hinge position at the segment end (the root's when the format gives none).
        hinge: The hinge AeroBuildup is given, the mean of the two.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    wing: str
    index: int
    device: str
    role: str
    hinge_root: float
    hinge_tip: float
    hinge: float


def _checked_hinges(
    key: str, wing: Wing, index: int, device: TrailingEdgeDevice, noun: str, unmirrored_code: str
) -> RollSegment:
    """Validate a device the tools are given (mirrored surface, hinge given) and build its segment.

    Args:
        key: Key of the wing in the document.
        wing: The wing.
        index: Index of the rib the segment starts on.
        device: The device.
        noun: What the device is called in messages (``roll device`` or ``flap``).
        unmirrored_code: The error code for a device on an unmirrored wing.
    """
    label = segment_label(device, index)
    if not wing.symmetric:
        raise FormulaError(
            ErrorCategory.UNSUPPORTED_CONFIGURATION,
            unmirrored_code,
            f"the {noun} {label!r} (role {device.role}) sits on the unmirrored wing {key!r}",
            f"a {noun} is supported on a mirrored surface only",
            detail={"wing": key, "device": label, "role": device.role},
            parameter="airplane",
        )
    if device.rel_chord_root is None:
        raise FormulaError(
            ErrorCategory.INVALID_INPUT,
            "missing_hinge",
            f"the {noun} {label!r} of the wing {key!r} has no hinge position",
            "give rel_chord_root; the tool's default hinge is never used",
            detail={"wing": key, "device": label},
            parameter="airplane",
        )
    root = device.rel_chord_root
    tip = root if device.rel_chord_tip is None else device.rel_chord_tip
    return RollSegment(
        wing=key,
        index=index,
        device=label,
        role=device.role,
        hinge_root=root,
        hinge_tip=tip,
        hinge=(root + tip) / 2.0,
    )


class FlapSegment(RollSegment):
    """One segment of a stored wing that carries a deflected flap (ch. 8.8).

    Attributes:
        deflection_deg: The flap deflection in degrees, trailing edge down positive.
    """

    deflection_deg: float


def roll_segments(airplane: AirplaneGeometry) -> list[RollSegment]:
    """The segments that carry a device acting as aileron (``aileron``, ``flaperon``, ``elevon``).

    The role alone decides (ch. 8.11): ``symmetric`` and the mixing gains are not read.

    Args:
        airplane: The geometry; its devices are at rest (see :func:`refuse_deflected_devices`).

    Returns:
        The roll segments in document order.

    Raises:
        FormulaError: ``unsupported_configuration`` for a roll device on an unmirrored wing;
            ``invalid_input`` (``missing_hinge``) for one without a hinge position.
    """
    return [
        _checked_hinges(
            key,
            wing,
            index,
            section.trailing_edge_device,
            "roll device",
            "roll_device_on_unmirrored_surface",
        )
        for key, wing in (airplane.wings or {}).items()
        for index, section in enumerate(wing.x_secs)
        if section.trailing_edge_device is not None
        and section.trailing_edge_device.role in AILERON_ROLES
    ]


def flap_segments(airplane: AirplaneGeometry) -> list[FlapSegment]:
    """The segments that carry a flap (``flap``, ``flaperon``) off its rest position.

    A flap at rest, and every other role, is not mapped: the airplane the tools are given is then
    the clean one, bit for bit. The deflection is the angle itself, trailing edge down positive, on
    both halves (D9/D10: surface roles are typed, never inferred).

    Args:
        airplane: The geometry with its devices as they are to be evaluated.

    Returns:
        The deflected flap segments in document order.

    Raises:
        FormulaError: ``unsupported_configuration`` (``flap_on_unmirrored_surface``) for a flap on
            an unmirrored wing; ``invalid_input`` (``missing_hinge``) for one without a hinge.
    """
    return [
        FlapSegment(
            **_checked_hinges(
                key, wing, index, device, "flap", "flap_on_unmirrored_surface"
            ).model_dump(),
            deflection_deg=device.deflection_deg,
        )
        for key, wing in (airplane.wings or {}).items()
        for index, section in enumerate(wing.x_secs)
        if (device := section.trailing_edge_device) is not None
        and device.role in FLAP_ROLES
        and device.deflection_deg
    ]


def roll_hinge_warnings(segments: list[RollSegment]) -> list[KernelWarning]:
    """One ``hinge_line_averaged`` warning per segment whose root and tip hinge differ (ADR 0020).

    AeroBuildup holds one hinge per segment, so a tapered hinge line is replaced by the mean.
    """
    return [
        KernelWarning.of(
            "hinge_line_averaged",
            f"AeroBuildup holds one hinge per segment: the device {segment.device!r} of "
            f"{segment.wing!r} uses the mean {segment.hinge:g} of {segment.hinge_root:g} "
            f"(root) and {segment.hinge_tip:g} (tip)",
            detail={
                "wing": segment.wing,
                "device": segment.device,
                "root": segment.hinge_root,
                "tip": segment.hinge_tip,
                "used": segment.hinge,
            },
        )
        for segment in segments
        if segment.hinge_root != segment.hinge_tip
    ]
