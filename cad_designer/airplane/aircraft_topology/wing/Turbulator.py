from typing import Literal, Optional

from cad_designer.airplane.types import Factor

TurbulatorForm = Literal["zigzag", "dots", "thread"]


class Turbulator:
    """Represents an optional upper-surface turbulator strip on a wing segment.

    Turbulators trip the boundary layer to delay separation and reduce drag at
    low Reynolds numbers. One turbulator per segment, upper surface only.

    Attributes:
        form: Build form — "zigzag" tape, "dots", or adhesive "thread".
        height_mm: Strip/thread height in mm.
        position_root: Chordwise x/c position (0–1) at segment root.
        position_tip: Chordwise x/c position (0–1) at segment tip; mirrors
            position_root when not specified explicitly.
        enabled: Whether the turbulator is active (for CAD output).
    """

    def __init__(
        self,
        position_root: Factor,
        form: TurbulatorForm = "zigzag",
        height_mm: float = 0.3,
        position_tip: Optional[Factor] = None,
        enabled: bool = True,
    ) -> None:
        """Initialise a Turbulator instance.

        Args:
            position_root: Chordwise x/c position (0–1) at segment root.
            form: Build form — ``"zigzag"``, ``"dots"``, or ``"thread"``.
            height_mm: Strip/thread height in mm (non-negative).
            position_tip: Chordwise x/c position at segment tip; defaults to
                ``position_root`` when ``None`` (flat strip, no taper).
            enabled: Whether the turbulator is rendered in CAD output.
        """
        self.form: TurbulatorForm = form
        self.height_mm: float = height_mm
        self.position_root: Factor = position_root
        self.position_tip: Factor = position_tip if position_tip is not None else position_root
        self.enabled: bool = enabled

    def __repr__(self) -> str:
        from pprint import pformat

        return pformat(vars(self), indent=4, width=1)

    def __getstate__(self) -> dict:
        """Return a dictionary of serialisable attributes for JSON serialisation."""
        return {
            "form": self.form,
            "height_mm": self.height_mm,
            "position_root": self.position_root,
            "position_tip": self.position_tip,
            "enabled": self.enabled,
        }

    @staticmethod
    def from_json_dict(data: dict) -> "Turbulator":
        """Create a Turbulator from a JSON dictionary.

        Args:
            data: Dictionary containing Turbulator field values.

        Returns:
            A new Turbulator instance.
        """
        position_root = data.get("position_root", 0.1)
        return Turbulator(
            form=data.get("form", "zigzag"),
            height_mm=data.get("height_mm", 0.3),
            position_root=position_root,
            position_tip=data.get("position_tip"),  # None → defaults to position_root in __init__
            enabled=data.get("enabled", True),
        )
