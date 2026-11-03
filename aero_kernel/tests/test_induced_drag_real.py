"""The kernel's drag against real AeroSandbox (aero tier, #1346).

The canon's k_e,D0 must be the factor AeroSandbox actually multiplies into its Oswald factor, or the
kernel's correction would no longer remove it exactly; and AeroBuildup's total drag must be the sum
of the two parts the kernel reads. If AeroSandbox changes either, these tests say so.
"""

import math

import numpy as np
import pytest
from aero_kernel.solvers.aerobuildup import kernel_drag
from aero_kernel.solvers.asb_airplane import load_aerosandbox, to_asb_airplane
from aero_kernel.tests.reference_fleet import FleetMember, reference_document
from aero_kernel.tests.solver_builders import K_E_D0
from aero_kernel.tests.test_stall_speed_fleet import sea_level_air

pytestmark = pytest.mark.aero


def nita_scholz_e_theo(taper: float, aspect_ratio: float, sweep_deg: float) -> float:
    """The theoretical Oswald factor of Nita & Scholz (2012), section 5, eqs. 36 and 37.

    ``e_theo = 1 / (1 + f(lambda - delta_lambda) A)``, ``f`` the fourth-order polynomial of eq. 36,
    ``delta_lambda = -0.357 + 0.45 exp(-0.0375 phi_25)`` of eq. 37 (with the sign of the exponent as
    AeroSandbox corrects it, ``inviscid.py:58-61``).
    """
    shifted = taper - (-0.357 + 0.45 * math.exp(-0.0375 * sweep_deg))
    f = 0.0524 * shifted**4 - 0.15 * shifted**3 + 0.1659 * shifted**2 - 0.0706 * shifted + 0.0119
    return 1.0 / (1.0 + f * aspect_ratio)


@pytest.mark.parametrize(
    ("taper", "aspect_ratio", "sweep_deg"),
    [(1.0, 6.0, 0.0), (0.5, 8.0, 0.0), (0.45, 12.0, 5.0), (0.3, 4.5, 25.0)],
)
def test_the_canon_viscous_factor_is_aerosandboxs(
    taper: float, aspect_ratio: float, sweep_deg: float
) -> None:
    """AeroSandbox's Oswald factor over the inviscid one is the canon's k_e,D0 (fuselage factor 1)."""
    import importlib

    aerolib = importlib.import_module("aerosandbox.library.aerodynamics")  # untyped AeroSandbox
    e = float(
        aerolib.oswalds_efficiency(
            taper_ratio=taper,
            aspect_ratio=aspect_ratio,
            sweep=sweep_deg,
            fuselage_diameter_to_span_ratio=0.0,
            method="nita_scholz",
        )
    )
    ratio = e / nita_scholz_e_theo(taper, aspect_ratio, sweep_deg)
    assert math.isclose(ratio, K_E_D0, rel_tol=0.0, abs_tol=1e-9)


@pytest.mark.parametrize("member", [FleetMember.BRYAN, FleetMember.BELEMNITOS])
def test_aerobuildups_drag_is_the_sum_of_the_two_parts_the_kernel_reads(
    member: FleetMember,
) -> None:
    """``D = D_profile + D_induced`` (``aero_buildup.py:279-345``), so with k_e,D0 = 1 the kernel's drag
    is AeroBuildup's own, and with the canon's factor it is smaller by (1 - k_e,D0) D_induced."""
    from aero_kernel.geometry import AirplaneGeometry
    from aero_kernel.solvers.air import FixedAtmosphere

    asb = load_aerosandbox()
    converted = to_asb_airplane(AirplaneGeometry.model_validate(reference_document(member)))
    alphas = np.array([-2.0, 2.0, 6.0, 10.0])
    result = asb.AeroBuildup(
        converted,
        asb.OperatingPoint(
            atmosphere=FixedAtmosphere(sea_level_air()),
            velocity=np.full_like(alphas, 9.0),
            alpha=alphas,
        ),
        model_size="xlarge",
    ).run()
    total = np.asarray(result["D"], dtype=float)
    induced = np.asarray(result["D_induced"], dtype=float)
    assert np.allclose(np.asarray(kernel_drag(result, 1.0)), total, rtol=1e-9, atol=0.0)
    assert np.allclose(
        np.asarray(kernel_drag(result, K_E_D0)),
        total - (1.0 - K_E_D0) * induced,
        rtol=1e-9,
        atol=0.0,
    )
    assert bool(np.all(induced > 0.0))
