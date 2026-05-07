"""Tests for app/api/utils.py — aerodynamic analysis helpers and file utilities.

Covers: _as_array_if_needed, _build_operating_point, _run_avl, _run_aerobuildup,
_run_vlm, analyse_aerodynamics, compile_four_view_figure,
save_content_and_get_static_url, _write_file_sync.

All external dependencies (aerosandbox, plotly, pyvista) are mocked so these
tests run without heavy scientific packages being exercised.
"""

from __future__ import annotations

import asyncio
import os
from unittest.mock import MagicMock, call, patch

import numpy as np
import pytest

from app.schemas.AeroplaneRequest import AnalysisToolUrlType
from app.schemas.aeroanalysisschema import OperatingPointSchema


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_operating_point(**overrides) -> OperatingPointSchema:
    """Build a minimal OperatingPointSchema via model_construct."""
    defaults = dict(
        velocity=20.0,
        alpha=5.0,
        beta=0.0,
        p=0.0,
        q=0.0,
        r=0.0,
        xyz_ref=[0.0, 0.0, 0.0],
        altitude=0.0,
    )
    defaults.update(overrides)
    return OperatingPointSchema.model_construct(**defaults)


# =========================================================================== #
# _as_array_if_needed
# =========================================================================== #


class TestAsArrayIfNeeded:
    """_as_array_if_needed returns floats unchanged, wraps others in np.array."""

    def test_float_returned_as_is(self):
        from app.api.utils import _as_array_if_needed

        result = _as_array_if_needed(3.14)
        assert isinstance(result, float)
        assert result == 3.14

    def test_list_wrapped_in_np_array(self):
        from app.api.utils import _as_array_if_needed

        result = _as_array_if_needed([1.0, 2.0, 3.0])
        assert isinstance(result, np.ndarray)
        np.testing.assert_array_equal(result, [1.0, 2.0, 3.0])

    def test_np_array_returned_as_np_array(self):
        from app.api.utils import _as_array_if_needed

        arr = np.array([10.0, 20.0])
        result = _as_array_if_needed(arr)
        assert isinstance(result, np.ndarray)
        np.testing.assert_array_equal(result, arr)

    def test_int_wrapped_in_np_array(self):
        from app.api.utils import _as_array_if_needed

        result = _as_array_if_needed(5)
        assert isinstance(result, np.ndarray)

    def test_tuple_wrapped_in_np_array(self):
        from app.api.utils import _as_array_if_needed

        result = _as_array_if_needed((1.0, 2.0))
        assert isinstance(result, np.ndarray)
        np.testing.assert_array_equal(result, [1.0, 2.0])


# =========================================================================== #
# _build_operating_point
# =========================================================================== #


class TestBuildOperatingPoint:
    """_build_operating_point maps schema fields to asb.OperatingPoint."""

    @patch("app.api.utils.asb")
    def test_scalar_values_passed_through(self, mock_asb):
        from app.api.utils import _build_operating_point

        mock_atmosphere = MagicMock()
        mock_asb.Atmosphere.return_value = mock_atmosphere
        mock_op = MagicMock()
        mock_asb.OperatingPoint.return_value = mock_op

        schema = _make_operating_point(velocity=25.0, alpha=3.0, beta=1.0)
        result = _build_operating_point(schema)

        mock_asb.Atmosphere.assert_called_once_with(altitude=0.0)
        mock_asb.OperatingPoint.assert_called_once()
        kwargs = mock_asb.OperatingPoint.call_args.kwargs
        assert kwargs["velocity"] == 25.0
        assert kwargs["alpha"] == 3.0
        assert kwargs["beta"] == 1.0
        assert kwargs["atmosphere"] is mock_atmosphere
        assert result is mock_op

    @patch("app.api.utils.asb")
    def test_list_alpha_wrapped_in_array(self, mock_asb):
        from app.api.utils import _build_operating_point

        mock_asb.Atmosphere.return_value = MagicMock()
        mock_asb.OperatingPoint.return_value = MagicMock()

        schema = _make_operating_point(alpha=[0.0, 5.0, 10.0])
        _build_operating_point(schema)

        kwargs = mock_asb.OperatingPoint.call_args.kwargs
        np.testing.assert_array_equal(kwargs["alpha"], [0.0, 5.0, 10.0])


# =========================================================================== #
# _run_avl
# =========================================================================== #


class TestRunAvl:
    """_run_avl uses AVLRunner and raises for parameter sweeps."""

    @patch("app.api.utils.AnalysisModel")
    @patch("app.services.avl_runner.AVLRunner.run")
    def test_scalar_alpha_beta_runs_successfully(self, mock_runner_run, mock_analysis_model):
        from app.api.utils import _run_avl

        mock_runner_run.return_value = {"CL": 0.5}
        mock_analysis_model.from_avl_dict.return_value = MagicMock()

        airplane = MagicMock()
        op_point = MagicMock()
        operating_point = _make_operating_point(alpha=5.0, beta=0.0)

        result, figure = _run_avl(airplane, op_point, operating_point, avl_file_content="GEOM")

        mock_runner_run.assert_called_once_with(avl_file_content="GEOM")
        mock_analysis_model.from_avl_dict.assert_called_once_with({"CL": 0.5})
        assert figure is None

    def test_list_alpha_raises_value_error(self):
        from app.api.utils import _run_avl

        airplane = MagicMock()
        op_point = MagicMock()
        operating_point = _make_operating_point(alpha=[0.0, 5.0, 10.0])

        with pytest.raises(ValueError, match="AVL analysis does not support parameter sweeps"):
            _run_avl(airplane, op_point, operating_point)

    def test_list_beta_raises_value_error(self):
        from app.api.utils import _run_avl

        airplane = MagicMock()
        op_point = MagicMock()
        operating_point = _make_operating_point(beta=[0.0, 2.0])

        with pytest.raises(ValueError, match="AVL analysis does not support parameter sweeps"):
            _run_avl(airplane, op_point, operating_point)

    def test_np_array_alpha_raises_value_error(self):
        from app.api.utils import _run_avl

        airplane = MagicMock()
        op_point = MagicMock()
        operating_point = _make_operating_point(alpha=np.array([1.0, 2.0]))

        with pytest.raises(ValueError, match="AVL analysis does not support parameter sweeps"):
            _run_avl(airplane, op_point, operating_point)

    def test_none_avl_file_content_raises_value_error(self):
        from app.api.utils import _run_avl

        airplane = MagicMock()
        op_point = MagicMock()
        operating_point = _make_operating_point(alpha=5.0, beta=0.0)

        with pytest.raises(ValueError, match="avl_file_content is required"):
            _run_avl(airplane, op_point, operating_point, avl_file_content=None)


# =========================================================================== #
# _run_aerobuildup
# =========================================================================== #


class TestRunAerobuildup:
    """_run_aerobuildup creates an AeroBuildup and runs with stability derivatives."""

    @patch("app.api.utils.AnalysisModel")
    @patch("app.api.utils.asb")
    def test_runs_with_stability_derivatives(self, mock_asb, mock_analysis_model):
        from app.api.utils import _run_aerobuildup

        mock_abu_instance = MagicMock()
        mock_abu_instance.run_with_stability_derivatives.return_value = {"CL": 0.3}
        mock_asb.AeroBuildup.return_value = mock_abu_instance
        mock_analysis_model.from_abu_dict.return_value = MagicMock(name="result")

        airplane = MagicMock()
        op_point = MagicMock()
        operating_point = _make_operating_point()

        result, figure = _run_aerobuildup(airplane, op_point, operating_point)

        mock_asb.AeroBuildup.assert_called_once_with(
            airplane=airplane,
            op_point=op_point,
            xyz_ref=operating_point.xyz_ref,
        )
        mock_abu_instance.run_with_stability_derivatives.assert_called_once()
        mock_analysis_model.from_abu_dict.assert_called_once_with(
            {"CL": 0.3},
            asb_airplan=airplane,
            methode="aerobuildup",
        )
        assert figure is None


# =========================================================================== #
# _run_vlm
# =========================================================================== #


class TestRunVlm:
    """_run_vlm creates a VortexLatticeMethod, runs, and optionally draws."""

    @patch("app.api.utils.AnalysisModel")
    @patch("app.api.utils.asb")
    def test_without_streamlines(self, mock_asb, mock_analysis_model):
        from app.api.utils import _run_vlm

        mock_vlm_instance = MagicMock()
        mock_vlm_instance.run_with_stability_derivatives.return_value = {"CL": 0.4}
        mock_asb.VortexLatticeMethod.return_value = mock_vlm_instance
        mock_analysis_model.from_abu_dict.return_value = MagicMock(name="result")

        airplane = MagicMock()
        op_point = MagicMock()
        operating_point = _make_operating_point()

        result, figure = _run_vlm(
            airplane,
            op_point,
            operating_point,
            draw_streamlines=False,
            backend="plotly",
        )

        mock_asb.VortexLatticeMethod.assert_called_once_with(
            airplane=airplane,
            op_point=op_point,
            xyz_ref=operating_point.xyz_ref,
        )
        assert mock_vlm_instance.verbose is True
        mock_vlm_instance.run_with_stability_derivatives.assert_called_once()
        mock_vlm_instance.draw.assert_not_called()
        assert figure is None

    @patch("app.api.utils.AnalysisModel")
    @patch("app.api.utils.asb")
    def test_with_streamlines(self, mock_asb, mock_analysis_model):
        from app.api.utils import _run_vlm

        mock_vlm_instance = MagicMock()
        mock_vlm_instance.run_with_stability_derivatives.return_value = {"CL": 0.4}
        mock_vlm_instance.draw.return_value = MagicMock(name="figure")
        mock_asb.VortexLatticeMethod.return_value = mock_vlm_instance
        mock_analysis_model.from_abu_dict.return_value = MagicMock(name="result")

        airplane = MagicMock()
        op_point = MagicMock()
        operating_point = _make_operating_point()

        result, figure = _run_vlm(
            airplane,
            op_point,
            operating_point,
            draw_streamlines=True,
            backend="pyvista",
        )

        mock_vlm_instance.draw.assert_called_once_with(show=False, backend="pyvista")
        assert figure is not None

    @patch("app.api.utils.AnalysisModel")
    @patch("app.api.utils.asb")
    def test_from_abu_dict_called_with_vortex_lattice_method(self, mock_asb, mock_analysis_model):
        from app.api.utils import _run_vlm

        mock_vlm_instance = MagicMock()
        vlm_results = {"CL": 0.4, "CD": 0.01}
        mock_vlm_instance.run_with_stability_derivatives.return_value = vlm_results
        mock_asb.VortexLatticeMethod.return_value = mock_vlm_instance
        mock_analysis_model.from_abu_dict.return_value = MagicMock()

        airplane = MagicMock()
        op_point = MagicMock()
        operating_point = _make_operating_point()

        _run_vlm(airplane, op_point, operating_point, False, "plotly")

        mock_analysis_model.from_abu_dict.assert_called_once_with(
            vlm_results,
            asb_airplan=airplane,
            operating_point=op_point,
            methode="vortex_lattice",
        )


# =========================================================================== #
# analyse_aerodynamics (dispatcher)
# =========================================================================== #


class TestAnalyseAerodynamics:
    """analyse_aerodynamics dispatches to the correct backend."""

    @patch("app.api.utils._build_operating_point")
    @patch("app.api.utils._run_avl")
    def test_dispatches_to_avl(self, mock_run_avl, mock_build_op):
        from app.api.utils import analyse_aerodynamics

        mock_build_op.return_value = MagicMock()
        expected = (MagicMock(), None)
        mock_run_avl.return_value = expected

        airplane = MagicMock()
        op_schema = _make_operating_point()

        result = analyse_aerodynamics(
            AnalysisToolUrlType.AVL,
            op_schema,
            airplane,
        )

        mock_run_avl.assert_called_once()
        assert result == expected

    @patch("app.api.utils._build_operating_point")
    @patch("app.api.utils._run_aerobuildup")
    def test_dispatches_to_aerobuildup(self, mock_run_abu, mock_build_op):
        from app.api.utils import analyse_aerodynamics

        mock_build_op.return_value = MagicMock()
        expected = (MagicMock(), None)
        mock_run_abu.return_value = expected

        airplane = MagicMock()
        op_schema = _make_operating_point()

        result = analyse_aerodynamics(
            AnalysisToolUrlType.AEROBUILDUP,
            op_schema,
            airplane,
        )

        mock_run_abu.assert_called_once()
        assert result == expected

    @patch("app.api.utils._build_operating_point")
    @patch("app.api.utils._run_vlm")
    def test_dispatches_to_vlm(self, mock_run_vlm, mock_build_op):
        from app.api.utils import analyse_aerodynamics

        mock_build_op.return_value = MagicMock()
        expected = (MagicMock(), MagicMock())
        mock_run_vlm.return_value = expected

        airplane = MagicMock()
        op_schema = _make_operating_point()

        result = analyse_aerodynamics(
            AnalysisToolUrlType.VORTEX_LATTICE,
            op_schema,
            airplane,
            draw_streamlines=True,
            backend="pyvista",
        )

        mock_run_vlm.assert_called_once()
        # Verify streamline args forwarded
        args = mock_run_vlm.call_args
        assert args[0][3] is True  # draw_streamlines
        assert args[0][4] == "pyvista"  # backend
        assert result == expected

    @patch("app.api.utils._build_operating_point")
    def test_invalid_tool_raises_value_error(self, mock_build_op):
        from app.api.utils import analyse_aerodynamics

        mock_build_op.return_value = MagicMock()
        airplane = MagicMock()
        op_schema = _make_operating_point()

        with pytest.raises(ValueError, match="Invalid analysis tool"):
            analyse_aerodynamics("nonexistent_tool", op_schema, airplane)

    @patch("app.api.utils._build_operating_point")
    @patch("app.api.utils._run_avl")
    def test_sets_xyz_ref_on_airplane(self, mock_run_avl, mock_build_op):
        from app.api.utils import analyse_aerodynamics

        mock_build_op.return_value = MagicMock()
        mock_run_avl.return_value = (MagicMock(), None)

        airplane = MagicMock()
        op_schema = _make_operating_point(xyz_ref=[1.0, 2.0, 3.0])

        analyse_aerodynamics(AnalysisToolUrlType.AVL, op_schema, airplane)

        assert airplane.xyz_ref == [1.0, 2.0, 3.0]


# =========================================================================== #
# compile_four_view_figure
# =========================================================================== #


class TestCompileFourViewFigure:
    """compile_four_view_figure creates a 2x2 (actually 3x2) subplot layout."""

    @patch("app.api.utils.make_subplots")
    def test_creates_subplots_and_adds_traces(self, mock_make_subplots):
        from app.api.utils import compile_four_view_figure

        # Build a mock input figure with one trace that has x, y, z data
        mock_trace = MagicMock()
        mock_trace.x = [0.0, 1.0, 2.0]
        mock_trace.y = [0.0, 1.0, 2.0]
        mock_trace.z = [0.0, 1.0, 2.0]

        input_figure = MagicMock()
        input_figure.data = [mock_trace]

        mock_fig = MagicMock()
        mock_make_subplots.return_value = mock_fig

        result = compile_four_view_figure(input_figure)

        # Should create subplots with 3 rows and 2 cols
        mock_make_subplots.assert_called_once()
        kwargs = mock_make_subplots.call_args.kwargs
        assert kwargs["rows"] == 3
        assert kwargs["cols"] == 2

        # Each trace should be added 4 times (one per view)
        assert mock_fig.add_trace.call_count == 4

        # Should update scenes 4 times (one per camera angle)
        assert mock_fig.update_scenes.call_count == 4

        # Should update layout (at least twice)
        assert mock_fig.update_layout.call_count >= 2

        assert result is mock_fig

    @patch("app.api.utils.make_subplots")
    def test_multiple_traces_each_added_four_times(self, mock_make_subplots):
        from app.api.utils import compile_four_view_figure

        traces = []
        for i in range(3):
            t = MagicMock()
            t.x = [float(i)]
            t.y = [float(i)]
            t.z = [float(i)]
            traces.append(t)

        input_figure = MagicMock()
        input_figure.data = traces

        mock_fig = MagicMock()
        mock_make_subplots.return_value = mock_fig

        compile_four_view_figure(input_figure)

        # 3 traces x 4 views = 12 add_trace calls
        assert mock_fig.add_trace.call_count == 12

    @patch("app.api.utils.make_subplots")
    def test_layout_sets_height_width_title(self, mock_make_subplots):
        from app.api.utils import compile_four_view_figure

        mock_trace = MagicMock()
        mock_trace.x = [0.0, 1.0]
        mock_trace.y = [0.0, 1.0]
        mock_trace.z = [0.0, 1.0]

        input_figure = MagicMock()
        input_figure.data = [mock_trace]

        mock_fig = MagicMock()
        mock_make_subplots.return_value = mock_fig

        compile_four_view_figure(input_figure)

        # Find the layout call that sets height/width/title
        layout_calls = mock_fig.update_layout.call_args_list
        # First call sets height, width, title_text
        first_layout = layout_calls[0].kwargs
        assert first_layout["height"] == 1000
        assert first_layout["width"] == 1000
        assert first_layout["title_text"] == "Four Views of Aerodynamic Analysis"
        assert first_layout["showlegend"] is False


# =========================================================================== #
# _write_file_sync
# =========================================================================== #


class TestWriteFileSync:
    """_write_file_sync creates directories and writes content."""

    def test_creates_directory_and_writes_file(self, tmp_path):
        from app.api.utils import _write_file_sync

        content_dir = str(tmp_path / "sub" / "dir")
        file_path = str(tmp_path / "sub" / "dir" / "output.html")

        _write_file_sync(content_dir, file_path, "<html>hello</html>")

        assert os.path.isdir(content_dir)
        with open(file_path) as f:
            assert f.read() == "<html>hello</html>"

    def test_overwrites_existing_file(self, tmp_path):
        from app.api.utils import _write_file_sync

        content_dir = str(tmp_path)
        file_path = str(tmp_path / "out.txt")

        _write_file_sync(content_dir, file_path, "first")
        _write_file_sync(content_dir, file_path, "second")

        with open(file_path) as f:
            assert f.read() == "second"

    def test_existing_directory_no_error(self, tmp_path):
        from app.api.utils import _write_file_sync

        content_dir = str(tmp_path / "existing")
        os.makedirs(content_dir)
        file_path = str(tmp_path / "existing" / "file.txt")

        # Should not raise even though directory already exists
        _write_file_sync(content_dir, file_path, "content")

        with open(file_path) as f:
            assert f.read() == "content"


# =========================================================================== #
# save_content_and_get_static_url
# =========================================================================== #


class TestSaveContentAndGetStaticUrl:
    """save_content_and_get_static_url writes file and returns URL (async)."""

    def test_returns_correct_url(self):
        from app.api.utils import save_content_and_get_static_url

        with patch("app.api.utils._write_file_sync") as mock_write:
            url = asyncio.run(
                save_content_and_get_static_url(
                    aeroplane_id="abc-123",
                    base_url="http://localhost:8001/",
                    content="<html/>",
                    content_type="html",
                    filename="view.html",
                )
            )

        assert url == "http://localhost:8001/static/abc-123/html/view.html"
        mock_write.assert_called_once()

    def test_passes_correct_paths_to_write(self):
        from app.api.utils import save_content_and_get_static_url

        with patch("app.api.utils._write_file_sync") as mock_write:
            asyncio.run(
                save_content_and_get_static_url(
                    aeroplane_id="plane-1",
                    base_url="http://example.com/",
                    content="data",
                    content_type="png",
                    filename="image.png",
                )
            )

        args = mock_write.call_args.args
        expected_dir = os.path.join("tmp", "plane-1", "png")
        expected_file = os.path.join("tmp", "plane-1", "png", "image.png")
        assert args[0] == expected_dir
        assert args[1] == expected_file
        assert args[2] == "data"

    def test_url_construction_with_trailing_slash_base(self):
        from app.api.utils import save_content_and_get_static_url

        with patch("app.api.utils._write_file_sync"):
            url = asyncio.run(
                save_content_and_get_static_url(
                    aeroplane_id="id",
                    base_url="http://host:8001/",
                    content="c",
                    content_type="t",
                    filename="f",
                )
            )

        assert url == "http://host:8001/static/id/t/f"

    def test_url_construction_without_trailing_slash_base(self):
        from app.api.utils import save_content_and_get_static_url

        with patch("app.api.utils._write_file_sync"):
            url = asyncio.run(
                save_content_and_get_static_url(
                    aeroplane_id="id",
                    base_url="http://host:8001",
                    content="c",
                    content_type="t",
                    filename="f",
                )
            )

        # urljoin with no trailing slash replaces last path segment,
        # but since the base has no path segment, it works fine
        assert "/static/id/t/f" in url
