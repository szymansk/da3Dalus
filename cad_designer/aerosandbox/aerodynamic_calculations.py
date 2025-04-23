from typing import List

import numpy as np
from scipy.interpolate import UnivariateSpline
from scipy.optimize import minimize_scalar

def calculate_stall_velocity(CL_max, mass_kg, wing_area_m2, rho=1.225, g=9.81, return_kmh=False):
    """
    Berechnet die Stallgeschwindigkeit (V_stall) eines Flugzeugs.

    Parameter:
    - CL_max: maximaler Auftriebsbeiwert (dimensionless)
    - mass_kg: Masse des Flugzeugs in kg
    - wing_area_m2: Flügelfläche in Quadratmetern
    - rho: Luftdichte in kg/m³ (Standard: 1.225)
    - g: Erdbeschleunigung (Standard: 9.81 m/s²)
    - return_kmh: Falls True, wird zusätzlich die Geschwindigkeit in km/h zurückgegeben

    Rückgabe:
    - V_stall_mps: Stallgeschwindigkeit in m/s
    - V_stall_kmh: (optional) in km/h
    """
    weight_N = mass_kg * g
    V_stall_mps = np.sqrt((2 * weight_N) / (rho * wing_area_m2 * CL_max))

    if return_kmh:
        V_stall_kmh = V_stall_mps * 3.6
        return V_stall_mps, V_stall_kmh
    else:
        return V_stall_mps

def analyze_static_longitudinal_stability(alpha_deg: List[float], Cm: List[float]):
    """
    Analyzes static longitudinal stability based on Cm vs. alpha slope.

    Parameters:
    - alpha_deg: array of angle of attack in degrees
    - Cm: array of pitching moment coefficients

    Returns:
    - result: str indicating stability type
    - slope: float (mean slope dCm/dα)
    """

    # Convert to numpy arrays if not already
    alpha = np.array(alpha_deg)
    Cm = np.array(Cm)

    # Compute slope using linear regression
    coeffs = np.polyfit(alpha, Cm, 1)  # [slope, intercept]
    slope = coeffs[0]

    # Interpret result
    if slope < -0.005:
        result = "Stable (dCm/dα = {:.5f})".format(slope)
    elif slope > 0.005:
        result = "Unstable (dCm/dα = {:.5f})".format(slope)
    else:
        result = "Neutrally Stable (dCm/dα = {:.5f})".format(slope)

    return result, slope

def calculate_cl_max(alpha_deg: List[float], CL: List[float]):
    """
    Estimate CL_max (stall AoA) using spline interpolation.

    Parameters:
    - alpha_deg: list or array of AoA in degrees
    - CL: list or array of lift coefficients

    Returns:
    - stall_alpha: float, estimated angle of attack at stall
    - CL_max: float, maximum lift coefficient
    """
    alpha = np.array(alpha_deg)
    CL = np.array(CL)

    # Fit a smoothing spline to the CL vs alpha data
    spline = UnivariateSpline(alpha, CL, s=0, k=4)  # Cubic spline

    # Find max of the spline function within the AoA range
    result = minimize_scalar(lambda x: -spline(x), bounds=(alpha[0], alpha[-1]), method='bounded')

    stall_alpha = result.x
    CL_max = spline(stall_alpha)

    return stall_alpha, CL_max

def calculate_CL_per_CD_max(alpha_deg: List[float], CL: List[float], CD: List[float]):
    """
    Calculates the maximum lift-to-drag ratio (CL/CD) and the corresponding angle of attack.

    Parameters:
    - alpha_deg: array of angle of attack in degrees
    - CL: array of lift coefficients
    - CD: array of drag coefficients

    Returns:
    - best_aoa: angle of attack (deg) for maximum CL/CD
    - max_LD: maximum lift-to-drag ratio
    """
    alpha_deg = np.array(alpha_deg)
    CL = np.array(CL)
    CD = np.array(CD)

    LD_ratio = CL / CD
    best_idx = np.argmax(LD_ratio)

    best_aoa = alpha_deg[best_idx]
    max_LD = LD_ratio[best_idx]

    return best_aoa, max_LD, CL[best_idx]

def best_range_speed(CL_at_max_LD, mass_kg: float, wing_area_m2: float, rho=1.225, gravity=9.81):
    """
    Calculates the best travel flight velocity (max L/D speed) in m/s.

    Parameters:
    - alpha_deg: array of angle of attack in degrees
    - CL: array of lift coefficients
    - CD: array of drag coefficients
    - mass_kg: mass of the aircraft in kg
    - wing_area_m2: wing area in square meters
    - rho: air density in kg/m³ (default: 1.225)
    - gravity: gravitational acceleration (default: 9.81 m/s²)

    Returns:
    - best_aoa: angle of attack (deg) for best range
    - best_speed: airspeed (m/s)
    - max_LD: maximum L/D ratio
    """
    W = mass_kg * gravity
    V_best = np.sqrt((2 * W) / (rho * wing_area_m2 * CL_at_max_LD))

    return V_best

def estimate_motor_down_and_right_thrust(mass_kg: float,
                                    prop_diameter_inch: float,
                                    wing_span_m: float,
                                    wing_chord_m: float,
                                    wing_area_m2: float,
                                    tail_moment_arm_m: float = 0.5,
                                    motor_mount_offset_m: float = 0.03,
                                    thrust_N: float = None):
    """
    Improved estimation of motor Sturz (down-thrust) and Zug (right-thrust).
    Now includes wing geometry influence.
    """
    import math

    #aspect_ratio = wing_span_m**2 / wing_area_m2
    prop_diameter_m = prop_diameter_inch * 0.0254
    prop_area = math.pi * (prop_diameter_m / 2)**2

    # Estimate propwash influence
    propwash_wing_coverage = min(prop_area / wing_area_m2, 1.0)

    # Estimate thrust-to-weight ratio if not provided
    g = 9.81
    if thrust_N is None:
        # Assume ~1.3x static thrust for typical RC setups
        thrust_N = 1.3 * mass_kg * g

    t2w = thrust_N / (mass_kg * g)

    # Down-thrust scales with pitch-up moment potential
    sturz_deg = 1.5 + 2.0 * (t2w - 1.0) * propwash_wing_coverage
    sturz_deg *= (wing_chord_m / tail_moment_arm_m)
    sturz_deg = min(max(sturz_deg, 1.0), 5.0)

    # Right-thrust scales with prop torque and short moment arm
    lever_ratio = motor_mount_offset_m / tail_moment_arm_m
    zug_deg = 2.0 + 5.0 * lever_ratio
    zug_deg = min(zug_deg, 5.0)

    return round(sturz_deg, 2), round(zug_deg, 2)

def suggest_wing_incidence_angle(
        alpha_range_deg: List[float],
        moment_curve_alpha: List[float],
        current_incidence_deg=0.0,
        cruise_alpha_deg=3.0):
    """
    Suggest an improved wing incidence angle for level trimmed cruise.

    Parameters:
        alpha_range_deg (array-like): Array of angle of attack values [deg]
        moment_curve_alpha (array-like): Corresponding Cm values
        current_incidence_deg (float): Current incidence angle of the wing [deg]
        cruise_alpha_deg (float): Desired angle of attack for efficient cruise [deg]

    Returns:
        new_incidence_deg (float): Suggested new incidence angle [deg]
        trim_alpha_deg (float): Alpha at which Cm ≈ 0
    """
    # Fit a spline to the Cm curve
    alpha_range_deg = np.array(alpha_range_deg)
    moment_curve_alpha = np.array(moment_curve_alpha)
    spline = UnivariateSpline(alpha_range_deg, moment_curve_alpha, s=0)

    # Find alpha where Cm = 0 (trimmed angle of attack)
    trim_alpha_deg = float(spline.roots()[0])  # Closest to zero

    # Incidence correction needed
    delta_incidence = trim_alpha_deg - cruise_alpha_deg
    new_incidence_deg = current_incidence_deg - delta_incidence

    return round(new_incidence_deg, 2), round(trim_alpha_deg, 2)


def compute_derivative(x_array: np.ndarray, y_array: np.ndarray) -> float:
    """
    Compute the first derivative (slope) using linear regression via polyfit.

    Args:
        x_array (np.ndarray): Independent variable (e.g., alpha or beta).
        y_array (np.ndarray): Dependent variable (e.g., Cm or Cl).

    Returns:
        float: Slope (dy/dx)
    """
    coeffs = np.polyfit(x_array, y_array, 1)  # 1st-degree polynomial fit
    slope = float(coeffs[0])
    return slope