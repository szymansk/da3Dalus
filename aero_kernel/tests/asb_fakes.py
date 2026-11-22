"""Fakes of ``aerosandbox`` that record what the kernel hands to it.

Two groups: the geometry fakes record how the conversion builds its objects
(:func:`install_fake_aerosandbox`); the optimiser fakes record the problem a worker states
(:class:`RecordingBoundary`: variables with their bounds, constraints, objective, operating points),
so a test compares what went to the solver instead of the fake's own return.
"""

import importlib.machinery
import math
import sys
import types
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
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
        self.chord = kwargs.get("chord")
        self.twist = kwargs.get("twist")
        self.airfoil = kwargs.get("airfoil")


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
    """The stand-in planform values of the wing under ``key`` (see :mod:`planform_stand_in`).

    A ``v_tail`` is the horizontal tail of the neutral point with its effective area and its true
    panel aspect ratio (:func:`stand_in_v_tail_surface`).
    """
    wing = (airplane.wings or {})[key]
    if wing.surface_type == "v_tail":
        return stand_in_v_tail_surface(wing)
    return stand_in_surface_properties(wing)


def stand_in_quarter_chord_x(wing: Wing) -> float:
    """x of the quarter-chord MAC of a wing without AeroSandbox, by ASB's own formula.

    See :func:`stand_in_mac_and_centre`.
    """
    return stand_in_mac_and_centre(wing)[1]


def stand_in_mac_and_centre(wing: Wing) -> tuple[float, float]:
    """``(c_MAC, x_AC)`` of a wing without AeroSandbox, by ASB's own formula.

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
    total = moment = mac_sum = 0.0
    for a, b in pairwise(chain):
        taper = b.chord / a.chord
        mac = (2.0 / 3.0) * a.chord * (1.0 + taper + taper**2) / (1.0 + taper)
        mac_le = a.x + (b.x - a.x) * (1.0 + 2.0 * taper) / (3.0 + 3.0 * taper)
        area = (a.chord + b.chord) / 2.0 * math.hypot(b.y - a.y, b.z - a.z)
        total += area
        moment += area * (mac_le + 0.25 * mac)
        mac_sum += area * mac
    return mac_sum / total, moment / total


def _v_tail_halves(wing: Wing) -> tuple[float, float, float]:
    """``(S_h,eff, S_true, b_true)`` of one half of a V-tail, the root carried to the centreline (#1208)."""
    chain = oriented_chain(wing, 1 if wing.symmetric else 2)
    effective = true_area = span = 0.0
    root, neighbour = chain[0], chain[1]
    if wing.symmetric and root.y > 0.0 and abs(neighbour.y - root.y) > 0.0:
        # the root carried to the centreline at the root panel's angle, with the root chord
        slope = (neighbour.z - root.z) / (neighbour.y - root.y)
        length = math.hypot(root.y, slope * root.y)
        extension = root.chord * length
        true_area += extension
        span += length
        effective += extension * root.y**2 / (root.y**2 + (slope * root.y) ** 2)
    for a, b in pairwise(chain):
        run, rise = b.y - a.y, b.z - a.z
        length = math.hypot(run, rise)
        panel = (a.chord + b.chord) / 2.0 * length
        true_area += panel
        span += length
        effective += panel * run**2 / (run**2 + rise**2)
    return effective, true_area, span


def stand_in_v_tail_surface(wing: Wing) -> SurfaceProperties:
    """A V-tail as the horizontal tail without AeroSandbox: ``S_h,eff = sum S_i cos^2(nu_i)``, true panel AR.

    Per panel the true area ``(c1 + c2) / 2`` times the panel length in the y-z plane and the true
    length itself, with the root carried to the centreline at the root panel's angle; the aspect ratio
    is the developed one, (both halves' developed span)^2 / (both halves' true area). The MAC and its
    centre are :func:`stand_in_mac_and_centre`. A stand-in for the fast tier (the real values are ASB's,
    compared in the aero tier).
    """
    effective, true_area, span = _v_tail_halves(wing)
    mirrored = 2.0 if wing.symmetric else 1.0
    c_mac, centre = stand_in_mac_and_centre(wing)
    return SurfaceProperties(
        area=mirrored * effective,
        span=mirrored * span,
        aspect_ratio=mirrored * span**2 / true_area,
        c_mac=c_mac,
        x_le_mac=centre - 0.25 * c_mac,
    )


def stand_in_fin_area(wing: Wing) -> float:
    """The fin area of a surface without AeroSandbox: true area of the lofted panels, a V-tail's fin share.

    Per panel ``(c1 + c2) / 2`` times the panel's length in the y-z plane; a mirrored surface counts
    both halves; a ``v_tail`` is the sum of its panels' areas times ``sin^2`` of the panel angle to the
    horizontal, with the root carried to the centreline. A stand-in for the fast tier (the real value is
    ASB's ``Wing.area(type="planform", include_centerline_distance=False)``, compared in the aero tier).
    """
    mirrored = 2.0 if wing.symmetric else 1.0
    if wing.surface_type == "v_tail":
        effective, true_area, _span = _v_tail_halves(wing)
        return mirrored * (true_area - effective)
    chain = oriented_chain(wing, 1 if wing.symmetric else 2)
    total = sum(
        (a.chord + b.chord) / 2.0 * math.hypot(b.y - a.y, b.z - a.z) for a, b in pairwise(chain)
    )
    return total * mirrored


def stand_in_horizontal_tail_area(wing: Wing) -> float:
    """The gross planform area of a horizontal tail without AeroSandbox, from the stand-in planform.

    For a ``v_tail`` the effective area ``S_h,eff = sum S_i cos^2(nu_i)``.

    A stand-in for the fast tier (the real value is ASB's ``Wing.area(type="planform",
    include_centerline_distance=True)``, compared in the aero tier).
    """
    if wing.surface_type == "v_tail":
        return stand_in_v_tail_surface(wing).area
    return stand_in_surface_properties(wing).area


# --- the optimiser boundary: what a worker states to ``asb.Opti`` ----------------------------------


class RecordedExpression:
    """A symbolic expression of the faked optimiser: how it was built, and its value at the optimum.

    Arithmetic builds a new expression that keeps its operands; ``==`` builds a
    :class:`RecordedConstraint`, as a CasADi expression does.

    Attributes:
        name: The expression in text, e.g. ``"speed"`` or ``"(D_profile+0.9*D_induced)*speed"``.
        value: Its value at the faked optimum.
        operator: ``"*"`` or ``"+"`` of a compound expression, ``""`` of a leaf (variable or output).
        operands: The two operands of a compound expression, in order; empty for a leaf.
    """

    def __init__(
        self,
        name: str,
        value: float = 0.0,
        operator: str = "",
        operands: "tuple[RecordedExpression | float, ...]" = (),
    ) -> None:
        self.name = name
        self.value = value
        self.operator = operator
        self.operands = operands

    # CasADi's ``==`` returns a constraint, not a bool; the fake mirrors that so the constraint a
    # worker builds with ``aero["L"] == lift`` can be recorded.
    def __eq__(self, other: object) -> "RecordedConstraint":  # pyright: ignore[reportIncompatibleMethodOverride]
        return RecordedConstraint(left=self, right=other)

    __hash__ = object.__hash__

    def __mul__(self, other: "RecordedExpression | float") -> "RecordedExpression":
        if isinstance(other, RecordedExpression):
            return RecordedExpression(
                f"{self.name}*{other.name}", self.value * other.value, "*", (self, other)
            )
        return RecordedExpression(f"{self.name}*{other}", self.value * other, "*", (self, other))

    def __rmul__(self, other: float) -> "RecordedExpression":
        return RecordedExpression(f"{other}*{self.name}", other * self.value, "*", (other, self))

    def __add__(self, other: "RecordedExpression") -> "RecordedExpression":
        return RecordedExpression(
            f"({self.name}+{other.name})", self.value + other.value, "+", (self, other)
        )


@dataclass(frozen=True, eq=False)
class RecordedConstraint:
    """An equality constraint ``left == right`` as the worker built it.

    Attributes:
        left: The expression on the left.
        right: What it is set equal to, exactly as the worker passed it (a number, or another
            expression).
    """

    left: RecordedExpression
    right: Any


class RecordingOpti:
    """A fake ``asb.Opti`` that records the problem and 'solves' it to given values.

    Attributes:
        variables: The keyword arguments of each ``variable(...)`` call (``init_guess``,
            ``lower_bound``, ``upper_bound``) by the variable's name.
        constraints: Every argument of ``subject_to``, in order.
        objectives: Every argument of ``minimize``, in order.
        solve_options: The keyword arguments of each ``solve(...)`` call.
    """

    def __init__(
        self,
        names: Sequence[str],
        optimum: Mapping[str, float],
        error: Exception | None = None,
        on_minimize: Callable[[RecordedExpression], None] | None = None,
    ) -> None:
        """Create the problem.

        Args:
            names: The names the decision variables get, in the order the worker creates them.
            optimum: The value of each variable and model output at the faked optimum (0 if absent).
            error: Raised by ``solve`` instead of returning, to fake a failed solve.
            on_minimize: Also called with every objective, for a test that collects them itself.
        """
        self._names = tuple(names)
        self._optimum = dict(optimum)
        self._error = error
        self._on_minimize = on_minimize
        self.variables: dict[str, dict[str, Any]] = {}
        self.constraints: list[RecordedConstraint] = []
        self.objectives: list[RecordedExpression] = []
        self.solve_options: list[dict[str, Any]] = []

    def expression(self, name: str) -> RecordedExpression:
        """A leaf expression (a variable or a model output) with its value at the faked optimum."""
        return RecordedExpression(name, self._optimum.get(name, 0.0))

    def variable(self, **kwargs: Any) -> RecordedExpression:
        """Record a decision variable; it is named by its position in ``names``."""
        name = self._names[len(self.variables)]
        self.variables[name] = kwargs
        return self.expression(name)

    def subject_to(self, constraint: RecordedConstraint) -> None:
        """Record a constraint."""
        self.constraints.append(constraint)

    def minimize(self, expression: RecordedExpression) -> None:
        """Record the objective."""
        self.objectives.append(expression)
        if self._on_minimize is not None:
            self._on_minimize(expression)

    def solve(self, **options: Any) -> Callable[[RecordedExpression], float]:
        """Return the reader of the faked optimum, or raise the given error."""
        self.solve_options.append(options)
        if self._error is not None:
            raise self._error

        def solved(expression: RecordedExpression) -> float:
            return expression.value

        return solved


class RecordingBoundary:
    """The faked ``aerosandbox`` of an Opti worker: ``Opti``, ``OperatingPoint`` and ``AeroBuildup``.

    Every ``Opti()`` the worker creates is a new :class:`RecordingOpti`; ``AeroBuildup(...).run()``
    returns one leaf expression per name in ``outputs`` (valued at the faked optimum), so objective and
    constraints are built from recorded expressions.

    Attributes:
        problems: The problems the worker created, in order.
        operating_points: The keyword arguments of each ``OperatingPoint(...)`` call.
    """

    def __init__(
        self,
        names: Sequence[str],
        optimum: Mapping[str, float],
        outputs: Sequence[str],
        error: Exception | None = None,
        on_minimize: Callable[[RecordedExpression], None] | None = None,
    ) -> None:
        """Create the boundary.

        Args:
            names: The names of the decision variables, in the order the worker creates them.
            optimum: The value of each variable and model output at the faked optimum.
            outputs: The keys of the AeroBuildup result the worker may read.
            error: Raised by every ``solve``, to fake a failed solve.
            on_minimize: Also called with every objective, for a test that collects them itself.
        """
        self._names = tuple(names)
        self._optimum = dict(optimum)
        self._outputs = tuple(outputs)
        self._error = error
        self._on_minimize = on_minimize
        self.problems: list[RecordingOpti] = []
        self.operating_points: list[dict[str, Any]] = []

    def _opti(self) -> RecordingOpti:
        problem = RecordingOpti(self._names, self._optimum, self._error, self._on_minimize)
        self.problems.append(problem)
        return problem

    def _operating_point(self, **kwargs: Any) -> types.SimpleNamespace:
        self.operating_points.append(kwargs)
        return types.SimpleNamespace(**kwargs)

    def _aero_buildup(self, *_: object, **__: object) -> types.SimpleNamespace:
        problem = self.problems[-1]
        aero = {name: problem.expression(name) for name in self._outputs}
        return types.SimpleNamespace(run=lambda: aero)

    def namespace(self) -> types.SimpleNamespace:
        """The object to return from the worker's ``load_aerosandbox``."""
        return types.SimpleNamespace(
            Opti=self._opti, OperatingPoint=self._operating_point, AeroBuildup=self._aero_buildup
        )
