from enum import Enum

from pydantic import BaseModel, Field
from typing import List, Literal, Tuple, Union


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

class AvlReferenceModel(BaseModel):
    Bref: float = Field(..., title="Reference Span", description="Reference span [m]")
    Cref: float = Field(..., title="Reference Chord", description="Reference chord [m]")
    Sref: float = Field(..., title="Reference Area", description="Reference area [m²]")
    Xref: float = Field(..., title="X Reference", description="X reference location [m]")
    Yref: float = Field(..., title="Y Reference", description="Y reference location [m]")
    Zref: float = Field(..., title="Z Reference", description="Z reference location [m]")
    Xnp: float = Field(..., title="Neutral Point", description="Neutral point location [m]")
    Strips: float = Field(..., title="Strip Count", description="Number of strips in the model [-]")
    Surfaces: float = Field(..., title="Surface Count", description="Number of surfaces in the model [-]")
    Vortices: float = Field(..., title="Vortex Count", description="Number of vortices in the model [-]")

class AvlForceModel(BaseModel):
    F_b: Tuple[float, float, float] = Field(..., title="Body Axes Forces", description="Forces in body axes [N]")
    F_g: Tuple[float, float, float] = Field(..., title="Geometry Axes Forces", description="Forces in geometry axes [N]")
    F_w: List[float] = Field(..., title="Wind Axes Forces", description="Forces in wind axes [N]")
    L: float = Field(..., title="Lift Force", description="Lift force [N]")
    D: float = Field(..., title="Drag Force", description="Drag force [N]")
    Y: float = Field(..., title="Side Force", description="Side force [N]")

class AvlMomentModel(BaseModel):
    M_b: List[float] = Field(..., title="Body Moments", description="Moments about body axes [Nm]")
    M_g: Tuple[float, float, float] = Field(..., title="Geometry Moments", description="Moments about geometry axes [Nm]")
    M_w: List[float] = Field(..., title="Wind Moments", description="Moments about wind axes [Nm]")
    l_b: float = Field(..., title="Body Roll Moment", description="Roll moment in body axes [Nm]")
    m_b: float = Field(..., title="Body Pitch Moment", description="Pitch moment in body axes [Nm]")
    n_b: float = Field(..., title="Body Yaw Moment", description="Yaw moment in body axes [Nm]")

class AvlCoefficientsModel(BaseModel):
    CL: float = Field(..., title="Lift Coefficient", description="Total lift coefficient [-]")
    CD: float = Field(..., title="Drag Coefficient", description="Total drag coefficient [-]")
    CY: float = Field(..., title="Y-Force Coefficient", description="Y-axis force coefficient [-]")
    CZ: float = Field(..., title="Z-Force Coefficient", description="Z-axis force coefficient [-]")
    CX: float = Field(..., title="X-Force Coefficient", description="X-axis force coefficient [-]")
    Cl: float = Field(..., title="Roll Moment Coefficient", description="Roll moment coefficient [-]")
    Cl_prime: float = Field(..., title="Roll Moment Prime", description="Roll moment coefficient prime [-]")#, alias="Cl'")
    Cm: float = Field(..., title="Pitch Moment Coefficient", description="Pitch moment coefficient [-]")
    Cn: float = Field(..., title="Yaw Moment Coefficient", description="Yaw moment coefficient [-]")
    Cn_prime: float = Field(..., title="Yaw Moment Prime", description="Yaw moment coefficient prime [-]")#, alias="Cn'")
    CDff: float = Field(..., title="Form Factor Drag", description="Form factor drag coefficient [-]")
    CDind: float = Field(..., title="Induced Drag", description="Induced drag coefficient [-]")
    CDvis: float = Field(..., title="Viscous Drag", description="Viscous drag coefficient [-]")
    CLff: float = Field(..., title="Form Factor Lift", description="Form factor lift coefficient [-]")
    CYff: float = Field(..., title="Form Factor Side Force", description="Form factor side force coefficient [-]")
    e: float = Field(..., title="Oswald Efficiency", description="Oswald efficiency factor [-]")

class AvlDerivativesModel(BaseModel):
    CLa: float = Field(..., title="Lift Curve Slope", description="Lift curve slope [1/rad]")
    CLb: float = Field(..., title="Lift-Sideslip Derivative", description="Lift coefficient derivative with sideslip [1/rad]")
    CLp: float = Field(..., title="Roll Damping", description="Roll damping derivative [1/rad]")
    CLq: float = Field(..., title="Pitch Rate Lift", description="Pitch rate lift derivative [1/rad]")
    CLr: float = Field(..., title="Yaw Rate Lift", description="Yaw rate lift derivative [1/rad]")
    CYa: float = Field(..., title="Side Force-Alpha", description="Side force derivative with alpha [1/rad]")
    CYb: float = Field(..., title="Side Force-Beta", description="Side force derivative with beta [1/rad]")
    CYp: float = Field(..., title="Roll Rate Side Force", description="Roll rate side force derivative [1/rad]")
    CYq: float = Field(..., title="Pitch Rate Side Force", description="Pitch rate side force derivative [1/rad]")
    CYr: float = Field(..., title="Yaw Rate Side Force", description="Yaw rate side force derivative [1/rad]")
    Cla: float = Field(..., title="Roll-Alpha Derivative", description="Roll moment derivative with alpha [1/rad]")
    Clb: float = Field(..., title="Roll-Beta Derivative", description="Roll moment derivative with beta [1/rad]")
    Clp: float = Field(..., title="Roll Damping", description="Roll damping derivative [1/rad]")
    Clq: float = Field(..., title="Pitch Rate Roll", description="Pitch rate roll derivative [1/rad]")
    Clr: float = Field(..., title="Yaw Rate Roll", description="Yaw rate roll derivative [1/rad]")
    Cma: float = Field(..., title="Pitch-Alpha Derivative", description="Pitch moment derivative with alpha [1/rad]")
    Cmb: float = Field(..., title="Pitch-Beta Derivative", description="Pitch moment derivative with beta [1/rad]")
    Cmp: float = Field(..., title="Roll Rate Pitch", description="Roll rate pitch derivative [1/rad]")
    Cmq: float = Field(..., title="Pitch Damping", description="Pitch damping derivative [1/rad]")
    Cmr: float = Field(..., title="Yaw Rate Pitch", description="Yaw rate pitch derivative [1/rad]")
    Cna: float = Field(..., title="Yaw-Alpha Derivative", description="Yaw moment derivative with alpha [1/rad]")
    Cnb: float = Field(..., title="Yaw-Beta Derivative", description="Yaw moment derivative with beta [1/rad]")
    Cnp: float = Field(..., title="Roll Rate Yaw", description="Roll rate yaw derivative [1/rad]")
    Cnq: float = Field(..., title="Pitch Rate Yaw", description="Pitch rate yaw derivative [1/rad]")
    Cnr: float = Field(..., title="Yaw Damping", description="Yaw damping derivative [1/rad]")
    Clb_Cnr_div_Clr_Cnb: float = Field(..., title="Roll-Yaw Coupling", description="Roll-yaw coupling parameter [-]")#, alias="Clb Cnr / Clr Cnb")

class AvlSingleControlSurfaceModel(BaseModel):
    name: str = Field(..., title="Control Surface Name", description="Name of the control surface")
    ed: float = Field(..., title="Control Surface Efficiency", description="Control surface efficiency [-]")
    CDff: float = Field(..., title="Control Surface Drag", description="Control surface drag contribution [-]")
    CLd: float = Field(..., title="Control Surface Lift", description="Control surface lift contribution [-]")
    CYd: float = Field(..., title="Control Surface Side Force", description="Control surface side force contribution [-]")
    Cld: float = Field(..., title="Control Surface Roll", description="Control surface roll contribution [-]")
    Cmd: float = Field(..., title="Control Surface Pitch", description="Control surface pitch contribution [-]")
    Cnd: float = Field(..., title="Control Surface Yaw", description="Control surface yaw contribution [-]")

class AvlControlSurfaceModel(BaseModel):
    aileron: float = Field(..., title="Aileron Deflection", description="Aileron deflection angle [deg]")
    flaps: float = Field(..., title="Flap Setting", description="Flap setting [0-1]")
    control_surfaces: List[AvlSingleControlSurfaceModel] = Field(default_factory=list, title="Control Surfaces", description="List of control surfaces")

class AvlFlightConditionModel(BaseModel):
    alpha: float = Field(..., title="Angle of Attack", description="Angle of attack [deg]")
    beta: float = Field(..., title="Sideslip Angle", description="Sideslip angle [deg]")
    mach: float = Field(..., title="Mach Number", description="Mach number [-]")
    p: float = Field(..., title="Roll Rate", description="Roll rate [rad/s]")
    q: float = Field(..., title="Pitch Rate", description="Pitch rate [rad/s]")
    r: float = Field(..., title="Yaw Rate", description="Yaw rate [rad/s]")
    p_prime_b_div_2V: float = Field(..., title="Normalized Roll Acceleration", description="Normalized roll acceleration [-]")#, alias="p'b/2V")
    pb_div_2V: float = Field(..., title="Normalized Roll Rate", description="Normalized roll rate [-]")#, alias="pb/2V")
    qc_div_2V: float = Field(..., title="Normalized Pitch Rate", description="Normalized pitch rate [-]")#, alias="qc/2V")
    r_prime_b_div_2V: float = Field(..., title="Normalized Yaw Acceleration", description="Normalized yaw acceleration [-]")#, alias="r'b/2V")
    rb_div_2V: float = Field(..., title="Normalized Yaw Rate", description="Normalized yaw rate [-]")#, alias="rb/2V")

class AvlAnalysisModel(BaseModel):
    reference: AvlReferenceModel
    forces: AvlForceModel
    moments: AvlMomentModel
    coefficients: AvlCoefficientsModel
    derivatives: AvlDerivativesModel
    control_surfaces: AvlControlSurfaceModel
    flight_condition: AvlFlightConditionModel

    @staticmethod
    def from_dict(data: dict) -> 'AvlAnalysisModel':
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
            Xnp=data['Xnp'],
            Strips=data['Strips'],
            Surfaces=data['Surfaces'],
            Vortices=data['Vortices']
        )

        forces = AvlForceModel(
            F_b=data['F_b'],
            F_g=data['F_g'],
            F_w=data['F_w'],
            L=data['L'],
            D=data['D'],
            Y=data['Y']
        )

        moments = AvlMomentModel(
            M_b=data['M_b'],
            M_g=data['M_g'],
            M_w=data['M_w'],
            l_b=data['l_b'],
            m_b=data['m_b'],
            n_b=data['n_b']
        )

        coefficients = AvlCoefficientsModel(
            CL=data['CL'],
            CD=data['CD'],
            CY=data['CY'],
            CZ=data['CZ'],
            CX=data['CX'],
            Cl=data['Cl'],
            Cl_prime=data["Cl'"],
            Cm=data['Cm'],
            Cn=data['Cn'],
            Cn_prime=data["Cn'"],
            CDff=data['CDff'],
            CDind=data['CDind'],
            CDvis=data['CDvis'],
            CLff=data['CLff'],
            CYff=data['CYff'],
            e=data['e']
        )

        derivatives = AvlDerivativesModel(
            CLa=data['CLa'],
            CLb=data['CLb'],
            CLp=data['CLp'],
            CLq=data['CLq'],
            CLr=data['CLr'],
            CYa=data['CYa'],
            CYb=data['CYb'],
            CYp=data['CYp'],
            CYq=data['CYq'],
            CYr=data['CYr'],
            Cla=data['Cla'],
            Clb=data['Clb'],
            Clp=data['Clp'],
            Clq=data['Clq'],
            Clr=data['Clr'],
            Cma=data['Cma'],
            Cmb=data['Cmb'],
            Cmp=data['Cmp'],
            Cmq=data['Cmq'],
            Cmr=data['Cmr'],
            Cna=data['Cna'],
            Cnb=data['Cnb'],
            Cnp=data['Cnp'],
            Cnq=data['Cnq'],
            Cnr=data['Cnr'],
            Clb_Cnr_div_Clr_Cnb=data['Clb Cnr / Clr Cnb']
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
                ed=data[f'ed{index}'],
                CDff=data[f'CDffd{index}'],
                CLd=data[f'CLd{index}'],
                CYd=data[f'CYd{index}'],
                Cld=data[f'Cld{index}'],
                Cmd=data[f'Cmd{index}'],
                Cnd=data[f'Cnd{index}']
            )
            control_surface_list.append(control_surface)

        control_surfaces = AvlControlSurfaceModel(
            aileron=data['aileron'],
            flaps=data['flaps'],
            control_surfaces=control_surface_list
        )

        flight_condition = AvlFlightConditionModel(
            alpha=data['alpha'],
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
        return AvlAnalysisModel(
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
