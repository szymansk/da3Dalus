"""Tests for ComputeRequest (ARCHITECTURE ch. 8.11)."""

import pytest
from aero_kernel.schema import AircraftInput, ComputeRequest
from pydantic import ValidationError


class TestComputeRequestDefaults:
    def test_defaults_follow_the_architecture(self) -> None:
        request = ComputeRequest(quantities=("stall-speed",))
        assert request.quantities == ("stall-speed",)
        assert request.include_long_runs is False


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
    def test_unknown_field_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            ComputeRequest.model_validate({"quantities": ["a"], "cache": True})


class TestComputeRequestShape:
    def test_empty_quantities_are_rejected(self) -> None:
        with pytest.raises(ValidationError, match="quantities"):
            ComputeRequest(quantities=())

    def test_time_budget_is_not_a_field_yet(self) -> None:
        """It comes back with the solver path (ch. 8.10); no field without behaviour."""
        assert "time_budget_s" not in ComputeRequest.model_fields
        with pytest.raises(ValidationError, match="extra_forbidden"):
            ComputeRequest.model_validate({"quantities": ["a"], "time_budget_s": 2.5})

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


class TestComputeRequestFields:
    def test_the_fields_are_exactly_these(self) -> None:
        assert sorted(ComputeRequest.model_fields) == ["include_long_runs", "quantities"]

    def test_accuracy_is_no_field_any_more(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            ComputeRequest.model_validate({"quantities": ["a"], "accuracy": "medium"})
