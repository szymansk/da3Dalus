"""The refusal of a configuration with deflected control devices (ARCHITECTURE ch. 8.8)."""

from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry, TrailingEdgeDevice, Wing
from aero_kernel.graph import AILERON_ROLES
from aero_kernel.schema import KernelWarning
from pydantic import BaseModel, ConfigDict

__all__ = [
    "RollSegment",
    "refuse_deflected_devices",
    "roll_deflection",
    "roll_hinge_warnings",
    "roll_segments",
    "segment_label",
]


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
        side: +1 if the segment is stored on the positive y side, -1 on the negative one.
        hinge_root: Hinge position at the segment start as a fraction of chord.
        hinge_tip: Hinge position at the segment end (the root's when the format gives none).
        hinge: The hinge AeroBuildup is given, the mean of the two.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    wing: str
    index: int
    device: str
    role: str
    side: int
    hinge_root: float
    hinge_tip: float
    hinge: float


def _side(wing: Wing, index: int, key: str) -> int:
    """The side of y a stored segment lies on: the sign of the sum of its end ribs' y."""
    total = wing.x_secs[index].xyz_le[1] + wing.x_secs[index + 1].xyz_le[1]
    if total == 0.0:
        raise FormulaError(
            ErrorCategory.UNSUPPORTED_CONFIGURATION,
            "unsupported_layout",
            f"the roll device of the wing {key!r} starting on rib {index} lies in the plane y = 0",
            "a roll device needs a side of the centre plane",
            detail={"wing": key},
            parameter="airplane",
        )
    return 1 if total > 0.0 else -1


def _roll_segment(key: str, wing: Wing, index: int, device: TrailingEdgeDevice) -> RollSegment:
    """Validate one roll device and build its segment."""
    label = segment_label(device, index)
    if not wing.symmetric:
        raise FormulaError(
            ErrorCategory.UNSUPPORTED_CONFIGURATION,
            "roll_device_on_unmirrored_surface",
            f"the roll device {label!r} (role {device.role}) sits on the unmirrored wing {key!r}",
            "a roll device is supported on a mirrored surface only",
            detail={"wing": key, "device": label, "role": device.role},
            parameter="airplane",
        )
    if device.rel_chord_root is None:
        raise FormulaError(
            ErrorCategory.INVALID_INPUT,
            "missing_hinge",
            f"the roll device {label!r} of the wing {key!r} has no hinge position",
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
        side=_side(wing, index, key),
        hinge_root=root,
        hinge_tip=tip,
        hinge=(root + tip) / 2.0,
    )


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
        _roll_segment(key, wing, index, section.trailing_edge_device)
        for key, wing in (airplane.wings or {}).items()
        for index, section in enumerate(wing.x_secs)
        if section.trailing_edge_device is not None
        and section.trailing_edge_device.role in AILERON_ROLES
    ]


def roll_hinge_warnings(segments: list[RollSegment]) -> list[KernelWarning]:
    """One ``hinge_line_averaged`` warning per segment whose root and tip hinge differ (ADR 0020).

    AeroBuildup holds one hinge per segment, so a tapered hinge line is replaced by the mean.
    """
    return [
        KernelWarning.of(
            "hinge_line_averaged",
            f"AeroBuildup holds one hinge per segment: the roll device {segment.device!r} of "
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
