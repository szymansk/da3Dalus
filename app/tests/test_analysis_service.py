"""Tests for app.services.analysis_service — helper functions and async orchestration.

Focuses on the pure helper functions (_safe_slice, _compute_cl_cd_points, etc.)
which are independently testable without aerodynamic backends, plus mocked
tests for the async orchestration functions.
"""

from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.core.exceptions import InternalError, NotFoundError
from app.db.exceptions import NotFoundInDbException
from app.services.analysis_service import (
    _classify_longitudinal_stability,
    _classify_variation,
    _compute_alpha_sweep_characteristic_points,
    _compute_cl_cd_points,
    _compute_trim_point,
    _extract_alpha_sweep_arrays,
    _find_stall_point,
    _interpolate_zero_crossing,
    _safe_slice,
    get_aeroplane_schema_or_raise,
    get_wing_schema_or_raise,
)


# =========================================================================
# _safe_slice
# =========================================================================


class TestSafeSlice:
    """Tests for _safe_slice — align arrays to shortest length."""

    def test_equal_length_arrays(self):
        a = np.array([1, 2, 3])
        b = np.array([4, 5, 6])
        result = _safe_slice(a, b)
        assert result is not None
        np.testing.assert_array_equal(result[0], a)
        np.testing.assert_array_equal(result[1], b)

    def test_unequal_length_arrays_truncates_to_shortest(self):
        a = np.array([1, 2, 3, 4, 5])
        b = np.array([10, 20, 30])
        result = _safe_slice(a, b)
        assert result is not None
        assert len(result[0]) == 3
        assert len(result[1]) == 3
        np.testing.assert_array_equal(result[0], np.array([1, 2, 3]))

    def test_three_arrays_unequal(self):
        a = np.array([1, 2, 3, 4])
        b = np.array([5, 6])
        c = np.array([7, 8, 9])
        result = _safe_slice(a, b, c)
        assert result is not None
        assert all(len(r) == 2 for r in result)

    def test_returns_none_when_any_input_is_none(self):
        a = np.array([1, 2, 3])
        assert _safe_slice(a, None) is None
        assert _safe_slice(None, a) is None
        assert _safe_slice(None, None) is None

    def test_returns_none_for_empty_array(self):
        a = np.array([])
        b = np.array([1, 2])
        assert _safe_slice(a, b) is None

    def test_single_element_arrays(self):
        a = np.array([42.0])
        b = np.array([99.0])
        result = _safe_slice(a, b)
        assert result is not None
        assert len(result[0]) == 1
        assert float(result[0][0]) == 42.0


# =========================================================================
# _extract_alpha_sweep_arrays
# =========================================================================


class TestExtractAlphaSweepArrays:
    """Tests for _extract_alpha_sweep_arrays."""

    def _make_sweep_request(self, start=-5.0, end=15.0, num=5):
        from app.schemas.AeroplaneRequest import AlphaSweepRequest

        return AlphaSweepRequest.model_construct(
            altitude=0.0,
            velocity=20.0,
            alpha_start=start,
            alpha_end=end,
            alpha_num=num,
            beta=0.0,
            p=0.0,
            q=0.0,
            r=0.0,
            xyz_ref=[0, 0, 0],
        )

    def test_extracts_from_result_with_all_coefficients(self):
        result = SimpleNamespace(
            flight_condition=SimpleNamespace(alpha=np.array([0.0, 5.0, 10.0])),
            coefficients=SimpleNamespace(
                CL=np.array([0.1, 0.5, 0.9]),
                CD=np.array([0.01, 0.02, 0.05]),
                Cm=np.array([-0.05, -0.02, 0.01]),
            ),
        )
        sr = self._make_sweep_request()
        alpha, cl, cd, cm = _extract_alpha_sweep_arrays(result, sr)

        np.testing.assert_array_equal(alpha, np.array([0.0, 5.0, 10.0]))
        assert cl is not None
        assert cd is not None
        assert cm is not None

    def test_falls_back_to_linspace_when_flight_condition_is_none(self):
        result = SimpleNamespace(
            flight_condition=None,
            coefficients=SimpleNamespace(CL=None, CD=None, Cm=None),
        )
        sr = self._make_sweep_request(start=0.0, end=10.0, num=3)
        alpha, cl, cd, cm = _extract_alpha_sweep_arrays(result, sr)

        np.testing.assert_allclose(alpha, np.array([0.0, 5.0, 10.0]))
        assert cl is None
        assert cd is None
        assert cm is None

    def test_missing_alpha_on_flight_condition_falls_back(self):
        result = SimpleNamespace(
            flight_condition=SimpleNamespace(alpha=None),
            coefficients=SimpleNamespace(CL=None, CD=None, Cm=None),
        )
        sr = self._make_sweep_request(start=-2.0, end=2.0, num=5)
        alpha, cl, cd, cm = _extract_alpha_sweep_arrays(result, sr)

        assert len(alpha) == 5
        assert cl is None

    def test_partial_coefficients(self):
        result = SimpleNamespace(
            flight_condition=SimpleNamespace(alpha=[1.0, 2.0]),
            coefficients=SimpleNamespace(
                CL=[0.2, 0.4],
                CD=None,
                Cm=[0.01, 0.02],
            ),
        )
        sr = self._make_sweep_request()
        alpha, cl, cd, cm = _extract_alpha_sweep_arrays(result, sr)

        assert cl is not None
        assert cd is None
        assert cm is not None


# =========================================================================
# _compute_cl_cd_points
# =========================================================================


class TestComputeClCdPoints:
    """Tests for _compute_cl_cd_points — characteristic aerodynamic points."""

    def test_basic_characteristic_points(self):
        alpha = np.linspace(-5, 15, 21)
        # Simple linear CL, quadratic CD
        cl = 0.1 * alpha
        cd = 0.01 + 0.001 * alpha**2

        points = _compute_cl_cd_points(alpha, cl, cd, len(alpha))

        # Should have the expected keys
        assert "maximum_lift_to_drag_ratio_point" in points
        assert "minimum_drag_coefficient_point" in points
        assert "maximum_lift_coefficient_point" in points
        assert "drag_at_zero_lift_point" in points
        assert "stall_point" in points

    def test_clmax_is_at_highest_cl(self):
        alpha = np.array([0.0, 5.0, 10.0, 15.0, 12.0])
        cl = np.array([0.0, 0.5, 1.0, 0.8, 0.9])
        cd = np.array([0.01, 0.02, 0.04, 0.06, 0.05])

        points = _compute_cl_cd_points(alpha, cl, cd, len(alpha))

        clmax_point = points["maximum_lift_coefficient_point"]
        assert clmax_point["CL"] == 1.0
        assert clmax_point["index"] == 2

    def test_cdmin_is_at_lowest_cd(self):
        alpha = np.array([-5.0, 0.0, 5.0, 10.0])
        cl = np.array([-0.5, 0.0, 0.5, 1.0])
        cd = np.array([0.02, 0.005, 0.01, 0.03])

        points = _compute_cl_cd_points(alpha, cl, cd, len(alpha))

        cdmin_point = points["minimum_drag_coefficient_point"]
        assert cdmin_point["CD"] == 0.005
        assert cdmin_point["index"] == 1

    def test_ldmax_computed_correctly(self):
        alpha = np.array([0.0, 5.0, 10.0])
        cl = np.array([0.0, 0.5, 0.8])
        cd = np.array([0.01, 0.02, 0.10])
        # L/D = [0, 25, 8] -> max at index 1

        points = _compute_cl_cd_points(alpha, cl, cd, len(alpha))

        ldmax = points["maximum_lift_to_drag_ratio_point"]
        assert ldmax["index"] == 1
        assert abs(ldmax["lift_to_drag_ratio"] - 25.0) < 1e-6

    def test_handles_zero_cd(self):
        """When CD contains zeros, L/D should use nan safely."""
        alpha = np.array([0.0, 5.0])
        cl = np.array([0.5, 1.0])
        cd = np.array([0.0, 0.02])

        # Should not raise
        points = _compute_cl_cd_points(alpha, cl, cd, len(alpha))
        assert "maximum_lift_to_drag_ratio_point" in points


# =========================================================================
# _interpolate_zero_crossing
# =========================================================================


class TestInterpolateZeroCrossing:
    """Tests for _interpolate_zero_crossing — find drag at zero lift."""

    def test_exact_zero_crossing(self):
        alpha = np.array([-5.0, 0.0, 5.0, 10.0])
        cl = np.array([-0.5, 0.0, 0.5, 1.0])
        cd = np.array([0.02, 0.01, 0.02, 0.05])

        result = _interpolate_zero_crossing(alpha, cl, cd)
        # Should find crossing between index 0 and 1 (signs differ)
        assert result["CL"] == 0.0
        assert result["index"] is None  # interpolated

    def test_interpolated_crossing(self):
        alpha = np.array([-5.0, 5.0, 10.0])
        cl = np.array([-0.5, 0.5, 1.0])
        cd = np.array([0.02, 0.03, 0.05])

        result = _interpolate_zero_crossing(alpha, cl, cd)
        assert result["CL"] == 0.0
        # Alpha should be interpolated to 0.0
        assert abs(result["alpha_deg"] - 0.0) < 1e-6

    def test_no_sign_change_uses_nearest(self):
        """When CL never crosses zero, use closest point."""
        alpha = np.array([5.0, 10.0, 15.0])
        cl = np.array([0.3, 0.5, 0.8])  # all positive
        cd = np.array([0.01, 0.02, 0.05])

        result = _interpolate_zero_crossing(alpha, cl, cd)
        # Nearest to zero is index 0 (cl=0.3)
        assert result["index"] == 0
        assert result["CL"] == 0.3

    def test_all_negative_cl(self):
        alpha = np.array([-10.0, -5.0, 0.0])
        cl = np.array([-1.0, -0.5, -0.1])
        cd = np.array([0.05, 0.02, 0.01])

        result = _interpolate_zero_crossing(alpha, cl, cd)
        # Nearest to zero is index 2
        assert result["index"] == 2


# =========================================================================
# _find_stall_point
# =========================================================================


class TestFindStallPoint:
    """Tests for _find_stall_point."""

    def test_clear_stall_after_clmax(self):
        alpha = np.array([0.0, 5.0, 10.0, 15.0, 20.0])
        cl = np.array([0.0, 0.5, 1.0, 0.9, 0.7])  # stall after index 2
        cd = np.array([0.01, 0.02, 0.04, 0.06, 0.10])

        result = _find_stall_point(alpha, cl, cd, len(alpha))
        # CL drops and CD rises at index 3
        assert result["index"] == 3
        assert result["CL"] == 0.9

    def test_clmax_at_last_point_no_stall(self):
        """When CLmax is at the last index, stall point equals CLmax."""
        alpha = np.array([0.0, 5.0, 10.0])
        cl = np.array([0.0, 0.5, 1.0])
        cd = np.array([0.01, 0.02, 0.04])

        result = _find_stall_point(alpha, cl, cd, len(alpha))
        assert result["index"] == 2  # CLmax is at end, so stall = CLmax

    def test_flat_cl_after_max(self):
        """When CL doesn't drop after max, stall falls back to CLmax+1."""
        alpha = np.array([0.0, 5.0, 10.0, 15.0])
        cl = np.array([0.0, 0.5, 1.0, 1.0])  # flat after max
        cd = np.array([0.01, 0.02, 0.04, 0.06])

        result = _find_stall_point(alpha, cl, cd, len(alpha))
        # CL[3] is not < CL[2], so for-else triggers i_clmax + 1
        assert result["index"] == 3

    def test_single_point(self):
        alpha = np.array([5.0])
        cl = np.array([0.5])
        cd = np.array([0.02])

        result = _find_stall_point(alpha, cl, cd, 1)
        assert result["index"] == 0


# =========================================================================
# _compute_trim_point
# =========================================================================


class TestComputeTrimPoint:
    """Tests for _compute_trim_point — find where Cm crosses zero."""

    def test_cm_crosses_zero(self):
        alpha = np.array([-5.0, 0.0, 5.0, 10.0])
        cl = np.array([-0.5, 0.0, 0.5, 1.0])
        cm = np.array([0.05, 0.02, -0.01, -0.04])
        cd = np.array([0.02, 0.01, 0.02, 0.05])

        result = _compute_trim_point(alpha, cl, cm, cd)
        assert result["Cm"] == 0.0  # interpolated to zero
        assert result["index"] is None  # interpolated

    def test_cm_never_crosses_zero(self):
        alpha = np.array([0.0, 5.0, 10.0])
        cl = np.array([0.1, 0.5, 1.0])
        cm = np.array([0.1, 0.2, 0.3])  # all positive
        cd = np.array([0.01, 0.02, 0.05])

        result = _compute_trim_point(alpha, cl, cm, cd)
        # Falls back to nearest-to-zero: index 0 (cm=0.1)
        assert result["index"] == 0
        assert result["Cm"] == pytest.approx(0.1)

    def test_no_cd_values(self):
        alpha = np.array([-5.0, 5.0])
        cl = np.array([-0.3, 0.3])
        cm = np.array([0.05, -0.05])

        result = _compute_trim_point(alpha, cl, cm, cd_values=None)
        assert result["CD"] is None

    def test_cd_interpolated_at_crossing(self):
        alpha = np.array([0.0, 10.0])
        cl = np.array([0.0, 1.0])
        cm = np.array([0.1, -0.1])  # crosses at midpoint
        cd = np.array([0.01, 0.03])

        result = _compute_trim_point(alpha, cl, cm, cd)
        # t = 0.5 -> CD = 0.01 + 0.5 * (0.03 - 0.01) = 0.02
        assert result["CD"] == pytest.approx(0.02)
        assert result["CL"] == pytest.approx(0.5)
        assert result["alpha_deg"] == pytest.approx(5.0)


# =========================================================================
# _compute_alpha_sweep_characteristic_points
# =========================================================================


class TestComputeAlphaSweepCharacteristicPoints:
    """Tests for the top-level orchestrator of characteristic points."""

    def test_all_none_returns_all_none_points(self):
        alpha = np.array([0.0, 5.0, 10.0])
        points = _compute_alpha_sweep_characteristic_points(alpha, None, None, None)

        assert points["maximum_lift_to_drag_ratio_point"] is None
        assert points["minimum_drag_coefficient_point"] is None
        assert points["maximum_lift_coefficient_point"] is None
        assert points["drag_at_zero_lift_point"] is None
        assert points["stall_point"] is None
        assert points["trim_point_cm_equals_zero"] is None

    def test_with_cl_and_cd(self):
        alpha = np.linspace(-5, 15, 21)
        cl = 0.1 * alpha
        cd = 0.01 + 0.001 * alpha**2

        points = _compute_alpha_sweep_characteristic_points(alpha, cl, cd, None)

        assert points["maximum_lift_coefficient_point"] is not None
        assert points["minimum_drag_coefficient_point"] is not None
        assert points["trim_point_cm_equals_zero"] is None  # no Cm

    def test_with_cl_cd_and_cm(self):
        alpha = np.linspace(-5, 15, 21)
        cl = 0.1 * alpha
        cd = 0.01 + 0.001 * alpha**2
        cm = -0.01 * alpha + 0.05

        points = _compute_alpha_sweep_characteristic_points(alpha, cl, cd, cm)

        assert points["trim_point_cm_equals_zero"] is not None


# =========================================================================
# _classify_longitudinal_stability
# =========================================================================


class TestClassifyLongitudinalStability:
    """Tests for _classify_longitudinal_stability."""

    def test_stable_negative_slope(self):
        alpha = np.array([0.0, 5.0, 10.0, 15.0])
        cm = np.array([0.10, 0.05, -0.02, -0.10])  # negative slope

        label, color = _classify_longitudinal_stability(cm, alpha)
        assert "Stable" in label
        assert color == "tab:green"

    def test_unstable_positive_slope(self):
        alpha = np.array([0.0, 5.0, 10.0, 15.0])
        cm = np.array([-0.10, -0.05, 0.02, 0.10])  # positive slope

        label, color = _classify_longitudinal_stability(cm, alpha)
        assert "Unstable" in label
        assert color == "tab:red"

    def test_neutral_near_zero_slope(self):
        alpha = np.array([0.0, 5.0, 10.0, 15.0])
        cm = np.array([0.01, 0.01, 0.01, 0.01])  # near-zero slope

        label, color = _classify_longitudinal_stability(cm, alpha)
        assert "Neutral" in label
        assert color == "tab:orange"

    def test_none_cm_returns_na(self):
        alpha = np.array([0.0, 5.0])
        label, color = _classify_longitudinal_stability(None, alpha)
        assert label == "N/A"
        assert color == "gray"

    def test_single_point_returns_na(self):
        alpha = np.array([5.0])
        cm = np.array([0.02])
        label, color = _classify_longitudinal_stability(cm, alpha)
        assert label == "N/A"
        assert color == "gray"

    def test_non_finite_values_handled(self):
        alpha = np.array([0.0, 5.0, 10.0])
        cm = np.array([np.nan, np.nan, np.nan])

        label, color = _classify_longitudinal_stability(cm, alpha)
        assert label == "N/A"
        assert color == "gray"


# =========================================================================
# _classify_variation
# =========================================================================


class TestClassifyVariation:
    """Tests for _classify_variation — robustness classification."""

    def test_robust_low_span(self):
        series = np.array([1.0, 1.1, 1.2, 1.0])  # span = 0.2
        label, color = _classify_variation(series, "Xnp")
        assert "robust" in label
        assert color == "tab:green"

    def test_moderate_span(self):
        series = np.array([1.0, 1.5, 2.0, 1.8])  # span = 1.0
        label, color = _classify_variation(series, "Xnp")
        assert "moderate" in label
        assert color == "tab:orange"

    def test_volatile_high_span(self):
        series = np.array([0.0, 5.0, 10.0, 0.5])  # span = 10.0
        label, color = _classify_variation(series, "Xnp_lat")
        assert "volatile" in label
        assert color == "tab:red"

    def test_none_series_returns_na(self):
        label, color = _classify_variation(None, "test")
        assert "N/A" in label
        assert color == "gray"

    def test_single_element_returns_na(self):
        label, color = _classify_variation(np.array([1.0]), "test")
        assert "N/A" in label
        assert color == "gray"

    def test_all_nan_returns_na(self):
        series = np.array([np.nan, np.nan, np.nan])
        label, color = _classify_variation(series, "test")
        assert "N/A" in label
        assert color == "gray"

    def test_label_included_in_output(self):
        series = np.array([1.0, 1.1])
        label, _ = _classify_variation(series, "MyLabel")
        assert "MyLabel" in label


# =========================================================================
# get_aeroplane_schema_or_raise
# =========================================================================


class TestGetAeroplaneSchemaOrRaise:
    """Tests for get_aeroplane_schema_or_raise."""

    def test_returns_schema_on_success(self):
        mock_db = MagicMock()
        expected = MagicMock()
        test_uuid = uuid.uuid4()

        with patch(
            "app.services.analysis_service.get_aeroplane_by_id",
            return_value=expected,
        ) as mock_get:
            result = get_aeroplane_schema_or_raise(mock_db, test_uuid)

        assert result is expected
        mock_get.assert_called_once_with(test_uuid, mock_db)

    def test_raises_not_found_error_on_missing(self):
        mock_db = MagicMock()
        test_uuid = uuid.uuid4()

        with patch(
            "app.services.analysis_service.get_aeroplane_by_id",
            side_effect=NotFoundInDbException("not found"),
        ):
            with pytest.raises(NotFoundError) as exc_info:
                get_aeroplane_schema_or_raise(mock_db, test_uuid)

        assert str(test_uuid) in exc_info.value.details.get("aeroplane_id", "")

    def test_raises_internal_error_on_db_error(self):
        from sqlalchemy.exc import SQLAlchemyError

        mock_db = MagicMock()
        test_uuid = uuid.uuid4()

        with patch(
            "app.services.analysis_service.get_aeroplane_by_id",
            side_effect=SQLAlchemyError("connection lost"),
        ):
            with pytest.raises(InternalError):
                get_aeroplane_schema_or_raise(mock_db, test_uuid)


# =========================================================================
# get_wing_schema_or_raise
# =========================================================================


class TestGetWingSchemaOrRaise:
    """Tests for get_wing_schema_or_raise."""

    def test_returns_schema_on_success(self):
        mock_db = MagicMock()
        expected = MagicMock()
        test_uuid = uuid.uuid4()

        with patch(
            "app.services.analysis_service.get_wing_by_name_and_aeroplane_id",
            return_value=expected,
        ) as mock_get:
            result = get_wing_schema_or_raise(mock_db, test_uuid, "main_wing")

        assert result is expected
        mock_get.assert_called_once_with(test_uuid, "main_wing", mock_db)

    def test_raises_not_found_error_on_missing(self):
        mock_db = MagicMock()
        test_uuid = uuid.uuid4()

        with patch(
            "app.services.analysis_service.get_wing_by_name_and_aeroplane_id",
            side_effect=NotFoundInDbException("wing not found"),
        ):
            with pytest.raises(NotFoundError) as exc_info:
                get_wing_schema_or_raise(mock_db, test_uuid, "main_wing")

        assert exc_info.value.details.get("wing_name") == "main_wing"

    def test_raises_internal_error_on_db_error(self):
        from sqlalchemy.exc import SQLAlchemyError

        mock_db = MagicMock()
        test_uuid = uuid.uuid4()

        with patch(
            "app.services.analysis_service.get_wing_by_name_and_aeroplane_id",
            side_effect=SQLAlchemyError("timeout"),
        ):
            with pytest.raises(InternalError):
                get_wing_schema_or_raise(mock_db, test_uuid, "main_wing")


# =========================================================================
# analyze_wing (async orchestration)
# =========================================================================


class TestAnalyzeWing:
    """Tests for analyze_wing — async orchestration with mocks."""

    def test_success_path(self):
        from app.schemas.AeroplaneRequest import AnalysisToolUrlType
        from app.schemas.aeroanalysisschema import OperatingPointSchema
        from app.services.analysis_service import analyze_wing

        mock_db = MagicMock()
        test_uuid = uuid.uuid4()
        mock_schema = MagicMock()
        mock_asb_airplane = MagicMock()
        mock_asb_airplane.wings = [
            MagicMock(name="target_wing"),
            MagicMock(name="other_wing"),
        ]
        mock_result = MagicMock()
        op = OperatingPointSchema.model_construct(
            velocity=20.0, alpha=5.0, beta=0.0,
            p=0.0, q=0.0, r=0.0, xyz_ref=[0.0, 0.0, 0.0],
        )

        with (
            patch(
                "app.services.analysis_service.get_wing_schema_or_raise",
                return_value=mock_schema,
            ),
            patch(
                "app.services.analysis_service.aeroplane_schema_to_asb_airplane_async",
                return_value=mock_asb_airplane,
            ),
            patch(
                "app.services.analysis_service.analyse_aerodynamics",
                return_value=(mock_result, None),
            ),
        ):
            result = asyncio.run(
                analyze_wing(mock_db, test_uuid, "target_wing", op, AnalysisToolUrlType.AEROBUILDUP)
            )

        assert result is mock_result
        # Verify fuselages cleared and wings filtered
        assert mock_asb_airplane.fuselages == []

    def test_raises_internal_error_on_analysis_failure(self):
        from app.schemas.AeroplaneRequest import AnalysisToolUrlType
        from app.schemas.aeroanalysisschema import OperatingPointSchema
        from app.services.analysis_service import analyze_wing

        mock_db = MagicMock()
        op = OperatingPointSchema.model_construct(
            velocity=20.0, alpha=5.0, beta=0.0,
            p=0.0, q=0.0, r=0.0, xyz_ref=[0.0, 0.0, 0.0],
        )

        with (
            patch(
                "app.services.analysis_service.get_wing_schema_or_raise",
                return_value=MagicMock(),
            ),
            patch(
                "app.services.analysis_service.aeroplane_schema_to_asb_airplane_async",
                side_effect=RuntimeError("converter broken"),
            ),
        ):
            with pytest.raises(InternalError, match="Analysis error"):
                asyncio.run(
                    analyze_wing(mock_db, uuid.uuid4(), "w", op, AnalysisToolUrlType.AEROBUILDUP)
                )


# =========================================================================
# analyze_airplane (async orchestration)
# =========================================================================


class TestAnalyzeAirplane:
    """Tests for analyze_airplane — async orchestration with mocks."""

    def test_success_path(self):
        from app.schemas.AeroplaneRequest import AnalysisToolUrlType
        from app.schemas.aeroanalysisschema import OperatingPointSchema
        from app.services.analysis_service import analyze_airplane

        mock_db = MagicMock()
        mock_result = MagicMock()
        op = OperatingPointSchema.model_construct(
            velocity=20.0, alpha=5.0, beta=0.0,
            p=0.0, q=0.0, r=0.0, xyz_ref=[0.0, 0.0, 0.0],
        )

        with (
            patch(
                "app.services.analysis_service.get_aeroplane_schema_or_raise",
                return_value=MagicMock(),
            ),
            patch(
                "app.services.analysis_service.aeroplane_schema_to_asb_airplane_async",
                return_value=MagicMock(),
            ),
            patch(
                "app.services.analysis_service.analyse_aerodynamics",
                return_value=(mock_result, None),
            ),
        ):
            result = asyncio.run(
                analyze_airplane(
                    mock_db, uuid.uuid4(), op, AnalysisToolUrlType.VORTEX_LATTICE
                )
            )

        assert result is mock_result

    def test_raises_internal_error_on_failure(self):
        from app.schemas.AeroplaneRequest import AnalysisToolUrlType
        from app.schemas.aeroanalysisschema import OperatingPointSchema
        from app.services.analysis_service import analyze_airplane

        mock_db = MagicMock()
        op = OperatingPointSchema.model_construct(
            velocity=20.0, alpha=5.0, beta=0.0,
            p=0.0, q=0.0, r=0.0, xyz_ref=[0.0, 0.0, 0.0],
        )

        with (
            patch(
                "app.services.analysis_service.get_aeroplane_schema_or_raise",
                return_value=MagicMock(),
            ),
            patch(
                "app.services.analysis_service.aeroplane_schema_to_asb_airplane_async",
                side_effect=ValueError("bad schema"),
            ),
        ):
            with pytest.raises(InternalError):
                asyncio.run(
                    analyze_airplane(
                        mock_db, uuid.uuid4(), op, AnalysisToolUrlType.AEROBUILDUP
                    )
                )


# =========================================================================
# _extract_reference_arrays and _extract_force_arrays
# =========================================================================


class TestExtractHelpers:
    """Tests for _extract_reference_arrays and _extract_force_arrays."""

    def test_extract_reference_arrays_with_data(self):
        from app.services.analysis_service import _extract_reference_arrays

        result = SimpleNamespace(
            reference=SimpleNamespace(
                Xnp=np.array([0.1, 0.2]),
                Xnp_lat=np.array([0.3, 0.4]),
            )
        )
        xnp, xnp_lat = _extract_reference_arrays(result)
        assert xnp is not None
        assert xnp_lat is not None
        np.testing.assert_array_equal(xnp, [0.1, 0.2])

    def test_extract_reference_arrays_none(self):
        from app.services.analysis_service import _extract_reference_arrays

        result = SimpleNamespace(reference=None)
        xnp, xnp_lat = _extract_reference_arrays(result)
        assert xnp is None
        assert xnp_lat is None

    def test_extract_force_arrays_with_data(self):
        from app.services.analysis_service import _extract_force_arrays

        result = SimpleNamespace(
            forces=SimpleNamespace(
                L=np.array([100.0, 200.0]),
                D=np.array([10.0, 20.0]),
            )
        )
        lift, drag = _extract_force_arrays(result)
        assert lift is not None
        assert drag is not None

    def test_extract_force_arrays_none(self):
        from app.services.analysis_service import _extract_force_arrays

        result = SimpleNamespace(forces=None)
        lift, drag = _extract_force_arrays(result)
        assert lift is None
        assert drag is None


# =========================================================================
# _compute_cm_strip_colors
# =========================================================================


class TestComputeCmStripColors:
    """Tests for _compute_cm_strip_colors."""

    def test_stable_gradient(self):
        from app.services.analysis_service import _compute_cm_strip_colors

        # All strongly negative gradient -> stable (green)
        cm_grad = np.array([-0.05, -0.03, -0.02])
        colors = _compute_cm_strip_colors(cm_grad)
        assert all(c == "#4caf50" for c in colors)

    def test_unstable_gradient(self):
        from app.services.analysis_service import _compute_cm_strip_colors

        cm_grad = np.array([0.05, 0.03, 0.02])
        colors = _compute_cm_strip_colors(cm_grad)
        assert all(c == "#e57373" for c in colors)

    def test_marginal_gradient(self):
        from app.services.analysis_service import _compute_cm_strip_colors

        cm_grad = np.array([0.005, -0.005, 0.0])
        colors = _compute_cm_strip_colors(cm_grad)
        assert all(c == "#ffb74d" for c in colors)

    def test_nan_gradient(self):
        from app.services.analysis_service import _compute_cm_strip_colors

        cm_grad = np.array([np.nan, np.nan])
        colors = _compute_cm_strip_colors(cm_grad)
        assert all(c == "lightgray" for c in colors)


# =========================================================================
# _format_polar_label
# =========================================================================


class TestFormatPolarLabel:
    """Tests for _format_polar_label."""

    def test_ldmax_label(self):
        from app.services.analysis_service import _format_polar_label

        point = {"lift_to_drag_ratio": 25.0}
        label = _format_polar_label(
            "maximum_lift_to_drag_ratio_point", point, 0.02, 0.5
        )
        assert "(CL/CD)max=25.00" in label

    def test_cdmin_label(self):
        from app.services.analysis_service import _format_polar_label

        label = _format_polar_label(
            "minimum_drag_coefficient_point", {}, 0.005, 0.1
        )
        assert "CDmin=0.005" in label

    def test_clmax_label(self):
        from app.services.analysis_service import _format_polar_label

        label = _format_polar_label(
            "maximum_lift_coefficient_point", {}, 0.04, 1.2
        )
        assert "CLmax=1.200" in label

    def test_cd0_label(self):
        from app.services.analysis_service import _format_polar_label

        label = _format_polar_label(
            "drag_at_zero_lift_point", {}, 0.008, 0.0
        )
        assert "CD0=0.008" in label

    def test_fallback_label(self):
        from app.services.analysis_service import _format_polar_label

        label = _format_polar_label(
            "stall_point", {}, 0.06, 0.9
        )
        assert "CD=0.060" in label
        assert "CL=0.900" in label


# =========================================================================
# analyze_alpha_sweep (async orchestration)
# =========================================================================


class TestAnalyzeAlphaSweep:
    """Tests for analyze_alpha_sweep — integration of helpers."""

    def test_returns_analysis_and_characteristic_points(self):
        from app.schemas.AeroplaneRequest import AlphaSweepRequest
        from app.services.analysis_service import analyze_alpha_sweep

        mock_db = MagicMock()
        mock_schema = MagicMock()
        mock_schema.name = "TestPlane"

        mock_result = SimpleNamespace(
            flight_condition=SimpleNamespace(
                alpha=np.linspace(-5, 15, 21)
            ),
            coefficients=SimpleNamespace(
                CL=0.1 * np.linspace(-5, 15, 21),
                CD=0.01 + 0.001 * np.linspace(-5, 15, 21) ** 2,
                Cm=-0.01 * np.linspace(-5, 15, 21) + 0.05,
            ),
        )
        sweep = AlphaSweepRequest.model_construct(
            altitude=0.0, velocity=20.0,
            alpha_start=-5, alpha_end=15, alpha_num=21,
            beta=0.0, p=0.0, q=0.0, r=0.0, xyz_ref=[0, 0, 0],
        )

        with (
            patch(
                "app.services.analysis_service.get_aeroplane_schema_or_raise",
                return_value=mock_schema,
            ),
            patch(
                "app.services.analysis_service.aeroplane_schema_to_asb_airplane_async",
                return_value=MagicMock(),
            ),
            patch(
                "app.services.analysis_service.analyse_aerodynamics",
                return_value=(mock_result, None),
            ),
        ):
            result = asyncio.run(
                analyze_alpha_sweep(mock_db, uuid.uuid4(), sweep)
            )

        assert "analysis" in result
        assert "characteristic_points" in result
        assert "aircraft_name" in result
        cp = result["characteristic_points"]
        assert cp["maximum_lift_coefficient_point"] is not None
        assert cp["trim_point_cm_equals_zero"] is not None
