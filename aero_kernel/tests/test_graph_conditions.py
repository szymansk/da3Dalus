"""Application conditions: the closed `when` vocabulary and `given` (ARCHITECTURE ch. 8.5)."""

from typing import Any

import pytest
from aero_kernel.canon.model import CanonModel
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.graph import (
    CanonGraph,
    Node,
    NodeId,
    WhenFacts,
    facts_from_geometry,
    unmet_condition,
)
from aero_kernel.schema import ReasonCode

AILERON_ROLES = ("aileron", "flaperon", "elevon")


def sec(x: float, y: float, chord: float, role: str | None = None) -> dict[str, Any]:
    """A rib at (x, y) with a chord, carrying a device of the given role if any."""
    rib: dict[str, Any] = {
        "xyz_le": [x, y, 0.0],
        "chord": chord,
        "twist": 0.0,
        "airfoil": "naca2412",
    }
    if role is not None:
        rib["trailing_edge_device"] = {"role": role}
    return rib


def wing(*secs: dict[str, Any], symmetric: bool = True) -> dict[str, Any]:
    """A wing document of the given ribs."""
    return {"name": "w", "symmetric": symmetric, "x_secs": list(secs)}


def facts(wings: dict[str, dict[str, Any]] | None) -> WhenFacts:
    """The facts of an aircraft with the given wings."""
    document: dict[str, Any] = {"name": "t"}
    if wings is not None:
        document["wings"] = wings
    return facts_from_geometry(AirplaneGeometry.model_validate(document))


MAIN = wing(sec(0.0, 0.0, 0.2), sec(0.0, 0.5, 0.15))


def test_an_aircraft_without_wings_has_no_facts() -> None:
    no_wings: list[dict[str, dict[str, Any]] | None] = [None, {}]
    for wings in no_wings:
        assert facts(wings) == WhenFacts(
            has_aileron=False, has_separate_flap_and_aileron=False, has_vertical_tail=False
        )


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        ("aileron", True),
        ("flaperon", True),
        ("elevon", True),
        ("flap", False),
        ("elevator", False),
        ("rudder", False),
        ("ruddervator", False),
        ("stabilator", False),
        ("other", False),
    ],
)
def test_has_aileron_goes_by_the_role_of_the_device(role: str, expected: bool) -> None:
    held = facts({"w": wing(sec(0, 0, 0.2, role), sec(0, 0.5, 0.2))})
    assert held.has_aileron is expected


def test_a_control_surface_name_is_not_a_role() -> None:
    rib = sec(0, 0, 0.2) | {"control_surface": {"name": "aileron"}}
    assert facts({"w": wing(rib, sec(0, 0.5, 0.2))}).has_aileron is False


@pytest.mark.parametrize(
    ("roles", "expected"),
    [
        (("flap", "aileron"), True),
        (("flap", "elevon"), True),
        (("flaperon", "aileron"), True),
        (("flap", "flaperon"), True),
        (("flaperon", "flaperon"), True),
        (("flaperon",), False),
        (("flap",), False),
        (("aileron", "aileron"), False),
        (("elevon", "elevator"), False),
    ],
)
def test_separate_flap_and_aileron_needs_two_distinct_devices(
    roles: tuple[str, ...], expected: bool
) -> None:
    ribs = [sec(0, 0.1 * i, 0.2, role) for i, role in enumerate(roles)]
    held = facts({"w": wing(*ribs, sec(0, 1.0, 0.2))})
    assert held.has_separate_flap_and_aileron is expected


def test_devices_on_different_wings_are_distinct() -> None:
    held = facts(
        {
            "a": wing(sec(0, 0, 0.2, "flaperon"), sec(0, 0.5, 0.2)),
            "b": wing(sec(0, 0, 0.2, "flaperon"), sec(0, 0.5, 0.2)),
        }
    )
    assert held.has_separate_flap_and_aileron is True


def fin(x: float = 0.9) -> dict[str, Any]:
    return wing(sec(x, 0.0, 0.15), sec(x + 0.05, 0.0, 0.1), symmetric=False)


def test_a_conventional_fin_behind_the_wing_is_a_vertical_tail() -> None:
    assert facts({"main": MAIN, "fin": fin()}).has_vertical_tail is True


def test_a_v_tail_with_ruddervators_is_a_vertical_tail() -> None:
    v_tail = wing(sec(0.9, 0.0, 0.15, "ruddervator"), sec(0.95, 0.3, 0.1))
    assert facts({"main": MAIN, "vtail": v_tail}).has_vertical_tail is True


def test_a_rudder_on_a_symmetric_wing_is_a_vertical_tail() -> None:
    surface = wing(sec(0.9, 0.0, 0.15, "rudder"), sec(0.95, 0.3, 0.1))
    assert facts({"main": MAIN, "t": surface}).has_vertical_tail is True


def test_a_horizontal_tail_is_no_vertical_tail() -> None:
    stabiliser = wing(sec(0.9, 0.0, 0.1, "elevator"), sec(0.9, 0.3, 0.1))
    assert facts({"main": MAIN, "tail": stabiliser}).has_vertical_tail is False


def test_a_tailless_centre_fin_overlapping_the_root_chord_is_none() -> None:
    assert facts({"main": MAIN, "fin": fin(0.1)}).has_vertical_tail is False


def test_a_fin_exactly_at_the_trailing_edge_counts() -> None:
    assert facts({"main": MAIN, "fin": fin(0.2)}).has_vertical_tail is True


def test_winglets_are_sections_of_the_main_wing_and_no_tail() -> None:
    winglet = wing(sec(0, 0, 0.2), sec(0, 0.5, 0.15), sec(0.05, 0.55, 0.1))
    assert facts({"main": winglet}).has_vertical_tail is False


def test_the_main_wing_is_the_largest_symmetric_planform() -> None:
    big = wing(sec(0.0, 0.0, 0.3), sec(0.0, 1.0, 0.3))
    small = wing(sec(0.0, 0.0, 0.1), sec(0.0, 0.2, 0.1))
    held = facts({"small": small, "fin": fin(0.5), "big": big})
    assert held.has_vertical_tail is True
    assert facts({"small": small, "fin": fin(0.25), "big": big}).has_vertical_tail is False


def test_a_fin_alone_has_no_main_wing_to_stand_behind() -> None:
    assert facts({"fin": fin()}).has_vertical_tail is False


def test_a_wing_without_ribs_is_ignored() -> None:
    assert facts({"empty": wing(), "main": MAIN, "fin": fin()}).has_vertical_tail is True
    assert facts({"empty": wing()}).has_vertical_tail is False


def node_of(model: CanonModel, formula: str, application: str) -> Node:
    return CanonGraph(model).node(NodeId(formula=f"calc:{formula}", application=application))


ALL = WhenFacts(has_aileron=True, has_separate_flap_and_aileron=True, has_vertical_tail=True)
NONE = WhenFacts(has_aileron=False, has_separate_flap_and_aileron=False, has_vertical_tail=False)


def test_an_unconditional_application_has_no_unmet_condition(flight_canon: CanonModel) -> None:
    node = node_of(flight_canon, "stall-speed", "clean")
    assert unmet_condition(node, NONE, set()) is None


def test_an_unmet_when_is_condition_not_met_and_names_the_term(flight_canon: CanonModel) -> None:
    node = node_of(flight_canon, "roll-rate-cruise", "cruise")
    reason = unmet_condition(node, NONE, {"cruise-speed-target"})
    assert reason is not None
    assert reason.code is ReasonCode.CONDITION_NOT_MET
    assert "has_aileron" in reason.message


def test_a_missing_given_is_not_given_and_names_the_slug(flight_canon: CanonModel) -> None:
    node = node_of(flight_canon, "roll-rate-cruise", "cruise")
    reason = unmet_condition(node, ALL, set())
    assert reason is not None
    assert reason.code is ReasonCode.NOT_GIVEN
    assert "cruise-speed-target" in reason.message


def test_when_is_checked_before_given(flight_canon: CanonModel) -> None:
    node = node_of(flight_canon, "roll-rate-cruise", "cruise")
    reason = unmet_condition(node, NONE, set())
    assert reason is not None
    assert reason.code is ReasonCode.CONDITION_NOT_MET


@pytest.mark.parametrize("supplied", [{"cruise-speed-target"}, {"calc:cruise-speed-target"}])
def test_a_supplied_given_in_either_spelling_is_met(
    flight_canon: CanonModel, supplied: set[str]
) -> None:
    node = node_of(flight_canon, "roll-rate-cruise", "cruise")
    assert unmet_condition(node, ALL, supplied) is None


@pytest.mark.parametrize(
    "term", ["has_aileron", "has_separate_flap_and_aileron", "has_vertical_tail"]
)
def test_every_term_of_the_vocabulary_is_read_from_its_own_fact(term: str) -> None:
    for name in ("has_aileron", "has_separate_flap_and_aileron", "has_vertical_tail"):
        only = WhenFacts(
            **{
                n: n == name
                for n in ("has_aileron", "has_separate_flap_and_aileron", "has_vertical_tail")
            }
        )
        assert only.holds(term) is (term == name)  # type: ignore[arg-type]  # term is one of the Literal values
