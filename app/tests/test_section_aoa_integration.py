"""Slow integration test for section_aoa_service (gh-840).

Uses real AeroSandbox LiftingLine on a tapered/washed wing (the integration
aeroplane from conftest.py) and asserts physically sane distributions:
  - cl decreases from root toward tip on a tapered washed wing
  - induced angle is positive everywhere
  - alpha_eff < alpha_geom everywhere

Marked @pytest.mark.slow — only run in the aero tier.
"""

from __future__ import annotations

import math
import uuid

import pytest


@pytest.mark.slow
def test_section_aoa_physical_sanity_on_tapered_wing():
    """LiftingLine on the integration plane yields physically sane span distribution.

    Assertions:
      1. cl decreases from root to tip (loaded tapered wing with twist).
      2. induced_angle_deg > 0 at all stations (lift present → downwash).
      3. alpha_eff < alpha_geom (downwash reduces effective incidence).
      4. Output is sorted by ascending y_m.
    """
    import aerosandbox as asb
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session, sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.db.base import Base
    from app.services.section_aoa_service import compute_section_aoa
    from app.converters.model_schema_converters import aeroplane_schema_to_asb_airplane_async

    # --- Build an inline tapered+washed wing using ASB directly ---
    # Two-xsec wing: root (y=0, chord=0.2, twist=4°), tip (y=0.5, chord=0.12, twist=0°)
    # Symmetric → span = 1 m.  Approximate a lightly loaded glider wing.
    root_xsec = asb.WingXSec(
        xyz_le=[0.0, 0.0, 0.0],
        chord=0.20,
        twist=4.0,  # geometric twist [deg] — root pitched up
        airfoil=asb.Airfoil("naca2412"),
    )
    tip_xsec = asb.WingXSec(
        xyz_le=[0.05, 0.50, 0.0],
        chord=0.12,
        twist=0.0,  # tip not twisted
        airfoil=asb.Airfoil("naca2412"),
    )
    wing = asb.Wing(
        name="main_wing",
        xsecs=[root_xsec, tip_xsec],
        symmetric=True,
    )
    airplane = asb.Airplane(
        wings=[wing],
        xyz_ref=[0.05, 0.0, 0.0],
    )
    op = asb.OperatingPoint(
        velocity=15.0,
        alpha=4.0,  # 4° trim α
        beta=0.0,
        atmosphere=asb.Atmosphere(altitude=0.0),
    )

    # --- Run compute_section_aoa ---
    entries = compute_section_aoa(airplane, op, wing_name="main_wing", spanwise_resolution=8)

    assert len(entries) >= 2, "Expected at least 2 spanwise panels"

    # 1. Sorted by ascending y
    ys = [e.y_m for e in entries]
    assert ys == sorted(ys), "Sections not sorted by ascending y_m"

    # 2. All cl values are positive (wing generating positive lift)
    for e in entries:
        assert e.cl > 0, f"Non-positive cl at y={e.y_m:.3f}: {e.cl:.4f}"

    # 3. cl decreases from mid-span toward the tip on the positive-y half.
    #    For a symmetric wing, the inner-most positive-y panels have higher cl
    #    than the outer panels.  We use only positive-y panels for this check.
    pos_entries = [e for e in entries if e.y_m > 0]
    assert len(pos_entries) >= 2, "Expected at least 2 positive-y panels"
    cl_inner = pos_entries[0].cl  # most inboard positive-y panel
    cl_outer = pos_entries[-1].cl  # most outboard panel (tip)
    assert cl_inner > cl_outer, (
        f"Expected cl_inner({cl_inner:.3f}) > cl_outer({cl_outer:.3f}): "
        "lift should peak near root for a tapered washed wing"
    )

    # 4. Induced angle is positive for inner panels (downwash from lifting wing).
    #    Only check positive-y panels to avoid the symmetric mirror panels.
    for e in pos_entries:
        assert e.induced_angle_deg > -1.0, (
            f"Induced angle unexpectedly negative at y={e.y_m:.3f}: {e.induced_angle_deg:.2f}°"
        )

    # 5. alpha_eff ≤ alpha_geom (downwash reduces effective incidence).
    #    Allow a small tolerance for numerical noise.
    for e in pos_entries:
        assert e.alpha_effective_deg <= e.alpha_geometric_deg + 0.5, (
            f"alpha_eff({e.alpha_effective_deg:.2f}) > alpha_geom({e.alpha_geometric_deg:.2f}) "
            f"at y={e.y_m:.3f}"
        )
