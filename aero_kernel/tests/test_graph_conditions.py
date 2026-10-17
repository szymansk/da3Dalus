"""Application conditions: the closed `when` vocabulary and `given` (ARCHITECTURE ch. 8.5)."""

from typing import Any, get_args

import pytest
from aero_kernel.canon.model import CanonModel, WhenTerm
from aero_kernel.errors import ErrorCategory, KernelError
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.graph import (
    PENDING_WHEN_TERMS,
    CanonGraph,
    Node,
    NodeId,
    WhenFacts,
    facts_from_geometry,
    unmet_condition,
)
from aero_kernel.schema import Reason, ReasonCode
from aero_kernel.tests.graph_builders import formula, model_of, quantity

AILERON_ROLES = ("aileron", "flaperon", "elevon")


def sec(
    x: float, y: float, chord: float, role: str | None = None, z: float = 0.0
) -> dict[str, Any]:
    """A rib at (x, y) with a chord, carrying a device of the given role if any."""
    rib: dict[str, Any] = {
        "xyz_le": [x, y, z],
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
        (("flaperon", "aileron"), False),
        (("flap", "flaperon"), False),
        (("flaperon", "flaperon"), False),
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
            "a": wing(sec(0, 0, 0.2, "flap"), sec(0, 0.5, 0.2)),
            "b": wing(sec(0, 0, 0.2, "aileron"), sec(0, 0.5, 0.2)),
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


def test_one_flaperon_is_an_aileron_but_no_butterfly_layout() -> None:
    held = facts({"w": wing(sec(0, 0, 0.2, "flaperon"), sec(0, 0.5, 0.2))})
    assert (held.has_aileron, held.has_separate_flap_and_aileron) == (True, False)


def test_flaperons_never_make_a_butterfly_layout() -> None:
    """D10: butterfly needs a flap and a distinct aileron or elevon; a flaperon is neither."""
    held = facts(
        {"w": wing(sec(0, 0, 0.2, "flaperon"), sec(0, 0.3, 0.2, "flaperon"), sec(0, 0.6, 0.2))}
    )
    assert (held.has_aileron, held.has_separate_flap_and_aileron) == (True, False)


def test_the_main_wing_is_chosen_by_area_not_by_span() -> None:
    narrow = wing(sec(0, 0, 0.05), sec(0, 1.0, 0.05))  # area .05, span 1.0, trailing edge .05
    wide = wing(sec(0, 0, 0.5), sec(0, 0.4, 0.5))  # area .2, span .4, trailing edge .5
    assert facts({"narrow": narrow, "wide": wide, "fin": fin(0.3)}).has_vertical_tail is False


def test_a_larger_fin_does_not_take_over_as_main_wing() -> None:
    main = wing(sec(0, 0, 0.2), sec(0, 1.0, 0.2))  # area .2
    big_fin = wing(sec(0.9, 0, 1.0), sec(0.95, 0.3, 1.0), symmetric=False)  # area .3
    assert facts({"main": main, "fin": big_fin}).has_vertical_tail is True


def test_the_root_of_the_main_wing_is_its_first_rib() -> None:
    swept = wing(sec(0, 0, 0.2), sec(0.5, 0.5, 0.1))  # root trailing edge .2, tip's .6
    assert facts({"main": swept, "fin": fin(0.3)}).has_vertical_tail is True


def test_the_area_weights_chords_by_segment_length() -> None:
    long_segment = wing(sec(0, 0, 0.3), sec(0, 1.0, 0.3))  # area .3
    short_segments = wing(sec(0, 0, 0.2), sec(0, 0.1, 0.2), sec(0, 0.2, 0.2), sec(0, 0.3, 0.2))
    held = facts({"a": long_segment, "b": short_segments, "fin": fin(0.25)})
    assert held.has_vertical_tail is False  # a is main (trailing edge .3), the fin is not behind


def test_sweep_does_not_count_towards_the_planform_area() -> None:
    swept = wing(sec(0, 0, 0.2), sec(1.0, 0.5, 0.2))  # y-z area .1, Euclidean .22
    straight = wing(sec(0, 0, 0.3), sec(0, 0.5, 0.3))  # area .15, trailing edge .3
    assert (
        facts({"swept": swept, "straight": straight, "fin": fin(0.25)}).has_vertical_tail is False
    )


def test_a_missing_given_of_another_namespace_is_written_qualified() -> None:
    model = model_of(
        {"t": quantity("target"), "r": quantity("derived")},
        {"f": formula({"p": "t"}, {"y": "r"}, namespace="other", given=["other:t"])},
        namespace="other",
    )
    node = CanonGraph(model).node(NodeId(formula="other:f", application="default"))
    reason = unmet_condition(node, NONE, set())
    assert reason is not None
    assert "`other:t`" in reason.message


def test_dihedral_counts_towards_the_planform_area() -> None:
    flat = wing(sec(0, 0, 0.2), sec(0, 0.5, 0.2))  # area .1, trailing edge .2
    dihedral = wing(sec(0, 0, 0.3), sec(0, 0.1, 0.3, z=0.5))  # y-z area .153, by y alone .03
    held = facts({"flat": flat, "dihedral": dihedral, "fin": fin(0.25)})
    assert held.has_vertical_tail is False  # the dihedral wing is main, its trailing edge .3


def test_a_pending_term_is_a_declared_not_implemented_error(flight_canon: CanonModel) -> None:
    node = node_of(flight_canon, "roll-rate-cruise", "cruise").model_copy(
        update={"when": "has_horizontal_tail"}
    )
    outcome = unmet_condition(node, ALL, {"cruise-speed-target"})
    assert isinstance(outcome, KernelError)
    assert (outcome.code, outcome.category) == ("not_implemented", ErrorCategory.NOT_IMPLEMENTED)
    assert "has_horizontal_tail" in outcome.message
    assert "#1187" in outcome.hint
    assert (outcome.formula, outcome.application) == ("calc:roll-rate-cruise", "cruise")


def test_every_when_term_has_a_fact_or_is_pending() -> None:
    """The next term added to the vocabulary cannot fall into the gap unannounced."""
    vocabulary = set(get_args(WhenTerm))
    implemented = set(WhenFacts.model_fields)
    assert PENDING_WHEN_TERMS == {"has_horizontal_tail": "#1187"}
    assert not implemented & PENDING_WHEN_TERMS.keys()
    assert vocabulary == implemented | PENDING_WHEN_TERMS.keys()
    for term in implemented:
        assert isinstance(ALL.holds(term), bool)  # type: ignore[arg-type]  # term is a Literal value


def test_holds_refuses_a_pending_term_and_names_the_ticket() -> None:
    with pytest.raises(ValueError, match="#1187"):
        ALL.holds("has_horizontal_tail")


def test_a_pending_when_term_does_not_mask_an_unmet_given() -> None:
    model = model_of(
        {"a": quantity("input"), "b": quantity("output")},
        {"f": formula({"x": "a"}, {"y": "b"}, when="has_horizontal_tail", given=["calc:a"])},
    )
    node = CanonGraph(model).node(NodeId(formula="calc:f", application="default"))
    unmet = unmet_condition(node, facts(None), [])
    assert isinstance(unmet, Reason)
    assert unmet.code is ReasonCode.NOT_GIVEN
    pending = unmet_condition(node, facts(None), ["a"])
    assert isinstance(pending, KernelError)
    assert pending.category is ErrorCategory.NOT_IMPLEMENTED
