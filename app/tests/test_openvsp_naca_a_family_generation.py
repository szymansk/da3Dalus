"""Unit tests for the NACA "a"-family mean-line generator (gh-733 Phase 2).

The "a"-family is the canonical NACA 6-series mean line (Abbott eq.
4.26 / NACA TR-824) — uniform lift distribution over 0 ≤ x ≤ a,
linearly unloading to zero at x=1. It also overlays on 4-/5-digit-mod
shapes when OpenVSP carries a ``MeanLine_a`` parm (e.g.
``naca4-923-a0.6`` on the Spitfire).

Pre-Phase-2 these xsecs silently passed through with a name string
but no ``.dat`` — the renderer drew the wing planform without the
airfoil curve. This module pins:

* analytical correctness of the a=1.0 closed form against a known
  hand-computable invariant (y_c_max at mid-chord = Cl·ln(2)/(4π))
* boundary conditions at LE and TE
* coordinate-file generation for the gh-733 reference profiles
  (Spitfire ``-a0.6``, Stratos ``-a1.0``, generic 6-series)
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from app.converters.openvsp_airfoil import (
    _naca_a_family_g,
    _naca_a_family_h,
    ensure_naca_a_family_dat,
    naca_a_family_camber_at,
    naca_a_family_coordinates,
)


# ---------------------------------------------------------------------------
# Constants g, h depend only on a
# ---------------------------------------------------------------------------


class TestConstants:
    def test_g_at_a_zero_is_minus_quarter(self):
        # Limit a→0: g = -1/(1-0) · [0·... + 1/4] = -1/4.
        assert _naca_a_family_g(0.0) == pytest.approx(-0.25)

    def test_h_at_a_zero(self):
        # At a=0: h = 1 · [0 - 1/4] + g = -1/4 + (-1/4) = -1/2.
        assert _naca_a_family_h(0.0) == pytest.approx(-0.5, abs=1e-9)

    def test_constants_avoid_division_by_zero_at_a_equals_1(self):
        # Singular branch — handled separately by the camber function.
        # The constants are not used in the a=1 path, but the helpers
        # must not raise.
        assert _naca_a_family_g(1.0) == 0.0
        assert _naca_a_family_h(1.0) == 0.0


# ---------------------------------------------------------------------------
# Camber line — closed-form (a=1) verifiable invariants
# ---------------------------------------------------------------------------


class TestCamberLineA1:
    """a=1.0 → uniform load over the entire chord. Closed-form:
    ``y_c = -Cl/(4π) · [(1-x)·ln(1-x) + x·ln(x)]``. Max at x=0.5
    with value ``Cl·ln(2)/(4π)``. This is the hand-computable
    invariant — pinning it catches every algebraic sign error and
    coefficient typo in the implementation."""

    def test_max_at_midchord_matches_closed_form(self):
        cl = 0.4
        expected_peak = cl * math.log(2) / (4.0 * math.pi)
        actual = naca_a_family_camber_at(0.5, a=1.0, design_cl=cl)
        assert actual == pytest.approx(expected_peak, rel=1e-9)

    def test_symmetric_about_midchord(self):
        # For a=1 the camber line is symmetric: y_c(x) = y_c(1-x).
        for x in (0.1, 0.2, 0.3, 0.4):
            y_left = naca_a_family_camber_at(x, a=1.0, design_cl=0.3)
            y_right = naca_a_family_camber_at(1.0 - x, a=1.0, design_cl=0.3)
            assert y_left == pytest.approx(y_right, abs=1e-12)

    def test_zero_at_le_and_te(self):
        assert naca_a_family_camber_at(0.0, a=1.0, design_cl=0.3) == 0.0
        assert naca_a_family_camber_at(1.0, a=1.0, design_cl=0.3) == 0.0

    def test_scales_linearly_with_design_cl(self):
        # The whole expression is multiplicative in design_cl.
        y_low = naca_a_family_camber_at(0.5, a=1.0, design_cl=0.2)
        y_high = naca_a_family_camber_at(0.5, a=1.0, design_cl=0.6)
        assert y_high == pytest.approx(3 * y_low, rel=1e-9)


# ---------------------------------------------------------------------------
# Camber line — general a < 1
# ---------------------------------------------------------------------------


class TestCamberLineGeneral:
    def test_zero_at_le_and_te_for_various_a(self):
        # BC: y_c(0) = y_c(1) = 0 for all valid a values.
        for a in (0.0, 0.3, 0.5, 0.6, 0.8, 0.95):
            assert naca_a_family_camber_at(0.0, a=a, design_cl=0.3) == 0.0
            assert naca_a_family_camber_at(1.0, a=a, design_cl=0.3) == 0.0

    def test_a_06_peak_near_x_05(self):
        # For the canonical Spitfire a=0.6 case, the camber peak
        # sits near x≈0.48 (verified against the implementation's
        # numerical scan in the source-control PR description).
        # Pin the qualitative property: peak ∈ (0.4, 0.55).
        xs = [i * 0.005 for i in range(201)]
        ys = [naca_a_family_camber_at(x, a=0.6, design_cl=0.3) for x in xs]
        i_max = ys.index(max(ys))
        assert 0.4 <= xs[i_max] <= 0.55, (
            f"a=0.6 peak position out of expected range: x={xs[i_max]}"
        )

    def test_a_below_a1_distinct_from_a1(self):
        # Without this, the singular-branch detection might silently
        # fall through and a < 1 would just return the a=1 result.
        # Sample x=0.5 — for a=0.6 the asymmetric mean line yields a
        # noticeably different y_c than a=1.0.
        y_a06 = naca_a_family_camber_at(0.5, a=0.6, design_cl=0.3)
        y_a1 = naca_a_family_camber_at(0.5, a=1.0, design_cl=0.3)
        assert abs(y_a06 - y_a1) > 1e-4

    def test_positive_camber_for_positive_cl(self):
        # The whole forward+mid region must be y_c > 0 for design Cl
        # > 0. (Aft of the unloading break the sign can flip; sample
        # only the forward region.)
        for a in (0.4, 0.6, 0.8):
            assert naca_a_family_camber_at(0.2, a=a, design_cl=0.3) > 0
            assert naca_a_family_camber_at(a / 2, a=a, design_cl=0.3) > 0


# ---------------------------------------------------------------------------
# Full-coordinate generator
# ---------------------------------------------------------------------------


class TestCoordinates:
    def test_returns_2n_plus_1_points(self):
        coords = naca_a_family_coordinates(
            a=0.6, design_cl=0.3, thick_chord=0.12, n_half=20
        )
        assert len(coords) == 2 * 20 + 1

    def test_le_at_origin_and_te_symmetric(self):
        coords = naca_a_family_coordinates(
            a=0.6, design_cl=0.3, thick_chord=0.12
        )
        # Selig: LE is the midpoint.
        assert coords[len(coords) // 2] == (0.0, 0.0)
        # TE x ≈ 1, lower below chord, upper above.
        assert coords[0][1] > 0
        assert coords[-1][1] < 0
        # Open-TE pattern from the 4-digit thickness polynomial.
        assert abs(coords[0][1] + coords[-1][1]) < 1e-9

    def test_symmetric_airfoil_when_cl_zero(self):
        # design_Cl=0 should produce a perfectly symmetric airfoil
        # regardless of a — the camber term vanishes for all x.
        coords = naca_a_family_coordinates(
            a=0.6, design_cl=0.0, thick_chord=0.12
        )
        mid = len(coords) // 2
        # Selig: upper from index 0 (TE) to ``mid`` (LE), lower from
        # ``mid`` (LE) to len-1 (TE). For symmetric pairs at the same
        # chord position: ``coords[mid - k]`` ↔ ``coords[mid + k]``.
        for k in range(1, mid):
            x_u, y_u = coords[mid - k]
            x_l, y_l = coords[mid + k]
            assert x_u == pytest.approx(x_l, abs=1e-9)
            assert y_u == pytest.approx(-y_l, abs=1e-9)


# ---------------------------------------------------------------------------
# File-on-disk contract
# ---------------------------------------------------------------------------


class TestEnsureDat:
    def test_writes_spitfire_a06(self, tmp_path: Path):
        # Spitfire's ``naca4-923-a0.6``: design Cl ≈ 0.49 (the "4" in
        # the 4-digit nomenclature × 1/15 ≈ 0.267, but VSP carries the
        # design Cl directly via the Camber parm). We exercise the
        # writer with a representative Cl=0.3, a=0.6, t/c=0.12.
        out = ensure_naca_a_family_dat(
            name="naca4-923-a0.6",
            a=0.6, design_cl=0.3, thick_chord=0.12,
            airfoils_dir=tmp_path,
        )
        assert out.exists()
        assert out.stat().st_size > 200  # ~162 lines of coordinates
        # Header line follows the same convention as the 4-/5-digit
        # writers (uppercase, space after NACA).
        first_line = out.read_text().splitlines()[0]
        assert first_line == "NACA 4-923-A0.6"

    def test_writes_stratos_a10(self, tmp_path: Path):
        # Stratos_UL ``naca0-414-a1.0``: a=1.0 uniform-load mean line.
        out = ensure_naca_a_family_dat(
            name="naca0-414-a1.0",
            a=1.0, design_cl=0.4, thick_chord=0.14,
            airfoils_dir=tmp_path,
        )
        assert out.exists()
        assert out.stat().st_size > 200

    def test_idempotent_when_file_exists(self, tmp_path: Path):
        out = ensure_naca_a_family_dat(
            name="naca6series",
            a=0.5, design_cl=0.4, thick_chord=0.10,
            airfoils_dir=tmp_path,
        )
        first = out.read_text()
        # Subsequent call with nonsense parms must NOT overwrite.
        ensure_naca_a_family_dat(
            name="naca6series",
            a=0.99, design_cl=0.99, thick_chord=0.99,
            airfoils_dir=tmp_path,
        )
        assert out.read_text() == first

    def test_out_of_range_a_clamps_and_emits_warning(self, tmp_path: Path):
        # Defensive: if the upstream stores a corrupt a=1.5, the
        # writer must clamp + warn rather than raise log-of-negative.
        warnings_seen = []

        class _MockCtx:
            def add_warning(self, **kw):
                warnings_seen.append(kw)

        out = ensure_naca_a_family_dat(
            name="naca-clamped",
            a=1.5, design_cl=0.3, thick_chord=0.12,
            airfoils_dir=tmp_path,
            ctx=_MockCtx(),
        )
        assert out.exists()
        assert any("outside the physical range" in w["reason"] for w in warnings_seen)


# ---------------------------------------------------------------------------
# 6-series + 16-series writer naming round-trip
# ---------------------------------------------------------------------------


class TestSeriesNamingRoundTrip:
    """The dispatch in ``import_airfoil_from_xsec`` writes
    .dat with the name returned by ``naca_6series_name`` /
    ``naca_16series_name``. Pin those names so the schema's
    ``airfoil="naca65-410-a0.5"`` reference resolves to a real file."""

    def test_6series_canonical_name_matches_writer(self, tmp_path: Path):
        from app.converters.openvsp_airfoil import naca_6series_name

        name = naca_6series_name(
            series=65, ideal_cl=0.4, thick_chord=0.10, a=0.5
        )
        assert name == "naca65-410-a0.5"

        out = ensure_naca_a_family_dat(
            name=name,
            a=0.5, design_cl=0.4, thick_chord=0.10,
            airfoils_dir=tmp_path,
        )
        assert out.exists()
        assert out.name == "naca65-410-a0.5.dat"

    def test_16series_canonical_name_matches_writer(self, tmp_path: Path):
        from app.converters.openvsp_airfoil import naca_16series_name

        name = naca_16series_name(camber=0.04, thick_chord=0.12)
        assert name == "naca16-412"
        out = ensure_naca_a_family_dat(
            name=name,
            a=1.0, design_cl=0.04, thick_chord=0.12,
            airfoils_dir=tmp_path,
        )
        assert out.exists()
