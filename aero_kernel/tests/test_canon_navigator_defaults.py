"""The navigator generator shows every default with its source and rejects a default it cannot show."""

import importlib.util
import json
import math
import pathlib
from typing import Any

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "build_canon_navigator", REPO / "scripts" / "build_canon_navigator.py"
)
assert _SPEC is not None
assert _SPEC.loader is not None
nav = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(nav)

CHAIN = [("g", "w", "weight"), ("w", "ld", "loading"), ("m", "w", "weight")]


def default(basis: str, value: float = 2.0) -> dict[str, Any]:
    return {
        "value": value,
        "unit": "1",
        "basis": basis,
        "source": f"source of {basis}",
        "regime": "regime-independent",
    }


def make(defaults: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    quantities: dict[str, Any] = {q: {} for q in ("g", "m", "w", "ld", "unrelated")}
    data: dict[str, Any] = {"Q": quantities, "edges": [list(e) for e in CHAIN]}
    return data, {"namespaces": {"calc": {"defaults": defaults}}}


def test_every_default_is_listed_with_its_fields_whatever_its_basis() -> None:
    data, model = make({"g": default("standard"), "m": default("convention")})
    nav.default_marks(data, model)
    assert set(data["defaults"]) == {"g", "m"}
    assert data["defaults"]["g"]["basis"] == "standard"
    assert data["defaults"]["g"]["source"] == "source of standard"
    assert data["defaults"]["g"]["regime"] == "regime-independent"
    assert data["defaults"]["g"]["unit"] == "1"


def test_a_default_lists_the_quantities_and_formulas_that_rest_on_it() -> None:
    data, model = make({"g": default("standard")})
    nav.default_marks(data, model)
    assert data["defaults"]["g"]["quantities"] == ["ld", "w"]
    assert data["defaults"]["g"]["formulas"] == ["loading", "weight"]


def test_the_quantity_itself_is_not_among_what_rests_on_it() -> None:
    data, model = make({"w": default("sourced")})
    nav.default_marks(data, model)
    assert data["defaults"]["w"]["quantities"] == ["ld"]


def test_conventions_stay_the_convention_basis_only() -> None:
    data, model = make({"g": default("standard"), "m": default("convention")})
    nav.default_marks(data, model)
    assert set(data["conventions"]) == {"m"}
    assert set(data["conv"]) == {"m", "w", "ld"}


def test_starting_values_get_their_own_marking_and_are_not_conventions() -> None:
    data, model = make({"g": default("start"), "m": default("convention")})
    nav.default_marks(data, model)
    assert set(data["conventions"]) == {"m"}
    assert set(data["conv"]) == {"m", "w", "ld"}
    assert set(data["starts"]) == {"g"}
    assert set(data["start"]) == {"g", "w", "ld"}
    assert data["start"]["w"] == ["g"]


def test_starting_values_form_their_own_group_in_the_data_source_layer() -> None:
    model = json.loads((REPO / "aero_kernel" / "canon" / "canon_model.json").read_text("utf-8"))
    formulas = {slug: {"status": "draft"} for slug in model["namespaces"]["calc"]["formulas"]}
    data: dict[str, Any] = {"F": formulas}
    nav.approval_marks(data, model)
    assert "start" in {kind["id"] for kind in data["srckinds"]}
    by_id = {source["id"]: source["kind"] for source in data["src"]}
    assert by_id["default:static-margin-target"] == "start"
    assert by_id["default:altitude"] == "start"
    assert by_id["default:gravity"] == "default"


def test_data_source_nodes_carry_the_input_they_refine() -> None:
    model = json.loads((REPO / "aero_kernel" / "canon" / "canon_model.json").read_text("utf-8"))
    quantities = model["namespaces"]["calc"]["quantities"]
    formulas = {slug: {"status": "draft"} for slug in model["namespaces"]["calc"]["formulas"]}
    data: dict[str, Any] = {"F": formulas}
    nav.approval_marks(data, model)
    parents = {source["id"]: source["parent"] for source in data["src"]}
    assert parents["component:battery.capacity_mah"] == "components"
    assert parents["geometry:total_mass_kg"] == "airplane"
    assert parents["default:gravity"] == ""
    # a source that feeds the input itself is that input's root, never its child (no 2-cycle)
    assert parents["component:battery"] == ""
    assert parents["geometry:$"] == ""
    for source in data["src"]:
        if source["kind"] in ("default", "start", "app", "evaluation"):
            assert source["parent"] == "", source["id"]
        assert source["parent"] not in source["qs"], source["id"]
    for source in data["src"]:
        assert source["parent"] in ("", *quantities), source["id"]
        if source["parent"]:
            assert quantities[source["parent"]]["role"] == "input"
    battery = next(s for s in data["src"] if s["id"] == "component:battery.capacity_mah")
    assert "battery-charge-capacity" in battery["qs"]


@pytest.mark.parametrize("basis", ["definition", "standard", "sourced", "convention", "start"])
def test_a_default_of_a_quantity_the_navigator_lacks_fails_for_any_basis(basis: str) -> None:
    data, model = make({"ghost": default(basis)})
    with pytest.raises(SystemExit, match=r"defaults for quantities the canon lacks.*ghost"):
        nav.default_marks(data, model)


def test_binding_constants_are_collected_with_their_source() -> None:
    mf = {
        "stall": {
            "applications": [
                {
                    "id": "clean",
                    "bind": {"m": "calc:m", "n": {"const": 1.0, "source": "definition"}},
                },
                {"id": "inverted", "bind": {"n": {"const": -1.0, "source": "inverted"}}},
            ]
        }
    }
    found = nav.binding_constants(mf)
    assert found["stall"]["clean"] == [{"param": "n", "value": 1.0, "source": "definition"}]
    assert math.isclose(found["stall"]["inverted"][0]["value"], -1.0)


def test_the_real_navigator_shows_all_defaults_and_the_load_factor_constants() -> None:
    model = json.loads((REPO / "aero_kernel/canon/canon_model.json").read_text())
    defaults = model["namespaces"]["calc"]["defaults"]
    _, data = nav.build()
    assert set(data["defaults"]) == set(defaults)
    assert "cell-voltage-nominal" in data["defaults"]
    consts = [c for f in data["F"].values() for a in f["apps"] for c in a["consts"]]
    assert len(consts) >= 6
    assert {c["param"] for c in consts} >= {"n_load"}


def test_the_navigator_carries_stage_two_of_the_approval_per_formula_and_quantity() -> None:
    model = json.loads((REPO / "aero_kernel" / "canon" / "canon_model.json").read_text("utf-8"))
    formulas = {slug: {"status": "approved"} for slug in model["namespaces"]["calc"]["formulas"]}
    data: dict[str, Any] = {"F": formulas}
    nav.approval_marks(data, model)
    stall = data["appr"]["stall-speed"]
    assert stall["s1"] == "approved"
    assert stall["k"] == stall["n"]
    assert stall["missing"] == []
    assert data["qstat"]["aircraft-mass"] == "approved"
    assert data["qdata"]["aircraft-mass"] == ["geometry:total_mass_kg"]


def test_every_missing_input_is_named_with_its_root_cause() -> None:
    model = json.loads((REPO / "aero_kernel" / "canon" / "canon_model.json").read_text("utf-8"))
    formulas = {slug: {"status": "draft"} for slug in model["namespaces"]["calc"]["formulas"]}
    data: dict[str, Any] = {"F": formulas}
    nav.approval_marks(data, model)
    for row in data["appr"].values():
        assert row["k"] + len([m for m in row["missing"] if m["q"]]) == row["n"]
        for missing in row["missing"]:
            assert "no data source" in missing["why"] or "not approved" in missing["why"]


def test_the_navigator_lists_every_data_source_with_what_it_feeds_and_the_missing_ones() -> None:
    model = json.loads((REPO / "aero_kernel" / "canon" / "canon_model.json").read_text("utf-8"))
    formulas = {slug: {"status": "draft"} for slug in model["namespaces"]["calc"]["formulas"]}
    data: dict[str, Any] = {"F": formulas}
    nav.approval_marks(data, model)
    kinds = {kind["id"] for kind in data["srckinds"]}
    assert {source["kind"] for source in data["src"]} <= kinds
    fed = {q for source in data["src"] for q in source["qs"]}
    assert fed == set(data["qdata"])
    assert set(data["miss"]).isdisjoint(fed)
    assert set(data["miss"]) == {q for q, s in data["qstat"].items() if s == "unmapped"}
