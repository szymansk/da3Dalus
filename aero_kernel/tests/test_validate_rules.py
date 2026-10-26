"""The thresholds of the validation rules come from the canon and may be overridden (gh-1260)."""

import math
from pathlib import Path
from typing import Any

import pytest
from aero_kernel import compute
from aero_kernel.build import shipped_build
from aero_kernel.canon.model import CanonModel
from aero_kernel.rules import Rules, rule_override_errors
from aero_kernel.schema import AircraftInput
from aero_kernel.tests.canon_builders import base_namespaces, with_hash
from aero_kernel.tests.engine_builders import request
from aero_kernel.validate import validate_aircraft

MODEL = shipped_build().model
RULE = "main-wing-spanwise-extent"
CODE = "main_wing_without_spanwise_extent"


def aircraft(
    *points: tuple[float, float], overrides: dict[str, float] | None = None
) -> AircraftInput:
    """An aircraft whose main wing has sections at the given (y, z) positions."""
    sections = [
        {"xyz_le": [0.0, y, z], "chord": 0.2, "twist": 0.0, "airfoil": "naca2412"}
        for y, z in points
    ]
    wing = {"name": "Main", "surface_type": "main_wing", "x_secs": sections}
    return AircraftInput.model_validate(
        {
            "airplane": {"name": "t", "wings": {"Main": wing}},
            "values": {},
            "rule_overrides": overrides or {},
        }
    )


def codes(found: AircraftInput) -> list[str]:
    return [e.code for e in validate_aircraft(found, Rules(MODEL, found.rule_overrides)).errors]


@pytest.mark.parametrize(
    ("points", "expected"),
    [
        (((0.0, 0.0), (0.5, 0.0)), []),  # flat
        (((0.0, 0.0), (0.5, 0.4)), []),  # 38.7 deg
        (((0.0, 0.0), (0.6, 0.0), (0.62, 0.1)), []),  # a winglet; the whole wing is flat
        (((0.0, 0.0), (-0.5, 0.0)), []),  # stored on the negative side
        (((0.0, 0.0), (0.5, 0.5)), [CODE]),  # exactly 45 deg
        (((0.0, 0.0), (0.0, 0.5)), [CODE]),  # vertical
    ],
)
def test_the_main_wing_inclination_rule(
    points: tuple[tuple[float, float], ...], expected: list[str]
) -> None:
    assert codes(aircraft(*points)) == expected


def test_the_error_names_the_wing_and_the_remedy() -> None:
    found = aircraft((0.0, 0.0), (0.0, 0.5))
    (error,) = validate_aircraft(found, Rules(MODEL)).errors
    assert error.input_path == 'airplane.wings["Main"]'
    assert error.category.value == "invalid_input"
    assert "surface type" in error.hint
    assert error.detail["max_inclination_deg"] == 45.0


def test_an_override_moves_the_threshold_and_is_declared() -> None:
    steep = ((0.0, 0.0), (0.5, 0.8))  # 58 deg
    assert codes(aircraft(*steep)) == [CODE]
    found = aircraft(*steep, overrides={f"{RULE}.max_inclination": 70.0})
    rules = Rules(MODEL, found.rule_overrides)
    assert validate_aircraft(found, rules).errors == ()
    (used,) = [u for u in rules.used() if u.rule == RULE]
    assert (used.value, used.unit, used.basis, used.overridden) == (70.0, "deg", "convention", True)


def test_a_threshold_that_is_not_overridden_is_declared_with_the_canon_value() -> None:
    rules = Rules(MODEL)
    validate_aircraft(aircraft((0.0, 0.0), (0.5, 0.0)), rules)
    by_key = {(u.rule, u.parameter): u for u in rules.used()}
    assert by_key[RULE, "max_inclination"].value == 45.0
    assert not by_key[RULE, "max_inclination"].overridden
    assert by_key["minimum-sections", "min_sections"].value == 2.0


def test_the_section_threshold_comes_from_the_canon() -> None:
    one = aircraft((0.0, 0.0))
    assert "too_few_sections" in codes(one)
    relaxed = aircraft((0.0, 0.0), overrides={"minimum-sections.min_sections": 1.0})
    assert "too_few_sections" not in codes(relaxed)


@pytest.mark.parametrize(
    ("key", "code"),
    [
        ("no-such-rule.x", "unknown_rule_parameter"),
        (f"{RULE}.no_such", "unknown_rule_parameter"),
        (f"{RULE}.max_inclination", "non_finite_number"),
    ],
)
def test_a_bad_override_is_an_input_error(key: str, code: str) -> None:
    value = math.nan if code == "non_finite_number" else 1.0
    (error,) = rule_override_errors({key: value}, MODEL)
    assert (error.code, error.input_path) == (code, f"rule_overrides.{key}")


def pending_model() -> CanonModel:
    """A model whose rules.yaml-equivalent table has a pending parameter (a proposal, not decided)."""
    namespaces = base_namespaces()
    namespaces["calc"]["rules"] = {
        "a-proposal": {
            "applies_to": {"quantity": "aircraft-mass"},
            "kind": "input",
            "on_violation": "error",
            "criterion": "The value stays below a limit that is only proposed.",
            "parameters": {
                "limit": {
                    "value": 5.0,
                    "unit": "kg",
                    "basis": "convention",
                    "status": "pending",
                    "source": "a proposal awaiting the maintainer",
                    "regime": "regime-independent",
                }
            },
        }
    }
    return CanonModel.model_validate(with_hash(namespaces))


def test_overriding_a_pending_parameter_is_an_input_error() -> None:
    (error,) = rule_override_errors({"a-proposal.limit": 1.0}, pending_model())
    assert (error.code, error.input_path) == (
        "rule_parameter_pending",
        "rule_overrides.a-proposal.limit",
    )


def test_a_pending_parameter_is_never_read() -> None:
    rules = Rules(pending_model())
    with pytest.raises(ValueError, match="pending"):
        rules.value("a-proposal", "limit")


def test_the_adopted_probe_tolerance_is_read_as_five_percent_mac() -> None:
    assert Rules(MODEL).value("static-margin-probe-agreement", "agreement_tolerance") == 0.05


@pytest.mark.asyncio
async def test_the_rule_runs_on_every_path_and_the_provenance_names_the_thresholds() -> None:
    """stall-speed alone does not pass through airplane-geometry; the input rule still refuses."""
    vertical = aircraft((0.0, 0.0), (0.0, 0.5))
    result = await compute(vertical, request("stall-speed"))
    assert result.quantities == ()
    assert [e.code for e in result.input_errors] == [CODE]
    assert {(u.rule, u.parameter) for u in result.provenance.rules_used} >= {
        (RULE, "max_inclination")
    }


@pytest.mark.asyncio
async def test_an_overridden_threshold_reaches_the_provenance_of_a_computed_result() -> None:
    steep = aircraft((0.0, 0.0), (0.5, 0.8), overrides={f"{RULE}.max_inclination": 70.0})
    result = await compute(steep, request("wing-reference-area"))
    assert result.input_errors == ()
    (used,) = [u for u in result.provenance.rules_used if u.rule == RULE]
    assert used.overridden
    assert used.value == 70.0


@pytest.mark.asyncio
async def test_a_bad_override_refuses_the_call() -> None:
    bad = aircraft((0.0, 0.0), (0.5, 0.0), overrides={"no-such-rule.x": 1.0})
    result = await compute(bad, request("wing-reference-area"))
    assert [e.code for e in result.input_errors] == ["unknown_rule_parameter"]


def test_every_code_a_rule_names_is_a_code_the_kernel_reports() -> None:
    """Traces the canon's rules into the code: a rule's codes appear as literals in the sources."""
    root = Path(__file__).resolve().parent.parent
    sources = "\n".join(
        path.read_text(encoding="utf-8") for path in root.rglob("*.py") if "tests" not in path.parts
    )
    missing: list[Any] = [
        (rule_id, code)
        for rule_id, rule in MODEL.namespaces["calc"].rules.items()
        for code in rule.codes
        if f'"{code}"' not in sources
    ]
    assert missing == []


def test_the_test_builders_state_the_geometry_rules_as_the_shipped_canon_does() -> None:
    """The rules of hand-made test models must not drift from rules.yaml."""
    from aero_kernel.tests.canon_builders import GEOMETRY_RULES

    shipped = MODEL.namespaces["calc"].rules
    for rule_id, rule in GEOMETRY_RULES.items():
        for name, parameter in rule["parameters"].items():
            canon = shipped[rule_id].parameters[name]
            assert (parameter["value"], parameter["unit"], parameter["basis"]) == (
                canon.value,
                canon.unit,
                canon.basis,
            ), (rule_id, name)
