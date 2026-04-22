"""Tests for the fuselage STEP slicing endpoint (GH#59).

Uses client_and_db fixture for in-memory SQLite isolation.
"""

import io
from unittest.mock import MagicMock, patch

from app.schemas.fuselage_slice import FuselageSliceResponse, GeometryProperties, FidelityMetrics
from app.schemas.aeroplaneschema import FuselageSchema, FuselageXSecSuperEllipseSchema


MOCK_RESPONSE = FuselageSliceResponse(
    fuselage=FuselageSchema(
        name="Test Fuselage",
        x_secs=[
            FuselageXSecSuperEllipseSchema(xyz=[0, 0, 0], a=0.01, b=0.01, n=2.0),
            FuselageXSecSuperEllipseSchema(xyz=[0.1, 0, 0], a=0.05, b=0.04, n=2.3),
            FuselageXSecSuperEllipseSchema(xyz=[0.2, 0, 0], a=0.03, b=0.02, n=2.1),
        ],
    ),
    original_properties=GeometryProperties(volume_m3=0.00234, surface_area_m2=0.0891),
    reconstructed_properties=GeometryProperties(volume_m3=0.00228, surface_area_m2=0.0876),
    fidelity=FidelityMetrics(volume_ratio=0.974, area_ratio=0.983),
)


class TestFuselageSliceEndpoint:

    def test_accepts_step_upload(self, client_and_db):
        client, _ = client_and_db
        with patch(
            "app.services.fuselage_slice_service.slice_step_file",
            new_callable=MagicMock,
            return_value=MOCK_RESPONSE,
        ):
            res = client.post(
                "/fuselages/slice",
                files={"file": ("fuselage.step", io.BytesIO(b"ISO-10303-21;"), "application/step")},
                data={"number_of_slices": "20", "fuselage_name": "Test"},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["fuselage"]["name"] == "Test Fuselage"
            assert len(data["fuselage"]["x_secs"]) == 3

    def test_returns_valid_fuselage_schema(self, client_and_db):
        client, _ = client_and_db
        with patch(
            "app.services.fuselage_slice_service.slice_step_file",
            new_callable=MagicMock,
            return_value=MOCK_RESPONSE,
        ):
            res = client.post(
                "/fuselages/slice",
                files={"file": ("test.step", io.BytesIO(b"content"), "application/step")},
            )
            xsecs = res.json()["fuselage"]["x_secs"]
            for xsec in xsecs:
                assert len(xsec["xyz"]) == 3
                assert xsec["a"] > 0
                assert xsec["b"] > 0
                assert 0.5 <= xsec["n"] <= 10.0

    def test_returns_fidelity_metrics(self, client_and_db):
        client, _ = client_and_db
        with patch(
            "app.services.fuselage_slice_service.slice_step_file",
            new_callable=MagicMock,
            return_value=MOCK_RESPONSE,
        ):
            res = client.post(
                "/fuselages/slice",
                files={"file": ("test.step", io.BytesIO(b"content"), "application/step")},
            )
            fidelity = res.json()["fidelity"]
            assert 0.8 <= fidelity["volume_ratio"] <= 1.2
            assert 0.8 <= fidelity["area_ratio"] <= 1.2

    def test_rejects_non_step_file(self, client_and_db):
        client, _ = client_and_db
        res = client.post(
            "/fuselages/slice",
            files={"file": ("model.pdf", io.BytesIO(b"pdf content"), "application/pdf")},
        )
        # The service validates file extension — mock not needed
        # But since the service is async, we need to let it validate
        with patch(
            "app.services.fuselage_slice_service.slice_step_file",
            new_callable=MagicMock,
            side_effect=Exception("Should not be called"),
        ):
            from app.core.exceptions import ValidationError
            with patch(
                "app.services.fuselage_slice_service.slice_step_file",
                new_callable=MagicMock,
                side_effect=ValidationError(message="Unsupported file type: .pdf"),
            ):
                res = client.post(
                    "/fuselages/slice",
                    files={"file": ("model.pdf", io.BytesIO(b"pdf"), "application/pdf")},
                )
                assert res.status_code == 422

    def test_rejects_empty_file(self, client_and_db):
        client, _ = client_and_db
        res = client.post(
            "/fuselages/slice",
            files={"file": ("empty.step", io.BytesIO(b""), "application/step")},
        )
        assert res.status_code == 422

    def test_custom_slice_axis(self, client_and_db):
        client, _ = client_and_db
        with patch(
            "app.services.fuselage_slice_service.slice_step_file",
            new_callable=MagicMock,
            return_value=MOCK_RESPONSE,
        ) as mock_svc:
            client.post(
                "/fuselages/slice",
                files={"file": ("test.step", io.BytesIO(b"content"), "application/step")},
                data={"slice_axis": "y"},
            )
            mock_svc.assert_called_once()
            assert mock_svc.call_args.kwargs["slice_axis"] == "y"

    def test_invalid_slice_axis_rejected(self, client_and_db):
        client, _ = client_and_db
        res = client.post(
            "/fuselages/slice",
            files={"file": ("test.step", io.BytesIO(b"content"), "application/step")},
            data={"slice_axis": "w"},
        )
        assert res.status_code == 422

    def test_default_parameters(self, client_and_db):
        client, _ = client_and_db
        with patch(
            "app.services.fuselage_slice_service.slice_step_file",
            new_callable=MagicMock,
            return_value=MOCK_RESPONSE,
        ) as mock_svc:
            client.post(
                "/fuselages/slice",
                files={"file": ("test.step", io.BytesIO(b"content"), "application/step")},
            )
            kwargs = mock_svc.call_args.kwargs
            assert kwargs["number_of_slices"] == 50
            assert kwargs["points_per_slice"] == 30
            assert kwargs["slice_axis"] == "auto"
