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
    get_aeroplane_wing_cross_section_control_surface,
    create_and_update_aeroplane_wing_cross_section_control_surface,
    delete_aeroplane_wing_cross_section_control_surface,
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
            schemas.WingXSecSchema.model_construct(airfoil="NACA0012", chord=1.0),
            schemas.WingXSecSchema.model_construct(airfoil="NACA2412", chord=0.8)
        ]

        with patch('app.schemas.aeroplaneschema.WingXSecSchema.model_validate',
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

    def test_delete_cross_sections_success(self):
        mock_db = MagicMock()
        # Simulate plane with a wing that has cross sections
        wing_model = MagicMock(name=self.test_wing_name)
        wing_model.name = self.test_wing_name
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

        mock_schema = schemas.WingXSecSchema.model_construct(airfoil="NACA0012", chord=1.0)

        with patch('app.schemas.aeroplaneschema.WingXSecSchema.model_validate',
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

    def test_create_cross_section_success(self):
        mock_db = MagicMock()
        # Simulate plane with a wing that has cross sections
        wing_model = MagicMock(name=self.test_wing_name)
        wing_model.name = self.test_wing_name
        wing_model.x_secs = []
        plane = MagicMock()
        plane.wings = [wing_model]
        mock_db.query.return_value.filter.return_value.first.return_value = plane

        request_schema = schemas.WingXSecSchema.model_construct(airfoil="NACA0012", chord=1.0)

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

    def test_update_cross_section_success(self):
        mock_db = MagicMock()
        # Simulate plane with a wing that has cross sections
        wing_model = MagicMock(name=self.test_wing_name)
        wing_model.name = self.test_wing_name
        old_xsec = MagicMock()
        old_xsec.control_surface = None  # No control surface initially
        wing_model.x_secs = [old_xsec]
        plane = MagicMock()
        plane.wings = [wing_model]
        mock_db.query.return_value.filter.return_value.first.return_value = plane

        request_schema = schemas.WingXSecSchema.model_construct(airfoil="NACA0019", chord=3.0)

        with patch('app.models.aeroplanemodel.WingXSecModel', autospec=True) as MockXSecModel:
            # Mock the updated cross section
            new_xsec = MagicMock()
            MockXSecModel.return_value = new_xsec

            result = asyncio.run(
                update_aeroplane_wing_cross_section(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    cross_section_index=0,
                    request=request_schema,
                    db=mock_db
                )
            )

            # Verify cross section was updated
            self.assertEqual(wing_model.x_secs[0].airfoil, "NACA0019")
            self.assertEqual(wing_model.x_secs[0].chord, 3.0)
            # Verify timestamp was updated
            self.assertIsNotNone(plane.updated_at)

    def test_delete_cross_section_success(self):
        mock_db = MagicMock()
        # Simulate plane with a wing that has cross sections
        wing_model = MagicMock(name=self.test_wing_name)
        wing_model.name = self.test_wing_name
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

    def test_get_control_surface_success(self):
        mock_db = MagicMock()
        # Simulate plane with a wing that has a cross section with a control surface
        control_surface = MagicMock()
        cross_section = MagicMock()
        cross_section.control_surface = control_surface
        wing_model = MagicMock(name=self.test_wing_name)
        wing_model.name = self.test_wing_name
        wing_model.x_secs = [cross_section]
        plane = MagicMock()
        plane.wings = [wing_model]
        mock_db.query.return_value.filter.return_value.first.return_value = plane

        mock_schema = schemas.ControlSurfaceSchema.model_construct(name="aileron", hinge_pos=0.75)

        with patch('app.schemas.aeroplaneschema.ControlSurfaceSchema.model_validate',
                  return_value=mock_schema) as validate:
            result = asyncio.run(
                get_aeroplane_wing_cross_section_control_surface(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    cross_section_index=0,
                    db=mock_db
                )
            )

            validate.assert_called_once_with(control_surface, from_attributes=True)
            self.assertEqual(result, mock_schema)

    def test_create_control_surface_success(self):
        mock_db = MagicMock()
        # Simulate plane with a wing that has a cross section without a control surface
        cross_section = MagicMock()
        cross_section.control_surface = None
        wing_model = MagicMock(name=self.test_wing_name)
        wing_model.name = self.test_wing_name
        wing_model.x_secs = [cross_section]
        plane = MagicMock()
        plane.wings = [wing_model]
        mock_db.query.return_value.filter.return_value.first.return_value = plane

        request_schema = schemas.ControlSurfaceSchema.model_construct(name="aileron", hinge_pos=0.75)

        with patch('app.models.aeroplanemodel.ControlSurfaceModel', autospec=True) as MockCSModel, \
             patch('app.schemas.aeroplaneschema.ControlSurfaceSchema.model_validate', return_value=request_schema) as mock_validate:
            # Mock the created control surface
            mock_cs = MagicMock()
            MockCSModel.return_value = mock_cs

            result = asyncio.run(
                create_and_update_aeroplane_wing_cross_section_control_surface(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    cross_section_index=0,
                    request=request_schema,
                    db=mock_db
                )
            )

        # Verify that the new control surface was added to the DB session and committed
        mock_db.add.assert_called_once()
        added_cs = mock_db.add.call_args[0][0]
        self.assertEqual(added_cs.name, 'aileron')
        self.assertEqual(added_cs.hinge_point, 0.8)
        # Verify timestamp was updated
        self.assertIsNotNone(plane.updated_at)

    def test_delete_control_surface_success(self):
        mock_db = MagicMock()
        # Simulate plane with a wing that has a cross section with a control surface
        control_surface = MagicMock()
        cross_section = MagicMock()
        cross_section.control_surface = control_surface
        wing_model = MagicMock(name=self.test_wing_name)
        wing_model.name = self.test_wing_name
        wing_model.x_secs = [cross_section]
        plane = MagicMock()
        plane.wings = [wing_model]
        mock_db.query.return_value.filter.return_value.first.return_value = plane

        result = asyncio.run(
            delete_aeroplane_wing_cross_section_control_surface(
                aeroplane_id=self.test_plane_id,
                wing_name=self.test_wing_name,
                cross_section_index=0,
                db=mock_db
            )
        )

        # Verify control surface was deleted
        self.assertIsNone(cross_section.control_surface)
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
        self.assertTrue("Database error" in ctx.exception.detail)

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
        self.assertTrue("Unexpected error" in ctx.exception.detail)

    def test_delete_cross_sections_db_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = SQLAlchemyError("Database error")

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                delete_aeroplane_wing_cross_sections(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    db=mock_db
                )
            )
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertTrue("Database error" in ctx.exception.detail)

    def test_delete_cross_sections_unexpected_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("Unexpected error")

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                delete_aeroplane_wing_cross_sections(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    db=mock_db
                )
            )
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertTrue("Unexpected error" in ctx.exception.detail)

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
        self.assertTrue("Database error" in ctx.exception.detail)

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
        self.assertTrue("Unexpected error" in ctx.exception.detail)

    def test_create_cross_section_db_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = SQLAlchemyError("Database error")
        request_schema = schemas.WingXSecSchema.model_construct(airfoil="NACA0012", chord=1.0)

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
        self.assertTrue("Database error" in ctx.exception.detail)

    def test_create_cross_section_unexpected_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("Unexpected error")
        request_schema = schemas.WingXSecSchema.model_construct(airfoil="NACA0012", chord=1.0)

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
        self.assertTrue("Unexpected error" in ctx.exception.detail)

    def test_update_cross_section_db_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = SQLAlchemyError("Database error")
        request_schema = schemas.WingXSecSchema.model_construct(airfoil="NACA0012", chord=1.0)

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
        self.assertTrue("Database error" in ctx.exception.detail)

    def test_update_cross_section_unexpected_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("Unexpected error")
        request_schema = schemas.WingXSecSchema.model_construct(airfoil="NACA0012", chord=1.0)

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
        self.assertTrue("Unexpected error" in ctx.exception.detail)

    def test_delete_cross_section_db_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = SQLAlchemyError("Database error")

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
        self.assertTrue("Database error" in ctx.exception.detail)

    def test_delete_cross_section_unexpected_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("Unexpected error")

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
        self.assertTrue("Unexpected error" in ctx.exception.detail)

    def test_get_control_surface_db_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = SQLAlchemyError("Database error")

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                get_aeroplane_wing_cross_section_control_surface(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    cross_section_index=0,
                    db=mock_db
                )
            )
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertTrue("Database error" in ctx.exception.detail)

    def test_get_control_surface_unexpected_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("Unexpected error")

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                get_aeroplane_wing_cross_section_control_surface(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    cross_section_index=0,
                    db=mock_db
                )
            )
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertTrue("Unexpected error" in ctx.exception.detail)

    def test_create_control_surface_db_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = SQLAlchemyError("Database error")
        request_schema = schemas.ControlSurfaceSchema.model_construct(name="aileron", hinge_pos=0.75)

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                create_and_update_aeroplane_wing_cross_section_control_surface(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    cross_section_index=0,
                    request=request_schema,
                    db=mock_db
                )
            )
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertTrue("Database error" in ctx.exception.detail)

    def test_create_control_surface_unexpected_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("Unexpected error")
        request_schema = schemas.ControlSurfaceSchema.model_construct(name="aileron", hinge_pos=0.75)

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                create_and_update_aeroplane_wing_cross_section_control_surface(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    cross_section_index=0,
                    request=request_schema,
                    db=mock_db
                )
            )
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertTrue("Unexpected error" in ctx.exception.detail)

    def test_delete_control_surface_db_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = SQLAlchemyError("Database error")

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                delete_aeroplane_wing_cross_section_control_surface(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    cross_section_index=0,
                    db=mock_db
                )
            )
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertTrue("Database error" in ctx.exception.detail)

    def test_delete_control_surface_unexpected_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("Unexpected error")

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                delete_aeroplane_wing_cross_section_control_surface(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    cross_section_index=0,
                    db=mock_db
                )
            )
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertTrue("Unexpected error" in ctx.exception.detail)

if __name__ == "__main__":
    unittest.main()
