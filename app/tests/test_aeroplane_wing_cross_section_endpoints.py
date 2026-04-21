import unittest
import asyncio
import uuid
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.api.v2.endpoints.aeroplane.wings import (
    get_aeroplane_wing_cross_sections,
    delete_aeroplane_wing_cross_sections,
    get_aeroplane_wing_cross_section,
    create_aeroplane_wing_cross_section,
    update_aeroplane_wing_cross_section,
    delete_aeroplane_wing_cross_section,
    get_aeroplane_wing_cross_section_spars,
    create_aeroplane_wing_cross_section_spar,
    get_aeroplane_wing_cross_section_control_surface,
    patch_aeroplane_wing_cross_section_control_surface,
    delete_aeroplane_wing_cross_section_control_surface,
    get_aeroplane_wing_cross_section_control_surface_cad_details,
    patch_aeroplane_wing_cross_section_control_surface_cad_details,
    delete_aeroplane_wing_cross_section_control_surface_cad_details,
    get_aeroplane_wing_cross_section_control_surface_cad_details_servo_details,
    patch_aeroplane_wing_cross_section_control_surface_cad_details_servo_details,
    delete_aeroplane_wing_cross_section_control_surface_cad_details_servo_details,
)

from app import schemas

class TestAeroplaneWingCrossSectionEndpoints(unittest.TestCase):
    def setUp(self):
        self.test_plane_id = uuid.uuid4()
        self.test_wing_name = "test_wing"
        self.test_cross_section_index = 0

    def test_get_cross_sections_success(self):
        mock_db = MagicMock()
        # Simulate plane with a wing that has cross sections
        wing_model = MagicMock(name=self.test_wing_name)
        wing_model.name = self.test_wing_name
        wing_model.x_secs = [MagicMock(), MagicMock()]
        plane = MagicMock()
        plane.wings = [wing_model]
        mock_db.query.return_value.filter.return_value.first.return_value = plane

        # Mock the schema validation
        mock_schemas = [
            schemas.WingXSecReadSchema.model_construct(airfoil="NACA0012", chord=1.0),
            schemas.WingXSecReadSchema.model_construct(airfoil="NACA2412", chord=0.8)
        ]

        with patch('app.schemas.aeroplaneschema.WingXSecReadSchema.model_validate',
                  side_effect=mock_schemas) as validate:
            result = asyncio.run(
                get_aeroplane_wing_cross_sections(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    db=mock_db
                )
            )

            self.assertEqual(len(result), 2)
            self.assertEqual(validate.call_count, 2)

    def test_get_cross_sections_aeroplane_not_found(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                get_aeroplane_wing_cross_sections(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    db=mock_db
                )
            )
        self.assertEqual(ctx.exception.status_code, 404)

    def test_get_cross_sections_wing_not_found(self):
        mock_db = MagicMock()
        plane = MagicMock()
        plane.wings = []  # No wings
        mock_db.query.return_value.filter.return_value.first.return_value = plane

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                get_aeroplane_wing_cross_sections(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    db=mock_db
                )
            )
        self.assertEqual(ctx.exception.status_code, 404)

    @patch("app.api.v2.endpoints.aeroplane.wings.wing_service.get_wing_design_model", return_value="asb")
    def test_delete_cross_sections_success(self, _mock_dm):
        mock_db = MagicMock()
        # Simulate plane with a wing that has cross sections
        wing_model = MagicMock(name=self.test_wing_name)
        wing_model.name = self.test_wing_name
        wing_model.design_model = "asb"
        wing_model.x_secs = [MagicMock(), MagicMock()]
        plane = MagicMock()
        plane.wings = [wing_model]
        mock_db.query.return_value.filter.return_value.first.return_value = plane

        result = asyncio.run(
            delete_aeroplane_wing_cross_sections(
                aeroplane_id=self.test_plane_id,
                wing_name=self.test_wing_name,
                db=mock_db
            )
        )

        # Verify cross sections were cleared
        self.assertEqual(wing_model.x_secs, [])
        # Verify timestamp was updated
        self.assertIsNotNone(plane.updated_at)

    def test_get_cross_section_success(self):
        mock_db = MagicMock()
        # Simulate plane with a wing that has cross sections
        wing_model = MagicMock(name=self.test_wing_name)
        wing_model.name = self.test_wing_name
        cross_section = MagicMock()
        wing_model.x_secs = [cross_section]
        plane = MagicMock()
        plane.wings = [wing_model]
        mock_db.query.return_value.filter.return_value.first.return_value = plane

        mock_schema = schemas.WingXSecReadSchema.model_construct(airfoil="NACA0012", chord=1.0)

        with patch('app.schemas.aeroplaneschema.WingXSecReadSchema.model_validate',
                  return_value=mock_schema) as validate:
            result = asyncio.run(
                get_aeroplane_wing_cross_section(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    cross_section_index=self.test_cross_section_index,
                    db=mock_db
                )
            )

            validate.assert_called_once_with(cross_section, from_attributes=True)
            self.assertEqual(result, mock_schema)

    def test_get_cross_section_index_out_of_range(self):
        mock_db = MagicMock()
        # Simulate plane with a wing that has cross sections
        wing_model = MagicMock(name=self.test_wing_name)
        wing_model.name = self.test_wing_name
        wing_model.x_secs = []  # Empty list
        plane = MagicMock()
        plane.wings = [wing_model]
        mock_db.query.return_value.filter.return_value.first.return_value = plane

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                get_aeroplane_wing_cross_section(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    cross_section_index=0,  # Index 0 is out of range for empty list
                    db=mock_db
                )
            )
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "Cross-section not found")

    @patch("app.api.v2.endpoints.aeroplane.wings.wing_service.get_wing_design_model", return_value="asb")
    def test_create_cross_section_success(self, _mock_dm):
        mock_db = MagicMock()
        # Simulate plane with a wing that has cross sections
        wing_model = MagicMock(name=self.test_wing_name)
        wing_model.name = self.test_wing_name
        wing_model.design_model = "asb"
        wing_model.x_secs = []
        plane = MagicMock()
        plane.wings = [wing_model]
        mock_db.query.return_value.filter.return_value.first.return_value = plane

        request_schema = schemas.WingXSecGeometryWriteSchema.model_construct(
            xyz_le=[0.0, 0.0, 0.0],
            airfoil="NACA0012",
            chord=1.0,
            twist=0.0,
        )

        with patch('app.models.aeroplanemodel.WingXSecModel', autospec=True) as MockXSecModel:
            # Mock the created cross section
            mock_xsec = MagicMock()
            MockXSecModel.return_value = mock_xsec

            result = asyncio.run(
                create_aeroplane_wing_cross_section(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    cross_section_index=0,
                    request=request_schema,
                    db=mock_db
                )
            )

            # Verify cross section was added
            mock_db.add.assert_called_once()
            added_cs = mock_db.add.call_args[0][0]
            self.assertEqual(added_cs.airfoil, 'NACA0012')
            self.assertEqual(added_cs.chord, 1.0)
            # Verify timestamp was updated
            self.assertIsNotNone(plane.updated_at)

    @patch("app.api.v2.endpoints.aeroplane.wings.wing_service.get_wing_design_model", return_value="asb")
    def test_update_cross_section_success(self, _mock_dm):
        mock_db = MagicMock()
        # Simulate plane with a wing that has cross sections
        wing_model = MagicMock(name=self.test_wing_name)
        wing_model.name = self.test_wing_name
        wing_model.design_model = "asb"
        old_xsec = MagicMock()
        wing_model.x_secs = [old_xsec]
        plane = MagicMock()
        plane.wings = [wing_model]
        mock_db.query.return_value.filter.return_value.first.return_value = plane

        old_xsec.airfoil = "NACA0012"
        old_xsec.chord = 1.0
        old_xsec.twist = 0.0
        old_xsec.xyz_le = [0.0, 0.0, 0.0]
        request_schema = schemas.WingXSecGeometryWriteSchema.model_construct(
            xyz_le=[0.1, 0.0, 0.0],
            airfoil="NACA0019",
            chord=3.0,
            twist=2.5,
        )

        asyncio.run(
            update_aeroplane_wing_cross_section(
                aeroplane_id=self.test_plane_id,
                wing_name=self.test_wing_name,
                cross_section_index=0,
                request=request_schema,
                db=mock_db
            )
        )

        # Verify cross section was updated in place
        self.assertEqual(wing_model.x_secs[0].airfoil, "NACA0019")
        self.assertEqual(wing_model.x_secs[0].chord, 3.0)
        self.assertEqual(wing_model.x_secs[0].twist, 2.5)
        self.assertEqual(wing_model.x_secs[0].xyz_le, [0.1, 0.0, 0.0])
        # Verify timestamp was updated
        self.assertIsNotNone(plane.updated_at)

    @patch("app.api.v2.endpoints.aeroplane.wings.wing_service.get_wing_design_model", return_value="asb")
    def test_delete_cross_section_success(self, _mock_dm):
        mock_db = MagicMock()
        # Simulate plane with a wing that has cross sections
        wing_model = MagicMock(name=self.test_wing_name)
        wing_model.name = self.test_wing_name
        wing_model.design_model = "asb"
        xsec_to_delete = MagicMock()
        wing_model.x_secs = [xsec_to_delete]
        plane = MagicMock()
        plane.wings = [wing_model]
        mock_db.query.return_value.filter.return_value.first.return_value = plane

        result = asyncio.run(
            delete_aeroplane_wing_cross_section(
                aeroplane_id=self.test_plane_id,
                wing_name=self.test_wing_name,
                cross_section_index=0,
                db=mock_db
            )
        )

        # Verify cross section was deleted
        self.assertEqual(wing_model.x_secs, [])
        # Verify timestamp was updated
        self.assertIsNotNone(plane.updated_at)

    def test_get_cross_sections_db_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = SQLAlchemyError("Database error")

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                get_aeroplane_wing_cross_sections(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    db=mock_db
                )
            )
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Database error", ctx.exception.detail)

    def test_get_cross_sections_unexpected_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("Unexpected error")

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                get_aeroplane_wing_cross_sections(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    db=mock_db
                )
            )
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Unexpected error", ctx.exception.detail)

    def test_delete_cross_sections_db_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = SQLAlchemyError("Database error")
        mock_db.execute.side_effect = SQLAlchemyError("Database error")

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                delete_aeroplane_wing_cross_sections(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    db=mock_db
                )
            )
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Database error", ctx.exception.detail)

    def test_delete_cross_sections_unexpected_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("Unexpected error")
        mock_db.execute.side_effect = Exception("Unexpected error")

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                delete_aeroplane_wing_cross_sections(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    db=mock_db
                )
            )
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Unexpected error", ctx.exception.detail)

    def test_get_cross_section_db_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = SQLAlchemyError("Database error")

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                get_aeroplane_wing_cross_section(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    cross_section_index=0,
                    db=mock_db
                )
            )
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Database error", ctx.exception.detail)

    def test_get_cross_section_unexpected_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("Unexpected error")

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                get_aeroplane_wing_cross_section(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    cross_section_index=0,
                    db=mock_db
                )
            )
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Unexpected error", ctx.exception.detail)

    def test_create_cross_section_db_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = SQLAlchemyError("Database error")
        mock_db.execute.side_effect = SQLAlchemyError("Database error")
        request_schema = schemas.WingXSecGeometryWriteSchema.model_construct(
            xyz_le=[0.0, 0.0, 0.0],
            airfoil="NACA0012",
            chord=1.0,
            twist=0.0,
        )

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                create_aeroplane_wing_cross_section(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    cross_section_index=0,
                    request=request_schema,
                    db=mock_db
                )
            )
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Database error", ctx.exception.detail)

    def test_create_cross_section_unexpected_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("Unexpected error")
        mock_db.execute.side_effect = Exception("Unexpected error")
        request_schema = schemas.WingXSecGeometryWriteSchema.model_construct(
            xyz_le=[0.0, 0.0, 0.0],
            airfoil="NACA0012",
            chord=1.0,
            twist=0.0,
        )

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                create_aeroplane_wing_cross_section(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    cross_section_index=0,
                    request=request_schema,
                    db=mock_db
                )
            )
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Unexpected error", ctx.exception.detail)

    def test_update_cross_section_db_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = SQLAlchemyError("Database error")
        mock_db.execute.side_effect = SQLAlchemyError("Database error")
        request_schema = schemas.WingXSecGeometryWriteSchema.model_construct(
            xyz_le=[0.0, 0.0, 0.0],
            airfoil="NACA0012",
            chord=1.0,
            twist=0.0,
        )

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                update_aeroplane_wing_cross_section(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    cross_section_index=0,
                    request=request_schema,
                    db=mock_db
                )
            )
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Database error", ctx.exception.detail)

    def test_update_cross_section_unexpected_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("Unexpected error")
        mock_db.execute.side_effect = Exception("Unexpected error")
        request_schema = schemas.WingXSecGeometryWriteSchema.model_construct(
            xyz_le=[0.0, 0.0, 0.0],
            airfoil="NACA0012",
            chord=1.0,
            twist=0.0,
        )

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                update_aeroplane_wing_cross_section(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    cross_section_index=0,
                    request=request_schema,
                    db=mock_db
                )
            )
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Unexpected error", ctx.exception.detail)

    def test_delete_cross_section_db_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = SQLAlchemyError("Database error")
        mock_db.execute.side_effect = SQLAlchemyError("Database error")

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                delete_aeroplane_wing_cross_section(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    cross_section_index=0,
                    db=mock_db
                )
            )
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Database error", ctx.exception.detail)

    def test_delete_cross_section_unexpected_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("Unexpected error")
        mock_db.execute.side_effect = Exception("Unexpected error")

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                delete_aeroplane_wing_cross_section(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    cross_section_index=0,
                    db=mock_db
                )
            )
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Unexpected error", ctx.exception.detail)

    def test_get_spars_success(self):
        mock_db = MagicMock()
        expected = [
            schemas.SpareDetailSchema.model_construct(
                spare_support_dimension_width=4.42,
                spare_support_dimension_height=4.42,
                spare_position_factor=0.25,
                spare_length=None,
                spare_start=0.0,
                spare_mode="standard",
                spare_vector=[0.0, 1.0, 0.0],
                spare_origin=[1.0, 2.0, 3.0],
            )
        ]
        with patch("app.api.v2.endpoints.aeroplane.wings.wing_service.get_spares", return_value=expected) as get_spars:
            result = asyncio.run(
                get_aeroplane_wing_cross_section_spars(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    cross_section_index=self.test_cross_section_index,
                    db=mock_db,
                )
            )
        get_spars.assert_called_once_with(
            mock_db,
            self.test_plane_id,
            self.test_wing_name,
            self.test_cross_section_index,
        )
        self.assertEqual(result, expected)

    def test_create_spar_success(self):
        mock_db = MagicMock()
        request = schemas.SpareDetailSchema.model_construct(
            spare_support_dimension_width=4.42,
            spare_support_dimension_height=4.42,
            spare_position_factor=0.25,
            spare_length=None,
            spare_start=0.0,
            spare_mode="standard",
            spare_vector=[0.0, 1.0, 0.0],
            spare_origin=[1.0, 2.0, 3.0],
        )
        with patch("app.api.v2.endpoints.aeroplane.wings.wing_service.get_wing_design_model", return_value="asb"), \
             patch("app.api.v2.endpoints.aeroplane.wings.wing_service.create_spare", return_value=None) as create_spare:
            result = asyncio.run(
                create_aeroplane_wing_cross_section_spar(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    cross_section_index=self.test_cross_section_index,
                    request=request,
                    db=mock_db,
                )
            )
        create_spare.assert_called_once_with(
            mock_db,
            self.test_plane_id,
            self.test_wing_name,
            self.test_cross_section_index,
            request,
        )
        self.assertEqual(result.status, "created")
        self.assertEqual(result.operation, "create_wing_cross_section_spar")

    def test_control_surface_endpoints_delegate_to_service(self):
        mock_db = MagicMock()
        expected = schemas.ControlSurfaceSchema.model_construct(
            name="aileron",
            hinge_point=0.8,
            symmetric=False,
            deflection=3.0,
        )
        patch_request = schemas.ControlSurfacePatchSchema.model_construct(hinge_point=0.82)

        with patch("app.api.v2.endpoints.aeroplane.wings.wing_service.get_control_surface", return_value=expected) as get_cs:
            result = asyncio.run(
                get_aeroplane_wing_cross_section_control_surface(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    cross_section_index=self.test_cross_section_index,
                    db=mock_db,
                )
            )
        get_cs.assert_called_once_with(mock_db, self.test_plane_id, self.test_wing_name, self.test_cross_section_index)
        self.assertEqual(result, expected)

        with patch("app.api.v2.endpoints.aeroplane.wings.wing_service.get_wing_design_model", return_value="asb"), \
             patch("app.api.v2.endpoints.aeroplane.wings.wing_service.patch_control_surface", return_value=expected) as patch_cs:
            result = asyncio.run(
                patch_aeroplane_wing_cross_section_control_surface(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    cross_section_index=self.test_cross_section_index,
                    request=patch_request,
                    db=mock_db,
                )
            )
        patch_cs.assert_called_once_with(
            mock_db, self.test_plane_id, self.test_wing_name, self.test_cross_section_index, patch_request
        )
        self.assertEqual(result, expected)

        with patch("app.api.v2.endpoints.aeroplane.wings.wing_service.get_wing_design_model", return_value="asb"), \
             patch("app.api.v2.endpoints.aeroplane.wings.wing_service.delete_control_surface", return_value=None) as delete_cs:
            result = asyncio.run(
                delete_aeroplane_wing_cross_section_control_surface(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    cross_section_index=self.test_cross_section_index,
                    db=mock_db,
                )
            )
        delete_cs.assert_called_once_with(mock_db, self.test_plane_id, self.test_wing_name, self.test_cross_section_index)
        self.assertEqual(result.status, "ok")

    def test_control_surface_cad_details_endpoints_delegate_to_service(self):
        mock_db = MagicMock()
        expected = schemas.ControlSurfaceCadDetailsSchema.model_construct(
            rel_chord_tip=0.75,
            hinge_spacing=2.0,
        )
        patch_request = schemas.ControlSurfaceCadDetailsPatchSchema.model_construct(rel_chord_tip=0.77)

        with patch(
            "app.api.v2.endpoints.aeroplane.wings.wing_service.get_control_surface_cad_details",
            return_value=expected,
        ) as get_cad_details:
            result = asyncio.run(
                get_aeroplane_wing_cross_section_control_surface_cad_details(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    cross_section_index=self.test_cross_section_index,
                    db=mock_db,
                )
            )
        get_cad_details.assert_called_once_with(
            mock_db,
            self.test_plane_id,
            self.test_wing_name,
            self.test_cross_section_index,
        )
        self.assertEqual(result, expected)

        with patch("app.api.v2.endpoints.aeroplane.wings.wing_service.get_wing_design_model", return_value="asb"), \
             patch(
            "app.api.v2.endpoints.aeroplane.wings.wing_service.patch_control_surface_cad_details",
            return_value=expected,
        ) as patch_cad_details:
            result = asyncio.run(
                patch_aeroplane_wing_cross_section_control_surface_cad_details(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    cross_section_index=self.test_cross_section_index,
                    request=patch_request,
                    db=mock_db,
                )
            )
        patch_cad_details.assert_called_once_with(
            mock_db, self.test_plane_id, self.test_wing_name, self.test_cross_section_index, patch_request
        )
        self.assertEqual(result, expected)

        with patch("app.api.v2.endpoints.aeroplane.wings.wing_service.get_wing_design_model", return_value="asb"), \
             patch(
            "app.api.v2.endpoints.aeroplane.wings.wing_service.delete_control_surface_cad_details",
            return_value=None,
        ) as delete_cad_details:
            result = asyncio.run(
                delete_aeroplane_wing_cross_section_control_surface_cad_details(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    cross_section_index=self.test_cross_section_index,
                    db=mock_db,
                )
            )
        delete_cad_details.assert_called_once_with(
            mock_db,
            self.test_plane_id,
            self.test_wing_name,
            self.test_cross_section_index,
        )
        self.assertEqual(result.status, "ok")

    def test_control_surface_cad_servo_details_endpoints_delegate_to_service(self):
        mock_db = MagicMock()
        expected = schemas.ControlSurfaceServoDetailsSchema.model_construct(servo=1)
        patch_request = schemas.ControlSurfaceServoDetailsPatchSchema.model_construct(servo=2)

        with patch(
            "app.api.v2.endpoints.aeroplane.wings.wing_service.get_control_surface_cad_details_servo_details",
            return_value=expected,
        ) as get_servo_details:
            result = asyncio.run(
                get_aeroplane_wing_cross_section_control_surface_cad_details_servo_details(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    cross_section_index=self.test_cross_section_index,
                    db=mock_db,
                )
            )
        get_servo_details.assert_called_once_with(
            mock_db,
            self.test_plane_id,
            self.test_wing_name,
            self.test_cross_section_index,
        )
        self.assertEqual(result, expected)

        with patch("app.api.v2.endpoints.aeroplane.wings.wing_service.get_wing_design_model", return_value="asb"), \
             patch(
            "app.api.v2.endpoints.aeroplane.wings.wing_service.patch_control_surface_cad_details_servo_details",
            return_value=expected,
        ) as patch_servo_details:
            result = asyncio.run(
                patch_aeroplane_wing_cross_section_control_surface_cad_details_servo_details(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    cross_section_index=self.test_cross_section_index,
                    request=patch_request,
                    db=mock_db,
                )
            )
        patch_servo_details.assert_called_once_with(
            mock_db, self.test_plane_id, self.test_wing_name, self.test_cross_section_index, patch_request
        )
        self.assertEqual(result, expected)

        with patch("app.api.v2.endpoints.aeroplane.wings.wing_service.get_wing_design_model", return_value="asb"), \
             patch(
            "app.api.v2.endpoints.aeroplane.wings.wing_service.delete_control_surface_cad_details_servo_details",
            return_value=None,
        ) as delete_servo_details:
            result = asyncio.run(
                delete_aeroplane_wing_cross_section_control_surface_cad_details_servo_details(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    cross_section_index=self.test_cross_section_index,
                    db=mock_db,
                )
            )
        delete_servo_details.assert_called_once_with(
            mock_db,
            self.test_plane_id,
            self.test_wing_name,
            self.test_cross_section_index,
        )
        self.assertEqual(result.status, "ok")

if __name__ == "__main__":
    unittest.main()
