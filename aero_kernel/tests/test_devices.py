"""Control-device state of a geometry: at rest, and the flaps set for a configuration (ch. 8.11)."""

from typing import Any

from aero_kernel.devices import devices_at_rest, has_flap, with_flaps_at
from aero_kernel.geometry import AirplaneGeometry


def section(y: float, device: dict[str, Any] | None = None, surface: float | None = None) -> Any:
    document: dict[str, Any] = {
        "xyz_le": [0.0, y, 0.0],
        "chord": 0.2,
        "twist": 0.0,
        "airfoil": "naca2412",
    }
    if device is not None:
        document["trailing_edge_device"] = device
    if surface is not None:
        document["control_surface"] = {"name": "cs", "deflection": surface}
    return document


def airplane(*sections: dict[str, Any]) -> AirplaneGeometry:
    wing = {"name": "Main", "surface_type": "main_wing", "x_secs": list(sections)}
    return AirplaneGeometry.model_validate({"name": "t", "wings": {"Main": wing}})


def devices(model: AirplaneGeometry) -> list[tuple[float | None, float | None]]:
    """(device deflection_deg, control_surface deflection) per section of the main wing."""
    result: list[tuple[float | None, float | None]] = []
    for x_sec in (model.wings or {})["Main"].x_secs:
        device = x_sec.trailing_edge_device
        surface = x_sec.control_surface
        result.append(
            (
                None if device is None else device.deflection_deg,
                None if surface is None else surface.deflection,
            )
        )
    return result


def test_devices_at_rest_zeroes_both_state_fields_and_nothing_else() -> None:
    model = airplane(
        section(
            0.0, {"role": "flap", "deflection_deg": 20.0, "positive_deflection_deg": 30.0}, 7.0
        ),
        section(0.4, {"role": "aileron", "deflection_deg": -5.0}),
        section(0.8),
    )
    at_rest = devices_at_rest(model)
    assert devices(at_rest) == [(0.0, 0.0), (0.0, None), (None, None)]
    first = (at_rest.wings or {})["Main"].x_secs[0]
    assert first.trailing_edge_device is not None
    assert first.trailing_edge_device.positive_deflection_deg == 30.0  # stops are kept, never read
    assert first.trailing_edge_device.role == "flap"


def test_devices_at_rest_of_a_geometry_without_wings_is_the_geometry() -> None:
    model = AirplaneGeometry.model_validate({"name": "t"})
    assert devices_at_rest(model) == model


def test_has_flap_holds_for_flap_and_flaperon_roles_only() -> None:
    assert has_flap(airplane(section(0.0, {"role": "flap"}), section(0.4)))
    assert has_flap(airplane(section(0.0, {"role": "flaperon"}), section(0.4)))
    assert not has_flap(airplane(section(0.0, {"role": "aileron"}), section(0.4)))
    assert not has_flap(airplane(section(0.0), section(0.4)))


def test_with_flaps_at_sets_the_flap_devices_and_leaves_the_others() -> None:
    model = airplane(
        section(0.0, {"role": "flap", "positive_deflection_deg": 30.0}),
        section(0.2, {"role": "flaperon"}),
        section(0.4, {"role": "aileron", "deflection_deg": 3.0}),
        section(0.8),
    )
    configured = with_flaps_at(model, 55.0)  # beyond the stop of 30 deg: applied exactly
    assert devices(configured) == [(55.0, None), (55.0, None), (3.0, None), (None, None)]


def test_with_flaps_at_a_geometry_without_flaps_is_the_geometry() -> None:
    model = airplane(section(0.0, {"role": "aileron", "deflection_deg": 3.0}), section(0.4))
    assert with_flaps_at(model, 20.0) == model
