import unittest
import asyncio
import uuid
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.api.v2.endpoints.aeroplane.fuselages import (
    create_aeroplane_fuselage,
    update_aeroplane_fuselage,
    get_aeroplane_fuselage,
    delete_aeroplane_fuselage,
)
from app.core.exceptions import InternalError, NotFoundError
from app import schemas


class TestAeroplaneFuselageEndpoints(unittest.TestCase):
    def setUp(self):
        self.test_plane_id = uuid.uuid4()
        self.test_fuselage_name = "this is a test fuselage"

    def test_create_fuselage_success(self):
        mock_db = MagicMock()
        request_schema = schemas.FuselageSchema.model_construct(name=str(self.test_fuselage_name))

        with patch('app.services.fuselage_service.create_fuselage') as mock_create:
            result = asyncio.run(
                create_aeroplane_fuselage(
                    aeroplane_id=self.test_plane_id,
                    fuselage_name=self.test_fuselage_name,
                    request=request_schema,
                    db=mock_db
                )
            )
            mock_create.assert_called_once_with(
                mock_db, self.test_plane_id, self.test_fuselage_name, request_schema
            )
        self.assertEqual(result.status, "created")
        self.assertEqual(result.operation, "create_aeroplane_fuselage")

    def test_update_fuselage_not_found_plane(self):
        mock_db = MagicMock()

        with patch(
            'app.services.fuselage_service.update_fuselage',
            side_effect=NotFoundError(message="Aeroplane not found"),
        ):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(
                    update_aeroplane_fuselage(
                        aeroplane_id=self.test_plane_id,
                        fuselage_name=self.test_fuselage_name,
                        request=schemas.FuselageSchema.model_construct(
                            name=str(self.test_fuselage_name)
                        ),
                        db=mock_db,
                    )
                )
            self.assertEqual(ctx.exception.status_code, 404)

    def test_get_fuselage_success(self):
        mock_db = MagicMock()
        schema = schemas.FuselageSchema.model_construct(
            name=str(self.test_fuselage_name), x_secs=[{"a": 1}, {"b": 2}]
        )

        with patch(
            'app.services.fuselage_service.get_fuselage', return_value=schema
        ) as mock_get:
            result = asyncio.run(
                get_aeroplane_fuselage(
                    aeroplane_id=self.test_plane_id,
                    fuselage_name=self.test_fuselage_name,
                    db=mock_db,
                )
            )

        mock_get.assert_called_once_with(mock_db, self.test_plane_id, self.test_fuselage_name)
        self.assertEqual(result, schema)

    def test_delete_fuselage_db_error(self):
        mock_db = MagicMock()

        with patch(
            'app.services.fuselage_service.delete_fuselage',
            side_effect=InternalError(message="Database error: fail"),
        ):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(
                    delete_aeroplane_fuselage(
                        aeroplane_id=self.test_plane_id,
                        fuselage_name=self.test_fuselage_name,
                        db=mock_db,
                    )
                )
            self.assertEqual(ctx.exception.status_code, 500)

    def test_delete_fuselage_success(self):
        mock_db = MagicMock()

        with patch('app.services.fuselage_service.delete_fuselage') as mock_delete:
            result = asyncio.run(
                delete_aeroplane_fuselage(
                    aeroplane_id=self.test_plane_id,
                    fuselage_name=self.test_fuselage_name,
                    db=mock_db,
                )
            )

        mock_delete.assert_called_once_with(mock_db, self.test_plane_id, self.test_fuselage_name)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.operation, "delete_aeroplane_fuselage")


if __name__ == "__main__":
    unittest.main()
