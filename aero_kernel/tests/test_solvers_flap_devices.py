"""The flap-device mapping to AeroBuildup: symmetric, trailing edge down positive (ch. 8.8, 8.11)."""

import math
from typing import Any

import pytest
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


def test_a_deflected_flap_is_one_symmetric_surface_trailing_edge_down_positive() -> None:
    per_section = surfaces(converted(geometry(flap(deflection_deg=30.0))))
    assert [len(c) for c in per_section] == [0, 1, 0]
    (surface,) = per_section[1]
    assert surface.kwargs["symmetric"] is True
    assert math.isclose(surface.kwargs["deflection"], 30.0, rel_tol=1e-12)
    assert math.isclose(surface.kwargs["hinge_point"], 0.8, rel_tol=1e-12)
    assert surface.kwargs["name"] == "Flap"


@pytest.mark.parametrize("deflection", [None, 0.0])
def test_a_flap_at_rest_gives_the_clean_airplane_bit_for_bit(deflection: float | None) -> None:
    model = geometry(flap(deflection_deg=deflection))
    for xsec in converted(model).kwargs["wings"][0].kwargs["xsecs"]:
        assert set(xsec.kwargs) == {"xyz_le", "chord", "twist", "airfoil"}
    assert flap_segments(model) == []


def test_a_deflected_flap_is_not_driven_by_the_roll_command() -> None:
    """A flap is symmetric whatever the roll command is."""
    (surface,) = surfaces(converted(geometry(flap(deflection_deg=30.0)), 15.0))[1]
    assert surface.kwargs["symmetric"] is True
    assert math.isclose(surface.kwargs["deflection"], 30.0, rel_tol=1e-12)


def test_a_flaperon_carries_the_bias_symmetric_and_the_command_antisymmetric() -> None:
    """The landing deflection is the bias; the aileron deflection is applied on top (#1212)."""
    model = geometry(flap("flaperon", deflection_deg=20.0))
    (bias, command) = surfaces(converted(model, 10.0))[1]
    assert bias.kwargs["symmetric"] is True
    assert math.isclose(bias.kwargs["deflection"], 20.0, rel_tol=1e-12)
    assert command.kwargs["symmetric"] is False
    assert math.isclose(command.kwargs["deflection"], -10.0, rel_tol=1e-12)
    assert bias.kwargs["hinge_point"] == command.kwargs["hinge_point"]


def test_a_flaperon_without_bias_is_only_the_roll_surface() -> None:
    (command,) = surfaces(converted(geometry(flap("flaperon")), 10.0))[1]
    assert command.kwargs["symmetric"] is False


def test_a_flaperon_with_bias_and_no_command_is_only_the_bias() -> None:
    (bias,) = surfaces(converted(geometry(flap("flaperon", deflection_deg=20.0))))[1]
    assert bias.kwargs["symmetric"] is True


def test_the_flap_hinge_is_the_mean_with_the_declared_warning() -> None:
    model = geometry(flap(root=0.78, tip=0.80, deflection_deg=30.0))
    (surface,) = surfaces(converted(model))[1]
    assert math.isclose(surface.kwargs["hinge_point"], 0.79, rel_tol=1e-12)
    (segment,) = flap_segments(model)
    assert segment.deflection_deg == 30.0
    (warning,) = roll_hinge_warnings([segment])
    assert warning.code == "hinge_line_averaged"
    assert warning.detail["device"] == "Flap"


def test_a_deflected_flap_without_hinge_is_invalid_input() -> None:
    with pytest.raises(FormulaError) as raised:
        to_asb_airplane(geometry(flap(root=None, tip=None, deflection_deg=30.0)))
    assert (raised.value.category, raised.value.code) == (
        ErrorCategory.INVALID_INPUT,
        "missing_hinge",
    )


def test_a_deflected_flap_on_an_unmirrored_surface_is_unsupported() -> None:
    with pytest.raises(FormulaError) as raised:
        flap_segments(geometry(flap(deflection_deg=30.0), symmetric=False))
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION
    assert raised.value.code == "flap_on_unmirrored_surface"
    assert raised.value.detail == {"wing": "Main", "device": "Flap", "role": "flap"}


def test_a_stored_minus_y_wing_puts_the_flap_on_the_same_segment() -> None:
    plus = surfaces(converted(geometry(flap(deflection_deg=30.0))))
    minus = surfaces(converted(geometry(flap(deflection_deg=30.0), ys=(0.0, -0.2, -0.4))))
    assert [len(c) for c in plus] == [len(c) for c in minus]


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
        asb_airplane._section(asb_airplane.load_aerosandbox(), point, 0.0, "x", True)  # pyright: ignore[reportPrivateUsage]
