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


class FakeWing:
    """Records ``asb.Wing(...)``."""

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
    module.Wing = FakeWing  # pyright: ignore[reportAttributeAccessIssue]
    module.Airplane = FakeAirplane  # pyright: ignore[reportAttributeAccessIssue]
    monkeypatch.setitem(sys.modules, "aerosandbox", module)
    return module
