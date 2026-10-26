"""The flap-device mapping to AeroBuildup: symmetric, trailing edge down positive (ch. 8.8, 8.11)."""

import math
from typing import Any

import pytest
from aero_kernel.config import config
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.solvers.asb_airplane import to_asb_airplane
from aero_kernel.solvers.devices import (
    flap_segments,
    refuse_deflected_devices,
    roll_hinge_warnings,
)
from aero_kernel.tests.asb_fakes import FakeAirplane, FakeControlSurface, install_fake_aerosandbox
from aero_kernel.tests.test_solvers_roll_devices import section

NACA = "naca2412"


def flap(
    role: str = "flap", root: float | None = 0.8, tip: float | None = 0.8, **extra: Any
) -> dict[str, Any]:
    return {"name": "Flap", "role": role, "rel_chord_root": root, "rel_chord_tip": tip, **extra}


def geometry(
    device: dict[str, Any] | None,
    *,
    symmetric: bool = True,
    ys: tuple[float, ...] = (0.0, 0.2, 0.4),
) -> AirplaneGeometry:
    sections = [section(y, device if index == 1 else None) for index, y in enumerate(ys)]
    wing = {"name": "Main", "surface_type": "main_wing", "symmetric": symmetric, "x_secs": sections}
    return AirplaneGeometry.model_validate({"name": "t", "wings": {"Main": wing}})


@pytest.fixture(autouse=True)
def fake(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_aerosandbox(monkeypatch)


def surfaces(airplane: FakeAirplane) -> list[list[FakeControlSurface]]:
    return [
        list(x.kwargs.get("control_surfaces", []))
        for x in airplane.kwargs["wings"][0].kwargs["xsecs"]
    ]


def converted(model: AirplaneGeometry, roll_deg: float = 0.0) -> FakeAirplane:
    airplane = to_asb_airplane(model, roll_deg)
    assert isinstance(airplane, FakeAirplane)
    return airplane


def airfoils(airplane: FakeAirplane) -> list[object]:
    """The ``coordinates`` of each section's airfoil: a tuple for a deflected contour, else None."""
    return [x.kwargs["airfoil"].coordinates for x in airplane.kwargs["wings"][0].kwargs["xsecs"]]


def test_a_deflected_flap_is_the_geometry_of_its_strip_and_no_control_surface() -> None:
    """Route A (maintainer 2026-10-26): the contour behind the hinge is rotated, trailing edge down
    positive, so the Hoerner factor is 1 and tau * delta is not counted."""
    airplane = converted(geometry(flap(deflection_deg=30.0)))
    assert surfaces(airplane) == [[], [], [], []]
    deflected = ("deflected", NACA, 30.0, 0.8)
    # ribs: root | end of the strip before (plain) | start of the flap strip | tip (end of the flap)
    assert airfoils(airplane) == [None, None, deflected, deflected]


def test_the_rib_where_the_flap_state_changes_is_written_twice_offset_by_the_configured_gap() -> (
    None
):
    airplane = converted(geometry(flap(deflection_deg=30.0)))
    positions = [x.kwargs["xyz_le"] for x in airplane.kwargs["wings"][0].kwargs["xsecs"]]
    gap = config().opt_flap_rib_gap.value
    assert positions == [[0.0, 0.0, 0.0], [0.0, 0.2, 0.0], [0.0, 0.2 + gap, 0.0], [0.0, 0.4, 0.0]]


def test_a_flap_over_the_first_strip_needs_no_extra_rib_at_the_root() -> None:
    sections = [
        section(y, flap(deflection_deg=30.0) if y == 0.0 else None) for y in (0.0, 0.2, 0.4)
    ]
    wing = {"name": "Main", "surface_type": "main_wing", "symmetric": True, "x_secs": sections}
    model = AirplaneGeometry.model_validate({"name": "t", "wings": {"Main": wing}})
    deflected = ("deflected", NACA, 30.0, 0.8)
    assert airfoils(converted(model)) == [deflected, deflected, None, None]


def test_two_neighbouring_strips_of_one_flap_share_their_rib() -> None:
    sections = [section(y, flap(deflection_deg=30.0) if y < 0.3 else None) for y in (0.0, 0.2, 0.4)]
    wing = {"name": "Main", "surface_type": "main_wing", "symmetric": True, "x_secs": sections}
    model = AirplaneGeometry.model_validate({"name": "t", "wings": {"Main": wing}})
    deflected = ("deflected", NACA, 30.0, 0.8)
    assert airfoils(converted(model)) == [deflected, deflected, deflected]  # 3 ribs, no split


@pytest.mark.parametrize("deflection", [None, 0.0])
def test_a_flap_at_rest_gives_the_clean_airplane_bit_for_bit(deflection: float | None) -> None:
    model = geometry(flap(deflection_deg=deflection))
    xsecs = converted(model).kwargs["wings"][0].kwargs["xsecs"]
    assert len(xsecs) == 3
    for xsec in xsecs:
        assert set(xsec.kwargs) == {"xyz_le", "chord", "twist", "airfoil"}
        assert xsec.kwargs["airfoil"].coordinates is None
    assert flap_segments(model) == []


def test_a_deflected_flap_is_not_driven_by_the_roll_command() -> None:
    """A flap is symmetric geometry whatever the roll command is: no control surface at all."""
    airplane = converted(geometry(flap(deflection_deg=30.0)), 15.0)
    assert surfaces(airplane) == [[], [], [], []]


def test_a_flaperon_is_the_geometric_bias_with_the_antisymmetric_command_on_top() -> None:
    """The landing deflection is the bias; the aileron deflection is applied on top (#1212)."""
    airplane = converted(geometry(flap("flaperon", deflection_deg=20.0)), 10.0)
    deflected = ("deflected", NACA, 20.0, 0.8)
    assert airfoils(airplane) == [None, None, deflected, deflected]
    assert [len(c) for c in surfaces(airplane)] == [0, 0, 1, 0]
    (command,) = surfaces(airplane)[2]
    assert command.kwargs["symmetric"] is False
    assert math.isclose(command.kwargs["deflection"], -10.0, rel_tol=1e-12)
    assert math.isclose(command.kwargs["hinge_point"], 0.8, rel_tol=1e-12)


def test_a_flaperon_without_bias_is_only_the_roll_surface() -> None:
    airplane = converted(geometry(flap("flaperon")), 10.0)
    assert [len(c) for c in surfaces(airplane)] == [0, 1, 0]
    assert airfoils(airplane) == [None, None, None]


def test_a_flaperon_with_bias_and_no_command_is_only_the_geometry() -> None:
    airplane = converted(geometry(flap("flaperon", deflection_deg=20.0)))
    assert surfaces(airplane) == [[], [], [], []]


def test_the_flap_hinge_is_the_mean_with_the_declared_warning() -> None:
    model = geometry(flap(root=0.78, tip=0.80, deflection_deg=30.0))
    assert airfoils(converted(model))[2] == ("deflected", NACA, 30.0, 0.79)
    (segment,) = flap_segments(model)
    assert segment.deflection_deg == 30.0
    (warning,) = roll_hinge_warnings([segment])
    assert warning.code == "hinge_line_averaged"
    assert warning.detail["device"] == "Flap"


def test_a_deflected_flap_without_hinge_is_invalid_input() -> None:
    model = geometry(flap(root=None, tip=None, deflection_deg=30.0))
    with pytest.raises(FormulaError) as raised:
        to_asb_airplane(model)
    assert (raised.value.category, raised.value.code) == (
        ErrorCategory.INVALID_INPUT,
        "missing_hinge",
    )


def test_a_deflected_flap_on_an_unmirrored_surface_is_unsupported() -> None:
    model = geometry(flap(deflection_deg=30.0), symmetric=False)
    with pytest.raises(FormulaError) as raised:
        flap_segments(model)
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION
    assert raised.value.code == "flap_on_unmirrored_surface"
    assert raised.value.detail == {"wing": "Main", "device": "Flap", "role": "flap"}


def test_a_stored_minus_y_wing_puts_the_flap_on_the_same_segment() -> None:
    plus = airfoils(converted(geometry(flap(deflection_deg=30.0))))
    minus = airfoils(converted(geometry(flap(deflection_deg=30.0), ys=(0.0, -0.2, -0.4))))
    assert plus == minus


def test_flaps_are_accepted_where_supported_and_refused_where_not() -> None:
    model = geometry(flap(deflection_deg=30.0))
    refuse_deflected_devices(model, "AeroBuildup", flaps_supported=True)
    with pytest.raises(FormulaError) as raised:
        refuse_deflected_devices(model, "AeroBuildup", flaps_supported=False)
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION
    assert "Flap" in raised.value.message


def test_an_aileron_off_its_rest_position_is_refused_even_where_flaps_are_supported() -> None:
    model = geometry({"name": "A", "role": "aileron", "rel_chord_root": 0.8, "deflection_deg": 3.0})
    with pytest.raises(FormulaError) as raised:
        refuse_deflected_devices(model, "AeroBuildup", flaps_supported=True)
    assert raised.value.code == "unsupported_configuration"


def test_a_driven_flap_without_a_hinge_in_the_chain_is_a_defect_of_the_caller() -> None:
    """flap_segments refuses a hinge-less flap first; the conversion's own guard is a ValueError."""
    from aero_kernel.solvers import asb_airplane
    from aero_kernel.surface_chain import ChainDevice, ChainPoint

    point = ChainPoint(
        x=0.0,
        y=0.0,
        z=0.0,
        chord=0.2,
        twist=0.0,
        airfoil=NACA,
        device=ChainDevice(
            name="f", role="flap", hinge_start=None, hinge_end=None, deflection_deg=30.0
        ),
    )
    with pytest.raises(ValueError, match="without a hinge"):
        asb_airplane._flap_state(point, True)  # pyright: ignore[reportPrivateUsage]
