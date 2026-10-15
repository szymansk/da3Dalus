"""Tests for ComputeRequest (ARCHITECTURE ch. 8.11)."""

from typing import get_args

import pytest
from aero_kernel.schema import Accuracy, ComputeRequest
from pydantic import ValidationError


class TestComputeRequestDefaults:
    def test_defaults_follow_the_architecture(self) -> None:
        request = ComputeRequest(quantities=("stall-speed",))
        assert request.quantities == ("stall-speed",)
        assert request.include_long_runs is False
        assert request.time_budget_s is None
        assert request.accuracy == "xxxlarge"


class TestComputeRequestQuantities:
    def test_duplicate_slug_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match=r"duplicate quantity in request: stall-speed"):
            ComputeRequest(quantities=("stall-speed", "wing-area", "stall-speed"))


class TestComputeRequestStrictness:
    def test_unknown_accuracy_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="accuracy"):
            ComputeRequest.model_validate({"quantities": ["a"], "accuracy": "huge"})

    def test_unknown_field_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            ComputeRequest.model_validate({"quantities": ["a"], "cache": True})

    def test_accuracy_is_the_shared_literal(self) -> None:
        for tier in get_args(Accuracy):
            assert ComputeRequest(quantities=("a",), accuracy=tier).accuracy == tier
