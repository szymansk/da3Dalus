"""The fixture canon models: valid against schema and types, and meaningful for later units."""

import json
from pathlib import Path

import jsonschema
import pytest
from aero_kernel.canon.load import load_canon_model
from aero_kernel.canon.model import CanonModel, ConstBinding, Formula
from aero_kernel.canon.schema_file import SCHEMA_PATH
from aero_kernel.tests.fixtures.build import FIXTURE_PATH, build_flight_canon

FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.json"))


@pytest.mark.parametrize("path", FIXTURES, ids=lambda path: path.name)
def test_fixture_is_valid_against_schema_and_types(path: Path) -> None:
    document = json.loads(path.read_text(encoding="utf-8"))
    jsonschema.validate(document, json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
    assert load_canon_model(path).content_hash == document["content_hash"]


def formulas(model: CanonModel) -> dict[str, Formula]:
    """The formulas of the ``calc`` namespace."""
    return model.namespaces["calc"].formulas


def test_flight_canon_has_several_applications(flight_canon: CanonModel) -> None:
    stall = formulas(flight_canon)["stall-speed"]
    assert [a.id for a in stall.applications] == ["clean", "landing", "inverted"]
    assert stall.application("inverted").produce["v_s"] is None


def test_flight_canon_has_when_and_given(flight_canon: CanonModel) -> None:
    application = formulas(flight_canon)["roll-rate-cruise"].application("cruise")
    assert application.when == "has_aileron"
    assert application.given == ("calc:cruise-speed-target",)


def test_flight_canon_has_scoped_pre_and_postconditions(flight_canon: CanonModel) -> None:
    stall = formulas(flight_canon)["stall-speed"]
    assert stall.preconditions[0].applications is None
    assert {c.id: c.applications for c in stall.preconditions}["landing_configuration_given"] == (
        "landing",
    )
    scoped = {c.id: c.applications for c in stall.postconditions}
    assert scoped["optimum_at_first_cl_peak"] == ("clean", "landing")
    assert scoped["cl_max_at_stall_reynolds_number"] is None


def test_flight_canon_has_embeds_with_variables(flight_canon: CanonModel) -> None:
    embedder = formulas(flight_canon)["max-mass-level-flight"]
    assert embedder.embeds == embedder.embeds_closure == ("calc:stall-speed.clean",)
    assert embedder.variables == ("calc:aircraft-mass",)
    assert embedder.cost == "minutes"


def test_flight_canon_has_worlds_and_an_optional_parameter(flight_canon: CanonModel) -> None:
    neutral_point = formulas(flight_canon)["neutral-point"]
    assert neutral_point.worlds == ("textbook", "pappas", "avl")
    assert formulas(flight_canon)["airplane-configuration"].optional == ("flap_deflection",)


def test_flight_canon_has_positive_and_non_scalar_quantities(flight_canon: CanonModel) -> None:
    mass = flight_canon.quantity("aircraft-mass")
    assert mass is not None
    assert mass.positive
    kinds = {q.type for q in flight_canon.namespaces["calc"].quantities.values()}
    assert kinds == {"scalar", "airplane", "curve", "polar", "curve_pair"}


def test_flight_canon_has_a_target_default_and_a_const_binding(flight_canon: CanonModel) -> None:
    target = flight_canon.quantity("approach-speed-margin-target")
    assert target is not None
    assert target.role == "target"
    assert "approach-speed-margin-target" in flight_canon.namespaces["calc"].defaults
    clean = formulas(flight_canon)["stall-speed"].application("clean")
    n_load = clean.bind["n_load"]
    assert isinstance(n_load, ConstBinding)
    assert n_load.const == 1


def test_committed_fixture_equals_the_built_one() -> None:
    assert FIXTURE_PATH.read_text(encoding="utf-8") == build_flight_canon(), (
        "flight_canon.json is stale: run `python -m aero_kernel.tests.fixtures.build`"
    )


def test_absent_conditions_are_stored_as_explicit_null(flight_canon: CanonModel) -> None:
    """ch. 8.9: ``when``, ``given`` and a check's ``applications`` absent are written as null."""
    document = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    stall = document["namespaces"]["calc"]["formulas"]["stall-speed"]
    assert stall["applications"][0]["when"] is None
    assert stall["applications"][0]["given"] is None
    assert stall["preconditions"][0]["applications"] is None
    assert stall["postconditions"][0]["applications"] is None
