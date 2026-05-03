import unittest
import asyncio
import uuid
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.api.v2.endpoints.aeroplane.fuselages import (
    get_aeroplane_fuselage_cross_sections,
    delete_aeroplane_fuselage_cross_sections,
    get_aeroplane_fuselage_cross_section,
    create_aeroplane_fuselage_cross_section,
    update_aeroplane_fuselage_cross_section,
    delete_aeroplane_fuselage_cross_section,
)

from app import schemas
from app.core.exceptions import InternalError, NotFoundError


class TestAeroplaneFuselageCrossSectionEndpoints(unittest.TestCase):
    def setUp(self):
        self.test_plane_id = uuid.uuid4()
        self.test_fuselage_name = "test fuselage"
        self.test_cross_section_index = 0

    def test_get_cross_sections_success(self):
        mock_db = MagicMock()
        schema1 = schemas.FuselageXSecSuperEllipseSchema.model_construct()
        schema2 = schemas.FuselageXSecSuperEllipseSchema.model_construct()

        with patch(
            'app.services.fuselage_service.get_fuselage_cross_sections',
            return_value=[schema1, schema2],
        ) as mock_get:
            result = asyncio.run(
                get_aeroplane_fuselage_cross_sections(
                    aeroplane_id=self.test_plane_id,
                    fuselage_name=self.test_fuselage_name,
                    db=mock_db,
                )
            )

        mock_get.assert_called_once_with(mock_db, self.test_plane_id, self.test_fuselage_name)
        self.assertEqual(len(result), 2)
        self.assertEqual(result, [schema1, schema2])

    def test_get_cross_sections_aeroplane_not_found(self):
        mock_db = MagicMock()

        with patch(
            'app.services.fuselage_service.get_fuselage_cross_sections',
            side_effect=NotFoundError(message="Aeroplane not found"),
        ):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(
                    get_aeroplane_fuselage_cross_sections(
                        aeroplane_id=self.test_plane_id,
                        fuselage_name=self.test_fuselage_name,
                        db=mock_db,
                    )
                )
            self.assertEqual(ctx.exception.status_code, 404)
            self.assertIn("not found", ctx.exception.detail.lower())

    def test_get_cross_sections_fuselage_not_found(self):
        mock_db = MagicMock()

        with patch(
            'app.services.fuselage_service.get_fuselage_cross_sections',
            side_effect=NotFoundError(message="Fuselage not found"),
        ):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(
                    get_aeroplane_fuselage_cross_sections(
                        aeroplane_id=self.test_plane_id,
                        fuselage_name=self.test_fuselage_name,
                        db=mock_db,
                    )
                )
            self.assertEqual(ctx.exception.status_code, 404)
            self.assertIn("not found", ctx.exception.detail.lower())

    def test_delete_cross_sections_success(self):
        mock_db = MagicMock()

        with patch('app.services.fuselage_service.delete_all_cross_sections') as mock_delete:
            result = asyncio.run(
                delete_aeroplane_fuselage_cross_sections(
                    aeroplane_id=self.test_plane_id,
                    fuselage_name=self.test_fuselage_name,
                    db=mock_db,
                )
            )

        mock_delete.assert_called_once_with(mock_db, self.test_plane_id, self.test_fuselage_name)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.operation, "delete_all_fuselage_cross_sections")

    def test_create_cross_section_success(self):
        mock_db = MagicMock()
        request_schema = schemas.FuselageXSecSuperEllipseSchema.model_construct()

        with patch('app.services.fuselage_service.create_cross_section') as mock_create:
            result = asyncio.run(
                create_aeroplane_fuselage_cross_section(
                    aeroplane_id=self.test_plane_id,
                    fuselage_name=self.test_fuselage_name,
                    cross_section_index=1,
                    request=request_schema,
                    db=mock_db,
                )
            )

        mock_create.assert_called_once_with(
            mock_db, self.test_plane_id, self.test_fuselage_name, 1, request_schema
        )
        self.assertEqual(result.status, "created")
        self.assertEqual(result.operation, "create_fuselage_cross_section")

    def test_get_cross_sections_db_error(self):
        mock_db = MagicMock()

        with patch(
            'app.services.fuselage_service.get_fuselage_cross_sections',
            side_effect=InternalError(message="Database error: Database error"),
        ):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(
                    get_aeroplane_fuselage_cross_sections(
                        aeroplane_id=self.test_plane_id,
                        fuselage_name=self.test_fuselage_name,
                        db=mock_db,
                    )
                )
            self.assertEqual(ctx.exception.status_code, 500)
            self.assertIn("Database error", ctx.exception.detail)

    def test_get_cross_sections_unexpected_error(self):
        mock_db = MagicMock()

        with patch(
            'app.services.fuselage_service.get_fuselage_cross_sections',
            side_effect=InternalError(message="Unexpected error: Unexpected error"),
        ):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(
                    get_aeroplane_fuselage_cross_sections(
                        aeroplane_id=self.test_plane_id,
                        fuselage_name=self.test_fuselage_name,
                        db=mock_db,
                    )
                )
            self.assertEqual(ctx.exception.status_code, 500)
            self.assertIn("Unexpected error", ctx.exception.detail)

    def test_delete_cross_sections_db_error(self):
        mock_db = MagicMock()

        with patch(
            'app.services.fuselage_service.delete_all_cross_sections',
            side_effect=InternalError(message="Database error: Database error"),
        ):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(
                    delete_aeroplane_fuselage_cross_sections(
                        aeroplane_id=self.test_plane_id,
                        fuselage_name=self.test_fuselage_name,
                        db=mock_db,
                    )
                )
            self.assertEqual(ctx.exception.status_code, 500)
            self.assertIn("Database error", ctx.exception.detail)

    def test_delete_cross_sections_unexpected_error(self):
        mock_db = MagicMock()

        with patch(
            'app.services.fuselage_service.delete_all_cross_sections',
            side_effect=InternalError(message="Unexpected error: Unexpected error"),
        ):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(
                    delete_aeroplane_fuselage_cross_sections(
                        aeroplane_id=self.test_plane_id,
                        fuselage_name=self.test_fuselage_name,
                        db=mock_db,
                    )
                )
            self.assertEqual(ctx.exception.status_code, 500)
            self.assertIn("Unexpected error", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()
