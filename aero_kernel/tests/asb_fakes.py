"""A fake ``aerosandbox`` that records how the geometry conversion builds its objects."""

import importlib.machinery
import math
import sys
import types
from itertools import pairwise
from typing import Any

import pytest
from aero_kernel.geometry import AirplaneGeometry, Wing
from aero_kernel.geometry_properties import MainWingProperties, SurfaceProperties
from aero_kernel.surface_chain import ChainPoint, oriented_chain
from aero_kernel.tests.planform_stand_in import stand_in_surface_properties

# ``Any``: the fake stands in for an untyped third-party module; keyword arguments are recorded
# exactly as passed.


class FakeAirfoil:
    """Records ``asb.Airfoil(name=..., coordinates=...)``."""

    def __init__(self, name: str | None = None, coordinates: Any = None) -> None:
        self.name = name
        self.coordinates = coordinates

    def add_control_surface(
        self, deflection: float = 0.0, hinge_point_x: float = 0.75
    ) -> "FakeAirfoil":
        """The deflected contour, recorded: ``coordinates`` says which contour, angle and hinge."""
        return FakeAirfoil(
            name=self.name, coordinates=("deflected", self.name, deflection, hinge_point_x)
        )


class FakeWingXSec:
    """Records ``asb.WingXSec(...)``."""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.xyz_le = kwargs.get("xyz_le")


class FakeControlSurface:
    """Records ``asb.ControlSurface(...)``."""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs


# (area, span, mean aerodynamic chord) the fake wing reports by name; any other name gets the default.
FAKE_REFERENCE: dict[str, tuple[float, float, float]] = {
    "Main": (0.31, 1.7, 0.21),
    "Fin": (0.07, 0.4, 0.08),
}
# x of the aerodynamic centre the fake wing reports by name.
FAKE_AC_X: dict[str, float] = {"Main": 0.12, "Fin": 0.55}
FAKE_DEFAULT_REFERENCE = (1.0, 2.0, 0.5)
# Without the centreline distance the span is this much shorter, and the area this much smaller.
FAKE_CENTRELINE_GAP = 0.1
FAKE_CENTRELINE_AREA = 0.02


class FakeWing:
    """Records ``asb.Wing(...)`` and reports the reference values of :data:`FAKE_REFERENCE`."""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.name = kwargs.get("name")
        self.symmetric = kwargs.get("symmetric")
        self.xsecs = kwargs.get("xsecs")
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def _reference(self) -> tuple[float, float, float]:
        return FAKE_REFERENCE.get(str(self.name), FAKE_DEFAULT_REFERENCE)

    def area(self, *, type: str, include_centerline_distance: bool) -> float:  # noqa: A002
        """The area; both arguments are required, so a call that relies on ASB's defaults fails."""
        self.calls.append(
            ("area", {"type": type, "include_centerline_distance": include_centerline_distance})
        )
        extra = FAKE_CENTRELINE_AREA if include_centerline_distance else 0.0
        return self._reference()[0] + extra

    def span(self, *, type: str, include_centerline_distance: bool) -> float:  # noqa: A002
        """The span; both arguments are required, so a call that relies on ASB's defaults fails."""
        self.calls.append(
            ("span", {"type": type, "include_centerline_distance": include_centerline_distance})
        )
        gap = FAKE_CENTRELINE_GAP if include_centerline_distance else 0.0
        return self._reference()[1] + gap

    def aerodynamic_center(self, **options: Any) -> list[float]:
        """The aerodynamic centre: x from :data:`FAKE_AC_X`, on the centreline."""
        self.calls.append(("aerodynamic_center", options))
        return [FAKE_AC_X.get(str(self.name), 0.1), 0.0, 0.0]

    def mean_aerodynamic_chord(self, **options: Any) -> float:
        """The mean aerodynamic chord."""
        self.calls.append(("mean_aerodynamic_chord", options))
        return self._reference()[2]


class FakeFuselageXSec:
    """Records ``asb.FuselageXSec(...)``."""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs


class FakeFuselage:
    """Records ``asb.Fuselage(...)``."""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs


class FakeAirplane:
    """Records ``asb.Airplane(...)``."""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs


def install_fake_aerosandbox(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    """Put a fake ``aerosandbox`` into ``sys.modules`` that ``find_spec`` can see."""
    module = types.ModuleType("aerosandbox")
    module.__spec__ = importlib.machinery.ModuleSpec("aerosandbox", None)
    module.Airfoil = FakeAirfoil  # pyright: ignore[reportAttributeAccessIssue]  # fake module
    module.WingXSec = FakeWingXSec  # pyright: ignore[reportAttributeAccessIssue]
    module.ControlSurface = FakeControlSurface  # pyright: ignore[reportAttributeAccessIssue]
    module.Wing = FakeWing  # pyright: ignore[reportAttributeAccessIssue]
    module.FuselageXSec = FakeFuselageXSec  # pyright: ignore[reportAttributeAccessIssue]
    module.Fuselage = FakeFuselage  # pyright: ignore[reportAttributeAccessIssue]
    module.Airplane = FakeAirplane  # pyright: ignore[reportAttributeAccessIssue]
    monkeypatch.setitem(sys.modules, "aerosandbox", module)
    return module


def stand_in_main_wing_properties(airplane: AirplaneGeometry) -> MainWingProperties:
    """The reference values without AeroSandbox, for fast tests that need consistent numbers only.

    Taken from the kernel's own planform integration of the main wing; these are not AeroSandbox's
    values (the aero tier compares those), only a deterministic stand-in at the solver boundary.
    """
    (main,) = [w for w in (airplane.wings or {}).values() if w.surface_type == "main_wing"]
    surface = stand_in_surface_properties(main)
    return MainWingProperties(s_ref=surface.area, b_ref=surface.span, c_mac=surface.c_mac)


def stand_in_surface_of(airplane: AirplaneGeometry, key: str) -> SurfaceProperties:
    """The stand-in planform values of the wing under ``key`` (see :mod:`planform_stand_in`)."""
    return stand_in_surface_properties((airplane.wings or {})[key])


def stand_in_quarter_chord_x(wing: Wing) -> float:
    """x of the quarter-chord MAC of a wing without AeroSandbox, by ASB's own formula.

    Per panel (ASB, ``Wing.aerodynamic_center``): taper ratio ``l``, ``c_MAC = 2/3 c1 (1 + l + l^2) /
    (1 + l)``, MAC leading edge at ``x1 + (x2 - x1) (1 + 2 l) / (3 + 3 l)``, centre at a quarter of the
    panel MAC behind it, panels weighted by their (here: y-z) area. A stand-in for the fast tier.
    """
    chain = (
        oriented_chain(wing, 1)
        if wing.symmetric
        else [
            ChainPoint(
                x=s.xyz_le[0],
                y=s.xyz_le[1],
                z=s.xyz_le[2],
                chord=s.chord,
                twist=s.twist,
                airfoil=s.airfoil,
            )
            for s in wing.x_secs
        ]
    )
    total = moment = 0.0
    for a, b in pairwise(chain):
        taper = b.chord / a.chord
        mac = (2.0 / 3.0) * a.chord * (1.0 + taper + taper**2) / (1.0 + taper)
        mac_le = a.x + (b.x - a.x) * (1.0 + 2.0 * taper) / (3.0 + 3.0 * taper)
        area = (a.chord + b.chord) / 2.0 * math.hypot(b.y - a.y, b.z - a.z)
        total += area
        moment += area * (mac_le + 0.25 * mac)
    return moment / total


def stand_in_fin_area(wing: Wing) -> float:
    """The fin area of a surface without AeroSandbox: true area of the lofted panels, a V-tail's fin share.

    Per panel ``(c1 + c2) / 2`` times the panel's length in the y-z plane; a mirrored surface counts
    both halves; a ``v_tail`` weights each panel by ``sin^2`` of its angle to the horizontal. A stand-in
    for the fast tier (the real value is ASB's ``Wing.area(type="planform",
    include_centerline_distance=False)``, compared in the aero tier).
    """
    axis = 1 if wing.symmetric else 2
    chain = oriented_chain(wing, axis)
    total = 0.0
    for a, b in pairwise(chain):
        run, rise = b.y - a.y, b.z - a.z
        panel = (a.chord + b.chord) / 2.0 * math.hypot(run, rise)
        total += panel * (rise**2 / (run**2 + rise**2) if wing.surface_type == "v_tail" else 1.0)
    return total * (2.0 if wing.symmetric else 1.0)


def stand_in_horizontal_tail_area(wing: Wing) -> float:
    """The gross planform area of a horizontal tail without AeroSandbox, from the stand-in planform.

    A stand-in for the fast tier (the real value is ASB's ``Wing.area(type="planform",
    include_centerline_distance=True)``, compared in the aero tier).
    """
    return stand_in_surface_properties(wing).area
