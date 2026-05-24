"""Unit tests for the NACA 4-digit .dat generator (gh-700).

Closes the gap where OpenVSP-imported wings reference NACA 4-digit
airfoils that aren't in our curated ``components/airfoils`` library
(Cessna 172: naca0212, naca0209, naca0206 — none shipped). The
generator writes a Selig-format .dat on demand from the analytical
NACA 4-digit equation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.converters.openvsp_airfoil import (
    _naca4_camber_line,
    _naca4_thickness_offset,
    ensure_naca4_dat,
    naca4_coordinates,
)


# ---------------------------------------------------------------------------
# _naca4_thickness_offset
# ---------------------------------------------------------------------------


class TestThicknessOffset:
    def test_zero_at_le_and_te(self):
        # LE and TE: thickness offset is 0 (LE has sqrt(0)=0; TE is by
        # design close to 0 but the open-TE coefficient leaves ~0.001).
        assert _naca4_thickness_offset(0.0, 0.12) == 0.0
        # TE is not exactly zero with the open-TE coefficient, but small.
        te = _naca4_thickness_offset(1.0, 0.12)
        assert abs(te) < 0.002

    def test_peak_near_30pct_chord(self):
        # Standard NACA 4-digit thickness peaks at ~30% chord at value
        # = thickness/2 (since the polynomial is the half-thickness).
        # For NACA 0012: peak half-thickness ≈ 0.06.
        peak = max(_naca4_thickness_offset(x, 0.12) for x in [0.25, 0.30, 0.35])
        assert peak == pytest.approx(0.06, abs=0.005)

    def test_scales_linearly_with_thickness(self):
        x = 0.30
        t1 = _naca4_thickness_offset(x, 0.12)
        t2 = _naca4_thickness_offset(x, 0.24)
        assert t2 == pytest.approx(2 * t1, rel=1e-9)


# ---------------------------------------------------------------------------
# _naca4_camber_line
# ---------------------------------------------------------------------------


class TestCamberLine:
    def test_symmetric_when_camber_zero(self):
        yc, dyc = _naca4_camber_line(0.5, camber=0.0, camber_loc=0.4)
        assert yc == 0.0
        assert dyc == 0.0

    def test_symmetric_when_camber_loc_zero(self):
        # Degenerate input: avoid division-by-zero.
        yc, dyc = _naca4_camber_line(0.5, camber=0.02, camber_loc=0.0)
        assert yc == 0.0
        assert dyc == 0.0

    def test_naca_2412_peak_camber_at_40pct(self):
        # NACA 2412: max camber 2% at x=0.4.
        yc_peak, dyc_peak = _naca4_camber_line(0.4, camber=0.02, camber_loc=0.4)
        assert yc_peak == pytest.approx(0.02, rel=1e-9)
        # At the peak, dy/dx is zero (the parabola apex).
        assert dyc_peak == pytest.approx(0.0, abs=1e-12)

    def test_camber_is_zero_at_le_and_te(self):
        # 2412 camber line passes through (0, 0) and (1, 0).
        assert _naca4_camber_line(0.0, 0.02, 0.4)[0] == pytest.approx(0.0)
        assert _naca4_camber_line(1.0, 0.02, 0.4)[0] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# naca4_coordinates
# ---------------------------------------------------------------------------


class TestCoordinates:
    def test_returns_2n_plus_1_points(self):
        coords = naca4_coordinates(camber=0, camber_loc=0, thick_chord=0.12, n_half=20)
        # 21 upper (incl. LE) + 20 lower (LE shared) = 41
        assert len(coords) == 41

    def test_starts_and_ends_at_te(self):
        coords = naca4_coordinates(camber=0, camber_loc=0, thick_chord=0.12, n_half=20)
        # First and last point are at x ≈ 1.0 (TE), within thickness-offset
        # rotation tolerance for symmetric profiles.
        assert coords[0][0] == pytest.approx(1.0, abs=0.01)
        assert coords[-1][0] == pytest.approx(1.0, abs=0.01)

    def test_le_at_origin_for_symmetric(self):
        coords = naca4_coordinates(camber=0, camber_loc=0, thick_chord=0.12, n_half=20)
        # Middle point should be at the LE (x ≈ 0).
        middle = coords[len(coords) // 2]
        assert middle[0] == pytest.approx(0.0, abs=0.001)
        assert middle[1] == pytest.approx(0.0, abs=0.001)

    def test_naca_0012_max_thickness(self):
        coords = naca4_coordinates(camber=0, camber_loc=0, thick_chord=0.12, n_half=80)
        # Maximum y across all upper points: 0.06 (half-thickness for 12%)
        max_y = max(y for _x, y in coords)
        assert max_y == pytest.approx(0.06, abs=0.003)

    def test_naca_2412_max_camber_offset_at_40pct(self):
        coords = naca4_coordinates(camber=0.02, camber_loc=0.4, thick_chord=0.12, n_half=80)
        # The MEAN of upper+lower y at each x is the camber line.
        # Easiest sanity: at x≈0.4, mean(yu, yl) should ≈ 0.02 (max camber)
        # Find the pair of points closest to x=0.4 on upper + lower
        n = len(coords)
        upper = coords[: n // 2 + 1]   # TE → LE
        lower = coords[n // 2 :]       # LE → TE
        # closest to x=0.4 on each side
        u_at_04 = min(upper, key=lambda p: abs(p[0] - 0.4))
        l_at_04 = min(lower, key=lambda p: abs(p[0] - 0.4))
        mean_y = (u_at_04[1] + l_at_04[1]) / 2
        assert mean_y == pytest.approx(0.02, abs=0.003)

    def test_naca_2412_camber_positive(self):
        # Cambered profile: upper surface y > 0 in the middle.
        coords = naca4_coordinates(camber=0.02, camber_loc=0.4, thick_chord=0.12, n_half=40)
        # x near 0.5: y on upper surface should be clearly above 0
        for x, y in coords[: len(coords) // 2]:
            if abs(x - 0.5) < 0.05:
                assert y > 0.04   # camber + half-thickness


# ---------------------------------------------------------------------------
# ensure_naca4_dat — file I/O
# ---------------------------------------------------------------------------


class TestEnsureDat:
    def test_writes_dat_when_missing(self, tmp_path: Path):
        path = ensure_naca4_dat(
            name="naca0212",
            camber=0.0,
            camber_loc=0.2,
            thick_chord=0.12,
            airfoils_dir=tmp_path,
        )
        assert path == tmp_path / "naca0212.dat"
        assert path.exists()
        text = path.read_text()
        # Header + many coord lines.
        assert text.splitlines()[0].startswith("NACA")
        assert len(text.splitlines()) > 50

    def test_idempotent_does_not_overwrite(self, tmp_path: Path):
        target = tmp_path / "naca0012.dat"
        target.write_text("HAND-WRITTEN\n0 0\n1 0\n")
        original = target.read_text()
        ensure_naca4_dat(
            name="naca0012",
            camber=0,
            camber_loc=0,
            thick_chord=0.12,
            airfoils_dir=tmp_path,
        )
        # File unchanged.
        assert target.read_text() == original

    def test_creates_airfoils_dir_if_missing(self, tmp_path: Path):
        nested = tmp_path / "nested" / "airfoils"
        ensure_naca4_dat(
            name="naca0008",
            camber=0,
            camber_loc=0,
            thick_chord=0.08,
            airfoils_dir=nested,
        )
        assert (nested / "naca0008.dat").exists()

    def test_silent_on_readonly_filesystem(self, tmp_path: Path, monkeypatch):
        # Simulate OSError on write — function must not raise.
        def boom(*_a, **_kw):  # noqa: ANN002,ANN003
            raise OSError("read-only")

        target = tmp_path / "naca0010.dat"
        monkeypatch.setattr(Path, "write_text", boom)
        # Should not raise; returns the planned path.
        result = ensure_naca4_dat(
            name="naca0010",
            camber=0,
            camber_loc=0,
            thick_chord=0.10,
            airfoils_dir=tmp_path,
        )
        assert result == target
        assert not target.exists()

    def test_dat_lines_well_formed(self, tmp_path: Path):
        """Generated file is readable as plain text — header + coord pairs."""
        path = ensure_naca4_dat(
            name="naca0012",
            camber=0,
            camber_loc=0,
            thick_chord=0.12,
            airfoils_dir=tmp_path,
        )
        lines = path.read_text().splitlines()
        assert lines[0].startswith("NACA")
        # Every non-header line is "x  y" with two floats.
        for line in lines[1:]:
            parts = line.split()
            assert len(parts) == 2
            float(parts[0])  # raises ValueError on garbage
            float(parts[1])
