"""Tests for ComputeRequest (ARCHITECTURE ch. 8.11)."""

import inspect
from typing import get_args

import pytest
from aero_kernel import schema
from aero_kernel.schema import Accuracy, AircraftInput, ComputeRequest, Provenance
from pydantic import ValidationError


class TestComputeRequestDefaults:
    def test_defaults_follow_the_architecture(self) -> None:
        request = ComputeRequest(quantities=("stall-speed",))
        assert request.quantities == ("stall-speed",)
        assert request.include_long_runs is False
        assert request.time_budget_s is None
        assert request.accuracy == "xxxlarge"


class TestComputeRequestQuantities:
    def test_empty_slug_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="quantities"):
            ComputeRequest(quantities=("stall-speed", ""))

    def test_duplicate_slug_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match=r"duplicate quantity in request: stall-speed"):
            ComputeRequest(quantities=("stall-speed", "wing-area", "stall-speed"))

    @pytest.mark.parametrize(
        "quantities", [("stall-speed", "calc:stall-speed"), ("calc:stall-speed", "stall-speed")]
    )
    def test_two_spellings_of_one_quantity_are_a_duplicate(
        self, quantities: tuple[str, str]
    ) -> None:
        with pytest.raises(ValidationError) as excinfo:
            ComputeRequest(quantities=quantities)
        first, second = quantities
        assert f"duplicate quantity in request: {second} (the same quantity as {first})" in str(
            excinfo.value
        )

    @pytest.mark.parametrize("slug", ["Stall Speed", "stall_speed", "calc:", "a:b:c"])
    def test_a_malformed_slug_stays_a_per_quantity_matter(self, slug: str) -> None:
        request = ComputeRequest(quantities=(slug, "stall-speed"))
        assert request.quantities == (slug, "stall-speed")

    @pytest.mark.parametrize(
        "pair", [("stall_speed", "calc:stall_speed"), ("Stall Speed", "calc:Stall Speed")]
    )
    def test_a_malformed_slug_is_not_qualified_to_find_duplicates(
        self, pair: tuple[str, str]
    ) -> None:
        assert ComputeRequest(quantities=pair).quantities == pair

    def test_a_malformed_slug_requested_twice_is_a_duplicate(self) -> None:
        with pytest.raises(ValidationError, match=r"duplicate quantity in request: stall_speed"):
            ComputeRequest(quantities=("stall_speed", "stall_speed"))

    def test_the_same_slug_in_another_namespace_is_no_duplicate(self) -> None:
        request = ComputeRequest(quantities=("stall-speed", "other:stall-speed"))
        assert request.quantities == ("stall-speed", "other:stall-speed")


class TestComputeRequestStrictness:
    def test_unknown_accuracy_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="accuracy"):
            ComputeRequest.model_validate({"quantities": ["a"], "accuracy": "huge"})

    def test_unknown_field_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            ComputeRequest.model_validate({"quantities": ["a"], "cache": True})

    def test_accuracy_is_the_alias_of_the_result_types(self) -> None:
        """One definition of the tiers: a redefined Literal could drift from Provenance."""
        assert ComputeRequest.model_fields["accuracy"].annotation is schema.Accuracy
        # typing caches Literal objects, so an identical redefinition would pass the identity
        # check above: the source must name the alias
        assert "accuracy: Accuracy" in inspect.getsource(ComputeRequest)
        assert Provenance.model_fields["accuracy"].annotation is schema.Accuracy

    def test_accuracy_is_the_shared_literal(self) -> None:
        for tier in get_args(Accuracy):
            assert ComputeRequest(quantities=("a",), accuracy=tier).accuracy == tier


class TestComputeRequestShape:
    def test_empty_quantities_are_rejected(self) -> None:
        with pytest.raises(ValidationError, match="quantities"):
            ComputeRequest(quantities=())

    @pytest.mark.parametrize("budget", [0, -1.5])
    def test_non_positive_time_budget_is_rejected(self, budget: float) -> None:
        with pytest.raises(ValidationError, match="time_budget_s"):
            ComputeRequest(quantities=("a",), time_budget_s=budget)

    @pytest.mark.parametrize("budget", [float("inf"), float("nan")])
    def test_non_finite_time_budget_is_rejected(self, budget: float) -> None:
        """Unlimited is spelled None, never infinity."""
        with pytest.raises(ValidationError, match="time_budget_s"):
            ComputeRequest(quantities=("a",), time_budget_s=budget)

    def test_positive_time_budget_is_kept(self) -> None:
        assert ComputeRequest(quantities=("a",), time_budget_s=2.5).time_budget_s == 2.5

    @pytest.mark.parametrize("budget", [True, "5"])
    def test_time_budget_must_be_a_number(self, budget: object) -> None:
        with pytest.raises(ValidationError, match="time_budget_s"):
            ComputeRequest.model_validate({"quantities": ["a"], "time_budget_s": budget})

    def test_long_runs_flag_must_be_a_bool(self) -> None:
        with pytest.raises(ValidationError, match="include_long_runs"):
            ComputeRequest.model_validate({"quantities": ["a"], "include_long_runs": "yes"})


class TestAircraftInput:
    def test_airplane_and_values_parse(self) -> None:
        aircraft = AircraftInput.model_validate(
            {"airplane": {"name": "A"}, "values": {"aircraft-mass": 2, "gravity": 9.81}}
        )
        assert aircraft.airplane.name == "A"
        assert aircraft.values == {"aircraft-mass": 2.0, "gravity": 9.81}

    def test_values_default_to_empty(self) -> None:
        assert AircraftInput.model_validate({"airplane": {"name": "A"}}).values == {}

    def test_non_finite_values_parse(self) -> None:
        aircraft = AircraftInput.model_validate(
            {
                "airplane": {"name": "A"},
                "values": {"aircraft-mass": float("nan"), "altitude": float("inf")},
            }
        )
        assert aircraft.values["altitude"] == float("inf")

    @pytest.mark.parametrize("value", [True, "2.0", None])
    def test_values_must_be_numbers(self, value: object) -> None:
        with pytest.raises(ValidationError, match="aircraft-mass"):
            AircraftInput.model_validate(
                {"airplane": {"name": "A"}, "values": {"aircraft-mass": value}}
            )

    def test_empty_slug_key_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="values"):
            AircraftInput.model_validate({"airplane": {"name": "A"}, "values": {"": 1.0}})

    def test_airplane_is_required_and_unknown_fields_rejected(self) -> None:
        with pytest.raises(ValidationError, match="airplane"):
            AircraftInput.model_validate({"values": {}})
        with pytest.raises(ValidationError, match="extra_forbidden"):
            AircraftInput.model_validate({"airplane": {"name": "A"}, "providers": {}})

    def test_geometry_mass_is_parsed_but_independent_of_values(self) -> None:
        aircraft = AircraftInput.model_validate(
            {"airplane": {"name": "A", "total_mass_kg": 3.0}, "values": {"aircraft-mass": 2.0}}
        )
        assert aircraft.airplane.total_mass_kg == 3.0
        assert aircraft.values["aircraft-mass"] == 2.0
