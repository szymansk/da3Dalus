"""The role and attachment of the bodies of an aircraft (#1355, slice 1)."""

import math

from aero_kernel.body_attachment import AttachedBody, attachment_defects

MIN_SECTIONS = 2


def _body(
    x: tuple[float, ...] = (0.0, 1.0), role: str = "fuselage", attached_to: str | None = None
) -> AttachedBody:
    return AttachedBody(role=role, attached_to=attached_to, x=x)


def _canopy(
    x: tuple[float, ...] = (0.2, 0.5), attached_to: str | None = "fuselage"
) -> AttachedBody:
    return _body(x, role="canopy", attached_to=attached_to)


def test_a_canopy_on_its_fuselage_is_admissible() -> None:
    bodies = {"fuselage": _body(), "canopy": _canopy()}
    assert attachment_defects(bodies, MIN_SECTIONS) == []


def test_bodies_without_attachment_are_admissible() -> None:
    bodies = {"fuselage": _body(), "nacelle": _body(role="nacelle")}
    assert attachment_defects(bodies, MIN_SECTIONS) == []


def test_a_canopy_flush_with_the_parent_ends_is_inside() -> None:
    bodies = {"fuselage": _body(), "canopy": _canopy((0.0, 1.0))}
    assert attachment_defects(bodies, MIN_SECTIONS) == []


def test_a_body_attached_to_itself_is_refused() -> None:
    defects = attachment_defects({"pod": _body(attached_to="pod")}, MIN_SECTIONS)
    assert [(d.body, d.field, d.code) for d in defects] == [
        ("pod", "attached_to", "invalid_body_attachment")
    ]
    assert "itself" in defects[0].message


def test_an_unknown_parent_is_refused() -> None:
    defects = attachment_defects({"fairing": _body(attached_to="gear")}, MIN_SECTIONS)
    assert [(d.body, d.field, d.code) for d in defects] == [
        ("fairing", "attached_to", "invalid_body_attachment")
    ]
    assert "'gear'" in defects[0].message


def test_a_canopy_without_parent_is_refused() -> None:
    defects = attachment_defects(
        {"fuselage": _body(), "canopy": _canopy(attached_to=None)}, MIN_SECTIONS
    )
    assert [(d.body, d.field, d.code) for d in defects] == [
        ("canopy", "attached_to", "invalid_body_attachment")
    ]
    assert "canopy" in defects[0].message


def test_a_cycle_is_refused_at_every_body_in_it() -> None:
    bodies = {
        "a": _body(attached_to="b"),
        "b": _body(attached_to="c"),
        "c": _body(attached_to="a"),
        "d": _body(attached_to="a"),
    }
    defects = attachment_defects(bodies, MIN_SECTIONS)
    assert [(d.body, d.code) for d in defects] == [
        ("a", "invalid_body_attachment"),
        ("b", "invalid_body_attachment"),
        ("c", "invalid_body_attachment"),
    ]
    assert "a -> b -> c -> a" in defects[0].message


def test_a_canopy_reaching_ahead_of_its_parent_is_refused_at_that_section() -> None:
    bodies = {"fuselage": _body((0.1, 1.0)), "canopy": _canopy((0.3, 0.05, 0.5))}
    defects = attachment_defects(bodies, MIN_SECTIONS)
    assert [(d.body, d.field, d.section, d.code) for d in defects] == [
        ("canopy", "x_secs", 1, "canopy_outside_parent")
    ]
    assert "0.05" in defects[0].message
    assert "0.1" in defects[0].message


def test_a_canopy_reaching_behind_its_parent_is_refused_at_that_section() -> None:
    bodies = {"fuselage": _body(), "canopy": _canopy((0.5, 1.2))}
    defects = attachment_defects(bodies, MIN_SECTIONS)
    assert [(d.field, d.section, d.code) for d in defects] == [
        ("x_secs", 1, "canopy_outside_parent")
    ]


def test_a_canopy_longer_than_its_parent_is_refused_at_both_ends() -> None:
    bodies = {"fuselage": _body((0.2, 0.8)), "canopy": _canopy((0.0, 1.0))}
    defects = attachment_defects(bodies, MIN_SECTIONS)
    assert [d.section for d in defects] == [0, 1]


def test_the_range_is_not_compared_for_a_body_with_too_few_sections() -> None:
    """A body with fewer sections than a loft needs has no x range; too_few_sections says so."""
    bodies = {"fuselage": _body((0.4,)), "canopy": _canopy((0.0, 1.0))}
    assert attachment_defects(bodies, MIN_SECTIONS) == []
    bodies = {"fuselage": _body(), "canopy": _canopy((2.0,))}
    assert attachment_defects(bodies, MIN_SECTIONS) == []


def test_the_range_is_not_compared_for_non_finite_positions() -> None:
    """A NaN position is reported by the walk over the numbers, not as a range defect."""
    bodies = {"fuselage": _body((math.nan, 1.0)), "canopy": _canopy((-1.0, 0.5))}
    assert attachment_defects(bodies, MIN_SECTIONS) == []


def test_a_non_canopy_body_may_reach_beyond_its_parent() -> None:
    bodies = {
        "fuselage": _body(),
        "fairing": _body((0.9, 1.5), role="fairing", attached_to="fuselage"),
    }
    assert attachment_defects(bodies, MIN_SECTIONS) == []


def test_the_range_is_not_compared_against_a_missing_parent() -> None:
    defects = attachment_defects({"canopy": _canopy(attached_to="fuselage")}, MIN_SECTIONS)
    assert [d.code for d in defects] == ["invalid_body_attachment"]


def test_a_canopy_on_a_canopy_is_refused() -> None:
    """Only a body that is no canopy takes a canopy: the merge folds canopies into one parent."""
    bodies = {"fuselage": _body(), "canopy": _canopy(), "hood": _canopy(attached_to="canopy")}
    defects = attachment_defects(bodies, MIN_SECTIONS)
    assert [(d.body, d.field, d.code) for d in defects] == [
        ("hood", "attached_to", "invalid_body_attachment")
    ]
    assert "'canopy', itself a canopy" in defects[0].message


def test_a_nacelle_on_a_canopy_is_admissible() -> None:
    bodies = {"fuselage": _body(), "canopy": _canopy(), "light": _body(attached_to="canopy")}
    assert attachment_defects(bodies, MIN_SECTIONS) == []
