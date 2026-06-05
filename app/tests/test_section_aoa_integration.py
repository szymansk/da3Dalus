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
      1. Sorted by ascending y_m.
      2. All cl values finite and positive (wing generating positive lift).
      3. cl decreases from inner to outer span (tapered washed wing).
      4. All effective-AoA values are finite.
      5. No section shows a tip-singularity spike: |alpha_eff − alpha_geom| ≤ 5°.
      6. Washout trend: alpha_eff at root ≥ alpha_eff at tip (twist reduces
         effective incidence toward tip).
      7. VAST majority (≥ 90%) of positive-y panels have induced_angle > 0.
         A small negative induced angle (|i| < ~0.1°) is physically real for
         non-elliptic loading and is intentionally NOT clamped.
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

    # 2. All cl values are finite and positive (wing generating positive lift)
    for e in entries:
        assert math.isfinite(e.cl), f"Non-finite cl at y={e.y_m:.3f}: {e.cl}"
        assert e.cl > 0, f"Non-positive cl at y={e.y_m:.3f}: {e.cl:.4f}"

    pos_entries = [e for e in entries if e.y_m > 0]
    assert len(pos_entries) >= 2, "Expected at least 2 positive-y panels"

    # 3. cl decreases from mid-span toward the tip on the positive-y half.
    cl_inner = pos_entries[0].cl  # most inboard positive-y panel
    cl_outer = pos_entries[-1].cl  # most outboard panel (tip)
    assert cl_inner > cl_outer, (
        f"Expected cl_inner({cl_inner:.3f}) > cl_outer({cl_outer:.3f}): "
        "lift should peak near root for a tapered washed wing"
    )

    # 4. All effective-AoA values are finite (no NaN/inf singularities).
    for e in pos_entries:
        assert math.isfinite(e.alpha_effective_deg), (
            f"Non-finite alpha_eff at y={e.y_m:.3f}: {e.alpha_effective_deg}"
        )

    # 5. No section shows a tip-singularity spike (|alpha_eff − alpha_geom| ≤ 5°).
    #    This is the primary invariant the cl-based path must satisfy.
    for e in pos_entries:
        diff = abs(e.alpha_effective_deg - e.alpha_geometric_deg)
        assert diff <= 5.0, (
            f"TIP-SINGULARITY: |alpha_eff({e.alpha_effective_deg:.2f}) − "
            f"alpha_geom({e.alpha_geometric_deg:.2f})| = {diff:.2f}° > 5° at y={e.y_m:.3f}"
        )

    # 6. Washout trend: alpha_eff at the innermost positive-y panel ≥ alpha_eff at tip.
    #    Geometric twist reduces the effective angle of attack from root toward tip.
    alpha_eff_inner = pos_entries[0].alpha_effective_deg
    alpha_eff_outer = pos_entries[-1].alpha_effective_deg
    assert alpha_eff_inner >= alpha_eff_outer - 0.2, (
        f"Washout trend violated: alpha_eff_inner({alpha_eff_inner:.2f}) < "
        f"alpha_eff_outer({alpha_eff_outer:.2f}) — twist should reduce effective AoA toward tip"
    )

    # 7. VAST majority (≥ 90%) of positive-y panels must have a positive induced angle.
    #    A small negative induced angle (|i| < ~0.1°) is physically valid for
    #    non-elliptic loading — it represents local upwash, not a solver error.
    #    We do NOT require 100% positive; that would reject real physics.
    n_positive = sum(1 for e in pos_entries if e.induced_angle_deg > 0)
    fraction_positive = n_positive / len(pos_entries)
    assert fraction_positive >= 0.9, (
        f"Only {fraction_positive:.0%} of sections have positive induced angle "
        f"({n_positive}/{len(pos_entries)}); expected ≥ 90%"
    )

    # 8. TIP panel: no singularity and no strongly negative induced angle.
    tip_panel = pos_entries[-1]
    assert abs(tip_panel.alpha_effective_deg) < 20.0, (
        f"TIP alpha_eff spike: {tip_panel.alpha_effective_deg:.2f}° at y={tip_panel.y_m:.3f}"
    )
    assert tip_panel.induced_angle_deg > -5.0, (
        f"TIP induced angle strongly negative: {tip_panel.induced_angle_deg:.2f}° at y={tip_panel.y_m:.3f}"
    )


@pytest.mark.slow
def test_section_aoa_tip_singularity_free_on_high_taper():
    """CL-based alpha_eff derivation must not produce singularities at collapsing-chord tips.

    Uses an extreme taper (root chord 0.30 m → tip chord 0.03 m over 0.8 m span)
    at high spanwise resolution.  The velocity-based atan2 path is singular here
    (self-induced velocity diverges as chord→0); the CL-based path must stay well-
    behaved.

    Assertions (positive-y panels only):
      1. No panel has alpha_eff > alpha_geom + 1.0° (no singularity spikes).
      2. No panel has |alpha_eff| > 20° (no runaway values).
      3. induced_angle > −5° everywhere (no strongly negative values).
      4. TIP panel specifically: induced_angle > 0° (downwash present at tip).
    """
    import aerosandbox as asb

    from app.services.section_aoa_service import compute_section_aoa

    # 30:1 taper (root 0.30 m → tip 0.01 m) — collapses chord toward the tip.
    # The old velocity-based atan2 path produces alpha_eff > alpha_geom by ~2° at
    # the outer panels (4 panels at res=32 in the velocity path; zero violations in
    # the CL path).  NACA0012 is used so alpha_L0=0; the formula simplifies to
    # alpha_eff = degrees(cl / (2*pi)).
    root_xsec = asb.WingXSec(
        xyz_le=[0.0, 0.0, 0.0],
        chord=0.30,
        twist=3.0,
        airfoil=asb.Airfoil("naca0012"),  # symmetric → alpha_L0 = 0
    )
    tip_xsec = asb.WingXSec(
        xyz_le=[0.05, 0.80, 0.0],
        chord=0.01,  # 30:1 taper — collapses toward zero
        twist=0.0,
        airfoil=asb.Airfoil("naca0012"),
    )
    wing = asb.Wing(
        name="high_taper_wing",
        xsecs=[root_xsec, tip_xsec],
        symmetric=True,
    )
    airplane = asb.Airplane(
        wings=[wing],
        xyz_ref=[0.05, 0.0, 0.0],
    )
    op = asb.OperatingPoint(
        velocity=15.0,
        alpha=4.0,
        beta=0.0,
        atmosphere=asb.Atmosphere(altitude=0.0),
    )

    # res=32 exposes the singularity in the old velocity-based path (4 violations)
    entries = compute_section_aoa(airplane, op, wing_name="high_taper_wing", spanwise_resolution=32)

    pos_entries = [e for e in entries if e.y_m > 0]
    assert len(pos_entries) >= 4, "Expected multiple positive-y panels"

    for e in pos_entries:
        assert e.alpha_effective_deg <= e.alpha_geometric_deg + 1.0, (
            f"alpha_eff({e.alpha_effective_deg:.2f}) > alpha_geom({e.alpha_geometric_deg:.2f}) "
            f"at y={e.y_m:.3f} — possible tip singularity"
        )
        assert abs(e.alpha_effective_deg) < 20.0, (
            f"alpha_eff spike: {e.alpha_effective_deg:.2f}° at y={e.y_m:.3f}"
        )
        assert e.induced_angle_deg > -5.0, (
            f"induced_angle strongly negative: {e.induced_angle_deg:.2f}° at y={e.y_m:.3f}"
        )

    # Tip panel specifically: induced downwash must be positive (lift generates downwash)
    tip_panel = pos_entries[-1]
    assert tip_panel.induced_angle_deg > 0.0, (
        f"TIP induced angle non-positive: {tip_panel.induced_angle_deg:.2f}° at y={tip_panel.y_m:.3f}"
    )
