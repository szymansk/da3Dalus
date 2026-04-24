"""Tests for cad_designer.aerosandbox.classification module.

Covers all three classification functions with boundary values,
interior values, and edge cases for each stability tier.
"""

from __future__ import annotations

import pytest

from cad_designer.aerosandbox.classification import (
    classify_Cl_beta,
    classify_Cm_alpha,
    classify_Cn_beta,
)
from cad_designer.airplane.aircraft_topology.models.analysis_model import (
    ClBetaClassification,
    CmAlphaClassification,
    CnBetaClassification,
    StabilityLevel,
)


# ---------------------------------------------------------------------------
# classify_Cm_alpha
# ---------------------------------------------------------------------------
# Thresholds (all < comparisons):
#   < -0.08  -> STRONGLY_STABLE
#   < -0.04  -> MODERATELY_STABLE
#   < -0.005 -> MARGINALLY_STABLE
#   >= -0.005 -> UNSTABLE

class TestClassifyCmAlpha:
    """Table-driven tests for classify_Cm_alpha."""

    @pytest.mark.parametrize(
        "value, expected_level",
        [
            # Strongly stable — well below -0.08
            (-0.20, StabilityLevel.STRONGLY_STABLE),
            (-0.09, StabilityLevel.STRONGLY_STABLE),
            # Boundary: exactly -0.08 is NOT < -0.08 -> moderately stable
            (-0.08, StabilityLevel.MODERATELY_STABLE),
            # Moderately stable interior
            (-0.06, StabilityLevel.MODERATELY_STABLE),
            (-0.05, StabilityLevel.MODERATELY_STABLE),
            # Boundary: exactly -0.04 is NOT < -0.04 -> marginally stable
            (-0.04, StabilityLevel.MARGINALLY_STABLE),
            # Marginally stable interior
            (-0.02, StabilityLevel.MARGINALLY_STABLE),
            (-0.01, StabilityLevel.MARGINALLY_STABLE),
            # Boundary: exactly -0.005 is NOT < -0.005 -> unstable
            (-0.005, StabilityLevel.UNSTABLE),
            # Unstable
            (0.0, StabilityLevel.UNSTABLE),
            (0.05, StabilityLevel.UNSTABLE),
        ],
        ids=[
            "strongly_stable_deep",
            "strongly_stable_near_boundary",
            "boundary_strongly_to_moderately",
            "moderately_stable_interior_1",
            "moderately_stable_interior_2",
            "boundary_moderately_to_marginally",
            "marginally_stable_interior_1",
            "marginally_stable_interior_2",
            "boundary_marginally_to_unstable",
            "unstable_zero",
            "unstable_positive",
        ],
    )
    def test_classification_level(
        self, value: float, expected_level: StabilityLevel
    ) -> None:
        result = classify_Cm_alpha(value)
        assert isinstance(result, CmAlphaClassification)
        assert result.classification == expected_level
        assert result.value == value
        assert isinstance(result.comment, str)
        assert len(result.comment) > 0


# ---------------------------------------------------------------------------
# classify_Cl_beta
# ---------------------------------------------------------------------------
# Thresholds (all > comparisons):
#   > 0.05   -> STRONGLY_STABLE
#   > 0.02   -> MODERATELY_STABLE
#   > 0.005  -> MARGINALLY_STABLE
#   <= 0.005 -> UNSTABLE

class TestClassifyClBeta:
    """Table-driven tests for classify_Cl_beta."""

    @pytest.mark.parametrize(
        "value, expected_level",
        [
            # Strongly stable
            (0.10, StabilityLevel.STRONGLY_STABLE),
            (0.06, StabilityLevel.STRONGLY_STABLE),
            # Boundary: exactly 0.05 is NOT > 0.05 -> moderately stable
            (0.05, StabilityLevel.MODERATELY_STABLE),
            # Moderately stable interior
            (0.03, StabilityLevel.MODERATELY_STABLE),
            # Boundary: exactly 0.02 is NOT > 0.02 -> marginally stable
            (0.02, StabilityLevel.MARGINALLY_STABLE),
            # Marginally stable interior
            (0.01, StabilityLevel.MARGINALLY_STABLE),
            # Boundary: exactly 0.005 is NOT > 0.005 -> unstable
            (0.005, StabilityLevel.UNSTABLE),
            # Unstable
            (0.0, StabilityLevel.UNSTABLE),
            (-0.05, StabilityLevel.UNSTABLE),
        ],
        ids=[
            "strongly_stable_deep",
            "strongly_stable_near_boundary",
            "boundary_strongly_to_moderately",
            "moderately_stable_interior",
            "boundary_moderately_to_marginally",
            "marginally_stable_interior",
            "boundary_marginally_to_unstable",
            "unstable_zero",
            "unstable_negative",
        ],
    )
    def test_classification_level(
        self, value: float, expected_level: StabilityLevel
    ) -> None:
        result = classify_Cl_beta(value)
        assert isinstance(result, ClBetaClassification)
        assert result.classification == expected_level
        assert result.value == value
        assert isinstance(result.comment, str)
        assert len(result.comment) > 0


# ---------------------------------------------------------------------------
# classify_Cn_beta
# ---------------------------------------------------------------------------
# Thresholds (all > comparisons):
#   > 0.09   -> STRONGLY_STABLE
#   > 0.02   -> MODERATELY_STABLE
#   > 0.0025 -> MARGINALLY_STABLE
#   <= 0.0025 -> UNSTABLE

class TestClassifyCnBeta:
    """Table-driven tests for classify_Cn_beta."""

    @pytest.mark.parametrize(
        "value, expected_level",
        [
            # Strongly stable
            (0.20, StabilityLevel.STRONGLY_STABLE),
            (0.10, StabilityLevel.STRONGLY_STABLE),
            # Boundary: exactly 0.09 is NOT > 0.09 -> moderately stable
            (0.09, StabilityLevel.MODERATELY_STABLE),
            # Moderately stable interior
            (0.05, StabilityLevel.MODERATELY_STABLE),
            # Boundary: exactly 0.02 is NOT > 0.02 -> marginally stable
            (0.02, StabilityLevel.MARGINALLY_STABLE),
            # Marginally stable interior
            (0.01, StabilityLevel.MARGINALLY_STABLE),
            # Boundary: exactly 0.0025 is NOT > 0.0025 -> unstable
            (0.0025, StabilityLevel.UNSTABLE),
            # Unstable
            (0.0, StabilityLevel.UNSTABLE),
            (-0.05, StabilityLevel.UNSTABLE),
        ],
        ids=[
            "strongly_stable_deep",
            "strongly_stable_near_boundary",
            "boundary_strongly_to_moderately",
            "moderately_stable_interior",
            "boundary_moderately_to_marginally",
            "marginally_stable_interior",
            "boundary_marginally_to_unstable",
            "unstable_zero",
            "unstable_negative",
        ],
    )
    def test_classification_level(
        self, value: float, expected_level: StabilityLevel
    ) -> None:
        result = classify_Cn_beta(value)
        assert isinstance(result, CnBetaClassification)
        assert result.classification == expected_level
        assert result.value == value
        assert isinstance(result.comment, str)
        assert len(result.comment) > 0


# ---------------------------------------------------------------------------
# Cross-cutting: return-type consistency
# ---------------------------------------------------------------------------

class TestClassificationReturnTypes:
    """Verify that all classifiers return Pydantic models with the right fields."""

    def test_cm_alpha_is_pydantic_model(self) -> None:
        result = classify_Cm_alpha(-0.06)
        assert hasattr(result, "model_dump")
        dumped = result.model_dump()
        assert set(dumped.keys()) == {"value", "classification", "comment"}

    def test_cl_beta_is_pydantic_model(self) -> None:
        result = classify_Cl_beta(0.03)
        assert hasattr(result, "model_dump")
        dumped = result.model_dump()
        assert set(dumped.keys()) == {"value", "classification", "comment"}

    def test_cn_beta_is_pydantic_model(self) -> None:
        result = classify_Cn_beta(0.05)
        assert hasattr(result, "model_dump")
        dumped = result.model_dump()
        assert set(dumped.keys()) == {"value", "classification", "comment"}
