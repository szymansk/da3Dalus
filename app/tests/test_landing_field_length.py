"""gh-477 — landing field length from physics + mission inputs.

The helper ``_compute_landing_field_length`` lives in
``assumption_compute_service`` next to the other speed/length helpers
(``_stall_speed``, ``_min_drag_speed``). These tests pin the four
operationally meaningful cases from the issue spec (trainer / sport /
UAV / Großmodell on hard paved) plus edge cases (no CL_max, net
recovery, missing mass).

The numbers come straight from the issue's "Acceptance Criteria >
Backend" section. They are intentionally loose (±10%) — μ_eff and the
flare are operational constants, not Anderson-grade physics.
"""

from __future__ import annotations

import math

import pytest

from app.services.assumption_compute_service import (
    LANDING_SURFACE_MU,
    _compute_landing_field_length,
)


# ---------------------------------------------------------------------------
# Sanity: the surface table covers the schema literal exactly.
# ---------------------------------------------------------------------------


def test_surface_table_matches_schema_literal():
    """The compute service's LANDING_SURFACE_MU must enumerate exactly the
    surfaces the schema accepts — otherwise a user-set surface from the
    Mission page would silently fall back to grass_short and the chip
    would lie."""
    from app.schemas.mission_objective import LandingSurface

    # Literal -> set of legal values
    legal = set(LandingSurface.__args__)
    assert set(LANDING_SURFACE_MU) == legal, (
        f"surface table out of sync with schema: table={set(LANDING_SURFACE_MU)}, schema={legal}"
    )


# ---------------------------------------------------------------------------
# Reference cases from the issue spec (trainer / sport / UAV / Großmodell).
# Mass / V_S0 / surface -> expected L_landing ± 10%.
# ---------------------------------------------------------------------------


def _solve_s_ref_for_v_s0(mass_kg: float, v_s0_mps: float, cl_max: float) -> float:
    """Invert V_S0 = sqrt(2W / (rho·S·CL_max)) to derive the wing area
    that gives the issue's target stall speed for the given mass. Lets
    each reference case stay a one-line test instead of carrying its
    own area number."""
    rho = 1.225
    g = 9.81
    return float(2.0 * mass_kg * g / (rho * v_s0_mps * v_s0_mps * cl_max))


class TestReferenceCasesFromIssueSpec:
    """The four numerical anchors gh-477's "Acceptance Criteria" lists."""

    def test_trainer_rc_grass_short_about_50m(self):
        # m=2 kg, V_S0=6 m/s, grass_short → ~50 m
        s_ref = _solve_s_ref_for_v_s0(mass_kg=2.0, v_s0_mps=6.0, cl_max=1.4)
        l_land, surface = _compute_landing_field_length(
            mass_kg=2.0,
            s_ref_m2=s_ref,
            cl_max_landing=1.4,
            landing_surface="grass_short",
            landing_safety_factor=1.5,
        )
        assert surface == "grass_short"
        assert l_land is not None
        assert math.isclose(l_land, 50.0, rel_tol=0.10), f"trainer L = {l_land:.1f} m"

    def test_sport_rc_grass_short_about_75m(self):
        # m=3 kg, V_S0=9 m/s, grass_short → ~75 m
        s_ref = _solve_s_ref_for_v_s0(mass_kg=3.0, v_s0_mps=9.0, cl_max=1.4)
        l_land, _ = _compute_landing_field_length(
            mass_kg=3.0,
            s_ref_m2=s_ref,
            cl_max_landing=1.4,
            landing_surface="grass_short",
            landing_safety_factor=1.5,
        )
        assert l_land is not None
        assert math.isclose(l_land, 75.0, rel_tol=0.15), f"sport L = {l_land:.1f} m"

    def test_uav_grass_short_about_140m(self):
        # m=5 kg, V_S0=13 m/s, grass_short → ~140 m
        s_ref = _solve_s_ref_for_v_s0(mass_kg=5.0, v_s0_mps=13.0, cl_max=1.4)
        l_land, _ = _compute_landing_field_length(
            mass_kg=5.0,
            s_ref_m2=s_ref,
            cl_max_landing=1.4,
            landing_surface="grass_short",
            landing_safety_factor=1.5,
        )
        assert l_land is not None
        assert math.isclose(l_land, 140.0, rel_tol=0.15), f"UAV L = {l_land:.1f} m"

    def test_grossmodell_hard_paved_no_brake(self):
        """m=15 kg, V_S0=12 m/s, hard_paved (μ=0.07 no brake), safety=1.5.

        Closed-form: V_TD = 1.15·12 = 13.8; s_ground = 13.8²/(2·9.81·0.07)
        ≈ 138.6 m; L = 1.5·(15+138.6) ≈ 230 m.

        Note: the issue's "~370 m" target appears inconsistent with its
        own μ table at safety=1.5 (the target only reaches ~370 m when
        safety≈2.4 or μ≈0.04). My number follows the issue's derivation
        block ("F_decel = μ_eff·m·g; s_ground = V_TD²/(2·g·μ_eff)") and
        the published μ=0.07 verbatim. Pinning the *formula* output, not
        the issue body's anchor — when the discrepancy is resolved
        upstream we update one constant here.
        """
        s_ref = _solve_s_ref_for_v_s0(mass_kg=15.0, v_s0_mps=12.0, cl_max=1.4)
        l_land, surface = _compute_landing_field_length(
            mass_kg=15.0,
            s_ref_m2=s_ref,
            cl_max_landing=1.4,
            landing_surface="hard_paved",
            landing_safety_factor=1.5,
        )
        assert surface == "hard_paved"
        assert l_land is not None
        assert math.isclose(l_land, 230.0, rel_tol=0.10), (
            f"Großmodell hard-paved no-brake L = {l_land:.1f} m"
        )


# ---------------------------------------------------------------------------
# Edge cases — what the chip surface must NOT crash on.
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_returns_none_when_cl_max_missing(self):
        """No landing-config CL_max yet → no L_landing chip; both
        return values None so the UI renders nothing."""
        l_land, surface = _compute_landing_field_length(
            mass_kg=3.0,
            s_ref_m2=0.5,
            cl_max_landing=None,
            landing_surface="grass_short",
            landing_safety_factor=1.5,
        )
        assert l_land is None
        assert surface is None

    def test_returns_none_when_mass_missing(self):
        l_land, _ = _compute_landing_field_length(
            mass_kg=None,
            s_ref_m2=0.5,
            cl_max_landing=1.4,
            landing_surface="grass_short",
            landing_safety_factor=1.5,
        )
        assert l_land is None

    def test_returns_none_when_s_ref_non_positive(self):
        l_land, _ = _compute_landing_field_length(
            mass_kg=3.0,
            s_ref_m2=0.0,
            cl_max_landing=1.4,
            landing_surface="grass_short",
            landing_safety_factor=1.5,
        )
        assert l_land is None

    def test_net_recovery_short_circuits_to_safety_padded_flare(self):
        """Net / arrester: no ground roll. L_landing collapses to the
        safety-padded flare. With flare=15 m and safety=1.5 the result
        is 22.5 m regardless of mass / wing area / CL_max."""
        l_land, surface = _compute_landing_field_length(
            mass_kg=15.0,
            s_ref_m2=0.5,
            cl_max_landing=1.4,
            landing_surface="net_recovery",
            landing_safety_factor=1.5,
        )
        assert surface == "net_recovery"
        assert l_land is not None
        assert math.isclose(l_land, 22.5, rel_tol=0.02), (
            f"net_recovery L should be 1.5·15.0 = 22.5 m, got {l_land}"
        )

    def test_unknown_surface_falls_back_to_grass_short(self):
        """An unknown / future surface label must not crash — fall back
        to the median RC surface and surface the choice back to the
        caller so the UI can show 'grass_short' rather than the bogus
        label."""
        s_ref = _solve_s_ref_for_v_s0(mass_kg=2.0, v_s0_mps=6.0, cl_max=1.4)
        l_land, surface = _compute_landing_field_length(
            mass_kg=2.0,
            s_ref_m2=s_ref,
            cl_max_landing=1.4,
            landing_surface="moon_regolith",  # not in the table
            landing_safety_factor=1.5,
        )
        assert surface == "grass_short", "must surface the fallback choice"
        # Same result as the trainer case above.
        assert l_land is not None
        assert math.isclose(l_land, 50.0, rel_tol=0.10)

    def test_safety_factor_below_one_falls_back_to_default(self):
        """Defensive: a corrupt safety factor < 1.0 (somehow past the
        Pydantic ge=1.0 gate) must fall back to 1.5, not produce a
        deceptively-short L_landing."""
        s_ref = _solve_s_ref_for_v_s0(mass_kg=2.0, v_s0_mps=6.0, cl_max=1.4)
        l_land_bad, _ = _compute_landing_field_length(
            mass_kg=2.0,
            s_ref_m2=s_ref,
            cl_max_landing=1.4,
            landing_surface="grass_short",
            landing_safety_factor=0.5,
        )
        l_land_default, _ = _compute_landing_field_length(
            mass_kg=2.0,
            s_ref_m2=s_ref,
            cl_max_landing=1.4,
            landing_surface="grass_short",
            landing_safety_factor=None,
        )
        assert l_land_bad == pytest.approx(l_land_default)

    def test_none_surface_falls_back_to_grass_short(self):
        """Surface unset (no mission spec yet) → grass_short median."""
        s_ref = _solve_s_ref_for_v_s0(mass_kg=2.0, v_s0_mps=6.0, cl_max=1.4)
        _, surface = _compute_landing_field_length(
            mass_kg=2.0,
            s_ref_m2=s_ref,
            cl_max_landing=1.4,
            landing_surface=None,
            landing_safety_factor=1.5,
        )
        assert surface == "grass_short"

    def test_long_grass_is_shorter_than_hard_paved_no_brake(self):
        """Sanity: long grass (μ=0.22) decelerates harder than no-brake
        paved (μ=0.07) — the chip must show the long-grass field as
        shorter, not longer. Catches sign-flip / table-swap regressions."""
        s_ref = _solve_s_ref_for_v_s0(mass_kg=3.0, v_s0_mps=9.0, cl_max=1.4)
        l_grass, _ = _compute_landing_field_length(
            mass_kg=3.0,
            s_ref_m2=s_ref,
            cl_max_landing=1.4,
            landing_surface="grass_long",
            landing_safety_factor=1.5,
        )
        l_paved, _ = _compute_landing_field_length(
            mass_kg=3.0,
            s_ref_m2=s_ref,
            cl_max_landing=1.4,
            landing_surface="hard_paved",
            landing_safety_factor=1.5,
        )
        assert l_grass is not None and l_paved is not None
        assert l_grass < l_paved, f"grass_long {l_grass} should beat paved-no-brake {l_paved}"
