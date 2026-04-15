"""Tests for the stability summary endpoint (GH#39)."""

from unittest.mock import AsyncMock, patch, MagicMock

from app.schemas.stability import StabilitySummaryResponse


class TestStabilitySummarySchema:
    """Test the response schema directly."""

    def test_stable_aircraft(self):
        resp = StabilitySummaryResponse(
            static_margin=0.15,
            neutral_point_x=0.087,
            cg_x=0.05,
            trim_alpha_deg=2.3,
            trim_elevator_deg=-1.5,
            Cma=-0.8,
            Cnb=0.05,
            Clb=-0.03,
            is_statically_stable=True,
            is_directionally_stable=True,
            is_laterally_stable=True,
            analysis_method="aerobuildup",
        )
        assert resp.is_statically_stable is True
        assert resp.is_directionally_stable is True
        assert resp.is_laterally_stable is True
        assert resp.static_margin == 0.15

    def test_unstable_aircraft(self):
        resp = StabilitySummaryResponse(
            Cma=0.3,  # positive = unstable
            Cnb=-0.01,  # negative = directionally unstable
            Clb=0.02,  # positive = laterally unstable
            is_statically_stable=False,
            is_directionally_stable=False,
            is_laterally_stable=False,
        )
        assert resp.is_statically_stable is False
        assert resp.is_directionally_stable is False
        assert resp.is_laterally_stable is False

    def test_partial_data(self):
        """When analysis doesn't provide all fields, nulls are acceptable."""
        resp = StabilitySummaryResponse(
            Cma=-0.5,
            is_statically_stable=True,
        )
        assert resp.neutral_point_x is None
        assert resp.static_margin is None
        assert resp.trim_elevator_deg is None

    def test_json_serialization(self):
        resp = StabilitySummaryResponse(
            static_margin=0.12,
            neutral_point_x=0.09,
            Cma=-0.6,
            Cnb=0.04,
            Clb=-0.02,
            is_statically_stable=True,
            is_directionally_stable=True,
            is_laterally_stable=True,
            analysis_method="vortex_lattice",
        )
        d = resp.model_dump()
        assert "static_margin" in d
        assert "is_statically_stable" in d
        assert d["analysis_method"] == "vortex_lattice"


class TestStabilityEndpoint:
    """Test the endpoint via TestClient with mocked analysis."""

    def test_stability_endpoint_returns_200(self, client_and_db):
        """Test that the endpoint wiring works (mocking the actual analysis)."""
        client, _ = client_and_db

        # The endpoint requires a valid aeroplane UUID — we mock the service
        mock_response = StabilitySummaryResponse(
            static_margin=0.15,
            neutral_point_x=0.087,
            cg_x=0.05,
            trim_alpha_deg=2.3,
            Cma=-0.8,
            Cnb=0.05,
            Clb=-0.03,
            is_statically_stable=True,
            is_directionally_stable=True,
            is_laterally_stable=True,
            analysis_method="aerobuildup",
        )

        with patch(
            "app.services.stability_service.get_stability_summary",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            res = client.post(
                "/aeroplanes/00000000-0000-0000-0000-000000000001/stability_summary/aerobuildup",
                json={"velocity": 14.0, "alpha": 2.0, "beta": 0.0, "altitude": 0},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["static_margin"] == 0.15
            assert data["is_statically_stable"] is True
            assert data["Cma"] == -0.8
