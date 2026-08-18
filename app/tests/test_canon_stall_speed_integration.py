"""Canon test — the approved stall-speed relation must close in Reynolds number.

This is a *fachlicher* test: it asserts a domain truth, not a code path. It would still
be meaningful if every function it touches were rewritten.

Canon entry, approved 2026-08-18:
    ``_reversa_sdd/calculations/canon/formulas/stall-speed.md``

    V_S = sqrt( 2*m*g / (rho * S_ref * C_L,max) )

Precondition on the binding ``cl_max``:

    C_L,max must be evaluated at the Reynolds number of the stall condition itself.

C_L,max is a steep function of Reynolds number in the model range — at low Re the
boundary layer stays laminar further aft and forms a separation bubble that caps the
suction peak. Since ``V_S ~ C_L,max^-1/2`` and ``Re ~ V_S``, the relation is an
**implicit equation** at this scale. The test asserts its fixed point:

    take the app's C_L,max -> compute V_S
    -> re-evaluate C_L,max at that V_S alone -> compute V_S again
    -> the two must agree

The precondition is recorded as **violated** (gh-1142): ``_fine_sweep_cl_max`` takes
``np.max`` over a velocity x alpha grid, so the C_L,max that sizes the slowest point of
the envelope comes from the fastest sample. This test is therefore expected to fail, and
**its failure message is the measurement gh-1142 asks for** — the spread it prints is the
quantity that turns "violated, magnitude unknown" into a number.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

asb = pytest.importorskip("aerosandbox")

from app.models.computation_config import (  # noqa: E402
    COMPUTATION_CONFIG_DEFAULTS,
    AircraftComputationConfigModel,
)
from app.services.assumption_compute_service import (  # noqa: E402
    _coarse_alpha_sweep,
    _fine_sweep_cl_max,
)

#: Approved canon quantity ``gravity`` (m/s^2).
G = 9.81
#: Approved canon quantity ``air-density``, evaluated at sea level for this fixture.
RHO = 1.225

#: How far the fixed point may miss before the binding is judged inconsistent.
#: 2 % of V_S is well inside every other uncertainty in the chain and far below the
#: ~35 % that a handbook C_L,max can cost (canon: validity note on stall-speed).
TOLERANCE = 0.02


def _config() -> AircraftComputationConfigModel:
    """The sweep parameters as the service expects them, without a database row."""
    return AircraftComputationConfigModel(**COMPUTATION_CONFIG_DEFAULTS)


def _rc_trainer():
    """A 1.5 kg RC trainer: rectangular wing, 1.4 m span, 0.2 m chord.

    Returns ``(airplane, mass_kg, s_ref_m2)``. Deliberately built from AeroSandbox
    primitives rather than from the database, so the test binds to the physics and not
    to the converter chain.
    """
    chord, half_span = 0.20, 0.70
    airfoil = asb.Airfoil("naca2412")
    wing = asb.Wing(
        name="Main Wing",
        symmetric=True,
        xsecs=[
            asb.WingXSec(xyz_le=[0, 0, 0], chord=chord, twist=0, airfoil=airfoil),
            asb.WingXSec(xyz_le=[0, half_span, 0], chord=chord, twist=0, airfoil=airfoil),
        ],
    )
    plane = asb.Airplane(name="rc-trainer", xyz_ref=[0.05, 0, 0], wings=[wing])
    return plane, 1.5, float(plane.s_ref)


def _stall_speed(mass_kg: float, s_ref: float, cl_max: float) -> float:
    """The approved canon relation, written once and used for both sides."""
    return math.sqrt(2.0 * mass_kg * G / (RHO * s_ref * cl_max))


def _cl_max_at(plane, velocity_mps: float, stall_alpha_deg: float, config) -> float:
    """C_L,max at a single velocity — i.e. at one Reynolds number."""
    alphas = np.arange(
        stall_alpha_deg - config.fine_alpha_margin_deg,
        stall_alpha_deg + config.fine_alpha_margin_deg + 0.01,
        config.fine_alpha_step_deg,
    )
    op = asb.OperatingPoint(
        velocity=np.full_like(alphas, float(velocity_mps)),
        alpha=alphas,
    )
    result = asb.AeroBuildup(airplane=plane, op_point=op, xyz_ref=plane.xyz_ref).run()
    return float(np.max(np.atleast_1d(np.asarray(result["CL"], dtype=float))))


@pytest.mark.slow
@pytest.mark.requires_aerosandbox
def test_stall_speed_closes_in_reynolds_number():
    """The C_L,max that sizes V_S must be the C_L,max that holds at V_S."""
    plane, mass_kg, s_ref = _rc_trainer()
    config = _config()
    v_cruise, v_max = 14.0, 28.0

    stall_alpha = _coarse_alpha_sweep(plane, v_cruise, config)

    # What the application does today: one C_L,max for the whole envelope.
    cl_max_app, *_ = _fine_sweep_cl_max(plane, stall_alpha, v_cruise, v_max, config)
    v_stall_app = _stall_speed(mass_kg, s_ref, cl_max_app)

    # What the canon requires: C_L,max evaluated at the stall condition.
    cl_max_at_stall = _cl_max_at(plane, v_stall_app, stall_alpha, config)
    v_stall_consistent = _stall_speed(mass_kg, s_ref, cl_max_at_stall)

    spread = abs(v_stall_consistent - v_stall_app) / v_stall_app

    assert spread <= TOLERANCE, (
        "The stall-speed binding does not close in Reynolds number.\n"
        f"  C_L,max as the app computes it (max over the velocity grid) : {cl_max_app:.4f}\n"
        f"  C_L,max at the resulting stall speed                        : "
        f"{cl_max_at_stall:.4f}\n"
        f"  V_stall from the first                                     : "
        f"{v_stall_app:.3f} m/s\n"
        f"  V_stall from the second                                    : "
        f"{v_stall_consistent:.3f} m/s\n"
        f"  spread                                                     : "
        f"{100 * spread:.1f} %  (tolerance {100 * TOLERANCE:.0f} %)\n"
        "\n"
        "The reported stall speed is the lower one, so the aircraft stalls sooner than\n"
        "the application says. This is the measurement gh-1142 asks for; canon entry\n"
        "_reversa_sdd/calculations/canon/formulas/stall-speed.md, precondition `cl_max`."
    )
