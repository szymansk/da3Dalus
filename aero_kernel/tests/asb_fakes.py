"""A fake ``aerosandbox`` that records how the geometry conversion builds its objects."""

import importlib.machinery
import sys
import types
from typing import Any

import pytest

# ``Any``: the fake stands in for an untyped third-party module; keyword arguments are recorded
# exactly as passed.


class FakeAirfoil:
    """Records ``asb.Airfoil(name=..., coordinates=...)``."""

    def __init__(self, name: str | None = None, coordinates: Any = None) -> None:
        self.name = name
        self.coordinates = coordinates


class FakeWingXSec:
    """Records ``asb.WingXSec(...)``."""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs


class FakeControlSurface:
    """Records ``asb.ControlSurface(...)``."""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs


# (area, span, mean aerodynamic chord) the fake wing reports by name; any other name gets the default.
FAKE_REFERENCE: dict[str, tuple[float, float, float]] = {
    "Main": (0.31, 1.7, 0.21),
    "Fin": (0.07, 0.4, 0.08),
}
FAKE_DEFAULT_REFERENCE = (1.0, 2.0, 0.5)
# The span without the centreline distance is this much shorter than the one with it.
FAKE_CENTRELINE_GAP = 0.1


class FakeWing:
    """Records ``asb.Wing(...)`` and reports the reference values of :data:`FAKE_REFERENCE`."""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.name = kwargs.get("name")
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def _reference(self) -> tuple[float, float, float]:
        return FAKE_REFERENCE.get(str(self.name), FAKE_DEFAULT_REFERENCE)

    def area(self, **options: Any) -> float:
        """The planform area (centreline gap excluded, as ASB does)."""
        self.calls.append(("area", options))
        return self._reference()[0]

    def span(self, **options: Any) -> float:
        """The span; the one with the centreline distance is the longer."""
        self.calls.append(("span", options))
        gap = FAKE_CENTRELINE_GAP if options.get("include_centerline_distance") else 0.0
        return self._reference()[1] + gap

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
