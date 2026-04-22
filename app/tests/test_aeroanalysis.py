import asyncio
import unittest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException, Request

from app.api.v2.endpoints.aeroanalysis import (
    analyze_airplane_alpha_sweep,
    analyze_airplane_alpha_sweep_diagram,
    analyze_airplane_post,
    analyze_airplane_simple_sweep,
    analyze_wing_post,
    get_aeroplane_three_view_url as get_aeroplane_three_view,
    get_streamlines_three_view_url as get_streamlines_three_view,
)
from app.core.exceptions import NotFoundError
from app.schemas.AeroplaneRequest import AnalysisToolUrlType, AlphaSweepRequest, SimpleSweepRequest
from app.schemas.aeroanalysisschema import OperatingPointSchema
from app.schemas.api_responses import StaticUrlResponse


class TestAeroanalysis(unittest.TestCase):
    def setUp(self):
        self.test_plane_id = uuid.uuid4()
        self.test_wing_name = "test-wing"
        self.test_operating_point = OperatingPointSchema.model_construct(
            velocity=10.0,
            alpha=5.0,
            beta=0.0,
            p=0.0,
            q=0.0,
            r=0.0,
            xyz_ref=[0.0, 0.0, 0.0],
        )

    def test_analyze_wing_post_success(self):
        mock_db = MagicMock()
        expected = {"ok": True}

        with patch("app.api.v2.endpoints.aeroanalysis.analysis_service.analyze_wing", new=AsyncMock(return_value=expected)) as mock_analyze:
            result = asyncio.run(
                analyze_wing_post(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    operating_point=self.test_operating_point,
                    analysis_tool=AnalysisToolUrlType.AEROBUILDUP,
                    db=mock_db,
                )
            )

        self.assertEqual(result, expected)
        mock_analyze.assert_awaited_once_with(
            mock_db,
            self.test_plane_id,
            self.test_wing_name,
            self.test_operating_point,
            AnalysisToolUrlType.AEROBUILDUP,
        )

    def test_analyze_wing_post_not_found_maps_to_http_404(self):
        mock_db = MagicMock()

        with patch(
            "app.api.v2.endpoints.aeroanalysis.analysis_service.analyze_wing",
            new=AsyncMock(side_effect=NotFoundError("Wing not found")),
        ):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(
                    analyze_wing_post(
                        aeroplane_id=self.test_plane_id,
                        wing_name=self.test_wing_name,
                        operating_point=self.test_operating_point,
                        analysis_tool=AnalysisToolUrlType.AEROBUILDUP,
                        db=mock_db,
                    )
                )

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("Wing not found", str(ctx.exception.detail))

    def test_analyze_airplane_post_success(self):
        mock_db = MagicMock()
        expected = {"lift": 123}

        with patch("app.api.v2.endpoints.aeroanalysis.analysis_service.analyze_airplane", new=AsyncMock(return_value=expected)) as mock_analyze:
            result = asyncio.run(
                analyze_airplane_post(
                    aeroplane_id=self.test_plane_id,
                    operating_point=self.test_operating_point,
                    analysis_tool=AnalysisToolUrlType.VORTEX_LATTICE,
                    db=mock_db,
                )
            )

        self.assertEqual(result, expected)
        mock_analyze.assert_awaited_once_with(
            mock_db,
            self.test_plane_id,
            self.test_operating_point,
            AnalysisToolUrlType.VORTEX_LATTICE,
        )

    def test_analyze_airplane_alpha_sweep_success(self):
        mock_db = MagicMock()
        sweep_request = AlphaSweepRequest.model_construct(
            altitude=1000.0,
            velocity=20.0,
            alpha_start=0.0,
            alpha_end=10.0,
            alpha_num=5,
            beta=0.0,
            p=0.0,
            q=0.0,
            r=0.0,
            xyz_ref=[0.0, 0.0, 0.0],
        )

        with patch(
            "app.api.v2.endpoints.aeroanalysis.analysis_service.analyze_alpha_sweep",
            new=AsyncMock(return_value={"curve": []}),
        ) as mock_sweep:
            result = asyncio.run(
                analyze_airplane_alpha_sweep(
                    aeroplane_id=self.test_plane_id,
                    sweep_request=sweep_request,
                    db=mock_db,
                )
            )

        self.assertEqual(result, {"curve": []})
        mock_sweep.assert_awaited_once_with(mock_db, self.test_plane_id, sweep_request)

    def test_analyze_airplane_alpha_sweep_diagram_returns_static_url(self):
        """Happy-path coverage for POST /aeroplanes/{id}/alpha_sweep/diagram."""
        mock_db = MagicMock()
        mock_request = MagicMock(spec=Request)
        mock_request.base_url = "http://testserver/"
        mock_settings = MagicMock(base_url="http://testserver")
        sweep_request = AlphaSweepRequest.model_construct(
            altitude=0.0,
            velocity=20.0,
            alpha_start=0.0,
            alpha_end=10.0,
            alpha_num=5,
            beta=0.0,
            p=0.0,
            q=0.0,
            r=0.0,
            xyz_ref=[0.0, 0.0, 0.0],
        )

        with patch(
            "app.api.v2.endpoints.aeroanalysis.analysis_service.get_alpha_sweep_diagram_url",
            new=AsyncMock(return_value="http://testserver/static/fake_alpha_sweep.png"),
        ) as mock_diag:
            result = asyncio.run(
                analyze_airplane_alpha_sweep_diagram(
                    aeroplane_id=self.test_plane_id,
                    sweep_request=sweep_request,
                    db=mock_db,
                    request=mock_request,
                    settings=mock_settings,
                )
            )

        self.assertIsInstance(result, StaticUrlResponse)
        self.assertEqual(result.url, "http://testserver/static/fake_alpha_sweep.png")
        mock_diag.assert_awaited_once()

    def test_analyze_airplane_alpha_sweep_diagram_not_found_maps_to_404(self):
        """404 propagation for the alpha sweep diagram endpoint."""
        mock_db = MagicMock()
        mock_request = MagicMock(spec=Request)
        mock_request.base_url = "http://testserver/"
        mock_settings = MagicMock(base_url="http://testserver")
        sweep_request = AlphaSweepRequest.model_construct(
            altitude=0.0,
            velocity=20.0,
            alpha_start=0.0,
            alpha_end=10.0,
            alpha_num=5,
            beta=0.0,
            p=0.0,
            q=0.0,
            r=0.0,
            xyz_ref=[0.0, 0.0, 0.0],
        )

        with patch(
            "app.api.v2.endpoints.aeroanalysis.analysis_service.get_alpha_sweep_diagram_url",
            new=AsyncMock(side_effect=NotFoundError("aeroplane not found")),
        ):
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(
                    analyze_airplane_alpha_sweep_diagram(
                        aeroplane_id=self.test_plane_id,
                        sweep_request=sweep_request,
                        db=mock_db,
                        request=mock_request,
                        settings=mock_settings,
                    )
                )
        self.assertEqual(raised.exception.status_code, 404)

    def test_analyze_airplane_simple_sweep_success(self):
        mock_db = MagicMock()
        sweep_request = SimpleSweepRequest.model_construct(
            sweep_var="velocity",
            step_size=5.0,
            num=5,
            altitude=1000.0,
            velocity=20.0,
            alpha=5.0,
            beta=0.0,
            p=0.0,
            q=0.0,
            r=0.0,
            xyz_ref=[0.0, 0.0, 0.0],
        )

        with patch(
            "app.api.v2.endpoints.aeroanalysis.analysis_service.analyze_simple_sweep",
            new=AsyncMock(return_value={"sweep": []}),
        ) as mock_sweep:
            result = asyncio.run(
                analyze_airplane_simple_sweep(
                    aeroplane_id=self.test_plane_id,
                    sweep_request=sweep_request,
                    db=mock_db,
                )
            )

        self.assertEqual(result, {"sweep": []})
        mock_sweep.assert_awaited_once_with(mock_db, self.test_plane_id, sweep_request)

    def test_get_streamlines_three_view_success(self):
        mock_db = MagicMock()
        mock_request = MagicMock(spec=Request)
        mock_request.base_url = "http://example.com/"
        mock_settings = MagicMock()
        mock_settings.base_url = "http://example.com"

        with patch(
            "app.api.v2.endpoints.aeroanalysis.analysis_service.get_streamlines_three_view_image",
            new=AsyncMock(return_value=b"png"),
        ) as mock_image, patch("app.api.v2.endpoints.aeroanalysis.uuid4") as mock_uuid:
            mock_uuid.return_value = MagicMock(hex="abc123")

            result = asyncio.run(
                get_streamlines_three_view(
                    aeroplane_id=self.test_plane_id,
                    operating_point=self.test_operating_point,
                    db=mock_db,
                    request=mock_request,
                    settings=mock_settings,
                )
            )

        self.assertIsInstance(result, StaticUrlResponse)
        self.assertTrue(result.url.endswith(f"/static/{self.test_plane_id}/png/streamlines_three_view_abc123.png"))
        mock_image.assert_awaited_once_with(mock_db, self.test_plane_id, self.test_operating_point)

    def test_get_aeroplane_three_view_success(self):
        mock_db = MagicMock()
        mock_request = MagicMock(spec=Request)
        mock_request.base_url = "http://example.com/"
        mock_settings = MagicMock()
        mock_settings.base_url = "http://example.com"

        with patch(
            "app.api.v2.endpoints.aeroanalysis.analysis_service.get_three_view_image",
            new=AsyncMock(return_value=b"png"),
        ) as mock_image, patch("app.api.v2.endpoints.aeroanalysis.uuid4") as mock_uuid:
            mock_uuid.return_value = MagicMock(hex="def456")

            result = asyncio.run(
                get_aeroplane_three_view(
                    aeroplane_id=self.test_plane_id,
                    db=mock_db,
                    request=mock_request,
                    settings=mock_settings,
                )
            )

        self.assertIsInstance(result, StaticUrlResponse)
        self.assertTrue(result.url.endswith(f"/static/{self.test_plane_id}/png/three_view_def456.png"))
        mock_image.assert_awaited_once_with(mock_db, self.test_plane_id)

    def test_calculate_streamlines_json_success(self):
        """Happy-path: POST streamlines returns Plotly figure JSON."""
        from app.api.v2.endpoints.aeroanalysis import calculate_streamlines_json

        mock_db = MagicMock()
        plotly_figure = {
            "data": [{"type": "mesh3d", "x": [], "y": [], "z": []}],
            "layout": {"scene": {}},
        }

        with patch(
            "app.api.v2.endpoints.aeroanalysis.analysis_service.calculate_streamlines_json",
            new=AsyncMock(return_value=plotly_figure),
        ) as mock_calc:
            result = asyncio.run(
                calculate_streamlines_json(
                    aeroplane_id=self.test_plane_id,
                    operating_point=self.test_operating_point,
                    db=mock_db,
                )
            )

        self.assertIsInstance(result, dict)
        self.assertIn("data", result)
        self.assertIsInstance(result["data"], list)
        self.assertIn("layout", result)
        self.assertIsInstance(result["layout"], dict)
        mock_calc.assert_awaited_once_with(
            mock_db,
            self.test_plane_id,
            self.test_operating_point,
        )

    def test_calculate_streamlines_json_not_found(self):
        """404 propagation when aeroplane does not exist."""
        from app.api.v2.endpoints.aeroanalysis import calculate_streamlines_json

        mock_db = MagicMock()

        with patch(
            "app.api.v2.endpoints.aeroanalysis.analysis_service.calculate_streamlines_json",
            new=AsyncMock(side_effect=NotFoundError("Aeroplane not found")),
        ):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(
                    calculate_streamlines_json(
                        aeroplane_id=self.test_plane_id,
                        operating_point=self.test_operating_point,
                        db=mock_db,
                    )
                )

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("Aeroplane not found", str(ctx.exception.detail))


class TestAnalysisServiceAwaitContract(unittest.TestCase):
    """Service-level tests that verify sync helper functions are NOT awaited.

    These tests call the async service functions directly (not the endpoint
    layer) with MagicMock (not AsyncMock) for the sync dependencies. If a
    sync function is incorrectly awaited, asyncio will raise TypeError.
    """

    def setUp(self):
        self.test_plane_id = uuid.uuid4()
        self.mock_db = MagicMock()
        self.mock_plane_schema = MagicMock()
        self.mock_plane_schema.name = "TestPlane"
        self.mock_plane_schema.wings = {}
        self.test_operating_point = OperatingPointSchema.model_construct(
            velocity=10.0, alpha=5.0, beta=0.0,
            p=0.0, q=0.0, r=0.0, xyz_ref=[0.0, 0.0, 0.0],
        )

    def _make_mock_result(self):
        """Build a mock analysis result with the minimum attributes."""
        result = MagicMock()
        result.flight_condition.alpha = [0.0, 2.0, 4.0]
        result.coefficients.CL = [0.0, 0.2, 0.4]
        result.coefficients.CD = [0.01, 0.02, 0.04]
        result.coefficients.Cm = [-0.05, -0.03, -0.01]
        result.reference.Xnp = None
        result.reference.Xnp_lat = None
        result.forces.L = None
        result.forces.D = None
        return result

    def test_analyze_alpha_sweep_does_not_await_sync_functions(self):
        """analyse_aerodynamics is sync — awaiting it raises TypeError."""
        from app.services.analysis_service import analyze_alpha_sweep

        mock_result = self._make_mock_result()
        sweep_request = AlphaSweepRequest.model_construct(
            altitude=1000.0, velocity=30.0,
            alpha_start=-5, alpha_end=15, alpha_num=3,
            beta=0.0, p=0.0, q=0.0, r=0.0, xyz_ref=[0, 0, 0],
        )

        with (
            patch(
                "app.services.analysis_service.get_aeroplane_schema_or_raise",
                return_value=self.mock_plane_schema,
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
                analyze_alpha_sweep(self.mock_db, self.test_plane_id, sweep_request)
            )

        self.assertIn("analysis", result)
        self.assertIn("characteristic_points", result)

    def test_analyze_airplane_does_not_await_sync_functions(self):
        """analyse_aerodynamics is sync — awaiting it raises TypeError."""
        from app.services.analysis_service import analyze_airplane

        mock_result = MagicMock()

        with (
            patch(
                "app.services.analysis_service.get_aeroplane_schema_or_raise",
                return_value=self.mock_plane_schema,
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
                    self.mock_db, self.test_plane_id,
                    self.test_operating_point, AnalysisToolUrlType.AEROBUILDUP,
                )
            )

        self.assertEqual(result, mock_result)


if __name__ == "__main__":
    unittest.main()
