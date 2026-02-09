import unittest
import asyncio
import uuid
import io
from unittest.mock import MagicMock, patch
from fastapi import HTTPException, Request
from sqlalchemy.exc import SQLAlchemyError
import numpy as np
from starlette.responses import PlainTextResponse, Response

from app.api.v2.endpoints.aeroanalysis import (
    analyze_wing_post,
    analyze_airplane_post,
    calculate_streamlines,
    analyze_airplane_alpha_sweep,
    analyze_airplane_simple_sweep,
    get_streamlines_three_view,
    get_aeroplane_three_view,
)
from app.db.exceptions import NotFoundInDbException
from app.schemas.aeroanalysisschema import OperatingPointSchema
from app.schemas.AeroplaneRequest import AnalysisToolUrlType, AlphaSweepRequest, SimpleSweepRequest
from cad_designer.airplane.aircraft_topology.models.analysis_model import AnalysisModel

class TestAeroanalysis(unittest.TestCase):
    def setUp(self):
        self.test_plane_id = uuid.uuid4()
        self.test_wing_name = "test wing"
        self.test_operating_point = OperatingPointSchema.model_construct(
            velocity=10.0,
            alpha=5.0,
            beta=0.0,
            p=0.0,
            q=0.0,
            r=0.0,
            xyz_ref=[0.0, 0.0, 0.0]
        )
        self.test_analysis_tool = AnalysisToolUrlType.AEROBUILDUP

    @patch('app.api.v2.endpoints.aeroanalysis.get_wing_by_name_and_aeroplane_id')
    async def _test_analyze_wing_post_db_error(self, mock_get_wing):
        # Setup mock to raise SQLAlchemyError
        mock_get_wing.side_effect = SQLAlchemyError("Database error")
        mock_db = MagicMock()

        # Call function and check for exception
        with self.assertRaises(HTTPException) as ctx:
            await analyze_wing_post(
                aeroplane_id=self.test_plane_id,
                wing_name=self.test_wing_name,
                operating_point=self.test_operating_point,
                analysis_tool=self.test_analysis_tool,
                db=mock_db
            )

        # Assertions
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Database error", ctx.exception.detail)
        mock_get_wing.assert_called_once_with(self.test_plane_id, self.test_wing_name, mock_db)

    def test_analyze_wing_post_db_error(self):
        asyncio.run(self._test_analyze_wing_post_db_error())

    @patch('app.api.v2.endpoints.aeroanalysis.get_wing_by_name_and_aeroplane_id')
    async def _test_analyze_wing_post_not_found(self, mock_get_wing):
        # Setup mock to raise NotFoundInDbException
        mock_get_wing.side_effect = NotFoundInDbException("Wing not found")
        mock_db = MagicMock()

        # Call function and check for exception
        with self.assertRaises(HTTPException) as ctx:
            await analyze_wing_post(
                aeroplane_id=self.test_plane_id,
                wing_name=self.test_wing_name,
                operating_point=self.test_operating_point,
                analysis_tool=self.test_analysis_tool,
                db=mock_db
            )

        # Assertions
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("Wing not found", ctx.exception.detail)
        mock_get_wing.assert_called_once_with(self.test_plane_id, self.test_wing_name, mock_db)

    def test_analyze_wing_post_not_found(self):
        asyncio.run(self._test_analyze_wing_post_not_found())

    @patch('app.api.v2.endpoints.aeroanalysis.get_wing_by_name_and_aeroplane_id')
    async def _test_analyze_wing_post_unexpected_error(self, mock_get_wing):
        # Setup mock to raise unexpected exception
        mock_get_wing.side_effect = Exception("Unexpected error")
        mock_db = MagicMock()

        # Call function and check for exception
        with self.assertRaises(HTTPException) as ctx:
            await analyze_wing_post(
                aeroplane_id=self.test_plane_id,
                wing_name=self.test_wing_name,
                operating_point=self.test_operating_point,
                analysis_tool=self.test_analysis_tool,
                db=mock_db
            )

        # Assertions
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Unexpected error", ctx.exception.detail)
        mock_get_wing.assert_called_once_with(self.test_plane_id, self.test_wing_name, mock_db)

    def test_analyze_wing_post_unexpected_error(self):
        asyncio.run(self._test_analyze_wing_post_unexpected_error())

    @patch('app.api.v2.endpoints.aeroanalysis.get_aeroplane_by_id')
    async def _test_analyze_airplane_post_db_error(self, mock_get_aeroplane):
        # Setup mock to raise SQLAlchemyError
        mock_get_aeroplane.side_effect = SQLAlchemyError("Database error")
        mock_db = MagicMock()

        # Call function and check for exception
        with self.assertRaises(HTTPException) as ctx:
            await analyze_airplane_post(
                aeroplane_id=self.test_plane_id,
                operating_point=self.test_operating_point,
                analysis_tool=self.test_analysis_tool,
                db=mock_db
            )

        # Assertions
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Database error", ctx.exception.detail)
        mock_get_aeroplane.assert_called_once_with(self.test_plane_id, mock_db)

    def test_analyze_airplane_post_db_error(self):
        asyncio.run(self._test_analyze_airplane_post_db_error())

    @patch('app.api.v2.endpoints.aeroanalysis.get_aeroplane_by_id')
    async def _test_analyze_airplane_post_not_found(self, mock_get_aeroplane):
        # Setup mock to raise NotFoundInDbException
        mock_get_aeroplane.side_effect = NotFoundInDbException("Aeroplane not found")
        mock_db = MagicMock()

        # Call function and check for exception
        with self.assertRaises(HTTPException) as ctx:
            await analyze_airplane_post(
                aeroplane_id=self.test_plane_id,
                operating_point=self.test_operating_point,
                analysis_tool=self.test_analysis_tool,
                db=mock_db
            )

        # Assertions
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("Aeroplane not found", ctx.exception.detail)
        mock_get_aeroplane.assert_called_once_with(self.test_plane_id, mock_db)

    def test_analyze_airplane_post_not_found(self):
        asyncio.run(self._test_analyze_airplane_post_not_found())

    @patch('app.api.v2.endpoints.aeroanalysis.get_aeroplane_by_id')
    async def _test_analyze_airplane_post_unexpected_error(self, mock_get_aeroplane):
        # Setup mock to raise unexpected exception
        mock_get_aeroplane.side_effect = Exception("Unexpected error")
        mock_db = MagicMock()

        # Call function and check for exception
        with self.assertRaises(HTTPException) as ctx:
            await analyze_airplane_post(
                aeroplane_id=self.test_plane_id,
                operating_point=self.test_operating_point,
                analysis_tool=self.test_analysis_tool,
                db=mock_db
            )

        # Assertions
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Unexpected error", ctx.exception.detail)
        mock_get_aeroplane.assert_called_once_with(self.test_plane_id, mock_db)

    def test_analyze_airplane_post_unexpected_error(self):
        asyncio.run(self._test_analyze_airplane_post_unexpected_error())

    @patch('app.api.v2.endpoints.aeroanalysis.get_wing_by_name_and_aeroplane_id')
    @patch('app.api.v2.endpoints.aeroanalysis.aeroplaneSchemaToAsbAirplane_async')
    @patch('app.api.v2.endpoints.aeroanalysis.analyse_aerodynamics')
    async def _test_analyze_wing_post_success(self, mock_analyse_aerodynamics, mock_asb_airplane, mock_get_wing):
        # Setup mocks
        mock_plane_schema = MagicMock()
        mock_get_wing.return_value = mock_plane_schema

        mock_airplane = MagicMock()
        mock_asb_airplane.return_value = mock_airplane

        mock_analysis_result = MagicMock(spec=AnalysisModel)
        mock_figure = None
        mock_analyse_aerodynamics.return_value = (mock_analysis_result, mock_figure)

        mock_db = MagicMock()

        # Call function
        result = await analyze_wing_post(
            aeroplane_id=self.test_plane_id,
            wing_name=self.test_wing_name,
            operating_point=self.test_operating_point,
            analysis_tool=self.test_analysis_tool,
            db=mock_db
        )

        # Assertions
        mock_get_wing.assert_called_once_with(self.test_plane_id, self.test_wing_name, mock_db)
        mock_asb_airplane.assert_called_once_with(plane_schema=mock_plane_schema)
        mock_analyse_aerodynamics.assert_called_once()
        self.assertEqual(result, mock_analysis_result)

        # Verify airplane modifications
        self.assertEqual(mock_airplane.xyz_ref, self.test_operating_point.xyz_ref)
        self.assertEqual(mock_airplane.fuselages, [])

    def test_analyze_wing_post_success(self):
        asyncio.run(self._test_analyze_wing_post_success())

    @patch('app.api.v2.endpoints.aeroanalysis.get_aeroplane_by_id')
    @patch('app.api.v2.endpoints.aeroanalysis.aeroplaneSchemaToAsbAirplane_async')
    @patch('app.api.v2.endpoints.aeroanalysis.analyse_aerodynamics')
    async def _test_analyze_airplane_post_success(self, mock_analyse_aerodynamics, mock_asb_airplane, mock_get_aeroplane):
        # Setup mocks
        mock_plane_schema = MagicMock()
        mock_get_aeroplane.return_value = mock_plane_schema

        mock_airplane = MagicMock()
        mock_asb_airplane.return_value = mock_airplane

        mock_analysis_result = MagicMock(spec=AnalysisModel)
        mock_figure = None
        mock_analyse_aerodynamics.return_value = (mock_analysis_result, mock_figure)

        mock_db = MagicMock()

        # Call function
        result = await analyze_airplane_post(
            aeroplane_id=self.test_plane_id,
            operating_point=self.test_operating_point,
            analysis_tool=self.test_analysis_tool,
            db=mock_db
        )

        # Assertions
        mock_get_aeroplane.assert_called_once_with(self.test_plane_id, mock_db)
        mock_asb_airplane.assert_called_once_with(plane_schema=mock_plane_schema)
        mock_analyse_aerodynamics.assert_called_once_with(self.test_analysis_tool, self.test_operating_point, mock_airplane)
        self.assertEqual(result, mock_analysis_result)

    def test_analyze_airplane_post_success(self):
        asyncio.run(self._test_analyze_airplane_post_success())

    @patch('app.api.v2.endpoints.aeroanalysis.get_aeroplane_by_id')
    @patch('app.api.v2.endpoints.aeroanalysis.aeroplaneSchemaToAsbAirplane_async')
    @patch('app.api.v2.endpoints.aeroanalysis.analyse_aerodynamics')
    @patch('app.api.v2.endpoints.aeroanalysis.save_content_and_get_static_url')
    async def _test_calculate_streamlines_success(self, mock_save_content, mock_analyse_aerodynamics, 
                                                 mock_asb_airplane, mock_get_aeroplane):
        # Setup mocks
        mock_plane_schema = MagicMock()
        mock_get_aeroplane.return_value = mock_plane_schema

        mock_airplane = MagicMock()
        mock_asb_airplane.return_value = mock_airplane

        mock_analysis_result = MagicMock(spec=AnalysisModel)
        mock_figure = MagicMock()
        mock_figure.to_html.return_value = "<html>Test content</html>"
        mock_analyse_aerodynamics.return_value = (mock_analysis_result, mock_figure)

        mock_url = "http://example.com/static/test-url"
        mock_save_content.return_value = mock_url

        mock_db = MagicMock()
        mock_request = MagicMock(spec=Request)
        mock_request.base_url = "http://example.com/"

        mock_settings = MagicMock()
        mock_settings.base_url = "http://example.com"

        # Call function
        result = await calculate_streamlines(
            aeroplane_id=self.test_plane_id,
            operating_point=self.test_operating_point,
            db=mock_db,
            request=mock_request,
            settings=mock_settings
        )

        # Assertions
        mock_get_aeroplane.assert_called_once_with(self.test_plane_id, mock_db)
        mock_asb_airplane.assert_called_once_with(plane_schema=mock_plane_schema)
        mock_analyse_aerodynamics.assert_called_once_with(
            AnalysisToolUrlType.VORTEX_LATTICE, 
            self.test_operating_point, 
            mock_airplane,
            draw_streamlines=True
        )
        mock_figure.to_html.assert_called_once()
        mock_save_content.assert_called_once()
        self.assertEqual(result, mock_url)

    def test_calculate_streamlines_success(self):
        asyncio.run(self._test_calculate_streamlines_success())

    @patch('app.api.v2.endpoints.aeroanalysis.get_aeroplane_by_id')
    @patch('app.api.v2.endpoints.aeroanalysis.aeroplaneSchemaToAsbAirplane_async')
    @patch('app.api.v2.endpoints.aeroanalysis.analyse_aerodynamics')
    async def _test_analyze_airplane_alpha_sweep_success(self, mock_analyse_aerodynamics, 
                                                       mock_asb_airplane, mock_get_aeroplane):
        # Setup mocks
        mock_plane_schema = MagicMock()
        mock_get_aeroplane.return_value = mock_plane_schema

        mock_airplane = MagicMock()
        mock_asb_airplane.return_value = mock_airplane

        mock_analysis_result = MagicMock(spec=AnalysisModel)
        mock_figure = None
        mock_analyse_aerodynamics.return_value = (mock_analysis_result, mock_figure)

        mock_db = MagicMock()

        # Create a sweep request
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
            xyz_ref=[0.0, 0.0, 0.0]
        )

        # Call function
        result = await analyze_airplane_alpha_sweep(
            aeroplane_id=self.test_plane_id,
            sweep_request=sweep_request,
            db=mock_db
        )

        # Assertions
        mock_get_aeroplane.assert_called_once_with(self.test_plane_id, mock_db)
        mock_asb_airplane.assert_called_once_with(plane_schema=mock_plane_schema)
        mock_analyse_aerodynamics.assert_called_once()
        # Check that the operating point was created correctly with a numpy array for alpha
        args, kwargs = mock_analyse_aerodynamics.call_args
        self.assertEqual(args[0], AnalysisToolUrlType.AEROBUILDUP)
        self.assertEqual(args[2], mock_airplane)
        op_point = args[1]
        self.assertEqual(op_point.altitude, sweep_request.altitude)
        self.assertEqual(op_point.velocity, sweep_request.velocity)
        self.assertEqual(op_point.beta, sweep_request.beta)
        self.assertEqual(op_point.p, sweep_request.p)
        self.assertEqual(op_point.q, sweep_request.q)
        self.assertEqual(op_point.r, sweep_request.r)
        self.assertEqual(op_point.xyz_ref, sweep_request.xyz_ref)
        # Check that alpha is a numpy array with the correct values
        self.assertTrue(isinstance(op_point.alpha, np.ndarray))
        self.assertEqual(len(op_point.alpha), sweep_request.alpha_num)
        self.assertEqual(op_point.alpha[0], sweep_request.alpha_start)
        self.assertEqual(op_point.alpha[-1], sweep_request.alpha_end)

        self.assertEqual(result, mock_analysis_result)

    def test_analyze_airplane_alpha_sweep_success(self):
        asyncio.run(self._test_analyze_airplane_alpha_sweep_success())

    @patch('app.api.v2.endpoints.aeroanalysis.get_aeroplane_by_id')
    @patch('app.api.v2.endpoints.aeroanalysis.aeroplaneSchemaToAsbAirplane_async')
    @patch('app.api.v2.endpoints.aeroanalysis.analyse_aerodynamics')
    async def _test_analyze_airplane_simple_sweep_success(self, mock_analyse_aerodynamics, 
                                                        mock_asb_airplane, mock_get_aeroplane):
        # Setup mocks
        mock_plane_schema = MagicMock()
        mock_get_aeroplane.return_value = mock_plane_schema

        mock_airplane = MagicMock()
        mock_asb_airplane.return_value = mock_airplane

        mock_analysis_result = MagicMock(spec=AnalysisModel)
        mock_figure = None
        mock_analyse_aerodynamics.return_value = (mock_analysis_result, mock_figure)

        mock_db = MagicMock()

        # Create a sweep request for velocity sweep
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
            xyz_ref=[0.0, 0.0, 0.0]
        )

        # Call function
        result = await analyze_airplane_simple_sweep(
            aeroplane_id=self.test_plane_id,
            sweep_request=sweep_request,
            db=mock_db
        )

        # Assertions
        mock_get_aeroplane.assert_called_once_with(self.test_plane_id, mock_db)
        mock_asb_airplane.assert_called_once_with(plane_schema=mock_plane_schema)
        mock_analyse_aerodynamics.assert_called_once()
        # Check that the operating point was created correctly with a numpy array for velocity
        args, kwargs = mock_analyse_aerodynamics.call_args
        self.assertEqual(args[0], AnalysisToolUrlType.AEROBUILDUP)
        self.assertEqual(args[2], mock_airplane)
        op_point = args[1]
        self.assertEqual(op_point.altitude, sweep_request.altitude)
        self.assertEqual(op_point.alpha, sweep_request.alpha)
        self.assertEqual(op_point.beta, sweep_request.beta)
        self.assertEqual(op_point.p, sweep_request.p)
        self.assertEqual(op_point.q, sweep_request.q)
        self.assertEqual(op_point.r, sweep_request.r)
        self.assertEqual(op_point.xyz_ref, sweep_request.xyz_ref)
        # Check that velocity is a numpy array with the correct values
        self.assertTrue(isinstance(op_point.velocity, np.ndarray))
        self.assertEqual(len(op_point.velocity), sweep_request.num)
        self.assertEqual(op_point.velocity[0], sweep_request.velocity)

        self.assertEqual(result, mock_analysis_result)

    def test_analyze_airplane_simple_sweep_success(self):
        asyncio.run(self._test_analyze_airplane_simple_sweep_success())

    @patch('app.api.v2.endpoints.aeroanalysis.get_aeroplane_by_id')
    @patch('app.api.v2.endpoints.aeroanalysis.aeroplaneSchemaToAsbAirplane_async')
    @patch('app.api.v2.endpoints.aeroanalysis.analyse_aerodynamics')
    @patch('app.api.v2.endpoints.aeroanalysis.compile_four_view_figure')
    async def _test_get_streamlines_three_view_success(self, mock_compile_four_view, 
                                                     mock_analyse_aerodynamics, 
                                                     mock_asb_airplane, mock_get_aeroplane):
        # Setup mocks
        mock_plane_schema = MagicMock()
        mock_get_aeroplane.return_value = mock_plane_schema

        mock_airplane = MagicMock()
        mock_asb_airplane.return_value = mock_airplane

        mock_analysis_result = MagicMock(spec=AnalysisModel)
        mock_figure = MagicMock()
        mock_analyse_aerodynamics.return_value = (mock_analysis_result, mock_figure)

        mock_compiled_figure = MagicMock()
        mock_compiled_figure.to_image.return_value = b"test image data"
        mock_compile_four_view.return_value = mock_compiled_figure

        mock_db = MagicMock()

        # Call function
        result = await get_streamlines_three_view(
            aeroplane_id=self.test_plane_id,
            operating_point=self.test_operating_point,
            db=mock_db
        )

        # Assertions
        mock_get_aeroplane.assert_called_once_with(self.test_plane_id, mock_db)
        mock_asb_airplane.assert_called_once_with(plane_schema=mock_plane_schema)
        mock_analyse_aerodynamics.assert_called_once_with(
            AnalysisToolUrlType.VORTEX_LATTICE, 
            self.test_operating_point, 
            mock_airplane,
            draw_streamlines=True,
            backend='plotly'
        )
        mock_compile_four_view.assert_called_once_with(mock_figure)
        mock_compiled_figure.to_image.assert_called_once_with(format="png", width=1000, height=1000, scale=2)

        self.assertIsInstance(result, Response)
        self.assertEqual(result.body, b"test image data")
        self.assertEqual(result.media_type, "image/png")

    def test_get_streamlines_three_view_success(self):
        asyncio.run(self._test_get_streamlines_three_view_success())

    @patch('app.api.v2.endpoints.aeroanalysis.get_aeroplane_by_id')
    @patch('app.api.v2.endpoints.aeroanalysis.aeroplaneSchemaToAsbAirplane_async')
    @patch('app.api.v2.endpoints.aeroanalysis.plt')
    @patch('app.api.v2.endpoints.aeroanalysis.io.BytesIO')
    async def _test_get_aeroplane_three_view_success(self, mock_bytesio, mock_plt, 
                                                   mock_asb_airplane, mock_get_aeroplane):
        # Setup mocks
        mock_plane_schema = MagicMock()
        mock_get_aeroplane.return_value = mock_plane_schema

        mock_airplane = MagicMock()
        mock_asb_airplane.return_value = mock_airplane

        mock_fig = MagicMock()
        mock_plt.figure.return_value = mock_fig

        mock_axs = MagicMock()
        mock_airplane.draw_three_view.return_value = mock_axs

        mock_io = MagicMock()
        mock_io.getvalue.return_value = b"test image data"
        mock_bytesio.return_value = mock_io

        mock_db = MagicMock()

        # Call function
        result = await get_aeroplane_three_view(
            aeroplane_id=self.test_plane_id,
            db=mock_db
        )

        # Assertions
        mock_get_aeroplane.assert_called_once_with(self.test_plane_id, mock_db)
        mock_asb_airplane.assert_called_once_with(plane_schema=mock_plane_schema)
        mock_plt.figure.assert_called_once_with(figsize=(10, 10))
        mock_airplane.draw_three_view.assert_called_once_with(show=False)
        mock_plt.savefig.assert_called_once()
        mock_plt.close.assert_called_once_with(mock_fig)

        self.assertIsInstance(result, Response)
        self.assertEqual(result.body, b"test image data")
        self.assertEqual(result.media_type, "image/png")

    def test_get_aeroplane_three_view_success(self):
        asyncio.run(self._test_get_aeroplane_three_view_success())

if __name__ == "__main__":
    unittest.main()
