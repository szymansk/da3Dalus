import unittest
import asyncio
import uuid
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.api.v2.endpoints.aeroplane.fuselages import (
    get_aeroplane_fuselage_cross_sections,
    delete_aeroplane_fuselage_cross_sections,
    get_aeroplane_fuselage_cross_section,
    create_aeroplane_fuselage_cross_section,
    update_aeroplane_fuselage_cross_section,
    delete_aeroplane_fuselage_cross_section,
)

from app import schemas

class TestAeroplaneFuselageCrossSectionEndpoints(unittest.TestCase):
    def setUp(self):
        self.test_plane_id = uuid.uuid4()
        self.test_fuselage_name = "test fuselage"
        self.test_cross_section_index = 0

    def test_get_cross_sections_success(self):
        mock_db = MagicMock()
        # Mock aeroplane with fuselage that has cross sections
        mock_xsec1 = MagicMock()
        mock_xsec2 = MagicMock()
        mock_fuselage = MagicMock()
        mock_fuselage.name = self.test_fuselage_name
        mock_fuselage.x_secs = [mock_xsec1, mock_xsec2]
        mock_plane = MagicMock()
        mock_plane.fuselages = [mock_fuselage]
        mock_db.query.return_value.filter.return_value.first.return_value = mock_plane

        # Mock schema validation
        schema1 = schemas.FuselageXSecSuperEllipseSchema.model_construct()
        schema2 = schemas.FuselageXSecSuperEllipseSchema.model_construct()

        with patch('app.schemas.FuselageXSecSuperEllipseSchema.model_validate', side_effect=[schema1, schema2]) as validate:
            result = asyncio.run(
                get_aeroplane_fuselage_cross_sections(
                    aeroplane_id=self.test_plane_id,
                    fuselage_name=self.test_fuselage_name,
                    db=mock_db
                )
            )

        # Assertions
        mock_db.query.assert_called_once()
        self.assertEqual(validate.call_count, 2)
        self.assertEqual(len(result), 2)
        self.assertEqual(result, [schema1, schema2])

    def test_get_cross_sections_aeroplane_not_found(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                get_aeroplane_fuselage_cross_sections(
                    aeroplane_id=self.test_plane_id,
                    fuselage_name=self.test_fuselage_name,
                    db=mock_db
                )
            )

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("not found", ctx.exception.detail.lower())

    def test_get_cross_sections_fuselage_not_found(self):
        mock_db = MagicMock()
        # Plane exists but doesn't have the requested fuselage
        mock_plane = MagicMock()
        mock_plane.fuselages = []
        mock_db.query.return_value.filter.return_value.first.return_value = mock_plane

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                get_aeroplane_fuselage_cross_sections(
                    aeroplane_id=self.test_plane_id,
                    fuselage_name=self.test_fuselage_name,
                    db=mock_db
                )
            )

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("not found", ctx.exception.detail.lower())

    def test_delete_cross_sections_success(self):
        mock_db = MagicMock()
        # Mock fuselage with cross sections
        mock_fuselage = MagicMock()
        mock_fuselage.name = self.test_fuselage_name
        # Create a mock for x_secs with a mock clear method
        mock_x_secs = MagicMock()
        mock_x_secs.clear = MagicMock()
        mock_fuselage.x_secs = mock_x_secs
        mock_plane = MagicMock()
        mock_plane.fuselages = [mock_fuselage]
        mock_db.query.return_value.filter.return_value.first.return_value = mock_plane

        # Context manager for transaction
        begin_cm = mock_db.begin.return_value
        begin_cm.__enter__.return_value = None

        result = asyncio.run(
            delete_aeroplane_fuselage_cross_sections(
                aeroplane_id=self.test_plane_id,
                fuselage_name=self.test_fuselage_name,
                db=mock_db
            )
        )

        # Assertions
        mock_db.query.assert_called_once()
        mock_x_secs.clear.assert_called_once()
        begin_cm.__enter__.assert_called_once()
        self.assertEqual(result.status_code, 204)

    def test_create_cross_section_success(self):
        mock_db = MagicMock()
        # Mock fuselage with existing cross sections
        mock_xsec1 = MagicMock()
        mock_xsec1.sort_index = 0
        mock_fuselage = MagicMock()
        mock_fuselage.name = self.test_fuselage_name

        # Create a mock for x_secs with a mock append method
        mock_x_secs = MagicMock()
        mock_x_secs.append = MagicMock()
        # Make it behave like a list for indexing
        mock_x_secs.__getitem__.return_value = mock_xsec1
        mock_x_secs.__len__.return_value = 1
        mock_x_secs.__iter__.return_value = iter([mock_xsec1])
        mock_fuselage.x_secs = mock_x_secs

        mock_plane = MagicMock()
        mock_plane.fuselages = [mock_fuselage]
        mock_db.query.return_value.filter.return_value.first.return_value = mock_plane

        # Context manager for transaction
        begin_cm = mock_db.begin.return_value
        begin_cm.__enter__.return_value = None

        # Create request schema
        request_schema = schemas.FuselageXSecSuperEllipseSchema.model_construct()

        # Mock the model class without autospec to allow direct instantiation
        with patch('app.api.v2.endpoints.aeroplane.fuselages.FuselageXSecSuperEllipseModel') as model_class:
            # Mock the created model instance
            mock_model = MagicMock()
            model_class.return_value = mock_model

            result = asyncio.run(
                create_aeroplane_fuselage_cross_section(
                    aeroplane_id=self.test_plane_id,
                    fuselage_name=self.test_fuselage_name,
                    cross_section_index=1,  # Add at the end
                    request=request_schema,
                    db=mock_db
                )
            )

        # Assertions
        mock_db.query.assert_called_once()
        # Check that the model class was called with the expected arguments
        model_class.assert_called_once()
        mock_x_secs.append.assert_called_once_with(mock_model)
        mock_db.add.assert_called_once_with(mock_model)
        begin_cm.__enter__.assert_called_once()

    def test_get_cross_sections_db_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = SQLAlchemyError("Database error")

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                get_aeroplane_fuselage_cross_sections(
                    aeroplane_id=self.test_plane_id,
                    fuselage_name=self.test_fuselage_name,
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
                get_aeroplane_fuselage_cross_sections(
                    aeroplane_id=self.test_plane_id,
                    fuselage_name=self.test_fuselage_name,
                    db=mock_db
                )
            )

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Unexpected error", ctx.exception.detail)

    def test_delete_cross_sections_db_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = SQLAlchemyError("Database error")

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                delete_aeroplane_fuselage_cross_sections(
                    aeroplane_id=self.test_plane_id,
                    fuselage_name=self.test_fuselage_name,
                    db=mock_db
                )
            )

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Database error", ctx.exception.detail)

    def test_delete_cross_sections_unexpected_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("Unexpected error")

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                delete_aeroplane_fuselage_cross_sections(
                    aeroplane_id=self.test_plane_id,
                    fuselage_name=self.test_fuselage_name,
                    db=mock_db
                )
            )

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Unexpected error", ctx.exception.detail)

if __name__ == "__main__":
    unittest.main()
