"""Powertrain Performance Model — T(V), P(V), η_prop(J) curves (gh-615).

Given a brushless motor + propeller polars + battery, computes:
  - T(V): thrust as a function of airspeed
  - P_shaft(V): shaft power as a function of airspeed
  - η_prop(J): propulsive efficiency as a function of advance ratio
  - P_available_w: electrical power ceiling from motor + battery

Motor model — power-limited + efficiency-chain (no Rm):
  Motor winding resistance Rm is not available in the current D-Power catalog
  (only Kv and sometimes Io are provided).  We therefore use a simplified model:
    P_electrical = min(P_battery_max, P_motor_max_elec)
    P_shaft = P_electrical × η_motor
  where η_motor = efficiency_pct/100 if known, else 0.85 default.
  The full QPROP 3-parameter (Kv, Rm, Io) model requires Rm; see follow-up
  ticket for refinement when winding-resistance data is available.

Gear-aware RPM (UAT note, gh-615 comment #3):
  output_kv = kv_rpm_per_volt / (gear_ratio or 1)
  RPM = output_kv × V_battery

Power from current (UAT note, gh-615 comment #3):
  max_electrical_power_w = max_current_a × 3.7 V/cell × cells_lipo_max
  Uses 3.7 V/cell (loaded, not 4.2 V peak) to avoid 13% inflation.

Propeller polars (UAT note, gh-615 comment #4):
  Ct/Cp/Pe are interpolated from APC polar samples vs J.
  Torque is derived from PWR_W / (2π·n), NOT from stored Torque_Nm
  (which loses precision at 3 decimal places for low-RPM rows).
  Ct is clamped at 0 — the slightly-negative tail past zero-thrust is
  ignored; windmilling drag is out of scope for this ticket.
  Extrapolation beyond the dataset J-range emits a warning.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------

RHO_SEA_LEVEL = 1.225  # kg/m³
G = 9.80665  # m/s²
_VOLTS_PER_LIPO_CELL = 3.7  # loaded nominal (NOT 4.2 V peak)
_DEFAULT_ETA_MOTOR = 0.85  # brushless outrunner default


# ---------------------------------------------------------------------------
# Data structures for polar samples
# ---------------------------------------------------------------------------


@dataclass
class PropellerPolarRow:
    """One measurement row from the APC PER3 database.

    Mirrors PropellerPolarSampleModel columns but is a plain dataclass so
    tests can mock it without a DB session.
    """

    rpm: int
    J: float  # advance ratio V/(n·D)
    Ct: float  # thrust coefficient T/(ρ·n²·D⁴)
    Cp: float  # power coefficient P/(ρ·n³·D⁵)
    Pe: Optional[float]  # propulsive efficiency Ct·J/Cp (0 at J=0)
    PWR_W: Optional[float]  # shaft power [W]
    Torque_Nm: Optional[float]  # stored torque — NOT used for physics; see docstring
    Thrust_N: Optional[float]  # stored thrust — NOT used for physics; see docstring


# ---------------------------------------------------------------------------
# Motor / Battery specs (plain dataclasses, sourced from ComponentModel.specs)
# ---------------------------------------------------------------------------


class MotorSpec(BaseModel):
    """Motor specs sourced from the brushless_motor component catalog.

    Gear-aware: output_kv = kv_rpm_per_volt / (gear_ratio or 1).
    The raw kv_rpm_per_volt must never be used directly for RPM/prop matching
    when gear_ratio > 1 (D-Drive geared motors).
    """

    kv_rpm_per_volt: float = Field(..., gt=0, description="Raw motor KV (before gearbox)")
    gear_ratio: Optional[float] = Field(None, gt=0, description="Gearbox reduction ratio")
    efficiency_pct: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="Motor+gearbox combined efficiency % from datasheet",
    )
    cells_lipo_max: int = Field(..., ge=1, description="Max LiPo cell count")
    io_no_load_a: Optional[float] = Field(None, ge=0, description="No-load current Io [A]")
    max_current_a: Optional[float] = Field(None, gt=0, description="Burst current limit [A]")
    continuous_current_a: Optional[float] = Field(
        None, gt=0, description="Continuous current rating [A]"
    )
    rm_ohm: Optional[float] = Field(
        None,
        gt=0,
        description=(
            "Motor winding (terminal-to-terminal) resistance Rm [Ω]. "
            "When provided, enables the QPROP 3-parameter torque-balance model "
            "(gh-1006); when absent the simplified fixed-RPM model is used."
        ),
    )

    @property
    def uses_qprop_model(self) -> bool:
        """True when enough data is present for the QPROP 3-param model.

        Requires winding resistance Rm. Io defaults to 0 A if not provided
        (an ideal-loss-free no-load assumption), so Rm alone is sufficient
        to unlock the torque-balance solver.
        """
        return self.rm_ohm is not None and self.rm_ohm > 0

    @property
    def kv_si(self) -> float:
        """Motor speed constant in SI: output-shaft rad/s per volt of back-EMF.

        Kv_si = output_kv [rpm/V] × 2π/60. In SI the torque constant Kt = 1/Kv_si
        [Nm/A], which is the basis of the QPROP torque relation Q = (I − I0)/Kv_si.
        """
        return self.output_kv * 2.0 * math.pi / 60.0

    @property
    def output_kv(self) -> float:
        """KV at the output shaft — accounts for gearbox reduction.

        Use this (not kv_rpm_per_volt) for all RPM / propeller matching.
        Gear-blind consumers MUST read output_kv, not kv_rpm_per_volt.
        """
        return self.kv_rpm_per_volt / (self.gear_ratio or 1.0)

    @property
    def eta_motor(self) -> float:
        """Motor + gearbox combined efficiency (0..1)."""
        if self.efficiency_pct is not None:
            return self.efficiency_pct / 100.0
        return _DEFAULT_ETA_MOTOR

    @property
    def max_electrical_power_w(self) -> float:
        """Estimated maximum electrical input power [W].

        Derived from max_current_a × 3.7 V/cell × cells_lipo_max.
        Uses loaded 3.7 V/cell, not peak 4.2 V (UAT note, gh-615 comment #3).
        Tagged as ESTIMATED — not a datasheet-reported value.
        """
        if self.max_current_a is None:
            return float("inf")
        return self.max_current_a * _VOLTS_PER_LIPO_CELL * self.cells_lipo_max

    @property
    def continuous_electrical_power_w(self) -> float:
        """Estimated continuous electrical input power [W].

        Derived from continuous_current_a × 3.7 V/cell × cells_lipo_max.
        Tagged as ESTIMATED.
        """
        i_cont = self.continuous_current_a or self.max_current_a
        if i_cont is None:
            return float("inf")
        return i_cont * _VOLTS_PER_LIPO_CELL * self.cells_lipo_max


class BatterySpec(BaseModel):
    """Battery specs sourced from the battery component catalog."""

    cells: int = Field(..., ge=1, description="LiPo cell count (S)")
    capacity_mah: float = Field(..., gt=0, description="Capacity [mAh]")
    c_rate: Optional[int] = Field(None, gt=0, description="C-rate (discharge rating)")

    @property
    def nominal_voltage_v(self) -> float:
        """Nominal pack voltage [V] at 3.7 V/cell (loaded)."""
        return self.cells * _VOLTS_PER_LIPO_CELL

    @property
    def max_continuous_discharge_w(self) -> float:
        """Max continuous discharge power [W] from C-rate.

        P = capacity_ah × C-rate × V_nominal
        """
        if self.c_rate is None:
            return float("inf")
        capacity_ah = self.capacity_mah / 1000.0
        return capacity_ah * self.c_rate * self.nominal_voltage_v

    @property
    def max_current_a(self) -> float:
        """Max continuous discharge current [A] from C-rate."""
        if self.c_rate is None:
            return float("inf")
        return (self.capacity_mah / 1000.0) * self.c_rate


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class PowertrainPerformanceRequest(BaseModel):
    """Request to compute T(V)/P(V)/η(J) curves for a powertrain."""

    motor: MotorSpec
    battery: BatterySpec
    propeller_diameter_in: float = Field(..., gt=0, description="Propeller diameter [inches]")
    polar_samples: list[PropellerPolarRow] = Field(
        ..., description="Propeller polar rows from DB (all RPMs)"
    )
    v_min_ms: float = Field(0.0, ge=0.0, description="Start of velocity range [m/s]")
    v_max_ms: float = Field(30.0, gt=0.0, description="End of velocity range [m/s]")
    n_points: int = Field(20, ge=1, le=500, description="Number of velocity samples")
    altitude_m: float = Field(0.0, ge=0.0, description="Operating altitude [m]")
    throttle: float = Field(1.0, gt=0.0, le=1.0, description="Throttle fraction (0..1]")

    model_config = {"arbitrary_types_allowed": True}

    @model_validator(mode="after")
    def _v_max_gt_v_min(self) -> "PowertrainPerformanceRequest":
        if self.v_max_ms <= self.v_min_ms:
            raise ValueError(f"v_max_ms ({self.v_max_ms}) must be > v_min_ms ({self.v_min_ms})")
        return self


class PerformanceSample(BaseModel):
    """One point on the T(V)/P(V)/η(J) curve."""

    velocity_ms: float = Field(..., ge=0.0)
    thrust_n: float = Field(..., ge=0.0)
    p_shaft_w: float = Field(..., ge=0.0)
    eta_prop: float = Field(..., ge=0.0, le=1.0)
    J: float = Field(..., ge=0.0, description="Advance ratio V/(n·D)")
    rpm: float = Field(..., ge=0.0)
    estimated: bool = Field(
        True,
        description=(
            "True when power was derived from current×voltage rather than a "
            "directly measured datasheet value."
        ),
    )


class PowertrainPerformanceResponse(BaseModel):
    """Output of compute_performance_curve."""

    samples: list[PerformanceSample] = Field(default_factory=list)
    p_available_w: float = Field(
        0.0,
        ge=0.0,
        description="Electrical power ceiling (min of motor + battery limits) [W]",
    )
    warnings: list[str] = Field(default_factory=list)
    notes: str = Field(
        "",
        description=(
            "Human-readable notes about model simplifications and derived values. "
            "Motor power values are ESTIMATED from current×3.7 V/cell×cells; "
            "not datasheet-reported. Motor model: power-limited + η-chain (no Rm). "
            "See follow-up ticket for QPROP 3-param refinement."
        ),
    )


# ---------------------------------------------------------------------------
# Interpolation helper
# ---------------------------------------------------------------------------


def interpolate_ct_cp_pe(
    samples: list[PropellerPolarRow],
    J: float,
    return_warning: bool = False,
) -> tuple:
    """Interpolate Ct, Cp, Pe at a given advance ratio J.

    Uses all rows that share the nearest RPM to J (or all rows if single RPM
    is supplied). Extrapolation beyond the dataset range emits a warning flag.

    Ct is clamped at 0 — the slightly-negative tail past zero-thrust is
    discarded (UAT note, gh-615 comment #4).

    Parameters
    ----------
    samples : list[PropellerPolarRow]
        Polar rows — may span multiple RPMs.
    J : float
        Advance ratio to interpolate at.
    return_warning : bool
        If True, return a 4-tuple (Ct, Cp, Pe, extrapolation_warning).

    Returns
    -------
    (Ct, Cp, Pe) normally, or (Ct, Cp, Pe, bool) when return_warning=True.
    """
    if not samples:
        result = (0.0, 0.0, 0.0)
        return result + (True,) if return_warning else result

    # Use all rows regardless of RPM — Ct(J) is nearly RPM-independent for standard
    # APC props, so merging across RPMs gives a better-sampled interpolation grid.
    # When actual RPM is unknown (this helper is J-only), merging is the right choice.
    # compute_prop_operating_point and compute_performance_curve each pre-filter by
    # nearest RPM before calling this helper when they know the operating RPM.
    rows = samples

    # Sort by J
    rows_sorted = sorted(rows, key=lambda r: r.J)
    Js = np.array([r.J for r in rows_sorted])
    Cts = np.array([r.Ct for r in rows_sorted])
    Cps = np.array([r.Cp for r in rows_sorted])

    J_min = Js[0]
    J_max = Js[-1]
    extrapolation_warning = (J < J_min) or (J > J_max)

    # Clamp J to dataset range for interpolation
    J_clamp = float(np.clip(J, J_min, J_max))

    Ct_interp = float(np.interp(J_clamp, Js, Cts))
    Cp_interp = float(np.interp(J_clamp, Js, Cps))

    # Clamp Ct at 0 — discard negative-thrust windmilling tail
    Ct_interp = max(Ct_interp, 0.0)

    # Pe = Ct·J/Cp (undefined/0 at J=0)
    if Cp_interp > 0 and J_clamp > 0:
        Pe_interp = Ct_interp * J_clamp / Cp_interp
    else:
        Pe_interp = 0.0

    result = (Ct_interp, Cp_interp, Pe_interp)
    if return_warning:
        return result + (extrapolation_warning,)
    return result


def _air_density(altitude_m: float) -> float:
    """ISA air density approximation [kg/m³]."""
    return RHO_SEA_LEVEL * math.exp(-altitude_m / 8500.0)


# ---------------------------------------------------------------------------
# Prop operating-point solver
# ---------------------------------------------------------------------------


def compute_prop_operating_point(
    samples: list[PropellerPolarRow],
    rpm: float,
    V: float,
    D_m: float,
    altitude_m: float = 0.0,
) -> tuple[float, float, float]:
    """Compute thrust, shaft power, and η_prop at a given RPM and airspeed.

    Torque is derived from PWR_W / (2π·n), NOT from stored Torque_Nm, which
    loses precision at 3 decimal places for low-RPM rows (UAT note, comment #4).

    Parameters
    ----------
    samples : list[PropellerPolarRow]
        Polar rows for this propeller (all RPMs).
    rpm : float
        Propeller rotational speed [RPM].
    V : float
        Airspeed [m/s].
    D_m : float
        Propeller diameter [m].
    altitude_m : float
        Operating altitude for air density correction [m].

    Returns
    -------
    (thrust_n, p_shaft_w, eta_prop)
    """
    rho = _air_density(altitude_m)
    n_rps = rpm / 60.0  # revolutions per second

    # Advance ratio J = V / (n·D)
    if n_rps > 0 and D_m > 0:
        J = V / (n_rps * D_m)
    else:
        J = 0.0

    # Interpolate coefficients from polar data
    # Use rows closest to the requested RPM for better fidelity
    if samples:
        rpms = sorted({s.rpm for s in samples})
        nearest_rpm = min(rpms, key=lambda r: abs(r - rpm))
        rpm_rows = [s for s in samples if s.rpm == nearest_rpm]
    else:
        rpm_rows = samples

    Ct, Cp, Pe = interpolate_ct_cp_pe(rpm_rows, J)

    # Thrust from Ct: T = Ct · ρ · n² · D⁴
    thrust_n = Ct * rho * (n_rps**2) * (D_m**4)
    thrust_n = max(thrust_n, 0.0)  # clamp

    # Shaft power from Cp: P = Cp · ρ · n³ · D⁵
    # This is the correct path — NOT from stored Torque_Nm (UAT note)
    p_shaft_w = Cp * rho * (n_rps**3) * (D_m**5)
    p_shaft_w = max(p_shaft_w, 0.0)

    # η_prop = Pe = Ct·J/Cp (already computed in interpolate_ct_cp_pe)
    eta_prop = Pe
    eta_prop = max(eta_prop, 0.0)

    return thrust_n, p_shaft_w, eta_prop


# ---------------------------------------------------------------------------
# QPROP 3-parameter motor model (gh-1006)
# ---------------------------------------------------------------------------


@dataclass
class QpropOperatingPoint:
    """Solved torque-balance operating point for the QPROP 3-param motor model.

    All quantities are at the (gear-aware) output shaft.
    """

    rpm: float  # operating speed [rpm]
    current_a: float  # motor terminal current I [A]
    torque_nm: float  # shaft torque Q [Nm]
    p_shaft_w: float  # shaft mechanical power Q·ω [W]
    eta_motor: float  # motor electrical→mechanical efficiency (0..1)


def _prop_torque_demand(
    samples: list[PropellerPolarRow],
    rpm: float,
    V_airspeed: float,
    D_m: float,
    rho: float,
) -> float:
    """Propeller absorbed torque [Nm] at a given shaft RPM and airspeed.

    Q_prop = P_prop / ω = Cp·ρ·n³·D⁵ / (2π·n) = Cp·ρ·n²·D⁵ / (2π).
    Cp is interpolated at the advance ratio J = V/(n·D), using the polar
    rows nearest the requested RPM (consistent with compute_prop_operating_point).
    """
    n_rps = rpm / 60.0
    if n_rps <= 0 or D_m <= 0:
        return 0.0

    J = V_airspeed / (n_rps * D_m)

    if samples:
        rpms = sorted({s.rpm for s in samples})
        nearest_rpm = min(rpms, key=lambda r: abs(r - rpm))
        rpm_rows = [s for s in samples if s.rpm == nearest_rpm]
    else:
        rpm_rows = samples

    _ct, cp, _pe = interpolate_ct_cp_pe(rpm_rows, J)
    p_prop = cp * rho * (n_rps**3) * (D_m**5)
    omega = 2.0 * math.pi * n_rps
    if omega <= 0:
        return 0.0
    return p_prop / omega


def solve_qprop_operating_point(
    motor: MotorSpec,
    samples: list[PropellerPolarRow],
    V_terminal: float,
    V_airspeed: float,
    D_m: float,
    altitude_m: float = 0.0,
    max_current_a: Optional[float] = None,
) -> QpropOperatingPoint:
    """Solve Drela's QPROP 3-parameter torque balance for the operating RPM.

    Model (output-shaft frame, Kv_si in rad/s per volt, Kt = 1/Kv_si):

        back-EMF / speed:   ω/Kv_si = V_terminal − I·Rm
        motor torque:       Q_motor(I) = (I − I0) / Kv_si
        prop demand:        Q_prop(n) = Cp·ρ·n²·D⁵ / (2π)
        torque balance:     Q_motor(I) = Q_prop(n)        at the solution

    Eliminating I via the back-EMF relation gives a single monotone equation in
    n; we bracket and bisect on RPM. Motor efficiency at the solution is the
    QPROP form η = (V_terminal − I·Rm)·(I − I0) / (V_terminal·I).

    Parameters
    ----------
    motor : MotorSpec
        Must have rm_ohm set (uses_qprop_model True). Io defaults to 0 A.
    samples : list[PropellerPolarRow]
        Propeller polar rows (all RPMs).
    V_terminal : float
        Voltage at the motor terminals [V] (battery × throttle).
    V_airspeed : float
        Airspeed [m/s] for advance-ratio-dependent torque demand.
    D_m : float
        Propeller diameter [m].
    altitude_m : float
        Operating altitude for air density [m].
    max_current_a : float, optional
        Hard current ceiling [A]; the back-EMF floor caps the search RPM so the
        solution never demands more than this current.

    Returns
    -------
    QpropOperatingPoint
    """
    rm = motor.rm_ohm
    if rm is None or rm <= 0:
        raise ValueError("solve_qprop_operating_point requires motor.rm_ohm > 0")

    kv_si = motor.kv_si  # rad/s per volt
    i0 = motor.io_no_load_a or 0.0
    rho = _air_density(altitude_m)

    def current_for_rpm(rpm: float) -> float:
        """Terminal current implied by the back-EMF relation at this RPM."""
        omega = rpm * 2.0 * math.pi / 60.0
        back_emf = omega / kv_si
        return (V_terminal - back_emf) / rm

    def residual(rpm: float) -> float:
        """Q_motor − Q_prop at this RPM (root → torque balance)."""
        i = current_for_rpm(rpm)
        q_motor = (i - i0) / kv_si
        q_prop = _prop_torque_demand(samples, rpm, V_airspeed, D_m, rho)
        return q_motor - q_prop

    # Upper RPM bound: free-running speed (I=0) where back-EMF == V_terminal.
    rpm_free = V_terminal * kv_si * 60.0 / (2.0 * math.pi)

    # If a current ceiling is set, the back-EMF floor caps the minimum RPM the
    # motor will run at; current rises as RPM falls (more I·Rm drop).
    rpm_lo = 0.0
    if max_current_a is not None:
        # RPM where current_for_rpm == max_current_a
        # back_emf = V_terminal − max_current_a·rm ; rpm = back_emf·kv_si·60/2π
        back_emf_floor = V_terminal - max_current_a * rm
        rpm_at_imax = max(back_emf_floor, 0.0) * kv_si * 60.0 / (2.0 * math.pi)
        rpm_lo = rpm_at_imax

    rpm_hi = rpm_free

    if rpm_hi <= rpm_lo:
        # Degenerate (V_terminal too low or current ceiling binds everywhere).
        rpm_sol = max(rpm_lo, 0.0)
    else:
        # At rpm_hi (free run) I→0 so Q_motor<0<Q_prop → residual<0.
        # At rpm_lo (no/low speed) Q_motor is large and Q_prop→0 → residual>0.
        r_lo = residual(rpm_lo)
        r_hi = residual(rpm_hi)
        if r_lo <= 0:
            # Even at the lowest RPM the motor cannot match prop demand.
            rpm_sol = rpm_lo
        elif r_hi >= 0:
            # Motor over-powers even at free-run bound (no current headroom hit).
            rpm_sol = rpm_hi
        else:
            for _ in range(80):
                rpm_mid = 0.5 * (rpm_lo + rpm_hi)
                r_mid = residual(rpm_mid)
                if r_mid > 0:
                    rpm_lo = rpm_mid
                else:
                    rpm_hi = rpm_mid
            rpm_sol = 0.5 * (rpm_lo + rpm_hi)

    current = max(current_for_rpm(rpm_sol), 0.0)
    omega = rpm_sol * 2.0 * math.pi / 60.0
    torque = max((current - i0) / kv_si, 0.0)
    p_shaft = max(torque * omega, 0.0)

    # QPROP motor efficiency η = (V − I·Rm)(I − I0)/(V·I)
    if V_terminal > 0 and current > 0:
        eta = (V_terminal - current * rm) * (current - i0) / (V_terminal * current)
        eta = float(min(max(eta, 0.0), 1.0))
    else:
        eta = 0.0

    return QpropOperatingPoint(
        rpm=rpm_sol,
        current_a=current,
        torque_nm=torque,
        p_shaft_w=p_shaft,
        eta_motor=eta,
    )


# ---------------------------------------------------------------------------
# Main curve computation
# ---------------------------------------------------------------------------


def compute_performance_curve(
    request: PowertrainPerformanceRequest,
) -> PowertrainPerformanceResponse:
    """Compute T(V), P_shaft(V), η_prop(J) curves for a powertrain.

    Motor model (simplified power-limited + η-chain, no Rm):
      1. Battery voltage: V_bat = cells × 3.7 V (loaded nominal, not peak)
      2. RPM from output shaft KV: n = output_kv × V_bat × throttle
      3. P_available_elec = min(motor_max_elec, battery_discharge_max)
      4. P_shaft_max = P_available_elec × η_motor
      5. For each velocity V:
         a. J = V / (n·D)
         b. Ct, Cp, Pe = interpolate from polars
         c. T = Ct·ρ·n²·D⁴ (clamped ≥ 0)
         d. P_shaft = min(Cp·ρ·n³·D⁵, P_shaft_max)  — power ceiling
         e. η_prop = Pe (J-dependent, not flat scalar)

    Simplification note (gh-615):
      No Rm (winding resistance) — can't solve the full QPROP voltage/current
      operating point. RPM is fixed at output_kv × V_battery rather than
      solving for the torque-balance equilibrium. A follow-up ticket will
      refine this with Rm when D-Power publishes resistance data.

    Parameters
    ----------
    request : PowertrainPerformanceRequest

    Returns
    -------
    PowertrainPerformanceResponse
    """
    motor = request.motor
    battery = request.battery
    warnings: list[str] = []

    # --- Battery voltage (loaded, 3.7 V/cell) ---
    V_bat = battery.nominal_voltage_v  # cells × 3.7 V

    # --- Operating RPM (gear-aware output_kv × V_bat × throttle) ---
    prop_rpm = motor.output_kv * V_bat * request.throttle

    # --- Propeller geometry ---
    D_m = request.propeller_diameter_in * 0.0254  # inches → metres

    # --- Power ceiling ---
    p_motor_max_elec = motor.max_electrical_power_w
    p_battery_max = battery.max_continuous_discharge_w

    # Take the tighter constraint
    p_available_elec = min(p_motor_max_elec, p_battery_max)
    if math.isinf(p_available_elec):
        # Both limits unknown — use a conservative 500 W placeholder
        p_available_elec = V_bat * (
            battery.max_current_a if not math.isinf(battery.max_current_a) else 100.0
        )
        warnings.append(
            "Motor current limit not specified — power ceiling estimated from battery C-rate only."
        )

    p_shaft_max = p_available_elec * motor.eta_motor

    # Warn if prop_rpm is zero (degenerate)
    if prop_rpm <= 0:
        warnings.append("Computed RPM is zero — check motor KV and battery voltage.")
        samples_out = []
        for V in np.linspace(request.v_min_ms, request.v_max_ms, request.n_points):
            samples_out.append(
                PerformanceSample(
                    velocity_ms=float(V),
                    thrust_n=0.0,
                    p_shaft_w=0.0,
                    eta_prop=0.0,
                    J=0.0,
                    rpm=0.0,
                )
            )
        return PowertrainPerformanceResponse(
            samples=samples_out,
            p_available_w=0.0,
            warnings=warnings,
        )

    # Check if power ceiling is very low (infeasibility check)
    if p_shaft_max < 0.1:
        warnings.append(
            f"Motor shaft power ceiling is very low ({p_shaft_max:.2f} W) — "
            "powertrain may be infeasible for any useful thrust."
        )

    # --- Velocity sweep ---
    velocities = np.linspace(request.v_min_ms, request.v_max_ms, request.n_points)
    rho = _air_density(request.altitude_m)
    n_rps = prop_rpm / 60.0

    # gh-1006: when winding resistance Rm is available, solve the QPROP
    # 3-parameter torque balance per velocity point (RPM is load-dependent)
    # instead of the fixed-RPM approximation.  V_terminal = battery × throttle.
    use_qprop = motor.uses_qprop_model
    v_terminal = V_bat * request.throttle
    # Current ceiling for the back-EMF floor (motor burst limit if known).
    i_ceiling = motor.max_current_a

    samples_out: list[PerformanceSample] = []

    # Extrapolation tracking
    extrapolation_seen = False

    for V in velocities:
        V_f = float(V)

        if use_qprop:
            op = solve_qprop_operating_point(
                motor=motor,
                samples=request.polar_samples,
                V_terminal=v_terminal,
                V_airspeed=V_f,
                D_m=D_m,
                altitude_m=request.altitude_m,
                max_current_a=i_ceiling,
            )
            point_rpm = op.rpm
            point_n_rps = point_rpm / 60.0
            estimated_flag = False
        else:
            point_rpm = prop_rpm
            point_n_rps = n_rps
            estimated_flag = True

        # Advance ratio at the (possibly load-dependent) operating RPM
        J = V_f / (point_n_rps * D_m) if (point_n_rps > 0 and D_m > 0) else 0.0

        # Get coefficients from polar, selecting closest RPM group
        if request.polar_samples:
            rpms = sorted({s.rpm for s in request.polar_samples})
            nearest_rpm = min(rpms, key=lambda r: abs(r - point_rpm))
            rpm_rows = [s for s in request.polar_samples if s.rpm == nearest_rpm]
        else:
            rpm_rows = request.polar_samples

        Ct, Cp, Pe, ext_warn = interpolate_ct_cp_pe(rpm_rows, J, return_warning=True)
        if ext_warn:
            extrapolation_seen = True

        # Thrust: T = Ct · ρ · n² · D⁴  (clamped ≥ 0)
        thrust_n = max(Ct * rho * (point_n_rps**2) * (D_m**4), 0.0)

        if use_qprop:
            # Shaft power comes from the solved torque balance (Q·ω); already
            # consistent with Cp·ρ·n³·D⁵ at the solution RPM.
            p_shaft_w = float(max(op.p_shaft_w, 0.0))
        else:
            # Shaft power from Cp: P = Cp · ρ · n³ · D⁵  (clamped ≤ P_shaft_max)
            p_shaft_uncapped = Cp * rho * (point_n_rps**3) * (D_m**5)
            p_shaft_w = float(np.clip(p_shaft_uncapped, 0.0, p_shaft_max))

        # η_prop from Pe (J-dependent — NOT the flat 0.65 scalar)
        eta_prop = float(np.clip(Pe, 0.0, 1.0))

        samples_out.append(
            PerformanceSample(
                velocity_ms=V_f,
                thrust_n=round(thrust_n, 4),
                p_shaft_w=round(p_shaft_w, 4),
                eta_prop=round(eta_prop, 4),
                J=round(J, 6),
                rpm=round(point_rpm, 1),
                estimated=estimated_flag,
            )
        )

    if extrapolation_seen:
        warnings.append(
            "Some velocity samples required advance-ratio extrapolation beyond the "
            "polar dataset range. Results at those points are less reliable."
        )

    if use_qprop:
        notes = (
            "Motor model: QPROP 3-parameter torque balance (gh-1006) — "
            f"Kv={motor.output_kv:.0f} rpm/V, Rm={motor.rm_ohm:.4g} Ω, "
            f"Io={motor.io_no_load_a or 0.0:.3g} A. "
            "Operating RPM solved per velocity from V_terminal = I·Rm + ω/Kv with "
            "shaft torque Q = (I − Io)/Kv and motor η = (V−I·Rm)(I−Io)/(V·I). "
            "These values are physics-solved (not current×voltage estimates)."
        )
    else:
        notes = (
            "Motor power values are ESTIMATED from max_current_a × 3.7 V/cell × cells_lipo_max "
            "(loaded voltage, not 4.2 V peak). "
            f"Motor η = {motor.eta_motor:.2f} ({'from efficiency_pct' if motor.efficiency_pct is not None else 'default 0.85'}). "
            "RPM model: output_kv × V_battery × throttle (simplified; no Rm torque-balance). "
            "Provide winding resistance (rm_ohm) to enable the QPROP 3-param refinement."
        )

    return PowertrainPerformanceResponse(
        samples=samples_out,
        p_available_w=round(p_available_elec, 2),
        warnings=warnings,
        notes=notes,
    )
