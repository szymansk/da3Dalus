"""Tests for NeuralFoil CDCL service."""

from __future__ import annotations

import aerosandbox as asb


class TestCdclConfig:
    def test_defaults(self):
        from app.schemas.aeroanalysisschema import CdclConfig

        config = CdclConfig()
        assert config.alpha_start_deg == -10.0
        assert config.alpha_end_deg == 16.0
        assert config.model_size == "large"
        assert config.n_crit == 9.0

    def test_custom_values(self):
        from app.schemas.aeroanalysisschema import CdclConfig

        config = CdclConfig(alpha_start_deg=-5.0, n_crit=11.0)
        assert config.alpha_start_deg == -5.0
        assert config.n_crit == 11.0


class TestSpacingConfig:
    def test_defaults(self):
        from app.schemas.aeroanalysisschema import SpacingConfig

        config = SpacingConfig()
        assert config.n_chord == 12
        assert config.n_span == 20
        assert config.auto_optimise is True

    def test_auto_optimise_false(self):
        from app.schemas.aeroanalysisschema import SpacingConfig

        assert SpacingConfig(auto_optimise=False).auto_optimise is False


class TestNeuralFoilCdclService:
    def test_compute_cdcl_returns_avl_cdcl(self):
        from app.avl.geometry import AvlCdcl
        from app.schemas.aeroanalysisschema import CdclConfig
        from app.services.neuralfoil_cdcl_service import NeuralFoilCdclService

        service = NeuralFoilCdclService()
        result = service.compute_cdcl(
            asb.Airfoil("naca2412"), re=500_000.0, mach=0.1, config=CdclConfig()
        )
        assert isinstance(result, AvlCdcl)
        assert result.cd_0 > 0
        assert result.cl_min < result.cl_0 < result.cl_max
        assert result.cd_0 <= result.cd_min
        assert result.cd_0 <= result.cd_max

    def test_different_re_gives_different_results(self):
        from app.schemas.aeroanalysisschema import CdclConfig
        from app.services.neuralfoil_cdcl_service import NeuralFoilCdclService

        service = NeuralFoilCdclService()
        af = asb.Airfoil("naca2412")
        config = CdclConfig()
        low = service.compute_cdcl(af, re=100_000.0, mach=0.1, config=config)
        high = service.compute_cdcl(af, re=1_000_000.0, mach=0.1, config=config)
        assert high.cd_0 < low.cd_0

    def test_cache_reuses_results(self):
        from app.schemas.aeroanalysisschema import CdclConfig
        from app.services.neuralfoil_cdcl_service import NeuralFoilCdclService

        service = NeuralFoilCdclService()
        af = asb.Airfoil("naca0012")
        config = CdclConfig()
        r1 = service.compute_cdcl(af, re=500_000.0, mach=0.1, config=config)
        r2 = service.compute_cdcl(af, re=500_000.0, mach=0.1, config=config)
        assert r1.cd_0 == r2.cd_0
        assert r1.cl_max == r2.cl_max

    def test_compute_reynolds_number(self):
        from app.services.neuralfoil_cdcl_service import compute_reynolds_number

        re = compute_reynolds_number(velocity=30.0, chord=0.2, altitude=0.0)
        assert 350_000 < re < 500_000

    def test_compute_reynolds_number_zero_velocity(self):
        from app.services.neuralfoil_cdcl_service import compute_reynolds_number

        assert compute_reynolds_number(velocity=0.0, chord=0.2, altitude=0.0) == 0.0

    def test_compute_reynolds_number_zero_chord(self):
        from app.services.neuralfoil_cdcl_service import compute_reynolds_number

        assert compute_reynolds_number(velocity=30.0, chord=0.0, altitude=0.0) == 0.0

    def test_xtr_fields_wired_through(self):
        from app.avl.geometry import AvlCdcl
        from app.schemas.aeroanalysisschema import CdclConfig
        from app.services.neuralfoil_cdcl_service import NeuralFoilCdclService

        service = NeuralFoilCdclService()
        config = CdclConfig(xtr_upper=0.3, xtr_lower=0.3)
        result = service.compute_cdcl(
            asb.Airfoil("naca2412"), re=500_000.0, mach=0.1, config=config
        )
        assert isinstance(result, AvlCdcl)
        assert result.cd_0 > 0


    def test_compute_cdcl_with_file_based_airfoil(self):
        """Airfoils loaded from .dat files (e.g. naca23013.5) must not crash.

        Regression test for gh-409: _get_polar_data recreated the airfoil
        from just the name, losing the coordinate file reference.
        """
        from app.avl.geometry import AvlCdcl
        from app.converters.model_schema_converters import _build_asb_airfoil
        from app.schemas.aeroanalysisschema import CdclConfig
        from app.services.neuralfoil_cdcl_service import NeuralFoilCdclService

        airfoil = _build_asb_airfoil("naca23013.5")
        assert airfoil.coordinates is not None, "Coordinate file should be loaded"

        service = NeuralFoilCdclService()
        result = service.compute_cdcl(
            airfoil, re=500_000.0, mach=0.1, config=CdclConfig()
        )
        assert isinstance(result, AvlCdcl)
        assert result.cd_0 > 0


class TestOperatingPointWithConfigs:
    def test_operating_point_accepts_configs(self):
        from app.schemas.aeroanalysisschema import CdclConfig, OperatingPointSchema, SpacingConfig

        op = OperatingPointSchema(
            velocity=30.0,
            alpha=5.0,
            cdcl_config=CdclConfig(n_crit=11.0),
            spacing_config=SpacingConfig(n_chord=16),
        )
        assert op.cdcl_config.n_crit == 11.0
        assert op.spacing_config.n_chord == 16

    def test_operating_point_configs_optional(self):
        from app.schemas.aeroanalysisschema import OperatingPointSchema

        op = OperatingPointSchema(velocity=30.0)
        assert op.cdcl_config is None
        assert op.spacing_config is None
