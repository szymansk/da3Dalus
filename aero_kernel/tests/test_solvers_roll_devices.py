"""The roll-device mapping to AeroBuildup and the sign rule shared with AVL (ch. 8.8, 8.11)."""

import math
from typing import Any

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.solvers.asb_airplane import to_asb_airplane
from aero_kernel.solvers.devices import (
    refuse_deflected_devices,
    roll_deflection,
    roll_hinge_warnings,
    roll_segments,
)
from aero_kernel.tests.asb_fakes import FakeAirplane, FakeControlSurface, install_fake_aerosandbox

NACA = "naca2412"


def section(y: float, device: dict[str, Any] | None = None) -> dict[str, Any]:
    document: dict[str, Any] = {
        "xyz_le": [0.0, y, 0.0],
        "chord": 0.2,
        "twist": 0.0,
        "airfoil": NACA,
    }
    if device is not None:
        document["trailing_edge_device"] = device
    return document


def aileron(root: float | None = 0.8, tip: float | None = 0.8, **extra: Any) -> dict[str, Any]:
    return {
        "name": "Querruder",
        "role": "aileron",
        "rel_chord_root": root,
        "rel_chord_tip": tip,
        **extra,
    }


def wing_geometry(
    ys: tuple[float, ...],
    device_at: int | None,
    device: dict[str, Any] | None = None,
    symmetric: bool = True,
    surface_deflection: float | None = None,
) -> AirplaneGeometry:
    sections = [
        section(y, (device or aileron()) if index == device_at else None)
        for index, y in enumerate(ys)
    ]
    if surface_deflection is not None:
        sections[1]["control_surface"] = {"name": "cs", "deflection": surface_deflection}
    wing = {
        "name": "Main",
        "surface_type": "main_wing",
        "symmetric": symmetric,
        "x_secs": sections,
    }
    return AirplaneGeometry.model_validate({"name": "t", "wings": {"Main": wing}})


@pytest.fixture(autouse=True)
def fake(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_aerosandbox(monkeypatch)


def control_surfaces(airplane: FakeAirplane, wing: int = 0) -> list[list[FakeControlSurface]]:
    """The ``control_surfaces`` argument per section of one wing ([] where none was given)."""
    return [
        list(x.kwargs.get("control_surfaces", []))
        for x in airplane.kwargs["wings"][wing].kwargs["xsecs"]
    ]


def converted(model: AirplaneGeometry, roll_deg: float) -> FakeAirplane:
    airplane = to_asb_airplane(model, roll_deg)
    assert isinstance(airplane, FakeAirplane)
    return airplane


@pytest.mark.parametrize("role", ["aileron", "flaperon", "elevon"])
def test_roll_devices_map_antisymmetric_on_their_segment_start_xsec(role: str) -> None:
    model = wing_geometry((0.0, 0.2, 0.4), 1, aileron(0.8, 0.8, role=role))
    per_section = control_surfaces(converted(model, 20.0))
    assert per_section[0] == []
    assert per_section[2] == []
    (surface,) = per_section[1]
    assert surface.kwargs["symmetric"] is False
    assert surface.kwargs["hinge_point"] == 0.8
    assert surface.kwargs["deflection"] == -20.0  # positive command: right trailing edge up
    assert surface.kwargs["name"] == "Querruder"


@pytest.mark.parametrize(
    ("side", "delta", "expected"), [(1, 20.0, -20.0), (-1, 20.0, 20.0), (1, -5.0, 5.0)]
)
def test_roll_sign_from_the_side_as_written(side: int, delta: float, expected: float) -> None:
    assert roll_deflection(side, delta) == expected


def test_minus_y_stored_wing_is_written_on_the_positive_side_like_the_avl_writer() -> None:
    """One orientation rule: a mirrored wing stored on -y reaches ASB at +y, root first, so the
    sign helper sees side +1 in both tools and the airplane is the +y one."""
    plus_model = converted(wing_geometry((0.0, 0.2, 0.4), 1), 20.0)
    minus_model = converted(wing_geometry((0.0, -0.2, -0.4), 1), 20.0)
    assert control_surfaces(minus_model)[1][0].kwargs["deflection"] == -20.0
    assert [x.kwargs["xyz_le"] for x in minus_model.kwargs["wings"][0].kwargs["xsecs"]] == [
        x.kwargs["xyz_le"] for x in plus_model.kwargs["wings"][0].kwargs["xsecs"]
    ]


def test_tip_first_stored_wing_maps_each_device_to_its_own_segment() -> None:
    """Stored tip first at +y, the device on the stored section 1 (segment 0.2 -> 0.0): the wing
    is written root first, so the control sits on the first section (segment 0.0 -> 0.2)."""
    model = wing_geometry((0.4, 0.2, 0.0), 1)
    per_section = control_surfaces(converted(model, 20.0))
    assert [len(c) for c in per_section] == [1, 0, 0]
    assert per_section[0][0].kwargs["deflection"] == -20.0


def test_no_roll_command_gives_todays_airplane() -> None:
    model = wing_geometry((0.0, 0.2, 0.4), 1)
    for roll in (None, 0.0):
        airplane = to_asb_airplane(model) if roll is None else to_asb_airplane(model, roll)
        for xsec in airplane.kwargs["wings"][0].kwargs["xsecs"]:
            assert set(xsec.kwargs) == {"xyz_le", "chord", "twist", "airfoil"}


def test_hinge_is_mean_of_root_and_tip_with_declared_warning() -> None:
    model = wing_geometry((0.0, 0.2, 0.4), 1, aileron(0.78, 0.80))
    (surface,) = control_surfaces(converted(model, 20.0))[1]
    assert math.isclose(surface.kwargs["hinge_point"], 0.79, rel_tol=1e-12)
    (warning,) = roll_hinge_warnings(roll_segments(model))
    assert warning.code == "hinge_line_averaged"
    assert warning.severity == "practice"
    assert warning.detail == {
        "wing": "Main",
        "device": "Querruder",
        "root": 0.78,
        "tip": 0.80,
        "used": 0.79,
    }


def test_a_missing_tip_hinge_takes_the_root_and_declares_nothing() -> None:
    model = wing_geometry((0.0, 0.2, 0.4), 1, aileron(0.8, None))
    (surface,) = control_surfaces(converted(model, 20.0))[1]
    assert surface.kwargs["hinge_point"] == 0.8
    assert roll_hinge_warnings(roll_segments(model)) == []


def test_equal_root_and_tip_hinge_has_no_warning() -> None:
    assert roll_hinge_warnings(roll_segments(wing_geometry((0.0, 0.2, 0.4), 1))) == []


def test_driven_device_without_hinge_is_invalid_input() -> None:
    model = wing_geometry((0.0, 0.2, 0.4), 1, aileron(None, None))
    with pytest.raises(FormulaError) as raised:
        to_asb_airplane(model, 20.0)
    assert raised.value.category is ErrorCategory.INVALID_INPUT
    assert raised.value.code == "missing_hinge"
    assert raised.value.detail == {"wing": "Main", "device": "Querruder"}


def test_roll_device_on_unmirrored_surface_is_unsupported() -> None:
    model = wing_geometry((0.0, 0.2, 0.4), 1, symmetric=False)
    with pytest.raises(FormulaError) as raised:
        roll_segments(model)
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION
    assert raised.value.code == "roll_device_on_unmirrored_surface"
    assert raised.value.detail == {"wing": "Main", "device": "Querruder", "role": "aileron"}


def test_undriven_roles_are_not_mapped_and_not_checked() -> None:
    model = wing_geometry((0.0, 0.2, 0.4), 1, {"name": "Rudder", "role": "elevator"})
    assert roll_segments(model) == []
    assert control_surfaces(converted(model, 20.0)) == [[], [], []]


@pytest.mark.parametrize("on_device", [True, False])
def test_deflected_geometry_state_still_refused(on_device: bool) -> None:
    """The roll command is an adapter argument; a deflected geometry state stays refused."""
    model = wing_geometry(
        (0.0, 0.2, 0.4),
        1,
        aileron(deflection_deg=3.0) if on_device else aileron(),
        surface_deflection=None if on_device else 2.0,
    )
    with pytest.raises(FormulaError) as raised:
        refuse_deflected_devices(model, "AeroBuildup")
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION
