"""Tests for gh-1075: shape-aware joint assignment in plan_spar.

Iron Law: write failing tests FIRST.

Spec (authoritative comment in gh-1075):
- `plan_spar` must emit `joint_to_next='telescoping'` only for tube pieces.
- For non-tube intermediate pieces (e.g. 'rod') the joint must be 'joiner',
  because a solid rod has no bore to telescope into.
"""

from __future__ import annotations

import pytest

from cad_designer.airplane.geometry.spar_solver import (
    SparRole,
    SparSpec,
    StationData,
    plan_spar,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _station(
    y_span: float,
    *,
    y_mm: float,
    band: tuple[float, float] = (-50.0, 50.0),
    required_od: float = 10.0,
    x_c: float = 0.4,
) -> StationData:
    return StationData(
        y_span=y_span,
        y_mm=y_mm,
        x_c=x_c,
        center_z=0.0,
        band_lo=band[0],
        band_hi=band[1],
        required_od=required_od,
    )


def _uniform_stations(n: int = 5, *, required_od: float = 10.0) -> list[StationData]:
    """Straight generously-thick wing: every station easily contains the OD."""
    return [
        _station(i / (n - 1), y_mm=i * 100.0, band=(-50.0, 50.0), required_od=required_od)
        for i in range(n)
    ]


def _multi_piece_stations() -> list[StationData]:
    """Stations that force a two-piece telescoping plan: root requires a large OD
    that won't fit the tight outboard sections, so the solver splits into at least
    two straight runs."""
    return [
        _station(0.0, y_mm=0.0, band=(-60.0, 60.0), required_od=50.0),
        _station(0.5, y_mm=500.0, band=(-60.0, 60.0), required_od=50.0),
        _station(0.5001, y_mm=500.1, band=(-10.0, 10.0), required_od=8.0),
        _station(1.0, y_mm=1000.0, band=(-10.0, 10.0), required_od=8.0),
    ]


# ---------------------------------------------------------------------------
# gh-1075: tube spec → intermediate joints must be 'telescoping'
# ---------------------------------------------------------------------------


class TestTubeJoints:
    def test_single_piece_tube_has_no_joint(self) -> None:
        spec = SparSpec(role=SparRole.FRONT, shape="tube")
        pieces = plan_spar(_uniform_stations(), spec)
        assert len(pieces) == 1
        assert pieces[0].joint_to_next is None

    def test_multi_piece_tube_intermediate_joint_is_telescoping(self) -> None:
        """Regression guard: tubes still telescope between pieces."""
        spec = SparSpec(role=SparRole.FRONT, shape="tube")
        pieces = plan_spar(_multi_piece_stations(), spec)
        assert len(pieces) >= 2, "expected at least two pieces from tight outboard band"
        # every piece except the last must be 'telescoping'
        for p in pieces[:-1]:
            assert p.joint_to_next == "telescoping", (
                f"tube piece at y={p.governing_y} should be 'telescoping', got {p.joint_to_next!r}"
            )
        # last piece has no joint
        assert pieces[-1].joint_to_next is None


# ---------------------------------------------------------------------------
# gh-1075: non-tube specs → intermediate joints must NOT be 'telescoping'
# They must be 'joiner' (the agreed token per spec validation comment).
# Parametrised over rod, rectangular and capped — all lack a bore to telescope.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("shape", ["rod", "rectangular", "capped"])
class TestNonTubeJoints:
    def test_single_piece_non_tube_has_no_joint(self, shape: str) -> None:
        spec = SparSpec(role=SparRole.FRONT, shape=shape)
        pieces = plan_spar(_uniform_stations(), spec)
        assert len(pieces) == 1
        assert pieces[0].joint_to_next is None

    def test_multi_piece_non_tube_intermediate_joint_is_joiner(self, shape: str) -> None:
        """Core of gh-1075: non-tube shapes cannot telescope → joint must be 'joiner'."""
        spec = SparSpec(role=SparRole.FRONT, shape=shape)
        pieces = plan_spar(_multi_piece_stations(), spec)
        assert len(pieces) >= 2, f"expected at least two pieces for shape={shape!r}"
        # every intermediate piece must be 'joiner', never 'telescoping'
        for p in pieces[:-1]:
            assert p.joint_to_next == "joiner", (
                f"{shape!r} piece at y={p.governing_y} should be 'joiner', got {p.joint_to_next!r}"
            )
        # last piece has no joint
        assert pieces[-1].joint_to_next is None

    def test_non_tube_piece_joint_is_never_telescoping(self, shape: str) -> None:
        """No non-tube piece (at any position) may carry joint_to_next='telescoping'."""
        spec = SparSpec(role=SparRole.FRONT, shape=shape)
        pieces = plan_spar(_multi_piece_stations(), spec)
        for p in pieces:
            assert p.joint_to_next != "telescoping", (
                f"{shape!r} piece at y={p.governing_y} must not be 'telescoping'"
            )
