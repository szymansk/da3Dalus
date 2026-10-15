"""The closed vocabularies of the canon model, pinned to their exact members (ch. 8.9).

A deliberate change detector: the member lists below are hand-copied from the canon README
"Machine-readable fields" as of #1181 (the units from the quantity entries, normalised). A change
to a vocabulary must change this file in the same commit, and the model's ``schema_version``.
"""

from typing import get_args

import pytest
from aero_kernel.canon import model
from aero_kernel.tests.test_canon_formula import make_formula
from pydantic import ValidationError

VOCABULARIES = {
    "Unit": [
        "1",
        "m",
        "m^2",
        "kg",
        "s",
        "deg",
        "deg/s",
        "m/s",
        "m/s^2",
        "1/s",
        "1/rad",
        "1/rad^2",
        "N",
        "N/m^2",
        "Pa",
        "kg/m^3",
        "W",
        "V",
        "A",
        "ohm",
        "Wh",
        "Wh/kg",
        "rpm/V",
    ],
    "FormulaKind": ["law", "procedure", "optimization", "fit", "rating"],
    "Tool": ["APP", "ATM", "GEO", "AB", "AVL", "OPT", "KAT", "APC"],
    "QuantityRole": ["input", "target", "derived", "output"],
    "QuantityType": ["scalar", "airplane", "curve", "polar", "curve_pair"],
    "WhenTerm": ["has_aileron", "has_separate_flap_and_aileron", "has_vertical_tail"],
    "CostClass": ["instant", "seconds", "minutes"],
    "OnViolation": ["warning", "error"],
}


@pytest.mark.parametrize("name", sorted(VOCABULARIES))
def test_vocabulary_has_exactly_these_members(name: str) -> None:
    members = get_args(getattr(model, name))
    assert len(members) == len(set(members)) == len(VOCABULARIES[name])
    assert set(members) == set(VOCABULARIES[name])


@pytest.mark.parametrize("value", ["point", "Interval", "", "continuous"])
def test_uncertainty_accepts_only_interval(value: str) -> None:
    quantity = {"symbol": "x", "unit": "m", "role": "output", "type": "scalar"}
    assert model.Quantity.model_validate({**quantity, "uncertainty": "interval"}).uncertainty
    with pytest.raises(ValidationError):
        model.Quantity.model_validate({**quantity, "uncertainty": value})
    with pytest.raises(ValidationError):
        make_formula(uncertainty=value, worlds=["a", "b"])
