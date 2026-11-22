"""Control-device state of a geometry: at rest, and the flaps set for a configuration (ch. 8.11)."""

from typing import Any

from aero_kernel.devices import (
    CROW_AILERON_ROLES,
    CROW_FLAP_ROLES,
    crow_configuration,
    devices_at_rest,
    flap_deflections,
    has_flap,
    with_flaps_at,
)
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


def crow_airplane() -> AirplaneGeometry:
    """A wing with a flap, a flaperon, an aileron and an elevator, all at rest."""
    return airplane(
        section(0.0, {"role": "flap", "name": "F", "rel_chord_root": 0.75}),
        section(0.2, {"role": "flaperon", "name": "FA", "rel_chord_root": 0.75}),
        section(0.4, {"role": "aileron", "name": "A", "rel_chord_root": 0.75}),
        section(0.6, {"role": "elevator", "name": "E", "rel_chord_root": 0.75}),
        section(0.8),
    )


def roles_and_angles(model: AirplaneGeometry) -> list[tuple[str, float] | None]:
    return [
        None if (d := s.trailing_edge_device) is None else (d.role, d.deflection_deg or 0.0)
        for s in (model.wings or {})["Main"].x_secs
    ]


def test_the_crow_configuration_runs_the_flaps_from_landing_to_crow_and_raises_the_ailerons() -> (
    None
):
    # flap 30 + 0.5 * (70 - 30) = 50 down; aileron 0.5 * 40 = 20 up = -20 (down positive), evaluated
    # as a symmetric flap-like contour; the flaperon and the elevator are not part of crow
    model = crow_configuration(crow_airplane(), 0.5, 30.0, 70.0, 40.0)
    assert roles_and_angles(model) == [
        ("flap", 50.0),
        ("flaperon", 0.0),
        ("flap", -20.0),
        ("elevator", 0.0),
        None,
    ]


def test_the_crow_configuration_at_zero_mix_is_the_landing_flap_and_a_level_aileron() -> None:
    model = crow_configuration(crow_airplane(), 0.0, 30.0, 70.0, 40.0)
    assert roles_and_angles(model)[:3] == [("flap", 30.0), ("flaperon", 0.0), ("flap", 0.0)]


def test_the_crow_configuration_leaves_the_flaperon_where_landing_put_it() -> None:
    landing = with_flaps_at(crow_airplane(), 30.0)  # flap and flaperon both at 30
    model = crow_configuration(landing, 1.0, 30.0, 70.0, 40.0)
    assert roles_and_angles(model)[:3] == [("flap", 70.0), ("flaperon", 30.0), ("flap", -40.0)]


def test_crow_roles_name_the_butterfly_layout_the_graph_tests() -> None:
    assert frozenset({"flap"}) == CROW_FLAP_ROLES
    assert frozenset({"aileron", "elevon"}) == CROW_AILERON_ROLES


def test_flap_deflections_lists_only_flap_roles_off_rest_labelled_by_name_or_index() -> None:
    """Sections 0..4: flap 'F' 20, unnamed flaperon -5, aileron 'A' 3, flap 'G' at rest, none.

    Expected: the flap and the flaperon (a flap role), the unnamed one labelled by its section
    index; the aileron is no flap and the flap at 0 deg is not deflected.
    """

    def tev(role: str, deflection: float, name: str | None = None) -> dict[str, Any]:
        device: dict[str, Any] = {
            "role": role,
            "rel_chord_root": 0.25,
            "rel_chord_tip": 0.25,
            "deflection_deg": deflection,
        }
        if name is not None:
            device["name"] = name
        return device

    model = airplane(
        section(0.0, tev("flap", 20.0, "F")),
        section(0.2, tev("flaperon", -5.0)),
        section(0.4, tev("aileron", 3.0, "A")),
        section(0.6, tev("flap", 0.0, "G")),
        section(0.8),
    )
    assert flap_deflections(model) == [("Main", "F", 20.0), ("Main", "device 1", -5.0)]
