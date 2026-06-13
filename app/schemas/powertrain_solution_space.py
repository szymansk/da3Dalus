"""Pydantic v2 schemas for the powertrain solution-space endpoint (gh-975).

Public surface
--------------
SolutionSpaceAssumptions   — overridable inputs with documented defaults
SolutionRow                — one row per cell-count S, spanning the η_prop band
FeasibleRegion             — capacity floor and C-rate floor curve per cell-count
ShoppingSpec               — minimum-spec summary for copy-paste shopping
PowertrainSolutionSpaceResponse — full endpoint response
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field


class SolutionSpaceAssumptions(BaseModel):
    """Tunable assumptions for the solution-space computation.

    All fields have spec defaults. Pass any subset to override.
    """

    cell_counts: list[int] = Field(
        default=[2, 3, 4, 6],
        description="LiPo cell counts to evaluate (e.g. [2, 3, 4, 6])",
    )
    eta_prop_lo: float = Field(
        default=0.65,
        ge=0.01,
        le=0.99,
        description="Lower bound of propeller efficiency band",
    )
    eta_prop_hi: float = Field(
        default=0.78,
        ge=0.01,
        le=0.99,
        description="Upper bound of propeller efficiency band",
    )
    eta_motor: float = Field(
        default=0.85,
        ge=0.01,
        le=0.99,
        description="Motor efficiency (brushless outrunner typical)",
    )
    eta_esc: float = Field(
        default=0.94,
        ge=0.01,
        le=0.99,
        description="ESC efficiency (modern ESC typical)",
    )
    dod: float = Field(
        default=0.80,
        ge=0.01,
        le=1.0,
        description="Depth of discharge (usable fraction of rated capacity)",
    )
    esc_margin: float = Field(
        default=1.4,
        ge=1.0,
        description="ESC current rating margin multiplier (ESC_min = I_peak × esc_margin)",
    )
    c_margin: float = Field(
        default=1.25,
        ge=1.0,
        description="Battery C-rate margin multiplier",
    )
    load_rpm_factor: float = Field(
        default=0.85,
        ge=0.5,
        le=1.0,
        description="Motor shaft RPM under load vs. no-load (V_nom × KV × factor)",
    )
    prop_pd: float = Field(
        default=0.65,
        ge=0.3,
        le=1.5,
        description=("Prop pitch/diameter ratio. Trainer: 0.65, 3D: 0.5, glider: 0.8, speed: 1.0"),
    )
    t_target_min: float = Field(
        default=10.0,
        gt=0,
        description="Target flight time [minutes]",
    )
    v_top_mps: float | None = Field(
        default=None,
        gt=0,
        description=(
            "Top speed [m/s] for peak-power sizing. Defaults to 1.4 × V_cruise when not supplied."
        ),
    )
    rho: float = Field(
        default=1.225,
        gt=0,
        description="Air density [kg/m³] (ISA sea-level default)",
    )
    g: float = Field(
        default=9.80665,
        gt=0,
        description="Gravitational acceleration [m/s²]",
    )


class SolutionRow(BaseModel):
    """Computed specs for one cell-count S, spanning the η_prop band.

    Scalar fields are computed at the mid-point of the η_prop band
    (eta_prop_lo + eta_prop_hi) / 2.  Fields with ``_lo`` / ``_hi``
    suffixes are band extremes — _lo uses eta_prop_hi (more efficient →
    less current) and _hi uses eta_prop_lo (less efficient → more current).
    """

    cell_count: int = Field(description="Number of LiPo cells (S)")
    v_nom_v: float = Field(description="Nominal pack voltage [V] = S × 3.7")
    v_sag_v: float = Field(description="Pack voltage under load [V] = S × 3.5")

    # Electrical power
    p_cruise_w: float = Field(description="Electrical power at cruise speed [W] (mid η)")
    p_top_w: float = Field(description="Peak electrical power at top speed [W] (mid η)")
    p_cruise_lo_w: float = Field(description="Electrical cruise power — low side of band [W]")
    p_cruise_hi_w: float = Field(description="Electrical cruise power — high side of band [W]")
    p_top_lo_w: float = Field(description="Peak electrical power — low side of band [W]")
    p_top_hi_w: float = Field(description="Peak electrical power — high side of band [W]")

    # Energy
    energy_wh: float = Field(description="Required energy [Wh] at mid η")

    # Battery
    capacity_mah_min: float = Field(description="Minimum battery capacity [mAh] (mid η)")
    capacity_mah_min_lo: float = Field(description="Minimum capacity — low side of band [mAh]")
    capacity_mah_min_hi: float = Field(description="Minimum capacity — high side of band [mAh]")

    # Peak current
    i_peak_a: float = Field(description="Peak battery current [A] (mid η)")
    i_peak_lo_a: float = Field(description="Peak current — low side of band [A]")
    i_peak_hi_a: float = Field(description="Peak current — high side of band [A]")

    # C-rate (includes the c_margin safety factor — the value to shop for)
    c_min: float = Field(description="Required C-rate incl. c_margin (mid η)")
    c_min_lo: float = Field(description="Required C-rate incl. c_margin — low side of band")
    c_min_hi: float = Field(description="Required C-rate incl. c_margin — high side of band")

    # ESC
    esc_min_a: float = Field(description="Minimum ESC continuous current rating [A] (mid η)")
    esc_min_lo_a: float = Field(description="ESC minimum — low side of band [A]")
    esc_min_hi_a: float = Field(description="ESC minimum — high side of band [A]")

    # Motor — required mechanical SHAFT power (P_aero / η_prop), not aerodynamic power
    motor_peak_w: float = Field(
        description="Motor peak shaft power required [W] (= P_aero(V_top) / η_prop_mid)"
    )
    motor_cont_w: float = Field(
        description="Motor continuous shaft power required [W] (= P_aero(V_cruise) / η_prop_mid)"
    )

    # KV (approximate; Phase 1 — marked approximate per spec)
    kv_approx: float | None = Field(
        default=None,
        description=(
            "Approximate motor KV [RPM/V]. "
            "KV ≈ RPM_target / (V_nom × load_rpm_factor). "
            "Phase 1 estimate — depends on prop_pd and V_top."
        ),
    )

    # Catalog match flags
    has_motor_match: bool = Field(
        default=False,
        description="True if a catalog motor's shaft-power rating meets motor_peak_w",
    )
    has_battery_match: bool = Field(
        default=False,
        description="True if a catalog battery meets capacity_mah_min and c_min",
    )
    has_esc_match: bool = Field(default=False, description="True if a catalog ESC meets esc_min_a")


class FeasibleRegion(BaseModel):
    """Feasible region in the (capacity [mAh], C-rate) plane for one cell-count.

    The region is open toward higher mAh and higher C-rate (more is always OK).
    The boundary consists of:
    - A vertical floor at capacity_floor_mah (energy constraint).
    - A hyperbolic curve C ≥ i_peak_a / (capacity_mah / 1000) (current constraint).
    """

    cell_count: int
    capacity_floor_mah: float = Field(
        description="Minimum capacity [mAh] (energy-budget constraint)"
    )
    i_peak_a: float = Field(description="Peak current [A] that determines the C-rate hyperbola")
    # Sample points on the C-rate hyperbola for plotting.
    # capacity_curve_mah[i] → c_rate_curve[i]
    capacity_curve_mah: list[float] = Field(
        default_factory=list,
        description="Sample capacity values [mAh] for the C-rate hyperbola",
    )
    c_rate_curve: list[float] = Field(
        default_factory=list,
        description="Corresponding minimum C-rates for the hyperbola samples",
    )


class ShoppingSpec(BaseModel):
    """Minimum-spec summary for a selected cell-count — copy-paste to online shop."""

    cell_count: int
    battery_min_mah: float
    battery_min_c: float = Field(description="Required C-rate incl. c_margin")
    battery_v_nom: float
    esc_min_a: float
    motor_min_peak_w: float = Field(
        description="Required motor peak SHAFT power [W] (P_aero / η_prop_mid)"
    )
    motor_cont_w: float = Field(
        description="Required motor continuous SHAFT power [W] (P_aero / η_prop_mid)"
    )
    kv_approx: float | None


class PowertrainSolutionSpaceResponse(BaseModel):
    """Full response from GET /aeroplanes/{id}/powertrain/solution-space."""

    rows: list[SolutionRow] = Field(description="One row per requested cell-count S")
    feasible_regions: list[FeasibleRegion] = Field(
        description="Feasible (capacity, C) region per cell-count"
    )
    shopping_specs: list[ShoppingSpec] = Field(description="Minimum shopping spec per cell-count")
    # Invariants (aero-side, independent of cell count)
    p_aero_cruise_w: Annotated[float, Field(description="Aerodynamic power at cruise speed [W]")]
    p_aero_top_w: Annotated[float, Field(description="Aerodynamic power at top speed [W]")]
    energy_wh: Annotated[
        float,
        Field(
            description=(
                "Required energy [Wh] at mid-η, accounting for DoD. Independent of cell-count."
            )
        ),
    ]
    v_cruise_mps: float = Field(description="Cruise speed used [m/s]")
    v_top_mps: float = Field(description="Top speed used for peak sizing [m/s]")
    t_target_min: float = Field(description="Target flight time [minutes]")
    assumptions_used: SolutionSpaceAssumptions = Field(
        description="Effective assumptions used for this computation"
    )
    warnings: list[str] = Field(
        default_factory=list,
        description=(
            "Design warnings — e.g. missing context values. "
            "Non-empty means results may be based on fallback defaults."
        ),
    )
