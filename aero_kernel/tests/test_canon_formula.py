"""The formula entries of the canon model: applications, checks, worlds, embeds."""

import copy
from typing import Any

import pytest
from aero_kernel.canon.model import Application, ConstBinding, Formula
from pydantic import ValidationError


def formula_fields() -> dict[str, Any]:
    """Return the fields of a valid single-application law, as a fresh dict."""
    return {
        "kind": "law",
        "tool": "APP",
        "cost": "instant",
        "inputs": {"m": "calc:aircraft-mass", "g": "calc:gravity"},
        "outputs": {"w": "calc:weight"},
        "applications": [
            {
                "id": "default",
                "bind": {"m": "calc:aircraft-mass", "g": "calc:gravity"},
                "produce": {"w": "calc:weight"},
            }
        ],
    }


def make_formula(**overrides: Any) -> Formula:
    """Build a valid formula, with ``overrides`` replacing top-level fields."""
    return Formula.model_validate({**copy.deepcopy(formula_fields()), **overrides})


def test_single_application_law_defaults() -> None:
    formula = make_formula()
    assert formula.uncertainty is None
    assert formula.worlds == ()
    assert formula.embeds == ()
    assert formula.variables == ()
    assert formula.optional == ()
    assert formula.preconditions == ()
    assert formula.application("default").when is None
    assert formula.application("default").given is None


def test_unknown_application_id_is_reported() -> None:
    with pytest.raises(KeyError, match="nope"):
        make_formula().application("nope")


def test_extra_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_formula(tags=["x"])


@pytest.mark.parametrize(
    ("field", "value"),
    [("kind", "magic"), ("tool", "XFOIL"), ("cost", "hours")],
)
def test_closed_vocabularies(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        make_formula(**{field: value})


def test_constant_binding_needs_a_source() -> None:
    fields = formula_fields()
    fields["applications"][0]["bind"]["g"] = {"const": 9.81, "source": "ISO 80000-3"}
    binding = Formula.model_validate(fields).applications[0].bind["g"]
    assert isinstance(binding, ConstBinding)
    assert (binding.const, binding.source) == (9.81, "ISO 80000-3")
    fields["applications"][0]["bind"]["g"] = {"const": 9.81, "source": ""}
    with pytest.raises(ValidationError):
        Formula.model_validate(fields)


def test_reference_must_be_qualified() -> None:
    fields = formula_fields()
    fields["inputs"]["m"] = "aircraft-mass"
    with pytest.raises(ValidationError):
        Formula.model_validate(fields)


def test_parameter_names_are_snake_case() -> None:
    fields = formula_fields()
    fields["inputs"]["Bad-Name"] = None
    with pytest.raises(ValidationError):
        Formula.model_validate(fields)


def test_application_must_bind_every_input_and_nothing_else() -> None:
    fields = formula_fields()
    del fields["applications"][0]["bind"]["g"]
    with pytest.raises(ValidationError, match="bind"):
        Formula.model_validate(fields)
    fields = formula_fields()
    fields["applications"][0]["bind"]["extra"] = "calc:gravity"
    with pytest.raises(ValidationError, match="bind"):
        Formula.model_validate(fields)


def test_application_must_produce_every_output_and_nothing_else() -> None:
    fields = formula_fields()
    fields["applications"][0]["produce"] = {}
    with pytest.raises(ValidationError, match="produce"):
        Formula.model_validate(fields)
    fields = formula_fields()
    fields["applications"][0]["produce"]["extra"] = None
    with pytest.raises(ValidationError, match="produce"):
        Formula.model_validate(fields)


def test_unexposed_output_is_null() -> None:
    fields = formula_fields()
    fields["outputs"]["polar"] = None
    fields["applications"][0]["produce"]["polar"] = None
    assert (
        make_formula(**{k: fields[k] for k in ("outputs", "applications")}).outputs["polar"] is None
    )


def test_application_ids_are_unique_and_at_least_one() -> None:
    fields = formula_fields()
    fields["applications"].append(copy.deepcopy(fields["applications"][0]))
    with pytest.raises(ValidationError, match="unique"):
        Formula.model_validate(fields)
    fields["applications"] = []
    with pytest.raises(ValidationError):
        Formula.model_validate(fields)


def test_when_vocabulary_is_closed() -> None:
    fields = formula_fields()
    fields["applications"][0]["when"] = "has_aileron"
    assert (
        make_formula(applications=fields["applications"]).application("default").when
        == "has_aileron"
    )
    fields["applications"][0]["when"] = "has_wings"
    with pytest.raises(ValidationError):
        Formula.model_validate(fields)


def test_given_is_non_empty_and_bound_by_the_application() -> None:
    fields = formula_fields()
    fields["applications"][0]["given"] = ["calc:gravity"]
    assert Application.model_validate(fields["applications"][0]).given == ("calc:gravity",)
    fields["applications"][0]["given"] = []
    with pytest.raises(ValidationError):
        Formula.model_validate(fields)
    fields["applications"][0]["given"] = ["calc:wingspan"]
    with pytest.raises(ValidationError, match="given"):
        Formula.model_validate(fields)


def test_checks_name_parameters_of_the_right_side() -> None:
    fields = formula_fields()
    fields["preconditions"] = [{"id": "mass_known", "parameter": "m", "on_violation": "warning"}]
    fields["postconditions"] = [{"id": "weight_ok", "parameter": "w", "on_violation": "error"}]
    formula = Formula.model_validate(fields)
    assert formula.preconditions[0].applications is None
    fields["preconditions"][0]["parameter"] = "w"
    with pytest.raises(ValidationError, match="precondition"):
        Formula.model_validate(fields)
    fields["preconditions"][0]["parameter"] = "m"
    fields["postconditions"][0]["parameter"] = "m"
    with pytest.raises(ValidationError, match="postcondition"):
        Formula.model_validate(fields)


def test_check_ids_unique_per_kind_and_applications_exist() -> None:
    fields = formula_fields()
    check = {"id": "c", "parameter": "m", "on_violation": "warning"}
    fields["preconditions"] = [check, dict(check)]
    with pytest.raises(ValidationError, match="unique"):
        Formula.model_validate(fields)
    fields["preconditions"] = [{**check, "applications": ["ghost"]}]
    with pytest.raises(ValidationError, match="ghost"):
        Formula.model_validate(fields)
    fields["preconditions"] = [{**check, "applications": []}]
    with pytest.raises(ValidationError):
        Formula.model_validate(fields)
    fields["preconditions"] = [{**check, "on_violation": "ignore"}]
    with pytest.raises(ValidationError):
        Formula.model_validate(fields)


def test_worlds_exactly_with_interval_uncertainty() -> None:
    formula = make_formula(uncertainty="interval", worlds=["avl", "textbook"])
    assert formula.worlds == ("avl", "textbook")
    with pytest.raises(ValidationError, match="worlds"):
        make_formula(uncertainty="interval")
    with pytest.raises(ValidationError, match="worlds"):
        make_formula(worlds=["avl", "textbook"])


@pytest.mark.parametrize("worlds", [["avl"], ["avl", "avl"], ["avl", "Bad World"]])
def test_worlds_are_two_or_more_unique_snake_case(worlds: list[str]) -> None:
    with pytest.raises(ValidationError):
        make_formula(uncertainty="interval", worlds=worlds)


def test_embeds_need_variables_and_a_closure_that_contains_them() -> None:
    items = ["calc:stall-speed.clean"]
    formula = make_formula(
        embeds=items, variables=["calc:aircraft-mass"], embeds_closure=[*items, "calc:x.default"]
    )
    assert formula.embeds_closure == ("calc:stall-speed.clean", "calc:x.default")
    with pytest.raises(ValidationError, match="variables"):
        make_formula(embeds=items, embeds_closure=items)
    with pytest.raises(ValidationError, match="variables"):
        make_formula(variables=["calc:aircraft-mass"])
    with pytest.raises(ValidationError, match="closure"):
        make_formula(embeds=items, variables=["calc:aircraft-mass"], embeds_closure=[])


def test_embeds_items_are_qualified_with_an_application() -> None:
    with pytest.raises(ValidationError):
        make_formula(
            embeds=["calc:stall-speed"],
            variables=["calc:aircraft-mass"],
            embeds_closure=["calc:stall-speed"],
        )


def test_closure_is_sorted_and_unique() -> None:
    items = ["calc:b.default", "calc:a.default"]
    with pytest.raises(ValidationError, match="sorted"):
        make_formula(embeds=items, variables=["calc:aircraft-mass"], embeds_closure=items)


def test_optional_names_input_parameters() -> None:
    assert make_formula(optional=["m"]).optional == ("m",)
    with pytest.raises(ValidationError, match="optional"):
        make_formula(optional=["w"])


def test_closure_without_embeds_is_rejected() -> None:
    with pytest.raises(ValidationError, match="closure"):
        make_formula(embeds_closure=["calc:x.default"])


def test_closure_that_lacks_the_embedded_item_is_rejected() -> None:
    """A non-empty closure that does not contain the direct embed is a different closure."""
    with pytest.raises(ValidationError, match="contain them"):
        make_formula(
            embeds=["calc:a.default"],
            variables=["calc:aircraft-mass"],
            embeds_closure=["calc:b.default"],
        )


def test_every_model_type_is_frozen() -> None:
    formula = make_formula(preconditions=[{"id": "c", "parameter": "m", "on_violation": "error"}])
    application = formula.applications[0]
    targets = [
        (formula, "kind", "fit"),
        (application, "id", "other"),
        (formula.preconditions[0], "id", "other"),
    ]
    for target, field, value in targets:
        with pytest.raises(ValidationError, match="frozen"):
            setattr(target, field, value)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_const_binding_must_be_finite(bad: float) -> None:
    with pytest.raises(ValidationError, match="finite"):
        ConstBinding.model_validate({"const": bad, "source": "s"})
