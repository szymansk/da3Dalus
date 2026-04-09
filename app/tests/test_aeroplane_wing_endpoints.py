import unittest
import asyncio
import uuid
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.api.v2.endpoints.aeroplane.wings import (
    create_aeroplane_wing,
    create_aeroplane_wing_from_wingconfig,
    update_aeroplane_wing,
    get_aeroplane_wing,
    delete_aeroplane_wing,
)
from app.models.aeroplanemodel import WingModel
from app import schemas
from app.schemas.wing import Wing as WingConfigurationSchema

class TestAeroplaneWingEndpoints(unittest.TestCase):
    def setUp(self):
        self.test_plane_id = uuid.uuid4()
        self.test_wing_name = "this is a test wing"

    def test_create_wing_success(self):
        mock_db = MagicMock()
        plane = MagicMock()
        plane.wings = []
        mock_db.query.return_value.filter.return_value.first.return_value = plane

        request_schema = schemas.AsbWingGeometryWriteSchema.model_construct(name=str(self.test_wing_name), x_secs=[])

        with patch('app.models.aeroplanemodel.WingModel.from_dict', autospec=True) as from_dict:
            # WingModel.from_dict returns an instance
            wing_instance = MagicMock(name=str(self.test_wing_name))
            from_dict.return_value = wing_instance
            result = asyncio.run(
                create_aeroplane_wing(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    request=request_schema,
                    db=mock_db
                )
            )
            # Ensure from_dict was called with the correct parameters
            from_dict.assert_called_once_with(name=self.test_wing_name, data=request_schema.model_dump())

    def test_create_wing_from_wingconfig_success(self):
        mock_db = MagicMock()
        request_schema = WingConfigurationSchema.model_construct(segments=[], nose_pnt=[0, 0, 0])

        with patch("app.services.wing_service.create_wing_from_wing_configuration", return_value=None) as create_from_wc:
            result = asyncio.run(
                create_aeroplane_wing_from_wingconfig(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    request=request_schema,
                    db=mock_db,
                )
            )

        create_from_wc.assert_called_once_with(mock_db, self.test_plane_id, self.test_wing_name, request_schema)
        self.assertEqual(result.status, "created")
        self.assertEqual(result.operation, "create_aeroplane_wing_from_wingconfig")

    def test_update_wing_not_found_plane(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                update_aeroplane_wing(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    request=schemas.AsbWingGeometryWriteSchema.model_construct(name=str(self.test_wing_name), x_secs=[]),
                    db=mock_db
                )
            )
        self.assertEqual(ctx.exception.status_code, 404)

    def test_get_wing_success(self):
        mock_db = MagicMock()
        # Simulate plane with a wing
        wing_model = MagicMock()
        wing_model.name = self.test_wing_name
        wing_model.x_secs = [MagicMock(), MagicMock()]
        plane = MagicMock()
        plane.wings = [wing_model]
        mock_db.query.return_value.filter.return_value.first.return_value = plane

        schema = schemas.AsbWingReadSchema.model_construct(name=str(self.test_wing_name), x_secs=[{'a': 1}, {'b': 2}])
        with patch('app.schemas.AsbWingReadSchema.model_validate', return_value=schema) as validate:
            result = asyncio.run(
                get_aeroplane_wing(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    db=mock_db
                )
            )

        validate.assert_called_once_with(wing_model, from_attributes=True)
        self.assertEqual(result, schema)

    def test_delete_wing_db_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = SQLAlchemyError("fail")

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                delete_aeroplane_wing(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    db=mock_db
                )
            )
        self.assertEqual(ctx.exception.status_code, 500)

if __name__ == "__main__":
    unittest.main()
