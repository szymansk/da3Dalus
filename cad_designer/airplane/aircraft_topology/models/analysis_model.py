from __future__ import annotations

from enum import Enum

import math
import numpy as np
from pydantic import BaseModel, Field, field_validator
from typing import Literal

import aerosandbox as asb


class AircraftModel(BaseModel):
    name: str = Field(..., title="Aircraft Name", description="Name of the aircraft [string]")
    mass_kg: float = Field(..., title="Total Mass", description="Total aircraft mass [kg]")
    wing_area_m2: float = Field(..., title="Wing Area", description="Wing reference area [m²]")
    wing_span_m: float = Field(..., title="Wing Span", description="Wingspan [m]")
    wing_chord_m: float = Field(..., title="Mean Geometric Chord", description="Mean geometric chord of the wing [m]")
    MAC_m: float = Field(..., title="Mean Aerodynamic Chord", description="Mean aerodynamic chord [m]")
    static_margin_in_percent_MAC: float = Field(..., title="Static Margin", description="Static margin as % of MAC [%]")
    NP_m: list[float] = Field(..., title="Neutral Point", description="Neutral point coordinates [m]")
    airfoil_root: str = Field(..., title="Root Airfoil", description="Root airfoil name [string]")
    airfoil_tip: str = Field(..., title="Tip Airfoil", description="Tip airfoil name [string]")


class EnvironmentModel(BaseModel):
    rho_kgm3: float = Field(..., title="Air Density", description="Air density [kg/m³]")
    gravity: float = Field(..., title="Gravity", description="Gravitational acceleration [m/s²]")
    elevation_m: float = Field(..., title="Elevation", description="Field elevation above sea level [m]")


class ControlSurfacesModel(BaseModel):
    flaps_installed: bool = Field(..., title="Flaps Installed", description="Flag if flaps are installed [bool]")
    flap_type: Literal["none", "plain", "split", "slotted", "fowler", "double-slotted", "triple-slotted"] = Field(
        ..., title="Flap Type", description="Type of flap [string]"
    )
    flap_deflection_deg: float = Field(..., title="Flap Deflection", description="Flap deflection angle [deg]")
    flap_area_m2: float = Field(..., title="Flap Area", description="Flap surface area [m²]")
    aileron_area_m2: float = Field(..., title="Aileron Area", description="Aileron surface area [m²]")


class WingGeometryModel(BaseModel):
    taper_ratio: float = Field(..., title="Taper Ratio", description="Wing taper ratio [-]: tip/root chord")
    sweep_deg: float = Field(..., title="Sweep Angle", description="Mean sweep angle [deg]")
    dihedral_deg: float = Field(..., title="Dihedral Angle", description="Mean dihedral angle [deg]")
    washout_deg: float = Field(..., title="Washout Angle", description="Washout angle (twist) [deg]")
    incidence_deg: float = Field(..., title="Incidence Angle", description="Wing incidence angle [deg]")


class AerodynamicsModel(BaseModel):
    alpha_range_deg: list[float] = Field(..., title="Angle of Attack Range", description="Angle of attack values [deg]")
    F_g_curve_alpha: list[list[float]] = Field(..., title="Geometry Axes Forces", description="Forces in geometry axes [N]")
    F_b_curve_alpha: list[list[float]] = Field(..., title="Body Axes Forces", description="Forces in body axes [N]")
    F_w_curve_alpha: list[list[float]] = Field(..., title="Wind Axes Forces", description="Forces in wind axes [N]")
    M_g_curve_alpha: list[list[float]] = Field(..., title="Geometry Moments", description="Moments about geometry axes [Nm]")
    M_b_curve_alpha: list[list[float]] = Field(..., title="Body Moments", description="Moments about body axes [Nm]")
    M_w_curve_alpha: list[list[float]] = Field(..., title="Wind Moments", description="Moments about wind axes [Nm]")
    L_lift_force_N_curve_alpha: list[float] = Field(..., title="Lift Force", description="Lift force [N]")
    Y_side_force_N_curve_alpha: list[float] = Field(..., title="Side Force", description="Side force [N]")
    D_drag_force_N_curve_alpha: list[float] = Field(..., title="Drag Force", description="Drag force [N]")
    l_b_rolling_moment_Nm_curve_alpha: list[float] = Field(..., title="Rolling Moment", description="Rolling moment [Nm]")
    m_b_pitching_moment_Nm_curve_alpha: list[float] = Field(..., title="Pitching Moment", description="Pitching moment [Nm]")
    n_b_yawing_moment_Nm_curve_alpha: list[float] = Field(..., title="Yawing Moment", description="Yawing moment [Nm]")
    CL_lift_coefficient_curve_alpha: list[float] = Field(..., title="Lift Coefficient", description="Lift coefficient [-]: wind axes")
    CY_sideforce_coefficient_curve_alpha: list[float] = Field(..., title="Sideforce Coefficient", description="Sideforce coefficient [-]: wind axes")
    CD_drag_coefficient_curve_alpha: list[float] = Field(..., title="Drag Coefficient", description="Drag coefficient [-]: wind axes")
    Cl_rolling_moment_curve_alpha: list[float] = Field(..., title="Rolling Coefficient", description="Rolling coefficient [-]: body axes")
    Cm_pitching_moment_curve_alpha: list[float] = Field(..., title="Pitching Coefficient", description="Pitching coefficient [-]: body axes")
    Cn_yawing_moment_curve_alpha: list[float] = Field(..., title="Yawing Coefficient", description="Yawing coefficient [-]: body axes")


class EfficiencyModel(BaseModel):
    masses_kg: list[float] = Field(..., title="Masses", description="List of mass configurations [kg]")
    stall_velocity_m_per_s_curve_masses_kg: list[float] = Field(..., title="Stall Velocities", description="Stall velocity per mass [m/s]")
    travel_velocity_m_per_s_curve_masses_kg: list[float] = Field(..., title="Travel Velocities", description="Travel velocity per mass [m/s]")
    stall_velocity_m_per_s: float = Field(..., title="Stall Velocity", description="Stall speed at current mass [m/s]")
    travel_velocity_m_per_s: float = Field(..., title="Travel Velocity", description="Optimal travel speed [m/s]")
    alpha_at_stall_deg: float = Field(..., title="Stall AoA", description="Angle of attack at stall [deg]")
    alpha_at_best_LD_deg: float = Field(..., title="Best L/D AoA", description="AoA at best lift-to-drag ratio [deg]")
    max_LD_ratio: float = Field(..., title="Max L/D Ratio", description="Maximum lift-to-drag ratio [-]: unitless")
    CL_at_max_LD: float = Field(..., title="CL at Max L/D", description="Lift coefficient at best L/D [-]: unitless")


class StabilityLevel(str, Enum):
    STRONGLY_STABLE = "Strongly Stable"
    MODERATELY_STABLE = "Moderately Stable"
    MARGINALLY_STABLE = "Marginally Stable"
    NEUTRALLY_STABLE = "Neutrally Stable"
    UNSTABLE = "Unstable"

class CmAlphaClassification(BaseModel):
    value: float = Field(..., title="Cm_alpha", description="Pitching moment derivative with respect to angle of attack [1/rad]")
    classification: StabilityLevel = Field(..., title="Stability Classification", description="Stability category based on Cm_alpha magnitude")
    comment: str = Field(..., title="Comment", description="Interpretation and suggestions based on classification")

class ClBetaClassification(BaseModel):
    value: float = Field(..., title="Cl_beta", description="Rolling moment derivative with respect to sideslip angle [1/rad]")
    classification: StabilityLevel = Field(..., title="Stability Classification", description="Stability category based on Cl_beta magnitude")
    comment: str = Field(..., title="Comment", description="Interpretation and suggestions based on classification")

class CnBetaClassification(BaseModel):
    value: float = Field(..., title="Cn_beta", description="Yawing moment derivative w.r.t. sideslip angle [1/rad]")
    classification: StabilityLevel = Field(..., title="Stability Classification", description="Directional stability class")
    comment: str = Field(..., title="Comment", description="Explanation of classification")

class StabilityModel(BaseModel):
    static_longitudinal_stability_best_alpha: CmAlphaClassification = Field(..., title="Longitudinal Stability", description="Static longitudinal stability present")
    static_lateral_stability_best_alpha: ClBetaClassification = Field(..., title="Lateral Stability", description="Static lateral stability present")
    static_directional_stability_best_alpha: CnBetaClassification = Field(..., title="Lateral Stability", description="Static directional stability present")

class AvlReferenceModel(BaseModel):
    Bref: float | None = Field(None, title="Reference Span", description="Reference span [m]")
    Cref: float | None = Field(None, title="Reference Chord", description="Reference chord [m]")
    Sref: float | None = Field(None, title="Reference Area", description="Reference area [m²]")
    Xref: float | None = Field(None, title="X Reference", description="X reference location [m]")
    Yref: float | None = Field(None, title="Y Reference", description="Y reference location [m]")
    Zref: float | None = Field(None, title="Z Reference", description="Z reference location [m]")
    Xnp: list[float] | None = Field(None, title="Neutral Point", description="Neutral point location [m]")
    Xnp_lat: list[float] | None = Field(None, title="Lateral Neutral Point", description="Lateral Neutral point location [m]")
    Strips: float | None = Field(None, title="Strip Count", description="Number of strips in the model [-]")
    Surfaces: float | None = Field(None, title="Surface Count", description="Number of surfaces in the model [-]")
    Vortices: float | None = Field(None, title="Vortex Count", description="Number of vortices in the model [-]")

class AvlForceModel(BaseModel):
    F_b: list[tuple[float, float, float]] | None = Field(None, title="Body Axes Forces", description="List of forces in body axes for each alpha [N]")
    F_g: list[tuple[float, float, float]] | None = Field(None, title="Geometry Axes Forces", description="List of forces in geometry axes for each alpha [N]")
    F_w: list[list[float]] | None = Field(None, title="Wind Axes Forces", description="List of forces in wind axes for each alpha [N]")
    L: list[float] | None = Field(None, title="Lift Force", description="List of lift force for each alpha [N]")
    D: list[float] | None = Field(None, title="Drag Force", description="List of drag force for each alpha [N]")
    Y: list[float] | None = Field(None, title="Side Force", description="List of side force for each alpha [N]")

class AvlMomentModel(BaseModel):
    M_b: list[list[float]] | None = Field(None, title="Body Moments", description="List of moments about body axes for each alpha [Nm]")
    M_g: list[tuple[float, float, float]] | None = Field(None, title="Geometry Moments", description="List of moments about geometry axes for each alpha [Nm]")
    M_w: list[list[float]] | None = Field(None, title="Wind Moments", description="List of moments about wind axes for each alpha [Nm]")
    l_b: list[float] | None = Field(None, title="Body Roll Moment", description="List of roll moment in body axes for each alpha [Nm]")
    m_b: list[float] | None = Field(None, title="Body Pitch Moment", description="List of pitch moment in body axes for each alpha [Nm]")
    n_b: list[float] | None = Field(None, title="Body Yaw Moment", description="List of yaw moment in body axes for each alpha [Nm]")

class AvlCoefficientsModel(BaseModel):
    CL: list[float] | None = Field(None, title="Lift Coefficient", description="List of lift coefficient for each alpha [-]")
    CD: list[float] | None = Field(None, title="Drag Coefficient", description="List of drag coefficient for each alpha [-]")
    CY: list[float] | None = Field(None, title="Y-Force Coefficient", description="List of y-axis force coefficient for each alpha [-]")
    CZ: list[float] | None = Field(None, title="Z-Force Coefficient", description="List of z-axis force coefficient for each alpha [-]")
    CX: list[float] | None = Field(None, title="X-Force Coefficient", description="List of x-axis force coefficient for each alpha [-]")
    Cl: list[float] | None = Field(None, title="Roll Moment Coefficient", description="List of roll moment coefficient for each alpha [-]")
    Cl_prime: list[float] | None = Field(None, title="Roll Moment Prime", description="List of roll moment coefficient prime for each alpha [-]")
    Cm: list[float] | None = Field(None, title="Pitch Moment Coefficient", description="List of pitch moment coefficient for each alpha [-]")
    Cn: list[float] | None = Field(None, title="Yaw Moment Coefficient", description="List of yaw moment coefficient for each alpha [-]")
    Cn_prime: list[float] | None = Field(None, title="Yaw Moment Prime", description="List of yaw moment coefficient prime for each alpha [-]")
    CDff: list[float] | None = Field(None, title="Drag in Trefftz Plane", description="List ofTrefftz Plane drag coefficient for each alpha [-]")
    CDind: list[float] | None = Field(None, title="Induced Drag", description="List of induced drag coefficient for each alpha [-]")
    CDvis: list[float] | None = Field(None, title="Viscous Drag", description="List of viscous drag coefficient for each alpha [-]")
    CLff: list[float] | None = Field(None, title="Lift in Trefftz Plane", description="List of Trefftz Plane lift coefficient for each alpha [-]")
    CYff: list[float] | None = Field(None, title="Trefftz Plane Side Force", description="List of Trefftz Plane side force coefficient for each alpha [-]")
    e: list[float] | None = Field(None, title="Oswald Efficiency", description="List of Oswald efficiency factor for each alpha [-]")

class AvlDerivativesModel(BaseModel):
    CLa: list[float | None] | None = Field(None, title="Lift Curve Slope", description="List of lift curve slope for each alpha [1/rad]")
    CLb: list[float | None] | None = Field(None, title="Lift-Sideslip Derivative", description="List of lift coefficient derivative with sideslip for each alpha [1/rad]")
    CLp: list[float | None] | None = Field(None, title="Roll Damping", description="List of roll damping derivative for each alpha [1/rad]")
    CLq: list[float | None] | None = Field(None, title="Pitch Rate Lift", description="List of pitch rate lift derivative for each alpha [1/rad]")
    CLr: list[float | None] | None = Field(None, title="Yaw Rate Lift", description="List of yaw rate lift derivative for each alpha [1/rad]")
    CYa: list[float | None] | None = Field(None, title="Side Force-Alpha", description="List of side force derivative with alpha for each alpha [1/rad]")
    CYb: list[float | None] | None = Field(None, title="Side Force-Beta", description="List of side force derivative with beta for each alpha [1/rad]")
    CYp: list[float | None] | None = Field(None, title="Roll Rate Side Force", description="List of roll rate side force derivative for each alpha [1/rad]")
    CYq: list[float | None] | None = Field(None, title="Pitch Rate Side Force", description="List of pitch rate side force derivative for each alpha [1/rad]")
    CYr: list[float | None] | None = Field(None, title="Yaw Rate Side Force", description="List of yaw rate side force derivative for each alpha [1/rad]")
    Cla: list[float | None] | None = Field(None, title="Roll-Alpha Derivative", description="List of roll moment derivative with alpha for each alpha [1/rad]")
    Clb: list[float | None] | None = Field(None, title="Roll-Beta Derivative", description="List of roll moment derivative with beta for each alpha [1/rad]")
    Clp: list[float | None] | None = Field(None, title="Roll Damping", description="List of roll damping derivative for each alpha [1/rad]")
    Clq: list[float | None] | None = Field(None, title="Pitch Rate Roll", description="List of pitch rate roll derivative for each alpha [1/rad]")
    Clr: list[float | None] | None = Field(None, title="Yaw Rate Roll", description="List of yaw rate roll derivative for each alpha [1/rad]")
    Cma: list[float | None] | None = Field(None, title="Pitch-Alpha Derivative", description="List of pitch moment derivative with alpha for each alpha [1/rad]")
    Cmb: list[float | None] | None = Field(None, title="Pitch-Beta Derivative", description="List of pitch moment derivative with beta for each alpha [1/rad]")
    Cmp: list[float | None] | None = Field(None, title="Roll Rate Pitch", description="List of roll rate pitch derivative for each alpha [1/rad]")
    Cmq: list[float | None] | None = Field(None, title="Pitch Damping", description="List of pitch damping derivative for each alpha [1/rad]")
    Cmr: list[float | None] | None = Field(None, title="Yaw Rate Pitch", description="List of yaw rate pitch derivative for each alpha [1/rad]")
    Cna: list[float | None] | None = Field(None, title="Yaw-Alpha Derivative", description="List of yaw moment derivative with alpha for each alpha [1/rad]")
    Cnb: list[float | None] | None = Field(None, title="Yaw-Beta Derivative", description="List of yaw moment derivative with beta for each alpha [1/rad]")
    Cnp: list[float | None] | None = Field(None, title="Roll Rate Yaw", description="List of roll rate yaw derivative for each alpha [1/rad]")
    Cnq: list[float | None] | None = Field(None, title="Pitch Rate Yaw", description="List of pitch rate yaw derivative for each alpha [1/rad]")
    Cnr: list[float | None] | None = Field(None, title="Yaw Damping", description="List of yaw damping derivative for each alpha [1/rad]")
    Clb_Cnr_div_Clr_Cnb: list[float | None] | None = Field(None, title="Roll-Yaw Coupling", description="List of roll-yaw coupling parameter for each alpha [-]")

    @field_validator('*', mode='before')
    @classmethod
    def sanitize_floats(cls, v):
        if isinstance(v, list):
            return [x if isinstance(x, float) and math.isfinite(x) else None for x in v]
        return v

class AvlSingleControlSurfaceModel(BaseModel):
    name: str | None = Field(None, title="Control Surface Name", description="Name of the control surface")
    ed: list[float] | None = Field(None, title="Control Surface Efficiency", description="List of control surface efficiency for each alpha [-]")
    CDff: list[float] | None = Field(None, title="Control Surface Drag", description="List of control surface drag contribution for each alpha [-]")
    CLd: list[float] | None = Field(None, title="Control Surface Lift", description="List of control surface lift contribution for each alpha [-]")
    CYd: list[float] | None = Field(None, title="Control Surface Side Force", description="List of control surface side force contribution for each alpha [-]")
    Cld: list[float] | None = Field(None, title="Control Surface Roll", description="List of control surface roll contribution for each alpha [-]")
    Cmd: list[float] | None = Field(None, title="Control Surface Pitch", description="List of control surface pitch contribution for each alpha [-]")
    Cnd: list[float] | None = Field(None, title="Control Surface Yaw", description="List of control surface yaw contribution for each alpha [-]")
    deflection: list[float] | None = Field(None, title="Control Surface Deflection", description="List of control surface deflection angle for each alpha [deg]")

class AvlControlSurfaceModel(BaseModel):
    control_surfaces: list[AvlSingleControlSurfaceModel] | None = Field(None, title="Control Surfaces", description="List of control surfaces")

    def _deflection_by_name(self, name: str):
        for control_surface in self.control_surfaces or []:
            if control_surface.name == name:
                return control_surface.deflection
        return None

    @property
    def aileron(self):
        return self._deflection_by_name("aileron")

    @property
    def flaps(self):
        return self._deflection_by_name("flaps")

    @property
    def elevator(self):
        return self._deflection_by_name("elevator")

    @property
    def rudder(self):
        return self._deflection_by_name("rudder")

class AvlFlightConditionModel(BaseModel):
    alpha: float | list[float] | None = Field(None, title="Angle of Attack", description="List of angle of attack for each alpha [deg]")
    beta: float | list[float] | None = Field(None, title="Sideslip Angle", description="Sideslip angle [deg]")
    mach: float | list[float] | None = Field(None, title="Mach Number", description="Mach number [-]")
    p: float | list[float] | None = Field(None, title="Roll Rate", description="Roll rate [rad/s]")
    q: float | list[float] | None = Field(None, title="Pitch Rate", description="Pitch rate [rad/s]")
    r: float | list[float] | None = Field(None, title="Yaw Rate", description="Yaw rate [rad/s]")
    p_prime_b_div_2V: float | None = Field(None, title="Normalized Roll Acceleration", description="Normalized roll acceleration [-]")
    pb_div_2V: float | None = Field(None, title="Normalized Roll Rate", description="Normalized roll rate [-]")
    qc_div_2V: float | None = Field(None, title="Normalized Pitch Rate", description="Normalized pitch rate [-]")
    r_prime_b_div_2V: float | None = Field(None, title="Normalized Yaw Acceleration", description="Normalized yaw acceleration [-]")
    rb_div_2V: float | None = Field(None, title="Normalized Yaw Rate", description="Normalized yaw rate [-]")

class AnalysisModel(BaseModel):
    method: Literal['avl', 'aerobuildup', 'vortex_lattice'] = Field(..., title="Analysis Method", description="Method used for analysis: 'avl', 'aerobuildup', or 'vortex_lattice'")
    reference: AvlReferenceModel
    forces: AvlForceModel
    moments: AvlMomentModel
    coefficients: AvlCoefficientsModel
    derivatives: AvlDerivativesModel
    control_surfaces: AvlControlSurfaceModel
    flight_condition: AvlFlightConditionModel

    @staticmethod
    def _singleton_to_scalar(value):
        if isinstance(value, list) and len(value) == 1:
            return value[0]
        return value

    @classmethod
    def _flatten_single_point_fields(cls, model: 'AnalysisModel') -> 'AnalysisModel':
        model.reference.Xnp = cls._singleton_to_scalar(model.reference.Xnp)
        model.reference.Xnp_lat = cls._singleton_to_scalar(model.reference.Xnp_lat)

        model.forces.L = cls._singleton_to_scalar(model.forces.L)
        model.forces.D = cls._singleton_to_scalar(model.forces.D)
        model.forces.Y = cls._singleton_to_scalar(model.forces.Y)

        model.moments.l_b = cls._singleton_to_scalar(model.moments.l_b)
        model.moments.m_b = cls._singleton_to_scalar(model.moments.m_b)
        model.moments.n_b = cls._singleton_to_scalar(model.moments.n_b)

        model.coefficients.CL = cls._singleton_to_scalar(model.coefficients.CL)
        model.coefficients.CD = cls._singleton_to_scalar(model.coefficients.CD)
        model.coefficients.Cm = cls._singleton_to_scalar(model.coefficients.Cm)

        model.derivatives.CLa = cls._singleton_to_scalar(model.derivatives.CLa)
        model.derivatives.Cmq = cls._singleton_to_scalar(model.derivatives.Cmq)
        model.derivatives.Cnb = cls._singleton_to_scalar(model.derivatives.Cnb)

        for control_surface in model.control_surfaces.control_surfaces or []:
            control_surface.ed = cls._singleton_to_scalar(control_surface.ed)
            control_surface.CDff = cls._singleton_to_scalar(control_surface.CDff)
            control_surface.CLd = cls._singleton_to_scalar(control_surface.CLd)
            control_surface.CYd = cls._singleton_to_scalar(control_surface.CYd)
            control_surface.Cld = cls._singleton_to_scalar(control_surface.Cld)
            control_surface.Cmd = cls._singleton_to_scalar(control_surface.Cmd)
            control_surface.Cnd = cls._singleton_to_scalar(control_surface.Cnd)
            control_surface.deflection = cls._singleton_to_scalar(control_surface.deflection)

        model.flight_condition.alpha = cls._singleton_to_scalar(model.flight_condition.alpha)
        model.flight_condition.beta = cls._singleton_to_scalar(model.flight_condition.beta)
        model.flight_condition.mach = cls._singleton_to_scalar(model.flight_condition.mach)

        return model

    @staticmethod
    def from_dict(data: dict) -> 'AnalysisModel':
        model = AnalysisModel.from_avl_dict(data)
        return AnalysisModel._flatten_single_point_fields(model)

    @staticmethod
    def from_avl_dict(data: dict) -> 'AnalysisModel':
        """
        Create an AvlAnalysisModel instance from a flat dictionary structure.

        Args:
            data: A dictionary containing all the AVL analysis results

        Returns:
            An instance of AvlAnalysisModel with all submodels populated
        """
        # Create submodels
        reference = AvlReferenceModel(
            Bref=data['Bref'],
            Cref=data['Cref'],
            Sref=data['Sref'],
            Xref=data['Xref'],
            Yref=data['Yref'],
            Zref=data['Zref'],
            Xnp=[data['Xnp']],
            Xnp_lat=[data['Xref'] - (data["Cnb"] * (data['Bref'] / data["CYb"]))] if data['CYb'] != 0 else None,
            Strips=data['Strips'],
            Surfaces=data['Surfaces'],
            Vortices=data['Vortices']
        )

        forces = AvlForceModel(
            F_b=[data['F_b']],
            F_g=[data['F_g']],
            F_w=[data['F_w']],
            L=[data['L']],
            D=[data['D']],
            Y=[data['Y']]
        )

        moments = AvlMomentModel(
            M_b=[data['M_b']],
            M_g=[data['M_g']],
            M_w=[data['M_w']],
            l_b=[data['l_b']],
            m_b=[data['m_b']],
            n_b=[data['n_b']]
        )

        coefficients = AvlCoefficientsModel(
            CL=[data['CL']],
            CD=[data['CD']],
            CY=[data['CY']],
            CZ=[data['CZ']],
            CX=[data['CX']],
            Cl=[data['Cl']],
            Cl_prime=[data["Cl'"]],
            Cm=[data['Cm']],
            Cn=[data['Cn']],
            Cn_prime=[data["Cn'"]],
            CDff=[data['CDff']],
            CDind=[data['CDind']],
            CDvis=[data['CDvis']],
            CLff=[data['CLff']],
            CYff=[data['CYff']],
            e=[data['e']]
        )

        derivatives = AvlDerivativesModel(
            CLa=[data['CLa']],
            CLb=[data['CLb']],
            CLp=[data['CLp']],
            CLq=[data['CLq']],
            CLr=[data['CLr']],
            CYa=[data['CYa']],
            CYb=[data['CYb']],
            CYp=[data['CYp']],
            CYq=[data['CYq']],
            CYr=[data['CYr']],
            Cla=[data['Cla']],
            Clb=[data['Clb']],
            Clp=[data['Clp']],
            Clq=[data['Clq']],
            Clr=[data['Clr']],
            Cma=[data['Cma']],
            Cmb=[data['Cmb']],
            Cmp=[data['Cmp']],
            Cmq=[data['Cmq']],
            Cmr=[data['Cmr']],
            Cna=[data['Cna']],
            Cnb=[data['Cnb']],
            Cnp=[data['Cnp']],
            Cnq=[data['Cnq']],
            Cnr=[data['Cnr']],
            Clb_Cnr_div_Clr_Cnb=[data['Clb Cnr / Clr Cnb']]
        )

        # Extract control surface names from keys between 'e' and 'CLa'
        control_surface_indices = set()
        control_surface_names = {}

        # Find all control surface indices
        for key in data.keys():
            if any(key.startswith(prefix) and key[len(prefix):].isdigit() for prefix in ['ed', 'CDff', 'CL', 'CY', 'Cl', 'Cm', 'Cn']):
                if key.startswith('ed'):  # Use 'ed' keys to identify control surfaces
                    index = key[2:]  # Extract the index (e.g., '01', '02')
                    control_surface_indices.add(index)

        # Sort indices to maintain order
        control_surface_indices = sorted(control_surface_indices)

        # Find control surface names from keys between 'e' and 'CLa'
        # Get all keys in the data dictionary
        keys = list(data.keys())

        # Find the indices of 'e' and 'CLa' in the keys list
        try:
            e_index = keys.index('e')
            cla_index = keys.index('CLa')

            # Extract the keys between 'e' and 'CLa'
            potential_names = keys[e_index+1:cla_index]

            # Map control surface indices to names
            # The issue description states that the numbering is ordered
            # So we'll map the first name to the first index, second name to second index, etc.
            if len(potential_names) >= len(control_surface_indices):
                for i, index in enumerate(control_surface_indices):
                    if i < len(potential_names):
                        control_surface_names[index] = potential_names[i]
        except ValueError:
            # If 'e' or 'CLa' is not found, we'll use default names
            pass

        # Create control surface models
        control_surface_list = []
        for index in control_surface_indices:
            # Use the mapped name if available, otherwise use a default name
            name = control_surface_names.get(index, f"control_surface_{index}")

            # Create the control surface model
            control_surface = AvlSingleControlSurfaceModel(
                name=name,
                ed=[data[f'ed{index}']],
                CDff=[data[f'CDffd{index}']],
                CLd=[data[f'CLd{index}']],
                CYd=[data[f'CYd{index}']],
                Cld=[data[f'Cld{index}']],
                Cmd=[data[f'Cmd{index}']],
                Cnd=[data[f'Cnd{index}']],
                deflection=[data[name]]
            )
            control_surface_list.append(control_surface)

        control_surfaces = AvlControlSurfaceModel(
            control_surfaces=control_surface_list
        )

        flight_condition = AvlFlightConditionModel(
            alpha=[data['alpha']],
            beta=data['beta'],
            mach=data['mach'],
            p=data['p'],
            q=data['q'],
            r=data['r'],
            p_prime_b_div_2V=data["p'b/2V"],
            pb_div_2V=data['pb/2V'],
            qc_div_2V=data['qc/2V'],
            r_prime_b_div_2V=data["r'b/2V"],
            rb_div_2V=data['rb/2V']
        )

        # Create main model
        return AnalysisModel(
            method='avl',
            reference=reference,
            forces=forces,
            moments=moments,
            coefficients=coefficients,
            derivatives=derivatives,
            control_surfaces=control_surfaces,
            flight_condition=flight_condition
        )

    @staticmethod
    def from_abu_dict(data: dict, asb_airplan: asb.Airplane, operating_point = None, methode: Literal['aerobuildup', 'vortex_lattice'] = 'aerobuildup') -> 'AnalysisModel':
        """Create an AvlAnalysisModel from ABU-style dict, mapping provided values and using None for missing."""
        # Reference
        x_np = data.get('x_np')
        if isinstance(x_np, (list, tuple)):
            xnp_val = x_np[0] if x_np else None
        else:
            xnp_val = x_np

        x_np_lat = data.get('x_np_lateral')
        if isinstance(x_np_lat, (list, tuple)):
            xnp_lat_val = x_np_lat[0] if x_np_lat else None
        else:
            xnp_lat_val = x_np_lat

        reference = AvlReferenceModel(
            Bref=asb_airplan.b_ref,
            Cref=asb_airplan.c_ref,
            Sref=asb_airplan.s_ref,
            Xref=asb_airplan.xyz_ref[0],
            Yref=asb_airplan.xyz_ref[1],
            Zref=asb_airplan.xyz_ref[2],
            Xnp=[xnp_val] if isinstance(xnp_val, float) else x_np,
            Xnp_lat=[xnp_lat_val] if isinstance(xnp_lat_val, float) else xnp_lat_val,
            Strips=None,
            Surfaces=None,
            Vortices=None
        )
        # Forces
        f_b_raw = data.get('F_b')
        if f_b_raw is not None and len(f_b_raw) == 3 and type(f_b_raw[0]) is np.float64:
            f_b = [f_b_raw]
        elif f_b_raw is not None and len(f_b_raw) == 3:
            f_b = [(f_b_raw[0][0], f_b_raw[1][0], f_b_raw[2][0])]
        else:
            f_b = None
        f_g_raw = data.get('F_g')
        if f_g_raw is not None and len(f_g_raw) == 3 and type(f_g_raw[0]) is np.float64:
            f_g = [f_g_raw]
        elif f_g_raw is not None and len(f_g_raw) == 3:
            f_g = [(f_g_raw[0][0], f_g_raw[1][0], f_g_raw[2][0])]
        else:
            f_g = None
        f_w_raw = data.get('F_w')
        if f_w_raw is not None and len(f_w_raw) == 3 and type(f_w_raw[0]) is np.float64:
            f_w = [f_w_raw]
        elif f_w_raw is not None and len(f_w_raw) == 3:
            f_w = [(f_w_raw[0][0], f_w_raw[1][0], f_w_raw[2][0])]
        else:
            f_w = None

        def to_list(val):
            if isinstance(val, (list, tuple, np.ndarray)):
                vals = val
            elif val is not None:
                vals = [val]
            else:
                vals = None
            return vals

        forces = AvlForceModel(
            F_b=f_b,
            F_g=f_g,
            F_w=f_w,
            L=to_list(data.get('L')),
            D=to_list(data.get('D')),
            Y=to_list(data.get('Y'))
        )
        # Moments
        m_b_raw = data.get('M_b')
        if m_b_raw is not None and len(m_b_raw) == 3 and type(m_b_raw[0]) is np.float64:
            m_b = [m_b_raw]
        elif m_b_raw is not None and len(m_b_raw) == 3:
            m_b = [(m_b_raw[0][0], m_b_raw[1][0], m_b_raw[2][0])]
        else:
            m_b = None
        m_g_raw = data.get('M_g')
        if m_g_raw is not None and len(m_g_raw) == 3 and type(m_g_raw[0]) is np.float64:
            m_g = [m_g_raw]
        elif m_g_raw is not None and len(m_g_raw) == 3:
            m_g = [(m_g_raw[0][0], m_g_raw[1][0], m_g_raw[2][0])]
        else:
            m_g = None
        m_w_raw = data.get('M_w')
        if m_w_raw is not None and len(m_w_raw) == 3 and type(m_w_raw[0]) is np.float64:
            m_w = [m_w_raw]
        elif m_w_raw is not None and len(m_w_raw) == 3:
            m_w = [(m_w_raw[0][0], m_w_raw[1][0], m_w_raw[2][0])]
        else:
            m_w = None
        moments = AvlMomentModel(
            M_b=m_b,
            M_g=m_g,
            M_w=m_w,
            l_b=to_list(data.get('l_b')),
            m_b=to_list(data.get('m_b')),
            n_b=to_list(data.get('n_b'))
        )
        # Coefficients

        coefficients = AvlCoefficientsModel(
            CL=to_list(data.get('CL')),
            CD=to_list(data.get('CD')),
            CY=to_list(data.get('CY')),
            CZ=to_list(data.get('CZ')),
            CX=to_list(data.get('CX')),
            Cl=to_list(data.get('Cl')),
            Cl_prime=to_list(data.get("Cl'")),
            Cm=to_list(data.get('Cm')),
            Cn=to_list(data.get('Cn')),
            Cn_prime=to_list(data.get("Cn'")),
            CDff=to_list(data.get('CDff')),
            CDind=to_list(data.get('CDind')),
            CDvis=to_list(data.get('CDvis')),
            CLff=to_list(data.get('CLff')),
            CYff=to_list(data.get('CYff')),
            e=[data.get('wing_aero_components')[0].oswalds_efficiency] if data.get('wing_aero_components') else None,
        )
        # Derivatives
        derivatives = AvlDerivativesModel(
            CLa=to_list(data.get('CLa')),
            CLb=to_list(data.get('CLb')),
            CLp=to_list(data.get('CLp')),
            CLq=to_list(data.get('CLq')),
            CLr=to_list(data.get('CLr')),
            CYa=to_list(data.get('CYa')),
            CYb=to_list(data.get('CYb')),
            CYp=to_list(data.get('CYp')),
            CYq=to_list(data.get('CYq')),
            CYr=to_list(data.get('CYr')),
            Cla=to_list(data.get('Cla')),
            Clb=to_list(data.get('Clb')),
            Clp=to_list(data.get('Clp')),
            Clq=to_list(data.get('Clq')),
            Clr=to_list(data.get('Clr')),
            Cma=to_list(data.get('Cma')),
            Cmb=to_list(data.get('Cmb')),
            Cmp=to_list(data.get('Cmp')),
            Cmq=to_list(data.get('Cmq')),
            Cmr=to_list(data.get('Cmr')),
            Cna=to_list(data.get('Cna')),
            Cnb=to_list(data.get('Cnb')),
            Cnp=to_list(data.get('Cnp')),
            Cnq=to_list(data.get('Cnq')),
            Cnr=to_list(data.get('Cnr')),
            Clb_Cnr_div_Clr_Cnb=None
        )
        # Control Surfaces
        control_surfaces = AvlControlSurfaceModel(control_surfaces=None)
        # Flight Condition
        op_point = data.get('wing_aero_components')[0].op_point if data.get('wing_aero_components') else operating_point
        flight_condition = AvlFlightConditionModel(
            alpha=to_list(op_point.alpha),
            beta=op_point.beta,
            mach=op_point.velocity/347.,
            p=op_point.p,
            q=op_point.q,
            r=op_point.r,
            p_prime_b_div_2V=None,
            pb_div_2V=None,
            qc_div_2V=None,
            r_prime_b_div_2V=None,
            rb_div_2V=None
        )
        return AnalysisModel(
            method=methode,
            reference=reference,
            forces=forces,
            moments=moments,
            coefficients=coefficients,
            derivatives=derivatives,
            control_surfaces=control_surfaces,
            flight_condition=flight_condition
        )


class AircraftSummaryModel(BaseModel):
    aircraft: AircraftModel
    environment: EnvironmentModel
    control_surfaces: ControlSurfacesModel
    wing_geometry: WingGeometryModel
    aerodynamics: AerodynamicsModel
    efficiency: EfficiencyModel
    stability: StabilityModel
