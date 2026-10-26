"""The navigator generator shows the evaluation rules as a layer and rejects a table the canon cannot back."""

import importlib.util
import pathlib
from typing import Any

import pytest
from aero_kernel.canon.load import load_canon_model
from aero_kernel.tests.evaluation_builders import rule_of, table_of

REPO = pathlib.Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "build_canon_navigator", REPO / "scripts" / "build_canon_navigator.py"
)
assert _SPEC is not None
assert _SPEC.loader is not None
nav = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(nav)

MODEL = load_canon_model()


def data_of(*slugs: str) -> dict[str, Any]:
    return {"Q": {slug: {} for slug in slugs}}


def test_a_rule_is_listed_with_its_band_source_and_meanings() -> None:
    data = data_of("static-margin-target")
    nav.rule_marks(data, table_of(rule_of()), MODEL)
    (rule,) = data["rules"]["rules"]
    assert rule["id"] == "static-margin"
    assert rule["band"] == {
        "min": 0.05,
        "max": 0.15,
        "min_inclusive": True,
        "max_inclusive": True,
    }
    assert rule["source"].endswith("Eq. (2)")
    assert rule["below"] == "Negative: unstable."
    assert rule["above"] == "Large trim changes with speed."
    assert data["rules"]["source"] == "Drela, Lab 11 Notes"


def test_a_rule_links_to_the_quantity_it_judges() -> None:
    data = data_of("static-margin-target")
    nav.rule_marks(data, table_of(rule_of()), MODEL)
    assert data["rules"]["rules"][0]["quantity"] == {"slug": "static-margin-target"}


def test_a_planned_rule_is_listed_without_a_quantity_node() -> None:
    data = data_of("static-margin-target")
    rule = rule_of(id="later", quantity={"slug": "horizontal-tail-volume", "planned": "#1273"})
    nav.rule_marks(data, table_of(rule), MODEL)
    assert data["rules"]["rules"][0]["quantity"]["planned"] == "#1273"


def test_a_rule_for_a_quantity_the_canon_lacks_is_an_error() -> None:
    data = data_of("static-margin-target")
    table = table_of(rule_of(quantity={"slug": "no-such-quantity"}))
    with pytest.raises(SystemExit):
        nav.rule_marks(data, table, MODEL)


def test_the_shipped_table_is_part_of_the_page_data() -> None:
    _, data = nav.build()
    ids = [rule["id"] for rule in data["rules"]["rules"]]
    assert {"static-margin-design", "static-margin-measured"} <= set(ids)
    assert "turn-sideslip" in ids
