"""Shared pytest configuration for the ``aero_kernel`` tests."""

from pathlib import Path

import pytest
from aero_kernel.canon.load import load_canon_model
from aero_kernel.canon.model import CanonModel
from aero_kernel.graph import PENDING_WHEN_TERMS
from aero_kernel.tests.asb_fakes import stand_in_main_wing_properties, stand_in_surface_of

PACKAGE_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def package_root() -> Path:
    """Directory of the ``aero_kernel`` package."""
    return PACKAGE_ROOT


@pytest.fixture(scope="session")
def flight_canon() -> CanonModel:
    """The fixture canon model of tests/fixtures/flight_canon.json (frozen, shared)."""
    return load_canon_model(PACKAGE_ROOT / "tests" / "fixtures" / "flight_canon.json")


@pytest.fixture(autouse=True)
def no_aerosandbox_for_the_reference_values(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fast tier: the main wing's reference values come from a stand-in, never from AeroSandbox.

    The CI fast tier runs without the aero dependencies. The aero tier (marker ``aero``) measures
    with the real AeroSandbox.
    """
    if request.node.get_closest_marker("aero") is not None:  # pyright: ignore[reportUnknownMemberType]
        return
    for module in (
        "aero_kernel.solvers.geometry",
        "aero_kernel.solvers.avl",
        "aero_kernel.formulas.stall_speed",
    ):
        monkeypatch.setattr(
            f"{module}.main_wing_properties", stand_in_main_wing_properties, raising=True
        )
    monkeypatch.setattr(
        "aero_kernel.solvers.geometry.surface_properties", stand_in_surface_of, raising=True
    )


@pytest.fixture
def pending_horizontal_tail(monkeypatch: pytest.MonkeyPatch) -> None:
    """Declare ``has_horizontal_tail`` a vocabulary term whose fact is not computed yet (#1187).

    No term of the vocabulary is pending in production since the fact exists; the declared
    ``not_implemented`` path for a future term is tested by pending this one for the test.
    """
    monkeypatch.setitem(PENDING_WHEN_TERMS, "has_horizontal_tail", "#1187")
