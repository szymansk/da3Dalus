"""Containers of the planform values AeroSandbox measures (ARCHITECTURE ch. 8.5, 8.8).

The values are AeroSandbox's (``solvers.asb_airplane``); nothing is integrated here (gh-1240, gh-1253).
"""

from pydantic import BaseModel, ConfigDict

__all__ = ["MainWingProperties", "SurfaceProperties"]


class MainWingProperties(BaseModel):
    """The reference values of the main wing, as AeroSandbox measures them.

    Attributes:
        s_ref: Reference area in m^2 (canon quantity ``wing-reference-area``).
        b_ref: Reference span in m (``wing-span``).
        c_mac: Mean aerodynamic chord in m (``mean-aerodynamic-chord``).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    s_ref: float
    b_ref: float
    c_mac: float


class SurfaceProperties(BaseModel):
    """Area, span, aspect ratio and mean aerodynamic chord of one surface, as AeroSandbox measures them.

    Attributes:
        area: ``Wing.area(type="planform", include_centerline_distance=True)`` in m^2.
        span: ``Wing.span(type="yz", include_centerline_distance=True)`` in m.
        aspect_ratio: ``span^2 / area`` (the decision of gh-1253: derived from the two ASB values).
        c_mac: ``Wing.mean_aerodynamic_chord()`` in m.
        x_le_mac: x of the leading edge of the mean aerodynamic chord in m, in the geometry frame,
            aft positive: ``x_AC - 0.25 c_MAC`` with ``x_AC`` from ``Wing.aerodynamic_center()``.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    area: float
    span: float
    aspect_ratio: float
    c_mac: float
    x_le_mac: float
