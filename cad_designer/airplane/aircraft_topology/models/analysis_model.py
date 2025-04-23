from enum import Enum

from pydantic import BaseModel, Field
from typing import List, Literal


class AircraftModel(BaseModel):
    name: str = Field(..., title="Aircraft Name", description="Name of the aircraft [string]")
    mass_kg: float = Field(..., title="Total Mass", description="Total aircraft mass [kg]")
    wing_area_m2: float = Field(..., title="Wing Area", description="Wing reference area [m²]")
    wing_span_m: float = Field(..., title="Wing Span", description="Wingspan [m]")
    wing_chord_m: float = Field(..., title="Mean Geometric Chord", description="Mean geometric chord of the wing [m]")
    MAC_m: float = Field(..., title="Mean Aerodynamic Chord", description="Mean aerodynamic chord [m]")
    static_margin_in_percent_MAC: float = Field(..., title="Static Margin", description="Static margin as % of MAC [%]")
    NP_m: List[float] = Field(..., title="Neutral Point", description="Neutral point coordinates [m]")
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
    alpha_range_deg: List[float] = Field(..., title="Angle of Attack Range", description="Angle of attack values [deg]")
    F_g_curve_alpha: List[List[float]] = Field(..., title="Geometry Axes Forces", description="Forces in geometry axes [N]")
    F_b_curve_alpha: List[List[float]] = Field(..., title="Body Axes Forces", description="Forces in body axes [N]")
    F_w_curve_alpha: List[List[float]] = Field(..., title="Wind Axes Forces", description="Forces in wind axes [N]")
    M_g_curve_alpha: List[List[float]] = Field(..., title="Geometry Moments", description="Moments about geometry axes [Nm]")
    M_b_curve_alpha: List[List[float]] = Field(..., title="Body Moments", description="Moments about body axes [Nm]")
    M_w_curve_alpha: List[List[float]] = Field(..., title="Wind Moments", description="Moments about wind axes [Nm]")
    L_lift_force_N_curve_alpha: List[float] = Field(..., title="Lift Force", description="Lift force [N]")
    Y_side_force_N_curve_alpha: List[float] = Field(..., title="Side Force", description="Side force [N]")
    D_drag_force_N_curve_alpha: List[float] = Field(..., title="Drag Force", description="Drag force [N]")
    l_b_rolling_moment_Nm_curve_alpha: List[float] = Field(..., title="Rolling Moment", description="Rolling moment [Nm]")
    m_b_pitching_moment_Nm_curve_alpha: List[float] = Field(..., title="Pitching Moment", description="Pitching moment [Nm]")
    n_b_yawing_moment_Nm_curve_alpha: List[float] = Field(..., title="Yawing Moment", description="Yawing moment [Nm]")
    CL_lift_coefficient_curve_alpha: List[float] = Field(..., title="Lift Coefficient", description="Lift coefficient [-]: wind axes")
    CY_sideforce_coefficient_curve_alpha: List[float] = Field(..., title="Sideforce Coefficient", description="Sideforce coefficient [-]: wind axes")
    CD_drag_coefficient_curve_alpha: List[float] = Field(..., title="Drag Coefficient", description="Drag coefficient [-]: wind axes")
    Cl_rolling_moment_curve_alpha: List[float] = Field(..., title="Rolling Coefficient", description="Rolling coefficient [-]: body axes")
    Cm_pitching_moment_curve_alpha: List[float] = Field(..., title="Pitching Coefficient", description="Pitching coefficient [-]: body axes")
    Cn_yawing_moment_curve_alpha: List[float] = Field(..., title="Yawing Coefficient", description="Yawing coefficient [-]: body axes")


class EfficiencyModel(BaseModel):
    masses_kg: List[float] = Field(..., title="Masses", description="List of mass configurations [kg]")
    stall_velocity_m_per_s_curve_masses_kg: List[float] = Field(..., title="Stall Velocities", description="Stall velocity per mass [m/s]")
    travel_velocity_m_per_s_curve_masses_kg: List[float] = Field(..., title="Travel Velocities", description="Travel velocity per mass [m/s]")
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

class AircraftSummaryModel(BaseModel):
    aircraft: AircraftModel
    environment: EnvironmentModel
    control_surfaces: ControlSurfacesModel
    wing_geometry: WingGeometryModel
    aerodynamics: AerodynamicsModel
    efficiency: EfficiencyModel
    stability: StabilityModel
