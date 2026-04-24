"""Tests for app/services/stability_service.py helper functions and main entry point."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.core.exceptions import InternalError, NotFoundError
from app.schemas.stability import StabilitySummaryResponse
from app.services.stability_service import (
    _compute_static_margin,
    _find_trim_elevator,
    _scalar,
    get_stability_summary,
)


# ------------------------------------------------------------------ #
# _scalar
# ------------------------------------------------------------------ #


class TestScalar:
    """Test _scalar helper that extracts a float from various input types."""

    def test_none_returns_none(self):
        assert _scalar(None) is None

    def test_float_returns_float(self):
        assert _scalar(3.14) == 3.14

    def test_int_returns_float(self):
        result = _scalar(7)
        assert result == 7.0
        assert isinstance(result, float)

    def test_list_single_element(self):
        assert _scalar([2.5]) == 2.5

    def test_list_multiple_elements_returns_first(self):
        assert _scalar([1.0, 2.0, 3.0]) == 1.0

    def test_empty_list_returns_none(self):
        assert _scalar([]) is None

    def test_numpy_scalar(self):
        result = _scalar(np.float64(4.2))
        assert result == pytest.approx(4.2)
        assert isinstance(result, float)

    def test_numpy_array_single_element_raises(self):
        """NOTE: _scalar does not handle numpy arrays (not isinstance list).

        A single-element np.array falls through to float(), which raises
        TypeError in numpy >= 1.24. This documents current production
        behaviour. If numpy arrays need support, _scalar should be updated
        to check for np.ndarray.
        """
        # numpy >= 1.24 raises TypeError for float(np.array([x]))
        # numpy < 1.24 may succeed. We document both possibilities.
        try:
            result = _scalar(np.array([9.9]))
            # If it succeeds (older numpy), the value should be correct.
            assert result == pytest.approx(9.9)
        except TypeError:
            # Expected on numpy >= 1.24: cannot convert array to scalar.
            pass

    def test_string_numeric(self):
        """A numeric string should convert to float."""
        assert _scalar("3.5") == 3.5

    def test_zero_returns_zero(self):
        result = _scalar(0.0)
        assert result == 0.0
        assert isinstance(result, float)

    def test_negative(self):
        assert _scalar(-1.5) == -1.5

    def test_list_with_none_first_element(self):
        """List whose first element is None-ish but present."""
        assert _scalar([0]) == 0.0

    def test_numpy_0d_array(self):
        """A 0-d numpy array (scalar wrapped in array) should convert via float()."""
        result = _scalar(np.array(5.5))
        assert result == pytest.approx(5.5)
        assert isinstance(result, float)


# ------------------------------------------------------------------ #
# _compute_static_margin
# ------------------------------------------------------------------ #


class TestComputeStaticMargin:
    """Test _compute_static_margin(xnp, xcg, cref_val)."""

    def test_happy_path(self):
        # SM = (0.10 - 0.05) / 0.25 = 0.2
        result = _compute_static_margin(0.10, 0.05, 0.25)
        assert result == pytest.approx(0.2)

    def test_xnp_none(self):
        assert _compute_static_margin(None, 0.05, 0.25) is None

    def test_xcg_none(self):
        assert _compute_static_margin(0.10, None, 0.25) is None

    def test_both_none(self):
        assert _compute_static_margin(None, None, 0.25) is None

    def test_zero_mac_returns_none(self):
        """MAC = 0 would cause division by zero; should return None."""
        assert _compute_static_margin(0.10, 0.05, 0.0) is None

    def test_negative_mac_returns_none(self):
        """Negative MAC is physically nonsensical; should return None."""
        assert _compute_static_margin(0.10, 0.05, -0.5) is None

    def test_mac_as_list(self):
        """cref_val may come as a list from the analysis result."""
        result = _compute_static_margin(0.10, 0.05, [0.25])
        assert result == pytest.approx(0.2)

    def test_mac_none_returns_none(self):
        """If cref_val is None, _scalar returns None, guard catches it."""
        assert _compute_static_margin(0.10, 0.05, None) is None

    def test_negative_static_margin(self):
        """When CG is ahead of NP, static margin is negative (unstable)."""
        result = _compute_static_margin(0.05, 0.10, 0.25)
        assert result == pytest.approx(-0.2)

    def test_zero_static_margin(self):
        """When CG == NP, static margin is zero (neutrally stable)."""
        result = _compute_static_margin(0.10, 0.10, 0.25)
        assert result == pytest.approx(0.0)

    def test_large_positive_margin(self):
        """Very stable aircraft with large static margin."""
        result = _compute_static_margin(1.0, 0.0, 0.5)
        assert result == pytest.approx(2.0)


# ------------------------------------------------------------------ #
# _find_trim_elevator
# ------------------------------------------------------------------ #


class TestFindTrimElevator:
    """Test _find_trim_elevator with various control surface configurations."""

    def test_with_elevator(self):
        cs = SimpleNamespace(deflections={"elevator": -2.5})
        assert _find_trim_elevator(cs) == -2.5

    def test_case_insensitive_match(self):
        cs = SimpleNamespace(deflections={"Elevator_Main": 1.0})
        assert _find_trim_elevator(cs) == 1.0

    def test_mixed_name_with_elevator(self):
        cs = SimpleNamespace(deflections={"left_elevator": -3.0, "rudder": 0.5})
        assert _find_trim_elevator(cs) == -3.0

    def test_no_elevator_surface(self):
        cs = SimpleNamespace(deflections={"aileron": 1.0, "rudder": 0.5})
        assert _find_trim_elevator(cs) is None

    def test_empty_deflections(self):
        cs = SimpleNamespace(deflections={})
        assert _find_trim_elevator(cs) is None

    def test_no_deflections_attribute(self):
        cs = SimpleNamespace()
        assert _find_trim_elevator(cs) is None

    def test_deflections_is_none(self):
        cs = SimpleNamespace(deflections=None)
        assert _find_trim_elevator(cs) is None

    def test_plain_object_without_deflections(self):
        """A plain object without 'deflections' attr should return None."""
        assert _find_trim_elevator(object()) is None

    def test_elevator_value_as_list(self):
        """Elevator deflection may come as a list; _scalar should handle it."""
        cs = SimpleNamespace(deflections={"elevator": [1.5, 2.0]})
        assert _find_trim_elevator(cs) == 1.5


# ------------------------------------------------------------------ #
# get_stability_summary (integration-style with mocks)
# ------------------------------------------------------------------ #


def _make_analysis_result(
    *,
    xnp=0.09,
    cref=0.25,
    cma=-0.8,
    cnb=0.05,
    clb=-0.03,
    alpha=2.3,
    method="aerobuildup",
    elevator_defl=-1.5,
):
    """Build a mock analysis result namespace mirroring the real structure."""
    control_surfaces = SimpleNamespace(
        deflections={"elevator": elevator_defl} if elevator_defl is not None else {},
    )
    return SimpleNamespace(
        reference=SimpleNamespace(Xnp=xnp, Cref=cref),
        derivatives=SimpleNamespace(Cma=cma, Cnb=cnb, Clb=clb),
        flight_condition=SimpleNamespace(alpha=alpha),
        control_surfaces=control_surfaces,
        method=method,
    )


def _run_async(coro):
    """Run an async coroutine synchronously for tests (no pytest-asyncio needed)."""
    return asyncio.run(coro)


def _patch_analysis_deps(mock_result, *, converter_side_effect=None):
    """Context manager that patches all three lazy-import dependencies."""
    converter_kwargs = (
        {"side_effect": converter_side_effect}
        if converter_side_effect
        else {"return_value": MagicMock()}
    )
    return (
        patch(
            "app.services.stability_service.get_aeroplane_schema_or_raise",
            return_value=MagicMock(),
        ),
        patch(
            "app.converters.model_schema_converters.aeroplane_schema_to_asb_airplane_async",
            **converter_kwargs,
        ),
        patch(
            "app.api.utils.analyse_aerodynamics",
            return_value=(mock_result, None),
        ),
    )


class TestGetStabilitySummary:
    """Test the main async entry point with mocked dependencies."""

    def test_stable_aircraft(self):
        mock_result = _make_analysis_result()
        mock_op = MagicMock()
        mock_op.xyz_ref = [0.05, 0.0, 0.0]

        p1, p2, p3 = _patch_analysis_deps(mock_result)
        with p1, p2, p3:
            resp = _run_async(
                get_stability_summary(
                    db=MagicMock(),
                    aeroplane_uuid="some-uuid",
                    operating_point=mock_op,
                    analysis_tool="aerobuildup",
                )
            )

        assert isinstance(resp, StabilitySummaryResponse)
        assert resp.neutral_point_x == pytest.approx(0.09)
        assert resp.cg_x == pytest.approx(0.05)
        assert resp.Cma == pytest.approx(-0.8)
        assert resp.Cnb == pytest.approx(0.05)
        assert resp.Clb == pytest.approx(-0.03)
        assert resp.is_statically_stable is True
        assert resp.is_directionally_stable is True
        assert resp.is_laterally_stable is True
        assert resp.analysis_method == "aerobuildup"
        assert resp.trim_alpha_deg == pytest.approx(2.3)
        assert resp.trim_elevator_deg == pytest.approx(-1.5)
        # Static margin = (0.09 - 0.05) / 0.25 = 0.16
        assert resp.static_margin == pytest.approx(0.16)

    def test_unstable_aircraft(self):
        mock_result = _make_analysis_result(cma=0.3, cnb=-0.01, clb=0.02)
        mock_op = MagicMock()
        mock_op.xyz_ref = [0.05, 0.0, 0.0]

        p1, p2, p3 = _patch_analysis_deps(mock_result)
        with p1, p2, p3:
            resp = _run_async(
                get_stability_summary(
                    db=MagicMock(),
                    aeroplane_uuid="some-uuid",
                    operating_point=mock_op,
                    analysis_tool="aerobuildup",
                )
            )

        assert resp.is_statically_stable is False
        assert resp.is_directionally_stable is False
        assert resp.is_laterally_stable is False

    def test_no_xyz_ref_gives_none_cg(self):
        mock_result = _make_analysis_result()
        mock_op = MagicMock()
        mock_op.xyz_ref = None

        p1, p2, p3 = _patch_analysis_deps(mock_result)
        with p1, p2, p3:
            resp = _run_async(
                get_stability_summary(
                    db=MagicMock(),
                    aeroplane_uuid="some-uuid",
                    operating_point=mock_op,
                    analysis_tool="aerobuildup",
                )
            )

        assert resp.cg_x is None
        assert resp.static_margin is None

    def test_empty_xyz_ref_gives_none_cg(self):
        mock_result = _make_analysis_result()
        mock_op = MagicMock()
        mock_op.xyz_ref = []

        p1, p2, p3 = _patch_analysis_deps(mock_result)
        with p1, p2, p3:
            resp = _run_async(
                get_stability_summary(
                    db=MagicMock(),
                    aeroplane_uuid="some-uuid",
                    operating_point=mock_op,
                    analysis_tool="aerobuildup",
                )
            )

        assert resp.cg_x is None

    def test_analysis_exception_raises_internal_error(self):
        mock_op = MagicMock()
        mock_op.xyz_ref = [0.05, 0.0, 0.0]

        with (
            patch(
                "app.services.stability_service.get_aeroplane_schema_or_raise",
                return_value=MagicMock(),
            ),
            patch(
                "app.converters.model_schema_converters.aeroplane_schema_to_asb_airplane_async",
                side_effect=RuntimeError("ASB blew up"),
            ),
        ):
            with pytest.raises(InternalError, match="Stability analysis error"):
                _run_async(
                    get_stability_summary(
                        db=MagicMock(),
                        aeroplane_uuid="some-uuid",
                        operating_point=mock_op,
                        analysis_tool="aerobuildup",
                    )
                )

    def test_aeroplane_not_found_propagates(self):
        """NotFoundError from get_aeroplane_schema_or_raise should propagate."""
        mock_op = MagicMock()
        mock_op.xyz_ref = [0.05, 0.0, 0.0]

        with patch(
            "app.services.stability_service.get_aeroplane_schema_or_raise",
            side_effect=NotFoundError(message="Aeroplane not found"),
        ):
            with pytest.raises(NotFoundError):
                _run_async(
                    get_stability_summary(
                        db=MagicMock(),
                        aeroplane_uuid="missing-uuid",
                        operating_point=mock_op,
                        analysis_tool="aerobuildup",
                    )
                )

    def test_no_elevator_in_control_surfaces(self):
        mock_result = _make_analysis_result(elevator_defl=None)
        mock_op = MagicMock()
        mock_op.xyz_ref = [0.05, 0.0, 0.0]

        p1, p2, p3 = _patch_analysis_deps(mock_result)
        with p1, p2, p3:
            resp = _run_async(
                get_stability_summary(
                    db=MagicMock(),
                    aeroplane_uuid="some-uuid",
                    operating_point=mock_op,
                    analysis_tool="aerobuildup",
                )
            )

        assert resp.trim_elevator_deg is None

    def test_derivatives_as_lists(self):
        """Analysis tools may return derivatives as single-element lists."""
        mock_result = _make_analysis_result()
        mock_result.derivatives.Cma = [-0.5]
        mock_result.derivatives.Cnb = [0.03]
        mock_result.derivatives.Clb = [-0.01]
        mock_result.reference.Xnp = [0.08]
        mock_result.flight_condition.alpha = [3.0]

        mock_op = MagicMock()
        mock_op.xyz_ref = [0.05, 0.0, 0.0]

        p1, p2, p3 = _patch_analysis_deps(mock_result)
        with p1, p2, p3:
            resp = _run_async(
                get_stability_summary(
                    db=MagicMock(),
                    aeroplane_uuid="some-uuid",
                    operating_point=mock_op,
                    analysis_tool="aerobuildup",
                )
            )

        assert resp.Cma == pytest.approx(-0.5)
        assert resp.Cnb == pytest.approx(0.03)
        assert resp.Clb == pytest.approx(-0.01)
        assert resp.neutral_point_x == pytest.approx(0.08)
        assert resp.trim_alpha_deg == pytest.approx(3.0)
        assert resp.is_statically_stable is True
        assert resp.is_directionally_stable is True
        assert resp.is_laterally_stable is True

    def test_none_derivatives(self):
        """When derivatives are None, stability flags should be False."""
        mock_result = _make_analysis_result(cma=None, cnb=None, clb=None)
        mock_result.reference.Xnp = None

        mock_op = MagicMock()
        mock_op.xyz_ref = [0.05, 0.0, 0.0]

        p1, p2, p3 = _patch_analysis_deps(mock_result)
        with p1, p2, p3:
            resp = _run_async(
                get_stability_summary(
                    db=MagicMock(),
                    aeroplane_uuid="some-uuid",
                    operating_point=mock_op,
                    analysis_tool="aerobuildup",
                )
            )

        assert resp.Cma is None
        assert resp.Cnb is None
        assert resp.Clb is None
        assert resp.is_statically_stable is False
        assert resp.is_directionally_stable is False
        assert resp.is_laterally_stable is False
        assert resp.neutral_point_x is None
        assert resp.static_margin is None

    def test_method_passed_through(self):
        """The analysis_method field should reflect result.method."""
        mock_result = _make_analysis_result(method="vortex_lattice")
        mock_op = MagicMock()
        mock_op.xyz_ref = [0.05, 0.0, 0.0]

        p1, p2, p3 = _patch_analysis_deps(mock_result)
        with p1, p2, p3:
            resp = _run_async(
                get_stability_summary(
                    db=MagicMock(),
                    aeroplane_uuid="some-uuid",
                    operating_point=mock_op,
                    analysis_tool="vortex_lattice",
                )
            )

        assert resp.analysis_method == "vortex_lattice"
