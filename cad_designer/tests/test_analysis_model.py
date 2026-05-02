"""Tests for cad_designer.airplane.aircraft_topology.models.analysis_model."""
from __future__ import annotations

import math
from collections import OrderedDict
from unittest.mock import MagicMock

import numpy as np
import pytest
from pydantic import ValidationError

from cad_designer.airplane.aircraft_topology.models.analysis_model import (
    AircraftModel,
    AircraftSummaryModel,
    AerodynamicsModel,
    AnalysisModel,
    AvlCoefficientsModel,
    AvlControlSurfaceModel,
    AvlDerivativesModel,
    AvlFlightConditionModel,
    AvlForceModel,
    AvlMomentModel,
    AvlReferenceModel,
    AvlSingleControlSurfaceModel,
    ClBetaClassification,
    CmAlphaClassification,
    CnBetaClassification,
    ControlSurfacesModel,
    EfficiencyModel,
    EnvironmentModel,
    StabilityLevel,
    StabilityModel,
    WingGeometryModel,
)


# ---------------------------------------------------------------------------
# Fixtures — reusable data builders
# ---------------------------------------------------------------------------

def _make_avl_flat_dict(
    *,
    alpha: float = 5.0,
    num_control_surfaces: int = 1,
) -> OrderedDict:
    """Build a minimal flat dict that mimics AVL solver output."""
    d = OrderedDict()
    # Reference
    d["Bref"] = 2.0
    d["Cref"] = 0.3
    d["Sref"] = 0.6
    d["Xref"] = 0.1
    d["Yref"] = 0.0
    d["Zref"] = 0.0
    d["Xnp"] = 0.15
    d["Strips"] = 40.0
    d["Surfaces"] = 4.0
    d["Vortices"] = 200.0
    # Forces
    d["F_b"] = (1.0, 0.0, -10.0)
    d["F_g"] = (1.0, 0.0, -10.0)
    d["F_w"] = [1.0, 0.0, -10.0]
    d["L"] = 10.0
    d["D"] = 0.5
    d["Y"] = 0.0
    # Moments
    d["M_b"] = [0.01, 0.02, 0.03]
    d["M_g"] = (0.01, 0.02, 0.03)
    d["M_w"] = [0.01, 0.02, 0.03]
    d["l_b"] = 0.01
    d["m_b"] = 0.02
    d["n_b"] = 0.03
    # Coefficients
    d["CL"] = 0.8
    d["CD"] = 0.02
    d["CY"] = 0.0
    d["CZ"] = -0.8
    d["CX"] = 0.02
    d["Cl"] = 0.001
    d["Cl'"] = 0.001
    d["Cm"] = -0.05
    d["Cn"] = 0.0
    d["Cn'"] = 0.0
    d["CDff"] = 0.018
    d["CDind"] = 0.015
    d["CDvis"] = 0.003
    d["CLff"] = 0.79
    d["CYff"] = 0.0
    d["e"] = 0.85

    # Control surfaces: keys between 'e' and 'CLa' provide names
    cs_names = ["aileron", "flaps", "elevator", "rudder"][:num_control_surfaces]
    for name in cs_names:
        d[name] = 5.0  # deflection value, keyed by name

    # Derivatives
    d["CLa"] = 4.5
    d["CLb"] = 0.0
    d["CLp"] = 0.0
    d["CLq"] = 7.0
    d["CLr"] = 0.0
    d["CYa"] = 0.0
    d["CYb"] = -0.3
    d["CYp"] = 0.0
    d["CYq"] = 0.0
    d["CYr"] = 0.2
    d["Cla"] = 0.0
    d["Clb"] = -0.05
    d["Clp"] = -0.4
    d["Clq"] = 0.0
    d["Clr"] = 0.1
    d["Cma"] = -1.2
    d["Cmb"] = 0.0
    d["Cmp"] = 0.0
    d["Cmq"] = -15.0
    d["Cmr"] = 0.0
    d["Cna"] = 0.0
    d["Cnb"] = 0.06
    d["Cnp"] = -0.02
    d["Cnq"] = 0.0
    d["Cnr"] = -0.1
    d["Clb Cnr / Clr Cnb"] = 0.83

    # Control surface derivative keys (ed01, CLd01, ...)
    for i, name in enumerate(cs_names):
        idx = f"{i + 1:02d}"
        d[f"ed{idx}"] = 0.9
        d[f"CDffd{idx}"] = 0.001
        d[f"CLd{idx}"] = 0.3
        d[f"CYd{idx}"] = 0.0
        d[f"Cld{idx}"] = 0.01
        d[f"Cmd{idx}"] = -0.1
        d[f"Cnd{idx}"] = 0.0

    # Flight condition
    d["alpha"] = alpha
    d["beta"] = 0.0
    d["mach"] = 0.1
    d["p"] = 0.0
    d["q"] = 0.0
    d["r"] = 0.0
    d["p'b/2V"] = 0.0
    d["pb/2V"] = 0.0
    d["qc/2V"] = 0.0
    d["r'b/2V"] = 0.0
    d["rb/2V"] = 0.0

    return d


def _make_mock_operating_point(
    alpha: float = 5.0,
    beta: float = 0.0,
    velocity: float = 30.0,
):
    op = MagicMock()
    op.alpha = alpha
    op.beta = beta
    op.velocity = velocity
    op.p = 0.0
    op.q = 0.0
    op.r = 0.0
    return op


def _make_mock_asb_airplane(
    b_ref: float = 2.0,
    c_ref: float = 0.3,
    s_ref: float = 0.6,
    xyz_ref: tuple = (0.1, 0.0, 0.0),
):
    airplane = MagicMock()
    airplane.b_ref = b_ref
    airplane.c_ref = c_ref
    airplane.s_ref = s_ref
    airplane.xyz_ref = xyz_ref
    return airplane


def _make_abu_data_dict(
    *,
    with_wing_aero: bool = True,
    operating_point=None,
) -> dict:
    """Build a dict that mimics AeroBuildup solver output."""
    op = operating_point or _make_mock_operating_point()

    wing_comp = MagicMock()
    wing_comp.oswalds_efficiency = 0.82
    wing_comp.op_point = op

    d: dict = {
        "x_np": 0.15,
        "x_np_lateral": 0.12,
        "F_b": np.array([1.0, 0.0, -10.0]),
        "F_g": np.array([1.0, 0.0, -10.0]),
        "F_w": np.array([1.0, 0.0, -10.0]),
        "L": 10.0,
        "D": 0.5,
        "Y": 0.0,
        "M_b": np.array([0.01, 0.02, 0.03]),
        "M_g": np.array([0.01, 0.02, 0.03]),
        "M_w": np.array([0.01, 0.02, 0.03]),
        "l_b": 0.01,
        "m_b": 0.02,
        "n_b": 0.03,
        "CL": 0.8,
        "CD": 0.02,
        "CY": 0.0,
        "CZ": None,
        "CX": None,
        "Cl": None,
        "Cl'": None,
        "Cm": -0.05,
        "Cn": None,
        "Cn'": None,
        "CDff": None,
        "CDind": None,
        "CDvis": None,
        "CLff": None,
        "CYff": None,
        "CLa": 4.5,
        "CLb": None,
        "CLp": None,
        "CLq": None,
        "CLr": None,
        "CYa": None,
        "CYb": -0.3,
        "CYp": None,
        "CYq": None,
        "CYr": None,
        "Cla": None,
        "Clb": -0.05,
        "Clp": None,
        "Clq": None,
        "Clr": None,
        "Cma": -1.2,
        "Cmb": None,
        "Cmp": None,
        "Cmq": None,
        "Cmr": None,
        "Cna": None,
        "Cnb": 0.06,
        "Cnp": None,
        "Cnq": None,
        "Cnr": None,
    }
    if with_wing_aero:
        d["wing_aero_components"] = [wing_comp]
    else:
        d["wing_aero_components"] = None
    return d


# ===========================================================================
# 1. Pydantic sub-model instantiation
# ===========================================================================

class TestAvlReferenceModel:
    """Test AvlReferenceModel instantiation and defaults."""

    def test_all_none_defaults(self):
        model = AvlReferenceModel()
        assert model.Bref is None
        assert model.Cref is None
        assert model.Sref is None
        assert model.Xnp is None

    def test_with_values(self):
        model = AvlReferenceModel(Bref=2.0, Cref=0.3, Sref=0.6, Xref=0.1, Yref=0.0, Zref=0.0)
        assert model.Bref == 2.0
        assert model.Sref == 0.6

    def test_serialization_roundtrip(self):
        model = AvlReferenceModel(Bref=2.0, Cref=0.3, Sref=0.6, Xnp=[0.15])
        data = model.model_dump()
        restored = AvlReferenceModel(**data)
        assert restored == model


class TestAvlForceModel:
    def test_all_none_defaults(self):
        model = AvlForceModel()
        assert model.F_b is None
        assert model.L is None

    def test_with_values(self):
        model = AvlForceModel(L=[10.0, 12.0], D=[0.5, 0.6])
        assert model.L == [10.0, 12.0]
        assert model.D == [0.5, 0.6]


class TestAvlMomentModel:
    def test_all_none_defaults(self):
        model = AvlMomentModel()
        assert model.M_b is None
        assert model.l_b is None

    def test_with_values(self):
        model = AvlMomentModel(l_b=[0.01], m_b=[0.02], n_b=[0.03])
        assert model.l_b == [0.01]


class TestAvlCoefficientsModel:
    def test_all_none_defaults(self):
        model = AvlCoefficientsModel()
        assert model.CL is None
        assert model.e is None

    def test_with_values(self):
        model = AvlCoefficientsModel(CL=[0.8], CD=[0.02], e=[0.85])
        assert model.CL == [0.8]
        assert model.e == [0.85]

    def test_serialization_roundtrip(self):
        model = AvlCoefficientsModel(CL=[0.8], CD=[0.02], CDff=[0.018])
        data = model.model_dump()
        restored = AvlCoefficientsModel(**data)
        assert restored == model


class TestAvlDerivativesModel:
    def test_all_none_defaults(self):
        model = AvlDerivativesModel()
        assert model.CLa is None
        assert model.Clb_Cnr_div_Clr_Cnb is None

    def test_with_values(self):
        model = AvlDerivativesModel(CLa=[4.5], Cmq=[-15.0])
        assert model.CLa == [4.5]
        assert model.Cmq == [-15.0]

    def test_sanitize_floats_replaces_nan(self):
        model = AvlDerivativesModel(CLa=[1.0, float("nan"), 3.0])
        assert model.CLa[0] == 1.0
        assert model.CLa[1] is None
        assert model.CLa[2] == 3.0

    def test_sanitize_floats_replaces_inf(self):
        model = AvlDerivativesModel(CLa=[float("inf"), float("-inf"), 2.0])
        assert model.CLa[0] is None
        assert model.CLa[1] is None
        assert model.CLa[2] == 2.0

    def test_sanitize_floats_none_passthrough(self):
        model = AvlDerivativesModel(CLa=[None, 1.0])
        # None is not a float, so sanitizer replaces it with None (no change)
        assert model.CLa[0] is None
        assert model.CLa[1] == 1.0

    def test_sanitize_floats_scalar_passthrough(self):
        """Non-list values should pass through unchanged."""
        model = AvlDerivativesModel()
        # Validator should not crash on None
        assert model.CLa is None


class TestAvlFlightConditionModel:
    def test_all_none_defaults(self):
        model = AvlFlightConditionModel()
        assert model.alpha is None
        assert model.mach is None

    def test_scalar_alpha(self):
        model = AvlFlightConditionModel(alpha=5.0)
        assert model.alpha == 5.0

    def test_list_alpha(self):
        model = AvlFlightConditionModel(alpha=[0.0, 5.0, 10.0])
        assert model.alpha == [0.0, 5.0, 10.0]


class TestAvlSingleControlSurfaceModel:
    def test_defaults_all_none(self):
        model = AvlSingleControlSurfaceModel()
        assert model.name is None
        assert model.ed is None

    def test_with_values(self):
        model = AvlSingleControlSurfaceModel(name="aileron", ed=[0.9], deflection=[5.0])
        assert model.name == "aileron"
        assert model.deflection == [5.0]


class TestAvlControlSurfaceModel:
    def test_empty(self):
        model = AvlControlSurfaceModel(control_surfaces=None)
        assert model.aileron is None
        assert model.flaps is None
        assert model.elevator is None
        assert model.rudder is None

    def test_deflection_by_name_found(self):
        cs = AvlSingleControlSurfaceModel(name="aileron", deflection=[3.0])
        model = AvlControlSurfaceModel(control_surfaces=[cs])
        assert model.aileron == [3.0]
        assert model.flaps is None

    def test_deflection_by_name_multiple(self):
        cs_aileron = AvlSingleControlSurfaceModel(name="aileron", deflection=[3.0])
        cs_flaps = AvlSingleControlSurfaceModel(name="flaps", deflection=[10.0])
        cs_elevator = AvlSingleControlSurfaceModel(name="elevator", deflection=[2.0])
        cs_rudder = AvlSingleControlSurfaceModel(name="rudder", deflection=[0.0])
        model = AvlControlSurfaceModel(
            control_surfaces=[cs_aileron, cs_flaps, cs_elevator, cs_rudder]
        )
        assert model.aileron == [3.0]
        assert model.flaps == [10.0]
        assert model.elevator == [2.0]
        assert model.rudder == [0.0]


class TestStabilityModels:
    """Test StabilityLevel enum and classification models."""

    def test_stability_level_values(self):
        assert StabilityLevel.STRONGLY_STABLE == "Strongly Stable"
        assert StabilityLevel.UNSTABLE == "Unstable"

    def test_cm_alpha_classification(self):
        model = CmAlphaClassification(
            value=-1.2,
            classification=StabilityLevel.STRONGLY_STABLE,
            comment="Good longitudinal stability",
        )
        assert model.value == -1.2
        assert model.classification == StabilityLevel.STRONGLY_STABLE

    def test_cl_beta_classification(self):
        model = ClBetaClassification(
            value=-0.05,
            classification=StabilityLevel.MODERATELY_STABLE,
            comment="Adequate lateral stability",
        )
        assert model.value == -0.05

    def test_cn_beta_classification(self):
        model = CnBetaClassification(
            value=0.06,
            classification=StabilityLevel.MARGINALLY_STABLE,
            comment="Marginal directional stability",
        )
        assert model.value == 0.06

    def test_stability_model(self):
        sm = StabilityModel(
            static_longitudinal_stability_best_alpha=CmAlphaClassification(
                value=-1.2, classification=StabilityLevel.STRONGLY_STABLE, comment="ok"
            ),
            static_lateral_stability_best_alpha=ClBetaClassification(
                value=-0.05, classification=StabilityLevel.MODERATELY_STABLE, comment="ok"
            ),
            static_directional_stability_best_alpha=CnBetaClassification(
                value=0.06, classification=StabilityLevel.MARGINALLY_STABLE, comment="ok"
            ),
        )
        assert sm.static_longitudinal_stability_best_alpha.value == -1.2


# ===========================================================================
# 2. Ancillary models (AircraftModel, EnvironmentModel, etc.)
# ===========================================================================

class TestAncillaryModels:
    def test_aircraft_model(self):
        m = AircraftModel(
            name="TestPlane",
            mass_kg=5.0,
            wing_area_m2=0.6,
            wing_span_m=2.0,
            wing_chord_m=0.3,
            MAC_m=0.31,
            static_margin_in_percent_MAC=10.0,
            NP_m=[0.15, 0.0, 0.0],
            airfoil_root="NACA2412",
            airfoil_tip="NACA0012",
        )
        assert m.name == "TestPlane"
        assert m.mass_kg == 5.0

    def test_environment_model(self):
        m = EnvironmentModel(rho_kgm3=1.225, gravity=9.81, elevation_m=0.0)
        assert m.rho_kgm3 == 1.225

    def test_control_surfaces_model(self):
        m = ControlSurfacesModel(
            flaps_installed=True,
            flap_type="plain",
            flap_deflection_deg=15.0,
            flap_area_m2=0.05,
            aileron_area_m2=0.03,
        )
        assert m.flaps_installed is True

    def test_control_surfaces_model_invalid_flap_type(self):
        with pytest.raises(ValidationError):
            ControlSurfacesModel(
                flaps_installed=True,
                flap_type="invalid_type",
                flap_deflection_deg=15.0,
                flap_area_m2=0.05,
                aileron_area_m2=0.03,
            )

    def test_wing_geometry_model(self):
        m = WingGeometryModel(
            taper_ratio=0.5,
            sweep_deg=5.0,
            dihedral_deg=3.0,
            washout_deg=2.0,
            incidence_deg=1.0,
        )
        assert m.taper_ratio == 0.5

    def test_efficiency_model(self):
        m = EfficiencyModel(
            masses_kg=[3.0, 5.0],
            stall_velocity_m_per_s_curve_masses_kg=[8.0, 10.0],
            travel_velocity_m_per_s_curve_masses_kg=[12.0, 15.0],
            stall_velocity_m_per_s=9.0,
            travel_velocity_m_per_s=13.0,
            alpha_at_stall_deg=12.0,
            alpha_at_best_LD_deg=5.0,
            max_LD_ratio=15.0,
            CL_at_max_LD=0.8,
        )
        assert m.max_LD_ratio == 15.0


# ===========================================================================
# 3. AnalysisModel.from_avl_dict
# ===========================================================================

class TestFromAvlDict:
    """Test parsing of flat AVL output dicts."""

    def test_basic_parsing(self):
        data = _make_avl_flat_dict()
        model = AnalysisModel.from_avl_dict(data)

        assert model.method == "avl"
        assert model.reference.Bref == 2.0
        assert model.reference.Cref == 0.3
        assert model.reference.Sref == 0.6
        assert model.reference.Xnp == [0.15]
        assert model.reference.Strips == 40.0

    def test_forces_wrapped_in_list(self):
        data = _make_avl_flat_dict()
        model = AnalysisModel.from_avl_dict(data)
        assert model.forces.L == [10.0]
        assert model.forces.D == [0.5]
        assert model.forces.Y == [0.0]

    def test_moments_wrapped_in_list(self):
        data = _make_avl_flat_dict()
        model = AnalysisModel.from_avl_dict(data)
        assert model.moments.l_b == [0.01]
        assert model.moments.m_b == [0.02]

    def test_coefficients(self):
        data = _make_avl_flat_dict()
        model = AnalysisModel.from_avl_dict(data)
        assert model.coefficients.CL == [0.8]
        assert model.coefficients.CD == [0.02]
        assert model.coefficients.e == [0.85]

    def test_derivatives(self):
        data = _make_avl_flat_dict()
        model = AnalysisModel.from_avl_dict(data)
        assert model.derivatives.CLa == [4.5]
        assert model.derivatives.Cmq == [-15.0]
        assert model.derivatives.Clb_Cnr_div_Clr_Cnb == [0.83]

    def test_flight_condition(self):
        data = _make_avl_flat_dict(alpha=7.0)
        model = AnalysisModel.from_avl_dict(data)
        assert model.flight_condition.alpha == [7.0]
        assert model.flight_condition.beta == 0.0
        assert model.flight_condition.mach == 0.1

    def test_single_control_surface(self):
        data = _make_avl_flat_dict(num_control_surfaces=1)
        model = AnalysisModel.from_avl_dict(data)
        cs = model.control_surfaces.control_surfaces
        assert cs is not None
        assert len(cs) == 1
        assert cs[0].name == "aileron"
        assert cs[0].deflection == [5.0]
        assert cs[0].ed == [0.9]

    def test_multiple_control_surfaces(self):
        data = _make_avl_flat_dict(num_control_surfaces=4)
        model = AnalysisModel.from_avl_dict(data)
        cs = model.control_surfaces.control_surfaces
        assert len(cs) == 4
        names = [c.name for c in cs]
        assert "aileron" in names
        assert "flaps" in names
        assert "elevator" in names
        assert "rudder" in names

    def test_no_control_surfaces(self):
        data = _make_avl_flat_dict(num_control_surfaces=0)
        model = AnalysisModel.from_avl_dict(data)
        assert model.control_surfaces.control_surfaces == []

    def test_xnp_lat_calculation(self):
        """Xnp_lat = Xref - (Cnb * Bref / CYb) when CYb != 0."""
        data = _make_avl_flat_dict()
        model = AnalysisModel.from_avl_dict(data)
        expected = data["Xref"] - (data["Cnb"] * (data["Bref"] / data["CYb"]))
        assert model.reference.Xnp_lat == [expected]

    def test_xnp_lat_cyb_zero(self):
        """When CYb == 0, Xnp_lat must be None (not [None]) to satisfy type."""
        data = _make_avl_flat_dict()
        data["CYb"] = 0
        model = AnalysisModel.from_avl_dict(data)
        assert model.reference.Xnp_lat is None


# ===========================================================================
# 4. AnalysisModel.from_dict (delegates to from_avl_dict + flattening)
# ===========================================================================

class TestFromDict:
    """from_dict calls from_avl_dict then _flatten_single_point_fields."""

    def test_single_point_flattened(self):
        data = _make_avl_flat_dict()
        model = AnalysisModel.from_dict(data)
        # Single-element lists should be flattened to scalars
        assert isinstance(model.forces.L, float)
        assert model.forces.L == 10.0
        assert isinstance(model.coefficients.CL, float)
        assert model.coefficients.CL == 0.8
        assert isinstance(model.flight_condition.alpha, float)

    def test_method_is_avl(self):
        data = _make_avl_flat_dict()
        model = AnalysisModel.from_dict(data)
        assert model.method == "avl"


# ===========================================================================
# 5. AnalysisModel._singleton_to_scalar
# ===========================================================================

class TestSingletonToScalar:
    @pytest.mark.parametrize(
        "input_val, expected",
        [
            ([42.0], 42.0),
            ([1, 2, 3], [1, 2, 3]),
            ([], []),
            (5.0, 5.0),
            (None, None),
            ("hello", "hello"),
        ],
    )
    def test_various_inputs(self, input_val, expected):
        result = AnalysisModel._singleton_to_scalar(input_val)
        assert result == expected


# ===========================================================================
# 6. AnalysisModel._flatten_single_point_fields
# ===========================================================================

class TestFlattenSinglePointFields:
    def test_flattens_singleton_lists(self):
        data = _make_avl_flat_dict(num_control_surfaces=1)
        model = AnalysisModel.from_avl_dict(data)
        # Before flattening, values are single-element lists
        assert model.forces.L == [10.0]
        flattened = AnalysisModel._flatten_single_point_fields(model)
        assert flattened.forces.L == 10.0
        assert flattened.forces.D == 0.5
        assert flattened.moments.l_b == 0.01
        assert flattened.coefficients.CL == 0.8
        assert flattened.derivatives.CLa == 4.5

    def test_flattens_control_surface_fields(self):
        data = _make_avl_flat_dict(num_control_surfaces=2)
        model = AnalysisModel.from_avl_dict(data)
        flattened = AnalysisModel._flatten_single_point_fields(model)
        for cs in flattened.control_surfaces.control_surfaces:
            # Each should be a scalar now
            assert isinstance(cs.ed, float)
            assert isinstance(cs.deflection, float)

    def test_no_control_surfaces_does_not_crash(self):
        data = _make_avl_flat_dict(num_control_surfaces=0)
        model = AnalysisModel.from_avl_dict(data)
        flattened = AnalysisModel._flatten_single_point_fields(model)
        assert flattened.control_surfaces.control_surfaces == []


# ===========================================================================
# 7. AnalysisModel.from_abu_dict
# ===========================================================================

class TestFromAbuDict:
    """Test AeroBuildup dict parsing with mocked aerosandbox objects."""

    def test_basic_parsing(self):
        airplane = _make_mock_asb_airplane()
        abu_data = _make_abu_data_dict()
        model = AnalysisModel.from_abu_dict(abu_data, airplane)

        assert model.method == "aerobuildup"
        assert model.reference.Bref == 2.0
        assert model.reference.Cref == 0.3
        assert model.reference.Sref == 0.6

    def test_method_override(self):
        airplane = _make_mock_asb_airplane()
        abu_data = _make_abu_data_dict()
        model = AnalysisModel.from_abu_dict(abu_data, airplane, methode="vortex_lattice")
        assert model.method == "vortex_lattice"

    def test_forces_from_numpy_scalars(self):
        airplane = _make_mock_asb_airplane()
        abu_data = _make_abu_data_dict()
        model = AnalysisModel.from_abu_dict(abu_data, airplane)
        assert model.forces.L == [10.0]
        assert model.forces.D == [0.5]

    def test_forces_f_b_numpy_array(self):
        airplane = _make_mock_asb_airplane()
        abu_data = _make_abu_data_dict()
        model = AnalysisModel.from_abu_dict(abu_data, airplane)
        # F_b is np.array([1.0, 0.0, -10.0]) -> wrapped in list
        assert model.forces.F_b is not None
        assert len(model.forces.F_b) == 1

    def test_moments_from_numpy(self):
        airplane = _make_mock_asb_airplane()
        abu_data = _make_abu_data_dict()
        model = AnalysisModel.from_abu_dict(abu_data, airplane)
        assert model.moments.l_b == [0.01]

    def test_coefficients(self):
        airplane = _make_mock_asb_airplane()
        abu_data = _make_abu_data_dict()
        model = AnalysisModel.from_abu_dict(abu_data, airplane)
        assert model.coefficients.CL == [0.8]
        assert model.coefficients.CD == [0.02]
        assert model.coefficients.e == [0.82]

    def test_derivatives(self):
        airplane = _make_mock_asb_airplane()
        abu_data = _make_abu_data_dict()
        model = AnalysisModel.from_abu_dict(abu_data, airplane)
        assert model.derivatives.CLa == [4.5]
        assert model.derivatives.Cma == [-1.2]
        assert model.derivatives.Clb_Cnr_div_Clr_Cnb is None

    def test_no_control_surfaces(self):
        airplane = _make_mock_asb_airplane()
        abu_data = _make_abu_data_dict()
        model = AnalysisModel.from_abu_dict(abu_data, airplane)
        assert model.control_surfaces.control_surfaces is None

    def test_flight_condition_from_wing_aero(self):
        airplane = _make_mock_asb_airplane()
        abu_data = _make_abu_data_dict()
        model = AnalysisModel.from_abu_dict(abu_data, airplane)
        assert model.flight_condition.alpha == [5.0]
        assert model.flight_condition.beta == 0.0
        # mach = velocity / 347
        assert model.flight_condition.mach == pytest.approx(30.0 / 347.0)

    def test_flight_condition_fallback_to_operating_point(self):
        """When wing_aero_components is None, use operating_point arg."""
        airplane = _make_mock_asb_airplane()
        op = _make_mock_operating_point(alpha=8.0, velocity=50.0)
        abu_data = _make_abu_data_dict(with_wing_aero=False, operating_point=op)
        model = AnalysisModel.from_abu_dict(abu_data, airplane, operating_point=op)
        assert model.flight_condition.alpha == [8.0]
        assert model.flight_condition.mach == pytest.approx(50.0 / 347.0)

    def test_reference_xnp_float(self):
        airplane = _make_mock_asb_airplane()
        abu_data = _make_abu_data_dict()
        model = AnalysisModel.from_abu_dict(abu_data, airplane)
        assert model.reference.Xnp == [0.15]

    def test_reference_xnp_list(self):
        airplane = _make_mock_asb_airplane()
        abu_data = _make_abu_data_dict()
        abu_data["x_np"] = [0.15, 0.16]
        model = AnalysisModel.from_abu_dict(abu_data, airplane)
        # When x_np is a list with >1 element, xnp_val is first element (a float),
        # so it wraps as [0.15]
        assert model.reference.Xnp == [0.15]

    def test_reference_xnp_none(self):
        airplane = _make_mock_asb_airplane()
        abu_data = _make_abu_data_dict()
        abu_data["x_np"] = None
        model = AnalysisModel.from_abu_dict(abu_data, airplane)
        assert model.reference.Xnp is None

    def test_oswald_efficiency_from_wing_aero(self):
        airplane = _make_mock_asb_airplane()
        abu_data = _make_abu_data_dict()
        model = AnalysisModel.from_abu_dict(abu_data, airplane)
        assert model.coefficients.e == [0.82]

    def test_oswald_efficiency_none_without_wing_aero(self):
        airplane = _make_mock_asb_airplane()
        op = _make_mock_operating_point()
        abu_data = _make_abu_data_dict(with_wing_aero=False, operating_point=op)
        model = AnalysisModel.from_abu_dict(abu_data, airplane, operating_point=op)
        assert model.coefficients.e is None

    def test_forces_f_b_nested_arrays(self):
        """When F_b is [[x], [y], [z]] (multi-point arrays), extract first element."""
        airplane = _make_mock_asb_airplane()
        abu_data = _make_abu_data_dict()
        abu_data["F_b"] = [np.array([1.0]), np.array([0.0]), np.array([-10.0])]
        model = AnalysisModel.from_abu_dict(abu_data, airplane)
        assert model.forces.F_b is not None

    def test_forces_f_b_none(self):
        airplane = _make_mock_asb_airplane()
        abu_data = _make_abu_data_dict()
        abu_data["F_b"] = None
        model = AnalysisModel.from_abu_dict(abu_data, airplane)
        assert model.forces.F_b is None


# ===========================================================================
# 8. Serialization roundtrip for AnalysisModel
# ===========================================================================

class TestAnalysisModelSerialization:
    def test_avl_roundtrip(self):
        data = _make_avl_flat_dict()
        model = AnalysisModel.from_avl_dict(data)
        dumped = model.model_dump()
        restored = AnalysisModel(**dumped)
        assert restored.method == model.method
        assert restored.reference.Bref == model.reference.Bref
        assert restored.coefficients.CL == model.coefficients.CL

    def test_json_roundtrip(self):
        data = _make_avl_flat_dict()
        model = AnalysisModel.from_avl_dict(data)
        json_str = model.model_dump_json()
        restored = AnalysisModel.model_validate_json(json_str)
        assert restored.method == "avl"
        assert restored.reference.Bref == 2.0


# ===========================================================================
# 9. AircraftSummaryModel
# ===========================================================================

class TestAircraftSummaryModel:
    def test_instantiation(self):
        summary = AircraftSummaryModel(
            aircraft=AircraftModel(
                name="Test", mass_kg=5.0, wing_area_m2=0.6, wing_span_m=2.0,
                wing_chord_m=0.3, MAC_m=0.31, static_margin_in_percent_MAC=10.0,
                NP_m=[0.15, 0.0, 0.0], airfoil_root="NACA2412", airfoil_tip="NACA0012",
            ),
            environment=EnvironmentModel(rho_kgm3=1.225, gravity=9.81, elevation_m=0.0),
            control_surfaces=ControlSurfacesModel(
                flaps_installed=False, flap_type="none", flap_deflection_deg=0.0,
                flap_area_m2=0.0, aileron_area_m2=0.03,
            ),
            wing_geometry=WingGeometryModel(
                taper_ratio=0.5, sweep_deg=5.0, dihedral_deg=3.0,
                washout_deg=2.0, incidence_deg=1.0,
            ),
            aerodynamics=AerodynamicsModel(
                alpha_range_deg=[0.0, 5.0],
                F_g_curve_alpha=[[1.0, 0.0, -10.0]],
                F_b_curve_alpha=[[1.0, 0.0, -10.0]],
                F_w_curve_alpha=[[1.0, 0.0, -10.0]],
                M_g_curve_alpha=[[0.01, 0.02, 0.03]],
                M_b_curve_alpha=[[0.01, 0.02, 0.03]],
                M_w_curve_alpha=[[0.01, 0.02, 0.03]],
                L_lift_force_N_curve_alpha=[10.0],
                Y_side_force_N_curve_alpha=[0.0],
                D_drag_force_N_curve_alpha=[0.5],
                l_b_rolling_moment_Nm_curve_alpha=[0.01],
                m_b_pitching_moment_Nm_curve_alpha=[0.02],
                n_b_yawing_moment_Nm_curve_alpha=[0.03],
                CL_lift_coefficient_curve_alpha=[0.8],
                CY_sideforce_coefficient_curve_alpha=[0.0],
                CD_drag_coefficient_curve_alpha=[0.02],
                Cl_rolling_moment_curve_alpha=[0.001],
                Cm_pitching_moment_curve_alpha=[-0.05],
                Cn_yawing_moment_curve_alpha=[0.0],
            ),
            efficiency=EfficiencyModel(
                masses_kg=[5.0],
                stall_velocity_m_per_s_curve_masses_kg=[9.0],
                travel_velocity_m_per_s_curve_masses_kg=[13.0],
                stall_velocity_m_per_s=9.0,
                travel_velocity_m_per_s=13.0,
                alpha_at_stall_deg=12.0,
                alpha_at_best_LD_deg=5.0,
                max_LD_ratio=15.0,
                CL_at_max_LD=0.8,
            ),
            stability=StabilityModel(
                static_longitudinal_stability_best_alpha=CmAlphaClassification(
                    value=-1.2, classification=StabilityLevel.STRONGLY_STABLE, comment="ok"
                ),
                static_lateral_stability_best_alpha=ClBetaClassification(
                    value=-0.05, classification=StabilityLevel.MODERATELY_STABLE, comment="ok"
                ),
                static_directional_stability_best_alpha=CnBetaClassification(
                    value=0.06, classification=StabilityLevel.MARGINALLY_STABLE, comment="ok"
                ),
            ),
        )
        assert summary.aircraft.name == "Test"
        assert summary.environment.rho_kgm3 == 1.225


# ===========================================================================
# 10. Edge cases
# ===========================================================================

class TestEdgeCases:
    def test_analysis_model_missing_required_method(self):
        with pytest.raises(ValidationError):
            AnalysisModel(
                reference=AvlReferenceModel(),
                forces=AvlForceModel(),
                moments=AvlMomentModel(),
                coefficients=AvlCoefficientsModel(),
                derivatives=AvlDerivativesModel(),
                control_surfaces=AvlControlSurfaceModel(control_surfaces=None),
                flight_condition=AvlFlightConditionModel(),
            )

    def test_analysis_model_invalid_method(self):
        with pytest.raises(ValidationError):
            AnalysisModel(
                method="invalid_method",
                reference=AvlReferenceModel(),
                forces=AvlForceModel(),
                moments=AvlMomentModel(),
                coefficients=AvlCoefficientsModel(),
                derivatives=AvlDerivativesModel(),
                control_surfaces=AvlControlSurfaceModel(control_surfaces=None),
                flight_condition=AvlFlightConditionModel(),
            )

    def test_derivatives_all_nan_list(self):
        model = AvlDerivativesModel(CLa=[float("nan"), float("nan")])
        assert all(v is None for v in model.CLa)

    def test_aircraft_model_missing_field(self):
        with pytest.raises(ValidationError):
            AircraftModel(name="X")  # missing required fields
